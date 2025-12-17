from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Sum, Q, F
from django.db import transaction  # <--- MODIFICACIÓN 1: Importar la funcionalidad de transacciones
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest
from .forms import UploadXMLForm
from .services.xml_processor import procesar_xml_cfdi
from .services.accounting_service import AccountingService
from .models import Factura, Empresa, CuentaContable, UsuarioEmpresa, MovimientoPoliza, Poliza, PlantillaPoliza
from .decorators import require_active_empresa
import logging
import os
from .services.export_service import ExportService
import datetime
import openpyxl
from openpyxl.styles import Alignment

logger = logging.getLogger(__name__)

# --- Helper de Sesión ---
def get_active_empresa_id(request):
    """Retorna el ID de la empresa activa desde la sesión"""
    return request.session.get('active_empresa_id')

@login_required
def switch_empresa(request, empresa_id):
    """Cambia la empresa activa en la sesión, validando permisos"""
    print(f"\n🔥 SWITCH_EMPRESA EJECUTADO")
    print(f"  User: {request.user.username}")
    print(f"  Empresa ID: {empresa_id}")
    print(f"  Session antes: {dict(request.session)}")
    
    try:
        # Validar que el usuario tenga acceso a esta empresa
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa__id=empresa_id)
        # Guardar en sesión
        request.session['active_empresa_id'] = ue.empresa.id
        request.session['active_empresa_nombre'] = ue.empresa.nombre
        request.session.modified = True
        
        print(f"  ✅ SESIÓN GUARDADA:")
        print(f"    active_empresa_id: {ue.empresa.id}")
        print(f"    active_empresa_nombre: {ue.empresa.nombre}")
        print(f"  Session después: {dict(request.session)}")
        
        messages.success(request, f"Empresa cambiada a: {ue.empresa.nombre}")
    except UsuarioEmpresa.DoesNotExist:
        print(f"  ❌ ERROR: Usuario no tiene acceso a empresa {empresa_id}")
        messages.error(request, "Acceso denegado a esta empresa.")
    
    next_url = request.META.get('HTTP_REFERER', 'dashboard')
    print(f"  🔄 Redirigiendo a: {next_url}\n")
    return redirect(next_url)

@login_required
@require_active_empresa
@transaction.atomic # <--- MODIFICACIÓN 2: Transacción Atómica
def upload_xml(request):
    """Vista para subir archivos XML CFDI"""
    # El decorador ya validó permisos e inyectó request.empresa
    empresa = request.empresa
    
    # Validar Permiso y Rol (opcional - ya validado por decorator)
    try:
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
        if ue.rol == 'lectura':
            messages.error(request, "Tu rol de Lectura no permite subir archivos.")
            return redirect('dashboard') # Assuming 'dashboard' is the default redirect
    except UsuarioEmpresa.DoesNotExist:
        messages.error(request, "No tienes permisos en esta empresa.")
        return redirect('dashboard') # Assuming 'dashboard' is the default redirect
    
    if request.method == 'POST':
        form = UploadXMLForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('xml_files')
            procesadas = 0
            errores = 0
            errores_detalle = []

            for file in files:
                try:
                    factura, created = procesar_xml_cfdi(file, file.name, empresa)
                    # Si se creó la factura, intentamos contabilizarla automáticamente
                    if created:
                        try:
                            from . import tasks as task_module
                            task_module.enqueue_contabilizar(factura.uuid, request.user.id)
                            procesadas += 1
                        except Exception as e:
                            errores += 1
                            logger.error(f"Error encolando contabilización {file.name} (UUID={getattr(factura,'uuid',None)}): {e}")
                            if len(errores_detalle) < 5:
                                errores_detalle.append(f"{file.name}: encolado fallido: {str(e)[:100]}")
                    else:
                        # Archivo ya existía (duplicado)
                        # Contamos como procesado para el propósito de upload simple
                        procesadas += 1
                except Exception as e:
                    errores += 1
                    # Log detallado en servidor
                    logger.error(f"Error procesando {file.name}: {str(e)}")
                    # Guardar para resumen (máximo 5 para no saturar UI)
                    if len(errores_detalle) < 5:
                        errores_detalle.append(f"{file.name}: {str(e)[:100]}")

            # Mensajes consolidados profesionales
            if procesadas > 0:
                messages.success(request, f"✅ {procesadas} factura(s) procesada(s) correctamente para {empresa.nombre}.")
            
            if errores > 0:
                error_msg = f"⚠️ {errores} archivo(s) no pudieron procesarse."
                if errores_detalle:
                    error_msg += " Primeros errores: " + "; ".join(errores_detalle)
                if errores > 5:
                    error_msg += f" (y {errores - 5} más - ver logs del servidor)"
                messages.warning(request, error_msg)
                
            return redirect('dashboard')
    else:
        form = UploadXMLForm()
    
    return render(request, 'core/upload.html', {
        'form': form,
        'empresa': empresa
    })

