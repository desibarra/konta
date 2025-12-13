from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Sum, Q
from django.http import FileResponse
from .forms import UploadXMLForm
from .services.xml_processor import procesar_xml_cfdi
from .models import Factura, Empresa, CuentaContable

@login_required
def upload_xml(request):
    if request.method == 'POST':
        form = UploadXMLForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.cleaned_data['empresa']
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
    return render(request, 'core/upload.html', {'form': form})

@login_required
def carga_masiva_xml(request):
    if request.method == "POST":
        empresa_id = request.POST.get("empresa")
        files = request.FILES.getlist("xmls")
        
        if not empresa_id:
            messages.error(request, "Debe seleccionar una empresa.")
            return redirect("carga_masiva_xml")
            
        empresa = get_object_or_404(Empresa, pk=empresa_id)
        
        procesados = 0
        duplicados = 0
        errores = 0
        
        if not files:
             messages.error(request, "Debe seleccionar al menos un archivo XML.")
             return redirect("carga_masiva_xml")

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
                # We could log the specific error per file if needed
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error procesando {file.name}: {e}")
        
        if procesados > 0:
            messages.success(request, f"✅ Se procesaron {procesados} facturas correctamente.")
        
        if duplicados > 0:
            messages.info(request, f"ℹ️ {duplicados} facturas ya existían (se validaron y no se duplicaron).")
            
        if errores > 0:
            messages.warning(request, f"⚠️ {errores} archivos no se pudieron procesar.")
            for err_msg in errors_list:
                messages.error(request, err_msg)
            
        return redirect("dashboard")
    
    empresas = Empresa.objects.all()
    return render(request, "core/carga_masiva_xml.html", {"empresas": empresas})

@method_decorator(login_required, name='dispatch')
class DashboardView(ListView):
    model = Factura
    template_name = 'core/dashboard.html'
    context_object_name = 'facturas'
    paginate_by = 20
    
    def get_queryset(self):
        # Corrección: El modelo Empresa no tiene relación con Usuario. 
        # Se listan todas las empresas disponibles.
        qs = Factura.objects.all().select_related('empresa').order_by('-fecha_subida')
        
        empresa_id = self.request.GET.get('empresa')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        empresa_id_str = self.request.GET.get('empresa')
        empresa_id_seleccionada = None
        if empresa_id_str and empresa_id_str.isdigit():
             empresa_id_seleccionada = int(empresa_id_str)
        
        # Construir lista segura para el template
        empresas_select = []
        # Corrección: Mostrar todas las empresas ya que no hay filtro de usuario
        mis_empresas = Empresa.objects.all()
        
        for emp in mis_empresas:
            empresas_select.append({
                'id': emp.id,
                'nombre': emp.nombre,
                'rfc': emp.rfc,
                'selected': (emp.id == empresa_id_seleccionada)
            })
        
        context['empresas_select'] = empresas_select
        context['empresa_id_seleccionada'] = empresa_id_seleccionada
        
        # Totales Contables (Desde Pólizas)
        from .models import MovimientoPoliza
        
        qs = self.get_queryset()
        
        # Filtro base: Movimientos de Pólizas asociadas a las facturas filtradas
        movs_qs = MovimientoPoliza.objects.filter(poliza__factura__in=qs)

        # Ingresos: Suma de HABER en cuentas de Ingresos (4xx)
        ingresos = movs_qs.filter(
            cuenta__codigo__startswith='4'
        ).aggregate(Sum('haber'))['haber__sum'] or 0
        
        # Egresos: Suma de DEBE en cuentas de Gastos (6xx) y Costos (5xx)
        # Corregido: Usar Q objects para OR lógico en startswith
        egresos = movs_qs.filter(
            Q(cuenta__codigo__startswith='5') | Q(cuenta__codigo__startswith='6')
        ).aggregate(Sum('debe'))['debe__sum'] or 0
        
        context['total_facturas'] = qs.count()
        context['total_ingresos'] = ingresos
        context['total_egresos'] = egresos
        
        return context

@method_decorator(login_required, name='dispatch')
class FacturaDetailView(DetailView):
    model = Factura
    template_name = 'core/factura_detail.html'
    context_object_name = 'factura'
    
    def get_object(self):
        return get_object_or_404(Factura, uuid=self.kwargs['pk'])

@login_required
def descargar_xml(request, pk):
    factura = get_object_or_404(Factura, uuid=pk) # Lookup by UUID
    if not factura.archivo_xml:
        messages.error(request, "El archivo XML no se encuentra en el servidor.")
        return redirect('dashboard')
    
    try:
        response = FileResponse(factura.archivo_xml.open('rb'), content_type='text/xml')
        response['Content-Disposition'] = f'attachment; filename="{factura.uuid}.xml"'
        return response
    except FileNotFoundError:
        messages.error(request, "El archivo físico no existe.")
        return redirect('dashboard')

@login_required
def ver_pdf(request, pk):
    factura = get_object_or_404(Factura, uuid=pk)
    print(f"PDF DATA | ID: {factura.uuid} | CST: {factura.tipo_comprobante} | Subtotal: {factura.subtotal} | ImpTra: {factura.total_impuestos_trasladados} | Total: {factura.total}")
    return render(request, 'core/factura_pdf.html', {'factura': factura})

@login_required
def eliminar_factura(request, pk):
    factura = get_object_or_404(Factura, uuid=pk)
    
    if request.method == 'POST':
        # Eliminar archivo físico si existe
        if factura.archivo_xml:
            try:
                factura.archivo_xml.delete(save=False)
            except Exception:
                pass # Continue delete even if file error
        
        # Eliminar registro (Cascade borra poliza y conceptos)
        factura.delete()
        messages.success(request, "Factura eliminada correctamente.")
        return redirect('dashboard')
    
    # Proteccion contra GET accidental
    # Proteccion contra GET accidental
    return redirect('dashboard')

# --- CONTABILIDAD ---

@method_decorator(login_required, name='dispatch')
class BandejaContabilizacionView(ListView):
    model = Factura
    template_name = 'core/bandeja_contabilizacion.html'
    context_object_name = 'facturas'
    paginate_by = 20
    
    def get_queryset(self):
        # Solo mostrar Facturas Pendientes de Contabilizar
        # Y que NO sean de Control (Excluidas)
        return Factura.objects.filter(
            estado_contable='PENDIENTE'
        ).exclude(naturaleza='C').order_by('fecha')

@login_required
def contabilizar_factura(request, pk):
    from core.services.accounting_service import AccountingService
    
    if request.method == 'POST':
        try:
            poliza = AccountingService.contabilizar_factura(pk)
            messages.success(request, f"Factura contabilizada exitosamente. Póliza #{poliza.id} creada.")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
            
    return redirect('bandeja_contabilizacion')
