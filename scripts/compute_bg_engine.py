import os, sys
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from core.services.contabilidad_engine import ContabilidadEngine
from core.models import Empresa
from datetime import date

empresa = Empresa.objects.first()
res = ContabilidadEngine.obtener_balance_general(empresa, date(2025,12,31))
print('Total Activo:', f"${res['total_activo']:,.2f}")
print('Total Pasivo:', f"${res['total_pasivo']:,.2f}")
print('Total Capital (con utilidad):', f"${res['total_capital']:,.2f}")
print('Utilidad ejercicio:', f"${res['utilidad_ejercicio']:,.2f}")
print('Diferencia:', f"${res['diferencia']:,.2f}")
print('Cuadra?', res['cuadra'])
