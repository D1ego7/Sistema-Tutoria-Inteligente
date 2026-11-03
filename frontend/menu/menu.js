let consultaLecturas = 0;
document.addEventListener("DOMContentLoaded", function () {
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
        logoutBtn.addEventListener("click", function () {
            localStorage.removeItem("token");
            localStorage.removeItem("user");
            window.location.href = "/";
        });
    }
});

async function loadProgress() {
    const token = localStorage.getItem("token");
    const userId = getUserId();

    try {
        const res = await fetch('/progreso', {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (res.status === 403) {
            window.location.href = "/diagnostico.html";
            return;
        }
        if (res.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/";
            return;
        }

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'No se pudo cargar el progreso');
        mostrarProgreso(data);

    } catch (err) {
        console.error("Error cargando progreso:", err);
        document.getElementById('recommendation').textContent = 'No se pudo actualizar el progreso. Actualiza la página para volver a consultarlo.';
    }
}

function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
}

async function loadTexts(nivelSeleccionado = "actual") {
    const turno = ++consultaLecturas;
    const token = localStorage.getItem("token");

    try {
        let url = '/textos';

        if (nivelSeleccionado !== "actual") {
            url += `?nivel=${encodeURIComponent(nivelSeleccionado)}`;
        }

        const res = await fetch(url, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (turno !== consultaLecturas) return;

        if (res.status === 403) {
            window.location.href = "/diagnostico.html";
            return;
        }
        if (res.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/";
            return;
        }

        const data = await res.json();
        if (turno !== consultaLecturas) return;
        if (!res.ok) throw new Error(data.error || 'No se pudo cargar las lecturas');

        llenarComboNiveles(
            data.niveles_permitidos || [],
            data.nivel_actual || "literal",
            data.nivel_mostrado || data.nivel_actual || "literal",
            nivelSeleccionado
        );

        displayTexts(data.textos || []);

    } catch (err) {
        console.error("Error cargando textos:", err);
        if (turno !== consultaLecturas) return;
        const aviso = document.createElement('p'); aviso.className = 'empty-state';
        aviso.setAttribute('role', 'status');
        aviso.textContent = 'No se pudo cargar las lecturas. Comprueba la conexión y vuelve a seleccionar el nivel.';
        document.getElementById('texts-container').replaceChildren(aviso);
    }
}

function llenarComboNiveles(nivelesPermitidos, nivelActual, nivelMostrado, nivelSeleccionado) {
    const select = document.getElementById("level-filter");

    if (!select) return;

    const valorActualPrevio = select.value || "actual";

    select.innerHTML = "";

    const optionActual = document.createElement("option");
    optionActual.value = "actual";
    optionActual.textContent = `Nivel actual (${formatNivel(nivelActual)})`;
    select.appendChild(optionActual);

    nivelesPermitidos.forEach(nivel => {
        const option = document.createElement("option");
        option.value = nivel;
        option.textContent = formatNivel(nivel);
        select.appendChild(option);
    });

    if (nivelSeleccionado === "actual") {
        select.value = "actual";
    } else {
        select.value = nivelMostrado;
    }

    select.onchange = function () {
        loadTexts(this.value);
    };
}

function displayTexts(texts) {
    const container = document.getElementById("texts-container");
    container.innerHTML = "";

    texts.forEach(text => {
        const badgeLabel = getLevelLabel(text.nivel);
        const emoji = getEmojiForText(text.titulo);
        const readingTime = calculateReadingTime(text.contenido);
        const isCompleted = text.completado === true;

        const card = document.createElement("div");
        card.className = `text-card ${isCompleted ? 'text-card-completed' : ''}`;

        const buttonText = isCompleted
            ? '✅ Completado'
            : 'Leer y responder →';
        const buttonClass = isCompleted
            ? 'btn-read btn-completed'
            : 'btn-read';
        const buttonOnclick = isCompleted
            ? `selectText(${text.id_texto})`
            : `selectText(${text.id_texto})`;

        card.innerHTML = `
            <div class="text-card-top">
                <div class="text-emoji">${emoji}</div>
                <span class="badge badge-${text.nivel}">${badgeLabel}</span>
                ${isCompleted ? '<span class="completion-badge">✓</span>' : ''}
            </div>
            <h3>${text.titulo}</h3>
            <div class="text-meta">
                <span class="meta-item">
                    <span class="meta-icon">⏱️</span>
                    <span>${readingTime} min</span>
                </span>
            </div>
            <button class="${buttonClass}" onclick="${buttonOnclick}">${buttonText}</button>
        `;
        container.appendChild(card);
    });
}

function getLevelLabel(level) {
    if (level === "literal") return "Literal";
    if (level === "inferencial") return "Inferencial";
    if (level === "crítico" || level === "critico") return "Crítico";
    return "Nivel";
}

function selectText(id) {
    window.location.href = `reading.html?id=${id}`;
}

function getUserId() {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    return user.id;
}

// Funcion para calcular tiempo de lectura estimado (palabras / 200)
function calculateReadingTime(content) {
    if (!content) return 3;
    const wordCount = content.trim().split(/\s+/).length;
    const minutes = Math.ceil(wordCount / 200);
    return Math.max(1, Math.min(minutes, 15)); // Entre 1 y 15 minutos
}
