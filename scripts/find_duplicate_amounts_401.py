import os
import sys
from collections import defaultdict
from decimal import Decimal

BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from core.models import CuentaContable, MovimientoPoliza, Poliza
from django.db.models import Count
from datetime import date

FECHA_INI = date(2025,1,1)
FECHA_FIN = date(2025,12,31)
TARGET_CODIGO = '401-01'

cuenta = CuentaContable.objects.filter(codigo__startswith=TARGET_CODIGO).first()
if not cuenta:
    print('Cuenta no encontrada')
    sys.exit(1)

movs = MovimientoPoliza.objects.filter(
    cuenta=cuenta,
    poliza__fecha__date__gte=FECHA_INI,
    poliza__fecha__date__lte=FECHA_FIN
).select_related('poliza','poliza__factura')

# Agrupar por (haber, fecha)
groups = defaultdict(list)
for m in movs:
    key = (m.haber, m.poliza.fecha.date())
    groups[key].append(m)

# Filtrar grupos con >1 entradas
dup_groups = {k:v for k,v in groups.items() if len(v)>1}

if not dup_groups:
    print('No se encontraron grupos duplicados por (importe, fecha).')
else:
    print(f'Encontrados {len(dup_groups)} grupos duplicados (importe, fecha):\n')
    for (importe, fecha), items in sorted(dup_groups.items(), key=lambda x: (-len(x[1]), -float(x[0][0] or 0))):
        print(f'Importe: {importe} | Fecha: {fecha} | Count: {len(items)}')
        for m in items:
            pol = m.poliza
            fact_uuid = getattr(getattr(pol, 'factura', None), 'uuid', None)
            print(f"  MovID:{m.id} Poliza:{pol.id} FechaPoliza:{pol.fecha.date()} Factura:{fact_uuid} Debe:{m.debe} Haber:{m.haber}")
        print('')

# Además listar importes que aparecen >1 (independiente de fecha)
from django.db.models import Sum
val_counts = movs.values('haber').annotate(cnt=Count('id')).filter(cnt__gt=1).order_by('-cnt')
if val_counts:
    print('\nImportes repetidos (sin considerar fecha):')
    for v in val_counts:
        print(f"  Importe: {v['haber']} -> Count: {v['cnt']}")

print('\nFin del reporte.')
