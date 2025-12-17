"""
Corregir factura c4523692-fa69-5226-8a9d-552656e41707
Agregar $156.00 a total_impuestos_retenidos
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from decimal import Decimal

uuid = 'c4523692-fa69-5226-8a9d-552656e41707'

f = Factura.objects.get(uuid=uuid)

print(f"Factura: {uuid}")
print(f"Emisor: {f.emisor_nombre}")
print(f"Total: ${f.total:,.2f}")
print(f"\nRetenciones actuales: ${f.total_impuestos_retenidos:,.2f}")

# Agregar $156.00
ajuste = Decimal('156.00')
f.total_impuestos_retenidos += ajuste

print(f"Retenciones nuevas: ${f.total_impuestos_retenidos:,.2f}")

f.save()

print(f"\n✅ Factura corregida. Ahora intenta contabilizarla desde la bandeja.")
