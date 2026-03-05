from rest_framework import generics
from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer


class RoomListView(generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(
            room_id=self.kwargs["room_id"]
        ).select_related("user").order_by("-created_at")[:50]
