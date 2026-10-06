"""Consultas de seguimiento: solo lectura y desempeño por último intento."""
from services.actividades import ActivityError
from services.lectura import entero_positivo, obtener_estado_lecturas
from services.tutoring import calcular_puntuacion_estudiante, recomendar_nivel_siguiente


def validar_acceso_docente(cursor, usuario):
    rol = usuario['rol']
    if rol not in (2, 3):
        raise ActivityError('Solo docentes y administradores pueden consultar el seguimiento', 403)
    cursor.execute('SELECT id_rol FROM usuarios WHERE id_usuario = %s', (usuario['id_usuario'],))
    cuenta = cursor.fetchone()
    if not cuenta or cuenta['id_rol'] != rol:
        raise ActivityError('La cuenta no tiene permisos de seguimiento', 403)
    if rol == 2:
        cursor.execute('SELECT id_docente FROM docentes WHERE id_usuario = %s', (usuario['id_usuario'],))
        if not cursor.fetchone():
            raise ActivityError('La cuenta no tiene un perfil docente', 403)


def parametros_pagina(args):
    pagina = entero_positivo(args.get('pagina', '1'), 'pagina')
    if pagina > 100000:
        raise ValueError('pagina fuera de rango')
    return pagina, 20, (pagina - 1) * 20


def listar_estudiantes(cursor, args):
    pagina, limite, offset = parametros_pagina(args)
    buscar = args.get('buscar', '').strip()
    nivel = args.get('nivel', '')
    if len(buscar) > 100 or nivel not in ('', 'literal', 'inferencial', 'crítico'):
        raise ValueError('Filtro de búsqueda o nivel inválido')
    # LOCATE evita tratar % y _ del usuario como comodines SQL.
    condicion = 'WHERE (%s = \'\' OR LOCATE(%s, u.nombre) > 0) AND (%s = \'\' OR e.nivel_actual = %s)'
    params = (buscar, buscar, nivel, nivel)
    cursor.execute('SELECT COUNT(*) AS total FROM estudiantes e JOIN usuarios u ON u.id_usuario=e.id_usuario ' + condicion, params)
    total = cursor.fetchone()['total']
    cursor.execute('''SELECT e.id_estudiante, u.nombre, e.nivel_actual,
        d.puntaje AS puntaje_diagnostico, d.nivel_asignado AS nivel_diagnostico,
        COALESCE(a.respondidas,0) AS respondidas, COALESCE(a.correctas,0) AS correctas,
        a.ultima_actividad
        FROM estudiantes e JOIN usuarios u ON u.id_usuario=e.id_usuario
        LEFT JOIN diagnostico d ON d.id_diagnostico=(SELECT MAX(d2.id_diagnostico) FROM diagnostico d2 WHERE d2.id_estudiante=e.id_estudiante)
        LEFT JOIN (
            SELECT r.id_estudiante, COUNT(*) AS respondidas,
                   SUM(r.es_correcta=1) AS correctas, MAX(r.fecha) AS ultima_actividad
            FROM respuestas_estudiante r
            JOIN (SELECT id_estudiante,id_pregunta,MAX(id_respuesta_est) AS ultimo
                  FROM respuestas_estudiante GROUP BY id_estudiante,id_pregunta) ult
              ON ult.ultimo=r.id_respuesta_est
            GROUP BY r.id_estudiante
        ) a ON a.id_estudiante=e.id_estudiante
        ''' + condicion + ' ORDER BY u.nombre,e.id_estudiante LIMIT %s OFFSET %s', params + (limite, offset))
    filas = cursor.fetchall()
    for fila in filas:
        fila['porcentaje_acierto'] = round(float(fila['correctas']) / fila['respondidas'] * 100, 2) if fila['respondidas'] else None
        fila['correctas'] = int(fila['correctas'])
        fila['ultima_actividad'] = str(fila['ultima_actividad']) if fila['ultima_actividad'] else None
    return {'estudiantes': filas, 'total': total, 'pagina': pagina, 'por_pagina': limite}


def detalle_estudiante(cursor, sid, args):
    pagina, limite, offset = parametros_pagina(args)
    cursor.execute('''SELECT e.id_estudiante,e.nivel_actual,u.nombre
                      FROM estudiantes e JOIN usuarios u ON u.id_usuario=e.id_usuario
                      WHERE e.id_estudiante=%s''', (sid,))
    estudiante = cursor.fetchone()
    if not estudiante:
        raise ActivityError('Estudiante no encontrado', 404)
    cursor.execute('''SELECT puntaje,nivel_asignado,fecha FROM diagnostico
                      WHERE id_estudiante=%s ORDER BY id_diagnostico DESC LIMIT 1''', (sid,))
    diagnostico = cursor.fetchone()
    if diagnostico:
        diagnostico['fecha'] = str(diagnostico['fecha']) if diagnostico['fecha'] else None
    evaluacion = calcular_puntuacion_estudiante(sid, cursor=cursor)
    recomendacion = recomendar_nivel_siguiente(sid, cursor=cursor)
    if 'error' in recomendacion:
        raise RuntimeError('No se pudo consultar la recomendación')
    estados = obtener_estado_lecturas(cursor, sid)
    cursor.execute('SELECT COUNT(*) AS total FROM respuestas_estudiante WHERE id_estudiante=%s', (sid,))
    total = cursor.fetchone()['total']
    cursor.execute('''SELECT r.id_respuesta_est,r.id_pregunta,r.respuesta,r.es_correcta,
                      r.tiempo_respuesta,r.fecha,p.enunciado,p.tipo,t.titulo,
                      f.mensaje AS retroalimentacion,
                      (r.id_respuesta_est=(SELECT MAX(r2.id_respuesta_est)
                       FROM respuestas_estudiante r2 WHERE r2.id_estudiante=r.id_estudiante
                       AND r2.id_pregunta=r.id_pregunta)) AS ultimo_intento
                      FROM respuestas_estudiante r JOIN preguntas p ON p.id_pregunta=r.id_pregunta
                      JOIN textos t ON t.id_texto=p.id_texto
                      LEFT JOIN retroalimentacion f ON f.id_respuesta_est=r.id_respuesta_est
                      WHERE r.id_estudiante=%s ORDER BY r.id_respuesta_est DESC LIMIT %s OFFSET %s''', (sid, limite, offset))
    historial = cursor.fetchall()
    for fila in historial:
        fila['fecha'] = str(fila['fecha']) if fila['fecha'] else None
        fila['es_correcta'] = bool(fila['es_correcta'])
        fila['ultimo_intento'] = bool(fila['ultimo_intento'])
    return {'estudiante': estudiante, 'diagnostico': diagnostico, 'evaluacion': evaluacion,
            'recomendacion': recomendacion, 'lecturas_completadas': sum(s['completada'] for s in estados.values()),
            'historial': historial, 'total_intentos': total, 'pagina': pagina, 'por_pagina': limite}
