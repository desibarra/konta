import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import PlantillaPoliza, CuentaContable, Poliza, Factura
from django.db import transaction

print("=" * 70)
print("CORRECCIÓN MANUAL DE PLANTILLA DE EGRESOS")
print("=" * 70)

# 1. Obtener cuenta de Gastos
cuenta_gastos = CuentaContable.objects.get(codigo='601-01')
print(f"\n✅ Cuenta de Gastos: {cuenta_gastos.codigo} - {cuenta_gastos.nombre}")
print(f"   Tipo: {cuenta_gastos.tipo}")

# 2. Obtener plantilla de Egresos
plantilla_e = PlantillaPoliza.objects.filter(tipo_factura='E').first()

if not plantilla_e:
    print("\n❌ ERROR: No existe plantilla para Egresos")
    exit(1)

print(f"\n📋 Plantilla actual: {plantilla_e.nombre}")
print(f"   cuenta_flujo:     {plantilla_e.cuenta_flujo.codigo if plantilla_e.cuenta_flujo else 'None'} - {plantilla_e.cuenta_flujo.nombre if plantilla_e.cuenta_flujo else ''}")
print(f"   cuenta_provision: {plantilla_e.cuenta_provision.codigo if plantilla_e.cuenta_provision else 'None'} - {plantilla_e.cuenta_provision.nombre if plantilla_e.cuenta_provision else ''}")
print(f"   cuenta_impuesto:  {plantilla_e.cuenta_impuesto.codigo if plantilla_e.cuenta_impuesto else 'None'} - {plantilla_e.cuenta_impuesto.nombre if plantilla_e.cuenta_impuesto else ''}")

# 3. CORREGIR plantilla
print("\n🔧 Corrigiendo plantilla...")
plantilla_e.cuenta_provision = cuenta_gastos
plantilla_e.save()

print(f"✅ Plantilla actualizada:")
print(f"   cuenta_provision: {plantilla_e.cuenta_provision.codigo} - {plantilla_e.cuenta_provision.nombre} (Tipo: {plantilla_e.cuenta_provision.tipo})")

# 4. Limpiar y re-contabilizar
print("\n🧹 Limpiando pólizas de Egresos...")
polizas_eliminadas = Poliza.objects.filter(factura__naturaleza='E').delete()[0]
print(f"✅ Eliminadas: {polizas_eliminadas} pólizas")

print("\n🔄 Reseteando facturas...")
facturas_reset = Factura.objects.filter(naturaleza='E').update(estado_contable='PENDIENTE')
print(f"✅ Reseteadas: {facturas_reset} facturas")

print("\n" + "=" * 70)
print("✅ CORRECCIÓN COMPLETADA")
print("=" * 70)
print("\nAhora ejecuta:")
print("  python manage.py force_recontabilizar_egresos")
