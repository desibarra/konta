"""
Paso 3: Reclasificar Gastos Existentes

Este script reclasifica todos los gastos que están en "Gastos en General (Default)"
a sus cuentas específicas basándose en el concepto del XML.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Empresa, CuentaContable, MovimientoPoliza, Poliza
from core.utils.clasificador_gastos import clasificar_gasto_por_concepto
from django.db import transaction

print("=" * 80)
print("RECLASIFICACIÓN DE GASTOS EXISTENTES")
print("=" * 80)

empresa = Empresa.objects.first()

# Buscar cuenta 601-01 (que actualmente tiene todos los gastos)
try:
    cuenta_default = CuentaContable.objects.get(
        empresa=empresa,
        codigo='601-01'
    )
except CuentaContable.DoesNotExist:
    print("\n❌ No se encontró cuenta 601-01")
    print("\nBuscando otras cuentas de gastos...")
    
    # Buscar cualquier cuenta 60X con movimientos
    cuentas_gasto = CuentaContable.objects.filter(
        empresa=empresa,
        codigo__startswith='60'
    )
    
    for c in cuentas_gasto:
        num_movs = MovimientoPoliza.objects.filter(cuenta=c).count()
        if num_movs > 0:
            print(f"   {c.codigo} - {c.nombre}: {num_movs} movimientos")
    
    exit()

print(f"\n📊 Cuenta a reclasificar: {cuenta_default.codigo} - {cuenta_default.nombre}")

# Buscar todos los movimientos en esta cuenta
movimientos = MovimientoPoliza.objects.filter(
    cuenta=cuenta_default
).select_related('poliza__factura')

print(f"   Total de movimientos: {movimientos.count()}")

if movimientos.count() == 0:
    print("\n✅ No hay movimientos para reclasificar")
    exit()

# Clasificar cada movimiento
reclasificaciones = {}

for mov in movimientos:
    if not mov.poliza or not mov.poliza.factura:
        continue
    
    factura = mov.poliza.factura
    
    # Obtener concepto
    concepto = getattr(factura, 'concepto', '') or mov.descripcion or ""
    
    # Clasificar
    codigo_nuevo = clasificar_gasto_por_concepto(
        concepto=concepto,
        emisor_rfc=factura.emisor_rfc
    )
    
    if codigo_nuevo not in reclasificaciones:
        reclasificaciones[codigo_nuevo] = []
    
    reclasificaciones[codigo_nuevo].append({
        'movimiento': mov,
        'concepto': concepto[:50],
        'monto': mov.debe if mov.debe > 0 else mov.haber
    })

# Mostrar resumen
print(f"\n{'='*80}")
print("RESUMEN DE RECLASIFICACIÓN:")
print(f"{'='*80}")

for codigo, movs in sorted(reclasificaciones.items()):
    total = sum(m['monto'] for m in movs)
    print(f"\n{codigo}: {len(movs)} movimientos - Total: ${total:,.2f}")
    
    # Mostrar top 3 conceptos
    for i, m in enumerate(movs[:3], 1):
        print(f"   {i}. {m['concepto'][:60]} - ${m['monto']:,.2f}")
    
    if len(movs) > 3:
        print(f"   ... y {len(movs) - 3} más")

print(f"\n{'='*80}")
print(f"¿Ejecutar reclasificación? (s/n): ", end='')
respuesta = input().strip().lower()

if respuesta != 's':
    print("\n❌ Reclasificación cancelada")
    exit()

# Ejecutar reclasificación
print(f"\n{'='*80}")
print("EJECUTANDO RECLASIFICACIÓN...")
print(f"{'='*80}")

reclasificados = 0
errores = 0

with transaction.atomic():
    for codigo, movs in reclasificaciones.items():
        try:
            # Buscar cuenta destino
            cuenta_destino = CuentaContable.objects.get(
                empresa=empresa,
                codigo=codigo
            )
            
            # Reclasificar movimientos
            for m in movs:
                mov = m['movimiento']
                mov.cuenta = cuenta_destino
                mov.save()
                reclasificados += 1
            
            print(f"   ✅ {codigo}: {len(movs)} movimientos → {cuenta_destino.nombre}")
            
        except CuentaContable.DoesNotExist:
            print(f"   ⚠️  {codigo}: Cuenta no existe, se mantienen en default")
            errores += len(movs)
        except Exception as e:
            print(f"   ❌ {codigo}: Error - {str(e)}")
            errores += len(movs)

print(f"\n{'='*80}")
print("RESUMEN:")
print(f"   Reclasificados: {reclasificados}")
print(f"   Errores: {errores}")
print(f"{'='*80}")

if reclasificados > 0:
    print(f"\n✅ Reclasificación completada")
    print(f"\n💡 Ahora genera el Estado de Resultados para ver los gastos desglosados")
else:
    print(f"\n⚠️  No se reclasificó ningún movimiento")
