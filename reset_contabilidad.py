import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza

print("=" * 70)
print("LIMPIEZA DE PÓLIZAS ANTIGUAS")
print("=" * 70)

# Contar pólizas antes
total_polizas = Poliza.objects.count()
total_facturas_contabilizadas = Factura.objects.filter(estado_contable='CONTABILIZADA').count()

print(f"\nAntes de limpiar:")
print(f"   Pólizas: {total_polizas}")
print(f"   Facturas contabilizadas: {total_facturas_contabilizadas}")

# Eliminar todas las pólizas (esto también elimina MovimientoPoliza por CASCADE)
Poliza.objects.all().delete()

# Resetear estado de facturas a PENDIENTE
Factura.objects.filter(estado_contable='CONTABILIZADA').update(estado_contable='PENDIENTE')

print(f"\nDespués de limpiar:")
print(f"   Pólizas: {Poliza.objects.count()}")
print(f"   Facturas pendientes: {Factura.objects.filter(estado_contable='PENDIENTE').count()}")

print("\n✅ Listo para re-contabilizar con plantillas correctas")
print("=" * 70)
