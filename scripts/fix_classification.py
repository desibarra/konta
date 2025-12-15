
import os
import django
import sys
# Add project root to path
sys.path.append(r'c:\Users\desib\Documents\app_Konta')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from core.models import Factura, Empresa

def run():
    print("Iniciando Migración de Clasificación Contable...")
    
    facturas = Factura.objects.select_related('empresa').all()
    count_ingreso = 0
    count_egreso = 0
    count_control = 0
    
    for f in facturas:
        empresa_rfc = f.empresa.rfc.upper().strip()
        emisor_rfc = f.emisor_rfc.upper().strip()
        receptor_rfc = f.receptor_rfc.upper().strip()
        
        # Lógica espejo de xml_processor.py
        naturaleza = 'C'
        
        # 1. Ingreso: Emisor == Empresa y Tipo I
        if f.tipo_comprobante == 'I' and emisor_rfc == empresa_rfc:
            naturaleza = 'I'
            
        # 2. Egreso: Receptor == Empresa y Tipo I
        elif f.tipo_comprobante == 'I' and receptor_rfc == empresa_rfc:
            naturaleza = 'E'
            
        # 3. Egreso (Dev Em): Emisor == Empresa y Tipo E
        elif f.tipo_comprobante == 'E' and emisor_rfc == empresa_rfc:
            naturaleza = 'E'
            
        # 4. Ingreso (Dev Rec): Receptor == Empresa y Tipo E
        elif f.tipo_comprobante == 'E' and receptor_rfc == empresa_rfc:
            naturaleza = 'I'
            
        # Exclusiones
        if f.tipo_comprobante in ['P', 'N', 'T']:
            naturaleza = 'C'
            
        # Guardar cambios
        f.naturaleza = naturaleza
        f.estado_contable = 'PENDIENTE' if naturaleza in ['I', 'E'] else 'EXCLUIDA'
        f.save()
        
        if naturaleza == 'I': count_ingreso += 1
        elif naturaleza == 'E': count_egreso += 1
        else: count_control += 1
        
        print(f"Factura {f.uuid}: {f.tipo_comprobante} | {emisor_rfc} -> {receptor_rfc} | CLAS: {naturaleza}")

    print("="*40)
    print(f"Migración Completada.")
    print(f"Ingresos: {count_ingreso}")
    print(f"Egresos:  {count_egreso}")
    print(f"Control:  {count_control}")

if __name__ == '__main__':
    run()
