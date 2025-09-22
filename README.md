# Flashcards App para Aprender Inglés

Esta es una aplicación web construida con Flask y JavaScript para ayudar a los usuarios a aprender inglés mediante el uso de flashcards, un sistema de repetición espaciada (SM-2) y funcionalidades asistidas por IA a través de la API de Gemini.

## Funcionalidades Principales

- **Autenticación de Usuarios**: Sistema de registro e inicio de sesión seguro basado en tokens JWT.
- **Gestión de Flashcards**: Los usuarios obtienen un conjunto de tarjetas por defecto y pueden gestionarlas.
- **Repetición Espaciada**: El algoritmo SM-2 calcula la próxima fecha de revisión de cada tarjeta según el rendimiento del usuario.
- **Modo Estudio**: Interfaz para calificar las tarjetas como "Fácil", "Normal" o "Difícil" y actualizar su estado de revisión.
- **Modo Inmersión**: Diálogos interactivos para practicar inglés en diferentes escenarios.
- **Funcionalidades con IA (Gemini)**:
    - **Traducción**: Traduce texto de inglés a español.
    - **Análisis de Canciones**: Extrae vocabulario y verbos frasales de letras de canciones.
    - **Generación de Párrafos**: Crea párrafos sencillos usando una lista de palabras.
- **Archivo de Tarjetas**: Permite archivar y desarchivar tarjetas para enfocarse en el material de estudio relevante.

## Stack Tecnológico

- **Backend**: Python, Flask
- **Base de Datos**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **API de IA**: Google Gemini
- **Autenticación**: JSON Web Tokens (JWT)

## Instalación y Ejecución

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local.

### 1. Prerrequisitos

- Tener Python 3.8 o superior instalado.
- Tener Git instalado.

### 2. Clonar el Repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd flashcards_ingles
```

### 3. Crear y Activar un Entorno Virtual

Es una buena práctica usar un entorno virtual para aislar las dependencias del proyecto.

- **En Windows**:
  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  ```

- **En macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 4. Instalar Dependencias

Instala todas las librerías de Python necesarias con el siguiente comando:

```bash
pip install -r requirements.txt
```

### 5. Configurar Variables de Entorno

La aplicación requiere algunas claves y configuraciones que deben ser almacenadas en un archivo `.env`.

1.  Crea un archivo llamado `.env` en la raíz del proyecto.
2.  Añade las siguientes variables al archivo:

    ```env
    GEMINI_API_KEY="TU_API_KEY_DE_GEMINI"
    SECRET_KEY="UNA_CLAVE_SECRETA_ALEATORIA_Y_LARGA"
    DATABASE_NAME="flashcards.db"
    ```

    - `GEMINI_API_KEY`: Tu clave personal para la API de Google Gemini.
    - `SECRET_KEY`: Una cadena de texto larga y aleatoria que Flask usa para firmar sesiones y tokens.
    - `DATABASE_NAME`: El nombre del archivo de la base de datos (puedes dejar `flashcards.db`).

### 6. Ejecutar la Aplicación

Una vez que las dependencias y las variables de entorno estén configuradas, la aplicación se puede iniciar con:

```bash
python app.py
```

La aplicación estará disponible en `http://127.0.0.1:5000` en tu navegador.

La primera vez que se ejecute, se creará y configurará automáticamente la base de datos `flashcards.db`.
