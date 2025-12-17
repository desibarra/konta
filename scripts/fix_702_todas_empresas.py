"""
Corregir cuenta 702-99 en TODAS las empresas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable
from django.db.models import Sum
from decimal import Decimal

print("=" * 80)
print("CORRECCIÓN DE CUENTA 702-99 EN TODAS LAS EMPRESAS")
print("=" * 80)

empresas = Empresa.objects.all()
total_corregidas = 0

for empresa in empresas:
    print(f"\n📊 {empresa.nombre} ({empresa.rfc})")
    
    try:
        cuenta_702 = CuentaContable.objects.get(empresa=empresa, codigo='702-99')
        
        # Calcular saldo
        movs = cuenta_702.movimientopoliza_set.all()
        debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
        haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
        saldo = haber - debe if cuenta_702.naturaleza == 'A' else debe - haber
        
        print(f"   Cuenta 702-99 encontrada")
        print(f"   Tipo actual: {cuenta_702.tipo}")
        print(f"   Saldo: ${saldo:,.2f}")
        
        if cuenta_702.tipo != 'GASTO':
            cuenta_702.tipo = 'GASTO'
            cuenta_702.naturaleza = 'A'
            cuenta_702.save()
            print(f"   ✅ Actualizada a tipo GASTO")
            total_corregidas += 1
        else:
            print(f"   ✓ Ya es tipo GASTO")
            
    except CuentaContable.DoesNotExist:
        print(f"   - No tiene cuenta 702-99")

print(f"\n{'='*80}")
print(f"✅ Empresas corregidas: {total_corregidas}")
print(f"{'='*80}")
print(f"\n💡 Ahora recarga el Balance General de cualquier empresa")
print(f"   Usa Ctrl+Shift+R para forzar recarga sin caché")
