import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','konta.settings')
import django
django.setup()
from core.services.export_service import ExportService, _WEASYPRINT_AVAILABLE, _XHTML2PDF_AVAILABLE, _LXML_AVAILABLE
print('WEASYPRINT_AVAILABLE=', _WEASYPRINT_AVAILABLE)
print('XHTML2PDF_AVAILABLE=', _XHTML2PDF_AVAILABLE)
print('LXML_AVAILABLE=', _LXML_AVAILABLE)
from core.models import Empresa
empresa = Empresa.objects.first()
if not empresa:
    print('No empresa')
    raise SystemExit(1)
try:
    bio, fn, ct = ExportService.generate_balanza_pdf(empresa, 2025, 12)
    path = os.path.join('tmp/exports', fn)
    with open(path, 'wb') as f:
        f.write(bio.getvalue())
    print('WROTE', path)
except Exception as e:
    print('ERR', e)
