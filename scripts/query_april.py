from core.models import MovimientoPoliza, CuentaContable
from django.db.models import Sum
import datetime
inicio = datetime.date(2025,4,1)
fin = datetime.date(2025,4,30)

def saldo(codigo):
    qs = MovimientoPoliza.objects.filter(cuenta__codigo__startswith=codigo, poliza__fecha__date__gte=inicio, poliza__fecha__date__lte=fin)
    s = qs.aggregate(s=Sum('debe'))['s'] or 0
    h = qs.aggregate(h=Sum('haber'))['h'] or 0
    return float(s) - float(h)

print('Saldo Abril 105-01 Clientes:', saldo('105-01'))
print('Saldo Abril 401-01 Ventas (subtotal):', saldo('401-01'))
print('Cuenta 402-01 existe:', CuentaContable.objects.filter(codigo__startswith='402-01').exists())
print('Cuenta 502-01 existe:', CuentaContable.objects.filter(codigo__startswith='502-01').exists())
