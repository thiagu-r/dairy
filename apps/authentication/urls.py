from django.urls import path
from .views import (
    AuthLoginBasicView,
    RegisterView,
    CustomPasswordResetView,
)

urlpatterns = [
    path('login/', AuthLoginBasicView.as_view(), name='auth-login-basic'),
    path('register/', RegisterView.as_view(), name='auth-register-basic'),
    path('forgot-password/', CustomPasswordResetView.as_view(), name='auth-forgot-password-basic'),
]
