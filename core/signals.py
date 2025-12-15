"""
Signals para automatizar la inicialización de empresas
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Empresa
from core.services.seeder import inicializar_empresa
import logging

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
