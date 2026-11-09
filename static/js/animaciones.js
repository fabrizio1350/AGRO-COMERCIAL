// Comportamiento general de MercOfertas: cabecera al bajar, enlace activo del menu,
// alertas que se cierran solas y carrusel de categorias. Sin animaciones decorativas.
document.addEventListener('DOMContentLoaded', function () {
    var sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Cabecera: sombra al bajar y fila de navegacion que se esconde al bajar y vuelve al subir
    var cabecera = document.getElementById('cabecera');
    var botonSubir = document.getElementById('btnSubir');
    var ultimoScroll = 0;
    function revisarScroll() {
        var y = window.scrollY;
        if (cabecera) {
            cabecera.classList.toggle('con-sombra', y > 10);
            cabecera.classList.toggle('compacta', y > 160 && y > ultimoScroll);
        }
        if (botonSubir) botonSubir.classList.toggle('mostrar', y > 500);
        ultimoScroll = y;
    }
    window.addEventListener('scroll', revisarScroll, { passive: true });
    revisarScroll();
    if (botonSubir) {
        botonSubir.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: sinMovimiento ? 'auto' : 'smooth' }); });
    }

    // 2. Marcar la seccion actual en el menu, el menu lateral y la barra inferior
    var ruta = window.location.pathname;
    document.querySelectorAll('.enlace-nav[href], .menu-movil-enlaces a, .barra-inferior a').forEach(function (enlace) {
        var destino = enlace.getAttribute('data-ruta') || enlace.getAttribute('href');
        if (!destino || destino.indexOf('#') !== -1) return;
        destino = destino.split('?')[0];
        if (destino === ruta || (destino !== '/' && ruta.indexOf(destino) === 0)) enlace.classList.add('activo');
    });

    // 3. Alertas que se cierran solas
    document.querySelectorAll('.alert-dismissible').forEach(function (alerta) {
        setTimeout(function () {
            if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(alerta).close();
        }, 6000);
    });

    // 4. Barras de tiempo y tarjetas: se muestran completas desde el inicio
    document.querySelectorAll('.barra-tiempo').forEach(function (b) { b.classList.add('lista'); });
    document.querySelectorAll('.aparecer').forEach(function (el) { el.classList.add('visible'); });

    // 5. Categorias de la portada: fila que se arrastra en el celular
    var categorias = document.querySelector('[data-swiper-categorias]');
    if (categorias && window.Swiper) {
        new Swiper(categorias, { slidesPerView: 'auto', spaceBetween: 16, freeMode: true, grabCursor: true });
    }
});
