from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Sum, Q, F
from django.http import FileResponse
from .forms import UploadXMLForm
from .services.xml_processor import procesar_xml_cfdi
from .services.accounting_service import AccountingService
from .models import Factura, Empresa, CuentaContable, UsuarioEmpresa, MovimientoPoliza, Poliza, PlantillaPoliza
from .decorators import require_active_empresa
import logging
import os

logger = logging.getLogger(__name__)

# --- Helper de Sesión ---
def get_active_empresa_id(request):
    """Retorna el ID de la empresa activa desde la sesión"""
    return request.session.get('active_empresa_id')

@login_required
def switch_empresa(request, empresa_id):
    """Cambia la empresa activa en la sesión, validando permisos"""
    print(f"\n🔥 SWITCH_EMPRESA EJECUTADO")
    print(f"   User: {request.user.username}")
    print(f"   Empresa ID: {empresa_id}")
    print(f"   Session antes: {dict(request.session)}")
    
    try:
        # Validar que el usuario tenga acceso a esta empresa
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa__id=empresa_id)
        # Guardar en sesión
        request.session['active_empresa_id'] = ue.empresa.id
        request.session['active_empresa_nombre'] = ue.empresa.nombre
        request.session.modified = True
        
        print(f"   ✅ SESIÓN GUARDADA:")
        print(f"      active_empresa_id: {ue.empresa.id}")
        print(f"      active_empresa_nombre: {ue.empresa.nombre}")
        print(f"   Session después: {dict(request.session)}")
        
        messages.success(request, f"Empresa cambiada a: {ue.empresa.nombre}")
    except UsuarioEmpresa.DoesNotExist:
        print(f"   ❌ ERROR: Usuario no tiene acceso a empresa {empresa_id}")
        messages.error(request, "Acceso denegado a esta empresa.")
    
    next_url = request.META.get('HTTP_REFERER', 'dashboard')
    print(f"   🔄 Redirigiendo a: {next_url}\n")
    return redirect(next_url)

@login_required
@require_active_empresa
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
                    procesar_xml_cfdi(file, file.name, empresa)
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
                _, created = procesar_xml_cfdi(file, file.name, empresa)
                if created:
                    procesados += 1
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
        
        if active_id:
            # Queryset total de la empresa FILTRADO POR FECHAS
            qs_total = Factura.objects.filter(
                empresa_id=active_id,
                fecha__date__gte=fecha_inicio,
                fecha__date__lte=fecha_fin
            )
            
            # Calcular totales SOLO de facturas contabilizadas en el rango
            movs_qs = MovimientoPoliza.objects.filter(
                poliza__factura__in=qs_total,
                poliza__factura__estado_contable='CONTABILIZADA',
                poliza__factura__naturaleza__in=['I', 'E']
            )
            
            totales = movs_qs.values('poliza__factura__naturaleza').annotate(
                total_debe=Sum('debe'),
                total_haber=Sum('haber')
            )
            
            total_ingresos = 0
            total_egresos = 0
            
            for t in totales:
                nat = t['poliza__factura__naturaleza']
                if nat == 'I':
                    total_ingresos += t['total_haber'] or 0
                elif nat == 'E':
                    total_egresos += t['total_debe'] or 0
                    
            context['total_ingresos'] = total_ingresos
            context['total_egresos'] = total_egresos
            context['utilidad_neta'] = total_ingresos - total_egresos
        
        else:
             context['total_ingresos'] = 0
             context['total_egresos'] = 0
             context['utilidad_neta'] = 0

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
    """Vista para eliminar factura"""
    empresa = request.empresa
    
    # Validar Rol (Lectura NO borra)
    ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
    if ue.rol == 'lectura':
        messages.error(request, "Solo administradores o contadores pueden eliminar.")
        return redirect('factura_detail', pk=pk)
    
    factura = get_object_or_404(Factura, uuid=pk, empresa=empresa)
    
    if request.method == 'POST':
        factura.delete()
        messages.success(request, "Factura eliminada correctamente.")
        return redirect('dashboard')
        
    return render(request, 'core/confirm_delete.html', {'object': factura})

@method_decorator(login_required, name='dispatch')
class BandejaContabilizacionView(ListView):
    model = Factura
    template_name = 'core/bandeja_contabilizacion.html'
    context_object_name = 'facturas_pendientes'
    paginate_by = 50

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
