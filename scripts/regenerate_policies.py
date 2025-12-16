import os
import django
import sys

# 1. Añadir el directorio raíz del proyecto al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')

# 3. Inicializar las aplicaciones de Django
django.setup()

from core.models import Poliza
from core.services.accounting_service import AccountingService

def regenerate_policies():
    desbalanceadas = [p for p in Poliza.objects.all() if abs(p.total_debe - p.total_haber) > 0.01]
    print(f"Regenerando {len(desbalanceadas)} pólizas desbalanceadas...")

    for poliza in desbalanceadas:
        try:
            # Eliminar póliza desbalanceada
            poliza.delete()
            print(f"Póliza {poliza.id} eliminada.")

            # Verificar si la factura ya está contabilizada
            if hasattr(poliza.factura, 'poliza'):
                print(f"Factura {poliza.factura.uuid} ya está contabilizada. Omitiendo.")
                continue

            # Regenerar póliza
            nueva_poliza = AccountingService.contabilizar_factura(poliza.factura.uuid)
            print(f"Nueva póliza creada: {nueva_poliza.id}")

            # Verificar balance
            if nueva_poliza.total_debe == nueva_poliza.total_haber:
                print(f"✅ Póliza {nueva_poliza.id} balanceada correctamente.")
            else:
                print(f"❌ Póliza {nueva_poliza.id} sigue desbalanceada.")

        except Exception as e:
            print(f"Error al procesar póliza {poliza.id}: {e}")

if __name__ == "__main__":
    regenerate_policies()