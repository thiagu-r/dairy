from django.views.generic import TemplateView, ListView, CreateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Count, Sum, Q, Prefetch
from web_project import TemplateLayout
from web_project.mixins import DeliveryTeamRequiredMixin
from .models import DeliveryOrder, DailyDeliveryTeam, Distributor, PurchaseOrder, PurchaseOrderItem, DeliveryTeam, LoadingOrder
from apps.sales.models import SalesOrder, OrderItem
from apps.seller.models import Route
from decimal import Decimal
import json
from django.db import transaction, OperationalError
from django.db.utils import IntegrityError
import time
from django.shortcuts import render
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.http import QueryDict
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required


class DeliveryDashboardView(LoginRequiredMixin, DeliveryTeamRequiredMixin, TemplateView):
    template_name = "delivery/dashboard.html"

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        today = timezone.now().date()
        user = self.request.user

        # Base queryset for delivery orders
        delivery_orders = DeliveryOrder.objects.select_related(
            'seller', 'route', 'sales_order', 
            'loading_order', 'loading_order__purchase_order'
        ).filter(delivery_date=today)

        if user.role == 'DISTRIBUTOR':
            # For distributor, show all orders under their distribution
            distributor = Distributor.objects.get(user=user)
            delivery_teams = distributor.delivery_teams.all()
            context['distributor'] = distributor
            
            # Filter orders for distributor's teams
            delivery_orders = delivery_orders.filter(
                loading_order__purchase_order__delivery_team__in=delivery_teams
            )
        else:
            # For delivery team members, show only their assigned orders
            daily_teams = DailyDeliveryTeam.objects.filter(
                Q(driver__user=user) |
                Q(supervisor__user=user) |
                Q(delivery_man__user=user),
                delivery_date=today
            ).select_related('delivery_team', 'route')
            
            context['daily_teams'] = daily_teams
            
            # Filter orders for team member's assignments
            team_ids = daily_teams.values_list('delivery_team', flat=True)
            delivery_orders = delivery_orders.filter(
                loading_order__purchase_order__delivery_team__in=team_ids
            )

        context.update({
            'total_orders': delivery_orders.count(),
            'completed_orders': delivery_orders.filter(status='completed').count(),
            'pending_orders': delivery_orders.filter(status='pending').count(),
            'in_progress_orders': delivery_orders.filter(status='in_progress').count(),
            'total_amount': delivery_orders.aggregate(
                total=Sum('total_price')
            )['total'] or 0,
            'collected_amount': delivery_orders.aggregate(
                total=Sum('amount_collected')
            )['total'] or 0,
            
            # Recent orders
            'recent_orders': delivery_orders.order_by('-created_at')[:10],
            
            # Route summary
            'route_summary': delivery_orders.values('route__name').annotate(
                total_orders=Count('id'),
                completed_orders=Count('id', filter=Q(status='completed')),
                total_amount=Sum('total_price'),
                collected_amount=Sum('amount_collected')
            ).order_by('route__name'),
        })

        return context

