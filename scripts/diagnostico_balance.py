"""
Script de diagnóstico profundo para el Balance General
Identifica exactamente dónde está el descuadre
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa, CuentaContable, MovimientoPoliza
from django.db.models import Sum, Q
from decimal import Decimal

def diagnosticar_balance():
    empresa = Empresa.objects.first()
    fecha_corte = date.today()
    
    print("=" * 80)
    print("DIAGNÓSTICO PROFUNDO: Balance General")
    print("=" * 80)
    print(f"Empresa: {empresa.nombre}")
    print(f"Fecha: {fecha_corte}\n")
    
    # 1. Verificar TODOS los movimientos
    total_debe = MovimientoPoliza.objects.filter(
        poliza__factura__empresa=empresa,
        poliza__fecha__lte=fecha_corte
    ).aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
    
    total_haber = MovimientoPoliza.objects.filter(
        poliza__factura__empresa=empresa,
        poliza__fecha__lte=fecha_corte
    ).aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
    
    print("📊 TOTALES DE MOVIMIENTOS:")
    print(f"   Total Debe:  ${total_debe:>20,.2f}")
    print(f"   Total Haber: ${total_haber:>20,.2f}")
    print(f"   Diferencia:  ${(total_debe - total_haber):>20,.2f}")
    
    if abs(total_debe - total_haber) > 0.01:
        print("   ❌ LOS MOVIMIENTOS NO CUADRAN - Error en pólizas")
    else:
        print("   ✅ Los movimientos cuadran (Debe = Haber)")
    
    print("\n" + "-" * 80 + "\n")
    
    # 2. Analizar por TIPO de cuenta
    tipos = ['ACTIVO', 'PASIVO', 'CAPITAL', 'INGRESO', 'COSTO', 'GASTO']
    
    print("📋 SALDOS POR TIPO DE CUENTA:\n")
    
    totales_por_tipo = {}
    
    for tipo in tipos:
        cuentas = CuentaContable.objects.filter(empresa=empresa, tipo=tipo)
        
        saldo_total = Decimal('0')
        count = 0
        
        for cuenta in cuentas:
            movs = MovimientoPoliza.objects.filter(
                cuenta=cuenta,
                poliza__fecha__lte=fecha_corte
            )
            
            debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
            haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
            
            # Calcular saldo según naturaleza
            if cuenta.naturaleza == 'D':  # Deudora
                saldo = debe - haber
            else:  # Acreedora
                saldo = haber - debe
            
            if saldo != 0:
                saldo_total += saldo
                count += 1
        
        totales_por_tipo[tipo] = saldo_total
        print(f"   {tipo:12s}: ${saldo_total:>20,.2f}  ({count} cuentas)")
    
    print("\n" + "-" * 80 + "\n")
    
    # 3. Verificar ecuación contable
    print("🧮 ECUACIÓN CONTABLE:\n")
    
    activo = totales_por_tipo['ACTIVO']
    pasivo = totales_por_tipo['PASIVO']
    capital = totales_por_tipo['CAPITAL']
    
    # Utilidad = Ingresos - Costos - Gastos
    utilidad = (totales_por_tipo['INGRESO'] - 
                totales_por_tipo['COSTO'] - 
                totales_por_tipo['GASTO'])
    
    print(f"   Activo:                    ${activo:>20,.2f}")
    print(f"   Pasivo:                    ${pasivo:>20,.2f}")
    print(f"   Capital Contribuido:       ${capital:>20,.2f}")
    print(f"   Utilidad del Ejercicio:    ${utilidad:>20,.2f}")
    print(f"   Total Pasivo + Capital:    ${(pasivo + capital + utilidad):>20,.2f}")
    print()
    print(f"   Diferencia (A - P - C):    ${(activo - pasivo - capital - utilidad):>20,.2f}")
    
    diferencia = activo - pasivo - capital - utilidad
    
    print("\n" + "-" * 80 + "\n")
    
    if abs(diferencia) < 0.10:
        print("✅ BALANCE CUADRADO")
    else:
        print("❌ BALANCE DESCUADRADO")
        print("\n🔍 INVESTIGANDO CAUSA...\n")
        
        # Buscar cuentas problemáticas
        print("Cuentas con mayor saldo (Top 10):\n")
        
        todas_cuentas = []
        for cuenta in CuentaContable.objects.filter(empresa=empresa):
            movs = MovimientoPoliza.objects.filter(
                cuenta=cuenta,
                poliza__fecha__lte=fecha_corte
            )
            
            debe = movs.aggregate(Sum('debe'))['debe__sum'] or Decimal('0')
            haber = movs.aggregate(Sum('haber'))['haber__sum'] or Decimal('0')
            
            if cuenta.naturaleza == 'D':
                saldo = debe - haber
            else:
                saldo = haber - debe
            
            if saldo != 0:
                todas_cuentas.append({
                    'codigo': cuenta.codigo,
                    'nombre': cuenta.nombre,
                    'tipo': cuenta.tipo,
                    'naturaleza': cuenta.naturaleza,
                    'saldo': saldo
                })
        
        # Ordenar por saldo absoluto
        todas_cuentas.sort(key=lambda x: abs(x['saldo']), reverse=True)
        
        for i, c in enumerate(todas_cuentas[:10], 1):
            print(f"   {i:2d}. {c['codigo']:15s} {c['tipo']:8s} ${c['saldo']:>15,.2f} - {c['nombre'][:40]}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    diagnosticar_balance()
