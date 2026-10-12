"""Revisión de respuestas abiertas inferenciales y críticas con autorización."""
from services.actividades import ActivityError, persistir_progreso
from services.seguimiento_docente import validar_acceso_docente
from services.tutoring import obtener_nivel_actual


def revisar_respuesta(usuario, rid, data, get_cursor):
    correcta = data.get('cumple')
    if type(correcta) is not bool:
        raise ValueError('Debes seleccionar Cumple o No cumple')
    devolucion = data.get('devolucion', '')
    if not isinstance(devolucion,str) or len(devolucion)>500:
        raise ValueError('La retroalimentación opcional admite hasta 500 caracteres')
    devolucion = devolucion.strip() or None
    if usuario['rol'] not in (2,3):
        raise ActivityError('Solo docentes y administradores pueden revisar respuestas',403)
    conn,cursor = get_cursor()
    try:
        validar_acceso_docente(cursor,usuario)
        cursor.execute('SELECT id_estudiante FROM respuestas_estudiante WHERE id_respuesta_est=%s',(rid,))
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
        nivel = obtener_nivel_actual(sid,cursor=cursor)
        evaluacion = persistir_progreso(cursor,sid,nivel)
        conn.commit()
        return {'id_respuesta_est':rid,'es_correcta':correcta,'estado':'revisada','evaluacion':evaluacion}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close(); conn.close()
