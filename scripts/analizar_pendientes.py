import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, PlantillaPoliza
from core.services.accounting_service import AccountingService
from django.contrib.auth.models import User
from decimal import Decimal

print("ANALISIS DE 25 FACTURAS PENDIENTES")
print("=" * 80)

pendientes = Factura.objects.filter(estado_contable='PENDIENTE').order_by('naturaleza', 'fecha')
plantilla = PlantillaPoliza.objects.first()
usuario = User.objects.first()

print(f"Total: {pendientes.count()}")
print(f"Plantilla: {plantilla.nombre if plantilla else 'N/A'}\n")

# Analizar cada una
errores_por_tipo = {}

for f in pendientes:
    try:
        # Intentar contabilizar para ver el error
        AccountingService.contabilizar_factura(f, plantilla, usuario)
    except Exception as e:
        error_msg = str(e)
        
        # Clasificar error
        if "no cuadra" in error_msg.lower():
            tipo = "NO_CUADRA"
        elif "cuenta" in error_msg.lower():
            tipo = "CUENTA_FALTANTE"
        elif "plantilla" in error_msg.lower():
            tipo = "PLANTILLA"
        else:
            tipo = "OTRO"
        
        if tipo not in errores_por_tipo:
            errores_por_tipo[tipo] = []
        
        errores_por_tipo[tipo].append({
            'uuid': str(f.uuid)[:8],
            'emisor': f.emisor_nombre[:35],
            'naturaleza': f.naturaleza,
            'total': float(f.total),
            'error': error_msg[:100]
        })

# Mostrar resumen
print("RESUMEN POR TIPO DE ERROR:")
print("-" * 80)
for tipo, errores in errores_por_tipo.items():
    print(f"\n{tipo}: {len(errores)} facturas")
    for err in errores[:3]:  # Mostrar solo 3 ejemplos
        print(f"  - {err['uuid']} | {err['emisor']:35} | {err['naturaleza']} | ${err['total']:>10,.2f}")
        print(f"    Error: {err['error']}")

print("\n" + "=" * 80)
print("PLAN DE ACCION:")
print("-" * 80)

if "NO_CUADRA" in errores_por_tipo:
    print(f"1. Corregir {len(errores_por_tipo['NO_CUADRA'])} facturas que no cuadran")
    print("   Accion: Agregar diferencia a retenciones")

if "CUENTA_FALTANTE" in errores_por_tipo:
    print(f"2. Crear cuentas faltantes para {len(errores_por_tipo['CUENTA_FALTANTE'])} facturas")
    print("   Accion: Crear cuenta generica 'Gastos por Identificar'")

if "PLANTILLA" in errores_por_tipo:
    print(f"3. Revisar plantilla para {len(errores_por_tipo['PLANTILLA'])} facturas")

if "OTRO" in errores_por_tipo:
    print(f"4. Revisar manualmente {len(errores_por_tipo['OTRO'])} facturas con errores diversos")

print("=" * 80)
