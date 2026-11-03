"""Revisión de respuestas abiertas inferenciales y críticas con autorización."""
from services.actividades import ActivityError, persistir_progreso
from services.seguimiento_docente import validar_acceso_docente
from services.tutoring import obtener_nivel_actual, recomendar_nivel_siguiente
from services.banco_versionado import SQL_TEXTO_ACTIVO


def aplicar_nivel_tras_revision(cursor, sid, rid):
    """Aplica como máximo un paso con evidencia vigente del nivel actual.

    El llamador debe bloquear al estudiante y confirmar resultado, nivel y
    progreso en la misma transacción. No modifica umbrales ni permite saltos.
    """
    anterior = obtener_nivel_actual(sid,cursor=cursor)
    # Revisar un intento anterior, archivado o de otro nivel no debe provocar
    # ascensos ni descensos basados en evidencia ajena al nivel vigente.
    cursor.execute(f'''SELECT p.tipo FROM respuestas_estudiante r
                      JOIN preguntas p ON p.id_pregunta=r.id_pregunta
                      JOIN textos t ON t.id_texto=p.id_texto
                      JOIN revisiones_criticas rv ON rv.id_respuesta_est=r.id_respuesta_est
                      WHERE r.id_respuesta_est=%s AND r.id_estudiante=%s
                      AND r.es_correcta IS NOT NULL AND rv.fecha_revision IS NOT NULL
                      AND {SQL_TEXTO_ACTIVO}
                      AND r.id_respuesta_est=(
                          SELECT MAX(r2.id_respuesta_est) FROM respuestas_estudiante r2
                          WHERE r2.id_estudiante=r.id_estudiante
                          AND r2.id_pregunta=r.id_pregunta)''', (rid,sid))
    evidencia = cursor.fetchone()
    nuevo = anterior
    if evidencia and evidencia['tipo'] == anterior:
        recomendacion = recomendar_nivel_siguiente(sid,cursor=cursor)
        if 'error' in recomendacion:
            raise RuntimeError('No se pudo recalcular el nivel tras la revisión docente')
        nuevo = recomendacion['nuevo_nivel']
        if nuevo != anterior:
            cursor.execute('UPDATE estudiantes SET nivel_actual=%s WHERE id_estudiante=%s', (nuevo,sid))
    return anterior, nuevo


def revisar_respuesta(usuario, rid, data, get_cursor):
    if usuario['rol'] != 2:
        raise ActivityError('Solo los docentes pueden guardar revisiones. El administrador tiene acceso de solo lectura.',403)
    correcta = data.get('cumple')
    if type(correcta) is not bool:
        raise ValueError('Debes seleccionar Cumple o No cumple')
    devolucion = data.get('devolucion', '')
    if not isinstance(devolucion,str) or len(devolucion)>500:
        raise ValueError('La retroalimentación opcional admite hasta 500 caracteres')
    devolucion = devolucion.strip() or None
    conn,cursor = get_cursor()
    try:
        validar_acceso_docente(cursor,usuario,bloquear=True)
        # Lectura actual bloqueante: no abrir un snapshot previo a esperar el
        # bloqueo del estudiante, que podría ocultar otra revisión recién guardada.
        cursor.execute('SELECT id_estudiante FROM respuestas_estudiante WHERE id_respuesta_est=%s FOR UPDATE',(rid,))
        respuesta = cursor.fetchone()
        if not respuesta: raise ActivityError('Respuesta no encontrada',404)
        sid = respuesta['id_estudiante']
        cursor.execute('SELECT id_estudiante FROM estudiantes WHERE id_estudiante=%s FOR UPDATE',(sid,))
        cursor.fetchone()
        cursor.execute('SELECT fecha_revision FROM revisiones_criticas WHERE id_respuesta_est=%s FOR UPDATE',(rid,))
        revision = cursor.fetchone()
        if not revision: raise ActivityError('Este intento no admite revisión docente',409)
        if revision['fecha_revision'] is not None:
            raise ActivityError('La respuesta ya fue revisada. Actualiza el seguimiento.',409)
        cursor.execute('''UPDATE revisiones_criticas SET id_usuario_revisor=%s,
                          devolucion=%s,fecha_revision=NOW()
                          WHERE id_respuesta_est=%s''', (usuario['id_usuario'],devolucion,rid))
        cursor.execute('UPDATE respuestas_estudiante SET es_correcta=%s WHERE id_respuesta_est=%s',(correcta,rid))
        cursor.execute("UPDATE retroalimentacion SET mensaje=%s,tipo=%s WHERE id_respuesta_est=%s",
                       (devolucion or ('Revisión docente: cumple.' if correcta else 'Revisión docente: no cumple.'),
                        'revision_satisfactoria' if correcta else 'revision_refuerzo',rid))
        nivel_anterior, nivel = aplicar_nivel_tras_revision(cursor,sid,rid)
        evaluacion = persistir_progreso(cursor,sid,nivel)
        conn.commit()
        return {'id_respuesta_est':rid,'es_correcta':correcta,'estado':'revisada','evaluacion':evaluacion,
                'nivel_anterior':nivel_anterior,'nivel_actual':nivel,
                'nivel_actualizado':nivel != nivel_anterior}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close(); conn.close()
