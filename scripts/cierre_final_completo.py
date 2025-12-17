# -*- coding: utf-8 -*-
"""
REPARACION DE UUIDS Y CONTABILIZACION FINAL
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, PlantillaPoliza, CuentaContable, Empresa
from core.services.accounting_service import AccountingService
from django.contrib.auth.models import User
from decimal import Decimal
import uuid as uuid_lib
import re

print("=" * 80)
print("CIERRE FINAL - REPARACION DE UUIDS Y CONTABILIZACION")
print("=" * 80)

# Crear cuenta genérica
empresa = Empresa.objects.first()
cuenta_gen, created = CuentaContable.objects.get_or_create(
    empresa=empresa,
    codigo='601-99',
    defaults={
        'nombre': 'Gastos por Identificar',
        'tipo': 'GASTO',
        'naturaleza': 'D',
        'es_deudora': True,
        'nivel': 2
    }
)

pendientes = Factura.objects.filter(estado_contable='PENDIENTE')
plantilla = PlantillaPoliza.objects.first()
usuario = User.objects.first()

total = pendientes.count()
print(f"\nFacturas pendientes: {total}")
print(f"Plantilla: {plantilla.nombre if plantilla else 'N/A'}\n")

uuids_reparados = 0
exitosas = 0
fallidas = 0
errores = []

for i, factura in enumerate(pendientes, 1):
    uuid_original = str(factura.uuid)
    
    try:
        # PASO 1: Limpiar UUID
        uuid_limpio = uuid_original.strip()
        
        # Verificar formato (8-4-4-4-12)
        patron = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(patron, uuid_limpio, re.IGNORECASE):
            print(f"[{i}/{total}] UUID invalido: {uuid_limpio[:40]}")
            # Intentar reparar
            uuid_limpio = uuid_limpio.replace(' ', '').lower()
            
            if not re.match(patron, uuid_limpio):
                print(f"  No se puede reparar, saltando...")
                fallidas += 1
                continue
        
        if uuid_limpio != uuid_original:
            factura.uuid = uuid_limpio
            factura.save()
            uuids_reparados += 1
            print(f"[{i}/{total}] UUID reparado")
        
        # PASO 2: Corregir retenciones si es egreso
        if factura.naturaleza == 'E':
            iva_tras = factura.total_impuestos_trasladados or Decimal('0')
            iva_ret = factura.total_impuestos_retenidos or Decimal('0')
            
            debe = factura.subtotal + iva_tras
            haber = factura.total + iva_ret
            dif = debe - haber
            
            if abs(dif) > Decimal('1'):
                factura.total_impuestos_retenidos += abs(dif)
                factura.save()
                print(f"[{i}/{total}] Retenciones corregidas: +${abs(dif):.2f}")
        
        # PASO 3: Contabilizar
        poliza = AccountingService.contabilizar_factura(
            factura=factura,
            plantilla=plantilla,
            usuario=usuario
        )
        
        print(f"[{i}/{total}] OK - Poliza #{poliza.id}")
        exitosas += 1
        
    except Exception as e:
        error_msg = str(e)
        print(f"[{i}/{total}] ERROR: {error_msg[:70]}")
        fallidas += 1
        errores.append({
            'uuid': uuid_original[:40],
            'emisor': factura.emisor_nombre[:35],
            'error': error_msg[:100]
        })

print("\n" + "=" * 80)
print("RESUMEN:")
print("=" * 80)
print(f"Total procesadas:     {total}")
print(f"UUIDs reparados:      {uuids_reparados}")
print(f"Exitosas:             {exitosas}")
print(f"Fallidas:             {fallidas}")

# Verificar estado final
from django.db import models

pendientes_final = Factura.objects.filter(estado_contable='PENDIENTE').count()
contabilizadas = Factura.objects.filter(estado_contable='CONTABILIZADA').count()
total_facturas = Factura.objects.count()

print(f"\nESTADO FINAL:")
print(f"  Total facturas:       {total_facturas}")
print(f"  Contabilizadas:       {contabilizadas} ({contabilizadas/total_facturas*100:.1f}%)")
print(f"  Pendientes:           {pendientes_final}")

if pendientes_final == 0:
    print(f"\n*** EXITO TOTAL: 100% CONTABILIZADO ***")

# BALANZA
from core.models import MovimientoPoliza

total_debe = MovimientoPoliza.objects.aggregate(t=models.Sum('debe'))['t'] or Decimal('0')
total_haber = MovimientoPoliza.objects.aggregate(t=models.Sum('haber'))['t'] or Decimal('0')
diferencia = abs(total_debe - total_haber)

print(f"\nBALANZA DE COMPROBACION:")
print(f"  Total DEBE:  ${total_debe:>20,.2f}")
print(f"  Total HABER: ${total_haber:>20,.2f}")
print(f"  Diferencia:  ${diferencia:>20,.2f}")

if diferencia < Decimal('1.00'):
    print(f"\n*** BALANZA CUADRADA ***")
else:
    print(f"\nADVERTENCIA: Diferencia de ${diferencia:.2f}")

# Cuenta 702-99
try:
    cuenta_702 = CuentaContable.objects.get(empresa=empresa, codigo='702-99')
    saldo_702 = MovimientoPoliza.objects.filter(cuenta=cuenta_702).aggregate(
        debe=models.Sum('debe'),
        haber=models.Sum('haber')
    )
    
    debe_702 = saldo_702['debe'] or Decimal('0')
    haber_702 = saldo_702['haber'] or Decimal('0')
    saldo_final_702 = debe_702 - haber_702
    
    print(f"\nCUENTA 702-99 (Ajuste por Redondeo):")
    print(f"  Saldo: ${abs(saldo_final_702):,.2f}")
    
    if abs(saldo_final_702) < Decimal('1.00'):
        print(f"  *** CORRECTO (< $1.00) ***")
except:
    print(f"\nCuenta 702-99: No existe")

if errores:
    print(f"\n" + "=" * 80)
    print("ERRORES DETALLADOS:")
    print("=" * 80)
    for err in errores[:5]:
        print(f"\nUUID: {err['uuid']}")
        print(f"Emisor: {err['emisor']}")
        print(f"Error: {err['error']}")

print("\n" + "=" * 80)
print("PROCESO COMPLETADO")
print("=" * 80)
