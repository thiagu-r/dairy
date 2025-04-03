from django.views.generic import TemplateView, ListView, CreateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Count, Sum, Q, Prefetch
from web_project import TemplateLayout
from web_project.mixins import DeliveryTeamRequiredMixin
from .models import (
    DeliveryOrder,
    DailyDeliveryTeam,
    Distributor,
    PurchaseOrder,
    PurchaseOrderItem,
    DeliveryTeam,
    LoadingOrder,
    LoadingOrderItem,
    DeliveryOrderItem,
    BrokenOrder,
    BrokenOrderItem,
    ReturnedOrder,
    ReturnedOrderItem,
    FutureOrderRequest,
    FutureOrderRequestItem,
    DeliveryExpense,
    CashDenomination,
    SellerPriceCache,
    GeneralPriceCache,
    PublicSale,
    PublicSaleItem
 )
from apps.sales.models import SalesOrder, OrderItem
from apps.seller.models import Route, Seller
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
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse

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
            items_data_str = request.POST.get('items_data')
            print(f"Items data received: {items_data_str}")

            if not items_data_str:
                return JsonResponse({
                    'success': False,
                    'error': 'No items data provided'
                }, status=400)

            try:
                items_data = json.loads(items_data_str)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid items data format: {str(e)}'
                }, status=400)

            if not items_data:
                return JsonResponse({
                    'success': False,
                    'error': 'No items to process'
                }, status=400)

            print(f"Processing {len(items_data)} items")
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

            # Create the loading order
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

            # Create loading order items from purchase order items
            purchase_order_items = purchase_order.items.all()
            for po_item in purchase_order_items:
                # Create loading order item
                LoadingOrderItem.objects.create(
                    loading_order=loading_order,
                    product=po_item.product,
                    purchase_order_quantity=po_item.total_quantity,
                    loaded_quantity=po_item.total_quantity,  # Initially set to purchase order quantity
                    total_quantity=po_item.total_quantity,   # Initially set to purchase order quantity
                    remaining_quantity=po_item.total_quantity  # Initially all quantity is remaining
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
                'items': loading_order.purchase_order.items.all(),
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
            loading_order.crates_loaded = request.POST.get('crates_loaded')
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

class DeliveryOrderListView(LoginRequiredMixin, TemplateView):
    template_name = "delivery/delivery_order_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # Add filters
        status_filter = self.request.GET.get('status', 'pending')
        date_filter = self.request.GET.get('date', timezone.now().date().isoformat())
        route_filter = self.request.GET.get('route')

        # Base queryset
        orders = DeliveryOrder.objects.select_related(
            'route', 'seller', 'sales_order', 'loading_order'
        )
        print('delivery orders: ', orders)
        print('status filter: ', status_filter)
        print('date filter: ', date_filter)
        print('route filter: ', route_filter)

        # Apply filters
        # if status_filter != 'all':
        #     orders = orders.filter(status=status_filter)

        # if date_filter:
        #     orders = orders.filter(delivery_date=date_filter)

        # if route_filter:
        #     orders = orders.filter(route_id=route_filter)

        # Process orders to add display properties
        delivery_orders = orders.order_by('-delivery_date', '-delivery_time')
        print('delivery orders after filters: ', delivery_orders)
        for order in delivery_orders:
            # Add status color
            if order.status == 'pending':
                order.status_color = 'warning'
            elif order.status == 'in_progress':
                order.status_color = 'info'
            elif order.status == 'completed':
                order.status_color = 'success'
            else:
                order.status_color = 'danger'

            # Format display values
            order.total_amount = order.total_price if order.total_price is not None else 0
            order.paid_amount = order.amount_collected if order.amount_collected is not None else 0

            # Debug
            print(f"Order {order.pk}: total_price={order.total_price}, total_amount={order.total_amount}")

        context.update({
            'delivery_orders': delivery_orders,
            'routes': Route.objects.all().order_by('name'),
            'sellers': Seller.objects.all().order_by('store_name'),
            'sales_orders': SalesOrder.objects.filter(status='confirmed').order_by('-created_at'),
            'current_status': status_filter,
            'current_date': date_filter,
            'current_route': route_filter,
        })
        return context

class DeliveryOrderCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, pk=None):
        routes = Route.objects.all().order_by('name')
        sellers = Seller.objects.all().order_by('store_name')
        sales_orders = SalesOrder.objects.filter(status='confirmed').order_by('-created_at')

        # If pk is provided, we're editing an existing order
        delivery_order = None
        if pk:
            try:
                delivery_order = DeliveryOrder.objects.select_related(
                    'route', 'seller', 'sales_order', 'loading_order'
                ).prefetch_related('items__product').get(pk=pk)
                print(f"Editing delivery order: {delivery_order.pk}")
            except DeliveryOrder.DoesNotExist:
                print(f"Delivery order with pk={pk} not found")
                return redirect('delivery:delivery-order-list')

        return render(request, 'delivery/delivery_order_form.html', {
            'routes': routes,
            'sellers': sellers,
            'sales_orders': sales_orders,
            'delivery_order': delivery_order,
            'is_edit': pk is not None,
        })

    # We now handle updates in the post method

    def post(self, request, pk=None):
        try:
            if pk:
                print(f"Received delivery order update request for order {pk}")
            else:
                print("Received delivery order creation request")

            # Get form data
            route_id = request.POST.get('route_id')
            seller_id = request.POST.get('seller_id')
            delivery_date = request.POST.get('delivery_date')
            delivery_time = request.POST.get('delivery_time')
            payment_method = request.POST.get('payment_method')
            notes = request.POST.get('notes')
            amount_collected = request.POST.get('amount_collected', '0')

            # Get items data
            items_data_str = request.POST.get('items_data')
            print(f"Items data received: {items_data_str}")

            if not items_data_str:
                return JsonResponse({
                    'status': 'error',
                    'error': 'No items data provided'
                }, status=400)

            try:
                items_data = json.loads(items_data_str)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return JsonResponse({
                    'status': 'error',
                    'error': f'Invalid items data format: {str(e)}'
                }, status=400)

            # Validate required fields
            if pk:
                # If editing, get the existing delivery order to fill in missing fields
                try:
                    existing_order = DeliveryOrder.objects.get(pk=pk)

                    # Use existing values if not provided in the form
                    route_id = route_id or existing_order.route_id
                    seller_id = seller_id or existing_order.seller_id
                    delivery_date = delivery_date or existing_order.delivery_date
                    delivery_time = delivery_time or existing_order.delivery_time.strftime('%H:%M')

                    print(f"Using existing values for edit: route={route_id}, seller={seller_id}, date={delivery_date}, time={delivery_time}")
                except DeliveryOrder.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'error': f'Delivery order with ID {pk} not found'
                    }, status=404)

            # Now validate that we have all required fields
            if not all([route_id, seller_id, delivery_date, delivery_time]):
                missing = []
                if not route_id: missing.append('route')
                if not seller_id: missing.append('seller')
                if not delivery_date: missing.append('delivery date')
                if not delivery_time: missing.append('delivery time')

                return JsonResponse({
                    'status': 'error',
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)

            # Find sales order if not provided
            sales_order_id = request.POST.get('sales_order_id')
            if not sales_order_id:
                sales_order = SalesOrder.objects.filter(
                    seller_id=seller_id,
                    delivery_date=delivery_date,
                    status='draft'
                ).first()

                if sales_order:
                    sales_order_id = sales_order.id

            # Find a loading order for this route and date
            loading_order = LoadingOrder.objects.filter(
                route_id=route_id,
                loading_date=delivery_date,
                # status='completed'
            ).first()

            # Even if there's no loading order, we'll continue
            if not loading_order:
                print(f"No loading order found for route {route_id} and date {delivery_date}, but continuing anyway")

            # First, calculate the total price and prepare items
            total_price = Decimal('0.00')
            items_to_create = []

            for item in items_data:
                ordered_qty = Decimal(item['ordered_quantity'])
                delivered_qty = Decimal(item['delivered_quantity'])
                unit_price = Decimal(item['unit_price'])
                item_total = delivered_qty * unit_price
                total_price += item_total

                # Make sure product_id is correctly handled
                try:
                    product_id = int(item['product_id'])
                    # Get extra_quantity if it exists, otherwise calculate it as delivered - ordered
                    extra_qty = Decimal(item.get('extra_quantity', 0))

                    # If extra_quantity is not provided but delivered_quantity > ordered_quantity,
                    # calculate extra_quantity as the difference
                    if extra_qty == 0 and delivered_qty > ordered_qty:
                        extra_qty = delivered_qty - ordered_qty
                        print(f"Calculated extra_quantity: {extra_qty} (delivered={delivered_qty}, ordered={ordered_qty})")

                    items_to_create.append({
                        'product_id': product_id,
                        'ordered_quantity': ordered_qty,
                        'extra_quantity': extra_qty,
                        'delivered_quantity': delivered_qty,
                        'unit_price': unit_price,
                        'total_price': item_total
                    })
                except (ValueError, TypeError) as e:
                    print(f"Error processing product ID {item['product_id']}: {e}")

            # Get last order's total balance for this seller
            last_order = DeliveryOrder.objects.filter(
                seller_id=seller_id,
                delivery_date__lt=delivery_date
            ).order_by('-delivery_date', '-delivery_time').first()

            # Handle the case where there's no previous order
            if last_order:
                opening_balance = last_order.total_balance
                print(f"Found previous order with balance: {opening_balance}")
            else:
                opening_balance = Decimal('0.00')
                print("No previous order found, setting opening balance to 0")
            amount_collected_decimal = Decimal(amount_collected)
            balance_amount = total_price - amount_collected_decimal
            total_balance = opening_balance + balance_amount

            # If pk is provided, update existing order, otherwise create new one
            if pk:
                # Get the existing delivery order
                delivery_order = get_object_or_404(DeliveryOrder, pk=pk)

                # Update the delivery order fields
                delivery_order.route_id = route_id
                delivery_order.seller_id = seller_id
                delivery_order.sales_order_id = sales_order_id if sales_order_id else None
                delivery_order.loading_order = loading_order if loading_order else None
                delivery_order.delivery_date = delivery_date
                delivery_order.delivery_time = delivery_time
                delivery_order.payment_method = payment_method
                delivery_order.notes = notes
                delivery_order.total_price = total_price
                delivery_order.opening_balance = opening_balance
                delivery_order.amount_collected = amount_collected_decimal
                delivery_order.balance_amount = balance_amount
                delivery_order.total_balance = total_balance
                delivery_order.updated_by = request.user
                delivery_order.save()

                # Delete existing items
                delivery_order.items.all().delete()
                print(f"Deleted existing items for delivery order {pk}")
            else:
                # Create new delivery order
                delivery_order = DeliveryOrder.objects.create(
                    route_id=route_id,
                    seller_id=seller_id,
                    sales_order_id=sales_order_id if sales_order_id else None,
                    loading_order=loading_order if loading_order else None,
                    delivery_date=delivery_date,
                    delivery_time=delivery_time,
                    payment_method=payment_method,
                    notes=notes,
                    total_price=total_price,
                    opening_balance=opening_balance,
                    amount_collected=amount_collected_decimal,
                    balance_amount=balance_amount,
                    total_balance=total_balance,
                    status='pending',
                    created_by=request.user,
                    updated_by=request.user
                )

            print(f"Created delivery order: {delivery_order.id}")

            # Now create the items
            print(f"Creating {len(items_to_create)} delivery order items")
            for item_data in items_to_create:
                try:
                    print(f"Creating delivery order item with data: {item_data}")
                    DeliveryOrderItem.objects.create(
                        delivery_order=delivery_order,
                        **item_data
                    )
                    print(f"Successfully created delivery order item for product {item_data['product_id']}")
                except Exception as e:
                    print(f"Error creating delivery order item: {str(e)}")

            # Recalculate totals after all items have been added
            delivery_order.recalculate_totals()

            return JsonResponse({
                'status': 'success',
                'message': f"Delivery order {'updated' if pk else 'created'} successfully"
            })

        except Exception as e:
            action = 'updating' if pk else 'creating'
            print(f"Error {action} delivery order: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=400)

class DeliveryOrderDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, pk):
        try:
            delivery_order = get_object_or_404(
                DeliveryOrder.objects.select_related(
                    'route', 'seller', 'sales_order', 'loading_order'
                ).prefetch_related('items__product'),
                pk=pk
            )

            # Get items and debug
            items = delivery_order.items.all()
            print(f"Delivery order {pk} has {items.count()} items")
            for item in items:
                print(f"Item: product={item.product.name if item.product else 'None'}, ordered={item.ordered_quantity}, delivered={item.delivered_quantity}")

            context = TemplateLayout.init(self, {
                'delivery_order': delivery_order,
                'items': items,
                'title': f'Delivery Order Details - {delivery_order.order_number}'
            })

            return render(request, 'delivery/delivery_order_detail.html', context)

        except Exception as e:
            messages.error(request, str(e))
            return redirect('delivery:delivery-order-list')

class BrokenOrderListView(LoginRequiredMixin, TemplateView):
    template_name = "delivery/broken_order_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        date_filter = self.request.GET.get('date', timezone.now().date().isoformat())
        route_filter = self.request.GET.get('route')

        orders = BrokenOrder.objects.select_related('route', 'loading_order')

        if date_filter:
            orders = orders.filter(report_date=date_filter)

        if route_filter:
            orders = orders.filter(route_id=route_filter)

        context.update({
            'orders': orders.order_by('-report_date', '-report_time'),
            'routes': Route.objects.all().order_by('name'),
            'current_date': date_filter,
            'current_route': route_filter,
        })
        return context

class BrokenOrderCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        routes = Route.objects.all().order_by('name')
        return render(request, 'delivery/broken_order_form.html', {
            'routes': routes,
        })

    def post(self, request):
        try:
            data = json.loads(request.body)

            broken_order = BrokenOrder.objects.create(
                loading_order_id=data['loading_order_id'],
                route_id=data['route_id'],
                report_date=data['report_date'],
                report_time=data['report_time'],
                notes=data.get('notes'),
                created_by=request.user,
                updated_by=request.user
            )

            for item in data['items']:
                BrokenOrderItem.objects.create(
                    broken_order=broken_order,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    reason=item['reason']
                )

            return JsonResponse({
                'status': 'success',
                'order_number': broken_order.order_number
            })

        except Exception as e:
            return HttpResponseBadRequest(str(e))

class ReturnedOrderListView(LoginRequiredMixin, TemplateView):
    template_name = "delivery/returned_order_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        date_filter = self.request.GET.get('date', timezone.now().date().isoformat())
        route_filter = self.request.GET.get('route')

        orders = ReturnedOrder.objects.select_related(
            'route', 'delivery_order', 'delivery_order__seller'
        )

        if date_filter:
            orders = orders.filter(return_date=date_filter)

        if route_filter:
            orders = orders.filter(route_id=route_filter)

        context.update({
            'orders': orders.order_by('-return_date', '-return_time'),
            'routes': Route.objects.all().order_by('name'),
            'current_date': date_filter,
            'current_route': route_filter,
        })
        return context

class ReturnedOrderCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        routes = Route.objects.all().order_by('name')
        delivery_orders = DeliveryOrder.objects.filter(
            status='completed'
        ).order_by('-delivery_date')

        return render(request, 'delivery/returned_order_form.html', {
            'routes': routes,
            'delivery_orders': delivery_orders,
        })

    def post(self, request):
        try:
            data = json.loads(request.body)

            returned_order = ReturnedOrder.objects.create(
                delivery_order_id=data['delivery_order_id'],
                route_id=data['route_id'],
                return_date=data['return_date'],
                return_time=data['return_time'],
                reason=data['reason'],
                notes=data.get('notes'),
                created_by=request.user,
                updated_by=request.user
            )

            for item in data['items']:
                ReturnedOrderItem.objects.create(
                    returned_order=returned_order,
                    product_id=item['product_id'],
                    quantity=item['quantity']
                )

            return JsonResponse({
                'status': 'success',
                'order_number': returned_order.order_number
            })

        except Exception as e:
            return HttpResponseBadRequest(str(e))

# API views for mobile app sync
class DeliveryOrderSyncView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)

            # Handle sync logic here
            # This would include creating/updating delivery orders
            # based on data from mobile app

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return HttpResponseBadRequest(str(e))