@login_required
@require_active_empresa
def detalle_factura(request, pk):
    """Vista para ver el detalle de una factura"""
    empresa = request.empresa
    
    # Obtener la factura y verificar que pertenece a la empresa activa
    factura = get_object_or_404(Factura, uuid=pk, empresa=empresa)
    
    context = {
        'factura': factura,
    }
    
    return render(request, 'core/factura_detail.html', context)

@login_required
@require_active_empresa
@transaction.atomic # <--- MODIFICACIÓN 3: Transacción Atómica
def carga_masiva_xml(request):
    """Vista para carga masiva de XMLs"""
    empresa = request.empresa
    
    if request.method == "POST":
        # Validar Rol de Escritura
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
        if ue.rol == 'lectura':
            messages.error(request, "Tu rol de Lectura no permite subir archivos.")
            return redirect('dashboard')
        
        files = request.FILES.getlist("xmls")
        if not files:
            messages.error(request, "Debe seleccionar al menos un archivo XML.")
            return redirect("carga_masiva_xml")

        procesados = 0
        duplicados = 0
        errores = 0
        errores_detalle = []

        for file in files:
            try:
                # procesar_xml_cfdi returns (factura, created)
                factura, created = procesar_xml_cfdi(file, file.name, empresa)
                if created:
                    try:
                        from . import tasks as task_module
                        task_module.enqueue_contabilizar(factura.uuid, request.user.id)
                        procesadas += 1
                    except Exception as e:
                        errores += 1
                        logger.error(f"Error encolando contabilización {file.name} (UUID={getattr(factura,'uuid',None)}): {e}")
                        if len(errores_detalle) < 5:
                            errores_detalle.append(f"{file.name}: encolado fallido: {str(e)[:100]}")
                else:
                    duplicados += 1
            except Exception as e:
                errores += 1
                # Log detallado en servidor
                logger.error(f"Error procesando {file.name}: {str(e)}")
                # Guardar para resumen (máximo 5 para no saturar UI)
                if len(errores_detalle) < 5:
                    errores_detalle.append(f"{file.name}: {str(e)[:100]}")
        
        # Mensajes consolidados profesionales
        if procesados > 0:
            messages.success(request, f"✅ {procesados} factura(s) procesada(s) correctamente.")
        if duplicados > 0:
            messages.info(request, f"ℹ️ {duplicados} factura(s) ya existían (duplicadas).")
        if errores > 0:
            error_msg = f"⚠️ {errores} archivo(s) fallaron."
            if errores_detalle:
                error_msg += " Primeros errores: " + "; ".join(errores_detalle)
            if errores > 5:
                error_msg += f" (y {errores - 5} más - revisar logs del servidor)"
            messages.warning(request, error_msg)
            
        return redirect("dashboard")
    
    return render(request, "core/carga_masiva_xml.html", {})

