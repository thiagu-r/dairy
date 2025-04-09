from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Dashboard home
    path('', views.DashboardHomeView.as_view(), name='dashboard_home'),
    
    # Sales analytics
    path('analytics/sales/', views.SalesAnalyticsView.as_view(), name='sales_analytics'),
    path('api/analytics/sales/', views.SalesAnalyticsDataAPIView.as_view(), name='sales_analytics_data'),
    
    # Seller balance report
    path('reports/seller-balance/', views.SellerBalanceReportView.as_view(), name='seller_balance_report'),
    path('api/reports/seller-balance/', views.SellerBalanceDataAPIView.as_view(), name='seller_balance_data'),
    
    # Excel exports
    path('export/sales/', views.export_sales_excel, name='export_sales_excel'),
    path('export/detailed-sales/', views.export_detailed_sales_excel, name='export_detailed_sales_excel'),
    path('export/seller-balance/', views.export_seller_balance_excel, name='export_seller_balance_excel'),
]
