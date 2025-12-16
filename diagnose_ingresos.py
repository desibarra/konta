import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from django.db.models import Count, Sum
from decimal import Decimal

print("DIAGNÓSTICO: Facturas de Ingreso 2025")
print("=" * 70)

# Obtener facturas de Ingreso
facturas_ingreso = Factura.objects.filter(
    fecha__year=2025,
    naturaleza='I'
).order_by('fecha')

total = facturas_ingreso.count()

print(f"\nTotal facturas Ingreso: {total}")
print(f"\nPrimeras 10 facturas:")
print(f"{'UUID':<40} {'Fecha':<12} {'Subtotal':>15} {'Tipo':>5}")
print("-" * 75)

for idx, f in enumerate(facturas_ingreso[:10], 1):
    print(f"{str(f.uuid)[:36]:<40} {f.fecha.strftime('%Y-%m-%d'):<12} ${f.subtotal:>13,.2f} {f.tipo_comprobante:>5}")

print("\n" + "=" * 70)
suma_total = facturas_ingreso.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
print(f"SUMA TOTAL SUBTOTALES: ${suma_total:,.2f}")
print(f"ESPERADO (Excel):      $414,886.64")
diferencia = suma_total - Decimal('414886.64')
print(f"DIFERENCIA:            ${diferencia:,.2f}")

# Ver si hay facturas que no deberían estar
print("\n\nFacturas por tipo_comprobante:")
tipos = facturas_ingreso.values('tipo_comprobante').annotate(
    count=Count('id'),
    suma=Sum('subtotal')
)

for t in tipos:
    print(f"  {t['tipo_comprobante']}: {t['count']} facturas, Subtotal: ${t['suma']:,.2f}")
