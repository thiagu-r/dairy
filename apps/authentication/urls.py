from django.urls import path
from .views import (
    AuthLoginBasicView,
    RegisterView,
    CustomPasswordResetView,
    UserListView,
    UserCreateView,
    UserCreateFormView,
    UserEditView,
)

urlpatterns = [
    path('login/', AuthLoginBasicView.as_view(), name='auth-login-basic'),
    path('register/', RegisterView.as_view(), name='auth-register-basic'),
    path('forgot-password/', CustomPasswordResetView.as_view(), name='auth-forgot-password-basic'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/create/', UserCreateView.as_view(), name='user-create'),
    path('users/create-form/', UserCreateFormView.as_view(), name='user-create-form'),
    path('users/<int:user_id>/edit/', UserEditView.as_view(), name='user-edit'),
    path('users/<int:user_id>/edit-form/', UserEditView.as_view(), name='user-edit-form'),
]
