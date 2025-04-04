from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
import json
from decimal import Decimal

from web_project import TemplateLayout
from web_project.mixins import DeliveryTeamRequiredMixin
from .models import (
    BrokenOrder, 
    BrokenOrderItem, 
    DeliveryTeam, 
    LoadingOrder, 
    Route,
    Product
)


class BrokenOrderListView(LoginRequiredMixin, DeliveryTeamRequiredMixin, ListView):
    """View for listing all broken orders"""
    model = BrokenOrder
    template_name = 'delivery/broken_orders/broken_order_list.html'
    context_object_name = 'broken_orders'
    
    def get_queryset(self):
        queryset = BrokenOrder.objects.select_related(
             'loading_order', 'created_by', 'updated_by'
        ).order_by('-report_date')
        
        # Apply filters if provided
        report_date = self.request.GET.get('report_date')
        delivery_team_id = self.request.GET.get('delivery_team')
        status = self.request.GET.get('status')
        
        if report_date:
            queryset = queryset.filter(report_date=report_date)
        
        if delivery_team_id:
            queryset = queryset.filter(delivery_team_id=delivery_team_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = TemplateLayout.init(self, context)
        
        # Add filter options
        context['delivery_teams'] = DeliveryTeam.objects.filter(is_active=True)
        # context['statuses'] = dict(BrokenOrder.STATUS_CHOICES)
        
        # Add current filter values
        context['current_filters'] = {
            'report_date': self.request.GET.get('report_date', ''),
            'delivery_team': self.request.GET.get('delivery_team', ''),
            'status': self.request.GET.get('status', '')
        }
        
        return context


class BrokenOrderDetailView(LoginRequiredMixin, DeliveryTeamRequiredMixin, DetailView):
    """View for displaying broken order details"""
    model = BrokenOrder
    template_name = 'delivery/broken_orders/broken_order_detail.html'
    context_object_name = 'broken_order'
    
    def get_queryset(self):
        return BrokenOrder.objects.select_related(
            'delivery_team', 'loading_order', 'created_by', 'updated_by'
        ).prefetch_related('items__product')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = TemplateLayout.init(self, context)
        
        # Add items to context
        context['items'] = self.object.items.select_related('product').all()
        
        return context


class BrokenOrderCreateView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for creating a new broken order"""
    
    def get(self, request):
        # Get data for the form
        delivery_teams = DeliveryTeam.objects.filter(is_active=True).order_by('name')
        loading_orders = LoadingOrder.objects.filter(status='completed').order_by('-loading_date')
        
        context = TemplateLayout.init(self, {
            'delivery_teams': delivery_teams,
            'loading_orders': loading_orders,
            'title': 'Report Broken Products'
        })
        
        return render(request, 'delivery/broken_orders/broken_order_form.html', context)
    
    def post(self, request):
        try:
            # Get form data
            delivery_team_id = request.POST.get('delivery_team_id')
            loading_order_id = request.POST.get('loading_order_id')
            report_date = request.POST.get('report_date')
            notes = request.POST.get('notes', '')
            
            # Get items data
            items_data_str = request.POST.get('items_data')
            
            if not items_data_str:
                return JsonResponse({
                    'status': 'error',
                    'error': 'No items data provided'
                }, status=400)
            
            try:
                items_data = json.loads(items_data_str)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error',
                    'error': f'Invalid items data format: {str(e)}'
                }, status=400)
            
            # Validate required fields
            if not all([delivery_team_id, loading_order_id, report_date]):
                missing = []
                if not delivery_team_id: missing.append('delivery team')
                if not loading_order_id: missing.append('loading order')
                if not report_date: missing.append('report date')
                
                return JsonResponse({
                    'status': 'error',
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)
            
            # Create broken order
            broken_order = BrokenOrder.objects.create(
                delivery_team_id=delivery_team_id,
                loading_order_id=loading_order_id,
                report_date=report_date,
                notes=notes,
                status='pending',
                created_by=request.user,
                updated_by=request.user
            )
            
            # Create broken order items
            for item in items_data:
                try:
                    product_id = int(item['product_id'])
                    quantity = Decimal(item['quantity'])
                    reason = item.get('reason', '')
                    
                    BrokenOrderItem.objects.create(
                        broken_order=broken_order,
                        product_id=product_id,
                        quantity=quantity,
                        reason=reason
                    )
                except Exception as e:
                    print(f"Error creating broken order item: {str(e)}")
                    # Continue with other items even if one fails
            
            return JsonResponse({
                'status': 'success',
                'message': 'Broken products reported successfully',
                'redirect_url': reverse_lazy('delivery:broken-order-detail', kwargs={'pk': broken_order.pk})
            })
            
        except Exception as e:
            print(f"Error creating broken order: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


class BrokenOrderUpdateView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for updating an existing broken order"""
    
    def get(self, request, pk):
        # Get the broken order
        broken_order = get_object_or_404(
            BrokenOrder.objects.select_related('delivery_team', 'loading_order'),
            pk=pk
        )
        
        # Get data for the form
        delivery_teams = DeliveryTeam.objects.filter(is_active=True).order_by('name')
        loading_orders = LoadingOrder.objects.filter(status='completed').order_by('-loading_date')
        
        context = TemplateLayout.init(self, {
            'broken_order': broken_order,
            'delivery_teams': delivery_teams,
            'loading_orders': loading_orders,
            'items': broken_order.items.select_related('product').all(),
            'title': f'Edit Broken Products Report - {broken_order.order_number}'
        })
        
        return render(request, 'delivery/broken_orders/broken_order_form.html', context)
    
    def post(self, request, pk):
        try:
            # Get the broken order
            broken_order = get_object_or_404(BrokenOrder, pk=pk)
            
            # Get form data
            delivery_team_id = request.POST.get('delivery_team_id')
            loading_order_id = request.POST.get('loading_order_id')
            report_date = request.POST.get('report_date')
            notes = request.POST.get('notes', '')
            
            # Get items data
            items_data_str = request.POST.get('items_data')
            
            if not items_data_str:
                return JsonResponse({
                    'status': 'error',
                    'error': 'No items data provided'
                }, status=400)
            
            try:
                items_data = json.loads(items_data_str)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error',
                    'error': f'Invalid items data format: {str(e)}'
                }, status=400)
            
            # Validate required fields
            if not all([delivery_team_id, loading_order_id, report_date]):
                missing = []
                if not delivery_team_id: missing.append('delivery team')
                if not loading_order_id: missing.append('loading order')
                if not report_date: missing.append('report date')
                
                return JsonResponse({
                    'status': 'error',
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)
            
            # Update broken order
            broken_order.delivery_team_id = delivery_team_id
            broken_order.loading_order_id = loading_order_id
            broken_order.report_date = report_date
            broken_order.notes = notes
            broken_order.updated_by = request.user
            broken_order.save()
            
            # Delete existing items
            broken_order.items.all().delete()
            
            # Create new items
            for item in items_data:
                try:
                    product_id = int(item['product_id'])
                    quantity = Decimal(item['quantity'])
                    reason = item.get('reason', '')
                    
                    BrokenOrderItem.objects.create(
                        broken_order=broken_order,
                        product_id=product_id,
                        quantity=quantity,
                        reason=reason
                    )
                except Exception as e:
                    print(f"Error updating broken order item: {str(e)}")
                    # Continue with other items even if one fails
            
            return JsonResponse({
                'status': 'success',
                'message': 'Broken products report updated successfully',
                'redirect_url': reverse_lazy('delivery:broken-order-detail', kwargs={'pk': broken_order.pk})
            })
            
        except Exception as e:
            print(f"Error updating broken order: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


class BrokenOrderApproveView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for approving a broken order"""
    
    def post(self, request, pk):
        try:
            # Get the broken order
            broken_order = get_object_or_404(BrokenOrder, pk=pk)
            
            # Mark as approved
            broken_order.status = 'approved'
            broken_order.updated_by = request.user
            broken_order.save()
            
            messages.success(request, 'Broken products report approved successfully')
            return redirect('delivery:broken-order-detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error approving broken products report: {str(e)}')
            return redirect('delivery:broken-order-detail', pk=pk)


class BrokenOrderRejectView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for rejecting a broken order"""
    
    def post(self, request, pk):
        try:
            # Get the broken order
            broken_order = get_object_or_404(BrokenOrder, pk=pk)
            
            # Mark as rejected
            broken_order.status = 'rejected'
            broken_order.updated_by = request.user
            broken_order.save()
            
            messages.success(request, 'Broken products report rejected')
            return redirect('delivery:broken-order-detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error rejecting broken products report: {str(e)}')
            return redirect('delivery:broken-order-detail', pk=pk)


class BrokenOrderDeleteView(LoginRequiredMixin, DeliveryTeamRequiredMixin, View):
    """View for deleting a broken order"""
    
    def post(self, request, pk):
        try:
            # Get the broken order
            broken_order = get_object_or_404(BrokenOrder, pk=pk)
            
            # Delete the broken order
            broken_order.delete()
            
            messages.success(request, 'Broken products report deleted successfully')
            return redirect('delivery:broken-order-list')
            
        except Exception as e:
            messages.error(request, f'Error deleting broken products report: {str(e)}')
            return redirect('delivery:broken-order-detail', pk=pk)


# API Views for Broken Orders
def get_available_products_for_broken_order(request):
    """API endpoint to get available products for broken order from a loading order"""
    loading_order_id = request.GET.get('loading_order_id')
    
    if not loading_order_id:
        return JsonResponse({
            'status': 'error',
            'error': 'Loading order ID is required'
        }, status=400)
    
    try:
        # Get the loading order
        loading_order = get_object_or_404(LoadingOrder, pk=loading_order_id)
        
        # Get the loading order items
        loading_order_items = loading_order.items.select_related('product').all()
        
        # Format the response
        products = []
        for item in loading_order_items:
            products.append({
                'id': item.product.id,
                'code': item.product.code,
                'name': item.product.name,
                'quantity': float(item.quantity),
                'price': float(item.product.price)
            })
        
        return JsonResponse({
            'status': 'success',
            'products': products
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
