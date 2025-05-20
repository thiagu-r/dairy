import django_filters
from apps.delivery.models import (
    Seller, 
    SalesOrder, 
    PurchaseOrder, 
    LoadingOrder,
    DeliveryOrder, 
    ReturnedOrder, 
    BrokenOrder, 
    PublicSale, 
    # Payment
)

class SellerFilter(django_filters.FilterSet):
    route = django_filters.NumberFilter(field_name='route__id')
    
    class Meta:
        model = Seller
        fields = ['route']

class SalesOrderFilter(django_filters.FilterSet):
    seller = django_filters.NumberFilter(field_name='seller__id')
    route = django_filters.NumberFilter(field_name='seller__route__id')
    route_name = django_filters.CharFilter(field_name='seller__route__name', lookup_expr='icontains')
    seller_store = django_filters.CharFilter(field_name='seller__store_name', lookup_expr='icontains')
    delivery_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='exact')
    start_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    
    class Meta:
        model = SalesOrder
        fields = [
            'seller', 'route', 'route_name', 'seller_store',
            'delivery_date', 'start_date', 'end_date', 'status'
        ]

class PurchaseOrderFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    delivery_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='exact')
    route__name = django_filters.CharFilter(field_name='route__name', lookup_expr='icontains')
    
    class Meta:
        model = PurchaseOrder
        fields = ['start_date', 'end_date', 'status', 'delivery_date', 'route__name']

class LoadingOrderFilter(django_filters.FilterSet):
    route = django_filters.NumberFilter(field_name='route__id')
    start_date = django_filters.DateFilter(field_name='loading_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='loading_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    
    class Meta:
        model = LoadingOrder
        fields = ['route', 'start_date', 'end_date', 'status']

class DeliveryOrderFilter(django_filters.FilterSet):
    seller = django_filters.NumberFilter(field_name='seller__id')
    route = django_filters.NumberFilter(field_name='route__id')
    start_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    sync_status = django_filters.CharFilter(field_name='sync_status')
    delivery_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='exact')
    
    class Meta:
        model = DeliveryOrder
        fields = ['seller', 'route', 'start_date', 'end_date', 'status', 'sync_status','delivery_date']

class ReturnedOrderFilter(django_filters.FilterSet):
    route = django_filters.NumberFilter(field_name='route__id')
    start_date = django_filters.DateFilter(field_name='return_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='return_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    sync_status = django_filters.CharFilter(field_name='sync_status')
    
    class Meta:
        model = ReturnedOrder
        fields = ['route', 'start_date', 'end_date', 'status', 'sync_status']

class BrokenOrderFilter(django_filters.FilterSet):
    route = django_filters.NumberFilter(field_name='route__id')
    start_date = django_filters.DateFilter(field_name='broken_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='broken_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    sync_status = django_filters.CharFilter(field_name='sync_status')
    
    class Meta:
        model = BrokenOrder
        fields = ['route', 'start_date', 'end_date', 'status', 'sync_status']

class PublicSaleFilter(django_filters.FilterSet):
    route = django_filters.NumberFilter(field_name='route__id')
    start_date = django_filters.DateFilter(field_name='sale_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='sale_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    sync_status = django_filters.CharFilter(field_name='sync_status')
    
    class Meta:
        model = PublicSale
        fields = ['route', 'start_date', 'end_date', 'status', 'sync_status']

# class PaymentFilter(django_filters.FilterSet):
#     seller = django_filters.NumberFilter(field_name='seller__id')
#     start_date = django_filters.DateFilter(field_name='payment_date', lookup_expr='gte')
#     end_date = django_filters.DateFilter(field_name='payment_date', lookup_expr='lte')
#     payment_method = django_filters.CharFilter(field_name='payment_method')
#     sync_status = django_filters.CharFilter(field_name='sync_status')
    
#     class Meta:
#         model = Payment
#         fields = ['seller', 'start_date', 'end_date', 'payment_method', 'sync_status']
