from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask import send_from_directory
from config import get_db_connection
from services.tutoring import (
    calcular_puntuacion_estudiante, 
    detectar_patrones_error, 
    recomendar_nivel_siguiente,
    generar_feedback_personalizado,
    calcular_nivel_lector_diagnostico,
    normalizar_texto,
    get_db_cursor,
    actualizar_nivel_estudiante
)
import bcrypt
import os
import unicodedata

app = Flask(__name__)

# Configuración JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'tu_clave_secreta_aqui')
jwt = JWTManager(app)

@app.route("/")
def index():
    return send_from_directory("frontend/login", "login.html")

@app.route("/styles.css")
def styles():
    return send_from_directory("frontend/common", "styles_general.css")

@app.route("/login.js")
def login_js():
    return send_from_directory("frontend/login", "login.js")

@app.route("/dashboard.html")
def dashboard():
    return send_from_directory("frontend/menu", "menu.html")

@app.route("/menu.html")
def menu_html():
    return send_from_directory("frontend/menu", "menu.html")

@app.route("/dashboard.js")
def dashboard_js():
    return send_from_directory("frontend/menu", "menu.js")

@app.route("/reading.html")
def reading():
    return send_from_directory("frontend/reading", "reading.html")

@app.route("/reading.js")
def reading_js():
    return send_from_directory("frontend/reading", "reading.js")

@app.route("/header.js")
def header_js():
    return send_from_directory("frontend/common", "header.js")

@app.route("/header.html")
def header_html():
    return send_from_directory("frontend/common", "header.html")

@app.route("/texto/<int:id_texto>", methods=['GET'])
@jwt_required()
def obtener_texto(id_texto):
    """Obtiene un texto específico (requiere autenticación)"""
    try:
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_texto, titulo, contenido, nivel FROM textos WHERE id_texto = %s", (id_texto,))
        texto = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not texto:
            return jsonify({"error": "Texto no encontrado"}), 404
        
        return jsonify(texto), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener texto: {str(e)}"}), 500

@app.route("/textos")
@jwt_required()
def obtener_textos():
    """Obtiene todos los textos disponibles (requiere autenticación)"""
    try:
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_texto, titulo, contenido, nivel FROM textos")
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not resultados:
            return jsonify([]), 200
        
        return jsonify(resultados), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener textos: {str(e)}"}), 500

