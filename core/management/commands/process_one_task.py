from django.core.management.base import BaseCommand
from django.db import transaction
import traceback


class Command(BaseCommand):
    help = 'Procesa una tarea pendiente de BackgroundTask (una sola) y sale.'

    def handle(self, *args, **options):
        from core.models import BackgroundTask
        from core.tasks import mark_started, mark_completed, mark_failed
        from core.services.accounting_service import AccountingService

        try:
            with transaction.atomic():
                task = BackgroundTask.objects.select_for_update(skip_locked=True).filter(status='PENDING').order_by('created_at').first()
                if not task:
                    self.stdout.write('No hay tareas PENDING en la cola.')
                    return
                mark_started(task)

            payload = task.payload or {}
            if task.task_type == 'contabilizar_factura':
                factura_uuid = payload.get('factura_uuid')
                try:
                    AccountingService.contabilizar_factura(factura_uuid, usuario_id=payload.get('usuario_id'))
                    mark_completed(task)
                    self.stdout.write(f'Processed task {task.id} factura {factura_uuid}')
                except ValueError as ve:
                    msg = str(ve or '').lower()
                    if 'ya está contabilizada' in msg or 'ya esta contabilizada' in msg or 'ya está contabilizado' in msg:
                        mark_completed(task)
                        self.stdout.write(f'WARNING: Factura ya procesada, saltando task {task.id} (factura {factura_uuid})')
                    else:
                        tb = traceback.format_exc()
                        mark_failed(task, tb)
                        self.stderr.write(f'Error processing task {task.id}: {ve}\n{tb}')
            else:
                mark_failed(task, f'Unknown task_type: {task.task_type}')
                self.stderr.write(f'Unknown task_type: {task.task_type}')

        except Exception as e:
            tb = traceback.format_exc()
            self.stderr.write(f'Unexpected error in process_one_task: {e}\n{tb}')
