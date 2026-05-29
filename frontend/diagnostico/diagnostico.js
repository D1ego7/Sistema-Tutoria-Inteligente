document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("token");

    if (!token) {
        window.location.href = "/";
        return;
    }

    cargarDiagnostico();

    document.getElementById("submit-diagnostic").addEventListener("click", enviarDiagnostico);
});

const preguntasDiagnostico = [
    {
        id: 1,
        pregunta: "¿Quién es el personaje principal del texto?",
        correcta: "el ratón"
    },
    {
        id: 2,
        pregunta: "¿Dónde dormía el león?",
        correcta: "bajo un árbol"
    },
    {
        id: 3,
        pregunta: "¿Por qué el león dejó libre al ratón?",
        correcta: "porque el ratón le prometió ayudarlo"
    },
    {
        id: 4,
        pregunta: "¿Qué enseñanza deja la historia?",
        correcta: "todos pueden ayudar sin importar su tamaño"
    }
];

function cargarDiagnostico() {
    const texto = `
Un pequeño ratón despertó accidentalmente a un enorme león que dormía bajo un árbol.
El león, furioso, atrapó al ratón entre sus garras. El ratón le rogó que lo dejara libre y prometió ayudarlo algún día.
El león se rió, pero decidió soltarlo. Días después, el león cayó atrapado en una red.
El ratón escuchó sus rugidos, corrió hacia él y mordió la red hasta liberarlo.
Desde entonces, el león comprendió que hasta los más pequeños pueden ser de gran ayuda.
`;

    document.getElementById("diagnostic-text").textContent = texto;

    const container = document.getElementById("diagnostic-questions");
    container.innerHTML = "";

    preguntasDiagnostico.forEach((p, index) => {
        const div = document.createElement("div");
        div.className = "question-card";
        div.innerHTML = `
            <p class="question-label"><strong>${index + 1}.</strong> ${p.pregunta}</p>
            <input type="text" id="diag-${p.id}" placeholder="Tu respuesta">
        `;
        container.appendChild(div);
    });
}

async function enviarDiagnostico() {
    const token = localStorage.getItem("token");

    let respuestasBooleanas = [];
    let preguntasIds = [];

    for (const p of preguntasDiagnostico) {
        const input = document.getElementById(`diag-${p.id}`);
        const respuesta = input.value.trim().toLowerCase();

        if (!respuesta) {
            alert("Debes responder todas las preguntas.");
            return;
        }

        const correcta = respuesta.includes(p.correcta.toLowerCase()) || p.correcta.toLowerCase().includes(respuesta);

        respuestasBooleanas.push(correcta);
        preguntasIds.push(p.id);
    }

    const res = await fetch("http://127.0.0.1:5000/diagnostico-inicial", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            respuestas: respuestasBooleanas,
            preguntas_ids: preguntasIds
        })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.error || "Error al guardar diagnóstico");
        return;
    }

    alert(`Diagnóstico completado. Tu nivel inicial es: ${data.nivel_inicial}`);
    window.location.href = "menu.html";
}