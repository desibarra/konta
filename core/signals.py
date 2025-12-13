from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Empresa, CuentaContable

@receiver(post_save, sender=Empresa)
def crear_cuentas_basicas(sender, instance, created, **kwargs):
    """
    Crea automáticamente las cuentas contables básicas cuando se crea una nueva Empresa.
    """
    if created:
        cuentas_base = [
            {'codigo': '102', 'nombre': 'Bancos', 'es_deudora': True},
            {'codigo': '105', 'nombre': 'Clientes', 'es_deudora': True},
            {'codigo': '118', 'nombre': 'IVA pendiente de pago', 'es_deudora': True},
            {'codigo': '201', 'nombre': 'Proveedores', 'es_deudora': False},
            {'codigo': '209', 'nombre': 'IVA por cobrar', 'es_deudora': False},
            {'codigo': '401', 'nombre': 'Ventas / Ingresos', 'es_deudora': False},
            {'codigo': '600', 'nombre': 'Gastos generales', 'es_deudora': True},
        ]
        
        print(f"✨ Generando cuentas contables automáticas para: {instance.nombre}")
        
        for c in cuentas_base:
            CuentaContable.objects.get_or_create(
                empresa=instance,
                codigo=c['codigo'],
                defaults={'nombre': c['nombre'], 'es_deudora': c['es_deudora']}
            )
