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
    ReturnedOrder,
    ReturnedOrderItem,
    DeliveryOrder,
    DeliveryOrderItem,
    LoadingOrder,
    LoadingOrderItem,
    BrokenOrder,
    BrokenOrderItem,
    Product,
    Route
)
from django.db.models import Sum, F


class ReturnOrderListView(LoginRequiredMixin, DeliveryTeamRequiredMixin, ListView):
    """View for listing all return orders"""
    model = ReturnedOrder
    template_name = 'delivery/return_orders/return_order_list.html'
    context_object_name = 'return_orders'

    def get_queryset(self):
        queryset = ReturnedOrder.objects.select_related(
            'delivery_order', 'created_by', 'updated_by'
        ).order_by('-return_date')

        # Apply filters if provided
        return_date = self.request.GET.get('return_date')
        status = self.request.GET.get('status')

        if return_date:
            queryset = queryset.filter(return_date=return_date)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = TemplateLayout.init(self, context)

        # Add filter options
        # context['statuses'] = dict(ReturnedOrder.STATUS_CHOICES)

        # Add current filter values
        context['current_filters'] = {
            'return_date': self.request.GET.get('return_date', ''),
            'status': self.request.GET.get('status', '')
        }

        return context


class ReturnOrderDetailView(LoginRequiredMixin, DeliveryTeamRequiredMixin, DetailView):
    """View for displaying return order details"""
    model = ReturnedOrder
    template_name = 'delivery/return_orders/return_order_detail.html'
    context_object_name = 'return_order'

    def get_queryset(self):
        return ReturnedOrder.objects.select_related(
            'delivery_order', 'created_by', 'updated_by'
        ).prefetch_related('items__product')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = TemplateLayout.init(self, context)

        # Add items to context
        context['items'] = self.object.items.select_related('product').all()

        return context


