from datetime import date
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
        for c in qs[:30]:
            print(c.codigo, c.nombre, float(c.movimientos_debe), float(c.movimientos_haber), float(c.saldo_inicial), float(c.saldo_final))
