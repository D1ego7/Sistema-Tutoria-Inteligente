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

    // Delegación para submit-answers (selector dinámico)
    document.addEventListener("click", async function(e) {
        if (e.target.id === "submit-answers" || e.target.id === "submit-answers-retry") {
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
    document.getElementById("btn-continue-dashboard").addEventListener("click", function () {
        window.location.href = "menu.html";
    });

    document.getElementById("btn-retry-reading").addEventListener("click", function () {
        // Limpiar inputs y permitir reintentar
        document.getElementById("summary-modal").style.display = "none";
        const inputs = document.querySelectorAll(".question-card input");
        inputs.forEach(input => {
            input.value = "";
            input.style.borderColor = "#d1d5db";
        });
    });
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
            // Prellenar inputs con respuestas previas
            for (const idPregunta in respuestas) {
                const input = document.getElementById(`q-${idPregunta}`);
                if (input) {
                    input.value = respuestas[idPregunta].respuesta;

                    // Colorear según si es correcta o no
                    if (respuestas[idPregunta].es_correcta) {
                        input.style.backgroundColor = "#dcfce7";
                        input.style.borderColor = "#22c55e";
                        input.style.color = "#15803d";
                        input.style.fontWeight = "600";
                    }
                }
            }

            // Si todas son correctas, deshabilitar inputs y ocultar botón
            if (todasCorrectas && Object.keys(respuestas).length > 0) {
                const inputs = document.querySelectorAll(".question-card input");
                inputs.forEach(input => {
                    input.disabled = true;
                    input.style.cursor = "not-allowed";
                    if (input.style.backgroundColor !== "#dcfce7") {
                        input.style.backgroundColor = "#dcfce7";
                        input.style.borderColor = "#22c55e";
                        input.style.color = "#15803d";
                        input.style.fontWeight = "600";
                    }
                });
                document.getElementById("submit-answers").style.display = "none";
            } else if (Object.keys(respuestas).length > 0) {
                // Si hay incorrectas, mostrar botón "Volver a intentar" en lugar de "Enviar"
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
    container.style.display = "flex";
    container.style.gap = "0.75rem";
    container.style.marginTop = "1.5rem";
    container.style.flexDirection = "column";

    const retryBtn = document.createElement("button");
    retryBtn.id = "retry-button";
    retryBtn.className = "retry-button-styled";
    retryBtn.innerHTML = '<span style="font-size: 1.1em; margin-right: 0.5rem;">🔄</span>Volver a intentar';
    
    const submitBtnClone = submitBtn.cloneNode(true);
    submitBtnClone.id = "submit-answers-retry";
    submitBtnClone.className = "submit-answers-styled";

    retryBtn.addEventListener("click", function () {
        // Recargar respuestas del servidor para no tener datos antiguos
        const urlParams = new URLSearchParams(window.location.search);
        const textId = urlParams.get('id');
        loadPreviousAnswersForRetry(textId);

        // Reemplazar el contenedor por el botón de enviar (el clon) para permitir enviar de nuevo
        if (container.parentElement) {
            container.parentElement.replaceChild(submitBtnClone, container);
        } else {
            // fallback: intentar mostrar el botón original si sigue en DOM
            if (submitBtn && submitBtn.parentElement) {
                submitBtn.style.display = "block";
            }
            container.style.display = "none";
        }
    });

    container.appendChild(retryBtn);
    container.appendChild(submitBtnClone);
    submitBtn.parentElement.replaceChild(container, submitBtn);
}

async function loadPreviousAnswersForRetry(textId) {
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

        // Limpiar inputs y prellenar con las respuestas más recientes
        const inputs = document.querySelectorAll(".question-card input");
        inputs.forEach(input => {
            const id_pregunta = input.id.replace("q-", "");
            
            if (respuestas[id_pregunta]) {
                const respuesta = respuestas[id_pregunta];
                
                // Si es correcta, mantenerla y no permitir cambios
                if (respuesta.es_correcta) {
                    input.value = respuesta.respuesta;
                    input.style.backgroundColor = "#dcfce7";
                    input.style.borderColor = "#22c55e";
                    input.style.color = "#15803d";
                    input.disabled = true;
                    input.style.cursor = "not-allowed";
                    input.style.fontWeight = "600";
                } else {
                    // Si es incorrecta, limpiar para reintentar
                    input.value = "";
                    input.style.backgroundColor = "#fff";
                    input.style.borderColor = "#d1d5db";
                    input.style.color = "#111827";
                    input.disabled = false;
                    input.style.fontWeight = "400";
                }
            } else {
                // Si no hay respuesta previa, limpiar
                input.value = "";
                input.style.backgroundColor = "#fff";
                input.style.borderColor = "#d1d5db";
                input.style.color = "#111827";
                input.disabled = false;
            }
        });
    } catch (err) {
        console.error("Error recargando respuestas:", err);
    }
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
