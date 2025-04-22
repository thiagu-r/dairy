from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import transaction

from apps.delivery.models import (
    DeliveryOrder,
    DeliveryOrderItem,
    BrokenOrder,
    BrokenOrderItem,
    ReturnedOrder,
    ReturnedOrderItem,
    PublicSale,
    PublicSaleItem,
    DeliveryExpense,
    CashDenomination,
    LoadingOrder
)
from apps.seller.models import Route, Seller
from apps.products.models import Product

from .serializers import (
    DeliveryOrderSerializer,
    BrokenOrderSerializer,
    ReturnedOrderSerializer,
    PublicSaleSerializer,
    DeliveryExpenseSerializer,
    CashDenominationSerializer
)

import json
from datetime import datetime


class BaseSyncView(APIView):
    """Base class for all sync views with common functionality"""
    permission_classes = [IsAuthenticated]

    def fix_time_format(self, time_str):
        """Convert various time formats to HH:MM:SS format."""
        if not time_str:
            return '00:00:00'

        try:
            # If it's a datetime string with space (e.g., '2025-04-20 15:57:11')
            if isinstance(time_str, str) and ' ' in time_str:
                time_part = time_str.split(' ')[1]
                return time_part

            # If it's already in the correct format
            if isinstance(time_str, str) and len(time_str.split(':')) == 3:
                return time_str

            # Try to parse as datetime
            dt = datetime.strptime(str(time_str), '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%H:%M:%S')
        except (ValueError, TypeError):
            try:
                # Try to parse as time
                dt = datetime.strptime(str(time_str), '%H:%M:%S')
                return dt.strftime('%H:%M:%S')
            except (ValueError, TypeError):
                # If all else fails, return a default time
                return '00:00:00'

    def extract_data(self, request):
        """Extract data from request, handling nested data structure if present."""
        if 'data' in request.data:
            return request.data['data']
        return request.data


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryOrderSyncView(BaseSyncView):
    """API endpoint for syncing delivery orders only"""

    @transaction.atomic
    def post(self, request):
        try:
            user = request.user
            data = self.extract_data(request)
            
            if not isinstance(data, list):
                # If data is not a list, wrap it in a list
                data = [data]
            
            print(f"Processing {len(data)} delivery orders")
            
            results = []
            for order_data in data:
                # Fix time formats
                if 'delivery_time' in order_data and order_data['delivery_time']:
                    order_data['delivery_time'] = self.fix_time_format(order_data['delivery_time'])
                
                if 'actual_delivery_time' in order_data and order_data['actual_delivery_time']:
                    order_data['actual_delivery_time'] = self.fix_time_format(order_data['actual_delivery_time'])
                
                # Fix status
                if 'status' in order_data and order_data['status'] == 'draft':
                    order_data['status'] = 'pending'
                
                # Fix payment method - ensure it's one of the valid choices
                if 'payment_method' in order_data:
                    valid_payment_methods = ['cash', 'online']
                    if order_data['payment_method'] not in valid_payment_methods:
                        print(f"Invalid payment_method: {order_data['payment_method']}, setting to 'cash'")
                        order_data['payment_method'] = 'cash'
                
                # Try to find existing order
                existing_order = None
                
                # First, check if we have an ID in the order data
                if 'id' in order_data and order_data['id']:
                    try:
                        existing_order = DeliveryOrder.objects.get(id=order_data['id'])
                        print(f"Found existing delivery order by ID: {existing_order.id}")
                    except DeliveryOrder.DoesNotExist:
                        print(f"No existing order found with ID: {order_data['id']}")
                
                # If not found by ID, try to find by local_id
                if not existing_order and 'local_id' in order_data and order_data['local_id']:
                    existing_order = DeliveryOrder.objects.filter(local_id=order_data['local_id']).first()
                    if existing_order:
                        print(f"Found existing delivery order by local_id: {existing_order.id}")
                
                # If not found by local_id, try to find by unique constraint fields
                if not existing_order and 'route' in order_data and 'seller' in order_data and 'delivery_date' in order_data:
                    try:
                        existing_order = DeliveryOrder.objects.filter(
                            route_id=order_data['route'],
                            seller_id=order_data['seller'],
                            delivery_date=order_data['delivery_date']
                        ).first()
                        if existing_order:
                            print(f"Found existing delivery order by constraint fields: {existing_order.id}")
                            # Add the ID to the order data for future reference
                            order_data['id'] = existing_order.id
                    except Exception as e:
                        print(f"Error finding existing delivery order: {e}")
                
                if existing_order:
                    # Update existing order
                    serializer = DeliveryOrderSerializer(existing_order, data=order_data, partial=True)
                    if serializer.is_valid():
                        updated_order = serializer.save(sync_status='synced', updated_by=user)
                        results.append({
                            'id': updated_order.id,
                            'local_id': updated_order.local_id,
                            'status': 'updated',
                            'message': 'Delivery order updated successfully'
                        })
                    else:
                        results.append({
                            'local_id': order_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
                else:
                    # Create new order
                    serializer = DeliveryOrderSerializer(data=order_data)
                    if serializer.is_valid():
                        new_order = serializer.save(sync_status='synced', created_by=user, updated_by=user)
                        results.append({
                            'id': new_order.id,
                            'local_id': new_order.local_id,
                            'status': 'created',
                            'message': 'Delivery order created successfully'
                        })
                    else:
                        results.append({
                            'local_id': order_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
            
            return Response({
                'status': 'success',
                'message': f'Processed {len(data)} delivery orders',
                'results': results
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class BrokenOrderSyncView(BaseSyncView):
    """API endpoint for syncing broken orders only"""

    @transaction.atomic
    def post(self, request):
        try:
            user = request.user
            data = self.extract_data(request)
            
            if not isinstance(data, list):
                # If data is not a list, wrap it in a list
                data = [data]
            
            print(f"Processing {len(data)} broken orders")
            
            results = []
            for order_data in data:
                # Handle route_id vs route field
                if 'route_id' in order_data and 'route' not in order_data:
                    order_data['route'] = order_data['route_id']
                    print(f"Mapped route_id {order_data['route_id']} to route field")
                
                # Map date field if needed
                if 'date' in order_data and 'report_date' not in order_data:
                    order_data['report_date'] = order_data['date']
                    print(f"Mapped date {order_data['date']} to report_date field")
                
                # Set report_time if not provided
                if 'report_time' not in order_data:
                    order_data['report_time'] = datetime.now().strftime('%H:%M:%S')
                    print(f"Set default report_time: {order_data['report_time']}")
                
                # Process items to ensure product is a primary key
                if 'items' in order_data:
                    processed_items = []
                    for item in order_data['items']:
                        # Create a new item dictionary to avoid modifying the original
                        processed_item = {}
                        
                        # Handle different field names in the payload
                        if 'product_id' in item and 'product' not in item:
                            # Map product_id to product
                            processed_item['product'] = item['product_id']
                            print(f"Mapped product_id {item['product_id']} to product field")
                        elif 'product' in item:
                            processed_item['product'] = item['product']
                        else:
                            # Skip items without product
                            continue
                        
                        # Copy other fields
                        for key, value in item.items():
                            if key != 'product_id':  # Skip product_id as we've already handled it
                                processed_item[key] = value
                        
                        processed_items.append(processed_item)
                    
                    # Replace items with processed items
                    order_data['items'] = processed_items
                
                # Try to find existing order by local_id
                existing_order = None
                if 'local_id' in order_data and order_data['local_id']:
                    existing_order = BrokenOrder.objects.filter(local_id=order_data['local_id']).first()
                    if existing_order:
                        print(f"Found existing broken order by local_id: {existing_order.id}")
                
                if existing_order:
                    # Update existing order
                    serializer = BrokenOrderSerializer(existing_order, data=order_data, partial=True)
                    if serializer.is_valid():
                        updated_order = serializer.save(sync_status='synced', updated_by=user)
                        results.append({
                            'id': updated_order.id,
                            'local_id': updated_order.local_id,
                            'status': 'updated',
                            'message': 'Broken order updated successfully'
                        })
                    else:
                        results.append({
                            'local_id': order_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
                else:
                    # Create new order
                    serializer = BrokenOrderSerializer(data=order_data)
                    if serializer.is_valid():
                        new_order = serializer.save(sync_status='synced', created_by=user, updated_by=user)
                        results.append({
                            'id': new_order.id,
                            'local_id': new_order.local_id,
                            'status': 'created',
                            'message': 'Broken order created successfully'
                        })
                    else:
                        results.append({
                            'local_id': order_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
            
            return Response({
                'status': 'success',
                'message': f'Processed {len(data)} broken orders',
                'results': results
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class ReturnOrderSyncView(BaseSyncView):
    """API endpoint for syncing return orders only"""

    @transaction.atomic
    def post(self, request):
        try:
            user = request.user
            data = self.extract_data(request)
            
            if not isinstance(data, list):
                # If data is not a list, wrap it in a list
                data = [data]
            
            print(f"Processing {len(data)} return orders")
            
            results = []
            for order_data in data:
                # Ensure route is a primary key
                if 'route' in order_data and not isinstance(order_data['route'], int):
                    order_data['route'] = order_data['route'].id if hasattr(order_data['route'], 'id') else order_data['route']
                
                # Process items to ensure product is a primary key
                if 'items' in order_data:
                    for item in order_data['items']:
                        if 'product' in item and not isinstance(item['product'], int):
                            item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']
                
                # Try to find existing order by local_id
                existing_order = None
                if 'local_id' in order_data and order_data['local_id']:
                    existing_order = ReturnedOrder.objects.filter(local_id=order_data['local_id']).first()
                    if existing_order:
                        print(f"Found existing return order by local_id: {existing_order.id}")
                
                if existing_order:
                    # Update existing order
                    serializer = ReturnedOrderSerializer(existing_order, data=order_data, partial=True)
                    if serializer.is_valid():
                        updated_order = serializer.save(sync_status='synced', updated_by=user)
                        results.append({
                            'id': updated_order.id,
                            'local_id': updated_order.local_id,
                            'status': 'updated',
                            'message': 'Return order updated successfully'
                        })
                    else:
                        results.append({
                            'local_id': order_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
                else:
                    # Create new order
                    serializer = ReturnedOrderSerializer(data=order_data)
                    if serializer.is_valid():
                        new_order = serializer.save(sync_status='synced', created_by=user, updated_by=user)
                        results.append({
                            'id': new_order.id,
                            'local_id': new_order.local_id,
                            'status': 'created',
                            'message': 'Return order created successfully'
                        })
                    else:
                        results.append({
                            'local_id': order_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
            
            return Response({
                'status': 'success',
                'message': f'Processed {len(data)} return orders',
                'results': results
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class PublicSaleSyncView(BaseSyncView):
    """API endpoint for syncing public sales only"""

    @transaction.atomic
    def post(self, request):
        try:
            user = request.user
            data = self.extract_data(request)
            
            if not isinstance(data, list):
                # If data is not a list, wrap it in a list
                data = [data]
            
            print(f"Processing {len(data)} public sales")
            
            results = []
            for sale_data in data:
                # Fix time formats
                if 'sale_time' in sale_data and sale_data['sale_time']:
                    sale_data['sale_time'] = self.fix_time_format(sale_data['sale_time'])
                
                # Fix payment method - ensure it's one of the valid choices
                if 'payment_method' in sale_data:
                    valid_payment_methods = ['cash', 'online']
                    if sale_data['payment_method'] not in valid_payment_methods:
                        print(f"Invalid payment_method: {sale_data['payment_method']}, setting to 'cash'")
                        sale_data['payment_method'] = 'cash'
                
                # Try to find existing sale by local_id
                existing_sale = None
                if 'local_id' in sale_data and sale_data['local_id']:
                    existing_sale = PublicSale.objects.filter(local_id=sale_data['local_id']).first()
                    if existing_sale:
                        print(f"Found existing public sale by local_id: {existing_sale.id}")
                
                if existing_sale:
                    # Update existing sale
                    serializer = PublicSaleSerializer(existing_sale, data=sale_data, partial=True)
                    if serializer.is_valid():
                        updated_sale = serializer.save(sync_status='synced', updated_by=user)
                        results.append({
                            'id': updated_sale.id,
                            'local_id': updated_sale.local_id,
                            'status': 'updated',
                            'message': 'Public sale updated successfully'
                        })
                    else:
                        results.append({
                            'local_id': sale_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
                else:
                    # Create new sale
                    serializer = PublicSaleSerializer(data=sale_data)
                    if serializer.is_valid():
                        new_sale = serializer.save(sync_status='synced', created_by=user, updated_by=user)
                        results.append({
                            'id': new_sale.id,
                            'local_id': new_sale.local_id,
                            'status': 'created',
                            'message': 'Public sale created successfully'
                        })
                    else:
                        results.append({
                            'local_id': sale_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
            
            return Response({
                'status': 'success',
                'message': f'Processed {len(data)} public sales',
                'results': results
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryExpenseSyncView(BaseSyncView):
    """API endpoint for syncing delivery expenses only"""

    @transaction.atomic
    def post(self, request):
        try:
            user = request.user
            data = self.extract_data(request)
            
            if not isinstance(data, list):
                # If data is not a list, wrap it in a list
                data = [data]
            
            print(f"Processing {len(data)} delivery expenses")
            
            results = []
            for expense_data in data:
                # Map expense type
                if 'expense_type' in expense_data:
                    expense_type_mapping = {
                        'food': 'food',
                        'vehicle': 'vehicle',
                        'fuel': 'fuel',
                        'other': 'other',
                        'maintenance': 'vehicle',  # Map maintenance to vehicle
                        'repairs': 'vehicle'       # Map repairs to vehicle
                    }
                    
                    original_type = expense_data['expense_type'].lower() if expense_data['expense_type'] else ''
                    print(f'Original expense_type: {original_type}')
                    
                    if original_type in expense_type_mapping:
                        expense_data['expense_type'] = expense_type_mapping[original_type]
                        print(f'Mapped expense_type to: {expense_data["expense_type"]}')
                
                # Set created_by if not provided
                if 'created_by' not in expense_data:
                    expense_data['created_by'] = user.id
                
                # Try to find existing expense by local_id
                existing_expense = None
                if 'local_id' in expense_data and expense_data['local_id']:
                    existing_expense = DeliveryExpense.objects.filter(local_id=expense_data['local_id']).first()
                    if existing_expense:
                        print(f"Found existing delivery expense by local_id: {existing_expense.id}")
                
                if existing_expense:
                    # Update existing expense
                    serializer = DeliveryExpenseSerializer(existing_expense, data=expense_data, partial=True)
                    if serializer.is_valid():
                        updated_expense = serializer.save(sync_status='synced')
                        results.append({
                            'id': updated_expense.id,
                            'local_id': updated_expense.local_id,
                            'status': 'updated',
                            'message': 'Delivery expense updated successfully'
                        })
                    else:
                        results.append({
                            'local_id': expense_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
                else:
                    # Create new expense
                    serializer = DeliveryExpenseSerializer(data=expense_data)
                    if serializer.is_valid():
                        new_expense = serializer.save(sync_status='synced')
                        results.append({
                            'id': new_expense.id,
                            'local_id': new_expense.local_id,
                            'status': 'created',
                            'message': 'Delivery expense created successfully'
                        })
                    else:
                        results.append({
                            'local_id': expense_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
            
            return Response({
                'status': 'success',
                'message': f'Processed {len(data)} delivery expenses',
                'results': results
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class CashDenominationSyncView(BaseSyncView):
    """API endpoint for syncing cash denominations only"""

    @transaction.atomic
    def post(self, request):
        try:
            user = request.user
            data = self.extract_data(request)
            
            if not isinstance(data, list):
                # If data is not a list, wrap it in a list
                data = [data]
            
            print(f"Processing {len(data)} cash denominations")
            
            results = []
            for denomination_data in data:
                # Try to find existing denomination by local_id
                existing_denomination = None
                if 'local_id' in denomination_data and denomination_data['local_id']:
                    existing_denomination = CashDenomination.objects.filter(local_id=denomination_data['local_id']).first()
                    if existing_denomination:
                        print(f"Found existing cash denomination by local_id: {existing_denomination.id}")
                
                if existing_denomination:
                    # Update existing denomination
                    serializer = CashDenominationSerializer(existing_denomination, data=denomination_data, partial=True)
                    if serializer.is_valid():
                        updated_denomination = serializer.save(sync_status='synced')
                        results.append({
                            'id': updated_denomination.id,
                            'local_id': updated_denomination.local_id,
                            'status': 'updated',
                            'message': 'Cash denomination updated successfully'
                        })
                    else:
                        results.append({
                            'local_id': denomination_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
                else:
                    # Create new denomination
                    serializer = CashDenominationSerializer(data=denomination_data)
                    if serializer.is_valid():
                        new_denomination = serializer.save(sync_status='synced')
                        results.append({
                            'id': new_denomination.id,
                            'local_id': new_denomination.local_id,
                            'status': 'created',
                            'message': 'Cash denomination created successfully'
                        })
                    else:
                        results.append({
                            'local_id': denomination_data.get('local_id'),
                            'status': 'error',
                            'message': 'Validation error',
                            'errors': serializer.errors
                        })
            
            return Response({
                'status': 'success',
                'message': f'Processed {len(data)} cash denominations',
                'results': results
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
