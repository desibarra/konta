"""
Probar si ahora se lee correctamente el impuesto estatal
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from core.services.accounting_service import AccountingService

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'
f = Factura.objects.get(uuid=uuid)

# Leer impuestos con el método actualizado
iva_tras, isr_ret, iva_ret, desc, imp_locales = AccountingService._accumulate_impuestos_from_xml(f)

print("IMPUESTOS LEÍDOS DEL XML:")
print(f"IVA Trasladado: ${iva_tras:,.2f}")
print(f"ISR Retenido: ${isr_ret:,.2f}")
print(f"IVA Retenido: ${iva_ret:,.2f}")
print(f"Impuestos Locales: ${imp_locales:,.2f}")
print(f"Descuento: ${desc:,.2f}")

print(f"\nTOTAL RETENCIONES: ${isr_ret + iva_ret + imp_locales:,.2f}")

# Verificar cuadre
debe = f.subtotal + iva_tras
haber = f.total + isr_ret + iva_ret + imp_locales

print(f"\nVERIFICACIÓN DE CUADRE:")
print(f"DEBE (Gasto + IVA): ${debe:,.2f}")
print(f"HABER (Proveedor + Retenciones): ${haber:,.2f}")
print(f"Diferencia: ${abs(debe - haber):,.2f}")

if abs(debe - haber) < 1:
    print(f"\n✅ ¡CUADRA! La diferencia es menor a $1.00")
else:
    print(f"\n❌ NO CUADRA: Diferencia de ${abs(debe - haber):,.2f}")
