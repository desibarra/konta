from django.db import models
from django.contrib.auth.models import User
import uuid as uuid_lib

class Empresa(models.Model):
    REGIMENES_FISCALES = (
        ('601', 'General de Ley Personas Morales'),
        ('603', 'Personas Morales con Fines No Lucrativos'),
        ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
        ('606', 'Arrendamiento'),
        ('607', 'Régimen de Enajenación o Adquisición de Bienes'),
        ('608', 'Demás ingresos'),
        ('610', 'Residentes en el Extranjero sin Establecimiento Permanente en México'),
        ('611', 'Ingresos por Dividendos (socios y accionistas)'),
        ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
        ('614', 'Ingresos por intereses'),
        ('615', 'Régimen de los ingresos por obtención de premios'),
        ('616', 'Sin obligaciones fiscales'),
        ('620', 'Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
        ('621', 'Incorporación Fiscal'),
        ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
        ('623', 'Opcional para Grupos de Sociedades'),
        ('624', 'Coordinados'),
        ('625', 'Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
        ('626', 'Régimen Simplificado de Confianza (RESICO) - Personas Físicas'),
        ('628', 'Régimen Simplificado de Confianza (RESICO) - Personas Morales'),
        ('629', 'Régimen de los ingresos por hidrocarburos'),
        ('630', 'Régimen de Enajenación de acciones en Bolsa de Valores'),
    )

    nombre = models.CharField(max_length=200)
    rfc = models.CharField(max_length=13, unique=True)
    regimen_fiscal = models.CharField(
        max_length=3,
        choices=REGIMENES_FISCALES,
        blank=True,
        help_text="Selecciona el régimen fiscal según el SAT"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre} ({self.rfc})"

    class Meta:
        verbose_name_plural = "Empresas"


class CuentaContable(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cuentas')
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=200)
    es_deudora = models.BooleanField(default=True)  # Naturaleza deudora
    
    class Meta:
        unique_together = ('empresa', 'codigo')
        verbose_name_plural = "Cuentas Contables"
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.empresa.rfc})"


class Factura(models.Model):
    TIPO_CHOICES = (
        ('I', 'Ingreso'),
        ('E', 'Egreso'),
        ('T', 'Traslado'),
        ('N', 'Nómina'),
        ('P', 'Pago'),
    )
    
    NATURALEZA_CHOICES = (
        ('I', 'Ingreso'),
        ('E', 'Egreso'),
        ('C', 'Control/Neutro'),
    )
    ESTADO_CONTABLE_CHOICES = (
        ('PENDIENTE', 'Pendiente'),
        ('CONTABILIZADA', 'Contabilizada'),
        ('EXCLUIDA', 'Excluida'),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='facturas')
    uuid = models.UUIDField(unique=True)
    fecha = models.DateTimeField()
    emisor_rfc = models.CharField(max_length=13)
    emisor_nombre = models.CharField(max_length=300)
    receptor_rfc = models.CharField(max_length=13)
    receptor_nombre = models.CharField(max_length=300)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_impuestos_trasladados = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_impuestos_retenidos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    
    tipo_comprobante = models.CharField(max_length=1, choices=TIPO_CHOICES)
    
    # Nuevo: Clasificación Contable Persistente
    naturaleza = models.CharField(max_length=1, choices=NATURALEZA_CHOICES, default='C')
    estado_contable = models.CharField(max_length=15, choices=ESTADO_CONTABLE_CHOICES, default='PENDIENTE')
    
    archivo_xml = models.FileField(upload_to='xmls/', null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('empresa', 'uuid')
        verbose_name_plural = "Facturas"
    
    def __str__(self):
        return f"{self.uuid} - {self.naturaleza} - {self.total}"


class Concepto(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='conceptos')
    clave_prod_serv = models.CharField(max_length=20, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    descripcion = models.CharField(max_length=1000)
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=2)
    importe = models.DecimalField(max_digits=14, decimal_places=2)
    impuestos_trasladados = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    def __str__(self):
        return self.descripcion[:50]


class Poliza(models.Model):
    factura = models.OneToOneField(Factura, on_delete=models.CASCADE, related_name="poliza")
    fecha = models.DateField()
    descripcion = models.CharField(max_length=500)
    creada_en = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Póliza {self.id} - {self.factura}"
    
    @property
    def total_debe(self):
        return sum(m.debe for m in self.movimientos.all())
        
    @property
    def total_haber(self):
        return sum(m.haber for m in self.movimientos.all())


class MovimientoPoliza(models.Model):
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, related_name='movimientos')
    cuenta = models.ForeignKey(CuentaContable, on_delete=models.PROTECT)
    debe = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    haber = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descripcion = models.CharField(max_length=300, blank=True)
    
    def __str__(self):
        return f"{self.cuenta.codigo} - Debe: {self.debe} Haber: {self.haber}"
