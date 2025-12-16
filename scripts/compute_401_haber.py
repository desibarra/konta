import os, sys
BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','konta.settings')
import django
django.setup()
from core.models import MovimientoPoliza, CuentaContable
from django.db.models import Sum
from datetime import date

inicio=date(2025,1,1)
fin=date(2025,12,31)
cuenta=CuentaContable.objects.filter(codigo__startswith='401-01').first()
if not cuenta:
    print('NO_CUENTA')
else:
    total=MovimientoPoliza.objects.filter(cuenta=cuenta, poliza__fecha__date__gte=inicio, poliza__fecha__date__lte=fin).aggregate(t=Sum('haber'))['t'] or 0
    print('MOV_HABER_401:', float(total))
