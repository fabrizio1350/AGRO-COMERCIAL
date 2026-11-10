// Comportamiento general de MercOfertas: cabecera al bajar, enlace activo del menu,
// alertas que se cierran solas, carruseles de la portada, aparecer al hacer scroll y barra de carga.
document.addEventListener('DOMContentLoaded', function () {
    var sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Cabecera: sombra al bajar. La fila del menu queda fija: esconderla hacia saltar la pagina al final del scroll
    var cabecera = document.getElementById('cabecera');
    var botonSubir = document.getElementById('btnSubir');
    function revisarScroll() {
        var y = window.scrollY;
        if (cabecera) {
            cabecera.classList.toggle('con-sombra', y > 10);
        }
        if (botonSubir) botonSubir.classList.toggle('mostrar', y > 500);
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

    // 5. Carrusel de la portada: cambia con un fundido suave cada 7 segundos y se detiene al pasar el mouse
    var hero = document.querySelector('[data-hero]');
    if (hero && window.Swiper) {
        new Swiper(hero.querySelector('.hero-swiper'), {
            loop: true,
            speed: sinMovimiento ? 0 : 700,
            effect: 'fade',
            fadeEffect: { crossFade: true },
            autoplay: sinMovimiento ? false : { delay: 7000, disableOnInteraction: false, pauseOnMouseEnter: true },
            pagination: { el: hero.querySelector('[data-hero-paginacion]'), clickable: true },
            navigation: { prevEl: hero.querySelector('[data-hero-anterior]'), nextEl: hero.querySelector('[data-hero-siguiente]') },
            keyboard: { enabled: true },
            a11y: { prevSlideMessage: 'Banner anterior', nextSlideMessage: 'Banner siguiente', paginationBulletMessage: 'Ir al banner {{index}}' }
        });
    }

    // 6. Categorias de la portada: fila que se arrastra en el celular
    var categorias = document.querySelector('[data-swiper-categorias]');
    if (categorias && window.Swiper) {
        new Swiper(categorias, { slidesPerView: 'auto', spaceBetween: 16, freeMode: true, grabCursor: true });
    }

    if (sinMovimiento) return;

    // 7. Aparecer al hacer scroll: tarjetas y secciones entran suave cuando llegan a la pantalla
    var revelables = document.querySelectorAll('.tarjeta-producto, main .seccion, .info-bloque, .barra-tiempo');
    if ('IntersectionObserver' in window && revelables.length) {
        var observador = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (!entrada.isIntersecting) return;
                entrada.target.classList.add('revelado');
                observador.unobserve(entrada.target);
            });
        }, { rootMargin: '0px 0px -40px 0px', threshold: 0.08 });
        var altoPantalla = window.innerHeight;
        revelables.forEach(function (el) {
            var caja = el.getBoundingClientRect();
            if (caja.top < altoPantalla && caja.bottom > 0) {
                // Lo que ya se ve al abrir la pagina entra escalonado
                var columna = el.closest('.row > *');
                var posicion = columna ? Array.prototype.indexOf.call(columna.parentNode.children, columna) : 0;
                el.style.setProperty('--retraso', Math.min(posicion, 6) * 0.05 + 's');
            }
            el.classList.add('revelar');
            observador.observe(el);
        });
    }

    // 8. Barra de carga al ir a otra pagina del sitio
    var barra = document.createElement('div');
    barra.className = 'barra-carga';
    barra.setAttribute('aria-hidden', 'true');
    document.body.appendChild(barra);
    document.addEventListener('click', function (evento) {
        var enlace = evento.target.closest('a[href]');
        if (!enlace || evento.defaultPrevented || evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey) return;
        if (enlace.target === '_blank' || enlace.hasAttribute('download') || enlace.hasAttribute('data-bs-toggle')) return;
        var destino = new URL(enlace.href, window.location.href);
        if (destino.origin !== window.location.origin || destino.protocol.indexOf('http') !== 0) return;
        if (destino.pathname === window.location.pathname && destino.hash) return;
        barra.classList.add('cargando');
    });
    document.addEventListener('submit', function (evento) {
        if (!evento.defaultPrevented && !evento.target.hasAttribute('hx-post')) barra.classList.add('cargando');
    });
    // Al volver con el boton atras, la pagina sale de la cache: se quita la barra
    window.addEventListener('pageshow', function () { barra.classList.remove('cargando'); });

    // 9. El numerito del carrito rebota cuando cambia
    document.querySelectorAll('.contador-icono').forEach(function (burbuja) {
        new MutationObserver(function () {
            burbuja.classList.remove('rebote');
            void burbuja.offsetWidth;
            burbuja.classList.add('rebote');
        }).observe(burbuja, { childList: true, characterData: true, subtree: true });
    });

    // 10. Onda que sale desde donde se toca el boton
    document.addEventListener('pointerdown', function (evento) {
        var boton = evento.target.closest('.btn, .boton-comprar, .boton-circular');
        if (!boton || boton.disabled) return;
        // Solo mientras dura la onda: asi no se cortan los contadores que sobresalen del boton
        var estilo = window.getComputedStyle(boton);
        var antes = { position: boton.style.position, overflow: boton.style.overflow };
        if (estilo.position === 'static') boton.style.position = 'relative';
        boton.style.overflow = 'hidden';
        var caja = boton.getBoundingClientRect();
        var tamano = Math.max(caja.width, caja.height);
        var onda = document.createElement('span');
        onda.className = 'onda-boton';
        onda.style.width = onda.style.height = tamano + 'px';
        onda.style.left = (evento.clientX - caja.left - tamano / 2) + 'px';
        onda.style.top = (evento.clientY - caja.top - tamano / 2) + 'px';
        boton.appendChild(onda);
        onda.addEventListener('animationend', function () {
            onda.remove();
            if (!boton.querySelector('.onda-boton')) {
                boton.style.position = antes.position;
                boton.style.overflow = antes.overflow;
            }
        });
    });
});
