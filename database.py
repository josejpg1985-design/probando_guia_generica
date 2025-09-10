import sqlite3
import datetime
import json
import os
from werkzeug.security import generate_password_hash

DB_NAME = 'flashcards.db'

def get_db_connection():
    """Crea y retorna una conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Crea las tablas de la base de datos y añade nuevas columnas si es necesario."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Crear tabla de usuarios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Crear tabla de flashcards con la nueva columna
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        front_content TEXT NOT NULL,
        back_content TEXT NOT NULL,
        category TEXT NOT NULL,
        example_en TEXT,
        example_es TEXT,
        interval INTEGER DEFAULT 0,
        repetitions INTEGER DEFAULT 0,
        ease_factor REAL DEFAULT 2.5,
        next_review_date TEXT DEFAULT (date('now')),
        is_archived INTEGER DEFAULT 0,
        flip_count INTEGER DEFAULT 0,  -- Nueva columna
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # --- Bloque para añadir la columna a tablas existentes (migración) ---
    try:
        # Revisar si la columna ya existe
        cursor.execute("PRAGMA table_info(flashcards)")
        columns = [column['name'] for column in cursor.fetchall()]
        if 'flip_count' not in columns:
            print("Añadiendo columna 'flip_count' a la tabla 'flashcards'...")
            cursor.execute("ALTER TABLE flashcards ADD COLUMN flip_count INTEGER DEFAULT 0")
            print("Columna 'flip_count' añadida exitosamente.")
    except Exception as e:
        print(f"Error al intentar modificar la tabla 'flashcards': {e}")
    # --- Fin del bloque de migración ---


    print("Tablas 'users' y 'flashcards' creadas o ya existentes.")
    conn.commit()
    conn.close()

def add_user(email, password):
    """Añade un nuevo usuario a la base de datos con contraseña hasheada."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"status": "success", "user_id": user_id}
    except sqlite3.IntegrityError:
        conn.close()
        return {"status": "error", "message": "El correo electrónico ya existe."}

def get_user_by_email(email):
    """Busca un usuario por su email y devuelve sus datos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Busca un usuario por su ID y devuelve sus datos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_categories_for_user(user_id):
    """Devuelve una lista de categorías únicas para un usuario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM flashcards WHERE user_id = ?", (user_id,))
    categories = [row['category'] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_flashcards_by_category(user_id, category):
    """Devuelve una lista de flashcards para un usuario y categoría específicos que están pendientes de revisión."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, front_content, back_content, example_en, example_es, flip_count FROM flashcards WHERE user_id = ? AND category = ? AND next_review_date <= date('now') AND is_archived = 0",
        (user_id, category)
    )
    flashcards = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return flashcards

def update_flashcard_sm2_data(card_id, rating):
    """
    Actualiza los datos de repetición espaciada de una flashcard usando el algoritmo SM-2.
    rating: 1 (Difícil), 2 (Normal), 3 (Fácil)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener datos actuales de la flashcard
    cursor.execute(
        "SELECT interval, repetitions, ease_factor FROM flashcards WHERE id = ?",
        (card_id,)
    )
    card_data = cursor.fetchone()

    if not card_data:
        conn.close()
        return False # Card not found

    interval = card_data['interval']
    repetitions = card_data['repetitions']
    ease_factor = card_data['ease_factor']

    # Aplicar lógica SM-2
    if rating == 3: # Fácil
        repetitions += 1
        new_ease_factor = ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02)) # Standard SM-2 ease factor adjustment
        if repetitions == 1:
            new_interval = 1
        elif repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval * new_ease_factor)
    elif rating == 2: # Normal
        repetitions += 1
        new_ease_factor = ease_factor # No change to ease factor for 'Normal'
        if repetitions == 1:
            new_interval = 1
        elif repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval * new_ease_factor)
    elif rating == 1: # Difícil
        repetitions = 0 # Reset repetitions
        new_ease_factor = ease_factor - 0.2 # Decrease ease factor
        new_interval = 1 # Next review in 1 day
    else: # Invalid rating
        conn.close()
        return False

    # Ensure ease factor doesn't go below 1.3
    new_ease_factor = max(1.3, new_ease_factor)

    # Calculate next review date
    next_review_date = (datetime.date.today() + datetime.timedelta(days=new_interval)).isoformat()

    # Actualizar la flashcard en la base de datos
    cursor.execute(
        """
        UPDATE flashcards
        SET interval = ?, repetitions = ?, ease_factor = ?, next_review_date = ?
        WHERE id = ?
        """,
        (new_interval, repetitions, new_ease_factor, next_review_date, card_id)
    )
    conn.commit()
    conn.close()
    return True

