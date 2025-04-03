from django.urls import path
from . import views
from . import public_sales_views

app_name = 'delivery'

urlpatterns = [
    path('delivery/dashboard/', views.DeliveryDashboardView.as_view(), name='dashboard'),
    path('delivery/teams/', views.DeliveryTeamListView.as_view(), name='team-list'),
    path('delivery/teams/create/', views.DeliveryTeamCreateView.as_view(), name='team-create'),
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase-order-list'),
    path('purchase-orders/create/', views.create_purchase_order, name='purchase-order-create'),
    path('delivery/purchase-orders/<int:pk>/edit/',
         views.PurchaseOrderEditView.as_view(),
         name='purchase-order-edit'),
    path('delivery/purchase-orders/<int:pk>/',
         views.PurchaseOrderDetailView.as_view(),
         name='purchase-order-detail'),
    path('delivery/purchase-orders/create/', views.create_purchase_order, name='purchase-order-create'),
    path('delivery-get-route-sales-summary/', views.get_route_sales_summary, name='get-route-sales-summary'),
    path('delivery-get-delivery-teams/', views.get_delivery_teams, name='get-delivery-teams'),
    path('purchase-orders/update-extra-qty/', views.update_extra_quantity, name='update-extra-quantity'),
    path('delivery-check-existing-purchase-order/', views.check_existing_purchase_order, name='check-existing-purchase-order'),
    path('delivery-purchase-orders/<int:pk>/update-item/<int:product_id>/',
         views.update_purchase_order_item,
         name='update-purchase-order-item'),
    path('delivery-check-existing-order-purchase-order/',
         views.check_existing_order,
         name='check-existing-order-purchase-order'),
    path('loading-orders/', views.LoadingOrderListView.as_view(), name='loading-order-list'),
    path('loading-orders/create/', views.create_loading_order, name='loading-order-create'),
    path('loading-orders/check-purchase-order/', views.check_purchase_order, name='check-purchase-order'),
    path('loading-orders/<int:pk>/', views.LoadingOrderDetailView.as_view(), name='loading-order-detail'),
    path('loading-orders/<int:pk>/edit/', views.LoadingOrderEditView.as_view(), name='loading-order-edit'),
    path('delivery/orders/', views.DeliveryOrderListView.as_view(), name='delivery-order-list'),
    path('delivery/orders/create/', views.DeliveryOrderCreateView.as_view(), name='delivery-order-create'),
    path('delivery/orders/<int:pk>/', views.DeliveryOrderDetailView.as_view(), name='delivery-order-detail'),
    path('delivery/orders/<int:pk>/edit/', views.DeliveryOrderCreateView.as_view(), name='delivery-order-edit'),
    path('api/routes/<int:route_id>/sellers/', views.get_route_sellers, name='get-route-sellers'),
    #     path('api/sellers/<int:seller_id>/sales-items/', views.get_seller_sales_items, name='get-seller-sales-items'),
    path('api/sales-items/', views.get_seller_sales_items, name='get-seller-sales-items'),
    path('api/routes/<int:route_id>/available-products/', views.get_available_products, name='get-available-products'),
    path('api/products/', views.get_all_products, name='get-all-products'),
    path('api/products/<int:product_id>/price/', views.get_product_price, name='get-product-price'),
    path('api/check-existing-delivery-order/', views.check_existing_delivery_order, name='check-existing-delivery-order'),
    path('api/sellers/<int:seller_id>/opening-balance/', views.get_seller_opening_balance, name='get-seller-opening-balance'),
    path('api/delivery-orders/<int:order_id>/', views.get_delivery_order, name='get-delivery-order'),

    # Public Sales URLs
    path('delivery/public-sales/', public_sales_views.PublicSaleListView.as_view(), name='public-sale-list'),
    path('delivery/public-sales/create/', public_sales_views.PublicSaleCreateView.as_view(), name='public-sale-create'),
    path('delivery/public-sales/<int:pk>/', public_sales_views.PublicSaleDetailView.as_view(), name='public-sale-detail'),
    path('delivery/public-sales/<int:pk>/edit/', public_sales_views.PublicSaleUpdateView.as_view(), name='public-sale-edit'),
    path('delivery/public-sales/<int:pk>/complete/', public_sales_views.PublicSaleCompleteView.as_view(), name='public-sale-complete'),
    path('delivery/public-sales/<int:pk>/cancel/', public_sales_views.PublicSaleCancelView.as_view(), name='public-sale-cancel'),
    path('delivery/public-sales/<int:pk>/delete/', public_sales_views.PublicSaleDeleteView.as_view(), name='public-sale-delete'),

    # API for Public Sales
    path('api/delivery/public-sales/available-products/', public_sales_views.get_available_products_for_public_sale, name='get-available-products-for-public-sale'),
]
