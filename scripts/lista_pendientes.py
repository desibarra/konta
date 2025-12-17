import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura

print("FACTURAS PENDIENTES - LISTA SIMPLE")
print("=" * 80)

pendientes = Factura.objects.filter(estado_contable='PENDIENTE').order_by('naturaleza')

print(f"Total: {pendientes.count()}\n")

for i, f in enumerate(pendientes, 1):
    print(f"{i:2}. Naturaleza: {f.naturaleza} | Emisor: {f.emisor_nombre[:40]:40} | Total: ${f.total:>10,.2f}")

print("\n" + "=" * 80)

# Contar por naturaleza
ingresos = pendientes.filter(naturaleza='I').count()
egresos = pendientes.filter(naturaleza='E').count()
control = pendientes.filter(naturaleza='C').count()

print(f"Ingresos (I): {ingresos}")
print(f"Egresos (E): {egresos}")
print(f"Control (C): {control}")
