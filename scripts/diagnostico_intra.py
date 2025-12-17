"""
Listar todas las empresas y diagnosticar INTRA
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
print("EMPRESAS EN EL SISTEMA")
print("=" * 80)

empresas = Empresa.objects.all()
for i, emp in enumerate(empresas, 1):
    print(f"{i}. {emp.nombre} ({emp.rfc})")

print("\n" + "=" * 80)

# Buscar INTRA
intra = Empresa.objects.filter(nombre__icontains='INTRA').first()

if not intra:
    print("❌ No se encontró empresa INTRA")
else:
    print(f"✅ Empresa INTRA encontrada: {intra.nombre} ({intra.rfc})")
    print("=" * 80)
    
    fecha_corte = date.today()
    
    # Diagnóstico de INTRA
    print(f"\n📊 BALANCE DE {intra.nombre}:")
    balance = ContabilidadEngine.obtener_balance_general(intra, fecha_corte)
    
    print(f"   Activo:     ${balance['total_activo']:>20,.2f}")
    print(f"   Pasivo:     ${balance['total_pasivo']:>20,.2f}")
    print(f"   Capital:    ${balance['total_capital']:>20,.2f}")
    print(f"   Utilidad:   ${balance['utilidad_ejercicio']:>20,.2f}")
    print(f"   Diferencia: ${balance['diferencia']:>20,.2f}")
    
    # Buscar cuenta 702-99 en INTRA
    print(f"\n🔍 CUENTA 702-99 EN INTRA:")
    try:
        cuenta_702 = CuentaContable.objects.get(empresa=intra, codigo='702-99')
        print(f"   ✅ Existe")
        print(f"   Tipo: {cuenta_702.tipo}")
        print(f"   Naturaleza: {cuenta_702.naturaleza}")
        
        # Calcular saldo
        movs = MovimientoPoliza.objects.filter(
            cuenta=cuenta_702,
            poliza__fecha__lte=fecha_corte
        )
        debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
        haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
        
        if cuenta_702.naturaleza == 'D':
            saldo = debe - haber
        else:
            saldo = haber - debe
        
        print(f"   Saldo: ${saldo:,.2f}")
        
    except CuentaContable.DoesNotExist:
        print(f"   ❌ No existe")
    
    print("\n" + "=" * 80)
