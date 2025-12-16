"""
SAT Status Validator - SOAP Web Service Integration

Conecta con el servicio público del SAT para validar el estatus real
de una factura (Vigente o Cancelado).

Endpoint: https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc
Protocolo: SOAP 1.1

Autor: Sistema Konta
Fecha: 2025-12-15
Referencia: Documentación SAT - Consulta de CFDI
"""

import requests
import xml.etree.ElementTree as ET
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SatStatusValidator:
    """
    Cliente SOAP para consultar el estatus de facturas en el SAT
    """
    
    ENDPOINT = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc'
    
    # Namespace del SAT
    NAMESPACES = {
        's': 'http://schemas.xmlsoap.org/soap/envelope/',
        'tem': 'http://tempuri.org/',
    }
    
    @staticmethod
    def validar_cfdi(uuid, rfc_emisor, rfc_receptor, total):
        """
        Consulta el estatus de un CFDI en el SAT
        
        Args:
            uuid (str): UUID de la factura
            rfc_emisor (str): RFC del emisor
            rfc_receptor (str): RFC del receptor
            total (Decimal): Total de la factura
        
        Returns:
            dict: {
                'estado': 'Vigente' | 'Cancelado' | 'No Encontrado' | 'Error',
                'es_cancelable': bool,
                'estado_cancelacion': str,
                'mensaje': str
            }
        """
        try:
            # Construir el sobre SOAP
            soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:tem="http://tempuri.org/">
    <soap:Header/>
    <soap:Body>
        <tem:Consulta>
            <tem:expresionImpresa><![CDATA[?re={rfc_emisor}&rr={rfc_receptor}&tt={total:.6f}&id={uuid}]]></tem:expresionImpresa>
        </tem:Consulta>
    </soap:Body>
</soap:Envelope>"""
            
            # Headers SOAP
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta'
            }
            
            # Hacer la petición
            logger.info(f"Consultando SAT para UUID: {uuid}")
            
            response = requests.post(
                SatStatusValidator.ENDPOINT,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            # Verificar respuesta HTTP
            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code}: {response.text}")
                return {
                    'estado': 'Error',
                    'es_cancelable': False,
                    'estado_cancelacion': '',
                    'mensaje': f'Error HTTP {response.status_code}'
                }
            
            # Parsear respuesta XML
            root = ET.fromstring(response.content)
            
            # Buscar el resultado
            resultado = root.find('.//a:ConsultaResult', {
                'a': 'http://tempuri.org/'
            })
            
            if resultado is None:
                # Intentar con namespace diferente
                resultado = root.find('.//{http://tempuri.org/}ConsultaResult')
            
            if resultado is None:
                logger.warning(f"No se encontró resultado en respuesta SAT para {uuid}")
                return {
                    'estado': 'No Encontrado',
                    'es_cancelable': False,
                    'estado_cancelacion': '',
                    'mensaje': 'No se encontró el CFDI en el SAT'
                }
            
            # Extraer campos
            codigo_estatus = resultado.find('.//a:CodigoEstatus', {
                'a': 'http://tempuri.org/'
            })
            
            if codigo_estatus is None:
                codigo_estatus = resultado.find('.//{http://tempuri.org/}CodigoEstatus')
            
            estado_texto = codigo_estatus.text if codigo_estatus is not None else 'Desconocido'
            
            # Mapear código a estado
            estado_map = {
                'S - Comprobante obtenido satisfactoriamente': 'Vigente',
                'N - 601: La fecha de emisión no está dentro de la vigencia del CSD del Emisor': 'Vigente',
                'N - 602: El CSD del Emisor ha sido revocado': 'Cancelado',
                'N - 603: El certificado del Emisor no es de tipo CSD': 'Error',
                'N - 604: El certificado del PAC no es de tipo CSD': 'Error',
                'N - 605: No se pudo obtener el certificado del Emisor': 'Error',
            }
            
            # Determinar estado
            if 'Cancelado' in estado_texto or 'cancelado' in estado_texto.lower():
                estado = 'Cancelado'
            elif 'Vigente' in estado_texto or 'satisfactoriamente' in estado_texto:
                estado = 'Vigente'
            else:
                estado = estado_map.get(estado_texto, 'No Encontrado')
            
            logger.info(f"UUID {uuid}: Estado SAT = {estado}")
            
            return {
                'estado': estado,
                'es_cancelable': estado == 'Vigente',
                'estado_cancelacion': estado_texto,
                'mensaje': estado_texto
            }
        
        except requests.Timeout:
            logger.error(f"Timeout consultando SAT para {uuid}")
            return {
                'estado': 'Error',
                'es_cancelable': False,
                'estado_cancelacion': '',
                'mensaje': 'Timeout en conexión con SAT'
            }
        
        except Exception as e:
            logger.error(f"Error consultando SAT para {uuid}: {e}", exc_info=True)
            return {
                'estado': 'Error',
                'es_cancelable': False,
                'estado_cancelacion': '',
                'mensaje': f'Error: {str(e)}'
            }
    
    @staticmethod
    def validar_factura_model(factura):
        """
        Valida una instancia de Factura contra el SAT
        
        Args:
            factura: Instancia del modelo Factura
        
        Returns:
            dict: Resultado de la validación
        """
        return SatStatusValidator.validar_cfdi(
            uuid=str(factura.uuid),
            rfc_emisor=factura.emisor_rfc,
            rfc_receptor=factura.receptor_rfc,
            total=factura.total
        )
