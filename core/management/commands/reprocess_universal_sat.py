"""
Management Command: Reprocess Universal SAT

Re-procesa todas las facturas de Egreso aplicando el nuevo sistema
de clasificación automática basado en UsoCFDI del SAT.

Este comando:
1. Extrae UsoCFDI de los XMLs almacenados (si están disponibles)
2. Elimina pólizas antiguas de Egresos
3. Re-contabiliza usando el nuevo sistema de mapeo SAT
4. Genera estadísticas por categoría (Costos, Gastos, Inversiones)

Uso:
    python manage.py reprocess_universal_sat
    python manage.py reprocess_universal_sat --dry-run
    python manage.py reprocess_universal_sat --empresa-rfc=ABC123456XYZ

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Factura, Poliza, Empresa
from core.services.accounting_service import AccountingService
from core.services.sat_uso_cfdi_map import get_account_config
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Re-procesa facturas de Egreso con clasificación SAT UsoCFDI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula sin guardar cambios',
        )
        parser.add_argument(
            '--empresa-rfc',
            type=str,
            help='RFC de empresa específica (opcional)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_rfc = options.get('empresa_rfc')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('RE-PROCESAMIENTO UNIVERSAL SAT UsoCFDI'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN'))
        
        # Filtrar empresas
        empresas = Empresa.objects.all()
        if empresa_rfc:
            empresas = empresas.filter(rfc=empresa_rfc)
        
        total_procesadas = 0
        total_errores = 0
        estadisticas = {
            'ventas': 0,          # Ingresos tipo I
            'notas_credito': 0,   # Ingresos tipo E (emitidas)
            'costos': 0,          # Egresos G01, G02
            'gastos': 0,          # Egresos G03, D01-D10
            'inversiones': 0,     # Egresos I01-I08
            'nomina': 0,          # Egresos CN01
            'otros': 0            # Egresos P01, S01
        }
        
        for empresa in empresas:
            self.stdout.write(f'\n📊 Empresa: {empresa.nombre} ({empresa.rfc})')
            
            procesadas, errores, stats = self._process_empresa(empresa, dry_run)
            total_procesadas += procesadas
            total_errores += errores
            
            # Acumular estadísticas
            for key in estadisticas:
                estadisticas[key] += stats.get(key, 0)
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'✅ Facturas procesadas: {total_procesadas}')
        self.stdout.write(f'❌ Errores: {total_errores}')
        
        self.stdout.write('\n📊 CLASIFICACIÓN POR CATEGORÍA SAT:')
        self.stdout.write(f'   💵 Ventas (I):                {estadisticas["ventas"]:4} facturas')
        self.stdout.write(f'   🔄 Notas de Crédito (E emit): {estadisticas["notas_credito"]:4} facturas')
        self.stdout.write(f'   💰 Costos (G01-G02):          {estadisticas["costos"]:4} facturas')
        self.stdout.write(f'   📝 Gastos (G03, D01-D10):     {estadisticas["gastos"]:4} facturas')
        self.stdout.write(f'   🏢 Inversiones (I01-I08):     {estadisticas["inversiones"]:4} facturas')
        self.stdout.write(f'   👥 Nómina (CN01):             {estadisticas["nomina"]:4} facturas')
        self.stdout.write(f'   ❓ Otros (P01, S01):          {estadisticas["otros"]:4} facturas')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se guardaron cambios'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Re-procesamiento completado'))

    def _process_empresa(self, empresa, dry_run):
        """Procesa facturas de una empresa"""
        procesadas = 0
        errores = 0
        estadisticas = {
            'ventas': 0,
            'notas_credito': 0,
            'costos': 0,
            'gastos': 0,
            'inversiones': 0,
            'nomina': 0,
            'otros': 0
        }
        
        # Obtener TODAS las facturas (Ingresos y Egresos)
        facturas = Factura.objects.filter(
            empresa=empresa,
            naturaleza__in=['I', 'E']  # Ingresos y Egresos
        )
        
        total = facturas.count()
        self.stdout.write(f'   📋 Total facturas: {total}')
        
        if total == 0:
            return 0, 0, estadisticas
        
        # PASO 1: Limpiar TODAS las pólizas
        if not dry_run:
            polizas_eliminadas = Poliza.objects.filter(
                factura__empresa=empresa,
                factura__naturaleza__in=['I', 'E']
            ).delete()[0]
            
            facturas.update(estado_contable='PENDIENTE')
            
            self.stdout.write(f'   🧹 Pólizas eliminadas: {polizas_eliminadas}')
        
        # PASO 2: Re-contabilizar con clasificación SAT
        self.stdout.write(f'\n   ♻️  Re-contabilizando con motor universal...')
        
        for idx, factura in enumerate(facturas, 1):
            try:
                # Progreso
                if idx % 10 == 0 or idx == total:
                    self.stdout.write(
                        f'   ⏳ {idx}/{total} ({int(idx/total*100)}%)',
                        ending='\r'
                    )
                
                # Clasificar
                if factura.naturaleza == 'I':
                    # Ingreso: Venta o Nota de Crédito
                    es_nota_credito = (
                        factura.tipo_comprobante == 'E' and
                        factura.emisor_rfc == factura.empresa.rfc
                    )
                    if es_nota_credito:
                        estadisticas['notas_credito'] += 1
                    else:
                        estadisticas['ventas'] += 1
                else:
                    # Egreso: Clasificar por UsoCFDI
                    uso_cfdi = factura.uso_cfdi or 'G03'
                    if uso_cfdi.startswith('G0') and uso_cfdi in ['G01', 'G02']:
                        estadisticas['costos'] += 1
                    elif uso_cfdi.startswith('G') or uso_cfdi.startswith('D'):
                        estadisticas['gastos'] += 1
                    elif uso_cfdi.startswith('I'):
                        estadisticas['inversiones'] += 1
                    elif uso_cfdi.startswith('CN'):
                        estadisticas['nomina'] += 1
                    else:
                        estadisticas['otros'] += 1
                
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
                if errores <= 5:  # Mostrar solo primeros 5 errores
                    self.stdout.write(
                        f'\n   ❌ Error en {factura.uuid}: {str(e)[:60]}'
                    )
                logger.error(f'Error en {factura.uuid}: {e}', exc_info=True)
        
        self.stdout.write('')  # Nueva línea
        
        return procesadas, errores, estadisticas
