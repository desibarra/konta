"""
Prueba directa del motor de balance
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

print("PRUEBA DIRECTA DEL MOTOR DE BALANCE")
print("=" * 60)

balance = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)

print(f"\nActivo:     ${balance['total_activo']:,.2f}")
print(f"Pasivo:     ${balance['total_pasivo']:,.2f}")
print(f"Capital:    ${balance['total_capital']:,.2f}")
print(f"Utilidad:   ${balance['utilidad_ejercicio']:,.2f}")
print(f"Diferencia: ${balance['diferencia']:,.2f}")
print(f"Cuadra:     {balance['cuadra']}")

print("\n" + "=" * 60)
print(f"ECUACIÓN: ${balance['total_activo']:,.2f} = ${balance['total_pasivo']:,.2f} + ${balance['total_capital']:,.2f}")
print(f"Resultado: ${balance['total_activo']:,.2f} - ${balance['total_pasivo'] + balance['total_capital']:,.2f} = ${balance['diferencia']:,.2f}")
