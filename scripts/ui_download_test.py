import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
import django
django.setup()

from django.test import Client
from core.models import UsuarioEmpresa
from django.conf import settings

# Ensure testserver is allowed for test client
if 'testserver' not in getattr(settings, 'ALLOWED_HOSTS', []):
    try:
        settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
    except Exception:
        settings.ALLOWED_HOSTS = ['testserver']

# Find a mapping user -> empresa
ue = UsuarioEmpresa.objects.select_related('usuario','empresa').first()
if not ue:
    print('No UsuarioEmpresa entry found; cannot simulate UI download.'); raise SystemExit(1)

user = ue.usuario
empresa = ue.empresa
print('Using user:', user.username, 'empresa:', empresa.nombre)

client = Client()
client.force_login(user)

# Set active_empresa_id in session
s = client.session
s['active_empresa_id'] = empresa.id
s.save()

# Parameters
params = {
    'doc': 'balanza',
    'fmt': 'pdf',
    'fecha_inicio': '2025-12-01',
    'fecha_fin': '2025-12-31',
}

# PDF
r = client.get('/cumplimiento-sat/download/', params)
if r.status_code == 200:
    fn = 'tmp/exports/ui_balanza_test.pdf'
    os.makedirs('tmp/exports', exist_ok=True)
    with open(fn, 'wb') as f:
        if hasattr(r, 'streaming_content'):
            for chunk in r.streaming_content:
                f.write(chunk)
        else:
            f.write(r.content)
    print('WROTE', fn)
else:
    print('PDF request failed:', r.status_code, getattr(r, 'content', b'')[:200])

# XML
params['fmt'] = 'xml'
r = client.get('/cumplimiento-sat/download/', params)
if r.status_code == 200:
    fn = 'tmp/exports/ui_balanza_test.xml'
    with open(fn, 'wb') as f:
        if hasattr(r, 'streaming_content'):
            for chunk in r.streaming_content:
                f.write(chunk)
        else:
            f.write(r.content)
    print('WROTE', fn)
else:
    print('XML request failed:', r.status_code, getattr(r, 'content', b'')[:200])
