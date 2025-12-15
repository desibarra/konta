from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views_bulk import contabilizar_lote
from .views_reportes import (
    reporte_balanza,
    reporte_estado_resultados,
    reporte_balance_general
)

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
    path('contabilizar-lote/', contabilizar_lote, name='contabilizar_lote'),  # Bulk contabilization
    
    # Reportes
    path('reportes/balanza/', reporte_balanza, name='reporte_balanza'),
    path('reportes/estado-resultados/', reporte_estado_resultados, name='reporte_estado_resultados'),
    path('reportes/balance-general/', reporte_balance_general, name='reporte_balance_general'),
]
