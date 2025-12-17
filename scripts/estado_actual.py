import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura

pendientes = Factura.objects.filter(estado_contable='PENDIENTE').count()
contabilizadas = Factura.objects.filter(estado_contable='CONTABILIZADA').count()
total = Factura.objects.count()

print(f"ESTADO ACTUAL:")
print(f"  Pendientes: {pendientes}")
print(f"  Contabilizadas: {contabilizadas}")
print(f"  Total: {total}")
print(f"  Porcentaje contabilizado: {(contabilizadas/total*100):.1f}%")
