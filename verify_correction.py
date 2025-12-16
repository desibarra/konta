import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, MovimientoPoliza, PlantillaPoliza
from django.db.models import Sum, Count

print("=" * 70)
print("POST-CORRECCIÓN: VERIFICACIÓN DE EGRESOS")
print("=" * 70)

# 1. Estado de facturas
print("\n📋 ESTADO DE FACTURAS:")
estados = Factura.objects.values('naturaleza', 'estado_contable').annotate(
    count=Count('id')
).order_by('naturaleza', 'estado_contable')

for e in estados:
    nat = 'INGRESO' if e['naturaleza'] == 'I' else 'EGRESO' if e['naturaleza'] == 'E' else e['naturaleza']
    print(f"   {nat:10} {e['estado_contable']:15} = {e['count']:3} facturas")

# 2. Plantilla de Egresos
print("\n🔧 PLANTILLA DE EGRESOS:")
plantilla_e = PlantillaPoliza.objects.filter(tipo_factura='E').first()
if plantilla_e:
    print(f"   Nombre: {plantilla_e.nombre}")
    if plantilla_e.cuenta_provision:
        print(f"   Provisión: {plantilla_e.cuenta_provision.codigo} - {plantilla_e.cuenta_provision.nombre}")
        print(f"   Tipo: {plantilla_e.cuenta_provision.tipo}")
else:
    print("   ⚠️  No encontrada")

# 3. Movimientos en cuentas de GASTO
print("\n💰 MOVIMIENTOS EN CUENTAS DE GASTO:")
movs_gasto = MovimientoPoliza.objects.filter(
    cuenta__tipo='GASTO'
).aggregate(
    total_debe=Sum('debe'),
    count=Count('id')
)

print(f"   Total movimientos: {movs_gasto['count'] or 0}")
print(f"   Total DEBE: ${movs_gasto['total_debe'] or 0:,.2f}")

print("\n" + "=" * 70)
