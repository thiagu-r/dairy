# Generated by Django 5.1.7 on 2025-03-24 14:55

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0002_product_is_active'),
        ('sales', '0003_salesorder_unique_seller_delivery_date'),
        ('seller', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BrokenOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(editable=False, max_length=20, unique=True)),
                ('report_date', models.DateField(db_index=True)),
                ('report_time', models.TimeField()),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='broken_orders_created', to=settings.AUTH_USER_MODEL)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='broken_orders', to='seller.route')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='broken_orders_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Broken Order',
                'verbose_name_plural': 'Broken Orders',
                'ordering': ['-report_date', '-report_time'],
            },
        ),
        migrations.CreateModel(
            name='BrokenOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, help_text='Quantity of broken/damaged products', max_digits=10)),
                ('reason', models.TextField(help_text='Reason for damage/breakage')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('broken_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='delivery.brokenorder')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='broken_order_items', to='products.product')),
            ],
            options={
                'ordering': ['product__category', 'product__name'],
            },
        ),
        migrations.CreateModel(
            name='DeliverySync',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(help_text='Unique identifier for mobile device', max_length=100)),
                ('sync_type', models.CharField(choices=[('delivery_order', 'Delivery Order'), ('order_item', 'Order Item'), ('payment', 'Payment'), ('price_update', 'Price Update')], max_length=20)),
                ('local_id', models.CharField(help_text='Temporary ID from mobile app', max_length=50)),
                ('server_id', models.CharField(blank=True, help_text='Actual ID from server after sync', max_length=50, null=True)),
                ('data', models.JSONField(help_text='Data to be synced')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_sync_attempt', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'indexes': [models.Index(fields=['device_id', 'sync_type', 'status'], name='delivery_de_device__6aae17_idx'), models.Index(fields=['local_id', 'server_id'], name='delivery_de_local_i_5ca48f_idx'), models.Index(fields=['status', 'last_sync_attempt'], name='delivery_de_status_d92b46_idx')],
            },
        ),
        migrations.CreateModel(
            name='DeliveryTeam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_teams', to='seller.route')),
            ],
            options={
                'verbose_name': 'Delivery Team',
                'verbose_name_plural': 'Delivery Teams',
                'ordering': ['distributor', 'name'],
            },
        ),
        migrations.CreateModel(
            name='DeliveryTeamMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('DRIVER', 'Truck Driver'), ('SUPERVISOR', 'Sales Supervisor'), ('DELIVERY', 'Delivery Man')], max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('delivery_team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='team_members', to='delivery.deliveryteam')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_team_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Delivery Team Member',
                'verbose_name_plural': 'Delivery Team Members',
                'ordering': ['delivery_team', 'role'],
            },
        ),
        migrations.CreateModel(
            name='DailyDeliveryTeam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_date', models.DateField(db_index=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='daily_teams_created', to=settings.AUTH_USER_MODEL)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='daily_teams', to='seller.route')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='daily_teams_updated', to=settings.AUTH_USER_MODEL)),
                ('delivery_team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='daily_teams', to='delivery.deliveryteam')),
                ('delivery_man', models.ForeignKey(blank=True, limit_choices_to={'role': 'DELIVERY'}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='daily_delivery_duties', to='delivery.deliveryteammember')),
                ('driver', models.ForeignKey(limit_choices_to={'role': 'DRIVER'}, on_delete=django.db.models.deletion.PROTECT, related_name='daily_driver_duties', to='delivery.deliveryteammember')),
                ('supervisor', models.ForeignKey(blank=True, limit_choices_to={'role': 'SUPERVISOR'}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='daily_supervisor_duties', to='delivery.deliveryteammember')),
            ],
            options={
                'verbose_name': 'Daily Delivery Team',
                'verbose_name_plural': 'Daily Delivery Teams',
                'ordering': ['-delivery_date'],
            },
        ),
        migrations.CreateModel(
            name='Distributor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('contact_person', models.CharField(max_length=100)),
                ('mobile', models.CharField(max_length=15)),
                ('address', models.TextField()),
                ('is_internal', models.BooleanField(default=False, help_text='True if distributor is part of dairy factory')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='distributors_created', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='distributors_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Distributor',
                'verbose_name_plural': 'Distributors',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='deliveryteam',
            name='distributor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_teams', to='delivery.distributor'),
        ),
        migrations.CreateModel(
            name='FutureOrderRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_date', models.DateField(help_text='Requested delivery date')),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('local_id', models.CharField(blank=True, max_length=50, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='future_order_requests', to='seller.seller')),
            ],
        ),
        migrations.CreateModel(
            name='FutureOrderRequestItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=10)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='products.product')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='delivery.futureorderrequest')),
            ],
        ),
        migrations.CreateModel(
            name='GeneralPriceCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('valid_from', models.DateField()),
                ('valid_to', models.DateField()),
                ('is_active', models.BooleanField(default=True)),
                ('last_sync', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='general_price_cache', to='products.product')),
            ],
        ),
        migrations.CreateModel(
            name='LoadingOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(editable=False, max_length=20, unique=True)),
                ('loading_date', models.DateField(db_index=True)),
                ('loading_time', models.TimeField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('loading', 'Loading in Progress'), ('completed', 'Loading Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('crates_loaded', models.PositiveIntegerField(default=0, help_text='Number of crates loaded')),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('local_id', models.CharField(blank=True, max_length=50, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loading_orders_created', to=settings.AUTH_USER_MODEL)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loading_orders', to='seller.route')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loading_orders_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Loading Order',
                'verbose_name_plural': 'Loading Orders',
                'ordering': ['-loading_date', '-loading_time'],
            },
        ),
        migrations.CreateModel(
            name='DeliveryOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(editable=False, max_length=20, unique=True)),
                ('delivery_date', models.DateField(db_index=True)),
                ('delivery_time', models.TimeField()),
                ('total_price', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total price for all items in this delivery', max_digits=10)),
                ('opening_balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Previous balance amount', max_digits=10)),
                ('amount_collected', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Amount collected on delivery date', max_digits=10)),
                ('payment_method', models.CharField(choices=[('cash', 'Cash'), ('online', 'Online Transfer')], default='cash', help_text='Method of payment collection', max_length=10)),
                ('balance_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Remaining balance for this delivery', max_digits=10)),
                ('total_balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total outstanding balance including previous balance', max_digits=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_orders_created', to=settings.AUTH_USER_MODEL)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_orders', to='seller.route')),
                ('sales_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_orders', to='sales.salesorder')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_orders', to='seller.seller')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_orders_updated', to=settings.AUTH_USER_MODEL)),
                ('loading_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_orders', to='delivery.loadingorder')),
            ],
            options={
                'verbose_name': 'Delivery Order',
                'verbose_name_plural': 'Delivery Orders',
                'ordering': ['-delivery_date', '-delivery_time'],
            },
        ),
        migrations.AddField(
            model_name='brokenorder',
            name='loading_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='broken_orders', to='delivery.loadingorder'),
        ),
        migrations.CreateModel(
            name='LoadingOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requested_quantity', models.DecimalField(decimal_places=3, help_text='Quantity requested in purchase order', max_digits=10)),
                ('loaded_quantity', models.DecimalField(decimal_places=3, help_text='Actual quantity loaded from factory', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('loading_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='delivery.loadingorder')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loading_order_items', to='products.product')),
            ],
            options={
                'ordering': ['product__category', 'product__name'],
            },
        ),
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(editable=False, max_length=20, unique=True)),
                ('delivery_date', models.DateField(db_index=True, help_text='Date when products will be delivered')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('processing', 'Processing'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders_created', to=settings.AUTH_USER_MODEL)),
                ('delivery_team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders', to='delivery.deliveryteam')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders', to='seller.route')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Purchase Order',
                'verbose_name_plural': 'Purchase Orders',
                'ordering': ['-delivery_date', '-created_at'],
            },
        ),
        migrations.AddField(
            model_name='loadingorder',
            name='purchase_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loading_orders', to='delivery.purchaseorder'),
        ),
        migrations.CreateModel(
            name='PurchaseOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sales_order_quantity', models.DecimalField(decimal_places=3, help_text='Total quantity from sales orders', max_digits=10)),
                ('extra_quantity', models.DecimalField(decimal_places=3, default=Decimal('0.000'), help_text='Additional quantity for public sales', max_digits=10)),
                ('remaining_quantity', models.DecimalField(decimal_places=3, default=Decimal('0.000'), help_text='Remaining quantity from previous day', max_digits=10)),
                ('total_quantity', models.DecimalField(decimal_places=3, help_text='Total quantity to be loaded', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_order_items', to='products.product')),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='delivery.purchaseorder')),
            ],
            options={
                'verbose_name': 'Purchase Order Item',
                'verbose_name_plural': 'Purchase Order Items',
                'ordering': ['product__category', 'product__name'],
            },
        ),
        migrations.CreateModel(
            name='ReturnedOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(editable=False, max_length=20, unique=True)),
                ('return_date', models.DateField(db_index=True)),
                ('return_time', models.TimeField()),
                ('reason', models.TextField(help_text='Reason for return')),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('crates_returned', models.PositiveIntegerField(default=0, help_text='Number of crates returned')),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('local_id', models.CharField(blank=True, max_length=50, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='returned_orders_created', to=settings.AUTH_USER_MODEL)),
                ('delivery_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='returned_orders', to='delivery.deliveryorder')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='returned_orders', to='seller.route')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='returned_orders_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Returned Order',
                'verbose_name_plural': 'Returned Orders',
                'ordering': ['-return_date', '-return_time'],
            },
        ),
        migrations.CreateModel(
            name='ReturnedOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, help_text='Quantity of returned products', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='returned_order_items', to='products.product')),
                ('returned_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='delivery.returnedorder')),
            ],
            options={
                'ordering': ['product__category', 'product__name'],
            },
        ),
        migrations.CreateModel(
            name='SellerPriceCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('valid_from', models.DateField()),
                ('valid_to', models.DateField()),
                ('is_active', models.BooleanField(default=True)),
                ('last_sync', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='seller_price_cache', to='products.product')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='price_cache', to='seller.seller')),
            ],
        ),
        migrations.CreateModel(
            name='CashDenomination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('denomination', models.PositiveIntegerField(help_text='Value of the note (500, 200, etc.)')),
                ('count', models.PositiveIntegerField(help_text='Number of notes')),
                ('total_amount', models.DecimalField(decimal_places=2, help_text='Total amount (denomination * count)', max_digits=10)),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('local_id', models.CharField(blank=True, max_length=50, null=True)),
                ('delivery_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cash_denominations', to='delivery.deliveryorder')),
            ],
            options={
                'indexes': [models.Index(fields=['delivery_order', 'denomination'], name='delivery_ca_deliver_8dbef1_idx'), models.Index(fields=['sync_status'], name='delivery_ca_sync_st_e76463_idx')],
            },
        ),
        migrations.CreateModel(
            name='DeliveryOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordered_quantity', models.DecimalField(decimal_places=3, help_text='Quantity from sales order', max_digits=10)),
                ('delivered_quantity', models.DecimalField(decimal_places=3, help_text='Actually delivered quantity', max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, help_text='Price per unit for this seller', max_digits=10)),
                ('total_price', models.DecimalField(decimal_places=2, help_text='Total price for delivered quantity', max_digits=10)),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending', help_text='Sync status for mobile app', max_length=20)),
                ('local_id', models.CharField(blank=True, help_text='Temporary ID used by mobile app before sync', max_length=50, null=True)),
                ('last_sync_attempt', models.DateTimeField(blank=True, help_text='Last attempted sync timestamp', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('delivery_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='delivery.deliveryorder')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delivery_order_items', to='products.product')),
            ],
            options={
                'ordering': ['product__category', 'product__name'],
                'indexes': [models.Index(fields=['sync_status', 'last_sync_attempt'], name='delivery_de_sync_st_95fb69_idx'), models.Index(fields=['local_id'], name='delivery_de_local_i_13b147_idx')],
            },
        ),
        migrations.CreateModel(
            name='DeliveryExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expense_date', models.DateField()),
                ('expense_type', models.CharField(choices=[('food', 'Food/Snacks'), ('vehicle', 'Vehicle Repair/Maintenance'), ('fuel', 'Fuel'), ('other', 'Other Expenses')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('local_id', models.CharField(blank=True, max_length=50, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('delivery_team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='expenses', to='delivery.deliveryteam')),
            ],
            options={
                'indexes': [models.Index(fields=['delivery_team', 'expense_date'], name='delivery_de_deliver_e2514e_idx'), models.Index(fields=['sync_status'], name='delivery_de_sync_st_2cffd8_idx')],
            },
        ),
        migrations.AddConstraint(
            model_name='deliveryteammember',
            constraint=models.UniqueConstraint(fields=('delivery_team', 'user', 'role'), name='unique_team_user_role'),
        ),
        migrations.AddConstraint(
            model_name='dailydeliveryteam',
            constraint=models.UniqueConstraint(fields=('delivery_team', 'route', 'delivery_date'), name='unique_team_route_date'),
        ),
        migrations.AddIndex(
            model_name='futureorderrequest',
            index=models.Index(fields=['seller', 'delivery_date'], name='delivery_fu_seller__37131f_idx'),
        ),
        migrations.AddIndex(
            model_name='futureorderrequest',
            index=models.Index(fields=['sync_status'], name='delivery_fu_sync_st_d7171f_idx'),
        ),
        migrations.AddIndex(
            model_name='generalpricecache',
            index=models.Index(fields=['product', 'valid_from', 'valid_to'], name='delivery_ge_product_20c9b1_idx'),
        ),
        migrations.AddIndex(
            model_name='generalpricecache',
            index=models.Index(fields=['is_active', 'last_sync'], name='delivery_ge_is_acti_de5f73_idx'),
        ),
        migrations.AddConstraint(
            model_name='generalpricecache',
            constraint=models.UniqueConstraint(fields=('product', 'valid_from'), name='unique_product_price_period'),
        ),
        migrations.AddConstraint(
            model_name='deliveryorder',
            constraint=models.UniqueConstraint(fields=('loading_order', 'route', 'seller', 'delivery_date'), name='unique_lo_route_seller_delivery_date'),
        ),
        migrations.AddConstraint(
            model_name='brokenorder',
            constraint=models.UniqueConstraint(fields=('loading_order', 'route', 'report_date'), name='unique_lo_route_report_date'),
        ),
        migrations.AddConstraint(
            model_name='purchaseorder',
            constraint=models.UniqueConstraint(fields=('delivery_team', 'route', 'delivery_date'), name='unique_team_route_delivery_date'),
        ),
        migrations.AddConstraint(
            model_name='loadingorder',
            constraint=models.UniqueConstraint(fields=('purchase_order', 'route', 'loading_date'), name='unique_po_route_loading_date'),
        ),
        migrations.AddConstraint(
            model_name='returnedorder',
            constraint=models.UniqueConstraint(fields=('delivery_order', 'route', 'return_date'), name='unique_do_route_return_date'),
        ),
        migrations.AddIndex(
            model_name='sellerpricecache',
            index=models.Index(fields=['seller', 'product', 'valid_from', 'valid_to'], name='delivery_se_seller__d68287_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerpricecache',
            index=models.Index(fields=['is_active', 'last_sync'], name='delivery_se_is_acti_525b29_idx'),
        ),
        migrations.AddConstraint(
            model_name='sellerpricecache',
            constraint=models.UniqueConstraint(fields=('seller', 'product', 'valid_from'), name='unique_seller_product_price_period'),
        ),
    ]