@method_decorator(login_required, name='dispatch')
class DashboardView(ListView):
    model = Factura
    template_name = 'core/dashboard.html'
    context_object_name = 'facturas'
    paginate_by = 20
    
    def get_queryset(self):
        # NO auto-select - usuario DEBE seleccionar manualmente
        active_id = self.request.session.get('active_empresa_id')
        if not active_id:
            return Factura.objects.none()
        
        # Obtener rango de fechas
        fecha_inicio, fecha_fin = self._get_date_range()
        
        # Filtrar por empresa y rango de fechas
        queryset = Factura.objects.filter(
            empresa_id=active_id,
            fecha__date__gte=fecha_inicio,
            fecha__date__lte=fecha_fin
        ).select_related('empresa').order_by('-fecha')
        
        return queryset
    
    def _get_date_range(self):
        """
        Obtiene el rango de fechas desde los parámetros GET.
        Por defecto: mes actual (del 1ro al día de hoy)
        """
        from datetime import date, timedelta
        from django.utils.dateparse import parse_date
        
        today = date.today()
        
        # Leer parámetros GET
        fecha_inicio_str = self.request.GET.get('fecha_inicio')
        fecha_fin_str = self.request.GET.get('fecha_fin')
        
        # Si hay parámetros, usarlos
        if fecha_inicio_str and fecha_fin_str:
            fecha_inicio = parse_date(fecha_inicio_str)
            fecha_fin = parse_date(fecha_fin_str)
            
            # Validar que sean fechas válidas
            if fecha_inicio and fecha_fin:
                return fecha_inicio, fecha_fin
        
        # Default: Mes actual (del 1ro a hoy)
        fecha_inicio = today.replace(day=1)
        fecha_fin = today
        
        return fecha_inicio, fecha_fin
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date, timedelta
        
        active_id = self.request.session.get('active_empresa_id')
        # Exponer objeto Empresa activo (si existe) para plantillas base y controles
        active_empresa_obj = None
        if active_id:
            try:
                active_empresa_obj = Empresa.objects.filter(id=active_id).first()
            except Exception:
                active_empresa_obj = None

        # Nombre a mostrar del usuario
        user_display = getattr(self.request.user, 'get_full_name', None)
        if callable(user_display):
            user_display = self.request.user.get_full_name() or self.request.user.username
        else:
            user_display = self.request.user.username
        
        # Obtener rango de fechas actual
        fecha_inicio, fecha_fin = self._get_date_range()
        
        # Pasar fechas al contexto para mantener valores en inputs
        context['fecha_inicio'] = fecha_inicio.strftime('%Y-%m-%d')
        context['fecha_fin'] = fecha_fin.strftime('%Y-%m-%d')
        
        # Calcular fechas para botones rápidos
        today = date.today()
        
        # Este Mes
        context['preset_este_mes_inicio'] = today.replace(day=1).strftime('%Y-%m-%d')
        context['preset_este_mes_fin'] = today.strftime('%Y-%m-%d')
        
        # Mes Anterior
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        first_day_prev_month = last_day_prev_month.replace(day=1)
        context['preset_mes_anterior_inicio'] = first_day_prev_month.strftime('%Y-%m-%d')
        context['preset_mes_anterior_fin'] = last_day_prev_month.strftime('%Y-%m-%d')
        
        # Este Año
        context['preset_este_anio_inicio'] = today.replace(month=1, day=1).strftime('%Y-%m-%d')
        context['preset_este_anio_fin'] = today.strftime('%Y-%m-%d')
        
        # Todo (últimos 5 años para no sobrecargar)
        context['preset_todo_inicio'] = today.replace(year=today.year - 5, month=1, day=1).strftime('%Y-%m-%d')
        context['preset_todo_fin'] = today.strftime('%Y-%m-%d')
        
        # Determinar qué preset está activo
        context['preset_activo'] = self._get_active_preset(fecha_inicio, fecha_fin)
        
        # Construir selector de empresas (solo las permitidas)
        mis_empresas_rels = UsuarioEmpresa.objects.filter(usuario=self.request.user).select_related('empresa')
        empresas_select = []
        
        for rel in mis_empresas_rels:
            empresas_select.append({
                'id': rel.empresa.id,
                'nombre': rel.empresa.nombre,
                'rfc': rel.empresa.rfc,
                'rol': rel.get_rol_display(),
                'selected': (rel.empresa.id == active_id)
            })
        
        context['empresas_select'] = empresas_select
        context['empresa_id_seleccionada'] = active_id
        # Compatibilidad con base.html y otros templates que esperan estas claves
        context['available_empresas'] = empresas_select
        context['active_empresa'] = active_empresa_obj
        context['user_display_name'] = user_display
        
        if active_id:
            # CAMBIO CRÍTICO: Sumar directamente de Factura (flujo operativo)
            # NO de MovimientoPoliza (solo contabilizadas)
            # Esto permite ver totales INMEDIATAMENTE después de carga masiva
            
            # Queryset filtrado por fechas para totales
            qs_total = Factura.objects.filter(
                empresa_id=active_id,
                fecha__date__gte=fecha_inicio,
                fecha__date__lte=fecha_fin
            )
            
            # INGRESOS: Suma directa de Facturas con naturaleza 'I'
            total_ingresos = qs_total.filter(
                naturaleza='I'
            ).aggregate(
                total=Sum('total')
            )['total'] or 0
            
            # EGRESOS: Suma directa de Facturas con naturaleza 'E'
            total_egresos = qs_total.filter(
                naturaleza='E'
            ).aggregate(
                total=Sum('total')
            )['total'] or 0
            
            # CONTADOR: Total de facturas en el periodo
            total_facturas = qs_total.count()
            
            context['total_ingresos'] = total_ingresos
            context['total_egresos'] = total_egresos
            context['utilidad_neta'] = total_ingresos - total_egresos
            context['total_facturas'] = total_facturas
        
        else:
             context['total_ingresos'] = 0
             context['total_egresos'] = 0
             context['utilidad_neta'] = 0
             context['total_facturas'] = 0

        return context
    
    def _get_active_preset(self, fecha_inicio, fecha_fin):
        """Determina qué preset está activo basado en las fechas"""
        from datetime import date, timedelta
        
        today = date.today()
        
        # Este Mes
        if (fecha_inicio == today.replace(day=1) and fecha_fin == today):
            return 'este_mes'
        
        # Mes Anterior
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        first_day_prev_month = last_day_prev_month.replace(day=1)
        if (fecha_inicio == first_day_prev_month and fecha_fin == last_day_prev_month):
            return 'mes_anterior'
        
        # Este Año
        if (fecha_inicio == today.replace(month=1, day=1) and fecha_fin == today):
            return 'este_anio'
        
        # Todo (últimos 5 años)
        if (fecha_inicio == today.replace(year=today.year - 5, month=1, day=1)):
            return 'todo'
        
        # Personalizado
        return 'personalizado'


