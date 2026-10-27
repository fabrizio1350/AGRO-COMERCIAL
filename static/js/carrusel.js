// Carrusel de ofertas: muestra una oferta a la vez y pasa sola a la siguiente.
// Se detiene mientras el mouse o el foco estan encima y no avanza solo si se prefiere menos movimiento.
document.addEventListener('DOMContentLoaded', function () {
    var sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var TIEMPO = 5000;

    document.querySelectorAll('.carrusel-ofertas').forEach(function (carrusel) {
        var slides = Array.prototype.slice.call(carrusel.querySelectorAll('.carrusel-slide'));
        var contador = carrusel.querySelector('[data-carrusel-contador]');
        var btnAnterior = carrusel.querySelector('[data-carrusel-anterior]');
        var btnSiguiente = carrusel.querySelector('[data-carrusel-siguiente]');
        if (slides.length < 2) return;

        var actual = 0;
        var temporizador = null;

        function mostrar(indice) {
            actual = (indice + slides.length) % slides.length;
            slides.forEach(function (slide, i) {
                var activo = i === actual;
                slide.classList.toggle('activo', activo);
                slide.setAttribute('aria-hidden', activo ? 'false' : 'true');
                slide.querySelectorAll('a.btn').forEach(function (a) {
                    if (activo) a.removeAttribute('tabindex'); else a.setAttribute('tabindex', '-1');
                });
            });
            if (contador) contador.textContent = (actual + 1) + ' / ' + slides.length;
        }

        function iniciar() {
            detener();
            if (!sinMovimiento) temporizador = setInterval(function () { mostrar(actual + 1); }, TIEMPO);
        }
        function detener() {
            if (temporizador) clearInterval(temporizador);
            temporizador = null;
        }

        btnAnterior.addEventListener('click', function () { mostrar(actual - 1); iniciar(); });
        btnSiguiente.addEventListener('click', function () { mostrar(actual + 1); iniciar(); });

        // Deslizar con el dedo en el celular
        var inicioX = null;
        carrusel.addEventListener('touchstart', function (e) { inicioX = e.touches[0].clientX; detener(); }, { passive: true });
        carrusel.addEventListener('touchend', function (e) {
            if (inicioX === null) return;
            var diferencia = e.changedTouches[0].clientX - inicioX;
            if (Math.abs(diferencia) > 40) mostrar(diferencia < 0 ? actual + 1 : actual - 1);
            inicioX = null;
            iniciar();
        }, { passive: true });

        carrusel.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowRight') { mostrar(actual + 1); iniciar(); }
            if (e.key === 'ArrowLeft') { mostrar(actual - 1); iniciar(); }
        });
        carrusel.addEventListener('mouseenter', detener);
        carrusel.addEventListener('mouseleave', iniciar);
        carrusel.addEventListener('focusin', detener);
        carrusel.addEventListener('focusout', function (e) {
            if (!carrusel.contains(e.relatedTarget)) iniciar();
        });
        // No gastar recursos si la pestaña no esta visible
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) detener(); else iniciar();
        });

        mostrar(0);
        iniciar();
    });
});
