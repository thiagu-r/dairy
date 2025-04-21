from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from apps.seller.models import Seller, Route
from apps.products.models import Product, PricePlan, ProductPrice, Category
from apps.sales.models import SalesOrder
from apps.delivery.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    LoadingOrder,
    LoadingOrderItem,
    DeliveryOrder,
    DeliveryOrderItem,
    ReturnedOrder,
    ReturnedOrderItem,
    BrokenOrder,
    BrokenOrderItem,
    PublicSale,
    PublicSaleItem,
    DeliveryExpense,
    CashDenomination,
    DeliveryTeam
    # Payment
)

from .serializers import (
    UserSerializer,
    LoginSerializer,
    SellerSerializer,
    ProductSerializer,
    RouteSerializer,
    PricePlanSerializer,
    ProductPriceSerializer,
    SalesOrderSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderItemSerializer,
    LoadingOrderSerializer,
    LoadingOrderItemSerializer,
    DeliveryOrderSerializer,
    DeliveryOrderItemSerializer,
    ReturnedOrderSerializer,
    ReturnedOrderItemSerializer,
    BrokenOrderSerializer,
    BrokenOrderItemSerializer,
    PublicSaleSerializer,
    PublicSaleItemSerializer,
    DeliveryExpenseSerializer,
    CashDenominationSerializer,
    # PaymentSerializer,
    SyncDataSerializer,
    SyncStatusSerializer,
    CategorySerializer
)

from .filters import (
    SellerFilter,
    SalesOrderFilter,
    PurchaseOrderFilter,
    LoadingOrderFilter,
    DeliveryOrderFilter,
    ReturnedOrderFilter,
    BrokenOrderFilter,
    PublicSaleFilter,
    # PaymentFilter
)

# Authentication Views
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Use JWT Authentication
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # For JWT tokens, we can't invalidate them on the server side
            # The client should discard the tokens
            # We'll just log the user out of the session
            logout(request)
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Master Data Views
class SellerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Seller.objects.all()
    serializer_class = SellerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SellerFilter
    search_fields = ['store_name', 'owner_name']
    ordering_fields = ['store_name', 'route__name']
    ordering = ['store_name']
    pagination_class = None  # No pagination for master data

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code']
    ordering = ['name']
    pagination_class = None  # No pagination for master data)

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code']
    ordering = ['name']
    pagination_class = None  # No pagination for master data

class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']
    pagination_class = None  # No pagination for master data

class PricePlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PricePlan.objects.filter(is_active=True)
    serializer_class = PricePlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_general', 'seller', 'is_active']
    search_fields = ['name']
    ordering_fields = ['valid_from', 'valid_to', 'name']
    ordering = ['-valid_from']
    pagination_class = None  # No pagination for master data

class ProductPriceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['price_plan', 'product']
    ordering_fields = ['price_plan', 'product']
    ordering = ['price_plan', 'product']
    pagination_class = None  # No pagination for master data

class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SalesOrderFilter
    search_fields = ['order_number', 'seller__store_name']
    ordering_fields = ['order_date', 'seller__store_name']
    ordering = ['-order_date']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Use the default create method, which will call our custom serializer's create method
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Use the default update method, which will call our custom serializer's update method
        return super().update(request, *args, **kwargs)

class PurchaseOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PurchaseOrderFilter
    search_fields = ['order_number','delivery_date', 'route__name']
    ordering_fields = ['delivery_date']
    ordering = ['-delivery_date']

class LoadingOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoadingOrder.objects.all()
    serializer_class = LoadingOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LoadingOrderFilter
    search_fields = ['order_number', 'route__name']
    ordering_fields = ['loading_date', 'route__name']
    ordering = ['-loading_date']

# Delivery Operation Views
class DeliveryOrderViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOrder.objects.all()
    serializer_class = DeliveryOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DeliveryOrderFilter
    search_fields = ['order_number', 'seller__store_name', 'route__name']
    ordering_fields = ['delivery_date', 'seller__store_name', 'route__name']
    ordering = ['-delivery_date']
    pagination_class = None  # Disable pagination for this viewset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Set sync_status to 'pending' for offline-created records
        if request.data.get('is_offline', False):
            request.data['sync_status'] = 'pending'

        return super().create(request, *args, **kwargs)

class ReturnedOrderViewSet(viewsets.ModelViewSet):
    queryset = ReturnedOrder.objects.all()
    serializer_class = ReturnedOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReturnedOrderFilter
    search_fields = ['order_number', 'route__name']
    ordering_fields = ['return_date', 'route__name']
    ordering = ['-return_date']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Set sync_status to 'pending' for offline-created records
        if request.data.get('is_offline', False):
            request.data['sync_status'] = 'pending'

        return super().create(request, *args, **kwargs)

class BrokenOrderViewSet(viewsets.ModelViewSet):
    queryset = BrokenOrder.objects.all()
    serializer_class = BrokenOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BrokenOrderFilter
    search_fields = ['order_number', 'route__name']
    ordering_fields = ['broken_date', 'route__name']
    ordering = ['-broken_date']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Set sync_status to 'pending' for offline-created records
        if request.data.get('is_offline', False):
            request.data['sync_status'] = 'pending'

        return super().create(request, *args, **kwargs)

class PublicSaleViewSet(viewsets.ModelViewSet):
    queryset = PublicSale.objects.all()
    serializer_class = PublicSaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PublicSaleFilter
    search_fields = ['sale_number', 'route__name']
    ordering_fields = ['sale_date', 'route__name']
    ordering = ['-sale_date']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Set sync_status to 'pending' for offline-created records
        if request.data.get('is_offline', False):
            request.data['sync_status'] = 'pending'

        return super().create(request, *args, **kwargs)

# class PaymentViewSet(viewsets.ModelViewSet):
#     queryset = Payment.objects.all()
#     serializer_class = PaymentSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_class = PaymentFilter
#     search_fields = ['payment_number', 'seller__store_name']
#     ordering_fields = ['payment_date', 'seller__store_name']
#     ordering = ['-payment_date']

#     @transaction.atomic
#     def create(self, request, *args, **kwargs):
#         # Set sync_status to 'pending' for offline-created records
#         if request.data.get('is_offline', False):
#             request.data['sync_status'] = 'pending'

#         return super().create(request, *args, **kwargs)

class DeliveryOrderItemViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOrderItem.objects.all()
    serializer_class = DeliveryOrderItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['delivery_order']

    def get_queryset(self):
        queryset = super().get_queryset()
        delivery_order_id = self.request.query_params.get('delivery_order')
        if delivery_order_id:
            queryset = queryset.filter(delivery_order_id=delivery_order_id)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Set sync_status to 'pending' for offline-created records
        if request.data.get('is_offline', False):
            request.data['sync_status'] = 'pending'
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Set sync_status to 'pending' for offline updates
        if request.data.get('is_offline', False):
            request.data['sync_status'] = 'pending'
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Only allow deletion if the delivery order is in draft status
        if instance.delivery_order.status != 'draft':
            return Response(
                {'detail': 'Cannot delete items from a delivery order that is not in draft status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def bulk_create(self, request):
        """Create multiple delivery order items in a single request."""
        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'detail': 'No items provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if all items belong to the same delivery order
        delivery_order_ids = set(item.get('delivery_order') for item in items_data)
        if len(delivery_order_ids) != 1:
            return Response(
                {'detail': 'All items must belong to the same delivery order'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate delivery order exists
        delivery_order_id = list(delivery_order_ids)[0]
        try:
            delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
        except DeliveryOrder.DoesNotExist:
            return Response(
                {'detail': f'Delivery order with id {delivery_order_id} does not exist'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process items
        created_items = []
        errors = []

        for index, item_data in enumerate(items_data):
            # Set sync_status to 'pending' for offline-created records
            if request.data.get('is_offline', False):
                item_data['sync_status'] = 'pending'

            serializer = self.get_serializer(data=item_data)
            if serializer.is_valid():
                serializer.save()
                created_items.append(serializer.data)
            else:
                errors.append({
                    'index': index,
                    'errors': serializer.errors
                })

        # If there were any errors, rollback and return the errors
        if errors:
            return Response({
                'detail': 'Some items could not be created',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Recalculate delivery order totals
        delivery_order.recalculate_totals()

        return Response({
            'detail': f'Successfully created {len(created_items)} items',
            'items': created_items
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['put'])
    @transaction.atomic
    def bulk_update(self, request):
        """Update multiple delivery order items in a single request."""
        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'detail': 'No items provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if all items have IDs
        missing_ids = [i for i, item in enumerate(items_data) if 'id' not in item]
        if missing_ids:
            return Response({
                'detail': 'All items must have an id',
                'missing_ids_at_indices': missing_ids
            }, status=status.HTTP_400_BAD_REQUEST)

        # Process items
        updated_items = []
        errors = []
        delivery_order_ids = set()

        for index, item_data in enumerate(items_data):
            try:
                item = DeliveryOrderItem.objects.get(id=item_data['id'])
                delivery_order_ids.add(item.delivery_order_id)

                # Set sync_status to 'pending' for offline updates
                if request.data.get('is_offline', False):
                    item_data['sync_status'] = 'pending'

                serializer = self.get_serializer(item, data=item_data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    updated_items.append(serializer.data)
                else:
                    errors.append({
                        'id': item_data['id'],
                        'index': index,
                        'errors': serializer.errors
                    })
            except DeliveryOrderItem.DoesNotExist:
                errors.append({
                    'id': item_data['id'],
                    'index': index,
                    'errors': {'detail': f'Item with id {item_data["id"]} does not exist'}
                })

        # If there were any errors, rollback and return the errors
        if errors:
            return Response({
                'detail': 'Some items could not be updated',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Recalculate delivery order totals for all affected orders
        for delivery_order_id in delivery_order_ids:
            try:
                delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
                delivery_order.recalculate_totals()
            except DeliveryOrder.DoesNotExist:
                pass  # This shouldn't happen, but just in case

        return Response({
            'detail': f'Successfully updated {len(updated_items)} items',
            'items': updated_items
        })

# Sync Views
@method_decorator(csrf_exempt, name='dispatch')
class SyncView(APIView):
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

    def preprocess_data(self, data, user):
        """Preprocess the data before passing it to the serializer validation."""
        # Make a deep copy to avoid modifying the original data
        import copy
        processed_data = copy.deepcopy(data)
        delivery_date = None
        route_id = None
        try:
            if 'delivery_orders' in processed_data:
                delivery_order = processed_data['delivery_orders'][0]
                delivery_date = delivery_order.get('delivery_date')
                route_id = delivery_order.get('route')
        except Exception as e:
            print('No delivery orders provided in the request data.', e)

        # Process delivery orders
        if 'delivery_orders' in processed_data:
            # First, check for duplicate delivery orders (same route, seller, delivery_date)
            unique_orders = {}
            duplicate_indices = []

            for i, order in enumerate(processed_data['delivery_orders']):
                if 'route' in order and 'seller' in order and 'delivery_date' in order:
                    key = f"{order['route']}-{order['seller']}-{order['delivery_date']}"
                    if key in unique_orders:
                        # This is a duplicate, mark it for removal
                        duplicate_indices.append(i)
                        print(f"Found duplicate delivery order at index {i}: {key}")

                        # Merge items if both orders have items
                        if 'items' in order and 'items' in unique_orders[key]:
                            # Create a set of product IDs to avoid duplicates
                            existing_product_ids = set(item['product'] for item in unique_orders[key]['items'] if 'product' in item)

                            # Add only items with products not already in the order
                            for item in order['items']:
                                if 'product' in item and item['product'] not in existing_product_ids:
                                    unique_orders[key]['items'].append(item)
                                    existing_product_ids.add(item['product'])
                                    print(f"Added new product {item['product']} to merged order")
                                elif 'product' in item:
                                    # Update quantities for existing products
                                    for existing_item in unique_orders[key]['items']:
                                        if 'product' in existing_item and existing_item['product'] == item['product']:
                                            # Update quantities if needed
                                            if 'extra_quantity' in item and 'extra_quantity' in existing_item:
                                                existing_item['extra_quantity'] = max(existing_item['extra_quantity'], item['extra_quantity'])
                                            if 'ordered_quantity' in item and 'ordered_quantity' in existing_item:
                                                existing_item['ordered_quantity'] = max(existing_item['ordered_quantity'], item['ordered_quantity'])
                                            print(f"Updated quantities for product {item['product']} in merged order")
                                            break
                    else:
                        # This is a unique order
                        unique_orders[key] = order

            # Remove duplicates (in reverse order to avoid index shifting)
            for i in sorted(duplicate_indices, reverse=True):
                print(f"Removing duplicate delivery order at index {i}")
                processed_data['delivery_orders'].pop(i)

            # Now check for existing delivery orders in the database
            for order in processed_data['delivery_orders']:
                if 'route' in order and 'seller' in order and 'delivery_date' in order:
                    try:
                        # Check if this order already exists in the database
                        existing_order = DeliveryOrder.objects.filter(
                            route_id=order['route'],
                            seller_id=order['seller'],
                            delivery_date=order['delivery_date']
                        ).first()

                        if existing_order:
                            print(f"Found existing delivery order in database: {existing_order.id}")
                            # Add the existing order ID to the data
                            order['id'] = existing_order.id

                            # If we have local_id in the data but not in the database, update it
                            if 'local_id' in order and order['local_id'] and not existing_order.local_id:
                                print(f"Updating local_id for existing order: {order['local_id']}")
                                existing_order.local_id = order['local_id']
                                existing_order.save(update_fields=['local_id'])
                    except Exception as e:
                        print(f"Error checking for existing delivery order: {e}")

            # Now process each order
            for order in processed_data['delivery_orders']:
                # Fix time formats
                if 'delivery_time' in order and order['delivery_time']:
                    order['delivery_time'] = self.fix_time_format(order['delivery_time'])

                if 'actual_delivery_time' in order and order['actual_delivery_time']:
                    order['actual_delivery_time'] = self.fix_time_format(order['actual_delivery_time'])

                # Fix status
                if 'status' in order and order['status'] == 'draft':
                    order['status'] = 'pending'

                # Fix payment method
                if 'payment_method' in order and order['payment_method'] == 'credit':
                    order['payment_method'] = 'cash'

        # Process public sales
        if 'public_sales' in processed_data:
            for sale in processed_data['public_sales']:
                # Fix time formats
                if 'sale_time' in sale and sale['sale_time']:
                    sale['sale_time'] = self.fix_time_format(sale['sale_time'])

        # Process expenses
        if 'expenses' in processed_data:
            for expense in processed_data['expenses']:
                # Map expense type
                if 'expense_type' in expense:
                    expense_type = expense['expense_type'].lower() if expense['expense_type'] else ''
                    if expense_type == 'maintenance':
                        expense['expense_type'] = 'vehicle'
                if 'expense_date' not in expense:
                    expense['expense_date'] = delivery_date
                if 'created_by' not in expense:
                    expense['created_by'] = user.id
                if 'delivery_team' not in expense:
                    loading_order = LoadingOrder.objects.filter(route_id=route_id, loading_date=delivery_date).first()
                    print('delivery team: ', loading_order.purchase_order.delivery_team.id)
                    expense['delivery_team'] = loading_order.purchase_order.delivery_team.id if loading_order else None

        # Process denominations
        if 'denominations' in processed_data and isinstance(processed_data['denominations'], list):
            # If it's a list of lists, flatten it
            if processed_data['denominations'] and isinstance(processed_data['denominations'][0], list):
                flattened = []
                for group in processed_data['denominations']:
                    if isinstance(group, list):
                        flattened.extend(group)
                    else:
                        flattened.append(group)
                processed_data['denominations'] = flattened

            # Make sure each denomination has a delivery_order
            if 'delivery_orders' in processed_data and processed_data['delivery_orders']:
                # Find the first delivery order with an ID or local_id
                delivery_order_ref = None
                for order in processed_data['delivery_orders']:
                    if 'id' in order or 'local_id' in order:
                        delivery_order_ref = order
                        break

                # Set delivery_order for denominations that don't have one
                if delivery_order_ref:
                    for denomination in processed_data['denominations']:
                        if 'delivery_order' not in denomination or not denomination['delivery_order']:
                            if 'id' in delivery_order_ref:
                                denomination['delivery_order'] = delivery_order_ref['id']
                            elif 'local_id' in delivery_order_ref:
                                # We'll use the local_id to find the delivery order later
                                denomination['delivery_order_local_id'] = delivery_order_ref['local_id']

        return processed_data

    def post(self, request):
        try:
            user = request.user
            # Check if data is nested inside a 'data' key
            if 'data' in request.data:
                data_to_process = request.data['data']
                print('Found nested data structure, extracting data from "data" key')
            else:
                data_to_process = request.data
                print('Using direct data structure')

            # Pre-process the data to fix time formats and other issues before validation
            data_to_process = self.preprocess_data(data_to_process, user)
            print('Preprocessed data:', data_to_process)

            # Instead of validating all data at once, we'll validate each section separately
            # This way, if one section fails validation, we can still process the others
            validated_data = {}

            # Process delivery orders separately
            if 'delivery_orders' in data_to_process:
                print(f"Processing {len(data_to_process['delivery_orders'])} delivery orders")
                valid_delivery_orders = []

                for order_data in data_to_process['delivery_orders']:
                    # Try to find existing order first
                    existing_order = None

                    # First, check if we have an ID in the order data (added during preprocessing)
                    if 'id' in order_data:
                        print(f"Searching for existing order by ID: {order_data['id']}")
                        try:
                            existing_order = DeliveryOrder.objects.get(id=order_data['id'])
                            print(f"Found existing delivery order by ID: {existing_order.id}")
                        except DeliveryOrder.DoesNotExist:
                            print(f"No existing order found with ID: {order_data['id']}")

                    # If not found by ID, try to find by local_id
                    if not existing_order and 'local_id' in order_data and order_data['local_id']:
                        print(f"Searching for existing order by local_id: {order_data['local_id']}")
                        existing_order = DeliveryOrder.objects.filter(local_id=order_data['local_id']).first()
                        if existing_order:
                            print(f"Found existing delivery order by local_id: {existing_order.id}")

                    # If not found by local_id, try to find by unique constraint fields
                    if not existing_order and 'route' in order_data and 'seller' in order_data and 'delivery_date' in order_data:
                        print(f"Searching for existing order by constraint fields:")
                        print(f"  - route: {order_data['route']}")
                        print(f"  - seller: {order_data['seller']}")
                        print(f"  - delivery_date: {order_data['delivery_date']}")

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
                        print(f"Updating existing delivery order: {existing_order.id}")

                        # Check if there are any items in the order data
                        if 'items' not in order_data or not order_data['items']:
                            print("No items in order data, removing items field to avoid validation errors")
                            # Remove items field to avoid validation errors
                            order_data_copy = order_data.copy()
                            if 'items' in order_data_copy:
                                del order_data_copy['items']
                        else:
                            order_data_copy = order_data

                        try:
                            # Update the order directly using model instance
                            for key, value in order_data_copy.items():
                                # Skip id, route, seller, and delivery_date fields to maintain the unique constraint
                                if key in ['id', 'route', 'seller', 'delivery_date']:
                                    continue

                                if key != 'items' and hasattr(existing_order, key):
                                    # Handle foreign key fields
                                    if key == 'sales_order' and isinstance(value, int):
                                        try:
                                            sales_order = SalesOrder.objects.get(id=value)
                                            setattr(existing_order, key, sales_order)
                                        except SalesOrder.DoesNotExist:
                                            print(f"SalesOrder with id {value} does not exist")
                                    else:
                                        # For non-foreign key fields
                                        setattr(existing_order, key, value)

                            existing_order.sync_status = 'synced'
                            existing_order.updated_by = user
                            existing_order.save()

                            # Process items separately
                            if 'items' in order_data and order_data['items']:
                                print(f"Processing {len(order_data['items'])} items for delivery order {existing_order.id}")

                                # Get all existing items for this delivery order
                                existing_items = {item.product_id: item for item in DeliveryOrderItem.objects.filter(delivery_order=existing_order)}
                                print(f"Found {len(existing_items)} existing items in the database")

                                for item_data in order_data['items']:
                                    if 'product' in item_data:
                                        product_id = item_data['product']

                                        # Check if this product already exists in the delivery order
                                        if product_id in existing_items:
                                            # Update existing item
                                            existing_item = existing_items[product_id]
                                            print(f"Updating existing item for product {product_id}")

                                            # Update fields
                                            for key, value in item_data.items():
                                                if key != 'product' and hasattr(existing_item, key):
                                                    # For quantity fields, take the maximum value
                                                    if key in ['ordered_quantity', 'extra_quantity', 'delivered_quantity'] and getattr(existing_item, key) is not None:
                                                        current_value = getattr(existing_item, key)
                                                        # Convert both values to float for comparison
                                                        try:
                                                            # Handle various types by converting to string first, then to float
                                                            if current_value is None or current_value == '':
                                                                current_float = 0.0
                                                            else:
                                                                current_float = float(str(current_value).replace(',', ''))

                                                            if value is None or value == '':
                                                                new_float = 0.0
                                                            else:
                                                                new_float = float(str(value).replace(',', ''))

                                                            # Use the maximum value
                                                            max_value = max(current_float, new_float)

                                                            # Format as string with 2 decimal places for consistency
                                                            formatted_value = f"{max_value:.2f}"
                                                            setattr(existing_item, key, formatted_value)
                                                            print(f"Updated {key} from {current_value} to {formatted_value}")
                                                        except Exception as e:
                                                            print(f"Error comparing quantities for {key}: {e}, using new value")
                                                            setattr(existing_item, key, value)
                                                    else:
                                                        setattr(existing_item, key, value)

                                            existing_item.save()
                                        else:
                                            # Create new item
                                            try:
                                                # Get the product instance
                                                product = Product.objects.get(id=product_id)
                                                print(f"Creating new item for product {product_id}")

                                                # Create new item with product instance
                                                new_item = DeliveryOrderItem(
                                                    delivery_order=existing_order,
                                                    product=product
                                                )

                                                # Set other fields
                                                for key, value in item_data.items():
                                                    if key != 'product' and hasattr(new_item, key):
                                                        setattr(new_item, key, value)

                                                new_item.save()

                                                # Add to existing items dict to avoid duplicates
                                                existing_items[product_id] = new_item
                                            except Product.DoesNotExist:
                                                print(f"Product with id {product_id} does not exist")
                                            except Exception as e:
                                                print(f"Error creating delivery order item: {e}")

                            # Add to valid orders
                            valid_delivery_orders.append(existing_order)
                            print(f"Successfully updated delivery order: {existing_order.id}")
                        except Exception as e:
                            print(f"Error updating delivery order: {e}")
                    else:
                        # Create new order
                        print("Creating new delivery order")
                        try:
                            # Create the order directly using model
                            new_order = DeliveryOrder(
                                sync_status='synced',
                                created_by=user,
                                updated_by=user
                            )

                            # Set fields from order_data
                            for key, value in order_data.items():
                                if key != 'items' and hasattr(new_order, key):
                                    # Handle foreign key fields
                                    if key == 'route' and isinstance(value, int):
                                        try:
                                            route = Route.objects.get(id=value)
                                            setattr(new_order, key, route)
                                        except Route.DoesNotExist:
                                            print(f"Route with id {value} does not exist")
                                    elif key == 'seller' and isinstance(value, int):
                                        try:
                                            seller = Seller.objects.get(id=value)
                                            setattr(new_order, key, seller)
                                        except Seller.DoesNotExist:
                                            print(f"Seller with id {value} does not exist")
                                    elif key == 'sales_order' and isinstance(value, int):
                                        try:
                                            sales_order = SalesOrder.objects.get(id=value)
                                            setattr(new_order, key, sales_order)
                                        except SalesOrder.DoesNotExist:
                                            print(f"SalesOrder with id {value} does not exist")
                                    else:
                                        # For non-foreign key fields
                                        setattr(new_order, key, value)

                            # Save the new order
                            new_order.save()

                            # Process items
                            if 'items' in order_data and order_data['items']:
                                print(f"Processing {len(order_data['items'])} items for new delivery order {new_order.id}")

                                # Keep track of products we've already added
                                added_products = set()

                                for item_data in order_data['items']:
                                    if 'product' in item_data:
                                        product_id = item_data['product']

                                        # Skip if we've already added this product
                                        if product_id in added_products:
                                            print(f"Skipping duplicate product {product_id}")
                                            continue

                                        try:
                                            # Get the product instance
                                            product = Product.objects.get(id=product_id)
                                            print(f"Creating item for product {product_id}")

                                            # Create new item with product instance
                                            new_item = DeliveryOrderItem(
                                                delivery_order=new_order,
                                                product=product
                                            )

                                            # Set other fields
                                            for key, value in item_data.items():
                                                if key != 'product' and hasattr(new_item, key):
                                                    setattr(new_item, key, value)

                                            new_item.save()

                                            # Mark this product as added
                                            added_products.add(product_id)
                                        except Product.DoesNotExist:
                                            print(f"Product with id {product_id} does not exist")
                                        except Exception as e:
                                            print(f"Error creating delivery order item: {e}")

                            # Add to valid orders
                            valid_delivery_orders.append(new_order)
                            print(f"Successfully created delivery order: {new_order.id}")
                        except Exception as e:
                            print(f"Error creating delivery order: {e}")

            # Add valid delivery orders to validated data
            validated_data['delivery_orders'] = valid_delivery_orders
        except Exception as e:
            print(f"Error during sync: {e}")
            import traceback
            traceback.print_exc()
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # For other sections, use the serializer as before
        other_sections = ['returned_orders', 'broken_orders', 'public_sales', 'expenses', 'denominations']
        for section in other_sections:
            if section in data_to_process:
                section_serializer = None
                if section == 'returned_orders':
                    section_serializer = ReturnedOrderSerializer(data=data_to_process[section], many=True)
                elif section == 'broken_orders':
                    section_serializer = BrokenOrderSerializer(data=data_to_process[section], many=True)
                elif section == 'public_sales':
                    section_serializer = PublicSaleSerializer(data=data_to_process[section], many=True)
                elif section == 'expenses':
                    section_serializer = DeliveryExpenseSerializer(data=data_to_process[section], many=True)
                elif section == 'denominations':
                    section_serializer = CashDenominationSerializer(data=data_to_process[section], many=True)

                if section_serializer and section_serializer.is_valid():
                    validated_data[section] = section_serializer.validated_data
                else:
                    print(f"Validation errors in {section}: {section_serializer.errors if section_serializer else 'No serializer'}")

        # Create a dummy serializer for compatibility with the rest of the code
        class DummySerializer:
            def __init__(self, validated_data):
                self.validated_data = validated_data

        serializer = DummySerializer(validated_data)

        # We've already processed delivery orders above, so we can skip this section
        # Process other sections

        # Process returned orders - check both 'returned_orders' and 'return_orders' keys
        return_orders_key = 'returned_orders' if 'returned_orders' in serializer.validated_data else 'return_orders' if 'return_orders' in serializer.validated_data else None

        if return_orders_key:
            for order_data in serializer.validated_data[return_orders_key]:
                # Ensure route is a primary key
                if 'route' in order_data and not isinstance(order_data['route'], int):
                    order_data['route'] = order_data['route'].id if hasattr(order_data['route'], 'id') else order_data['route']

                # Process items to ensure product is a primary key
                if 'items' in order_data:
                    for item in order_data['items']:
                        if 'product' in item and not isinstance(item['product'], int):
                            item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']

                # Check if this returned order already exists by local_id
                existing_order = None
                if 'local_id' in order_data and order_data['local_id']:
                    existing_order = ReturnedOrder.objects.filter(local_id=order_data['local_id']).first()
                    if existing_order:
                        print(f"Found existing returned order by local_id: {existing_order.id}")

                if existing_order:
                    # Update existing order
                    returned_serializer = ReturnedOrderSerializer(existing_order, data=order_data, partial=True)
                    if returned_serializer.is_valid():
                        returned_serializer.save(sync_status='synced', updated_by=request.user)
                        print(f"Successfully updated returned order: {existing_order.id}")
                    else:
                        print(f"Validation errors updating returned order: {returned_serializer.errors}")
                        print(f"Data received: {order_data}")
                        # Continue processing other orders instead of failing the whole request
                        continue
                else:
                    # Create new order
                    returned_serializer = ReturnedOrderSerializer(data=order_data)
                    if returned_serializer.is_valid():
                        returned_serializer.save(sync_status='synced', updated_by=request.user, created_by=request.user)
                        print(f"Successfully created returned order")
                    else:
                        print(f"Validation errors creating returned order: {returned_serializer.errors}")
                        print(f"Data received: {order_data}")
                        # Continue processing other orders instead of failing the whole request
                        continue
        else:
            print("Returned orders not provided in the request data.")

        # Process broken orders
        if 'broken_orders' in serializer.validated_data:
            for order_data in serializer.validated_data['broken_orders']:
                # Handle route_id vs route field
                if 'route_id' in order_data and not 'route' in order_data:
                    order_data['route'] = order_data['route_id']
                    print(f"Mapped route_id {order_data['route_id']} to route field")

                # Ensure route is a primary key
                if 'route' in order_data and not isinstance(order_data['route'], int):
                    try:
                        order_data['route'] = int(order_data['route'])
                        print(f"Converted route {order_data['route']} to integer")
                    except (ValueError, TypeError):
                        order_data['route'] = order_data['route'].id if hasattr(order_data['route'], 'id') else order_data['route']
                        print(f"Used object id for route: {order_data['route']}")

                # Process items to ensure product is a primary key
                if 'items' in order_data:
                    for item in order_data['items']:
                        # Handle different field names in the payload
                        if 'product_id' in item and not 'product' in item:
                            # Map product_id to product
                            item['product'] = item['product_id']
                            print(f"Mapped product_id {item['product_id']} to product field")

                        # Ensure product is an integer
                        if 'product' in item and not isinstance(item['product'], int):
                            try:
                                item['product'] = int(item['product'])
                                print(f"Converted product {item['product']} to integer")
                            except (ValueError, TypeError):
                                item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']
                                print(f"Used object id for product: {item['product']}")

                        # Map quantity field if needed
                        if 'quantity' in item and not 'broken_quantity' in item:
                            item['broken_quantity'] = item['quantity']
                            print(f"Mapped quantity {item['quantity']} to broken_quantity field")

                # Check if this broken order already exists by id or local_id
                existing_order = None

                # First check by id field (which might be used as local_id in the mobile app)
                if 'id' in order_data and order_data['id']:
                    existing_order = BrokenOrder.objects.filter(local_id=str(order_data['id'])).first()
                    if existing_order:
                        print(f"Found existing broken order by id as local_id: {existing_order.id}")

                # Then check by local_id if not found
                if not existing_order and 'local_id' in order_data and order_data['local_id']:
                    existing_order = BrokenOrder.objects.filter(local_id=order_data['local_id']).first()
                    if existing_order:
                        print(f"Found existing broken order by local_id: {existing_order.id}")

                if existing_order:
                    # Update existing order
                    broken_serializer = BrokenOrderSerializer(existing_order, data=order_data, partial=True)
                    if broken_serializer.is_valid():
                        broken_serializer.save(sync_status='synced', updated_by=request.user)
                        print(f"Successfully updated broken order: {existing_order.id}")
                    else:
                        print(f"Validation errors updating broken order: {broken_serializer.errors}")
                        print(f"Data received: {order_data}")
                        # Continue processing other orders instead of failing the whole request
                        continue
                else:
                    # Create new order
                    broken_serializer = BrokenOrderSerializer(data=order_data)
                    if broken_serializer.is_valid():
                        broken_serializer.save(sync_status='synced', updated_by=request.user, created_by=request.user)
                        print(f"Successfully created broken order")
                    else:
                        print(f"Validation errors creating broken order: {broken_serializer.errors}")
                        print(f"Data received: {order_data}")
                        # Continue processing other orders instead of failing the whole request
                        continue
        else:
            print("Broken orders not provided in the request data.")

        # Process public sales
        if 'public_sales' in serializer.validated_data:
            for sale_data in serializer.validated_data['public_sales']:
                # Fix sale_time format
                if 'sale_time' in sale_data and sale_data['sale_time']:
                    try:
                        # First, check if it's a datetime string with space
                        if isinstance(sale_data['sale_time'], str) and ' ' in sale_data['sale_time']:
                            # Extract just the time part
                            time_part = sale_data['sale_time'].split(' ')[1]
                            # Parse the time part
                            time_obj = datetime.strptime(time_part, '%H:%M:%S').time()
                            # Format as HH:MM:SS
                            sale_data['sale_time'] = time_obj.strftime('%H:%M:%S')
                        else:
                            # Try to parse as datetime
                            dt = datetime.strptime(str(sale_data['sale_time']), '%Y-%m-%d %H:%M:%S')
                            sale_data['sale_time'] = dt.time().strftime('%H:%M:%S')
                    except (ValueError, TypeError):
                        try:
                            # Try to parse as time
                            dt = datetime.strptime(str(sale_data['sale_time']), '%H:%M:%S')
                            sale_data['sale_time'] = dt.strftime('%H:%M:%S')
                        except (ValueError, TypeError):
                            # If all else fails, set to a default time
                            sale_data['sale_time'] = '00:00:00'

                # Ensure route and product are primary keys
                if 'route' in sale_data and not isinstance(sale_data['route'], int):
                    sale_data['route'] = sale_data['route'].id if hasattr(sale_data['route'], 'id') else sale_data['route']

                # Process items to ensure product is a primary key
                if 'items' in sale_data:
                    for item in sale_data['items']:
                        if 'product' in item and not isinstance(item['product'], int):
                            item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']

                # Check if this public sale already exists by local_id
                existing_sale = None
                if 'local_id' in sale_data and sale_data['local_id']:
                    existing_sale = PublicSale.objects.filter(local_id=sale_data['local_id']).first()
                    if existing_sale:
                        print(f"Found existing public sale by local_id: {existing_sale.id}")

                if existing_sale:
                    # Update existing sale
                    sale_serializer = PublicSaleSerializer(existing_sale, data=sale_data, partial=True)
                    if sale_serializer.is_valid():
                        sale_serializer.save(sync_status='synced', updated_by=request.user)
                        print(f"Successfully updated public sale: {existing_sale.id}")
                    else:
                        # Print detailed error information
                        print(f"Validation errors updating public sale: {sale_serializer.errors}")
                        print(f"Data received: {sale_data}")
                        # Continue processing other sales instead of failing the whole request
                        continue
                else:
                    # Create new sale
                    sale_serializer = PublicSaleSerializer(data=sale_data)
                    if sale_serializer.is_valid():
                        sale_serializer.save(sync_status='synced', updated_by=request.user, created_by=request.user)
                        print(f"Successfully created public sale")
                    else:
                        # Print detailed error information
                        print(f"Validation errors creating public sale: {sale_serializer.errors}")
                        print(f"Data received: {sale_data}")
                        # Continue processing other sales instead of failing the whole request
                        continue

        else:
            print("Public sales not provided in the request data.")

        # Process expenses
        if 'expenses' in serializer.validated_data:
            for expense_data in serializer.validated_data['expenses']:
                # Find the delivery team for the route
                route_id = expense_data.get('route', None)
                expense_date = expense_data.get('date', None)

                # If we don't have a date, use the first delivery order's date
                if not expense_date and 'delivery_orders' in serializer.validated_data and serializer.validated_data['delivery_orders']:
                    expense_date = serializer.validated_data['delivery_orders'][0].get('delivery_date')

                # Find the delivery team for this route
                delivery_team = None
                if route_id:
                    # Try to find a loading order for this route and date
                    loading_order = LoadingOrder.objects.filter(route_id=route_id, delivery_date=expense_date).first()
                    if loading_order and loading_order.purchase_order and loading_order.purchase_order.delivery_team:
                        delivery_team = loading_order.purchase_order.delivery_team.id
                    else:
                        # Fallback: find any delivery team assigned to this route
                        delivery_team_obj = DeliveryTeam.objects.filter(routes__id=route_id).first()
                        if delivery_team_obj:
                            delivery_team = delivery_team_obj.id
                        else:
                            # Last resort: use the first delivery team
                            first_team = DeliveryTeam.objects.first()
                            if first_team:
                                delivery_team = first_team.id

                # Map expense fields to match the model
                mapped_expense_data = {
                    'delivery_team': delivery_team,
                    'expense_date': expense_date,
                    'expense_type': 'other',  # Default to 'other' and map if possible
                    'amount': expense_data.get('amount', None),
                    'notes': expense_data.get('description', None),
                    'local_id': expense_data.get('local_id', None),
                    'sync_status': 'synced'
                }

                print(f"Before expense type mapping: {expense_data.get('expense_type')}")
                # Map expense type
                expense_type = expense_data.get('expense_type', '').lower() if expense_data.get('expense_type') else ''
                if expense_type == 'fuel':
                    mapped_expense_data['expense_type'] = 'fuel'
                elif expense_type == 'food':
                    mapped_expense_data['expense_type'] = 'food'
                elif expense_type in ['vehicle', 'maintenance', 'repairs']:
                    mapped_expense_data['expense_type'] = 'vehicle'
                print(f"After expense type mapping: {mapped_expense_data['expense_type']}")

                print(f"Mapped expense data: {mapped_expense_data}")

                # Skip if we couldn't find a delivery team
                if not mapped_expense_data['delivery_team']:
                    print(f"Skipping expense due to missing delivery team: {expense_data}")
                    continue

                # Add created_by to the data directly
                # This is needed because the serializer requires it
                mapped_expense_data['created_by'] = request.user.id

                print(f"Final expense data with created_by: {mapped_expense_data}")

                # Check if this expense already exists by local_id
                existing_expense = None
                if 'local_id' in mapped_expense_data and mapped_expense_data['local_id']:
                    existing_expense = DeliveryExpense.objects.filter(local_id=mapped_expense_data['local_id']).first()
                    if existing_expense:
                        print(f"Found existing expense by local_id: {existing_expense.id}")

                if existing_expense:
                    # Update existing expense
                    expense_serializer = DeliveryExpenseSerializer(existing_expense, data=mapped_expense_data, partial=True)
                    if expense_serializer.is_valid():
                        expense_serializer.save(sync_status='synced')
                        print(f"Successfully updated expense: {existing_expense.id}")
                    else:
                        print(f"Validation errors updating expense: {expense_serializer.errors}")
                        print(f"Data received: {mapped_expense_data}")
                        # Continue processing other expenses instead of failing the whole request
                        continue
                else:
                    # Create new expense
                    expense_serializer = DeliveryExpenseSerializer(data=mapped_expense_data)
                    if expense_serializer.is_valid():
                        expense_serializer.save(sync_status='synced')
                        print(f"Successfully created expense: {expense_serializer.data}")
                    else:
                        print(f"Validation errors creating expense: {expense_serializer.errors}")
                        print(f"Data received: {mapped_expense_data}")
                        # Continue processing other expenses instead of failing the whole request
                        continue

        else:
            print("Expenses not provided in the request data.")

        # Process denominations
        if 'denominations' in serializer.validated_data:
            # The denominations data is a list of lists, where each inner list contains denomination objects for a delivery order
            denominations_data = serializer.validated_data['denominations']
            print(f"Processing denominations: {denominations_data}")

            # If we have a list of lists, flatten it
            if isinstance(denominations_data, list) and all(isinstance(item, list) for item in denominations_data):
                # Flatten the list of lists
                flattened_denominations = []
                for denomination_group in denominations_data:
                    flattened_denominations.extend(denomination_group)
                denominations_data = flattened_denominations

            # Store successfully processed delivery orders for later use
            processed_delivery_orders = []
            if 'delivery_orders' in serializer.validated_data and serializer.validated_data['delivery_orders']:
                for order in serializer.validated_data['delivery_orders']:
                    if hasattr(order, 'id'):
                        processed_delivery_orders.append(order)

            # Process each denomination
            for denomination_data in denominations_data:
                # Try to find the delivery order from the local_id
                delivery_order_id = None

                # First, check if delivery_order is already set
                if 'delivery_order' in denomination_data and denomination_data['delivery_order']:
                    # Check if delivery_order is an object or an ID
                    if isinstance(denomination_data['delivery_order'], DeliveryOrder):
                        # It's a DeliveryOrder object, get its ID
                        delivery_order = denomination_data['delivery_order']
                        delivery_order_id = delivery_order.id
                        # Replace the object with the ID
                        denomination_data['delivery_order'] = delivery_order_id
                        print(f"Using provided delivery_order object: {delivery_order_id}")
                    else:
                        # It's an ID (or should be), verify it exists
                        try:
                            delivery_order = DeliveryOrder.objects.get(id=denomination_data['delivery_order'])
                            delivery_order_id = delivery_order.id
                            print(f"Using provided delivery_order ID: {delivery_order_id}")
                        except (DeliveryOrder.DoesNotExist, ValueError, TypeError):
                            print(f"Provided delivery_order {denomination_data['delivery_order']} does not exist or is invalid")
                            # Set to None to avoid validation errors
                            denomination_data['delivery_order'] = None

                # Check if we have a delivery_order_local_id
                if not delivery_order_id and 'delivery_order_local_id' in denomination_data:
                    # Find the delivery order with this local_id
                    matching_order = DeliveryOrder.objects.filter(local_id=denomination_data['delivery_order_local_id']).first()
                    if matching_order:
                        delivery_order_id = matching_order.id
                        print(f"Found delivery order from delivery_order_local_id: {delivery_order_id}")
                        # Remove the temporary field
                        del denomination_data['delivery_order_local_id']

                # Try to extract from denomination local_id
                if not delivery_order_id and 'local_id' in denomination_data:
                    # Extract delivery order ID from local_id (format: mobile-den-{timestamp}-{denomination})
                    local_id_parts = denomination_data.get('local_id', '').split('-')
                    if len(local_id_parts) >= 3:
                        timestamp = local_id_parts[2]
                        # Find delivery order with matching local_id timestamp
                        matching_orders = DeliveryOrder.objects.filter(local_id__contains=timestamp)
                        if matching_orders.exists():
                            delivery_order_id = matching_orders.first().id
                            print(f"Found delivery order from local_id timestamp: {delivery_order_id}")

                # If we couldn't find a matching delivery order, use the first one from the processed delivery orders
                if not delivery_order_id and processed_delivery_orders:
                    delivery_order_id = processed_delivery_orders[0].id
                    print(f"Using first processed delivery order: {delivery_order_id}")

                # If we still don't have a delivery order, try to find one in the database
                if not delivery_order_id:
                    # Try to find any delivery order for the current date
                    today = timezone.now().date()
                    recent_order = DeliveryOrder.objects.filter(delivery_date=today).order_by('-created_at').first()
                    if recent_order:
                        delivery_order_id = recent_order.id
                        print(f"Using recent delivery order: {delivery_order_id}")
                    else:
                        # Last resort: use any delivery order
                        first_order = DeliveryOrder.objects.order_by('-created_at').first()
                        if first_order:
                            delivery_order_id = first_order.id
                            print(f"Using first available delivery order: {delivery_order_id}")
                        else:
                            print("No delivery orders found for denominations")
                            # Set to None and add route and delivery_date instead
                            denomination_data['delivery_order'] = None
                            # Try to get route and date from the first delivery order in the payload
                            if 'delivery_orders' in serializer.validated_data and serializer.validated_data['delivery_orders']:
                                first_order_data = serializer.validated_data['delivery_orders'][0]
                                if 'route' in first_order_data:
                                    denomination_data['route'] = first_order_data['route']
                                if 'delivery_date' in first_order_data:
                                    denomination_data['delivery_date'] = first_order_data['delivery_date']
                            continue

                # Add delivery_order to the data if we found one
                if delivery_order_id:
                    denomination_data['delivery_order'] = delivery_order_id
                else:
                    # Set to None to avoid validation errors
                    denomination_data['delivery_order'] = None
                    # Try to get route and date from the first delivery order in the payload
                    if 'delivery_orders' in serializer.validated_data and serializer.validated_data['delivery_orders']:
                        first_order_data = serializer.validated_data['delivery_orders'][0]
                        if 'route' in first_order_data:
                            denomination_data['route'] = first_order_data['route']
                        if 'delivery_date' in first_order_data:
                            denomination_data['delivery_date'] = first_order_data['delivery_date']

                print(f"Processing denomination: {denomination_data}")

                # Check if this denomination already exists by local_id
                existing_denomination = None
                if 'local_id' in denomination_data and denomination_data['local_id']:
                    existing_denomination = CashDenomination.objects.filter(local_id=denomination_data['local_id']).first()
                    if existing_denomination:
                        print(f"Found existing denomination by local_id: {existing_denomination.id}")

                if existing_denomination:
                    # Update existing denomination
                    denomination_serializer = CashDenominationSerializer(existing_denomination, data=denomination_data, partial=True)
                    if denomination_serializer.is_valid():
                        denomination_serializer.save(sync_status='synced')
                        print(f"Successfully updated denomination: {existing_denomination.id}")
                    else:
                        print(f"Validation errors updating denomination: {denomination_serializer.errors}")
                        print(f"Data received: {denomination_data}")
                        # Continue processing other denominations instead of failing the whole request
                        continue
                else:
                    # Create new denomination
                    denomination_serializer = CashDenominationSerializer(data=denomination_data)
                    if denomination_serializer.is_valid():
                        denomination_serializer.save(sync_status='synced')
                        print(f"Successfully created denomination")
                    else:
                        print(f"Validation errors creating denomination: {denomination_serializer.errors}")
                        print(f"Data received: {denomination_data}")
                        # Continue processing other denominations instead of failing the whole request
                        continue
        else:
            print("Denominations not provided in the request data.")

        # Process payments
        # Commented out until Payment model is implemented
        # if 'payments' in serializer.validated_data:
        #     for payment_data in serializer.validated_data['payments']:
        #         payment_serializer = PaymentSerializer(data=payment_data)
        #         if payment_serializer.is_valid():
        #             payment_serializer.save(sync_status='synced')
        #         else:
        #             return Response(payment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Update last sync time for the user
            request.user.profile.last_sync = timezone.now()
            request.user.profile.save()

            return Response({'status': 'success', 'message': 'Data synchronized successfully'}, status=status.HTTP_200_OK)



@method_decorator(csrf_exempt, name='dispatch')
class SyncStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Count pending sync records
        pending_delivery = DeliveryOrder.objects.filter(sync_status='pending').count()
        pending_returned = ReturnedOrder.objects.filter(sync_status='pending').count()
        pending_broken = BrokenOrder.objects.filter(sync_status='pending').count()
        pending_sales = PublicSale.objects.filter(sync_status='pending').count()
        pending_expenses = DeliveryExpense.objects.filter(sync_status='pending').count()
        pending_denominations = CashDenomination.objects.filter(sync_status='pending').count()
        # pending_payments = Payment.objects.filter(sync_status='pending').count()
        pending_payments = 0  # Placeholder until Payment model is implemented

        total_pending = pending_delivery + pending_returned + pending_broken + pending_sales + pending_expenses + pending_denominations + pending_payments

        # Get last sync time
        last_sync = request.user.profile.last_sync if hasattr(request.user, 'profile') else None

        # Determine sync status
        sync_status = 'up_to_date' if total_pending == 0 else 'pending'

        data = {
            'last_sync': last_sync,
            'pending_count': {
                'delivery_orders': pending_delivery,
                'returned_orders': pending_returned,
                'broken_orders': pending_broken,
                'public_sales': pending_sales,
                'expenses': pending_expenses,
                'denominations': pending_denominations,
                'payments': pending_payments,
                'total': total_pending
            },
            'sync_status': sync_status
        }

        serializer = SyncStatusSerializer(data)
        return Response(serializer.data)

# @login_required
# def check_purchase_order(request):
#     route_id = request.GET.get('route')
#     delivery_date = request.GET.get('delivery_date')

#     try:
#         purchase_order = PurchaseOrder.objects.filter(
#             route_id=route_id,
#             delivery_date=delivery_date,
#             # status='confirmed'  # Only confirmed purchase orders
#         ).prefetch_related('items__product').first()

#         if purchase_order:
#             items_data = [{
#                 'product_name': f"{item.product.code} - {item.product.name}",
#                 'total_quantity': str(item.total_quantity),
#                 'remaining_quantity': str(item.remaining_quantity)
#             } for item in purchase_order.items.all()]

#             return JsonResponse({
#                 'exists': True,
#                 'purchase_order_id': purchase_order.id,
#                 'items': items_data
#             })

#         return JsonResponse({'exists': False})

#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=400)

class CheckPurchaseOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        route_id = request.query_params.get('route')
        delivery_date = request.query_params.get('delivery_date')

        try:
            # Get first matching purchase order with related items
            purchase_order = PurchaseOrder.objects.filter(
                route_id=route_id,
                delivery_date=delivery_date
            ).prefetch_related('items__product').first()

            if purchase_order:
                # Serialize items data
                items_data = [{
                    'product_name': f"{item.product.code} - {item.product.name}",
                    'total_quantity': str(item.total_quantity),
                    'remaining_quantity': str(item.remaining_quantity)
                } for item in purchase_order.items.all()]

                return Response({
                    'exists': True,
                    'purchase_order_id': purchase_order.id,
                    'items': items_data
                })

            return Response({'exists': False})

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class CheckLoadingOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        route_id = request.query_params.get('route')
        delivery_date = request.query_params.get('delivery_date')

        try:
            # Get first matching purchase order with related items
            loading_order = LoadingOrder.objects.filter(
                route_id=route_id,
                loading_date=delivery_date
            ).prefetch_related('items__product').first()

            if loading_order:
                data = LoadingOrderSerializer(loading_order)
                return Response(data.data)


            return Response({'exists': False})

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CreateLoadingOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        required_fields = [
            'purchase_order_id',
            'route',
            'loading_date',
            'loading_time'
        ]

        # Validate required fields
        missing_fields = [field for field in required_fields if field not in request.data]
        if missing_fields:
            return Response(
                {'success': False, 'error': f'Missing fields: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get and validate purchase order
            purchase_order = PurchaseOrder.objects.get(id=request.data['purchase_order_id'])

            # Check for existing loading order
            if LoadingOrder.objects.filter(
                purchase_order=purchase_order,
                loading_date=request.data['loading_date']
            ).exists():
                return Response({
                    'success': False,
                    'error': 'Loading order already exists for this date'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create loading order
            loading_order = LoadingOrder.objects.create(
                purchase_order=purchase_order,
                route_id=request.data['route'],
                loading_date=request.data['loading_date'],
                loading_time=request.data['loading_time'],
                crates_loaded=request.data.get('crates_loaded', 0),
                notes=request.data.get('notes', ''),
                status='draft',
                created_by=request.user,
                updated_by=request.user
            )

            # Create loading order items
            items = []
            for po_item in purchase_order.items.all():
                items.append(LoadingOrderItem(
                    loading_order=loading_order,
                    product=po_item.product,
                    purchase_order_quantity=po_item.total_quantity,
                    loaded_quantity=po_item.total_quantity,
                    total_quantity=po_item.total_quantity,
                    remaining_quantity=po_item.total_quantity
                ))

            LoadingOrderItem.objects.bulk_create(items)
            serializer_class = LoadingOrderSerializer(loading_order)
            return Response({
                'success': True,
                'message': 'Loading order created successfully',
                'order_number': loading_order.order_number,
                'loading_order_id': loading_order.id,
                'loading_order': serializer_class.data
            }, status=status.HTTP_201_CREATED)

        except PurchaseOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Purchase order not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)