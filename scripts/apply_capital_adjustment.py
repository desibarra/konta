import os, sys
from decimal import Decimal
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from core.models import CuentaContable, Poliza, Factura, MovimientoPoliza, Empresa
from django.utils import timezone
import uuid

empresa = Empresa.objects.first()
if not empresa:
    print('No empresa')
    sys.exit(1)

# Difference to fix (recompute)
from django.db.models import Sum
from core.models import MovimientoPoliza
qs = MovimientoPoliza.objects.filter(poliza__fecha__year=2025, cuenta__empresa=empresa)
agg = qs.aggregate(debe=Sum('debe'), haber=Sum('haber'))
suma_debe = Decimal(agg.get('debe') or 0)
suma_haber = Decimal(agg.get('haber') or 0)
diff = (suma_debe - suma_haber).quantize(Decimal('0.01'))
print('Current diff:', diff)
if diff == Decimal('0.00'):
    print('No action required')
    sys.exit(0)

# adj_account should exist
adj_account = CuentaContable.objects.filter(empresa=empresa, codigo='999-99-999').first()
if not adj_account:
    print('Cuenta de ajuste adj_account missing')
    sys.exit(1)

# capital account
cap_account, created = CuentaContable.objects.get_or_create(
    empresa=empresa,
    codigo='999-99-997',
    defaults={'nombre':'Ajuste de Cuadre (Capital)','tipo':'CAPITAL','naturaleza':'A','nivel':1}
)
if created:
    print('Created capital account', cap_account.codigo)

# create a placeholder factura/poliza
placeholder_uuid = uuid.uuid4()
factura = Factura.objects.create(
    empresa=empresa,
    uuid=placeholder_uuid,
    fecha=timezone.datetime(2025,12,31,23,59,59,tzinfo=timezone.get_current_timezone()),
    emisor_rfc=empresa.rfc or 'XAXX010101000',
    emisor_nombre='Ajuste Capital',
    receptor_rfc=empresa.rfc or 'XAXX010101000',
    receptor_nombre='Ajuste Capital',
    subtotal=abs(diff),
    total=abs(diff),
    tipo_comprobante='T',
    naturaleza='C',
    estado_contable='CONTABILIZADA'
)
poliza = Poliza.objects.create(factura=factura, fecha=factura.fecha, descripcion='Ajuste de Capital por Cuadre')

# Create balanced movements: debit adj_account, credit cap_account
from decimal import Decimal
if diff > 0:
    MovimientoPoliza.objects.create(poliza=poliza, cuenta=adj_account, debe=diff, haber=Decimal('0.00'), descripcion='Ajuste cuadre (debito)')
    MovimientoPoliza.objects.create(poliza=poliza, cuenta=cap_account, debe=Decimal('0.00'), haber=diff, descripcion='Ajuste cuadre (capital)')
else:
    MovimientoPoliza.objects.create(poliza=poliza, cuenta=adj_account, debe=Decimal('0.00'), haber=abs(diff), descripcion='Ajuste cuadre (credito)')
    MovimientoPoliza.objects.create(poliza=poliza, cuenta=cap_account, debe=abs(diff), haber=Decimal('0.00'), descripcion='Ajuste cuadre (capital)')

print('Adjustment applied')
