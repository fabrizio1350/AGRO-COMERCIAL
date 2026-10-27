// Carrusel horizontal de ofertas: flechas, deslizar con el dedo (scroll nativo) y avance automatico con pausa
document.addEventListener('DOMContentLoaded', function () {
    var sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    document.querySelectorAll('.carrusel-ofertas').forEach(function (carrusel) {
        var pista = carrusel.querySelector('[data-carrusel-pista]');
        var btnAnterior = carrusel.querySelector('[data-carrusel-anterior]');
        var btnSiguiente = carrusel.querySelector('[data-carrusel-siguiente]');
        var btnPausa = carrusel.querySelector('[data-carrusel-pausa]');
        if (!pista) return;

        function paso() {
            var tarjeta = pista.querySelector('.carrusel-tarjeta');
            return tarjeta ? tarjeta.getBoundingClientRect().width + 16 : pista.clientWidth;
        }

        function mover(direccion) {
            var alFinal = pista.scrollLeft + pista.clientWidth >= pista.scrollWidth - 4;
            if (direccion > 0 && alFinal) {
                pista.scrollTo({ left: 0, behavior: sinMovimiento ? 'auto' : 'smooth' });
            } else {
                pista.scrollBy({ left: direccion * paso(), behavior: sinMovimiento ? 'auto' : 'smooth' });
            }
        }

        function revisarFlechas() {
            var sobra = pista.scrollWidth - pista.clientWidth > 4;
            carrusel.classList.toggle('sin-desborde', !sobra);
        }

        // Avance automatico: no corre si el usuario prefiere menos movimiento
        var temporizador = null;
        var pausado = sinMovimiento;

        function iniciar() {
            detener();
            if (!pausado) temporizador = setInterval(function () { mover(1); }, 5000);
        }
        function detener() {
            if (temporizador) clearInterval(temporizador);
            temporizador = null;
        }
        function pintarPausa() {
            if (!btnPausa) return;
            btnPausa.innerHTML = pausado ? '<i class="bi bi-play-fill" aria-hidden="true"></i>' : '<i class="bi bi-pause-fill" aria-hidden="true"></i>';
            btnPausa.setAttribute('aria-label', pausado ? 'Reanudar el avance automático' : 'Pausar el avance automático');
            btnPausa.title = pausado ? 'Reanudar' : 'Pausar';
            btnPausa.setAttribute('aria-pressed', pausado ? 'true' : 'false');
        }

        // Cuando el usuario interactua, el carrusel se detiene
        function interaccionUsuario() {
            pausado = true;
            detener();
            pintarPausa();
        }

        if (btnAnterior) btnAnterior.addEventListener('click', function () { interaccionUsuario(); mover(-1); });
        if (btnSiguiente) btnSiguiente.addEventListener('click', function () { interaccionUsuario(); mover(1); });
        if (btnPausa) btnPausa.addEventListener('click', function () {
            pausado = !pausado;
            pintarPausa();
            iniciar();
        });
        pista.addEventListener('touchstart', interaccionUsuario, { passive: true });
        pista.addEventListener('wheel', function (e) { if (Math.abs(e.deltaX) > 0) interaccionUsuario(); }, { passive: true });
        pista.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowRight') { e.preventDefault(); interaccionUsuario(); mover(1); }
            if (e.key === 'ArrowLeft') { e.preventDefault(); interaccionUsuario(); mover(-1); }
        });
        // Pausa temporal mientras el mouse o el foco estan dentro
        carrusel.addEventListener('mouseenter', detener);
        carrusel.addEventListener('mouseleave', iniciar);
        carrusel.addEventListener('focusin', detener);
        carrusel.addEventListener('focusout', function (e) {
            if (!carrusel.contains(e.relatedTarget)) iniciar();
        });

        window.addEventListener('resize', revisarFlechas);
        revisarFlechas();
        pintarPausa();
        iniciar();
    });
});
