"""
Vista para contabilización masiva (bulk) de facturas.

Permite seleccionar múltiples facturas y contabilizarlas en lote,
usando el patrón de iteración resiliente.
"""

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.contrib import messages
from core.models import Factura, UsuarioEmpresa
from core.services.accounting_service import AccountingService
from core.decorators import require_active_empresa
import logging

logger = logging.getLogger(__name__)


@login_required
@require_active_empresa
@require_http_methods(["POST"])
def contabilizar_lote(request):
    """
    Contabiliza múltiples facturas seleccionadas.
    
    Patrón Resiliente:
    - Si una factura falla, las demás continúan
    - Logging detallado en servidor
    - Mensajes consolidados para usuario
    
    POST Parameters:
        factura_ids: Lista de UUIDs de facturas a contabilizar
    """
    empresa = request.empresa
    
    # Validar permisos (solo Admin/Contador)
    try:
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
        if ue.rol == 'lectura':
            messages.error(request, "⛔ Rol de Lectura no permite contabilizar.")
            return redirect('bandeja_contabilizacion')
    except UsuarioEmpresa.DoesNotExist:
        messages.error(request, "⛔ No tienes permisos para esta empresa.")
        return redirect('bandeja_contabilizacion')
    
    # Obtener UUIDs seleccionados
    factura_ids = request.POST.getlist('factura_ids')
    
    if not factura_ids:
        messages.error(request, "📋 No seleccionaste ninguna factura.")
        return redirect('bandeja_contabilizacion')
    
    # Contadores
    total = len(factura_ids)
    contabilizadas = 0
    ya_contabilizadas = 0
    errores = 0
    errores_detalle = []
    
    logger.info(f"🚀 Contabilización masiva: {total} facturas para {empresa.nombre}")
    
    # ITERACIÓN RESILIENTE (PATRÓN CRÍTICO)
    for idx, uuid in enumerate(factura_ids, 1):
        try:
            # Obtener factura
            factura = Factura.objects.get(uuid=uuid, empresa=empresa)
            
            # Validar estado
            if factura.estado_contable == 'CONTABILIZADA':
                ya_contabilizadas += 1
                logger.info(f"ℹ️ [{idx}/{total}] Ya contabilizada: {factura.uuid}")
                continue
            
            if factura.estado_contable == 'EXCLUIDA':
                logger.warning(f"⚠️ [{idx}/{total}] Excluida: {factura.uuid}")
                continue
            
            # Contabilizar usando AccountingService
            poliza = AccountingService.contabilizar_factura(
                factura.uuid,
                usuario_id=request.user.id
            )
            
            contabilizadas += 1
            logger.info(
                f"✅ [{idx}/{total}] Contabilizada: {factura.uuid} "
                f"(Póliza #{poliza.id})"
            )
            
        except Factura.DoesNotExist:
            errores += 1
            logger.error(f"❌ [{idx}/{total}] Factura no encontrada: {uuid}")
            if len(errores_detalle) < 5:
                errores_detalle.append(f"{uuid[:8]}: No encontrada")
                
        except Exception as e:
            errores += 1
            logger.error(
                f"❌ [{idx}/{total}] Error contabilizando {uuid}: {str(e)}",
                exc_info=True
            )
            if len(errores_detalle) < 5:
                errores_detalle.append(f"{uuid[:8]}: {str(e)[:80]}")
    
    # Log final
    logger.info(
        f"🏁 Contabilización masiva completada: "
        f"{contabilizadas} nuevas, {ya_contabilizadas} ya existían, {errores} errores"
    )
    
    # MENSAJES CONSOLIDADOS PARA USUARIO
    if contabilizadas > 0:
        messages.success(
            request,
            f"✅ {contabilizadas} factura(s) contabilizada(s) correctamente."
        )
    
    if ya_contabilizadas > 0:
        messages.info(
            request,
            f"ℹ️ {ya_contabilizadas} factura(s) ya estaban contabilizadas (omitidas)."
        )
    
    if errores > 0:
        error_msg = f"⚠️ {errores} factura(s) no pudieron contabilizarse."
        
        if errores_detalle:
            error_msg += "\n\n📋 Primeros errores:\n• " + "\n• ".join(errores_detalle)
        
        if errores > 5:
            error_msg += f"\n\n📊 ({errores - 5} errores adicionales en logs del servidor)"
        
        messages.warning(request, error_msg)
    
    # Mensaje especial si TODOS fallaron
    if errores == total and total > 0:
        messages.error(
            request,
            "🚨 NINGUNA factura pudo contabilizarse. Revisa los logs del servidor."
        )
    
    return redirect('bandeja_contabilizacion')
