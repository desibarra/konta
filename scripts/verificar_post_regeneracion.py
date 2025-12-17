"""
Verificación rápida del balance después de regenerar pólizas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa, CuentaContable, MovimientoPoliza
from core.services.contabilidad_engine import ContabilidadEngine
from django.db.models import Sum
from decimal import Decimal

empresa = Empresa.objects.first()
fecha_corte = date.today()

print("=" * 80)
print("VERIFICACIÓN POST-REGENERACIÓN")
print("=" * 80)
print(f"Empresa: {empresa.nombre}")
print(f"Fecha: {fecha_corte}\n")

# 1. Verificar movimientos totales
total_debe = MovimientoPoliza.objects.filter(
    poliza__factura__empresa=empresa
).aggregate(Sum('debe'))['debe__sum'] or Decimal('0')

total_haber = MovimientoPoliza.objects.filter(
    poliza__factura__empresa=empresa
).aggregate(Sum('haber'))['haber__sum'] or Decimal('0')

print("📊 TOTALES DE MOVIMIENTOS:")
print(f"   Debe:  ${total_debe:>20,.2f}")
print(f"   Haber: ${total_haber:>20,.2f}")
print(f"   Diff:  ${(total_debe - total_haber):>20,.2f}")

if abs(total_debe - total_haber) < 0.01:
    print("   ✅ Movimientos cuadran perfectamente\n")
else:
    print("   ❌ ERROR: Movimientos no cuadran\n")

# 2. Verificar cuenta 702-99
try:
    cuenta_702 = CuentaContable.objects.get(empresa=empresa, codigo='702-99')
    movs_702 = MovimientoPoliza.objects.filter(cuenta=cuenta_702)
    debe_702 = movs_702.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
    haber_702 = movs_702.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
    saldo_702 = haber_702 - debe_702
    
    print("🔍 CUENTA 702-99 (Ajustes):")
    print(f"   Debe:  ${debe_702:>20,.2f}")
    print(f"   Haber: ${haber_702:>20,.2f}")
    print(f"   Saldo: ${saldo_702:>20,.2f}")
    print(f"   Movimientos: {movs_702.count()}\n")
except CuentaContable.DoesNotExist:
    print("✅ Cuenta 702-99 no existe (no se necesitaron ajustes)\n")

# 3. Verificar Balance General
print("🧮 BALANCE GENERAL:")
balance = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)

print(f"   Activo:              ${balance['total_activo']:>20,.2f}")
print(f"   Pasivo:              ${balance['total_pasivo']:>20,.2f}")
print(f"   Capital:             ${balance['total_capital']:>20,.2f}")
print(f"   Utilidad Ejercicio:  ${balance['utilidad_ejercicio']:>20,.2f}")
print(f"   Diferencia:          ${balance['diferencia']:>20,.2f}")

print("\n" + "=" * 80)
if balance['cuadra']:
    print("✅ ¡BALANCE CUADRADO! El sistema está funcionando correctamente")
else:
    print(f"❌ Balance descuadrado por ${abs(balance['diferencia']):,.2f}")
print("=" * 80)
