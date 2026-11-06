// Panel del vendedor: registrar "Vendí", "Llegó" y "Agotado" sin recargar la pagina.
(function () {
    var soles = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: false });

    // Los totales vienen del servidor: asi no se mezclan comas y puntos al sumar en el navegador
    function agregarVenta(fila, cantidad, d, csrf) {
        var lista = document.getElementById('ventasHoy');
        if (!lista) return;
        var vacio = lista.querySelector('[data-sin-ventas]');
        if (vacio) vacio.remove();
        var li = document.createElement('li');
        var hora = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false });
        var nombre = fila.querySelector('.info strong').textContent;
        [hora, nombre, cantidad + ' × S/ ' + soles.format(Number(d.precio)), 'S/ ' + soles.format(Number(d.total_venta))].forEach(function (t, i) {
            var n = document.createElement(i === 1 ? 'strong' : 'span');
            if (i === 3) n.className = 'text-success fw-semibold';
            n.textContent = t;
            li.appendChild(n);
        });
        var urlQuitar = lista.getAttribute('data-url-quitar');
        if (urlQuitar && d.venta_id) {
            var form = document.createElement('form');
            form.method = 'post';
            form.className = 'm-0';
            form.action = urlQuitar.replace('/0/', '/' + d.venta_id + '/');
            var token = document.createElement('input');
            token.type = 'hidden';
            token.name = 'csrfmiddlewaretoken';
            token.value = csrf || '';
            var boton = document.createElement('button');
            boton.type = 'submit';
            boton.className = 'btn btn-link btn-sm text-danger p-0';
            boton.textContent = 'Quitar';
            boton.setAttribute('aria-label', 'Quitar la venta de ' + nombre);
            form.appendChild(token);
            form.appendChild(boton);
            li.appendChild(form);
        }
        li.classList.add('nueva');
        lista.prepend(li);
        var total = document.getElementById('vendidoHoy');
        if (total && d.vendido_hoy !== undefined) total.textContent = 'S/ ' + soles.format(Number(d.vendido_hoy));
        var registradas = document.getElementById('unidadesHoy');
        if (registradas && d.ventas_hoy !== undefined) registradas.textContent = d.ventas_hoy;
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
                if (res.ok && accion === 'vendi' && fila) agregarVenta(fila, cantidad, d, datos.get('csrfmiddlewaretoken'));
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
