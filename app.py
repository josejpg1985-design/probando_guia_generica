from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.security import check_password_hash
import jwt
import datetime
import database
from functools import wraps

app = Flask(__name__, static_folder='static', static_url_path='/static')

app.config['SECRET_KEY'] = 'esto-es-un-secreto-temporal'

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
    token = jwt.encode({'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({"status": "success", "token": token})

# --- API Protegida ---
@app.route('/api/user_info')
@token_required
@api_error_handler
def get_user_info(current_user):
    """Devuelve información del usuario autenticado."""
    return jsonify({'email': current_user['email'], 'id': current_user['id']})

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
    """Devuelve las flashcards para una categoría específica."""
    flashcards = database.get_flashcards_by_category(current_user['id'], category)
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
    per_page = 8 # 2 filas de 4 tarjetas

    archived_data = database.get_archived_flashcards(current_user['id'], page, per_page)
    
    return jsonify({
        "status": "success",
        "flashcards": archived_data['flashcards'],
        "total_cards": archived_data['total_cards'],
        "page": page,
        "per_page": per_page,
        "total_pages": (archived_data['total_cards'] + per_page - 1) // per_page
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

# --- Arranque de la App ---
def setup_app_database():
    with app.app_context():
        database.setup_database()

if __name__ == '__main__':
    setup_app_database()
    app.run(debug=True, port=5000)
