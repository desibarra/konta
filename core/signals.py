"""
Signals para automatizar la inicialización de empresas
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Empresa
from core.services.seeder import inicializar_empresa
import logging
from django.core.management import call_command
import builtins
import datetime
import subprocess
import sys
from core.models import UsuarioEmpresa
from django.db.models.signals import post_save
from core.models import PlantillaPoliza, CuentaContable

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Empresa)
def auto_inicializar_empresa(sender, instance, created, **kwargs):
    """
    Signal que se ejecuta automáticamente cuando se crea una nueva empresa.
    Inicializa el catálogo de cuentas y plantillas de pólizas.
    
    Args:
        sender: Modelo Empresa
        instance: Instancia de la empresa creada
        created: True si es una nueva empresa, False si es actualización
    """
    if created:
        logger.info(f"🔔 Signal: Nueva empresa creada - {instance.nombre}")
        try:
            inicializar_empresa(instance)
            logger.info(f"✅ Empresa {instance.nombre} inicializada automáticamente")
        except Exception as e:
            logger.error(f"❌ Error al inicializar empresa {instance.nombre}: {e}")
            # No lanzamos la excepción para no bloquear la creación de la empresa
            # El admin puede ejecutar la inicialización manualmente si falla
        # Después de inicializar, intentar reconstruir contabilidad del año actual
        try:
            year = datetime.date.today().year
            logger.info(f"🔁 Ejecutando rebuild contable para el año {year} (signal automático)")
            # Evitar prompt de confirmación en el management command
            saved_input = builtins.input
            builtins.input = lambda prompt=None: 'REBUILD'
            try:
                call_command('rebuild_accounting_2025', year=year)
            finally:
                builtins.input = saved_input

            # Ejecutar validación de XMLs (script externo)
            script_path = os.path.join(getattr(settings, 'BASE_DIR', os.getcwd()), 'scripts', 'validate_xml_accounts.py')
            if os.path.isfile(script_path):
                logger.info('🔎 Ejecutando validación de XMLs (validate_xml_accounts.py)')
                subprocess.run([sys.executable, script_path], check=False)
        except Exception as e:
            logger.error(f"❌ Error en post-inicialización automatizada: {e}")


# Cuando se crea un UsuarioEmpresa, asegurarse de que la empresa esté inicializada
@receiver(post_save, sender=UsuarioEmpresa)
def auto_on_usuario_empresa(sender, instance, created, **kwargs):
    if not created:
        return
    empresa = instance.empresa
    # Si la empresa no tiene plantillas o pocas cuentas, inicializar
    try:
        cuentas_count = CuentaContable.objects.filter(empresa=empresa).count()
        plantillas_count = PlantillaPoliza.objects.filter(empresa=empresa).count()
        if cuentas_count < 5 or plantillas_count == 0:
            logger.info(f"🔔 UsuarioEmpresa creado — inicializando empresa {empresa.nombre} (cuentas: {cuentas_count}, plantillas: {plantillas_count})")
            try:
                inicializar_empresa(empresa)
            except Exception as e:
                logger.error(f"❌ Error inicializando empresa desde UsuarioEmpresa signal: {e}")
        # Opcional: ejecutar rebuild en modo dry-run para verificar
        year = datetime.date.today().year
        saved_input = builtins.input
        builtins.input = lambda prompt=None: 'REBUILD'
        try:
            call_command('rebuild_accounting_2025', year=year, dry_run=True)
        finally:
            builtins.input = saved_input
    except Exception as e:
        logger.error(f"❌ Error en signal UsuarioEmpresa: {e}")
