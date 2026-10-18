let preguntasDiagnostico = [];
let versionDiagnostico = '';
let diagnosticoCargado = false;
let enviandoDiagnostico = false;

document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('token')) { window.location.href = '/'; return; }
    document.getElementById('submit-diagnostic').addEventListener('click', enviarDiagnostico);
    cargarDiagnostico();
});

function barajarOpcionesDiagnostico(opciones, aleatorio = Math.random) {
    const mezcla = [...opciones];
    for (let i = mezcla.length - 1; i > 0; i--) {
        const j = Math.floor(aleatorio() * (i + 1));
        [mezcla[i], mezcla[j]] = [mezcla[j], mezcla[i]];
    }
    return mezcla;
}

function elementoDiagnostico(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
}

function respuestaSeleccionada(id) {
    return document.getElementById(`pregunta-${id}`)?.querySelector('input:checked');
}

function actualizarContadorDiagnostico() {
    const respondidas = preguntasDiagnostico.filter(p => respuestaSeleccionada(p.id)).length;
    document.getElementById('diagnostic-status').textContent = `Respondidas ${respondidas} de ${preguntasDiagnostico.length} preguntas`;
}

function mostrarDiagnostico(data) {
    preguntasDiagnostico = data.preguntas;
    versionDiagnostico = data.version;
    document.getElementById('diagnostic-instructions').textContent = data.instrucciones;
    const contenedor = document.getElementById('diagnostic-readings');
    contenedor.replaceChildren();
    data.lecturas.forEach((lectura, indice) => {
        const seccion = elementoDiagnostico('section', 'diagnostic-section');
        const texto = elementoDiagnostico('article', 'diagnostic-text');
        texto.append(elementoDiagnostico('p', 'diagnostic-reading-label', `Lectura ${indice + 1} de ${data.lecturas.length}`));
        const titulo = elementoDiagnostico('h3', '', lectura.titulo);
        titulo.id = `lectura-${lectura.id}`;
        seccion.setAttribute('aria-labelledby', titulo.id);
        texto.append(titulo);
        lectura.contenido.forEach(parrafo => texto.append(elementoDiagnostico('p', '', parrafo)));
        seccion.append(texto);
        const grupo = elementoDiagnostico('div', 'diagnostic-questions');
        preguntasDiagnostico.forEach((pregunta, numero) => {
            if (pregunta.id_lectura !== lectura.id) return;
            const tarjeta = elementoDiagnostico('fieldset', 'question-card');
            tarjeta.id = `pregunta-${pregunta.id}`;
            tarjeta.append(elementoDiagnostico('legend', 'question-label', `${numero + 1}. ${pregunta.pregunta}`));
            barajarOpcionesDiagnostico(pregunta.opciones).forEach((opcion, posicion) => {
                const etiqueta = elementoDiagnostico('label', 'diagnostic-option');
                const radio = document.createElement('input');
                radio.type = 'radio'; radio.name = `diag-${pregunta.id}`;
                radio.value = String(opcion.id); radio.required = true;
                radio.addEventListener('change', actualizarContadorDiagnostico);
                etiqueta.append(radio, elementoDiagnostico('span', '', `${String.fromCharCode(65 + posicion)}. ${opcion.texto}`));
                tarjeta.append(etiqueta);
            });
            grupo.append(tarjeta);
        });
        seccion.append(grupo); contenedor.append(seccion);
    });
    actualizarContadorDiagnostico();
}

async function cargarDiagnostico() {
    const boton = document.getElementById('submit-diagnostic');
    boton.disabled = true; diagnosticoCargado = false;
    try {
        const res = await fetch('/diagnostico-preguntas', {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await res.json();
        if (res.status === 409) { window.location.href = '/dashboard.html'; return; }
        if (res.status === 401 || res.status === 403) { window.location.href = '/'; return; }
        if (!res.ok) throw new Error(data.error || 'No se pudo cargar el diagnóstico');
        if (!data.version || !Array.isArray(data.lecturas) || !Array.isArray(data.preguntas) || !data.preguntas.length) {
            throw new Error('No se pudo cargar el contenido del diagnóstico. Actualiza la página.');
        }
        mostrarDiagnostico(data); diagnosticoCargado = true; boton.disabled = false;
    } catch (error) {
        document.getElementById('diagnostic-status').textContent = 'No se pudo cargar el diagnóstico. Actualiza la página para volver a intentarlo.';
        alert(error.message || 'No se pudo conectar con el servidor.');
    }
}

async function enviarDiagnostico() {
    if (!diagnosticoCargado || enviandoDiagnostico) return;
    const respuestas = [];
    for (const pregunta of preguntasDiagnostico) {
        const seleccion = respuestaSeleccionada(pregunta.id);
        if (!seleccion) {
            alert('Selecciona una alternativa en cada pregunta antes de finalizar.');
            document.getElementById(`pregunta-${pregunta.id}`).querySelector('input')?.focus();
            return;
        }
        respuestas.push({ id: pregunta.id, id_opcion: Number(seleccion.value) });
    }
    const boton = document.getElementById('submit-diagnostic');
    enviandoDiagnostico = true; boton.disabled = true;
    try {
        const res = await fetch('/diagnostico-inicial', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` },
            body: JSON.stringify({ version: versionDiagnostico, respuestas })
        });
        const data = await res.json();
        if (res.status === 401 || res.status === 403) { window.location.href = '/'; return; }
        if (res.status === 409) {
            if (data.actualizar_diagnostico) { alert(data.error); await cargarDiagnostico(); }
            else { alert(data.error || 'El diagnóstico ya fue completado.'); window.location.href = '/dashboard.html'; }
            return;
        }
        if (!res.ok) throw new Error(data.error || 'No se pudo guardar el diagnóstico');
        alert(`Diagnóstico completado. Tu nivel inicial es: ${data.nivel_inicial}`);
        window.location.href = '/dashboard.html';
    } catch (error) {
        alert(error.message || 'No se pudo conectar con el servidor. Inténtalo nuevamente.');
    } finally {
        enviandoDiagnostico = false; boton.disabled = !diagnosticoCargado;
    }
}
