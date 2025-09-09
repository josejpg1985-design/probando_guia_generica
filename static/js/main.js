document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('auth-form');
    const registerBtn = document.getElementById('register-btn');
    const loginBtn = document.getElementById('login-btn');
    const messageArea = document.getElementById('message-area');

    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');

    // --- Lógica de Registro ---
    registerBtn.addEventListener('click', async (event) => {
        event.preventDefault();
        const email = emailInput.value;
        const password = passwordInput.value;

        if (!email || !password) {
            showMessage('Por favor, completa todos los campos.', 'error');
            return;
        }

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            const result = await response.json();
            if (response.ok) {
                showMessage(`Usuario registrado con éxito. ID: ${result.user_id}`, 'success');
                form.reset();
            } else {
                showMessage(result.message, 'error');
            }
        } catch (error) {
            showMessage('Error de conexión con el servidor.', 'error');
        }
    });

    // --- Lógica de Login ---
    loginBtn.addEventListener('click', async (event) => {
        event.preventDefault();
        const email = emailInput.value;
        const password = passwordInput.value;

        if (!email || !password) {
            showMessage('Por favor, completa todos los campos.', 'error');
            return;
        }

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            const result = await response.json();
            if (response.ok) {
                // Guardar el token en el navegador
                localStorage.setItem('jwt_token', result.token);
                showMessage('Inicio de sesión exitoso. Redirigiendo...', 'success');
                form.reset();
                // Redirigir al dashboard después de un breve retraso.
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000); // 1 segundo 
            } else {
                showMessage(result.message, 'error');
            }
        } catch (error) {
            showMessage('Error de conexión con el servidor.', 'error');
        }
    });

    // --- Función para mostrar mensajes ---
    function showMessage(message, type) {
        messageArea.textContent = message;
        messageArea.style.color = type === 'success' ? 'var(--success-color)' : 'var(--error-color)';
        messageArea.style.backgroundColor = type === 'success' ? '#d4edda' : '#f8d7da';
        messageArea.style.padding = '1rem';
        messageArea.style.display = 'block';
    }
});
