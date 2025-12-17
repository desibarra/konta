"""
Diagnóstico detallado del cálculo de utilidad
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa
from core.services.contabilidad_engine import ContabilidadEngine
from decimal import Decimal

empresa = Empresa.objects.first()
fecha_corte = date.today()

print("=" * 80)
print("DIAGNÓSTICO: Cálculo de Utilidad")
print("=" * 80)

# Obtener balance
balance = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)

print(f"\n📊 COMPONENTES DEL BALANCE:")
print(f"   Total Activo:           ${balance['total_activo']:>20,.2f}")
print(f"   Total Pasivo:           ${balance['total_pasivo']:>20,.2f}")
print(f"   Total Capital Contrib:  ${sum(c.saldo for c in balance['capital_contribuido']):>20,.2f}")
print(f"   Utilidad Ejercicio:     ${balance['utilidad_ejercicio']:>20,.2f}")
print(f"   Total Capital:          ${balance['total_capital']:>20,.2f}")

suma_pasivo_capital = balance['total_pasivo'] + balance['total_capital']
print(f"\n   Pasivo + Capital:       ${suma_pasivo_capital:>20,.2f}")
print(f"   Diferencia:             ${balance['diferencia']:>20,.2f}")

# Obtener resultados directamente
print(f"\n🔍 VERIFICACIÓN DE UTILIDAD:")
print(f"   Fecha inicio: 2000-01-01")
print(f"   Fecha fin: {fecha_corte}")

resultados = ContabilidadEngine.obtener_resultados(empresa, date(2000, 1, 1), fecha_corte)

print(f"\n   Total Ingresos:  ${resultados['total_ingresos']:>20,.2f}")
print(f"   Total Egresos:   ${resultados['total_egresos']:>20,.2f}")
print(f"   Utilidad Neta:   ${resultados['utilidad_neta']:>20,.2f}")

# Comparar
print(f"\n⚖️  COMPARACIÓN:")
print(f"   Utilidad (Balance):     ${balance['utilidad_ejercicio']:>20,.2f}")
print(f"   Utilidad (Resultados):  ${resultados['utilidad_neta']:>20,.2f}")
print(f"   Diferencia:             ${(balance['utilidad_ejercicio'] - resultados['utilidad_neta']):>20,.2f}")

# Calcular manualmente A = P + C
activo = balance['total_activo']
pasivo = balance['total_pasivo']
capital_contrib = sum(c.saldo for c in balance['capital_contribuido'])
utilidad = resultados['utilidad_neta']

total_capital_correcto = capital_contrib + utilidad
diferencia_correcta = activo - pasivo - total_capital_correcto

print(f"\n🧮 CÁLCULO MANUAL:")
print(f"   Activo:                 ${activo:>20,.2f}")
print(f"   Pasivo:                 ${pasivo:>20,.2f}")
print(f"   Capital Contribuido:    ${capital_contrib:>20,.2f}")
print(f"   Utilidad (correcta):    ${utilidad:>20,.2f}")
print(f"   Total P+C (correcto):   ${(pasivo + total_capital_correcto):>20,.2f}")
print(f"   Diferencia (correcta):  ${diferencia_correcta:>20,.2f}")

print("\n" + "=" * 80)

if abs(diferencia_correcta) < 0.10:
    print("✅ Con la utilidad correcta, el balance CUADRA")
    print(f"\n💡 SOLUCIÓN: El problema está en ContabilidadEngine.obtener_balance_general()")
    print(f"   Está calculando utilidad = ${balance['utilidad_ejercicio']:,.2f}")
    print(f"   Pero debería ser         = ${utilidad:,.2f}")
else:
    print(f"❌ Aún hay diferencia de ${abs(diferencia_correcta):,.2f}")

print("=" * 80)
