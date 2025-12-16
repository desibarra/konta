"""
Management Command: Rebuild Accounting 2025

PROBLEMA CRÍTICO: Sistema en estado inconsistente
- Balanza vacía
- Ingresos inflados ($452k vs $414k esperados)
- Pólizas de facturas canceladas/duplicadas no eliminadas

SOLUCIÓN: Reconstrucción completa con lógica fiscal correcta

PASOS:
1. WIPE: Eliminar TODAS las pólizas de 2025
2. REBUILD: Regenerar solo facturas Vigentes/Sin Validar
3. VERIFY: Verificar que totales coincidan con esperado

Uso:
    python manage.py rebuild_accounting_2025
    python manage.py rebuild_accounting_2025 --dry-run

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Q
from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable
from core.services.accounting_service import AccountingService
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reconstruye TODA la contabilidad de 2025 con lógica fiscal correcta'

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
            help='Año a reconstruir (default: 2025)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options['year']
        
        self.stdout.write(self.style.ERROR('=' * 70))
        self.stdout.write(self.style.ERROR('🔨 RECONSTRUCCIÓN TOTAL DE CONTABILIDAD'))
        self.stdout.write(self.style.ERROR('=' * 70))
        self.stdout.write(f'\n📅 Año: {year}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN'))
        else:
            self.stdout.write(self.style.ERROR('\n🔥 MODO REAL - Se eliminarán y regenerarán datos'))
            confirm = input('\n¿Estás seguro? Escribe "REBUILD" para continuar: ')
            if confirm != 'REBUILD':
                self.stdout.write(self.style.WARNING('\nOperación cancelada'))
                return
        
        # ============================================================
        # PASO 1: LIMPIEZA TOTAL (WIPE)
        # ============================================================
        self.stdout.write('\n\n🗑️  PASO 1: LIMPIEZA TOTAL')
        self.stdout.write('=' * 70)
        
        movimientos_count = MovimientoPoliza.objects.filter(
            poliza__fecha__year=year
        ).count()
        
        polizas_count = Poliza.objects.filter(
            fecha__year=year
        ).count()
        
        self.stdout.write(f'\n📊 Registros a eliminar:')
        self.stdout.write(f'   Movimientos: {movimientos_count:,}')
        self.stdout.write(f'   Pólizas: {polizas_count:,}')
        
        if not dry_run:
            MovimientoPoliza.objects.filter(poliza__fecha__year=year).delete()
            Poliza.objects.filter(fecha__year=year).delete()
            # CRÍTICO: Resetear estado_contable a PENDIENTE
            Factura.objects.filter(
                fecha__year=year,
                naturaleza__in=['I', 'E']
            ).exclude(
                estado_sat='Cancelado'
            ).update(estado_contable='PENDIENTE')
            self.stdout.write(self.style.SUCCESS('\n   ✅ Limpieza completada'))
            self.stdout.write(self.style.SUCCESS('   ✅ Estados reseteados a PENDIENTE'))
        
        # ============================================================
        # PASO 2: REGENERACIÓN SELECTIVA (REBUILD)
        # ============================================================
        self.stdout.write('\n\n♻️  PASO 2: REGENERACIÓN SELECTIVA')
        self.stdout.write('=' * 70)
        
        # Filtrar facturas VIGENTES o SIN VALIDAR (excluir canceladas)
        facturas = Factura.objects.filter(
            fecha__year=year,
            naturaleza__in=['I', 'E']
        ).exclude(
            estado_sat='Cancelado'
        ).order_by('fecha')
        
        total_facturas = facturas.count()
        
        self.stdout.write(f'\n📊 Facturas a procesar: {total_facturas}')
        self.stdout.write(f'   Condición: estado_sat != "Cancelado"')
        
        # Estadísticas
        procesadas = 0
        errores = 0
        
        suma_ventas_subtotal = Decimal('0.00')
        suma_ventas_iva = Decimal('0.00')
        suma_ventas_total = Decimal('0.00')
        
        suma_gastos_subtotal = Decimal('0.00')
        suma_gastos_iva = Decimal('0.00')
        suma_gastos_total = Decimal('0.00')
        
        # Procesar
        for idx, factura in enumerate(facturas, 1):
            try:
                # Progreso
                if idx % 10 == 0 or idx == total_facturas:
                    self.stdout.write(
                        f'   ⏳ {idx}/{total_facturas} ({int(idx/total_facturas*100)}%)',
                        ending='\r'
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
                
                # Contabilizar con lógica fiscal correcta
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
                        f'\n   ❌ Error en {factura.uuid}: {str(e)[:60]}'
                    )
                logger.error(f'Error en {factura.uuid}: {e}', exc_info=True)
        
        self.stdout.write('')  # Nueva línea
        
        # ============================================================
        # PASO 3: VERIFICACIÓN FINAL
        # ============================================================
        self.stdout.write('\n\n📊 VERIFICACIÓN FINAL')
        self.stdout.write('=' * 70)
        
        self.stdout.write(f'\n✅ Facturas procesadas: {procesadas}')
        self.stdout.write(f'❌ Errores: {errores}')
        
        self.stdout.write('\n\n💰 INGRESOS (VENTAS):')
        self.stdout.write(f'   Subtotal (401-01): ${suma_ventas_subtotal:,.2f}')
        self.stdout.write(f'   IVA (208-01):      ${suma_ventas_iva:,.2f}')
        self.stdout.write(f'   Total (105-01):    ${suma_ventas_total:,.2f}')
        
        self.stdout.write('\n📝 EGRESOS (GASTOS):')
        self.stdout.write(f'   Subtotal (601-01): ${suma_gastos_subtotal:,.2f}')
        self.stdout.write(f'   IVA (118-01):      ${suma_gastos_iva:,.2f}')
        self.stdout.write(f'   Total (201-01):    ${suma_gastos_total:,.2f}')
        
        # Verificación contra esperado
        self.stdout.write('\n\n🎯 VERIFICACIÓN CONTRA ESPERADO:')
        esperado = Decimal('414886.64')
        diferencia = abs(suma_ventas_subtotal - esperado)
        
        self.stdout.write(f'   Esperado (Excel):  ${esperado:,.2f}')
        self.stdout.write(f'   Obtenido (Sistema): ${suma_ventas_subtotal:,.2f}')
        self.stdout.write(f'   Diferencia:        ${diferencia:,.2f}')
        
        if diferencia < Decimal('100.00'):
            self.stdout.write(self.style.SUCCESS('   ✅ ¡COINCIDE! (diferencia < $100)'))
        elif diferencia < Decimal('1000.00'):
            self.stdout.write(self.style.WARNING('   ⚠️  Diferencia aceptable (< $1,000)'))
        else:
            self.stdout.write(self.style.ERROR('   ❌ Diferencia significativa'))
        
        # Verificar en base de datos (solo si no es dry-run)
        if not dry_run:
            self.stdout.write('\n\n💾 VERIFICACIÓN EN BASE DE DATOS:')
            
            # Sumar HABER en cuentas 400 (Ventas)
            ventas_db = MovimientoPoliza.objects.filter(
                poliza__fecha__year=year,
                cuenta__codigo__startswith='40'
            ).aggregate(total=Sum('haber'))['total'] or Decimal('0.00')
            
            self.stdout.write(f'   Total Ventas (Cuentas 400): ${ventas_db:,.2f}')
            
            if abs(ventas_db - esperado) < Decimal('100.00'):
                self.stdout.write(self.style.SUCCESS('   ✅ Base de datos CORRECTA'))
            else:
                self.stdout.write(self.style.WARNING(f'   ⚠️  Diferencia: ${abs(ventas_db - esperado):,.2f}'))
        
        # Resumen final
        if dry_run:
            self.stdout.write(self.style.WARNING('\n\n⚠️  DRY-RUN: No se guardaron cambios'))
        else:
            self.stdout.write(self.style.SUCCESS('\n\n✅ Reconstrucción completada'))
            self.stdout.write('\n💡 SIGUIENTE PASO:')
            self.stdout.write('   1. Refresca los reportes en el navegador')
            self.stdout.write('   2. Verifica Balanza de Comprobación')
            self.stdout.write('   3. Verifica Estado de Resultados')
            self.stdout.write('   4. Verifica Balance General')
