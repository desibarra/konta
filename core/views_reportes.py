from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from datetime import date, timedelta
from core.models import Empresa
from core.services.reportes_engine import ReportesEngine
from core.services.contabilidad_engine import ContabilidadEngine
from .decorators import require_active_empresa

@login_required
@require_active_empresa
def reporte_balanza(request):
    """Vista para generar la Balanza de Comprobación"""
    empresa = request.empresa
    
    # Manejo de fechas default (mes actual)
    today = date.today()
    default_start = today.replace(day=1)
    # Calculo fin de mes
    next_month = today.replace(day=28) + timedelta(days=4)
    default_end = next_month - timedelta(days=next_month.day)

    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    fecha_inicio = parse_date(fecha_inicio_str) if fecha_inicio_str else default_start
    fecha_fin = parse_date(fecha_fin_str) if fecha_fin_str else default_end

    # Llamada al motor
    cuentas = ReportesEngine.obtener_balanza_comprobacion(empresa, fecha_inicio, fecha_fin)
    
    # PROTECCIÓN CONTRA NONETYPE
    if cuentas is None:
        cuentas = []
    
    # Asegurar orden por código en el queryset (si es queryset)
    if hasattr(cuentas, 'order_by'):
        try:
            cuentas = cuentas.order_by('codigo')
        except Exception:
            pass

    # Normalizar la salida: crear objetos simples con valores numéricos
    from types import SimpleNamespace
    from decimal import Decimal

    cuentas_list = []
    for c in cuentas:
        md = c.movimientos_debe if hasattr(c, 'movimientos_debe') else 0
        mh = c.movimientos_haber if hasattr(c, 'movimientos_haber') else 0
        si = c.saldo_inicial if hasattr(c, 'saldo_inicial') else 0
        sf = c.saldo_final if hasattr(c, 'saldo_final') else 0
        # Nivel: preferir campo `nivel` del modelo; si no existe, inferir desde el código
        nivel_raw = getattr(c, 'nivel', None)
        nivel_val = None
        if nivel_raw is not None:
            try:
                nivel_val = int(nivel_raw)
            except Exception:
                nivel_val = None
        if nivel_val is None:
            codigo = getattr(c, 'codigo', '') or ''
            # Inferir por cantidad de guiones: 0 -> nivel 1, 1 -> nivel 2, >=2 -> nivel 3
            parts = [p for p in codigo.split('-') if p]
            if len(parts) <= 1:
                nivel_val = 1
            elif len(parts) == 2:
                nivel_val = 2
            else:
                nivel_val = 3

        # Asegurar tipos numéricos (Decimal preferible)
        def _to_decimal(v):
            if v is None:
                return Decimal('0')
            if isinstance(v, Decimal):
                return v
            try:
                return Decimal(str(v))
            except Exception:
                return Decimal('0')

        obj = SimpleNamespace(
            id=getattr(c, 'id', None),
            codigo=getattr(c, 'codigo', ''),
            nombre=getattr(c, 'nombre', ''),
            nivel=nivel_val,
            saldo_inicial=_to_decimal(si),
            movimientos_debe=_to_decimal(md),
            movimientos_haber=_to_decimal(mh),
            saldo_final=_to_decimal(sf),
            es_deudora=getattr(c, 'es_deudora', False)
        )
        cuentas_list.append(obj)

    # Ordenar estrictamente por código
    cuentas_list = sorted(cuentas_list, key=lambda x: (str(x.codigo) or ''))

    total_debe = sum(c.movimientos_debe for c in cuentas_list) if cuentas_list else Decimal('0')
    total_haber = sum(c.movimientos_haber for c in cuentas_list) if cuentas_list else Decimal('0')

    context = {
        'cuentas': cuentas_list,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'total_debe': total_debe,
        'total_haber': total_haber,
    }
    return render(request, 'reportes/balanza.html', context)

