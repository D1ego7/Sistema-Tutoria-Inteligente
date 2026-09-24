"""Completa feedback histórico faltante y recalcula el progreso consolidado.

El script es idempotente: solo crea retroalimentación para respuestas que aún
no la tienen. Usa la configuración local de ``.env``.
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
sys.path.insert(0, str(SITE_PACKAGES))
sys.path.insert(0, str(ROOT))

from config import get_db_connection
from services.tutoring import generar_feedback_personalizado, sincronizar_progreso_estudiante


def asegurar_indices_unicos():
    indices = [
        ("usuarios", "uq_usuarios_email", "email"),
        ("estudiantes", "uq_estudiantes_usuario", "id_usuario"),
        ("docentes", "uq_docentes_usuario", "id_usuario"),
        ("progreso", "uq_progreso_estudiante", "id_estudiante"),
        ("retroalimentacion", "uq_retro_respuesta", "id_respuesta_est"),
    ]
    connection = get_db_connection()
    cursor = connection.cursor()
    creados = 0
    try:
        for tabla, indice, columna in indices:
            cursor.execute(
                f"SELECT `{columna}`, COUNT(*) AS cantidad FROM `{tabla}` "
                f"GROUP BY `{columna}` HAVING COUNT(*) > 1 LIMIT 1"
            )
            if cursor.fetchone():
                raise RuntimeError(
                    f"No se puede crear {indice}: existen valores duplicados en {tabla}.{columna}"
                )
            cursor.execute("""
                SELECT 1
                FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = %s AND index_name = %s
                LIMIT 1
            """, (tabla, indice))
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE `{tabla}` ADD UNIQUE KEY `{indice}` (`{columna}`)")
                creados += 1
        connection.commit()
        return creados
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def completar_retroalimentacion():
    connection = get_db_connection()
    cursor = connection.cursor()
    insertadas = 0
    try:
        cursor.execute("""
            SELECT re.id_respuesta_est, re.respuesta, re.es_correcta,
                   p.id_pregunta, p.tipo,
                   COALESCE(rc.respuesta, op.texto_opcion, '') AS respuesta_correcta
            FROM respuestas_estudiante re
            JOIN preguntas p ON p.id_pregunta = re.id_pregunta
            LEFT JOIN respuestas_correctas rc ON rc.id_pregunta = p.id_pregunta
            LEFT JOIN opciones_pregunta op
                ON op.id_pregunta = p.id_pregunta AND op.es_correcta = TRUE
            LEFT JOIN retroalimentacion rf ON rf.id_respuesta_est = re.id_respuesta_est
            WHERE rf.id_feedback IS NULL
            ORDER BY re.id_respuesta_est
        """)
        respuestas = cursor.fetchall()

        for respuesta in respuestas:
            feedback = generar_feedback_personalizado(
                respuesta['id_pregunta'],
                bool(respuesta['es_correcta']),
                respuesta['respuesta'] or '',
                respuesta['respuesta_correcta'] or '',
                respuesta['tipo']
            )
            mensaje = " ".join(
                parte for parte in [
                    feedback.get('mensaje'),
                    feedback.get('explicacion'),
                    feedback.get('pista')
                ] if parte
            )
            cursor.execute("""
                INSERT INTO retroalimentacion (id_respuesta_est, mensaje, tipo)
                VALUES (%s, %s, %s)
            """, (
                respuesta['id_respuesta_est'],
                mensaje,
                'correcta' if respuesta['es_correcta'] else f"refuerzo_{respuesta['tipo']}"
            ))
            insertadas += 1

        connection.commit()
        return insertadas
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def recalcular_progreso():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id_estudiante FROM estudiantes ORDER BY id_estudiante")
        estudiantes = [fila['id_estudiante'] for fila in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

    errores = []
    for id_estudiante in estudiantes:
        resultado = sincronizar_progreso_estudiante(id_estudiante)
        if 'error' in resultado:
            errores.append((id_estudiante, resultado['error']))
    return len(estudiantes), errores


if __name__ == "__main__":
    indices = asegurar_indices_unicos()
    feedbacks = completar_retroalimentacion()
    estudiantes, errores = recalcular_progreso()
    print(f"Índices únicos creados: {indices}")
    print(f"Retroalimentaciones creadas: {feedbacks}")
    print(f"Progresos recalculados: {estudiantes - len(errores)}/{estudiantes}")
    if errores:
        raise SystemExit(f"No se pudo recalcular el progreso de {len(errores)} estudiante(s)")
