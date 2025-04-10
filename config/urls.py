"""
URL configuration for web_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LogoutView
from django.views.generic.base import RedirectView
from web_project.views import SystemView
from apps.authentication.views import AdminDashboardView, LogoutView, AuthLoginBasicView
from apps.admin_dashboard.views import DashboardHomeView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Dashboard urls
    # path('admin_dashboard/', DashboardHomeView.as_view(), name='admin_dashboard'),
    path('admin_dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    # path('sales/dashboard/', apps.sales.views.DashboardView.as_view(), name='sales:dashboard'),
    # path('delivery/dashboard/', delivery_views.DashboardView.as_view(), name='delivery:dashboard'),
    # path('supervisor/dashboard/', supervisor_views.DashboardView.as_view(), name='supervisor:dashboard'),

    # layouts urls
    path("", include("apps.layouts.urls")),

    # Pages urls
    path("", include("apps.pages.urls")),

    # Auth urls
    path("", include("apps.authentication.urls")),

    # Card urls
    # path("", include("apps.cards.urls")),

    # UI urls
    # path("", include("apps.ui.urls")),

    # Extended UI urls
    # path("", include("apps.extended_ui.urls")),

    # Icons urls
    # path("", include("apps.icons.urls")),

    # Forms urls
    # path("", include("apps.forms.urls")),

    # FormLayouts urls
    # path("", include("apps.form_layouts.urls")),

    # Tables urls
    # path("", include("apps.tables.urls")),

    # Seller urls
    path("", include("apps.seller.urls")),

    # Products urls
    path('', include('apps.products.urls', namespace='products')),

    # Sales urls
    path('', include('apps.sales.urls')),

    # Delivery urls
    path('', include('apps.delivery.urls')),
    path('apiapp/', include('apps.api.urls')),
    path('', include('apps.admin_dashboard.urls')),

    path('', RedirectView.as_view(pattern_name='auth-login-basic'), name='index'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
handler404 = SystemView.as_view(template_name="pages_misc_error.html", status=404)
handler400 = SystemView.as_view(template_name="pages_misc_error.html", status=400)
handler500 = SystemView.as_view(template_name="pages_misc_error.html", status=500)
