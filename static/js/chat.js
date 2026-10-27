// Chat comprador - vendedor: envia sin recargar y pide mensajes nuevos cada 3 segundos.
(function () {
    var caja = document.getElementById('burbujas');
    var form = document.getElementById('formChat');
    if (!caja || !form) return;
    var texto = document.getElementById('textoChat');
    var urlNuevos = caja.getAttribute('data-nuevos');
    var ocupado = false;

    function ultimoId() {
        var burbujas = caja.querySelectorAll('.burbuja[data-id]');
        return burbujas.length ? burbujas[burbujas.length - 1].getAttribute('data-id') : 0;
    }
    function alFondo() { caja.scrollTop = caja.scrollHeight; }
    function cercaDelFondo() { return caja.scrollHeight - caja.scrollTop - caja.clientHeight < 120; }

    function agregar(html) {
        var temporal = document.createElement('div');
        temporal.innerHTML = html;
        var bajar = cercaDelFondo();
        var nuevos = 0;
        temporal.querySelectorAll('.burbuja').forEach(function (b) {
            if (caja.querySelector('.burbuja[data-id="' + b.getAttribute('data-id') + '"]')) return;
            b.classList.add('nueva');
            caja.appendChild(b);
            nuevos++;
        });
        if (nuevos) {
            var vacio = caja.querySelector('.chat-vacio');
            if (vacio) vacio.remove();
            if (bajar) alFondo();
        }
    }

    function revisar() {
        if (ocupado || document.hidden) return;
        ocupado = true;
        fetch(urlNuevos + '?despues=' + ultimoId(), { credentials: 'same-origin' })
            .then(function (r) { return r.ok ? r.text() : ''; })
            .then(agregar)
            .catch(function () {})
            .finally(function () { ocupado = false; });
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (!texto.value.trim()) return;
        var datos = new FormData(form);
        datos.append('despues', ultimoId());
        var boton = form.querySelector('button');
        boton.disabled = true;
        ocupado = true;
        fetch(form.action, { method: 'POST', body: datos, credentials: 'same-origin', headers: { 'HX-Request': 'true' } })
            .then(function (r) {
                if (!r.ok) throw new Error('error');
                return r.text();
            })
            .then(function (html) {
                texto.value = '';
                texto.style.height = '';
                agregar(html);
                alFondo();
            })
            .catch(function () {
                if (window.mostrarAviso) window.mostrarAviso('No se pudo enviar el mensaje. Revisa tu conexión e intenta otra vez.', 'error');
            })
            .finally(function () { boton.disabled = false; ocupado = false; texto.focus(); });
    });

    // Enter envia, Shift+Enter hace salto de linea; el cuadro crece con el texto
    texto.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            form.requestSubmit();
        }
    });
    texto.addEventListener('input', function () {
        texto.style.height = 'auto';
        texto.style.height = Math.min(texto.scrollHeight, 140) + 'px';
    });

    alFondo();
    setInterval(revisar, 3000);
    document.addEventListener('visibilitychange', revisar);
})();
