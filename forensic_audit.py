import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import MovimientoPoliza, Factura
from django.db.models import Sum, Count

print("=" * 70)
print("AUDITORÍA FORENSE - ¿DÓNDE ESTÁN LOS EGRESOS?")
print("=" * 70)

# 1. Total de movimientos
total_debe = MovimientoPoliza.objects.aggregate(Sum('debe'))['debe__sum'] or 0
total_haber = MovimientoPoliza.objects.aggregate(Sum('haber'))['haber__sum'] or 0

print(f"\n📊 TOTALES GENERALES:")
print(f"   Total DEBE:  ${total_debe:,.2f}")
print(f"   Total HABER: ${total_haber:,.2f}")
print(f"   Diferencia:  ${abs(total_debe - total_haber):,.2f}")

# 2. Facturas por tipo
facturas_stats = Factura.objects.values('naturaleza').annotate(
    count=Count('id'),
    total=Sum('total')
).order_by('naturaleza')

print(f"\n📋 FACTURAS POR TIPO:")
for stat in facturas_stats:
    nat = 'INGRESO' if stat['naturaleza'] == 'I' else 'EGRESO' if stat['naturaleza'] == 'E' else stat['naturaleza']
    print(f"   {nat}: {stat['count']} facturas = ${stat['total']:,.2f}")

# 3. ¿Dónde está el dinero? (Top 15 cuentas con DEBE)
print(f"\n💰 TOP 15 CUENTAS CON MOVIMIENTOS DEBE:")
movs_debe = MovimientoPoliza.objects.values(
    'cuenta__codigo', 
    'cuenta__nombre',
    'cuenta__tipo'
).annotate(
    total=Sum('debe')
).filter(total__gt=0).order_by('-total')[:15]

for m in movs_debe:
    print(f"   {m['cuenta__codigo']:10} {m['cuenta__nombre'][:40]:40} ${m['total']:>15,.2f} ({m['cuenta__tipo']})")

# 4. ¿Dónde está el dinero? (Top 15 cuentas con HABER)
print(f"\n💸 TOP 15 CUENTAS CON MOVIMIENTOS HABER:")
movs_haber = MovimientoPoliza.objects.values(
    'cuenta__codigo', 
    'cuenta__nombre',
    'cuenta__tipo'
).annotate(
    total=Sum('haber')
).filter(total__gt=0).order_by('-total')[:15]

for m in movs_haber:
    print(f"   {m['cuenta__codigo']:10} {m['cuenta__nombre'][:40]:40} ${m['total']:>15,.2f} ({m['cuenta__tipo']})")

# 5. Análisis por TIPO de cuenta
print(f"\n🔍 ANÁLISIS POR TIPO DE CUENTA:")
tipos_debe = MovimientoPoliza.objects.values('cuenta__tipo').annotate(
    total=Sum('debe')
).filter(total__gt=0).order_by('-total')

for t in tipos_debe:
    print(f"   DEBE en {t['cuenta__tipo']:15}: ${t['total']:>15,.2f}")

tipos_haber = MovimientoPoliza.objects.values('cuenta__tipo').annotate(
    total=Sum('haber')
).filter(total__gt=0).order_by('-total')

print()
for t in tipos_haber:
    print(f"   HABER en {t['cuenta__tipo']:15}: ${t['total']:>15,.2f}")

print("\n" + "=" * 70)
