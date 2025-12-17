"""
Benchmark script para medir el rendimiento de la Balanza de Comprobación
"""
import os
import django
import time
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konta.settings')
django.setup()

from datetime import date
from core.models import Empresa
from core.services.reportes_engine import ReportesEngine

def benchmark_balanza():
    """Mide el tiempo de ejecución de la Balanza de Comprobación"""
    
    # Obtener primera empresa
    empresa = Empresa.objects.first()
    if not empresa:
        print("❌ No hay empresas en la base de datos")
        return
    
    # Periodo de prueba (año completo 2025)
    fecha_inicio = date(2025, 1, 1)
    fecha_fin = date(2025, 12, 31)
    
    print("=" * 60)
    print("BENCHMARK: Balanza de Comprobación")
    print("=" * 60)
    print(f"Empresa: {empresa.nombre} ({empresa.rfc})")
    print(f"Periodo: {fecha_inicio} a {fecha_fin}")
    print("-" * 60)
    
    # Ejecutar benchmark
    start = time.time()
    cuentas = ReportesEngine.obtener_balanza_comprobacion(empresa, fecha_inicio, fecha_fin)
    
    # Forzar ejecución de la query
    count = len(list(cuentas))
    
    end = time.time()
    elapsed = end - start
    
    # Resultados
    print(f"\n📊 RESULTADOS:")
    print(f"   Cuentas retornadas: {count}")
    print(f"   Tiempo de ejecución: {elapsed:.3f} segundos")
    print(f"   Objetivo: < 1.0 segundo")
    print("-" * 60)
    
    if elapsed < 1.0:
        print(f"✅ ÉXITO - Rendimiento óptimo ({elapsed:.3f}s < 1.0s)")
    elif elapsed < 2.0:
        print(f"⚠️  ACEPTABLE - Cerca del objetivo ({elapsed:.3f}s)")
    else:
        print(f"❌ LENTO - Requiere más optimización ({elapsed:.3f}s)")
    
    print("=" * 60)
    
    return elapsed, count

if __name__ == '__main__':
    benchmark_balanza()
