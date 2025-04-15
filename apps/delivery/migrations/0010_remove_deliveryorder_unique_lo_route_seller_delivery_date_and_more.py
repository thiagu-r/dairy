# Generated by Django 5.1.7 on 2025-04-15 08:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0009_alter_deliveryorder_created_by_and_more"),
        ("sales", "0003_salesorder_unique_seller_delivery_date"),
        ("seller", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="deliveryorder",
            name="unique_lo_route_seller_delivery_date",
        ),
        migrations.AlterField(
            model_name="deliveryorder",
            name="loading_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="delivery_orders",
                to="delivery.loadingorder",
            ),
        ),
        migrations.AddConstraint(
            model_name="deliveryorder",
            constraint=models.UniqueConstraint(
                fields=("route", "seller", "delivery_date"),
                name="unique_lo_route_seller_delivery_date",
            ),
        ),
    ]
