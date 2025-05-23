from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.is_staff or 
            self.request.user.is_superuser or 
            self.request.user.role in ['ADMIN', 'CEO', 'MANAGER']
        )

    def handle_no_permission(self):
        raise PermissionDenied("You do not have permission to access this page.")

class SalesTeamRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.is_staff or 
            self.request.user.is_superuser or 
            self.request.user.groups.filter(name='Sales Team').exists()
        )

    def handle_no_permission(self):
        raise PermissionDenied("You do not have permission to access this page.")

class DeliveryTeamRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        print('role:', self.request.user.role)
        if not self.request.user.is_authenticated:
            return redirect('auth-login-basic')
            
        # Allow staff and superusers
        if self.request.user.is_staff or self.request.user.is_superuser:
            return True
            
        # Check if user has delivery-related role
        return self.request.user.role in ['DELIVERY', 'SUPERVISOR', 'DISTRIBUTOR']

    def handle_no_permission(self):
        print('role  :', self.request.user.role)
        raise PermissionDenied("You do not have permission to access this page.")
