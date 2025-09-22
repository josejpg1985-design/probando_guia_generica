import pytest
import os
import sys
import sqlite3

# Añadir el directorio raíz del proyecto al path para permitir la importación de 'database'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ahora podemos importar los módulos del proyecto
import database
from werkzeug.security import check_password_hash

# --- Configuración de la Prueba ---
TEST_DB_NAME = 'test_flashcards.db'

@pytest.fixture(scope='function')
def test_db():
    """
    Fixture de Pytest para configurar una base de datos limpia para cada función de prueba
    y limpiarla después.
    """
    # Guardar el nombre original de la BD y establecer el de prueba
    original_db_name = database.DB_NAME
    database.DB_NAME = TEST_DB_NAME

    # Asegurarse de que no haya un archivo de BD de prueba antiguo
    if os.path.exists(TEST_DB_NAME):
        os.remove(TEST_DB_NAME)

    # Configurar la base de datos y las tablas de prueba
    database.setup_database()

    # 'yield' pasa el control a la función de prueba
    yield

    # --- Limpieza (Teardown) ---
    # Restaurar el nombre original de la BD
    database.DB_NAME = original_db_name
    # Eliminar el archivo de la base de datos de prueba
    if os.path.exists(TEST_DB_NAME):
        os.remove(TEST_DB_NAME)

# --- Casos de Prueba ---

def test_add_user_success(test_db):
    """
    Prueba la creación exitosa de un usuario.
    """
    email = "test@example.com"
    password = "password123"

    result = database.add_user(email, password)

    # 1. Verificar que la función reportó éxito
    assert result['status'] == 'success'
    assert 'user_id' in result
    assert result['user_id'] is not None

    # 2. Verificar que el usuario realmente existe en la BD
    user = database.get_user_by_id(result['user_id'])
    assert user is not None
    assert user['email'] == email
    assert check_password_hash(user['password_hash'], password)

def test_add_user_duplicate_email(test_db):
    """
    Prueba que la creación de un usuario con un email duplicado falla.
    """
    email = "duplicate@example.com"
    password = "password123"

    # Añadir el usuario por primera vez (debería funcionar)
    first_result = database.add_user(email, password)
    assert first_result['status'] == 'success'

    # Intentar añadir el mismo usuario de nuevo
    second_result = database.add_user(email, password)

    # Verificar que el segundo intento falló correctamente
    assert second_result['status'] == 'error'
    assert "ya existe" in second_result['message']

def test_get_user_by_email(test_db):
    """
    Prueba que se puede obtener un usuario por su email.
    """
    email = "findme@example.com"
    password = "password123"
    database.add_user(email, password)

    # Buscar el usuario
    user = database.get_user_by_email(email)

    assert user is not None
    assert user['email'] == email

def test_get_user_nonexistent(test_db):
    """
    Prueba que al buscar un usuario inexistente se devuelve None.
    """
    user = database.get_user_by_email("nouser@example.com")
    assert user is None
