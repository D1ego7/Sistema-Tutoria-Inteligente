// Tiempo transcurrido visible + resolución; nunca se interpreta como velocidad lectora.
let enviandoRespuestas = false;
let actividadLista = false;
const inicioPorPregunta = new Map();
const ordenOpcionesPorPregunta = new Map();

function barajarOpciones(opciones, aleatorio = Math.random) {
    const mezcla = [...opciones];
    for (let i = mezcla.length - 1; i > 0; i--) {
        const j = Math.floor(aleatorio() * (i + 1));
        [mezcla[i], mezcla[j]] = [mezcla[j], mezcla[i]];
    }
    return mezcla;
}

function opcionesEnOrdenDeSesion(pregunta) {
    const opciones = pregunta.opciones || [];
    let usuario = {};
    try { usuario = JSON.parse(localStorage.getItem('user') || '{}'); } catch { /* Mantener la actividad utilizable. */ }
    const clave = `orden-opciones:${usuario?.id || 'sesion'}:${pregunta.id_pregunta}`;
    let orden = ordenOpcionesPorPregunta.get(clave);
    if (!orden) {
        try { orden = JSON.parse(sessionStorage.getItem(clave) || 'null'); } catch { /* Almacenamiento no disponible. */ }
    }
    const ids = new Set(opciones.map(opcion => opcion.id_opcion));
    const vigente = Array.isArray(orden) && orden.length === opciones.length &&
        new Set(orden).size === ids.size && orden.every(id => ids.has(id));
    if (!vigente) {
        orden = barajarOpciones(opciones).map(opcion => opcion.id_opcion);
        try { sessionStorage.setItem(clave, JSON.stringify(orden)); } catch { /* Caché en memoria como respaldo. */ }
    }
    ordenOpcionesPorPregunta.set(clave, orden);
    const porId = new Map(opciones.map(opcion => [opcion.id_opcion, opcion]));
    return orden.map(id => porId.get(id));
}

function iniciarTiempos(cards = document.querySelectorAll('.question-card')) {
    const ahora = performance.now();
    cards.forEach(card => {
        if (card.querySelector('input:not(:disabled)')) {
            inicioPorPregunta.set(Number(card.dataset.idPregunta), ahora);
        }
    });
}

function segundosTranscurridos(idPregunta, ahora = performance.now()) {
    const inicio = inicioPorPregunta.get(idPregunta);
    if (inicio === undefined) throw new Error('La actividad todavía no está lista');
    return Math.ceil(Math.max(0, ahora - inicio) / 1000);
}