@login_required
@require_active_empresa
def reporte_estado_resultados(request):
    """Vista para generar Estado de Resultados"""
    empresa = request.empresa
    
    today = date.today()
    default_start = today.replace(day=1)
    default_end = today
    
    f_ini = request.GET.get('fecha_inicio')
    f_fin = request.GET.get('fecha_fin')
    
    fecha_inicio = parse_date(f_ini) if f_ini else default_start
    fecha_fin = parse_date(f_fin) if f_fin else default_end
    
    # Llamada al motor principal para listas y detalles
    data = ContabilidadEngine.obtener_resultados(empresa, fecha_inicio, fecha_fin)

    # PROTECCIÓN CONTRA NONETYPE
    if data is None:
        data = {'ingresos': [], 'egresos': [], 'total_ingresos': 0, 'total_egresos': 0, 'utilidad_neta': 0}

    # Unificar cálculo de utilidad vía ReportesEngine (DRY)
    calc = ReportesEngine.calcular_utilidad_neta(empresa, fecha_inicio, fecha_fin)

    context = {
        'empresa': empresa,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'ingresos': data.get('ingresos', []),
        'egresos': data.get('egresos', []),
        'total_ingresos': calc.get('total_ingresos', data.get('total_ingresos', 0)),
        'total_egresos': calc.get('total_egresos', data.get('total_egresos', 0)),
        'utilidad_neta': calc.get('utilidad_neta', data.get('utilidad_neta', 0)),
    }
    return render(request, 'reportes/estado_resultados.html', context)

@login_required
@require_active_empresa
def reporte_balance_general(request):
    """Vista para generar Balance General"""
    empresa = request.empresa
    
    today = date.today()
    fecha_corte_str = request.GET.get('fecha_corte')
    fecha_corte = parse_date(fecha_corte_str) if fecha_corte_str else today
    
    # Llamada al motor
    balance = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)

    # PROTECCIÓN: Inicializar estructura vacía si falla
    if balance is None:
        balance = {
            'activos': [], 'pasivos': [], 'capital': [], 
            'total_activo': 0, 'total_pasivo': 0, 'total_capital': 0, 
            'capital_contribuido': [], 'utilidad_ejercicio': 0,
            'cuadra': False, 'diferencia': 0
        }

    # VERIFICACIÓN: calcular la Utilidad acumulada del ejercicio usando la misma
    # lógica que el Estado de Resultados. Si el usuario solicita "al 31-Dic",
    # usamos desde 1-Ene del mismo año hasta la fecha de corte.
    anio = fecha_corte.year
    fecha_inicio_ejercicio = date(anio, 1, 1)
    calc = ReportesEngine.calcular_utilidad_neta(empresa, fecha_inicio_ejercicio, fecha_corte)

    # Calcular totales numéricos a partir de las estructuras devueltas por el motor
    capital_list = balance.get('capital_contribuido') or []
    try:
        total_capital_contribuido = sum((getattr(c, 'saldo', c) for c in capital_list), 0)
    except Exception:
        total_capital_contribuido = balance.get('total_capital', balance.get('capital_contribuido', 0)) or 0

    total_activo = balance.get('total_activo', 0)
    total_pasivo = balance.get('total_pasivo', 0)

    utilidad_ejercicio = calc.get('utilidad_neta', balance.get('utilidad_ejercicio', 0))

    total_capital = total_capital_contribuido + utilidad_ejercicio

    suma_pasivo_capital = total_pasivo + total_capital
    diferencia = total_activo - suma_pasivo_capital
    cuadra = abs(diferencia) < 0.1

    context = {
        'empresa': empresa,
        'fecha_corte': fecha_corte.strftime('%Y-%m-%d'),
        # Pass lists to the template (template iterates over these)
        'activos': balance.get('activos', []),
        'pasivos': balance.get('pasivos', []),
        'capital_contribuido': capital_list,
        # Totals for display
        'total_capital_contribuido': total_capital_contribuido,
        'utilidad_ejercicio': utilidad_ejercicio,
        'total_activo': total_activo,
        'total_pasivo': total_pasivo,
        'total_capital': total_capital,
        'cuadra_ok': cuadra,
        'diferencia': diferencia
    }
    return render(request, 'reportes/balance_general.html', context)
