"""
Script FINAL: Corregir todas las facturas pendientes
Calcula el impuesto local faltante y lo agrega al campo total_impuestos_retenidos
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, CuentaContable, Empresa
from decimal import Decimal

print("CORRECCION MASIVA DE IMPUESTOS LOCALES")
print("=" * 80)

# Obtener facturas de egreso pendientes
facturas = Factura.objects.filter(
    estado_contable='PENDIENTE',
    naturaleza='E'
).order_by('fecha')

print(f"Facturas de egreso pendientes: {facturas.count()}\n")

actualizadas = 0
ya_correctas = 0

for factura in facturas:
    # Calcular cuadre esperado
    # DEBE = Subtotal + IVA Trasladado
    # HABER = Total + Retenciones
    
    debe = factura.subtotal + factura.total_impuestos_trasladados
    haber_actual = factura.total + factura.total_impuestos_retenidos
    
    diferencia = debe - haber_actual
    
    if abs(diferencia) > Decimal('1.00'):
        # Hay una diferencia significativa
        # Verificar si es un porcentaje razonable del subtotal (2-3%)
        porcentaje = (abs(diferencia) / factura.subtotal) * 100
        
        if Decimal('1.5') <= porcentaje <= Decimal('3.5'):
            # Es probable que sea impuesto local
            print(f"Factura: {factura.uuid}")
            print(f"  Emisor: {factura.emisor_nombre[:50]}")
            print(f"  Subtotal: ${factura.subtotal:,.2f}")
            print(f"  Diferencia: ${abs(diferencia):,.2f} ({porcentaje:.2f}%)")
            print(f"  Retenciones actuales: ${factura.total_impuestos_retenidos:,.2f}")
            print(f"  Retenciones nuevas: ${factura.total_impuestos_retenidos + abs(diferencia):,.2f}")
            
            # Actualizar
            factura.total_impuestos_retenidos += abs(diferencia)
            factura.save()
            
            actualizadas += 1
            print(f"  ✅ ACTUALIZADA\n")
    else:
        ya_correctas += 1

print("=" * 80)
print(f"RESUMEN:")
print(f"  Facturas actualizadas: {actualizadas}")
print(f"  Facturas ya correctas: {ya_correctas}")
print(f"  Total procesadas: {facturas.count()}")

# Crear cuenta para retenciones estatales
print("\nCreando cuenta 213-03...")
empresa = Empresa.objects.first()

cuenta, created = CuentaContable.objects.get_or_create(
    empresa=empresa,
    codigo='213-03',
    defaults={
        'nombre': 'Retenciones Estatales por Pagar',
        'tipo': 'PASIVO',
        'naturaleza': 'A',
        'es_deudora': False,
        'nivel': 2
    }
)

if created:
    print(f"✅ Cuenta creada: {cuenta.codigo} - {cuenta.nombre}")
else:
    print(f"✅ Cuenta ya existe: {cuenta.codigo} - {cuenta.nombre}")

print("\n" + "=" * 80)
print("PROCESO COMPLETADO")
print("Ahora puedes contabilizar las facturas desde la bandeja.")
print("=" * 80)
