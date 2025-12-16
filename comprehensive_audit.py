import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable, PlantillaPoliza
from django.db.models import Sum, Count, Q
from datetime import date

print("=" * 80)
print("AUDITORÍA COMPLETA POST-RECONTABILIZACIÓN")
print("=" * 80)

# 1. Estado de Facturas
print("\n📋 1. ESTADO DE FACTURAS:")
facturas_stats = Factura.objects.values('naturaleza', 'estado_contable').annotate(
    count=Count('id'),
    total=Sum('total')
).order_by('naturaleza', 'estado_contable')

for stat in facturas_stats:
    nat = 'INGRESO' if stat['naturaleza'] == 'I' else 'EGRESO' if stat['naturaleza'] == 'E' else stat['naturaleza']
    print(f"   {nat:10} {stat['estado_contable']:15} = {stat['count']:3} facturas (${stat['total']:,.2f})")

# 2. Pólizas Generadas
print("\n📊 2. PÓLIZAS GENERADAS:")
total_polizas = Poliza.objects.count()
polizas_por_tipo = Poliza.objects.values('factura__naturaleza').annotate(
    count=Count('id')
).order_by('factura__naturaleza')

print(f"   Total pólizas: {total_polizas}")
for p in polizas_por_tipo:
    nat = 'INGRESO' if p['factura__naturaleza'] == 'I' else 'EGRESO' if p['factura__naturaleza'] == 'E' else p['factura__naturaleza']
    print(f"   {nat}: {p['count']} pólizas")

# 3. Movimientos Contables
print("\n💰 3. MOVIMIENTOS CONTABLES:")
total_movs = MovimientoPoliza.objects.count()
total_debe = MovimientoPoliza.objects.aggregate(Sum('debe'))['debe__sum'] or 0
total_haber = MovimientoPoliza.objects.aggregate(Sum('haber'))['haber__sum'] or 0

print(f"   Total movimientos: {total_movs}")
print(f"   Total DEBE:  ${total_debe:,.2f}")
print(f"   Total HABER: ${total_haber:,.2f}")
print(f"   Diferencia:  ${abs(total_debe - total_haber):,.2f}")

# 4. Movimientos por TIPO de Cuenta
print("\n🔍 4. MOVIMIENTOS POR TIPO DE CUENTA:")
tipos_debe = MovimientoPoliza.objects.values('cuenta__tipo').annotate(
    total=Sum('debe'),
    count=Count('id')
).filter(total__gt=0).order_by('-total')

print("\n   DEBE:")
for t in tipos_debe:
    print(f"      {t['cuenta__tipo']:15}: ${t['total']:>15,.2f} ({t['count']:4} movs)")

tipos_haber = MovimientoPoliza.objects.values('cuenta__tipo').annotate(
    total=Sum('haber'),
    count=Count('id')
).filter(total__gt=0).order_by('-total')

print("\n   HABER:")
for t in tipos_haber:
    print(f"      {t['cuenta__tipo']:15}: ${t['total']:>15,.2f} ({t['count']:4} movs)")

# 5. Cuentas de GASTO (lo más importante)
print("\n🎯 5. CUENTAS DE GASTO (CRÍTICO):")
cuentas_gasto = CuentaContable.objects.filter(tipo='GASTO')
print(f"   Total cuentas de GASTO: {cuentas_gasto.count()}")

for cuenta in cuentas_gasto:
    movs_debe = MovimientoPoliza.objects.filter(cuenta=cuenta).aggregate(Sum('debe'))['debe__sum'] or 0
    movs_count = MovimientoPoliza.objects.filter(cuenta=cuenta).count()
    print(f"   {cuenta.codigo} {cuenta.nombre[:40]:40} = ${movs_debe:>12,.2f} ({movs_count} movs)")

# 6. Plantilla de Egresos
print("\n🔧 6. PLANTILLA DE EGRESOS:")
plantilla_e = PlantillaPoliza.objects.filter(tipo_factura='E').first()
if plantilla_e:
    print(f"   Nombre: {plantilla_e.nombre}")
    if plantilla_e.cuenta_flujo:
        print(f"   Flujo:     {plantilla_e.cuenta_flujo.codigo} - {plantilla_e.cuenta_flujo.nombre} (Tipo: {plantilla_e.cuenta_flujo.tipo})")
    if plantilla_e.cuenta_provision:
        print(f"   Provisión: {plantilla_e.cuenta_provision.codigo} - {plantilla_e.cuenta_provision.nombre} (Tipo: {plantilla_e.cuenta_provision.tipo})")
    if plantilla_e.cuenta_impuesto:
        print(f"   Impuesto:  {plantilla_e.cuenta_impuesto.codigo} - {plantilla_e.cuenta_impuesto.nombre} (Tipo: {plantilla_e.cuenta_impuesto.tipo})")
else:
    print("   ⚠️  NO ENCONTRADA")

# 7. Muestra de Pólizas de Egreso
print("\n📝 7. MUESTRA DE PÓLIZAS DE EGRESO (últimas 3):")
polizas_egreso = Poliza.objects.filter(factura__naturaleza='E').order_by('-id')[:3]

for poliza in polizas_egreso:
    print(f"\n   Póliza #{poliza.id} - {poliza.factura.emisor_nombre[:30]}")
    movs = MovimientoPoliza.objects.filter(poliza=poliza)
    for mov in movs:
        if mov.debe > 0:
            print(f"      DEBE:  {mov.cuenta.codigo} {mov.cuenta.nombre[:30]:30} ${mov.debe:>12,.2f} (Tipo: {mov.cuenta.tipo})")
        if mov.haber > 0:
            print(f"      HABER: {mov.cuenta.codigo} {mov.cuenta.nombre[:30]:30} ${mov.haber:>12,.2f} (Tipo: {mov.cuenta.tipo})")

# 8. Rango de fechas de movimientos
print("\n📅 8. RANGO DE FECHAS:")
from django.db.models import Min, Max
fecha_range = Poliza.objects.aggregate(Min('fecha'), Max('fecha'))
print(f"   Fecha más antigua: {fecha_range['fecha__min']}")
print(f"   Fecha más reciente: {fecha_range['fecha__max']}")

print("\n" + "=" * 80)
print("FIN DE AUDITORÍA")
print("=" * 80)
