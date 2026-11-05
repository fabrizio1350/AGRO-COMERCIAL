// Mapa para que el vendedor marque su puesto.
// Con GOOGLE_MAPS_API_KEY usa Google Maps (buscador de lugares + marcador arrastrable);
// sin llave usa OpenStreetMap con Leaflet para que la pagina siga funcionando.
(function () {
    var CENTRO_AREQUIPA = { lat: -16.3989, lng: -71.5369 };
    var lat = document.getElementById('id_latitud');
    var lng = document.getElementById('id_longitud');
    var nombre = document.getElementById('id_nombre');
    var direccion = document.getElementById('id_direccion');
    var estado = document.getElementById('estadoMapa');
    var buscador = document.getElementById('textoLugar');
    var botonUbicacion = document.getElementById('btnMiUbicacion');
    var contenedor = document.getElementById('mapaPuesto');
    if (!contenedor || !lat || !lng) return;

    function puntoGuardado() {
        return lat.value && lng.value ? { lat: Number(lat.value), lng: Number(lng.value) } : null;
    }
    function guardar(punto) {
        lat.value = Number(punto.lat).toFixed(6);
        lng.value = Number(punto.lng).toFixed(6);
        avisar('<i class="bi bi-check-circle-fill text-success me-1"></i>Ubicación guardada. Puedes arrastrar el marcador para afinarla.');
    }
    function avisar(html) { if (estado) estado.innerHTML = html; }
    function ponerNombre(texto) { if (nombre && texto && !nombre.value.trim()) nombre.value = texto; }
    function ponerDireccion(texto) { if (direccion && texto) direccion.value = texto.slice(0, 200); }

    function pedirUbicacion(alEncontrar) {
        if (!navigator.geolocation) { avisar('Tu navegador no permite usar la ubicación. Toca el mapa.'); return; }
        avisar('<span class="spinner-border spinner-border-sm me-1"></span>Buscando tu ubicación...');
        navigator.geolocation.getCurrentPosition(function (pos) {
            alEncontrar({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        }, function () {
            avisar('No pudimos obtener tu ubicación. Busca tu mercado o toca el mapa.');
        }, { enableHighAccuracy: true, timeout: 10000 });
    }

    // ---------------- Google Maps ----------------
    window.iniciarMapaPuesto = async function () {
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
        botonUbicacion.addEventListener('click', function () { pedirUbicacion(function (p) { mover(p, true); }); });

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
            });
        } catch (e) {
            buscador.addEventListener('keydown', function (ev) {
                if (ev.key !== 'Enter' || !geocoder) return;
                ev.preventDefault();
                geocoder.geocode({ address: buscador.value + ', Arequipa, Perú' }).then(function (r) {
                    if (r.results && r.results[0]) { ponerDireccion(r.results[0].formatted_address); mover(r.results[0].geometry.location.toJSON(), true); }
                });
            });
        }
    };

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
        botonUbicacion.addEventListener('click', function () { pedirUbicacion(function (p) { mover(p, true); }); });
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
                })
                .catch(function () { avisar('No se pudo buscar. Toca el mapa para marcarlo.'); });
        });
        buscador.setAttribute('enterkeyhint', 'search');
        buscador.placeholder = 'Busca tu mercado y presiona Enter';
        setTimeout(function () { mapa.invalidateSize(); }, 300);
    }

    if (contenedor.getAttribute('data-proveedor') === 'osm') {
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciarOSM);
        else iniciarOSM();
    }
    // Evita enviar el formulario al presionar Enter en el buscador
    document.getElementById('formPuesto').addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && e.target.id === 'textoLugar') e.preventDefault();
    });
})();