class PurchaseOrderListView(LoginRequiredMixin, DeliveryTeamRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'delivery/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    
    def get_queryset(self):
        return PurchaseOrder.objects.select_related(
            'route', 
            'delivery_team'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context.update({
            'routes': Route.objects.all().order_by('name'),
            'delivery_teams': DeliveryTeam.objects.filter(is_active=True).order_by('name'),
            'title': 'Purchase Orders'
        })
        return context

def get_route_sales_summary(request):
    route_id = request.GET.get('route')
    delivery_date = request.GET.get('delivery_date')

    try:
        # Get all sales orders for the route and date
        sales_summary = SalesOrder.objects.filter(
            seller__route_id=route_id,
            delivery_date=delivery_date,
            status='draft'  # Only include confirmed orders
        ).values(
            'items__product__id',
            'items__product__code',
            'items__product__name'
        ).annotate(
            total_quantity=Sum('items__quantity')
        ).filter(total_quantity__gt=0)  # Only include products with quantities > 0

        items_data = [{
            'product_id': str(item['items__product__id']),
            'product_name': f"{item['items__product__code']} - {item['items__product__name']}",
            'sales_quantity': str(item['total_quantity']),
            'extra_quantity': '0.000',
            'remaining_quantity': '0.000',
            'total_quantity': str(item['total_quantity'])
        } for item in sales_summary]

        return JsonResponse({'items': items_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@transaction.atomic
def create_purchase_order(request):
    if request.method == 'GET':
        context = {
            'routes': Route.objects.all().order_by('name'),
            'delivery_teams': DeliveryTeam.objects.filter(is_active=True).order_by('name')
        }
        return render(request, 'delivery/purchase_order_form.html', context)
    
    elif request.method == 'POST':
        try:
            delivery_team_id = request.POST.get('delivery_team')
            route_id = request.POST.get('route')
            delivery_date = request.POST.get('delivery_date')
            
            # Validate required fields
            if not all([delivery_team_id, route_id, delivery_date]):
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required fields'
                }, status=400)
            
            # Check for existing order
            existing_order = PurchaseOrder.objects.filter(
                delivery_team_id=delivery_team_id,
                route_id=route_id,
                delivery_date=delivery_date
            ).first()
            
            if existing_order:
                return JsonResponse({
                    'success': False,
                    'error': 'Purchase order already exists for this team, route and date'
                }, status=400)
            
            # Create purchase order
            purchase_order = PurchaseOrder.objects.create(
                delivery_team_id=delivery_team_id,
                route_id=route_id,
                delivery_date=delivery_date,
                status='draft',
                notes=request.POST.get('notes'),
                created_by=request.user,
                updated_by=request.user
            )
            
            # Create purchase order items
            items_data = json.loads(request.POST.get('items', '[]'))
            for item in items_data:
                sales_qty = Decimal(item['sales_quantity'])
                extra_qty = Decimal(item['extra_quantity'])
                remaining_qty = Decimal(item['remaining_quantity'])
                
                # Validate quantities
                if (sales_qty + extra_qty - remaining_qty) < sales_qty:
                    raise ValueError(f"Total quantity must be greater than or equal to sales quantity for {item['product_name']}")
                
                PurchaseOrderItem.objects.create(
                    purchase_order=purchase_order,
                    product_id=item['product_id'],
                    sales_order_quantity=sales_qty,
                    extra_quantity=extra_qty,
                    remaining_quantity=remaining_qty
                )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

class PurchaseOrderEditView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            purchase_order = get_object_or_404(
                PurchaseOrder.objects.select_related('route', 'delivery_team'),
                pk=pk
            )
            
            context = {
                'purchase_order': purchase_order,
                'routes': Route.objects.all().order_by('name'),
                'delivery_teams': DeliveryTeam.objects.filter(is_active=True).order_by('name'),
            }
            
            return render(request, 'delivery/purchase_order_edit_form.html', context)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

    @transaction.atomic
    def put(self, request, pk):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with transaction.atomic():
                    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
                    data = QueryDict(request.body)
                    
                    # Update purchase order
                    purchase_order.route_id = data.get('route')
                    purchase_order.delivery_team_id = data.get('delivery_team')
                    purchase_order.delivery_date = data.get('delivery_date')
                    purchase_order.notes = data.get('notes', '')
                    purchase_order.save()
                    
                    # Update items
                    for item in purchase_order.items.all():
                        extra_qty_key = f'extra_qty_{item.product.id}'
                        remaining_qty_key = f'remaining_qty_{item.product.id}'
                        
                        if extra_qty_key in data:
                            item.extra_quantity = Decimal(str(data[extra_qty_key]))
                        if remaining_qty_key in data:
                            item.remaining_quantity = Decimal(str(data[remaining_qty_key]))
                        item.save()

                    # Fetch updated data
                    purchase_orders = PurchaseOrder.objects.select_related(
                        'route', 'delivery_team'
                    ).order_by('-delivery_date', '-created_at')
                    
                    html_content = render_to_string(
                        'delivery/partials/purchase_order_table.html',
                        {'purchase_orders': purchase_orders},
                        request=request
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'html': html_content,
                        'message': 'Purchase order updated successfully'
                    })

            except OperationalError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    return JsonResponse({
                        'success': True,  # Still return success since the update probably succeeded
                        'refresh': True,  # Signal the frontend to refresh the page
                        'message': 'Purchase order updated, refreshing page...'
                    })
                time.sleep(0.1)  # Wait briefly before retrying
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'refresh': True
                }, status=400)

class PurchaseOrderDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        purchase_order = get_object_or_404(
            PurchaseOrder.objects.select_related(
                'route', 
                'delivery_team',
                'delivery_team__distributor'
            ).prefetch_related('items__product'),
            pk=pk
        )
        
        context = {
            'purchase_order': purchase_order,
            'title': f'Purchase Order Details - {purchase_order.order_number}'
        }
        return render(request, 'delivery/purchase_order_detail.html', context)

