"""
Buscar la cuenta que tiene los gastos principales
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable, MovimientoPoliza
from django.db.models import Sum, Q

empresa = Empresa.objects.first()

print("=" * 80)
print("BÚSQUEDA DE CUENTA PRINCIPAL DE GASTOS")
print("=" * 80)

# Buscar cuentas que empiecen con 601 o 602 o 603
cuentas_60x = CuentaContable.objects.filter(
    empresa=empresa,
    codigo__startswith='60'
).order_by('codigo')

print(f"\nCuentas 60X encontradas:\n")

for cuenta in cuentas_60x:
    num_movs = MovimientoPoliza.objects.filter(cuenta=cuenta).count()
    
    if num_movs > 0:
        total = MovimientoPoliza.objects.filter(cuenta=cuenta).aggregate(
            total=Sum('debe')
        )['total'] or 0
        
        print(f"  {cuenta.codigo:10s} - {cuenta.nombre[:60]:60s}")
        print(f"             Movimientos: {num_movs:,} - Total: ${total:,.2f}\n")

# Buscar la cuenta con más movimientos
cuenta_principal = None
max_movs = 0

for cuenta in cuentas_60x:
    num_movs = MovimientoPoliza.objects.filter(cuenta=cuenta).count()
    if num_movs > max_movs:
        max_movs = num_movs
        cuenta_principal = cuenta

if cuenta_principal:
    print(f"\n{'='*80}")
    print(f"CUENTA PRINCIPAL IDENTIFICADA:")
    print(f"  Código: {cuenta_principal.codigo}")
    print(f"  Nombre: {cuenta_principal.nombre}")
    print(f"  Movimientos: {max_movs:,}")
    print(f"{'='*80}")
else:
    print("\n⚠️  No se encontró cuenta principal de gastos")
