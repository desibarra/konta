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
    
    cuentas_list = list(cuentas)
    total_debe = sum(c.movimientos_debe for c in cuentas_list) if cuentas_list else 0
    total_haber = sum(c.movimientos_haber for c in cuentas_list) if cuentas_list else 0

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
    
    # Llamada al motor
    data = ContabilidadEngine.obtener_resultados(empresa, fecha_inicio, fecha_fin)
    
    # PROTECCIÓN CONTRA NONETYPE
    if data is None:
        data = {'ingresos': [], 'egresos': [], 'total_ingresos': 0, 'total_egresos': 0, 'utilidad_neta': 0}

    context = {
        'empresa': empresa,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'ingresos': data.get('ingresos', []),
        'egresos': data.get('egresos', []),
        'total_ingresos': data.get('total_ingresos', 0),
        'total_egresos': data.get('total_egresos', 0),
        'utilidad_neta': data.get('utilidad_neta', 0),
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
            'capital_contribuido': 0, 'utilidad_ejercicio': 0,
            'cuadra': False, 'diferencia': 0
        }
    
    context = {
        'empresa': empresa,
        'fecha_corte': fecha_corte.strftime('%Y-%m-%d'),
        'capital_contribuido': balance.get('capital_contribuido', 0),  # CORREGIDO: balance, no data
        'utilidad_ejercicio': balance.get('utilidad_ejercicio', 0),
        'total_activo': balance.get('total_activo', 0),
        'total_pasivo': balance.get('total_pasivo', 0),
        'total_capital': balance.get('total_capital', 0),
        'cuadra_ok': balance.get('cuadra', False),
        'diferencia': balance.get('diferencia', 0)
    }
    return render(request, 'reportes/balance_general.html', context)
