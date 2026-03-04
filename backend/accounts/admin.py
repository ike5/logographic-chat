from django.contrib import admin
from .models import DeviceCode


@admin.register(DeviceCode)
class DeviceCodeAdmin(admin.ModelAdmin):
    list_display = ["user_code", "device_code", "user", "is_authorized", "created_at", "expires_at"]
    list_filter = ["is_authorized", "created_at"]
    search_fields = ["user_code", "user__username"]
    readonly_fields = ["device_code", "user_code", "created_at", "expires_at"]
