// Interacciones de la tienda: avisos tipo toast, agregar al carrito sin recargar
// (con la foto volando hasta el carrito) y animaciones despues de filtrar con HTMX.
(function () {
    var sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ---------- Avisos ----------
    function cerrarAviso(aviso) {
        aviso.classList.add('saliendo');
        setTimeout(function () { aviso.remove(); }, 300);
    }
    function prepararAviso(aviso) {
        var boton = aviso.querySelector('.aviso-cerrar');
        if (boton) boton.addEventListener('click', function () { cerrarAviso(aviso); });
        setTimeout(function () { if (aviso.isConnected) cerrarAviso(aviso); }, 6000);
    }
    window.mostrarAviso = function (texto, tipo) {
        var zona = document.getElementById('zonaAvisos');
        if (!zona) return;
        var iconos = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
        var aviso = document.createElement('div');
        aviso.className = 'aviso aviso-' + (tipo || 'info');
        aviso.setAttribute('role', 'status');
        aviso.innerHTML = '<i class="bi ' + (iconos[tipo] || iconos.info) + '" aria-hidden="true"></i><span></span>' +
            '<button type="button" class="aviso-cerrar" aria-label="Cerrar aviso"><i class="bi bi-x-lg" aria-hidden="true"></i></button>';
        aviso.querySelector('span').textContent = texto;
        zona.appendChild(aviso);
        prepararAviso(aviso);
    };

    // ---------- Carrito rapido ----------
    function actualizarContadores(total) {
        document.querySelectorAll('#contadorCarrito, .barra-inferior a[data-ruta="/carrito/"] .contador-icono').forEach(function (c) {
            c.textContent = total;
            c.classList.toggle('d-none', !total);
            c.classList.remove('rebote');
            void c.offsetWidth;
            c.classList.add('rebote');
        });
    }

    function volarAlCarrito(img) {
        var destino = document.getElementById('contadorCarrito');
        if (!img || !destino || sinMovimiento || !window.gsap) return;
        var desde = img.getBoundingClientRect();
        var hasta = destino.getBoundingClientRect();
        if (!hasta.width) return;
        var copia = img.cloneNode();
        copia.removeAttribute('style');
        copia.className = 'foto-volando';
        copia.style.left = desde.left + 'px';
        copia.style.top = desde.top + 'px';
        copia.style.width = desde.width + 'px';
        copia.style.height = desde.height + 'px';
        document.body.appendChild(copia);
        gsap.to(copia, {
            left: hasta.left, top: hasta.top, width: 24, height: 24, opacity: 0.4, borderRadius: '50%',
            duration: 0.8, ease: 'power2.in', onComplete: function () { copia.remove(); }
        });
    }

    document.addEventListener('submit', function (e) {
        var form = e.target.closest('form[data-carrito-rapido]');
        if (!form || !window.fetch) return;
        e.preventDefault();
        var boton = form.querySelector('button');
        if (boton) boton.disabled = true;
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-Carrito-Rapido': '1' },
            credentials: 'same-origin'
        }).then(function (r) {
            var tipo = r.headers.get('content-type') || '';
            if (tipo.indexOf('application/json') === -1) { window.location = r.url; return null; }
            return r.json();
        }).then(function (datos) {
            if (!datos) return;
            var tarjeta = form.closest('.tarjeta-producto');
            volarAlCarrito(tarjeta ? tarjeta.querySelector('.foto img') : null);
            setTimeout(function () { actualizarContadores(datos.total_carrito); }, sinMovimiento ? 0 : 750);
            window.mostrarAviso(datos.mensaje, 'success');
        }).catch(function () {
            window.mostrarAviso('No pudimos agregar el producto. Intenta de nuevo.', 'error');
        }).finally(function () {
            if (boton) boton.disabled = false;
        });
    });

    // ---------- Favoritos (corazon) ----------
    document.addEventListener('submit', function (e) {
        var form = e.target.closest('form[data-favorito]');
        if (!form || !window.fetch) return;
        e.preventDefault();
        var boton = form.querySelector('button');
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-Rapido': '1' },
            credentials: 'same-origin'
        }).then(function (r) {
            var tipo = r.headers.get('content-type') || '';
            if (tipo.indexOf('application/json') === -1) { window.location = r.url; return null; }
            return r.json();
        }).then(function (datos) {
            if (!datos) return;
            boton.classList.toggle('activo', datos.favorito);
            boton.setAttribute('aria-pressed', datos.favorito ? 'true' : 'false');
            boton.querySelector('i').className = 'bi ' + (datos.favorito ? 'bi-heart-fill' : 'bi-heart');
            boton.classList.remove('latido');
            void boton.offsetWidth;
            if (datos.favorito) boton.classList.add('latido');
            window.mostrarAviso(datos.mensaje, 'success');
        }).catch(function () {
            window.mostrarAviso('No pudimos guardar el favorito. Intenta de nuevo.', 'error');
        });
    });

    // ---------- Galeria del detalle ----------
    document.addEventListener('click', function (e) {
        var mini = e.target.closest('[data-galeria] .miniatura');
        if (!mini) return;
        var principal = document.querySelector('.foto-detalle img');
        if (!principal) return;
        principal.src = mini.getAttribute('data-foto');
        mini.parentNode.querySelectorAll('.miniatura').forEach(function (m) { m.classList.toggle('activa', m === mini); });
    });

    // ---------- Despues de filtrar con HTMX ----------
    document.addEventListener('htmx:afterSwap', function (e) {
        var zona = e.detail.target && document.getElementById(e.detail.target.id) || document;
        zona.querySelectorAll('.barra-tiempo').forEach(function (b) { b.classList.add('lista'); });
        if (window.gsap && !sinMovimiento) {
            zona.querySelectorAll('[data-escalonado]').forEach(function (grupo) {
                gsap.from(grupo.children, { y: 30, opacity: 0, duration: 0.5, stagger: 0.05, ease: 'power2.out' });
            });
        }
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('#zonaAvisos .aviso').forEach(prepararAviso);
    });
})();
