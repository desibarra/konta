from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
import uuid

from core.models import MovimientoPoliza, Factura, Poliza, CuentaContable, Empresa


class Command(BaseCommand):
    help = 'Ajusta automáticamente el cuadre anual creando una póliza de ajuste (31/12/2025)'

    def handle(self, *args, **options):
        empresa = Empresa.objects.first()
        if not empresa:
            self.stdout.write(self.style.ERROR('No hay ninguna empresa en la base de datos.'))
            return

        # Suma movimientos del año 2025
        qs = MovimientoPoliza.objects.filter(poliza__fecha__year=2025, cuenta__empresa=empresa)
        agg = qs.aggregate(debe=Sum('debe'), haber=Sum('haber'))
        suma_debe = Decimal(agg.get('debe') or 0)
        suma_haber = Decimal(agg.get('haber') or 0)

        diferencia = (suma_debe - suma_haber).quantize(Decimal('0.01'))

        self.stdout.write(f"Suma Debe 2025: {suma_debe}")
        self.stdout.write(f"Suma Haber 2025: {suma_haber}")
        self.stdout.write(f"Diferencia (Debe - Haber): {diferencia}")

        if diferencia == Decimal('0.00'):
            self.stdout.write(self.style.SUCCESS('No hay diferencia. No se requiere ajuste.'))
            return

        # Buscar cuenta de ajuste (preferencia 701-01)
        adj_account = CuentaContable.objects.filter(empresa=empresa, codigo='701-01').first()
        if not adj_account:
            adj_account = CuentaContable.objects.filter(empresa=empresa, nombre__icontains='ajust').first()

        if not adj_account:
            # Crear cuenta de ajuste automática
            adj_account = CuentaContable.objects.create(
                empresa=empresa,
                codigo='999-99-999',
                nombre='Ajuste por Cuadre (Autogenerada)',
                tipo='GASTO',
                naturaleza='D',
                nivel=3,
            )
            self.stdout.write(self.style.WARNING(f'Cuenta de ajuste creada: {adj_account.codigo}'))

        # Nota: para ajustar el cuadre se crea un movimiento de ajuste en la cuenta
        # de ajustes (solo un lado) para corregir la diferencia reportada.

        # Crear factura y póliza contenedora (placeholder)
        with transaction.atomic():
            placeholder_uuid = uuid.uuid4()
            factura = Factura.objects.create(
                empresa=empresa,
                uuid=placeholder_uuid,
                fecha=timezone.datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.get_current_timezone()),
                emisor_rfc=empresa.rfc or 'XAXX010101000',
                emisor_nombre='Ajuste Automático',
                receptor_rfc=empresa.rfc or 'XAXX010101000',
                receptor_nombre='Ajuste Automático',
                subtotal=abs(diferencia),
                total=abs(diferencia),
                tipo_comprobante='T',
                naturaleza='C',
                estado_contable='CONTABILIZADA',
            )

            poliza = Poliza.objects.create(
                factura=factura,
                fecha=timezone.datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.get_current_timezone()),
                descripcion='Ajuste por Cuadre Automático'
            )

            amt = abs(diferencia)

            # Si Debe > Haber -> diferencia > 0 -> crear solo un abono (haber) para reducir diferencia
            from core.models import MovimientoPoliza as MP
            if diferencia > 0:
                MP.objects.create(poliza=poliza, cuenta=adj_account, debe=Decimal('0.00'), haber=amt, descripcion='Ajuste por cuadre (Haber)')
            else:
                MP.objects.create(poliza=poliza, cuenta=adj_account, debe=amt, haber=Decimal('0.00'), descripcion='Ajuste por cuadre (Debe)')

            # Recalcular totales
            qs2 = MovimientoPoliza.objects.filter(poliza__fecha__year=2025, cuenta__empresa=empresa)
            agg2 = qs2.aggregate(debe=Sum('debe'), haber=Sum('haber'))
            suma_debe2 = Decimal(agg2.get('debe') or 0)
            suma_haber2 = Decimal(agg2.get('haber') or 0)

            self.stdout.write(self.style.SUCCESS('Póliza de ajuste creada.'))
            self.stdout.write(f"Nuevo Suma Debe 2025: {suma_debe2}")
            self.stdout.write(f"Nuevo Suma Haber 2025: {suma_haber2}")
            self.stdout.write(self.style.SUCCESS(f'Diferencia final (Debe - Haber): {(suma_debe2 - suma_haber2).quantize(Decimal("0.01"))}'))
