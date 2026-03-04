from django.shortcuts import render, get_object_or_404, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import DeviceCode


@api_view(["POST"])
@permission_classes([AllowAny])
def device_request(request):
    """CLI calls this to start the auth flow."""
    dc = DeviceCode.objects.create()
    return Response({
        "device_code": dc.device_code,
        "user_code": dc.user_code,
        "verification_url": f"{request.scheme}://{request.get_host()}/auth/device/verify/",
        "expires_in": 900,
        "interval": 5,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def device_token(request):
    """CLI polls this until the user authorizes in the browser."""
    device_code = request.data.get("device_code")
    try:
        dc = DeviceCode.objects.get(device_code=device_code)
    except DeviceCode.DoesNotExist:
        return Response({"error": "invalid_device_code"}, status=400)

    if dc.is_expired:
        return Response({"error": "expired_token"}, status=400)

    if not dc.is_authorized or dc.user is None:
        return Response({"error": "authorization_pending"}, status=428)

    refresh = RefreshToken.for_user(dc.user)
    username = dc.user.username
    dc.delete()  # Single use
    return Response({
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "username": username,
    })


def device_success(request):
    """Landing page after allauth login; resumes pending device authorization."""
    user_code = request.session.pop("pending_device_code", None)
    if user_code and request.user.is_authenticated:
        try:
            dc = DeviceCode.objects.get(user_code=user_code)
            if not dc.is_expired:
                dc.user = request.user
                dc.is_authorized = True
                dc.save()
                return render(request, "accounts/auth_success.html")
        except DeviceCode.DoesNotExist:
            pass
    return render(request, "accounts/auth_success.html")


def device_verify(request):
    """Browser page where user enters their user_code then logs in."""
    if request.method == "GET":
        code = request.GET.get("code", "")
        return render(request, "accounts/verify_device.html", {"code": code})

    if request.method == "POST":
        user_code = request.POST.get("user_code", "").strip().upper()
        confirm = request.POST.get("confirm")

        try:
            dc = DeviceCode.objects.get(user_code=user_code)
        except DeviceCode.DoesNotExist:
            return render(request, "accounts/verify_device.html", {"error": "Invalid code."})

        if dc.is_expired:
            return render(request, "accounts/verify_device.html", {
                "error": "Code expired. Try again from the terminal."
            })

        if not request.user.is_authenticated:
            request.session["pending_device_code"] = user_code
            return redirect(f"/accounts/login/?next=/auth/device/verify/?code={user_code}")

        if not confirm:
            return render(request, "accounts/verify_device.html", {
                "confirm_user": request.user.username,
                "user_code": user_code,
            })

        dc.user = request.user
        dc.is_authorized = True
        dc.save()
        return render(request, "accounts/auth_success.html")
