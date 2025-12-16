"""
Management Command: Fix Egresos Accounting

Corrige la contabilización de facturas de Egreso que fueron procesadas
con plantillas incorrectas (usando cuentas de Pasivo en lugar de Gastos).

Proceso:
1. Corrige PlantillaPoliza de Egresos para usar cuenta 601-01 (Gastos)
2. Elimina pólizas incorrectas de facturas de Egreso
3. Re-contabiliza facturas de Egreso con configuración correcta

Uso:
    python manage.py fix_egresos_accounting
    python manage.py fix_egresos_accounting --dry-run
    python manage.py fix_egresos_accounting --empresa-rfc=ABC123456XYZ

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import (
    PlantillaPoliza, CuentaContable, Factura, Poliza, 
    MovimientoPoliza, Empresa
)
from core.services.accounting_service import AccountingService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Corrige contabilización de Egresos y re-procesa con cuentas de Gastos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la corrección sin guardar cambios',
        )
        parser.add_argument(
            '--empresa-rfc',
            type=str,
            help='RFC de empresa específica a corregir (opcional)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_rfc = options.get('empresa_rfc')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('CORRECCIÓN DE CONTABILIZACIÓN DE EGRESOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO DRY-RUN: No se guardarán cambios'))
        
        # Filtrar empresas
        empresas = Empresa.objects.all()
        if empresa_rfc:
            empresas = empresas.filter(rfc=empresa_rfc)
            if not empresas.exists():
                raise CommandError(f'Empresa con RFC {empresa_rfc} no encontrada')
        
        total_corregidas = 0
        total_errores = 0
        
        for empresa in empresas:
            self.stdout.write(f'\n📊 Procesando empresa: {empresa.nombre} ({empresa.rfc})')
            
            corregidas, errores = self._fix_empresa(empresa, dry_run)
            total_corregidas += corregidas
            total_errores += errores
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN DE CORRECCIÓN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'✅ Facturas re-contabilizadas: {total_corregidas}')
        self.stdout.write(f'❌ Errores: {total_errores}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: Ningún cambio fue guardado'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Corrección completada exitosamente'))

    def _fix_empresa(self, empresa, dry_run):
        """
        Corrige contabilización de egresos para una empresa.
        
        Returns:
            tuple: (corregidas, errores)
        """
        corregidas = 0
        errores = 0
        
        # PASO 1: Corregir Plantilla de Egresos
        self.stdout.write('\n   🔧 PASO 1: Corrigiendo Plantilla de Egresos')
        
        try:
            # Buscar o crear cuenta de Gastos (601-01)
            cuenta_gastos, created = CuentaContable.objects.get_or_create(
                empresa=empresa,
                codigo='601-01',
                defaults={
                    'nombre': 'Gastos Generales',
                    'tipo': 'GASTO',
                    'naturaleza': 'D',
                    'es_deudora': True,
                    'nivel': 1,
                    'agrupador_sat': '601.01'
                }
            )
            
            if created:
                self.stdout.write(f'      ✅ Cuenta creada: {cuenta_gastos.codigo} - {cuenta_gastos.nombre}')
            else:
                self.stdout.write(f'      ℹ️  Cuenta existente: {cuenta_gastos.codigo} - {cuenta_gastos.nombre}')
            
            # Buscar plantilla de Egresos
            plantilla_egreso = PlantillaPoliza.objects.filter(
                empresa=empresa,
                tipo_factura='E'
            ).first()
            
            if plantilla_egreso:
                old_provision = plantilla_egreso.cuenta_provision
                
                if not dry_run:
                    plantilla_egreso.cuenta_provision = cuenta_gastos
                    plantilla_egreso.save()
                
                self.stdout.write(
                    f'      ✅ Plantilla corregida: '
                    f'{old_provision.codigo if old_provision else "None"} → {cuenta_gastos.codigo}'
                )
            else:
                self.stdout.write(self.style.WARNING('      ⚠️  No se encontró plantilla de Egresos'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'      ❌ Error corrigiendo plantilla: {e}'))
            logger.error(f'Error corrigiendo plantilla: {e}', exc_info=True)
            errores += 1
        
        # PASO 2: Identificar y limpiar facturas de Egreso
        self.stdout.write('\n   🧹 PASO 2: Limpiando pólizas incorrectas')
        
        facturas_egreso = Factura.objects.filter(
            empresa=empresa,
            naturaleza='E',
            estado_contable='CONTABILIZADA'
        )
        
        total_facturas = facturas_egreso.count()
        self.stdout.write(f'      📋 Facturas de Egreso encontradas: {total_facturas}')
        
        if total_facturas == 0:
            self.stdout.write('      ℹ️  No hay facturas de Egreso para corregir')
            return 0, 0
        
        # Eliminar pólizas antiguas
        if not dry_run:
            polizas_eliminadas = Poliza.objects.filter(
                factura__in=facturas_egreso
            ).delete()[0]
            
            # Resetear estado
            facturas_egreso.update(estado_contable='PENDIENTE')
            
            self.stdout.write(f'      ✅ Pólizas eliminadas: {polizas_eliminadas}')
            self.stdout.write(f'      ✅ Facturas reseteadas a PENDIENTE: {total_facturas}')
        else:
            polizas_count = Poliza.objects.filter(factura__in=facturas_egreso).count()
            self.stdout.write(f'      🔍 Pólizas a eliminar: {polizas_count}')
        
        # PASO 3: Re-contabilizar con configuración correcta
        self.stdout.write('\n   ♻️  PASO 3: Re-contabilizando facturas de Egreso')
        
        for idx, factura in enumerate(facturas_egreso, 1):
            try:
                # Mostrar progreso cada 10 facturas
                if idx % 10 == 0 or idx == total_facturas:
                    self.stdout.write(
                        f'      ⏳ Progreso: {idx}/{total_facturas} '
                        f'({int(idx/total_facturas*100)}%)',
                        ending='\r'
                    )
                
                if not dry_run:
                    # Re-contabilizar usando AccountingService
                    poliza = AccountingService.contabilizar_factura(
                        factura.uuid,
                        usuario_id=None
                    )
                    
                    corregidas += 1
                    
                    # Log detallado cada 50 facturas
                    if idx % 50 == 0:
                        self.stdout.write(
                            f'\n      ✅ Póliza #{poliza.id} creada para {factura.emisor_nombre[:30]}'
                        )
                else:
                    corregidas += 1
            
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'\n      ❌ Error en factura {factura.uuid}: {str(e)[:100]}'
                    )
                )
                logger.error(
                    f'Error re-contabilizando factura {factura.uuid}: {e}',
                    exc_info=True
                )
        
        self.stdout.write('')  # Nueva línea después del progreso
        
        # PASO 4: Verificación
        if not dry_run:
            self.stdout.write('\n   ✓ PASO 4: Verificación')
            
            # Verificar que se crearon movimientos en cuentas de GASTO
            movs_gastos = MovimientoPoliza.objects.filter(
                poliza__factura__empresa=empresa,
                poliza__factura__naturaleza='E',
                cuenta__tipo='GASTO'
            ).count()
            
            self.stdout.write(f'      ✅ Movimientos en cuentas de GASTO: {movs_gastos}')
            
            if movs_gastos == 0:
                self.stdout.write(
                    self.style.WARNING(
                        '      ⚠️  ADVERTENCIA: No se encontraron movimientos en cuentas de GASTO'
                    )
                )
        
        return corregidas, errores
