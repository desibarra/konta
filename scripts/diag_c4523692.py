"""
Diagnosticar factura c4523692-fa69-5226-8a9d-552656e41707
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from core.services.accounting_service import AccountingService
from decimal import Decimal

uuid = 'c4523692-fa69-5226-8a9d-552656e41707'

f = Factura.objects.get(uuid=uuid)

print("DIAGNOSTICO FACTURA", uuid)
print("=" * 80)
print("Emisor:", f.emisor_nombre)
print("Naturaleza:", f.naturaleza)
print("Fecha:", f.fecha)

print("\nMONTOS DE LA FACTURA:")
print(f"  Subtotal:           ${f.subtotal:>12,.2f}")
print(f"  IVA Trasladado:     ${f.total_impuestos_trasladados:>12,.2f}")
print(f"  IVA Retenido:       ${f.total_impuestos_retenidos:>12,.2f}")
print(f"  Total:              ${f.total:>12,.2f}")

# Leer del XML
iva_tras, isr_ret, iva_ret, desc, imp_locales = AccountingService._accumulate_impuestos_from_xml(f)

print("\nIMPUESTOS DEL XML:")
print(f"  IVA Trasladado:     ${iva_tras:>12,.2f}")
print(f"  ISR Retenido:       ${isr_ret:>12,.2f}")
print(f"  IVA Retenido:       ${iva_ret:>12,.2f}")
print(f"  Impuestos Locales:  ${imp_locales:>12,.2f}")

total_ret = isr_ret + iva_ret + imp_locales
print(f"  Total Retenciones:  ${total_ret:>12,.2f}")

# Calcular cuadre para EGRESO
print("\nCALCULO DE CUADRE (EGRESO):")
debe = f.subtotal + iva_tras
haber = f.total + total_ret

print(f"  DEBE (Gasto + IVA): ${debe:>12,.2f}")
print(f"  HABER (Prov + Ret): ${haber:>12,.2f}")
print(f"  Diferencia:         ${abs(debe - haber):>12,.2f}")

if abs(debe - haber) > 1:
    print(f"\n⚠️  PROBLEMA: Diferencia de ${abs(debe - haber):.2f}")
    
    if imp_locales == 0:
        faltante = abs(debe - haber)
        porcentaje = (faltante / f.subtotal) * 100
        print(f"\nPOSIBLE CAUSA: Impuestos locales no leidos")
        print(f"  Faltante:           ${faltante:>12,.2f}")
        print(f"  Porcentaje:         {porcentaje:>12.2f}%")
        print(f"  2.5% del subtotal:  ${(f.subtotal * Decimal('0.025')):>12,.2f}")
        
        if 1.5 <= porcentaje <= 3.5:
            print(f"\n✅ SOLUCION: Agregar ${faltante:.2f} a total_impuestos_retenidos")
            print(f"   Nuevo total retenciones: ${f.total_impuestos_retenidos + faltante:.2f}")
else:
    print(f"\n✅ CUADRA CORRECTAMENTE")

print("=" * 80)
