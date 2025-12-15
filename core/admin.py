from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.utils.html import format_html
from django import forms
from .models import Empresa, CuentaContable, Factura, Concepto, Poliza, MovimientoPoliza, UsuarioEmpresa, PlantillaPoliza, PlantillaPoliza
from .forms import MovimientoPolizaFormSet
from decimal import Decimal
from satcfdi.cfdi import CFDI
import logging

logger = logging.getLogger(__name__)

# --- Mixin de Seguridad Multi-Empresa ---
class EmpresaFilterMixin:
    """
    Mixin para filtrar querysets en el Admin según las empresas asignadas al usuario.
    Asume que el modelo tiene un campo 'empresa' o 'factura__empresa' accesible.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Obtener IDs de empresas permitidas
        empresas_ids = UsuarioEmpresa.objects.filter(usuario=request.user).values_list('empresa_id', flat=True)
        
        # Lógica de filtrado según el modelo
        if hasattr(self.model, 'empresa'):
            return qs.filter(empresa__id__in=empresas_ids)
        elif hasattr(self.model, 'factura'): # Caso Poliza
            return qs.filter(factura__empresa__id__in=empresas_ids)
        elif self.model == Empresa: # Caso Empresa
             return qs.filter(id__in=empresas_ids)
            
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restringir dropdowns a empresas permitidas"""
        if request.user.is_superuser:
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        empresas_ids = UsuarioEmpresa.objects.filter(usuario=request.user).values_list('empresa_id', flat=True)

        if db_field.name == "empresa":
            kwargs["queryset"] = Empresa.objects.filter(id__in=empresas_ids)
        elif db_field.name == "factura":
            kwargs["queryset"] = Factura.objects.filter(empresa__id__in=empresas_ids)
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'rol')
    list_filter = ('company__nombre', 'rol') if hasattr(UsuarioEmpresa, 'company') else ('empresa__nombre', 'rol')
    search_fields = ('usuario__username', 'empresa__nombre')

@admin.register(Empresa)
class EmpresaAdmin(EmpresaFilterMixin, admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'regimen_fiscal', 'fecha_creacion')
    search_fields = ('nombre', 'rfc')

@admin.register(CuentaContable)
class CuentaContableAdmin(EmpresaFilterMixin, admin.ModelAdmin):
    list_display = ('empresa', 'codigo', 'nombre', 'es_deudora')
    list_filter = ('empresa', 'es_deudora')
    search_fields = ('codigo', 'nombre', 'empresa__nombre')

class ConceptoInline(admin.TabularInline):
    model = Concepto
    extra = 0
    readonly_fields = ('descripcion', 'importe', 'clave_prod_serv')

