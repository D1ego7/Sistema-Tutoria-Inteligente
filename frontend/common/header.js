document.addEventListener("DOMContentLoaded", async function() {
    const headerContainer = document.getElementById("app-header");
    if (!headerContainer) return;

    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "/";
        return;
    }

    try {
        const response = await fetch("/header.html");
        if (!response.ok) {
            throw new Error("No se pudo cargar el encabezado");
        }
        const headerHtml = await response.text();
        headerContainer.innerHTML = headerHtml;

        const user = JSON.parse(localStorage.getItem("user") || "{}");
        const greeting = document.getElementById("user-greeting");
        if (greeting) {
            greeting.textContent = `Hola, ${user.nombre || "Estudiante"}`;
        }

        const logoutBtn = document.getElementById("logout-btn");
        if (logoutBtn) {
            logoutBtn.addEventListener("click", function() {
                localStorage.removeItem("token");
                localStorage.removeItem("user");
                window.location.href = "/";
            });
        }

        const rutaActual = window.location.pathname;
        const navInicio = document.querySelector('[data-nav="inicio"]');
        const navLecturas = document.querySelector('[data-nav="lecturas"]');
        const estaEnInicio = rutaActual.endsWith("/dashboard.html") || rutaActual.endsWith("/inicio");
        const estaEnLecturas = rutaActual.endsWith("/menu.html") || rutaActual.endsWith("/reading.html");

        if (estaEnInicio && navInicio) {
            navInicio.classList.add("active");
            navInicio.setAttribute("aria-current", "page");
        }
        if (estaEnLecturas && navLecturas) {
            navLecturas.classList.add("active");
            navLecturas.setAttribute("aria-current", "page");
        }

        const estadoResponse = await fetch("/diagnostico-estado", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const estado = await estadoResponse.json();
        const esDiagnostico = rutaActual.endsWith("/diagnostico.html");
        const esPantallaEstudiante = ["/dashboard.html", "/inicio", "/menu.html", "/reading.html"].some(
            ruta => rutaActual.endsWith(ruta)
        );

        if (estadoResponse.status === 401 || estadoResponse.status === 403) {
            localStorage.removeItem("token");
            localStorage.removeItem("user");
            window.location.href = "/";
            return;
        }
        if (estadoResponse.ok && esDiagnostico && estado.tiene_diagnostico) {
            window.location.href = "/dashboard.html";
            return;
        }
        if (estadoResponse.ok && esPantallaEstudiante && !estado.tiene_diagnostico) {
            window.location.href = "/diagnostico.html";
        }
    } catch (err) {
        console.error(err);
    }
});