# Generated by Django 5.1.7 on 2025-03-21 12:59

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0002_remove_sellercalllog_sales_order_and_more"),
        ("seller", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="salesorder",
            constraint=models.UniqueConstraint(
                fields=("seller", "delivery_date"), name="unique_seller_delivery_date"
            ),
        ),
    ]
