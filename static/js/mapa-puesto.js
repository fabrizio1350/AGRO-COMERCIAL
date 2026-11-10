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
        if (siguiendo !== null) {
            avisar('<span class="punto-vivo me-1" aria-hidden="true"></span>Siguiendo tu ubicación en vivo' +
                   (precision ? ' (precisión de ' + precision + ' m)' : '') + '. ' +
                   (zona && resumen ? '<button type="button" class="btn btn-success btn-sm ms-1" data-listo-mapa>Listo, usar este lugar</button>' : ''));
        } else if (zona && resumen) {
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
        detenerSeguimiento();
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

    // "Usar mi ubicación actual" sigue al vendedor en tiempo real: el marcador se mueve mientras camina
    // y se afina cuando el GPS mejora. Se detiene al tocar el mapa, elegir un lugar o presionar "Listo".
    var siguiendo = null;
    var precision = 0;
    var textoBoton = botonUbicacion ? botonUbicacion.innerHTML : '';
    function metrosEntre(a, b) {
        var rad = Math.PI / 180, dLat = (b.lat - a.lat) * rad, dLng = (b.lng - a.lng) * rad;
        var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        return 12742000 * Math.asin(Math.sqrt(h));
    }
    function detenerSeguimiento() {
        if (siguiendo === null) return;
        navigator.geolocation.clearWatch(siguiendo);
        siguiendo = null;
        if (botonUbicacion) { botonUbicacion.innerHTML = textoBoton; botonUbicacion.classList.remove('activo'); }
    }
    function pedirUbicacion(alEncontrar) {
        if (siguiendo !== null) {
            // Segundo toque: deja de seguir y se queda con el ultimo punto
            detenerSeguimiento();
            if (puntoGuardado()) guardar(puntoGuardado());
            return;
        }
        if (!navigator.geolocation || window.isSecureContext === false) {
            mostrarAviso('Este navegador no deja usar tu ubicación', [
                'Abre la página en Chrome o Safari actualizado (con https://).',
                'Mientras tanto, busca tu mercado o toca el mapa donde está tu puesto.',
            ]);
            return;
        }
        ocultarAviso();
        avisar('<span class="spinner-border spinner-border-sm me-1"></span>Buscando tu ubicación...');
        var ultimo = null, ultimaVez = 0;
        siguiendo = navigator.geolocation.watchPosition(function (pos) {
            var punto = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            var ahora = Date.now();
            var mejoro = precision && pos.coords.accuracy < precision * 0.6;
            // No mueve el marcador por cada temblor del GPS: solo si avanzo unos metros o la señal mejoro bastante
            if (ultimo && !mejoro && (metrosEntre(ultimo, punto) < 8 || ahora - ultimaVez < 4000)) return;
            precision = Math.round(pos.coords.accuracy || 0);
            var primera = !ultimo;
            ultimo = punto; ultimaVez = ahora;
            if (botonUbicacion) {
                botonUbicacion.innerHTML = '<i class="bi bi-stop-circle me-1" aria-hidden="true"></i>Dejar de seguir';
                botonUbicacion.classList.add('activo');
            }
            alEncontrar(punto, primera);
        }, function (error) {
            // Si ya tiene un punto y solo se perdio la señal un momento, sigue esperando sin borrar nada
            if (ultimo && error.code !== 1) return;
            detenerSeguimiento();
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
        }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
    }

    // Buscador con lupa: mientras el vendedor escribe aparecen lugares recomendados de Arequipa.
    // Usa Photon (buscador libre hecho para sugerencias, con datos de OpenStreetMap). Solo se envia el texto escrito.
    function activarSugerencias(campoBuscar, alElegir) {
        var caja = document.createElement('div');
        caja.className = 'buscador-lugares';
        campoBuscar.parentNode.insertBefore(caja, campoBuscar);
        var lupa = document.createElement('i');
        lupa.className = 'bi bi-search lupa';
        lupa.setAttribute('aria-hidden', 'true');
        var lista = document.createElement('ul');
        lista.className = 'sugerencias-lugar d-none';
        lista.id = 'sugerenciasLugar';
        lista.setAttribute('role', 'listbox');
        lista.setAttribute('aria-label', 'Lugares recomendados');
        caja.appendChild(lupa); caja.appendChild(campoBuscar); caja.appendChild(lista);
        campoBuscar.setAttribute('role', 'combobox');
        campoBuscar.setAttribute('aria-autocomplete', 'list');
        campoBuscar.setAttribute('aria-controls', lista.id);
        campoBuscar.setAttribute('aria-expanded', 'false');
        campoBuscar.placeholder = 'Escribe y elige un lugar, ej. Mercado San Camilo';
        var lugares = [], activo = -1, espera = null, pedido = null;

        function cerrar() {
            lista.classList.add('d-none');
            campoBuscar.setAttribute('aria-expanded', 'false');
            activo = -1;
        }
        function marcar(indice) {
            activo = indice;
            Array.prototype.forEach.call(lista.children, function (li, i) {
                li.classList.toggle('activo', i === indice);
                li.setAttribute('aria-selected', i === indice ? 'true' : 'false');
            });
        }
        function elegir(lugar) {
            cerrar();
            campoBuscar.value = lugar.nombre;
            alElegir(lugar);
        }
        function pintar(mensaje) {
            lista.textContent = '';
            if (mensaje) {
                var vacio = document.createElement('li');
                vacio.className = 'sin-resultados';
                vacio.textContent = mensaje;
                lista.appendChild(vacio);
            }
            lugares.forEach(function (lugar, i) {
                var li = document.createElement('li');
                li.setAttribute('role', 'option');
                li.id = 'sugerenciaLugar' + i;
                var icono = document.createElement('i');
                icono.className = 'bi bi-geo-alt';
                icono.setAttribute('aria-hidden', 'true');
                var texto = document.createElement('span');
                var titulo = document.createElement('strong');
                titulo.textContent = lugar.nombre;
                var detalle = document.createElement('small');
                detalle.textContent = lugar.detalle;
                texto.appendChild(titulo); texto.appendChild(detalle);
                li.appendChild(icono); li.appendChild(texto);
                // mousedown y no click: asi se elige antes de que el campo pierda el foco
                li.addEventListener('mousedown', function (e) { e.preventDefault(); elegir(lugar); });
                li.addEventListener('mouseenter', function () { marcar(i); });
                lista.appendChild(li);
            });
            lista.classList.remove('d-none');
            campoBuscar.setAttribute('aria-expanded', 'true');
            activo = -1;
        }
        function leer(datos) {
            var vistos = {};
            return (datos.features || []).map(function (f) {
                var p = f.properties || {}, c = (f.geometry || {}).coordinates || [];
                var calle = [p.street, p.housenumber].filter(Boolean).join(' ');
                var nombreLugar = p.name || calle;
                var detalle = [p.name ? calle : '', p.district || p.locality, p.city || p.county].filter(Boolean)
                    .filter(function (x, i, todos) { return todos.indexOf(x) === i && x !== nombreLugar; }).join(', ');
                return { nombre: nombreLugar, detalle: detalle, lat: Number(c[1]), lng: Number(c[0]) };
            }).filter(function (l) {
                var clave = l.nombre + '|' + l.detalle;
                if (!l.nombre || isNaN(l.lat) || isNaN(l.lng) || vistos[clave]) return false;
                vistos[clave] = true;
                return true;
            }).slice(0, 6);
        }
        function buscar() {
            var texto = campoBuscar.value.trim();
            if (pedido) pedido.abort();
            if (texto.length < 3) { lugares = []; cerrar(); return; }
            pedido = window.AbortController ? new AbortController() : null;
            lupa.className = 'spinner-border spinner-border-sm lupa';
            fetch('https://photon.komoot.io/api/?limit=8&lat=' + CENTRO_AREQUIPA.lat + '&lon=' + CENTRO_AREQUIPA.lng +
                  '&bbox=-71.75,-16.55,-71.35,-16.25&q=' + encodeURIComponent(texto), pedido ? { signal: pedido.signal } : undefined)
                .then(function (r) { if (!r.ok) throw new Error('sin respuesta'); return r.json(); })
                .then(function (datos) {
                    lupa.className = 'bi bi-search lupa';
                    if (campoBuscar.value.trim() !== texto) return;
                    lugares = leer(datos);
                    pintar(lugares.length ? '' : 'No hay lugares con ese nombre. Presiona Enter para buscar o toca el mapa.');
                })
                .catch(function (error) {
                    if (error && error.name === 'AbortError') return;
                    lupa.className = 'bi bi-search lupa';
                    lugares = [];
                    pintar('No se pudieron cargar las sugerencias. Presiona Enter para buscar o toca el mapa.');
                });
        }
        campoBuscar.addEventListener('input', function () {
            clearTimeout(espera);
            espera = setTimeout(buscar, 350);
        });
        campoBuscar.addEventListener('focus', function () { if (lugares.length) pintar(''); });
        campoBuscar.addEventListener('blur', function () { setTimeout(cerrar, 150); });
        campoBuscar.addEventListener('keydown', function (e) {
            var abierta = !lista.classList.contains('d-none') && lugares.length;
            if (e.key === 'Escape') { cerrar(); return; }
            if (!abierta) return;
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                marcar((activo + (e.key === 'ArrowDown' ? 1 : -1) + lugares.length) % lugares.length);
                campoBuscar.setAttribute('aria-activedescendant', 'sugerenciaLugar' + activo);
            } else if (e.key === 'Enter') {
                // Enter elige la sugerencia marcada (o la primera) y no deja que siga la busqueda simple
                e.preventDefault();
                e.stopImmediatePropagation();
                elegir(lugares[activo >= 0 ? activo : 0]);
            }
        });
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
        mapa.addListener('click', function (e) { if (e.latLng) { detenerSeguimiento(); mover(e.latLng.toJSON()); } });
        marcador.addListener('dragend', function () {
            detenerSeguimiento();
            var p = marcador.position;
            mover({ lat: typeof p.lat === 'function' ? p.lat() : p.lat, lng: typeof p.lng === 'function' ? p.lng() : p.lng });
        });
        botonUbicacion.addEventListener('click', function () { pedirUbicacion(function (p, primera) { mover(p, primera); }); });

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
            activarSugerencias(buscador, function (lugar) {
                detenerSeguimiento();
                ponerNombre(lugar.nombre);
                mover({ lat: lugar.lat, lng: lugar.lng }, true);
                cerrarMapa();
            });
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
                marcador.on('dragend', function () { detenerSeguimiento(); var p = marcador.getLatLng(); guardar(p); direccionDe(p); });
            } else {
                marcador.setLatLng(punto);
            }
            mapa.setView(punto, acercar ? 18 : mapa.getZoom());
            guardar(punto);
            direccionDe(punto);
        }
        if (inicio) { marcador = L.marker(inicio, { draggable: true }).addTo(mapa); marcador.on('dragend', function () { detenerSeguimiento(); var p = marcador.getLatLng(); guardar(p); direccionDe(p); }); }
        mapa.on('click', function (e) { detenerSeguimiento(); mover(e.latlng); });
        activarSugerencias(buscador, function (lugar) {
            detenerSeguimiento();
            ponerNombre(lugar.nombre);
            mover({ lat: lugar.lat, lng: lugar.lng }, true);
            cerrarMapa();
        });
        botonUbicacion.addEventListener('click', function () { pedirUbicacion(function (p, primera) { mover(p, primera); }); });
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
