from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    upload_xml, DashboardView, detalle_factura, carga_masiva_xml, 
    descargar_xml, ver_pdf, eliminar_factura,
    BandejaContabilizacionView, contabilizar_factura, switch_empresa
)
from .views_reportes import reporte_balanza, reporte_estado_resultados, reporte_balance_general

urlpatterns = [
    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Dashboard y Core
    path('', DashboardView.as_view(), name='dashboard'),
    path('switch-empresa/<int:empresa_id>/', switch_empresa, name='switch_empresa'),
    path('upload/', upload_xml, name='upload_xml'),
    path('carga-masiva-xml/', carga_masiva_xml, name='carga_masiva_xml'),
    path('factura/<uuid:pk>/', detalle_factura, name='factura_detail'),
    path('factura/<uuid:pk>/xml/', descargar_xml, name='descargar_xml'),
    path('factura/<uuid:pk>/pdf/', ver_pdf, name='ver_pdf'),
    path('factura/<uuid:pk>/delete/', eliminar_factura, name='eliminar_factura'),
    
    # Contabilización
    path('contabilidad/bandeja/', BandejaContabilizacionView.as_view(), name='bandeja_contabilizacion'),
    path('contabilidad/contabilizar/<uuid:pk>/', contabilizar_factura, name='contabilizar_factura'),
    
    # Reportes
    path('reportes/balanza/', reporte_balanza, name='reporte_balanza'),
    path('reportes/estado-resultados/', reporte_estado_resultados, name='reporte_estado_resultados'),
    path('reportes/balance-general/', reporte_balance_general, name='reporte_balance_general'),
]
