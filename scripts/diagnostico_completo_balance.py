"""
Diagnóstico completo del balance para encontrar la diferencia
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
print("DIAGNÓSTICO COMPLETO DEL BALANCE")
print("=" * 80)

# 1. Obtener balance usando el motor
balance = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)

print(f"\n📊 BALANCE SEGÚN MOTOR:")
print(f"   Activo:     ${balance['total_activo']:>20,.2f}")
print(f"   Pasivo:     ${balance['total_pasivo']:>20,.2f}")
print(f"   Capital:    ${balance['total_capital']:>20,.2f}")
print(f"   Utilidad:   ${balance['utilidad_ejercicio']:>20,.2f}")
print(f"   Diferencia: ${balance['diferencia']:>20,.2f}")

# 2. Calcular manualmente por tipo de cuenta
print(f"\n🔍 CÁLCULO MANUAL POR TIPO:")

tipos_cuentas = {}
for tipo in ['ACTIVO', 'PASIVO', 'CAPITAL', 'INGRESO', 'COSTO', 'GASTO', 'RESULTADO']:
    cuentas = CuentaContable.objects.filter(empresa=empresa, tipo=tipo)
    
    total = Decimal('0')
    count = 0
    cuentas_702 = []
    
    for cuenta in cuentas:
        movs = MovimientoPoliza.objects.filter(cuenta=cuenta, poliza__fecha__lte=fecha_corte)
        debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
        haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
        
        if cuenta.naturaleza == 'D':
            saldo = debe - haber
        else:
            saldo = haber - debe
        
        if saldo != 0:
            total += saldo
            count += 1
            
            if cuenta.codigo == '702-99':
                cuentas_702.append({
                    'codigo': cuenta.codigo,
                    'nombre': cuenta.nombre,
                    'tipo': cuenta.tipo,
                    'saldo': saldo
                })
    
    tipos_cuentas[tipo] = {
        'total': total,
        'count': count,
        'tiene_702': len(cuentas_702) > 0,
        'cuentas_702': cuentas_702
    }
    
    marca = "⚠️ " if len(cuentas_702) > 0 else "  "
    print(f"   {marca}{tipo:12s}: ${total:>20,.2f}  ({count} cuentas)")
    
    if cuentas_702:
        for c in cuentas_702:
            print(f"      └─ 702-99 encontrada: ${c['saldo']:,.2f}")

# 3. Calcular utilidad manualmente
utilidad_manual = tipos_cuentas['INGRESO']['total'] - tipos_cuentas['COSTO']['total'] - tipos_cuentas['GASTO']['total']

if tipos_cuentas['RESULTADO']['tiene_702']:
    utilidad_manual -= tipos_cuentas['RESULTADO']['total']

print(f"\n🧮 CÁLCULO DE UTILIDAD:")
print(f"   Ingresos:   ${tipos_cuentas['INGRESO']['total']:>20,.2f}")
print(f"   - Costos:   ${tipos_cuentas['COSTO']['total']:>20,.2f}")
print(f"   - Gastos:   ${tipos_cuentas['GASTO']['total']:>20,.2f}")
if tipos_cuentas['RESULTADO']['total'] != 0:
    print(f"   - Resultado: ${tipos_cuentas['RESULTADO']['total']:>20,.2f}")
print(f"   = Utilidad: ${utilidad_manual:>20,.2f}")

# 4. Verificar ecuación contable
activo_manual = tipos_cuentas['ACTIVO']['total']
pasivo_manual = tipos_cuentas['PASIVO']['total']
capital_manual = tipos_cuentas['CAPITAL']['total'] + utilidad_manual

diferencia_manual = activo_manual - pasivo_manual - capital_manual

print(f"\n⚖️  ECUACIÓN CONTABLE:")
print(f"   Activo:              ${activo_manual:>20,.2f}")
print(f"   Pasivo:              ${pasivo_manual:>20,.2f}")
print(f"   Capital + Utilidad:  ${capital_manual:>20,.2f}")
print(f"   Diferencia:          ${diferencia_manual:>20,.2f}")

print(f"\n" + "=" * 80)
if abs(diferencia_manual) < 0.10:
    print("✅ BALANCE CUADRA MANUALMENTE")
else:
    print(f"❌ BALANCE NO CUADRA - Diferencia: ${abs(diferencia_manual):,.2f}")
    
    if tipos_cuentas['RESULTADO']['tiene_702']:
        print(f"\n⚠️  PROBLEMA ENCONTRADO:")
        print(f"   La cuenta 702-99 está clasificada como tipo RESULTADO")
        print(f"   Saldo: ${tipos_cuentas['RESULTADO']['cuentas_702'][0]['saldo']:,.2f}")
        print(f"   Esto está afectando el cálculo de utilidad")

print("=" * 80)
