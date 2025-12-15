from django import forms
from .models import Empresa
from django.forms.models import BaseInlineFormSet
from decimal import Decimal

class UploadXMLForm(forms.Form):
    xml_files = forms.FileField(
        label='Selecciona uno o varios archivos XML de CFDI',
        help_text='Puedes seleccionar múltiples archivos manteniendo presionada la tecla Ctrl (o Cmd en Mac).',
        required=True
        # Django's FileField will render with proper input type="file"
        # The 'multiple' attribute must be added in the template manually
    )

    def clean_xml_files(self):
        """Permite múltiples archivos aunque el campo sea singular"""
        files = self.files.getlist('xml_files')
        if not files:
            raise forms.ValidationError("Debes seleccionar al menos un archivo XML.")
        return files

class MovimientoPolizaFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        total_debe = Decimal(0)
        total_haber = Decimal(0)
        count = 0

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                debe = form.cleaned_data.get('debe') or Decimal(0)
                haber = form.cleaned_data.get('haber') or Decimal(0)
                total_debe += debe
                total_haber += haber
                count += 1
        
        # Validar solo si hay movimientos (si está vacío, admin estándar ya lo maneja o no)
        if count > 0:
            diff = abs(total_debe - total_haber)
            if diff > Decimal('0.01'):
                raise forms.ValidationError(
                    f"⚠️ LA PÓLIZA NO CUADRA. Total Debe: ${total_debe:,.2f} | Total Haber: ${total_haber:,.2f} | Diferencia: ${diff:,.2f}"
                )
