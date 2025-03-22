from django.db import models
from django.utils import timezone
from decimal import Decimal
from apps.authentication.models import CustomUser
from apps.seller.models import Seller, Route
from apps.products.models import Product, PricePlan
from django.conf import settings

class SalesOrder(models.Model):
    ORDER_STATUS = (
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('ready', 'Ready for Delivery'),
        ('delivered', 'Delivered'),
        ('partially_delivered', 'Partially Delivered'),
        ('cancelled', 'Cancelled'),
    )

    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
    )
    seller = models.ForeignKey(
        Seller,
        on_delete=models.PROTECT,
        related_name='sales_orders'
    )
    delivery_date = models.DateField(
        help_text='Date when the order should be delivered',
        db_index=True  # Added index for better query performance
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS,
        default='draft'
    )
    is_delivered = models.BooleanField(
        default=False,
        help_text='Indicates if the order has been delivered'
    )
    actual_delivery_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual time when the order was delivered'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Any special instructions or notes for this order'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='sales_orders_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='sales_orders_updated'
    )

    class Meta:
        ordering = ['-delivery_date', '-created_at']
        verbose_name = 'Sales Order'
        verbose_name_plural = 'Sales Orders'
        indexes = [
            models.Index(fields=['delivery_date', 'seller']),
            models.Index(fields=['delivery_date', 'seller', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['seller', 'delivery_date'],
                name='unique_seller_delivery_date'
            )
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.seller.store_name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: SO-YYYYMMDD-XXXX
            today = timezone.now().date()
            prefix = f"SO-{today.strftime('%Y%m%d')}-"
            last_order = SalesOrder.objects.filter(
                order_number__startswith=prefix
            ).order_by('-order_number').first()
            
            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = str(last_number + 1).zfill(4)
            else:
                new_number = '0001'
            
            self.order_number = f"{prefix}{new_number}"
        
        super().save(*args, **kwargs)

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_amount(self):
        return sum(item.total_amount for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Ordered quantity in units'
    )
    delivered_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
        help_text='Actually delivered quantity'
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Price per unit from general price plan'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product__category', 'product__name']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"

    @property
    def total_amount(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if not self.unit_price:
            # Get price from active general price plan
            price_plan = PricePlan.objects.filter(
                is_general=True,
                is_active=True,
                valid_from__lte=self.order.delivery_date,
                valid_to__gte=self.order.delivery_date
            ).order_by('-created_at').first()
            
            if price_plan:
                product_price = price_plan.product_prices.filter(
                    product=self.product
                ).first()
                if product_price:
                    self.unit_price = product_price.price
                else:
                    self.unit_price = Decimal('0.00')
            else:
                self.unit_price = Decimal('0.00')

        super().save(*args, **kwargs)

class SellerCallLog(models.Model):
    CALL_STATUS = (
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('no_answer', 'No Answer'),
        ('cancelled', 'Cancelled'),
    )
    
    seller = models.ForeignKey('seller.Seller', on_delete=models.CASCADE)
    call_date = models.DateField()
    next_call_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=CALL_STATUS)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-call_date', '-created_at']
        verbose_name = 'Seller Call Log'
        verbose_name_plural = 'Seller Call Logs'
        indexes = [
            models.Index(fields=['call_date', 'seller', 'status']),
        ]

    def __str__(self):
        return f"Call to {self.seller.store_name} on {self.call_date}"
