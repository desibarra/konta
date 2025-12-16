import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura
from decimal import Decimal

# UUIDs del Excel del usuario (29 facturas)
uuids_excel = [
    'c4712b82-2598-48e8-97c7-83e20aebf023',
    '4bb9784c-29c1-4bd6-99d0-b59439f6f6bb',
    '085d6d4b-1d95-46cb-a645-20fdf7833801',
    '3e7bc041-ad93-478f-accf-4d19fac92f8e',
    'eff5c0b0-aab0-4c4f-9a2d-0bcea0439f2fb',
    'a0db76e0-f358-4f99-b603-e4dd680f0e83',
    '5e0cbc06-97a4-4c50-a613-5da70d774919',
    '4208dafe-e4b3-4992-abbe-4f7c5e1c59f5',
    'a4d80eac-2210-4561-8b82-894790b65f24',
    'fdddf13e-c9dc-460b-b8f1-6e32d4dbd37a',
    '54a5125b-e6b3-49aa-bf12-e5b454946731',
    'b580b79f-c8b3-42d2-a2c8-0c062968ec35',
    'ee2dde81-2720-4323-9824-5087c13c58e1',
    '36590522-4463-44c9-8b5b-8798821eb998',
    '1ab2a581-e23f-4092-b1c9-1b81a2c205c2',
    '78cb36af-53b3-4c0a-b266-40c54e2181cb',
    'fca7f8a1-2b15-4c26-a66f-54e95765c8c5',
    'a85125a0-9c3b-40a2-b6cf-29eb84eed9b9',
    'a0335a9c-3977-454d-a2c8-ed558934687f',
    '12c23ab0-3a2b-4492-b38d-6fd332eb677a',
    '8edbef1a-3cc0-4f15-b8a9-e79e7b1e36e2',
    '0423a56a-db94-4290-901f-2dbf22d448c0',
    'a002235e-c243-4077-a730-f169eb759701',
    'b82ccf38-5322-40ab-8e1a-83da8318407b',
    '18e5348c-50d6-4594-9e64-e8c085f64da7',
    '6beee2d8-e0c9-45d0-b96e-e3f1fb1d8c31',
    'b0bab139-55cb-4ff9-809b-4bdb85707ed6',
    '56bdab6e-1c5f-4a82-9aab-98b4afad9e87',
    '0d94aff2-98ec-4544-9f9c-125d5617cc38',
    'ff2092f8-bc4c-47be-b6af-8ffd1e509ef3',
    '2492344c-f77d-437a-ba42-aaa7c737e655',
    'ceb48601-0e46-4049-9f8e-b80f0d3b62c1',
    'e1f2d4b1-5be1-4a9b-9ace-412e06e311d7',
    '447279b5-3633-412b-9bf9-ad974287711',
    '5094566f-e53f-4185-bc2e-2d4ab37c179a'
]

print("COMPARACIÓN: Excel vs Base de Datos")
print("=" * 70)

# Obtener facturas de Ingreso de la BD
facturas_bd = Factura.objects.filter(
    fecha__year=2025,
    naturaleza='I'
)

uuids_bd = [str(f.uuid) for f in facturas_bd]

print(f"\nFacturas en Excel:  {len(uuids_excel)}")
print(f"Facturas en BD:     {len(uuids_bd)}")

# Facturas en BD que NO están en Excel
extra_bd = set(uuids_bd) - set(uuids_excel)
print(f"\n❌ Facturas EXTRA en BD (no en Excel): {len(extra_bd)}")

if extra_bd:
    print("\nFacturas que NO deberían estar:")
    suma_extra = Decimal('0.00')
    for uuid in extra_bd:
        f = Factura.objects.get(uuid=uuid)
        print(f"  {uuid}: ${f.subtotal:,.2f} - {f.emisor_nombre[:40]}")
        suma_extra += f.subtotal
    
    print(f"\n💡 Suma de facturas EXTRA: ${suma_extra:,.2f}")
    print(f"   Diferencia reportada:   $37,448.13")
    
    if abs(suma_extra - Decimal('37448.13')) < Decimal('1.00'):
        print("   ✅ ¡COINCIDE! Estas son las facturas que sobran")

# Facturas en Excel que NO están en BD
faltantes = set(uuids_excel) - set(uuids_bd)
print(f"\n⚠️  Facturas en Excel que NO están en BD: {len(faltantes)}")
if faltantes:
    for uuid in faltantes:
        print(f"  {uuid}")
