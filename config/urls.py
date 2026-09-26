from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from core import views as core_views
from dashboard import views as dashboard_views

urlpatterns = [
    path("", include("core.urls")),
    path("products/", include("catalog.urls")),
    path("", include("orders.inquiry_urls")),
    path("order/", include("orders.urls")),
    path("admin/login", core_views.admin_login, name="admin_login"),
    path("admin/login/", core_views.admin_login),
    path("admin/logout", core_views.admin_logout, name="admin_logout"),
    path("admin/logout/", core_views.admin_logout),
    path("admin", dashboard_views.overview, name="dashboard"),
    path("admin/", include("dashboard.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
