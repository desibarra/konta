"""
Investigar por qué la factura 1e87b201-c77d-4223-a958-57e2817f0fc7 no cuadra

Diferencia: $773.65
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from decimal import Decimal

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'

try:
    factura = Factura.objects.get(uuid=uuid)
except Factura.DoesNotExist:
    print(f"❌ Factura {uuid} no encontrada")
    exit()

print("=" * 80)
print(f"ANÁLISIS DE FACTURA {uuid}")
print("=" * 80)

print(f"\n📋 INFORMACIÓN BÁSICA:")
print(f"   Folio: {getattr(factura, 'folio', 'N/A')}")
print(f"   Fecha: {factura.fecha}")
print(f"   Emisor: {factura.emisor_nombre}")
print(f"   Receptor: {factura.receptor_nombre}")
print(f"   Naturaleza: {factura.naturaleza}")
print(f"   UsoCFDI: {factura.uso_cfdi}")

print(f"\n💰 MONTOS:")
print(f"   Subtotal:              ${factura.subtotal:>15,.2f}")
print(f"   IVA Trasladado:        ${factura.total_impuestos_trasladados:>15,.2f}")
print(f"   IVA Retenido:          ${factura.total_impuestos_retenidos:>15,.2f}")
print(f"   Total:                 ${factura.total:>15,.2f}")

# Calcular lo que debería ser
if factura.naturaleza == 'E':  # Egreso
    # Debe: Subtotal + IVA Trasladado - IVA Retenido
    # Haber: Total
    
    total_debe_esperado = factura.subtotal + factura.total_impuestos_trasladados - factura.total_impuestos_retenidos
    total_haber_esperado = factura.total
    
    print(f"\n🧮 CÁLCULO ESPERADO (EGRESO):")
    print(f"   DEBE (Gasto + IVA):    ${total_debe_esperado:>15,.2f}")
    print(f"   HABER (Proveedor):     ${total_haber_esperado:>15,.2f}")
    print(f"   Diferencia:            ${abs(total_debe_esperado - total_haber_esperado):>15,.2f}")
    
    if abs(total_debe_esperado - total_haber_esperado) > Decimal('1.00'):
        print(f"\n⚠️  PROBLEMA DETECTADO:")
        print(f"   La diferencia de ${abs(total_debe_esperado - total_haber_esperado):.2f} excede el umbral de $1.00")
        print(f"\n   Posibles causas:")
        print(f"   1. Descuento no considerado")
        print(f"   2. Impuestos mal calculados")
        print(f"   3. Error en el XML")
        
        # Verificar si hay descuento
        descuento = getattr(factura, 'descuento', Decimal('0.00')) or Decimal('0.00')
        if descuento > 0:
            print(f"\n   💡 Descuento encontrado: ${descuento:.2f}")
            print(f"      Recalculando con descuento...")
            
            total_debe_con_desc = total_debe_esperado
            total_haber_con_desc = total_haber_esperado + descuento
            
            print(f"      DEBE:  ${total_debe_con_desc:,.2f}")
            print(f"      HABER: ${total_haber_con_desc:,.2f}")
            print(f"      Diferencia: ${abs(total_debe_con_desc - total_haber_con_desc):,.2f}")

print(f"\n{'='*80}")
