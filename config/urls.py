from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from cracks.accounts import signup

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/signup/", signup, name="signup"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("cracks.urls")),
]

# Serve uploaded photos while developing. In production a web server or cloud storage does this.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
