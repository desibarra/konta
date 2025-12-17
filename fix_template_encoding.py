# -*- coding: utf-8 -*-
"""
Script para corregir el error de sintaxis en detalle_contable_xml.html
"""

file_path = r'c:\Users\desib\Documents\app_Konta\templates\core\detalle_contable_xml.html'

# Leer el archivo con encoding correcto
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    # Si falla UTF-8, intentar con latin-1
    with open(file_path, 'r', encoding='latin-1') as f:
        content = f.read()

# Reemplazar el error de sintaxis
content = content.replace("codigo=='702-99'", "codigo == '702-99'")

# Guardar con UTF-8
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Archivo corregido exitosamente")
print(f"Verificando cambio...")

# Verificar
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if '702-99' in line:
            print(f"Línea {i}: {line.strip()}")
