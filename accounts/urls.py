from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/auth/device/", views.device_request),
    path("api/auth/token/", views.device_token),
    path("auth/device/verify/", views.device_verify),
    path("auth/device/success/", views.device_success),
    path("health/", views.health_check),
]
