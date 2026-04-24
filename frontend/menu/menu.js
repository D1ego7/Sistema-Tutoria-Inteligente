// dashboard.js
const STORAGE_KEY = "tutor_progress";

document.addEventListener("DOMContentLoaded", function() {
    const token = localStorage.getItem("token");
    const user = JSON.parse(localStorage.getItem("user") || "{}");

    if (!token) {
        window.location.href = "/";
        return;
    }

    const userGreeting = document.getElementById("user-greeting");
    if (userGreeting) {
        userGreeting.textContent = `Hola, ${user.nombre || 'Estudiante'}`;
    }

    loadProgress();
    loadTexts();

    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", function() {
            localStorage.removeItem("token");
            localStorage.removeItem("user");
            window.location.href = "/";
        });
    }
});

function loadProgress() {
    const progress = JSON.parse(localStorage.getItem(STORAGE_KEY) || JSON.stringify({ correct: 0, total: 0, level: "literal" }));
    displayProgress(progress);
}

function displayProgress(progress) {
    const pct = progress.total === 0 ? 0 : Math.round((progress.correct / progress.total) * 100);
    document.getElementById("level-badge").textContent = capitalize(progress.level);
    document.getElementById("score-text").textContent = `${progress.correct} / ${progress.total} · ${pct}%`;
    document.getElementById("progress-bar").style.width = `${pct}%`;
    document.getElementById("recommendation").textContent = getRecommendation(progress, pct);
}

function getRecommendation(progress, pct) {
    if (progress.total < 2) {
        return "Responde una lectura para ver tu recomendación.";
    }
    if (pct >= 80 && progress.level === "literal") {
        return "¡Estás listo para subir al nivel inferencial! 🚀";
    }
    if (pct >= 80 && progress.level === "inferencial") {
        return "¡Bienvenido al nivel crítico! Sigue así. 🌟";
    }
    if (pct < 50 && progress.level === "critico") {
        return "Puedes repasar un nivel anterior para fortalecer tu comprensión.";
    }
    if (pct < 50 && progress.level === "inferencial") {
        return "Practica un nivel más fácil para ganar confianza.";
    }
    return "Sigue respondiendo para mejorar tu progreso.";
}

function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
}

async function loadTexts() {
    const token = localStorage.getItem("token");
    try {
        const res = await fetch("http://127.0.0.1:5000/textos", {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (res.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/";
            return;
        }

        const texts = await res.json();
        displayTexts(texts);
    } catch (err) {
        console.error("Error cargando textos:", err);
    }
}

function displayTexts(texts) {
    const container = document.getElementById("texts-container");
    container.innerHTML = "";

    texts.forEach(text => {
        const badgeLabel = getLevelLabel(text.nivel);
        const card = document.createElement("div");
        card.className = "text-card";
        card.innerHTML = `
            <div class="text-card-top">
                <div class="text-emoji">📖</div>
                <span class="badge badge-${text.nivel}">${badgeLabel}</span>
            </div>
            <h3>${text.titulo}</h3>
            <p class="text-muted">Nivel: ${capitalize(text.nivel)}</p>
            <button onclick="selectText(${text.id_texto})">Leer y responder</button>
        `;
        container.appendChild(card);
    });
}

function getLevelLabel(level) {
    if (level === "literal") return "Literal";
    if (level === "inferencial") return "Inferencial";
    if (level === "critico") return "Crítico";
    return "Nivel";
}

function selectText(id) {
    window.location.href = `reading.html?id=${id}`;
}