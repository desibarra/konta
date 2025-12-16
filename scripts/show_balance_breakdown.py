import os
import sys
from decimal import Decimal

# Prep Django
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from core.models import MovimientoPoliza, CuentaContable
from django.db.models import Sum


def saldo_cuenta(cta):
    agg = MovimientoPoliza.objects.filter(cuenta=cta).aggregate(debe=Sum('debe'), haber=Sum('haber'))
    d = Decimal(agg.get('debe') or 0)
    h = Decimal(agg.get('haber') or 0)
    if (cta.naturaleza or 'D') == 'D':
        return d - h
    return h - d

# Build list
activos = []
pasivos = []
capital = []

for c in CuentaContable.objects.all():
    s = saldo_cuenta(c)
    if c.tipo == 'ACTIVO':
        activos.append((c.codigo, c.nombre, s))
    elif c.tipo == 'PASIVO':
        pasivos.append((c.codigo, c.nombre, s))
    elif c.tipo == 'CAPITAL':
        capital.append((c.codigo, c.nombre, s))

# Sort by absolute impact desc
activos.sort(key=lambda x: abs(x[2]), reverse=True)
pasivos.sort(key=lambda x: abs(x[2]), reverse=True)
capital.sort(key=lambda x: abs(x[2]), reverse=True)

print('\nTop 12 ACTIVOS por saldo:')
for kode, name, val in activos[:12]:
    print(f"{kode} | {name[:40]:40} | ${val:,.2f}")

print('\nTop 12 PASIVOS por saldo:')
for kode, name, val in pasivos[:12]:
    print(f"{kode} | {name[:40]:40} | ${val:,.2f}")

print('\nTop 12 CAPITAL por saldo:')
for kode, name, val in capital[:12]:
    print(f"{kode} | {name[:40]:40} | ${val:,.2f}")

# Summary totals
from decimal import Decimal

tot_act = sum(v for _,_,v in activos)
tot_pas = sum(v for _,_,v in pasivos)
tot_cap = sum(v for _,_,v in capital)

print('\nResumen:')
print(f"Total ACTIVO: ${tot_act:,.2f}")
print(f"Total PASIVO: ${tot_pas:,.2f}")
print(f"Total CAPITAL:${tot_cap:,.2f}")
print(f"Pasivo+Capital: ${ (tot_pas+tot_cap):,.2f}")
print(f"Diferencia: ${ (tot_act - (tot_pas+tot_cap)):,.2f}")
