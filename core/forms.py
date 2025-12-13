from django import forms
from .models import Empresa

class UploadXMLForm(forms.Form):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        label="Empresa / RFC",
        empty_label="Selecciona una empresa",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    xml_files = forms.FileField(
        label='Selecciona uno o varios archivos XML de CFDI',
        help_text='Puedes seleccionar múltiples archivos manteniendo presionada la tecla Ctrl (o Cmd en Mac).',
        required=True
    )

    def clean_xml_files(self):
        """Permite múltiples archivos aunque el campo sea singular"""
        files = self.files.getlist('xml_files')
        if not files:
            raise forms.ValidationError("Debes seleccionar al menos un archivo XML.")
        return files
