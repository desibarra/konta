"""
Script simplificado para diagnosticar el problema de retenciones
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from core.services.accounting_service import AccountingService

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'

factura = Factura.objects.get(uuid=uuid)

print("=" * 80)
print(f"DIAGNÓSTICO DE RETENCIONES")
print("=" * 80)

print(f"\nFactura: {uuid}")
print(f"Emisor: {factura.emisor_nombre}")
print(f"Naturaleza: {factura.naturaleza}")

# Obtener impuestos del XML
total_iva_trasladado, total_isr_retenido, total_iva_retenido, total_descuento = AccountingService._accumulate_impuestos_from_xml(factura)

print(f"\n💰 IMPUESTOS DEL XML:")
print(f"   IVA Trasladado:  ${total_iva_trasladado:>12,.2f}")
print(f"   ISR Retenido:    ${total_isr_retenido:>12,.2f}")
print(f"   IVA Retenido:    ${total_iva_retenido:>12,.2f}")

print(f"\n📊 MONTOS DE LA FACTURA:")
print(f"   Subtotal:        ${factura.subtotal:>12,.2f}")
print(f"   Total:           ${factura.total:>12,.2f}")

# Calcular lo que debería ser
if factura.naturaleza == 'E':
    print(f"\n🧮 CÁLCULO PARA EGRESO:")
    
    # DEBE
    gasto = factura.subtotal
    iva_acreditable = total_iva_trasladado
    total_debe = gasto + iva_acreditable
    
    print(f"\n   DEBE:")
    print(f"      Gasto (601-XX):           ${gasto:>12,.2f}")
    print(f"      IVA Acreditable (119-01): ${iva_acreditable:>12,.2f}")
    print(f"      TOTAL DEBE:               ${total_debe:>12,.2f}")
    
    # HABER
    retenciones = total_isr_retenido + total_iva_retenido
    proveedor = factura.total
    total_haber = retenciones + proveedor
    
    print(f"\n   HABER:")
    print(f"      Retenciones (213-01):     ${retenciones:>12,.2f}")
    print(f"      Proveedor (201-XX):       ${proveedor:>12,.2f}")
    print(f"      TOTAL HABER:              ${total_haber:>12,.2f}")
    
    diferencia = total_debe - total_haber
    print(f"\n   DIFERENCIA:                 ${abs(diferencia):>12,.2f}")
    
    if abs(diferencia) > 1:
        print(f"\n   ⚠️  PROBLEMA: Diferencia de ${abs(diferencia):.2f} excede $1.00")
        print(f"\n   Verificando si cuadra con la fórmula correcta:")
        print(f"   Subtotal + IVA Trasladado = Total + Retenciones")
        print(f"   ${factura.subtotal:.2f} + ${total_iva_trasladado:.2f} = ${factura.total:.2f} + ${retenciones:.2f}")
        print(f"   ${factura.subtotal + total_iva_trasladado:.2f} = ${factura.total + retenciones:.2f}")
        
        if abs((factura.subtotal + total_iva_trasladado) - (factura.total + retenciones)) < 1:
            print(f"\n   ✅ La fórmula cuadra! El problema está en la lógica de contabilización.")
        else:
            print(f"\n   ❌ Hay un error en los datos del XML")

print(f"\n{'='*80}")
