from rest_framework import serializers
from apps.seller.models import Seller
from apps.sales.models import SalesOrder, OrderItem
from apps.delivery.models import DeliveryOrder
from apps.products.models import Product
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

class SalesAnalyticsSerializer(serializers.Serializer):
    """Serializer for sales analytics data."""
    id = serializers.IntegerField(source='seller_id')
    seller_name = serializers.CharField(source='seller__store_name')
    total_quantity = serializers.DecimalField(max_digits=15, decimal_places=3)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    order_count = serializers.IntegerField()

class ProductSalesAnalyticsSerializer(serializers.Serializer):
    """Serializer for product-based sales analytics data."""
    id = serializers.IntegerField(source='product_id')
    product_name = serializers.CharField(source='product__name')
    total_quantity = serializers.DecimalField(max_digits=15, decimal_places=3)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    order_count = serializers.IntegerField()

class RouteSalesAnalyticsSerializer(serializers.Serializer):
    """Serializer for route-based sales analytics data."""
    id = serializers.IntegerField(source='route_id')
    route_name = serializers.CharField(source='route__name')
    total_quantity = serializers.DecimalField(max_digits=15, decimal_places=3)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    order_count = serializers.IntegerField()

class SellerBalanceSerializer(serializers.Serializer):
    """Serializer for seller balance report."""
    id = serializers.IntegerField()
    store_name = serializers.CharField()
    owner_name = serializers.CharField()
    opening_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Calculate current balance
        data['current_balance'] = data['opening_balance'] + data['total_sales'] - data['total_payments']
        return data

class SalesOrderExportSerializer(serializers.ModelSerializer):
    """Serializer for exporting sales order data."""
    seller_name = serializers.CharField(source='seller.store_name')
    route_name = serializers.CharField(source='seller.route.name')
    
    class Meta:
        model = SalesOrder
        fields = ('id', 'order_number', 'seller_name', 'route_name', 'order_date', 'total_price', 'status')

class OrderItemExportSerializer(serializers.ModelSerializer):
    """Serializer for exporting order item data."""
    order_number = serializers.CharField(source='sales_order.order_number')
    seller_name = serializers.CharField(source='sales_order.seller.store_name')
    product_name = serializers.CharField(source='product.name')
    product_code = serializers.CharField(source='product.code')
    order_date = serializers.DateField(source='sales_order.order_date')
    
    class Meta:
        model = OrderItem
        fields = ('order_number', 'seller_name', 'order_date', 'product_name', 'product_code', 
                  'quantity', 'unit_price', 'total_price')

class SellerBalanceExportSerializer(serializers.Serializer):
    """Serializer for exporting seller balance data."""
    id = serializers.IntegerField()
    store_name = serializers.CharField()
    owner_name = serializers.CharField()
    route_name = serializers.CharField(source='route.name')
    opening_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    last_payment_date = serializers.DateField()
    last_order_date = serializers.DateField()