@admin.register(Factura)
class FacturaAdmin(EmpresaFilterMixin, admin.ModelAdmin):
    list_display = ('uuid', 'empresa', 'fecha', 'emisor_nombre', 'total', 'tipo_comprobante')
    list_filter = ('empresa', 'tipo_comprobante', 'fecha')
    search_fields = ('uuid', 'emisor_nombre', 'empresa__nombre')
    inlines = [ConceptoInline]
    date_hierarchy = 'fecha'
    
    class Media:
        js = ('admin/js/factura_admin.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('api/parse_xml/', self.admin_site.admin_view(self.parse_xml_api), name='factura-parse-xml'),
        ]
        return custom_urls + urls

    def parse_xml_api(self, request):
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)
        
        xml_file = request.FILES.get('xml_file')
        empresa_id = request.POST.get('empresa_id')
        
        if not xml_file:
            return JsonResponse({'error': 'No XML file'}, status=400)
            
        try:
            cfdi = CFDI.from_file(xml_file)
            xml_file.seek(0)
            
            def get_val(node, key):
                if hasattr(node, key.lower()): return getattr(node, key.lower()) 
                if isinstance(node, dict): return node.get(key)
                try: return node[key]
                except: return None
            
            uuid_str = None
            if hasattr(cfdi, 'complemento') and cfdi.complemento:
                tfd = getattr(cfdi.complemento, 'timbre_fiscal_digital', None)
                if tfd: uuid_str = tfd.uuid
            if not uuid_str:
                try: uuid_str = cfdi['Complemento']['TimbreFiscalDigital']['UUID']
                except: pass

            raw_fecha = get_val(cfdi, 'Fecha')
            fecha_str = ''
            hora_str = '00:00:00'
            
            if raw_fecha:
                s_fecha = str(raw_fecha)
                if 'T' in s_fecha:
                    fecha_part, hora_part = s_fecha.split('T')
                    fecha_str = fecha_part
                    hora_str = hora_part[:8]
                else:
                    fecha_str = s_fecha[:10]
                    if len(s_fecha) > 10:
                        hora_str = s_fecha[11:19]
            
            comprobante_data = {
                'uuid': uuid_str,
                'fecha': fecha_str,
                'hora': hora_str,
                'subtotal': float(get_val(cfdi, 'SubTotal') or 0),
                'descuento': float(get_val(cfdi, 'Descuento') or 0),
                'total': float(get_val(cfdi, 'Total') or 0),
            }

            raw_tipo = str(get_val(cfdi, 'TipoDeComprobante')).upper().strip()
            if raw_tipo.startswith('I'): tipo_norm = 'I'
            elif raw_tipo.startswith('E'): tipo_norm = 'E'
            elif raw_tipo.startswith('P'): tipo_norm = 'P'
            elif raw_tipo.startswith('N'): tipo_norm = 'N'
            elif raw_tipo.startswith('T'): tipo_norm = 'T'
            else: tipo_norm = raw_tipo
            comprobante_data['tipo_comprobante'] = tipo_norm

            emisor = get_val(cfdi, 'Emisor')
            receptor = get_val(cfdi, 'Receptor')
            comprobante_data['emisor_rfc'] = get_val(emisor, 'Rfc')
            comprobante_data['emisor_nombre'] = get_val(emisor, 'Nombre')
            comprobante_data['receptor_rfc'] = get_val(receptor, 'Rfc')
            comprobante_data['receptor_nombre'] = get_val(receptor, 'Nombre')

            naturaleza = 'C'
            if empresa_id:
                try:
                    empresa = Empresa.objects.get(pk=empresa_id)
                    rfc_empresa = empresa.rfc
                    tc = comprobante_data['tipo_comprobante']
                    e_rfc = comprobante_data['emisor_rfc']
                    if tc == 'I':
                        if e_rfc == rfc_empresa: naturaleza = 'I'
                        else: naturaleza = 'E'
                    elif tc == 'E':
                        if e_rfc == rfc_empresa: naturaleza = 'E'
                        else: naturaleza = 'I'
                except Exception as e:
                    logger.error(f"Error nat: {e}")
            
            comprobante_data['naturaleza'] = naturaleza
            
            impuestos = get_val(cfdi, 'Impuestos')
            total_tr = 0
            total_ret = 0
            if impuestos:
                try: total_tr = float(get_val(impuestos, 'TotalImpuestosTrasladados') or 0)
                except: pass
                try: total_ret = float(get_val(impuestos, 'TotalImpuestosRetenidos') or 0)
                except: pass

            comprobante_data['total_tr'] = total_tr
            comprobante_data['total_ret'] = total_ret

            return JsonResponse(comprobante_data)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class MovimientoInline(admin.TabularInline):
    model = MovimientoPoliza
    extra = 1
    formset = MovimientoPolizaFormSet

@admin.register(Poliza)
class PolizaAdmin(EmpresaFilterMixin, admin.ModelAdmin):
    list_display = ('id', 'factura', 'fecha', 'descripcion', 'total_debe', 'total_haber')
    list_filter = ('factura__empresa', 'fecha')
    inlines = [MovimientoInline]
    
    class Media:
        js = ('admin/js/poliza_admin.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('api/factura/<int:pk>/', self.admin_site.admin_view(self.factura_data_api), name='poliza-factura-api'),
        ]
        return custom_urls + urls

    def factura_data_api(self, request, pk):
        try:
            qs = Factura.objects.all()
            if not request.user.is_superuser:
                mis_empresas = UsuarioEmpresa.objects.filter(usuario=request.user).values_list('empresa_id', flat=True)
                qs = qs.filter(empresa__id__in=mis_empresas)

            factura = qs.get(pk=pk)
            
            uuid_short = str(factura.uuid)[:8].upper()
            desc = f"CFDI {uuid_short} | {factura.emisor_nombre} -> {factura.receptor_nombre} | Total ${factura.total:,.2f}"
            
            return JsonResponse({
                'fecha': factura.fecha.date().isoformat(),
                'descripcion': desc
            })
        except Factura.DoesNotExist:
             return JsonResponse({'error': 'Factura no encontrada o sin permiso'}, status=404)

@admin.register(PlantillaPoliza)
class PlantillaPolizaAdmin(EmpresaFilterMixin, admin.ModelAdmin):
    list_display = ('nombre', 'tipo_factura', 'empresa', 'es_default')
    list_filter = ('tipo_factura', 'empresa')
    search_fields = ('nombre', 'empresa__nombre')
    autocomplete_fields = ['cuenta_flujo', 'cuenta_provision', 'cuenta_impuesto']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Nota: autocomplete_fields maneja el filtrado via search.
        # EmpresaFilterMixin se encarga de restringir list_display y querysets generales.
        return form
