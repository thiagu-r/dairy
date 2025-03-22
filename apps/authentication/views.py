from django.views.generic import TemplateView, CreateView
from django.contrib.auth import login
from django.contrib.auth.views import PasswordChangeView, PasswordResetView, PasswordResetConfirmView, LoginView
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
class AuthLoginBasicView(LoginView):
    template_name = 'auth_login_basic.html'
    success_url = reverse_lazy('index')
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        next_url = request.GET.get('next')
        print('request.headers: ', request.headers)
        print('next_url: ', next_url)
        if request.headers.get('HX-Request'):
            return render(request, 'auth_login_modal.html', {'next': next_url})
        
        # For regular requests, render the full login page
        context = self.get_context_data()
        context['next'] = next_url
        print('Final context:', context)
        print('Layout path:', context.get('layout_path'))


        response = render(request, self.template_name, context)
        print("Rendering template:", self.template_name)
    
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
