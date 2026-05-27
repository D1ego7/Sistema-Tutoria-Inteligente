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
        const inputs = document.querySelectorAll(".question-card input");

        // Validar que todas las preguntas sean respondidas
        let allAnswered = true;
        for (let input of inputs) {
            const respuesta = input.value.trim();
            if (!respuesta) {
                allAnswered = false;
                input.style.borderColor = "#ef4444";
                break;
            }
            input.style.borderColor = "#d1d5db";
        }

        if (!allAnswered) {
            showToast("Debes responder todas las preguntas", false);
            return;
        }

        let enviadas = 0;
        let correctas = 0;

        for (let input of inputs) {
            const respuesta = input.value.trim();
            const id_pregunta = input.id.replace("q-", "");

            try {
                const res = await fetch("http://127.0.0.1:5000/respuesta-con-feedback", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        id_pregunta: parseInt(id_pregunta),
                        respuesta: respuesta,
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

        // Mostrar modal con resumen de sesión
        showSummaryModal(enviadas, correctas, textId);
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

function showSummaryModal(answered, correct, textId) {
    const percentage = answered > 0 ? Math.round((correct / answered) * 100) : 0;

    document.getElementById("summary-answered").textContent = answered;
    document.getElementById("summary-correct").textContent = correct;
    document.getElementById("summary-percentage").textContent = percentage + "%";

    // Si hay recomendación de nivel, mostrarla
    const recommendationBox = document.getElementById("recommendation-box");
    if (answered >= 5) {
        if (percentage >= 80) {
            recommendationBox.style.display = "block";
            document.getElementById("recommendation-text").textContent = "¡Excelente desempeño! Estás listo para el siguiente nivel.";
        } else if (percentage < 50) {
            recommendationBox.style.display = "block";
            document.getElementById("recommendation-text").textContent = "Necesitas practicar más en este nivel antes de avanzar.";
        } else {
            recommendationBox.style.display = "none";
        }
    } else {
        recommendationBox.style.display = "none";
    }

    document.getElementById("summary-modal").style.display = "flex";

    // Configurar botones
    document.getElementById("btn-continue-dashboard").onclick = function () {
        window.location.href = "menu.html";
    };

    document.getElementById("btn-retry-reading").onclick = function () {
        // Limpiar inputs incorrectos y permitir reintentar
        document.getElementById("summary-modal").style.display = "none";
        const inputs = document.querySelectorAll(".question-card input");
        inputs.forEach(input => {
            // Si no está correcto, limpiar
            if (input.style.backgroundColor !== "#d1fae5") {
                input.value = "";
                input.style.borderColor = "#d1d5db";
                input.disabled = false;
            }
        });
        // Mostrar botones
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
            // Prellenar inputs
            for (const idPregunta in respuestas) {
                const input = document.getElementById(`q-${idPregunta}`);
                if (input) {
                    if (respuestas[idPregunta].es_correcta) {
                        // Guardar respuestas CORRECTAS en verde
                        input.value = respuestas[idPregunta].respuesta;
                        input.style.backgroundColor = "#d1fae5";
                        input.style.borderColor = "#10b981";
                        input.style.color = "#065f46";
                        input.disabled = true;
                    } else {
                        // Dejar vacío si es incorrecta
                        input.value = "";
                        input.style.backgroundColor = "#ffffff";
                        input.style.borderColor = "#d1d5db";
                    }
                }
            }

            // Si todas son correctas, deshabilitar todo y ocultar botones
            if (todasCorrectas && Object.keys(respuestas).length > 0) {
                const inputs = document.querySelectorAll(".question-card input");
                inputs.forEach(input => {
                    input.disabled = true;
                    input.style.backgroundColor = "#d1fae5";
                    input.style.borderColor = "#10b981";
                    input.style.color = "#065f46";
                    input.style.cursor = "not-allowed";
                });
                // Ocultar ambos botones
                document.getElementById("submit-answers").style.display = "none";
            } else if (Object.keys(respuestas).length > 0) {
                // Si hay respuestas previas pero no todas correctas, mostrar "Volver a intentar"
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
    retryBtn.textContent = "🔄 Volver a intentar";
    retryBtn.style.flex = "1";
    retryBtn.style.padding = "0.95rem 1.3rem";
    retryBtn.style.borderRadius = "1rem";
    retryBtn.style.cursor = "pointer";
    retryBtn.style.fontWeight = "700";
    retryBtn.style.border = "none";
    retryBtn.style.background = "linear-gradient(135deg, #f59e0b 0%, #f97316 100%)";
    retryBtn.style.color = "white";
    retryBtn.style.fontSize = "1rem";
    retryBtn.style.transition = "all 0.2s ease";

    retryBtn.addEventListener("mouseover", function () {
        retryBtn.style.boxShadow = "0 10px 25px rgba(245, 158, 11, 0.2)";
    });

    retryBtn.addEventListener("mouseout", function () {
        retryBtn.style.boxShadow = "none";
    });

    retryBtn.addEventListener("click", function () {
        // Limpiar todos los inputs incorrectos (que no estén en verde)
        const inputs = document.querySelectorAll(".question-card input");
        inputs.forEach(input => {
            // Si no está correcto, limpiar y permitir edición
            if (input.style.backgroundColor !== "#d1fae5") {
                input.value = "";
                input.style.borderColor = "#d1d5db";
                input.disabled = false;
            }
        });
        // Mostrar botón de enviar de nuevo y ocultar retry
        submitBtn.style.display = "block";
        container.style.display = "none";
    });

    const submitBtnClone = submitBtn.cloneNode(true);
    submitBtnClone.id = "submit-answers-copy";
    submitBtnClone.style.flex = "1";
    submitBtnClone.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
    submitBtnClone.addEventListener("click", async function () {
        const token = localStorage.getItem("token");
        const inputs = document.querySelectorAll(".question-card input");

        // Validar que todas las preguntas sean respondidas
        let allAnswered = true;
        for (let input of inputs) {
            const respuesta = input.value.trim();
            if (!respuesta) {
                allAnswered = false;
                input.style.borderColor = "#ef4444";
                break;
            }
            input.style.borderColor = "#d1d5db";
        }

        if (!allAnswered) {
            showToast("Debes responder todas las preguntas", false);
            return;
        }

        let enviadas = 0;
        let correctas = 0;

        for (let input of inputs) {
            const respuesta = input.value.trim();
            const id_pregunta = input.id.replace("q-", "");

            try {
                const res = await fetch("http://127.0.0.1:5000/respuesta-con-feedback", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        id_pregunta: parseInt(id_pregunta),
                        respuesta: respuesta,
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

        // Mostrar modal con resumen de sesión
        const textId = new URLSearchParams(window.location.search).get('id');
        showSummaryModal(enviadas, correctas, textId);
    });

    container.appendChild(retryBtn);
    container.appendChild(submitBtnClone);
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

    questions.forEach((q, idx) => {
        const div = document.createElement("div");
        div.className = "question-card";
        div.innerHTML = `
            <p class="question-label"><strong>${idx + 1}.</strong> ${q.enunciado}</p>
            <input type="text" id="q-${q.id_pregunta}" placeholder="Tu respuesta">
        `;
        container.appendChild(div);
    });
}
