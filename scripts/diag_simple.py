"""
Diagnosticar factura 8a5e01d4
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from core.services.accounting_service import AccountingService
from decimal import Decimal

uuid = '8a5e01d4-bad6-4bd2-8fd1-790304d98069'

f = Factura.objects.get(uuid=uuid)

print("DIAGNOSTICO FACTURA", uuid)
print("Emisor:", f.emisor_nombre)
print("Naturaleza:", f.naturaleza)

print("\nMONTOS:")
print("Subtotal:", f.subtotal)
print("IVA Trasladado (campo):", f.total_impuestos_trasladados)
print("IVA Retenido (campo):", f.total_impuestos_retenidos)
print("Total:", f.total)

# Leer del XML
iva_tras, isr_ret, iva_ret, desc, imp_locales = AccountingService._accumulate_impuestos_from_xml(f)

print("\nIMPUESTOS DEL XML:")
print("IVA Trasladado:", iva_tras)
print("ISR Retenido:", isr_ret)
print("IVA Retenido:", iva_ret)
print("Impuestos Locales:", imp_locales)

total_ret = isr_ret + iva_ret + imp_locales
print("\nTotal Retenciones:", total_ret)

# Calcular cuadre
debe = f.subtotal + iva_tras
haber = f.total + total_ret

print("\nCALCULO:")
print("DEBE (Gasto + IVA):", debe)
print("HABER (Prov + Ret):", haber)
print("Diferencia:", abs(debe - haber))

if abs(debe - haber) > 1:
    print("\nPROBLEMA: Diferencia de", abs(debe - haber))
    if imp_locales == 0:
        print("POSIBLE CAUSA: Impuestos locales no leidos")
        print("Faltante:", abs(debe - haber))
        print("2.5% del subtotal:", f.subtotal * Decimal('0.025'))