function prepararReintento() {
    const cards = [...document.querySelectorAll('.question-card')];
    cards.forEach(card => {
        if (card.classList.contains('answer-correct') || card.classList.contains('answer-pending')) return;
        card.querySelectorAll('input').forEach(input => {
            if (input.type === 'radio') input.checked = false;
            else input.value = '';
            input.disabled = false;
        });
        card.classList.remove('answer-incorrect', 'question-unanswered');
    });
    iniciarTiempos(cards);
    document.getElementById('submit-answers').style.display = 'block';
    const container = document.getElementById('button-container');
    if (container) container.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', async function () {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const textId = new URLSearchParams(window.location.search).get('id');
    if (!token || !textId) { window.location.href = '/'; return; }
    const greeting = document.getElementById('user-greeting');
    if (greeting) greeting.textContent = `Hola, ${user.nombre || 'Estudiante'}`;
    const button = document.getElementById('submit-answers');
    button.disabled = true;
    try {
        await Promise.all([loadText(textId), loadQuestions(textId)]);
        await loadPreviousAnswers(textId);
        iniciarTiempos();
        actividadLista = true;
        button.disabled = false;
    } catch (error) {
        showToast(error.message || 'No se pudo cargar la actividad', false);
    }
    const logout = document.getElementById('logout-btn');
    if (logout) logout.addEventListener('click', () => {
        localStorage.removeItem('token'); localStorage.removeItem('user');
        window.location.href = '/';
    });
    document.getElementById('back-btn').addEventListener('click', () => { window.location.href = '/menu.html'; });
    button.addEventListener('click', async () => {
        if (!actividadLista || enviandoRespuestas) return;
        const cards = [...document.querySelectorAll('.question-card')]
            .filter(card => card.querySelector('input:not(:disabled)'));
        if (!cards.length) return;
        const answers = cards.map(obtenerRespuestaDePregunta);
        if (answers.some(answer => !answer)) {
            cards.forEach((card, i) => card.classList.toggle('question-unanswered', !answers[i]));
            showToast('Debes responder todas las preguntas habilitadas', false);
            return;
        }
        if (answers.some(answer => !answer.idOpcion && answer.respuesta.length > 100)) {
            showToast('Cada respuesta admite un máximo de 100 caracteres', false);
            return;
        }
        const ahora = performance.now(); // Congelar antes de la espera HTTP.
        const payload = answers.map(answer => ({
            id_pregunta: answer.idPregunta, respuesta: answer.respuesta,
            id_opcion: answer.idOpcion,
            tiempo_respuesta: segundosTranscurridos(answer.idPregunta, ahora)
        }));
        enviandoRespuestas = true;
        button.disabled = true;
        let guardadas = false;
        try {
            const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
            const res = await fetch('/respuestas-lectura', {
                method: 'POST', headers,
                body: JSON.stringify({ id_texto: Number(textId), respuestas: payload })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se guardaron las respuestas');
            guardadas = true;
            data.respuestas.forEach(result => {
                const card = cards.find(card => Number(card.dataset.idPregunta) === result.id_pregunta);
                card.classList.remove('answer-correct', 'answer-incorrect', 'question-unanswered');
                marcarResultado(card,result.es_correcta);
                card.querySelectorAll('input').forEach(input => { input.disabled = true; });
            });
            const feedbackRes = await fetch('/feedback-sesion', {
                method: 'POST', headers, body: JSON.stringify({ id_texto: Number(textId) })
            });
            const feedback = await feedbackRes.json();
            if (!feedbackRes.ok) throw new Error(feedback.error || 'No se pudo cargar el resumen');
            showSummaryModal(data.respuestas.length,
                data.respuestas.filter(answer => answer.es_correcta).length, feedback);
            button.style.display = 'none';
        } catch (error) {
            showToast((guardadas ? 'Respuestas guardadas. No se pudo mostrar el resumen: ' : '') + error.message, false);
            if (guardadas && document.querySelector('.answer-incorrect')) showRetryButton();
        } finally {
            enviandoRespuestas = false;
            button.disabled = false;
        }
    });
});

function showToast(mensaje, isSuccess = true) {
    const toast = document.createElement("div");
    toast.className = `toast ${isSuccess ? 'success' : 'error'}`;
    toast.textContent = mensaje;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "slideOut 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

function showSummaryModal(answered, correct, feedbackData) {
    const percentage = feedbackData?.puntaje?.porcentaje ?? (answered > 0 ? Math.round((correct / answered) * 100) : 0);

    document.getElementById("summary-answered").textContent = feedbackData?.puntaje?.respondidas ?? answered;
    document.getElementById("summary-correct").textContent = feedbackData?.puntaje?.correctas ?? correct;
    const pendientes=feedbackData?.puntaje?.pendientes || 0;
    const enRevision=pendientes>0 || feedbackData?.plan_reforzamiento?.estado==='pendiente_revision';
    const evaluadas=feedbackData?.puntaje?.evaluadas ?? Math.max(0,answered-pendientes);
    const mensajePendiente='La recomendación de práctica estará disponible cuando el docente termine de revisar tus respuestas. Las pendientes no cuentan como errores.';
    document.getElementById('summary-title').textContent=enRevision?'Respuestas enviadas':'Resumen de la sesión';
    document.getElementById('summary-correct').textContent=evaluadas===0 && enRevision?'Por evaluar':(feedbackData?.puntaje?.correctas ?? correct);
    document.getElementById('summary-percentage').textContent=evaluadas===0 && enRevision?'Pendiente':percentage+'%';
    const estadoRevision=document.getElementById('summary-review-status');
    estadoRevision.hidden=!enRevision;
    estadoRevision.textContent=pendientes
        ? `${pendientes} ${pendientes===1?'respuesta pendiente':'respuestas pendientes'} de revisión docente. ${evaluadas ? 'El porcentaje incluye solo respuestas evaluadas.' : 'El resultado aún no está disponible.'}`
        : 'Hay respuestas de otras lecturas pendientes de revisión docente. Las recomendaciones se actualizarán al finalizar la revisión.';

    document.getElementById("feedback-level").textContent = feedbackData?.nivel_actual || "-";
    document.getElementById("feedback-trend").textContent = enRevision?'En revisión':(feedbackData?.estado_nivel || '-');
    document.getElementById("feedback-next-level").textContent = feedbackData?.nuevo_nivel || "-";
    document.getElementById("feedback-tutor-message").textContent = feedbackData?.mensaje_tutor || "Sigue practicando para mejorar tu comprensión.";

    const errorsContainer = document.getElementById("feedback-errors");
    errorsContainer.innerHTML = "";
    if (feedbackData?.errores_detectados?.length > 0) {
        const questionIndexById = {};
        document.querySelectorAll(".question-card").forEach((card, index) => {
            questionIndexById[card.dataset.idPregunta] = index + 1;
        });

        const list = document.createElement("ul");
        list.className = "feedback-list";
        feedbackData.errores_detectados.forEach(error => {
            const numeroPregunta = questionIndexById[String(error.pregunta_id)] || error.pregunta_id;
            const item = document.createElement("li");
            item.textContent = `Pregunta ${numeroPregunta}: nivel ${error.nivel} — respuesta esperada: ${error.respuesta_correcta}`;
            list.appendChild(item);
        });
        errorsContainer.appendChild(list);
    } else {
        const empty = document.createElement("p");
        empty.className = "feedback-empty";
        empty.textContent = enRevision ? 'Las respuestas pendientes todavía no tienen un resultado. No se consideran incorrectas.' : "No se detectaron errores específicos en esta sesión.";
        errorsContainer.appendChild(empty);
    }

    const practiceContainer = document.getElementById("feedback-practice");
    practiceContainer.innerHTML = "";
    const plan = feedbackData?.plan_reforzamiento;
    const practicaUnica = enRevision ? mensajePendiente : plan?.mensaje || null;
    if (practicaUnica) {
        const paragraph = document.createElement("p");
        paragraph.className = "feedback-text";
        paragraph.textContent = practicaUnica;
        practiceContainer.appendChild(paragraph);
    } else {
        const empty = document.createElement("p");
        empty.className = "feedback-empty";
        empty.textContent = "No hay recomendaciones de práctica por ahora.";
        practiceContainer.appendChild(empty);
    }

    const recommendationBox = document.getElementById("recommendation-box");
    if (enRevision) {
        recommendationBox.style.display = 'none';
        document.getElementById('recommendation-text').textContent='';
    } else if (percentage >= 80) {
        recommendationBox.style.display = "block";
        document.getElementById("recommendation-text").textContent = feedbackData.mensaje_tutor;
    } else if (percentage < 50) {
        recommendationBox.style.display = "block";
        document.getElementById("recommendation-text").textContent = "No te preocupes. Practica un poco más en este mismo nivel y lo harás mejor.";
    } else {
        recommendationBox.style.display = "block";
        document.getElementById("recommendation-text").textContent = "Buen trabajo. Sigue practicando y poco a poco será más fácil.";
    }

    document.getElementById("summary-modal").style.display = "flex";

    document.getElementById("btn-continue-dashboard").onclick = function () {
        window.location.href = "menu.html";
    };

    document.getElementById('btn-retry-reading').onclick = () => {
        document.getElementById('summary-modal').style.display = 'none';
        prepararReintento();
    };
    document.getElementById('btn-retry-reading').style.display=document.querySelector('.answer-incorrect')?'block':'none';
    let apply = document.getElementById('apply-recommended-level');
    if (!apply) {
        apply = document.createElement('button');
        apply.id = 'apply-recommended-level';
        apply.className = 'btn-primary';
        document.querySelector('.modal-footer').appendChild(apply);
    }
    apply.textContent = 'Aplicar nivel recomendado';
    apply.style.display = !enRevision && feedbackData.nuevo_nivel !== feedbackData.nivel_actual ? 'block' : 'none';
    apply.onclick = async () => {
        apply.disabled = true;
        try {
            const res = await fetch('/aplicar-nivel-recomendado', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                body: JSON.stringify({ nivel_actual: feedbackData.nivel_actual, nuevo_nivel: feedbackData.nuevo_nivel })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo aplicar el nivel');
            window.location.href = '/menu.html';
        } catch (error) { showToast(error.message, false); }
        finally { apply.disabled = false; }
    };

}

async function loadPreviousAnswers(textId) {
    const res = await fetch(`/respuestas-texto/${textId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'No se pudieron cargar los intentos previos');
    const answers = data.respuestas || {};
    let incorrectas = 0;
    Object.entries(answers).forEach(([id, answer]) => {
        const card = document.querySelector(`[data-id-pregunta="${id}"]`);
        if (!card) return;
        const text = card.querySelector('input[type="text"]');
        if (text) text.value = answer.respuesta;
        else card.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.checked = radio.dataset.textoOpcion === answer.respuesta;
        });
        marcarResultado(card,answer.es_correcta);
        if (answer.devolucion) {
            const devolucion=document.createElement('p'); devolucion.className='estado-revision';
            devolucion.textContent=`Devolución del docente: ${answer.devolucion}`; card.appendChild(devolucion);
        }
        card.querySelectorAll('input').forEach(input => { input.disabled = true; });
        if (answer.es_correcta === false) incorrectas++;
    });
    if (data.todas_correctas) document.getElementById('submit-answers').style.display = 'none';
    else if (incorrectas) showRetryButton();
    else if (data.estado_lectura?.pendientes > 0 && data.estado_lectura.respondidas === data.estado_lectura.total_preguntas)
        document.getElementById('submit-answers').style.display = 'none';
}

function marcarResultado(card,correcta) {
    card.classList.remove('answer-correct','answer-incorrect','answer-pending');
    const previo=card.querySelector('.estado-revision');
    if (previo) previo.remove();
    if (correcta === null) {
        card.classList.add('answer-pending');
        const aviso=document.createElement('p'); aviso.className='estado-revision';
        aviso.textContent='Pendiente de revisión docente. Actualiza la lectura para consultar el resultado.';
        card.appendChild(aviso);
    } else card.classList.add(correcta ? 'answer-correct':'answer-incorrect');
}

function showRetryButton() {
    const submitBtn = document.getElementById("submit-answers");
    if (document.getElementById("retry-button")) {
        return; // Ya existe el botón
    }

    const container = document.createElement("div");
    container.id = "button-container";
    container.style.display = "flex";
    container.style.gap = "1rem";
    container.style.marginTop = "1.5rem";

    const retryBtn = document.createElement("button");
    retryBtn.id = "retry-button";
    retryBtn.className = "retry-button-styled";
    retryBtn.textContent = "🔄 Volver a intentar";
    retryBtn.style.flex = "1";

    retryBtn.addEventListener('click', prepararReintento);

    const submitBtnClone = document.createElement("button");
    submitBtnClone.id = "submit-answers-copy";
    submitBtnClone.className = "submit-answers-styled";
    submitBtnClone.textContent = "✓ Enviar respuestas";
    submitBtnClone.style.flex = "1";

    container.appendChild(retryBtn);
    // container.appendChild(submitBtnClone);
    submitBtn.parentElement.appendChild(container);
    submitBtn.style.display = "none";
}

async function loadText(id) {
    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`/texto/${id}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/";
            return;
        }

        const text = await res.json();
        if (!res.ok) throw new Error(text.error || 'No se pudo cargar la lectura');
        document.getElementById("text-title").textContent = text.titulo;
        document.getElementById("reading-emoji").textContent = getEmojiForText(text.titulo);
        document.getElementById("text-body").textContent = text.contenido;
    } catch (err) {
        throw err;
    }
}

async function loadQuestions(id) {
    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`/preguntas/${id}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        const questions = await res.json();
        if (!res.ok || !Array.isArray(questions) || !questions.length) {
            throw new Error(questions.error || 'La lectura no tiene preguntas disponibles');
        }
        displayQuestions(questions);
    } catch (err) {
        throw err;
    }
}

function displayQuestions(questions) {
    const container = document.getElementById("questions-list");
    container.innerHTML = "";

    questions.sort((a, b) => (a.orden || 0) - (b.orden || 0));

    questions.forEach((q, idx) => {
        const div = document.createElement("div");
        div.className = "question-card";
        div.dataset.idPregunta = q.id_pregunta;
        div.dataset.tipoRespuesta = q.tipo_respuesta;

        const label = document.createElement("p");
        label.className = "question-label";
        label.innerHTML = `<strong>${q.orden || idx + 1}.</strong> ${escaparHtml(q.enunciado)}`;
        div.appendChild(label);

        if (q.tipo_respuesta === "opcion") {
            const optionsContainer = document.createElement("div");
            optionsContainer.className = "question-options";

            opcionesEnOrdenDeSesion(q).forEach(opcion => {
                const optionLabel = document.createElement("label");
                optionLabel.className = "option-card";
                optionLabel.innerHTML = `
                    <input type="radio" name="q-${q.id_pregunta}" value="${opcion.id_opcion}" data-texto-opcion="${escaparAtributo(opcion.texto_opcion)}">
                    <span class="option-marker"></span>
                    <span class="option-text">${escaparHtml(opcion.texto_opcion)}</span>
                `;
                optionsContainer.appendChild(optionLabel);
            });

            div.appendChild(optionsContainer);
        } else {
            const input = document.createElement("input");
            input.type = "text";
            input.id = `q-${q.id_pregunta}`;
            input.placeholder = "Tu respuesta";
            input.maxLength = 100;
            div.appendChild(input);
        }

        container.appendChild(div);
    });
}

function obtenerRespuestaDePregunta(card) {
    const idPregunta = Number(card.dataset.idPregunta);
    const radio = card.querySelector("input[type='radio']:checked");

    if (radio) {
        return {
            idPregunta,
            idOpcion: Number(radio.value),
            respuesta: radio.dataset.textoOpcion
        };
    }

    const input = card.querySelector("input[type='text']");
    if (input && input.value.trim()) {
        return {
            idPregunta,
            idOpcion: null,
            respuesta: input.value.trim()
        };
    }

    return null;
}

function escaparHtml(texto) {
    const elemento = document.createElement("div");
    elemento.textContent = texto || "";
    return elemento.innerHTML;
}

function escaparAtributo(texto) {
    return String(texto || "")
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}
