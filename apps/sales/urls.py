from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('get-sellers-by-route/', views.GetSellersByRouteView.as_view(), name='get-sellers-by-route'),
    path('dashboard/', views.SalesDashboardView.as_view(), name='dashboard'),
    path('orders/', views.SalesOrderListView.as_view(), name='order-list'),
    path('orders/create/', views.SalesOrderCreateView.as_view(), name='order-create'),
    path('orders/<int:order_id>/view/', views.SalesOrderViewView.as_view(), name='order-view'),
    path('orders/<int:order_id>/edit/', views.SalesOrderEditView.as_view(), name='order-edit'),
    path('orders/<int:order_id>/update/', views.SalesOrderUpdateView.as_view(), name='order-update'),
    path('get-product-price/', views.GetProductPriceView.as_view(), name='get-product-price'),
    path('get-available-products/', views.GetAvailableProductsView.as_view(), name='get-available-products'),
    path('call-logs/', views.CallLogListView.as_view(), name='call-log-list'),
    path('call-logs/create/', views.CallLogCreateView.as_view(), name='call-log-create'),
    path('call-logs/<int:call_log_id>/edit-form/', views.CallLogEditFormView.as_view(), name='call-log-edit-form'),
    path('call-logs/<int:call_log_id>/edit/', views.CallLogEditView.as_view(), name='call-log-edit'),
    path('check-existing-order/', views.check_existing_order, name='check-existing-order'),
]
