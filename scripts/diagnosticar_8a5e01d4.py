"""
Diagnosticar factura 8a5e01d4-bad6-4bd2-8fd1-790304d98069
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from core.services.accounting_service import AccountingService
from decimal import Decimal

uuid = '8a5e01d4-bad6-4bd2-8fd1-790304d98069'

try:
    f = Factura.objects.get(uuid=uuid)
    
    print("=" * 80)
    print(f"DIAGNÓSTICO DE FACTURA {uuid}")
    print("=" * 80)
    
    print(f"\nEmisor: {f.emisor_nombre}")
    print(f"Receptor: {f.receptor_nombre}")
    print(f"Naturaleza: {f.naturaleza}")
    print(f"Fecha: {f.fecha}")
    
    print(f"\n💰 MONTOS DE LA FACTURA:")
    print(f"   Subtotal:                    ${f.subtotal:>15,.2f}")
    print(f"   IVA Trasladado (campo):      ${f.total_impuestos_trasladados:>15,.2f}")
    print(f"   IVA Retenido (campo):        ${f.total_impuestos_retenidos:>15,.2f}")
    print(f"   Total:                       ${f.total:>15,.2f}")
    
    # Leer impuestos del XML
    iva_tras, isr_ret, iva_ret, desc, imp_locales = AccountingService._accumulate_impuestos_from_xml(f)
    
    print(f"\n📋 IMPUESTOS DEL XML:")
    print(f"   IVA Trasladado:              ${iva_tras:>15,.2f}")
    print(f"   ISR Retenido:                ${isr_ret:>15,.2f}")
    print(f"   IVA Retenido:                ${iva_ret:>15,.2f}")
    print(f"   Impuestos Locales:           ${imp_locales:>15,.2f}")
    print(f"   Descuento:                   ${desc:>15,.2f}")
    
    total_retenciones_xml = isr_ret + iva_ret + imp_locales
    print(f"\n   Total Retenciones (XML):     ${total_retenciones_xml:>15,.2f}")
    
    # Calcular cuadre
    if f.naturaleza == 'E':
        print(f"\n🧮 CÁLCULO PARA EGRESO:")
        
        debe = f.subtotal + iva_tras
        haber = f.total + total_retenciones_xml
        
        print(f"\n   DEBE (Gasto + IVA):          ${debe:>15,.2f}")
        print(f"   HABER (Prov + Ret):          ${haber:>15,.2f}")
        print(f"   Diferencia:                  ${abs(debe - haber):>15,.2f}")
        
        if abs(debe - haber) > 1:
            print(f"\n   ⚠️  PROBLEMA: Diferencia de ${abs(debe - haber):.2f}")
            
            # Verificar si es problema de impuestos locales
            if imp_locales == 0:
                print(f"\n   💡 POSIBLE CAUSA: Impuestos locales no leídos del XML")
                print(f"      El XML podría tener impuestos locales que no se están leyendo")
            
            # Calcular cuánto falta
            faltante = abs(debe - haber)
            print(f"\n   📊 ANÁLISIS:")
            print(f"      Faltante: ${faltante:.2f}")
            print(f"      ¿Es ~2.5% del subtotal? {abs(faltante - (f.subtotal * Decimal('0.025'))) < 10}")
            print(f"      2.5% del subtotal = ${(f.subtotal * Decimal('0.025')):.2f}")
        else:
            print(f"\n   ✅ CUADRA CORRECTAMENTE")
    
    print(f"\n{'='*80}")
    
except Factura.DoesNotExist:
    print(f"❌ Factura no encontrada: {uuid}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
