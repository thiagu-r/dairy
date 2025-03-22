
from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    MANAGER = 'MANAGER', 'Manager'
    CEO = 'CEO', 'CEO'
    ADMIN = 'ADMIN', 'Admin'
    SALES = 'SALES', 'Sales'
    DELIVERY = 'DELIVERY', 'Delivery'
    SUPERVISOR = 'SUPERVISOR', 'Supervisor'

class CustomUser(AbstractUser):
    mobile_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SALES
    )

    # Make email required
    REQUIRED_FIELDS = ['email', 'mobile_number', 'first_name', 'last_name', 'role']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
