# -*- coding: utf-8 -*-
"""
Script para forzar la corrección del template con encoding correcto
"""
import codecs

file_path = r'c:\Users\desib\Documents\app_Konta\templates\core\detalle_contable_xml.html'

# Leer con diferentes encodings
content = None
for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
    try:
        with codecs.open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        print(f"✅ Archivo leído con encoding: {encoding}")
        break
    except:
        continue

if content is None:
    print("❌ No se pudo leer el archivo")
    exit(1)

# Aplicar todas las correcciones
corrections = [
    ("codigo=='702-99'", "codigo == '702-99'"),
    ("${{ factura.total_impuestos_trasladados|floatformat:2|intcomma\r\n                        }}", "${{ factura.total_impuestos_trasladados|floatformat:2|intcomma }}"),
    ("${{ factura.total_impuestos_trasladados|floatformat:2|intcomma\n                        }}", "${{ factura.total_impuestos_trasladados|floatformat:2|intcomma }}"),
    ("${{ factura.total|floatformat:2|intcomma\r\n                            }}", "${{ factura.total|floatformat:2|intcomma }}"),
    ("${{ factura.total|floatformat:2|intcomma\n                            }}", "${{ factura.total|floatformat:2|intcomma }}"),
]

for old, new in corrections:
    if old in content:
        content = content.replace(old, new)
        print(f"✅ Corregido: {old[:50]}...")

# Guardar con UTF-8 sin BOM
with codecs.open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Archivo guardado con UTF-8")

# Verificar
print("\nVerificando correcciones:")
with codecs.open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if 'IVA Trasladado' in line or 'TOTAL:' in line or '702-99' in line:
            print(f"Línea {i}: {line.strip()[:100]}")
