// reading.js
document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("token");
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const urlParams = new URLSearchParams(window.location.search);
    const textId = urlParams.get('id');

    if (!token || !textId) {
        window.location.href = "/";
        return;
    }

    const userGreeting = document.getElementById("user-greeting");
    if (userGreeting) {
        userGreeting.textContent = `Hola, ${user.nombre || 'Estudiante'}`;
    }

    loadText(textId);
    loadQuestions(textId);
    loadPreviousAnswers(textId);

    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", function () {
            localStorage.removeItem("token");
            localStorage.removeItem("user");
            window.location.href = "/";
        });
    }

    document.getElementById("back-btn").addEventListener("click", function () {
        window.location.href = "menu.html";
    });

    document.getElementById("submit-answers").addEventListener("click", async function () {
        const token = localStorage.getItem("token");
        const questionCards = [...document.querySelectorAll(".question-card")];
        const respuestas = questionCards.map(obtenerRespuestaDePregunta);

        if (respuestas.some(respuesta => !respuesta)) {
            questionCards.forEach((card, index) => {
                card.classList.toggle("question-unanswered", !respuestas[index]);
            });
            showToast("Debes responder todas las preguntas", false);
            return;
        }

        let enviadas = 0;
        let correctas = 0;

        for (const respuestaPregunta of respuestas) {
            const { idPregunta, respuesta, idOpcion } = respuestaPregunta;

            try {
                const res = await fetch("http://127.0.0.1:5000/respuesta-con-feedback", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        id_pregunta: idPregunta,
                        respuesta: respuesta,
                        id_opcion: idOpcion,
                        tiempo_respuesta: 10
                    })
                });

                const data = await res.json();

                if (!res.ok) {
                    console.error("Error del servidor:", data);
                    showToast(data.error || "No se pudo guardar la respuesta", false);
                    continue;
                }

                console.log("Respuesta guardada:", data);
                enviadas++;
                if (data.es_correcta) correctas++;

                // Mostrar toast con resultado de cada respuesta
                const mensaje = data.es_correcta ? "✓ Correcto" : "✗ Incorrecto";
                showToast(mensaje, data.es_correcta);

            } catch (err) {
                console.error("Error enviando respuesta:", err);
                showToast("Error al guardar respuesta", false);
            }
        }

        // Mostrar modal con resumen de sesión y retroalimentación del tutor
        const feedbackRes = await fetch("http://127.0.0.1:5000/feedback-sesion", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ id_texto: parseInt(textId) })
        });

        const feedbackData = await feedbackRes.json();
        if (!feedbackRes.ok) {
            console.error("Error obteniendo feedback:", feedbackData);
            showToast(feedbackData.error || "No se pudo generar la retroalimentación", false);
            return;
        }

        showSummaryModal(enviadas, correctas, feedbackData);
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
    document.getElementById("summary-percentage").textContent = percentage + "%";

    document.getElementById("feedback-level").textContent = feedbackData?.nivel_actual || "-";
    document.getElementById("feedback-trend").textContent = feedbackData?.estado_nivel ? feedbackData.estado_nivel.toUpperCase() : "-";
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
        empty.textContent = "No se detectaron errores específicos en esta sesión.";
        errorsContainer.appendChild(empty);
    }

    const practiceContainer = document.getElementById("feedback-practice");
    practiceContainer.innerHTML = "";
    const plan = feedbackData?.plan_reforzamiento;
    const practicaUnica = plan?.mensaje || null;
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
    if (percentage >= 80) {
        recommendationBox.style.display = "block";
        document.getElementById("recommendation-text").textContent = "¡Excelente! Respondiste muy bien. Puedes probar un poco más difícil si quieres.";
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

    document.getElementById("btn-retry-reading").onclick = function () {
        document.getElementById("summary-modal").style.display = "none";
        const inputs = document.querySelectorAll(".question-card input");
        inputs.forEach(input => {
            if (!input.disabled) {
                input.value = "";
                input.style.backgroundColor = "#ffffff";
                input.style.borderColor = "#d1d5db";
                input.style.color = "#000000";
            }
        });
        const submitBtn = document.getElementById("submit-answers");
        const buttonContainer = document.getElementById("button-container");
        if (submitBtn && submitBtn.style.display === "none") {
            submitBtn.style.display = "block";
        }
        if (buttonContainer) {
            buttonContainer.style.display = "none";
        }
    };
}

