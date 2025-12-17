"""
PASO 1: Análisis y Reclasificación de Ajustes Incorrectos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable
from decimal import Decimal

print("=" * 80)
print("ANÁLISIS DE AJUSTES INCORRECTOS EN CUENTA 702-99")
print("=" * 80)

# Buscar todas las pólizas con ajustes > $1.00
try:
    cuenta_702 = CuentaContable.objects.filter(codigo='702-99').first()
except:
    cuenta_702 = None

if not cuenta_702:
    print("✅ No existe cuenta 702-99")
    exit()

movimientos_ajuste = MovimientoPoliza.objects.filter(cuenta=cuenta_702).select_related('poliza__factura')

print(f"\nTotal de movimientos en 702-99: {movimientos_ajuste.count()}")

# Clasificar por tamaño
ajustes_grandes = []
ajustes_normales = []

for mov in movimientos_ajuste:
    monto = mov.haber if mov.haber > 0 else mov.debe
    
    if monto > Decimal('1.00'):
        try:
            ajustes_grandes.append({
                'movimiento': mov,
                'poliza': mov.poliza,
                'factura': mov.poliza.factura if mov.poliza else None,
                'monto': monto,
                'tipo': 'haber' if mov.haber > 0 else 'debe'
            })
        except:
            pass
    else:
        ajustes_normales.append(monto)

print(f"\n📊 CLASIFICACIÓN:")
print(f"   Ajustes NORMALES (≤ $1.00): {len(ajustes_normales)} - Total: ${sum(ajustes_normales):,.2f}")
print(f"   Ajustes INCORRECTOS (> $1.00): {len(ajustes_grandes)} - Total: ${sum(a['monto'] for a in ajustes_grandes):,.2f}")

if len(ajustes_grandes) == 0:
    print("\n✅ No hay ajustes incorrectos para reclasificar")
    exit()

# Mostrar top 10
print(f"\n{'='*80}")
print("TOP 10 AJUSTES MÁS GRANDES")
print(f"{'='*80}")

ajustes_grandes.sort(key=lambda x: x['monto'], reverse=True)

for i, ajuste in enumerate(ajustes_grandes[:10], 1):
    factura = ajuste['factura']
    if factura:
        folio = getattr(factura, 'folio', 'N/A')
        print(f"\n{i}. UUID: {factura.uuid}")
        print(f"   Folio: {folio}")
        print(f"   Ajuste: ${ajuste['monto']:,.2f}")
        print(f"   Naturaleza: {factura.naturaleza}")

print(f"\n{'='*80}")
print("RECOMENDACIÓN:")
print(f"{'='*80}")
print(f"\nEstos ajustes son demasiado grandes para ser redondeos.")
print(f"Opciones:")
print(f"  1. Regenerar las pólizas con plantillas corregidas")
print(f"  2. Eliminar los XMLs y volver a contabilizar")
print(f"  3. Editar manualmente cada póliza (requiere módulo de edición)")
print(f"\n💡 Con el nuevo umbral de $1.00, estas facturas ya NO se contabilizarán")
print(f"   automáticamente hasta que se corrijan las plantillas.")
