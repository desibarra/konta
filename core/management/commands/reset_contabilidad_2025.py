"""
Management Command: Reset Contabilidad 2025 (NUCLEAR)

ADVERTENCIA: Este comando ELIMINA TODA la contabilidad del año 2025
y la regenera desde cero con la lógica correcta.

Uso:
    python manage.py reset_contabilidad_2025
    python manage.py reset_contabilidad_2025 --dry-run

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Factura, Poliza, MovimientoPoliza, Empresa
from core.services.accounting_service import AccountingService
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'RESET NUCLEAR: Elimina y regenera TODA la contabilidad de 2025'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula sin guardar cambios',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=2025,
            help='Año a re-procesar (default: 2025)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options['year']
        
        self.stdout.write(self.style.ERROR('=' * 70))
        self.stdout.write(self.style.ERROR('⚠️  RESET NUCLEAR DE CONTABILIDAD'))
        self.stdout.write(self.style.ERROR('=' * 70))
        self.stdout.write(f'\\n📅 Año: {year}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\\n⚠️  MODO DRY-RUN (no se guardarán cambios)'))
        else:
            self.stdout.write(self.style.ERROR('\\n🔥 MODO REAL - Se eliminarán datos'))
            confirm = input('\\n¿Estás seguro? Escribe "SI" para continuar: ')
            if confirm != 'SI':
                self.stdout.write(self.style.WARNING('\\nOperación cancelada'))
                return
        
        # PASO 1: ELIMINAR PÓLIZAS
        self.stdout.write(f'\\n🗑️  PASO 1: Eliminando pólizas de {year}...')
        
        movimientos_count = MovimientoPoliza.objects.filter(
            poliza__fecha__year=year
        ).count()
        
        polizas_count = Poliza.objects.filter(
            fecha__year=year
        ).count()
        
        self.stdout.write(f'   📊 Movimientos a eliminar: {movimientos_count}')
        self.stdout.write(f'   📊 Pólizas a eliminar: {polizas_count}')
        
        if not dry_run:
            MovimientoPoliza.objects.filter(poliza__fecha__year=year).delete()
            Poliza.objects.filter(fecha__year=year).delete()
            self.stdout.write(self.style.SUCCESS('   ✅ Eliminación completada'))
        
        # PASO 2: RESETEAR FACTURAS
        self.stdout.write(f'\\n🔄 PASO 2: Reseteando facturas de {year}...')
        
        facturas = Factura.objects.filter(
            fecha__year=year,
            naturaleza__in=['I', 'E']
        )
        
        total_facturas = facturas.count()
        self.stdout.write(f'   📊 Facturas a resetear: {total_facturas}')
        
        if not dry_run:
            facturas.update(estado_contable='PENDIENTE')
            self.stdout.write(self.style.SUCCESS('   ✅ Reset completado'))
        
        # PASO 3: RE-CONTABILIZAR
        self.stdout.write(f'\\n♻️  PASO 3: Re-contabilizando {total_facturas} facturas...')
        
        procesadas = 0
        errores = 0
        
        # Estadísticas
        suma_ventas_subtotal = Decimal('0.00')
        suma_ventas_iva = Decimal('0.00')
        suma_ventas_total = Decimal('0.00')
        
        suma_gastos_subtotal = Decimal('0.00')
        suma_gastos_iva = Decimal('0.00')
        suma_gastos_total = Decimal('0.00')
        
        for idx, factura in enumerate(facturas, 1):
            try:
                # Progreso
                if idx % 10 == 0 or idx == total_facturas:
                    self.stdout.write(
                        f'   ⏳ {idx}/{total_facturas} ({int(idx/total_facturas*100)}%)',
                        ending='\\r'
                    )
                
                # Acumular estadísticas
                if factura.naturaleza == 'I':
                    suma_ventas_subtotal += factura.subtotal
                    suma_ventas_iva += factura.total_impuestos_trasladados
                    suma_ventas_total += factura.total
                else:  # 'E'
                    suma_gastos_subtotal += factura.subtotal
                    suma_gastos_iva += factura.total_impuestos_trasladados
                    suma_gastos_total += factura.total
                
                # Contabilizar
                if not dry_run:
                    poliza = AccountingService.contabilizar_factura(
                        factura.uuid,
                        usuario_id=None
                    )
                    procesadas += 1
                else:
                    procesadas += 1
            
            except Exception as e:
                errores += 1
                if errores <= 5:
                    self.stdout.write(
                        f'\\n   ❌ Error en {factura.uuid}: {str(e)[:60]}'
                    )
                logger.error(f'Error en {factura.uuid}: {e}', exc_info=True)
        
        self.stdout.write('')  # Nueva línea
        
        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS('\\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        self.stdout.write(f'\\n✅ Facturas procesadas: {procesadas}')
        self.stdout.write(f'❌ Errores: {errores}')
        
        self.stdout.write('\\n💰 INGRESOS (VENTAS):')
        self.stdout.write(f'   Subtotal (401-01): ${suma_ventas_subtotal:,.2f}')
        self.stdout.write(f'   IVA (208-01):      ${suma_ventas_iva:,.2f}')
        self.stdout.write(f'   Total (105-01):    ${suma_ventas_total:,.2f}')
        
        self.stdout.write('\\n📝 EGRESOS (GASTOS):')
        self.stdout.write(f'   Subtotal (601-01): ${suma_gastos_subtotal:,.2f}')
        self.stdout.write(f'   IVA (118-01):      ${suma_gastos_iva:,.2f}')
        self.stdout.write(f'   Total (201-01):    ${suma_gastos_total:,.2f}')
        
        self.stdout.write('\\n🎯 VERIFICACIÓN:')
        self.stdout.write(f'   Suma Ventas Subtotal debe ser: $414,886.64')
        self.stdout.write(f'   Suma actual:                   ${suma_ventas_subtotal:,.2f}')
        
        diferencia = abs(Decimal('414886.64') - suma_ventas_subtotal)
        if diferencia < Decimal('1.00'):
            self.stdout.write(self.style.SUCCESS('   ✅ ¡COINCIDE!'))
        else:
            self.stdout.write(self.style.ERROR(f'   ❌ Diferencia: ${diferencia:,.2f}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\\n⚠️  DRY-RUN: No se guardaron cambios'))
        else:
            self.stdout.write(self.style.SUCCESS('\\n✅ Re-contabilización completada'))
            self.stdout.write('\\n💡 Ahora refresca los reportes en el navegador')
