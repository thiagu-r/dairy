from rest_framework import serializers
# from django.contrib.auth.models import User
from apps.authentication.models import CustomUser as User
from apps.seller.models import Seller, Route
from apps.products.models import Product, PricePlan, ProductPrice, Category
from apps.sales.models import SalesOrder, OrderItem as SalesOrderItem
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
    # Payment
)
# Authentication Serializers
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role')
        read_only_fields = ('id',)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            from django.contrib.auth import authenticate
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)

            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        data['user'] = user
        return data

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'code')

# Master Data Serializers
class ProductPriceSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    # category = CategorySerializer(source='product.category')

    class Meta:
        model = ProductPrice
        fields = ('id', 'product','product_name',  'price')

class PricePlanSerializer(serializers.ModelSerializer):
    product_prices = ProductPriceSerializer(many=True, read_only=True)
    seller_name = serializers.ReadOnlyField(source='seller.store_name')

    class Meta:
        model = PricePlan
        fields = ('id', 'name', 'valid_from', 'valid_to', 'is_general', 'seller', 'seller_name', 'is_active', 'product_prices')

class SellerSerializer(serializers.ModelSerializer):
    price_plans = PricePlanSerializer(many=True, read_only=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    general_price_plan = serializers.SerializerMethodField()
    effective_prices = serializers.SerializerMethodField()

    class Meta:
        model = Seller
        fields = ('id', 'store_name', 'first_name','last_name','mobileno', 'lat','lan', 'store_address', 'route', 'route_name', 'price_plans', 'general_price_plan', 'effective_prices')

    def get_general_price_plan(self, obj):
        # Only include general price plan if seller has no specific price plans
        if not obj.price_plans.exists():
            general_plan = PricePlan.objects.filter(is_general=True, is_active=True).first()
            if general_plan:
                return PricePlanSerializer(general_plan).data
        return None

    def get_effective_prices(self, obj):
        # Create a dictionary to store the effective prices
        effective_prices = {}

        # First, try to get seller-specific prices
        seller_plans = obj.price_plans.filter(is_active=True).order_by('-valid_from')
        if seller_plans.exists():
            # Use the most recent seller-specific plan
            seller_plan = seller_plans.first()
            for price in seller_plan.product_prices.all():
                effective_prices[price.product_id] = {
                    'product_id': price.product_id,
                    'product_name': price.product.name,
                    'price': float(price.price),
                    'source': 'seller_specific'
                }

        # For any products without seller-specific prices, use general prices
        general_plan = PricePlan.objects.filter(is_general=True, is_active=True).first()
        if general_plan:
            for price in general_plan.product_prices.all():
                if price.product_id not in effective_prices:
                    effective_prices[price.product_id] = {
                        'product_id': price.product_id,
                        'product_name': price.product.name,
                        'price': float(price.price),
                        'source': 'general'
                    }

        # Convert dictionary to list
        return list(effective_prices.values())

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    # prices = ProductPriceSerializer(many=True, read_only=True, source='prices')

    class Meta:
        model = Product
        fields = ('id', 'code', 'name', 'category', 'category_name', 'is_liquid', 'unit_size', 'is_active')

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ('id', 'name', 'code')

# Order Serializers
class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = SalesOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price')

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True)
    seller_name = serializers.ReadOnlyField(source='seller.store_name')

    class Meta:
        model = SalesOrder
        fields = ('id', 'order_number', 'seller', 'seller_name', 'delivery_date', 'total_price', 'status', 'items')

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        sales_order = SalesOrder.objects.create(**validated_data)

        # Create sales order items
        for item_data in items_data:
            SalesOrderItem.objects.create(order=sales_order, **item_data)

        # Update delivery order items
        sales_order.update_delivery_order_items()

        return sales_order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])

        # Update sales order fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Get existing items
        existing_items = {item.id: item for item in instance.items.all()}

        # Update or create items
        for item_data in items_data:
            item_id = item_data.get('id', None)
            if item_id and item_id in existing_items:
                # Update existing item
                item = existing_items.pop(item_id)
                for attr, value in item_data.items():
                    setattr(item, attr, value)
                item.save()
            else:
                # Create new item
                SalesOrderItem.objects.create(order=instance, **item_data)

        # Delete items not included in the update
        for item in existing_items.values():
            item.delete()

        # Update delivery order items
        instance.update_delivery_order_items()

        return instance

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = PurchaseOrderItem
        fields = ('id', 'product', 'product_name', 'sales_order_quantity', 'extra_quantity', 'remaining_quantity', 'total_quantity')

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ('id', 'order_number','route', 'delivery_date', 'notes', 'status', 'items')

class LoadingOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = LoadingOrderItem
        fields = ('id', 'product', 'product_name', 'purchase_order_quantity', 'loaded_quantity', 'remaining_quantity','delivered_quantity','total_quantity', 'return_quantity')

class LoadingOrderSerializer(serializers.ModelSerializer):
    items = LoadingOrderItemSerializer(many=True, read_only=True)
    route_name = serializers.ReadOnlyField(source='route.name')

    class Meta:
        model = LoadingOrder
        fields = ('id', 'order_number', 'route', 'route_name', 'loading_date', 'status', 'items', 'crates_loaded', 'loading_time')

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

# class PaymentSerializer(serializers.ModelSerializer):
#     seller_name = serializers.ReadOnlyField(source='seller.store_name')

#     class Meta:
#         model = Payment
#         fields = ('id', 'payment_number', 'seller', 'seller_name', 'payment_date', 'amount', 'payment_method', 'reference_number', 'notes', 'sync_status')

# Sync Serializers
class SyncDataSerializer(serializers.Serializer):
    delivery_orders = DeliveryOrderSerializer(many=True, required=False)
    returned_orders = ReturnedOrderSerializer(many=True, required=False)
    broken_orders = BrokenOrderSerializer(many=True, required=False)
    public_sales = PublicSaleSerializer(many=True, required=False)
    # payments = PaymentSerializer(many=True, required=False)

class SyncStatusSerializer(serializers.Serializer):
    last_sync = serializers.DateTimeField()
    pending_sync_count = serializers.IntegerField()
    sync_status = serializers.CharField()
