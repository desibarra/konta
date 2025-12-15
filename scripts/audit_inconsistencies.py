import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza, MovimientoPoliza

print("--- AUDITORIA DE INCONSISTENCIAS CONTABLES ---")

# Buscar Facturas con Naturaleza 'E' (Egreso) que tengan póliza
qs = Factura.objects.filter(naturaleza='E', poliza__isnull=False)

inconsistentes = 0
total_e = qs.count()

print(f"Total Facturas 'E' con Póliza: {total_e}")

for fact in qs:
    poliza = fact.poliza
    # Buscar movimientos en cuentas 4xx (Ingresos)
    # Excluyendo si por alguna razón extraña hubiera devoluciones que afecten 4xx (pero en E puro no debería)
    movs_4xx = poliza.movimientos.filter(cuenta__codigo__startswith='4')
    
    if movs_4xx.exists():
        inconsistentes += 1
        print("--------------------------------------------------")
        print(f"Factura UUID: {fact.uuid}")
        print(f"Naturaleza: {fact.naturaleza}")
        print(f"Poliza ID: {poliza.id}")
        print("Cuentas involucradas (INCONSISTENTES):")
        for m in movs_4xx:
            print(f" - Cuenta: {m.cuenta.codigo} ({m.cuenta.nombre}) | Haber: {m.haber} | Debe: {m.debe}")
        print("Estado: INCONSISTENTE")

print("--------------------------------------------------")
if inconsistentes == 0:
    print("✅ RESULTADO: No se encontraron inconsistencias. (0 pólizas incorrectas)")
else:
    print(f"❌ RESULTADO: Se encontraron {inconsistentes} inconsistencias.")

print("--- FIN DEL REPORTE ---")
