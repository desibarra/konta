# Konta - Sistema de Contabilidad Fiscal Personal (Multi-Empresa)

Applicación profesional en Django para tu contabilidad fiscal en México. Soporte Multi-RFC y CFDI 4.0.

## Requisitos
- Python 3.10 o superior
- **SQLite** (por defecto) o PostgreSQL (opcional)

## Instalación desde Cero

### 1. Preparar Entorno
```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
.\venv\Scripts\activate

# Instalar librerías
pip install -r requirements.txt
```

### 2. Configurar Base de Datos
Por defecto usa SQLite. Si deseas reiniciar la BD:
```bash
del db.sqlite3  # Windows
rm db.sqlite3   # Mac/Linux
```

### 3. Inicializar el Sistema y Migraciones
```bash
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
```

### 4. Arrancar Servidor
```bash
python manage.py runserver
```

---

## Pasos exactos para probar la versión multi-empresa

1. **Crear tu Primera Empresa**:
   - Entra al panel de administración: `http://127.0.0.1:8000/admin/`
   - Ve a **Empresas** > Agrega una nueva (Ej: "Mi Negocio S.A. de C.V.").
   - **MAGIA**: Al guardar, el sistema creará automáticamente las 7 cuentas contables básicas para esa empresa.

2. **Verificar Cuentas**:
   - En el Admin, ve a **Cuentas Contables**. Deberías ver las cuentas creadas asociadas a la empresa que acabas de registrar.

3. **Subir XML**:
   - Ve al sitio principal: `http://127.0.0.1:8000/`
   - Ve a "Subir XML".
   - Selecciona la **Empresa** en el dropdown.
   - Sube un XML. Si intentas subirlo sin seleccionar empresa, el sistema te avisará.

4. **Filtrar en Dashboard**:
   - En el Dashboard, usa el filtro superior para ver solo las facturas de una empresa específica.

## Estructura del Proyecto

```text
konta/                  # Configuración (settings, urls)
core/                   # App principal
    models.py           # Modelos (Empresa, Factura, etc)
    signals.py          # Automatización (Cuentas al crear Empresa)
    services/           # Lógica de XML
    views.py            # Vistas
    forms.py            # Formularios
templates/              # UI Global
```