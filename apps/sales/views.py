from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, View
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import transaction
from web_project import TemplateLayout
from .models import SalesOrder, OrderItem, SellerCallLog, Product
from apps.seller.models import Route, Seller
from apps.products.models import ProductPrice
import json
from decimal import Decimal
import logging
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)

class SalesTeamRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # Allow both admin users and sales team users
        return self.request.user.is_superuser or self.request.user.role == 'SALES'

class SalesDashboardView(LoginRequiredMixin, SalesTeamRequiredMixin, TemplateView):
    template_name = "sales/dashboard.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        today = timezone.now().date()

        # Make sure menu is enabled
        context.update({
            'is_menu': True,  # Add this line to ensure menu is shown
            'today_calls': SellerCallLog.objects.filter(
                call_date=today
            ).count(),
            'pending_calls': SellerCallLog.objects.filter(
                call_date=today,
                status='scheduled'
            ).count(),
            'today_orders': SalesOrder.objects.filter(
                created_at__date=today
            ).count(),
            'routes_count': Route.objects.count(),
            'sellers_count': Seller.objects.count(),
            
            # Recent call logs
            'recent_calls': SellerCallLog.objects.select_related('seller').order_by(
                '-call_date', '-created_at'
            )[:5],
            
            # Recent orders
            'recent_orders': SalesOrder.objects.select_related('seller').order_by(
                '-created_at'
            )[:5],
        })
        return context

class CallLogListView(LoginRequiredMixin, SalesTeamRequiredMixin, TemplateView):
    template_name = "sales/call_log_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['call_logs'] = SellerCallLog.objects.select_related(
            'seller', 
            'seller__route'
        ).order_by('-call_date', '-created_at')
        context['routes'] = Route.objects.all().order_by('name')
        return context

