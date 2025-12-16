from django.db import transaction, models
from core.models import Factura, Poliza, MovimientoPoliza, Empresa, PlantillaPoliza
from core.services.account_resolver import AccountResolver
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class AccountingService:
    @staticmethod
    def contabilizar_factura(factura_uuid, usuario_id=None, plantilla_id=None):
        """
        Genera la Póliza Contable para una factura dada usando una Plantilla.
        
        LÓGICA INTELIGENTE:
        - Busca plantilla que coincida con tipo_comprobante de la factura (I, E, P, N, T)
        - Si no hay plantilla específica, usa la default del tipo
        - Valida que la empresa tenga plantillas configuradas
        
        Args:
            factura_uuid: UUID de la factura a contabilizar
            usuario_id: ID del usuario que contabiliza (opcional)
            plantilla_id: ID de plantilla específica (opcional, si no se usa auto-selección)
        
        Returns:
            Poliza: La póliza contable creada
        
        Raises:
            ValueError: Si no se puede contabilizar o falta configuración
        """
        try:
            factura = Factura.objects.select_related('empresa').get(uuid=factura_uuid)
        except Factura.DoesNotExist:
            raise ValueError("Factura no encontrada")

        if factura.estado_contable == 'CONTABILIZADA':
            raise ValueError("Esta factura ya está contabilizada")
        
        if factura.estado_contable == 'EXCLUIDA':
            raise ValueError("Esta factura está excluida de contabilización")

        # 1. Resolver Plantilla (LÓGICA INTELIGENTE)
        plantilla = None
        if plantilla_id:
            # Usuario seleccionó plantilla manualmente
            try:
                plantilla = PlantillaPoliza.objects.get(pk=plantilla_id, empresa=factura.empresa)
            except PlantillaPoliza.DoesNotExist:
                raise ValueError("La plantilla seleccionada no existe o no pertenece a esta empresa.")
        else:
            # AUTO-SELECCIÓN: Buscar por NATURALEZA (I/E) en lugar de tipo_comprobante
            # CRÍTICO: Las facturas de egreso pueden tener tipo_comprobante='I' en el XML
            # pero naturaleza='E' basándose en el RFC. Usamos naturaleza para la plantilla.
            plantilla = PlantillaPoliza.objects.filter(
                empresa=factura.empresa, 
                tipo_factura=factura.naturaleza,  # ← CAMBIO CRÍTICO: usar naturaleza (I/E)
                es_default=True
            ).first()
            
            if not plantilla:
                # Fallback: Buscar CUALQUIERA del mismo tipo
                plantilla = PlantillaPoliza.objects.filter(
                    empresa=factura.empresa, 
                    tipo_factura=factura.naturaleza  # ← CAMBIO CRÍTICO: usar naturaleza (I/E)
                ).first()

        if not plantilla:
            raise ValueError(
                f"No existe plantilla contable para {factura.get_tipo_comprobante_display()}. "
                "Configure una en el Panel de Administración o seleccione una manualmente."
            )

        with transaction.atomic():
            # 2. Limpieza de Póliza Previa (si existe)
            Poliza.objects.filter(factura=factura).delete()

            # 3. Crear Cabecera de Póliza
            poliza = Poliza.objects.create(
                factura=factura,
                fecha=factura.fecha.date() if hasattr(factura.fecha, 'date') else factura.fecha,
                descripcion=f"{factura.get_tipo_comprobante_display()} - {factura.emisor_nombre[:50]}",
                plantilla_usada=plantilla
            )

            # 4. Generar Movimientos según NATURALEZA (I/E)
            # CRÍTICO: Usar naturaleza en lugar de tipo_comprobante
            # porque facturas de egreso pueden tener tipo_comprobante='I' en el XML
            movs = []
            
            # --- INGRESO (I) - Factura Emitida ---
            if factura.naturaleza == 'I':  # ← CAMBIO CRÍTICO: usar naturaleza
                # CAMBIO CRÍTICO: Usar AccountResolver para subcuenta específica del cliente
                try:
                    cuenta_cliente = AccountResolver.resolver_cuenta_cliente(
                        empresa=factura.empresa,
                        factura=factura
                    )
                    logger.info(
                        f"✅ Cuenta cliente resuelta: {cuenta_cliente.codigo} "
                        f"para {factura.receptor_nombre[:30]}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error resolviendo cuenta cliente: {e}")
                    # Fallback a cuenta de plantilla si falla AccountResolver
                    cuenta_cliente = plantilla.cuenta_flujo
                
                # Cargo a Flujo (Clientes) -> Total
                movs.append(MovimientoPoliza(
                    poliza=poliza, 
                    cuenta=cuenta_cliente,  # ← SUBCUENTA ESPECÍFICA POR RFC
                    debe=factura.total, 
                    haber=0, 
                    descripcion=f"Cliente: {factura.receptor_nombre[:40]} (RFC: {factura.receptor_rfc})"
                ))
                # Abono a Provisión (Ventas) -> Subtotal
                movs.append(MovimientoPoliza(
                    poliza=poliza, cuenta=plantilla.cuenta_provision, 
                    debe=0, haber=factura.subtotal, 
                    descripcion="Venta de productos/servicios"
                ))
                # Abono a Impuesto (IVA Trasladado) -> Impuestos
                if factura.total_impuestos_trasladados > 0:
                    if plantilla.cuenta_impuesto:
                        movs.append(MovimientoPoliza(
                            poliza=poliza, cuenta=plantilla.cuenta_impuesto, 
                            debe=0, haber=factura.total_impuestos_trasladados, 
                            descripcion="IVA Trasladado"
                        ))
                    else:
                        raise ValueError("La factura tiene IVA pero la plantilla no tiene cuenta de impuestos configurada.")

            # --- EGRESO (E) - Gasto/Compra ---
            elif factura.naturaleza == 'E':  # ← CAMBIO CRÍTICO: usar naturaleza 
                # Cargo a Provisión (Gasto/Costo) -> Subtotal
                movs.append(MovimientoPoliza(
                    poliza=poliza, cuenta=plantilla.cuenta_provision, 
                    debe=factura.subtotal, haber=0, descripcion="Gasto Operativo / Compra"
                ))
                # Cargo a Impuesto (IVA Acreditable) -> Impuestos
                if factura.total_impuestos_trasladados > 0:
                    if plantilla.cuenta_impuesto:
                        movs.append(MovimientoPoliza(
                            poliza=poliza, cuenta=plantilla.cuenta_impuesto, 
                            debe=factura.total_impuestos_trasladados, haber=0, 
                            descripcion="IVA Acreditable"
                        ))
                    else:
                         raise ValueError("La factura tiene impuestos pero la plantilla no tiene cuenta de impuestos configurada.")
                
                # CAMBIO CRÍTICO: Usar AccountResolver para subcuenta específica del proveedor
                try:
                    cuenta_proveedor = AccountResolver.resolver_cuenta_proveedor(
                        empresa=factura.empresa,
                        factura=factura
                    )
                    logger.info(
                        f"✅ Cuenta proveedor resuelta: {cuenta_proveedor.codigo} "
                        f"para {factura.emisor_nombre[:30]}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error resolviendo cuenta proveedor: {e}")
                    # Fallback a cuenta de plantilla si falla AccountResolver
                    cuenta_proveedor = plantilla.cuenta_flujo
                
                # Abono a Flujo (Proveedores/Banco) -> Total
                movs.append(MovimientoPoliza(
                    poliza=poliza, 
                    cuenta=cuenta_proveedor,  # ← SUBCUENTA ESPECÍFICA POR RFC
                    debe=0, 
                    haber=factura.total, 
                    descripcion=f"Proveedor: {factura.emisor_nombre[:40]} (RFC: {factura.emisor_rfc})"
                ))

            # 5. Validar Cuadre y Ajuste de Centavos
            total_debe = sum(m.debe for m in movs)
            total_haber = sum(m.haber for m in movs)
            
            diff = total_debe - total_haber
            if abs(diff) > 0 and abs(diff) < 0.1:
                if diff > 0: movs[-1].haber += diff
                else: movs[-1].debe += abs(diff)
            
            # Guardar Movimientos
            MovimientoPoliza.objects.bulk_create(movs)
            
            # 6. Actualizar Estado
            factura.estado_contable = 'CONTABILIZADA'
            factura.save()
            
            return poliza
