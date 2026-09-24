from datetime import timedelta
from hashlib import sha256
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask import send_from_directory
from config import get_db_connection
from services.tutoring import (
    calcular_puntuacion_estudiante, 
    detectar_patrones_error, 
    recomendar_nivel_siguiente,
    generar_feedback_personalizado,
    calcular_nivel_lector_diagnostico,
    normalizar_texto,
    obtener_nivel_actual,
    get_db_cursor,
    actualizar_nivel_estudiante,
    sincronizar_progreso_estudiante,
    comparar_niveles,
    crear_plan_reforzamiento
)
import bcrypt
import os

app = Flask(__name__)

# Configuración JWT
app.config['JWT_SECRET_KEY'] = sha256(os.environ['JWT_SECRET_KEY'].encode('utf-8')).hexdigest()
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
jwt = JWTManager(app)

ROL_ESTUDIANTE = 1
ROL_DOCENTE = 2
ROL_ADMIN = 3
NIVELES_LECTORES = ['literal', 'inferencial', 'crítico']

DIAGNOSTICO_INICIAL = {
    "texto": (
        "Un pequeño ratón despertó accidentalmente a un enorme león que dormía bajo un árbol. "
        "El león, furioso, atrapó al ratón entre sus garras. El ratón le rogó que lo dejara libre "
        "y prometió ayudarlo algún día. El león se rió, pero decidió soltarlo. Días después, el león "
        "cayó atrapado en una red. El ratón escuchó sus rugidos, corrió hacia él y mordió la red hasta "
        "liberarlo. Desde entonces, el león comprendió que hasta los más pequeños pueden ser de gran ayuda."
    ),
    "preguntas": [
        {
            "id": 1,
            "pregunta": "¿Quién es el personaje principal del texto?",
            "respuestas_aceptadas": ["el ratón", "ratón"]
        },
        {
            "id": 2,
            "pregunta": "¿Dónde dormía el león?",
            "respuestas_aceptadas": ["bajo un árbol", "debajo de un árbol"]
        },
        {
            "id": 3,
            "pregunta": "¿Por qué el león dejó libre al ratón?",
            "respuestas_aceptadas": [
                "porque el ratón le prometió ayudarlo",
                "porque le prometió ayudarlo"
            ]
        },
        {
            "id": 4,
            "pregunta": "¿Qué enseñanza deja la historia?",
            "respuestas_aceptadas": [
                "todos pueden ayudar sin importar su tamaño",
                "hasta los más pequeños pueden ayudar",
                "no importa el tamaño todos podemos ayudar"
            ]
        }
    ]
}


def obtener_usuario_actual():
    """Devuelve una representación consistente del usuario autenticado."""
    id_usuario = int(get_jwt_identity())
    claims = get_jwt()
    return {
        "id_usuario": id_usuario,
        "rol": int(claims.get("rol", 0)),
        "nombre": claims.get("nombre", "")
    }


def obtener_estudiante_de_usuario(cursor, id_usuario):
    cursor.execute(
        "SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s",
        (id_usuario,)
    )
    return cursor.fetchone()


def puede_acceder_estudiante(cursor, usuario, id_estudiante):
    if usuario["rol"] in (ROL_DOCENTE, ROL_ADMIN):
        return True
    if usuario["rol"] != ROL_ESTUDIANTE:
        return False
    estudiante = obtener_estudiante_de_usuario(cursor, usuario["id_usuario"])
    return bool(estudiante and estudiante["id_estudiante"] == id_estudiante)


def respuesta_diagnostico_es_correcta(respuesta, respuestas_aceptadas):
    respuesta_normalizada = normalizar_texto(respuesta)
    if not respuesta_normalizada:
        return False
    for respuesta_aceptada in respuestas_aceptadas:
        esperada = normalizar_texto(respuesta_aceptada)
        if respuesta_normalizada == esperada or esperada in respuesta_normalizada:
            return True
    return False


def evaluar_respuestas_diagnostico(respuestas):
    """Valida y califica el diagnóstico exclusivamente en el servidor."""
    if not isinstance(respuestas, list):
        raise ValueError("respuestas debe ser una lista")

    respuestas_por_id = {}
    for item in respuestas:
        if not isinstance(item, dict) or "id" not in item or "respuesta" not in item:
            raise ValueError("Cada respuesta debe incluir id y respuesta")
        try:
            pregunta_id = int(item["id"])
        except (TypeError, ValueError) as exc:
            raise ValueError("ID de pregunta inválido") from exc
        if pregunta_id in respuestas_por_id:
            raise ValueError("No se permiten preguntas duplicadas")
        respuesta = str(item["respuesta"]).strip()
        if not respuesta:
            raise ValueError("Debes responder todas las preguntas")
        respuestas_por_id[pregunta_id] = respuesta

    preguntas = DIAGNOSTICO_INICIAL["preguntas"]
    ids_esperados = {pregunta["id"] for pregunta in preguntas}
    if set(respuestas_por_id) != ids_esperados:
        raise ValueError("Debes responder exactamente las preguntas del diagnóstico")

    return [
        respuesta_diagnostico_es_correcta(
            respuestas_por_id[pregunta["id"]],
            pregunta["respuestas_aceptadas"]
        )
        for pregunta in preguntas
    ]

