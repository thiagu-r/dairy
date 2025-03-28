from django.urls import path
from . import views

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
]
