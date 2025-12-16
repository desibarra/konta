"""
Management Command: Remove Duplicate Facturas

PROBLEMA: El sistema permitió la carga de facturas duplicadas (mismo UUID).
SOLUCIÓN: Detecta y elimina duplicados, conservando solo la copia original.

LÓGICA:
1. Agrupa facturas por UUID
2. Para cada UUID duplicado:
   - Conserva la factura CONTABILIZADA (si existe)
   - Si no, conserva la más antigua (menor ID)
   - Elimina todas las demás copias
3. Elimina pólizas huérfanas si es necesario

Uso:
    python manage.py remove_duplicate_facturas
    python manage.py remove_duplicate_facturas --dry-run

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from core.models import Factura, Poliza, MovimientoPoliza
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Elimina facturas duplicadas (mismo UUID), conservando solo una copia'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula sin eliminar nada',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.ERROR('=' * 70))
        self.stdout.write(self.style.ERROR('🧹 LIMPIEZA DE FACTURAS DUPLICADAS'))
        self.stdout.write(self.style.ERROR('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN (simulación)'))
        
        # PASO 1: Detectar UUIDs duplicados
        self.stdout.write('\n🔍 PASO 1: Detectando duplicados...')
        
        duplicados = Factura.objects.values('uuid').annotate(
            count=Count('id')
        ).filter(count__gt=1).order_by('-count')
        
        total_duplicados = duplicados.count()
        
        if total_duplicados == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No se encontraron facturas duplicadas'))
            return
        
        self.stdout.write(f'\n❌ Se encontraron {total_duplicados} UUIDs duplicados')
        
        # Mostrar top 10
        self.stdout.write('\nTop 10 UUIDs más duplicados:')
        for dup in duplicados[:10]:
            self.stdout.write(f"   {dup['uuid']}: {dup['count']} copias")
        
        # PASO 2: Procesar cada UUID duplicado
        self.stdout.write('\n\n🗑️  PASO 2: Eliminando copias sobrantes...')
        
        total_eliminadas = 0
        polizas_eliminadas = 0
        
        for dup in duplicados:
            uuid = dup['uuid']
            count = dup['count']
            
            # Obtener todas las facturas con este UUID
            facturas = Factura.objects.filter(uuid=uuid).order_by('id')
            
            # Decidir cuál conservar
            factura_a_conservar = None
            
            # Prioridad 1: Conservar la CONTABILIZADA
            contabilizada = facturas.filter(estado_contable='CONTABILIZADA').first()
            if contabilizada:
                factura_a_conservar = contabilizada
            else:
                # Prioridad 2: Conservar la más antigua (menor ID)
                factura_a_conservar = facturas.first()
            
            # Identificar las que se van a eliminar
            facturas_a_eliminar = facturas.exclude(id=factura_a_conservar.id)
            
            self.stdout.write(
                f'\n   UUID: {str(uuid)[:36]}'
            )
            self.stdout.write(
                f'      Copias: {count} | Conservar: ID={factura_a_conservar.id} '
                f'(Estado: {factura_a_conservar.estado_contable}) | '
                f'Eliminar: {facturas_a_eliminar.count()}'
            )
            
            # Eliminar pólizas de las facturas duplicadas
            for factura in facturas_a_eliminar:
                polizas = Poliza.objects.filter(factura=factura)
                if polizas.exists():
                    polizas_count = polizas.count()
                    if not dry_run:
                        # Eliminar movimientos primero
                        MovimientoPoliza.objects.filter(poliza__in=polizas).delete()
                        # Luego pólizas
                        polizas.delete()
                    polizas_eliminadas += polizas_count
                    self.stdout.write(
                        f'         └─ Eliminando {polizas_count} póliza(s) de factura ID={factura.id}'
                    )
            
            # Eliminar las facturas duplicadas
            if not dry_run:
                eliminadas = facturas_a_eliminar.delete()[0]
                total_eliminadas += eliminadas
        
        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        self.stdout.write(f'\n✅ UUIDs duplicados encontrados: {total_duplicados}')
        self.stdout.write(f'✅ Facturas eliminadas: {total_eliminadas}')
        self.stdout.write(f'✅ Pólizas eliminadas: {polizas_eliminadas}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se eliminó nada'))
            self.stdout.write('\nPara ejecutar la limpieza real, ejecuta:')
            self.stdout.write('   python manage.py remove_duplicate_facturas')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Limpieza completada'))
            self.stdout.write('\n💡 SIGUIENTE PASO:')
            self.stdout.write('   1. Ejecuta: python manage.py makemigrations')
            self.stdout.write('   2. Ejecuta: python manage.py migrate')
            self.stdout.write('   3. Esto aplicará la restricción unique=True en el campo UUID')
            self.stdout.write('   4. Ejecuta: python manage.py reset_contabilidad_2025')
