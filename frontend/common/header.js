document.addEventListener("DOMContentLoaded", async function() {
    const headerContainer = document.getElementById("app-header");
    if (!headerContainer) return;

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
    } catch (err) {
        console.error(err);
    }
});