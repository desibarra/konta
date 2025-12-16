"""
Mapeo Universal SAT UsoCFDI → Cuenta Contable

Este módulo contiene el diccionario maestro que mapea TODOS los códigos
de UsoCFDI del SAT a sus cuentas contables correspondientes según el
Código Agrupador del SAT (Anexo 24).

Autor: Sistema Konta
Fecha: 2025-12-15
Referencia: Catálogo de UsoCFDI del SAT
"""

# Diccionario Maestro: UsoCFDI → Configuración de Cuenta
SAT_ACCOUNT_MAP = {
    # ========================================================================
    # SERIE 500: COSTOS
    # ========================================================================
    'G01': {
        'nombre': 'Costo de Ventas - Adquisición de Mercancías',
        'agrupador': '501.01',
        'tipo': 'GASTO',  # En Django usamos GASTO para costos y gastos
        'codigo_base': '501-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'G02': {
        'nombre': 'Devoluciones, Descuentos o Bonificaciones',
        'agrupador': '501.02',
        'tipo': 'GASTO',
        'codigo_base': '502-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    
    # ========================================================================
    # SERIE 600: GASTOS GENERALES
    # ========================================================================
    'G03': {
        'nombre': 'Gastos en General',
        'agrupador': '601.01',
        'tipo': 'GASTO',
        'codigo_base': '601-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    
    # ========================================================================
    # SERIE 600: DEDUCCIONES PERSONALES (Tratadas como Gastos Operativos)
    # ========================================================================
    'D01': {'nombre': 'Honorarios Médicos y Dentales', 'agrupador': '601.84', 'tipo': 'GASTO', 'codigo_base': '601-84', 'naturaleza': 'D', 'es_deudora': True},
    'D02': {'nombre': 'Gastos Médicos por Incapacidad', 'agrupador': '601.84', 'tipo': 'GASTO', 'codigo_base': '601-84', 'naturaleza': 'D', 'es_deudora': True},
    'D03': {'nombre': 'Gastos Funerales', 'agrupador': '601.85', 'tipo': 'GASTO', 'codigo_base': '601-85', 'naturaleza': 'D', 'es_deudora': True},
    'D04': {'nombre': 'Donativos', 'agrupador': '601.86', 'tipo': 'GASTO', 'codigo_base': '601-86', 'naturaleza': 'D', 'es_deudora': True},
    'D05': {'nombre': 'Intereses Reales por Créditos Hipotecarios', 'agrupador': '601.87', 'tipo': 'GASTO', 'codigo_base': '601-87', 'naturaleza': 'D', 'es_deudora': True},
    'D06': {'nombre': 'Aportaciones Voluntarias al SAR', 'agrupador': '601.88', 'tipo': 'GASTO', 'codigo_base': '601-88', 'naturaleza': 'D', 'es_deudora': True},
    'D07': {'nombre': 'Primas por Seguros de Gastos Médicos', 'agrupador': '601.89', 'tipo': 'GASTO', 'codigo_base': '601-89', 'naturaleza': 'D', 'es_deudora': True},
    'D08': {'nombre': 'Gastos de Transportación Escolar', 'agrupador': '601.90', 'tipo': 'GASTO', 'codigo_base': '601-90', 'naturaleza': 'D', 'es_deudora': True},
    'D09': {'nombre': 'Depósitos en Cuentas para el Ahorro', 'agrupador': '601.91', 'tipo': 'GASTO', 'codigo_base': '601-91', 'naturaleza': 'D', 'es_deudora': True},
    'D10': {'nombre': 'Pagos por Servicios Educativos', 'agrupador': '601.92', 'tipo': 'GASTO', 'codigo_base': '601-92', 'naturaleza': 'D', 'es_deudora': True},
    
    # ========================================================================
    # SERIE 150: INVERSIONES / ACTIVOS FIJOS
    # ========================================================================
    'I01': {
        'nombre': 'Construcciones',
        'agrupador': '151.01',
        'tipo': 'ACTIVO',
        'codigo_base': '151-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'I02': {
        'nombre': 'Mobiliario y Equipo de Oficina',
        'agrupador': '152.01',
        'tipo': 'ACTIVO',
        'codigo_base': '152-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'I03': {
        'nombre': 'Equipo de Transporte',
        'agrupador': '154.01',
        'tipo': 'ACTIVO',
        'codigo_base': '154-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'I04': {
        'nombre': 'Equipo de Cómputo y Accesorios',
        'agrupador': '153.01',
        'tipo': 'ACTIVO',
        'codigo_base': '153-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'I05': {
        'nombre': 'Dados, Troqueles, Moldes y Herramental',
        'agrupador': '155.01',
        'tipo': 'ACTIVO',
        'codigo_base': '155-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'I06': {
        'nombre': 'Comunicaciones Telefónicas',
        'agrupador': '156.01',
        'tipo': 'ACTIVO',
        'codigo_base': '156-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'I07': {
        'nombre': 'Comunicaciones Satelitales',
        'agrupador': '156.02',
        'tipo': 'ACTIVO',
        'codigo_base': '156-02',
        'naturaleza': 'D',
        'es_deudora': True
    },
    'I08': {
        'nombre': 'Otra Maquinaria y Equipo',
        'agrupador': '155.02',
        'tipo': 'ACTIVO',
        'codigo_base': '155-02',
        'naturaleza': 'D',
        'es_deudora': True
    },
    
    # ========================================================================
    # SERIE 610: NÓMINA Y SUELDOS
    # ========================================================================
    'CN01': {
        'nombre': 'Nómina - Sueldos y Salarios',
        'agrupador': '610.01',
        'tipo': 'GASTO',
        'codigo_base': '610-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    
    # ========================================================================
    # PAGOS (P)
    # ========================================================================
    'P01': {
        'nombre': 'Por Definir - Pagos',
        'agrupador': '601.01',  # Usar gastos generales como default
        'tipo': 'GASTO',
        'codigo_base': '601-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
    
    # ========================================================================
    # SIN EFECTOS FISCALES (S)
    # ========================================================================
    'S01': {
        'nombre': 'Sin Efectos Fiscales',
        'agrupador': '601.01',  # Usar gastos generales como default
        'tipo': 'GASTO',
        'codigo_base': '601-01',
        'naturaleza': 'D',
        'es_deudora': True
    },
}

# Cuenta DEFAULT para UsoCFDI no reconocidos
DEFAULT_ACCOUNT = {
    'nombre': 'Gastos en General (Default)',
    'agrupador': '601.01',
    'tipo': 'GASTO',
    'codigo_base': '601-01',
    'naturaleza': 'D',
    'es_deudora': True
}


def get_account_config(uso_cfdi):
    """
    Obtiene la configuración de cuenta para un UsoCFDI dado.
    
    Args:
        uso_cfdi (str): Código de UsoCFDI del SAT (ej: 'G01', 'I04')
    
    Returns:
        dict: Configuración de cuenta o DEFAULT_ACCOUNT si no existe
    """
    if not uso_cfdi:
        return DEFAULT_ACCOUNT
    
    # Normalizar (mayúsculas, sin espacios)
    uso_cfdi_clean = uso_cfdi.strip().upper()
    
    return SAT_ACCOUNT_MAP.get(uso_cfdi_clean, DEFAULT_ACCOUNT)


def get_all_uso_cfdi_codes():
    """
    Retorna lista de todos los códigos UsoCFDI soportados.
    
    Returns:
        list: Lista de códigos UsoCFDI
    """
    return list(SAT_ACCOUNT_MAP.keys())


def get_accounts_by_type(tipo):
    """
    Filtra cuentas por tipo (GASTO, ACTIVO, etc.)
    
    Args:
        tipo (str): Tipo de cuenta ('GASTO', 'ACTIVO', 'PASIVO', 'INGRESO')
    
    Returns:
        dict: Diccionario filtrado de cuentas
    """
    return {
        codigo: config 
        for codigo, config in SAT_ACCOUNT_MAP.items() 
        if config['tipo'] == tipo
    }
