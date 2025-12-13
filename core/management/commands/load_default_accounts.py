from django.core.management.base import BaseCommand
from core.models import CuentaContable, Empresa

class Command(BaseCommand):
    help = 'Carga el catálogo de cuentas básicas para todas las empresas existentes'

    def handle(self, *args, **kwargs):
        cuentas_base = [
            {'codigo': '102', 'nombre': 'Bancos', 'es_deudora': True},
            {'codigo': '105', 'nombre': 'Clientes', 'es_deudora': True},
            {'codigo': '118', 'nombre': 'IVA pendiente de pago', 'es_deudora': True},
            {'codigo': '201', 'nombre': 'Proveedores', 'es_deudora': False},
            {'codigo': '209', 'nombre': 'IVA por cobrar', 'es_deudora': False},
            {'codigo': '401', 'nombre': 'Ventas / Ingresos', 'es_deudora': False},
            {'codigo': '600', 'nombre': 'Gastos generales', 'es_deudora': True},
        ]
        
        empresas = Empresa.objects.all()
        if not empresas.exists():
            self.stdout.write(self.style.WARNING("No hay empresas registradas. Creando una empresa por defecto..."))
            Empresa.objects.create(nombre="Mi Empresa Default", rfc="XAXX010101000", regimen_fiscal="General")
            empresas = Empresa.objects.all()

        total_creadas = 0
        for empresa in empresas:
            self.stdout.write(f"Procesando empresa: {empresa}")
            for c in cuentas_base:
                obj, created = CuentaContable.objects.get_or_create(
                    empresa=empresa,
                    codigo=c['codigo'],
                    defaults={'nombre': c['nombre'], 'es_deudora': c['es_deudora']}
                )
                if created:
                    total_creadas += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Operación finalizada. Se crearon {total_creadas} cuentas nuevas."))
