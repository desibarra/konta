from django.core.management.base import BaseCommand
from core.models import BackgroundTask

class Command(BaseCommand):
    help = 'List BackgroundTask entries'

    def handle(self, *args, **options):
        qs = BackgroundTask.objects.all().order_by('-created_at')[:50]
        if not qs.exists():
            self.stdout.write('No background tasks found')
            return
        for t in qs:
            self.stdout.write(f"ID:{t.id} type:{t.task_type} status:{t.status} attempts:{t.attempts} payload:{t.payload}")
