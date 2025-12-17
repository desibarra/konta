"""
Buscar y analizar el XML de la factura problemática
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from django.conf import settings
import xml.etree.ElementTree as ET

uuid = '1e87b201-c77d-4223-a958-57e2817f0fc7'

base_dir = settings.BASE_DIR
xml_dir = os.path.join(base_dir, 'xmls')

print(f"Buscando XML en: {xml_dir}")
print(f"UUID: {uuid}\n")

if not os.path.exists(xml_dir):
    print(f"❌ El directorio {xml_dir} no existe")
    exit()

# Buscar archivo
found = False
for filename in os.listdir(xml_dir):
    if uuid in filename and filename.lower().endswith('.xml'):
        found = True
        filepath = os.path.join(xml_dir, filename)
        print(f"✅ Archivo encontrado: {filename}\n")
        
        # Parsear XML
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        print("NAMESPACES EN EL XML:")
        for prefix, uri in root.attrib.items():
            if 'xmlns' in prefix:
                print(f"  {prefix}: {uri}")
        
        print("\nBUSCANDO NODOS CON 'IMPLOCAL' O 'LOCAL':")
        for elem in root.iter():
            if 'local' in elem.tag.lower() or 'implocal' in elem.tag.lower():
                print(f"\n  Tag: {elem.tag}")
                print(f"  Atributos: {elem.attrib}")
                
                # Mostrar hijos
                for child in elem:
                    print(f"    - Hijo: {child.tag}")
                    print(f"      Atributos: {child.attrib}")
        
        print("\nBUSCANDO NODOS CON 'COMPLEMENTO':")
        for elem in root.iter():
            if 'complemento' in elem.tag.lower():
                print(f"\n  Tag: {elem.tag}")
                # Mostrar hijos del complemento
                for child in elem:
                    print(f"    - Hijo: {child.tag}")
                    if 'local' in child.tag.lower():
                        print(f"      ¡ENCONTRADO IMPUESTO LOCAL!")
                        print(f"      Atributos: {child.attrib}")
                        for subchild in child:
                            print(f"        -- {subchild.tag}: {subchild.attrib}")
        
        break

if not found:
    print(f"❌ No se encontró el archivo XML para UUID: {uuid}")
    print(f"\nArchivos en {xml_dir}:")
    for f in os.listdir(xml_dir)[:10]:
        print(f"  - {f}")
