document.addEventListener('DOMContentLoaded', () => {
    const authForm = document.getElementById('auth-form');
    if (authForm) {
        const loginBtn = document.getElementById('login-btn');
        const registerBtn = document.getElementById('register-btn');
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        const messageArea = document.getElementById('message-area');

        loginBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            handleAuth('/api/login', {
                email: emailInput.value,
                password: passwordInput.value
            });
        });

        registerBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            handleAuth('/api/register', {
                email: emailInput.value,
                password: passwordInput.value
            });
        });

        async function handleAuth(url, data) {
            if (!data.email || !data.password) {
                showMessage('Por favor, introduce email y contraseña.', 'error');
                return;
            }

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok && result.status === 'success') {
                    if (result.token) {
                        localStorage.setItem('jwt_token', result.token);
                        window.location.href = '/dashboard';
                    } else {
                        // Registration successful
                        showMessage('Registro exitoso. Ahora puedes iniciar sesión.', 'success');
                        authForm.reset();
                    }
                } else {
                    showMessage(result.message || 'Ocurrió un error.', 'error');
                }
            } catch (error) {
                console.error('Error de autenticación:', error);
                showMessage('Error de conexión con el servidor.', 'error');
            }
        }

        function showMessage(message, type) {
            messageArea.textContent = message;
            messageArea.style.color = type === 'error' ? 'var(--error-color)' : 'var(--success-color)';
            messageArea.style.display = 'block';
        }
    }
});

function verificarAutenticacion() {
    const token = localStorage.getItem('jwt_token');
    // Si ya estamos en la página de login, no hacemos nada si no hay token.
    if (!token && (window.location.pathname === '/' || window.location.pathname === '/index.html')) {
        return null;
    }

    // Si hay un token y estamos en la página de login, redirigir al dashboard.
    if (token && (window.location.pathname === '/' || window.location.pathname === '/index.html')) {
        window.location.href = '/dashboard';
        return token;
    }

    // Si no hay token y no estamos en login, redirigir a login.
    if (!token) {
        console.log('No se encontró token, redirigiendo al login.');
        window.location.href = '/';
        return null;
    }

    return token;
}
