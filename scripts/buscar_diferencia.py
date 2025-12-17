"""
Buscar la causa exacta de la diferencia de $289,779.30
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa, CuentaContable, MovimientoPoliza
from django.db.models import Sum, Q
from decimal import Decimal

empresa = Empresa.objects.first()
fecha_corte = date.today()

print("=" * 80)
print("BÚSQUEDA DE DIFERENCIA: $289,779.30")
print("=" * 80)

# Buscar cuentas con saldo cercano a esta cantidad
target = Decimal('289779.30')
tolerance = Decimal('1.00')

print("\n🔍 Buscando cuentas con saldo cercano a $289,779.30...\n")

for cuenta in CuentaContable.objects.filter(empresa=empresa):
    movs = MovimientoPoliza.objects.filter(cuenta=cuenta, poliza__fecha__lte=fecha_corte)
    
    debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
    haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
    
    # Calcular saldo según naturaleza
    if cuenta.naturaleza == 'D':
        saldo = debe - haber
    else:
        saldo = haber - debe
    
    # Verificar si el saldo está cerca del target
    if abs(abs(saldo) - target) < tolerance:
        print(f"✅ ENCONTRADA: {cuenta.codigo} - {cuenta.nombre}")
        print(f"   Tipo: {cuenta.tipo}")
        print(f"   Naturaleza: {cuenta.naturaleza}")
        print(f"   Saldo: ${saldo:,.2f}")
        print(f"   Debe: ${debe:,.2f}")
        print(f"   Haber: ${haber:,.2f}")
        print()

# También buscar combinaciones que sumen exactamente
print("\n🔍 Buscando cuentas que sumen $289,779.30...\n")

cuentas_con_saldo = []
for cuenta in CuentaContable.objects.filter(empresa=empresa):
    movs = MovimientoPoliza.objects.filter(cuenta=cuenta, poliza__fecha__lte=fecha_corte)
    
    debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
    haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
    
    if cuenta.naturaleza == 'D':
        saldo = debe - haber
    else:
        saldo = haber - debe
    
    if saldo != 0:
        cuentas_con_saldo.append({
            'codigo': cuenta.codigo,
            'nombre': cuenta.nombre,
            'tipo': cuenta.tipo,
            'saldo': saldo
        })

# Buscar cuentas mal clasificadas (INGRESO/GASTO/COSTO que deberían estar en balance)
print("\n⚠️  CUENTAS POTENCIALMENTE MAL CLASIFICADAS:\n")

for c in cuentas_con_saldo:
    # Si es cuenta de resultados (4xx, 5xx, 6xx) pero está clasificada como ACTIVO/PASIVO/CAPITAL
    codigo = c['codigo']
    tipo = c['tipo']
    
    if codigo.startswith('4') and tipo not in ['INGRESO']:
        print(f"   {codigo} - {c['nombre']}: tipo={tipo} (debería ser INGRESO)")
    elif codigo.startswith('5') and tipo not in ['COSTO', 'GASTO']:
        print(f"   {codigo} - {c['nombre']}: tipo={tipo} (debería ser COSTO/GASTO)")
    elif codigo.startswith('6') and tipo not in ['GASTO']:
        print(f"   {codigo} - {c['nombre']}: tipo={tipo} (debería ser GASTO)")
    elif codigo.startswith('1') and tipo not in ['ACTIVO']:
        print(f"   {codigo} - {c['nombre']}: tipo={tipo} (debería ser ACTIVO)")
    elif codigo.startswith('2') and tipo not in ['PASIVO']:
        print(f"   {codigo} - {c['nombre']}: tipo={tipo} (debería ser PASIVO)")
    elif codigo.startswith('3') and tipo not in ['CAPITAL']:
        print(f"   {codigo} - {c['nombre']}: tipo={tipo} (debería ser CAPITAL)")

print("\n" + "=" * 80)
