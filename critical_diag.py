import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import PlantillaPoliza, Poliza, MovimientoPoliza, Factura
from django.db.models import Count

print("=" * 70)
print("DIAGNÓSTICO CRÍTICO - ¿POR QUÉ NO HAY GASTOS?")
print("=" * 70)

# 1. Verificar plantilla
print("\n1. PLANTILLA DE EGRESOS:")
plantilla_e = PlantillaPoliza.objects.filter(tipo_factura='E').first()
if plantilla_e:
    print(f"   Nombre: {plantilla_e.nombre}")
    print(f"   Provisión: {plantilla_e.cuenta_provision.codigo if plantilla_e.cuenta_provision else 'None'} - {plantilla_e.cuenta_provision.nombre if plantilla_e.cuenta_provision else ''}")
    print(f"   Tipo: {plantilla_e.cuenta_provision.tipo if plantilla_e.cuenta_provision else 'N/A'}")
else:
    print("   ❌ NO EXISTE")

# 2. Verificar pólizas de Egreso
print("\n2. PÓLIZAS DE EGRESO:")
polizas_e = Poliza.objects.filter(factura__naturaleza='E')
print(f"   Total: {polizas_e.count()}")

# 3. Verificar facturas de Egreso
print("\n3. FACTURAS DE EGRESO:")
facturas_e = Factura.objects.filter(naturaleza='E')
estados = facturas_e.values('estado_contable').annotate(count=Count('id'))
for e in estados:
    print(f"   {e['estado_contable']}: {e['count']}")

# 4. Ver una póliza de ejemplo
print("\n4. EJEMPLO DE PÓLIZA DE EGRESO:")
poliza_ejemplo = Poliza.objects.filter(factura__naturaleza='E').first()
if poliza_ejemplo:
    print(f"   Póliza #{poliza_ejemplo.id}")
    print(f"   Factura: {poliza_ejemplo.factura.emisor_nombre[:30]}")
    print(f"   Movimientos:")
    movs = MovimientoPoliza.objects.filter(poliza=poliza_ejemplo)
    for mov in movs:
        tipo_mov = "DEBE " if mov.debe > 0 else "HABER"
        monto = mov.debe if mov.debe > 0 else mov.haber
        print(f"      {tipo_mov}: {mov.cuenta.codigo} {mov.cuenta.nombre[:30]:30} ${monto:>10,.2f} (Tipo: {mov.cuenta.tipo})")
else:
    print("   ❌ NO HAY PÓLIZAS DE EGRESO")

# 5. Total de movimientos
print("\n5. RESUMEN DE MOVIMIENTOS:")
total_movs = MovimientoPoliza.objects.count()
movs_gasto = MovimientoPoliza.objects.filter(cuenta__tipo='GASTO').count()
print(f"   Total movimientos: {total_movs}")
print(f"   En cuentas GASTO: {movs_gasto}")

print("\n" + "=" * 70)
