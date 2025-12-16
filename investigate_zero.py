import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import MovimientoPoliza

print("INVESTIGACIÓN: ¿POR QUÉ GASTOS = $0?")
print("=" * 70)

# Ver movimientos en cuenta 601-01
movs_601 = MovimientoPoliza.objects.filter(cuenta__codigo='601-01')

print(f"\nTotal movimientos en 601-01: {movs_601.count()}")

# Ver primeros 5 movimientos
print("\nPrimeros 5 movimientos:")
for mov in movs_601[:5]:
    print(f"   Póliza #{mov.poliza.id}")
    print(f"      DEBE:  ${mov.debe:,.2f}")
    print(f"      HABER: ${mov.haber:,.2f}")
    print(f"      Descripción: {mov.descripcion}")
    print()

# Sumar totales
from django.db.models import Sum
totales = movs_601.aggregate(Sum('debe'), Sum('haber'))
print(f"Total DEBE en 601-01:  ${totales['debe__sum'] or 0:,.2f}")
print(f"Total HABER en 601-01: ${totales['haber__sum'] or 0:,.2f}")

print("\n" + "=" * 70)
