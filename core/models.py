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

class UsuarioEmpresa(models.Model):
    ROLES = (
        ('admin', 'Administrador'),
        ('contador', 'Contador'),
        ('lectura', 'Lectura'),
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='empresas_asignadas')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios_asignados')
    rol = models.CharField(max_length=10, choices=ROLES, default='lectura')
    
    class Meta:
        unique_together = ('usuario', 'empresa')
        verbose_name = "Asignación de Usuario"
        verbose_name_plural = "Usuarios por Empresa"
        
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa.nombre} ({self.get_rol_display()})"


class CuentaContable(models.Model):
    TIPO_CHOICES = (
        ('ACTIVO', 'Activo'),
        ('PASIVO', 'Pasivo'),
        ('CAPITAL', 'Capital'),
        ('INGRESO', 'Ingreso'),
        ('COSTO', 'Costo'),
        ('GASTO', 'Gasto'),
    )
    NATURALEZA_CHOICES = (
        ('D', 'Deudora'),
        ('A', 'Acreedora'),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cuentas')
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=200)
    # Se reemplazará el booleano es_deudora por naturaleza explícita
    # Se recomienda mantener es_deudora como property o migrarlo.
    # Para consistencia con engine nuevo:
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='ACTIVO')
    naturaleza = models.CharField(max_length=1, choices=NATURALEZA_CHOICES, default='D')
    
    es_deudora = models.BooleanField(default=True)  # Legacy
    
    # CAMPOS SAT ANEXO 24 (Subcuentas Automáticas)
    agrupador_sat = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Código agrupador SAT Anexo 24 (ej: 101.01). DEBE heredarse a subcuentas."
    )
    codigo_sat = models.CharField(max_length=20, blank=True, null=True, db_index=True, help_text='Código agrupador SAT (Anexo 24)')
    nivel = models.IntegerField(
        default=1,
        choices=[(1, 'Mayor'), (2, 'Subcuenta'), (3, 'Auxiliar')],
        help_text="Nivel jerárquico: 1=Mayor, 2=Subcuenta, 3=Auxiliar"
    )
    padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcuentas',
        help_text="Cuenta padre (solo para subcuentas nivel 2 y auxiliares nivel 3)"
    )
    rfc_tercero = models.CharField(
        max_length=13,
        blank=True,
        null=True,
        db_index=True,
        help_text="RFC del cliente/proveedor (para subcuentas específicas por tercero)"
    )

    class Meta:
        unique_together = ('empresa', 'codigo')
        verbose_name_plural = "Cuentas Contables"
        indexes = [
            models.Index(fields=['empresa', 'rfc_tercero']),
            models.Index(fields=['empresa', 'padre']),
        ]

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
    uuid = models.UUIDField(unique=True, db_index=True)  # ← CRÍTICO: unique=True previene duplicados
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
    
    # Nuevo: UsoCFDI del SAT para clasificación automática de gastos/inversiones
    uso_cfdi = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        default='G03',
        help_text='Código de Uso de CFDI del SAT (G01, G03, I04, etc.)'
    )
    
    # Validación SAT
    estado_sat = models.CharField(
        max_length=20,
        choices=[
            ('Sin Validar', 'Sin Validar'),
            ('Vigente', 'Vigente'),
            ('Cancelado', 'Cancelado'),
            ('No Encontrado', 'No Encontrado'),
            ('Error', 'Error'),
        ],
        default='Sin Validar',
        help_text='Estado de la factura en el SAT'
    )
    ultima_validacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de la última validación con el SAT'
    )
    
    def __str__(self):
        return f"{self.uuid} - {self.emisor_nombre}"

class Concepto(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='conceptos')
    clave_prod_serv = models.CharField(max_length=20)
    descripcion = models.TextField()
    cantidad = models.DecimalField(max_digits=14, decimal_places=2)
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=2)
    importe = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return self.descripcion[:50]

class Poliza(models.Model):
    factura = models.OneToOneField(Factura, on_delete=models.CASCADE, related_name='poliza')
    fecha = models.DateTimeField()
    descripcion = models.CharField(max_length=255)
    # Trazabilidad de Auditoría
    plantilla_usada = models.ForeignKey('PlantillaPoliza', on_delete=models.SET_NULL, null=True, blank=True, related_name='polizas_generadas', help_text="Plantilla utilizada para generar esta póliza")
    
    @property
    def total_debe(self):
        return sum(m.debe for m in self.movimientopoliza_set.all())

    @property
    def total_haber(self):
        return sum(m.haber for m in self.movimientopoliza_set.all())

    def __str__(self):
        return f"Póliza {self.id} - {self.fecha.date()}"

class MovimientoPoliza(models.Model):
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE)
    cuenta = models.ForeignKey(CuentaContable, on_delete=models.CASCADE)
    debe = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    haber = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.cuenta.codigo} | D:{self.debe} H:{self.haber}"

class PlantillaPoliza(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='plantillas')
    nombre = models.CharField(max_length=100)
    tipo_factura = models.CharField(max_length=1, choices=Factura.TIPO_CHOICES)
    
    # Cuentas Contables Configurables
    cuenta_flujo = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, related_name='plantillas_flujo', help_text="Cliente/Banco (Ingreso) o Proveedor/Banco (Egreso)")
    cuenta_provision = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, related_name='plantillas_provision', help_text="Ventas (Ingreso) o Gasto/Costo (Egreso)")
    cuenta_impuesto = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, related_name='plantillas_impuesto', null=True, blank=True, help_text="IVA Trasladado (Ingreso) o IVA Acreditable (Egreso)")
    
    es_default = models.BooleanField(default=False, help_text="Usar automáticamente para este tipo de factura")

    class Meta:
        verbose_name = "Plantilla Contable"
        verbose_name_plural = "Plantillas Contables"

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_factura_display()})"


class SatCodigo(models.Model):
    codigo = models.CharField(max_length=20, unique=True, db_index=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Código SAT'
        verbose_name_plural = 'Códigos SAT'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class BackgroundTask(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente'),
        ('IN_PROGRESS', 'En Progreso'),
        ('FAILED', 'Fallida'),
        ('COMPLETED', 'Completada'),
    )

    task_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    attempts = models.IntegerField(default=0)
    error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['status', 'created_at'])]

    def __str__(self):
        return f"Task {self.id} - {self.task_type} - {self.status}"
