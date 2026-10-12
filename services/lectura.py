"""Reglas compartidas de lectura: último intento, calificación y entradas válidas."""
import math
import re
from services.banco_versionado import SQL_TEXTO_ACTIVO
from services.tutoring import normalizar_texto


def entero_positivo(value, nombre):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{nombre} debe ser un entero positivo")
    if isinstance(value, str) and not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"{nombre} debe ser un entero positivo")
    result = int(value)
    if result <= 0:
        raise ValueError(f"{nombre} debe ser un entero positivo")
    return result


def validar_tiempo(value):
    # Segundos transcurridos reportados por el navegador, no velocidad lectora.
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("tiempo_respuesta debe ser un número de segundos")
    if not math.isfinite(value) or not 0 <= value <= 86400:
        raise ValueError("tiempo_respuesta debe estar entre 0 y 86400 segundos")
    return math.ceil(value)


def validar_respuesta(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 100:
        raise ValueError("respuesta debe ser texto no vacío de hasta 100 caracteres")
    return value.strip()


def evaluar_respuesta_abierta(respuesta, alternativas):
    """Equivalencia léxica conservadora, sin aceptar subcadenas ni inventar sinónimos.

    Tolera tildes, mayúsculas, puntuación y artículos. Conserva negaciones,
    cantidades y demás palabras; las paráfrasis requieren alternativas explícitas.
    """
    if not isinstance(respuesta, str):
        return False
    if isinstance(alternativas, str):
        alternativas = [alternativas]
    articles = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas'}
    def tokens(text):
        return [word for word in re.findall(r'\w+', normalizar_texto(text))
                if word not in articles]
    actual = tokens(respuesta)
    if not actual:
        return False
    # El orden se conserva: invertir los personajes de una acción no es equivalente.
    return any(actual == tokens(text) for text in alternativas or [] if text)


def estado_lectura(total_preguntas, respuestas):
    """Consolida incluso si la entrada contiene todo el historial, no solo últimos."""
    ultimas = {}
    for row in respuestas:
        previous = ultimas.get(row['id_pregunta'])
        if previous is None or row['id_respuesta_est'] > previous['id_respuesta_est']:
            ultimas[row['id_pregunta']] = row
    respondidas = len(ultimas)
    correctas = sum(bool(row['es_correcta']) for row in ultimas.values())
    evaluadas = sum(row['es_correcta'] is not None for row in ultimas.values())
    return {
        'total_preguntas': int(total_preguntas),
        'respondidas': respondidas,
        'correctas': correctas,
        'pendientes': respondidas-evaluadas,
        'porcentaje': round(correctas * 100 / evaluadas, 2) if evaluadas else 0,
        'completada': total_preguntas > 0 and respondidas == total_preguntas
                      and correctas == total_preguntas,
    }


def obtener_estado_lecturas(cursor, id_estudiante):
    """Una consulta para catálogo e Inicio, con el mismo criterio de finalización."""
    cursor.execute(f"""
        SELECT p.id_texto, COUNT(p.id_pregunta) AS total_preguntas,
               COUNT(re.id_respuesta_est) AS respondidas,
               COUNT(re.es_correcta) AS evaluadas,
               COALESCE(SUM(re.es_correcta = TRUE), 0) AS correctas
        FROM preguntas p
        JOIN textos t ON t.id_texto=p.id_texto
        LEFT JOIN (
            SELECT r.id_respuesta_est, r.id_pregunta, r.es_correcta
            FROM respuestas_estudiante r
            JOIN (
                SELECT id_pregunta, MAX(id_respuesta_est) AS ultima_respuesta
                FROM respuestas_estudiante WHERE id_estudiante = %s
                GROUP BY id_pregunta
            ) u ON u.ultima_respuesta = r.id_respuesta_est
            WHERE r.id_estudiante = %s
        ) re ON re.id_pregunta = p.id_pregunta
        WHERE {SQL_TEXTO_ACTIVO}
        GROUP BY p.id_texto
    """, (id_estudiante, id_estudiante))
    result = {}
    for row in cursor.fetchall():
        total, answered, correct = (int(row[key] or 0) for key in
                                    ['total_preguntas', 'respondidas', 'correctas'])
        result[row['id_texto']] = {
            'total_preguntas': total, 'respondidas': answered, 'correctas': correct,
            'pendientes': answered-int(row.get('evaluadas',answered)),
            'porcentaje': round(correct * 100 / int(row.get('evaluadas',answered)), 2) if row.get('evaluadas',answered) else 0,
            'completada': total > 0 and answered == total and correct == total,
        }
    return result
