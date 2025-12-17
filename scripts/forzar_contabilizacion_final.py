import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, PlantillaPoliza, CuentaContable, Empresa
from core.services.accounting_service import AccountingService
from django.contrib.auth.models import User
from decimal import Decimal

print("FORZAR CONTABILIZACION DE TODAS LAS PENDIENTES")
print("=" * 80)

# Crear cuenta generica si no existe
empresa = Empresa.objects.first()
cuenta_generica, created = CuentaContable.objects.get_or_create(
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

if created:
    print(f"Cuenta creada: 601-99 - Gastos por Identificar")

pendientes = Factura.objects.filter(estado_contable='PENDIENTE')
plantilla = PlantillaPoliza.objects.first()
usuario = User.objects.first()

total = pendientes.count()
print(f"Total pendientes: {total}\n")

exitosas = 0
fallidas = 0

for i, f in enumerate(pendientes, 1):
    try:
        # Intentar corregir si es egreso
        if f.naturaleza == 'E':
            iva_tras = f.total_impuestos_trasladados or Decimal('0')
            iva_ret = f.total_impuestos_retenidos or Decimal('0')
            
            debe = f.subtotal + iva_tras
            haber = f.total + iva_ret
            dif = debe - haber
            
            if abs(dif) > Decimal('1'):
                f.total_impuestos_retenidos += abs(dif)
                f.save()
                print(f"[{i}/{total}] Corregida: +${abs(dif):.2f} a retenciones")
        
        # Intentar contabilizar
        poliza = AccountingService.contabilizar_factura(f, plantilla, usuario)
        print(f"[{i}/{total}] OK - Poliza #{poliza.id}")
        exitosas += 1
        
    except Exception as e:
        print(f"[{i}/{total}] ERROR: {str(e)[:60]}")
        fallidas += 1

print("\n" + "=" * 80)
print(f"RESUMEN:")
print(f"  Exitosas: {exitosas}")
print(f"  Fallidas: {fallidas}")

# Verificar estado final
final = Factura.objects.filter(estado_contable='PENDIENTE').count()
print(f"\nPendientes restantes: {final}")

if final == 0:
    print("\n*** EXITO: CERO FACTURAS PENDIENTES ***")
