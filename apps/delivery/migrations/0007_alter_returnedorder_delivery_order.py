# Generated by Django 5.1.7 on 2025-04-04 06:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0006_alter_publicsale_delivery_team_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="returnedorder",
            name="delivery_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="returned_orders",
                to="delivery.deliveryorder",
            ),
        ),
    ]
