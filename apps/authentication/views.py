from django.views.generic import TemplateView, CreateView
from django.contrib.auth import login, logout
from django.contrib.auth.views import PasswordChangeView, PasswordResetView, PasswordResetConfirmView, LoginView, LogoutView as BaseLogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from web_project import TemplateLayout
from web_project.template_helpers.theme import TemplateHelper
from .forms import UserRegistrationForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CustomPasswordChangeForm, CustomPasswordResetForm
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, View
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from web_project import TemplateLayout
from .models import CustomUser, Role  # Add Role to imports
import json

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.role == 'ADMIN'

class UserListView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "authentication/user_list.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['users'] = CustomUser.objects.all().order_by('-date_joined')
        return context

class UserCreateFormView(LoginRequiredMixin, AdminRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request):
        return render(request, 'authentication/partials/user_modal.html', {
            'user': None,
            'roles': Role.choices  # Pass all roles to template
        })

class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')
    
    def post(self, request):
        try:
            user = CustomUser.objects.create_user(
                username=request.POST.get('username'),
                email=request.POST.get('email'),
                password=request.POST.get('password'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                mobile_number=request.POST.get('mobile_number'),
                role=request.POST.get('role'),
                is_active=request.POST.get('is_active') == 'on'
            )
            
            response = render(
                request,
                'authentication/partials/user_table.html',
                {'users': CustomUser.objects.all().order_by('-date_joined')}
            )
            
            response['HX-Trigger'] = json.dumps({
                'closeModal': True,
                'showMessage': 'User created successfully',
                'refreshPage': True  # Add this to trigger page refresh
            })
            
            return response
        except Exception as e:
            return render(
                request,
                'authentication/partials/user_modal.html',
                {'error': str(e), 'user': None},
                status=400
            )

class UserEditView(LoginRequiredMixin, AdminRequiredMixin, View):
    login_url = reverse_lazy('auth-login-basic')

    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            return render(request, 'authentication/partials/user_modal.html', {
                'user': user,
                'roles': Role.choices  # Pass all roles to template
            })
        except CustomUser.DoesNotExist:
            raise Http404("User does not exist")

    def post(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.mobile_number = request.POST.get('mobile_number')
            user.role = request.POST.get('role')
            user.is_active = request.POST.get('is_active') == 'on'
            
            if request.POST.get('password'):
                user.set_password(request.POST.get('password'))
            
            user.save()
            
            response = render(
                request,
                'authentication/partials/user_table.html',
                {'users': CustomUser.objects.all().order_by('-date_joined')}
            )
            
            response['HX-Trigger'] = json.dumps({
                'closeModal': True,
                'showMessage': 'User updated successfully',
                'refreshPage': True  # Add this to trigger page refresh
            })
            
            return response
        except CustomUser.DoesNotExist:
            raise Http404("User does not exist")
        except Exception as e:
            return render(
                request,
                'authentication/partials/user_modal.html',
                {'error': str(e), 'user': user},
                status=400
            )

class AuthLoginBasicView(LoginView):
    template_name = 'auth_login_basic.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        # Get the 'next' parameter if it exists
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url

        # Role-based redirects
        user = self.request.user
        if user.role == 'DELIVERY':
            return reverse_lazy('delivery:dashboard')
        elif user.role == 'SALES':
            return reverse_lazy('sales:dashboard')
        elif user.role in ['ADMIN', 'CEO', 'MANAGER']:
            return reverse_lazy('admin_dashboard')  # Changed from 'index'
        elif user.role == 'SUPERVISOR':
            return reverse_lazy('supervisor:dashboard')
        
        # Default fallback
        return reverse_lazy('auth-login-basic')

    def get(self, request, *args, **kwargs):
        next_url = request.GET.get('next')
        
        if request.headers.get('HX-Request'):
            return render(request, 'auth_login_modal.html', {'next': next_url})
        
        context = self.get_context_data()
        context['next'] = next_url 
        response = render(request, self.template_name, context)       
        return response

    def form_valid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(self.request, user)
                next_url = self.request.POST.get('next') or self.get_success_url()
                return JsonResponse({
                    'success': True,
                    'next': next_url
                })
            return JsonResponse({
                'success': False,
                'errors': 'Invalid credentials'
            })
        
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = TemplateLayout.init(self, context)
        context.update({
            'layout_path': TemplateHelper.set_layout('layout_blank.html', context),
            'app_name': 'Dairy Sales',
            'page_title': 'Login',
            'next': self.request.GET.get('next')
        })
        return context

class RegisterView(CreateView):
    template_name = 'auth_register_basic.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context.update({
            'layout_path': TemplateHelper.set_layout('layout_blank.html', context),
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response



class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'auth_change_password.html'
    success_url = reverse_lazy('password-change-done')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context.update({
            'layout_path': TemplateHelper.set_layout('layout_blank.html', context),
        })
        return context

class CustomPasswordResetView(PasswordResetView):
    template_name = 'auth_forgot_password_basic.html'
    email_template_name = 'auth_reset_password_email.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('password-reset-done')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context.update({
            'layout_path': TemplateHelper.set_layout('layout_blank.html', context),
        })
        return context

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "authentication/dashboard.html"
    login_url = reverse_lazy('auth-login-basic')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Add dashboard statistics and data here
        context.update({
            'total_users': CustomUser.objects.count(),
            'active_users': CustomUser.objects.filter(is_active=True).count(),
            'admin_users': CustomUser.objects.filter(role='ADMIN').count(),
            'sales_users': CustomUser.objects.filter(role='SALES').count(),
            'delivery_users': CustomUser.objects.filter(role='DELIVERY').count(),
        })
        
        return context

class LogoutView(BaseLogoutView):
    next_page = 'auth-login-basic'
    template_name = 'pages/authentication-logout.html'
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        # Perform logout
        logout(request)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # After logout, redirect to login page
        if not request.user.is_authenticated:
            return redirect('auth-login-basic')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Bharat'  # Replace with your actual app name
        return context
