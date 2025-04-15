from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'sellers', views.SellerViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'routes', views.RouteViewSet)
router.register(r'price-plans', views.PricePlanViewSet)
router.register(r'product-prices', views.ProductPriceViewSet)
router.register(r'orders/sales', views.SalesOrderViewSet)
router.register(r'orders/purchase', views.PurchaseOrderViewSet)
router.register(r'orders/loading', views.LoadingOrderViewSet)
router.register(r'orders/delivery', views.DeliveryOrderViewSet)
router.register(r'orders/delivery-items', views.DeliveryOrderItemViewSet)
router.register(r'orders/return', views.ReturnedOrderViewSet)
router.register(r'orders/broken', views.BrokenOrderViewSet)
router.register(r'orders/public_sale', views.PublicSaleViewSet)
# router.register(r'orders/payment', views.PaymentViewSet)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),

    # JWT Token endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Sync endpoints
    path('sync/', views.SyncView.as_view(), name='sync'),
    path('sync/status/', views.SyncStatusView.as_view(), name='sync-status'),

    # Router URLs
    path('', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('loading-orders/check-purchase-order/', views.CheckPurchaseOrderAPIView.as_view(), name='check-purchase-order'),
]
