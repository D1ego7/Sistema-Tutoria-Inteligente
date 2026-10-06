/* Vista de solo consulta. Los permisos se verifican nuevamente en el servidor. */
let paginaLista = 1;
let paginaHistorial = 1;
let estudianteSeleccionado = null;
let revisionLista = 0;
let revisionDetalle = 0;
const elemento = id => document.getElementById(id);
const texto = (id, valor) => { elemento(id).textContent = valor; };

async function consultar(ruta) {
    const res = await fetch(ruta, {headers: {Authorization: `Bearer ${localStorage.getItem('token')}`}});
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
        const params = new URLSearchParams({pagina: paginaLista, buscar: elemento('buscar').value, nivel: elemento('nivel').value});
        const data = await consultar(`/api/docente/estudiantes?${params}`);
        if (revision !== revisionLista) return;
        for (const e of data.estudiantes) {
            const fila = document.createElement('tr');
            if (e.id_estudiante === estudianteSeleccionado) fila.classList.add('seleccionado');
            celda(fila, e.nombre);
            celda(fila, e.puntaje_diagnostico === null ? 'Pendiente' : `${e.puntaje_diagnostico}% · ${e.nivel_diagnostico}`);
            celda(fila, e.nivel_actual || 'Sin asignar');
            celda(fila, e.porcentaje_acierto === null ? 'Sin respuestas' : `${e.porcentaje_acierto}% (${e.correctas}/${e.respondidas})`);
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
        texto('aciertos', data.evaluacion.total_respuestas ? `${data.evaluacion.porcentaje_acierto}%` : 'Sin respuestas');
        texto('completadas', data.lecturas_completadas); texto('intentos', data.total_intentos);
        texto('diagnostico', data.diagnostico ? `${data.diagnostico.puntaje}% de aciertos · Nivel asignado: ${data.diagnostico.nivel_asignado} · Fecha: ${data.diagnostico.fecha || 'Sin fecha'}` : 'El estudiante todavía no ha completado el diagnóstico.');
        texto('recomendacion', data.evaluacion.total_respuestas ? data.recomendacion.razon : 'Se necesitan respuestas para orientar el seguimiento.');
        elemento('por-nivel').replaceChildren();
        for (const nivel of ['literal', 'inferencial', 'crítico']) {
            const datos = data.evaluacion.por_nivel[nivel];
            const fila = document.createElement('tr');
            for (const valor of [nivel, datos?.total ?? 'Sin datos', datos?.correctas ?? '—', datos ? `${datos.porcentaje}%` : '—', datos ? datos.total - datos.correctas : '—']) celda(fila, valor);
            elemento('por-nivel').appendChild(fila);
        }
        elemento('historial').replaceChildren();
        for (const intento of data.historial) {
            const articulo = document.createElement('article'); articulo.className = 'intento';
            const meta = document.createElement('p'); meta.className = 'meta-intento';
            meta.textContent = `${intento.titulo} · ${intento.tipo} · ${intento.fecha || 'Sin fecha'} · ${intento.tiempo_respuesta ?? '—'} s · ${intento.ultimo_intento ? 'Último intento' : 'Intento anterior'}`;
            const pregunta = document.createElement('h4'); pregunta.textContent = intento.enunciado;
            const respuesta = document.createElement('p'); respuesta.textContent = `Respuesta: ${intento.respuesta || 'Sin respuesta'}`;
            const resultado = document.createElement('p'); resultado.className = intento.es_correcta ? 'respuesta-correcta' : 'respuesta-incorrecta'; resultado.textContent = intento.es_correcta ? 'Correcta' : 'Incorrecta';
            const feedback = document.createElement('p'); feedback.textContent = `Retroalimentación: ${intento.retroalimentacion || 'No registrada para este intento'}`;
            articulo.append(meta, pregunta, respuesta, resultado, feedback); elemento('historial').appendChild(articulo);
        }
        if (!data.historial.length) texto('historial', 'No hay intentos registrados.');
        paginar('historial', data); elemento('detalle').hidden = false;
        informar('Seguimiento actualizado.');
        if (enfocar) elemento('nombre-estudiante').focus();
    } catch (error) { if (revision === revisionDetalle) informar(error.message, true); }
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