class ReturnOrderCreateView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for creating a new return order"""

    def get(self, request):
        # Get data for the form
        routes = Route.objects.all().order_by('name')

        context = TemplateLayout.init(self, {
            'routes': routes,
            'title': 'Create Return Order'
        })

        return render(request, 'delivery/return_orders/return_order_form.html', context)

    def post(self, request):
        try:
            # Get form data
            route_id = request.POST.get('route_id')
            return_date = request.POST.get('return_date')
            reason = request.POST.get('reason', '')
            print('route id: ', route_id)

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
            if not all([route_id, return_date]):
                missing = []
                if not route_id: missing.append('route')
                if not return_date: missing.append('return date')

                return JsonResponse({
                    'status': 'error',
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)

            # Find the most recent delivery order for this route
            delivery_order = DeliveryOrder.objects.filter(
                route_id=route_id,
                # status='delivered',
                delivery_date__lte=return_date
            ).order_by('-delivery_date').first()

            # Create return order
            return_order = ReturnedOrder.objects.create(
                delivery_order=delivery_order,  # This might be None if no delivery order is found
                route_id=route_id,
                return_date=return_date,
                # reason=reason,
                # status='pending',
                created_by=request.user,
                updated_by=request.user
            )

            # Log whether a delivery order was found
            if delivery_order:
                print(f"Created return order {return_order.order_number} with delivery order {delivery_order.order_number}")
            else:
                print(f"Created return order {return_order.order_number} without a delivery order for route {route_id}")

            # Calculate the maximum returnable quantity for each product
            max_returnable = calculate_max_returnable_quantity(route_id, return_date)

            # Validate and create return order items
            invalid_items = []
            print('items_data: ', items_data)
            for item in items_data:
                try:
                    product_id = int(item['product_id'])
                    quantity = Decimal(item['quantity'])
                    item_reason = item.get('reason', '')

                    # Validate the quantity against the maximum returnable quantity
                    if product_id in max_returnable and quantity > max_returnable[product_id]['max_returnable']:
                        product_name = max_returnable[product_id]['product'].name
                        max_qty = max_returnable[product_id]['max_returnable']
                        invalid_items.append({
                            'product_id': product_id,
                            'product_name': product_name,
                            'requested_quantity': float(quantity),
                            'max_returnable': float(max_qty),
                            'message': f"Requested quantity ({quantity}) exceeds maximum returnable quantity ({max_qty})"
                        })
                        continue

                    ReturnedOrderItem.objects.create(
                        returned_order=return_order,
                        product_id=product_id,
                        quantity=quantity,
                        # reason=item_reason
                    )
                except Exception as e:
                    print(f"Error creating return order item: {str(e)}")
                    # Continue with other items even if one fails

            # If there are invalid items, return an error
            if invalid_items:
                # Delete the return order since it's invalid
                return_order.delete()

                return JsonResponse({
                    'status': 'error',
                    'error': 'Some items exceed the maximum returnable quantity',
                    'invalid_items': invalid_items
                }, status=400)

            return JsonResponse({
                'status': 'success',
                'message': 'Return order created successfully',
                'redirect_url': reverse_lazy('delivery:return-order-detail', kwargs={'pk': return_order.pk})
            })

        except Exception as e:
            print(f"Error creating return order: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


class ReturnOrderUpdateView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for updating an existing return order"""

    def get(self, request, pk):
        # Get the return order
        return_order = get_object_or_404(
            ReturnedOrder.objects.select_related('delivery_order'),
            pk=pk
        )

        # Get data for the form
        routes = Route.objects.all().order_by('name')

        # Get the route from the delivery order if it exists
        selected_route_id = None
        if return_order.delivery_order and return_order.delivery_order.route:
            selected_route_id = return_order.delivery_order.route.id

        context = TemplateLayout.init(self, {
            'return_order': return_order,
            'routes': routes,
            'selected_route_id': selected_route_id,
            'items': return_order.items.select_related('product').all(),
            'title': f'Edit Return Order - {return_order.order_number}'
        })

        return render(request, 'delivery/return_orders/return_order_form.html', context)

    def post(self, request, pk):
        try:
            # Get the return order
            return_order = get_object_or_404(ReturnedOrder, pk=pk)

            # Get form data
            route_id = request.POST.get('route_id')
            return_date = request.POST.get('return_date')
            reason = request.POST.get('reason', '')

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
            if not all([route_id, return_date]):
                missing = []
                if not route_id: missing.append('route')
                if not return_date: missing.append('return date')

                return JsonResponse({
                    'status': 'error',
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)

            # Find the most recent delivery order for this route
            delivery_order = DeliveryOrder.objects.filter(
                route_id=route_id,
                status='delivered',
                delivery_date__lte=return_date
            ).order_by('-delivery_date').first()

            # Update return order
            return_order.delivery_order = delivery_order  # This might be None if no delivery order is found
            return_order.route_id = route_id
            return_order.return_date = return_date
            return_order.reason = reason
            return_order.updated_by = request.user
            return_order.save()

            # Log whether a delivery order was found
            if delivery_order:
                print(f"Updated return order {return_order.order_number} with delivery order {delivery_order.order_number}")
            else:
                print(f"Updated return order {return_order.order_number} without a delivery order for route {route_id}")

            # Calculate the maximum returnable quantity for each product
            max_returnable = calculate_max_returnable_quantity(route_id, return_date)

            # Validate and create return order items
            invalid_items = []

            # Delete existing items
            return_order.items.all().delete()

            # Create new items
            for item in items_data:
                try:
                    product_id = int(item['product_id'])
                    quantity = Decimal(item['quantity'])
                    item_reason = item.get('reason', '')

                    # Validate the quantity against the maximum returnable quantity
                    if product_id in max_returnable and quantity > max_returnable[product_id]['max_returnable']:
                        product_name = max_returnable[product_id]['product'].name
                        max_qty = max_returnable[product_id]['max_returnable']
                        invalid_items.append({
                            'product_id': product_id,
                            'product_name': product_name,
                            'requested_quantity': float(quantity),
                            'max_returnable': float(max_qty),
                            'message': f"Requested quantity ({quantity}) exceeds maximum returnable quantity ({max_qty})"
                        })
                        continue

                    ReturnedOrderItem.objects.create(
                        returned_order=return_order,
                        product_id=product_id,
                        quantity=quantity,
                        reason=item_reason
                    )
                except Exception as e:
                    print(f"Error updating return order item: {str(e)}")
                    # Continue with other items even if one fails

            # If there are invalid items, return an error
            if invalid_items:
                # Delete the items we just created since they're invalid
                return_order.items.all().delete()

                return JsonResponse({
                    'status': 'error',
                    'error': 'Some items exceed the maximum returnable quantity',
                    'invalid_items': invalid_items
                }, status=400)

            return JsonResponse({
                'status': 'success',
                'message': 'Return order updated successfully',
                'redirect_url': reverse_lazy('delivery:return-order-detail', kwargs={'pk': return_order.pk})
            })

        except Exception as e:
            print(f"Error updating return order: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


class ReturnOrderApproveView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for approving a return order"""

    def post(self, request, pk):
        try:
            # Get the return order
            return_order = get_object_or_404(ReturnedOrder, pk=pk)

            # Mark as approved
            return_order.status = 'approved'
            return_order.updated_by = request.user
            return_order.save()

            messages.success(request, 'Return order approved successfully')
            return redirect('delivery:return-order-detail', pk=pk)

        except Exception as e:
            messages.error(request, f'Error approving return order: {str(e)}')
            return redirect('delivery:return-order-detail', pk=pk)


class ReturnOrderRejectView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for rejecting a return order"""

    def post(self, request, pk):
        try:
            # Get the return order
            return_order = get_object_or_404(ReturnedOrder, pk=pk)

            # Mark as rejected
            return_order.status = 'rejected'
            return_order.updated_by = request.user
            return_order.save()

            messages.success(request, 'Return order rejected')
            return redirect('delivery:return-order-detail', pk=pk)

        except Exception as e:
            messages.error(request, f'Error rejecting return order: {str(e)}')
            return redirect('delivery:return-order-detail', pk=pk)


class ReturnOrderDeleteView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for deleting a return order"""

    def post(self, request, pk):
        try:
            # Get the return order
            return_order = get_object_or_404(ReturnedOrder, pk=pk)

            # Delete the return order
            return_order.delete()

            messages.success(request, 'Return order deleted successfully')
            return redirect('delivery:return-order-list')

        except Exception as e:
            messages.error(request, f'Error deleting return order: {str(e)}')
            return redirect('delivery:return-order-detail', pk=pk)


# Helper function to calculate maximum returnable quantity
def calculate_max_returnable_quantity(route_id, return_date):
    """Calculate the maximum returnable quantity for each product based on loading orders, delivery orders, and broken orders"""
    # Find the most recent loading order for this route and date
    loading_order = LoadingOrder.objects.filter(
        route_id=route_id,
        loading_date__lte=return_date,
        # status='completed'
    ).order_by('-loading_date').first()

    if not loading_order:
        print(f"No loading order found for route {route_id} and date {return_date}")
        return {}

    # Get all products and quantities from the loading order
    loading_items = LoadingOrderItem.objects.filter(loading_order=loading_order).select_related('product')
    print('loading items: ', loading_items)

    # Initialize a dictionary to store the maximum returnable quantity for each product
    max_returnable = {}

    for item in loading_items:
        max_returnable[item.product_id] = {
            'product': item.product,
            'loaded_quantity': item.loaded_quantity,
            'delivered_quantity': 0,
            'broken_quantity': 0,
            'max_returnable': item.loaded_quantity
        }

    # Get all delivery orders for this loading order
    delivery_orders = DeliveryOrder.objects.filter(loading_order=loading_order)

    # Calculate the total delivered quantity for each product
    for order in delivery_orders:
        delivery_items = DeliveryOrderItem.objects.filter(delivery_order=order)
        for item in delivery_items:
            if item.product_id in max_returnable:
                max_returnable[item.product_id]['delivered_quantity'] += item.delivered_quantity

    # Get all broken orders for this loading order
    broken_orders = BrokenOrder.objects.filter(loading_order=loading_order)

    # Calculate the total broken quantity for each product
    for order in broken_orders:
        broken_items = BrokenOrderItem.objects.filter(broken_order=order)
        for item in broken_items:
            if item.product_id in max_returnable:
                max_returnable[item.product_id]['broken_quantity'] += item.quantity

    # Calculate the maximum returnable quantity for each product
    for product_id, data in max_returnable.items():
        # Max returnable = Loaded - Delivered - Broken
        data['max_returnable'] = max(
            0,
            data['loaded_quantity'] - data['delivered_quantity'] - data['broken_quantity']
        )

        print(f"Product {data['product'].name}: Loaded={data['loaded_quantity']}, Delivered={data['delivered_quantity']}, Broken={data['broken_quantity']}, Max Returnable={data['max_returnable']}")

    return max_returnable


# API Views for Return Orders
def get_available_products_for_return(request):
    """API endpoint to get available products for return from a route"""
    route_id = request.GET.get('route_id')
    return_date = request.GET.get('return_date')
    print('route: ', route_id)
    print('return date: ', return_date)
    if not route_id:
        # If no route is specified, return all products
        try:
            products = Product.objects.all()
            product_list = [{
                'id': product.id,
                'code': product.code,
                'name': product.name,
                # 'price': float(product.price)
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
        # If we don't have both route_id and return_date, return all products
        if not route_id or not return_date:
            products = Product.objects.all()
            product_list = [{
                'id': product.id,
                'code': product.code,
                'name': product.name,
                # 'price': float(product.price)
            } for product in products]

            return JsonResponse({
                'status': 'success',
                'products': product_list
            })

        # Calculate the maximum returnable quantity for each product
        max_returnable = calculate_max_returnable_quantity(route_id, return_date)

        # Find the most recent delivery order for this route (for reference only)
        delivery_order = DeliveryOrder.objects.filter(
            route_id=route_id,
            # status='delivered',
            delivery_date__lte=return_date
        ).order_by('-delivery_date').first()

        # Format the response
        products = []
        for product_id, data in max_returnable.items():
            if data['max_returnable'] > 0:
                product = data['product']
                products.append({
                    'id': product.id,
                    'code': product.code,
                    'name': product.name,
                    'max_returnable': float(data['max_returnable']),
                    'loaded_quantity': float(data['loaded_quantity']),
                    'delivered_quantity': float(data['delivered_quantity']),
                    'broken_quantity': float(data['broken_quantity']),
                    # 'price': float(product.price)
                })

        # If no products with returnable quantity, return all products
        if not products:
            print("No products with returnable quantity found, returning all products")
            products = Product.objects.all()
            product_list = [{
                'id': product.id,
                'code': product.code,
                'name': product.name,
                # 'price': float(product.price)
            } for product in products]

            return JsonResponse({
                'status': 'success',
                'products': product_list,
                'message': 'No products with returnable quantity found for this route and date'
            })

        response_data = {
            'status': 'success',
            'products': products
        }

        # Add delivery order info if available
        if delivery_order:
            response_data['delivery_order'] = {
                'id': delivery_order.id,
                'order_number': delivery_order.order_number,
                'delivery_date': delivery_order.delivery_date.strftime('%Y-%m-%d')
            }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
