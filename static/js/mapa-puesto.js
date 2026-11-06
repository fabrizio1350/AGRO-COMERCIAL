// Mapa para que el vendedor marque su puesto.
// Con GOOGLE_MAPS_API_KEY usa Google Maps (buscador de lugares + marcador arrastrable);
// sin llave usa OpenStreetMap con Leaflet para que la pagina siga funcionando.
(function () {
    var CENTRO_AREQUIPA = { lat: -16.3989, lng: -71.5369 };
    var contenedor = document.getElementById('mapaPuesto');
    if (!contenedor) return;
    // Los campos se pueden cambiar con data-* (el formulario de publicar usa los de la ubicacion nueva)
    function campo(nombreData, porDefecto) { return document.getElementById(contenedor.getAttribute('data-' + nombreData) || porDefecto); }
    var lat = campo('lat', 'id_latitud');
    var lng = campo('lng', 'id_longitud');
    var nombre = campo('nombre', 'id_nombre');
    var direccion = campo('direccion', 'id_direccion');
    var estado = document.getElementById('estadoMapa');
    var buscador = document.getElementById('textoLugar');
    var botonUbicacion = document.getElementById('btnMiUbicacion');
    if (!lat || !lng) return;

    // Si el mapa esta escondido (ej. "Agregar otra ubicacion"), se arma recien cuando se muestra
    function cuandoSeVea(arrancar) {
        if (contenedor.offsetParent !== null) { arrancar(); return; }
        document.addEventListener('mapa-puesto:mostrar', function alMostrar() {
            document.removeEventListener('mapa-puesto:mostrar', alMostrar);
            arrancar();
        });
    }

    function puntoGuardado() {
        return lat.value && lng.value ? { lat: Number(lat.value), lng: Number(lng.value) } : null;
    }
    function guardar(punto) {
        lat.value = Number(punto.lat).toFixed(6);
        lng.value = Number(punto.lng).toFixed(6);
        if (zona && resumen) {
            avisar('<i class="bi bi-check-circle-fill text-success me-1"></i>Punto marcado. ' +
                   '<button type="button" class="btn btn-success btn-sm ms-1" data-listo-mapa>Listo, usar este lugar</button>');
        } else {
            avisar('<i class="bi bi-check-circle-fill text-success me-1"></i>Ubicación guardada. Puedes arrastrar el marcador para afinarla.');
        }
    }
    function avisar(html) { if (estado) estado.innerHTML = html; }
    function ponerNombre(texto) { if (nombre && texto && !nombre.value.trim()) nombre.value = texto; }
    function ponerDireccion(texto) { if (direccion && texto) { direccion.value = texto.slice(0, 200); actualizarResumen(); } }

    // Cuando ya encontro el lugar, el mapa se cierra y queda un resumen con "Cambiar"; asi pasa directo a ponerle nombre
    var zona = document.getElementById('zonaMapa');
    var resumen = document.getElementById('resumenUbicacion');
    var alReabrir = null;
    function actualizarResumen() {
        var texto = resumen && resumen.querySelector('[data-resumen-texto]');
        if (!texto) return;
        texto.textContent = direccion && direccion.value ? direccion.value
            : 'Punto marcado en el mapa (' + Number(lat.value).toFixed(4) + ', ' + Number(lng.value).toFixed(4) + ')';
    }
    function cerrarMapa(enfocar) {
        if (!zona || !resumen || !puntoGuardado()) return;
        actualizarResumen();
        zona.classList.add('d-none');
        resumen.classList.remove('d-none');
        if (enfocar !== false && nombre) {
            nombre.scrollIntoView({ block: 'center', behavior: 'smooth' });
            nombre.focus({ preventScroll: true });
        }
    }
    function abrirMapa() {
        if (!zona || !resumen) return;
        resumen.classList.add('d-none');
        zona.classList.remove('d-none');
        document.dispatchEvent(new Event('mapa-puesto:mostrar'));
        if (alReabrir) alReabrir();
    }
    if (estado) estado.addEventListener('click', function (e) { if (e.target.closest('[data-listo-mapa]')) cerrarMapa(); });
    if (resumen) resumen.addEventListener('click', function (e) { if (e.target.closest('[data-cambiar-ubicacion]')) abrirMapa(); });
    // Si ya tiene un punto guardado (ej. al editar), empieza con el mapa cerrado
    if (puntoGuardado()) cerrarMapa(false);

    // Aviso grande cuando la ubicacion esta apagada o bloqueada, con los pasos para activarla
    var aviso = document.getElementById('avisoUbicacion');
    var esCelular = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    var esIphone = /iPhone|iPad|iPod/i.test(navigator.userAgent);

    function mostrarAviso(titulo, pasos) {
        avisar('<i class="bi bi-hand-index me-1"></i>Toca el mapa o arrastra el marcador hasta tu puesto.');
        if (!aviso) return;
        aviso.innerHTML = '<div class="fw-semibold mb-1"><i class="bi bi-geo-alt me-1"></i>' + titulo + '</div>' +
            '<ol class="mb-2 ps-3">' + pasos.map(function (p) { return '<li>' + p + '</li>'; }).join('') + '</ol>' +
            '<div class="d-flex flex-wrap align-items-center gap-2">' +
            '<button type="button" class="btn btn-sm btn-warning fw-semibold" data-reintentar><i class="bi bi-arrow-clockwise me-1"></i>Intentar de nuevo</button>' +
            '<span>o busca tu mercado arriba / toca el mapa.</span></div>';
        aviso.classList.remove('d-none');
        aviso.querySelector('[data-reintentar]').addEventListener('click', function () { botonUbicacion.click(); });
        aviso.focus({ preventScroll: true });
        aviso.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    function ocultarAviso() { if (aviso) aviso.classList.add('d-none'); }

    function pasosPermiso() {
        if (esIphone) {
            return ['Abre <strong>Ajustes → Privacidad y seguridad → Localización</strong> y actívala.',
                    'En la misma pantalla entra a tu navegador (Safari o Chrome) y elige <strong>Al usar la app</strong>.',
                    'Vuelve aquí y toca <strong>Intentar de nuevo</strong>.'];
        }
        if (esCelular) {
            return ['Baja la barra de arriba del celular y activa <strong>Ubicación</strong> (GPS).',
                    'Toca el candado <i class="bi bi-lock"></i> junto a la dirección de la página → <strong>Permisos</strong> → <strong>Ubicación</strong> → <strong>Permitir</strong>.',
                    'Vuelve aquí y toca <strong>Intentar de nuevo</strong>.'];
        }
        return ['Haz clic en el candado <i class="bi bi-lock"></i> junto a la dirección de la página y en <strong>Ubicación</strong> elige <strong>Permitir</strong>.',
                'En Windows revisa también <strong>Configuración → Privacidad → Ubicación</strong>.',
                'Toca <strong>Intentar de nuevo</strong>.'];
    }

    function pedirUbicacion(alEncontrar) {
        if (!navigator.geolocation || window.isSecureContext === false) {
            mostrarAviso('Este navegador no deja usar tu ubicación', [
                'Abre la página en Chrome o Safari actualizado (con https://).',
                'Mientras tanto, busca tu mercado o toca el mapa donde está tu puesto.',
            ]);
            return;
        }
        ocultarAviso();
        botonUbicacion.disabled = true;
        avisar('<span class="spinner-border spinner-border-sm me-1"></span>Buscando tu ubicación...');
        navigator.geolocation.getCurrentPosition(function (pos) {
            botonUbicacion.disabled = false;
            alEncontrar({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        }, function (error) {
            botonUbicacion.disabled = false;
            if (error.code === 1) {
                mostrarAviso('Tu ubicación está desactivada o bloqueada para esta página', pasosPermiso());
            } else if (error.code === 3) {
                mostrarAviso('Tardó mucho en encontrar tu ubicación', [
                    'Activa el Wi-Fi o acércate a una puerta o ventana para tener mejor señal.',
                    'Toca <strong>Intentar de nuevo</strong>.',
                ]);
            } else {
                mostrarAviso('No pudimos saber dónde estás', esCelular ? pasosPermiso() : [
                    'Revisa que la ubicación de tu equipo esté encendida (en Windows: <strong>Configuración → Privacidad → Ubicación</strong>).',
                    'Toca <strong>Intentar de nuevo</strong>.',
                ]);
            }
        }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
    }

    // ---------------- Google Maps ----------------
    window.iniciarMapaPuesto = function () { cuandoSeVea(iniciarGoogle); };
    async function iniciarGoogle() {
        var { Map } = await google.maps.importLibrary('maps');
        var { AdvancedMarkerElement } = await google.maps.importLibrary('marker');
        var inicio = puntoGuardado();
        var mapa = new Map(contenedor, {
            center: inicio || CENTRO_AREQUIPA, zoom: inicio ? 18 : 14, mapId: 'DEMO_MAP_ID',
            streetViewControl: false, mapTypeControl: false, fullscreenControl: false, gestureHandling: 'greedy',
        });
        var marcador = new AdvancedMarkerElement({ map: inicio ? mapa : null, position: inicio, gmpDraggable: true, title: 'Mi puesto' });
        var geocoder = null;
        try { geocoder = new (await google.maps.importLibrary('geocoding')).Geocoder(); } catch (e) { geocoder = null; }

        function mover(punto, acercar) {
            marcador.position = punto;
            marcador.map = mapa;
            mapa.panTo(punto);
            if (acercar) mapa.setZoom(18);
            guardar(punto);
            if (geocoder) {
                geocoder.geocode({ location: punto }).then(function (r) {
                    if (r.results && r.results[0]) ponerDireccion(r.results[0].formatted_address);
                }).catch(function () {});
            }
        }
        mapa.addListener('click', function (e) { if (e.latLng) mover(e.latLng.toJSON()); });
        marcador.addListener('dragend', function () {
            var p = marcador.position;
            mover({ lat: typeof p.lat === 'function' ? p.lat() : p.lat, lng: typeof p.lng === 'function' ? p.lng() : p.lng });
        });
        botonUbicacion.addEventListener('click', function () { pedirUbicacion(function (p) { mover(p, true); cerrarMapa(); }); });

        // Buscador de lugares (Places API New); si no esta habilitada se queda el campo simple
        try {
            var { PlaceAutocompleteElement } = await google.maps.importLibrary('places');
            var auto = new PlaceAutocompleteElement({ includedRegionCodes: ['pe'], locationBias: { center: CENTRO_AREQUIPA, radius: 30000 } });
            auto.id = 'textoLugar';
            auto.setAttribute('placeholder', buscador.placeholder);
            buscador.replaceWith(auto);
            auto.addEventListener('gmp-select', async function (evento) {
                var lugar = evento.placePrediction.toPlace();
                await lugar.fetchFields({ fields: ['displayName', 'formattedAddress', 'location'] });
                if (!lugar.location) return;
                ponerNombre(lugar.displayName);
                ponerDireccion(lugar.formattedAddress);
                mover(lugar.location.toJSON(), true);
                cerrarMapa();
            });
        } catch (e) {
            buscador.addEventListener('keydown', function (ev) {
                if (ev.key !== 'Enter' || !geocoder) return;
                ev.preventDefault();
                geocoder.geocode({ address: buscador.value + ', Arequipa, Perú' }).then(function (r) {
                    if (r.results && r.results[0]) { ponerDireccion(r.results[0].formatted_address); mover(r.results[0].geometry.location.toJSON(), true); cerrarMapa(); }
                });
            });
        }
    }

    // ---------------- OpenStreetMap (sin llave) ----------------
    function iniciarOSM() {
        if (!window.L) { avisar('No se pudo cargar el mapa. Revisa tu conexión.'); return; }
        var inicio = puntoGuardado();
        var mapa = L.map(contenedor, { scrollWheelZoom: false }).setView(inicio || CENTRO_AREQUIPA, inicio ? 18 : 14);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        }).addTo(mapa);
        L.Icon.Default.imagePath = contenedor.getAttribute('data-iconos') || '/static/vendor/leaflet/images/';
        var marcador = null;

        function direccionDe(punto) {
            fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=es&lat=' + punto.lat + '&lon=' + punto.lng)
                .then(function (r) { return r.json(); })
                .then(function (d) { if (d && d.display_name) ponerDireccion(d.display_name); })
                .catch(function () {});
        }
        function mover(punto, acercar) {
            if (!marcador) {
                marcador = L.marker(punto, { draggable: true, title: 'Mi puesto' }).addTo(mapa);
                marcador.on('dragend', function () { var p = marcador.getLatLng(); guardar(p); direccionDe(p); });
            } else {
                marcador.setLatLng(punto);
            }
            mapa.setView(punto, acercar ? 18 : mapa.getZoom());
            guardar(punto);
            direccionDe(punto);
        }
        if (inicio) { marcador = L.marker(inicio, { draggable: true }).addTo(mapa); marcador.on('dragend', function () { var p = marcador.getLatLng(); guardar(p); direccionDe(p); }); }
        mapa.on('click', function (e) { mover(e.latlng); });
        botonUbicacion.addEventListener('click', function () { pedirUbicacion(function (p) { mover(p, true); cerrarMapa(); }); });
        buscador.addEventListener('keydown', function (ev) {
            if (ev.key !== 'Enter') return;
            ev.preventDefault();
            var texto = buscador.value.trim();
            if (!texto) return;
            avisar('<span class="spinner-border spinner-border-sm me-1"></span>Buscando...');
            fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=pe&accept-language=es&viewbox=-71.75,-16.25,-71.35,-16.55&q=' + encodeURIComponent(texto + ', Arequipa'))
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    if (!res.length) { avisar('No encontramos ese lugar. Toca el mapa para marcarlo.'); return; }
                    ponerNombre(res[0].name || texto);
                    mover({ lat: Number(res[0].lat), lng: Number(res[0].lon) }, true);
                    cerrarMapa();
                })
                .catch(function () { avisar('No se pudo buscar. Toca el mapa para marcarlo.'); });
        });
        buscador.setAttribute('enterkeyhint', 'search');
        buscador.placeholder = 'Busca tu mercado y presiona Enter';
        setTimeout(function () { mapa.invalidateSize(); }, 300);
        alReabrir = function () { setTimeout(function () { mapa.invalidateSize(); }, 50); };
    }

    if (contenedor.getAttribute('data-proveedor') === 'osm') {
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { cuandoSeVea(iniciarOSM); });
        else cuandoSeVea(iniciarOSM);
    }
    // Evita enviar el formulario al presionar Enter en el buscador
    var formulario = contenedor.closest('form');
    if (formulario) formulario.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && e.target.id === 'textoLugar') e.preventDefault();
    });
})();
