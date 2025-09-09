
document.addEventListener('DOMContentLoaded', () => {
    const themeToggleButton = document.createElement('button');
    themeToggleButton.id = 'theme-toggle-btn';
    themeToggleButton.className = 'btn';
    themeToggleButton.textContent = 'Cambiar Tema';

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.parentNode.insertBefore(themeToggleButton, logoutBtn);
    } else {
        // Fallback for pages without logout button, e.g., index.html
        const container = document.querySelector('.container');
        if (container) {
            const buttonGroup = container.querySelector('.button-group');
            if (buttonGroup) {
                 buttonGroup.appendChild(themeToggleButton);
            } else {
                 container.appendChild(themeToggleButton);
            }
        }
    }
    
    const currentTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Set initial theme
    if (currentTheme === 'dark' || (!currentTheme && prefersDark)) {
        document.body.classList.add('dark-mode');
        updateButtonText(true);
    } else {
        updateButtonText(false);
    }

    themeToggleButton.addEventListener('click', () => {
        const isDarkMode = document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
        updateButtonText(isDarkMode);
    });

    function updateButtonText(isDarkMode) {
        themeToggleButton.textContent = isDarkMode ? 'Modo Claro' : 'Modo Oscuro';
    }
});
