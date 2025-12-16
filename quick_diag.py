import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import MovimientoPoliza, CuentaContable
from django.db.models import Sum

print("DIAGNÓSTICO RÁPIDO")
print("=" * 60)

# Verificar si hay movimientos en cuentas de GASTO
gastos = MovimientoPoliza.objects.filter(cuenta__tipo='GASTO')
print(f"Movimientos en cuentas GASTO: {gastos.count()}")

if gastos.exists():
    total_gastos = gastos.aggregate(Sum('debe'))['debe__sum']
    print(f"Total gastos (DEBE): ${total_gastos:,.2f}")
else:
    print("❌ NO HAY MOVIMIENTOS EN CUENTAS DE GASTO")
    
# Verificar cuenta 601-01
cuenta_601 = CuentaContable.objects.filter(codigo='601-01').first()
if cuenta_601:
    print(f"\n✅ Cuenta 601-01 existe: {cuenta_601.nombre} (Tipo: {cuenta_601.tipo})")
    movs_601 = MovimientoPoliza.objects.filter(cuenta=cuenta_601).count()
    print(f"   Movimientos en 601-01: {movs_601}")
else:
    print("\n❌ Cuenta 601-01 NO EXISTE")

# Total de movimientos
total_movs = MovimientoPoliza.objects.count()
print(f"\nTotal movimientos en DB: {total_movs}")
