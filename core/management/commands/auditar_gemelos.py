"""
Management Command: Auditar Facturas Gemelas

PROBLEMA: Facturas con montos idénticos y fechas cercanas pueden ser:
- Factura original + Factura sustituta (una debe estar cancelada)
- Duplicados accidentales

SOLUCIÓN: Detecta "gemelos" y valida con SAT cuál está vigente.

Uso:
    python manage.py auditar_gemelos
    python manage.py auditar_gemelos --dry-run
    python manage.py auditar_gemelos --tolerance=0.01

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from core.models import Factura, Poliza, MovimientoPoliza
from core.services.sat_status import SatStatusValidator
from decimal import Decimal
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Detecta facturas gemelas (mismo monto) y valida su estatus en SAT'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula sin eliminar nada',
        )
        parser.add_argument(
            '--tolerance',
            type=float,
            default=0.01,
            help='Tolerancia para considerar montos iguales (default: 0.01)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Días de diferencia para considerar fechas cercanas (default: 30)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tolerance = Decimal(str(options['tolerance']))
        days_diff = options['days']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('🔍 AUDITORÍA DE FACTURAS GEMELAS'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN'))
        
        self.stdout.write(f'\n📊 Parámetros:')
        self.stdout.write(f'   Tolerancia monto: ${tolerance}')
        self.stdout.write(f'   Días diferencia: {days_diff}')
        
        # PASO 1: Buscar facturas con montos idénticos
        self.stdout.write('\n\n🔍 PASO 1: Buscando facturas con montos idénticos...')
        
        facturas = Factura.objects.filter(
            naturaleza='I',  # Solo ingresos
            fecha__year=2025
        ).order_by('subtotal', 'fecha')
        
        gemelos_encontrados = []
        facturas_procesadas = set()
        
        for factura in facturas:
            if factura.id in facturas_procesadas:
                continue
            
            # Buscar facturas con monto similar y fecha cercana
            fecha_min = factura.fecha - timedelta(days=days_diff)
            fecha_max = factura.fecha + timedelta(days=days_diff)
            
            subtotal_min = factura.subtotal - tolerance
            subtotal_max = factura.subtotal + tolerance
            
            gemelos = Factura.objects.filter(
                naturaleza='I',
                fecha__gte=fecha_min,
                fecha__lte=fecha_max,
                subtotal__gte=subtotal_min,
                subtotal__lte=subtotal_max
            ).exclude(id=factura.id)
            
            if gemelos.exists():
                grupo = [factura] + list(gemelos)
                gemelos_encontrados.append(grupo)
                
                # Marcar como procesadas
                for f in grupo:
                    facturas_procesadas.add(f.id)
        
        if not gemelos_encontrados:
            self.stdout.write(self.style.SUCCESS('\n✅ No se encontraron facturas gemelas'))
            return
        
        self.stdout.write(f'\n❌ Se encontraron {len(gemelos_encontrados)} grupos de gemelos')
        
        # PASO 2: Validar cada grupo con SAT
        self.stdout.write('\n\n🌐 PASO 2: Validando estatus en SAT...')
        
        total_canceladas = 0
        total_polizas_eliminadas = 0
        suma_descontada = Decimal('0.00')
        
        for idx, grupo in enumerate(gemelos_encontrados, 1):
            self.stdout.write(f'\n\n📋 Grupo {idx}/{len(gemelos_encontrados)}:')
            self.stdout.write(f'   Monto: ${grupo[0].subtotal:,.2f}')
            self.stdout.write(f'   Facturas: {len(grupo)}')
            
            # Validar cada factura del grupo
            for factura in grupo:
                self.stdout.write(f'\n   🔍 Validando {str(factura.uuid)[:36]}...')
                fecha_str = factura.fecha.strftime('%Y-%m-%d')
                self.stdout.write(f'      Fecha: {fecha_str}')
                self.stdout.write(f'      Emisor: {factura.emisor_nombre[:40]}')
                self.stdout.write(f'      Estado actual: {factura.estado_contable}')
                
                # Consultar SAT
                resultado = SatStatusValidator.validar_factura_model(factura)
                
                estado_sat = resultado['estado']
                self.stdout.write(f'      Estado SAT: {estado_sat}')
                
                # Si está cancelada, eliminar su contabilidad
                if estado_sat == 'Cancelado':
                    self.stdout.write(self.style.ERROR(f'      ❌ FACTURA CANCELADA DETECTADA'))
                    
                    # Buscar pólizas
                    polizas = Poliza.objects.filter(factura=factura)
                    
                    if polizas.exists():
                        polizas_count = polizas.count()
                        self.stdout.write(f'         └─ Eliminando {polizas_count} póliza(s)...')
                        
                        if not dry_run:
                            # Eliminar movimientos
                            MovimientoPoliza.objects.filter(poliza__in=polizas).delete()
                            # Eliminar pólizas
                            polizas.delete()
                            # Actualizar estado
                            factura.estado_contable = 'EXCLUIDA'
                            factura.save()
                        
                        total_polizas_eliminadas += polizas_count
                    
                    total_canceladas += 1
                    suma_descontada += factura.subtotal
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'         ✅ Factura descontada: ${factura.subtotal:,.2f}'
                    ))
                
                elif estado_sat == 'Vigente':
                    self.stdout.write(self.style.SUCCESS(f'      ✅ Factura vigente'))
                
                elif estado_sat == 'Error':
                    mensaje = resultado.get('mensaje', 'Error desconocido')
                    self.stdout.write(self.style.WARNING(
                        f'      ⚠️  Error al consultar: {mensaje}'
                    ))
        
        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS('\n\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        self.stdout.write(f'\n✅ Grupos de gemelos encontrados: {len(gemelos_encontrados)}')
        self.stdout.write(f'❌ Facturas canceladas detectadas: {total_canceladas}')
        self.stdout.write(f'🗑️  Pólizas eliminadas: {total_polizas_eliminadas}')
        self.stdout.write(f'💰 Suma descontada: ${suma_descontada:,.2f}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se eliminó nada'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Auditoría completada'))
            self.stdout.write('\n💡 SIGUIENTE PASO:')
            self.stdout.write('   python manage.py reset_contabilidad_2025')
