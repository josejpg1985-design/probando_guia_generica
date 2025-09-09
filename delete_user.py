import sqlite3
import sys

DB_NAME = 'flashcards.db'

def delete_user_by_email(email):
    """Deletes a user and their associated flashcards."""
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Find the user_id for the given email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            print(f"No se encontró ningún usuario con el email: {email}")
            return

        user_id = user[0]

        # 1. Delete user's flashcards
        cursor.execute("DELETE FROM flashcards WHERE user_id = ?", (user_id,))
        print(f"Se eliminaron {cursor.rowcount} flashcards del usuario.")

        # 2. Delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        print(f"Se eliminó el usuario con email: {email}")

        conn.commit()
        print("Cambios confirmados en la base de datos.")

    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}")
        if conn:
            conn.rollback()
            print("Se revirtieron los cambios.")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python delete_user.py <email_del_usuario>")
        sys.exit(1)
    
    email_to_delete = sys.argv[1]
    print(f"--- Intentando eliminar al usuario: {email_to_delete} ---")
    delete_user_by_email(email_to_delete)
    print("--- Proceso finalizado ---")