def estudiante_tiene_diagnostico(id_usuario):
    conn, cursor = get_db_cursor()
    try:
        cursor.execute("""
            SELECT 1
            FROM estudiantes e
            JOIN diagnostico d ON d.id_estudiante = e.id_estudiante
            WHERE e.id_usuario = %s
            LIMIT 1
        """, (id_usuario,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()

@app.route("/")
def index():
    return send_from_directory("frontend/login", "login.html")

@app.route("/styles.css")
def styles():
    return send_from_directory("frontend/common", "styles_general.css")

@app.route("/login.css")
def login_css():
    return send_from_directory("frontend/login", "login.css")

@app.route("/menu.css")
def menu_css():
    return send_from_directory("frontend/menu", "menu.css")

@app.route("/reading.css")
def reading_css():
    return send_from_directory("frontend/reading", "reading.css")

@app.route("/header.css")
def header_css():
    return send_from_directory("frontend/common", "header.css")

@app.route("/login.js")
def login_js():
    return send_from_directory("frontend/login", "login.js")

@app.route("/dashboard.html")
def dashboard():
    return send_from_directory("frontend/dashboard", "dashboard.html")

@app.route("/inicio")
def inicio():
    return send_from_directory("frontend/dashboard", "dashboard.html")

@app.route("/dashboard.css")
def dashboard_css():
    return send_from_directory("frontend/dashboard", "dashboard.css")

@app.route("/dashboard.js")
def dashboard_js():
    return send_from_directory("frontend/dashboard", "dashboard.js")

@app.route("/menu.html")
def menu_html():
    return send_from_directory("frontend/menu", "menu.html")

@app.route("/menu.js")
def menu_js():
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

@app.route("/progress.js")
def progress_js():
    return send_from_directory("frontend/common", "progress.js")

@app.route("/reading-icons.js")
def reading_icons_js():
    return send_from_directory("frontend/common", "reading-icons.js")

@app.route("/header.html")
def header_html():
    return send_from_directory("frontend/common", "header.html")

@app.route("/diagnostico.html")
def diagnostico_html():
    return send_from_directory("frontend/diagnostico", "diagnostico.html")

@app.route("/diagnostico.js")
def diagnostico_js():
    return send_from_directory("frontend/diagnostico", "diagnostico.js")

@app.route("/diagnostico.css")
def diagnostico_css():
    return send_from_directory("frontend/diagnostico", "diagnostico.css")

@app.route("/texto/<int:id_texto>", methods=['GET'])
@jwt_required()
def obtener_texto(id_texto):
    """Obtiene un texto específico (requiere autenticación)"""
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] == ROL_ESTUDIANTE and not estudiante_tiene_diagnostico(usuario['id_usuario']):
            return jsonify({"error": "Debes completar el diagnóstico inicial"}), 403
        if usuario['rol'] not in (ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN):
            return jsonify({"error": "No tienes permisos para consultar textos"}), 403

        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_texto, titulo, contenido, nivel FROM textos WHERE id_texto = %s", (id_texto,))
        texto = cursor.fetchone()
        
        if not texto:
            cursor.close()
            conn.close()
            return jsonify({"error": "Texto no encontrado"}), 404

        if usuario['rol'] == ROL_ESTUDIANTE:
            estudiante = obtener_estudiante_de_usuario(cursor, usuario['id_usuario'])
            if not estudiante:
                cursor.close()
                conn.close()
                return jsonify({"error": "El usuario no es estudiante"}), 403
            nivel_actual = obtener_nivel_actual(estudiante['id_estudiante'])
            niveles_permitidos = NIVELES_LECTORES[:NIVELES_LECTORES.index(nivel_actual) + 1] \
                if nivel_actual in NIVELES_LECTORES else [NIVELES_LECTORES[0]]
            if normalizar_texto(texto['nivel']) not in [normalizar_texto(n) for n in niveles_permitidos]:
                cursor.close()
                conn.close()
                return jsonify({"error": "El texto aún no está habilitado para tu nivel"}), 403

        cursor.close()
        conn.close()
        
        return jsonify(texto), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener texto: {str(e)}"}), 500

@app.route("/textos")
@jwt_required()
def obtener_textos():
    """Obtiene textos según el nivel actual o un nivel anterior permitido"""
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "Esta vista solo está disponible para estudiantes"}), 403
        id_usuario = usuario['id_usuario']

        conn, cursor = get_db_cursor()

        cursor.execute(
            "SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s",
            (id_usuario,)
        )
        estudiante = cursor.fetchone()

        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "El usuario no es estudiante"}), 400

        if not estudiante_tiene_diagnostico(id_usuario):
            cursor.close()
            conn.close()
            return jsonify({"error": "Debes completar el diagnóstico inicial"}), 403

        id_estudiante = estudiante["id_estudiante"]

        nivel_actual = obtener_nivel_actual(id_estudiante)
        nivel_solicitado = request.args.get("nivel", nivel_actual)

        niveles = NIVELES_LECTORES

        if nivel_actual not in niveles:
            nivel_actual = "literal"

        if nivel_solicitado not in niveles:
            nivel_solicitado = nivel_actual

        indice_actual = niveles.index(nivel_actual)
        niveles_permitidos = niveles[:indice_actual + 1]

        if nivel_solicitado not in niveles_permitidos:
            nivel_solicitado = nivel_actual

        cursor.execute("""
            SELECT id_texto, titulo, contenido, nivel
            FROM textos
            WHERE LOWER(TRIM(nivel)) = LOWER(TRIM(%s))
            ORDER BY id_texto DESC
        """, (nivel_solicitado,))

        textos = cursor.fetchall()
        
        # Obtener información de textos completados
        textos_con_estado = []
        for texto in textos:
            id_texto = texto["id_texto"]
            
            # Verificar si el estudiante ha respondido correctamente todas las preguntas del texto
            cursor.execute("""
                SELECT COUNT(*) as total_preguntas
                FROM preguntas
                WHERE id_texto = %s
            """, (id_texto,))
            total_preguntas = cursor.fetchone()["total_preguntas"]
            
            respuestas_correctas = 0
            if total_preguntas > 0:
                cursor.execute("""
                    SELECT COUNT(DISTINCT re.id_pregunta) as correctas
                    FROM respuestas_estudiante re
                    JOIN preguntas p ON re.id_pregunta = p.id_pregunta
                    WHERE p.id_texto = %s 
                    AND re.id_estudiante = %s 
                    AND re.es_correcta = TRUE
                """, (id_texto, id_estudiante))
                respuestas_correctas = cursor.fetchone()["correctas"]
            
            # Un texto está completado si tiene todas las respuestas correctas
            completado = total_preguntas > 0 and respuestas_correctas == total_preguntas
            
            texto_con_estado = dict(texto)
            texto_con_estado["completado"] = completado
            textos_con_estado.append(texto_con_estado)

        cursor.close()
        conn.close()

        return jsonify({
            "nivel_actual": nivel_actual,
            "nivel_mostrado": nivel_solicitado,
            "niveles_permitidos": niveles_permitidos,
            "textos": textos_con_estado
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================================
# APARTADO DE AUTENTICACIÓN
# ===========================================
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')
    # El registro público solo crea estudiantes. Los roles privilegiados deben
    # ser administrados mediante un flujo separado y autenticado.
    id_rol = ROL_ESTUDIANTE

    if not nombre or not email or not password:
        return jsonify({"error": "Nombre, email y password son requeridos"}), 400
    if len(str(password)) < 8:
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres"}), 400

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
        
        user_id = cursor.lastrowid
        if int(id_rol) == 1:
            cursor.execute(
                "INSERT INTO estudiantes (id_usuario, nivel_actual) VALUES (%s, %s)",
                (user_id, "literal")
            )
        elif int(id_rol) == 2:
            cursor.execute(
                "INSERT INTO docentes (id_usuario) VALUES (%s)",
                (user_id,)
            )
        cursor.close()
        conn.commit()
        conn.close()
        return jsonify({"message": "Usuario registrado exitosamente", "id_usuario": user_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
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
            except (TypeError, ValueError):
                password_matches = False

            if password_matches:
                access_token = create_access_token(identity=str(user['id_usuario']),additional_claims={"rol": user["id_rol"],"nombre": user["nombre"]})
                return jsonify({"access_token": access_token, "user": {"id": user['id_usuario'], "nombre": user['nombre'], "rol": user['id_rol']}}), 200

        return jsonify({"error": "Credenciales inválidas"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    usuario = obtener_usuario_actual()
    return jsonify({
        "message": f"Hola {usuario['nombre'] or usuario['id_usuario']}, tienes acceso!"
    }), 200

# ===========================================
# APARTADO DE PREGUNTAS Y RESPUESTAS
# ===========================================
@app.route('/preguntas/<int:id_texto>', methods=['GET'])
@jwt_required()
def obtener_preguntas(id_texto):
    """Obtiene todas las preguntas de un texto específico (requiere autenticación)"""
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] == ROL_ESTUDIANTE and not estudiante_tiene_diagnostico(usuario['id_usuario']):
            return jsonify({"error": "Debes completar el diagnóstico inicial"}), 403
        if usuario['rol'] not in (ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN):
            return jsonify({"error": "No tienes permisos para consultar preguntas"}), 403

        if id_texto <= 0:
            return jsonify({"error": "ID de texto inválido"}), 400
        
        conn, cursor = get_db_cursor()
        
        # Verificar que el texto existe
        cursor.execute("SELECT id_texto, nivel FROM textos WHERE id_texto = %s", (id_texto,))
        texto = cursor.fetchone()
        if not texto:
            cursor.close()
            conn.close()
            return jsonify({"error": "Texto no encontrado"}), 404

        if usuario['rol'] == ROL_ESTUDIANTE:
            estudiante = obtener_estudiante_de_usuario(cursor, usuario['id_usuario'])
            if not estudiante:
                cursor.close()
                conn.close()
                return jsonify({"error": "El usuario no es estudiante"}), 403
            nivel_actual = obtener_nivel_actual(estudiante['id_estudiante'])
            indice_actual = NIVELES_LECTORES.index(nivel_actual) if nivel_actual in NIVELES_LECTORES else 0
            niveles_permitidos = NIVELES_LECTORES[:indice_actual + 1]
            if normalizar_texto(texto['nivel']) not in [normalizar_texto(n) for n in niveles_permitidos]:
                cursor.close()
                conn.close()
                return jsonify({"error": "Las preguntas aún no están habilitadas para tu nivel"}), 403
        
        cursor.execute("""
            SELECT p.id_pregunta, p.id_texto, p.enunciado, p.tipo,
                   p.tipo_respuesta, p.orden,
                   o.id_opcion, o.texto_opcion
            FROM preguntas p
            LEFT JOIN opciones_pregunta o ON o.id_pregunta = p.id_pregunta
            WHERE p.id_texto = %s
            ORDER BY p.orden, p.id_pregunta, o.id_opcion
        """, (id_texto,))
        filas = cursor.fetchall()
        preguntas_por_id = {}
        for fila in filas:
            id_pregunta = fila['id_pregunta']
            if id_pregunta not in preguntas_por_id:
                preguntas_por_id[id_pregunta] = {
                    "id_pregunta": id_pregunta,
                    "id_texto": fila['id_texto'],
                    "enunciado": fila['enunciado'],
                    "tipo": fila['tipo'],
                    "tipo_respuesta": fila['tipo_respuesta'],
                    "orden": fila['orden']
                }
                if fila['tipo_respuesta'] == 'opcion':
                    preguntas_por_id[id_pregunta]['opciones'] = []

            if fila['tipo_respuesta'] == 'opcion' and fila['id_opcion'] is not None:
                preguntas_por_id[id_pregunta]['opciones'].append({
                    "id_opcion": fila['id_opcion'],
                    "texto_opcion": fila['texto_opcion']
                })

        preguntas = list(preguntas_por_id.values())
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
        usuario = obtener_usuario_actual()
        cursor.execute("""
            SELECT p.id_pregunta, p.id_texto, p.enunciado, p.tipo, t.nivel
            FROM preguntas p
            JOIN textos t ON t.id_texto = p.id_texto
            WHERE p.id_pregunta = %s
        """, (id_pregunta,))
        pregunta = cursor.fetchone()
        
        if not pregunta:
            cursor.close()
            conn.close()
            return jsonify({"error": "Pregunta no encontrada"}), 404

        if usuario['rol'] == ROL_ESTUDIANTE:
            if not estudiante_tiene_diagnostico(usuario['id_usuario']):
                cursor.close()
                conn.close()
                return jsonify({"error": "Debes completar el diagnóstico inicial"}), 403
            estudiante = obtener_estudiante_de_usuario(cursor, usuario['id_usuario'])
            nivel_actual = obtener_nivel_actual(estudiante['id_estudiante']) if estudiante else 'literal'
            indice_actual = NIVELES_LECTORES.index(nivel_actual) if nivel_actual in NIVELES_LECTORES else 0
            niveles_permitidos = NIVELES_LECTORES[:indice_actual + 1]
            if normalizar_texto(pregunta['nivel']) not in [normalizar_texto(n) for n in niveles_permitidos]:
                cursor.close()
                conn.close()
                return jsonify({"error": "La pregunta aún no está habilitada para tu nivel"}), 403
        elif usuario['rol'] not in (ROL_DOCENTE, ROL_ADMIN):
            cursor.close()
            conn.close()
            return jsonify({"error": "No tienes permisos para consultar esta pregunta"}), 403

        pregunta.pop('nivel', None)
        cursor.close()
        conn.close()
        
        return jsonify(pregunta), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener pregunta: {str(e)}"}), 500

@app.route('/respuesta-correcta/<int:id_pregunta>', methods=['GET'])
@jwt_required()
def obtener_respuesta_correcta(id_pregunta):
    """Obtiene la respuesta correcta de una pregunta (solo para docentes/admin)"""
    try:
        usuario = obtener_usuario_actual()
        id_rol = usuario['rol']
        
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
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "Solo los estudiantes pueden guardar respuestas"}), 403
        id_usuario = usuario['id_usuario']
        data = request.get_json(silent=True) or {}
        
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
        
        id_estudiante = estudiante['id_estudiante']
        
        try:
            tiempo_respuesta = max(0, min(int(tiempo_respuesta), 3600))
        except (TypeError, ValueError):
            cursor.close()
            conn.close()
            return jsonify({"error": "tiempo_respuesta inválido"}), 400

        # Obtener la pregunta y su respuesta correcta.
        cursor.execute("""
            SELECT p.tipo, t.nivel, rc.respuesta
            FROM preguntas p
            JOIN textos t ON t.id_texto = p.id_texto
            LEFT JOIN respuestas_correctas rc ON rc.id_pregunta = p.id_pregunta
            WHERE p.id_pregunta = %s
        """, (id_pregunta,))
        pregunta = cursor.fetchone()
        if not pregunta:
            cursor.close()
            conn.close()
            return jsonify({"error": "Pregunta no encontrada"}), 404

        nivel_actual = obtener_nivel_actual(id_estudiante)
        indice_actual = NIVELES_LECTORES.index(nivel_actual) if nivel_actual in NIVELES_LECTORES else 0
        if normalizar_texto(pregunta['nivel']) not in [normalizar_texto(n) for n in NIVELES_LECTORES[:indice_actual + 1]]:
            cursor.close()
            conn.close()
            return jsonify({"error": "La actividad aún no está habilitada para tu nivel"}), 403
        
        es_correcta = False
        if pregunta['respuesta']:
            es_correcta = normalizar_texto(respuesta) == normalizar_texto(
                pregunta['respuesta']
            )
        
        # Guardar la respuesta del estudiante
        cursor.execute("""INSERT INTO respuestas_estudiante 
                         (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta, fecha) 
                         VALUES (%s, %s, %s, %s, %s, CURDATE())""",
                      (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta))
        respuesta_id = cursor.lastrowid

        feedback = generar_feedback_personalizado(
            id_pregunta,
            es_correcta,
            respuesta,
            pregunta['respuesta'] or '',
            pregunta['tipo']
        )
        mensaje_feedback = " ".join(
            parte for parte in [feedback.get('mensaje'), feedback.get('explicacion'), feedback.get('pista')]
            if parte
        )
        cursor.execute("""
            INSERT INTO retroalimentacion (id_respuesta_est, mensaje, tipo)
            VALUES (%s, %s, %s)
        """, (
            respuesta_id,
            mensaje_feedback,
            'correcta' if es_correcta else f"refuerzo_{pregunta['tipo']}"
        ))
        conn.commit()
        cursor.close()
        conn.close()

        sincronizar_progreso_estudiante(id_estudiante)
        
        return jsonify({"message": "Respuesta guardada exitosamente", 
                       "id_respuesta_est": respuesta_id, 
                       "es_correcta": es_correcta,
                       "feedback": feedback}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/respuestas-estudiante/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_respuestas_estudiante(id_estudiante):
    """Obtiene todas las respuestas de un estudiante (requiere ser el estudiante o docente/admin)"""
    try:
        usuario = obtener_usuario_actual()
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        # Obtener id_estudiante del usuario actual
        conn = get_db_connection()
        cursor = conn.cursor()
        if not puede_acceder_estudiante(cursor, usuario, id_estudiante):
            cursor.close()
            conn.close()
            return jsonify({"error": "No tienes permisos para acceder a esta información"}), 403
        
        cursor.execute("""
            SELECT re.id_respuesta_est, re.id_estudiante, re.id_pregunta,
                   re.respuesta, re.es_correcta, re.tiempo_respuesta, re.fecha,
                   rf.mensaje AS feedback_mensaje, rf.tipo AS feedback_tipo
            FROM respuestas_estudiante re
            LEFT JOIN retroalimentacion rf ON rf.id_respuesta_est = re.id_respuesta_est
            WHERE re.id_estudiante = %s
            ORDER BY re.id_respuesta_est DESC
        """, (id_estudiante,))
        respuestas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not respuestas:
            return jsonify([]), 200
        
        resultado = [{
            "id_respuesta_est": r['id_respuesta_est'],
            "id_estudiante": r['id_estudiante'],
            "id_pregunta": r['id_pregunta'],
            "respuesta": r['respuesta'],
            "es_correcta": bool(r['es_correcta']),
            "tiempo_respuesta": r['tiempo_respuesta'],
            "fecha": str(r['fecha']),
            "feedback": {
                "mensaje": r['feedback_mensaje'],
                "tipo": r['feedback_tipo']
            } if r['feedback_mensaje'] else None
        } for r in respuestas]
        
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener respuestas: {str(e)}"}), 500

@app.route('/verificar-respuesta/<int:id_pregunta>', methods=['POST'])
@jwt_required()
def verificar_respuesta(id_pregunta):
    """Verifica si una respuesta es correcta sin guardarla (requiere autenticación)"""
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "Solo los estudiantes pueden verificar respuestas"}), 403
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

@app.route('/respuestas-texto/<int:id_texto>', methods=['GET'])
@jwt_required()
def obtener_respuestas_por_texto(id_texto):
    """Obtiene las respuestas más recientes del estudiante para un texto específico"""
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "Solo los estudiantes pueden consultar sus respuestas"}), 403
        id_usuario = usuario['id_usuario']

        conn, cursor = get_db_cursor()

        # Obtener id_estudiante
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()

        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Estudiante no encontrado"}), 404

        id_estudiante = estudiante['id_estudiante']

        # Obtener las respuestas más recientes para cada pregunta de este texto
        query = """
            SELECT re.id_respuesta_est, re.id_pregunta, re.respuesta, re.es_correcta, p.enunciado, re.fecha
            FROM respuestas_estudiante re
            JOIN preguntas p ON re.id_pregunta = p.id_pregunta
            WHERE re.id_estudiante = %s AND p.id_texto = %s
            AND re.id_respuesta_est = (
                SELECT MAX(id_respuesta_est)
                FROM respuestas_estudiante r2
                WHERE r2.id_estudiante = re.id_estudiante
                AND r2.id_pregunta = re.id_pregunta
            )
            ORDER BY re.id_pregunta
        """

        cursor.execute(query, (id_estudiante, id_texto))
        respuestas = cursor.fetchall()
        cursor.close()
        conn.close()

        if not respuestas:
            return jsonify([]), 200

        # Obtener solo la más reciente por pregunta
        resultado = {}
        todas_correctas = True

        for r in respuestas:
            id_pregunta = r['id_pregunta']
            if id_pregunta not in resultado:  # Primera (más reciente) para esta pregunta
                resultado[id_pregunta] = {
                    "respuesta": r['respuesta'],
                    "es_correcta": bool(r['es_correcta']),
                    "enunciado": r['enunciado']
                }
                if not r['es_correcta']:
                    todas_correctas = False

        return jsonify({
            "respuestas": resultado,
            "todas_correctas": todas_correctas
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================================
# MÓDULO: TUTOR INTELIGENTE
# ===========================================
@app.route('/evaluacion/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_evaluacion(id_estudiante):
    """Obtiene la evaluación general del estudiante"""
    try:
        usuario = obtener_usuario_actual()
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        conn, cursor = get_db_cursor()
        autorizado = puede_acceder_estudiante(cursor, usuario, id_estudiante)
        cursor.close()
        conn.close()
        if not autorizado:
            return jsonify({"error": "No tienes permisos para ver esta evaluación"}), 403
        
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
        usuario = obtener_usuario_actual()
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        conn, cursor = get_db_cursor()
        autorizado = puede_acceder_estudiante(cursor, usuario, id_estudiante)
        cursor.close()
        conn.close()
        if not autorizado:
            return jsonify({"error": "No tienes permisos para ver estos patrones"}), 403
        
        patrones = detectar_patrones_error(id_estudiante)
        return jsonify(patrones), 200
    except Exception as e:
        return jsonify({"error": f"Error al detectar patrones: {str(e)}"}), 500

@app.route('/recomendacion-nivel/<int:id_estudiante>', methods=['GET'])
@jwt_required()
def obtener_recomendacion(id_estudiante):
    """Obtiene recomendación de nivel siguiente"""
    try:
        usuario = obtener_usuario_actual()
        
        if id_estudiante <= 0:
            return jsonify({"error": "ID de estudiante inválido"}), 400
        
        conn, cursor = get_db_cursor()
        autorizado = puede_acceder_estudiante(cursor, usuario, id_estudiante)
        cursor.close()
        conn.close()
        if not autorizado:
            return jsonify({"error": "No tienes permisos para ver esta recomendación"}), 403
        
        recomendacion = recomendar_nivel_siguiente(id_estudiante)
        # Consultar una recomendación no modifica el estado del estudiante.
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
    conn = None
    cursor = None
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "Solo los estudiantes pueden responder actividades"}), 403
        id_usuario = usuario['id_usuario']
        data = request.get_json(silent=True) or {}
        
        id_pregunta = data.get('id_pregunta')
        respuesta = data.get('respuesta')
        id_opcion = data.get('id_opcion')
        tiempo_respuesta = data.get('tiempo_respuesta', 0)
        
        if not id_pregunta or (respuesta is None and not id_opcion):
            return jsonify({"error": "id_pregunta y respuesta son requeridos"}), 400
        try:
            tiempo_respuesta = max(0, min(int(tiempo_respuesta), 3600))
        except (TypeError, ValueError):
            return jsonify({"error": "tiempo_respuesta inválido"}), 400
        
        conn, cursor = get_db_cursor()
        
        # Obtener info del estudiante y pregunta
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()
        
        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no es estudiante"}), 400
        
        id_estudiante = estudiante['id_estudiante']
        
        # Obtener el tipo de pregunta y validar su respuesta contra la BD.
        cursor.execute("""
            SELECT p.tipo, p.tipo_respuesta, p.id_texto, t.nivel, rc.respuesta
            FROM preguntas p
            JOIN textos t ON t.id_texto = p.id_texto
            LEFT JOIN respuestas_correctas rc ON p.id_pregunta = rc.id_pregunta 
            WHERE p.id_pregunta = %s
        """, (id_pregunta,))
        
        pregunta_info = cursor.fetchone()
        if not pregunta_info:
            cursor.close()
            conn.close()
            return jsonify({"error": "Pregunta no encontrada"}), 404
        
        tipo_pregunta = pregunta_info['tipo']
        tipo_respuesta = pregunta_info['tipo_respuesta']
        respuesta_correcta = pregunta_info['respuesta']

        nivel_actual = obtener_nivel_actual(id_estudiante)
        indice_actual = NIVELES_LECTORES.index(nivel_actual) if nivel_actual in NIVELES_LECTORES else 0
        niveles_permitidos = NIVELES_LECTORES[:indice_actual + 1]
        if normalizar_texto(pregunta_info['nivel']) not in [normalizar_texto(n) for n in niveles_permitidos]:
            cursor.close()
            conn.close()
            return jsonify({"error": "La actividad aún no está habilitada para tu nivel"}), 403

        if tipo_respuesta == 'opcion':
            if not id_opcion:
                cursor.close()
                conn.close()
                return jsonify({"error": "Debes seleccionar una opción"}), 400

            cursor.execute("""
                SELECT texto_opcion, es_correcta
                FROM opciones_pregunta
                WHERE id_opcion = %s AND id_pregunta = %s
            """, (id_opcion, id_pregunta))
            opcion = cursor.fetchone()
            if not opcion:
                cursor.close()
                conn.close()
                return jsonify({"error": "La opción seleccionada no pertenece a la pregunta"}), 400

            respuesta = opcion['texto_opcion']
            cursor.execute("""
                SELECT texto_opcion
                FROM opciones_pregunta
                WHERE id_pregunta = %s AND es_correcta = TRUE
                LIMIT 1
            """, (id_pregunta,))
            opcion_correcta = cursor.fetchone()
            respuesta_correcta = opcion_correcta['texto_opcion'] if opcion_correcta else ''
            es_correcta = bool(opcion['es_correcta'])
        else:
            es_correcta = bool(
                respuesta_correcta and respuesta and
                normalizar_texto(respuesta) == normalizar_texto(respuesta_correcta)
            )
        
        # Guardar respuesta
        cursor.execute("""INSERT INTO respuestas_estudiante
                         (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta, fecha)
                         VALUES (%s, %s, %s, %s, %s, NOW())""",
                      (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta))
        respuesta_id = cursor.lastrowid
        
        # Generar feedback
        feedback = generar_feedback_personalizado(
            id_pregunta, 
            es_correcta, 
            respuesta, 
            respuesta_correcta or '',
            tipo_pregunta
        )

        mensaje_feedback = " ".join(
            parte for parte in [
                feedback.get('mensaje', ''),
                feedback.get('explicacion', ''),
                feedback.get('pista', '')
            ] if parte
        )
        cursor.execute("""
            INSERT INTO retroalimentacion (id_respuesta_est, mensaje, tipo)
            VALUES (%s, %s, %s)
        """, (
            respuesta_id,
            mensaje_feedback,
            'correcta' if es_correcta else f'refuerzo_{tipo_pregunta}'
        ))
        conn.commit()
        
        # Obtener recomendación (si hay suficientes respuestas)
        cursor.execute("SELECT COUNT(*) FROM respuestas_estudiante WHERE id_estudiante = %s", (id_estudiante,))
        resultado_count = cursor.fetchone()
        total_respuestas = resultado_count['COUNT(*)'] if isinstance(resultado_count, dict) else resultado_count[0]
        
        recomendacion = None
        cursor.close()
        cursor = None
        conn.close()
        conn = None
        
        resultado = {
            "id_respuesta_est": respuesta_id,
            "es_correcta": es_correcta,
            "feedback": feedback,
            "recomendacion": recomendacion,
            "total_respuestas": total_respuestas
        }

        # Incluir el progreso consolidado y mantener sincronizada su persistencia.
        if total_respuestas > 0:
            progreso = sincronizar_progreso_estudiante(id_estudiante)
            evaluacion = progreso.get('evaluacion', calcular_puntuacion_estudiante(id_estudiante))
            resultado["progreso_actualizado"] = {
                "total_respuestas": evaluacion.get('total_respuestas', 0),
                "respuestas_correctas": evaluacion.get('respuestas_correctas', 0),
                "porcentaje_acierto": evaluacion.get('porcentaje_acierto', 0)
            }

        return jsonify(resultado), 201
    except Exception as e:
        if conn:
            conn.rollback()
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/feedback-sesion', methods=['POST'])
@jwt_required()
def feedback_sesion():
    """Genera un resumen completo de la sesión de lectura para el estudiante."""
    try:
        data = request.get_json() or {}
        id_texto = data.get('id_texto')

        if not id_texto:
            return jsonify({"error": "id_texto es requerido"}), 400

        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "Solo los estudiantes pueden cerrar una sesión de lectura"}), 403
        id_usuario = usuario['id_usuario']
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()

        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no es estudiante"}), 400

        id_estudiante = estudiante['id_estudiante']

        query = """
            SELECT re.id_pregunta, re.respuesta, re.es_correcta, p.enunciado, p.tipo,
                   COALESCE(rc.respuesta, op.texto_opcion) AS respuesta_correcta
            FROM respuestas_estudiante re
            JOIN preguntas p ON re.id_pregunta = p.id_pregunta
            LEFT JOIN respuestas_correctas rc ON p.id_pregunta = rc.id_pregunta
            LEFT JOIN opciones_pregunta op
                ON p.id_pregunta = op.id_pregunta AND op.es_correcta = TRUE
            WHERE re.id_estudiante = %s AND p.id_texto = %s
              AND re.id_respuesta_est = (
                  SELECT MAX(re2.id_respuesta_est)
                  FROM respuestas_estudiante re2
                  WHERE re2.id_pregunta = re.id_pregunta
                    AND re2.id_estudiante = re.id_estudiante
              )
        """
        cursor.execute(query, (id_estudiante, id_texto))
        respuestas = cursor.fetchall()

        preguntas_respondidas = len(respuestas)
        respuestas_correctas = sum(1 for r in respuestas if r['es_correcta'])
        porcentaje = round((respuestas_correctas / preguntas_respondidas * 100), 2) if preguntas_respondidas > 0 else 0

        errores_detectados = []
        for r in respuestas:
            if not r['es_correcta']:
                errores_detectados.append({
                    'pregunta_id': r['id_pregunta'],
                    'nivel': r['tipo'],
                    'respuesta_usuario': r['respuesta'],
                    'respuesta_correcta': r['respuesta_correcta']
                })

        nivel_actual = obtener_nivel_actual(id_estudiante)
        recomendacion = recomendar_nivel_siguiente(id_estudiante)
        if not recomendacion or 'error' in recomendacion:
            recomendacion = {
                'nuevo_nivel': nivel_actual,
                'recomendacion': 'mantener',
                'razon': 'Sigue practicando para mejorar tu comprensión.',
                'confianza': 'media'
            }
        nuevo_nivel = recomendacion.get('nuevo_nivel', nivel_actual)
        estado_nivel = comparar_niveles(nivel_actual, nuevo_nivel)

        if recomendacion and recomendacion.get('recomendacion') in ['siguiente', 'anterior']:
            actualizar_nivel_estudiante(id_estudiante, nuevo_nivel)

        patrones_error = detectar_patrones_error(id_estudiante, limite_respuestas=20)
        recomendaciones_practica = patrones_error.get('recomendaciones', [])
        if not recomendaciones_practica and recomendacion.get('razon'):
            recomendaciones_practica = [recomendacion.get('razon')]

        plan_reforzamiento = crear_plan_reforzamiento(id_estudiante)

        cursor.close()
        conn.close()

        sincronizar_progreso_estudiante(id_estudiante)

        return jsonify({
            'puntaje': {
                'respondidas': preguntas_respondidas,
                'correctas': respuestas_correctas,
                'porcentaje': porcentaje
            },
            'nivel_actual': nivel_actual,
            'nuevo_nivel': nuevo_nivel,
            'estado_nivel': estado_nivel,
            'mensaje_tutor': recomendacion.get('razon', 'Continúa practicando según tu desempeño.'),
            'errores_detectados': errores_detectados if respuestas_correctas < preguntas_respondidas else [],
            'patrones_error': patrones_error,
            'recomendacion_practica': recomendaciones_practica,
            'recomendacion_accion': recomendacion.get('recomendacion', 'mantener'),
            'plan_reforzamiento': plan_reforzamiento
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/diagnostico-preguntas', methods=['GET'])
@jwt_required()
def obtener_diagnostico_preguntas():
    """Entrega el contenido diagnóstico sin exponer las respuestas correctas."""
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "El diagnóstico solo está disponible para estudiantes"}), 403
        if estudiante_tiene_diagnostico(usuario['id_usuario']):
            return jsonify({"error": "El diagnóstico inicial ya fue completado"}), 409
        return jsonify({
            "texto": DIAGNOSTICO_INICIAL["texto"],
            "preguntas": [
                {"id": pregunta["id"], "pregunta": pregunta["pregunta"]}
                for pregunta in DIAGNOSTICO_INICIAL["preguntas"]
            ]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/diagnostico-inicial', methods=['POST'])
@jwt_required()
def realizar_diagnostico():
    """
    Realiza diagnóstico inicial del estudiante
    Body: {"respuestas": [{"id": 1, "respuesta": "..."}, ...]}
    Retorna el nivel inicial asignado
    """
    conn = None
    cursor = None
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "El diagnóstico solo está disponible para estudiantes"}), 403
        id_usuario = usuario['id_usuario']
        data = request.get_json(silent=True) or {}

        try:
            respuestas_calificadas = evaluar_respuestas_diagnostico(data.get('respuestas'))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        
        # Obtener estudiante
        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()
        
        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no es estudiante"}), 400
        
        id_estudiante = estudiante['id_estudiante']

        cursor.execute(
            "SELECT 1 FROM diagnostico WHERE id_estudiante = %s LIMIT 1",
            (id_estudiante,)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "El diagnóstico inicial ya fue completado"}), 409
        
        # Calcular nivel
        resultado_diagnostico = calcular_nivel_lector_diagnostico(respuestas_calificadas)
        nivel_asignado = resultado_diagnostico['nivel']
        
        # Guardar en tabla diagnostico
        cursor.execute("""INSERT INTO diagnostico 
                         (id_estudiante, puntaje, nivel_asignado, fecha) 
                         VALUES (%s, %s, %s, NOW())""",
                      (id_estudiante, resultado_diagnostico['porcentaje'], nivel_asignado))
        cursor.execute(
            "UPDATE estudiantes SET nivel_actual = %s WHERE id_estudiante = %s",
            (nivel_asignado, id_estudiante)
        )
        cursor.execute("""
            INSERT INTO progreso (id_estudiante, nivel_actual, porcentaje_avance)
            VALUES (%s, %s, 0)
            ON DUPLICATE KEY UPDATE nivel_actual = VALUES(nivel_actual), porcentaje_avance = 0
        """, (id_estudiante, nivel_asignado))

        conn.commit()
        cursor.close()
        cursor = None
        conn.close()
        conn = None
        
        return jsonify({
            "diagnostico_completado": True,
            "nivel_inicial": nivel_asignado,
            "detalle": resultado_diagnostico,
            "mensaje": resultado_diagnostico['razon']
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/diagnostico-estado', methods=['GET'])
@jwt_required()
def diagnostico_estado():
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "El diagnóstico solo está disponible para estudiantes"}), 403
        id_usuario = usuario['id_usuario']

        conn, cursor = get_db_cursor()
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()

        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no es estudiante"}), 400

        id_estudiante = estudiante['id_estudiante']

        cursor.execute("""
            SELECT id_diagnostico, nivel_asignado, puntaje, fecha
            FROM diagnostico
            WHERE id_estudiante = %s
            ORDER BY fecha DESC
            LIMIT 1
        """, (id_estudiante,))

        diagnostico = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "tiene_diagnostico": diagnostico is not None,
            "diagnostico": diagnostico
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/progreso-estudiante', methods=['GET'])
@jwt_required()
def obtener_progreso_estudiante():
    """Obtiene progreso simplificado del estudiante para sesiones de lectura"""
    try:
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "El progreso solo está disponible para estudiantes"}), 403
        id_usuario = usuario['id_usuario']
        conn, cursor = get_db_cursor()

        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s", (id_usuario,))
        estudiante = cursor.fetchone()

        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "El usuario no es estudiante"}), 400

        id_estudiante = estudiante['id_estudiante']

        # Obtener estadísticas de desempeño
        evaluacion = calcular_puntuacion_estudiante(id_estudiante)

        # Obtener nivel actual
        cursor.execute("""
            SELECT nivel_actual FROM progreso WHERE id_estudiante = %s LIMIT 1
        """, (id_estudiante,))
        progreso = cursor.fetchone()

        if not progreso:
            cursor.execute("SELECT nivel_asignado FROM diagnostico WHERE id_estudiante = %s ORDER BY fecha DESC LIMIT 1", (id_estudiante,))
            diagnostico = cursor.fetchone()
            nivel_actual = diagnostico['nivel_asignado'] if diagnostico else 'literal'
        else:
            nivel_actual = progreso['nivel_actual']

        cursor.close()
        conn.close()

        return jsonify({
            "nivel_actual": nivel_actual,
            "total_respuestas_historial": evaluacion.get('total_respuestas', 0),
            "respuestas_correctas_historial": evaluacion.get('respuestas_correctas', 0),
            "porcentaje_acierto_general": evaluacion.get('porcentaje_acierto', 0),
            "tendencia": evaluacion.get('tendencia', 'sin_datos'),
            "por_nivel": evaluacion.get('por_nivel', {})
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/progreso', methods=['GET'])
@jwt_required()
def obtener_progreso():
    """Obtiene resumen del progreso del estudiante (usuario logeado)"""
    try:
        # Obtener id_usuario desde el JWT (es string → convertir a int)
        usuario = obtener_usuario_actual()
        if usuario['rol'] != ROL_ESTUDIANTE:
            return jsonify({"error": "El progreso solo está disponible para estudiantes"}), 403
        id_usuario = usuario['id_usuario']

        # Obtener id_estudiante desde la BD
        conn, cursor = get_db_cursor()
        cursor.execute(
            "SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s",
            (id_usuario,)
        )
        estudiante = cursor.fetchone()

        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "El usuario no es estudiante"}), 400

        id_estudiante = estudiante['id_estudiante']

        # 🔹 Calcular datos del sistema inteligente
        evaluacion = calcular_puntuacion_estudiante(id_estudiante)
        patrones = detectar_patrones_error(id_estudiante, 10)
        recomendacion = recomendar_nivel_siguiente(id_estudiante)
        nivel_actual = obtener_nivel_actual(id_estudiante)

        # 🔹 Obtener diagnóstico inicial
        cursor.execute("""
            SELECT nivel_asignado, puntaje, fecha
            FROM diagnostico
            WHERE id_estudiante = %s
            ORDER BY fecha DESC
            LIMIT 1
        """, (id_estudiante,))
        diagnostico = cursor.fetchone()

        cursor.close()
        conn.close()

        diagnostico_info = {
            "nivel_inicial": diagnostico['nivel_asignado'],
            "puntaje_inicial": diagnostico['puntaje'],
            "fecha": str(diagnostico['fecha'])
        } if diagnostico else None

        return jsonify({
            "id_estudiante": id_estudiante,
            "nivel_actual": nivel_actual,
            "evaluacion": evaluacion,
            "diagnostico_inicial": diagnostico_info,
            "patrones_error": patrones,
            "recomendacion_siguiente": recomendacion
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estudiante/dashboard', methods=['GET'])
@jwt_required()
def obtener_dashboard_estudiante():
    """Obtiene los datos agregados del dashboard del estudiante autenticado."""
    try:
        claims = get_jwt()
        if claims.get('rol') != 1:
            return jsonify({"error": "El dashboard solo está disponible para estudiantes"}), 403

        id_usuario = int(get_jwt_identity())
        conn, cursor = get_db_cursor()

        cursor.execute(
            "SELECT id_estudiante, nombre FROM usuarios u "
            "JOIN estudiantes e ON e.id_usuario = u.id_usuario "
            "WHERE u.id_usuario = %s",
            (id_usuario,)
        )
        estudiante = cursor.fetchone()

        if not estudiante:
            cursor.close()
            conn.close()
            return jsonify({"error": "El usuario no es estudiante"}), 403

        if not estudiante_tiene_diagnostico(id_usuario):
            cursor.close()
            conn.close()
            return jsonify({
                "error": "Debes completar el diagnóstico inicial",
                "requiere_diagnostico": True
            }), 403

        id_estudiante = estudiante['id_estudiante']
        evaluacion = calcular_puntuacion_estudiante(id_estudiante)
        nivel_actual = obtener_nivel_actual(id_estudiante)

        cursor.execute("""
            SELECT t.id_texto, t.titulo, t.nivel, COUNT(DISTINCT p.id_pregunta) AS total_preguntas
            FROM textos t
            LEFT JOIN preguntas p ON p.id_texto = t.id_texto
            GROUP BY t.id_texto, t.titulo, t.nivel
            ORDER BY t.id_texto
        """)
        textos = cursor.fetchall()

        cursor.execute("""
            SELECT p.id_texto, re.id_pregunta, re.es_correcta, re.fecha, re.id_respuesta_est
            FROM respuestas_estudiante re
            JOIN preguntas p ON p.id_pregunta = re.id_pregunta
            WHERE re.id_estudiante = %s
            ORDER BY re.id_respuesta_est DESC
        """, (id_estudiante,))
        respuestas = cursor.fetchall()

        cursor.execute("""
            SELECT nivel_asignado, puntaje, fecha
            FROM diagnostico
            WHERE id_estudiante = %s
            ORDER BY fecha DESC, id_diagnostico DESC
            LIMIT 1
        """, (id_estudiante,))
        diagnostico = cursor.fetchone()

        cursor.close()
        conn.close()

        respuestas_por_texto = {}
        dias_estudio = set()
        for respuesta in respuestas:
            id_texto = respuesta['id_texto']
            respuestas_por_texto.setdefault(id_texto, []).append(respuesta)
            if respuesta['fecha']:
                dias_estudio.add(str(respuesta['fecha']))

        estado_textos = {}
        for texto in textos:
            id_texto = texto['id_texto']
            respuestas_texto = respuestas_por_texto.get(id_texto, [])
            respuestas_recientes = {}
            correctas_historicas = set()

            for respuesta in respuestas_texto:
                if respuesta['es_correcta']:
                    correctas_historicas.add(respuesta['id_pregunta'])
                respuestas_recientes.setdefault(respuesta['id_pregunta'], respuesta)

            total_preguntas = int(texto['total_preguntas'] or 0)
            correctas_recientes = sum(
                1 for respuesta in respuestas_recientes.values() if respuesta['es_correcta']
            )
            realizadas = len(respuestas_recientes)
            porcentaje = round((correctas_recientes / realizadas) * 100, 2) if realizadas else 0
            completada = total_preguntas > 0 and len(correctas_historicas) == total_preguntas

            estado_textos[id_texto] = {
                "titulo": texto['titulo'],
                "nivel": texto['nivel'],
                "completada": completada,
                "porcentaje": porcentaje,
                "fecha": str(respuestas_texto[0]['fecha']) if respuestas_texto else None
            }

        lecturas_completadas = sum(1 for texto in estado_textos.values() if texto['completada'])
        actividad_reciente = [
            {
                "id_texto": id_texto,
                "titulo": estado['titulo'],
                "nivel": estado['nivel'],
                "fecha": estado['fecha'],
                "porcentaje": estado['porcentaje']
            }
            for id_texto, estado in sorted(
                estado_textos.items(),
                key=lambda item: item[1]['fecha'] or '',
                reverse=True
            )
            if estado['fecha']
        ][:3]

        siguiente = next(
            (
                {"id_texto": texto['id_texto'], "titulo": texto['titulo'], "nivel": texto['nivel']}
                for texto in textos
                if (texto['nivel'] or '').strip().lower() == nivel_actual
                and not estado_textos[texto['id_texto']]['completada']
            ),
            None
        )
        if siguiente is None:
            siguiente = next(
                (
                    {"id_texto": texto['id_texto'], "titulo": texto['titulo'], "nivel": texto['nivel']}
                    for texto in textos
                    if (texto['nivel'] or '').strip().lower() == nivel_actual
                ),
                None
            )

        recomendacion = recomendar_nivel_siguiente(id_estudiante) if diagnostico else None

        racha = 0
        if dias_estudio:
            from datetime import date, timedelta
            dia = date.today()
            while str(dia) in dias_estudio:
                racha += 1
                dia -= timedelta(days=1)

        return jsonify({
            "nombre": estudiante['nombre'],
            "nivel_actual": nivel_actual,
            "promedio_aciertos": evaluacion.get('porcentaje_acierto', 0),
            "lecturas_completadas": lecturas_completadas,
            "racha": racha,
            "progreso": evaluacion,
            "recomendacion": recomendacion,
            "siguiente_lectura": siguiente,
            "actividad_reciente": actividad_reciente,
            "tiene_diagnostico": diagnostico is not None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1')
