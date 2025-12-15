from django.contrib.auth.models import User
from core.models import UsuarioEmpresa
from django.test import Client

# Crear cliente de test
client = Client()

# Login
user = User.objects.first()
client.force_login(user)

# Obtener primera empresa
empresa_rel = UsuarioEmpresa.objects.filter(usuario=user).first()
print(f'\n=== TEST DE DROPDOWN ===')
print(f'Usuario: {user.username}')
print(f'Empresa: {empresa_rel.empresa.nombre} (ID: {empresa_rel.empresa.id})')

# Simular click en dropdown
print(f'\n1. Simulando click en dropdown...')
response = client.get(f'/switch-empresa/{empresa_rel.empresa.id}/')
print(f'   Status: {response.status_code}')
if response.status_code == 302:
    print(f'   Redirect a: {response.url}')

# Verificar sesión
print(f'\n2. Verificando sesión...')
session = client.session
print(f'   active_empresa_id: {session.get("active_empresa_id")}')
print(f'   active_empresa_nombre: {session.get("active_empresa_nombre")}')

# Intentar acceder a upload
print(f'\n3. Intentando acceder a /upload/...')
response2 = client.get('/upload/')
print(f'   Status: {response2.status_code}')
if response2.status_code == 302:
    print(f'   ❌ REDIRIGE A: {response2.url}')
    print(f'   PROBLEMA: Sesión no persiste')
else:
    print(f'   ✅ OK - Página de upload cargada')

print(f'\n=== FIN TEST ===\n')
