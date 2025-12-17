# -*- coding: utf-8 -*-
"""
Script para corregir encoding UTF-8 en todos los templates
"""
import os
import codecs

templates_dir = r'c:\Users\desib\Documents\app_Konta\templates'

# Correcciones de caracteres comunes
corrections = {
    'InformaciÃ³n': 'Información',
    'pÃ³liza': 'póliza',
    'PÃ³liza': 'Póliza',
    'ContabilizaciÃ³n': 'Contabilización',
    'descripciÃ³n': 'descripción',
    'DescripciÃ³n': 'Descripción',
    'Ã¡': 'á',
    'Ã©': 'é',
    'Ã­': 'í',
    'Ã³': 'ó',
    'Ãº': 'ú',
    'Ã±': 'ñ',
    'Â¿': '¿',
    'Â¡': '¡',
}

files_fixed = 0

for root, dirs, files in os.walk(templates_dir):
    for filename in files:
        if filename.endswith('.html'):
            filepath = os.path.join(root, filename)
            
            try:
                # Leer con diferentes encodings
                content = None
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        with codecs.open(filepath, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except:
                        continue
                
                if content is None:
                    print(f"⚠️  No se pudo leer: {filename}")
                    continue
                
                # Aplicar correcciones
                original_content = content
                for wrong, correct in corrections.items():
                    content = content.replace(wrong, correct)
                
                # Asegurar que tiene meta charset
                if '<meta charset="UTF-8">' not in content and '<head>' in content:
                    content = content.replace('<head>', '<head>\n    <meta charset="UTF-8">')
                
                # Guardar solo si hubo cambios
                if content != original_content:
                    with codecs.open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Corregido: {filename}")
                    files_fixed += 1
            
            except Exception as e:
                print(f"❌ Error en {filename}: {e}")

print(f"\n✅ Total archivos corregidos: {files_fixed}")
