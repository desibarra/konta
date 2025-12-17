"""
Script para contabilizar TODAS las facturas pendientes de forma masiva
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, PlantillaPoliza
from core.services.accounting_service import AccountingService
from django.contrib.auth.models import User

print("CONTABILIZACION MASIVA DE FACTURAS")
print("=" * 80)

# Obtener facturas pendientes
facturas_pendientes = Factura.objects.filter(estado_contable='PENDIENTE').order_by('fecha')
total = facturas_pendientes.count()

print(f"Total facturas pendientes: {total}\n")

if total == 0:
    print("✅ No hay facturas pendientes para contabilizar")
    exit(0)

# Obtener plantilla por defecto
plantilla = PlantillaPoliza.objects.first()
if not plantilla:
    print("❌ No hay plantillas de póliza configuradas")
    exit(1)

print(f"Usando plantilla: {plantilla.nombre}\n")

# Obtener usuario admin
usuario = User.objects.filter(is_superuser=True).first()
if not usuario:
    usuario = User.objects.first()  # Usar cualquier usuario si no hay admin

if not usuario:
    print("❌ No hay usuarios en el sistema")
    exit(1)

exitosas = 0
fallidas = 0
errores = []

for i, factura in enumerate(facturas_pendientes, 1):
    try:
        print(f"[{i}/{total}] Contabilizando {factura.uuid[:8]}... ", end='')
        
        # Contabilizar
        poliza = AccountingService.contabilizar_factura(
            factura=factura,
            plantilla=plantilla,
            usuario=usuario
        )
        
        print(f"✅ OK (Póliza #{poliza.id})")
        exitosas += 1
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERROR: {error_msg[:60]}")
        fallidas += 1
        errores.append({
            'uuid': str(factura.uuid),
            'emisor': factura.emisor_nombre[:40],
            'error': error_msg[:100]
        })

print("\n" + "=" * 80)
print(f"RESUMEN:")
print(f"  Total procesadas:  {total}")
print(f"  Exitosas:          {exitosas}")
print(f"  Fallidas:          {fallidas}")

if errores:
    print(f"\nERRORES DETALLADOS:")
    for err in errores[:10]:  # Mostrar solo los primeros 10
        print(f"\n  UUID: {err['uuid']}")
        print(f"  Emisor: {err['emisor']}")
        print(f"  Error: {err['error']}")

print("\n" + "=" * 80)
print("PROCESO COMPLETADO")
print("=" * 80)
