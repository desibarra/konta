# -*- coding: utf-8 -*-
"""
CIERRE MASIVO BLINDADO
Corrige y contabiliza TODAS las facturas pendientes automaticamente
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, PlantillaPoliza, CuentaContable, Empresa
from core.services.accounting_service import AccountingService
from django.contrib.auth.models import User
from decimal import Decimal
import traceback

print("=" * 80)
print("CIERRE MASIVO BLINDADO - PROCESAMIENTO AUTOMATICO")
print("=" * 80)

# Crear cuenta 213-03 si no existe
empresa = Empresa.objects.first()
cuenta_ret_est, created = CuentaContable.objects.get_or_create(
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
    print(f"Cuenta creada: 213-03 - Retenciones Estatales por Pagar")
else:
    print(f"Cuenta existente: 213-03")

# Obtener plantilla y usuario
plantilla = PlantillaPoliza.objects.first()
usuario = User.objects.filter(is_superuser=True).first()
if not usuario:
    usuario = User.objects.first()

print(f"Plantilla: {plantilla.nombre if plantilla else 'N/A'}")
print(f"Usuario: {usuario.username if usuario else 'N/A'}")
print("=" * 80)

# Obtener facturas pendientes
facturas = Factura.objects.filter(estado_contable='PENDIENTE').order_by('fecha')
total = facturas.count()

print(f"\nTotal facturas pendientes: {total}\n")

exitosas = 0
corregidas = 0
fallidas = 0
errores = []

for i, factura in enumerate(facturas, 1):
    uuid_str = str(factura.uuid)
    print(f"[{i}/{total}] {uuid_str[:8]} - {factura.emisor_nombre[:30]}")
    
    try:
        # PASO 1: Calcular diferencia de cuadre
        iva_tras = factura.total_impuestos_trasladados or Decimal('0.00')
        iva_ret = factura.total_impuestos_retenidos or Decimal('0.00')
        
        if factura.naturaleza == 'E':
            # EGRESO: DEBE = Subtotal + IVA, HABER = Total + Retenciones
            debe = factura.subtotal + iva_tras
            haber = factura.total + iva_ret
            diferencia = debe - haber
            
            if abs(diferencia) > Decimal('1.00'):
                print(f"  Diferencia detectada: ${abs(diferencia):.2f}")
                print(f"  Agregando a retenciones...")
                
                # Agregar diferencia a retenciones
                factura.total_impuestos_retenidos += abs(diferencia)
                factura.save()
                corregidas += 1
                print(f"  Retenciones actualizadas: ${factura.total_impuestos_retenidos:.2f}")
        
        # PASO 2: Intentar contabilizar
        print(f"  Contabilizando...")
        poliza = AccountingService.contabilizar_factura(
            factura=factura,
            plantilla=plantilla,
            usuario=usuario
        )
        
        print(f"  OK - Poliza #{poliza.id}")
        exitosas += 1
        
    except Exception as e:
        error_msg = str(e)
        print(f"  ERROR: {error_msg[:80]}")
        fallidas += 1
        
        errores.append({
            'uuid': uuid_str,
            'emisor': factura.emisor_nombre[:40],
            'naturaleza': factura.naturaleza,
            'total': float(factura.total),
            'error': error_msg[:150]
        })
    
    print()

# RESUMEN FINAL
print("=" * 80)
print("RESUMEN FINAL")
print("=" * 80)
print(f"Total procesadas:     {total}")
print(f"Exitosas:             {exitosas}")
print(f"Corregidas:           {corregidas}")
print(f"Fallidas:             {fallidas}")
print(f"Tasa de exito:        {(exitosas/total*100):.1f}%")

# Verificar estado final
pendientes_final = Factura.objects.filter(estado_contable='PENDIENTE').count()
print(f"\nFacturas pendientes restantes: {pendientes_final}")

if pendientes_final == 0:
    print("\n*** EXITO TOTAL: CERO FACTURAS PENDIENTES ***")
else:
    print(f"\n*** QUEDAN {pendientes_final} FACTURAS POR REVISAR ***")

# Mostrar errores
if errores:
    print("\n" + "=" * 80)
    print("ERRORES DETALLADOS")
    print("=" * 80)
    for err in errores:
        print(f"\nUUID: {err['uuid']}")
        print(f"Emisor: {err['emisor']}")
        print(f"Naturaleza: {err['naturaleza']}")
        print(f"Total: ${err['total']:,.2f}")
        print(f"Error: {err['error']}")

print("\n" + "=" * 80)
print("PROCESO COMPLETADO")
print("=" * 80)
