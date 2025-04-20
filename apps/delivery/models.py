from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid
from apps.authentication.models import CustomUser
from apps.seller.models import Route, Seller
from apps.products.models import Product
from apps.sales.models import SalesOrder, OrderItem
from apps.products.models import PricePlan, Product

class Distributor(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    contact_person = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text='True if distributor is part of dairy factory'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='distributors_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='distributors_updated'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Distributor'
        verbose_name_plural = 'Distributors'

    def __str__(self):
        return f"{self.name} ({self.code})"

class DeliveryTeam(models.Model):
    name = models.CharField(max_length=100)
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.PROTECT,
        related_name='delivery_teams'
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name='delivery_teams'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['distributor', 'name']
        verbose_name = 'Delivery Team'
        verbose_name_plural = 'Delivery Teams'

    def __str__(self):
        return f"{self.name} - {self.distributor.name} ({self.route.name})"

class DeliveryTeamMember(models.Model):
    ROLE_CHOICES = (
        ('DRIVER', 'Truck Driver'),
        ('SUPERVISOR', 'Sales Supervisor'),
        ('DELIVERY', 'Delivery Man'),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='delivery_team_roles'
    )
    delivery_team = models.ForeignKey(
        DeliveryTeam,
        on_delete=models.PROTECT,
        related_name='team_members'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['delivery_team', 'role']
        verbose_name = 'Delivery Team Member'
        verbose_name_plural = 'Delivery Team Members'
        constraints = [
            models.UniqueConstraint(
                fields=['delivery_team', 'user', 'role'],
                name='unique_team_user_role'
            )
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"

class DailyDeliveryTeam(models.Model):
    delivery_team = models.ForeignKey(
        DeliveryTeam,
        on_delete=models.PROTECT,
        related_name='daily_teams'
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name='daily_teams'
    )
    delivery_date = models.DateField(db_index=True)
    driver = models.ForeignKey(
        DeliveryTeamMember,
        on_delete=models.PROTECT,
        related_name='daily_driver_duties',
        limit_choices_to={'role': 'DRIVER'}
    )
    supervisor = models.ForeignKey(
        DeliveryTeamMember,
        on_delete=models.PROTECT,
        related_name='daily_supervisor_duties',
        limit_choices_to={'role': 'SUPERVISOR'},
        blank=True,
        null=True
    )
    delivery_man = models.ForeignKey(
        DeliveryTeamMember,
        on_delete=models.PROTECT,
        related_name='daily_delivery_duties',
        limit_choices_to={'role': 'DELIVERY'},
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='daily_teams_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='daily_teams_updated'
    )

    class Meta:
        ordering = ['-delivery_date']
        verbose_name = 'Daily Delivery Team'
        verbose_name_plural = 'Daily Delivery Teams'
        constraints = [
            models.UniqueConstraint(
                fields=['delivery_team', 'route', 'delivery_date'],
                name='unique_team_route_date'
            )
        ]

    def __str__(self):
        return f"{self.delivery_team.name} - {self.delivery_date}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Ensure team members belong to the same delivery team
        members = [self.driver, self.supervisor]
        if self.delivery_man:
            members.append(self.delivery_man)

        for member in members:
            if member and member.delivery_team != self.delivery_team:
                raise ValidationError(
                    f"{member.get_role_display()} must belong to {self.delivery_team.name}"
                )

class PurchaseOrder(models.Model):
    ORDER_STATUS = (
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )
    delivery_team = models.ForeignKey(
        DeliveryTeam,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    delivery_date = models.DateField(
        help_text='Date when products will be delivered',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS,
        default='draft'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='purchase_orders_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='purchase_orders_updated'
    )

    class Meta:
        ordering = ['-delivery_date', '-created_at']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        constraints = [
            models.UniqueConstraint(
                fields=['delivery_team', 'route', 'delivery_date'],
                name='unique_team_route_delivery_date'
            )
        ]

    def __str__(self):
        return f"PO {self.order_number} - {self.delivery_team.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: PO-YYYYMMDD-XXXX
            today = timezone.now().date()
            prefix = f"PO-{today.strftime('%Y%m%d')}-"
            last_order = PurchaseOrder.objects.filter(
                order_number__startswith=prefix
            ).order_by('-order_number').first()

            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = str(last_number + 1).zfill(4)
            else:
                new_number = '0001'

            self.order_number = f"{prefix}{new_number}"

        super().save(*args, **kwargs)

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='purchase_order_items'
    )
    sales_order_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Total quantity from sales orders'
    )
    extra_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
        help_text='Additional quantity for public sales'
    )
    remaining_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
        help_text='Remaining quantity from previous day'
    )
    total_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Total quantity to be loaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product__category', 'product__name']
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"{self.product.name} - {self.total_quantity} units"

    def save(self, *args, **kwargs):
        # Calculate total quantity
        self.total_quantity = (
            self.sales_order_quantity +
            self.extra_quantity -
            self.remaining_quantity
        )
        super().save(*args, **kwargs)

class LoadingOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('loaded', 'Loaded'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=20, unique=True)
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.PROTECT,
        related_name='loading_orders'
    )
    route = models.ForeignKey(
        'seller.Route',
        on_delete=models.PROTECT,
        related_name='loading_orders'
    )
    loading_date = models.DateField(db_index=True)
    loading_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, null=True)

    # Track crates
    crates_loaded = models.PositiveIntegerField(
        default=0,
        help_text='Number of crates loaded'
    )

    # Add offline sync fields
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='loading_orders_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='loading_orders_updated'
    )

    class Meta:
        ordering = ['-loading_date', '-loading_time']
        verbose_name = 'Loading Order'
        verbose_name_plural = 'Loading Orders'
        constraints = [
            models.UniqueConstraint(
                fields=['purchase_order', 'route', 'loading_date'],
                name='unique_po_route_loading_date'
            )
        ]

    def __str__(self):
        return f"{self.order_number} - {self.route.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: LO-YYYYMMDD-XXXX
            last_order = LoadingOrder.objects.order_by('-order_number').first()
            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = str(last_number + 1).zfill(4)
            else:
                new_number = '0001'

            from datetime import date
            today = date.today()
            self.order_number = f'LO-{today.strftime("%Y%m%d")}-{new_number}'

        super().save(*args, **kwargs)
        delivery_orders = DeliveryOrder.objects.filter(route=self.route, delivery_date=self.loading_date)
        for delivery_order in delivery_orders:
            delivery_order.loading_order = self
            delivery_order.save()

class LoadingOrderItem(models.Model):
    loading_order = models.ForeignKey(LoadingOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    purchase_order_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    loaded_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    delivered_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    return_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    remaining_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    total_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['loading_order', 'product']

    def save(self, *args, **kwargs):
        # Calculate remaining quantity
        self.remaining_quantity = self.loaded_quantity - self.delivered_quantity - self.return_quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.loaded_quantity} units"

