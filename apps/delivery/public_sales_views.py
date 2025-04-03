from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
import json
from decimal import Decimal

from web_project import TemplateLayout
from web_project.mixins import DeliveryTeamRequiredMixin
from .models import (
    PublicSale,
    PublicSaleItem,
    DeliveryTeam,
    LoadingOrder,
    Route
)
from apps.products.models import Product


class PublicSaleListView(LoginRequiredMixin, DeliveryTeamRequiredMixin, ListView):
    """View for listing all public sales"""
    model = PublicSale
    template_name = 'delivery/public_sales/public_sale_list.html'
    context_object_name = 'public_sales'

    def get_queryset(self):
        queryset = PublicSale.objects.select_related(
            'route', 'delivery_team', 'loading_order', 'created_by', 'updated_by'
        ).order_by('-sale_date', '-sale_time')

        # Apply filters if provided
        sale_date = self.request.GET.get('sale_date')
        route_id = self.request.GET.get('route')
        status = self.request.GET.get('status')

        if sale_date:
            queryset = queryset.filter(sale_date=sale_date)

        if route_id:
            queryset = queryset.filter(route_id=route_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = TemplateLayout.init(self, context)

        # Add filter options
        context['routes'] = Route.objects.all()
        context['statuses'] = dict(PublicSale.STATUS_CHOICES)

        # Add current filter values
        context['current_filters'] = {
            'sale_date': self.request.GET.get('sale_date', ''),
            'route': self.request.GET.get('route', ''),
            'status': self.request.GET.get('status', '')
        }

        return context


class PublicSaleDetailView(LoginRequiredMixin, DeliveryTeamRequiredMixin, DetailView):
    """View for displaying public sale details"""
    model = PublicSale
    template_name = 'delivery/public_sales/public_sale_detail.html'
    context_object_name = 'public_sale'

    def get_queryset(self):
        return PublicSale.objects.select_related(
            'route', 'delivery_team', 'loading_order', 'created_by', 'updated_by'
        ).prefetch_related('items__product')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = TemplateLayout.init(self, context)

        # Add items to context
        context['items'] = self.object.items.select_related('product').all()

        return context


class PublicSaleCreateView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for creating a new public sale"""

    def get(self, request):
        # Get data for the form
        routes = Route.objects.all().order_by('name')
        delivery_teams = DeliveryTeam.objects.filter(is_active=True).order_by('name')
        loading_orders = LoadingOrder.objects.filter(status='completed').order_by('-loading_date')

        context = TemplateLayout.init(self, {
            'routes': routes,
            'delivery_teams': delivery_teams,
            'loading_orders': loading_orders,
            'payment_methods': dict(PublicSale.PAYMENT_METHOD_CHOICES),
            'title': 'Create Public Sale'
        })

        return render(request, 'delivery/public_sales/public_sale_form.html', context)

    def post(self, request):
        try:
            # Get form data
            route_id = request.POST.get('route_id')
            delivery_team_id = request.POST.get('delivery_team_id')
            loading_order_id = request.POST.get('loading_order_id')
            customer_name = request.POST.get('customer_name', '')
            customer_phone = request.POST.get('customer_phone', '')
            customer_address = request.POST.get('customer_address', '')
            sale_date = request.POST.get('sale_date')
            sale_time = request.POST.get('sale_time')
            payment_method = request.POST.get('payment_method')
            notes = request.POST.get('notes', '')
            amount_collected = request.POST.get('amount_collected', '0')

            # Get items data
            items_data_str = request.POST.get('items_data')

            if not items_data_str:
                return JsonResponse({
                    'status': 'error',
                    'error': 'No items data provided'
                }, status=400)

            try:
                items_data = json.loads(items_data_str)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error',
                    'error': f'Invalid items data format: {str(e)}'
                }, status=400)

            # Validate required fields
            if not all([route_id, sale_date, sale_time]):
                missing = []
                if not route_id: missing.append('route')
                if not sale_date: missing.append('sale date')
                if not sale_time: missing.append('sale time')

                return JsonResponse({
                    'status': 'error',
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)

            # Calculate total price
            total_price = Decimal('0.00')
            for item in items_data:
                quantity = Decimal(item['quantity'])
                unit_price = Decimal(item['unit_price'])
                total_price += quantity * unit_price

            # Convert amount_collected to Decimal
            amount_collected_decimal = Decimal(amount_collected)

            # Calculate balance amount
            balance_amount = total_price - amount_collected_decimal

            # Create public sale
            # If delivery_team_id is not provided, try to get it from the loading order or route
            if not delivery_team_id and loading_order_id:
                try:
                    loading_order = LoadingOrder.objects.get(pk=loading_order_id)
                    delivery_team_id = loading_order.delivery_team_id
                    print(f"Using delivery team {delivery_team_id} from loading order {loading_order_id}")
                except LoadingOrder.DoesNotExist:
                    print(f"Loading order {loading_order_id} not found")

            # If still no delivery_team_id, try to get the first team for this route
            if not delivery_team_id:
                try:
                    delivery_team = DeliveryTeam.objects.filter(route_id=route_id, is_active=True).first()
                    if delivery_team:
                        delivery_team_id = delivery_team.id
                        print(f"Using first delivery team {delivery_team_id} for route {route_id}")
                except Exception as e:
                    print(f"Error getting delivery team for route {route_id}: {str(e)}")

            # Create the public sale
            public_sale = PublicSale.objects.create(
                route_id=route_id,
                delivery_team_id=delivery_team_id,  # This might be None, which is now allowed
                loading_order_id=loading_order_id if loading_order_id else None,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_address=customer_address,
                sale_date=sale_date,
                sale_time=sale_time,
                payment_method=payment_method,
                notes=notes,
                total_price=total_price,
                amount_collected=amount_collected_decimal,
                balance_amount=balance_amount,
                status='pending',
                created_by=request.user,
                updated_by=request.user
            )

            # Create public sale items
            for item in items_data:
                try:
                    product_id = int(item['product_id'])
                    quantity = Decimal(item['quantity'])
                    unit_price = Decimal(item['unit_price'])
                    total_price = quantity * unit_price

                    PublicSaleItem.objects.create(
                        public_sale=public_sale,
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                except Exception as e:
                    print(f"Error creating public sale item: {str(e)}")
                    # Continue with other items even if one fails

            return JsonResponse({
                'status': 'success',
                'message': 'Public sale created successfully',
                'redirect_url': reverse_lazy('delivery:public-sale-detail', kwargs={'pk': public_sale.pk})
            })

        except Exception as e:
            print(f"Error creating public sale: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


class PublicSaleUpdateView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for updating an existing public sale"""

    def get(self, request, pk):
        # Get the public sale
        public_sale = get_object_or_404(
            PublicSale.objects.select_related('route', 'delivery_team', 'loading_order'),
            pk=pk
        )

        # Get data for the form
        routes = Route.objects.all().order_by('name')
        delivery_teams = DeliveryTeam.objects.filter(is_active=True).order_by('name')
        loading_orders = LoadingOrder.objects.filter(status='completed').order_by('-loading_date')

        context = TemplateLayout.init(self, {
            'public_sale': public_sale,
            'routes': routes,
            'delivery_teams': delivery_teams,
            'loading_orders': loading_orders,
            'payment_methods': dict(PublicSale.PAYMENT_METHOD_CHOICES),
            'items': public_sale.items.select_related('product').all(),
            'title': f'Edit Public Sale - {public_sale.sale_number}'
        })

        return render(request, 'delivery/public_sales/public_sale_form.html', context)

    def post(self, request, pk):
        try:
            # Get the public sale
            public_sale = get_object_or_404(PublicSale, pk=pk)

            # Get form data
            route_id = request.POST.get('route_id')
            delivery_team_id = request.POST.get('delivery_team_id')
            loading_order_id = request.POST.get('loading_order_id')
            customer_name = request.POST.get('customer_name', '')
            customer_phone = request.POST.get('customer_phone', '')
            customer_address = request.POST.get('customer_address', '')
            sale_date = request.POST.get('sale_date')
            sale_time = request.POST.get('sale_time')
            payment_method = request.POST.get('payment_method')
            notes = request.POST.get('notes', '')
            amount_collected = request.POST.get('amount_collected', '0')

            # Get items data
            items_data_str = request.POST.get('items_data')

            if not items_data_str:
                return JsonResponse({
                    'status': 'error',
                    'error': 'No items data provided'
                }, status=400)

            try:
                items_data = json.loads(items_data_str)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error',
                    'error': f'Invalid items data format: {str(e)}'
                }, status=400)

            # Validate required fields
            if not all([route_id, delivery_team_id, sale_date, sale_time]):
                missing = []
                if not route_id: missing.append('route')
                if not delivery_team_id: missing.append('delivery team')
                if not sale_date: missing.append('sale date')
                if not sale_time: missing.append('sale time')

                return JsonResponse({
                    'status': 'error',
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)

            # Calculate total price
            total_price = Decimal('0.00')
            for item in items_data:
                quantity = Decimal(item['quantity'])
                unit_price = Decimal(item['unit_price'])
                total_price += quantity * unit_price

            # Convert amount_collected to Decimal
            amount_collected_decimal = Decimal(amount_collected)

            # Calculate balance amount
            balance_amount = total_price - amount_collected_decimal

            # Update public sale
            public_sale.route_id = route_id
            public_sale.delivery_team_id = delivery_team_id
            public_sale.loading_order_id = loading_order_id if loading_order_id else None
            public_sale.customer_name = customer_name
            public_sale.customer_phone = customer_phone
            public_sale.customer_address = customer_address
            public_sale.sale_date = sale_date
            public_sale.sale_time = sale_time
            public_sale.payment_method = payment_method
            public_sale.notes = notes
            public_sale.total_price = total_price
            public_sale.amount_collected = amount_collected_decimal
            public_sale.balance_amount = balance_amount
            public_sale.updated_by = request.user
            public_sale.save()

            # Delete existing items
            public_sale.items.all().delete()

            # Create new items
            for item in items_data:
                try:
                    product_id = int(item['product_id'])
                    quantity = Decimal(item['quantity'])
                    unit_price = Decimal(item['unit_price'])
                    total_price = quantity * unit_price

                    PublicSaleItem.objects.create(
                        public_sale=public_sale,
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                except Exception as e:
                    print(f"Error updating public sale item: {str(e)}")
                    # Continue with other items even if one fails

            return JsonResponse({
                'status': 'success',
                'message': 'Public sale updated successfully',
                'redirect_url': reverse_lazy('delivery:public-sale-detail', kwargs={'pk': public_sale.pk})
            })

        except Exception as e:
            print(f"Error updating public sale: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


class PublicSaleDeleteView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for deleting a public sale"""

    def post(self, request, pk):
        try:
            # Get the public sale
            public_sale = get_object_or_404(PublicSale, pk=pk)

            # Delete the public sale
            public_sale.delete()

            messages.success(request, 'Public sale deleted successfully')
            return redirect('delivery:public-sale-list')

        except Exception as e:
            messages.error(request, f'Error deleting public sale: {str(e)}')
            return redirect('delivery:public-sale-detail', pk=pk)


class PublicSaleCompleteView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for marking a public sale as completed"""

    def post(self, request, pk):
        try:
            # Get the public sale
            public_sale = get_object_or_404(PublicSale, pk=pk)

            # Mark as completed
            public_sale.status = 'completed'
            public_sale.updated_by = request.user
            public_sale.save()

            messages.success(request, 'Public sale marked as completed')
            return redirect('delivery:public-sale-detail', pk=pk)

        except Exception as e:
            messages.error(request, f'Error completing public sale: {str(e)}')
            return redirect('delivery:public-sale-detail', pk=pk)


class PublicSaleCancelView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for cancelling a public sale"""

    def post(self, request, pk):
        try:
            # Get the public sale
            public_sale = get_object_or_404(PublicSale, pk=pk)

            # Mark as cancelled
            public_sale.status = 'cancelled'
            public_sale.updated_by = request.user
            public_sale.save()

            messages.success(request, 'Public sale cancelled successfully')
            return redirect('delivery:public-sale-detail', pk=pk)

        except Exception as e:
            messages.error(request, f'Error cancelling public sale: {str(e)}')
            return redirect('delivery:public-sale-detail', pk=pk)


# API Views for Public Sales
def get_available_products_for_public_sale(request):
    """API endpoint to get available products for public sale from a loading order"""
    loading_order_id = request.GET.get('loading_order_id')

    # If no loading order ID is provided, return all products
    if not loading_order_id:
        try:
            products = Product.objects.all()
            product_list = [{
                'id': product.id,
                'code': product.code,
                'name': product.name,
                'available_quantity': 999,  # No limit if no loading order
                'price': float(product.price)
            } for product in products]

            return JsonResponse({
                'status': 'success',
                'products': product_list
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)

    try:
        # Get the loading order
        loading_order = get_object_or_404(LoadingOrder, pk=loading_order_id)

        # Get the loading order items
        loading_order_items = loading_order.items.select_related('product').all()

        # Format the response
        products = []
        for item in loading_order_items:
            # Calculate available quantity (considering already sold items)
            available_quantity = item.quantity

            # Subtract quantities from delivery orders
            delivery_orders = loading_order.delivery_orders.all()
            for order in delivery_orders:
                order_items = order.items.filter(product=item.product)
                for order_item in order_items:
                    available_quantity -= order_item.delivered_quantity

            # Subtract quantities from public sales
            public_sales = loading_order.public_sales.all()
            for sale in public_sales:
                sale_items = sale.items.filter(product=item.product)
                for sale_item in sale_items:
                    available_quantity -= sale_item.quantity

            # Only include products with available quantity
            if available_quantity > 0:
                products.append({
                    'id': item.product.id,
                    'code': item.product.code,
                    'name': item.product.name,
                    'available_quantity': float(available_quantity),
                    'price': float(item.product.price)
                })

        return JsonResponse({
            'status': 'success',
            'products': products
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
