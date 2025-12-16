from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Encola una factura de prueba (ya contabilizada) para verificar el worker.'

    def handle(self, *args, **options):
        from core.models import Factura, BackgroundTask

        # Intentar encontrar una factura ya contabilizada
        fact = Factura.objects.filter(estado_contable='CONTABILIZADA').first()

        if not fact:
            # Si no existe, tomar la primera factura y marcarla como contabilizada
            fact = Factura.objects.first()
            if not fact:
                self.stderr.write('No hay facturas en la base de datos para usar en la prueba.')
                return
            fact.estado_contable = 'CONTABILIZADA'
            fact.save()
            self.stdout.write(f'No existía factura CONTABILIZADA; marcada la factura {fact.uuid} como CONTABILIZADA para la prueba.')

        task = BackgroundTask.objects.create(
            task_type='contabilizar_factura',
            payload={'factura_uuid': str(fact.uuid)},
            status='PENDING'
        )

        self.stdout.write(f'Encolada factura {fact.uuid} como tarea id={task.id}.')
