"""
Función de clasificación inteligente de gastos

Clasifica gastos automáticamente basándose en:
- Concepto del XML
- RFC del emisor
- Patrones conocidos
"""

def clasificar_gasto_por_concepto(concepto, emisor_rfc=''):
    """
    Clasifica el gasto en la cuenta correcta basándose en el concepto
    
    Args:
        concepto: Descripción del gasto del XML
        emisor_rfc: RFC del emisor (opcional, para casos específicos)
    
    Returns:
        str: Código de cuenta contable (ej: '601-05')
    """
    if not concepto:
        return '601-99'  # Otros gastos
    
    concepto_upper = concepto.upper()
    
    # Combustibles y Lubricantes (601-05)
    if any(palabra in concepto_upper for palabra in [
        'GASOLINA', 'DIESEL', 'COMBUSTIBLE', 'PEMEX', 'GAS', 'LUBRICANTE', 'ACEITE'
    ]):
        return '601-05'
    
    # Arrendamiento (601-03)
    if any(palabra in concepto_upper for palabra in [
        'RENTA', 'ARRENDAMIENTO', 'ALQUILER', 'LEASE'
    ]):
        return '601-03'
    
    # Servicios Públicos (601-08)
    if any(palabra in concepto_upper for palabra in [
        'LUZ', 'CFE', 'AGUA', 'TELMEX', 'TELEFONO', 'INTERNET', 'ELECTRICIDAD'
    ]):
        return '601-08'
    
    # Honorarios Profesionales (601-02)
    if any(palabra in concepto_upper for palabra in [
        'HONORARIOS', 'SERVICIOS PROFESIONALES', 'CONSULTORIA', 'ASESORIA',
        'CONTADOR', 'ABOGADO', 'NOTARIO'
    ]):
        return '601-02'
    
    # Sueldos y Salarios (601-01)
    if any(palabra in concepto_upper for palabra in [
        'NOMINA', 'SUELDO', 'SALARIO', 'PAGO EMPLEADO', 'REMUNERACION'
    ]):
        return '601-01'
    
    # Mantenimiento y Reparaciones (601-04)
    if any(palabra in concepto_upper for palabra in [
        'MANTENIMIENTO', 'REPARACION', 'REFACCION', 'TALLER', 'SERVICIO MECANICO'
    ]):
        return '601-04'
    
    # Seguros y Fianzas (601-06)
    if any(palabra in concepto_upper for palabra in [
        'SEGURO', 'POLIZA', 'FIANZA', 'ASEGURADORA'
    ]):
        return '601-06'
    
    # Papelería y Útiles (601-07)
    if any(palabra in concepto_upper for palabra in [
        'PAPELERIA', 'OFFICE', 'UTILES', 'MATERIAL OFICINA', 'TONER', 'PAPEL'
    ]):
        return '601-07'
    
    # Publicidad y Promoción (601-09)
    if any(palabra in concepto_upper for palabra in [
        'PUBLICIDAD', 'MARKETING', 'PROMOCION', 'ANUNCIO', 'FACEBOOK', 'GOOGLE ADS'
    ]):
        return '601-09'
    
    # Viáticos y Gastos de Viaje (601-10)
    if any(palabra in concepto_upper for palabra in [
        'VIATICO', 'HOTEL', 'HOSPEDAJE', 'PASAJE', 'AVION', 'AUTOBUS', 'TAXI', 'UBER'
    ]):
        return '601-10'
    
    # Fletes y Acarreos (601-11)
    if any(palabra in concepto_upper for palabra in [
        'FLETE', 'ACARREO', 'TRANSPORTE', 'ENVIO', 'PAQUETERIA', 'DHL', 'FEDEX', 'ESTAFETA'
    ]):
        return '601-11'
    
    # Mensajería (601-12)
    if any(palabra in concepto_upper for palabra in [
        'MENSAJERIA', 'CORREO', 'COURIER'
    ]):
        return '601-12'
    
    # Intereses Bancarios (602-01)
    if any(palabra in concepto_upper for palabra in [
        'INTERES', 'FINANCIAMIENTO'
    ]):
        return '602-01'
    
    # Comisiones Bancarias (602-02)
    if any(palabra in concepto_upper for palabra in [
        'COMISION BANCARIA', 'CARGO BANCO', 'ANUALIDAD TARJETA'
    ]):
        return '602-02'
    
    # Default: Otros Gastos de Operación
    return '601-99'
