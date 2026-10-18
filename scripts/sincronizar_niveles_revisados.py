"""Actualiza una vez niveles pendientes de aplicar tras revisiones ya guardadas.

Por defecto solo muestra cambios propuestos. --aplicar crea respaldo privado y
confirma nivel/progreso juntos. No cambia respuestas, revisiones ni diagnóstico.
Usar con el servidor detenido. El flujo ordinario se ejecuta al revisar, no aquí.
"""
import argparse
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / '.venv' / 'Lib' / 'site-packages'))
sys.path.insert(0, str(RAIZ))

from config import get_db_connection
from scripts.migrar_revision_docente import respaldar
from services.actividades import persistir_progreso
from services.banco_versionado import SQL_TEXTO_ACTIVO
from services.revision_docente import aplicar_nivel_tras_revision
from services.tutoring import obtener_nivel_actual, recomendar_nivel_siguiente


def sincronizar(aplicar=False):
    conn = get_db_connection()
    try:
        if aplicar:
            print('Respaldo privado:', respaldar(conn))
        conn.begin()
        cambios = []
        with conn.cursor() as cursor:
            cursor.execute('SELECT id_estudiante FROM estudiantes ORDER BY id_estudiante' +
                           (' FOR UPDATE' if aplicar else ''))
            estudiantes = cursor.fetchall()
            for estudiante in estudiantes:
                sid = estudiante['id_estudiante']
                anterior = obtener_nivel_actual(sid,cursor=cursor)
                cursor.execute(f'''SELECT r.id_respuesta_est FROM respuestas_estudiante r
                    JOIN revisiones_criticas rv ON rv.id_respuesta_est=r.id_respuesta_est
                    JOIN preguntas p ON p.id_pregunta=r.id_pregunta
                    JOIN textos t ON t.id_texto=p.id_texto
                    WHERE r.id_estudiante=%s AND p.tipo=%s
                    AND rv.fecha_revision IS NOT NULL AND r.es_correcta IS NOT NULL
                    AND {SQL_TEXTO_ACTIVO}
                    AND r.id_respuesta_est=(SELECT MAX(r2.id_respuesta_est)
                        FROM respuestas_estudiante r2 WHERE r2.id_estudiante=r.id_estudiante
                        AND r2.id_pregunta=r.id_pregunta)
                    ORDER BY r.id_respuesta_est DESC LIMIT 1''', (sid,anterior))
                evidencia = cursor.fetchone()
                if not evidencia:
                    continue
                if aplicar:
                    anterior, nuevo = aplicar_nivel_tras_revision(cursor,sid,evidencia['id_respuesta_est'])
                else:
                    recomendacion = recomendar_nivel_siguiente(sid,cursor=cursor)
                    if 'error' in recomendacion:
                        raise RuntimeError('No se pudo recalcular el nivel')
                    nuevo = recomendacion['nuevo_nivel']
                if nuevo != anterior:
                    if aplicar:
                        persistir_progreso(cursor,sid,nuevo)
                    cambios.append({'id_estudiante':sid,'nivel_anterior':anterior,'nivel_actual':nuevo})
        if aplicar:
            conn.commit()
        else:
            conn.rollback()
        print('Cambios aplicados:' if aplicar else 'Cambios propuestos (sin escritura):', cambios)
        return cambios
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    sincronizar(parser.parse_args().aplicar)
