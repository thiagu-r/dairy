from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db.models import Sum, F, DecimalField, Count, Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminOrCEOUser, IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from datetime import datetime, timedelta
import json
from decimal import Decimal

from apps.seller.models import Seller, Route
from apps.sales.models import SalesOrder, OrderItem
from apps.delivery.models import DeliveryOrder
from apps.products.models import Product

from .serializers import (
    SalesAnalyticsSerializer,
    ProductSalesAnalyticsSerializer,
    RouteSalesAnalyticsSerializer,
    SellerBalanceSerializer,
    SalesOrderExportSerializer,
    OrderItemExportSerializer,
    SellerBalanceExportSerializer
)

from .utils import (
    get_sales_analytics_by_seller,
    get_sales_analytics_by_product,
    get_sales_analytics_by_route,
    get_seller_balance_report,
    generate_excel_for_sales,
    generate_excel_for_seller_balance,
    generate_excel_for_detailed_sales
)

# Dashboard Home View
@method_decorator(login_required, name='dispatch')
class DashboardHomeView(TemplateView):

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.role == 'ADMIN' or request.user.role == 'ceo'):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
    template_name = 'admin_dashboard/dashboard_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get counts for various entities
        context['seller_count'] = Seller.objects.count()
        context['route_count'] = Route.objects.count()
        context['product_count'] = Product.objects.count()
        context['sales_order_count'] = SalesOrder.objects.count()

        # Get recent sales orders
        context['recent_orders'] = SalesOrder.objects.select_related('seller').order_by('-delivery_date')[:10]

        # Get top sellers
        context['top_sellers'] = Seller.objects.annotate(
            total_sales=Coalesce(Sum('delivery_orders__total_price'), Decimal('0.00'))
        ).order_by('-total_sales')[:5]

        return context

# Sales Analytics Views
@method_decorator(login_required, name='dispatch')
class SalesAnalyticsView(TemplateView):

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.role == 'ADMIN' or request.user.role == 'ceo'):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
    template_name = 'admin_dashboard/sales_analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter options to context
        context['sellers'] = Seller.objects.all().order_by('store_name')
        context['routes'] = Route.objects.all().order_by('name')
        context['products'] = Product.objects.filter(is_active=True).order_by('name')

        # Default time periods
        today = datetime.now().date()
        context['start_date'] = (today - timedelta(days=30)).isoformat()
        context['end_date'] = today.isoformat()

        return context

class SalesAnalyticsDataAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Get filter parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        group_by = request.query_params.get('group_by', 'seller')
        time_filter = request.query_params.get('time_filter', 'monthly')

        # Get analytics data based on grouping
        if group_by == 'product':
            analytics_data = get_sales_analytics_by_product(start_date, end_date, time_filter)
            serializer = ProductSalesAnalyticsSerializer(analytics_data, many=True)
        elif group_by == 'route':
            analytics_data = get_sales_analytics_by_route(start_date, end_date, time_filter)
            serializer = RouteSalesAnalyticsSerializer(analytics_data, many=True)
        else:  # default: group by seller
            analytics_data = get_sales_analytics_by_seller(start_date, end_date, time_filter)
            serializer = SalesAnalyticsSerializer(analytics_data, many=True)

        # Prepare chart data
        chart_data = {
            'labels': [],
            'datasets': [
                {
                    'label': 'Total Value',
                    'data': [],
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 1
                },
                {
                    'label': 'Total Quantity',
                    'data': [],
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                    'borderColor': 'rgba(255, 99, 132, 1)',
                    'borderWidth': 1
                }
            ]
        }

        # Populate chart data
        for item in serializer.data:
            if group_by == 'product':
                chart_data['labels'].append(item['product_name'])
            elif group_by == 'route':
                chart_data['labels'].append(item['route_name'])
            else:
                chart_data['labels'].append(item['seller_name'])

            chart_data['datasets'][0]['data'].append(float(item['total_value']))
            chart_data['datasets'][1]['data'].append(float(item['total_quantity']))

        return Response({
            'chart_data': chart_data,
            'table_data': serializer.data
        })

# Seller Balance Report Views
@method_decorator(login_required, name='dispatch')
class SellerBalanceReportView(TemplateView):

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.role == 'admin' or request.user.role == 'ceo'):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
    template_name = 'admin_dashboard/seller_balance_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter options to context
        context['sellers'] = Seller.objects.all().order_by('store_name')

        # Default time periods
        today = datetime.now().date()
        context['start_date'] = (today - timedelta(days=30)).isoformat()
        context['end_date'] = today.isoformat()

        return context

class SellerBalanceDataAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Get filter parameters
        seller_id = request.query_params.get('seller_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Get seller balance data
        balance_data = get_seller_balance_report(seller_id, start_date, end_date)
        serializer = SellerBalanceSerializer(balance_data, many=True)

        return Response(serializer.data)

# Excel Export Views
@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_sales_excel(request):
    # Get filter parameters
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    group_by = request.query_params.get('group_by', 'seller')
    time_filter = request.query_params.get('time_filter', 'monthly')

    # Get analytics data based on grouping
    if group_by == 'product':
        analytics_data = get_sales_analytics_by_product(start_date, end_date, time_filter)
        file_name = f"sales_by_product_{start_date}_to_{end_date}.xlsx"
    elif group_by == 'route':
        analytics_data = get_sales_analytics_by_route(start_date, end_date, time_filter)
        file_name = f"sales_by_route_{start_date}_to_{end_date}.xlsx"
    else:  # default: group by seller
        analytics_data = get_sales_analytics_by_seller(start_date, end_date, time_filter)
        file_name = f"sales_by_seller_{start_date}_to_{end_date}.xlsx"

    # Generate Excel file
    excel_file = generate_excel_for_sales(analytics_data, group_by, start_date, end_date)

    # Create response
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    return response

@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_detailed_sales_excel(request):
    # Get filter parameters
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    seller_id = request.query_params.get('seller_id')

    # Build queryset
    queryset = OrderItem.objects.select_related('order', 'order__seller', 'product')

    if start_date:
        queryset = queryset.filter(order__delivery_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(order__delivery_date__lte=end_date)
    if seller_id:
        queryset = queryset.filter(order__seller_id=seller_id)

    # Generate Excel file
    excel_file = generate_excel_for_detailed_sales(queryset, start_date, end_date)

    # Create response
    file_name = f"detailed_sales_{start_date}_to_{end_date}.xlsx"
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    return response

@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_seller_balance_excel(request):
    # Get filter parameters
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    seller_id = request.query_params.get('seller_id')

    # Get seller balance data
    balance_data = get_seller_balance_report(seller_id, start_date, end_date)

    # Generate Excel file
    excel_file = generate_excel_for_seller_balance(balance_data, start_date, end_date)

    # Create response
    file_name = f"seller_balance_{start_date}_to_{end_date}.xlsx"
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    return response
