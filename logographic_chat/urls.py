"""
URL configuration for logographic_chat project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("accounts.urls")),
    path("api/", include("chat.urls")),
    path("api/token/refresh/", TokenRefreshView.as_view()),
]
