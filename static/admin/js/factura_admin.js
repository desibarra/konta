document.addEventListener('DOMContentLoaded', function () {
    console.log("Factura Admin Auto-fill JS loaded");

    const xmlInput = document.querySelector('#id_archivo_xml');

    // Inputs del formulario
    const fields = {
        uuid: document.querySelector('#id_uuid'),
        // Corrección: Soporte para SplitDateTimeWidget de Admin (fecha_0, fecha_1)
        fecha: document.querySelector('#id_fecha_0') || document.querySelector('#id_fecha'),
        hora: document.querySelector('#id_fecha_1') || document.querySelector('#id_hora'),

        emisor_rfc: document.querySelector('#id_emisor_rfc'),
        emisor_nombre: document.querySelector('#id_emisor_nombre'),
        receptor_rfc: document.querySelector('#id_receptor_rfc'),
        receptor_nombre: document.querySelector('#id_receptor_nombre'),

        subtotal: document.querySelector('#id_subtotal'),
        descuento: document.querySelector('#id_descuento'),
        total_impuestos_trasladados: document.querySelector('#id_total_impuestos_trasladados'),
        total_impuestos_retenidos: document.querySelector('#id_total_impuestos_retenidos'),
        total: document.querySelector('#id_total'),

        tipo_comprobante: document.querySelector('#id_tipo_comprobante'),
        naturaleza: document.querySelector('#id_naturaleza'),
        estado_contable: document.querySelector('#id_estado_contable'),

        empresa: document.querySelector('#id_empresa') // Select dropdown
    };

    if (xmlInput) {
        xmlInput.addEventListener('change', function (e) {
            const file = this.files[0];
            if (!file) return;

            console.log("XML selected:", file.name);

            // Preparar FormData
            const formData = new FormData();
            formData.append('xml_file', file);

            // Agregar ID de empresa seleccionada para calcular Naturaleza
            if (fields.empresa && fields.empresa.value) {
                formData.append('empresa_id', fields.empresa.value);
            }

            // Endpoint interno definido en FacturaAdmin.get_urls
            // Fix: Usar ruta absoluta exacta para evitar problemas relativos
            const apiUrl = '/admin/core/factura/api/parse_xml/';

            // Mostrar estado de carga (opcional)
            document.body.style.cursor = 'wait';

            // Alert visual para debug del usuario
            const loadingMsg = document.createElement('div');
            loadingMsg.id = 'xml-loading-msg';
            loadingMsg.textContent = '⏳ Leyendo XML...';
            loadingMsg.style.cssText = 'position:fixed; top:20px; right:20px; background:orange; color:white; padding:10px; z-index:9999; border-radius:5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);';
            document.body.appendChild(loadingMsg);

            fetch(apiUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken') // Django CSRF
                }
            })
                .then(response => {
                    if (!response.ok) throw new Error("Error parsing XML");
                    return response.json();
                })
                .then(data => {
                    console.log("Parsed Data:", data);

                    // Mapear datos a campos
                    if (data.uuid && fields.uuid) fields.uuid.value = data.uuid;
                    if (data.fecha && fields.fecha) fields.fecha.value = data.fecha;
                    if (data.hora && fields.hora) fields.hora.value = data.hora;

                    if (fields.emisor_rfc) fields.emisor_rfc.value = data.emisor_rfc || '';
                    if (fields.emisor_nombre) fields.emisor_nombre.value = data.emisor_nombre || '';
                    if (fields.receptor_rfc) fields.receptor_rfc.value = data.receptor_rfc || '';
                    if (fields.receptor_nombre) fields.receptor_nombre.value = data.receptor_nombre || '';

                    if (fields.subtotal) fields.subtotal.value = data.subtotal || 0;
                    if (fields.descuento) fields.descuento.value = data.descuento || 0;
                    if (fields.total) fields.total.value = data.total || 0;

                    if (fields.total_impuestos_trasladados) fields.total_impuestos_trasladados.value = data.total_tr || 0;
                    if (fields.total_impuestos_retenidos) fields.total_impuestos_retenidos.value = data.total_ret || 0;

                    // Dropdowns
                    if (data.tipo_comprobante && fields.tipo_comprobante) {
                        fields.tipo_comprobante.value = data.tipo_comprobante;
                    }
                    if (data.naturaleza && fields.naturaleza) {
                        fields.naturaleza.value = data.naturaleza;
                    }

                    // Trigger events para UI
                    Object.values(fields).forEach(input => {
                        if (input) input.dispatchEvent(new Event('change'));
                    });

                    alert('✅ Datos del XML cargados correctamente.');
                })
                .catch(err => {
                    console.error(err);
                    alert('❌ Error al leer el XML: ' + err.message);
                })
                .finally(() => {
                    document.body.style.cursor = 'default';
                    const msg = document.getElementById('xml-loading-msg');
                    if (msg) msg.remove();
                });
        });
    }

    // Helper CSRF de Django Docs
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
