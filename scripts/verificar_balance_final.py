"""
Verificación final del balance después de corrección de ajustes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa
from core.services.contabilidad_engine import ContabilidadEngine

empresa = Empresa.objects.first()
fecha_corte = date.today()

print("=" * 80)
print("VERIFICACIÓN FINAL DEL BALANCE")
print("=" * 80)

balance = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)

print(f"\n📊 BALANCE GENERAL:")
print(f"   Activo:     ${balance['total_activo']:>20,.2f}")
print(f"   Pasivo:     ${balance['total_pasivo']:>20,.2f}")
print(f"   Capital:    ${balance['total_capital']:>20,.2f}")
print(f"   Utilidad:   ${balance['utilidad_ejercicio']:>20,.2f}")
print(f"   Diferencia: ${balance['diferencia']:>20,.2f}")

print(f"\n⚖️  ECUACIÓN CONTABLE:")
print(f"   {balance['total_activo']:,.2f} = {balance['total_pasivo']:,.2f} + {balance['total_capital']:,.2f}")

if abs(balance['diferencia']) < 100:
    print(f"\n✅ BALANCE CUADRA CORRECTAMENTE")
    print(f"   Diferencia: ${abs(balance['diferencia']):,.2f} (aceptable)")
else:
    print(f"\n⚠️  Balance con diferencia: ${abs(balance['diferencia']):,.2f}")

print(f"\n{'='*80}")
