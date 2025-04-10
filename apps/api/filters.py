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
    start_date = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    
    class Meta:
        model = SalesOrder
        fields = ['seller', 'route', 'start_date', 'end_date', 'status']

class PurchaseOrderFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')
    
    class Meta:
        model = PurchaseOrder
        fields = ['start_date', 'end_date', 'status']

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
    
    class Meta:
        model = DeliveryOrder
        fields = ['seller', 'route', 'start_date', 'end_date', 'status', 'sync_status']

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
