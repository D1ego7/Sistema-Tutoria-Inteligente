"""Registro transaccional de actividades, compartido por las rutas de respuesta."""
from services.lectura import entero_positivo, validar_respuesta, validar_tiempo, evaluar_respuesta_abierta
from services.tutoring import (
    obtener_nivel_actual, normalizar_texto, calcular_puntuacion_estudiante,
    generar_feedback_personalizado,
)

NIVELES = ['literal', 'inferencial', 'crítico']


class ActivityError(Exception):
    def __init__(self, mensaje, status=400):
        super().__init__(mensaje)
        self.status = status


def cargar_actividad(cursor, usuario, pregunta_id, estudiante=None):
    if usuario['rol'] != 1:
        raise ActivityError('Solo los estudiantes pueden responder actividades', 403)
    if estudiante is None:
        cursor.execute('SELECT id_estudiante FROM estudiantes WHERE id_usuario = %s FOR UPDATE',
                       (usuario['id_usuario'],))
        estudiante = cursor.fetchone()
    if not estudiante:
        raise ActivityError('Estudiante no encontrado', 403)
    sid = estudiante['id_estudiante']
    cursor.execute('SELECT 1 FROM diagnostico WHERE id_estudiante = %s LIMIT 1', (sid,))
    if not cursor.fetchone():
        raise ActivityError('Debes completar el diagnóstico inicial', 403)
    cursor.execute('''
        SELECT p.id_pregunta, p.tipo, p.tipo_respuesta, p.id_texto, t.nivel, rc.respuesta
        FROM preguntas p JOIN textos t ON t.id_texto = p.id_texto
        LEFT JOIN respuestas_correctas rc ON rc.id_pregunta = p.id_pregunta
        WHERE p.id_pregunta = %s
    ''', (pregunta_id,))
    pregunta = cursor.fetchone()
    if not pregunta:
        raise ActivityError('Pregunta no encontrada', 404)
    nivel = obtener_nivel_actual(sid, cursor=cursor)
    indice = NIVELES.index(nivel) if nivel in NIVELES else 0
    if normalizar_texto(pregunta['nivel']) not in [normalizar_texto(n) for n in NIVELES[:indice+1]]:
        raise ActivityError('La actividad aún no está habilitada para tu nivel', 403)
    return estudiante, pregunta, nivel


def calificar_actividad(cursor, pregunta_id, pregunta, data):
    if pregunta['tipo_respuesta'] == 'opcion':
        opcion_id = entero_positivo(data.get('id_opcion'), 'id_opcion')
        cursor.execute('SELECT texto_opcion, es_correcta FROM opciones_pregunta '
                       'WHERE id_opcion = %s AND id_pregunta = %s', (opcion_id, pregunta_id))
        opcion = cursor.fetchone()
        if not opcion:
            raise ActivityError('La opción seleccionada no pertenece a la pregunta')
        cursor.execute('SELECT texto_opcion FROM opciones_pregunta '
                       'WHERE id_pregunta = %s AND es_correcta = TRUE LIMIT 1', (pregunta_id,))
        correcta = cursor.fetchone()
        if not correcta:
            raise ActivityError('La pregunta no tiene una clave de evaluación configurada', 409)
        return opcion['texto_opcion'], bool(opcion['es_correcta']), correcta['texto_opcion']
    respuesta = validar_respuesta(data.get('respuesta'))
    if not pregunta['respuesta']:
        raise ActivityError('La pregunta no tiene una clave de evaluación configurada', 409)
    return respuesta, evaluar_respuesta_abierta(respuesta, pregunta['respuesta']), pregunta['respuesta']


def persistir_progreso(cursor, sid, nivel):
    evaluacion = calcular_puntuacion_estudiante(sid, cursor=cursor)
    cursor.execute('''
        INSERT INTO progreso (id_estudiante, nivel_actual, porcentaje_avance)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE nivel_actual = VALUES(nivel_actual),
                                porcentaje_avance = VALUES(porcentaje_avance)
    ''', (sid, nivel, evaluacion['porcentaje_acierto']))
    return evaluacion


def registrar_actividades(usuario, data, get_cursor, lote=False):
    if usuario['rol'] != 1:
        raise ActivityError('Solo los estudiantes pueden responder actividades', 403)
    items = data.get('respuestas') if lote else [data]
    if not isinstance(items, list) or not items or len(items) > 100:
        raise ValueError('respuestas debe contener entre 1 y 100 elementos')
    ids = []
    entradas = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Cada respuesta debe ser un objeto')
        pid = entero_positivo(item.get('id_pregunta'), 'id_pregunta')
        tiempo = validar_tiempo(item.get('tiempo_respuesta', 0))
        if pid in ids:
            raise ValueError('No se permiten preguntas duplicadas en un envío')
        ids.append(pid)
        entradas.append((pid, tiempo, item))
    texto_id = entero_positivo(data.get('id_texto'), 'id_texto') if lote else None
    conn, cursor = get_cursor()
    try:
        estudiante = None
        resultados = []
        for pid, tiempo, item in entradas:
            estudiante, pregunta, nivel = cargar_actividad(cursor, usuario, pid, estudiante)
            if lote and pregunta['id_texto'] != texto_id:
                raise ActivityError('Todas las preguntas deben pertenecer a la lectura enviada')
            respuesta, correcta, esperada = calificar_actividad(cursor, pid, pregunta, item)
            cursor.execute('''
                INSERT INTO respuestas_estudiante
                    (id_estudiante, id_pregunta, respuesta, es_correcta, tiempo_respuesta, fecha)
                VALUES (%s, %s, %s, %s, %s, NOW())
            ''', (estudiante['id_estudiante'], pid, respuesta, correcta, tiempo))
            respuesta_id = cursor.lastrowid
            feedback = generar_feedback_personalizado(pid, correcta, respuesta, esperada, pregunta['tipo'])
            mensaje = ' '.join(feedback[k] for k in ['mensaje', 'explicacion', 'pista'] if feedback.get(k))
            cursor.execute('INSERT INTO retroalimentacion (id_respuesta_est, mensaje, tipo) VALUES (%s, %s, %s)',
                           (respuesta_id, mensaje, 'correcta' if correcta else 'refuerzo_'+pregunta['tipo']))
            resultados.append({'id_pregunta': pid, 'id_respuesta_est': respuesta_id,
                               'es_correcta': correcta, 'feedback': feedback,
                               'tiempo_respuesta': tiempo})
        evaluacion = persistir_progreso(cursor, estudiante['id_estudiante'], nivel)
        conn.commit()  # Respuestas + feedback + resumen: todo o nada.
        if lote:
            return {'respuestas': resultados, 'progreso_actualizado': evaluacion}
        result = resultados[0]
        result.update(progreso_actualizado=evaluacion, total_respuestas=evaluacion['total_respuestas'],
                      recomendacion=None, message='Respuesta guardada exitosamente')
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
