#!/usr/bin/env python3
"""
Valida que los impuestos y retenciones presentes en los XMLs estén
reflejados en los movimientos de póliza asociados a cada factura.

Salida: informe en consola con discrepancias por UUID.
"""
import os
import sys
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET

if __name__ == '__main__':
    # Cargar Django
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
    import django
    django.setup()

    from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable
    from django.conf import settings

    base_dir = getattr(settings, 'BASE_DIR', project_root)
    xml_dir = os.path.join(base_dir, 'xmls')

    def local_name(tag):
        return tag.split('}')[-1] if '}' in tag else tag

    def parse_xml_file(path):
        tree = ET.parse(path)
        root = tree.getroot()
        # Buscar UUID en TimbreFiscalDigital
        uuid = None
        for el in root.iter():
            if local_name(el.tag).lower() == 'timbrefiscaldigital' or local_name(el.tag) == 'TimbreFiscalDigital':
                uuid = el.attrib.get('UUID') or el.attrib.get('Uuid')
                if uuid:
                    break

        # Acumular traslados y retenciones
        iva_trasladado = Decimal('0.00')
        isr_retenido = Decimal('0.00')
        iva_retenido = Decimal('0.00')

        for impuestos in root.iter():
            if local_name(impuestos.tag).lower() != 'impuestos':
                continue
            # Traslados
            for t in impuestos:
                tag = local_name(t.tag).lower()
                if tag in ('traslado', 'traslados'):
                    # if container
                    if tag == 'traslados':
                        for item in t:
                            imp = item.attrib.get('Impuesto') or item.attrib.get('impuesto')
                            imp_amt = item.attrib.get('Importe') or item.attrib.get('importe')
                            if imp and imp_amt:
                                if imp == '002':
                                    try:
                                        imp_amt = Decimal(imp_amt)
                                    except (ValueError, TypeError, InvalidOperation):
                                        print(f"Valor inválido para importe: {imp_amt}")
                                        continue

                                    iva_trasladado += imp_amt
                    else:
                        imp = t.attrib.get('Impuesto') or t.attrib.get('impuesto')
                        imp_amt = t.attrib.get('Importe') or t.attrib.get('importe')
                        if imp == '002' and imp_amt:
                            try:
                                imp_amt = Decimal(imp_amt)
                            except (ValueError, TypeError, InvalidOperation):
                                print(f"Valor inválido para importe: {imp_amt}")
                                continue

                            iva_trasladado += imp_amt

            # Retenciones
            for r in impuestos:
                tagr = local_name(r.tag).lower()
                if tagr in ('retencion', 'retenciones'):
                    if tagr == 'retenciones':
                        for item in r:
                            imp = item.attrib.get('Impuesto') or item.attrib.get('impuesto')
                            imp_amt = item.attrib.get('Importe') or item.attrib.get('importe')
                            if imp and imp_amt:
                                if imp == '001':
                                    try:
                                        imp_amt = Decimal(imp_amt)
                                    except (ValueError, TypeError, InvalidOperation):
                                        print(f"Valor inválido para importe: {imp_amt}")
                                        continue

                                    isr_retenido += imp_amt
                                if imp == '002':
                                    try:
                                        imp_amt = Decimal(imp_amt)
                                    except (ValueError, TypeError, InvalidOperation):
                                        print(f"Valor inválido para importe: {imp_amt}")
                                        continue

                                    iva_retenido += imp_amt
                    else:
                        imp = r.attrib.get('Impuesto') or r.attrib.get('impuesto')
                        imp_amt = r.attrib.get('Importe') or r.attrib.get('importe')
                        if imp and imp_amt:
                            if imp == '001':
                                try:
                                    imp_amt = Decimal(imp_amt)
                                except (ValueError, TypeError, InvalidOperation):
                                    print(f"Valor inválido para importe: {imp_amt}")
                                    continue

                                isr_retenido += imp_amt
                            if imp == '002':
                                try:
                                    imp_amt = Decimal(imp_amt)
                                except (ValueError, TypeError, InvalidOperation):
                                    print(f"Valor inválido para importe: {imp_amt}")
                                    continue

                                iva_retenido += imp_amt

        # Además, buscar traslados/retenciones dentro de conceptos
        for concepto in root.iter():
            if local_name(concepto.tag).lower() not in ('concepto', 'conceptos'):
                continue
            for c in concepto:
                tagc = local_name(c.tag).lower()
                if tagc in ('traslado', 'traslados'):
                    if tagc == 'traslados':
                        for t in c:
                            imp = t.attrib.get('Impuesto') or t.attrib.get('impuesto')
                            imp_amt = t.attrib.get('Importe') or t.attrib.get('importe')
                            if imp == '002' and imp_amt:
                                try:
                                    imp_amt = Decimal(imp_amt)
                                except (ValueError, TypeError, InvalidOperation):
                                    print(f"Valor inválido para importe: {imp_amt}")
                                    continue

                                iva_trasladado += imp_amt
                    else:
                        imp = c.attrib.get('Impuesto') or c.attrib.get('impuesto')
                        imp_amt = c.attrib.get('Importe') or c.attrib.get('importe')
                        if imp == '002' and imp_amt:
                            try:
                                imp_amt = Decimal(imp_amt)
                            except (ValueError, TypeError, InvalidOperation):
                                print(f"Valor inválido para importe: {imp_amt}")
                                continue

                            iva_trasladado += imp_amt
                if tagc in ('retencion', 'retenciones'):
                    if tagc == 'retenciones':
                        for r in c:
                            imp = r.attrib.get('Impuesto') or r.attrib.get('impuesto')
                            imp_amt = r.attrib.get('Importe') or r.attrib.get('importe')
                            if imp and imp_amt:
                                if imp == '001':
                                    try:
                                        imp_amt = Decimal(imp_amt)
                                    except (ValueError, TypeError, InvalidOperation):
                                        print(f"Valor inválido para importe: {imp_amt}")
                                        continue

                                    isr_retenido += imp_amt
                                if imp == '002':
                                    try:
                                        imp_amt = Decimal(imp_amt)
                                    except (ValueError, TypeError, InvalidOperation):
                                        print(f"Valor inválido para importe: {imp_amt}")
                                        continue

                                    iva_retenido += imp_amt
                    else:
                        imp = c.attrib.get('Impuesto') or c.attrib.get('impuesto')
                        imp_amt = c.attrib.get('Importe') or c.attrib.get('importe')
                        if imp and imp_amt:
                            if imp == '001':
                                try:
                                    imp_amt = Decimal(imp_amt)
                                except (ValueError, TypeError, InvalidOperation):
                                    print(f"Valor inválido para importe: {imp_amt}")
                                    continue

                                isr_retenido += imp_amt
                            if imp == '002':
                                try:
                                    imp_amt = Decimal(imp_amt)
                                except (ValueError, TypeError, InvalidOperation):
                                    print(f"Valor inválido para importe: {imp_amt}")
                                    continue

                                iva_retenido += imp_amt

        return uuid, iva_trasladado.quantize(Decimal('0.01')), isr_retenido.quantize(Decimal('0.01')), iva_retenido.quantize(Decimal('0.01'))

    # Ejecutar sobre archivos
    processed = 0
    mismatches = 0
    print("Validando XMLs en:", xml_dir)
    if not os.path.isdir(xml_dir):
        print("No existe carpeta xmls/ en el proyecto.")
        sys.exit(1)

    for fname in sorted(os.listdir(xml_dir)):
        if not fname.lower().endswith('.xml'):
            continue
        path = os.path.join(xml_dir, fname)
        try:
            uuid, iva_tr, isr_rt, iva_rt = parse_xml_file(path)
        except Exception as e:
            print(f"ERROR parseando {fname}: {e}")
            continue

        if not uuid:
            print(f"{fname}: UUID no encontrado, saltando.")
            continue

        processed += 1
        factura = Factura.objects.filter(uuid=uuid).first()
        # Recolectar movimientos por cuenta (codigo) en TODAS las pólizas de la factura
        movs_by_code = {}
        polizas = []
        if factura:
            polizas = list(Poliza.objects.filter(factura=factura))
        else:
            polizas = list(Poliza.objects.filter(factura__uuid=uuid))

        if polizas:
            for pol in polizas:
                for m in MovimientoPoliza.objects.filter(poliza=pol):
                    code = m.cuenta.codigo
                    movs_by_code.setdefault(code, Decimal('0.00'))
                    movs_by_code[code] += (m.haber - m.debe)

        # Comparaciones simples
        xml_total_reten = isr_rt + iva_rt

        iva_trasladado_match = (movs_by_code.get('216-01', Decimal('0.00')) == iva_tr)
        reten_activo_match = (movs_by_code.get('119-02', Decimal('0.00')) == xml_total_reten)
        reten_pasivo_match = (movs_by_code.get('213-01', Decimal('0.00')) == xml_total_reten)

        if not (iva_trasladado_match and (reten_activo_match or reten_pasivo_match)):
            mismatches += 1
            print('\nMISMATCH:', fname, 'UUID=', uuid)
            print('  XML IVA trasl:', iva_tr, ' Mov(216-01):', movs_by_code.get('216-01', Decimal('0.00')))
            print('  XML ISR reten:', isr_rt, ' XML IVA reten:', iva_rt, ' Total reten:', xml_total_reten)
            print('  Mov(119-02) activo ret:', movs_by_code.get('119-02', Decimal('0.00')))
            print('  Mov(213-01) pasivo ret:', movs_by_code.get('213-01', Decimal('0.00')))
            print('  Movimientos por cuenta (todos):')
            for c, v in sorted(movs_by_code.items()):
                print(f'    {c:12s} -> {v}')
            if factura:
                print('  Factura encontrada:', factura.uuid, ' Total:', factura.total)
            else:
                print('  Factura NO encontrada en DB')

    print('\nProcesados:', processed, 'XMLs. Discrepancias:', mismatches)
