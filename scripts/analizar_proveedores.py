"""
Analizar cuentas de proveedores para encontrar diferencia
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa, CuentaContable, MovimientoPoliza
from django.db.models import Sum, Q
from decimal import Decimal

# Buscar TRASLADOS DE VANGUARDIA
empresa = Empresa.objects.filter(nombre__icontains='TRASLADOS').first()

if not empresa:
    print("❌ No se encontró empresa TRASLADOS")
    exit()

print("=" * 80)
print(f"ANÁLISIS DE PROVEEDORES: {empresa.nombre}")
print("=" * 80)

fecha_corte = date.today()

# Buscar cuentas de proveedores (usualmente 201-xx o 2xx-xx)
cuentas_proveedores = CuentaContable.objects.filter(
    empresa=empresa
).filter(
    Q(codigo__startswith='201') | 
    Q(codigo__startswith='210') |
    Q(nombre__icontains='proveedor') |
    Q(nombre__icontains='por pagar')
).order_by('codigo')

print(f"\n📋 CUENTAS DE PROVEEDORES ENCONTRADAS: {cuentas_proveedores.count()}\n")

total_proveedores = Decimal('0')
cuentas_con_saldo = []

for cuenta in cuentas_proveedores:
    movs = MovimientoPoliza.objects.filter(
        cuenta=cuenta,
        poliza__fecha__lte=fecha_corte
    )
    
    debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
    haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
    
    # Proveedores son acreedores: Haber - Debe
    saldo = haber - debe
    
    if abs(saldo) > 0.01:
        total_proveedores += saldo
        cuentas_con_saldo.append({
            'codigo': cuenta.codigo,
            'nombre': cuenta.nombre,
            'saldo': saldo,
            'debe': debe,
            'haber': haber
        })

# Ordenar por saldo absoluto
cuentas_con_saldo.sort(key=lambda x: abs(x['saldo']), reverse=True)

print("CUENTAS CON SALDO (Top 20):")
for i, c in enumerate(cuentas_con_saldo[:20], 1):
    print(f"{i:2d}. {c['codigo']:15s} ${c['saldo']:>15,.2f} - {c['nombre'][:50]}")

print(f"\n{'='*80}")
print(f"TOTAL PROVEEDORES: ${total_proveedores:,.2f}")
print(f"{'='*80}")

# Buscar si hay alguna cuenta cercana a $289K
print(f"\n🔍 BUSCANDO CUENTA CERCANA A $289,779.30...")
for c in cuentas_con_saldo:
    if abs(abs(c['saldo']) - Decimal('289779.30')) < 100:
        print(f"\n⚠️  POSIBLE CAUSA ENCONTRADA:")
        print(f"   Cuenta: {c['codigo']} - {c['nombre']}")
        print(f"   Saldo: ${c['saldo']:,.2f}")
        print(f"   Debe: ${c['debe']:,.2f}")
        print(f"   Haber: ${c['haber']:,.2f}")
