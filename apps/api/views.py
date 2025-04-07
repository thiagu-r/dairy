from rest_framework import viewsets, generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from apps.seller.models import Seller, Route
from apps.products.models import Product, PricePlan, ProductPrice
from apps.sales.models import SalesOrder
from apps.delivery.models import (
    PurchaseOrder,
    LoadingOrder,
    DeliveryOrder,
    ReturnedOrder,
    BrokenOrder,
    PublicSale,
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
    LoadingOrderSerializer,
    DeliveryOrderSerializer,
    ReturnedOrderSerializer,
    BrokenOrderSerializer,
    PublicSaleSerializer,
    # PaymentSerializer,
    SyncDataSerializer,
    SyncStatusSerializer
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
class LoginView(ObtainAuthToken):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Delete the token to logout
            request.user.auth_token.delete()
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

class SalesOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SalesOrderFilter
    search_fields = ['order_number', 'seller__store_name']
    ordering_fields = ['order_date', 'seller__store_name']
    ordering = ['-order_date']

class PurchaseOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PurchaseOrderFilter
    search_fields = ['order_number']
    ordering_fields = ['order_date']
    ordering = ['-order_date']

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

# Sync Views
class SyncView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = SyncDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Process delivery orders
        if 'delivery_orders' in serializer.validated_data:
            for order_data in serializer.validated_data['delivery_orders']:
                delivery_serializer = DeliveryOrderSerializer(data=order_data)
                if delivery_serializer.is_valid():
                    delivery_serializer.save(sync_status='synced')
                else:
                    return Response(delivery_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process returned orders
        if 'returned_orders' in serializer.validated_data:
            for order_data in serializer.validated_data['returned_orders']:
                returned_serializer = ReturnedOrderSerializer(data=order_data)
                if returned_serializer.is_valid():
                    returned_serializer.save(sync_status='synced')
                else:
                    return Response(returned_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process broken orders
        if 'broken_orders' in serializer.validated_data:
            for order_data in serializer.validated_data['broken_orders']:
                broken_serializer = BrokenOrderSerializer(data=order_data)
                if broken_serializer.is_valid():
                    broken_serializer.save(sync_status='synced')
                else:
                    return Response(broken_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process public sales
        if 'public_sales' in serializer.validated_data:
            for sale_data in serializer.validated_data['public_sales']:
                sale_serializer = PublicSaleSerializer(data=sale_data)
                if sale_serializer.is_valid():
                    sale_serializer.save(sync_status='synced')
                else:
                    return Response(sale_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process payments
        if 'payments' in serializer.validated_data:
            for payment_data in serializer.validated_data['payments']:
                payment_serializer = PaymentSerializer(data=payment_data)
                if payment_serializer.is_valid():
                    payment_serializer.save(sync_status='synced')
                else:
                    return Response(payment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update last sync time for the user
        request.user.profile.last_sync = timezone.now()
        request.user.profile.save()

        return Response({'status': 'success', 'message': 'Data synchronized successfully'}, status=status.HTTP_200_OK)

class SyncStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Count pending sync records
        pending_delivery = DeliveryOrder.objects.filter(sync_status='pending').count()
        pending_returned = ReturnedOrder.objects.filter(sync_status='pending').count()
        pending_broken = BrokenOrder.objects.filter(sync_status='pending').count()
        pending_sales = PublicSale.objects.filter(sync_status='pending').count()
        pending_payments = Payment.objects.filter(sync_status='pending').count()

        total_pending = pending_delivery + pending_returned + pending_broken + pending_sales + pending_payments

        # Get last sync time
        last_sync = request.user.profile.last_sync if hasattr(request.user, 'profile') else None

        # Determine sync status
        sync_status = 'up_to_date' if total_pending == 0 else 'pending'

        data = {
            'last_sync': last_sync,
            'pending_sync_count': total_pending,
            'sync_status': sync_status
        }

        serializer = SyncStatusSerializer(data)
        return Response(serializer.data)
