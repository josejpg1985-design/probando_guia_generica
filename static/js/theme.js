
document.addEventListener('DOMContentLoaded', () => {
    // No mostrar el botón en la página de autenticación/login
    if (document.querySelector('.auth-container')) {
        return;
    }

    const themeToggleButton = document.createElement('button');
    themeToggleButton.id = 'theme-toggle-btn';
    themeToggleButton.className = 'theme-toggle-btn'; // Usar una clase específica para el estilo
    
    const themeIcon = document.createElement('span');
    themeToggleButton.appendChild(themeIcon);

    document.body.appendChild(themeToggleButton);

    const currentTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    function updateIcon(isDarkMode) {
        themeIcon.textContent = isDarkMode ? '☀️' : '🌙';
        themeToggleButton.setAttribute('aria-label', isDarkMode ? 'Activar modo claro' : 'Activar modo oscuro');
    }

    // Set initial theme
    if (currentTheme === 'dark' || (!currentTheme && prefersDark)) {
        document.body.classList.add('dark-mode');
        updateIcon(true);
    } else {
        document.body.classList.remove('dark-mode');
        updateIcon(false);
    }

    themeToggleButton.addEventListener('click', () => {
        const isDarkMode = document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
        updateIcon(isDarkMode);
    });
});
