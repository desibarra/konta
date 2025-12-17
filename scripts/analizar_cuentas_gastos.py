"""
Verificar qué cuentas de gastos existen y cuántos movimientos tienen
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable, MovimientoPoliza
from django.db.models import Count, Sum

empresa = Empresa.objects.first()

print("=" * 80)
print("ANÁLISIS DE CUENTAS DE GASTOS")
print("=" * 80)

# Buscar todas las cuentas de tipo GASTO
cuentas_gasto = CuentaContable.objects.filter(
    empresa=empresa,
    tipo='GASTO'
).order_by('codigo')

print(f"\nCuentas de GASTO encontradas: {cuentas_gasto.count()}\n")

for cuenta in cuentas_gasto:
    # Contar movimientos
    num_movs = MovimientoPoliza.objects.filter(cuenta=cuenta).count()
    
    if num_movs > 0:
        # Calcular total
        total_debe = MovimientoPoliza.objects.filter(cuenta=cuenta).aggregate(
            total=Sum('debe')
        )['total'] or 0
        
        print(f"{cuenta.codigo:15s} - {cuenta.nombre[:50]:50s} - {num_movs:5d} movs - ${total_debe:>15,.2f}")

print(f"\n{'='*80}")
