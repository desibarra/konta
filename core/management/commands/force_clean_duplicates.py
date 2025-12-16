"""
Management Command: Force Clean Duplicates

PROBLEMA: El validador SAT retorna "No Encontrado" para facturas duplicadas
SOLUCIÓN: Eliminar duplicados basándose en lógica interna

LÓGICA:
- Agrupa facturas por (total, fecha, emisor)
- Si grupo tiene > 1 factura:
  * Mantiene la última (ID mayor)
  * Elimina todas las demás

Uso:
    python manage.py force_clean_duplicates
    python manage.py force_clean_duplicates --dry-run

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from core.models import Factura, Poliza, MovimientoPoliza
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Elimina facturas duplicadas basándose en lógica interna (mismo total, fecha, emisor)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula sin eliminar nada',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=2025,
            help='Año a procesar (default: 2025)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options['year']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('🧹 LIMPIEZA FORZADA DE DUPLICADOS'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(f'\n📅 Año: {year}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN'))
        else:
            self.stdout.write(self.style.ERROR('\n🔥 MODO REAL - Se eliminarán facturas'))
            confirm = input('\n¿Estás seguro? Escribe "DELETE" para continuar: ')
            if confirm != 'DELETE':
                self.stdout.write(self.style.WARNING('\nOperación cancelada'))
                return
        
        # PASO 1: Identificar duplicados
        self.stdout.write('\n\n🔍 PASO 1: Identificando duplicados...')
        self.stdout.write('   Criterio: Mismo Total + Misma Fecha + Mismo Emisor')
        
        facturas = Factura.objects.filter(
            fecha__year=year,
            naturaleza='I'  # Solo ingresos
        ).order_by('total', 'fecha', 'emisor_rfc', 'id')
        
        # Agrupar por (total, fecha, emisor)
        grupos_duplicados = {}
        
        for factura in facturas:
            # Crear clave única
            fecha_str = factura.fecha.strftime('%Y-%m-%d')
            clave = f"{factura.total}_{fecha_str}_{factura.emisor_rfc}"
            
            if clave not in grupos_duplicados:
                grupos_duplicados[clave] = []
            
            grupos_duplicados[clave].append(factura)
        
        # Filtrar solo grupos con duplicados
        grupos_con_duplicados = {
            k: v for k, v in grupos_duplicados.items() if len(v) > 1
        }
        
        if not grupos_con_duplicados:
            self.stdout.write(self.style.SUCCESS('\n✅ No se encontraron duplicados'))
            return
        
        self.stdout.write(f'\n❌ Se encontraron {len(grupos_con_duplicados)} grupos de duplicados')
        
        # PASO 2: Eliminar duplicados
        self.stdout.write('\n\n🗑️  PASO 2: Eliminando duplicados...')
        
        total_eliminadas = 0
        polizas_eliminadas = 0
        suma_eliminada = Decimal('0.00')
        
        for idx, (clave, grupo) in enumerate(grupos_con_duplicados.items(), 1):
            # Ordenar por ID (la última es la más reciente)
            grupo_ordenado = sorted(grupo, key=lambda f: f.id)
            
            # Mantener la última
            factura_a_mantener = grupo_ordenado[-1]
            
            # Eliminar las demás
            facturas_a_eliminar = grupo_ordenado[:-1]
            
            self.stdout.write(f'\n📋 Grupo {idx}/{len(grupos_con_duplicados)}:')
            self.stdout.write(f'   Total: ${grupo[0].total:,.2f}')
            self.stdout.write(f'   Fecha: {grupo[0].fecha.strftime("%Y-%m-%d")}')
            self.stdout.write(f'   Emisor: {grupo[0].emisor_nombre[:40]}')
            self.stdout.write(f'   Duplicados: {len(grupo)} facturas')
            self.stdout.write(f'   ✅ Mantener: {factura_a_mantener.uuid} (ID: {factura_a_mantener.id})')
            
            for factura in facturas_a_eliminar:
                self.stdout.write(f'   ❌ Eliminar: {factura.uuid} (ID: {factura.id})')
                
                # Eliminar pólizas
                polizas = Poliza.objects.filter(factura=factura)
                if polizas.exists():
                    polizas_count = polizas.count()
                    if not dry_run:
                        MovimientoPoliza.objects.filter(poliza__in=polizas).delete()
                        polizas.delete()
                    polizas_eliminadas += polizas_count
                    self.stdout.write(f'      └─ Eliminando {polizas_count} póliza(s)')
                
                # Eliminar factura
                if not dry_run:
                    factura.delete()
                
                total_eliminadas += 1
                suma_eliminada += factura.subtotal
        
        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS('\n\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        self.stdout.write(f'\n✅ Grupos de duplicados encontrados: {len(grupos_con_duplicados)}')
        self.stdout.write(f'❌ Facturas eliminadas: {total_eliminadas}')
        self.stdout.write(f'🗑️  Pólizas eliminadas: {polizas_eliminadas}')
        self.stdout.write(f'💰 Suma eliminada (Subtotal): ${suma_eliminada:,.2f}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se eliminó nada'))
            self.stdout.write('\nPara ejecutar la limpieza real:')
            self.stdout.write('   python manage.py force_clean_duplicates')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Limpieza completada'))
            self.stdout.write('\n💡 SIGUIENTE PASO:')
            self.stdout.write('   python manage.py rebuild_accounting_2025')
