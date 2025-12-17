from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from core.models import Factura, Poliza, MovimientoPoliza
from core.services.accounting_service import AccountingService
from core.decorators import require_active_empresa
from decimal import Decimal

@login_required
@require_active_empresa
def detalle_contable_xml(request, uuid):
    """Vista para mostrar el detalle contable de un XML"""
    empresa = request.empresa
    
    factura = get_object_or_404(Factura, uuid=uuid, empresa=empresa)
    
    # Buscar póliza asociada
    try:
        poliza = Poliza.objects.get(factura=factura)
        movimientos = MovimientoPoliza.objects.filter(poliza=poliza).select_related('cuenta').order_by('id')
        
        total_debe = sum(mov.debe for mov in movimientos)
        total_haber = sum(mov.haber for mov in movimientos)
        diferencia = total_debe - total_haber
        
    except Poliza.DoesNotExist:
        poliza = None
        movimientos = []
        total_debe = Decimal('0')
        total_haber = Decimal('0')
        diferencia = Decimal('0')
    
    context = {
        'factura': factura,
        'poliza': poliza,
        'movimientos': movimientos,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'diferencia': diferencia,
    }
    
    return render(request, 'core/detalle_contable_xml.html', context)


@login_required
@require_active_empresa
def descontabilizar_factura(request, uuid):
    """Elimina la póliza de una factura para poder regenerarla"""
    empresa = request.empresa
    factura = get_object_or_404(Factura, uuid=uuid, empresa=empresa)
    
    try:
        poliza = Poliza.objects.get(factura=factura)
        poliza.delete()  # Esto eliminará también los MovimientoPoliza por CASCADE
        
        factura.estado_contable = 'PENDIENTE'
        factura.save()
        
        messages.success(request, f'Factura {factura.folio} descontabilizada correctamente.')
    except Poliza.DoesNotExist:
        messages.warning(request, 'Esta factura no estaba contabilizada.')
    
    return redirect('detalle_contable_xml', uuid=uuid)
