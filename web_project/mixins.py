from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

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