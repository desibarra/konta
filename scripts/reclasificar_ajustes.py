"""
PASO 1: Análisis y Reclasificación de Ajustes Incorrectos

Este script:
1. Identifica todas las pólizas con ajustes > $1.00
2. Analiza cada factura para determinar dónde debería ir el monto
3. Genera un reporte de reclasificación propuesta
4. Opcionalmente ejecuta la reclasificación
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable
from decimal import Decimal
from django.db.models import Sum

print("=" * 80)
print("ANÁLISIS DE AJUSTES INCORRECTOS EN CUENTA 702-99")
print("=" * 80)

# Buscar todas las pólizas con ajustes > $1.00
cuenta_702 = CuentaContable.objects.filter(codigo='702-99').first()

if not cuenta_702:
    print("✅ No existe cuenta 702-99")
    exit()

movimientos_ajuste = MovimientoPoliza.objects.filter(cuenta=cuenta_702).select_related('poliza__factura')

print(f"\nTotal de movimientos en 702-99: {movimientos_ajuste.count()}")

# Clasificar por tamaño
ajustes_grandes = []  # > $1.00
ajustes_normales = []  # <= $1.00

for mov in movimientos_ajuste:
    monto = mov.haber if mov.haber > 0 else mov.debe
    
    if monto > Decimal('1.00'):
        ajustes_grandes.append({
            'movimiento': mov,
            'poliza': mov.poliza,
            'factura': mov.poliza.factura,
            'monto': monto,
            'tipo': 'haber' if mov.haber > 0 else 'debe'
        })
    else:
        ajustes_normales.append({
            'movimiento': mov,
            'monto': monto
        })

print(f"\n📊 CLASIFICACIÓN:")
print(f"   Ajustes NORMALES (≤ $1.00): {len(ajustes_normales)}")
print(f"   Ajustes INCORRECTOS (> $1.00): {len(ajustes_grandes)}")

if len(ajustes_grandes) == 0:
    print("\n✅ No hay ajustes incorrectos para reclasificar")
    exit()

# Analizar cada ajuste grande
print(f"\n{'='*80}")
print("ANÁLISIS DE AJUSTES INCORRECTOS")
print(f"{'='*80}")

reclasificaciones = []

for i, ajuste in enumerate(ajustes_grandes, 1):
    factura = ajuste['factura']
    poliza = ajuste['poliza']
    monto = ajuste['monto']
    
    print(f"\n{i}. UUID: {factura.uuid}")
    print(f"   Folio: {factura.folio}")
    print(f"   Ajuste: ${monto:,.2f}")
    print(f"   Naturaleza: {factura.naturaleza}")
    
    # Analizar todos los movimientos de la póliza
    movs = MovimientoPoliza.objects.filter(poliza=poliza).exclude(cuenta__codigo='702-99')
    
    print(f"\n   Movimientos actuales:")
    for m in movs:
        print(f"      {m.cuenta.codigo:15s} D:${m.debe:>12,.2f} H:${m.haber:>12,.2f} - {m.cuenta.nombre[:40]}")
    
    # Determinar cuenta correcta según naturaleza y montos
    cuenta_sugerida = None
    razon = ""
    
    # Calcular totales
    total_debe_sin_ajuste = sum(m.debe for m in movs)
    total_haber_sin_ajuste = sum(m.haber for m in movs)
    
    # Buscar qué falta
    if factura.naturaleza == 'I':  # Ingreso
        # Debe: Clientes (total)
        # Haber: Ingresos (subtotal) + IVA Trasladado
        
        esperado_debe = factura.total
        esperado_haber = factura.subtotal + factura.total_impuestos_trasladados
        
        error_debe = abs(total_debe_sin_ajuste - esperado_debe)
        error_haber = abs(total_haber_sin_ajuste - esperado_haber)
        
        if error_haber > 1:
            # Falta en haber, probablemente IVA o Ingreso
            if abs(error_haber - factura.total_impuestos_trasladados) < 1:
                cuenta_sugerida = '118'  # IVA Trasladado
                razon = "Falta IVA Trasladado"
            else:
                cuenta_sugerida = '401'  # Ingresos
                razon = "Falta Ingreso"
                
    else:  # Egreso
        # Debe: Gasto + IVA Trasladado - IVA Retenido
        # Haber: Proveedores (total)
        
        esperado_debe = factura.subtotal + factura.total_impuestos_trasladados - factura.total_impuestos_retenidos
        esperado_haber = factura.total
        
        error_debe = abs(total_debe_sin_ajuste - esperado_debe)
        error_haber = abs(total_haber_sin_ajuste - esperado_haber)
        
        if error_debe > 1:
            # Falta en debe
            if abs(error_debe - factura.total_impuestos_trasladados) < 1:
                cuenta_sugerida = '119'  # IVA Acreditable
                razon = "Falta IVA Acreditable"
            elif abs(error_debe - factura.subtotal) < 1:
                cuenta_sugerida = '601'  # Gastos
                razon = "Falta Gasto"
        elif error_haber > 1:
            # Falta en haber
            cuenta_sugerida = '201'  # Proveedores
            razon = "Falta Proveedor"
    
    print(f"\n   💡 SUGERENCIA:")
    if cuenta_sugerida:
        print(f"      Mover ${monto:,.2f} a cuenta {cuenta_sugerida}")
        print(f"      Razón: {razon}")
        
        reclasificaciones.append({
            'uuid': factura.uuid,
            'folio': factura.folio,
            'monto': monto,
            'cuenta_origen': '702-99',
            'cuenta_destino': cuenta_sugerida,
            'razon': razon,
            'movimiento': ajuste['movimiento'],
            'tipo': ajuste['tipo']
        })
    else:
        print(f"      ⚠️ No se pudo determinar cuenta automáticamente")
        print(f"      Requiere revisión manual")

# Resumen
print(f"\n{'='*80}")
print(f"RESUMEN DE RECLASIFICACIÓN")
print(f"{'='*80}")
print(f"\nTotal a reclasificar: {len(reclasificaciones)} movimientos")
print(f"Monto total: ${sum(r['monto'] for r in reclasificaciones):,.2f}")

print(f"\n¿Ejecutar reclasificación? (s/n): ", end='')
respuesta = input().strip().lower()

if respuesta == 's':
    from django.db import transaction
    
    print(f"\nEjecutando reclasificación...")
    
    with transaction.atomic():
        for r in reclasificaciones:
            mov = r['movimiento']
            cuenta_destino = CuentaContable.objects.get(
                empresa=mov.poliza.factura.empresa,
                codigo=r['cuenta_destino']
            )
            
            # Cambiar cuenta del movimiento
            mov.cuenta = cuenta_destino
            mov.descripcion = f"{mov.descripcion} (Reclasificado de 702-99)"
            mov.save()
            
            print(f"   ✅ {r['folio']}: ${r['monto']:,.2f} → {r['cuenta_destino']}")
    
    print(f"\n✅ Reclasificación completada")
else:
    print(f"\n❌ Reclasificación cancelada")

print(f"\n{'='*80}")
