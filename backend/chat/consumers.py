import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        message_text = content.get("message", "").strip()
        if not message_text:
            return
        msg = await self.save_message(message_text)
        await self.channel_layer.group_send(self.group_name, {
            "type": "chat.message",
            "message": message_text,
            "username": self.user.username,
            "created_at": msg.created_at.isoformat(),
        })

    async def chat_message(self, event):
        await self.send_json({
            "username": event["username"],
            "message": event["message"],
            "created_at": event["created_at"],
        })

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(room_id=self.room_id, user=self.user, content=content)
