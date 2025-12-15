document.addEventListener('DOMContentLoaded', function () {
    console.log("Poliza Admin JS loaded"); // Debug check

    // ==========================================
    // 1. PRELLENADO INTELIGENTE (Factura -> Poliza)
    // ==========================================
    const facturaSelect = document.querySelector('#id_factura');
    const fechaInput = document.querySelector('#id_fecha');
    const descInput = document.querySelector('#id_descripcion');

    if (facturaSelect) {
        facturaSelect.addEventListener('change', function () {
            const id = this.value;
            console.log("Factura changed to:", id);

            if (id) {
                // Endpoint interno definido en PolizaAdmin.get_urls
                // Fix: Ajustar path relativo desde /add/ o /change/ (ambos son 1 nivel)
                const apiUrl = `../api/factura/${id}/`;
                console.log("Fetching from:", apiUrl);

                fetch(apiUrl)
                    .then(response => {
                        if (!response.ok) throw new Error("Network response was not ok");
                        return response.json();
                    })
                    .then(data => {
                        console.log("Data fetched:", data);
                        // Actualizar Fecha (evitar sobrescribir si el usuario ya puso algo? No, auto-fill manda)
                        if (data.fecha && fechaInput) {
                            fechaInput.value = data.fecha;
                        }
                        // Actualizar Descripción
                        if (data.descripcion && descInput) {
                            descInput.value = data.descripcion;
                            // Importante: Disparar evento para que otros listeners reaccionan
                            descInput.dispatchEvent(new Event('input'));
                        }
                    })
                    .catch(err => console.error('Error auto-filling factura data:', err));
            }
        });
    }

    // ==========================================
    // 2. TOTALES EN TIEMPO REAL (Debe / Haber)
    // ==========================================

    function calculateTotals() {
        let totalDebe = 0.0;
        let totalHaber = 0.0;

        // Django Admin inlines usan prefijos: movimientopoliza_set-0-debe
        // Buscamos cualquier input que termine en -debe o -haber (y sea visible/activo)
        const debeInputs = document.querySelectorAll('input[name$="-debe"]');
        const haberInputs = document.querySelectorAll('input[name$="-haber"]');

        debeInputs.forEach(input => {
            // Ignorar inputs de templates ocultos (__prefix__)
            if (input.id && !input.id.includes('__prefix__')) {
                totalDebe += parseFloat(input.value) || 0;
            }
        });

        haberInputs.forEach(input => {
            if (input.id && !input.id.includes('__prefix__')) {
                totalHaber += parseFloat(input.value) || 0;
            }
        });

        return { totalDebe, totalHaber };
    }

    function updateTotalsDisplay() {
        const { totalDebe, totalHaber } = calculateTotals();
        let diff = Math.abs(totalDebe - totalHaber);

        // Configuración visual
        const isBalanced = diff < 0.01;
        const color = isBalanced ? '#198754' : '#dc3545'; // Bootstrap success/danger
        const icon = isBalanced ? '✅' : '⚠️';
        const msg = isBalanced ? 'CUADRADA' : 'DESCUADRADA';

        const display = document.getElementById('poliza-totals-display');

        if (display) {
            display.innerHTML = `
                <div style="font-family: sans-serif; font-size: 14px; padding: 10px; border-radius: 5px; border: 2px solid ${color}; background-color: #fff; display: flex; gap: 20px; align-items: center;">
                    <div>
                        <strong style="display:block; font-size:11px; color:#666;">TOTAL DEBE</strong>
                        <span style="font-size:16px;">$${totalDebe.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div>
                        <strong style="display:block; font-size:11px; color:#666;">TOTAL HABER</strong>
                        <span style="font-size:16px;">$${totalHaber.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div style="margin-left:auto; text-align:right; color: ${color}; font-weight: bold;">
                        <div style="font-size:18px;">${icon} ${msg}</div>
                        <div style="font-size:11px;">DIFERENCIA: $${diff.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                    </div>
                </div>
            `;
        }
    }

    // Inyectar el contenedor visual
    const inlineGroup = document.querySelector('#movimientopoliza_set-group');
    if (inlineGroup) {
        // Insertar después del título del grupo
        const title = inlineGroup.querySelector('h2');
        const container = document.createElement('div');
        container.id = 'poliza-totals-display';
        container.style.marginBottom = '15px';

        if (title) {
            title.insertAdjacentElement('afterend', container);
        } else {
            inlineGroup.prepend(container);
        }

        // --- Event Delegation ---
        // Escuchar cambios en cualquier input dentro del grupo de inlines
        inlineGroup.addEventListener('input', (e) => {
            if (e.target.name && (e.target.name.endsWith('-debe') || e.target.name.endsWith('-haber'))) {
                updateTotalsDisplay();
            }
        });

        // También escuchar cuando se agrega una fila nueva (Django admin dynamic forms)
        // Django dispara evento de jquery, pero podemos usar MutationObserver para ser vanilla puro
        const observer = new MutationObserver(mutations => {
            updateTotalsDisplay();
        });
        observer.observe(inlineGroup, { childList: true, subtree: true });

        // Calculo inicial
        updateTotalsDisplay();
    }
});
