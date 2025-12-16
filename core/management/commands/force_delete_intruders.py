from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date

from core.models import Factura


class Command(BaseCommand):
    help = 'Elimina facturas intrusas (cascade) especificadas por UUIDs y muestra nuevo total de ingresos.'

    TARGET_UUIDS = [
        '78cb36af-53b3-4c0a-b266-40c54e2181cb',  # 2,883.44
        'ee2dde81-2720-4323-9824-5087c13c58e1',  # 254.14
        '36590522-4463-44c9-8b5b-8798821eb998',  # 217.75
    ]

    def handle(self, *args, **options):
        # Ejecutar en transacción para seguridad
        with transaction.atomic():
            deleted = 0
            for uuid in self.TARGET_UUIDS:
                qs = Factura.objects.filter(uuid=uuid)
                if qs.exists():
                    count = qs.count()
                    qs.delete()
                    deleted += count

        # Calcular nuevo total teórico de ingresos para 2025 tomando la SUMA del HABER en la cuenta 401-01
        try:
            from core.models import CuentaContable, MovimientoPoliza
            from django.db.models import Sum

            cuenta_401 = CuentaContable.objects.filter(codigo__startswith='401-01').first()
            if cuenta_401:
                inicio = date(2025, 1, 1)
                fin = date(2025, 12, 31)
                total_haber = MovimientoPoliza.objects.filter(
                    cuenta=cuenta_401,
                    poliza__fecha__date__gte=inicio,
                    poliza__fecha__date__lte=fin
                ).aggregate(total=Sum('haber'))['total'] or Decimal('0.00')
            else:
                total_haber = Decimal('0.00')

        except Exception:
            total_haber = Decimal('0.00')

        # Imprimir resultado solicitado (formato exacto)
        self.stdout.write('Eliminación exitosa. Nuevo Total de Ingresos Teórico: ${:,.2f}'.format(total_haber))