# --- Vistas Restauradas y Blindadas ---

@login_required
@require_active_empresa
def descargar_xml(request, pk):
    """Vista para descargar XML de factura"""
    empresa = request.empresa
    factura = get_object_or_404(Factura, uuid=pk, empresa=empresa)
    
    # Construir ruta (asumiendo guardado en media/xmls/rfc/...)
    # Ajustar según tu lógica real de almacenamiento.
    # Por ahora, usamos una ruta genérica basada en lo que xml_processor haga.
    # Si no se guardó el path, esto puede fallar. Revisa tu modelo Factura.
    # El modelo Factura borró 'archivo_xml' en una migración previa?
    # Revisé las migraciones, 0003 borró 'archivo_xml'. 
    # ENTONCES NO SE PUEDE DESCARGAR EL XML SI NO SE GUARDA.
    # Asumiremos que el usuario quiere ver los datos parseados, o que hay un path reconstruible.
    # Por ahora, enviamos mensaje de "No disponible" si no existe campo.
    messages.warning(request, "Descarga de archivos físicos pendiente de configuración.")
    return redirect('factura_detail', pk=pk)

@login_required
@require_active_empresa
def ver_pdf(request, pk):
    """Vista para ver PDF de factura"""
    # Funcionalidad pendiente de implementación
    messages.warning(request, "Visualización PDF pendiente.")
    return redirect('factura_detail', pk=pk)

