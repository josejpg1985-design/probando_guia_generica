import os
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.security import check_password_hash
import jwt
import datetime
import database
import json
from functools import wraps
import re

app = Flask(__name__, static_folder='static', static_url_path='/static')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Cargar variables de entorno y configurar Gemini
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Decorador para proteger rutas con JWT ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'message': 'Token es requerido'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = database.get_user_by_id(data['user_id'])
            if current_user is None:
                return jsonify({'message': 'Usuario no encontrado'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token ha expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# --- Decorador para manejar errores de API ---
def api_error_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"API Error in {f.__name__}: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return decorated_function

# --- Rutas Públicas ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/archived')
def archived_cards_page():
    """Renderiza la página de tarjetas archivadas."""
    return render_template('archivadas.html')

@app.route('/study/<category>')
def study(category):
    """Renderiza la página de estudio para una categoría específica."""
    return render_template('study.html', category=category)

# --- Modo Inmersión ---
@app.route('/inmersion/<escenario>')
def inmersion(escenario):
    """Renderiza la página del modo inmersión para un escenario específico."""
    try:
        # Validar que el usuario esté 'logueado' podría ir aquí si es necesario
        # Por ahora, lo dejamos abierto para simplicidad.
        
        with open('json/3_inmersion_dialogos.json', 'r', encoding='utf-8') as f:
            dialogos_data = json.load(f)
        
        dialogo = dialogos_data.get(escenario)
        if not dialogo:
            # Podríamos redirigir al dashboard o mostrar un error amigable
            return redirect(url_for('dashboard'))

        escenario_titulo = escenario.replace('_', ' ').capitalize()

        return render_template(
            'inmersion.html', 
            escenario=escenario,
            escenario_titulo=escenario_titulo,
            dialogo_json=dialogo # Pasamos el diálogo como JSON
        )
    except FileNotFoundError:
        # Manejo del error si el archivo JSON no se encuentra
        return "Error: El archivo de diálogos no fue encontrado.", 404
    except Exception as e:
        # Manejo de otros posibles errores
        app.logger.error(f"Error en modo inmersión para escenario '{escenario}': {e}")
        return "Ocurrió un error inesperado.", 500

# --- API de Autenticación ---
@app.route('/api/register', methods=['POST'])
@api_error_handler
def register_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"status": "error", "message": "Email y contraseña son requeridos."}), 400
    
    result = database.add_user(email, password)
    
    if result["status"] == "success":
        # Populate new user with default flashcards
        new_user_id = result['user_id']
        database.populate_user_with_default_cards(new_user_id)
        return jsonify(result), 201
    else:
        return jsonify(result), 409

