function verificarAutenticacion() {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
        console.log('No se encontró token, redirigiendo al login.');
        window.location.href = '/';
        return null;
    }
    return token;
}