@login_required
@require_active_empresa
def eliminar_factura(request, pk):
    """
    Vista para eliminar factura con cascada controlada y auditoría
    
    Proceso:
    1. Validar permisos
    2. Verificar dependencias (póliza contable)
    3. Registrar en auditoría
    4. Eliminar en cascada: Póliza → Movimientos → Factura → Archivo XML
    """
    empresa = request.empresa
    
    # Validar Rol (Lectura NO borra)
    ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
    if ue.rol == 'lectura':
        messages.error(request, "Solo administradores o contadores pueden eliminar.")
        return redirect('factura_detail', pk=pk)
    
    factura = get_object_or_404(Factura, uuid=pk, empresa=empresa)
    
    if request.method == 'POST':
        from django.db import transaction
        from core.models import Poliza, AuditoriaEliminacion
        import os
        
        try:
            with transaction.atomic():
                # 1. Verificar si tiene póliza contable
                tiene_poliza = False
                try:
                    poliza = Poliza.objects.get(factura=factura)
                    tiene_poliza = True
                except Poliza.DoesNotExist:
                    poliza = None
                
                # 2. Crear registro de auditoría ANTES de eliminar
                auditoria = AuditoriaEliminacion.objects.create(
                    uuid_factura=factura.uuid,
                    folio=factura.folio,
                    emisor_nombre=factura.emisor_nombre,
                    receptor_nombre=factura.receptor_nombre,
                    total=factura.total,
                    fecha_factura=factura.fecha,
                    usuario=request.user,
                    tenia_poliza=tiene_poliza,
                    motivo=request.POST.get('motivo', '')
                )
                
                # 3. Eliminar póliza (CASCADE eliminará MovimientoPoliza automáticamente)
                if poliza:
                    poliza.delete()
                
                # 4. Eliminar archivo XML físico si existe
                if factura.archivo_xml:
                    try:
                        if os.path.isfile(factura.archivo_xml.path):
                            os.remove(factura.archivo_xml.path)
                    except Exception as e:
                        # Log pero no fallar si el archivo no existe
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"No se pudo eliminar archivo XML: {e}")
                
                # 5. Eliminar factura de la base de datos
                factura_info = f"{factura.folio} - {factura.emisor_nombre}"
                factura.delete()
                
                messages.success(
                    request, 
                    f"✅ Factura {factura_info} eliminada correctamente. "
                    f"{'Póliza contable también eliminada.' if tiene_poliza else ''}"
                )
                
                return redirect('dashboard')
                
        except Exception as e:
            messages.error(request, f"❌ Error al eliminar factura: {str(e)}")
            return redirect('factura_detail', pk=pk)
    
    # GET: Mostrar confirmación con información de dependencias
    from core.models import Poliza
    
    try:
        poliza = Poliza.objects.get(factura=factura)
        tiene_poliza = True
        num_movimientos = poliza.movimientopoliza_set.count()
    except Poliza.DoesNotExist:
        tiene_poliza = False
        num_movimientos = 0
    
    context = {
        'object': factura,
        'factura': factura,
        'tiene_poliza': tiene_poliza,
        'num_movimientos': num_movimientos,
    }
    
    return render(request, 'core/confirm_delete.html', context)

@method_decorator(login_required, name='dispatch')
class BandejaContabilizacionView(ListView):
    model = Factura
    template_name = 'core/bandeja_contabilizacion.html'
    context_object_name = 'facturas_pendientes'
    paginate_by = 100

    def get_queryset(self):
        active_id = self.request.session.get('active_empresa_id')
        if not active_id:
            return Factura.objects.none()
            
        return Factura.objects.filter(
            empresa_id=active_id,
            estado_contable='PENDIENTE'
        ).order_by('fecha')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_id = self.request.session.get('active_empresa_id')
        if active_id:
            context['plantillas'] = PlantillaPoliza.objects.filter(empresa_id=active_id)
        return context

@login_required
@require_active_empresa
def contabilizar_factura(request, pk):
    """Vista para contabilizar factura"""
    empresa = request.empresa
    
    # Validar Rol (Lectura NO contabiliza)
    ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
    if ue.rol == 'lectura':
        messages.error(request, "Rol lectura no permite contabilizar.")
        return redirect('bandeja_contabilizacion')
    
    factura = get_object_or_404(Factura, uuid=pk, empresa=empresa)
    
    try:
        plantilla_id = None
        if request.method == 'POST':
            plantilla_id = request.POST.get('plantilla_id')
            
        poliza = AccountingService.contabilizar_factura(factura.uuid, usuario_id=request.user.id, plantilla_id=plantilla_id)
        messages.success(request, f"Factura contabilizada. Póliza #{poliza.id} creada.")
    except Exception as e:
        messages.error(request, f"Error al contabilizar: {e}")
        
    return redirect('bandeja_contabilizacion')


