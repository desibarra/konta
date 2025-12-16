# Generated manually on 2025-12-15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_add_sat_subcuentas_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='factura',
            name='uso_cfdi',
            field=models.CharField(
                blank=True,
                default='G03',
                help_text='Código de Uso de CFDI del SAT (G01, G03, I04, etc.)',
                max_length=4,
                null=True
            ),
        ),
    ]
