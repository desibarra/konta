"""
Script para analizar los ajustes de redondeo excesivos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable, MovimientoPoliza, Poliza
from django.db.models import Sum
from decimal import Decimal

def analizar_ajustes():
    empresa = Empresa.objects.first()
    
    print("=" * 80)
    print("ANÁLISIS: Cuenta 702-99 (Ajustes por Redondeo)")
    print("=" * 80)
    
    # Buscar cuenta de ajustes
    try:
        cuenta_ajuste = CuentaContable.objects.get(empresa=empresa, codigo='702-99')
    except CuentaContable.DoesNotExist:
        print("❌ Cuenta 702-99 no existe")
        return
    
    # Obtener todos los movimientos
    movimientos = MovimientoPoliza.objects.filter(cuenta=cuenta_ajuste).select_related('poliza', 'poliza__factura')
    
    total_debe = movimientos.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
    total_haber = movimientos.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
    saldo = total_haber - total_debe  # Acreedora
    
    print(f"\n📊 TOTALES:")
    print(f"   Debe:  ${total_debe:>20,.2f}")
    print(f"   Haber: ${total_haber:>20,.2f}")
    print(f"   Saldo: ${saldo:>20,.2f}")
    print(f"   Total movimientos: {movimientos.count()}")
    
    print(f"\n🔍 MOVIMIENTOS MÁS GRANDES (Top 20):\n")
    
    # Ordenar por monto absoluto
    movs_list = []
    for mov in movimientos:
        monto = mov.debe if mov.debe > 0 else -mov.haber
        movs_list.append({
            'poliza_id': mov.poliza.id,
            'factura_uuid': mov.poliza.factura.uuid if mov.poliza.factura else None,
            'fecha': mov.poliza.fecha,
            'monto': monto,
            'descripcion': mov.descripcion
        })
    
    movs_list.sort(key=lambda x: abs(x['monto']), reverse=True)
    
    for i, m in enumerate(movs_list[:20], 1):
        print(f"   {i:2d}. Póliza #{m['poliza_id']:5d} | {m['fecha'].strftime('%Y-%m-%d')} | ${m['monto']:>15,.2f} | {m['factura_uuid']}")
    
    # Estadísticas
    print(f"\n📈 ESTADÍSTICAS:")
    ajustes_grandes = [m for m in movs_list if abs(m['monto']) > 100]
    ajustes_pequenos = [m for m in movs_list if abs(m['monto']) <= 100]
    
    print(f"   Ajustes > $100:  {len(ajustes_grandes)} movimientos")
    print(f"   Ajustes <= $100: {len(ajustes_pequenos)} movimientos")
    
    if ajustes_grandes:
        suma_grandes = sum(m['monto'] for m in ajustes_grandes)
        print(f"   Total ajustes grandes: ${suma_grandes:,.2f}")
    
    print("\n" + "=" * 80)
    print("⚠️  CONCLUSIÓN:")
    if len(ajustes_grandes) > 10:
        print("   Hay DEMASIADOS ajustes grandes - indica error sistemático en contabilización")
    else:
        print("   Los ajustes parecen normales (redondeo de centavos)")
    print("=" * 80)

if __name__ == '__main__':
    analizar_ajustes()
