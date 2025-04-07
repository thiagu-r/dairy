from rest_framework import serializers
from django.contrib.auth.models import User
from apps.delivery.models import (
    Seller, 
    Product, 
    Route, 
    SalesOrder, 
    SalesOrderItem,
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
    Payment,
    PricePlan,
    PricePlanItem
)

# Authentication Serializers
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=128, write_only=True)

# Master Data Serializers
class PricePlanItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricePlanItem
        fields = ('id', 'product', 'price')

class PricePlanSerializer(serializers.ModelSerializer):
    items = PricePlanItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = PricePlan
        fields = ('id', 'name', 'is_general', 'items')

class SellerSerializer(serializers.ModelSerializer):
    price_plan = PricePlanSerializer(read_only=True)
    
    class Meta:
        model = Seller
        fields = ('id', 'store_name', 'owner_name', 'phone', 'address', 'route', 'price_plan')

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'code', 'name', 'description', 'price', 'is_active')

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ('id', 'name', 'description')

# Order Serializers
class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = SalesOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price')

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)
    seller_name = serializers.ReadOnlyField(source='seller.store_name')
    
    class Meta:
        model = SalesOrder
        fields = ('id', 'order_number', 'seller', 'seller_name', 'order_date', 'total_price', 'status', 'items')

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = PurchaseOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price')

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ('id', 'order_number', 'order_date', 'total_price', 'status', 'items')

class LoadingOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = LoadingOrderItem
        fields = ('id', 'product', 'product_name', 'quantity')

class LoadingOrderSerializer(serializers.ModelSerializer):
    items = LoadingOrderItemSerializer(many=True, read_only=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    
    class Meta:
        model = LoadingOrder
        fields = ('id', 'order_number', 'route', 'route_name', 'loading_date', 'status', 'items')

# Delivery Operation Serializers
class DeliveryOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = DeliveryOrderItem
        fields = ('id', 'product', 'product_name', 'ordered_quantity', 'extra_quantity', 'delivered_quantity', 'unit_price', 'total_price')

class DeliveryOrderSerializer(serializers.ModelSerializer):
    items = DeliveryOrderItemSerializer(many=True)
    seller_name = serializers.ReadOnlyField(source='seller.store_name')
    route_name = serializers.ReadOnlyField(source='route.name')
    
    class Meta:
        model = DeliveryOrder
        fields = ('id', 'order_number', 'seller', 'seller_name', 'route', 'route_name', 'delivery_date', 
                  'delivery_time', 'total_price', 'opening_balance', 'amount_collected', 'balance_amount', 
                  'payment_method', 'status', 'notes', 'items', 'sync_status')
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        delivery_order = DeliveryOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            DeliveryOrderItem.objects.create(delivery_order=delivery_order, **item_data)
        
        return delivery_order

class ReturnedOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = ReturnedOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'reason')

class ReturnedOrderSerializer(serializers.ModelSerializer):
    items = ReturnedOrderItemSerializer(many=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    
    class Meta:
        model = ReturnedOrder
        fields = ('id', 'order_number', 'route', 'route_name', 'return_date', 'status', 'notes', 'items', 'sync_status')
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        returned_order = ReturnedOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            ReturnedOrderItem.objects.create(returned_order=returned_order, **item_data)
        
        return returned_order

class BrokenOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = BrokenOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'reason')

class BrokenOrderSerializer(serializers.ModelSerializer):
    items = BrokenOrderItemSerializer(many=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    
    class Meta:
        model = BrokenOrder
        fields = ('id', 'order_number', 'route', 'route_name', 'broken_date', 'status', 'notes', 'items', 'sync_status')
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        broken_order = BrokenOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            BrokenOrderItem.objects.create(broken_order=broken_order, **item_data)
        
        return broken_order

class PublicSaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = PublicSaleItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price')

class PublicSaleSerializer(serializers.ModelSerializer):
    items = PublicSaleItemSerializer(many=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    
    class Meta:
        model = PublicSale
        fields = ('id', 'sale_number', 'route', 'route_name', 'sale_date', 'total_price', 'payment_method', 'status', 'notes', 'items', 'sync_status')
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        public_sale = PublicSale.objects.create(**validated_data)
        
        for item_data in items_data:
            PublicSaleItem.objects.create(public_sale=public_sale, **item_data)
        
        return public_sale

class PaymentSerializer(serializers.ModelSerializer):
    seller_name = serializers.ReadOnlyField(source='seller.store_name')
    
    class Meta:
        model = Payment
        fields = ('id', 'payment_number', 'seller', 'seller_name', 'payment_date', 'amount', 'payment_method', 'reference_number', 'notes', 'sync_status')

# Sync Serializers
class SyncDataSerializer(serializers.Serializer):
    delivery_orders = DeliveryOrderSerializer(many=True, required=False)
    returned_orders = ReturnedOrderSerializer(many=True, required=False)
    broken_orders = BrokenOrderSerializer(many=True, required=False)
    public_sales = PublicSaleSerializer(many=True, required=False)
    payments = PaymentSerializer(many=True, required=False)

class SyncStatusSerializer(serializers.Serializer):
    last_sync = serializers.DateTimeField()
    pending_sync_count = serializers.IntegerField()
    sync_status = serializers.CharField()
