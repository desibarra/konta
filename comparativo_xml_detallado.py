import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from django.db.models import Sum
from decimal import Decimal
from datetime import datetime

# UUIDs del Excel del usuario (35 facturas según imagen)
uuids_excel = {
    'c4712b82-2598-48e8-97c7-83e20aebf023': Decimal('1587.60'),
    '4bb9784c-29c1-4bd6-99d0-b59439f6f6bb': Decimal('41227.85'),
    '085d6d4b-1d95-46cb-a645-20fdf7833801': Decimal('483.62'),
    '3e7bc041-ad93-478f-accf-4d19fac92f8e': Decimal('32873.27'),
    'eff5c0b0-aab0-4c4f-9a2d-0bcea0439f2fb': Decimal('1204.02'),
    'a0db76e0-f358-4f99-b603-e4dd680f0e83': Decimal('21138.80'),
    '5e0cbc06-97a4-4c50-a613-5da70d774919': Decimal('3548.50'),
    '4208dafe-e4b3-4992-abbe-4f7c5e1c59f5': Decimal('254.60'),
    'a4d80eac-2210-4561-8b82-894790b65f24': Decimal('217.75'),
    'fdddf13e-c9dc-460b-b8f1-6e32d4dbd37a': Decimal('42245.54'),
    '54a5125b-e6b3-49aa-bf12-e5b454946731': Decimal('158.62'),
    'b580b79f-c8b3-42d2-a2c8-0c062968ec35': Decimal('606.84'),
    'ee2dde81-2720-4323-9824-5087c13c58e1': Decimal('254.14'),
    '36590522-4463-44c9-8b5b-8798821eb998': Decimal('217.75'),
    '1ab2a581-e23f-4092-b1c9-1b81a2c205c2': Decimal('577.24'),
    '78cb36af-53b3-4c0a-b266-40c54e2181cb': Decimal('2883.44'),
    'fca7f8a1-2b15-4c26-a66f-54e95765c8c5': Decimal('671.55'),
    'a85125a0-9c3b-40a2-b6cf-29eb84eed9b9': Decimal('34092.80'),
    'a0335a9c-3977-454d-a2c8-ed558934687f': Decimal('27527.01'),
    '12c23ab0-3a2b-4492-b38d-6fd332eb677a': Decimal('653.25'),
    '8edbef1a-3cc0-4f15-b8a9-e79e7b1e36e2': Decimal('61100.25'),
    '0423a56a-db94-4290-901f-2dbf22d448c0': Decimal('2183.12'),
    'a002235e-c243-4077-a730-f169eb759701': Decimal('2002.70'),
    'b82ccf38-5322-40ab-8e1a-83da8318407b': Decimal('39704.09'),
    '18e5348c-50d6-4594-9e64-e8c085f64da7': Decimal('5000.00'),
    '6beee2d8-e0c9-45d0-b96e-e3f1fb1d8c31': Decimal('29073.12'),
    'b0bab139-55cb-4ff9-809b-4bdb85707ed6': Decimal('894.03'),
    '56bdab6e-1c5f-4a82-9aab-98b4afad9e87': Decimal('5000.00'),
    '0d94aff2-98ec-4544-9f9c-125d5617cc38': Decimal('26819.99'),
    'ff2092f8-bc4c-47be-b6af-8ffd1e509ef3': Decimal('5555.94'),
    '2492344c-f77d-437a-ba42-aaa7c737e655': Decimal('237.93'),
    'ceb48601-0e46-4049-9f8e-b80f0d3b62c1': Decimal('641.62'),
    'e1f2d4b1-5be1-4a9b-9ace-412e06e311d7': Decimal('586.75'),
    '447279b5-3633-412b-9bf9-ad974287711': Decimal('23153.71'),
    '5094566f-e53f-4185-bc2e-2d4ab37c179a': Decimal('509.20'),
}

print("=" * 80)
print("COMPARATIVO DETALLADO: EXCEL vs PLATAFORMA")
print("=" * 80)

# Obtener facturas de Ingreso de la BD
facturas_bd = Factura.objects.filter(
    fecha__year=2025,
    naturaleza='I'
)

print(f"\n📊 RESUMEN:")
print(f"   Excel:      {len(uuids_excel)} facturas")
print(f"   Plataforma: {facturas_bd.count()} facturas")

# Crear diccionario de BD
bd_dict = {str(f.uuid): f for f in facturas_bd}

# ANÁLISIS 1: Facturas en EXCEL que NO están en PLATAFORMA
print(f"\n{'='*80}")
print("❌ FACTURAS FALTANTES EN PLATAFORMA (están en Excel, NO en plataforma)")
print(f"{'='*80}")

faltantes = []
suma_faltantes = Decimal('0.00')

for uuid, subtotal_excel in uuids_excel.items():
    if uuid not in bd_dict:
        faltantes.append((uuid, subtotal_excel))
        suma_faltantes += subtotal_excel

if faltantes:
    print(f"\nTotal: {len(faltantes)} facturas faltantes")
    print(f"\n{'UUID':<40} {'Subtotal Excel':>15}")
    print("-" * 60)
    for uuid, subtotal in faltantes:
        print(f"{uuid:<40} ${subtotal:>13,.2f}")
    print("-" * 60)
    print(f"{'SUMA FALTANTES:':<40} ${suma_faltantes:>13,.2f}")
