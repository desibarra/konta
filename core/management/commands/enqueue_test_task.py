from django.core.management.base import BaseCommand
from core.models import Factura
from core.tasks import enqueue_contabilizar


class Command(BaseCommand):
    help = 'Enqueue a test contabilizacion task for first pending factura (estado_contable=\'PENDIENTE\')'

    def handle(self, *args, **options):
        factura = Factura.objects.filter(estado_contable='PENDIENTE').order_by('fecha').first()
        if not factura:
            factura = Factura.objects.all().order_by('fecha').first()
            if not factura:
                self.stderr.write('No hay facturas en la base de datos para encolar.')
                return
        task_id = enqueue_contabilizar(factura.uuid, usuario_id=None)
        self.stdout.write(f'Enqueued task {task_id} for factura {factura.uuid}')
