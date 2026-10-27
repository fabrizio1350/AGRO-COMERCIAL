// Subir la foto del producto arrastrando o eligiendola.
// Antes de enviarla se recorta y achica a 1200x900 (4:3) para que se vea bien en la web.
document.addEventListener('DOMContentLoaded', function () {
    var zona = document.getElementById('zonaFoto');
    var input = document.querySelector('input[type="file"][name="imagen"]');
    var vista = document.getElementById('vistaFoto');
    var boton = document.getElementById('btnElegirFoto');
    var textoBoton = document.getElementById('textoBtnFoto');
    var estado = document.getElementById('estadoFoto');
    if (!zona || !input) return;

    var ANCHO = 1200;
    var ALTO = 900;
    var procesando = false;

    function abrirSelector() {
        if (!procesando) input.click();
    }

    zona.addEventListener('click', abrirSelector);
    zona.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            abrirSelector();
        }
    });
    if (boton) boton.addEventListener('click', abrirSelector);

    // Arrastrar y soltar
    ['dragenter', 'dragover'].forEach(function (evento) {
        zona.addEventListener(evento, function (e) {
            e.preventDefault();
            zona.classList.add('arrastrando');
        });
    });
    ['dragleave', 'drop'].forEach(function (evento) {
        zona.addEventListener(evento, function (e) {
            e.preventDefault();
            zona.classList.remove('arrastrando');
        });
    });
    zona.addEventListener('drop', function (e) {
        var archivo = e.dataTransfer.files && e.dataTransfer.files[0];
        if (archivo) prepararFoto(archivo);
    });

    input.addEventListener('change', function () {
        if (input.files && input.files[0]) prepararFoto(input.files[0]);
    });

    function mostrarEstado(texto, esError) {
        if (!estado) return;
        estado.textContent = texto;
        estado.classList.toggle('text-danger', !!esError);
        estado.classList.toggle('text-muted', !esError);
    }

    function prepararFoto(archivo) {
        if (!/^image\/(jpeg|png|webp)$/.test(archivo.type)) {
            mostrarEstado('Ese archivo no es una foto. Usa JPG, PNG o WEBP.', true);
            input.value = '';
            return;
        }
        procesando = true;
        zona.classList.add('cargando');
        mostrarEstado('Ajustando la foto...', false);

        var url = URL.createObjectURL(archivo);
        var img = new Image();
        img.onload = function () {
            // Recorte centrado para llenar 4:3 sin deformar la foto
            var escala = Math.max(ANCHO / img.width, ALTO / img.height);
            var anchoRecorte = ANCHO / escala;
            var altoRecorte = ALTO / escala;
            var x = (img.width - anchoRecorte) / 2;
            var y = (img.height - altoRecorte) / 2;

            var lienzo = document.createElement('canvas');
            lienzo.width = ANCHO;
            lienzo.height = ALTO;
            var ctx = lienzo.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, ANCHO, ALTO);
            ctx.drawImage(img, x, y, anchoRecorte, altoRecorte, 0, 0, ANCHO, ALTO);
            URL.revokeObjectURL(url);

            lienzo.toBlob(function (blob) {
                var nombre = archivo.name.replace(/\.[^.]+$/, '') + '.jpg';
                var ajustada = new File([blob], nombre, { type: 'image/jpeg' });
                try {
                    var dt = new DataTransfer();
                    dt.items.add(ajustada);
                    input.files = dt.files;
                } catch (err) {
                    // Navegador antiguo: se envia la foto original y la web igual la muestra recortada
                    if (!input.files || !input.files.length) {
                        mostrarEstado('No se pudo preparar la foto, intenta elegirla con el botón.', true);
                    }
                }
                vista.src = URL.createObjectURL(blob);
                zona.classList.add('con-foto');
                zona.classList.remove('cargando');
                if (textoBoton) textoBoton.textContent = 'Cambiar foto';
                mostrarEstado('Foto lista (' + Math.round(blob.size / 1024) + ' KB). Se guardará al publicar.', false);
                procesando = false;
            }, 'image/jpeg', 0.85);
        };
        img.onerror = function () {
            URL.revokeObjectURL(url);
            zona.classList.remove('cargando');
            mostrarEstado('No se pudo leer la foto, prueba con otra.', true);
            input.value = '';
            procesando = false;
        };
        img.src = url;
    }
});
