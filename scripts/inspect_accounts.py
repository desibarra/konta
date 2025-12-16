import os
import sys
from decimal import Decimal

proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from core.models import MovimientoPoliza, CuentaContable
from django.db.models import Sum

codes = ['2101', '105-01-001', '1201', '216-01', '213-01']

for code in codes:
    try:
        c = CuentaContable.objects.get(codigo=code)
    except CuentaContable.DoesNotExist:
        print(f"Cuenta {code} no existe")
        continue
    agg = MovimientoPoliza.objects.filter(cuenta=c).aggregate(debe=Sum('debe'), haber=Sum('haber'))
    d = Decimal(agg.get('debe') or 0)
    h = Decimal(agg.get('haber') or 0)
    if (c.naturaleza or 'D') == 'D':
        saldo = d - h
    else:
        saldo = h - d
    print(f"\nCuenta {c.codigo} - {c.nombre} -> Saldo: ${saldo:,.2f} (D:{d:,.2f} H:{h:,.2f})")
    print('Últimos 20 movimientos:')
    qs = MovimientoPoliza.objects.filter(cuenta=c).select_related('poliza').order_by('-poliza__fecha')[:20]
    for m in qs:
        fecha = m.poliza.fecha
        print(f"Poliza {m.poliza.id} | {fecha.date() if hasattr(fecha,'date') else fecha} | D:{m.debe:,.2f} H:{m.haber:,.2f} | {m.descripcion}")

print('\nHecho.')
