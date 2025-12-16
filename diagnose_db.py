import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Poliza, MovimientoPoliza, Factura

print("DIAGNÓSTICO DE BASE DE DATOS")
print("=" * 70)

# Verificar pólizas
polizas_2025 = Poliza.objects.filter(fecha__year=2025).count()
print(f"\nPólizas 2025: {polizas_2025}")

# Verificar movimientos
movimientos_2025 = MovimientoPoliza.objects.filter(poliza__fecha__year=2025).count()
print(f"Movimientos 2025: {movimientos_2025}")

# Verificar facturas
facturas_total = Factura.objects.filter(fecha__year=2025).count()
facturas_ingresos = Factura.objects.filter(fecha__year=2025, naturaleza='I').count()
facturas_egresos = Factura.objects.filter(fecha__year=2025, naturaleza='E').count()

print(f"\nFacturas 2025 Total: {facturas_total}")
print(f"Facturas Ingresos: {facturas_ingresos}")
print(f"Facturas Egresos: {facturas_egresos}")

# Verificar estados
pendientes = Factura.objects.filter(fecha__year=2025, estado_contable='PENDIENTE').count()
contabilizadas = Factura.objects.filter(fecha__year=2025, estado_contable='CONTABILIZADA').count()
excluidas = Factura.objects.filter(fecha__year=2025, estado_contable='EXCLUIDA').count()

print(f"\nEstados:")
print(f"  PENDIENTE: {pendientes}")
print(f"  CONTABILIZADA: {contabilizadas}")
print(f"  EXCLUIDA: {excluidas}")

# Si hay pólizas, mostrar algunas
if polizas_2025 > 0:
    print(f"\nPrimeras 5 pólizas:")
    for p in Poliza.objects.filter(fecha__year=2025)[:5]:
        movs = p.movimientos.count()
        print(f"  Póliza #{p.id}: {p.fecha} - {movs} movimientos")
else:
    print("\n❌ NO HAY PÓLIZAS EN 2025")
    print("\nPROBLEMA: Las facturas no se están contabilizando")
