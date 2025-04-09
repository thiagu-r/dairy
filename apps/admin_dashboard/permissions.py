from rest_framework import permissions
from apps.authentication.models import Role

class IsAdminOrCEOUser(permissions.BasePermission):
    """
    Custom permission to only allow users with 'ADMIN' or 'CEO' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in [Role.ADMIN, Role.CEO]
        )

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow users with 'ADMIN' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == Role.ADMIN
        )

class IsCEOUser(permissions.BasePermission):
    """
    Custom permission to only allow users with 'CEO' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == Role.CEO
        )

class IsManagerUser(permissions.BasePermission):
    """
    Custom permission to only allow users with 'MANAGER' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == Role.MANAGER
        )
