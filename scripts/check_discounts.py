from core.models import Factura, MovimientoPoliza, CuentaContable
from django.db.models import Sum
import datetime
start = datetime.date(2025,1,1)
end = datetime.date(2025,12,15)

total_fact = Factura.objects.filter(fecha__date__gte=start, fecha__date__lte=end, descuento__gt=0).aggregate(s=Sum('descuento'))['s'] or 0
mov402 = MovimientoPoliza.objects.filter(cuenta__codigo__startswith='402-01', poliza__fecha__date__gte=start, poliza__fecha__date__lte=end).aggregate(debe=Sum('debe'), haber=Sum('haber'))
mov502 = MovimientoPoliza.objects.filter(cuenta__codigo__startswith='502-01', poliza__fecha__date__gte=start, poliza__fecha__date__lte=end).aggregate(debe=Sum('debe'), haber=Sum('haber'))
posted_total = (mov402['debe'] or 0) + (mov502['haber'] or 0)

print('Total factura descuentos:', float(total_fact))
print('Posted 402.debe:', float(mov402['debe'] or 0))
print('Posted 502.haber:', float(mov502['haber'] or 0))
print('Posted total (402.debe + 502.haber):', float(posted_total))
print('Discrepancy after fix:', float(total_fact-posted_total))
print('Cuenta 402 exists:', CuentaContable.objects.filter(codigo__startswith='402-01').exists())
print('Cuenta 502 exists:', CuentaContable.objects.filter(codigo__startswith='502-01').exists())