class DeliveryOrder(models.Model):
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_METHOD = (
        ('cash', 'Cash'),
        ('online', 'Online Transfer'),
    )

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    loading_order = models.ForeignKey(
        LoadingOrder,
        on_delete=models.PROTECT,
        related_name='delivery_orders',
        null=True,
        blank=True
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name='delivery_orders'
    )
    seller = models.ForeignKey(
        Seller,
        on_delete=models.PROTECT,
        related_name='delivery_orders'
    )
    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.PROTECT,
        related_name='delivery_orders'
    )
    delivery_date = models.DateField(db_index=True)
    delivery_time = models.TimeField(blank=True, null=True)

    # Actual delivery datetime (when delivery was completed)
    actual_delivery_date = models.DateField(blank=True, null=True)
    actual_delivery_time = models.TimeField(blank=True, null=True)

    # New fields for pricing and payments
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total price for all items in this delivery'
    )
    opening_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Previous balance amount'
    )
    amount_collected = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Amount collected on delivery date'
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD,
        default='cash',
        help_text='Method of payment collection'
    )
    balance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Remaining balance for this delivery'
    )
    total_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total outstanding balance including previous balance'
    )

    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='delivery_orders_created',
        null=True,
        blank=True
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='delivery_orders_updated',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-delivery_date', '-delivery_time']
        verbose_name = 'Delivery Order'
        verbose_name_plural = 'Delivery Orders'
        constraints = [
            models.UniqueConstraint(
                fields=['route', 'seller', 'delivery_date'],
                name='unique_lo_route_seller_delivery_date'
            )
        ]

    def __str__(self):
        return f"DO {self.order_number} - {self.sales_order.seller.store_name}"

    # def save(self, *args, **kwargs):
    #     if not self.pk and not self.opening_balance:  # Only for new orders
    #         # Get last order's total balance for this seller
    #         last_order = DeliveryOrder.objects.filter(
    #             seller=self.seller,
    #             delivery_date__lt=self.delivery_date
    #         ).order_by('-delivery_date', '-delivery_time').first()

    #         self.opening_balance = last_order.total_balance if last_order else Decimal('0.00')

    #     # Calculate total price from items
    #     self.total_price = sum(
    #         item.delivered_quantity * item.product.price
    #         for item in self.items.all()
    #     )

    #     # Calculate balance amount for this delivery
    #     self.balance_amount = self.total_price - self.amount_collected

    #     # Calculate total balance including opening balance
    #     self.total_balance = self.opening_balance + self.balance_amount

    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: DO-YYYYMMDD-XXXX
            today = timezone.now().date()
            prefix = f"DO-{today.strftime('%Y%m%d')}-"
            last_order = DeliveryOrder.objects.filter(
                order_number__startswith=prefix
            ).order_by('-order_number').first()

            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = str(last_number + 1).zfill(4)
            else:
                new_number = '0001'

            self.order_number = f"{prefix}{new_number}"

        # Skip the problematic calculations for now - we'll handle these in the view
        # if not self.pk and not self.opening_balance:  # Only for new orders
        #     # Get last order's total balance for this seller
        #     last_order = DeliveryOrder.objects.filter(
        #         seller=self.seller,
        #         delivery_date__lt=self.delivery_date
        #     ).order_by('-delivery_date', '-delivery_time').first()
        #
        #     self.opening_balance = last_order.total_balance if last_order else Decimal('0.00')

        # # Calculate total price from items
        # self.total_price = sum(
        #     item.delivered_quantity * item.unit_price
        #     for item in self.items.all()
        # )

        # # Calculate balance amount for this delivery
        # self.balance_amount = self.total_price - self.amount_collected

        # # Calculate total balance including opening balance
        # self.total_balance = self.opening_balance + self.balance_amount

        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Recalculate totals after items have been added"""
        if self.pk:  # Only if the order has been saved
            # Calculate total price from items
            self.total_price = sum(
                item.delivered_quantity * item.unit_price
                for item in self.items.all()
            )

            # Calculate balance amount for this delivery
            self.balance_amount = self.total_price - self.amount_collected

            # Calculate total balance including opening balance
            self.total_balance = self.opening_balance + self.balance_amount

            # Save without triggering the full save method
            super().save(update_fields=['total_price', 'balance_amount', 'total_balance'])

class DeliveryOrderItem(models.Model):
    delivery_order = models.ForeignKey(
        DeliveryOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='delivery_order_items'
    )
    ordered_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Quantity from sales order'
    )
    extra_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Additional quantity beyond ordered quantity'
    )
    delivered_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Actually delivered quantity'
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Price per unit for this seller'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total price for delivered quantity'
    )

    # Fields for mobile app sync
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending',
        help_text='Sync status for mobile app'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Temporary ID used by mobile app before sync'
    )
    last_sync_attempt = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last attempted sync timestamp'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product__category', 'product__name']
        indexes = [
            models.Index(fields=['sync_status', 'last_sync_attempt']),
            models.Index(fields=['local_id']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.delivered_quantity} units"

    def save(self, *args, **kwargs):
        # Set unit price from cache if not set
        if not self.unit_price:
            self.unit_price = self.get_cached_price()

        # Calculate total price - only if delivered_quantity > 0
        if self.delivered_quantity > 0:
            self.total_price = self.delivered_quantity * self.unit_price
        else:
            self.total_price = Decimal('0.00')

        super().save(*args, **kwargs)

    def get_cached_price(self):
        """Get price from cached data for offline use"""
        delivery_date = self.delivery_order.delivery_date

        # Try seller-specific cached price
        seller_price = SellerPriceCache.objects.filter(
            seller=self.delivery_order.seller,
            product=self.product,
            valid_from__lte=delivery_date,
            valid_to__gte=delivery_date,
            is_active=True
        ).first()

        if seller_price:
            return seller_price.price

        # Fallback to general cached price
        general_price = GeneralPriceCache.objects.filter(
            product=self.product,
            valid_from__lte=delivery_date,
            valid_to__gte=delivery_date,
            is_active=True
        ).first()

        if general_price:
            return general_price.price

        return Decimal('0.00')

class BrokenOrder(models.Model):
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    loading_order = models.ForeignKey(
        LoadingOrder,
        on_delete=models.PROTECT,
        related_name='broken_orders'
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name='broken_orders'
    )
    report_date = models.DateField(db_index=True)
    report_time = models.TimeField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='broken_orders_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='broken_orders_updated'
    )

    class Meta:
        ordering = ['-report_date', '-report_time']
        verbose_name = 'Broken Order'
        verbose_name_plural = 'Broken Orders'
        constraints = [
            models.UniqueConstraint(
                fields=['loading_order', 'route', 'report_date'],
                name='unique_lo_route_report_date'
            )
        ]

    def __str__(self):
        return f"BO {self.order_number} - {self.loading_order.purchase_order.delivery_team.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: BO-YYYYMMDD-XXXX
            today = timezone.now().date()
            prefix = f"BO-{today.strftime('%Y%m%d')}-"
            last_order = BrokenOrder.objects.filter(
                order_number__startswith=prefix
            ).order_by('-order_number').first()

            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = str(last_number + 1).zfill(4)
            else:
                new_number = '0001'

            self.order_number = f"{prefix}{new_number}"
        super().save(*args, **kwargs)

class BrokenOrderItem(models.Model):
    broken_order = models.ForeignKey(
        BrokenOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='broken_order_items'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Quantity of broken/damaged products'
    )
    reason = models.TextField(help_text='Reason for damage/breakage')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product__category', 'product__name']

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units broken"

class ReturnedOrder(models.Model):
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    delivery_order = models.ForeignKey(
        DeliveryOrder,
        on_delete=models.PROTECT,
        related_name='returned_orders',
        null=True,
        blank=True
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name='returned_orders'
    )
    return_date = models.DateField(db_index=True)
    return_time = models.TimeField(blank=True, null=True)
    reason = models.TextField(help_text='Reason for return')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='returned_orders_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='returned_orders_updated'
    )

    # Add crate tracking
    crates_returned = models.PositiveIntegerField(
        default=0,
        help_text='Number of crates returned'
    )

    # Add offline sync fields
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-return_date', '-return_time']
        verbose_name = 'Returned Order'
        verbose_name_plural = 'Returned Orders'
        constraints = [
            models.UniqueConstraint(
                fields=['delivery_order', 'route', 'return_date'],
                name='unique_do_route_return_date'
            )
        ]

    def __str__(self):
        return f"RO {self.order_number} - {self.loading_order.purchase_order.delivery_team.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: RO-YYYYMMDD-XXXX
            today = timezone.now().date()
            prefix = f"RO-{today.strftime('%Y%m%d')}-"
            last_order = ReturnedOrder.objects.filter(
                order_number__startswith=prefix
            ).order_by('-order_number').first()

            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = str(last_number + 1).zfill(4)
            else:
                new_number = '0001'

            self.order_number = f"{prefix}{new_number}"
        super().save(*args, **kwargs)

class ReturnedOrderItem(models.Model):
    returned_order = models.ForeignKey(
        ReturnedOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='returned_order_items'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Quantity of returned products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product__category', 'product__name']

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units returned"

class DeliverySync(models.Model):
    SYNC_TYPE = (
        ('delivery_order', 'Delivery Order'),
        ('order_item', 'Order Item'),
        ('payment', 'Payment'),
        ('price_update', 'Price Update'),
    )

    SYNC_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    device_id = models.CharField(
        max_length=100,
        help_text='Unique identifier for mobile device'
    )
    sync_type = models.CharField(
        max_length=20,
        choices=SYNC_TYPE
    )
    local_id = models.CharField(
        max_length=50,
        help_text='Temporary ID from mobile app'
    )
    server_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Actual ID from server after sync'
    )
    data = models.JSONField(
        help_text='Data to be synced'
    )
    status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS,
        default='pending'
    )
    error_message = models.TextField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_attempt = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['device_id', 'sync_type', 'status']),
            models.Index(fields=['local_id', 'server_id']),
            models.Index(fields=['status', 'last_sync_attempt']),
        ]

class FutureOrderRequest(models.Model):
    """Store seller's future order requests"""
    seller = models.ForeignKey(
        Seller,
        on_delete=models.PROTECT,
        related_name='future_order_requests'
    )
    delivery_date = models.DateField(
        help_text='Requested delivery date'
    )
    notes = models.TextField(
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['seller', 'delivery_date']),
            models.Index(fields=['sync_status']),
        ]