@app.route('/api/login', methods=['POST'])
@api_error_handler
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password: return jsonify({"status": "error", "message": "Email y contraseña son requeridos."}), 400
    user = database.get_user_by_email(email)
    if not user or not check_password_hash(user['password_hash'], password): return jsonify({"status": "error", "message": "Credenciales inválidas."}), 401
    token = jwt.encode({'user_id': user['id'], 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({"status": "success", "token": token})

# --- API Protegida ---
@app.route('/api/user_info')
@token_required
@api_error_handler
def get_user_info(current_user):
    """Devuelve información del usuario autenticado."""
    return jsonify({'email': current_user['email'], 'id': current_user['id']})

@app.route('/api/user/progress')
@token_required
@api_error_handler
def get_user_progress_api(current_user):
    """Devuelve el progreso del usuario."""
    progress_data = database.get_user_progress(current_user['id'])
    return jsonify({"status": "success", "progress": progress_data})


@app.route('/api/categories')
@token_required
@api_error_handler
def get_categories(current_user):
    """Devuelve las categorías de flashcards disponibles para el usuario."""
    categories = database.get_categories_for_user(current_user['id'])
    return jsonify({'status': 'success', 'categories': categories})

@app.route('/api/flashcards/<category>')
@token_required
@api_error_handler
def get_flashcards(current_user, category):
    """Devuelve las flashcards para una categoría específica, con opción de búsqueda."""
    search_term = request.args.get('search', None)
    flashcards = database.get_flashcards_by_category(current_user['id'], category, search_term=search_term)
    return jsonify({'status': 'success', 'flashcards': flashcards})

@app.route('/api/flashcards/rate', methods=['POST'])
@token_required
@api_error_handler
def rate_flashcard(current_user):
    """Recibe la calificación de una flashcard y actualiza sus datos SM-2."""
    data = request.get_json()
    card_id = data.get('card_id')
    rating = data.get('rating') # 1=Difícil, 2=Normal, 3=Fácil

    if not card_id or rating is None:
        return jsonify({"status": "error", "message": "ID de tarjeta y calificación son requeridos."}), 400

    # Asegurarse de que la tarjeta pertenece al usuario actual antes de actualizar
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM flashcards WHERE id = ?", (card_id,))
    card_owner_id = cursor.fetchone()
    conn.close()

    if not card_owner_id or card_owner_id['user_id'] != current_user['id']:
        return jsonify({"status": "error", "message": "Tarjeta no encontrada o no pertenece al usuario."}), 403 # Prohibido

    success = database.update_flashcard_sm2_data(card_id, rating)

    if success:
        # También incrementamos el contador de calificación
        database.increment_rating_count(card_id, rating)
        return jsonify({"status": "success", "message": "Calificación registrada y tarjeta actualizada."})
    else:
        return jsonify({"status": "error", "message": "No se pudo actualizar la tarjeta."}), 500

@app.route('/api/flashcards/<int:card_id>/flip', methods=['POST'])
@token_required
@api_error_handler
def flip_card(current_user, card_id):
    """Incrementa el contador de giros de una flashcard."""
    # Asegurarse de que la tarjeta pertenece al usuario actual antes de actualizar
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM flashcards WHERE id = ?", (card_id,))
    card_owner = cursor.fetchone()
    conn.close()

    if not card_owner or card_owner['user_id'] != current_user['id']:
        return jsonify({"status": "error", "message": "Tarjeta no encontrada o no pertenece al usuario."}), 403

    success = database.increment_flip_count(card_id)

    if success:
        return jsonify({"status": "success", "message": "Contador de giros incrementado."})
    else:
        return jsonify({"status": "error", "message": "No se pudo incrementar el contador."}), 500

@app.route('/api/flashcards/archive', methods=['POST'])
@token_required
@api_error_handler
def archive_card(current_user):
    """Archiva una flashcard."""
    data = request.get_json()
    card_id = data.get('card_id')
    if not card_id:
        return jsonify({"status": "error", "message": "ID de tarjeta es requerido."}), 400
    
    success = database.archive_flashcard(card_id, current_user['id'])
    if success:
        return jsonify({"status": "success", "message": "Tarjeta archivada correctamente."})
    else:
        return jsonify({"status": "error", "message": "No se pudo archivar la tarjeta o no pertenece al usuario."}), 400

@app.route('/api/flashcards/unarchive', methods=['POST'])
@token_required
@api_error_handler
def unarchive_cards(current_user):
    """Desarchiva una o varias flashcards."""
    data = request.get_json()
    card_ids = data.get('card_ids') # Expects a list of IDs
    if not card_ids or not isinstance(card_ids, list):
        return jsonify({"status": "error", "message": "Lista de IDs de tarjeta es requerida."}), 400
    
    rows_affected = database.unarchive_flashcards(card_ids, current_user['id'])
    if rows_affected > 0:
        return jsonify({"status": "success", "message": f"{rows_affected} tarjeta(s) desarchivada(s) correctamente."})
    else:
        return jsonify({"status": "error", "message": "No se pudo desarchivar ninguna tarjeta o no pertenecen al usuario."}), 400

@app.route('/api/flashcards/archived', methods=['GET'])
@token_required
@api_error_handler
def get_archived_cards(current_user):
    """Devuelve una lista paginada de flashcards archivadas para el usuario actual."""
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    
    search_term = request.args.get('search', None)
    per_page = 8 # 2 filas de 4 tarjetas

    archived_data = database.get_archived_flashcards(current_user['id'], page, per_page, search=search_term)
    
    total_pages = (archived_data['total_cards'] + per_page - 1) // per_page if archived_data['total_cards'] > 0 else 1

    return jsonify({
        "status": "success",
        "flashcards": archived_data['flashcards'],
        "total_cards": archived_data['total_cards'],
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    })

@app.route('/api/flashcards/<int:card_id>', methods=['PUT'])
@token_required
@api_error_handler
def update_flashcard(current_user, card_id):
    """Actualiza el contenido de una flashcard."""
    data = request.get_json()
    back_content = data.get('back_content')
    if not back_content:
        return jsonify({"status": "error", "message": "El contenido trasero es requerido."}), 400

    success = database.update_flashcard_content(card_id, back_content, current_user['id'])
    
    if success:
        return jsonify({"status": "success", "message": "Tarjeta actualizada correctamente."})
    else:
        return jsonify({"status": "error", "message": "No se pudo actualizar la tarjeta o no pertenece al usuario."}), 404

@app.route('/api/flashcards/<int:card_id>', methods=['DELETE'])
@token_required
@api_error_handler
def delete_flashcard(current_user, card_id):
    """Elimina una flashcard permanentemente."""
    success = database.delete_flashcard_by_id(card_id, current_user['id'])
    
    if success:
        return jsonify({"status": "success", "message": "Tarjeta eliminada permanentemente."})
    else:
        return jsonify({"status": "error", "message": "No se pudo eliminar la tarjeta o no pertenece al usuario."}), 404

@app.route('/api/flashcards/archived/random/<int:count>', methods=['GET'])
@token_required
def get_random_cards(current_user, count):
    """
    Devuelve una lista de flashcards archivadas al azar.
    """
    if count <= 0 or count > 100: # Limitar para evitar abusos
        return jsonify({"status": "error", "message": "La cantidad debe estar entre 1 y 100."}), 400

    try:
        random_cards = database.get_random_archived_cards(current_user['id'], count)
        return jsonify({"status": "success", "flashcards": random_cards})

    except Exception as e:
        app.logger.error(f"Error getting random cards: {str(e)}")
        return jsonify({"status": "error", "message": "No se pudieron obtener las tarjetas aleatorias."}), 500

@app.route('/api/translate', methods=['POST'])
@token_required
def translate_text(current_user):
    """
    Traduce un texto proporcionado a un idioma de destino (por defecto, español).
    """
    if not GEMINI_API_KEY:
        return jsonify({"status": "error", "message": "La clave de API de Gemini no está configurada en el servidor."}), 500

    data = request.get_json()
    text_to_translate = data.get('text')
    target_language = data.get('target_language', 'Spanish') # Por defecto a español

    if not text_to_translate:
        return jsonify({"status": "error", "message": "Se requiere texto para traducir."}), 400

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"Translate the following English text to {target_language}: '{text_to_translate}'"
        
        response = model.generate_content(prompt)
        
        translated_text = response.text.strip()
        
        return jsonify({"status": "success", "translated_text": translated_text})

    except Exception as e:
        app.logger.error(f"Error translating text with Gemini: {str(e)}")
        return jsonify({"status": "error", "message": "No se pudo traducir el texto."}), 500

@app.route('/api/generate-paragraph', methods=['POST'])
@token_required
def generate_paragraph(current_user):
    """
    Genera un párrafo coloquial A1-A2 en inglés y su traducción al español.
    """
    if not GEMINI_API_KEY:
        return jsonify({"status": "error", "message": "La clave de API de Gemini no está configurada en el servidor."}), 500

    data = request.get_json()
    words = data.get('words')

    if not words or not isinstance(words, list):
        return jsonify({"status": "error", "message": "Se requiere una lista de palabras."}), 400

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        words_str = ", ".join(words)
        
        prompt = f"""You are an assistant for an English learner at A1-A2 level.
Your task is to generate a very simple, short, and colloquial paragraph in English.
The paragraph should incorporate the following words: {words_str}.
It must be grammatically correct, natural-sounding, and easy to understand, using basic vocabulary and sentence structures suitable for an A1-A2 learner.
After the English paragraph, provide its accurate and natural-sounding translation in Spanish.
Format your response as a single JSON object with two keys: "english_paragraph" and "spanish_paragraph".
Do not include any other text or markdown formatting like ```json. Just the raw JSON object.
Example response for words "cat, house, happy":
{{
  "english_paragraph": "The happy cat is in the house. It likes to play there.",
  "spanish_paragraph": "El gato feliz está en la casa. Le gusta jugar allí."
}}
"""
        
        response = model.generate_content(prompt)
        
        text_response = response.text.strip()
        
        try:
            data = json.loads(text_response)
            english_paragraph = data.get("english_paragraph")
            spanish_paragraph = data.get("spanish_paragraph")

            if not english_paragraph or not spanish_paragraph:
                raise ValueError("JSON response did not contain the expected keys.")

            return jsonify({
                "status": "success",
                "english_paragraph": english_paragraph,
                "spanish_paragraph": spanish_paragraph
            })
        except (json.JSONDecodeError, ValueError) as e:
            app.logger.error(f"Could not parse JSON response from Gemini: {text_response} - Error: {e}")
            return jsonify({"status": "error", "message": "La IA no devolvió un formato de respuesta válido. Inténtalo de nuevo."}), 500

    except Exception as e:
        app.logger.error(f"Error generating paragraph with Gemini: {str(e)}")
        return jsonify({"status": "error", "message": "No se pudo generar el párrafo. Verifica tu clave de API y la disponibilidad del modelo."}), 500

@app.route('/api/analyze-lyrics', methods=['POST'])
@token_required
@api_error_handler
def analyze_lyrics(current_user):
    try:
        if not GEMINI_API_KEY:
            return jsonify({"status": "error", "message": "La clave de API de Gemini no está configurada en el servidor."}), 500

        data = request.get_json()
        lyrics_paragraph = data.get('lyrics')
        if not lyrics_paragraph:
            return jsonify({"status": "error", "message": "Se requiere un párrafo de letras para analizar."}), 400

        # 1. Hacer una única llamada a la API para analizar la letra completa
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            prompt = f"""You are an expert linguistic assistant for an English learner at the A1-A2 level.
Your task is to analyze the provided song lyrics and extract meaningful vocabulary, including individual words and phrasal verbs.

The lyrics are: "{lyrics_paragraph}"

From these lyrics, identify and extract:
1.  A list of simple, useful vocabulary words (nouns, verbs, adjectives).
2.  A list of any phrasal verbs (e.g., 'come back', 'run in', 'take off').

For each word or phrasal verb you extract, you must provide:
1.  `item`: The vocabulary word or the full phrasal verb.
2.  `translation`: The most common Spanish equivalent.
3.  `english_phrase`: A simple, short English phrase using the item. This phrase MUST be directly from or clearly inspired by the context of the provided lyrics.
4.  `spanish_phrase`: An accurate and natural-sounding Spanish translation of the `english_phrase`.

Your response MUST be a single, valid JSON array where each element is an object with the keys: "item", "translation", "english_phrase", and "spanish_phrase".
Do not include items that are too simple (e.g., 'I', 'a', 'the', 'is').

Do not include any other text, explanations, or markdown formatting like ```json. Just the raw JSON array.

Example response for lyrics "Take me back to the start. The sun is out.":
[
  {{
    "item": "take back",
    "translation": "llevar de vuelta",
    "english_phrase": "Take me back to the start.",
    "spanish_phrase": "Llévame de vuelta al principio."
  }},
  {{
    "item": "start",
    "translation": "principio",
    "english_phrase": "Take me back to the start.",
    "spanish_phrase": "Llévame de vuelta al principio."
  }},
  {{
    "item": "sun",
    "translation": "sol",
    "english_phrase": "The sun is out.",
    "spanish_phrase": "El sol ha salido."
  }}
]
"""
            
            response = model.generate_content(prompt)

            if not response.text:
                raise ValueError("La respuesta de la IA está vacía.")
            
            cleaned_response_text = response.text.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[7:]
            if cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[:-3]

            if not cleaned_response_text:
                raise ValueError("La respuesta de la IA está vacía después de la limpieza.")
            
            try:
                ai_results = json.loads(cleaned_response_text)
            except (json.JSONDecodeError, TypeError) as e:
                app.logger.error(f"Error al procesar la respuesta JSON de la IA: {cleaned_response_text} - Error: {e}")
                raise ValueError(f"La IA devolvió un formato de respuesta inesperado. Detalles: {e}")

        except Exception as e:
            app.logger.error(f"Error processing analysis with Gemini: {str(e)}")
            return jsonify({"status": "error", "message": f"Error de la IA: {str(e)}"}), 500

        # 2. Combinar resultados de la IA con datos de la base de datos
        results = []
        if not isinstance(ai_results, list):
            app.logger.warning(f"AI returned a non-list type: {type(ai_results)}")
            return jsonify({"status": "success", "words": []})

        seen_items = set()
        for ai_word_data in ai_results:
            if not isinstance(ai_word_data, dict):
                continue

            word_or_phrase = ai_word_data.get("item")
            
            if not isinstance(word_or_phrase, str) or not word_or_phrase:
                continue
            
            if word_or_phrase in seen_items:
                continue
            seen_items.add(word_or_phrase)

            flashcard_data = database.get_flashcard_by_front_content(current_user['id'], word_or_phrase, "Lyrics")
            is_duplicate = flashcard_data is not None
            
            result_item = {
                "word": word_or_phrase,
                "is_duplicate": is_duplicate,
                "existing_en_phrase": "",
                "existing_es_phrase": "",
                "flashcard_id": None,
                "word_translation": ai_word_data.get("translation", "Error"),
                "new_en_phrase": ai_word_data.get("english_phrase", "Error"),
                "new_es_phrase": ai_word_data.get("spanish_phrase", "Error")
            }

            if is_duplicate and flashcard_data:
                result_item["existing_en_phrase"] = flashcard_data.get('example_en', '')
                result_item["existing_es_phrase"] = flashcard_data.get('example_es', '')
                result_item["flashcard_id"] = flashcard_data.get('id')
                
            results.append(result_item)

        return jsonify({"status": "success", "words": results})
    except Exception as e:
        app.logger.error(f"FATAL ERROR in analyze_lyrics: {e}")
        return jsonify({{"status": "fatal_error", "message": str(e)}}), 500

@app.route('/api/flashcards/add', methods=['POST'])
@token_required
@api_error_handler
def add_flashcard_api(current_user):
    data = request.get_json()
    front_content = data.get('front_content')
    back_content = data.get('back_content')
    category = data.get('category', 'Lyrics') # Default category
    example_en = data.get('example_en')
    example_es = data.get('example_es')

    if not all([front_content, back_content, example_en, example_es]):
        return jsonify({"status": "error", "message": "Faltan datos requeridos para la flashcard."}), 400

    result = database.add_flashcard(current_user['id'], front_content, back_content, category, example_en, example_es)
    if result['status'] == 'success':
        return jsonify({"status": "success", "message": "Flashcard añadida correctamente.", "card_id": result['card_id']}), 201
    else:
        return jsonify({"status": "error", "message": result['message']}), 500

@app.route('/api/flashcards/update_phrases/<int:card_id>', methods=['PUT'])
@token_required
@api_error_handler
def update_flashcard_phrases_api(current_user, card_id):
    data = request.get_json()
    back_content = data.get('back_content')
    example_en = data.get('example_en')
    example_es = data.get('example_es')

    if not all([back_content, example_en, example_es]):
        return jsonify({"status": "error", "message": "Faltan datos requeridos para actualizar la flashcard."}), 400

    success = database.update_flashcard_phrases(card_id, current_user['id'], back_content, example_en, example_es)
    if success:
        return jsonify({"status": "success", "message": "Flashcard actualizada correctamente."})
    else:
        return jsonify({"status": "error", "message": "No se pudo actualizar la flashcard o no pertenece al usuario."}), 404

# --- Arranque de la App ---
def setup_app_database():
    with app.app_context():
        database.setup_database()

if __name__ == '__main__':
    setup_app_database()
    app.run(debug=True, port=5000)