def archive_flashcard(card_id, user_id):
    """Marca una flashcard como archivada."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE flashcards SET is_archived = 1 WHERE id = ? AND user_id = ?",
        (card_id, user_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def increment_flip_count(card_id):
    """Incrementa en 1 el contador de giros de una flashcard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE flashcards SET flip_count = flip_count + 1 WHERE id = ?",
            (card_id,)
        )
        conn.commit()
        # Devolvemos True si se actualizó una fila
        success = cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error al incrementar el flip_count para la tarjeta {card_id}: {e}")
        success = False
    finally:
        conn.close()
    return success


def unarchive_flashcards(card_ids, user_id):
    """Desarchiva una o varias flashcards."""
    if not card_ids:
        return 0
    conn = get_db_connection()
    cursor = conn.cursor()
    # Using a placeholder for each ID to prevent SQL injection
    placeholders = ','.join('?' for _ in card_ids)
    query = f"UPDATE flashcards SET is_archived = 0 WHERE id IN ({placeholders}) AND user_id = ?"
    cursor.execute(query, (*card_ids, user_id))
    conn.commit()
    conn.close()
    return cursor.rowcount

def update_flashcard_content(card_id, back_content, user_id):
    """Actualiza el contenido trasero de una flashcard específica."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE flashcards SET back_content = ? WHERE id = ? AND user_id = ?",
        (back_content, card_id, user_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def delete_flashcard_by_id(card_id, user_id):
    """Elimina una flashcard permanentemente."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM flashcards WHERE id = ? AND user_id = ?",
        (card_id, user_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def get_archived_flashcards(user_id, page=1, per_page=8):
    """Devuelve una lista paginada de flashcards archivadas para un usuario."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Contar el total de tarjetas archivadas para la paginación
    cursor.execute(
        "SELECT COUNT(id) FROM flashcards WHERE user_id = ? AND is_archived = 1",
        (user_id,)
    )
    total_cards = cursor.fetchone()[0]

    # Calcular el offset
    offset = (page - 1) * per_page

    # Obtener las tarjetas para la página actual
    cursor.execute(
        "SELECT id, front_content, back_content, category FROM flashcards WHERE user_id = ? AND is_archived = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, per_page, offset)
    )
    flashcards = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"flashcards": flashcards, "total_cards": total_cards}

JSON_FILES_WITH_CATEGORIES = {
    'Vocabulario': 'json/1_flashcards_vocabulario.txt',
    'Phrasal Verb': 'json/2_flashcards_phrasal_verbs.txt'
}

def populate_user_with_default_cards(user_id):
    """Populates a new user's account with the default set of flashcards."""
    conn = get_db_connection()
    cursor = conn.cursor()
    total_imported = 0

    for category, file_path in JSON_FILES_WITH_CATEGORIES.items():
        if not os.path.exists(file_path):
            print(f"Advertencia: El archivo {file_path} no fue encontrado. Saltando.")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

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
                        category,
                        card['exampleSentences']['en'],
                        card['exampleSentences']['es']
                    )
                )
                total_imported += 1
            except sqlite3.Error as e:
                print(f"Error insertando la tarjeta por defecto '{card.get('front', 'N/A')}' para el usuario {user_id}: {e}")

    conn.commit()
    conn.close()
    print(f"Importadas {total_imported} tarjetas por defecto para el nuevo usuario con ID: {user_id}")
    return total_imported

# Si ejecutamos este script directamente, configurará la base de datos
if __name__ == '__main__':
    setup_database()
    print(f"Base de datos '{DB_NAME}' configurada exitosamente.")
