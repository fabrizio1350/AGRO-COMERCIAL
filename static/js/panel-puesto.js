// Panel del vendedor: registrar "Vendí", "Llegó" y "Agotado" sin recargar la pagina.
(function () {
    var soles = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: false });

    function agregarVenta(fila, cantidad, precio) {
        var lista = document.getElementById('ventasHoy');
        if (!lista) return;
        var vacio = lista.querySelector('[data-sin-ventas]');
        if (vacio) vacio.remove();
        var li = document.createElement('li');
        var hora = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false });
        var nombre = fila.querySelector('.info strong').textContent;
        [hora, nombre, cantidad + ' × S/ ' + soles.format(precio), 'S/ ' + soles.format(cantidad * precio)].forEach(function (t, i) {
            var n = document.createElement(i === 1 ? 'strong' : 'span');
            if (i === 3) n.className = 'text-success fw-semibold';
            n.textContent = t;
            li.appendChild(n);
        });
        li.classList.add('nueva');
        lista.prepend(li);
        var total = document.getElementById('vendidoHoy');
        if (total) {
            var actual = Number(total.textContent.replace(/[^\d.]/g, '')) || 0;
            total.textContent = 'S/ ' + soles.format(actual + cantidad * precio);
        }
        var unidades = document.getElementById('unidadesHoy');
        if (unidades) unidades.textContent = Number(unidades.textContent || 0) + cantidad;
    }

    document.addEventListener('submit', function (e) {
        var form = e.target.closest('form[data-stock-rapido]');
        if (!form || !window.fetch) return;
        e.preventDefault();
        var boton = e.submitter;
        var datos = new FormData(form, boton);
        var accion = datos.get('accion');
        var cantidad = Number(datos.get('cantidad') || 1);
        var fila = form.closest('[data-fila-panel]');
        form.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
        fetch(form.action, { method: 'POST', body: datos, headers: { 'X-Stock-Rapido': '1' }, credentials: 'same-origin' })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, datos: j }; }); })
            .then(function (res) {
                var d = res.datos;
                if (d.stock !== undefined && fila && window.pintarStockVivo) window.pintarStockVivo(fila.getAttribute('data-stock-id'), d);
                if (res.ok && accion === 'vendi' && fila) agregarVenta(fila, cantidad, Number(d.precio));
                if (res.ok) form.querySelector('input[name=cantidad]').value = 1;
                window.mostrarAviso && window.mostrarAviso(d.mensaje, res.ok ? 'success' : 'warning');
            })
            .catch(function () { window.mostrarAviso && window.mostrarAviso('No se pudo guardar. Revisa tu conexión.', 'error'); })
            .finally(function () {
                form.querySelectorAll('button').forEach(function (b) { b.disabled = false; });
                if (fila) {
                    var agotado = fila.classList.contains('esta-agotado');
                    fila.querySelectorAll('[data-boton-vendi], [data-boton-agotado]').forEach(function (b) { b.disabled = agotado; });
                }
            });
    });
})();
