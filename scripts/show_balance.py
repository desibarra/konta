import os
import sys
from decimal import Decimal

# Ensure project root is on sys.path so `konta` package imports correctly
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


tot_act = Decimal('0.00')
tot_pas = Decimal('0.00')
tot_cap = Decimal('0.00')

for c in CuentaContable.objects.all():
    s = saldo_cuenta(c)
    if c.tipo == 'ACTIVO':
        tot_act += s
    elif c.tipo == 'PASIVO':
        tot_pas += s
    elif c.tipo == 'CAPITAL':
        tot_cap += s

print('Total ACTIVO:    ', f"${tot_act:,.2f}")
print('Total PASIVO:    ', f"${tot_pas:,.2f}")
print('Total CAPITAL:   ', f"${tot_cap:,.2f}")
print('Pasivo + Capital:', f"${(tot_pas+tot_cap):,.2f}")
print('Diferencia ACTIVO - (PASIVO+CAPITAL):', f"${(tot_act - (tot_pas+tot_cap)):,.2f}")