else:
    print("\n✅ No hay facturas faltantes")

# ANÁLISIS 2: Facturas en PLATAFORMA que NO están en EXCEL
print(f"\n{'='*80}")
print("⚠️  FACTURAS SOBRANTES EN PLATAFORMA (están en plataforma, NO en Excel)")
print(f"{'='*80}")

sobrantes = []
suma_sobrantes = Decimal('0.00')

for uuid, factura in bd_dict.items():
    if uuid not in uuids_excel:
        sobrantes.append((uuid, factura))
        suma_sobrantes += factura.subtotal

if sobrantes:
    print(f"\nTotal: {len(sobrantes)} facturas sobrantes")
    print(f"\n{'UUID':<40} {'Subtotal BD':>15} {'Emisor':<30}")
    print("-" * 90)
    for uuid, factura in sobrantes:
        print(f"{uuid:<40} ${factura.subtotal:>13,.2f} {factura.emisor_nombre[:28]:<30}")
    print("-" * 90)
    print(f"{'SUMA SOBRANTES:':<40} ${suma_sobrantes:>13,.2f}")
    
    print(f"\n💡 ANÁLISIS:")
    print(f"   Si eliminas estas {len(sobrantes)} facturas sobrantes:")
    suma_total_bd = facturas_bd.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
    print(f"   Subtotal actual:  ${suma_total_bd:,.2f}")
    print(f"   Menos sobrantes:  ${suma_sobrantes:,.2f}")
    print(f"   Quedaría:         ${suma_total_bd - suma_sobrantes:,.2f}")
    print(f"   Esperado (Excel): ${sum(uuids_excel.values()):,.2f}")
else:
    print("\n✅ No hay facturas sobrantes")

# ANÁLISIS 3: Facturas que COINCIDEN pero con diferente subtotal
print(f"\n{'='*80}")
print("🔍 FACTURAS CON DIFERENCIAS EN SUBTOTAL")
print(f"{'='*80}")

diferencias = []

for uuid, subtotal_excel in uuids_excel.items():
    if uuid in bd_dict:
        factura = bd_dict[uuid]
        if abs(factura.subtotal - subtotal_excel) > Decimal('0.01'):
            diferencias.append((uuid, subtotal_excel, factura.subtotal))

if diferencias:
    print(f"\nTotal: {len(diferencias)} facturas con diferencias")
    print(f"\n{'UUID':<40} {'Excel':>15} {'BD':>15} {'Diferencia':>15}")
    print("-" * 90)
    for uuid, excel, bd in diferencias:
        diff = bd - excel
        print(f"{uuid:<40} ${excel:>13,.2f} ${bd:>13,.2f} ${diff:>13,.2f}")
else:
    print("\n✅ Todas las facturas coincidentes tienen el mismo subtotal")

# RESUMEN FINAL
print(f"\n{'='*80}")
print("📋 RESUMEN EJECUTIVO")
print(f"{'='*80}")

print(f"\n1. Facturas faltantes en plataforma: {len(faltantes)}")
print(f"   Suma: ${suma_faltantes:,.2f}")

print(f"\n2. Facturas sobrantes en plataforma: {len(sobrantes)}")
print(f"   Suma: ${suma_sobrantes:,.2f}")

print(f"\n3. Facturas con diferencias: {len(diferencias)}")

print(f"\n4. Facturas correctas: {len(uuids_excel) - len(faltantes) - len(diferencias)}")

print(f"\n{'='*80}")
print("💡 RECOMENDACIÓN:")
print(f"{'='*80}")

if sobrantes:
    print(f"\n1. ELIMINAR las {len(sobrantes)} facturas sobrantes de la plataforma")
    print(f"   Esto reducirá el subtotal en ${suma_sobrantes:,.2f}")

if faltantes:
    print(f"\n2. SUBIR los XMLs de las {len(faltantes)} facturas faltantes")
    print(f"   Esto agregará ${suma_faltantes:,.2f} al subtotal")

if diferencias:
    print(f"\n3. REVISAR las {len(diferencias)} facturas con diferencias")
    print(f"   Verificar que los XMLs sean correctos")

print(f"\n4. Después de los ajustes, ejecutar:")
print(f"   python manage.py reset_contabilidad_2025")

# Guardar reporte
with open('comparativo_xml_detallado.txt', 'w', encoding='utf-8') as f:
    f.write("COMPARATIVO DETALLADO XML\n")
    f.write("="*80 + "\n\n")
    f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("FACTURAS SOBRANTES (eliminar de plataforma):\n")
    f.write("-"*80 + "\n")
    for uuid, factura in sobrantes:
        f.write(f"{uuid}\n")
    
    f.write("\n\nFACTURAS FALTANTES (subir a plataforma):\n")
    f.write("-"*80 + "\n")
    for uuid, subtotal in faltantes:
        f.write(f"{uuid}\n")

print(f"\n📄 Reporte guardado en: comparativo_xml_detallado.txt")
