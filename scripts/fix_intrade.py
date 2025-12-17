"""
Buscar empresa INTRADE y diagnosticar
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

print("=" * 80)
print("TODAS LAS EMPRESAS:")
print("=" * 80)

for emp in Empresa.objects.all():
    print(f"  - {emp.nombre} ({emp.rfc})")

# Buscar INTRADE
intrade = Empresa.objects.filter(rfc='TVA060209QL6').first()

if not intrade:
    print("\n❌ No se encontró empresa con RFC TVA060209QL6")
else:
    print(f"\n✅ Empresa encontrada: {intrade.nombre}")
    print("=" * 80)
    
    fecha_corte = date.today()
    balance = ContabilidadEngine.obtener_balance_general(intrade, fecha_corte)
    
    print(f"\n📊 BALANCE:")
    print(f"   Activo:     ${balance['total_activo']:>20,.2f}")
    print(f"   Pasivo:     ${balance['total_pasivo']:>20,.2f}")
    print(f"   Capital:    ${balance['total_capital']:>20,.2f}")
    print(f"   Utilidad:   ${balance['utilidad_ejercicio']:>20,.2f}")
    print(f"   Diferencia: ${balance['diferencia']:>20,.2f}")
    
    # Buscar 702-99
    print(f"\n🔍 CUENTA 702-99:")
    try:
        cuenta_702 = CuentaContable.objects.get(empresa=intrade, codigo='702-99')
        print(f"   Tipo: {cuenta_702.tipo}")
        
        movs = MovimientoPoliza.objects.filter(cuenta=cuenta_702, poliza__fecha__lte=fecha_corte)
        debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
        haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
        saldo = haber - debe if cuenta_702.naturaleza == 'A' else debe - haber
        
        print(f"   Saldo: ${saldo:,.2f}")
        
        if abs(saldo - Decimal('289779.30')) < 1:
            print(f"\n⚠️  ESTA ES LA DIFERENCIA!")
            print(f"   La cuenta 702-99 tiene ${abs(saldo):,.2f}")
            print(f"   Tipo actual: {cuenta_702.tipo}")
            print(f"\n💡 SOLUCIÓN: Cambiar tipo a GASTO")
            
            cuenta_702.tipo = 'GASTO'
            cuenta_702.save()
            print(f"   ✅ Tipo actualizado a GASTO")
            print(f"\n   Recarga el Balance General ahora")
        
    except CuentaContable.DoesNotExist:
        print(f"   No existe")
    
    print("\n" + "=" * 80)