# ===========================================
# APARTADO DE AUTENTICACIÓN
# ===========================================
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')
    id_rol = data.get('id_rol', 1)  # Por defecto estudiante

    if not nombre or not email or not password:
        return jsonify({"error": "Nombre, email y password son requeridos"}), 400

    try:
        conn, cursor = get_db_cursor()
        
        # Validar si el email ya existe
        cursor.execute("SELECT id_usuario FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "El email ya está registrado"}), 409

        # Hashear la contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor.execute("INSERT INTO usuarios (nombre, email, contraseña, id_rol, fecha_registro) VALUES (%s, %s, %s, %s, CURDATE())",
                       (nombre, email, hashed_password.decode('utf-8'), id_rol))
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({"message": "Usuario registrado exitosamente", "id_usuario": user_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email y password son requeridos"}), 400

    try:
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_usuario, nombre, contraseña, id_rol FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            stored_password = user['contraseña']
            password_bytes = password.encode('utf-8')
            try:
                password_matches = bcrypt.checkpw(password_bytes, stored_password.encode('utf-8'))
            except ValueError:
                # Si la contraseña en la base de datos no está hasheada,
                # comparamos directamente el texto.
                password_matches = password == stored_password

            if password_matches:
                access_token = create_access_token(identity=str(user['id_usuario']))
                return jsonify({"access_token": access_token, "user": {"id": user['id_usuario'], "nombre": user['nombre'], "rol": user['id_rol']}}), 200

        return jsonify({"error": "Credenciales inválidas"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({"message": f"Hola {current_user['nombre']}, tienes acceso!"}), 200

# ===========================================
# APARTADO DE PREGUNTAS Y RESPUESTAS
# ===========================================
@app.route('/preguntas/<int:id_texto>', methods=['GET'])
@jwt_required()
def obtener_preguntas(id_texto):
    """Obtiene todas las preguntas de un texto específico (requiere autenticación)"""
    try:
        if id_texto <= 0:
            return jsonify({"error": "ID de texto inválido"}), 400
        
        conn, cursor = get_db_cursor()
        
        # Verificar que el texto existe
        cursor.execute("SELECT id_texto FROM textos WHERE id_texto = %s", (id_texto,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Texto no encontrado"}), 404
        
        cursor.execute("SELECT id_pregunta, id_texto, enunciado, tipo FROM preguntas WHERE id_texto = %s", (id_texto,))
        preguntas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(preguntas if preguntas else []), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener preguntas: {str(e)}"}), 500

@app.route('/pregunta/<int:id_pregunta>', methods=['GET'])
@jwt_required()
def obtener_pregunta(id_pregunta):
    """Obtiene los detalles de una pregunta específica (requiere autenticación)"""
    try:
        if id_pregunta <= 0:
            return jsonify({"error": "ID de pregunta inválido"}), 400
        
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_pregunta, id_texto, enunciado, tipo FROM preguntas WHERE id_pregunta = %s", (id_pregunta,))
        pregunta = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not pregunta:
            return jsonify({"error": "Pregunta no encontrada"}), 404
        
        return jsonify(pregunta), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener pregunta: {str(e)}"}), 500

@app.route('/respuesta-correcta/<int:id_pregunta>', methods=['GET'])
@jwt_required()
def obtener_respuesta_correcta(id_pregunta):
    """Obtiene la respuesta correcta de una pregunta (solo para docentes/admin)"""
    try:
        current_user = get_jwt_identity()
        id_rol = current_user.get('rol')
        
        # Validar que sea docente (id_rol 2) o admin (id_rol 3)
        if id_rol not in [2, 3]:
            return jsonify({"error": "No tienes permisos. Solo docentes y administradores pueden ver respuestas correctas."}), 403
        
        if id_pregunta <= 0:
            return jsonify({"error": "ID de pregunta inválido"}), 400
        
        conn, cursor = get_db_cursor()
        
        # Verificar que la pregunta existe
        cursor.execute("SELECT id_pregunta FROM preguntas WHERE id_pregunta = %s", (id_pregunta,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Pregunta no encontrada"}), 404
        
        cursor.execute("SELECT id_respuesta, id_pregunta, respuesta FROM respuestas_correctas WHERE id_pregunta = %s", (id_pregunta,))
        respuesta = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not respuesta:
            return jsonify({"error": "Respuesta correcta no encontrada"}), 404
        
        return jsonify(respuesta), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener respuesta correcta: {str(e)}"}), 500

@app.route('/respuestas', methods=['POST'])
@jwt_required()
def guardar_respuesta():
    """Guarda la respuesta de un estudiante a una pregunta"""
    try:
        current_user = get_jwt_identity()
        id_usuario = current_user['id']
        data = request.get_json()
        
        id_pregunta = data.get('id_pregunta')
        respuesta = data.get('respuesta')
        tiempo_respuesta = data.get('tiempo_respuesta', 0)
        
        if not id_pregunta or not respuesta:
            return jsonify({"error": "id_pregunta y respuesta son requeridos"}), 400
        
        # Obtener id_estudiante del usuario
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()
        
        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no es estudiante"}), 400
        
        id_estudiante = estudiante[0]
        
        # Obtener la respuesta correcta
        cursor.execute("SELECT respuesta FROM respuestas_correctas WHERE id_pregunta = %s", (id_pregunta,))
        respuesta_correcta_row = cursor.fetchone()
        
        es_correcta = False
        if respuesta_correcta_row:
            es_correcta = respuesta.lower().strip() == respuesta_correcta_row[0].lower().strip()
        
        # Guardar la respuesta del estudiante
        cursor.execute("""INSERT INTO respuestas_estudiante 
                         (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta, fecha) 
                         VALUES (%s, %s, %s, %s, %s, CURDATE())""",
                      (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta))
        conn.commit()
        respuesta_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Respuesta guardada exitosamente", 
                       "id_respuesta_est": respuesta_id, 
                       "es_correcta": es_correcta}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/respuestas-estudiante/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_respuestas_estudiante(id_estudiante):
    """Obtiene todas las respuestas de un estudiante (requiere ser el estudiante o docente/admin)"""
    try:
        current_user = get_jwt_identity()
        id_usuario = current_user['id']
        id_rol = current_user.get('rol')
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        # Obtener id_estudiante del usuario actual
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante_actual = cursor.fetchone()
        
        # Validar permisos: solo el estudiante o docente/admin pueden ver
        if id_rol == 1:  # Es estudiante
            if not estudiante_actual or estudiante_actual[0] != id_estudiante:
                cursor.close()
                conn.close()
                return jsonify({"error": "No tienes permisos para ver las respuestas de otro estudiante"}), 403
        elif id_rol not in [2, 3]:  # No es docente ni admin
            cursor.close()
            conn.close()
            return jsonify({"error": "No tienes permisos para acceder a esta información"}), 403
        
        cursor.execute("""SELECT id_respuesta_est, id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta, fecha 
                         FROM respuestas_estudiante WHERE id_estudiante = %s
                         ORDER BY fecha DESC""", (id_estudiante,))
        respuestas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not respuestas:
            return jsonify([]), 200
        
        resultado = [{
            "id_respuesta_est": r[0],
            "id_estudiante": r[1],
            "id_pregunta": r[2],
            "respuesta": r[3],
            "es_correcta": bool(r[4]),
            "tiempo_respuesta": r[5],
            "fecha": str(r[6])
        } for r in respuestas]
        
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener respuestas: {str(e)}"}), 500

@app.route('/verificar-respuesta/<int:id_pregunta>', methods=['POST'])
@jwt_required()
def verificar_respuesta(id_pregunta):
    """Verifica si una respuesta es correcta sin guardarla (requiere autenticación)"""
    try:
        if id_pregunta <= 0:
            return jsonify({"error": "ID de pregunta inválido"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Body JSON requerido"}), 400
        
        respuesta_usuario = data.get('respuesta', '').strip()
        
        if not respuesta_usuario:
            return jsonify({"error": "Respuesta requerida"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que la pregunta existe
        cursor.execute("SELECT id_pregunta FROM preguntas WHERE id_pregunta = %s", (id_pregunta,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Pregunta no encontrada"}), 404
        
        cursor.execute("SELECT respuesta FROM respuestas_correctas WHERE id_pregunta = %s", (id_pregunta,))
        respuesta_correcta_row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not respuesta_correcta_row:
            return jsonify({"error": "Pregunta sin respuesta correcta definida"}), 404
        
        es_correcta = respuesta_usuario.lower() == respuesta_correcta_row[0].lower().strip()
        
        return jsonify({"es_correcta": es_correcta}), 200
    except Exception as e:
        return jsonify({"error": f"Error al verificar respuesta: {str(e)}"}), 500

# ===========================================
# MÓDULO: TUTOR INTELIGENTE
# ===========================================
@app.route('/evaluacion/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_evaluacion(id_estudiante):
    """Obtiene la evaluación general del estudiante"""
    try:
        current_user = get_jwt_identity()
        id_rol = current_user.get('rol')
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        # Docentes y admin pueden ver cualquier estudiante, estudiantes solo el suyo
        if id_rol == 1:  # Estudiante
            conn, cursor = get_db_cursor()
            cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (current_user['id'],))
            estudiante_actual = cursor.fetchone()
            cursor.close()
            conn.close()
            if not estudiante_actual or estudiante_actual['id_estudiante'] != id_estudiante:
                return jsonify({"error": "No tienes permisos para ver la evaluación de otro estudiante"}), 403
        
        limite = request.args.get('limite', 50, type=int)
        if limite <= 0 or limite > 1000:
            limite = 50
        
        evaluacion = calcular_puntuacion_estudiante(id_estudiante, limite)
        return jsonify(evaluacion), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener evaluación: {str(e)}"}), 500

@app.route('/patrones-error/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_patrones(id_estudiante):
    """Detecta patrones de error del estudiante"""
    try:
        current_user = get_jwt_identity()
        id_rol = current_user.get('rol')
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        # Validar permisos
        if id_rol == 1:  # Estudiante
            conn, cursor = get_db_cursor()
            cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (current_user['id'],))
            estudiante_actual = cursor.fetchone()
            cursor.close()
            conn.close()
            if not estudiante_actual or estudiante_actual['id_estudiante'] != id_estudiante:
                return jsonify({"error": "No tienes permisos para ver los patrones de otro estudiante"}), 403
        
        patrones = detectar_patrones_error(id_estudiante)
        return jsonify(patrones), 200
    except Exception as e:
        return jsonify({"error": f"Error al detectar patrones: {str(e)}"}), 500

@app.route('/recomendacion-nivel/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_recomendacion(id_estudiante):
    """Obtiene recomendación de nivel siguiente"""
    try:
        current_user = get_jwt_identity()
        id_rol = current_user.get('rol')
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        # Validar permisos
        if id_rol == 1:  # Estudiante
            conn, cursor = get_db_cursor()
            cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (current_user['id'],))
            estudiante_actual = cursor.fetchone()
            cursor.close()
            conn.close()
            if not estudiante_actual or estudiante_actual['id_estudiante'] != id_estudiante:
                return jsonify({"error": "No tienes permisos para ver la recomendación de otro estudiante"}), 403
        
        recomendacion = recomendar_nivel_siguiente(id_estudiante)
        
        # Actualizar nivel si hay recomendación
        if recomendacion and recomendacion.get('recomendacion') in ['siguiente', 'anterior']:
            actualizar_nivel_estudiante(id_estudiante, recomendacion.get('nuevo_nivel'))
        
        return jsonify(recomendacion), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener recomendación: {str(e)}"}), 500

@app.route('/respuesta-con-feedback', methods=['POST'])
@jwt_required()
def responder_con_feedback():
    """
    Responde una pregunta y obtiene feedback inmediato
    Body: {
        "id_pregunta": 1,
        "respuesta": "texto",
        "tiempo_respuesta": 30
    }
    """
    try:
        current_user = get_jwt_identity()
        id_usuario = current_user['id']
        data = request.get_json()
        
        id_pregunta = data.get('id_pregunta')
        respuesta = data.get('respuesta')
        tiempo_respuesta = data.get('tiempo_respuesta', 0)
        
        if not id_pregunta or respuesta is None:
            return jsonify({"error": "id_pregunta y respuesta son requeridos"}), 400
        
        conn, cursor = get_db_cursor()
        
        # Obtener info del estudiante y pregunta
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()
        
        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no es estudiante"}), 400
        
        id_estudiante = estudiante['id_estudiante']
        
        # Obtener tipo de pregunta y respuesta correcta
        cursor.execute("""
            SELECT p.tipo, rc.respuesta 
            FROM preguntas p 
            LEFT JOIN respuestas_correctas rc ON p.id_pregunta = rc.id_pregunta 
            WHERE p.id_pregunta = %s
        """, (id_pregunta,))
        
        pregunta_info = cursor.fetchone()
        if not pregunta_info:
            cursor.close()
            conn.close()
            return jsonify({"error": "Pregunta no encontrada"}), 404
        
        tipo_pregunta = pregunta_info['tipo']
        respuesta_correcta = pregunta_info['respuesta']
        
        # Verificar si es correcta (con normalización de texto)
        es_correcta = False
        if respuesta_correcta and respuesta:
            es_correcta = normalizar_texto(respuesta) == normalizar_texto(respuesta_correcta)
        
        # Guardar respuesta
        cursor.execute("""INSERT INTO respuestas_estudiante 
                         (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta, fecha) 
                         VALUES (%s, %s, %s, %s, %s, CURDATE())""",
                      (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta))
        conn.commit()
        respuesta_id = cursor.lastrowid
        
        # Generar feedback
        feedback = generar_feedback_personalizado(
            id_pregunta, 
            es_correcta, 
            respuesta, 
            respuesta_correcta or '',
            tipo_pregunta
        )
        
        # Obtener recomendación (si hay suficientes respuestas)
        cursor.execute("SELECT COUNT(*) FROM respuestas_estudiante WHERE id_estudiante = %s", (id_estudiante,))
        resultado_count = cursor.fetchone()
        total_respuestas = resultado_count['COUNT(*)'] if isinstance(resultado_count, dict) else resultado_count[0]
        
        recomendacion = None
        if total_respuestas >= 5:
            cursor.close()
            conn.close()
            recomendacion = recomendar_nivel_siguiente(id_estudiante)
            # Actualizar nivel si hay recomendación de cambio
            if recomendacion and recomendacion.get('recomendacion') in ['siguiente', 'anterior']:
                actualizar_nivel_estudiante(id_estudiante, recomendacion.get('nuevo_nivel'))
        else:
            cursor.close()
            conn.close()
        
        resultado = {
            "id_respuesta_est": respuesta_id,
            "es_correcta": es_correcta,
            "feedback": feedback,
            "recomendacion": recomendacion,
            "total_respuestas": total_respuestas
        }
        
        return jsonify(resultado), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/diagnostico-inicial', methods=['POST'])
@jwt_required()
def realizar_diagnostico():
    """
    Realiza diagnóstico inicial del estudiante
    Body: {
        "respuestas": [true, false, true, ...],
        "preguntas_ids": [1, 2, 3, ...]
    }
    Retorna el nivel inicial asignado
    """
    try:
        current_user = get_jwt_identity()
        id_usuario = current_user['id']
        data = request.get_json()
        
        respuestas = data.get('respuestas', [])
        preguntas_ids = data.get('preguntas_ids', [])
        
        if not respuestas or len(respuestas) != len(preguntas_ids):
            return jsonify({"error": "respuestas y preguntas_ids deben coincidir"}), 400
        
        # Obtener estudiante
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()
        
        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no es estudiante"}), 400
        
        id_estudiante = estudiante['id_estudiante']
        
        # Guardar respuestas del diagnóstico
        for pregunta_id, es_correcta in zip(preguntas_ids, respuestas):
            cursor.execute("""INSERT INTO respuestas_estudiante 
                             (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta, fecha) 
                             VALUES (%s, %s, %s, %s, %s, CURDATE())""",
                          (id_estudiante, pregunta_id, '', es_correcta, 0))
        
        conn.commit()
        
        # Calcular nivel
        resultado_diagnostico = calcular_nivel_lector_diagnostico(respuestas)
        nivel_asignado = resultado_diagnostico['nivel']
        
        # Guardar en tabla diagnostico
        cursor.execute("""INSERT INTO diagnostico 
                         (id_estudiante, puntaje, nivel_asignado, fecha) 
                         VALUES (%s, %s, %s, CURDATE())""",
                      (id_estudiante, resultado_diagnostico['porcentaje'], nivel_asignado))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Actualizar nivel del estudiante
        actualizar_nivel_estudiante(id_estudiante, nivel_asignado)
        
        return jsonify({
            "diagnostico_completado": True,
            "nivel_inicial": nivel_asignado,
            "detalle": resultado_diagnostico,
            "mensaje": resultado_diagnostico['razon']
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/progreso/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_progreso(id_estudiante):
    """Obtiene resumen del progreso del estudiante"""
    try:
        current_user = get_jwt_identity()
        id_rol = current_user.get('rol')
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        # Validar permisos
        if id_rol == 1:  # Estudiante
            conn, cursor = get_db_cursor()
            cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (current_user['id'],))
            estudiante_actual = cursor.fetchone()
            cursor.close()
            conn.close()
            if not estudiante_actual or estudiante_actual['id_estudiante'] != id_estudiante:
                return jsonify({"error": "No tienes permisos para ver el progreso de otro estudiante"}), 403
        
        evaluacion = calcular_puntuacion_estudiante(id_estudiante)
        patrones = detectar_patrones_error(id_estudiante, 10)
        recomendacion = recomendar_nivel_siguiente(id_estudiante)
        
        conn, cursor = get_db_cursor()
        cursor.execute("""SELECT nivel_asignado, puntaje, fecha 
                         FROM diagnostico 
                         WHERE id_estudiante = %s 
                         ORDER BY fecha DESC LIMIT 1""", (id_estudiante,))
        diagnostico = cursor.fetchone()
        cursor.close()
        conn.close()
        
        diagnostico_info = {
            'nivel_inicial': diagnostico['nivel_asignado'],
            'puntaje_inicial': diagnostico['puntaje'],
            'fecha': str(diagnostico['fecha'])
        } if diagnostico else None
        
        return jsonify({
            "id_estudiante": id_estudiante,
            "evaluacion": evaluacion,
            "diagnostico_inicial": diagnostico_info,
            "patrones_error": patrones,
            "recomendacion_siguiente": recomendacion
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)