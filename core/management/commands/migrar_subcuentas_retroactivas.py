"""
Management Command: Migrar Subcuentas Retroactivas

Migra MovimientoPoliza existentes de cuentas Mayor generales (Nivel 1)
a subcuentas específicas por RFC (Nivel 2) usando AccountResolver.

Uso:
    python manage.py migrar_subcuentas_retroactivas
    python manage.py migrar_subcuentas_retroactivas --dry-run
    python manage.py migrar_subcuentas_retroactivas --empresa-rfc=ABC123456XYZ

Autor: Sistema Konta
Fecha: 2025-12-15
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import MovimientoPoliza, CuentaContable, Factura, Empresa
from core.services.account_resolver import AccountResolver
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migra movimientos contables de cuentas Mayor a subcuentas específicas por RFC'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin guardar cambios',
        )
        parser.add_argument(
            '--empresa-rfc',
            type=str,
            help='RFC de empresa específica a migrar (opcional)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_rfc = options.get('empresa_rfc')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('MIGRACIÓN RETROACTIVA DE SUBCUENTAS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO DRY-RUN: No se guardarán cambios'))
        
        # Filtrar empresas
        empresas = Empresa.objects.all()
        if empresa_rfc:
            empresas = empresas.filter(rfc=empresa_rfc)
            if not empresas.exists():
                raise CommandError(f'Empresa con RFC {empresa_rfc} no encontrada')
        
        total_migrados = 0
        total_errores = 0
        
        for empresa in empresas:
            self.stdout.write(f'\n📊 Procesando empresa: {empresa.nombre} ({empresa.rfc})')
            
            migrados, errores = self._migrar_empresa(empresa, dry_run)
            total_migrados += migrados
            total_errores += errores
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN DE MIGRACIÓN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'✅ Movimientos migrados: {total_migrados}')
        self.stdout.write(f'❌ Errores: {total_errores}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: Ningún cambio fue guardado'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Migración completada exitosamente'))

    def _migrar_empresa(self, empresa, dry_run):
        """
        Migra movimientos de una empresa específica.
        
        Returns:
            tuple: (migrados, errores)
        """
        migrados = 0
        errores = 0
        
        # 1. Identificar cuentas Mayor objetivo (Clientes y Proveedores)
        cuentas_mayor = CuentaContable.objects.filter(
            empresa=empresa,
            nivel=1,
            codigo__in=['105-01', '201-01']  # Clientes y Proveedores Nacionales
        )
        
        if not cuentas_mayor.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'   ⚠️  No se encontraron cuentas Mayor (105-01, 201-01) para {empresa.nombre}'
                )
            )
            return 0, 0
        
        for cuenta_mayor in cuentas_mayor:
            self.stdout.write(f'\n   🔍 Procesando cuenta: {cuenta_mayor.codigo} - {cuenta_mayor.nombre}')
            
            # 2. Obtener movimientos que usan esta cuenta Mayor
            movimientos = MovimientoPoliza.objects.filter(
                cuenta=cuenta_mayor,
                poliza__factura__isnull=False  # Solo movimientos con factura asociada
            ).select_related('poliza__factura', 'poliza__factura__empresa')
            
            total_movimientos = movimientos.count()
            self.stdout.write(f'      📋 Movimientos encontrados: {total_movimientos}')
            
            if total_movimientos == 0:
                continue
            
            # 3. Migrar cada movimiento
            for idx, movimiento in enumerate(movimientos, 1):
                try:
                    # Mostrar progreso cada 10 movimientos
                    if idx % 10 == 0 or idx == total_movimientos:
                        self.stdout.write(
                            f'      ⏳ Progreso: {idx}/{total_movimientos} '
                            f'({int(idx/total_movimientos*100)}%)',
                            ending='\r'
                        )
                    
                    factura = movimiento.poliza.factura
                    
                    # Determinar si es cliente o proveedor
                    if cuenta_mayor.codigo == '105-01':
                        # Clientes (Ingresos)
                        if factura.naturaleza != 'I':
                            self.stdout.write(
                                self.style.WARNING(
                                    f'\n      ⚠️  Movimiento {movimiento.id}: '
                                    f'Cuenta de clientes pero factura no es Ingreso'
                                )
                            )
                            continue
                        
                        subcuenta = AccountResolver.resolver_cuenta_cliente(
                            empresa=empresa,
                            factura=factura
                        )
                    
                    elif cuenta_mayor.codigo == '201-01':
                        # Proveedores (Egresos)
                        if factura.naturaleza != 'E':
                            self.stdout.write(
                                self.style.WARNING(
                                    f'\n      ⚠️  Movimiento {movimiento.id}: '
                                    f'Cuenta de proveedores pero factura no es Egreso'
                                )
                            )
                            continue
                        
                        subcuenta = AccountResolver.resolver_cuenta_proveedor(
                            empresa=empresa,
                            factura=factura
                        )
                    
                    else:
                        continue
                    
                    # 4. Actualizar movimiento
                    if not dry_run:
                        movimiento.cuenta = subcuenta
                        movimiento.save(update_fields=['cuenta'])
                    
                    migrados += 1
                    
                    # Log detallado cada 50 movimientos
                    if idx % 50 == 0:
                        self.stdout.write(
                            f'\n      ✅ Migrado a: {subcuenta.codigo} - {subcuenta.nombre[:40]}'
                        )
                
                except Exception as e:
                    errores += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'\n      ❌ Error en movimiento {movimiento.id}: {str(e)[:100]}'
                        )
                    )
                    logger.error(
                        f'Error migrando movimiento {movimiento.id}: {e}',
                        exc_info=True
                    )
            
            self.stdout.write('')  # Nueva línea después del progreso
        
        return migrados, errores


    def _validar_migracion(self, empresa):
        """
        Valida que la migración fue exitosa.
        
        Returns:
            dict: Estadísticas de validación
        """
        # Contar movimientos que aún usan cuentas Mayor
        movimientos_pendientes = MovimientoPoliza.objects.filter(
            cuenta__empresa=empresa,
            cuenta__nivel=1,
            cuenta__codigo__in=['105-01', '201-01'],
            poliza__factura__isnull=False
        ).count()
        
        # Contar movimientos migrados a subcuentas
        movimientos_migrados = MovimientoPoliza.objects.filter(
            cuenta__empresa=empresa,
            cuenta__nivel=2,
            cuenta__padre__codigo__in=['105-01', '201-01']
        ).count()
        
        return {
            'pendientes': movimientos_pendientes,
            'migrados': movimientos_migrados
        }
