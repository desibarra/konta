"""
Investigar pólizas con ajustes anormales
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Poliza, MovimientoPoliza, Factura
from decimal import Decimal

# Pólizas problemáticas
polizas_ids = [8217, 8261, 9287]

print("=" * 80)
print("INVESTIGACIÓN: Pólizas con Ajustes Anormales")
print("=" * 80)

for poliza_id in polizas_ids:
    try:
        poliza = Poliza.objects.get(id=poliza_id)
        factura = poliza.factura
        movimientos = MovimientoPoliza.objects.filter(poliza=poliza)
        
        print(f"\n📋 PÓLIZA #{poliza_id}")
        print(f"   Fecha: {poliza.fecha}")
        print(f"   Factura UUID: {factura.uuid}")
        print(f"   Tipo: {factura.tipo_comprobante}")
        print(f"   Naturaleza: {factura.naturaleza}")
        print(f"   Total Factura: ${factura.total:,.2f}")
        print(f"   Subtotal: ${factura.subtotal:,.2f}")
        print(f"   IVA Trasladado: ${factura.total_impuestos_trasladados:,.2f}")
        print(f"   IVA Retenido: ${factura.total_impuestos_retenidos:,.2f}")
        print(f"   Descuento: ${factura.descuento:,.2f}")
        
        print(f"\n   MOVIMIENTOS:")
        total_debe = Decimal('0')
        total_haber = Decimal('0')
        
        for mov in movimientos:
            print(f"      {mov.cuenta.codigo:15s} | D: ${mov.debe:>12,.2f} | H: ${mov.haber:>12,.2f} | {mov.descripcion[:40]}")
            total_debe += mov.debe
            total_haber += mov.haber
        
        diferencia = total_debe - total_haber
        
        print(f"\n   TOTALES:")
        print(f"      Debe:  ${total_debe:>15,.2f}")
        print(f"      Haber: ${total_haber:>15,.2f}")
        print(f"      Diff:  ${diferencia:>15,.2f}")
        
        # Buscar el ajuste
        ajuste = movimientos.filter(cuenta__codigo='702-99').first()
        if ajuste:
            monto_ajuste = ajuste.haber if ajuste.haber > 0 else -ajuste.debe
            print(f"\n   ⚠️  AJUSTE: ${monto_ajuste:,.2f}")
            print(f"      Esto indica que la póliza no cuadraba por ${monto_ajuste:,.2f}")
        
        print(f"\n   🔍 ANÁLISIS:")
        # Calcular lo que DEBERÍA ser
        if factura.naturaleza == 'I':  # Ingreso
            esperado_debe = factura.total
            esperado_haber = factura.subtotal + factura.total_impuestos_trasladados - factura.descuento
        else:  # Egreso
            esperado_debe = factura.subtotal + factura.total_impuestos_trasladados - factura.total_impuestos_retenidos
            esperado_haber = factura.total
        
        print(f"      Esperado Debe:  ${esperado_debe:,.2f}")
        print(f"      Esperado Haber: ${esperado_haber:,.2f}")
        print(f"      Real Debe:      ${total_debe:,.2f}")
        print(f"      Real Haber:     ${total_haber:,.2f}")
        
    except Poliza.DoesNotExist:
        print(f"\n❌ Póliza #{poliza_id} no encontrada")
    except Exception as e:
        print(f"\n❌ Error en póliza #{poliza_id}: {str(e)}")

print("\n" + "=" * 80)
print("💡 RECOMENDACIÓN:")
print("   Estas facturas tienen errores en su contabilización.")
print("   Necesitan regenerarse manualmente o investigar por qué no cuadran.")
print("=" * 80)
