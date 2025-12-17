"""
Regeneración Automática de Facturas con Ajustes Incorrectos

Este script:
1. Identifica facturas con ajustes > $1.00
2. Elimina las pólizas incorrectas
3. Regenera las pólizas con el nuevo umbral de $1.00
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable
from core.services.accounting_service import AccountingService
from decimal import Decimal
from django.db import transaction

print("=" * 80)
print("REGENERACIÓN AUTOMÁTICA DE PÓLIZAS CON AJUSTES INCORRECTOS")
print("=" * 80)

# Buscar cuenta 702-99
cuenta_702 = CuentaContable.objects.filter(codigo='702-99').first()

if not cuenta_702:
    print("✅ No existe cuenta 702-99, no hay nada que regenerar")
    exit()

# Encontrar movimientos con ajustes > $1.00
movimientos_ajuste = MovimientoPoliza.objects.filter(cuenta=cuenta_702).select_related('poliza__factura')

facturas_a_regenerar = []

for mov in movimientos_ajuste:
    monto = mov.haber if mov.haber > 0 else mov.debe
    
    if monto > Decimal('1.00'):
        factura = mov.poliza.factura
        if factura and factura not in facturas_a_regenerar:
            facturas_a_regenerar.append({
                'factura': factura,
                'poliza': mov.poliza,
                'ajuste': monto
            })

print(f"\n📊 Facturas a regenerar: {len(facturas_a_regenerar)}")
print(f"   Total en ajustes incorrectos: ${sum(f['ajuste'] for f in facturas_a_regenerar):,.2f}")

if len(facturas_a_regenerar) == 0:
    print("\n✅ No hay facturas para regenerar")
    exit()

# Mostrar top 10
print(f"\n{'='*80}")
print("TOP 10 FACTURAS A REGENERAR:")
print(f"{'='*80}")

facturas_a_regenerar.sort(key=lambda x: x['ajuste'], reverse=True)

for i, item in enumerate(facturas_a_regenerar[:10], 1):
    factura = item['factura']
    print(f"{i}. {factura.uuid} - Ajuste: ${item['ajuste']:,.2f}")

print(f"\n{'='*80}")
print("⚠️  ADVERTENCIA:")
print(f"{'='*80}")
print("Este proceso:")
print("  1. Eliminará las pólizas actuales (con ajustes incorrectos)")
print("  2. Intentará regenerar con el nuevo umbral de $1.00")
print("  3. Si una factura sigue sin cuadrar, quedará como PENDIENTE")
print("\n¿Continuar? (s/n): ", end='')

respuesta = input().strip().lower()

if respuesta != 's':
    print("\n❌ Operación cancelada")
    exit()

# Regenerar
print(f"\n{'='*80}")
print("REGENERANDO PÓLIZAS...")
print(f"{'='*80}")

exitosas = 0
fallidas = 0
errores = []

for item in facturas_a_regenerar:
    factura = item['factura']
    poliza = item['poliza']
    
    try:
        with transaction.atomic():
            # 1. Eliminar póliza actual
            poliza.delete()
            
            # 2. Marcar como pendiente
            factura.estado_contable = 'PENDIENTE'
            factura.save()
            
            # 3. Intentar regenerar
            try:
                AccountingService.contabilizar_factura(factura)
                exitosas += 1
                print(f"   ✅ {str(factura.uuid)[:8]}... - Regenerada exitosamente")
            except ValueError as e:
                # Error de cuadre - esperado para facturas con problemas
                fallidas += 1
                errores.append({
                    'uuid': factura.uuid,
                    'error': str(e)
                })
                print(f"   ⚠️  {str(factura.uuid)[:8]}... - No cuadra (requiere corrección manual)")
            except Exception as e:
                # Otro error
                fallidas += 1
                errores.append({
                    'uuid': factura.uuid,
                    'error': str(e)
                })
                print(f"   ❌ {str(factura.uuid)[:8]}... - Error: {str(e)[:50]}")
                
    except Exception as e:
        print(f"   ❌ {str(factura.uuid)[:8]}... - Error crítico: {str(e)}")
        fallidas += 1

# Resumen
print(f"\n{'='*80}")
print("RESUMEN DE REGENERACIÓN")
print(f"{'='*80}")
print(f"   Total procesadas: {len(facturas_a_regenerar)}")
print(f"   ✅ Exitosas: {exitosas}")
print(f"   ⚠️  Fallidas: {fallidas}")

if fallidas > 0:
    print(f"\n{'='*80}")
    print("FACTURAS QUE REQUIEREN ATENCIÓN MANUAL:")
    print(f"{'='*80}")
    for err in errores[:10]:
        print(f"\n   UUID: {err['uuid']}")
        print(f"   Error: {err['error'][:100]}")

print(f"\n{'='*80}")
print("💡 SIGUIENTE PASO:")
print(f"{'='*80}")
if exitosas > 0:
    print(f"   {exitosas} facturas regeneradas correctamente")
    print(f"   Verifica el saldo de cuenta 702-99 en la Balanza")
if fallidas > 0:
    print(f"   {fallidas} facturas requieren corrección manual:")
    print(f"   - Revisar plantillas contables")
    print(f"   - Verificar datos del XML")
    print(f"   - Usar módulo de edición manual (cuando esté disponible)")
