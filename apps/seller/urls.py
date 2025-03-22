from django.urls import path
from .views import (
    RouteListView, RouteCreateView, 
    RouteEditFormView, RouteEditView,
    SellerListView, SellerCreateView,
    SellerEditFormView, SellerEditView
)

app_name = 'seller'

urlpatterns = [
    path('routes/', RouteListView.as_view(), name='route-list'),
    path('routes/create/', RouteCreateView.as_view(), name='route-create'),
    path('routes/<int:route_id>/edit-form/', RouteEditFormView.as_view(), name='route-edit-form'),
    path('routes/<int:route_id>/edit/', RouteEditView.as_view(), name='route-edit'),
    path('sellers/', SellerListView.as_view(), name='seller-list'),
    path('sellers/create/', SellerCreateView.as_view(), name='seller-create'),
    path('sellers/<int:seller_id>/edit-form/', SellerEditFormView.as_view(), name='seller-edit-form'),
    path('sellers/<int:seller_id>/edit/', SellerEditView.as_view(), name='seller-edit'),
]