async function loadPreviousAnswers(textId) {
    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`http://127.0.0.1:5000/respuestas-texto/${textId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!res.ok) {
            console.log("No hay respuestas previas");
            return;
        }

        const data = await res.json();
        const respuestas = data.respuestas || {};
        const todasCorrectas = data.todas_correctas || false;

        // Esperar a que los inputs estén listos
        setTimeout(() => {
            // Contar respuestas correctas e incorrectas
            let totalRespuestas = Object.keys(respuestas).length;
            let respuestasCorrectas = 0;
            let respuestasIncorrectas = 0;

            // Prellenar inputs con las respuestas
            for (const idPregunta in respuestas) {
                const card = document.querySelector(`[data-id-pregunta="${idPregunta}"]`);
                if (!card) continue;

                const respuesta = respuestas[idPregunta];
                const input = card.querySelector("input[type='text']");
                const radios = [...card.querySelectorAll("input[type='radio']")];

                if (input) {
                    input.value = respuesta.respuesta;
                } else {
                    const radioSeleccionado = radios.find(radio => radio.dataset.textoOpcion === respuesta.respuesta);
                    if (radioSeleccionado) radioSeleccionado.checked = true;
                }

                card.classList.add(respuesta.es_correcta ? "answer-correct" : "answer-incorrect");
                card.querySelectorAll("input").forEach(control => {
                    control.disabled = true;
                });

                if (respuesta.es_correcta) {
                    respuestasCorrectas++;
                } else {
                    respuestasIncorrectas++;
                }
            }

            // Si todas son correctas, aplicar estilos a todos y ocultar botones
            if (todasCorrectas && totalRespuestas > 0) {
                document.getElementById("submit-answers").style.display = "none";
            } else if (respuestasIncorrectas > 0) {
                document.getElementById("submit-answers").style.display = "none";
                showRetryButton();
            }
        }, 500);

    } catch (err) {
        console.error("Error cargando respuestas previas:", err);
    }
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

    retryBtn.addEventListener("click", function () {
        // Limpiar SOLO los inputs incorrectos (que no están deshabilitados)
        // Las respuestas correctas (deshabilitadas) permanecen intactas
        const questionCards = document.querySelectorAll(".question-card");
        questionCards.forEach(card => {
            if (card.classList.contains("answer-incorrect")) {
                card.querySelectorAll("input").forEach(input => {
                    input.value = "";
                    input.checked = false;
                    input.disabled = false;
                });
                card.classList.remove("answer-incorrect", "question-unanswered");
            }
        });
        // Mostrar botón de enviar de nuevo y ocultar retry
        submitBtn.style.display = "block";
        container.style.display = "none";
    });

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
        const res = await fetch(`http://127.0.0.1:5000/texto/${id}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/";
            return;
        }

        const text = await res.json();
        document.getElementById("text-title").textContent = text.titulo;
        document.getElementById("reading-emoji").textContent = getEmojiForText(text.titulo);
        document.getElementById("text-body").textContent = text.contenido;
    } catch (err) {
        console.error("Error cargando texto:", err);
    }
}

async function loadQuestions(id) {
    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`http://127.0.0.1:5000/preguntas/${id}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        const questions = await res.json();
        displayQuestions(questions);
    } catch (err) {
        console.error("Error cargando preguntas:", err);
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

            (q.opciones || []).forEach(opcion => {
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