class CallLogCreateView(LoginRequiredMixin, SalesTeamRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        try:
            routes = Route.objects.all().order_by('name')
            context = {
                'routes': routes,
                'call_statuses': SellerCallLog.CALL_STATUS,
            }
            return render(request, 'sales/call_log_form.html', context)
        except Exception as e:
            return HttpResponseBadRequest(str(e))
    
    def post(self, request):
        try:
            seller_id = request.POST.get('seller')
            call_date = request.POST.get('call_date')
            notes = request.POST.get('notes')
            status = request.POST.get('status')
            next_call_date = request.POST.get('next_call_date')
            
            if not all([seller_id, call_date, status]):
                return HttpResponseBadRequest('All fields are required')
            
            SellerCallLog.objects.create(
                seller_id=seller_id,
                call_date=call_date,
                notes=notes,
                status=status,
                next_call_date=next_call_date if next_call_date else None,
                created_by=request.user
            )
            
            response = render(
                request,
                'sales/partials/call_log_table.html',
                {'call_logs': SellerCallLog.objects.select_related('seller').order_by('-call_date', '-created_at')}
            )
            
            response['HX-Trigger'] = 'closeModal'
            return response
            
        except Exception as e:
            return HttpResponseBadRequest(str(e))

class CallLogEditFormView(LoginRequiredMixin, SalesTeamRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, call_log_id):
        call_log = SellerCallLog.objects.get(id=call_log_id)
        sellers = Seller.objects.all().order_by('first_name')
        return render(request, 'sales/call_log_edit_form.html', {
            'call_log': call_log,
            'sellers': sellers
        })

class CallLogEditView(LoginRequiredMixin, SalesTeamRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def put(self, request, call_log_id):
        try:
            call_log = SellerCallLog.objects.get(id=call_log_id)
            
            data = parse_qs(request.body.decode('utf-8'))
            data = {k: v[0] for k, v in data.items()}
            
            if not all([data.get('seller'), data.get('call_date'), data.get('status')]):
                return HttpResponseBadRequest('Seller, call date and status are required')
            
            call_log.seller_id = data['seller']
            call_log.call_date = data['call_date']
            call_log.status = data['status']
            call_log.next_call_date = data.get('next_call_date') or None
            call_log.notes = data.get('notes', '')
            call_log.updated_by = request.user
            call_log.save()
            
            response = render(
                request,
                'sales/partials/call_log_table.html',
                {'call_logs': SellerCallLog.objects.select_related('seller', 'seller__route').order_by('-call_date', '-created_at')}
            )
            
            response['HX-Trigger'] = 'closeModal'
            return response
            
        except SellerCallLog.DoesNotExist:
            return HttpResponseBadRequest('Call log not found')
        except Exception as e:
            return HttpResponseBadRequest(str(e))

class GetSellersByRouteView(LoginRequiredMixin, View):
    def get(self, request):
        route_id = request.GET.get('route')
        if not route_id:
            return HttpResponseBadRequest('Route ID is required')
            
        sellers = Seller.objects.filter(route_id=route_id).order_by('store_name')
        return render(request, 'sales/partials/seller_select.html', {'sellers': sellers})

class SalesOrderListView(LoginRequiredMixin, SalesTeamRequiredMixin, TemplateView):
    template_name = "sales/sales_order_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Get filter parameters
        route_id = self.request.GET.get('route')
        status = self.request.GET.get('status')
        delivery_date = self.request.GET.get('delivery_date')

        # Base queryset with necessary related fields
        orders = SalesOrder.objects.select_related(
            'seller',
            'seller__route'
        ).order_by('-delivery_date', '-created_at')

        # Apply filters
        if route_id:
            orders = orders.filter(seller__route_id=route_id)
        if status:
            orders = orders.filter(status=status)
        if delivery_date:
            orders = orders.filter(delivery_date=delivery_date)

        # Pagination
        page_number = self.request.GET.get('page', 1)
        paginator = Paginator(orders, 5)  # Show 10 orders per page
        page_obj = paginator.get_page(page_number)

        context.update({
            'orders': page_obj,
            'routes': Route.objects.all().order_by('name'),
            'status_choices': SalesOrder.ORDER_STATUS,
            # Add filter values to context for maintaining state
            'selected_route': route_id,
            'selected_status': status,
            'selected_date': delivery_date,
        })
        
        return context

def check_existing_order(request):
    order_id = request.GET.get('order_id')
    seller_id = request.GET.get('seller_id')
    delivery_date = request.GET.get('delivery_date')
    
    try:
        if order_id:
            # Load specific order for editing
            order = get_object_or_404(
                SalesOrder.objects.select_related(
                    'seller',
                    'seller__route'
                ).prefetch_related(
                    'items__product'
                ),
                id=order_id
            )
            
            items_data = [{
                'product_id': str(item.product_id),
                'product_name': f"{item.product.code} - {item.product.name}",
                'quantity': str(item.quantity),
                'unit_price': str(item.unit_price),
                'total': str(item.quantity * item.unit_price)
            } for item in order.items.all()]
            
            return JsonResponse({
                'order_id': order.id,
                'route_id': order.seller.route_id,
                'seller_id': order.seller.id,
                'seller_name': str(order.seller),
                'delivery_date': order.delivery_date.strftime('%Y-%m-%d'),
                'status': order.status,
                'items': items_data,
                'is_edit': True
            })
        else:
            # Check for existing order by seller and date
            existing_order = SalesOrder.objects.filter(
                seller_id=seller_id,
                delivery_date=delivery_date
            ).select_related('seller').prefetch_related(
                'items__product'
            ).first()
            
            if existing_order:
                items_data = [{
                    'product_id': str(item.product_id),
                    'product_name': f"{item.product.code} - {item.product.name}",
                    'quantity': str(item.quantity),
                    'unit_price': str(item.unit_price),
                    'total': str(item.quantity * item.unit_price)
                } for item in existing_order.items.all()]
                
                return JsonResponse({
                    'order_id': existing_order.id,
                    'status': existing_order.status,
                    'items': items_data,
                    'is_edit': True
                })
            
            return JsonResponse({'order_id': '', 'items': [], 'is_edit': False})
            
    except Exception as e:
        logger.error(f"Error checking existing order: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

class SalesOrderCreateView(LoginRequiredMixin, SalesTeamRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        try:
            routes = Route.objects.all().order_by('name')
            products = Product.objects.filter(is_active=True).order_by('name')
            
            context = {
                'routes': routes,
                'products': products,
                'status_choices': SalesOrder.ORDER_STATUS,
            }
            
            return render(request, 'sales/sales_order_form.html', context)
            
        except Exception as e:
            logger.error(f"Error in SalesOrderCreateView.get: {str(e)}")
            return HttpResponseBadRequest(str(e))

    @transaction.atomic
    def post(self, request):
        try:
            seller_id = request.POST.get('seller')
            delivery_date = request.POST.get('delivery_date')
            status = request.POST.get('status', 'draft')
            
            if not all([seller_id, delivery_date]):
                return HttpResponseBadRequest('Seller and delivery date are required')

            # Create order
            order = SalesOrder.objects.create(
                seller_id=seller_id,
                delivery_date=delivery_date,
                status=status,
                created_by=request.user,
                updated_by=request.user
            )

            # Process order items
            items_data = json.loads(request.POST.get('items', '[]'))
            for item in items_data:
                product_id = item.get('product_id')
                quantity = Decimal(str(item.get('quantity', '0')))
                unit_price = Decimal(str(item.get('unit_price', '0')))
                
                if product_id and quantity > 0:
                    OrderItem.objects.create(
                        order=order,
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=unit_price
                    )

            response = render(
                request,
                'sales/partials/sales_order_table.html',
                {'orders': SalesOrder.objects.select_related(
                    'seller',
                    'seller__route'
                ).order_by('-delivery_date', '-created_at')}
            )
            
            response['HX-Trigger'] = 'closeModal'
            return response

        except Exception as e:
            logger.error(f"Error in SalesOrderCreateView.post: {str(e)}")
            return HttpResponseBadRequest(str(e))

class SalesOrderViewView(LoginRequiredMixin, SalesTeamRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, order_id):
        try:
            order = get_object_or_404(
                SalesOrder.objects.select_related(
                    'seller',
                    'seller__route'
                ).prefetch_related(
                    'items__product'
                ),
                id=order_id
            )
            
            context = TemplateLayout.init(self, {
                'order': order,
                'title': f'Order Details - {order.order_number}'
            })
            
            return render(request, 'sales/order_view.html', context)
            
        except Exception as e:
            logger.error(f"Error in SalesOrderViewView.get: {str(e)}")
            return HttpResponseBadRequest(str(e))

class SalesOrderEditView(LoginRequiredMixin, SalesTeamRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, order_id):
        try:
            order = get_object_or_404(
                SalesOrder.objects.select_related(
                    'seller',
                    'seller__route'
                ).prefetch_related(
                    'items__product'
                ),
                id=order_id
            )
            
            if order.status != 'draft':
                return HttpResponseBadRequest('Only draft orders can be edited')
            
            routes = Route.objects.all().order_by('name')
            products = Product.objects.filter(is_active=True).order_by('name')
            
            context = {
                'order': order,
                'routes': routes,
                'products': products,
                'status_choices': SalesOrder.ORDER_STATUS,
            }
            return render(request, 'sales/sales_order_edit_form.html', context)
            
        except Exception as e:
            logger.error(f"Error in SalesOrderEditView.get: {str(e)}")
            return HttpResponseBadRequest(str(e))

    @transaction.atomic
    def put(self, request, order_id):
        try:
            order = get_object_or_404(SalesOrder, id=order_id)
            
            if order.status != 'draft':
                return HttpResponseBadRequest('Only draft orders can be edited')
            
            # Parse the PUT data
            data = json.loads(request.body)
            
            # Update basic order information
            order.seller_id = data.get('seller_id', order.seller_id)
            order.delivery_date = data.get('delivery_date', order.delivery_date)
            order.status = data.get('status', order.status)
            order.updated_by = request.user
            order.save()

            # Update order items
            order.items.all().delete()  # Remove existing items
            
            items_data = data.get('items', [])
            for item in items_data:
                product_id = item.get('product_id')
                quantity = Decimal(item.get('quantity', 0))
                unit_price = Decimal(item.get('unit_price', 0))
                
                if product_id and quantity > 0:
                    OrderItem.objects.create(
                        order=order,
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=unit_price
                    )

            # Render updated table
            response = render(
                request,
                'sales/partials/sales_order_table.html',
                {'orders': SalesOrder.objects.select_related(
                    'seller',
                    'seller__route'
                ).order_by('-delivery_date', '-created_at')}
            )
            
            response['HX-Trigger'] = 'closeModal'
            return response

        except Exception as e:
            logger.error(f"Error in SalesOrderEditView.put: {str(e)}")
            return HttpResponseBadRequest(str(e))

class SalesOrderUpdateView(View):
    def put(self, request, order_id):
        try:
            order = get_object_or_404(SalesOrder, id=order_id)
            
            # Parse the JSON data
            data = json.loads(request.body)
            
            # Update order fields
            order.seller_id = data.get('seller_id', order.seller_id)
            order.delivery_date = data.get('delivery_date', order.delivery_date)
            # Set default status if not provided
            order.status = data.get('status') or order.status or 'draft'
            order.updated_by = request.user
            order.save()

            # Update order items
            order.items.all().delete()  # Remove existing items
            
            items_data = data.get('items', [])
            for item in items_data:
                OrderItem.objects.create(
                    order=order,
                    product_id=item['product_id'],
                    quantity=Decimal(str(item['quantity'])),
                    unit_price=Decimal(str(item['unit_price']))
                )

            response = render(
                request,
                'sales/partials/sales_order_table.html',
                {'orders': SalesOrder.objects.select_related(
                    'seller',
                    'seller__route'
                ).order_by('-delivery_date', '-created_at')}
            )
            
            response['HX-Trigger'] = 'closeModal'
            return response

        except Exception as e:
            logger.error(f"Error updating order: {str(e)}")
            return HttpResponseBadRequest(str(e))

class GetProductPriceView(LoginRequiredMixin, SalesTeamRequiredMixin, View):
    def get(self, request):
        try:
            product_id = request.GET.get('product_id')
            if not product_id:
                return JsonResponse({'error': 'Product ID is required'}, status=400)
            
            today = timezone.now().date()
            
            # Get the price from the active general price plan
            price = ProductPrice.objects.filter(
                product_id=product_id,
                price_plan__is_general=True,
                price_plan__is_active=True,
                price_plan__valid_from__lte=today,
                price_plan__valid_to__gte=today
            ).order_by('-price_plan__created_at').first()
            
            return JsonResponse({
                'price': float(price.price) if price else 10.00
            })
                
        except Exception as e:
            logger.error(f"Error in GetProductPriceView: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)

class GetAvailableProductsView(LoginRequiredMixin, View):
    def get(self, request):
        products = Product.objects.filter(is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(products), safe=False)

# def order_create(request):
#     if request.method == 'GET':
#         # Return the form template
#         return render(request, 'sales/sales_order_form.html', {
#             'routes': Route.objects.all(),
#             'products': Product.objects.all(),
#             'status_choices': OrderStatus.choices,
#         })
#     elif request.method == 'POST':
#         # Handle form submission
#         # ... your existing code ...
#         response = HttpResponse()
#         response['HX-Trigger'] = 'closeModal'
#         return response
