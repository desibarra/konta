from .models import BackgroundTask
from django.utils import timezone
import json


def enqueue_contabilizar(factura_uuid, usuario_id=None):
    """Crea una tarea en BD para contabilizar una factura."""
    payload = {
        'factura_uuid': str(factura_uuid),
        'usuario_id': usuario_id
    }
    task = BackgroundTask.objects.create(
        task_type='contabilizar_factura',
        payload=payload,
        status='PENDING'
    )
    return task.id


def mark_started(task):
    task.status = 'IN_PROGRESS'
    task.started_at = timezone.now()
    task.attempts = (task.attempts or 0) + 1
    task.save()


def mark_completed(task):
    task.status = 'COMPLETED'
    task.finished_at = timezone.now()
    task.save()


def mark_failed(task, error_text):
    task.status = 'FAILED'
    task.error = (task.error or '') + "\n" + str(error_text)
    task.finished_at = timezone.now()
    task.save()
