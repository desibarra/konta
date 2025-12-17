"""
Actualizar tipo de cuenta 702-99 si ya existe
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable

empresa = Empresa.objects.first()

try:
    cuenta = CuentaContable.objects.get(empresa=empresa, codigo='702-99')
    print(f"Cuenta 702-99 encontrada - Actualizando...")
    print(f"  Tipo anterior: {cuenta.tipo}")
    
    cuenta.tipo = 'GASTO'
    cuenta.naturaleza = 'A'
    cuenta.nivel = 3
    cuenta.codigo_sat = '999-99'
    cuenta.save()
    
    print(f"  Tipo nuevo: {cuenta.tipo}")
    print(f"✅ Cuenta actualizada")
except CuentaContable.DoesNotExist:
    print("✅ Cuenta 702-99 no existe (se creará con el tipo correcto)")
