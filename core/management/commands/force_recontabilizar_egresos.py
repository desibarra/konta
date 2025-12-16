"""
Management Command: Force Recontabilizar Egresos

Fuerza la re-contabilización de TODAS las facturas de Egreso,
independientemente de su estado actual.

Proceso:
1. Elimina TODAS las pólizas de facturas de Egreso
2. Resetea estado a PENDIENTE
3. Re-contabiliza usando la configuración correcta (cuenta 601-01 Gastos)

Uso:
    python manage.py force_recontabilizar_egresos
    python manage.py force_recontabilizar_egresos --dry-run

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Factura, Poliza, Empresa
from core.services.accounting_service import AccountingService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fuerza re-contabilización de TODAS las facturas de Egreso'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula sin guardar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('RE-CONTABILIZACIÓN FORZADA DE EGRESOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN'))
        
        # Obtener TODAS las facturas de Egreso
        facturas_egreso = Factura.objects.filter(naturaleza='E')
        total = facturas_egreso.count()
        
        self.stdout.write(f'\n📊 Total facturas de Egreso: {total}')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No hay facturas de Egreso'))
            return
        
        # PASO 1: Limpiar pólizas existentes
        self.stdout.write('\n🧹 PASO 1: Eliminando pólizas antiguas...')
        
        if not dry_run:
            polizas_eliminadas = Poliza.objects.filter(
                factura__naturaleza='E'
            ).delete()[0]
            
            self.stdout.write(f'   ✅ Pólizas eliminadas: {polizas_eliminadas}')
        else:
            polizas_count = Poliza.objects.filter(factura__naturaleza='E').count()
            self.stdout.write(f'   🔍 Pólizas a eliminar: {polizas_count}')
        
        # PASO 2: Resetear estado
        self.stdout.write('\n🔄 PASO 2: Reseteando estado...')
        
        if not dry_run:
            facturas_egreso.update(estado_contable='PENDIENTE')
            self.stdout.write(f'   ✅ {total} facturas → PENDIENTE')
        
        # PASO 3: Re-contabilizar
        self.stdout.write(f'\n♻️  PASO 3: Re-contabilizando {total} facturas...')
        
        exitosas = 0
        errores = 0
        errores_detalle = []
        
        for idx, factura in enumerate(facturas_egreso, 1):
            try:
                # Progreso
                if idx % 10 == 0 or idx == total:
                    porcentaje = int(idx/total*100)
                    self.stdout.write(
                        f'   ⏳ {idx}/{total} ({porcentaje}%) - '
                        f'✅ {exitosas} | ❌ {errores}',
                        ending='\r'
                    )
                
                if not dry_run:
                    poliza = AccountingService.contabilizar_factura(
                        factura.uuid,
                        usuario_id=None
                    )
                    exitosas += 1
                    
                    # Log cada 25
                    if idx % 25 == 0:
                        self.stdout.write(
                            f'\n   ✅ Póliza #{poliza.id}: {factura.emisor_nombre[:30]}'
                        )
                else:
                    exitosas += 1
            
            except Exception as e:
                errores += 1
                error_msg = f'{factura.uuid[:8]}: {str(e)[:60]}'
                
                if len(errores_detalle) < 5:
                    errores_detalle.append(error_msg)
                
                logger.error(f'Error en {factura.uuid}: {e}', exc_info=True)
        
        self.stdout.write('')  # Nueva línea
        
        # RESUMEN
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'✅ Exitosas: {exitosas}')
        self.stdout.write(f'❌ Errores:  {errores}')
        
        if errores > 0 and errores_detalle:
            self.stdout.write(f'\n⚠️  Primeros errores:')
            for err in errores_detalle:
                self.stdout.write(f'   • {err}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se guardaron cambios'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Re-contabilización completada'))
            self.stdout.write('\n💡 Ahora verifica el Estado de Resultados')
