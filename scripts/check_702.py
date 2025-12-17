"""
Verificar clasificación de cuenta 702-99
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable

empresa = Empresa.objects.first()

try:
    cuenta = CuentaContable.objects.get(empresa=empresa, codigo='702-99')
    print(f"Cuenta 702-99 encontrada:")
    print(f"  Nombre: {cuenta.nombre}")
    print(f"  Tipo: {cuenta.tipo}")
    print(f"  Naturaleza: {cuenta.naturaleza}")
    print(f"  Nivel: {cuenta.nivel}")
except CuentaContable.DoesNotExist:
    print("Cuenta 702-99 NO existe")
