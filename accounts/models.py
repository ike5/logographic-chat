import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


def generate_device_code():
    return secrets.token_urlsafe(32)


def generate_user_code():
    return secrets.token_urlsafe(4).upper()[:8]


def default_expiry():
    return timezone.now() + timedelta(minutes=15)


class DeviceCode(models.Model):
    device_code = models.CharField(max_length=64, unique=True, default=generate_device_code)
    user_code = models.CharField(max_length=8, unique=True, default=generate_user_code)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)
    is_authorized = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
