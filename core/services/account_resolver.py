"""
AccountResolver Service - SAT Anexo 24 Compliant Subcuentas

Servicio para resolver y crear automáticamente subcuentas específicas
por RFC de cliente/proveedor, cumpliendo con requisitos SAT.

REGLA CRÍTICA SAT:
Las subcuentas DEBEN heredar el agrupador_sat de su cuenta padre.
"""

from decimal import Decimal
from core.models import CuentaContable, Factura, Empresa
import logging

logger = logging.getLogger(__name__)


class AccountResolver:
    """
    Resuelve y crea automáticamente subcuentas específicas por RFC.
    
    Características:
    - Herencia automática de agrupador_sat
    - Generación de códigos secuenciales
    - Validación de jerarquía
    - Idempotencia (get_or_create)
    """
    
    @staticmethod
    def get_or_create_subcuenta(empresa, cuenta_mayor_codigo, rfc, nombre_tercero):
        """
        Obtiene o crea una subcuenta específica para un RFC.
        
        Args:
            empresa (Empresa): Instancia de empresa
            cuenta_mayor_codigo (str): Código de cuenta mayor (ej: '105-01')
            rfc (str): RFC del tercero
            nombre_tercero (str): Nombre del tercero
            
        Returns:
            CuentaContable: Subcuenta específica para el RFC
            
        Raises:
            ValueError: Si la cuenta mayor no existe
        """
        # 1. Buscar cuenta mayor
        try:
            cuenta_mayor = CuentaContable.objects.get(
                empresa=empresa,
                codigo=cuenta_mayor_codigo,
                nivel=1  # Solo cuentas de nivel Mayor
            )
        except CuentaContable.DoesNotExist:
            raise ValueError(
                f"Cuenta mayor '{cuenta_mayor_codigo}' no existe para {empresa.nombre}. "
                f"Ejecuta: python manage.py seed_empresas"
            )
        
        # 2. Verificar si ya existe subcuenta para este RFC
        subcuenta = CuentaContable.objects.filter(
            empresa=empresa,
            padre=cuenta_mayor,
            rfc_tercero=rfc
        ).first()
        
        if subcuenta:
            logger.info(f"✓ Subcuenta existente: {subcuenta.codigo} para RFC {rfc}")
            return subcuenta
        
        # 3. Generar código automático secuencial
        # Ejemplo: 105-01-001, 105-01-002, etc.
        ultimo_numero = CuentaContable.objects.filter(
            empresa=empresa,
            padre=cuenta_mayor
        ).count() + 1
        
        nuevo_codigo = f"{cuenta_mayor_codigo}-{str(ultimo_numero).zfill(3)}"
        
        # 4. HEREDAR agrupador_sat del padre (CRÍTICO PARA SAT)
        agrupador_sat_heredado = cuenta_mayor.agrupador_sat
        
        if not agrupador_sat_heredado:
            logger.warning(
                f"⚠️ Cuenta mayor {cuenta_mayor_codigo} no tiene agrupador_sat. "
                f"La balanza SAT puede ser inválida."
            )
        
        # 5. Crear subcuenta
        subcuenta = CuentaContable.objects.create(
            empresa=empresa,
            codigo=nuevo_codigo,
            nombre=f"{cuenta_mayor.nombre} - {nombre_tercero[:50]}",
            tipo=cuenta_mayor.tipo,
            naturaleza=cuenta_mayor.naturaleza,
            es_deudora=cuenta_mayor.es_deudora,
            nivel=2,  # Subcuenta
            padre=cuenta_mayor,
            rfc_tercero=rfc,
            agrupador_sat=agrupador_sat_heredado  # HERENCIA CRÍTICA
        )
        
        logger.info(
            f"✅ Subcuenta creada: {nuevo_codigo} - {nombre_tercero[:30]} "
            f"(RFC: {rfc}, Agrupador SAT: {agrupador_sat_heredado or 'N/A'})"
        )
        
        return subcuenta
    
    @staticmethod
    def resolver_cuenta_cliente(empresa, factura):
        """
        Resuelve la cuenta de cliente para una factura de ingreso.
        
        Args:
            empresa (Empresa): Instancia de empresa
            factura (Factura): Factura de ingreso (naturaleza='I')
            
        Returns:
            CuentaContable: Subcuenta específica del cliente
        """
        if factura.naturaleza != 'I':
            raise ValueError(f"Factura {factura.uuid} no es de tipo Ingreso")
        
        return AccountResolver.get_or_create_subcuenta(
            empresa=empresa,
            cuenta_mayor_codigo='105-01',  # Clientes Nacionales
            rfc=factura.receptor_rfc,
            nombre_tercero=factura.receptor_nombre
        )
    
    @staticmethod
    def resolver_cuenta_proveedor(empresa, factura):
        """
        Resuelve la cuenta de proveedor para una factura de egreso.
        
        Args:
            empresa (Empresa): Instancia de empresa
            factura (Factura): Factura de egreso (naturaleza='E')
            
        Returns:
            CuentaContable: Subcuenta específica del proveedor
        """
        if factura.naturaleza != 'E':
            raise ValueError(f"Factura {factura.uuid} no es de tipo Egreso")
        
        return AccountResolver.get_or_create_subcuenta(
            empresa=empresa,
            cuenta_mayor_codigo='201-01',  # Proveedores Nacionales
            rfc=factura.emisor_rfc,
            nombre_tercero=factura.emisor_nombre
        )
    
    @staticmethod
    def validar_jerarquia(cuenta):
        """
        Valida que la jerarquía de una cuenta sea correcta.
        
        Args:
            cuenta (CuentaContable): Cuenta a validar
            
        Returns:
            tuple: (es_valida, mensaje_error)
        """
        # Nivel 1 (Mayor) no debe tener padre
        if cuenta.nivel == 1 and cuenta.padre is not None:
            return False, "Cuenta Mayor no puede tener padre"
        
        # Nivel 2 y 3 DEBEN tener padre
        if cuenta.nivel in [2, 3] and cuenta.padre is None:
            return False, f"Cuenta nivel {cuenta.nivel} debe tener padre"
        
        # Subcuenta debe heredar agrupador_sat
        if cuenta.nivel == 2 and cuenta.padre:
            if cuenta.agrupador_sat != cuenta.padre.agrupador_sat:
                return False, "Subcuenta debe heredar agrupador_sat del padre"
        
        return True, "Jerarquía válida"
