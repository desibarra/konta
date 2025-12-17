import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura

print("ESTADO ACTUAL DEL SISTEMA")
print("=" * 60)

pendientes = Factura.objects.filter(estado_contable='PENDIENTE')
print(f"Facturas PENDIENTES: {pendientes.count()}")
print(f"Facturas CONTABILIZADAS: {Factura.objects.filter(estado_contable='CONTABILIZADA').count()}")

print("\nPRIMERAS 10 FACTURAS PENDIENTES:")
for f in pendientes[:10]:
    print(f"  - {str(f.uuid)[:8]} | {f.emisor_nombre[:35]:35} | ${f.total:>10,.2f} | {f.naturaleza}")
