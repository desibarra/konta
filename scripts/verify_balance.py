"""
Script para verificar que el Balance General cuadra correctamente
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa
from core.services.contabilidad_engine import ContabilidadEngine
from decimal import Decimal

def verificar_balance():
    """Verifica que Activo = Pasivo + Capital"""
    
    empresa = Empresa.objects.first()
    if not empresa:
        print("❌ No hay empresas en la base de datos")
        return
    
    fecha_corte = date.today()
    
    print("=" * 70)
    print("VERIFICACIÓN: Balance General (Ecuación Contable)")
    print("=" * 70)
    print(f"Empresa: {empresa.nombre} ({empresa.rfc})")
    print(f"Fecha de corte: {fecha_corte}")
    print("-" * 70)
    
    # Obtener balance
    balance = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)
    
    # Extraer valores
    total_activo = balance['total_activo']
    total_pasivo = balance['total_pasivo']
    total_capital = balance['total_capital']
    utilidad = balance['utilidad_ejercicio']
    diferencia = balance['diferencia']
    cuadra = balance['cuadra']
    
    # Mostrar resultados
    print(f"\n📊 COMPONENTES DEL BALANCE:")
    print(f"   Total Activo:              ${total_activo:>20,.2f}")
    print(f"   Total Pasivo:              ${total_pasivo:>20,.2f}")
    print(f"   Capital Contribuido:       ${balance['total_capital'] - utilidad:>20,.2f}")
    print(f"   Utilidad del Ejercicio:    ${utilidad:>20,.2f}")
    print(f"   Total Capital:             ${total_capital:>20,.2f}")
    print("-" * 70)
    
    suma_pasivo_capital = total_pasivo + total_capital
    print(f"\n🧮 ECUACIÓN CONTABLE:")
    print(f"   Activo                     ${total_activo:>20,.2f}")
    print(f"   Pasivo + Capital           ${suma_pasivo_capital:>20,.2f}")
    print(f"   Diferencia                 ${diferencia:>20,.2f}")
    print("-" * 70)
    
    # Detalles de cuentas
    print(f"\n📋 DETALLE DE CUENTAS:")
    print(f"   Activos:     {len(balance['activos'])} cuentas")
    print(f"   Pasivos:     {len(balance['pasivos'])} cuentas")
    print(f"   Capital:     {len(balance['capital_contribuido'])} cuentas")
    
    # Verificación
    print("\n" + "=" * 70)
    if cuadra:
        print("✅ BALANCE CUADRADO - La ecuación contable está balanceada")
        print(f"   Diferencia: ${abs(diferencia):.2f} (< $0.10 tolerancia)")
    else:
        print("❌ BALANCE DESCUADRADO - Revisar contabilización")
        print(f"   Diferencia: ${abs(diferencia):,.2f}")
        
        # Mostrar cuentas con saldos negativos para diagnóstico
        print("\n⚠️  DIAGNÓSTICO:")
        activos_neg = [a for a in balance['activos'] if a.saldo < 0]
        pasivos_neg = [p for p in balance['pasivos'] if p.saldo < 0]
        
        if activos_neg:
            print(f"\n   Activos con saldo negativo: {len(activos_neg)}")
            for a in activos_neg[:5]:
                print(f"      {a.codigo} - {a.nombre}: ${a.saldo:,.2f}")
        
        if pasivos_neg:
            print(f"\n   Pasivos con saldo negativo: {len(pasivos_neg)}")
            for p in pasivos_neg[:5]:
                print(f"      {p.codigo} - {p.nombre}: ${p.saldo:,.2f}")
    
    print("=" * 70)
    
    return cuadra

if __name__ == '__main__':
    verificar_balance()
