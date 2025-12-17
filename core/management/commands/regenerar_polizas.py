"""
Comando de gestión para limpiar y regenerar TODAS las pólizas contables
Esto eliminará los ajustes incorrectos de la cuenta 702-99
"""
from django.core.management.base import BaseCommand
from core.models import Factura, Poliza, MovimientoPoliza
from core.services.accounting_service import AccountingService
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Limpia y regenera todas las pólizas contables para eliminar ajustes incorrectos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de la empresa (opcional, si no se especifica procesa todas)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la operación sin hacer cambios reales'
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO SIMULACIÓN - No se harán cambios reales'))
        
        # Filtrar facturas
        facturas_qs = Factura.objects.filter(estado_contable='CONTABILIZADA')
        if empresa_id:
            facturas_qs = facturas_qs.filter(empresa_id=empresa_id)
        
        total = facturas_qs.count()
        self.stdout.write(f'\n📊 Facturas a reprocesar: {total}\n')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No hay facturas contabilizadas para reprocesar'))
            return
        
        # Confirmar
        if not dry_run:
            confirm = input(f'¿Estás seguro de regenerar {total} pólizas? (sí/no): ')
            if confirm.lower() not in ['sí', 'si', 's', 'yes', 'y']:
                self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                return
        
        exitosas = 0
        errores = 0
        errores_detalle = []
        
        for i, factura in enumerate(facturas_qs, 1):
            try:
                if not dry_run:
                    with transaction.atomic():
                        # 1. Eliminar póliza existente
                        Poliza.objects.filter(factura=factura).delete()
                        
                        # 2. Marcar como pendiente
                        factura.estado_contable = 'PENDIENTE'
                        factura.save()
                        
                        # 3. Regenerar póliza
                        AccountingService.contabilizar_factura(
                            factura.uuid,
                            usuario_id=None
                        )
                
                exitosas += 1
                
                if i % 50 == 0:
                    self.stdout.write(f'   Procesadas: {i}/{total}')
                    
            except Exception as e:
                errores += 1
                error_msg = f"Factura {factura.uuid}: {str(e)[:100]}"
                logger.error(error_msg)
                if len(errores_detalle) < 10:
                    errores_detalle.append(error_msg)
        
        # Resumen
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'✅ Exitosas: {exitosas}'))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errores: {errores}'))
            if errores_detalle:
                self.stdout.write('\n📋 Primeros errores:')
                for err in errores_detalle:
                    self.stdout.write(f'   - {err}')
        
        if not dry_run:
            self.stdout.write('\n🎯 RECOMENDACIÓN: Verifica el Balance General para confirmar que cuadra')
        else:
            self.stdout.write('\n💡 Ejecuta sin --dry-run para aplicar los cambios')
        
        self.stdout.write('='*70 + '\n')
