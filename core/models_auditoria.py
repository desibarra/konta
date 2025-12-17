from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class AuditoriaEliminacion(models.Model):
    """
    Registro de auditoría para eliminaciones de XMLs
    """
    uuid_factura = models.UUIDField(verbose_name="UUID del SAT")
    folio = models.CharField(max_length=50, blank=True, null=True)
    emisor_nombre = models.CharField(max_length=255, blank=True, null=True)
    receptor_nombre = models.CharField(max_length=255, blank=True, null=True)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    fecha_factura = models.DateField(null=True, blank=True)
    
    # Auditoría
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='eliminaciones')
    fecha_eliminacion = models.DateTimeField(default=timezone.now)
    motivo = models.TextField(blank=True, null=True)
    tenia_poliza = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'auditoria_eliminacion'
        verbose_name = 'Auditoría de Eliminación'
        verbose_name_plural = 'Auditorías de Eliminación'
        ordering = ['-fecha_eliminacion']
    
    def __str__(self):
        return f"Eliminación {self.uuid_factura} por {self.usuario} el {self.fecha_eliminacion}"
