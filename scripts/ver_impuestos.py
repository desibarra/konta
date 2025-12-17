"""
Script simple para ver los impuestos de la factura problemática
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from decimal import Decimal

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'
f = Factura.objects.get(uuid=uuid)

print(f"Subtotal: {f.subtotal}")
print(f"IVA Trasladado (campo): {f.total_impuestos_trasladados}")
print(f"IVA Retenido (campo): {f.total_impuestos_retenidos}")
print(f"Total: {f.total}")

# Calcular diferencia
debe = f.subtotal + f.total_impuestos_trasladados
haber = f.total + f.total_impuestos_retenidos

print(f"\nDEBE (Gasto + IVA): {debe}")
print(f"HABER (Proveedor + Retenciones): {haber}")
print(f"Diferencia: {abs(debe - haber)}")
