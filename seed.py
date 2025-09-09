

import sqlite3
import json
import os
from database import get_db_connection, add_user

# --- Configuration ---
JSON_FILES_WITH_CATEGORIES = {
    'Vocabulario': 'json/1_flashcards_vocabulario.txt',
    'Phrasal Verb': 'json/2_flashcards_phrasal_verbs.txt'
}
DEFAULT_USER_EMAIL = 'josejpg1985@gmail.com'
DEFAULT_USER_PASSWORD = 'password'

def create_default_user_if_not_exists():
    """Creates a default user for the flashcards and returns the user ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (DEFAULT_USER_EMAIL,))
    user = cursor.fetchone()
    conn.close()

    if user:
        print(f"Usuario por defecto '{DEFAULT_USER_EMAIL}' ya existe con ID: {user['id']}")
        return user['id']
    else:
        print(f"Creando usuario por defecto '{DEFAULT_USER_EMAIL}'...")
        result = add_user(DEFAULT_USER_EMAIL, DEFAULT_USER_PASSWORD)
        if result['status'] == 'success':
            print(f"Usuario creado con ID: {result['user_id']}")
            return result['user_id']
        else:
            raise Exception(f"No se pudo crear el usuario por defecto: {result['message']}")


def import_flashcards(user_id):
    """Imports flashcards from JSON files for a given user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Limpiar tarjetas antiguas del usuario por defecto para evitar duplicados en re-ejecuciones
    print(f"Limpiando tarjetas antiguas del usuario con ID: {user_id}...")
    cursor.execute("DELETE FROM flashcards WHERE user_id = ?", (user_id,))
    print(f"{cursor.rowcount} tarjetas antiguas eliminadas.")

    total_imported = 0
    for category, file_path in JSON_FILES_WITH_CATEGORIES.items():
        if not os.path.exists(file_path):
            print(f"Advertencia: El archivo {file_path} no fue encontrado. Saltando.")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        imported_in_file = 0
        for card in data:
            try:
                cursor.execute(
                    """
                    INSERT INTO flashcards (user_id, front_content, back_content, category, example_en, example_es)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        card['front'],
                        card['back'],
                        category, # <-- The new category field
                        card['exampleSentences']['en'],
                        card['exampleSentences']['es']
                    )
                )
                imported_in_file += 1
            except sqlite3.Error as e:
                print(f"Error insertando la tarjeta '{card.get('front', 'N/A')}': {e}")

        print(f"Importadas {imported_in_file} tarjetas de la categoría '{category}' desde {file_path}")
        total_imported += imported_in_file

    conn.commit()
    conn.close()
    print(f"\nTotal de tarjetas importadas: {total_imported}")

if __name__ == '__main__':
    print("--- Iniciando el proceso de carga de datos (seeding) ---")
    default_user_id = create_default_user_if_not_exists()
    import_flashcards(default_user_id)
    print("--- Proceso de carga de datos finalizado ---")

