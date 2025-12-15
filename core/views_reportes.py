from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from datetime import date, timedelta
from django.contrib import messages
from core.models import Empresa
from core.services.reportes_engine import ReportesEngine
from core.services.contabilidad_engine import ContabilidadEngine
from .decorators import require_active_empresa

@login_required
@require_active_empresa
def reporte_balanza(request):
    """Vista para generar la Balanza de Comprobación"""
    # El decorador require_active_empresa ya asegura que 'empresa' esté en request.
    empresa = request.empresa

    # Manejo de fechas default (mes actual)
    today = date.today()
    default_start = today.replace(day=1)
    next_month = today.replace(day=28) + timedelta(days=4)
    default_end = next_month - timedelta(days=next_month.day)

    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    fecha_inicio = parse_date(fecha_inicio_str) if fecha_inicio_str else default_start
    fecha_fin = parse_date(fecha_fin_str) if fecha_fin_str else default_end

    # Llamada al motor (Compatible Legacy)
    cuentas = ReportesEngine.obtener_balanza_comprobacion(empresa, fecha_inicio, fecha_fin)
    
    # Totales de control
    cuentas_list = list(cuentas)
    total_debe = sum(c.movimientos_debe for c in cuentas_list)
    total_haber = sum(c.movimientos_haber for c in cuentas_list)

    context = {
        'cuentas': cuentas_list,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'total_debe': total_debe,
        'total_haber': total_haber,
    }
    
    return render(request, 'reportes/balanza.html', context)

@login_required
def reporte_estado_resultados(request):
    active_id = request.session.get('active_empresa_id')
    if not active_id:
        # Dashboard ya muestra mensaje global
        return redirect('dashboard')
    
    try:
        empresa = Empresa.objects.get(pk=active_id)
    except Empresa.DoesNotExist:
        return redirect('dashboard')
    
    today = date.today()
    default_start = today.replace(day=1)
    default_end = today
    
    f_ini = request.GET.get('fecha_inicio')
    f_fin = request.GET.get('fecha_fin')
    
    fecha_inicio = parse_date(f_ini) if f_ini else default_start
    fecha_fin = parse_date(f_fin) if f_fin else default_end
    
    # USAR NUEVO MOTOR UNIFICADO
    data = ContabilidadEngine.obtener_resultados(empresa, fecha_inicio, fecha_fin)
    
    context = {
        'empresa': empresa,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'ingresos': data['ingresos'],
        'egresos': data['egresos'],
        'total_ingresos': data['total_ingresos'],
        'total_egresos': data['total_egresos'],
        'utilidad_neta': data['utilidad_neta'],
    }
    return render(request, 'reportes/estado_resultados.html', context)

@login_required
def reporte_balance_general(request):
    active_id = request.session.get('active_empresa_id')
    if not active_id:
        # Dashboard ya muestra mensaje global
        return redirect('dashboard')
    
    try:
        empresa = Empresa.objects.get(pk=active_id)
    except Empresa.DoesNotExist:
        return redirect('dashboard')
    
    # Balance General es a una Fecha de Corte
    today = date.today()
    f_corte = request.GET.get('fecha_corte')
    fecha_corte = parse_date(f_corte) if f_corte else today
    
    # Llamada al motor
    data = ContabilidadEngine.obtener_balance_general(empresa, fecha_corte)
    
    context = {
        'empresa': empresa,
        'fecha_corte': fecha_corte.strftime('%Y-%m-%d'),
        'activos': data['activos'],
        'pasivos': data['pasivos'],
        'capital_contribuido': data['capital_contribuido'],
        'utilidad_ejercicio': data['utilidad_ejercicio'],
        'total_activo': data['total_activo'],
        'total_pasivo': data['total_pasivo'],
        'total_capital': data['total_capital'],
        'cuadra_ok': data['cuadra'],
        'diferencia': data['diferencia']
    }
    return render(request, 'reportes/balance_general.html', context)
