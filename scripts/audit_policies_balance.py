import os
import sys

# Agregar el directorio raíz del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')

import django
django.setup()

import logging
from decimal import Decimal
from django.db.models import Sum
from core.models import Poliza, MovimientoPoliza

def audit_policies_balance():
    """
    Audita todas las pólizas en la base de datos para verificar que cumplan
    con la regla de partida doble (Debe = Haber).
    """
    logger = logging.getLogger("audit_policies_balance")
    logger.info("Iniciando auditoría de pólizas...")

    desbalanceadas = []

    for poliza in Poliza.objects.all():
        total_debe = MovimientoPoliza.objects.filter(poliza=poliza).aggregate(debe_sum=Sum('debe'))['debe_sum'] or Decimal('0.00')
        total_haber = MovimientoPoliza.objects.filter(poliza=poliza).aggregate(haber_sum=Sum('haber'))['haber_sum'] or Decimal('0.00')

        if total_debe != total_haber:
            desbalanceadas.append({
                'poliza_id': poliza.id,
                'factura_uuid': poliza.factura.uuid,
                'total_debe': total_debe,
                'total_haber': total_haber
            })
            logger.error(f"Póliza desbalanceada: ID={poliza.id}, Factura={poliza.factura.uuid}, Debe={total_debe}, Haber={total_haber}")

    logger.info(f"Auditoría completada. Total de pólizas desbalanceadas: {len(desbalanceadas)}")

    return desbalanceadas

if __name__ == "__main__":
    desbalanceadas = audit_policies_balance()
    if desbalanceadas:
        print("Pólizas desbalanceadas encontradas:")
        for item in desbalanceadas:
            print(item)
    else:
        print("Todas las pólizas están balanceadas.")