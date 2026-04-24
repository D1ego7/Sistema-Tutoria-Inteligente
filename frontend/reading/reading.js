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
                console.log("Respuesta guardada:", data);

                enviadas++;

            } catch (err) {
                console.error("Error enviando respuesta:", err);
            }
        }

        if (enviadas === 0) {
            alert("Por favor responde al menos una pregunta.");
            return;
        }

        alert("Respuestas enviadas correctamente 🎉");
        window.location.href = "menu.html";
    });
});

/* function saveProgress(answerCount) {
    const key = "tutor_progress";
    const stored = JSON.parse(localStorage.getItem(key) || "null");
    const progress = stored || { correct: 0, total: 0, level: "literal" };
    progress.total += answerCount;
    progress.level = computeLevel(progress);
    localStorage.setItem(key, JSON.stringify(progress));
}

function computeLevel(progress) {
    const pct = progress.total === 0 ? 0 : Math.round((progress.correct / progress.total) * 100);
    if (progress.total < 3) return "literal";
    if (pct >= 80 && progress.level === "literal") return "inferencial";
    if (pct >= 80 && progress.level === "inferencial") return "critico";
    if (pct < 50 && progress.level === "critico") return "inferencial";
    if (pct < 50 && progress.level === "inferencial") return "literal";
    return progress.level;
} */

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