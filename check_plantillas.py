import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import PlantillaPoliza

print("=" * 70)
print("PLANTILLAS CONTABLES CONFIGURADAS")
print("=" * 70)

plantillas = PlantillaPoliza.objects.all()

for p in plantillas:
    print(f"\n📋 {p.nombre} (Tipo: {p.tipo_factura})")
    if p.cuenta_flujo:
        print(f"   Flujo:     {p.cuenta_flujo.codigo} - {p.cuenta_flujo.nombre} (Tipo: {p.cuenta_flujo.tipo})")
    if p.cuenta_provision:
        print(f"   Provisión: {p.cuenta_provision.codigo} - {p.cuenta_provision.nombre} (Tipo: {p.cuenta_provision.tipo})")
    if p.cuenta_impuesto:
        print(f"   Impuesto:  {p.cuenta_impuesto.codigo} - {p.cuenta_impuesto.nombre} (Tipo: {p.cuenta_impuesto.tipo})")

print("\n" + "=" * 70)
