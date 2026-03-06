from django.core.management.base import BaseCommand
from chat.models import Room


class Command(BaseCommand):
    help = "Create default rooms if they don't exist"

    def handle(self, *args, **options):
        # Create the default rooms
        general_room, created_general = Room.objects.get_or_create(name="general")
        if created_general:
            self.stdout.write(
                self.style.SUCCESS('Created "general" room')
            )
        else:
            self.stdout.write('Room "general" already exists')

        questions_room, created_questions = Room.objects.get_or_create(name="questions")
        if created_questions:
            self.stdout.write(
                self.style.SUCCESS('Created "questions" room')
            )
        else:
            self.stdout.write('Room "questions" already exists')