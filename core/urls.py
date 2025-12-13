from django.urls import path
from .views import (
    upload_xml, DashboardView, FacturaDetailView, carga_masiva_xml, 
    descargar_xml, ver_pdf, eliminar_factura,
    BandejaContabilizacionView, contabilizar_factura
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('upload/', upload_xml, name='upload_xml'),
    path('carga-masiva-xml/', carga_masiva_xml, name='carga_masiva_xml'),
    path('factura/<uuid:pk>/', FacturaDetailView.as_view(), name='factura_detail'),
    path('factura/<uuid:pk>/xml/', descargar_xml, name='descargar_xml'),
    path('factura/<uuid:pk>/pdf/', ver_pdf, name='ver_pdf'),
    path('factura/<uuid:pk>/delete/', eliminar_factura, name='eliminar_factura'),
    
    # Contabilización
    path('contabilidad/bandeja/', BandejaContabilizacionView.as_view(), name='bandeja_contabilizacion'),
    path('contabilidad/contabilizar/<uuid:pk>/', contabilizar_factura, name='contabilizar_factura'),
]
