from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sellers', views.SellerViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'routes', views.RouteViewSet)
router.register(r'price-plans', views.PricePlanViewSet)
router.register(r'product-prices', views.ProductPriceViewSet)
router.register(r'orders/sales', views.SalesOrderViewSet)
router.register(r'orders/purchase', views.PurchaseOrderViewSet)
router.register(r'orders/loading', views.LoadingOrderViewSet)
router.register(r'orders/delivery', views.DeliveryOrderViewSet)
router.register(r'orders/return', views.ReturnedOrderViewSet)
router.register(r'orders/broken', views.BrokenOrderViewSet)
router.register(r'orders/public_sale', views.PublicSaleViewSet)
# router.register(r'orders/payment', views.PaymentViewSet)

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),

    # Sync endpoints
    path('sync/', views.SyncView.as_view(), name='sync'),
    path('sync/status/', views.SyncStatusView.as_view(), name='sync-status'),

    # Router URLs
    path('', include(router.urls)),
]
