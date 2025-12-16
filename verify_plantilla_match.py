import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import PlantillaPoliza, Factura

print("VERIFICACIÓN DE PLANTILLAS VS FACTURAS")
print("=" * 70)

# 1. Ver todas las plantillas
print("\n1. PLANTILLAS EXISTENTES:")
plantillas = PlantillaPoliza.objects.all()
for p in plantillas:
    print(f"   {p.nombre}: tipo_factura='{p.tipo_factura}'")
    if p.cuenta_provision:
        print(f"      Provisión: {p.cuenta_provision.codigo} - {p.cuenta_provision.nombre} (Tipo: {p.cuenta_provision.tipo})")

# 2. Ver tipos de comprobante de facturas
print("\n2. TIPOS DE COMPROBANTE EN FACTURAS:")
from django.db.models import Count
tipos = Factura.objects.values('tipo_comprobante', 'naturaleza').annotate(count=Count('id'))
for t in tipos:
    print(f"   tipo_comprobante='{t['tipo_comprobante']}', naturaleza='{t['naturaleza']}': {t['count']} facturas")

# 3. Verificar coincidencia
print("\n3. VERIFICACIÓN DE COINCIDENCIA:")
facturas_e = Factura.objects.filter(naturaleza='E').first()
if facturas_e:
    print(f"   Factura de Egreso ejemplo:")
    print(f"      tipo_comprobante: '{facturas_e.tipo_comprobante}'")
    print(f"      naturaleza: '{facturas_e.naturaleza}'")
    
    # Buscar plantilla como lo hace el servicio
    plantilla = PlantillaPoliza.objects.filter(
        empresa=facturas_e.empresa,
        tipo_factura=facturas_e.tipo_comprobante
    ).first()
    
    if plantilla:
        print(f"\n   ✅ Plantilla encontrada: {plantilla.nombre}")
        print(f"      cuenta_provision: {plantilla.cuenta_provision.codigo if plantilla.cuenta_provision else 'None'}")
        print(f"      Tipo: {plantilla.cuenta_provision.tipo if plantilla.cuenta_provision else 'N/A'}")
    else:
        print(f"\n   ❌ NO SE ENCONTRÓ PLANTILLA para tipo_factura='{facturas_e.tipo_comprobante}'")

print("\n" + "=" * 70)
