from django.db import transaction, models
from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable, Empresa
from decimal import Decimal

class AccountingService:
    @staticmethod
    def contabilizar_factura(factura_uuid, usuario_id=None):
        """
        Genera la Póliza Contable para una factura dada.
        Retorna: La póliza creada.
        Lanza: ValueError si no se puede contabilizar.
        """
        try:
            factura = Factura.objects.select_related('empresa').get(uuid=factura_uuid)
        except Factura.DoesNotExist:
            raise ValueError("Factura no encontrada")

        if factura.estado_contable == 'CONTABILIZADA':
            raise ValueError("La factura ya está contabilizada.")
            
        if factura.naturaleza == 'C':
             raise ValueError("Facturas de Control no se contabilizan automáticamente.")

        with transaction.atomic():
            # 1. Crear Cabecera de Póliza
            tipo_pol = 'Diario' # Por defecto
            if factura.naturaleza == 'I': tipo_pol = 'Ingresos'
            elif factura.naturaleza == 'E': tipo_pol = 'Egresos'
            
            poliza = Poliza.objects.create(
                factura=factura,
                fecha=factura.fecha.date(),
                descripcion=f"Prov. {factura.naturaleza} - {factura.emisor_nombre if factura.naturaleza == 'E' else factura.receptor_nombre}"
            )

            # 2. Definir Cuentas (Lógica Simplificada por ahora - Debería ser Configurable)
            # Todo: Usar reglas de negocio reales. Por ahora hardcodeamos cuentas base por RFC/Empresa.
            cta_clientes = AccountingService._get_or_create_cuenta(factura.empresa, '105', 'Clientes')
            cta_ventas = AccountingService._get_or_create_cuenta(factura.empresa, '401', 'Ingresos por Ventas')
            cta_iva_tras = AccountingService._get_or_create_cuenta(factura.empresa, '208', 'IVA Trasladado')
            
            cta_proveedores = AccountingService._get_or_create_cuenta(factura.empresa, '201', 'Proveedores')
            cta_gastos = AccountingService._get_or_create_cuenta(factura.empresa, '601', 'Gastos Generales')
            cta_iva_acred = AccountingService._get_or_create_cuenta(factura.empresa, '118', 'IVA Acreditable')

            # 3. Generar Movimientos (DEBE / HABER)
            movs = []
            
            if factura.naturaleza == 'I': # INGRESO (Venta)
                # Cargo a Clientes (Total)
                movs.append(MovimientoPoliza(poliza=poliza, cuenta=cta_clientes, debe=factura.total, haber=0, descripcion="Cobro a Cliente"))
                # Abono a Ventas (Subtotal)
                movs.append(MovimientoPoliza(poliza=poliza, cuenta=cta_ventas, debe=0, haber=factura.subtotal, descripcion="Venta"))
                # Abono a IVA (Impuestos)
                if factura.total_impuestos_trasladados > 0:
                    movs.append(MovimientoPoliza(poliza=poliza, cuenta=cta_iva_tras, debe=0, haber=factura.total_impuestos_trasladados, descripcion="IVA Trasladado"))
                    
            elif factura.naturaleza == 'E': # EGRESO (Compra/Gasto)
                # Cargo a Gastos (Subtotal)
                movs.append(MovimientoPoliza(poliza=poliza, cuenta=cta_gastos, debe=factura.subtotal, haber=0, descripcion="Gasto Operativo"))
                # Cargo a IVA (Impuestos)
                if factura.total_impuestos_trasladados > 0:
                    movs.append(MovimientoPoliza(poliza=poliza, cuenta=cta_iva_acred, debe=factura.total_impuestos_trasladados, haber=0, descripcion="IVA Acreditable"))
                # Abono a Proveedores (Total)
                movs.append(MovimientoPoliza(poliza=poliza, cuenta=cta_proveedores, debe=0, haber=factura.total, descripcion="Provision Proveedor"))

            # 4. Validar Cuadre
            total_debe = sum(m.debe for m in movs)
            total_haber = sum(m.haber for m in movs)
            
            # Ajuste de centavos (hack simple) si diferencia < 0.1
            diff = total_debe - total_haber
            if abs(diff) > 0 and abs(diff) < 0.1:
                # Ajustar al último movimiento
                if diff > 0: movs[-1].haber += diff
                else: movs[-1].debe += abs(diff)
            
            # Guardar Movimientos
            MovimientoPoliza.objects.bulk_create(movs)
            
            # 5. Actualizar Estado
            factura.estado_contable = 'CONTABILIZADA'
            factura.save()
            
            return poliza

    @staticmethod
    def _get_or_create_cuenta(empresa, codigo, nombre_base):
        cta, _ = CuentaContable.objects.get_or_create(
            empresa=empresa,
            codigo=codigo,
            defaults={'nombre': nombre_base, 'es_deudora': True}
        )
        return cta
