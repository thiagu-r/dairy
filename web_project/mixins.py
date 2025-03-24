from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

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
        if not self.request.user.is_authenticated:
            return False
            
        # Allow staff and superusers
        if self.request.user.is_staff or self.request.user.is_superuser:
            return True
            
        # Check if user has delivery-related role
        return self.request.user.role in ['DELIVERY', 'SUPERVISOR']

    def handle_no_permission(self):
        raise PermissionDenied("You do not have permission to access this page.")
