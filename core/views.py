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
    try:
        # Validar que el usuario tenga acceso a esta empresa
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa__id=empresa_id)
        # Guardar en sesión
        request.session['active_empresa_id'] = ue.empresa.id
        request.session['active_empresa_nombre'] = ue.empresa.nombre
        request.session.modified = True  # Forzar guardado de sesión
        messages.success(request, f"Empresa cambiada a: {ue.empresa.nombre}")
    except UsuarioEmpresa.DoesNotExist:
        messages.error(request, "Acceso denegado a esta empresa.")
    
    # Redirigir a la misma página o al dashboard
    next_url = request.META.get('HTTP_REFERER', 'dashboard')
    return redirect(next_url)

@login_required
def upload_xml(request):
    # Obtener empresa activa de sesión
    active_empresa_id = request.session.get('active_empresa_id')
    if not active_empresa_id:
        # Dashboard ya muestra mensaje global - no duplicar
        return redirect('dashboard')
    
    try:
        empresa = Empresa.objects.get(id=active_empresa_id)
    except Empresa.DoesNotExist:
        messages.error(request, "Empresa no encontrada.")
        return redirect('dashboard')
    
    # Validar Permiso y Rol
    try:
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
        if ue.rol == 'lectura':
            messages.error(request, "Tu rol de Lectura no permite subir archivos.")
            return redirect('dashboard')
    except UsuarioEmpresa.DoesNotExist:
        messages.error(request, "No tienes permiso para cargar en esta empresa.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UploadXMLForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('xml_files')
            procesadas = 0
            errores = 0
            
            for file in files:
                try:
                    procesar_xml_cfdi(file, file.name, empresa)
                    procesadas += 1
                except Exception as e:
                    errores += 1
                    messages.error(request, f"Error en '{file.name}': {str(e)}")
            
            if procesadas > 0:
                messages.success(request, f"✅ {procesadas} facturas procesadas correctamente para {empresa.nombre}.")
            if errores > 0:
                messages.warning(request, f"⚠️ {errores} archivos no pudieron procesarse.")
                
            return redirect('dashboard')
    else:
        form = UploadXMLForm()
    
    return render(request, 'core/upload.html', {
        'form': form,
        'empresa': empresa
    })

@login_required
def carga_masiva_xml(request):
    active_id = get_active_empresa_id(request)
    # Validar contexto
    if not active_id:
        # Dashboard ya muestra mensaje global - no duplicar
        return redirect('dashboard')

    if request.method == "POST":
        # Usar la empresa de la sesión, ignorar POST manipulado
        empresa = get_object_or_404(Empresa, pk=active_id)
        
        # Validar Rol de Escritura
        try:
            ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=empresa)
            if ue.rol == 'lectura':
                 messages.error(request, "Tu rol de Lectura no permite subir archivos.")
                 return redirect('dashboard')
        except UsuarioEmpresa.DoesNotExist:
             return redirect('dashboard')
        
        files = request.FILES.getlist("xmls")
        if not files:
             messages.error(request, "Debe seleccionar al menos un archivo XML.")
             return redirect("carga_masiva_xml")

        procesados = 0
        duplicados = 0
        errores = 0
        errors_list = []

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
                errors_list.append(f"{file.name}: {str(e)}")
                logger.error(f"Error procesando {file.name}: {e}")
        
        if procesados > 0:
            messages.success(request, f"✅ Se procesaron {procesados} facturas correctamente.")
        if duplicados > 0:
            messages.info(request, f"ℹ️ {duplicados} facturas ya existían.")
        if errores > 0:
            messages.warning(request, f"⚠️ {errores} archivos no se pudieron procesar.")
            
        return redirect("dashboard")
    
    return render(request, "core/carga_masiva_xml.html", {})

@method_decorator(login_required, name='dispatch')
class DashboardView(ListView):
    model = Factura
    template_name = 'core/dashboard.html'
    context_object_name = 'facturas'
    paginate_by = 20
    
    def get_queryset(self):
        # Filtro Global por Sesión
        active_id = self.request.session.get('active_empresa_id')
        if not active_id:
            return Factura.objects.none() # Nada visible si no hay empresa activa
            
        return Factura.objects.filter(empresa_id=active_id).select_related('empresa').order_by('-fecha_subida')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        active_id = self.request.session.get('active_empresa_id')
        
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
            # Queryset total de la empresa (sin paginacion)
            qs_total = Factura.objects.filter(empresa_id=active_id)
            
            movs_qs = MovimientoPoliza.objects.filter(
                poliza__factura__in=qs_total,
                poliza__factura__estado_contable='CONTABILIZADA', # Solo lo real
                poliza__factura__naturaleza__in=['I', 'E'] # Solo Ingresos/Egresos
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

@login_required
def detalle_factura(request, uuid):
    active_id = request.session.get('active_empresa_id')
    # Validar que la factura pertenezca a la empresa activa
    factura = get_object_or_404(Factura, uuid=uuid, empresa_id=active_id)
    
    # Validar acceso explicito user-empresa (redundante pero seguro)
    if not UsuarioEmpresa.objects.filter(usuario=request.user, empresa=factura.empresa).exists():
        messages.error(request, "No tienes permiso.")
        return redirect('dashboard')
        
    return render(request, 'core/detalle.html', {'factura': factura})

# --- Vistas Restauradas y Blindadas ---

@login_required
def descargar_xml(request, pk):
    active_id = request.session.get('active_empresa_id')
    if not active_id:
        return redirect('dashboard')
        
    factura = get_object_or_404(Factura, uuid=pk, empresa_id=active_id)
    
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
def ver_pdf(request, pk):
    # Igual que XML, requiere sistema de archivos. Placeholder seguro.
    messages.warning(request, "Visualización PDF pendiente.")
    return redirect('factura_detail', pk=pk)

@login_required
def eliminar_factura(request, pk):
    active_id = request.session.get('active_empresa_id')
    if not active_id: return redirect('dashboard')
        
    active_empresa = get_object_or_404(Empresa, pk=active_id)

    # Validar Rol (Lectura NO borra)
    try:
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=active_empresa)
        if ue.rol == 'lectura':
             messages.error(request, "Solo administradores o contadores pueden eliminar.")
             return redirect('factura_detail', pk=pk)
    except UsuarioEmpresa.DoesNotExist:
         return redirect('dashboard')

    factura = get_object_or_404(Factura, uuid=pk, empresa=active_empresa)
    
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
def contabilizar_factura(request, pk):
    active_id = request.session.get('active_empresa_id')
    if not active_id: return redirect('dashboard')
    
    active_empresa = get_object_or_404(Empresa, pk=active_id)

    # Validar Rol (Lectura NO contabiliza)
    try:
        ue = UsuarioEmpresa.objects.get(usuario=request.user, empresa=active_empresa)
        if ue.rol == 'lectura':
             messages.error(request, "Rol lectura no permite contabilizar.")
             return redirect('bandeja_contabilizacion')
    except UsuarioEmpresa.DoesNotExist:
         return redirect('dashboard')

    factura = get_object_or_404(Factura, uuid=pk, empresa=active_empresa)
    
    try:
        plantilla_id = None
        if request.method == 'POST':
            plantilla_id = request.POST.get('plantilla_id')
            
        poliza = AccountingService.contabilizar_factura(factura.uuid, usuario_id=request.user.id, plantilla_id=plantilla_id)
        messages.success(request, f"Factura contabilizada. Póliza #{poliza.id} creada.")
    except Exception as e:
        messages.error(request, f"Error al contabilizar: {e}")
        
    return redirect('bandeja_contabilizacion')