@login_required
@require_active_empresa
def validar_sat_lote(request):
    """
    Valida el estatus de facturas seleccionadas contra el SAT
    
    Recibe UUIDs por POST (JSON) y consulta el servicio SOAP del SAT
    para determinar si están Vigentes o Canceladas.
    
    Si una factura está cancelada, elimina sus pólizas y la marca como EXCLUIDA.
    """
    from django.http import JsonResponse
    from django.utils import timezone
    from .services.sat_status import SatStatusValidator
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        # Parsear JSON
        data = json.loads(request.body)
        uuids = data.get('uuids', [])
        
        if not uuids:
            return JsonResponse({'success': False, 'error': 'No se proporcionaron UUIDs'}, status=400)
        
        # Obtener empresa activa
        empresa_id = get_active_empresa_id(request)
        if not empresa_id:
            return JsonResponse({'success': False, 'error': 'No hay empresa activa'}, status=400)
        
        # Contadores
        vigentes = 0
        canceladas = 0
        no_encontradas = 0
        errores = 0
        
        # Procesar cada factura
        for uuid_str in uuids:
            try:
                # Buscar factura
                factura = Factura.objects.get(uuid=uuid_str, empresa_id=empresa_id)
                
                # Validar con SAT
                logger.info(f"Validando factura {uuid_str} con SAT...")
                resultado = SatStatusValidator.validar_factura_model(factura)
                
                estado_sat = resultado['estado']
                
                # Actualizar estado en BD
                factura.estado_sat = estado_sat
                factura.ultima_validacion = timezone.now()
                factura.save()
                
                # Contar y tomar acciones
                if estado_sat == 'Vigente':
                    vigentes += 1
                    logger.info(f"✅ Factura {uuid_str}: Vigente")
                
                elif estado_sat == 'Cancelado':
                    canceladas += 1
                    logger.warning(f"❌ Factura {uuid_str}: CANCELADA - Eliminando pólizas")
                    
                    # Eliminar pólizas contables
                    polizas = Poliza.objects.filter(factura=factura)
                    if polizas.exists():
                        MovimientoPoliza.objects.filter(poliza__in=polizas).delete()
                        polizas.delete()
                    
                    # Marcar como excluida
                    factura.estado_contable = 'EXCLUIDA'
                    factura.save()
                
                elif estado_sat == 'No Encontrado':
                    no_encontradas += 1
                    logger.warning(f"⚠️ Factura {uuid_str}: No encontrada en SAT")
                
                else:  # Error
                    errores += 1
                    logger.error(f"❌ Error validando {uuid_str}: {resultado.get('mensaje')}")
            
            except Factura.DoesNotExist:
                errores += 1
                logger.error(f"❌ Factura {uuid_str} no encontrada en BD")
            
            except Exception as e:
                errores += 1
                logger.error(f"❌ Error procesando {uuid_str}: {e}", exc_info=True)
        
        # Respuesta
        return JsonResponse({
            'success': True,
            'vigentes': vigentes,
            'canceladas': canceladas,
            'no_encontradas': no_encontradas,
            'errores': errores,
            'total': len(uuids)
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    
    except Exception as e:
        logger.error(f"Error en validar_sat_lote: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_active_empresa
def cumplimiento_sat(request):
    """Render a simple SAT compliance dashboard with year/month selectors."""
    empresa = request.empresa
    year = int(request.GET.get('year', request.GET.get('y', datetime.date.today().year)))
    month = int(request.GET.get('month', request.GET.get('m', datetime.date.today().month)))
    return render(request, 'core/cumplimiento_sat.html', {
        'empresa': empresa,
        'year': year,
        'month': month,
    })


@login_required
@require_active_empresa
def cumplimiento_sat_download(request):
    """Download generated files. Expects GET params: year, month, doc (balanza/catalogo/polizas), fmt (xml/xlsx/pdf)"""
    empresa = request.empresa
    from django.utils.dateparse import parse_date
    # Prefer explicit fecha_inicio/fecha_fin; fallback to year/month if not provided
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    if fecha_inicio_str and fecha_fin_str:
        fecha_inicio = parse_date(fecha_inicio_str)
        fecha_fin = parse_date(fecha_fin_str)
    else:
        year = int(request.GET.get('year', datetime.date.today().year))
        month = int(request.GET.get('month', datetime.date.today().month))
        # default to full month
        import calendar
        fecha_inicio = datetime.date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        fecha_fin = datetime.date(year, month, last_day)
    doc = request.GET.get('doc')
    fmt = request.GET.get('fmt')

    if not doc or not fmt:
        return HttpResponseBadRequest('doc and fmt are required')

    try:
        if doc == 'balanza':
            if fmt == 'xml':
                bio, filename, content_type = ExportService.generate_balanza_xml(empresa, fecha_inicio, fecha_fin)
                # Validate XML before sending
                try:
                    valid, errors = ExportService.validate_balanza_xml(bio)
                    if not valid:
                        msg = 'XML validation failed: ' + '; '.join(errors[:10])
                        logger.error(msg)
                        return HttpResponseBadRequest(msg)
                    # rewind bio for response
                    bio.seek(0)
                except Exception as e:
                    logger.error(f'Error validating XML: {e}', exc_info=True)
                    return HttpResponseBadRequest(f'Error validating XML: {e}')
            elif fmt == 'xlsx':
                bio, filename, content_type = ExportService.generate_balanza_excel(empresa, fecha_inicio, fecha_fin)
            elif fmt == 'pdf':
                bio, filename, content_type = ExportService.generate_balanza_pdf(empresa, fecha_inicio, fecha_fin)
            else:
                return HttpResponseBadRequest('fmt invalid')
        elif doc == 'catalogo' and fmt == 'xml':
            bio, filename, content_type = ExportService.generate_catalogo_xml(empresa, year, month)
        elif doc == 'polizas' and fmt == 'xml':
            bio, filename, content_type = ExportService.generate_polizas_xml(empresa, year, month)
        else:
            return HttpResponseBadRequest('Unsupported doc/fmt')

        resp = FileResponse(bio, as_attachment=True, filename=filename, content_type=content_type)
        return resp
    except Exception as e:
        logger.error(f"Error generating export {doc}.{fmt} for {empresa}: {e}", exc_info=True)
        return HttpResponseBadRequest(str(e))

@login_required
@require_active_empresa
def exportar_estado_facturas_a_excel(request):
    """Genera un archivo Excel consolidado de todas las facturas."""
    empresa = request.empresa
    facturas = Factura.objects.filter(empresa=empresa).values(
        'uuid', 'fecha', 'emisor_rfc', 'emisor_nombre', 'receptor_rfc', 'receptor_nombre', 'total', 'tipo_comprobante', 'estado_contable'
    )

    # Crear el archivo Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Estado de Facturas"

    # Encabezados
    headers = ["UUID", "Fecha", "RFC Emisor", "Nombre Emisor", "RFC Receptor", "Nombre Receptor", "Total", "Tipo", "Estado"]
    ws.append(headers)

    for col in ws.iter_cols(min_row=1, max_row=1, min_col=1, max_col=len(headers)):
        for cell in col:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Agregar datos
    for factura in facturas:
        ws.append([
            str(factura['uuid']),
            factura['fecha'].strftime('%Y-%m-%d'),
            factura['emisor_rfc'],
            factura['emisor_nombre'],
            factura['receptor_rfc'],
            factura['receptor_nombre'],
            f"{factura['total']:.2f}",
            factura['tipo_comprobante'],
            factura['estado_contable']
        ])

    # Respuesta HTTP con el archivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="estado_facturas_{empresa.nombre}.xlsx"'
    wb.save(response)
    return response