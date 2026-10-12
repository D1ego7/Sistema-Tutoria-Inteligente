document.getElementById("login-form").addEventListener("submit", async function(e) {
    e.preventDefault();
    await login();
});

function togglePassword() {
    const input = document.getElementById('password');
    const eyeIcon = document.querySelector('.eye-icon svg');
    if (input.type === 'password') {
        input.type = 'text';
        eyeIcon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
    } else {
        input.type = 'password';
        eyeIcon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
    }
}

async function login() {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    let error = document.getElementById("error");

    if (!error) {
        const errorP = document.createElement("p");
        errorP.id = "error";
        errorP.className = "error";
        document.querySelector(".login-card").appendChild(errorP);
        error = errorP;
    }
    error.textContent = "";

    if (email.length > 100 || new TextEncoder().encode(password).length > 72) {
        error.textContent = 'El correo admite hasta 100 caracteres y la contraseña hasta 72 bytes (las tildes pueden ocupar más de uno).';
        return;
    }

    try {
        const res = await fetch("http://127.0.0.1:5000/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (res.status === 200) {
            // Guardar token
            localStorage.setItem("token", data.access_token);
            localStorage.setItem("user", JSON.stringify(data.user));

            if ([2, 3].includes(data.user.rol)) {
                window.location.href = '/docente.html';
                return;
            }
            if (data.user.rol !== 1) {
                localStorage.removeItem("token");
                localStorage.removeItem("user");
                error.textContent = "La cuenta no tiene un rol habilitado.";
                return;
            }

            const estadoRes = await fetch("/diagnostico-estado", {
                headers: { "Authorization": `Bearer ${data.access_token}` }
            });
            const estado = await estadoRes.json();

            if (estadoRes.ok && estado.tiene_diagnostico === false) {
                window.location.href = "diagnostico.html";
            } else if (estadoRes.ok && estado.tiene_diagnostico === true) {
                window.location.href = "dashboard.html";
            } else {
                error.textContent = estado.error || "No se pudo validar el diagnóstico";
            }
        } else {
            error.textContent = data.error || "Error al iniciar sesión";
        }

    } catch (err) {
        error.textContent = "Error de conexión con el servidor";
    }
}