class FutureOrderRequestItem(models.Model):
    """Products requested for future delivery"""
    request = models.ForeignKey(
        FutureOrderRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )

class DeliveryExpense(models.Model):
    """Track delivery team expenses"""
    EXPENSE_TYPE = (
        ('food', 'Food/Snacks'),
        ('vehicle', 'Vehicle Repair/Maintenance'),
        ('fuel', 'Fuel'),
        ('other', 'Other Expenses')
    )

    delivery_team = models.ForeignKey(
        DeliveryTeam,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    expense_date = models.DateField()
    expense_type = models.CharField(
        max_length=20,
        choices=EXPENSE_TYPE
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    notes = models.TextField(
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Offline sync fields
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['delivery_team', 'expense_date']),
            models.Index(fields=['sync_status']),
        ]

class CashDenomination(models.Model):
    """Track cash collected by denomination"""
    delivery_order = models.ForeignKey(
        DeliveryOrder,
        on_delete=models.PROTECT,
        related_name='cash_denominations'
    )
    denomination = models.PositiveIntegerField(
        help_text='Value of the note (500, 200, etc.)'
    )
    count = models.PositiveIntegerField(
        help_text='Number of notes'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total amount (denomination * count)'
    )

    # Offline sync fields
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        self.total_amount = self.denomination * self.count
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['delivery_order', 'denomination']),
            models.Index(fields=['sync_status']),
        ]

