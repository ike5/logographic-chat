from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Room


@receiver(post_delete, sender=Room)
def recreate_default_rooms(sender, **kwargs):
    """Recreate default rooms if they get deleted"""
    # Use transaction.on_commit to avoid recursion issues
    transaction.on_commit(_recreate_default_rooms)


def _recreate_default_rooms():
    """Actual function to recreate default rooms"""
    # Check if any default rooms exist
    default_rooms = ["general", "questions"]
    existing_rooms = Room.objects.filter(name__in=default_rooms).values_list('name', flat=True)

    # Create rooms that don't exist
    for room_name in default_rooms:
        if room_name not in existing_rooms:
            Room.objects.create(name=room_name)