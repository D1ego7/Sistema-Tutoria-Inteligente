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

    // Variables para rastrear el progreso de la sesión
    let sessionProgress = {
        answered: 0,
        correct: 0,
        total: 0
    };

    // Cargar progreso histórico
    loadProgressHistoric();

    loadText(textId);
    loadQuestions(textId);

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

        let enviadas = 0;
        let correctas = 0;

        for (let input of inputs) {
            const respuesta = input.value.trim();
            const id_pregunta = input.id.replace("q-", "");

            if (!respuesta) continue;

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

                // Actualizar progreso de sesión
                if (data.progreso_actualizado) {
                    sessionProgress = {
                        answered: enviadas,
                        correct: correctas,
                        total: data.progreso_actualizado.total_respuestas || 0
                    };
                }

            } catch (err) {
                console.error("Error enviando respuesta:", err);
                showToast("Error al guardar respuesta", false);
            }
        }

        if (enviadas === 0) {
            showToast("Por favor responde al menos una pregunta", false);
            return;
        }

        // Mostrar modal con resumen de sesión
        showSummaryModal(enviadas, correctas);
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

function showSummaryModal(answered, correct) {
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

    document.getElementById("btn-continue-reading").addEventListener("click", function () {
        window.location.href = "menu.html";
    });
}

async function loadProgressHistoric() {
    const token = localStorage.getItem("token");
    try {
        const res = await fetch("http://127.0.0.1:5000/progreso-estudiante", {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!res.ok) {
            console.error("Error cargando progreso");
            return;
        }

        const progress = await res.json();

        // Mostrar card de progreso
        document.getElementById("progress-card").style.display = "block";
        document.getElementById("nivel-actual").textContent = progress.nivel_actual || "-";
        document.getElementById("porcentaje-acierto").textContent = progress.porcentaje_acierto_general.toFixed(1) + "%";
        document.getElementById("total-respuestas").textContent = progress.total_respuestas_historial;

    } catch (err) {
        console.error("Error cargando progreso histórico:", err);
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