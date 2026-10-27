// Animaciones de AgroComercial: GSAP para la portada y el scroll, Swiper para el hero
// y detalles como la onda de los botones. Todo se apaga si se prefiere menos movimiento.
document.addEventListener('DOMContentLoaded', function () {
    var sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var hayGsap = typeof window.gsap !== 'undefined';

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

    // 3. Onda al hacer clic en los botones
    document.addEventListener('click', function (e) {
        var boton = e.target.closest('.btn');
        if (!boton || sinMovimiento) return;
        var caja = boton.getBoundingClientRect();
        var tam = Math.max(caja.width, caja.height);
        var onda = document.createElement('span');
        onda.className = 'onda';
        onda.style.width = onda.style.height = tam + 'px';
        onda.style.left = (e.clientX - caja.left - tam / 2) + 'px';
        onda.style.top = (e.clientY - caja.top - tam / 2) + 'px';
        boton.appendChild(onda);
        setTimeout(function () { onda.remove(); }, 600);
    });

    // 4. Alertas que se cierran solas
    document.querySelectorAll('.alert-dismissible').forEach(function (alerta) {
        setTimeout(function () {
            if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(alerta).close();
        }, 6000);
    });

    // 5. Barras de tiempo: se llenan cuando aparecen en pantalla
    var barras = document.querySelectorAll('.barra-tiempo');
    if ('IntersectionObserver' in window && !sinMovimiento) {
        var obsBarras = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    entrada.target.classList.add('lista');
                    obsBarras.unobserve(entrada.target);
                }
            });
        }, { threshold: 0.4 });
        barras.forEach(function (b) { obsBarras.observe(b); });
    }

    // 6. Hero de la portada con Swiper
    var hero = document.querySelector('[data-hero]');
    if (hero && window.Swiper) {
        var swiperHero = new Swiper(hero.querySelector('.hero-swiper'), {
            loop: true,
            speed: sinMovimiento ? 0 : 900,
            effect: 'fade',
            fadeEffect: { crossFade: true },
            autoplay: sinMovimiento ? false : { delay: 6000, disableOnInteraction: false, pauseOnMouseEnter: true },
            pagination: { el: hero.querySelector('[data-hero-paginacion]'), clickable: true },
            navigation: { prevEl: hero.querySelector('[data-hero-anterior]'), nextEl: hero.querySelector('[data-hero-siguiente]') },
            keyboard: { enabled: true },
            a11y: { prevSlideMessage: 'Banner anterior', nextSlideMessage: 'Banner siguiente', paginationBulletMessage: 'Ir al banner {{index}}' },
            on: {
                slideChangeTransitionStart: function (s) { animarTitulo(s.slides[s.activeIndex]); },
                autoplayPause: function () { hero.classList.add('pausado'); },
                autoplayResume: function () { hero.classList.remove('pausado'); }
            }
        });
        animarTitulo(swiperHero.slides[swiperHero.activeIndex]);
    }

    // Separa el titulo del banner en palabras y las hace subir una tras otra
    function animarTitulo(slide) {
        if (!slide || !hayGsap || sinMovimiento) return;
        var titulo = slide.querySelector('[data-titulo-animado]');
        if (!titulo) return;
        if (!titulo.dataset.partido) {
            partirEnPalabras(titulo);
            titulo.dataset.partido = '1';
        }
        gsap.fromTo(titulo.querySelectorAll('.palabra'),
            { yPercent: 60, opacity: 0, rotate: 3 },
            { yPercent: 0, opacity: 1, rotate: 0, duration: 0.8, stagger: 0.06, ease: 'power3.out' });
        gsap.fromTo(slide.querySelectorAll('.hero-etiqueta, .hero-texto, .hero-acciones'),
            { y: 24, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.7, stagger: 0.12, delay: 0.25, ease: 'power3.out' });
    }
    function partirEnPalabras(nodo) {
        Array.prototype.slice.call(nodo.childNodes).forEach(function (hijo) {
            if (hijo.nodeType === 3) {
                var fragmento = document.createDocumentFragment();
                hijo.textContent.split(/(\s+)/).forEach(function (trozo) {
                    if (!trozo) return;
                    if (/^\s+$/.test(trozo)) { fragmento.appendChild(document.createTextNode(trozo)); return; }
                    var span = document.createElement('span');
                    span.className = 'palabra';
                    span.textContent = trozo;
                    fragmento.appendChild(span);
                });
                nodo.replaceChild(fragmento, hijo);
            } else if (hijo.nodeType === 1) {
                partirEnPalabras(hijo);
            }
        });
    }

    // 7. Categorias de la portada: carrusel libre que se arrastra
    var categorias = document.querySelector('[data-swiper-categorias]');
    if (categorias && window.Swiper) {
        new Swiper(categorias, { slidesPerView: 'auto', spaceBetween: 24, freeMode: true, grabCursor: true });
    }

    // 8. Animaciones al bajar con GSAP + ScrollTrigger
    if (hayGsap && window.ScrollTrigger && !sinMovimiento) {
        gsap.registerPlugin(ScrollTrigger);

        gsap.utils.toArray('.revelar').forEach(function (el) {
            gsap.from(el, { y: 40, opacity: 0, duration: 0.9, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 88%', once: true } });
        });

        gsap.utils.toArray('[data-escalonado]').forEach(function (grupo) {
            gsap.from(grupo.children, { y: 50, opacity: 0, duration: 0.8, stagger: 0.08, ease: 'power3.out', scrollTrigger: { trigger: grupo, start: 'top 85%', once: true } });
        });

        // Tarjetas sueltas de las paginas internas
        gsap.utils.toArray('.aparecer').forEach(function (el) {
            el.classList.add('visible');
            gsap.from(el, { y: 30, opacity: 0, duration: 0.7, ease: 'power2.out', scrollTrigger: { trigger: el, start: 'top 92%', once: true } });
        });

        var pasos = document.querySelector('[data-pasos]');
        if (pasos) {
            var linea = pasos.querySelector('.linea-pasos span');
            var tl = gsap.timeline({ scrollTrigger: { trigger: pasos, start: 'top 75%', once: true } });
            if (linea) tl.to(linea, { scaleX: 1, duration: 1.4, ease: 'power2.inOut' }, 0);
            tl.from(pasos.querySelectorAll('.paso'), { y: 40, opacity: 0, duration: 0.7, stagger: 0.2, ease: 'back.out(1.6)' }, 0);
        }

        // Cifras reales que suben de 0 a su valor
        document.querySelectorAll('[data-contador]').forEach(function (el) {
            var valor = parseInt(el.getAttribute('data-contador'), 10) || 0;
            var obj = { n: 0 };
            gsap.to(obj, {
                n: valor, duration: 1.6, ease: 'power2.out',
                scrollTrigger: { trigger: el, start: 'top 90%', once: true },
                onUpdate: function () { el.textContent = Math.round(obj.n); }
            });
        });
    } else {
        document.querySelectorAll('.aparecer').forEach(function (el) { el.classList.add('visible'); });
    }
});
