import os
import sys
from decimal import Decimal

BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from core.models import CuentaContable, MovimientoPoliza
from datetime import date

FECHA_INI = date(2025,1,1)
FECHA_FIN = date(2025,12,31)
TARGET_CODIGO = '401-01'
TARGET_AMOUNTS = [Decimal('2883.44'), Decimal('254.14'), Decimal('217.75')]

cuenta = CuentaContable.objects.filter(codigo__startswith=TARGET_CODIGO).first()
if not cuenta:
    print('Cuenta no encontrada')
    sys.exit(1)

movs = MovimientoPoliza.objects.filter(
    cuenta=cuenta,
    poliza__fecha__date__gte=FECHA_INI,
    poliza__fecha__date__lte=FECHA_FIN,
    haber__in=TARGET_AMOUNTS
).select_related('poliza','poliza__factura').order_by('poliza__fecha', 'haber')

print('Movimientos sospechosos (haber in', TARGET_AMOUNTS, '):\n')
for m in movs:
    pol = m.poliza
    fact_uuid = getattr(getattr(pol, 'factura', None), 'uuid', None)
    print(f"MovID:{m.id} | Poliza:{pol.id} | Fecha:{pol.fecha.date()} | Factura:{fact_uuid} | Debe:{m.debe} | Haber:{m.haber}")

print('\nTotal registros listados:', movs.count())
