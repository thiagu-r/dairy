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
    CashDenomination
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

    @transaction.atomic
    def post(self, request):
        print('Raw data received:', request.data)
        print('Data type:', type(request.data))
        serializer = SyncDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Process delivery orders
        if 'delivery_orders' in serializer.validated_data:
            for order_data in serializer.validated_data['delivery_orders']:
                # Ensure route and seller are primary keys
                if 'route' in order_data and not isinstance(order_data['route'], int):
                    order_data['route'] = order_data['route'].id if hasattr(order_data['route'], 'id') else order_data['route']
                if 'seller' in order_data and not isinstance(order_data['seller'], int):
                    order_data['seller'] = order_data['seller'].id if hasattr(order_data['seller'], 'id') else order_data['seller']

                # Process items to ensure product is a primary key
                if 'items' in order_data:
                    for item in order_data['items']:
                        if 'product' in item and not isinstance(item['product'], int):
                            item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']

                delivery_serializer = DeliveryOrderSerializer(data=order_data)
                if delivery_serializer.is_valid():
                    delivery_serializer.save(sync_status='synced', updated_by=request.user, created_by=request.user)
                else:
                    print(f"Validation errors: {delivery_serializer.errors}")
                    print(f"Data received: {order_data}")
                    return Response(delivery_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process returned orders
        if 'returned_orders' in serializer.validated_data:
            for order_data in serializer.validated_data['returned_orders']:
                # Ensure route is a primary key
                if 'route' in order_data and not isinstance(order_data['route'], int):
                    order_data['route'] = order_data['route'].id if hasattr(order_data['route'], 'id') else order_data['route']

                # Process items to ensure product is a primary key
                if 'items' in order_data:
                    for item in order_data['items']:
                        if 'product' in item and not isinstance(item['product'], int):
                            item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']

                returned_serializer = ReturnedOrderSerializer(data=order_data)
                if returned_serializer.is_valid():
                    returned_serializer.save(sync_status='synced', updated_by=request.user, created_by=request.user)
                else:
                    print(f"Validation errors: {returned_serializer.errors}")
                    print(f"Data received: {order_data}")
                    return Response(returned_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process broken orders
        if 'broken_orders' in serializer.validated_data:
            for order_data in serializer.validated_data['broken_orders']:
                # Ensure route is a primary key
                if 'route' in order_data and not isinstance(order_data['route'], int):
                    order_data['route'] = order_data['route'].id if hasattr(order_data['route'], 'id') else order_data['route']

                # Process items to ensure product is a primary key
                if 'items' in order_data:
                    for item in order_data['items']:
                        if 'product' in item and not isinstance(item['product'], int):
                            item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']

                broken_serializer = BrokenOrderSerializer(data=order_data)
                if broken_serializer.is_valid():
                    broken_serializer.save(sync_status='synced', updated_by=request.user, created_by=request.user)
                else:
                    print(f"Validation errors: {broken_serializer.errors}")
                    print(f"Data received: {order_data}")
                    return Response(broken_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process public sales
        if 'public_sales' in serializer.validated_data:
            for sale_data in serializer.validated_data['public_sales']:
                # Ensure route and product are primary keys
                if 'route' in sale_data and not isinstance(sale_data['route'], int):
                    sale_data['route'] = sale_data['route'].id if hasattr(sale_data['route'], 'id') else sale_data['route']

                # Process items to ensure product is a primary key
                if 'items' in sale_data:
                    for item in sale_data['items']:
                        if 'product' in item and not isinstance(item['product'], int):
                            item['product'] = item['product'].id if hasattr(item['product'], 'id') else item['product']

                sale_serializer = PublicSaleSerializer(data=sale_data)
                if sale_serializer.is_valid():
                    sale_serializer.save(sync_status='synced', updated_by=request.user, created_by=request.user)
                else:
                    # Print detailed error information
                    print(f"Validation errors: {sale_serializer.errors}")
                    print(f"Data received: {sale_data}")
                    return Response(sale_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process expenses
        if 'expenses' in serializer.validated_data:
            for expense_data in serializer.validated_data['expenses']:
                # Ensure delivery_team is a primary key
                if 'delivery_team' in expense_data and not isinstance(expense_data['delivery_team'], int):
                    expense_data['delivery_team'] = expense_data['delivery_team'].id if hasattr(expense_data['delivery_team'], 'id') else expense_data['delivery_team']

                expense_serializer = DeliveryExpenseSerializer(data=expense_data)
                if expense_serializer.is_valid():
                    expense_serializer.save(sync_status='synced', created_by=request.user)
                else:
                    print(f"Validation errors: {expense_serializer.errors}")
                    print(f"Data received: {expense_data}")
                    return Response(expense_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process denominations
        if 'denominations' in serializer.validated_data:
            for denomination_data in serializer.validated_data['denominations']:
                # Ensure delivery_order is a primary key
                if 'delivery_order' in denomination_data and not isinstance(denomination_data['delivery_order'], int):
                    denomination_data['delivery_order'] = denomination_data['delivery_order'].id if hasattr(denomination_data['delivery_order'], 'id') else denomination_data['delivery_order']

                denomination_serializer = CashDenominationSerializer(data=denomination_data)
                if denomination_serializer.is_valid():
                    denomination_serializer.save(sync_status='synced')
                else:
                    print(f"Validation errors: {denomination_serializer.errors}")
                    print(f"Data received: {denomination_data}")
                    return Response(denomination_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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