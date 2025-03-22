from django.db import models
from apps.authentication.models import CustomUser

class Route(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='routes_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='routes_updated'
    )

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        ordering = ['name']
        verbose_name = 'Route'
        verbose_name_plural = 'Routes'


class Seller(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    mobileno = models.CharField(max_length=15, unique=True)
    store_name = models.CharField(max_length=100)
    store_address = models.TextField()
    route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sellers'
    )
    lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Latitude'
    )
    lan = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Longitude'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sellers_created'
    )
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sellers_updated'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.store_name}"

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Seller'
        verbose_name_plural = 'Sellers'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"