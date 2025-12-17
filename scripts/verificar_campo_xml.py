"""
Verificar si la factura tiene el XML almacenado en un campo
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'

try:
    f = Factura.objects.get(uuid=uuid)
    print(f"Factura encontrada: {uuid}")
    print(f"Emisor: {f.emisor_nombre}")
    print(f"Total: ${f.total:,.2f}")
    print(f"Estado: {f.estado_contable}")
    
    # Ver si tiene campo xml_file
    if hasattr(f, 'xml_file') and f.xml_file:
        print(f"\n✅ Tiene campo xml_file: {f.xml_file}")
        print(f"   Path: {f.xml_file.path if hasattr(f.xml_file, 'path') else 'N/A'}")
    else:
        print(f"\n❌ No tiene campo xml_file")
    
    # Ver si tiene campo archivo_xml
    if hasattr(f, 'archivo_xml') and f.archivo_xml:
        print(f"\n✅ Tiene campo archivo_xml: {f.archivo_xml}")
    else:
        print(f"\n❌ No tiene campo archivo_xml")
    
    # Listar todos los campos
    print(f"\nCAMPOS DE LA FACTURA:")
    for field in f._meta.fields:
        field_name = field.name
        if 'xml' in field_name.lower() or 'archivo' in field_name.lower():
            value = getattr(f, field_name, None)
            print(f"  {field_name}: {value}")
            
except Factura.DoesNotExist:
    print(f"❌ Factura no encontrada: {uuid}")
