from django.db import models
from apps.authentication.models import CustomUser
from apps.seller.models import Seller

class Category(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='categories_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='categories_updated'
    )

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

class Product(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    is_liquid = models.BooleanField(default=False)
    unit_size = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Number per litre/kilo/pack'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive products won\'t be available for new orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_updated'
    )

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

class PricePlan(models.Model):
    name = models.CharField(max_length=100)
    valid_from = models.DateField()
    valid_to = models.DateField()
    is_general = models.BooleanField(
        default=True,
        help_text='If True, this is a general price plan. If False, it\'s specific to a seller'
    )
    seller = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_plans',
        help_text='Leave empty for general price plans'
    )
    excel_file = models.FileField(
        upload_to='price_plans/%Y/%m/',
        help_text='Upload Excel file containing prices'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='price_plans_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='price_plans_updated'
    )

    def __str__(self):
        if self.is_general:
            return f"General Price Plan: {self.name} ({self.valid_from} to {self.valid_to})"
        return f"Special Price Plan for {self.seller}: {self.name} ({self.valid_from} to {self.valid_to})"

    class Meta:
        ordering = ['-valid_from', 'name']
        verbose_name = 'Price Plan'
        verbose_name_plural = 'Price Plans'

class ProductPrice(models.Model):
    price_plan = models.ForeignKey(
        PricePlan,
        on_delete=models.CASCADE,
        related_name='product_prices'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='prices'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['price_plan', 'product']
        ordering = ['price_plan', 'product']
        verbose_name = 'Product Price'
        verbose_name_plural = 'Product Prices'

    def __str__(self):
        return f"{self.product} - {self.price} ({self.price_plan})"
