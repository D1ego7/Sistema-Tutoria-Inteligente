document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("token");

    if (!token) {
        window.location.href = "/";
        return;
    }

    cargarDiagnostico();

    document.getElementById("submit-diagnostic").addEventListener("click", enviarDiagnostico);
});

let preguntasDiagnostico = [];

async function cargarDiagnostico() {
    const token = localStorage.getItem("token");
    const res = await fetch("/diagnostico-preguntas", {
        headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();

    if (res.status === 409) {
        window.location.href = "/dashboard.html";
        return;
    }
    if (!res.ok) {
        alert(data.error || "No se pudo cargar el diagnóstico");
        return;
    }

    preguntasDiagnostico = data.preguntas || [];

    document.getElementById("diagnostic-text").textContent = data.texto || "";

    const container = document.getElementById("diagnostic-questions");
    container.innerHTML = "";

    preguntasDiagnostico.forEach((p, index) => {
        const div = document.createElement("div");
        div.className = "question-card";
        div.innerHTML = `
            <p class="question-label"><strong>${index + 1}.</strong> ${p.pregunta}</p>
            <input type="text" id="diag-${p.id}" placeholder="Tu respuesta" maxlength="100">
        `;
        container.appendChild(div);
    });
}

async function enviarDiagnostico() {
    const token = localStorage.getItem("token");

    const respuestas = [];

    for (const p of preguntasDiagnostico) {
        const input = document.getElementById(`diag-${p.id}`);
        const respuesta = input.value.trim();

        if (input.value.length > 100) {
            alert('Cada respuesta admite un máximo de 100 caracteres.');
            return;
        }

        if (!respuesta) {
            alert("Debes responder todas las preguntas.");
            return;
        }

        respuestas.push({ id: p.id, respuesta });
    }

    const res = await fetch("/diagnostico-inicial", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            respuestas
        })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.error || "Error al guardar diagnóstico");
        return;
    }

    alert(`Diagnóstico completado. Tu nivel inicial es: ${data.nivel_inicial}`);
    window.location.href = "dashboard.html";
}
