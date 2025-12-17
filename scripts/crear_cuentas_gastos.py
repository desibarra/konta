"""
Paso 1: Crear Cuentas de Gastos Detalladas

Este script crea un catálogo expandido de cuentas de gastos
para permitir un análisis detallado en el Estado de Resultados.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable

print("=" * 80)
print("CREACIÓN DE CUENTAS DE GASTOS DETALLADAS")
print("=" * 80)

empresa = Empresa.objects.first()

# Catálogo de cuentas de gastos
cuentas_gastos = [
    # Gastos de Operación (601-XX)
    {'codigo': '601-01', 'nombre': 'Sueldos y Salarios', 'codigo_sat': '601.84'},
    {'codigo': '601-02', 'nombre': 'Honorarios Profesionales', 'codigo_sat': '601.85'},
    {'codigo': '601-03', 'nombre': 'Arrendamiento', 'codigo_sat': '601.81'},
    {'codigo': '601-04', 'nombre': 'Mantenimiento y Reparaciones', 'codigo_sat': '601.82'},
    {'codigo': '601-05', 'nombre': 'Combustibles y Lubricantes', 'codigo_sat': '601.83'},
    {'codigo': '601-06', 'nombre': 'Seguros y Fianzas', 'codigo_sat': '601.86'},
    {'codigo': '601-07', 'nombre': 'Papelería y Útiles de Oficina', 'codigo_sat': '601.87'},
    {'codigo': '601-08', 'nombre': 'Servicios Públicos', 'codigo_sat': '601.88'},
    {'codigo': '601-09', 'nombre': 'Publicidad y Promoción', 'codigo_sat': '601.89'},
    {'codigo': '601-10', 'nombre': 'Viáticos y Gastos de Viaje', 'codigo_sat': '601.90'},
    {'codigo': '601-11', 'nombre': 'Fletes y Acarreos', 'codigo_sat': '601.91'},
    {'codigo': '601-12', 'nombre': 'Mensajería y Paquetería', 'codigo_sat': '601.92'},
    {'codigo': '601-99', 'nombre': 'Otros Gastos de Operación', 'codigo_sat': '601.01'},
    
    # Gastos Financieros (602-XX)
    {'codigo': '602-01', 'nombre': 'Intereses Bancarios', 'codigo_sat': '602.01'},
    {'codigo': '602-02', 'nombre': 'Comisiones Bancarias', 'codigo_sat': '602.02'},
    {'codigo': '602-03', 'nombre': 'Pérdida Cambiaria', 'codigo_sat': '602.03'},
    
    # Gastos Administrativos (603-XX)
    {'codigo': '603-01', 'nombre': 'Depreciación', 'codigo_sat': '603.01'},
    {'codigo': '603-02', 'nombre': 'Amortización', 'codigo_sat': '603.02'},
]

print(f"\n📋 Creando {len(cuentas_gastos)} cuentas de gastos...\n")

creadas = 0
existentes = 0

for cuenta_data in cuentas_gastos:
    cuenta, created = CuentaContable.objects.get_or_create(
        empresa=empresa,
        codigo=cuenta_data['codigo'],
        defaults={
            'nombre': cuenta_data['nombre'],
            'tipo': 'GASTO',
            'naturaleza': 'D',
            'nivel': 2,
            'codigo_sat': cuenta_data['codigo_sat']
        }
    )
    
    if created:
        print(f"   ✅ {cuenta_data['codigo']:10s} - {cuenta_data['nombre']}")
        creadas += 1
    else:
        # Actualizar nombre y código SAT si ya existe
        cuenta.nombre = cuenta_data['nombre']
        cuenta.codigo_sat = cuenta_data['codigo_sat']
        cuenta.save()
        print(f"   ♻️  {cuenta_data['codigo']:10s} - {cuenta_data['nombre']} (actualizada)")
        existentes += 1

print(f"\n{'='*80}")
print(f"RESUMEN:")
print(f"   Cuentas creadas: {creadas}")
print(f"   Cuentas actualizadas: {existentes}")
print(f"   Total: {creadas + existentes}")
print(f"{'='*80}")
print(f"\n✅ Catálogo de cuentas expandido exitosamente")
