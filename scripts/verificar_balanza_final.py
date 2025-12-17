import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, MovimientoPoliza
from decimal import Decimal

print("VERIFICACION FINAL DE BALANZA")
print("=" * 80)

# Estado de facturas
total_facturas = Factura.objects.count()
contabilizadas = Factura.objects.filter(estado_contable='CONTABILIZADA').count()
pendientes = Factura.objects.filter(estado_contable='PENDIENTE').count()

print(f"FACTURAS:")
print(f"  Total: {total_facturas}")
print(f"  Contabilizadas: {contabilizadas} ({contabilizadas/total_facturas*100:.1f}%)")
print(f"  Pendientes: {pendientes} ({pendientes/total_facturas*100:.1f}%)")

# Balanza
total_debe = MovimientoPoliza.objects.aggregate(
    total=models.Sum('debe')
)['total'] or Decimal('0')

total_haber = MovimientoPoliza.objects.aggregate(
    total=models.Sum('haber')
)['total'] or Decimal('0')

diferencia = abs(total_debe - total_haber)

print(f"\nBALANZA DE COMPROBACION:")
print(f"  Total DEBE:  ${total_debe:>20,.2f}")
print(f"  Total HABER: ${total_haber:>20,.2f}")
print(f"  Diferencia:  ${diferencia:>20,.2f}")

if diferencia < Decimal('1.00'):
    print(f"\n  *** BALANZA CUADRADA (dif < $1.00) ***")
else:
    print(f"\n  ADVERTENCIA: Diferencia de ${diferencia:.2f}")

# Cuenta de ajustes
from core.models import CuentaContable
try:
    cuenta_702 = CuentaContable.objects.get(codigo='702-99')
    saldo_702 = MovimientoPoliza.objects.filter(cuenta=cuenta_702).aggregate(
        debe=models.Sum('debe'),
        haber=models.Sum('haber')
    )
    
    debe_702 = saldo_702['debe'] or Decimal('0')
    haber_702 = saldo_702['haber'] or Decimal('0')
    saldo_final_702 = debe_702 - haber_702
    
    print(f"\nCUENTA 702-99 (Ajuste por Redondeo):")
    print(f"  Debe:  ${debe_702:>15,.2f}")
    print(f"  Haber: ${haber_702:>15,.2f}")
    print(f"  Saldo: ${saldo_final_702:>15,.2f}")
    
    if abs(saldo_final_702) < Decimal('1.00'):
        print(f"  *** CORRECTO (saldo < $1.00) ***")
    else:
        print(f"  ADVERTENCIA: Saldo alto")
except:
    print(f"\nCuenta 702-99 no existe")

print("\n" + "=" * 80)
