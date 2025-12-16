import io
import datetime
import xml.etree.ElementTree as ET
from django.utils import timezone
from openpyxl import Workbook
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone as dj_timezone

# optional imports for PDF and XML validation
try:
    from weasyprint import HTML
    _WEASYPRINT_AVAILABLE = True
except Exception:
    HTML = None
    _WEASYPRINT_AVAILABLE = False

try:
    from xhtml2pdf import pisa
    _XHTML2PDF_AVAILABLE = True
except Exception:
    pisa = None
    _XHTML2PDF_AVAILABLE = False

try:
    from lxml import etree as LET
    _LXML_AVAILABLE = True
except Exception:
    LET = None
    _LXML_AVAILABLE = False


class ExportService:
    @staticmethod
    def _empresa_prefix(empresa):
        # Use RFC if empresa has it, else use 'UNKNOWN'
        return getattr(empresa, 'rfc', 'UNKNOWN')

    @staticmethod
    def generate_balanza_xml(empresa, fecha_inicio, fecha_fin):
        """Generate a SAT Balanza XML using dynamic balances for the given date range."""
        root = ET.Element('Balanza')
        root.set('Version', '1.3')
        root.set('TipoEnvio', 'N')
        root.set('FechaModBal', fecha_fin.isoformat())

        cuentas_el = ET.SubElement(root, 'Ctas')
        from core.services.contabilidad_engine import ContabilidadEngine
        rows = ContabilidadEngine.calcular_balanza(empresa, fecha_inicio, fecha_fin)
        for r in rows:
            c_el = ET.SubElement(cuentas_el, 'Cta')
            c_el.set('NumCta', r.get('codigo') or '')
            c_el.set('Desc', r.get('nombre') or '')
            c_el.set('SaldoIni', str(r.get('saldo_ini') or 0))
            c_el.set('Debe', str(r.get('debe') or 0))
            c_el.set('Haber', str(r.get('haber') or 0))
            c_el.set('SaldoFin', str(r.get('saldo_fin') or 0))
            if r.get('codigo_sat'):
                c_el.set('CodAgrup', r.get('codigo_sat'))

        bio = io.BytesIO()
        tree = ET.ElementTree(root)
        tree.write(bio, encoding='utf-8', xml_declaration=True)
        bio.seek(0)
        filename = f"{ExportService._empresa_prefix(empresa)}{fecha_fin.strftime('%Y%m%d')}BN.xml"
        return bio, filename, 'application/xml'

    @staticmethod
    def generate_balanza_excel(empresa, fecha_inicio, fecha_fin):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Balanza'
        headers = ['Cuenta', 'Nombre', 'Saldo Inicial', 'Debe', 'Haber', 'Saldo Final']
        ws.append(headers)
        from core.services.contabilidad_engine import ContabilidadEngine
        rows = ContabilidadEngine.calcular_balanza(empresa, fecha_inicio, fecha_fin)
        for r in rows:
            ws.append([
                r.get('codigo'),
                r.get('nombre'),
                float(r.get('saldo_ini') or 0),
                float(r.get('debe') or 0),
                float(r.get('haber') or 0),
                float(r.get('saldo_fin') or 0),
            ])

        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        filename = f"{ExportService._empresa_prefix(empresa)}{fecha_fin.strftime('%Y%m%d')}BN.xlsx"
        return bio, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    @staticmethod
    def generate_balanza_pdf(empresa, fecha_inicio, fecha_fin):
        # Render a PDF-friendly HTML template (xhtml2pdf-compatible)
        # Collect rows from CuentaContable
        from core.services.contabilidad_engine import ContabilidadEngine
        rows = ContabilidadEngine.calcular_balanza(empresa, fecha_inicio, fecha_fin)

        periodo_inicio = fecha_inicio.strftime('%d/%m/%Y')
        periodo_fin = fecha_fin.strftime('%d/%m/%Y')

        # Avoid data URI for xhtml2pdf (poor support). Use inline SVG only for WeasyPrint.
        svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='200' height='60'><rect width='100%' height='100%' fill='%23{empresa.nombre[:3].encode('utf-8').hex()[:6] if empresa.nombre else 'dddddd'}'/><text x='10' y='35' font-family='Arial' font-size='20' fill='%23ffffff'>{(empresa.nombre or '')[:18]}</text></svg>"
        if _XHTML2PDF_AVAILABLE:
            logo_data_uri = None
        else:
            logo_data_uri = 'data:image/svg+xml;utf8,' + svg

        # format numeric values for template
        for r in rows:
            r['saldo_ini'] = f"{r['saldo_ini']:,.2f}"
            r['debe'] = f"{r['debe']:,.2f}"
            r['haber'] = f"{r['haber']:,.2f}"
            r['saldo_fin'] = f"{r['saldo_fin']:,.2f}"

        html = render_to_string('core/pdf_balanza.html', {
            'empresa': empresa,
            'rows': rows,
            'periodo_inicio': periodo_inicio,
            'periodo_fin': periodo_fin,
            'logo_data_uri': logo_data_uri,
            'generated_at': dj_timezone.now(),
        })
        try:
            if _WEASYPRINT_AVAILABLE and HTML is not None:
                bio = io.BytesIO()
                HTML(string=html).write_pdf(bio)
                bio.seek(0)
                filename = f"{ExportService._empresa_prefix(empresa)}{fecha_fin.strftime('%Y%m%d')}BN.pdf"
                return bio, filename, 'application/pdf'

            # fallback to xhtml2pdf if weasyprint not available or failed
            if _XHTML2PDF_AVAILABLE and pisa is not None:
                bio = io.BytesIO()
                # pisa.CreatePDF can accept a bytestring HTML
                pdf = pisa.CreatePDF(src=html, dest=bio)
                if getattr(pdf, 'err', 0):
                    raise RuntimeError('xhtml2pdf reported errors during PDF creation')
                bio.seek(0)
                filename = f"{ExportService._empresa_prefix(empresa)}{fecha_fin.strftime('%Y%m%d')}BN.pdf"
                return bio, filename, 'application/pdf'

            # Final fallback: return HTML bytes (for debugging)
            bio = io.BytesIO()
            bio.write(html.encode('utf-8'))
            bio.seek(0)
            filename = f"{ExportService._empresa_prefix(empresa)}{fecha_fin.strftime('%Y%m%d')}BN.html"
            return bio, filename, 'text/html'
        except Exception:
            # If WeasyPrint raised an exception, try xhtml2pdf before giving up
            if _XHTML2PDF_AVAILABLE and pisa is not None:
                try:
                    bio = io.BytesIO()
                    pdf = pisa.CreatePDF(src=html, dest=bio)
                    if not pdf.err:
                        bio.seek(0)
                        filename = f"{ExportService._empresa_prefix(empresa)}{fecha_fin.strftime('%Y%m%d')}BN.pdf"
                        return bio, filename, 'application/pdf'
                except Exception:
                    pass

            bio = io.BytesIO()
            bio.write(html.encode('utf-8'))
            bio.seek(0)
            filename = f"{ExportService._empresa_prefix(empresa)}{fecha_fin.strftime('%Y%m%d')}BN.html"
            return bio, filename, 'text/html'

    @staticmethod
    def validate_balanza_xml(xml_bytes):
        """Validate a Balanza XML (bytes or file-like) against local XSD. Returns (valid, errors_list)."""
        if not _LXML_AVAILABLE:
            return False, ['lxml not installed; cannot validate']

        xsd_path = settings.BASE_DIR / 'xsd' / 'balanza.xsd' if hasattr(settings, 'BASE_DIR') else 'xsd/balanza.xsd'
        try:
            with open(xsd_path, 'rb') as f:
                xsd_doc = LET.parse(f)
            schema = LET.XMLSchema(xsd_doc)

            if hasattr(xml_bytes, 'read'):
                doc = LET.parse(xml_bytes)
            else:
                doc = LET.fromstring(xml_bytes)

            valid = schema.validate(doc)
            if valid:
                return True, []
            else:
                # collect error messages
                return False, [str(e) for e in schema.error_log]
        except Exception as e:
            return False, [str(e)]

    @staticmethod
    def generate_catalogo_xml(empresa, year, month):
        root = ET.Element('Catalogo')
        root.set('Version', '1.3')
        from core.models import SatCodigo
        cods = SatCodigo.objects.all()
        ctas = ET.SubElement(root, 'Ctas')
        for s in cods:
            c = ET.SubElement(ctas, 'Cta')
            c.set('CodAgrup', s.codigo)
            c.set('Desc', s.nombre)
        bio = io.BytesIO()
        ET.ElementTree(root).write(bio, encoding='utf-8', xml_declaration=True)
        bio.seek(0)
        filename = f"{ExportService._empresa_prefix(empresa)}{year:04d}{month:02d}CT.xml"
        return bio, filename, 'application/xml'

    @staticmethod
    def generate_polizas_xml(empresa, year, month):
        root = ET.Element('Polizas')
        root.set('Version', '1.3')
        from core.models import Poliza
        qs = Poliza.objects.filter(factura__empresa=empresa, fecha__year=year, fecha__month=month).select_related('factura')
        for p in qs:
            pol_el = ET.SubElement(root, 'Poliza')
            pol_el.set('Num', str(p.id))
            pol_el.set('Fecha', p.fecha.isoformat())
            # Transacciones (movimientos)
            for m in p.movimientopoliza_set.all():
                tr = ET.SubElement(pol_el, 'Transaccion')
                tr.set('Cuenta', m.cuenta.codigo)
                tr.set('Debe', str(m.debe))
                tr.set('Haber', str(m.haber))
                # CompNal injection: use factura if available
                if hasattr(p, 'factura') and p.factura:
                    comp = ET.SubElement(tr, 'CompNal')
                    comp.set('UUID_CFDI', str(p.factura.uuid))
                    comp.set('RFC', p.factura.emisor_rfc or p.factura.receptor_rfc or '')
        bio = io.BytesIO()
        ET.ElementTree(root).write(bio, encoding='utf-8', xml_declaration=True)
        bio.seek(0)
        filename = f"{ExportService._empresa_prefix(empresa)}{year:04d}{month:02d}PL.xml"
        return bio, filename, 'application/xml'
