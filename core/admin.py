from django.contrib import admin
from .models import Empresa, CuentaContable, Factura, Concepto, Poliza, MovimientoPoliza

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'regimen_fiscal', 'fecha_creacion')
    search_fields = ('nombre', 'rfc')

@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'codigo', 'nombre', 'es_deudora')
    list_filter = ('empresa', 'es_deudora')
    search_fields = ('codigo', 'nombre', 'empresa__nombre')

class ConceptoInline(admin.TabularInline):
    model = Concepto
    extra = 0
    readonly_fields = ('descripcion', 'importe', 'clave_prod_serv')

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'empresa', 'fecha', 'emisor_nombre', 'total', 'tipo_comprobante')
    list_filter = ('empresa', 'tipo_comprobante', 'fecha')
    search_fields = ('uuid', 'emisor_nombre', 'empresa__nombre')
    inlines = [ConceptoInline]
    date_hierarchy = 'fecha'

class MovimientoInline(admin.TabularInline):
    model = MovimientoPoliza
    extra = 0

@admin.register(Poliza)
class PolizaAdmin(admin.ModelAdmin):
    list_display = ('id', 'factura', 'fecha', 'descripcion', 'total_debe', 'total_haber')
    list_filter = ('factura__empresa', 'fecha')
    inlines = [MovimientoInline]
