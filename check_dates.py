import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from django.db.models import Min, Max, Count
from django.db.models.functions import ExtractYear

# Rango de fechas
result = Factura.objects.aggregate(Min('fecha'), Max('fecha'))
print(f'Fecha más antigua: {result["fecha__min"]}')
print(f'Fecha más reciente: {result["fecha__max"]}')

# Facturas por año
print('\nFacturas por año:')
result = Factura.objects.annotate(year=ExtractYear('fecha')).values('year').annotate(count=Count('id')).order_by('year')
for r in result:
    print(f'  {r["year"]}: {r["count"]} facturas')
