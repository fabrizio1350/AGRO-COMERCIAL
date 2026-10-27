// Animaciones simples de la pagina de AgroComercial
document.addEventListener('DOMContentLoaded', function () {

    // 1. Mostrar los elementos con la clase .aparecer cuando entran en pantalla
    var elementos = document.querySelectorAll('.aparecer');
    if ('IntersectionObserver' in window) {
        var observador = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    entrada.target.classList.add('visible');
                    observador.unobserve(entrada.target);
                }
            });
        }, { threshold: 0.12 });

        elementos.forEach(function (el, i) {
            // pequeño retraso para que las tarjetas salgan una tras otra
            el.style.transitionDelay = (i % 4) * 0.08 + 's';
            observador.observe(el);
        });
    } else {
        elementos.forEach(function (el) { el.classList.add('visible'); });
    }

    // 2. Sombra en el header y boton de subir al hacer scroll
    var header = document.querySelector('.header-fijo');
    var botonSubir = document.getElementById('btnSubir');

    function revisarScroll() {
        var bajo = window.scrollY > 40;
        if (header) header.classList.toggle('con-sombra', bajo);
        if (botonSubir) botonSubir.classList.toggle('mostrar', window.scrollY > 400);
    }
    window.addEventListener('scroll', revisarScroll, { passive: true });
    revisarScroll();

    if (botonSubir) {
        botonSubir.addEventListener('click', function () {
            window.scrollTo({ top: 0 });
        });
    }

    // 3. Marcar en el menu la seccion donde estamos
    var rutaActual = window.location.pathname;
    document.querySelectorAll('.navbar-nav .nav-link').forEach(function (enlace) {
        var ruta = enlace.getAttribute('href');
        if (!ruta) return;
        if (ruta === rutaActual || (ruta !== '/' && rutaActual.indexOf(ruta) === 0)) {
            enlace.classList.add('activo');
        }
    });

    // 4. Cerrar las alertas solas despues de unos segundos
    document.querySelectorAll('.alert-dismissible').forEach(function (alerta) {
        setTimeout(function () {
            if (window.bootstrap) {
                bootstrap.Alert.getOrCreateInstance(alerta).close();
            }
        }, 6000);
    });
});
