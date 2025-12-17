"""
Script para actualizar TODAS las facturas con impuestos locales
Lee el XML desde el campo archivo_xml de la base de datos
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, CuentaContable, Empresa
from decimal import Decimal
import xml.etree.ElementTree as ET

def extraer_impuestos_locales_de_xml_string(xml_content):
    """
    Extrae impuestos locales directamente del contenido XML
    """
    if not xml_content:
        return Decimal('0.00')
    
    try:
        root = ET.fromstring(xml_content)
        
        # Helper para quitar namespace
        def tag_without_ns(t):
            return t.split('}')[-1] if '}' in t else t
        
        total_locales = Decimal('0.00')
        
        # Buscar en todo el árbol
        for elem in root.iter():
            tag = tag_without_ns(elem.tag).lower()
            
            # Buscar nodos de impuestos locales
            if 'implocal' in tag or 'impuestoslocales' in tag.lower():
                # Buscar retenciones locales
                for child in elem.iter():
                    child_tag = tag_without_ns(child.tag).lower()
                    
                    if 'retencionlocal' in child_tag or 'retencioneslocales' in child_tag:
                        importe = child.attrib.get('Importe') or child.attrib.get('importe')
                        if importe:
                            try:
                                total_locales += Decimal(importe)
                            except:
                                pass
                    
                    if 'trasladolocal' in child_tag or 'trasladoslocales' in child_tag:
                        importe = child.attrib.get('Importe') or child.attrib.get('importe')
                        if importe:
                            try:
                                total_locales += Decimal(importe)
                            except:
                                pass
        
        return total_locales
    
    except Exception as e:
        print(f"Error parseando XML: {e}")
        return Decimal('0.00')


# Obtener todas las facturas pendientes
facturas_pendientes = Factura.objects.filter(estado_contable='PENDIENTE')

print(f"Encontradas {facturas_pendientes.count()} facturas pendientes")
print("=" * 80)

actualizadas = 0
sin_xml = 0
sin_impuestos_locales = 0

for factura in facturas_pendientes:
    # Intentar obtener XML del campo archivo_xml
    xml_content = None
    
    if hasattr(factura, 'archivo_xml') and factura.archivo_xml:
        try:
            xml_content = factura.archivo_xml.read().decode('utf-8')
        except:
            pass
    
    # Si no hay XML en el campo, buscar en la carpeta xmls/
    if not xml_content:
        xml_dir = os.path.join(os.getcwd(), 'xmls')
        uuid_str = str(factura.uuid)
        
        if os.path.isdir(xml_dir):
            for filename in os.listdir(xml_dir):
                if uuid_str in filename and filename.lower().endswith('.xml'):
                    filepath = os.path.join(xml_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            xml_content = f.read()
                        break
                    except:
                        pass
    
    if not xml_content:
        sin_xml += 1
        continue
    
    # Extraer impuestos locales
    impuestos_locales = extraer_impuestos_locales_de_xml_string(xml_content)
    
    if impuestos_locales > 0:
        # Actualizar el campo total_impuestos_retenidos
        nuevo_total = factura.total_impuestos_retenidos + impuestos_locales
        
        print(f"\nFactura: {factura.uuid}")
        print(f"  Emisor: {factura.emisor_nombre[:40]}")
        print(f"  Retenciones actuales: ${factura.total_impuestos_retenidos:,.2f}")
        print(f"  Impuestos locales: ${impuestos_locales:,.2f}")
        print(f"  Nuevo total: ${nuevo_total:,.2f}")
        
        factura.total_impuestos_retenidos = nuevo_total
        factura.save()
        
        actualizadas += 1
    else:
        sin_impuestos_locales += 1

print("\n" + "=" * 80)
print(f"RESUMEN:")
print(f"  Facturas actualizadas: {actualizadas}")
print(f"  Sin XML disponible: {sin_xml}")
print(f"  Sin impuestos locales: {sin_impuestos_locales}")
print("=" * 80)

# Crear cuenta para retenciones estatales si no existe
print("\nCreando cuenta para retenciones estatales...")
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
    print(f"✓ Cuenta creada: {cuenta.codigo} - {cuenta.nombre}")
else:
    print(f"✓ Cuenta ya existe: {cuenta.codigo} - {cuenta.nombre}")

print("\n¡Proceso completado! Ahora puedes intentar contabilizar las facturas.")
