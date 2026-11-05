// Stock en tiempo real: cada pocos segundos pregunta al servidor cuanto queda de los productos
// que estan en pantalla y actualiza el texto con una pequena animacion cuando cambia.
(function () {
    var INTERVALO = 4000;
    var url = null;
    var consultando = false;
    // Mismo formato que Django en español (coma decimal), para que el precio no cambie de forma al refrescar
    var moneda = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: false });

    function elementos() {
        return Array.prototype.slice.call(document.querySelectorAll('[data-stock-url] [data-stock-id], [data-stock-url][data-stock-id]'));
    }

    function destacar(nodo) {
        if (!nodo) return;
        nodo.classList.remove('cambio');
        void nodo.offsetWidth;
        nodo.classList.add('cambio');
    }

    function pintar(elemento, dato) {
        var caja = elemento.querySelector('[data-existencias]') || elemento;
        var texto = caja.querySelector('[data-texto-stock]') || caja;
        var disponible = dato && dato.disponible && dato.stock > 0;
        var deseada = Number(caja.getAttribute('data-deseada') || 0);
        var nuevo = disponible ? 'Quedan ' + dato.stock + ' ' + dato.unidad : 'Agotado';
        if (disponible && deseada > dato.stock) nuevo += ' · menos de lo que quieres';
        if (texto.textContent.trim() !== nuevo) {
            var bajo = disponible && Number(texto.getAttribute('data-ultimo') || dato.stock) > dato.stock;
            texto.textContent = nuevo;
            texto.setAttribute('data-ultimo', dato ? dato.stock : 0);
            destacar(caja);
            if (bajo) caja.classList.add('bajo');
            setTimeout(function () { caja.classList.remove('bajo'); }, 1600);
        } else if (dato) {
            texto.setAttribute('data-ultimo', dato.stock);
        }
        caja.classList.toggle('agotado', !disponible);
        caja.classList.toggle('poco', disponible && dato.stock <= 5);
        caja.classList.toggle('insuficiente', !disponible || deseada > (dato ? dato.stock : 0));
        elemento.classList.toggle('esta-agotado', !disponible);

        var hora = elemento.querySelector('[data-hora-stock]');
        if (hora && dato && dato.actualizado) hora.textContent = 'actualizado ' + dato.actualizado;
        var precio = elemento.querySelector('[data-precio]');
        if (precio && dato && Number(precio.textContent.replace(',', '.')) !== Number(dato.precio)) {
            precio.textContent = moneda.format(Number(dato.precio));
            destacar(precio);
        }
        var cantidad = elemento.querySelector('[data-cantidad]');
        if (cantidad) {
            cantidad.disabled = !disponible;
            if (disponible) {
                cantidad.max = dato.stock;
                if (Number(cantidad.value) > dato.stock) cantidad.value = dato.stock;
            }
        }
        elemento.querySelectorAll('[data-guardar]').forEach(function (b) { b.disabled = !disponible; });

        // Panel del vendedor: el numero grande y los botones dependen solo de la cantidad
        var numero = elemento.querySelector('[data-numero-stock]');
        if (numero && dato && numero.textContent.trim() !== String(dato.stock)) { numero.textContent = dato.stock; destacar(caja); }
        if (elemento.hasAttribute('data-fila-panel') && dato) {
            elemento.classList.toggle('esta-agotado', dato.stock === 0);
            caja.classList.remove('agotado', 'insuficiente');
            elemento.querySelectorAll('[data-boton-vendi], [data-boton-agotado]').forEach(function (b) { b.disabled = dato.stock === 0; });
        }
    }

    function actualizar() {
        if (document.hidden || consultando) return;
        var lista = elementos();
        if (!lista.length) return;
        var contenedor = lista[0].closest('[data-stock-url]');
        url = url || contenedor.getAttribute('data-stock-url');
        var ids = [];
        lista.forEach(function (e) { var id = e.getAttribute('data-stock-id'); if (ids.indexOf(id) === -1) ids.push(id); });
        consultando = true;
        fetch(url + '?ids=' + ids.slice(0, 60).join(','), { cache: 'no-store', credentials: 'same-origin' })
            .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
            .then(function (datos) {
                lista.forEach(function (e) { pintar(e, datos[e.getAttribute('data-stock-id')]); });
                document.querySelectorAll('[data-estado-stock]').forEach(function (s) {
                    s.classList.remove('sin-conexion');
                    s.lastChild.textContent = 'Stock en vivo · ' + new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                });
            })
            .catch(function () {
                document.querySelectorAll('[data-estado-stock]').forEach(function (s) {
                    s.classList.add('sin-conexion');
                    s.lastChild.textContent = 'Sin conexión: el stock puede haber cambiado';
                });
            })
            .finally(function () { consultando = false; });
    }

    window.actualizarStockVivo = actualizar;
    window.pintarStockVivo = function (id, dato) {
        document.querySelectorAll('[data-stock-id="' + id + '"]').forEach(function (e) { pintar(e, dato); });
    };
    document.addEventListener('DOMContentLoaded', function () {
        actualizar();
        setInterval(actualizar, INTERVALO);
    });
    document.addEventListener('visibilitychange', actualizar);
    document.addEventListener('htmx:afterSwap', actualizar);

    // Selector de cantidad (- / +)
    document.addEventListener('click', function (e) {
        var boton = e.target.closest('[data-restar], [data-sumar]');
        if (!boton) return;
        var campo = boton.parentNode.querySelector('input[type=number]');
        if (!campo || campo.disabled) return;
        var valor = Number(campo.value || 0) + (boton.hasAttribute('data-sumar') ? 1 : -1);
        var minimo = Number(campo.min || 0);
        var maximo = campo.max ? Number(campo.max) : Infinity;
        campo.value = Math.max(minimo, Math.min(maximo, valor));
        campo.dispatchEvent(new Event('change', { bubbles: true }));
    });
})();
