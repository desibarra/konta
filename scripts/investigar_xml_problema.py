"""
Investigar contabilización del XML 673F1724-B6A9-4BE7-932F-86BD3E891F09
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza, MovimientoPoliza
from decimal import Decimal
import uuid

# UUID del XML problemático
uuid_str = '673F1724-B6A9-4BE7-932F-86BD3E891F09'
uuid_obj = uuid.UUID(uuid_str)

print("=" * 80)
print(f"INVESTIGACIÓN: XML {uuid_str}")
print("=" * 80)

try:
    factura = Factura.objects.get(uuid=uuid_obj)
    
    print(f"\n📄 DATOS DE LA FACTURA:")
    print(f"   UUID: {factura.uuid}")
    print(f"   Fecha: {factura.fecha}")
    print(f"   Tipo: {factura.tipo_comprobante}")
    print(f"   Naturaleza: {factura.naturaleza}")
    print(f"   Estado: {factura.estado_contable}")
    print(f"   Emisor: {factura.emisor_nombre} ({factura.emisor_rfc})")
    print(f"   Receptor: {factura.receptor_nombre} ({factura.receptor_rfc})")
    print(f"\n💰 IMPORTES:")
    print(f"   Subtotal: ${factura.subtotal:,.2f}")
    print(f"   Descuento: ${factura.descuento:,.2f}")
    print(f"   IVA Trasladado: ${factura.total_impuestos_trasladados:,.2f}")
    print(f"   IVA Retenido: ${factura.total_impuestos_retenidos:,.2f}")
    print(f"   TOTAL: ${factura.total:,.2f}")
    
    # Buscar póliza
    try:
        poliza = Poliza.objects.get(factura=factura)
        movimientos = MovimientoPoliza.objects.filter(poliza=poliza)
        
        print(f"\n📋 PÓLIZA #{poliza.id}")
        print(f"   Fecha: {poliza.fecha}")
        print(f"   Descripción: {poliza.descripcion}")
        print(f"\n   MOVIMIENTOS:")
        
        total_debe = Decimal('0')
        total_haber = Decimal('0')
        ajuste_702 = None
        
        for mov in movimientos:
            print(f"      {mov.cuenta.codigo:15s} | D: ${mov.debe:>12,.2f} | H: ${mov.haber:>12,.2f} | {mov.descripcion[:50]}")
            total_debe += mov.debe
            total_haber += mov.haber
            
            if mov.cuenta.codigo == '702-99':
                ajuste_702 = mov
        
        diferencia = total_debe - total_haber
        
        print(f"\n   TOTALES:")
        print(f"      Debe:  ${total_debe:>15,.2f}")
        print(f"      Haber: ${total_haber:>15,.2f}")
        print(f"      Diff:  ${diferencia:>15,.2f}")
        
        if ajuste_702:
            monto_ajuste = ajuste_702.haber if ajuste_702.haber > 0 else -ajuste_702.debe
            print(f"\n   ⚠️  AJUSTE 702-99: ${monto_ajuste:,.2f}")
            print(f"      La póliza necesitó un ajuste de ${abs(monto_ajuste):,.2f}")
        
        # Análisis de lo que DEBERÍA ser
        print(f"\n🔍 ANÁLISIS:")
        
        if factura.naturaleza == 'I':  # Ingreso
            print(f"   Tipo: INGRESO (empresa emite)")
            esperado_debe = factura.total
            esperado_haber = factura.subtotal + factura.total_impuestos_trasladados - factura.descuento
            
            print(f"\n   DEBE (Cliente):")
            print(f"      Esperado: ${esperado_debe:,.2f}")
            print(f"      Real:     ${total_debe:,.2f}")
            
            print(f"\n   HABER (Ventas + IVA - Desc):")
            print(f"      Subtotal:     ${factura.subtotal:,.2f}")
            print(f"      + IVA:        ${factura.total_impuestos_trasladados:,.2f}")
            print(f"      - Descuento:  ${factura.descuento:,.2f}")
            print(f"      = Esperado:   ${esperado_haber:,.2f}")
            print(f"      Real:         ${total_haber:,.2f}")
            
        else:  # Egreso
            print(f"   Tipo: EGRESO (empresa recibe)")
            esperado_debe = factura.subtotal + factura.total_impuestos_trasladados - factura.total_impuestos_retenidos - factura.descuento
            esperado_haber = factura.total
            
            print(f"\n   DEBE (Gasto + IVA - Ret - Desc):")
            print(f"      Subtotal:        ${factura.subtotal:,.2f}")
            print(f"      + IVA Trasl:     ${factura.total_impuestos_trasladados:,.2f}")
            print(f"      - IVA Ret:       ${factura.total_impuestos_retenidos:,.2f}")
            print(f"      - Descuento:     ${factura.descuento:,.2f}")
            print(f"      = Esperado:      ${esperado_debe:,.2f}")
            print(f"      Real:            ${total_debe:,.2f}")
            
            print(f"\n   HABER (Proveedor):")
            print(f"      Esperado: ${esperado_haber:,.2f}")
            print(f"      Real:     ${total_haber:,.2f}")
        
        error_debe = total_debe - esperado_debe
        error_haber = total_haber - esperado_haber
        
        if abs(error_debe) > 0.01 or abs(error_haber) > 0.01:
            print(f"\n❌ ERROR EN CONTABILIZACIÓN:")
            print(f"   Error en Debe:  ${error_debe:,.2f}")
            print(f"   Error en Haber: ${error_haber:,.2f}")
        else:
            print(f"\n✅ Contabilización correcta (ajuste solo por centavos)")
        
    except Poliza.DoesNotExist:
        print(f"\n❌ No hay póliza para esta factura")
        print(f"   Estado: {factura.estado_contable}")
        
except Factura.DoesNotExist:
    print(f"\n❌ Factura con UUID {uuid_str} no encontrada")

print("\n" + "=" * 80)
