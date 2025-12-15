import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Poliza, MovimientoPoliza, CuentaContable
from core.services.accounting_service import AccountingService
from django.db import transaction

def run_diagnosis(fix=False):
    print(f"--- ACCOUNTING DIAGNOSIS (Fix Mode: {fix}) ---")
    
    # Identify invoices: Naturaleza 'E' AND Linked to Poliza with Account 4xx (Ingresos)
    # Note: 4xx accounts are typically Ingresos by default in this system (e.g. 401 Ventas)
    
    candidates = Factura.objects.filter(
        naturaleza='E',
        poliza__isnull=False,
        poliza__movimientos__cuenta__codigo__startswith='4'
    ).distinct()
    
    count = candidates.count()
    print(f"Candidates found: {count}")
    
    if count == 0:
        print("✅ No issues found.")
        return

    for fact in candidates:
        poliza = fact.poliza
        print(f"\n[!] Invoice {fact.uuid} | Naturaleza: {fact.naturaleza} | Poliza: {poliza.id}")
        
        # Check specific bad movements
        bad_movs = poliza.movimientos.filter(cuenta__codigo__startswith='4')
        for m in bad_movs:
            print(f"    - BAD MOVEMENT: {m.cuenta.codigo} - {m.cuenta.nombre} | Haber: {m.haber}")
            
        if fix:
            print("    -> FIXING...")
            try:
                with transaction.atomic():
                    # 1. Delete Poliza (Cascade handles movements)
                    pid = poliza.id
                    poliza.delete()
                    print(f"       - Poliza {pid} deleted.")
                    
                    # 2. Reset Factura State
                    fact.estado_contable = 'PENDIENTE'
                    fact.save()
                    
                    # 3. Regenerate
                    new_poliza = AccountingService.contabilizar_factura(fact.uuid)
                    print(f"       - Created New Poliza {new_poliza.id}")
                    
                    # 4. Verify New Poliza
                    has_4xx = new_poliza.movimientos.filter(cuenta__codigo__startswith='4').exists()
                    if has_4xx:
                        print("       ❌ FAIL: Validated Poliza still has 4xx account!")
                    else:
                        print("       ✅ SUCCESS: Poliza cleaned.")
                        
            except Exception as e:
                print(f"       ❌ ERROR: {e}")

if __name__ == "__main__":
    fix_mode = '--fix' in sys.argv
    run_diagnosis(fix=fix_mode)
