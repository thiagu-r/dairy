from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpResponseBadRequest
from web_project import TemplateLayout
from .models import Route, Seller
import json
from urllib.parse import parse_qs

class RouteListView(LoginRequiredMixin, TemplateView):
    template_name = "seller/route_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['routes'] = Route.objects.all().order_by('-created_at')
        return context

class RouteCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        return render(request, 'seller/route_form.html')
    
    def post(self, request):
        name = request.POST.get('name')
        code = request.POST.get('code')
        
        Route.objects.create(
            name=name,
            code=code,
            created_by=request.user
        )
        
        # Render only the table partial
        response = render(
            request,
            'seller/partials/route_table.html',
            {'routes': Route.objects.all().order_by('-created_at')}
        )
        
        # Add HX-Trigger header
        response['HX-Trigger'] = 'closeModal'
        
        return response

class SellerListView(LoginRequiredMixin, TemplateView):
    template_name = "seller/seller_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['sellers'] = Seller.objects.all().order_by('-created_at')
        context['routes'] = Route.objects.all().order_by('name')  # Added for the form
        return context

class SellerCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        routes = Route.objects.all().order_by('name')
        return render(request, 'seller/seller_form.html', {'routes': routes})
    
    def post(self, request):
        # Create new seller
        seller = Seller.objects.create(
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            mobileno=request.POST.get('mobileno'),
            store_name=request.POST.get('store_name'),
            store_address=request.POST.get('store_address'),
            route_id=request.POST.get('route'),
            created_by=request.user
        )
        
        # Render only the table partial
        response = render(
            request,
            'seller/partials/seller_table.html',
            {'sellers': Seller.objects.all().order_by('-created_at')}
        )
        
        # Add HX-Trigger header to close the modal
        response['HX-Trigger'] = 'closeModal'
        
        return response

class RouteEditFormView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, route_id):
        route = Route.objects.get(id=route_id)
        return render(request, 'seller/route_edit_form.html', {'route': route})

class RouteEditView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def put(self, request, route_id):
        try:
            route = Route.objects.get(id=route_id)
            
            # Parse the PUT data
            body = request.body.decode('utf-8')
            if request.content_type == 'application/json':
                data = json.loads(body)
            else:
                # Parse form data
                data = parse_qs(body)
                # Convert from lists to single values
                data = {k: v[0] for k, v in data.items()}
            
            # Update route fields
            if 'name' not in data or 'code' not in data:
                return HttpResponseBadRequest('Name and code are required')
                
            route.name = data['name']
            route.code = data['code']
            route.updated_by = request.user
            route.save()
            
            # Render only the table partial
            response = render(
                request,
                'seller/partials/route_table.html',
                {'routes': Route.objects.all().order_by('-created_at')}
            )
            
            # Add HX-Trigger header
            response['HX-Trigger'] = 'closeModal'
            
            return response
            
        except Route.DoesNotExist:
            return HttpResponseBadRequest('Route not found')
        except Exception as e:
            return HttpResponseBadRequest(str(e))

class SellerEditFormView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, seller_id):
        seller = Seller.objects.get(id=seller_id)
        routes = Route.objects.all().order_by('name')
        return render(request, 'seller/seller_edit_form.html', {
            'seller': seller,
            'routes': routes
        })

class SellerEditView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def put(self, request, seller_id):
        try:
            seller = Seller.objects.get(id=seller_id)
            
            # Parse the PUT data
            body = request.body.decode('utf-8')
            if request.content_type == 'application/json':
                data = json.loads(body)
            else:
                # Parse form data
                data = parse_qs(body)
                # Convert from lists to single values
                data = {k: v[0] for k, v in data.items()}
            
            # Update seller fields
            required_fields = ['first_name', 'last_name', 'mobileno', 'store_name', 'store_address', 'route']
            if not all(field in data for field in required_fields):
                return HttpResponseBadRequest('All fields are required')
            
            seller.first_name = data['first_name']
            seller.last_name = data['last_name']
            seller.mobileno = data['mobileno']
            seller.store_name = data['store_name']
            seller.store_address = data['store_address']
            seller.route_id = data['route']
            seller.updated_by = request.user
            seller.save()
            
            # Render only the table partial
            response = render(
                request,
                'seller/partials/seller_table.html',
                {'sellers': Seller.objects.all().order_by('-created_at')}
            )
            
            # Add HX-Trigger header
            response['HX-Trigger'] = 'closeModal'
            
            return response
            
        except Seller.DoesNotExist:
            return HttpResponseBadRequest('Seller not found')
        except Exception as e:
            return HttpResponseBadRequest(str(e))
