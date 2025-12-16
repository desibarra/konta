from django.db import transaction, models
from core.models import Factura, Poliza, MovimientoPoliza, Empresa, PlantillaPoliza, CuentaContable
from core.services.account_resolver import AccountResolver
from core.services.sat_uso_cfdi_map import get_account_config
from decimal import Decimal
import logging
import os
import xml.etree.ElementTree as ET
from django.conf import settings

logger = logging.getLogger(__name__)

class AccountingService:
    @staticmethod
    def _accumulate_impuestos_from_xml(factura):
        """
        Busca el XML asociado a la factura en la carpeta `xmls/` del proyecto y
        acumula los importes de Traslados (IVA impuesto 002) y Retenciones
        (ISR impuesto 001 y IVA impuesto 002) tanto a nivel comprobante como
        a nivel concepto.

        Retorna tuple: (total_iva_trasladado, total_isr_retenido, total_iva_retenido)
        Si no se encuentra o hay error, retorna valores basados en los campos
        ya parseados en la factura (fallback).
        """
        base_dir = getattr(settings, 'BASE_DIR', None) or os.getcwd()
        xml_dir = os.path.join(base_dir, 'xmls')
        uuid_str = str(factura.uuid)

        total_iva_trasladado = Decimal('0.00')
        total_isr_retenido = Decimal('0.00')
        total_iva_retenido = Decimal('0.00')
        total_descuento = Decimal('0.00')

        # Buscar archivo que contenga el UUID en el nombre
        if os.path.isdir(xml_dir):
            for name in os.listdir(xml_dir):
                if uuid_str in name and name.lower().endswith('.xml'):
                    path = os.path.join(xml_dir, name)
                    try:
                        tree = ET.parse(path)
                        root = tree.getroot()
                        # Determinar namespaces si existen
                        nsmap = {}
                        for k, v in root.attrib.items():
                            if k.startswith('xmlns'):
                                # k may be 'xmlns' or 'xmlns:cfdi'
                                parts = k.split(':')
                                if len(parts) == 2:
                                    nsmap[parts[1]] = v
                                else:
                                    nsmap[''] = v

                        # Helper to strip namespace
                        def tag_without_ns(t):
                            return t.split('}')[-1] if '}' in t else t

                        # Buscar Impuestos a nivel comprobante
                        for impuestos in root.findall('.//'):
                            if tag_without_ns(impuestos.tag).lower() == 'impuestos':
                                # Traslados
                                for tras in impuestos.findall('.//'):
                                    tag = tag_without_ns(tras.tag).lower()
                                    if tag == 'traslado' or tag == 'traslados':
                                        # If this is a traslado node, inspect attributes
                                        # If it's container, iterate children
                                        if tag == 'traslados':
                                            for t in tras:
                                                impuesto = t.attrib.get('Impuesto') or t.attrib.get('impuesto')
                                                importe = t.attrib.get('Importe') or t.attrib.get('importe')
                                                if impuesto == '002' and importe:
                                                    total_iva_trasladado += Decimal(importe)
                                        else:
                                            impuesto = tras.attrib.get('Impuesto') or tras.attrib.get('impuesto')
                                            importe = tras.attrib.get('Importe') or tras.attrib.get('importe')
                                            if impuesto == '002' and importe:
                                                total_iva_trasladado += Decimal(importe)

                                # Retenciones
                                for ret in impuestos.findall('.//'):
                                    tag2 = tag_without_ns(ret.tag).lower()
                                    if tag2 == 'retencion' or tag2 == 'retenciones':
                                        if tag2 == 'retenciones':
                                            for r in ret:
                                                impuesto = r.attrib.get('Impuesto') or r.attrib.get('impuesto')
                                                importe = r.attrib.get('Importe') or r.attrib.get('importe')
                                                if impuesto == '001' and importe:
                                                    total_isr_retenido += Decimal(importe)
                                                if impuesto == '002' and importe:
                                                    total_iva_retenido += Decimal(importe)
                                        else:
                                            impuesto = ret.attrib.get('Impuesto') or ret.attrib.get('impuesto')
                                            importe = ret.attrib.get('Importe') or ret.attrib.get('importe')
                                            if impuesto == '001' and importe:
                                                total_isr_retenido += Decimal(importe)
                                            if impuesto == '002' and importe:
                                                total_iva_retenido += Decimal(importe)

                        # Buscar en conceptos: impuestos por concepto
                        for concepto in root.findall('.//'):
                            if tag_without_ns(concepto.tag).lower() == 'concepto' or tag_without_ns(concepto.tag).lower() == 'conceptos':
                                for c in concepto.findall('.//'):
                                    tagc = tag_without_ns(c.tag).lower()
                                    if tagc == 'traslado' or tagc == 'traslados':
                                        if tagc == 'traslados':
                                            for t in c:
                                                impuesto = t.attrib.get('Impuesto') or t.attrib.get('impuesto')
                                                importe = t.attrib.get('Importe') or t.attrib.get('importe')
                                                if impuesto == '002' and importe:
                                                    total_iva_trasladado += Decimal(importe)
                                        else:
                                            impuesto = c.attrib.get('Impuesto') or c.attrib.get('impuesto')
                                            importe = c.attrib.get('Importe') or c.attrib.get('importe')
                                            if impuesto == '002' and importe:
                                                total_iva_trasladado += Decimal(importe)
                                    if tagc == 'retencion' or tagc == 'retenciones':
                                        if tagc == 'retenciones':
                                            for r in c:
                                                impuesto = r.attrib.get('Impuesto') or r.attrib.get('impuesto')
                                                importe = r.attrib.get('Importe') or r.attrib.get('importe')
                                                if impuesto == '001' and importe:
                                                    total_isr_retenido += Decimal(importe)
                                                if impuesto == '002' and importe:
                                                    total_iva_retenido += Decimal(importe)
                                        else:
                                            impuesto = c.attrib.get('Impuesto') or c.attrib.get('impuesto')
                                            importe = c.attrib.get('Importe') or c.attrib.get('importe')
                                            if impuesto == '001' and importe:
                                                total_isr_retenido += Decimal(importe)
                                            if impuesto == '002' and importe:
                                                total_iva_retenido += Decimal(importe)

                        # Extraer atributo Descuento (si existe) en el nodo Comprobante
                        # Los atributos pueden venir como 'Descuento' o 'descuento'
                        for a_k, a_v in root.attrib.items():
                            key = tag_without_ns(a_k).lower()
                            if key == 'descuento' and a_v:
                                try:
                                    total_descuento = Decimal(a_v)
                                except Exception:
                                    total_descuento = Decimal('0.00')
                                break

                        # Successful parse -> return accumulated totals + descuento
                        return (
                            total_iva_trasladado.quantize(Decimal('0.01')),
                            total_isr_retenido.quantize(Decimal('0.01')),
                            total_iva_retenido.quantize(Decimal('0.01')),
                            total_descuento.quantize(Decimal('0.01'))
                        )
                    except Exception:
                        # On any parse error, fall back to stored fields
                        break

        # Fallback to fields parsed earlier (if XML not found or error)
        # Fallback: si no se encuentra XML, intentar usar campos existentes en la factura
        return (
            getattr(factura, 'total_impuestos_trasladados', Decimal('0.00')) or Decimal('0.00'),
            Decimal('0.00'),
            getattr(factura, 'total_impuestos_retenidos', Decimal('0.00')) or Decimal('0.00'),
            getattr(factura, 'descuento', Decimal('0.00')) or Decimal('0.00')
        )

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
            # Acumular impuestos leyendo el XML original si existe (más robusto)
            total_iva_trasladado, total_isr_retenido, total_iva_retenido, total_descuento = AccountingService._accumulate_impuestos_from_xml(factura)

            # --- AUDITORÍA 360°: calcular y validar componentes clave del comprobante
            # Subtotal real: suma de importes en conceptos (fallback a factura.subtotal)
            conceptos_qs = factura.conceptos.all()
            if conceptos_qs.exists():
                total_subtotal = sum((c.importe for c in conceptos_qs), Decimal('0.00'))
            else:
                total_subtotal = getattr(factura, 'subtotal', Decimal('0.00')) or Decimal('0.00')

            # Traslados: solo Impuesto='002' (IVA) acumulado desde XML helper
            total_traslados = total_iva_trasladado or Decimal('0.00')

            # Retenciones: ISR (001) + IVA (002)
            total_retenciones = (total_isr_retenido or Decimal('0.00')) + (total_iva_retenido or Decimal('0.00'))

            # Gran total esperado por la póliza = Subtotal + Traslados - Retenciones - Descuento
            gran_total = (total_subtotal + total_traslados - total_retenciones - (total_descuento or Decimal('0.00'))).quantize(Decimal('0.01'))

            # Validación: comparar con factura.total
            try:
                factura_total = getattr(factura, 'total', Decimal('0.00')) or Decimal('0.00')
            except Exception:
                factura_total = Decimal('0.00')

            if (gran_total - factura_total).copy_abs() > Decimal('0.05'):
                logger.warning(
                    f"⚠️ Discrepancia en totales XML vs Factura ({factura.uuid}): "
                    f"subtotal={total_subtotal} traslados={total_traslados} retenciones={total_retenciones} "
                    f"gran_total={gran_total} factura.total={factura_total}"
                )
            
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
                        debe=total_subtotal,
                        haber=0,
                        descripcion="Devolución sobre venta"
                    ))
                    # IVA (si aplica)
                    if total_iva_trasladado > 0:
                        cuenta_iva, _ = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='119-01',
                            defaults={'nombre': 'IVA Acreditable', 'tipo': 'ACTIVO', 'nivel': 1}
                        )
                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=cuenta_iva,
                            debe=total_iva_trasladado,
                            haber=0,
                            descripcion="IVA sobre devolución"
                        ))
                    # Abono a Cliente (reduce CxC)
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=cuenta_cliente,
                        debe=0,
                        haber=gran_total,
                        descripcion=f"Devolución a: {factura.receptor_nombre[:40]}"
                    ))
                else:
                    # Venta normal: CARGO a Clientes, ABONO a Ventas
                    # Manejo de retenciones en facturas emitidas:
                    # Si la factura reporta retenciones, las registramos como
                    # un ACTIVO (Impuestos a favor) y registramos la CxC
                    # por el neto (total - retenciones).
                    reten_total = (total_isr_retenido or Decimal('0.00')) + (total_iva_retenido or Decimal('0.00'))

                    # Reconstruir cargo a Clientes desde componentes (Conceptos + Traslados - Retenciones)
                    cargo_clientes_calc = (total_subtotal + total_traslados - (total_isr_retenido or Decimal('0.00')) - (total_iva_retenido or Decimal('0.00'))).quantize(Decimal('0.01'))

                    # Comparar con Total del XML; si la diferencia > $1 usamos el Total del XML y ajustamos IVA
                    iva_adjustment = Decimal('0.00')
                    if (cargo_clientes_calc - factura_total).copy_abs() > Decimal('1.00'):
                        iva_adjustment = (factura_total - cargo_clientes_calc).quantize(Decimal('0.01'))
                        cliente_debe_final = factura_total
                        logger.warning(f"🔧 Ajuste por discrepancia (>1$) en factura {factura.uuid}: cargo_calc={cargo_clientes_calc} total_xml={factura_total} ajuste_iva={iva_adjustment}")
                    else:
                        cliente_debe_final = cargo_clientes_calc

                    if reten_total and reten_total != Decimal('0.00'):
                        reten_cta, created = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='119-02',
                            defaults={
                                'nombre': 'Impuestos a Favor (Retenciones)',
                                'tipo': 'ACTIVO',
                                'naturaleza': 'D',
                                'es_deudora': True,
                                'nivel': 1
                            }
                        )
                        if created:
                            logger.info(f"✅ Cuenta 119-02 (Impuestos a Favor) creada para {factura.empresa.nombre}")

                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=reten_cta,
                            debe=reten_total,
                            haber=0,
                            descripcion='Retenciones a favor (Emitido)'
                        ))

                    # Registrar cargo a Cliente (CxC) por el valor calculado/final
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=cuenta_cliente,
                        debe=cliente_debe_final,
                        haber=0,
                        descripcion=f"Cliente: {factura.receptor_nombre[:40]} (RFC: {factura.receptor_rfc})"
                    ))

                    # Si existe descuento en el XML, registrar cuenta de descuentos (402-01)
                    monto_descuento = (total_descuento or Decimal('0.00'))
                    if monto_descuento and monto_descuento != Decimal('0.00'):
                        # Crear/obtener cuenta 402-01 Descuentos sobre Ventas como auxiliar (nivel 3)
                        desc_cta, created = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='402-01',
                            defaults={
                                'nombre': 'Descuentos sobre Ventas',
                                'tipo': 'GASTO',
                                'naturaleza': 'D',
                                'es_deudora': True,
                                'nivel': 3
                            }
                        )
                        if created:
                            logger.info(f"✅ Cuenta 402-01 Descuentos creada para {factura.empresa.nombre}")

                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=desc_cta,
                            debe=monto_descuento,
                            haber=0,
                            descripcion='Descuento concedido (XML)'
                        ))

                    # Abono a Ventas (401-01)
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=cuenta_ingreso,  # 401-01 Ventas
                        debe=0,
                        haber=total_subtotal,
                        descripcion="Venta de productos/servicios"
                    ))

                    # Abono a IVA Trasladado (ajustado si es necesario para empatar con Total XML)
                    iva_to_post = (total_iva_trasladado or Decimal('0.00')) + (iva_adjustment or Decimal('0.00'))
                    if iva_to_post and iva_to_post != Decimal('0.00'):
                        cuenta_iva, _ = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='216-01',
                            defaults={'nombre': 'IVA Trasladado', 'tipo': 'PASIVO', 'nivel': 1, 'agrupador_sat': '216.01'}
                        )
                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=cuenta_iva,
                            debe=0,
                            haber=iva_to_post,
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
                    debe=total_subtotal, 
                    haber=0, 
                    descripcion=f"{cuenta_gasto.nombre[:50]}"
                ))
                # Cargo a Impuesto (IVA Acreditable) -> Impuestos
                if total_iva_trasladado > 0:
                    if plantilla.cuenta_impuesto:
                        movs.append(MovimientoPoliza(
                            poliza=poliza, cuenta=plantilla.cuenta_impuesto, 
                            debe=total_iva_trasladado, haber=0, 
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
                # Manejo de retenciones: si existen, registrar Pasivo por Retenciones
                retenciones = (total_isr_retenido or Decimal('0.00')) + (total_iva_retenido or Decimal('0.00'))

                if retenciones and retenciones != Decimal('0.00'):
                    # Buscar/crear cuenta de Retenciones por Pagar (preferencia 213-01)
                    retenidos_cta, created = CuentaContable.objects.get_or_create(
                        empresa=factura.empresa,
                        codigo='213-01',
                        defaults={
                            'nombre': 'Impuestos Retenidos por Pagar',
                            'tipo': 'PASIVO',
                            'naturaleza': 'A',
                            'nivel': 1
                        }
                    )
                    if created:
                        logger.info(f"✅ Cuenta 213-01 creada para retenciones en {factura.empresa.nombre}")

                    # Registrar abono por retenciones (pasivo)
                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=retenidos_cta,
                        debe=0,
                        haber=retenciones,
                        descripcion='Impuestos retenidos (IVA/ISR)'
                    ))

                # Abono a proveedor: neto pagadero (factura.total == subtotal+traslados-retenciones)
                proveedor_haber = factura_total

                # Si existe descuento en el XML, registrar como Abono a cuenta de descuentos (502-01)
                monto_descuento = (total_descuento or Decimal('0.00'))
                if monto_descuento and monto_descuento != Decimal('0.00'):
                    # Crear/obtener cuenta 502-01 Descuentos sobre Compras como auxiliar (nivel 3)
                    desc_cta, created = CuentaContable.objects.get_or_create(
                        empresa=factura.empresa,
                        codigo='502-01',
                        defaults={
                            'nombre': 'Descuentos sobre Compras',
                            'tipo': 'GASTO',
                            'naturaleza': 'D',
                            'es_deudora': True,
                            'level': 3,
                            'nivel': 3
                        }
                    )
                    if created:
                        logger.info(f"✅ Cuenta 502-01 Descuentos creada para {factura.empresa.nombre}")

                    movs.append(MovimientoPoliza(
                        poliza=poliza,
                        cuenta=desc_cta,
                        debe=0,
                        haber=monto_descuento,
                        descripcion='Descuento en compra (XML)'
                    ))

                movs.append(MovimientoPoliza(
                    poliza=poliza,
                    cuenta=cuenta_proveedor,  # ← SUBCUENTA ESPECÍFICA POR RFC
                    debe=0,
                    haber=proveedor_haber,
                    descripcion=f"Proveedor: {factura.emisor_nombre[:40]} (RFC: {factura.emisor_rfc})"
                ))

            # 5. Validar Cuadre y Ajuste de Centavos
            # --- Asegurar que los descuentos del XML se registren siempre ---
            try:
                # Preferir el descuento declarado en el XML; si es cero, usar el campo factura.descuento
                if total_descuento and total_descuento != Decimal('0.00'):
                    monto_descuento = total_descuento
                else:
                    monto_descuento = getattr(factura, 'descuento', Decimal('0.00')) or Decimal('0.00')
            except Exception:
                monto_descuento = getattr(factura, 'descuento', Decimal('0.00')) or Decimal('0.00')

            if monto_descuento and monto_descuento != Decimal('0.00'):
                # Verificar si ya hay movimientos de descuento añadidos
                already = any(
                    getattr(m.cuenta, 'codigo', '').startswith('402-01') or getattr(m.cuenta, 'codigo', '').startswith('502-01')
                    for m in movs
                )
                if not already:
                    # Inferir si debemos tratar el descuento como sobre VENTAS (402) o COMPRAS (502)
                    is_issuer = getattr(factura, 'emisor_rfc', None) == getattr(factura.empresa, 'rfc', None)
                    is_receiver = getattr(factura, 'receptor_rfc', None) == getattr(factura.empresa, 'rfc', None)

                    # Preferir la naturaleza si es clara
                    target = None
                    if factura.naturaleza == 'I' or is_issuer:
                        target = '402'
                    elif factura.naturaleza == 'E' or is_receiver:
                        target = '502'
                    else:
                        # Fallback: si el emisor es la empresa -> 402, si el receptor es la empresa -> 502
                        if is_issuer:
                            target = '402'
                        elif is_receiver:
                            target = '502'
                        else:
                            # Último recurso: asignar a 402-01 (impacta resultados)
                            target = '402'

                    if target == '402':
                        desc_cta, created = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='402-01',
                            defaults={
                                'nombre': 'Descuentos sobre Ventas',
                                'tipo': 'GASTO',
                                'naturaleza': 'D',
                                'es_deudora': True,
                                'nivel': 3
                            }
                        )
                        if created:
                            logger.info(f"✅ Cuenta 402-01 Descuentos creada para {factura.empresa.nombre}")

                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=desc_cta,
                            debe=monto_descuento,
                            haber=0,
                            descripcion='Descuento (XML) - registrado automáticamente'
                        ))
                    else:
                        desc_cta, created = CuentaContable.objects.get_or_create(
                            empresa=factura.empresa,
                            codigo='502-01',
                            defaults={
                                'nombre': 'Descuentos sobre Compras',
                                'tipo': 'GASTO',
                                'naturaleza': 'D',
                                'es_deudora': True,
                                'nivel': 3
                            }
                        )
                        if created:
                            logger.info(f"✅ Cuenta 502-01 Descuentos creada para {factura.empresa.nombre}")

                        movs.append(MovimientoPoliza(
                            poliza=poliza,
                            cuenta=desc_cta,
                            debe=0,
                            haber=monto_descuento,
                            descripcion='Descuento (XML) - registrado automáticamente'
                        ))

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
