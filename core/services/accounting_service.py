from django.db import transaction, models
from core.models import Factura, Poliza, MovimientoPoliza, Empresa, PlantillaPoliza, CuentaContable
from core.services.account_resolver import AccountResolver
from core.services.sat_uso_cfdi_map import get_account_config
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class AccountingService:
    @staticmethod
    def _resolver_cuenta_por_uso_cfdi(empresa, uso_cfdi, factura):
        """
        Resuelve la cuenta contable basándose en el UsoCFDI del SAT.
        Crea la cuenta automáticamente si no existe.
        
        Args:
            empresa: Empresa
            uso_cfdi: Código UsoCFDI (G01, G03, I04, etc.)
            factura: Factura (para logging)
        
        Returns:
            CuentaContable: Cuenta resuelta o creada
        """
        # Obtener configuración del mapa SAT
        config = get_account_config(uso_cfdi)
        
        # Buscar o crear la cuenta
        cuenta, created = CuentaContable.objects.get_or_create(
            empresa=empresa,
            codigo=config['codigo_base'],
            defaults={
                'nombre': config['nombre'],
                'tipo': config['tipo'],
                'naturaleza': config['naturaleza'],
                'es_deudora': config['es_deudora'],
                'agrupador_sat': config['agrupador'],
                'nivel': 1  # Cuentas de UsoCFDI son nivel Mayor
            }
        )
        
        if created:
            logger.info(
                f"✅ Cuenta SAT creada: {cuenta.codigo} - {cuenta.nombre} "
                f"(UsoCFDI: {uso_cfdi}) para {factura.uuid}"
            )
        else:
            logger.debug(
                f"ℹ️  Cuenta SAT existente: {cuenta.codigo} (UsoCFDI: {uso_cfdi})"
            )
        
        return cuenta
    
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
            
            # --- INGRESO (I) - Factura Emitida / Nota de Crédito ---
            if factura.naturaleza == 'I':  # ← CAMBIO CRÍTICO: usar naturaleza
                # DETECCIÓN: ¿Es Nota de Crédito emitida?
                # Si tipo_comprobante='E' y somos el emisor, es Nota de Crédito
                es_nota_credito = (
                    factura.tipo_comprobante == 'E' and 
                    factura.emisor_rfc == factura.empresa.rfc
                )
                
                # Resolver cuenta de INGRESO (Ventas o Devoluciones)
                if es_nota_credito:
                    # Nota de Crédito: 402-01 Devoluciones sobre ventas
                    cuenta_ingreso, created = CuentaContable.objects.get_or_create(
                        empresa=factura.empresa,
                        codigo='402-01',
                        defaults={
                            'nombre': 'Devoluciones, Descuentos o Rebajas sobre Ventas',
                            'tipo': 'INGRESO',
                            'naturaleza': 'A',  # Acreedora pero resta
                            'es_deudora': True,  # Se carga (resta de ingresos)
                            'agrupador_sat': '402.01',
                            'nivel': 1
                        }
                    )
                    if created:
                        logger.info(f"✅ Cuenta 402-01 Devoluciones creada para {factura.empresa.nombre}")
                else:
                    # Venta normal: 401-01 Ventas y/o Servicios
                    cuenta_ingreso, created = CuentaContable.objects.get_or_create(
                        empresa=factura.empresa,
                        codigo='401-01',
                        defaults={
                            'nombre': 'Ventas y/o Servicios',
                            'tipo': 'INGRESO',
                            'naturaleza': 'A',  # Acreedora
                            'es_deudora': False,
                            'agrupador_sat': '401.01',
                            'nivel': 1
                        }
                    )
                    if created:
                        logger.info(f"✅ Cuenta 401-01 Ventas creada para {factura.empresa.nombre}")
                
                # Resolver subcuenta de cliente
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
                    # Fallback a cuenta genérica
                    cuenta_cliente, _ = CuentaContable.objects.get_or_create(
                        empresa=factura.empresa,
                        codigo='105-01',
                        defaults={'nombre': 'Clientes', 'tipo': 'ACTIVO', 'nivel': 1}
                    )
                
                # ASIENTO CONTABLE
                if es_nota_credito:
                    # Nota de Crédito: CARGO a Devoluciones, ABONO a Clientes
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=cuenta_ingreso,  # 402-01 Devoluciones
                        debe=factura.subtotal,
                        haber=0,
                        descripcion="Devolución sobre venta"
                    ))
                    # IVA (si aplica)
                    if factura.total_impuestos_trasladados > 0:
                        cuenta_iva, _ = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='119-01',
                            defaults={'nombre': 'IVA Acreditable', 'tipo': 'ACTIVO', 'nivel': 1}
                        )
                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=cuenta_iva,
                            debe=factura.total_impuestos_trasladados,
                            haber=0,
                            descripcion="IVA sobre devolución"
                        ))
                    # Abono a Cliente (reduce CxC)
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=cuenta_cliente,
                        debe=0,
                        haber=factura.total,
                        descripcion=f"Devolución a: {factura.receptor_nombre[:40]}"
                    ))
                else:
                    # Venta normal: CARGO a Clientes, ABONO a Ventas
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=cuenta_cliente,  # ← SUBCUENTA ESPECÍFICA POR RFC
                        debe=factura.total,
                        haber=0,
                        descripcion=f"Cliente: {factura.receptor_nombre[:40]} (RFC: {factura.receptor_rfc})"
                    ))
                    # Abono a Ventas (401-01)
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=cuenta_ingreso,  # 401-01 Ventas
                        debe=0,
                        haber=factura.subtotal,
                        descripcion="Venta de productos/servicios"
                    ))
                    # Abono a IVA Trasladado
                    if factura.total_impuestos_trasladados > 0:
                        cuenta_iva, _ = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='216-01',
                            defaults={'nombre': 'IVA Trasladado', 'tipo': 'PASIVO', 'nivel': 1, 'agrupador_sat': '216.01'}
                        )
                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=cuenta_iva,
                            debe=0,
                            haber=factura.total_impuestos_trasladados,
                            descripcion="IVA Trasladado"
                        ))

            # --- EGRESO (E) - Gasto/Compra/Inversión ---
            elif factura.naturaleza == 'E':  # ← CAMBIO CRÍTICO: usar naturaleza
                # NUEVA LÓGICA: Resolver cuenta por UsoCFDI del SAT
                # Esto permite clasificar automáticamente:
                # - G01 → Costo de Ventas (501-01)
                # - G03 → Gastos Generales (601-01)
                # - I04 → Equipo de Cómputo (153-01)
                # - etc.
                
                try:
                    cuenta_gasto = AccountingService._resolver_cuenta_por_uso_cfdi(
                        empresa=factura.empresa,
                        uso_cfdi=factura.uso_cfdi or 'G03',  # Default G03 si no tiene
                        factura=factura
                    )
                    logger.info(
                        f"✅ Cuenta por UsoCFDI '{factura.uso_cfdi or 'G03'}': "
                        f"{cuenta_gasto.codigo} - {cuenta_gasto.nombre}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error resolviendo UsoCFDI, usando plantilla: {e}")
                    # Fallback a plantilla si falla
                    cuenta_gasto = plantilla.cuenta_provision
                
                # Cargo a Gasto/Costo/Inversión -> Subtotal
                movs.append(MovimientoPoliza(
                    poliza=poliza, 
                    cuenta=cuenta_gasto,  # ← CUENTA DINÁMICA POR UsoCFDI
                    debe=factura.subtotal, 
                    haber=0, 
                    descripcion=f"{cuenta_gasto.nombre[:50]}"
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
