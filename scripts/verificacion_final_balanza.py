"""
Verificación final de la Balanza de Comprobación
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable, MovimientoPoliza
from django.db.models import Sum
from decimal import Decimal

empresa = Empresa.objects.first()

print("=" * 80)
print("VERIFICACIÓN FINAL - BALANZA DE COMPROBACIÓN")
print("=" * 80)

# Calcular totales
total_debe = MovimientoPoliza.objects.filter(
    poliza__factura__empresa=empresa
).aggregate(total=Sum('debe'))['total'] or Decimal('0')

total_haber = MovimientoPoliza.objects.filter(
    poliza__factura__empresa=empresa
).aggregate(total=Sum('haber'))['total'] or Decimal('0')

print(f"\n📊 TOTALES GENERALES:")
print(f"   Total DEBE:  ${total_debe:>20,.2f}")
print(f"   Total HABER: ${total_haber:>20,.2f}")
print(f"   Diferencia:  ${abs(total_debe - total_haber):>20,.2f}")

if abs(total_debe - total_haber) < 1:
    print(f"\n   ✅ BALANZA CUADRADA (diferencia < $1.00)")
else:
    print(f"\n   ⚠️  Diferencia: ${abs(total_debe - total_haber):,.2f}")

# Verificar cuenta 702-99
cuenta_702 = CuentaContable.objects.filter(
    empresa=empresa,
    codigo='702-99'
).first()

if cuenta_702:
    saldo_702 = MovimientoPoliza.objects.filter(
        cuenta=cuenta_702
    ).aggregate(
        debe=Sum('debe'),
        haber=Sum('haber')
    )
    
    debe_702 = saldo_702['debe'] or Decimal('0')
    haber_702 = saldo_702['haber'] or Decimal('0')
    saldo_final = debe_702 - haber_702
    
    print(f"\n💰 CUENTA 702-99 (Ajuste por Redondeo):")
    print(f"   Debe:  ${debe_702:>15,.2f}")
    print(f"   Haber: ${haber_702:>15,.2f}")
    print(f"   Saldo: ${saldo_final:>15,.2f}")
    
    if abs(saldo_final) < 100:
        print(f"\n   ✅ Saldo de ajustes CORRECTO (< $100)")
    else:
        print(f"\n   ⚠️  Saldo de ajustes ALTO: ${abs(saldo_final):,.2f}")
else:
    print(f"\n✅ Cuenta 702-99 no existe")

print(f"\n{'='*80}")
