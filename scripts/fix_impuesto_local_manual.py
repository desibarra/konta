"""
Solución: Actualizar el campo total_impuestos_retenidos para incluir impuesto local

Para la factura 1e87b201-c77d-4223-a958-57e2817f0fc7:
- IVA Retenido: $3,300.72
- ISR Retenido: $3,094.62
- Impuesto Estatal: $773.65
- TOTAL RETENCIONES: $7,169.01

Actualmente el campo tiene: $6,395.34 (IVA + ISR)
Debe tener: $7,169.01 (IVA + ISR + Estatal)
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from decimal import Decimal

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'

f = Factura.objects.get(uuid=uuid)

print(f"Factura: {uuid}")
print(f"Total impuestos retenidos ACTUAL: ${f.total_impuestos_retenidos:,.2f}")

# Calcular el total correcto
iva_retenido = Decimal('3300.72')
isr_retenido = Decimal('3094.62')
impuesto_estatal = Decimal('773.65')
total_correcto = iva_retenido + isr_retenido + impuesto_estatal

print(f"\nDESGLOSE:")
print(f"  IVA Retenido:      ${iva_retenido:>10,.2f}")
print(f"  ISR Retenido:      ${isr_retenido:>10,.2f}")
print(f"  Impuesto Estatal:  ${impuesto_estatal:>10,.2f}")
print(f"  TOTAL:             ${total_correcto:>10,.2f}")

print(f"\n¿Actualizar el campo total_impuestos_retenidos a ${total_correcto:,.2f}? (s/n): ", end='')
respuesta = input().strip().lower()

if respuesta == 's':
    f.total_impuestos_retenidos = total_correcto
    f.save()
    print(f"\n✅ Campo actualizado exitosamente")
    print(f"\nAhora intenta contabilizar la factura desde la bandeja.")
    print(f"La póliza debería cuadrar correctamente.")
else:
    print(f"\n❌ Operación cancelada")
