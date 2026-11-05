document.querySelectorAll('[data-stock-url]').forEach((contenedor) => {
    const productos = [...(contenedor.matches('[data-stock-id]') ? [contenedor] : []),
        ...contenedor.querySelectorAll('[data-stock-id]')];
    if (!productos.length) return;
    const estado = document.createElement('p');
    estado.className = 'ayuda';
    estado.textContent = 'Consultando disponibilidad…';
    contenedor.after(estado);

    const url = new URL(contenedor.dataset.stockUrl, location.href);
    url.searchParams.set('ids', [...new Set(productos.map((elemento) => elemento.dataset.stockId))].join(','));
    const moneda = new Intl.NumberFormat('es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    let consultando = false;

    async function actualizar() {
        if (document.hidden || consultando) return;
        consultando = true;
        try {
            const respuesta = await fetch(url, {cache: 'no-store'});
            if (!respuesta.ok) throw new Error('No se pudo consultar el stock');
            const datos = await respuesta.json();
            productos.forEach((elemento) => {
                const disponible = datos[elemento.dataset.stockId];
                const existencias = elemento.querySelector('[data-existencias]');
                const faltan = disponible && Number(existencias.dataset.deseada) > disponible.stock;
                const texto = disponible
                    ? `${disponible.stock} ${disponible.unidad} disponibles${faltan ? ' · Menos de lo que guardaste' : ''}`
                    : 'No disponible';
                if (existencias.textContent.trim() !== texto) existencias.textContent = texto;
                existencias.classList.toggle('insuficiente', !disponible || Boolean(faltan));

                if (disponible) elemento.querySelector('[data-precio]').textContent = moneda.format(Number(disponible.precio));
                const cantidad = elemento.querySelector('[data-cantidad]');
                if (cantidad) {
                    cantidad.disabled = !disponible;
                    if (disponible) cantidad.max = disponible.stock;
                    elemento.querySelector('[data-guardar]').disabled = !disponible;
                }
            });
            estado.textContent = 'Disponibilidad actualizada a las ' + new Date().toLocaleTimeString('es-PE') + '. Se revisa cada 5 segundos.';
        } catch {
            estado.textContent = 'No se pudo actualizar la disponibilidad. Los datos mostrados pueden haber cambiado.';
        } finally {
            consultando = false;
        }
    }

    actualizar();
    setInterval(actualizar, 5000);
    document.addEventListener('visibilitychange', actualizar);
});
