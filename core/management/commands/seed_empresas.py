"""
Comando de management para inicializar empresas existentes con plantillas contables.
Uso: python manage.py seed_empresas
"""

from django.core.management.base import BaseCommand
from core.models import Empresa
from core.services.seeder import inicializar_empresa


class Command(BaseCommand):
    help = 'Inicializa todas las empresas con catálogo de cuentas y plantillas contables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de empresa específica a inicializar (opcional)',
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        
        if empresa_id:
            # Inicializar empresa específica
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                self.stdout.write(f"Inicializando empresa: {empresa.nombre}")
                inicializar_empresa(empresa)
                self.stdout.write(self.style.SUCCESS(f'✅ Empresa {empresa.nombre} inicializada'))
            except Empresa.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Empresa con ID {empresa_id} no encontrada'))
        else:
            # Inicializar todas las empresas
            empresas = Empresa.objects.all()
            total = empresas.count()
            
            self.stdout.write(f"Inicializando {total} empresa(s)...")
            
            for empresa in empresas:
                try:
                    self.stdout.write(f"  → {empresa.nombre}")
                    inicializar_empresa(empresa)
                    self.stdout.write(self.style.SUCCESS(f'    ✅ OK'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ❌ Error: {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Proceso completado para {total} empresa(s)'))
