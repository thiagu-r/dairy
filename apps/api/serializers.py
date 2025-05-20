from rest_framework import serializers
# from django.contrib.auth.models import User
from apps.authentication.models import CustomUser as User
from apps.seller.models import Seller, Route
from apps.products.models import Product, PricePlan, ProductPrice, Category
from apps.sales.models import SalesOrder, OrderItem as SalesOrderItem
from datetime import datetime
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
# Authentication Serializers
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'password', 'mobile_number')
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

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
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_amount')

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True)
    seller_name = serializers.ReadOnlyField(source='seller.store_name')
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = SalesOrder
        fields = ('id', 'order_number', 'seller', 'seller_name', 'delivery_date', 'total_amount', 'status', 'items')

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
    unit_price = serializers.SerializerMethodField()

    class Meta:
        model = LoadingOrderItem
        fields = ('id', 'product', 'product_name', 'purchase_order_quantity', 'loaded_quantity', 'remaining_quantity','delivered_quantity','total_quantity', 'return_quantity', 'unit_price')

    def get_unit_price(self, obj):
        """Get the unit price from the general price plan"""
        from apps.products.models import PricePlan, ProductPrice
        from decimal import Decimal

        # Get the loading date from the loading order
        loading_date = obj.loading_order.loading_date

        # Find the active general price plan for this date
        general_price_plan = PricePlan.objects.filter(
            is_general=True,
            is_active=True,
            valid_from__lte=loading_date,
            valid_to__gte=loading_date
        ).first()

        if general_price_plan:
            # Get the price for this product from the general price plan
            product_price = ProductPrice.objects.filter(
                price_plan=general_price_plan,
                product=obj.product
            ).first()

            if product_price:
                return str(product_price.price)

        # Default to 0 if no price found
        return str(Decimal('0.00'))

class LoadingOrderSerializer(serializers.ModelSerializer):
    items = LoadingOrderItemSerializer(many=True, read_only=True)
    route_name = serializers.ReadOnlyField(source='route.name')

    class Meta:
        model = LoadingOrder
        fields = ('id', 'order_number', 'route', 'route_name', 'loading_date', 'status', 'items', 'crates_loaded', 'loading_time')

# Delivery Operation Serializers
class DeliveryOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    ordered_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    extra_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivered_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = DeliveryOrderItem
        fields = ('id', 'product', 'product_name', 'ordered_quantity', 'extra_quantity', 'delivered_quantity', 'unit_price', 'total_price')

class DeliveryOrderSerializer(serializers.ModelSerializer):
    items = DeliveryOrderItemSerializer(many=True, required=False)
    seller_name = serializers.ReadOnlyField(source='seller.store_name')
    route_name = serializers.ReadOnlyField(source='route.name')
    route = serializers.PrimaryKeyRelatedField(queryset=Route.objects.all())
    seller = serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all())
    # Make sales_order optional for mobile app sync
    sales_order = serializers.PrimaryKeyRelatedField(queryset=SalesOrder.objects.all(), required=False)

    class Meta:
        model = DeliveryOrder
        fields = ('id', 'order_number', 'seller', 'seller_name', 'route', 'route_name', 'delivery_date',
                  'delivery_time', 'actual_delivery_date', 'actual_delivery_time', 'total_price',
                  'opening_balance', 'amount_collected', 'balance_amount', 'payment_method',
                  'status', 'notes', 'items', 'sync_status', 'local_id', 'sales_order')

    def create(self, validated_data):
        items_data = validated_data.pop('items')

        # Handle missing sales_order for mobile app sync
        if 'sales_order' not in validated_data:
            # Try to find a sales order for this seller and route
            seller = validated_data.get('seller')
            route = validated_data.get('route')
            delivery_date = validated_data.get('delivery_date')

            if seller and route and delivery_date:
                # Look for a sales order for this seller
                sales_order = SalesOrder.objects.filter(
                    seller=seller,
                    route=route,
                    delivery_date__lte=delivery_date
                ).order_by('-delivery_date').first()

                if sales_order:
                    validated_data['sales_order'] = sales_order
                else:
                    # If no sales order exists, create a dummy one
                    from django.utils import timezone
                    sales_order = SalesOrder.objects.create(
                        seller=seller,
                        route=route,
                        delivery_date=delivery_date,
                        status='completed',
                        created_by=validated_data.get('created_by'),
                        updated_by=validated_data.get('updated_by')
                    )
                    validated_data['sales_order'] = sales_order

        delivery_order = DeliveryOrder.objects.create(**validated_data)

        for item_data in items_data:
            DeliveryOrderItem.objects.create(delivery_order=delivery_order, **item_data)

        return delivery_order

    def update(self, instance, validated_data):
        # Handle items separately
        items_data = validated_data.pop('items', [])

        # Update the delivery order fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If items are provided, update them
        if items_data:
            # Clear existing items if we're replacing them
            # instance.items.all().delete()

            # Create new items
            for item_data in items_data:
                # Try to find existing item by product
                if 'product' in item_data:
                    existing_item = instance.items.filter(product=item_data['product']).first()
                    if existing_item:
                        # Update existing item
                        for attr, value in item_data.items():
                            setattr(existing_item, attr, value)
                        existing_item.save()
                    else:
                        # Create new item
                        DeliveryOrderItem.objects.create(delivery_order=instance, **item_data)
                else:
                    # Create new item if no product to match on
                    DeliveryOrderItem.objects.create(delivery_order=instance, **item_data)

        return instance

class ReturnedOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = ReturnedOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'reason')

class ReturnedOrderSerializer(serializers.ModelSerializer):
    items = ReturnedOrderItemSerializer(many=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    route = serializers.PrimaryKeyRelatedField(queryset=Route.objects.all())

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
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    # Make reason optional for mobile app sync
    reason = serializers.CharField(required=False, allow_blank=True, default='')
    # Rename broken_quantity to quantity if needed
    broken_quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, source='quantity')

    class Meta:
        model = BrokenOrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'broken_quantity', 'reason')

class BrokenOrderSerializer(serializers.ModelSerializer):
    items = BrokenOrderItemSerializer(many=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    route = serializers.PrimaryKeyRelatedField(queryset=Route.objects.all())
    # Use report_date instead of broken_date to match the model
    # Also make loading_order optional for mobile app sync
    loading_order = serializers.PrimaryKeyRelatedField(queryset=LoadingOrder.objects.all(), required=False, allow_null=True)
    # Add status field with default value
    status = serializers.CharField(default='pending', required=False)
    # Add sync_status field with default value
    sync_status = serializers.CharField(default='pending', required=False)
    # Add local_id field
    local_id = serializers.CharField(required=False, allow_null=True)
    # Make report_time optional
    report_time = serializers.TimeField(required=False)
    # Make report_date optional with a default value
    report_date = serializers.DateField(required=False, default=datetime.now().date)
    # Make order_number optional
    order_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = BrokenOrder
        fields = ('id', 'order_number', 'route', 'route_name', 'report_date', 'report_time', 'loading_order', 'status', 'notes', 'items', 'sync_status', 'local_id')

    def validate(self, data):
        # If report_date is not provided, use today's date
        if 'report_date' not in data or data['report_date'] is None:
            data['report_date'] = datetime.now().date()

        # If report_time is not provided, use current time
        if 'report_time' not in data or data['report_time'] is None:
            data['report_time'] = datetime.now().time()

        # If order_number is not provided, generate one
        if 'order_number' not in data or not data['order_number']:
            today = datetime.now().strftime('%Y%m%d')
            count = BrokenOrder.objects.filter(order_number__contains=f"BO-{today}").count() + 1
            data['order_number'] = f"BO-{today}-{count:04d}"

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        broken_order = BrokenOrder.objects.create(**validated_data)

        for item_data in items_data:
            BrokenOrderItem.objects.create(broken_order=broken_order, **item_data)

        return broken_order

class PublicSaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = PublicSaleItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price')

class PublicSaleSerializer(serializers.ModelSerializer):
    items = PublicSaleItemSerializer(many=True)
    route_name = serializers.ReadOnlyField(source='route.name')
    route = serializers.PrimaryKeyRelatedField(queryset=Route.objects.all())

    class Meta:
        model = PublicSale
        fields = ('id', 'sale_number', 'route', 'route_name', 'sale_date', 'sale_time', 'customer_name', 'customer_phone', 'customer_address', 'total_price', 'amount_collected', 'balance_amount', 'payment_method', 'status', 'notes', 'items', 'sync_status', 'local_id')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        public_sale = PublicSale.objects.create(**validated_data)

        for item_data in items_data:
            PublicSaleItem.objects.create(public_sale=public_sale, **item_data)

        return public_sale

class DeliveryExpenseSerializer(serializers.ModelSerializer):
    delivery_team_name = serializers.ReadOnlyField(source='delivery_team.name')
    delivery_team = serializers.PrimaryKeyRelatedField(queryset=DeliveryTeam.objects.all())

    class Meta:
        model = DeliveryExpense
        fields = ('id', 'delivery_team', 'delivery_team_name', 'expense_date', 'expense_type',
                  'amount', 'notes', 'created_by', 'sync_status', 'local_id')

    def create(self, validated_data):
        expense = DeliveryExpense.objects.create(**validated_data)
        return expense

class CashDenominationSerializer(serializers.ModelSerializer):
    delivery_order = serializers.PrimaryKeyRelatedField(queryset=DeliveryOrder.objects.all(), required=False, allow_null=True)
    route = serializers.PrimaryKeyRelatedField(queryset=Route.objects.all(), required=False, allow_null=True)
    delivery_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CashDenomination
        fields = ('id', 'delivery_order', 'route', 'delivery_date', 'denomination', 'count', 'total_amount', 'sync_status', 'local_id')

    def create(self, validated_data):
        denomination = CashDenomination.objects.create(**validated_data)
        return denomination

# Sync Serializers
class SyncDataSerializer(serializers.Serializer):
    delivery_orders = DeliveryOrderSerializer(many=True, required=False)
    returned_orders = ReturnedOrderSerializer(many=True, required=False)
    broken_orders = BrokenOrderSerializer(many=True, required=False)
    public_sales = PublicSaleSerializer(many=True, required=False)
    expenses = DeliveryExpenseSerializer(many=True, required=False)
    denominations = CashDenominationSerializer(many=True, required=False)

class PendingCountSerializer(serializers.Serializer):
    delivery_orders = serializers.IntegerField()
    returned_orders = serializers.IntegerField()
    broken_orders = serializers.IntegerField()
    public_sales = serializers.IntegerField()
    expenses = serializers.IntegerField()
    denominations = serializers.IntegerField()
    payments = serializers.IntegerField()
    total = serializers.IntegerField()

class SyncStatusSerializer(serializers.Serializer):
    last_sync = serializers.DateTimeField()
    pending_count = PendingCountSerializer()
    sync_status = serializers.CharField()

# New V2 Serializers for simplified payload
class PublicSaleItemV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = PublicSaleItem
        fields = ('product', 'quantity', 'unit_price', 'total_price')

class PublicSaleV2Serializer(serializers.ModelSerializer):
    items = PublicSaleItemV2Serializer(many=True)
    
    class Meta:
        model = PublicSale
        fields = ('payment_method', 'customer_name', 'customer_phone', 'customer_address',
                 'total_price', 'amount_collected', 'balance_amount', 'status', 'notes',
                 'local_id', 'items')

class DeliveryOrderItemV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOrderItem
        fields = ('id', 'product', 'product_name', 'ordered_quantity', 'extra_quantity',
                 'delivered_quantity', 'unit_price', 'total_price')

class DeliveryOrderV2Serializer(serializers.ModelSerializer):
    items = DeliveryOrderItemV2Serializer(many=True)
    
    class Meta:
        model = DeliveryOrder
        fields = ('id', 'order_number', 'delivery_date', 'route', 'route_name',
                 'seller_name', 'status', 'seller', 'delivery_time', 'total_price',
                 'opening_balance', 'amount_collected', 'balance_amount', 'payment_method',
                 'notes', 'sync_status', 'actual_delivery_date', 'actual_delivery_time',
                 'local_id', 'items')

class BrokenOrderItemV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = BrokenOrderItem
        fields = ('product', 'quantity')

class BrokenOrderV2Serializer(serializers.ModelSerializer):
    items = BrokenOrderItemV2Serializer(many=True)
    
    class Meta:
        model = BrokenOrder
        fields = ('status', 'sync_status', 'local_id', 'items')

class ReturnOrderItemV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnedOrderItem
        fields = ('product', 'quantity')

class ReturnOrderV2Serializer(serializers.ModelSerializer):
    items = ReturnOrderItemV2Serializer(many=True)
    
    class Meta:
        model = ReturnedOrder
        fields = ('sync_status', 'local_id', 'items')

class ExpenseV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryExpense
        fields = ('description', 'amount', 'expense_type', 'local_id')

class DenominationV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = CashDenomination
        fields = ('denomination', 'count', 'total_amount', 'local_id')

class LoadingOrderReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField()

class SyncDataV2Serializer(serializers.Serializer):
    public_sales = PublicSaleV2Serializer(many=True, required=False)
    delivery_orders = DeliveryOrderV2Serializer(many=True, required=False)
    broken_orders = BrokenOrderV2Serializer(many=True, required=False)
    return_orders = ReturnOrderV2Serializer(many=True, required=False)
    expenses = ExpenseV2Serializer(many=True, required=False)
    denominations = DenominationV2Serializer(many=True, required=False)
    loading_order = LoadingOrderReferenceSerializer(required=True)

    def create(self, validated_data):
        loading_order = LoadingOrder.objects.get(id=validated_data['loading_order']['id'])
        delivery_order = validated_data.get('delivery_orders', [{}])[0]
        route = delivery_order.get('route')
        delivery_date = delivery_order.get('delivery_date')
        delivery_team = loading_order.purchase_order.delivery_team

        # Process delivery orders first to get reference data
        for order_data in validated_data.get('delivery_orders', []):
            if 'id' in order_data:
                try:
                    delivery_order = DeliveryOrder.objects.get(id=order_data['id'])
                    # Update existing delivery order
                    for attr, value in order_data.items():
                        if attr != 'items':
                            setattr(delivery_order, attr, value)
                    delivery_order.save()

                    # Update items
                    delivery_order.items.all().delete()
                    for item_data in order_data.get('items', []):
                        DeliveryOrderItem.objects.create(delivery_order=delivery_order, **item_data)
                except DeliveryOrder.DoesNotExist:
                    continue

        # Process public sales
        for sale_data in validated_data.get('public_sales', []):
            local_id = sale_data.get('local_id')
            sale_data['route'] = route
            sale_data['sale_date'] = delivery_date

            existing_sale = PublicSale.objects.filter(local_id=local_id).first()
            if existing_sale:
                # Update existing sale
                items_data = sale_data.pop('items', [])
                for attr, value in sale_data.items():
                    setattr(existing_sale, attr, value)
                existing_sale.save()

                # Update items
                existing_sale.items.all().delete()
                for item_data in items_data:
                    PublicSaleItem.objects.create(public_sale=existing_sale, **item_data)
            else:
                # Create new sale
                items_data = sale_data.pop('items', [])
                new_sale = PublicSale.objects.create(**sale_data)
                for item_data in items_data:
                    PublicSaleItem.objects.create(public_sale=new_sale, **item_data)

        # Process broken orders
        for order_data in validated_data.get('broken_orders', []):
            local_id = order_data.get('local_id')
            order_data['route'] = route
            order_data['report_date'] = delivery_date

            existing_order = BrokenOrder.objects.filter(local_id=local_id).first()
            if existing_order:
                # Update existing order
                items_data = order_data.pop('items', [])
                for attr, value in order_data.items():
                    setattr(existing_order, attr, value)
                existing_order.save()

                # Update items
                existing_order.items.all().delete()
                for item_data in items_data:
                    BrokenOrderItem.objects.create(broken_order=existing_order, **item_data)
            else:
                # Create new order
                items_data = order_data.pop('items', [])
                new_order = BrokenOrder.objects.create(**order_data)
                for item_data in items_data:
                    BrokenOrderItem.objects.create(broken_order=new_order, **item_data)

        # Process return orders
        for order_data in validated_data.get('return_orders', []):
            local_id = order_data.get('local_id')
            order_data['route'] = route
            order_data['return_date'] = delivery_date

            existing_order = ReturnedOrder.objects.filter(local_id=local_id).first()
            if existing_order:
                # Update existing order
                items_data = order_data.pop('items', [])
                for attr, value in order_data.items():
                    setattr(existing_order, attr, value)
                existing_order.save()

                # Update items
                existing_order.items.all().delete()
                for item_data in items_data:
                    ReturnedOrderItem.objects.create(returned_order=existing_order, **item_data)
            else:
                # Create new order
                items_data = order_data.pop('items', [])
                new_order = ReturnedOrder.objects.create(**order_data)
                for item_data in items_data:
                    ReturnedOrderItem.objects.create(returned_order=new_order, **item_data)

        # Process expenses
        for expense_data in validated_data.get('expenses', []):
            local_id = expense_data.get('local_id')
            expense_data['route'] = route
            expense_data['expense_date'] = delivery_date
            expense_data['delivery_team'] = delivery_team

            existing_expense = DeliveryExpense.objects.filter(local_id=local_id).first()
            if existing_expense:
                for attr, value in expense_data.items():
                    setattr(existing_expense, attr, value)
                existing_expense.save()
            else:
                DeliveryExpense.objects.create(**expense_data)

        # Process denominations
        for denom_data in validated_data.get('denominations', []):
            local_id = denom_data.get('local_id')
            denom_data['route'] = route
            denom_data['delivery_date'] = delivery_date

            existing_denom = CashDenomination.objects.filter(local_id=local_id).first()
            if existing_denom:
                for attr, value in denom_data.items():
                    setattr(existing_denom, attr, value)
                existing_denom.save()
            else:
                CashDenomination.objects.create(**denom_data)

        return validated_data
