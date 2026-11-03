document.addEventListener('DOMContentLoaded', () => {
    const $ = id => document.getElementById(id);
    let usuario;
    try { usuario = JSON.parse(localStorage.getItem('user') || '{}'); } catch { usuario = {}; }
    if (!localStorage.getItem('token')) { window.location.href = '/'; return; }
    if (usuario.rol !== 3) { window.location.href = usuario.rol === 2 ? '/docente.html' : '/dashboard.html'; return; }
    $('panel-administrador').hidden = false;
    let pagina = 1, cuentas = [], editando = null, eliminando = null, ocupado = false, consulta = 0;

    async function peticion(ruta, metodo = 'GET', datos) {
        const opciones = { method: metodo, headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } };
        if (datos !== undefined) { opciones.headers['Content-Type'] = 'application/json'; opciones.body = JSON.stringify(datos); }
        const respuesta = await fetch('/api/administrador/' + ruta, opciones);
        if (respuesta.status === 401 || respuesta.status === 403) {
            localStorage.removeItem('token'); localStorage.removeItem('user'); window.location.href = '/';
            throw new Error('La sesión terminó o ya no tiene permisos. Vuelve a ingresar.');
        }
        const contenido = await respuesta.json();
        if (!respuesta.ok) throw new Error(contenido.error || 'No se pudo completar la operación.');
        return contenido;
    }
    function estado(mensaje, error = false) {
        $('estado-administracion').textContent = mensaje;
        $('estado-administracion').dataset.error = String(error);
    }
    async function cargarResumen() {
        try {
            const datos = await peticion('resumen');
            ['estudiantes', 'docentes', 'lecturas', 'pendientes'].forEach(c => { $('total-' + c).textContent = datos[c]; });
        } catch (error) { estado(error.message, true); }
    }
    function celda(fila, texto) {
        const td = document.createElement('td'); td.textContent = texto; fila.append(td); return td;
    }
    async function cargarCuentas() {
        const turno = ++consulta;
        $('anterior-cuentas').disabled = true; $('siguiente-cuentas').disabled = true;
        const parametros = new URLSearchParams({ rol: $('rol-cuentas').value, buscar: $('buscar-cuentas').value.trim(), pagina: String(pagina) });
        try {
            const datos = await peticion('usuarios?' + parametros);
            if (turno !== consulta) return;
            if (pagina > 1 && !datos.cuentas.length) { pagina--; return cargarCuentas(); }
            cuentas = datos.cuentas;
            $('lista-cuentas').replaceChildren();
            for (const cuenta of cuentas) {
                const fila = document.createElement('tr');
                celda(fila, cuenta.nombre); celda(fila, cuenta.email);
                const n = cuenta.id_rol === 1 ? cuenta.respuestas : cuenta.revisiones;
                celda(fila, `${n} ${cuenta.id_rol === 1 ? 'respuestas' : 'revisiones'}`);
                const acciones = document.createElement('div'); acciones.className = 'acciones-cuenta';
                for (const [texto, clase, accion] of [['Editar', 'boton-secundario', () => abrirFormulario(cuenta)], ['Eliminar', 'boton-peligro', () => abrirEliminacion(cuenta)]]) {
                    const boton = document.createElement('button'); boton.type = 'button'; boton.className = clase; boton.textContent = texto;
                    boton.setAttribute('aria-label', `${texto} a ${cuenta.nombre}`); boton.addEventListener('click', accion); acciones.append(boton);
                }
                const td = document.createElement('td'); td.append(acciones); fila.append(td); $('lista-cuentas').append(fila);
            }
            if (!cuentas.length) { const fila = document.createElement('tr'); celda(fila, 'No se encontraron cuentas con estos filtros.').colSpan = 4; $('lista-cuentas').append(fila); }
            $('pagina-cuentas').textContent = `Página ${pagina} de ${Math.max(1, Math.ceil(datos.total / datos.por_pagina))} · ${datos.total} cuentas`;
            $('anterior-cuentas').disabled = pagina <= 1;
            $('siguiente-cuentas').disabled = pagina * datos.por_pagina >= datos.total;
        } catch (error) { if (turno === consulta) { $('lista-cuentas').replaceChildren(); estado(error.message, true); } }
    }
    function abrirFormulario(cuenta = null) {
        if (ocupado) return;
        editando = cuenta;
        $('formulario-cuenta').reset(); $('error-cuenta').textContent = '';
        const docente = (cuenta ? cuenta.id_rol : Number($('rol-cuentas').value)) === 2;
        $('tipo-formulario').textContent = docente ? 'Docente' : 'Estudiante';
        $('titulo-formulario').textContent = cuenta ? 'Editar cuenta' : `Nuevo ${docente ? 'docente' : 'estudiante'}`;
        $('nombre-cuenta').value = cuenta ? cuenta.nombre : ''; $('correo-cuenta').value = cuenta ? cuenta.email : '';
        $('clave-cuenta').required = !cuenta; $('clave-cuenta').value = cuenta ? '' : 'password123';
        $('etiqueta-clave').textContent = cuenta ? 'Nueva contraseña (opcional)' : 'Contraseña';
        $('ayuda-clave').textContent = cuenta ? 'Deja este campo vacío para conservar la contraseña actual.' : 'Contraseña inicial: password123. Puedes cambiarla antes de guardar.';
        $('dialogo-cuenta').showModal(); $('nombre-cuenta').focus();
    }
    function abrirEliminacion(cuenta) {
        if (ocupado) return;
        eliminando = cuenta; $('error-eliminar').textContent = '';
        $('nombre-eliminar').textContent = `${cuenta.nombre} · ${cuenta.email}`;
        $('aviso-eliminar').textContent = cuenta.id_rol === 1
            ? 'Se eliminará el acceso del estudiante y todo su historial: diagnóstico, respuestas, retroalimentación, progreso y reportes.'
            : 'Se eliminará el acceso del docente y sus reportes. Sus valoraciones y comentarios a estudiantes se conservarán.';
        $('dialogo-eliminar').showModal(); $('cancelar-eliminar').focus();
    }
    function bloquear(valor) {
        ocupado = valor;
        ['guardar-cuenta', 'cancelar-cuenta', 'confirmar-eliminar', 'cancelar-eliminar'].forEach(id => { $(id).disabled = valor; });
    }
    $('formulario-cuenta').addEventListener('submit', async evento => {
        evento.preventDefault(); if (ocupado) return;
        $('nombre-cuenta').value = $('nombre-cuenta').value.trim().replace(/\s+/g, ' ');
        $('correo-cuenta').value = $('correo-cuenta').value.trim().toLowerCase();
        if (!$('formulario-cuenta').reportValidity()) return;
        const datos = { nombre: $('nombre-cuenta').value.trim(), email: $('correo-cuenta').value.trim().toLowerCase(), password: $('clave-cuenta').value };
        if (!editando) datos.rol = Number($('rol-cuentas').value);
        bloquear(true); $('error-cuenta').textContent = '';
        try {
            const resultado = await peticion('usuarios' + (editando ? '/' + editando.id_usuario : ''), editando ? 'PUT' : 'POST', datos);
            $('dialogo-cuenta').close(); estado(resultado.mensaje);
            await Promise.all([cargarCuentas(), cargarResumen()]);
        } catch (error) {
            $('error-cuenta').textContent = error instanceof TypeError || error instanceof SyntaxError
                ? 'No se pudo confirmar el guardado. Los datos se conservan; consulta la lista antes de volver a guardar.' : error.message;
        }
        finally { bloquear(false); }
    });
    $('confirmar-eliminar').addEventListener('click', async () => {
        if (ocupado || !eliminando) return;
        bloquear(true); $('error-eliminar').textContent = '';
        try {
            const resultado = await peticion('usuarios/' + eliminando.id_usuario, 'DELETE', { confirmacion: eliminando.email });
            $('dialogo-eliminar').close(); estado(resultado.mensaje);
            await Promise.all([cargarCuentas(), cargarResumen()]);
        } catch (error) {
            $('error-eliminar').textContent = error instanceof TypeError || error instanceof SyntaxError
                ? 'No se pudo confirmar la eliminación. Consulta la lista antes de repetirla.' : error.message;
        }
        finally { bloquear(false); }
    });
    $('cancelar-cuenta').addEventListener('click', () => $('dialogo-cuenta').close());
    $('cancelar-eliminar').addEventListener('click', () => $('dialogo-eliminar').close());
    ['dialogo-cuenta', 'dialogo-eliminar'].forEach(id => { $(id).addEventListener('cancel', evento => { if (ocupado) evento.preventDefault(); }); });
    $('nueva-cuenta').addEventListener('click', () => abrirFormulario());
    $('filtros-cuentas').addEventListener('submit', evento => { evento.preventDefault(); pagina = 1; estado(''); cargarCuentas(); });
    $('rol-cuentas').addEventListener('change', () => { pagina = 1; $('nueva-cuenta').textContent = Number($('rol-cuentas').value) === 2 ? '+ Nuevo docente' : '+ Nuevo estudiante'; estado(''); cargarCuentas(); });
    $('anterior-cuentas').addEventListener('click', () => { pagina--; cargarCuentas(); });
    $('siguiente-cuentas').addEventListener('click', () => { pagina++; cargarCuentas(); });
    cargarResumen(); cargarCuentas();
});
