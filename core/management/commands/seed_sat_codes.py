from django.core.management.base import BaseCommand

# Minimal sample of SAT agrupadores (real catalog is extensive)
SAMPLE_CODES = [
    ('101.01', 'Caja'),
    ('101.02', 'Bancos'),
    ('102.01', 'Clientes'),
    ('119.01', 'IVA Acreditable'),
    ('119.02', 'Impuestos a favor (Retenciones)'),
    ('401.01', 'Ventas y/o Servicios'),
    ('402.01', 'Devoluciones, descuentos o rebajas sobre ventas'),
    ('501.01', 'Costo de Ventas'),
    ('502.01', 'Descuentos sobre Compras'),
    ('213.01', 'Impuestos retenidos por pagar'),
]


class Command(BaseCommand):
    help = 'Seed a minimal SAT Codigo catalog into core.SatCodigo'

    def handle(self, *args, **options):
        from core.models import SatCodigo
        created = 0
        updated = 0
        for code, name in SAMPLE_CODES:
            obj, was_created = SatCodigo.objects.update_or_create(
                codigo=code,
                defaults={'nombre': name}
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f'Created: {created} | Updated: {updated} SAT codes')