class SellerPriceCache(models.Model):
    """Cache seller prices for offline use"""
    seller = models.ForeignKey(
        Seller,
        on_delete=models.PROTECT,
        related_name='price_cache'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='seller_price_cache'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    valid_from = models.DateField()
    valid_to = models.DateField()
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['seller', 'product', 'valid_from', 'valid_to']),
            models.Index(fields=['is_active', 'last_sync']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['seller', 'product', 'valid_from'],
                name='unique_seller_product_price_period'
            )
        ]

class GeneralPriceCache(models.Model):
    """Cache general prices for offline use"""
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='general_price_cache'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    valid_from = models.DateField()
    valid_to = models.DateField()
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['product', 'valid_from', 'valid_to']),
            models.Index(fields=['is_active', 'last_sync']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'valid_from'],
                name='unique_product_price_period'
            )
        ]


class PublicSale(models.Model):
    """Model for recording sales to the public during delivery routes"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('credit', 'Credit'),
        ('bank_transfer', 'Bank Transfer'),
    )

    # Basic information
    sale_number = models.CharField(max_length=20, unique=True, editable=False)
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name='public_sales')
    delivery_team = models.ForeignKey('DeliveryTeam', on_delete=models.PROTECT, related_name='public_sales', null=True, blank=True)
    loading_order = models.ForeignKey('LoadingOrder', on_delete=models.PROTECT, related_name='public_sales', null=True, blank=True)

    # Customer information (optional since it's a public sale)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)

    # Sale details
    sale_date = models.DateField()
    sale_time = models.TimeField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    notes = models.TextField(blank=True, null=True)

    # Financial information
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='created_public_sales')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='updated_public_sales')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Offline sync fields
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    local_id = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        # Generate a unique sale number if not already set
        if not self.sale_number:
            self.sale_number = f"PS-{uuid.uuid4().hex[:8].upper()}"

        # Calculate balance amount
        self.balance_amount = self.total_price - self.amount_collected

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sale_number} - {self.sale_date} - {self.customer_name or 'Public'}"

    class Meta:
        indexes = [
            models.Index(fields=['route', 'sale_date']),
            models.Index(fields=['sync_status']),
        ]


class PublicSaleItem(models.Model):
    """Model for items in a public sale"""
    public_sale = models.ForeignKey(PublicSale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

        # Update the total price of the public sale
        self.public_sale.total_price = self.public_sale.items.aggregate(total=models.Sum('total_price'))['total'] or 0
        self.public_sale.save()

    def __str__(self):
        return f"{self.product.name} - {self.quantity} - {self.total_price}"