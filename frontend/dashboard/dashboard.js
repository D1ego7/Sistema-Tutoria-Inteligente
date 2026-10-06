document.addEventListener("DOMContentLoaded", async function () {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "/";
        return;
    }

    try {
        const response = await fetch("/api/estudiante/dashboard", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await response.json();

        if (response.status === 403 && data.requiere_diagnostico) {
            window.location.href = "/diagnostico.html";
            return;
        }
        if (response.status === 401 || response.status === 403) {
            localStorage.removeItem("token");
            window.location.href = "/";
            return;
        }
        if (!response.ok) throw new Error(data.error || "No se pudo cargar el dashboard");

        mostrarDashboard(data);
    } catch (error) {
        console.error("Error cargando dashboard:", error);
        document.querySelector(".student-dashboard").classList.add("dashboard-error");
    }
});

function mostrarDashboard(data) {
    const nombre = data.nombre || "Estudiante";
    const primerNombre = nombre.trim().split(/\s+/)[0];
    document.getElementById("first-name").textContent = primerNombre;

    document.getElementById("summary-level").textContent = formatNivel(data.nivel_actual);
    document.getElementById("summary-accuracy").textContent = `${data.promedio_aciertos || 0}%`;
    document.getElementById("summary-completed").textContent = data.lecturas_completadas || 0;
    document.getElementById("summary-streak").textContent = `${data.racha || 0} días`;

    const porcentaje = mostrarProgreso({
        nivel_actual: data.nivel_actual,
        evaluacion: data.progreso,
        recomendacion_siguiente: data.recomendacion
    });

    document.getElementById("tutor-recommendation").textContent = data.recomendacion?.razon || "Sigue practicando para mejorar tu comprensión.";
    mostrarSiguienteLectura(data.siguiente_lectura);

    mostrarActividad(data.actividad_reciente || []);
    document.title = `Tutor Inteligente - ${primerNombre}`;
    return porcentaje;
}

function mostrarSiguienteLectura(lectura) {
    const container = document.getElementById("next-reading");
    if (!lectura) {
        container.innerHTML = '<p class="empty-state">No hay lecturas disponibles para tu nivel actual.</p>';
        return;
    }

    container.innerHTML = `
        <div class="next-reading-content">
            <div class="reading-cover">▣</div>
            <div><h4>${escaparHtml(lectura.titulo)}</h4><p>Nivel: <strong>${formatNivel(lectura.nivel)}</strong></p></div>
        </div>
        <a class="primary-action compact" href="/reading.html?id=${lectura.id_texto}">Leer ahora <span>→</span></a>
    `;
}

function mostrarActividad(actividades) {
    const container = document.getElementById("recent-activity");
    if (!actividades.length) return;

    container.innerHTML = actividades.map(actividad => `
        <div class="activity-row">
            <div class="activity-book">▣</div>
            <div class="activity-info"><strong>${escaparHtml(actividad.titulo)}</strong><small>${formatearFecha(actividad.fecha)}</small></div>
            <strong class="activity-score">${actividad.porcentaje}%</strong>
        </div>
    `).join("");
}

function formatearFecha(fecha) {
    if (!fecha) return "Sin fecha";
    const date = new Date(`${String(fecha).slice(0, 10)}T00:00:00`);
    return date.toLocaleDateString("es-PE", { day: "numeric", month: "short", year: "numeric" });
}

function escaparHtml(texto) {
    const element = document.createElement("div");
    element.textContent = texto || "";
    return element.innerHTML;
}
