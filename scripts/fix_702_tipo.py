"""
Actualizar tipo de cuenta 702-99 existente
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable

empresa = Empresa.objects.first()

try:
    cuenta = CuentaContable.objects.get(empresa=empresa, codigo='702-99')
    print(f"✅ Cuenta 702-99 encontrada")
    print(f"   Tipo actual: {cuenta.tipo}")
    print(f"   Naturaleza: {cuenta.naturaleza}")
    
    # Cambiar a tipo que NO afecte balance
    cuenta.tipo = 'GASTO'
    cuenta.naturaleza = 'A'
    cuenta.save()
    
    print(f"\n✅ Cuenta actualizada:")
    print(f"   Nuevo tipo: {cuenta.tipo}")
    print(f"   Nueva naturaleza: {cuenta.naturaleza}")
    print(f"\n💡 Ahora recarga el Balance General")
    
except CuentaContable.DoesNotExist:
    print("❌ Cuenta 702-99 no existe en la base de datos")
