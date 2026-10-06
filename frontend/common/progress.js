function porcentajeAciertos(evaluacion) {
    if (typeof evaluacion?.porcentaje_acierto === "number") {
        return evaluacion.porcentaje_acierto;
    }
    const correctas = evaluacion?.respuestas_correctas || 0;
    const total = evaluacion?.total_respuestas || 0;
    return total === 0 ? 0 : Math.round((correctas / total) * 100);
}

function mostrarProgreso(data) {
    if (!data || !data.evaluacion) {
        console.error("Datos de progreso inválidos:", data);
        return 0;
    }

    const evaluacion = data.evaluacion;
    const porcentaje = porcentajeAciertos(evaluacion);
    const nivel = data.nivel_actual || "literal";

    const levelBadge = document.getElementById("level-badge");
    const scoreText = document.getElementById("score-text");
    const progressBar = document.getElementById("progress-bar");
    const progressPercent = document.getElementById("progress-percent");
    const recommendation = document.getElementById("recommendation");

    if (levelBadge) levelBadge.textContent = formatNivel(nivel);
    if (scoreText) {
        scoreText.textContent = `${evaluacion.respuestas_correctas || 0} / ${evaluacion.total_respuestas || 0} · ${porcentaje}%`;
    }
    if (progressBar) progressBar.style.width = `${porcentaje}%`;
    if (progressPercent) progressPercent.textContent = `${porcentaje}%`;
    if (recommendation) {
        recommendation.textContent = data.recomendacion_siguiente?.razon || "Sigue respondiendo para mejorar.";
    }

    return porcentaje;
}

function formatNivel(nivel) {
    if (nivel === "literal") return "Literal";
    if (nivel === "inferencial") return "Inferencial";
    if (nivel === "crítico" || nivel === "critico") return "Crítico";
    return nivel || "-";
}
