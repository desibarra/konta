from django.core.management.base import BaseCommand
from core.models import BackgroundTask
from core.services.accounting_service import AccountingService
from core.tasks import mark_started, mark_completed, mark_failed
from django.db import transaction
import time
import traceback


class Command(BaseCommand):
    help = 'Run background worker that processes contabilizacion tasks from DB'

    def handle(self, *args, **options):
        self.stdout.write('Starting contabilizacion worker (polling DB every 3s)...')
        try:
            while True:
                # Fetch next pending task
                task = None
                try:
                    with transaction.atomic():
                        task = BackgroundTask.objects.select_for_update(skip_locked=True).filter(status='PENDING').order_by('created_at').first()
                        if task:
                            mark_started(task)
                except Exception as e:
                    # DB may be locked or skip_locked not supported; fallback
                    task = BackgroundTask.objects.filter(status='PENDING').order_by('created_at').first()
                    if task:
                        mark_started(task)

                if not task:
                    time.sleep(3)
                    continue

                try:
                    payload = task.payload or {}
                    if task.task_type == 'contabilizar_factura':
                        factura_uuid = payload.get('factura_uuid')
                        usuario_id = payload.get('usuario_id')
                        # Ejecutar contabilización
                        try:
                            AccountingService.contabilizar_factura(factura_uuid, usuario_id=usuario_id)
                            mark_completed(task)
                            self.stdout.write(f"Processed task {task.id} factura {factura_uuid}")
                        except ValueError as ve:
                            msg = str(ve or '').lower()
                            if 'ya está contabilizada' in msg or 'ya esta contabilizada' in msg or 'ya está contabilizado' in msg:
                                # Factura already processed — mark as completed and continue
                                mark_completed(task)
                                self.stdout.write(f"WARNING: Factura ya procesada, saltando task {task.id} (factura {factura_uuid})")
                            else:
                                # Other ValueError: treat as failure
                                tb = ve
                                mark_failed(task, tb)
                                self.stderr.write(f"Error processing task {task.id}: {ve}\n")
                        
                    else:
                        mark_failed(task, f"Unknown task_type: {task.task_type}")
                except Exception as e:
                    tb = traceback.format_exc()
                    mark_failed(task, tb)
                    self.stderr.write(f"Error processing task {task.id}: {e}\n{tb}")

        except KeyboardInterrupt:
            self.stdout.write('Worker stopped by user')
