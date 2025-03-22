from django.contrib import admin
from .models import Route, Seller

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at', 'created_by')
    search_fields = ('name', 'code')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'store_name', 'mobileno', 'route')
    search_fields = ('first_name', 'last_name', 'store_name', 'mobileno')
    list_filter = ('route', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')