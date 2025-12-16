import os
from django.conf import settings
import django

django.setup()

from core.services.export_service import ExportService
from core.models import Empresa

os.makedirs('tmp/exports', exist_ok=True)

empresa = Empresa.objects.first()
if not empresa:
    print('No Empresa found; aborting sample export.')
    raise SystemExit(1)

YEAR = 2025
MONTH = 12

# Generate XML
try:
    buf, fn, ct = ExportService.generate_balanza_xml(empresa, YEAR, MONTH)
    path = os.path.join('tmp/exports', fn)
    with open(path, 'wb') as f:
        f.write(buf.getvalue())
    print('WROTE', path)
except Exception as e:
    print('ERROR generating XML:', e)

# Generate XLSX
try:
    buf, fn, ct = ExportService.generate_balanza_excel(empresa, YEAR, MONTH)
    path = os.path.join('tmp/exports', fn)
    with open(path, 'wb') as f:
        f.write(buf.getvalue())
    print('WROTE', path)
except Exception as e:
    print('ERROR generating XLSX:', e)

# Generate PDF (may fallback to HTML bytes)
try:
    buf, fn, ct = ExportService.generate_balanza_pdf(empresa, YEAR, MONTH)
    path = os.path.join('tmp/exports', fn)
    with open(path, 'wb') as f:
        f.write(buf.getvalue())
    print('WROTE', path)
except Exception as e:
    print('ERROR generating PDF:', e)
