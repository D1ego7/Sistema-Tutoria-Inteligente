/* Seguimiento y revisión de respuestas. El servidor vuelve a comprobar permisos. */
let paginaLista = 1;
let paginaHistorial = 1;
let estudianteSeleccionado = null;
let revisionLista = 0;
let revisionDetalle = 0;
const elemento = id => document.getElementById(id);
const texto = (id, valor) => { elemento(id).textContent = valor; };

async function consultar(ruta) {
    const res = await fetch(ruta, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
    const data = await res.json();
    if (res.status === 401) {
        localStorage.removeItem('token'); localStorage.removeItem('user');
        window.location.href = '/';
    }
    if (!res.ok) throw new Error(data.error || 'No se pudo consultar el seguimiento');
    return data;
}

function informar(mensaje, error = false) {
    texto('estado-panel', mensaje);
    elemento('estado-panel').classList.toggle('error', error);
}

function celda(fila, valor) {
    const td = document.createElement('td');
    td.textContent = valor;
    fila.appendChild(td);
    return td;
}

function paginar(sufijo, data) {
    const paginas = Math.max(1, Math.ceil((data.total ?? data.total_intentos) / data.por_pagina));
    texto(`pagina-${sufijo}`, `Página ${data.pagina} de ${paginas}`);
    elemento(`anterior-${sufijo}`).disabled = data.pagina <= 1;
    elemento(`siguiente-${sufijo}`).disabled = data.pagina >= paginas;
}

async function cargarEstudiantes() {
    const revision = ++revisionLista;
    informar('Cargando estudiantes…');
    elemento('anterior-lista').disabled = true;
    elemento('siguiente-lista').disabled = true;
    elemento('estudiantes').replaceChildren();
    try {
        const params = new URLSearchParams({ pagina: paginaLista, buscar: elemento('buscar').value, nivel: elemento('nivel').value });
        const data = await consultar(`/api/docente/estudiantes?${params}`);
        if (revision !== revisionLista) return;
        for (const e of data.estudiantes) {
            const fila = document.createElement('tr');
            if (e.id_estudiante === estudianteSeleccionado) fila.classList.add('seleccionado');
            celda(fila, e.nombre);
            celda(fila, e.puntaje_diagnostico === null ? 'Pendiente' : `${e.puntaje_diagnostico}% · ${e.nivel_diagnostico}`);
            celda(fila, e.nivel_actual || 'Sin asignar');
            celda(fila, (e.porcentaje_acierto === null ? 'Sin respuestas evaluadas' : `${e.porcentaje_acierto}% (${e.correctas}/${e.respondidas})`) + (e.pendientes ? ` · ${e.pendientes} pendientes` : ''));
            const boton = document.createElement('button');
            boton.className = 'boton-secundario'; boton.textContent = 'Ver detalle';
            boton.setAttribute('aria-label', `Ver seguimiento de ${e.nombre}`);
            boton.addEventListener('click', () => { estudianteSeleccionado = e.id_estudiante; paginaHistorial = 1; cargarDetalle(true); });
            celda(fila, '').appendChild(boton);
            elemento('estudiantes').appendChild(fila);
        }
        paginar('lista', data);
        informar(data.total === 1 ? '1 estudiante encontrado.' : data.total ? `${data.total} estudiantes encontrados.` : 'No se encontraron estudiantes.');
    } catch (error) { if (revision === revisionLista) informar(error.message, true); }
}

async function cargarDetalle(enfocar = false) {
    const revision = ++revisionDetalle;
    elemento('detalle').hidden = true;
    informar('Cargando seguimiento…');
    try {
        const data = await consultar(`/api/docente/estudiantes/${estudianteSeleccionado}?pagina=${paginaHistorial}`);
        if (revision !== revisionDetalle) return;
        texto('nombre-estudiante', data.estudiante.nombre);
        texto('nivel-actual', data.estudiante.nivel_actual || 'Sin asignar');
        texto('aciertos', data.evaluacion.total_respuestas ? `${data.evaluacion.porcentaje_acierto}%` : 'Sin respuestas evaluadas');
        texto('completadas', data.lecturas_completadas); texto('intentos', data.total_intentos);
        texto('diagnostico', data.diagnostico ? `${data.diagnostico.puntaje}% de aciertos · Nivel asignado: ${data.diagnostico.nivel_asignado} · Fecha: ${data.diagnostico.fecha || 'Sin fecha'}` : 'El estudiante todavía no ha completado el diagnóstico.');
        texto('recomendacion', data.recomendacion?.razon || 'Se necesitan respuestas para orientar el seguimiento.');
        elemento('por-nivel').replaceChildren();
        for (const nivel of ['literal', 'inferencial', 'crítico']) {
            const datos = data.evaluacion.por_nivel[nivel];
            const fila = document.createElement('tr');
            for (const valor of [nivel, datos?.total ?? 'Sin datos', datos?.correctas ?? '—', datos ? `${datos.porcentaje}%` : '—', datos ? datos.total - datos.correctas : '—']) celda(fila, valor);
            elemento('por-nivel').appendChild(fila);
        }
        mostrarHistorial(data.historial);
        paginar('historial', data); elemento('detalle').hidden = false;
        informar('Seguimiento actualizado.');
        if (enfocar) elemento('nombre-estudiante').focus();
    } catch (error) { if (revision === revisionDetalle) informar(error.message, true); }
}

function agruparHistorial(historial) {
    const lecturas = new Map();
    for (const intento of historial) {
        // Versiones con el mismo título nunca deben mezclarse.
        const clave = intento.id_texto ?? intento.titulo;
        if (!lecturas.has(clave)) lecturas.set(clave, { titulo: intento.titulo, archivada: !!intento.archivada, preguntas: new Map() });
        const preguntas = lecturas.get(clave).preguntas;
        if (!preguntas.has(intento.id_pregunta)) preguntas.set(intento.id_pregunta, []);
        preguntas.get(intento.id_pregunta).push(intento);
    }
    for (const lectura of lecturas.values()) {
        for (const intentos of lectura.preguntas.values()) intentos.sort((a, b) => b.id_respuesta_est - a.id_respuesta_est);
        lectura.preguntas = [...lectura.preguntas.values()].sort((a, b) => (a[0].orden ?? 0) - (b[0].orden ?? 0));
    }
    return [...lecturas.values()];
}

function nodoHistorial(etiqueta, clase, contenido) {
    const nodo = document.createElement(etiqueta); nodo.className = clase; nodo.textContent = contenido; return nodo;
}

function resumenHistorial(lectura) {
    const intentos = lectura.preguntas.flat();
    const actuales = intentos.filter(i => i.ultimo_intento);
    return {
        correctas: actuales.filter(i => i.es_correcta === true).length,
        refuerzo: actuales.filter(i => i.es_correcta === false).length,
        pendientes: actuales.filter(i => i.es_correcta === null).length,
        ultimaFecha: [...intentos].sort((a, b) => b.id_respuesta_est - a.id_respuesta_est)[0]?.fecha || null
    };
}

function mostrarHistorial(historial) {
    const contenedor = elemento('historial'); contenedor.replaceChildren();
    const lecturas = agruparHistorial(historial);
    for (const [indice, lectura] of lecturas.entries()) {
        const intentos = lectura.preguntas.flat();
        const pendientes = intentos.filter(i => i.es_correcta === null).length;
        const resumen = resumenHistorial(lectura);
        const grupo = document.createElement('details'); grupo.className = 'lectura-historial'; grupo.open = pendientes > 0 || indice === 0;
        const cabecera = document.createElement('summary');
        const titulo = document.createElement('div'); titulo.className = 'titulo-lectura';
        const icono = nodoHistorial('span', 'icono-lectura', ''); icono.setAttribute('aria-hidden', 'true');
        titulo.append(icono, nodoHistorial('h4', '', lectura.titulo));
        const etiquetas = document.createElement('div'); etiquetas.className = 'etiquetas-historial';
        const version = nodoHistorial('span', 'etiqueta-historial ' + (lectura.archivada ? 'version-archivada' : ''), lectura.archivada ? 'Versión anterior' : 'Versión actual');
        version.title = lectura.archivada ? 'Solo consulta: conserva respuestas anteriores y ya no admite nuevos intentos.' : 'Disponible actualmente para que los estudiantes respondan.';
        etiquetas.append(version,
            nodoHistorial('span', 'meta-intento', `${lectura.preguntas.length} ${lectura.preguntas.length === 1 ? 'pregunta' : 'preguntas'} · ${intentos.length} ${intentos.length === 1 ? 'intento' : 'intentos'} en esta página`));
        const estados = document.createElement('div'); estados.className = 'resumen-lectura';
        estados.append(nodoHistorial('span', 'meta-intento', 'Últimos intentos de esta página:'));
        for (const [cantidad, clase, nombre] of [[resumen.correctas, 'estado-correcto', 'Satisfactorias'], [resumen.refuerzo, 'estado-refuerzo', 'Requieren refuerzo'], [resumen.pendientes, 'estado-pendiente', 'Pendientes']]) {
            if (cantidad) estados.append(nodoHistorial('span', 'etiqueta-historial ' + clase, `${nombre}: ${cantidad}`));
        }
        if (!resumen.correctas && !resumen.refuerzo && !resumen.pendientes) estados.append(nodoHistorial('span', 'meta-intento', 'Solo intentos anteriores'));
        if (resumen.ultimaFecha) etiquetas.append(nodoHistorial('span', 'fecha-lectura', `Última actividad: ${resumen.ultimaFecha}`));
        const encabezado = document.createElement('div'); encabezado.className = 'encabezado-lectura'; encabezado.append(titulo, etiquetas, estados);
        cabecera.append(encabezado); grupo.append(cabecera);
        const contenido = document.createElement('div'); contenido.className = 'contenido-lectura';
        for (const intentosPregunta of lectura.preguntas) {
            const seccion = document.createElement('section'); seccion.className = 'pregunta-historial';
            const reciente = intentosPregunta[0];
            seccion.append(nodoHistorial('h5', '', `${reciente.orden ? reciente.orden + '. ' : ''}${reciente.enunciado}`));
            const nivel = nodoHistorial('span', 'etiqueta-historial', reciente.tipo); seccion.append(nivel);
            seccion.append(tarjetaIntento(reciente));
            if (intentosPregunta.length > 1) {
                const anteriores = document.createElement('details'); anteriores.className = 'intentos-anteriores';
                anteriores.open = intentosPregunta.slice(1).some(i => i.es_correcta === null);
                anteriores.append(nodoHistorial('summary', '', `Ver ${intentosPregunta.length - 1} ${intentosPregunta.length === 2 ? 'intento anterior' : 'intentos anteriores'} en esta página`));
                for (const intento of intentosPregunta.slice(1)) anteriores.append(tarjetaIntento(intento));
                seccion.append(anteriores);
            }
            contenido.append(seccion);
        }
        grupo.append(contenido); contenedor.append(grupo);
    }
    if (!historial.length) contenedor.append(nodoHistorial('p', 'historial-vacio', 'Todavía no hay respuestas registradas para este estudiante.'));
}

function tarjetaIntento(intento) {
    const articulo = document.createElement('article'); articulo.className = 'intento';
    const meta = document.createElement('p'); meta.className = 'meta-intento';
    meta.textContent = `${intento.ultimo_intento ? 'Último intento' : 'Intento anterior'} · ${intento.fecha || 'Sin fecha'} · ${intento.tiempo_respuesta ?? '—'} s transcurridos`;
    const respuesta = document.createElement('p'); respuesta.textContent = `Respuesta: ${intento.respuesta || 'Sin respuesta'}`;
    const pendiente = intento.es_correcta === null;
    const resultado = document.createElement('p');
    resultado.className = 'resultado-intento ' + (pendiente ? 'estado-pendiente' : intento.es_correcta ? 'estado-correcto' : 'estado-refuerzo');
    resultado.textContent = pendiente ? 'Pendiente de revisión docente' : intento.fecha_revision ? (intento.es_correcta ? 'Cumple' : 'No cumple') : intento.es_correcta ? 'Correcta' : 'Incorrecta';
    respuesta.className = 'respuesta-estudiante';
    const feedback = document.createElement('div'); feedback.className = 'devolucion-historial';
    feedback.append(nodoHistorial('strong', '', 'Retroalimentación'), nodoHistorial('p', '', intento.fecha_revision
        ? (intento.devolucion || 'Sin retroalimentación del docente.')
        : (intento.retroalimentacion || 'No registrada para este intento')));
    articulo.append(meta, resultado, respuesta);
    if (!pendiente) articulo.append(feedback);
    if (pendiente) articulo.append(formularioRevision(intento));
    if (intento.fecha_revision) {
        const registro = document.createElement('p'); registro.className = 'nota-docente';
        registro.textContent = `Revisado por usuario ${intento.id_usuario_revisor} · ${intento.fecha_revision}`;
        articulo.append(registro);
    }
    return articulo;
}

function formularioRevision(intento) {
    const form = document.createElement('form'); form.className = 'revision-docente';
    const labelResultado = document.createElement('label'); labelResultado.textContent = 'Evaluación del docente';
    const cumple = document.createElement('select'); cumple.required = true;
    for (const [valor, titulo] of [['', 'Selecciona'], ['si', 'Cumple'], ['no', 'No cumple']]) {
        const opcion = document.createElement('option'); opcion.value = valor; opcion.textContent = titulo; cumple.append(opcion);
    }
    labelResultado.append(cumple); form.append(labelResultado);
    const label = document.createElement('label'); label.textContent = 'Retroalimentación al estudiante (opcional)';
    const devolucion = document.createElement('textarea'); devolucion.maxLength = 500;
    label.append(devolucion); form.append(label);
    const nota = document.createElement('p'); nota.className = 'nota-docente';
    nota.textContent = 'Selecciona el resultado de tu revisión. Puedes añadir una orientación para el estudiante.';
    const boton = document.createElement('button'); boton.type = 'submit'; boton.className = 'boton-docente'; boton.textContent = 'Guardar revisión';
    form.append(nota, boton);
    form.addEventListener('submit', async e => {
        e.preventDefault(); boton.disabled = true;
        try {
            if (!['si', 'no'].includes(cumple.value)) throw new Error('Debes seleccionar Cumple o No cumple');
            const body = { cumple: cumple.value === 'si', devolucion: devolucion.value };
            const res = await fetch(`/api/docente/respuestas/${intento.id_respuesta_est}/revision`, {
                method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` }, body: JSON.stringify(body)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo guardar la revisión');
            await cargarEstudiantes(); await cargarDetalle();
        } catch (error) { informar(error.message, true); }
        finally { boton.disabled = false; }
    });
    return form;
}

document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('token')) { window.location.href = '/'; return; }
    let usuario;
    try { usuario = JSON.parse(localStorage.getItem('user') || '{}'); } catch { usuario = {}; }
    if (![2, 3].includes(usuario.rol)) { window.location.href = '/dashboard.html'; return; }
    elemento('filtros').addEventListener('submit', e => { e.preventDefault(); paginaLista = 1; cargarEstudiantes(); });
    elemento('anterior-lista').addEventListener('click', () => { paginaLista--; cargarEstudiantes(); });
    elemento('siguiente-lista').addEventListener('click', () => { paginaLista++; cargarEstudiantes(); });
    elemento('anterior-historial').addEventListener('click', () => { paginaHistorial--; cargarDetalle(); });
    elemento('siguiente-historial').addEventListener('click', () => { paginaHistorial++; cargarDetalle(); });
    cargarEstudiantes();
});