@require_http_methods(["GET"])
def get_route_sellers(request, route_id):
    sellers = Seller.objects.filter(route_id=route_id).values('id', 'store_name')
    return JsonResponse({'sellers': list(sellers)})


@require_http_methods(["GET"])
def get_seller_opening_balance(request, seller_id):
    """API endpoint to get the opening balance for a seller based on the last delivery order"""
    delivery_date = request.GET.get('date')

    print(f"\n\nGET_SELLER_OPENING_BALANCE CALLED: seller_id={seller_id}, date={delivery_date}\n\n")

    if not delivery_date:
        print("ERROR: Date parameter is missing")
        return JsonResponse({
            'status': 'error',
            'error': 'Date parameter is required'
        }, status=400)

    try:
        # Get last order's total balance for this seller
        last_order = DeliveryOrder.objects.filter(
            seller_id=seller_id,
            delivery_date__lt=delivery_date
        ).order_by('-delivery_date', '-delivery_time').first()

        # Handle the case where there's no previous order
        if last_order:
            opening_balance = last_order.total_balance
            print(f"SUCCESS: Found previous order #{last_order.pk} with balance: {opening_balance}")
        else:
            opening_balance = Decimal('0.00')
            print(f"INFO: No previous order found for seller {seller_id} before {delivery_date}, setting opening balance to 0")

        response_data = {
            'status': 'success',
            'opening_balance': float(opening_balance)
        }
        print(f"RESPONSE: {response_data}")
        return JsonResponse(response_data)
    except Exception as e:
        print(f"ERROR getting opening balance: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def check_existing_delivery_order(request):
    """Check if a delivery order already exists for the given route, seller, and date"""
    route_id = request.GET.get('route_id')
    seller_id = request.GET.get('seller_id')
    delivery_date = request.GET.get('delivery_date')

    if not all([route_id, seller_id, delivery_date]):
        return JsonResponse({
            'exists': False,
            'error': 'Missing required parameters'
        })

    try:
        # Check if a delivery order already exists
        existing_order = DeliveryOrder.objects.filter(
            route_id=route_id,
            seller_id=seller_id,
            delivery_date=delivery_date
        ).select_related('loading_order').first()

        if existing_order:
            # Get the order items
            items = existing_order.items.select_related('product').all()

            # Format the response
            return JsonResponse({
                'exists': True,
                'order': {
                    'id': existing_order.id,
                    'order_number': existing_order.order_number,
                    'route_id': existing_order.route_id,
                    'seller_id': existing_order.seller_id,
                    'loading_order_id': existing_order.loading_order_id,
                    'sales_order_id': existing_order.sales_order_id,
                    'delivery_date': existing_order.delivery_date.isoformat(),
                    'delivery_time': existing_order.delivery_time.isoformat(),
                    'payment_method': existing_order.payment_method,
                    'notes': existing_order.notes,
                    'total_price': float(existing_order.total_price),
                    'opening_balance': float(existing_order.opening_balance),
                    'amount_collected': float(existing_order.amount_collected),
                    'balance_amount': float(existing_order.balance_amount),
                    'total_balance': float(existing_order.total_balance),
                    'status': existing_order.status
                },
                'items': [
                    {
                        'product_id': str(item.product_id),
                        'product_name': f"{item.product.code} - {item.product.name}",
                        'ordered_quantity': float(item.ordered_quantity),
                        'delivered_quantity': float(item.delivered_quantity),
                        'unit_price': float(item.unit_price),
                        'total': float(item.total_price)
                    } for item in items
                ]
            })
        else:
            return JsonResponse({'exists': False})
    except Exception as e:
        return JsonResponse({
            'exists': False,
            'error': str(e)
        }, status=400)

@require_http_methods(["GET"])
def get_delivery_order(request, order_id):
    """Get delivery order data for editing"""
    try:
        delivery_order = DeliveryOrder.objects.get(pk=order_id)

        # Get order items
        items = [{
            'product_id': item.product_id,
            'product_name': f"{item.product.code} - {item.product.name}" if item.product else 'Unknown Product',
            'ordered_quantity': float(item.ordered_quantity),
            'delivered_quantity': float(item.delivered_quantity),
            'extra_quantity': float(item.extra_quantity) if hasattr(item, 'extra_quantity') else 0,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price)
        } for item in delivery_order.items.select_related('product').all()]

        return JsonResponse({
            'id': delivery_order.id,
            'order_number': delivery_order.order_number,
            'route_id': delivery_order.route_id,
            'seller_id': delivery_order.seller_id,
            'delivery_date': delivery_order.delivery_date.strftime('%Y-%m-%d'),
            'delivery_time': delivery_order.delivery_time.strftime('%H:%M') if delivery_order.delivery_time else '',
            'payment_method': delivery_order.payment_method,
            'notes': delivery_order.notes,
            'total_price': float(delivery_order.total_price),
            'opening_balance': float(delivery_order.opening_balance),
            'amount_collected': float(delivery_order.amount_collected),
            'balance_amount': float(delivery_order.balance_amount),
            'total_balance': float(delivery_order.total_balance),
            'status': delivery_order.status,
            'items': items
        })
    except DeliveryOrder.DoesNotExist:
        return JsonResponse({
            'error': f'Delivery order with ID {order_id} not found'
        }, status=404)
    except Exception as e:
        print(f"Error getting delivery order: {str(e)}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_seller_sales_items(request):
    print('seller: ', request.GET.get('seller'))
    seller = request.GET.get('seller')
    route = request.GET.get('route')
    delivery_date = request.GET.get('date')

    if not all([seller, route, delivery_date]):
        return JsonResponse({
            'success': False,
            'error': 'Missing required parameters'
        }, status=400)

    try:
        sales_order = SalesOrder.objects.filter(
            seller__id=seller,
            seller__route__id=route,
            delivery_date=delivery_date,
            status='draft'
        ).first()

        if not sales_order:
            return JsonResponse({'items': []})

        items = sales_order.items.select_related('product').values(
            'product_id',
            'product__name',
            'product__code',
            'quantity',
            'unit_price'
        )

        items_data = [{
            'product_id': str(item['product_id']),
            'product_name': f"{item['product__code']} - {item['product__name']}",
            'quantity': str(item['quantity']),
            'unit_price': str(item['unit_price'])
        } for item in items]

        return JsonResponse({
            'success': True,
            'items': items_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_available_products(request, route_id):
    print('route: ', route_id)
    delivery_date = request.GET.get('date')

    loading_order = LoadingOrder.objects.filter(
        route_id=route_id,
        loading_date=delivery_date
    ).first()

    # Even if there's no loading order, return an empty list without an error
    if not loading_order:
        print(f"No loading order found for route {route_id} and date {delivery_date}, returning empty list")
        return JsonResponse({
            'products': []
        })

    # Get loading order items with remaining quantity > 0
    try:
        products = loading_order.items.select_related('product').values(
            'product_id',
            'product__name',
            'product__code',
            'loaded_quantity',
            'delivered_quantity',
            'return_quantity',
            'remaining_quantity'
        )

        return JsonResponse({
            'products': [{
                'id': item['product_id'],
                'name': f"{item['product__code']} - {item['product__name']}",
                'loaded_quantity': str(item['loaded_quantity']),
                'delivered_quantity': str(item['delivered_quantity']),
                'return_quantity': str(item['return_quantity']),
                'available_quantity': str(item['remaining_quantity'])
            } for item in products]
        })
    except Exception as e:
        print(f"Error getting available products: {str(e)}")
        return JsonResponse({
            'products': [],
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_all_products(request):
    """API endpoint to fetch all active products"""
    from apps.products.models import Product, PricePlan, ProductPrice
    from django.db.models import F, Value, DecimalField

    try:
        # Get the general price plan
        general_price_plan = PricePlan.objects.filter(is_general=True, is_active=True).first()

        if general_price_plan:
            # Get products with prices from the general price plan
            products = Product.objects.filter(is_active=True).annotate(
                price=F('prices__price')
            ).filter(
                prices__price_plan=general_price_plan
            ).values(
                'id', 'name', 'code', 'category__name', 'price'
            ).order_by('category__name', 'name')
        else:
            # If no general price plan, use a default price of 0
            products = Product.objects.filter(is_active=True).annotate(
                price=Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            ).values(
                'id', 'name', 'code', 'category__name', 'price'
            ).order_by('category__name', 'name')

        print(f"Found {len(products)} active products")
        return JsonResponse({
            'products': [{
                'id': str(product['id']),
                'name': product['name'],
                'code': product['code'],
                'category': product['category__name'],
                'price': str(product['price']) if product['price'] is not None else '0.00'
            } for product in products]
        })
    except Exception as e:
        print(f"Error fetching products: {str(e)}")
        return JsonResponse({
            'products': [],
            'error': str(e)
        }, status=500)

    # This return statement is unreachable due to the try-except block above

@require_http_methods(["GET"])
def get_product_price(request, product_id):
    """API endpoint to fetch the price of a product"""
    from apps.products.models import Product, PricePlan, ProductPrice
    from django.db.models import F

    try:
        # Get the general price plan
        general_price_plan = PricePlan.objects.filter(is_general=True, is_active=True).first()

        if general_price_plan:
            # Get the price from the general price plan
            product_price = ProductPrice.objects.filter(
                product_id=product_id,
                price_plan=general_price_plan
            ).first()

            if product_price:
                return JsonResponse({
                    'success': True,
                    'price': str(product_price.price)
                })

        # If no price found, return 0
        return JsonResponse({
            'success': True,
            'price': '0.00'
        })

    except Exception as e:
        print(f"Error getting product price: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)