class DeliveryTeamListView(LoginRequiredMixin, ListView):
    model = DeliveryTeam
    template_name = 'delivery/team_list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        queryset = DeliveryTeam.objects.select_related('distributor', 'route').all()
        if self.request.user.role == 'DISTRIBUTOR':
            distributor = Distributor.objects.get(user=self.request.user)
            queryset = queryset.filter(distributor=distributor)
        return queryset.order_by('distributor', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['routes'] = Route.objects.all().order_by('name')
        if self.request.user.role == 'DISTRIBUTOR':
            context['distributor'] = Distributor.objects.get(user=self.request.user)
        else:
            context['distributors'] = Distributor.objects.all().order_by('name')
        return context

class DeliveryTeamCreateView(LoginRequiredMixin, View):
    def get(self, request):
        context = {
            'routes': Route.objects.all().order_by('name')
        }
        if request.user.role == 'DISTRIBUTOR':
            distributor = Distributor.objects.get(user=request.user)
            context['distributor'] = distributor
        else:
            context['distributors'] = Distributor.objects.all().order_by('name')
        
        return render(request, 'delivery/team_form_modal.html', context)

    def post(self, request):
        try:
            name = request.POST.get('name')
            route_id = request.POST.get('route')
            distributor_id = request.POST.get('distributor')
            
            if request.user.role == 'DISTRIBUTOR':
                distributor = Distributor.objects.get(user=request.user)
            else:
                distributor = Distributor.objects.get(id=distributor_id)
            
            team = DeliveryTeam.objects.create(
                name=name,
                route_id=route_id,
                distributor=distributor,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Team created successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

def get_delivery_teams(request):
    route_id = request.GET.get('route')
    if route_id:
        teams = DeliveryTeam.objects.filter(
            route_id=route_id,
            is_active=True
        ).order_by('name')
        return JsonResponse({
            'teams': [{'id': team.id, 'name': team.name} for team in teams]
        })
    return JsonResponse({'teams': []})

@transaction.atomic
def update_extra_quantity(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            extra_quantity = Decimal(str(data.get('extra_quantity', '0')))
            purchase_order_id = data.get('purchase_order_id')

            item = PurchaseOrderItem.objects.get(
                purchase_order_id=purchase_order_id,
                product_id=product_id
            )
            item.extra_quantity = extra_quantity
            item.save()  # This will trigger the save method that recalculates total_quantity

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def check_existing_purchase_order(request):
    route_id = request.GET.get('route')
    delivery_date = request.GET.get('delivery_date')
    team_id = request.GET.get('team')

    try:
        existing_order = PurchaseOrder.objects.filter(
            route_id=route_id,
            delivery_date=delivery_date,
            delivery_team_id=team_id
        ).prefetch_related('items__product').first()

        if existing_order:
            items_data = [{
                'product_id': str(item.product.id),
                'product_name': f"{item.product.code} - {item.product.name}",
                'sales_quantity': str(item.sales_order_quantity),
                'extra_quantity': str(item.extra_quantity),
                'remaining_quantity': str(item.remaining_quantity),
                'total_quantity': str(item.total_quantity)
            } for item in existing_order.items.all()]

            return JsonResponse({
                'exists': True,
                'order_id': existing_order.id,
                'items': items_data
            })

        return JsonResponse({'exists': False})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["POST"])
def update_purchase_order_item(request, pk, product_id):
    try:
        if not request.body:
            return JsonResponse({
                'success': False,
                'error': 'No data provided'
            }, status=400)
            
        purchase_order = PurchaseOrder.objects.get(pk=pk)
        item = purchase_order.items.get(product_id=product_id)
        
        data = json.loads(request.body)
        
        if 'extra_quantity' in data:
            item.extra_quantity = Decimal(str(data['extra_quantity']))
        if 'remaining_quantity' in data:
            item.remaining_quantity = Decimal(str(data['remaining_quantity']))
            
        item.save()
        
        return JsonResponse({
            'success': True,
            'total_quantity': str(item.total_quantity)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except (PurchaseOrder.DoesNotExist, PurchaseOrderItem.DoesNotExist) as e:
        return JsonResponse({
            'success': False,
            'error': f'Item not found: {str(e)}'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def check_existing_order(request):
    route_id = request.GET.get('route')
    delivery_date = request.GET.get('delivery_date')
    exclude_id = request.GET.get('exclude_id')

    query = PurchaseOrder.objects.filter(
        route_id=route_id,
        delivery_date=delivery_date
    )
    
    if exclude_id:
        query = query.exclude(id=exclude_id)
    
    exists = query.exists()
    return JsonResponse({'exists': exists})

class LoadingOrderListView(LoginRequiredMixin, ListView):
    model = LoadingOrder
    template_name = 'delivery/loading_order_list.html'
    context_object_name = 'loading_orders'
    
    def get_queryset(self):
        return LoadingOrder.objects.select_related(
            'purchase_order',
            'purchase_order__route',
            'purchase_order__delivery_team'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'routes': Route.objects.all().order_by('name'),
            'purchase_orders': PurchaseOrder.objects.filter(
                status='confirmed'
            ).select_related('route').order_by('-created_at'),
            'title': 'Loading Orders'
        })
        return context

@login_required
def check_purchase_order(request):
    route_id = request.GET.get('route')
    delivery_date = request.GET.get('delivery_date')

    try:
        purchase_order = PurchaseOrder.objects.filter(
            route_id=route_id,
            delivery_date=delivery_date,
            # status='confirmed'  # Only confirmed purchase orders
        ).prefetch_related('items__product').first()

        if purchase_order:
            items_data = [{
                'product_name': f"{item.product.code} - {item.product.name}",
                'total_quantity': str(item.total_quantity),
                'remaining_quantity': str(item.remaining_quantity)
            } for item in purchase_order.items.all()]

            return JsonResponse({
                'exists': True,
                'purchase_order_id': purchase_order.id,
                'items': items_data
            })

        return JsonResponse({'exists': False})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def create_loading_order(request):
    if request.method == 'POST':
        try:
            purchase_order_id = request.POST.get('purchase_order_id')
            purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)

            # Check if loading order already exists
            existing_order = LoadingOrder.objects.filter(
                purchase_order=purchase_order,
                loading_date=request.POST.get('loading_date')
            ).exists()

            if existing_order:
                return JsonResponse({
                    'success': False,
                    'error': 'Loading order already exists for this purchase order and date'
                }, status=400)

            loading_order = LoadingOrder.objects.create(
                purchase_order=purchase_order,
                route_id=request.POST.get('route'),
                loading_date=request.POST.get('loading_date'),
                loading_time=request.POST.get('loading_time'),
                crates_loaded=request.POST.get('crates_loaded'),
                notes=request.POST.get('notes'),
                status='draft',
                created_by=request.user,
                updated_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Loading order created successfully'
            })
            
        except PurchaseOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Purchase order not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=400)

class LoadingOrderDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            loading_order = get_object_or_404(
                LoadingOrder.objects.select_related(
                    'purchase_order',
                    'purchase_order__route',
                    'purchase_order__delivery_team'
                ).prefetch_related('purchase_order__items__product'),
                pk=pk
            )
            
            context = {
                'loading_order': loading_order,
                'title': f'Loading Order Details - {loading_order.order_number}'
            }
            return render(request, 'delivery/loading_order_detail.html', context)
            
        except Exception as e:
            messages.error(request, str(e))
            return redirect('delivery:loading-order-list')

class LoadingOrderEditView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            loading_order = get_object_or_404(
                LoadingOrder.objects.select_related(
                    'purchase_order',
                    'purchase_order__route',
                    'purchase_order__delivery_team'
                ),
                pk=pk
            )
            
            if loading_order.status != 'draft':
                messages.error(request, 'Only draft loading orders can be edited')
                return redirect('delivery:loading-order-list')
            
            context = {
                'loading_order': loading_order,
                'routes': Route.objects.all().order_by('name')
            }
            return render(request, 'delivery/loading_order_edit_form.html', context)
            
        except Exception as e:
            messages.error(request, str(e))
            return redirect('delivery:loading-order-list')

    def post(self, request, pk):
        try:
            loading_order = get_object_or_404(LoadingOrder, pk=pk)
            
            if loading_order.status != 'draft':
                return JsonResponse({
                    'success': False,
                    'error': 'Only draft loading orders can be edited'
                }, status=400)
            
            loading_order.loading_date = request.POST.get('loading_date')
            loading_order.loading_time = request.POST.get('loading_time')
            loading_order.notes = request.POST.get('notes')
            loading_order.updated_by = request.user
            loading_order.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Loading order updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
