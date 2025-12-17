from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views_bulk import contabilizar_lote
from .views_reportes import (
    reporte_balanza,
    reporte_estado_resultados,
    reporte_balance_general,
    reporte_auxiliares
)
from .views_detalle_contable import detalle_contable_xml, descontabilizar_factura
from .views_edicion_poliza import editar_poliza, crear_poliza_manual, validar_cuadre_ajax, obtener_cuentas_ajax

urlpatterns = [
    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Dashboard y Core
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('switch-empresa/<int:empresa_id>/', views.switch_empresa, name='switch_empresa'),
    path('upload/', views.upload_xml, name='upload_xml'),
    path('carga-masiva-xml/', views.carga_masiva_xml, name='carga_masiva_xml'),
    path('factura/<uuid:pk>/', views.detalle_factura, name='factura_detail'),
    path('factura/<uuid:pk>/xml/', views.descargar_xml, name='descargar_xml'),
    path('factura/<uuid:pk>/pdf/', views.ver_pdf, name='ver_pdf'),
    path('factura/<uuid:pk>/delete/', views.eliminar_factura, name='eliminar_factura'),
    
    # Contabilización
    path('contabilidad/bandeja/', views.BandejaContabilizacionView.as_view(), name='bandeja_contabilizacion'),
    path('contabilidad/contabilizar/<uuid:pk>/', views.contabilizar_factura, name='contabilizar_factura'),
    path('contabilidad/detalle/<uuid:uuid>/', detalle_contable_xml, name='detalle_contable_xml'),
    path('contabilidad/descontabilizar/<uuid:uuid>/', descontabilizar_factura, name='descontabilizar_factura'),
    
    # Edición Manual de Pólizas
    path('contabilidad/poliza/<int:poliza_id>/editar/', editar_poliza, name='editar_poliza'),
    path('contabilidad/poliza/crear/', crear_poliza_manual, name='crear_poliza_manual'),
    path('contabilidad/validar-cuadre/', validar_cuadre_ajax, name='validar_cuadre_ajax'),
    path('contabilidad/cuentas/ajax/', obtener_cuentas_ajax, name='obtener_cuentas_ajax'),
    
    path('contabilizar-lote/', contabilizar_lote, name='contabilizar_lote'),  # Bulk contabilization
    path('validar-sat-lote/', views.validar_sat_lote, name='validar_sat_lote'),  # SAT validation
    
    # Reportes
    path('reportes/balanza/', reporte_balanza, name='reporte_balanza'),
    path('reportes/estado-resultados/', reporte_estado_resultados, name='reporte_estado_resultados'),
    path('reportes/balance-general/', reporte_balance_general, name='reporte_balance_general'),
    path('reporte_auxiliares/', reporte_auxiliares, name='reporte_auxiliares'),
    # SAT Cumplimiento
    path('cumplimiento-sat/', views.cumplimiento_sat, name='cumplimiento_sat'),
    path('cumplimiento-sat/download/', views.cumplimiento_sat_download, name='cumplimiento_sat_download'),
    # Exportar Facturas
    path('exportar_facturas/', views.exportar_estado_facturas_a_excel, name='exportar_facturas'),
]
