const latitudPuesto = document.getElementById('id_latitud');
const longitudPuesto = document.getElementById('id_longitud');
const coordenadasPuesto = document.getElementById('coordenadas');

function establecerPunto(lat, lng) {
    latitudPuesto.value = lat.toFixed(6);
    longitudPuesto.value = lng.toFixed(6);
}

coordenadasPuesto.addEventListener('input', () => {
    const punto = coordenadasPuesto.value.trim().match(/^(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)$/);
    if (!punto) return;
    const lat = Number(punto[1]);
    const lng = Number(punto[2]);
    if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
        establecerPunto(lat, lng);
        latitudPuesto.dispatchEvent(new Event('change'));
    }
});

window.iniciarMapaPuesto = async function () {
    const {Map, InfoWindow} = await google.maps.importLibrary('maps');
    const puntoGuardado = () => latitudPuesto.value && longitudPuesto.value
        ? {lat: Number(latitudPuesto.value), lng: Number(longitudPuesto.value)}
        : null;
    const mapa = new Map(document.getElementById('mapa-puesto'), {
        center: puntoGuardado() || {lat: -16.409, lng: -71.537},
        zoom: 15, streetViewControl: false, mapTypeControl: false, clickableIcons: false,
    });
    const indicador = new InfoWindow({content: 'Mi puesto', disableAutoPan: true});
    function mostrarPunto() {
        const punto = puntoGuardado();
        if (!punto || Math.abs(punto.lat) > 90 || Math.abs(punto.lng) > 180) return;
        mapa.panTo(punto);
        indicador.setPosition(punto);
        indicador.open(mapa);
    }
    mapa.addListener('click', ({latLng}) => {
        if (!latLng) return;
        establecerPunto(latLng.lat(), latLng.lng());
        mostrarPunto();
    });
    latitudPuesto.addEventListener('change', mostrarPunto);
    longitudPuesto.addEventListener('change', mostrarPunto);
    mostrarPunto();
};
