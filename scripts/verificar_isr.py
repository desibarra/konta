"""
Verificar ISR retenido en el XML
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from core.services.accounting_service import AccountingService

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'
f = Factura.objects.get(uuid=uuid)

# Leer impuestos directamente del XML
iva_tras, isr_ret, iva_ret, desc = AccountingService._accumulate_impuestos_from_xml(f)

print("IMPUESTOS DEL XML (método _accumulate_impuestos_from_xml):")
print(f"IVA Trasladado: {iva_tras}")
print(f"ISR Retenido: {isr_ret}")
print(f"IVA Retenido: {iva_ret}")
print(f"Descuento: {desc}")

print("\nIMPUESTOS EN CAMPOS DE LA FACTURA:")
print(f"total_impuestos_trasladados: {f.total_impuestos_trasladados}")
print(f"total_impuestos_retenidos: {f.total_impuestos_retenidos}")

print("\nVERIFICACIÓN:")
total_retenciones_xml = isr_ret + iva_ret
print(f"Total retenciones del XML: {total_retenciones_xml}")
print(f"Campo total_impuestos_retenidos: {f.total_impuestos_retenidos}")

if total_retenciones_xml != f.total_impuestos_retenidos:
    print(f"\n⚠️  PROBLEMA: Los campos no coinciden con el XML!")
    print(f"Diferencia: {abs(total_retenciones_xml - f.total_impuestos_retenidos)}")
