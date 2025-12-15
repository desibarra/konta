"""
Servicio de Inicialización de Empresa
Crea automáticamente el catálogo de cuentas contables y plantillas de pólizas
para una nueva empresa.

IDEMPOTENTE: Puede ejecutarse múltiples veces sin duplicar datos.
"""

from core.models import Empresa, CuentaContable, PlantillaPoliza
import logging

logger = logging.getLogger(__name__)


class EmpresaInitializer:
    """
    Inicializa una empresa con:
    1. Catálogo de Cuentas Contables Base
    2. Plantillas de Pólizas para todos los tipos de CFDI
    """
    
    # Catálogo de Cuentas Base (Código SAT estándar)
    CUENTAS_BASE = [
        # ACTIVO
        {'codigo': '1101', 'nombre': 'Bancos', 'tipo': 'ACTIVO', 'naturaleza': 'D'},
        {'codigo': '1102', 'nombre': 'Clientes', 'tipo': 'ACTIVO', 'naturaleza': 'D'},
        {'codigo': '1103', 'nombre': 'Deudores Diversos', 'tipo': 'ACTIVO', 'naturaleza': 'D'},
        {'codigo': '1201', 'nombre': 'IVA Acreditable', 'tipo': 'ACTIVO', 'naturaleza': 'D'},
        
        # PASIVO
        {'codigo': '2101', 'nombre': 'Proveedores', 'tipo': 'PASIVO', 'naturaleza': 'A'},
        {'codigo': '2102', 'nombre': 'Acreedores Diversos', 'tipo': 'PASIVO', 'naturaleza': 'A'},
        {'codigo': '2201', 'nombre': 'IVA Trasladado', 'tipo': 'PASIVO', 'naturaleza': 'A'},
        {'codigo': '2202', 'nombre': 'IVA Retenido', 'tipo': 'PASIVO', 'naturaleza': 'A'},
        {'codigo': '2203', 'nombre': 'ISR Retenido', 'tipo': 'PASIVO', 'naturaleza': 'A'},
        
        # CAPITAL
        {'codigo': '3101', 'nombre': 'Capital Social', 'tipo': 'CAPITAL', 'naturaleza': 'A'},
        {'codigo': '3201', 'nombre': 'Utilidad del Ejercicio', 'tipo': 'CAPITAL', 'naturaleza': 'A'},
        
        # INGRESOS
        {'codigo': '4101', 'nombre': 'Ventas', 'tipo': 'INGRESO', 'naturaleza': 'A'},
        {'codigo': '4102', 'nombre': 'Devoluciones sobre Ventas', 'tipo': 'INGRESO', 'naturaleza': 'D'},
        {'codigo': '4103', 'nombre': 'Descuentos sobre Ventas', 'tipo': 'INGRESO', 'naturaleza': 'D'},
        
        # COSTOS
        {'codigo': '5101', 'nombre': 'Costo de Ventas', 'tipo': 'COSTO', 'naturaleza': 'D'},
        
        # GASTOS
        {'codigo': '6101', 'nombre': 'Gastos de Operación', 'tipo': 'GASTO', 'naturaleza': 'D'},
        {'codigo': '6102', 'nombre': 'Sueldos y Salarios', 'tipo': 'GASTO', 'naturaleza': 'D'},
        {'codigo': '6103', 'nombre': 'Honorarios', 'tipo': 'GASTO', 'naturaleza': 'D'},
        {'codigo': '6104', 'nombre': 'Arrendamientos', 'tipo': 'GASTO', 'naturaleza': 'D'},
        {'codigo': '6105', 'nombre': 'Servicios Profesionales', 'tipo': 'GASTO', 'naturaleza': 'D'},
    ]
    
    def __init__(self, empresa: Empresa):
        self.empresa = empresa
        self.cuentas_creadas = {}
    
    def inicializar(self):
        """
        Ejecuta la inicialización completa de la empresa.
        IDEMPOTENTE: No duplica si ya existe.
        """
        logger.info(f"🚀 Inicializando empresa: {self.empresa.nombre}")
        
        # 1. Crear Catálogo de Cuentas
        self._crear_catalogo_cuentas()
        
        # 2. Crear Plantillas de Pólizas
        self._crear_plantillas_polizas()
        
        logger.info(f"✅ Empresa {self.empresa.nombre} inicializada correctamente")
    
    def _crear_catalogo_cuentas(self):
        """Crea el catálogo de cuentas contables base"""
        logger.info("📊 Creando catálogo de cuentas...")
        
        for cuenta_data in self.CUENTAS_BASE:
            cuenta, created = CuentaContable.objects.get_or_create(
                empresa=self.empresa,
                codigo=cuenta_data['codigo'],
                defaults={
                    'nombre': cuenta_data['nombre'],
                    'tipo': cuenta_data['tipo'],
                    'naturaleza': cuenta_data['naturaleza'],
                    'es_deudora': (cuenta_data['naturaleza'] == 'D')
                }
            )
            
            # Guardar referencia para uso en plantillas
            self.cuentas_creadas[cuenta_data['codigo']] = cuenta
            
            if created:
                logger.info(f"   ✅ Creada: {cuenta.codigo} - {cuenta.nombre}")
            else:
                logger.debug(f"   ⏭️  Ya existe: {cuenta.codigo} - {cuenta.nombre}")
        
        logger.info(f"📊 Catálogo completo: {len(self.cuentas_creadas)} cuentas")
    
    def _crear_plantillas_polizas(self):
        """Crea las plantillas de pólizas para todos los tipos de CFDI"""
        logger.info("📋 Creando plantillas de pólizas...")
        
        plantillas = [
            # INGRESO (I) - Factura Emitida
            {
                'nombre': 'Ingreso - Factura Emitida',
                'tipo_factura': 'I',
                'cuenta_flujo_codigo': '1102',      # Clientes (Cargo)
                'cuenta_provision_codigo': '4101',   # Ventas (Abono)
                'cuenta_impuesto_codigo': '2201',    # IVA Trasladado (Abono)
                'es_default': True,
                'descripcion': 'Registro de venta a crédito con IVA trasladado'
            },
            
            # EGRESO (E) - Gasto/Compra
            {
                'nombre': 'Egreso - Gasto General',
                'tipo_factura': 'E',
                'cuenta_flujo_codigo': '2101',       # Proveedores (Abono)
                'cuenta_provision_codigo': '6101',   # Gastos de Operación (Cargo)
                'cuenta_impuesto_codigo': '1201',    # IVA Acreditable (Cargo)
                'es_default': True,
                'descripcion': 'Registro de gasto a crédito con IVA acreditable'
            },
            
            # EGRESO - Honorarios
            {
                'nombre': 'Egreso - Honorarios',
                'tipo_factura': 'E',
                'cuenta_flujo_codigo': '2102',       # Acreedores Diversos (Abono)
                'cuenta_provision_codigo': '6103',   # Honorarios (Cargo)
                'cuenta_impuesto_codigo': '1201',    # IVA Acreditable (Cargo)
                'es_default': False,
                'descripcion': 'Registro de honorarios profesionales'
            },
            
            # EGRESO - Arrendamiento
            {
                'nombre': 'Egreso - Arrendamiento',
                'tipo_factura': 'E',
                'cuenta_flujo_codigo': '2101',       # Proveedores (Abono)
                'cuenta_provision_codigo': '6104',   # Arrendamientos (Cargo)
                'cuenta_impuesto_codigo': '1201',    # IVA Acreditable (Cargo)
                'es_default': False,
                'descripcion': 'Registro de renta de inmuebles'
            },
            
            # PAGO (P) - Recepción de Pago
            {
                'nombre': 'Pago - Cobro a Cliente',
                'tipo_factura': 'P',
                'cuenta_flujo_codigo': '1101',       # Bancos (Cargo)
                'cuenta_provision_codigo': '1102',   # Clientes (Abono)
                'cuenta_impuesto_codigo': None,      # Sin IVA en pagos
                'es_default': True,
                'descripcion': 'Registro de cobro a cliente (REP)'
            },
            
            # NÓMINA (N)
            {
                'nombre': 'Nómina - Pago de Sueldos',
                'tipo_factura': 'N',
                'cuenta_flujo_codigo': '1101',       # Bancos (Abono)
                'cuenta_provision_codigo': '6102',   # Sueldos y Salarios (Cargo)
                'cuenta_impuesto_codigo': '2203',    # ISR Retenido (Abono)
                'es_default': True,
                'descripcion': 'Registro de pago de nómina con retenciones'
            },
            
            # TRASLADO (T) - Opcional
            {
                'nombre': 'Traslado - Movimiento Interno',
                'tipo_factura': 'T',
                'cuenta_flujo_codigo': '1103',       # Deudores Diversos (Cargo)
                'cuenta_provision_codigo': '2102',   # Acreedores Diversos (Abono)
                'cuenta_impuesto_codigo': None,      # Sin IVA
                'es_default': True,
                'descripcion': 'Registro de traslado entre almacenes/sucursales'
            },
        ]
        
        for plantilla_data in plantillas:
            # Obtener cuentas
            cuenta_flujo = self.cuentas_creadas.get(plantilla_data['cuenta_flujo_codigo'])
            cuenta_provision = self.cuentas_creadas.get(plantilla_data['cuenta_provision_codigo'])
            cuenta_impuesto = None
            if plantilla_data['cuenta_impuesto_codigo']:
                cuenta_impuesto = self.cuentas_creadas.get(plantilla_data['cuenta_impuesto_codigo'])
            
            if not cuenta_flujo or not cuenta_provision:
                logger.warning(f"   ⚠️  Saltando plantilla {plantilla_data['nombre']}: cuentas no encontradas")
                continue
            
            # Crear plantilla (idempotente)
            plantilla, created = PlantillaPoliza.objects.get_or_create(
                empresa=self.empresa,
                nombre=plantilla_data['nombre'],
                tipo_factura=plantilla_data['tipo_factura'],
                defaults={
                    'cuenta_flujo': cuenta_flujo,
                    'cuenta_provision': cuenta_provision,
                    'cuenta_impuesto': cuenta_impuesto,
                    'es_default': plantilla_data['es_default']
                }
            )
            
            if created:
                logger.info(f"   ✅ Creada: {plantilla.nombre}")
            else:
                logger.debug(f"   ⏭️  Ya existe: {plantilla.nombre}")
        
        total_plantillas = PlantillaPoliza.objects.filter(empresa=self.empresa).count()
        logger.info(f"📋 Plantillas completas: {total_plantillas}")


def inicializar_empresa(empresa: Empresa):
    """
    Función helper para inicializar una empresa.
    Puede ser llamada manualmente o desde signals.
    """
    initializer = EmpresaInitializer(empresa)
    initializer.inicializar()
