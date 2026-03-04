from django.urls import path
from . import views

urlpatterns = [
    path("rooms/", views.RoomListView.as_view()),
    path("rooms/<int:room_id>/messages/", views.MessageListView.as_view()),
]
