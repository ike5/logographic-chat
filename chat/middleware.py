from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = dict(
            x.split("=") for x in scope["query_string"].decode().split("&") if "=" in x
        )
        token = query.get("token")
        scope["user"] = await self.get_user(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, raw_token):
        try:
            validated = AccessToken(raw_token)
            return User.objects.get(id=validated["user_id"])
        except Exception:
            return AnonymousUser()
