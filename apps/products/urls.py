from django.urls import path
from .views import (
    CategoryListView, CategoryCreateView,
    CategoryEditFormView, CategoryEditView,
    ProductListView, ProductCreateView,
    ProductEditFormView, ProductEditView,
    PricePlanListView, PricePlanCreateView,
    PricePlanEditFormView, PricePlanEditView,
    download_price_plan_template,
    PricePlanPricesView,
    PricePlanUpdatePriceView,
    PricePlanDeletePriceView,
    PricePlanAddPriceView
)

app_name = 'products'

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/create/', CategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:category_id>/edit-form/', CategoryEditFormView.as_view(), name='category-edit-form'),
    path('categories/<int:category_id>/edit/', CategoryEditView.as_view(), name='category-edit'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:product_id>/edit-form/', ProductEditFormView.as_view(), name='product-edit-form'),
    path('products/<int:product_id>/edit/', ProductEditView.as_view(), name='product-edit'),
    path('price-plans/', PricePlanListView.as_view(), name='price-plan-list'),
    path('price-plans/create/', PricePlanCreateView.as_view(), name='price-plan-create'),
    path('price-plans/<int:price_plan_id>/edit-form/', PricePlanEditFormView.as_view(), name='price-plan-edit-form'),
    path('price-plans/<int:price_plan_id>/edit/', PricePlanEditView.as_view(), name='price-plan-edit'),
    path('price-plans/template/', download_price_plan_template, name='price-plan-template'),
    path('price-plans/<int:price_plan_id>/prices/', PricePlanPricesView.as_view(), name='price-plan-prices'),
    path('price-plans/<int:price_plan_id>/prices/add/', PricePlanAddPriceView.as_view(), name='price-plan-add-price'),
    path('price-plans/<int:price_plan_id>/prices/<int:price_id>/', PricePlanUpdatePriceView.as_view(), name='price-plan-update-price'),
    path('price-plans/<int:price_plan_id>/prices/<int:price_id>/delete/', PricePlanDeletePriceView.as_view(), name='price-plan-delete-price'),
]
