"""
Script para contabilizar TODAS las facturas pendientes
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, PlantillaPoliza
from core.services.accounting_service import AccountingService
from django.contrib.auth.models import User

print("CONTABILIZACION MASIVA")
print("=" * 80)

facturas = Factura.objects.filter(estado_contable='PENDIENTE').order_by('fecha')
total = facturas.count()

print(f"Total pendientes: {total}")

if total == 0:
    print("No hay facturas pendientes")
    exit(0)

plantilla = PlantillaPoliza.objects.first()
if not plantilla:
    print("ERROR: No hay plantillas")
    exit(1)

print(f"Plantilla: {plantilla.nombre}")

usuario = User.objects.filter(is_superuser=True).first()
if not usuario:
    usuario = User.objects.first()

exitosas = 0
fallidas = 0
errores = []

for i, factura in enumerate(facturas, 1):
    try:
        uuid_str = str(factura.uuid)
        print(f"[{i}/{total}] {uuid_str[:8]}... ", end='')
        
        poliza = AccountingService.contabilizar_factura(
            factura=factura,
            plantilla=plantilla,
            usuario=usuario
        )
        
        print(f"OK")
        exitosas += 1
        
    except Exception as e:
        print(f"ERROR: {str(e)[:50]}")
        fallidas += 1
        errores.append({
            'uuid': str(factura.uuid),
            'error': str(e)[:80]
        })

print("\n" + "=" * 80)
print(f"RESUMEN:")
print(f"  Exitosas: {exitosas}")
print(f"  Fallidas: {fallidas}")

if errores:
    print(f"\nPrimeros errores:")
    for err in errores[:5]:
        print(f"  {err['uuid'][:8]}: {err['error']}")

print("=" * 80)
