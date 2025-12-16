import os
import django
from decimal import Decimal

# Setup Django
BASE = os.path.dirname(os.path.dirname(__file__))
import sys
sys.path.insert(0, BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import MovimientoPoliza, CuentaContable, Poliza, Factura
from django.db.models import Sum
from datetime import date

TARGET_CODIGO = '401-01'
FECHA_INI = date(2025,1,1)
FECHA_FIN = date(2025,12,31)
TOLERANCE = Decimal('5.00')

print(f"Audit Income Diff - Cuenta {TARGET_CODIGO} - {FECHA_INI} to {FECHA_FIN}")

# Find the account
cuentas = CuentaContable.objects.filter(codigo__startswith=TARGET_CODIGO)
if not cuentas.exists():
    print('No se encontró cuenta con código', TARGET_CODIGO)
    sys.exit(1)

cuenta = cuentas.first()
print('Usando cuenta:', cuenta.codigo, cuenta.nombre)

# Total Haber sum for the account in range
total_haber = MovimientoPoliza.objects.filter(
    cuenta=cuenta,
    poliza__fecha__date__gte=FECHA_INI,
    poliza__fecha__date__lte=FECHA_FIN
).aggregate(total=Sum('haber'))['total'] or Decimal('0')

print('Total Haber (401) periodo:', f"${total_haber:,.2f}")

# Group by póliza: sum haber per poliza for this account
from django.db.models import Count
poliza_sums = MovimientoPoliza.objects.filter(
    cuenta=cuenta,
    poliza__fecha__date__gte=FECHA_INI,
    poliza__fecha__date__lte=FECHA_FIN
).values('poliza').annotate(
    suma_haber=Sum('haber'),
    movimientos=Count('id')
).order_by('-suma_haber')

print('\nTop pólizas por monto (haber) en cuenta 401-01:')
for p in poliza_sums[:50]:
    pol = Poliza.objects.filter(id=p['poliza']).select_related('factura').first()
    uuid = pol.factura.uuid if pol and hasattr(pol, 'factura') else 'N/A'
    fecha = pol.fecha.date() if pol else 'N/A'
    print(f"Poliza {p['poliza']} | Fecha: {fecha} | Movs: {p['movimientos']} | Haber: ${p['suma_haber']:,.2f} | Factura: {uuid}")

# Buscar movimientos sospechosos: duplicados exactos in same fecha/amount
from collections import defaultdict
pairs = defaultdict(list)
movs = MovimientoPoliza.objects.filter(
    cuenta=cuenta,
    poliza__fecha__date__gte=FECHA_INI,
    poliza__fecha__date__lte=FECHA_FIN
).select_related('poliza','poliza__factura')

for m in movs:
    key = (m.debe, m.haber, m.poliza.fecha.date())
    pairs[key].append(m)

print('\nMovimientos duplicados exactos (mismo importe y fecha):')
found_dup = False
for k,v in pairs.items():
    if len(v) > 1:
        found_dup = True
        print(f"Fecha: {k[2]} Debe: {k[0]} Haber: {k[1]} -> Count: {len(v)}")
        for m in v[:10]:
            fact_uuid = m.poliza.factura.uuid if hasattr(m.poliza, 'factura') and m.poliza.factura else 'N/A'
            print(f"   MovID:{m.id} Poliza:{m.poliza.id} Factura:{fact_uuid}")

if not found_dup:
    print('  No se encontraron duplicados exactos.')

# Buscar movimientos individuales cercanos a la diferencia (~3355)
TARGET_DIFF = Decimal('3355.33')
print(f"\nMovimientos con importe cercano a {TARGET_DIFF}: (tolerance {TOLERANCE})")
near_matches = []
for m in movs:
    if abs(m.haber - TARGET_DIFF) <= TOLERANCE or abs(m.debe - TARGET_DIFF) <= TOLERANCE:
        near_matches.append(m)

if near_matches:
    for m in near_matches:
        print(f"MovID:{m.id} Poliza:{m.poliza.id} Fecha:{m.poliza.fecha.date()} Debe:{m.debe} Haber:{m.haber} Factura:{getattr(getattr(m.poliza,'factura',None),'uuid','N/A')}")
else:
    print('  No se encontraron movimientos cercanos al monto objetivo.')

print('\nFin auditoría rápida.')
