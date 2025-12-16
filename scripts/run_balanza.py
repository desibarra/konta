import os
import sys
from datetime import date

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from core.services.reportes_engine import ReportesEngine
from core.models import Empresa

empresa = Empresa.objects.first()
if not empresa:
    print('NO_EMPRESA')
else:
    fecha_ini = date(2025,1,1)
    fecha_fin = date(2025,12,31)
    qs = ReportesEngine.obtener_balanza_comprobacion(empresa, fecha_ini, fecha_fin)
    if qs is None:
        print('QS_NONE')
    else:
        print('COUNT', qs.count())
        for c in qs[:50]:
            print(c.codigo, c.nombre, float(c.movimientos_debe), float(c.movimientos_haber), float(c.saldo_inicial), float(c.saldo_final))
