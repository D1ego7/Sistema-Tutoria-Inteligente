"""Carga local de datos ficticios con respaldo y una única transacción.

Sin --aplicar solo muestra el alcance. No elimina historiales ni modifica el banco.
Las valoraciones docentes generadas son ejemplos de demostración, no evaluaciones reales.
"""
import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / '.venv/Lib/site-packages'))
sys.path.insert(0, str(RAIZ))
import bcrypt
from config import get_db_connection, db_config
from services.actividades import cargar_actividad, calificar_actividad, persistir_progreso
from services.diagnostico import DIAGNOSTICO_INICIAL, evaluar_respuestas_diagnostico, detalle_evaluacion
from services.tutoring import (calcular_nivel_lector_diagnostico, generar_feedback_personalizado,
                              obtener_nivel_actual, recomendar_nivel_siguiente)
from services.revision_docente import aplicar_nivel_tras_revision

NUEVOS = [
    ('Valeria Luciana Castillo Fernández', 'valeria.castillo@gmail.com'),
    ('Mateo Sebastián Rojas Delgado', 'mateo.rojas@gmail.com'),
    ('Camila Alejandra Torres Vásquez', 'camila.torres@gmail.com'),
    ('Adrián Nicolás Sánchez Campos', 'adrian.sanchez@gmail.com'),
    ('Luciana Isabel Ramírez Salazar', 'luciana.ramirez@gmail.com'),
    ('Joaquín Andrés Castañeda Ríos', 'joaquin.castaneda@gmail.com'),
    ('Sofía Fernanda Flores Chávez', 'sofia.flores@gmail.com'),
    ('Gabriel Alejandro Mendoza Ruiz', 'gabriel.mendoza@gmail.com'),
    ('Antonella Belén Guerrero Díaz', 'antonella.guerrero@gmail.com'),
    ('Thiago Daniel Carrasco Medina', 'thiago.carrasco@gmail.com'),
    ('Mariana Lucía Paredes Gonzales', 'mariana.paredes@gmail.com'),
    ('Diego Alonso Bances Santisteban', 'diego.bances@gmail.com'),
    ('Renata Valentina Pizarro Córdova', 'renata.pizarro@gmail.com'),
    ('Leonardo José Núñez Espinoza', 'leonardo.nunez@gmail.com'),
    ('Alessia Daniela Huamán Coronado', 'alessia.huaman@gmail.com'),
]
NIVELES = ['literal', 'inferencial', 'crítico']
HOY = datetime.now(timezone(timedelta(hours=-5))).date()


def identificador(s):
    return '`' + s.replace('`', '``') + '`'


def respaldo(conn, cur):
    cur.execute('SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()')
    tablas = cur.fetchall()
    if any(t['ENGINE'] != 'InnoDB' for t in tablas):
        raise RuntimeError('Se requieren tablas InnoDB para garantizar la reversión.')
    datos, esquemas = {}, {}
    for t in sorted(x['TABLE_NAME'] for x in tablas):
        cur.execute('SELECT * FROM ' + identificador(t) + ' FOR UPDATE')
        datos[t] = cur.fetchall()
        cur.execute('SHOW CREATE TABLE ' + identificador(t))
        esquemas[t] = cur.fetchone()['Create Table']
    destino = RAIZ / 'respaldos' / ('antes_carga_historial_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.sql')
    destino.parent.mkdir(exist_ok=True)
    with destino.open('x', encoding='utf-8') as salida:
        salida.write('-- Respaldo completo anterior a la carga de datos ficticios.\nSET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n')
        for t, filas in datos.items():
            salida.write('DROP TABLE IF EXISTS ' + identificador(t) + ';\n' + esquemas[t] + ';\n')
            for fila in filas:
                columnas = ','.join(identificador(k) for k in fila)
                valores = ','.join(conn.escape(v) for v in fila.values())
                salida.write(f'INSERT INTO {identificador(t)} ({columnas}) VALUES ({valores});\n')
        salida.write('SET FOREIGN_KEY_CHECKS=1;\n')
    if destino.stat().st_size < 100:
        raise RuntimeError('No se pudo verificar el respaldo.')
    return destino, datos


def diagnosticar(cur, estudiante, indice, fecha, rng):
    cur.execute('SELECT id_diagnostico FROM diagnostico WHERE id_estudiante=%s LIMIT 1', (estudiante['id_estudiante'],))
    if cur.fetchone():
        return False
    aciertos = (3, 6, 8)[indice % 3]
    preguntas = DIAGNOSTICO_INICIAL['preguntas']
    correctas = set(rng.sample([q['id'] for q in preguntas], aciertos))
    respuestas = []
    for q in preguntas:
        opcion = q['respuesta_correcta'] if q['id'] in correctas else rng.choice([o['id'] for o in q['opciones'] if o['id'] != q['respuesta_correcta']])
        respuestas.append({'id': q['id'], 'id_opcion': opcion})
    calificadas = evaluar_respuestas_diagnostico(respuestas)
    resultado = calcular_nivel_lector_diagnostico(calificadas)
    detalles, _ = detalle_evaluacion(respuestas, calificadas)
    cur.execute('INSERT INTO diagnostico (id_estudiante,puntaje,nivel_asignado,fecha) VALUES (%s,%s,%s,%s)',
                (estudiante['id_estudiante'], resultado['porcentaje'], resultado['nivel'], fecha))
    did = cur.lastrowid
    cur.execute('INSERT INTO diagnostico_detalle (id_diagnostico,version,instrumento_json,respuestas_json) VALUES (%s,%s,%s,%s)',
                (did, DIAGNOSTICO_INICIAL['version'], json.dumps(DIAGNOSTICO_INICIAL, ensure_ascii=False), json.dumps(detalles, ensure_ascii=False)))
    cur.execute('UPDATE estudiantes SET nivel_actual=%s WHERE id_estudiante=%s', (resultado['nivel'], estudiante['id_estudiante']))
    persistir_progreso(cur, estudiante['id_estudiante'], resultado['nivel'])
    return True


def guardar_intento(cur, estudiante, pregunta, buena, pendiente, fecha, docente, rng):
    usuario = {'id_usuario': estudiante['id_usuario'], 'rol': 1}
    _, actividad, nivel = cargar_actividad(cur, usuario, pregunta['id_pregunta'])
    if pregunta['tipo_respuesta'] == 'opcion':
        cur.execute('SELECT id_opcion,texto_opcion,es_correcta FROM opciones_pregunta WHERE id_pregunta=%s', (pregunta['id_pregunta'],))
        opciones = [o for o in cur.fetchall() if bool(o['es_correcta']) == buena]
        if not opciones:
            raise RuntimeError('Faltan opciones de evaluación.')
        dato = {'id_opcion': rng.choice(opciones)['id_opcion']}
    else:
        respuesta = pregunta['respuesta'] if buena else (
            rng.choice(['Sí, porque me parece una buena idea.', 'No, porque no me gusta esa decisión.', 'Sí, porque todos lo hacen.'])
            if pregunta['tipo'] == 'crítico' else 'Porque quería terminar rápido.' if pregunta['tipo'] == 'inferencial' else 'Su hermana menor')
        if not respuesta or len(respuesta) > 100:
            raise RuntimeError(f'Respuesta inválida en pregunta {pregunta["id_pregunta"]}.')
        dato = {'respuesta': respuesta}
    respuesta, correcta, esperada = calificar_actividad(cur, pregunta['id_pregunta'], actividad, dato)
    if correcta is not None and correcta != buena:
        raise RuntimeError('La respuesta simulada no coincide con la evaluación del sistema.')
    cur.execute('INSERT INTO respuestas_estudiante (id_estudiante,id_pregunta,respuesta,es_correcta,tiempo_respuesta,fecha) VALUES (%s,%s,%s,%s,%s,%s)',
                (estudiante['id_estudiante'], pregunta['id_pregunta'], respuesta, correcta, rng.randint(35, 165), fecha))
    rid = cur.lastrowid
    if correcta is None:
        if pendiente:
            cur.execute('INSERT INTO revisiones_criticas (id_respuesta_est) VALUES (%s)', (rid,))
            mensaje, tipo = 'Respuesta enviada. Pendiente de revisión docente.', 'pendiente_revision'
        else:
            # Valoración ficticia del docente, siguiendo el mismo modelo persistente del sistema.
            comentario = ('Tu respuesta explica la idea del texto: ' + pregunta['respuesta'] if buena else
                          'Tu idea necesita una justificación relacionada con el texto. Revisa esta referencia: ' + pregunta['respuesta'])
            if len(comentario) > 500:
                raise RuntimeError('Comentario demasiado largo.')
            fecha_revision = datetime.combine(fecha, datetime.min.time()).replace(hour=rng.randint(15, 18), minute=rng.randint(0, 59))
            cur.execute('INSERT INTO revisiones_criticas (id_respuesta_est,id_usuario_revisor,devolucion,fecha_revision) VALUES (%s,%s,%s,%s)',
                        (rid, docente, comentario, fecha_revision))
            cur.execute('UPDATE respuestas_estudiante SET es_correcta=%s WHERE id_respuesta_est=%s', (buena, rid))
            mensaje, tipo = comentario, 'revision_satisfactoria' if buena else 'revision_refuerzo'
    else:
        feedback = generar_feedback_personalizado(pregunta['id_pregunta'], correcta, respuesta, esperada, pregunta['tipo'])
        mensaje = ' '.join(feedback[k] for k in ('mensaje', 'explicacion', 'pista') if feedback.get(k))
        tipo = 'correcta' if correcta else 'refuerzo_' + pregunta['tipo']
    cur.execute('INSERT INTO retroalimentacion (id_respuesta_est,mensaje,tipo) VALUES (%s,%s,%s)', (rid, mensaje, tipo))
    if correcta is None and not pendiente:
        _, nivel = aplicar_nivel_tras_revision(cur, estudiante['id_estudiante'], rid)
    persistir_progreso(cur, estudiante['id_estudiante'], nivel)
    return rid


def cargar(conn):
    cur = conn.cursor()
    backup, originales = respaldo(conn, cur)
    if any(u['email'] in {e for _, e in NUEVOS} for u in originales['usuarios']):
        raise RuntimeError('Una cuenta de esta carga ya existe; se evita repetir la población.')
    docentes = [u['id_usuario'] for u in originales['usuarios'] if u['id_rol'] == 2 and any(d['id_usuario'] == u['id_usuario'] for d in originales['docentes'])]
    if not docentes:
        raise RuntimeError('Se necesita un docente existente para las revisiones ficticias.')
    estudiantes = []
    for e in originales['estudiantes']:
        u = next(u for u in originales['usuarios'] if u['id_usuario'] == e['id_usuario'])
        if u['id_rol'] != 1 or not u['email'].endswith('@gmail.com'):
            raise RuntimeError('Revisar el perfil o correo de un estudiante existente.')
        estudiantes.append({**e, 'nombre': u['nombre'], 'email': u['email'], 'nuevo': False})
    for nombre, correo in NUEVOS:
        cur.execute('INSERT INTO usuarios (nombre,email,contraseña,id_rol,fecha_registro) VALUES (%s,%s,%s,1,%s)',
                    (nombre, correo, bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode(), HOY-timedelta(days=29)))
        uid = cur.lastrowid
        cur.execute("INSERT INTO estudiantes (id_usuario,nivel_actual) VALUES (%s,'literal')", (uid,))
        estudiantes.append({'id_estudiante': cur.lastrowid, 'id_usuario': uid, 'nombre': nombre, 'email': correo, 'nuevo': True})
    cur.execute('''SELECT p.*,rc.respuesta,t.nivel FROM preguntas p JOIN textos t USING(id_texto)
                   LEFT JOIN respuestas_correctas rc USING(id_pregunta)
                   WHERE NOT EXISTS (SELECT 1 FROM versiones_lecturas v WHERE v.id_texto_original=t.id_texto)
                   ORDER BY p.id_texto,p.orden''')
    banco = {}
    for q in cur.fetchall():
        banco.setdefault(q['nivel'], {}).setdefault(q['id_texto'], []).append(q)
    calendario = sorted(HOY-timedelta(days=n) for n in range(1,29) if (HOY-timedelta(days=n)).weekday() < 5)
    ids_nuevos, diagnosticos_nuevos = [], 0
    for indice, e in enumerate(estudiantes):
        rng = random.Random(20261102 + e['id_estudiante'])
        cur.execute('UPDATE usuarios SET contraseña=%s WHERE id_usuario=%s', (bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode(), e['id_usuario']))
        diagnosticos_nuevos += int(diagnosticar(cur, e, indice, calendario[0], rng))
        cur.execute('SELECT fecha FROM diagnostico WHERE id_estudiante=%s ORDER BY id_diagnostico DESC LIMIT 1', (e['id_estudiante'],))
        fecha_diagnostico = cur.fetchone()['fecha']
        dias = [d for d in calendario if d > fecha_diagnostico]
        if not dias:
            raise RuntimeError('No hay fechas de actividad posteriores al diagnóstico.')
        nivel = obtener_nivel_actual(e['id_estudiante'], cursor=cur)
        persistir_progreso(cur, e['id_estudiante'], nivel)
        cur.execute('SELECT DISTINCT p.id_texto FROM respuestas_estudiante r JOIN preguntas p USING(id_pregunta) WHERE r.id_estudiante=%s', (e['id_estudiante'],))
        usados = {r['id_texto'] for r in cur.fetchall()}
        sesion = 0
        for nivel_lectura in NIVELES:
            nivel = obtener_nivel_actual(e['id_estudiante'], cursor=cur)
            if NIVELES.index(nivel_lectura) > NIVELES.index(nivel):
                break
            lecturas = [t for t in banco[nivel_lectura] if t not in usados]
            rng.shuffle(lecturas)
            for j, tid in enumerate(lecturas[:3]):
                fecha = dias[min(len(dias)-1, 2+sesion*2)]
                sesion += 1
                for k, pregunta in enumerate(banco[nivel_lectura][tid]):
                    pendiente = nivel_lectura == 'crítico' and j == 2 and k < (0, 1, 3)[(indice//3) % 3]
                    buena = rng.random() < (1.0 if indice % 4 == 0 else (.67, .82, .9)[indice % 3])
                    rid = guardar_intento(cur, e, pregunta, buena, pendiente, fecha, docentes[(indice+j) % len(docentes)], rng)
                    ids_nuevos.append(rid)
                    # Algunos estudiantes corrigen una respuesta previamente evaluada.
                    if not buena and not pendiente and j == 0 and k == 0 and indice % 2 == 0:
                        ids_nuevos.append(guardar_intento(cur, e, pregunta, True, False, dias[min(len(dias)-1,3+(sesion-1)*2)], docentes[indice % len(docentes)], rng))
                actual = obtener_nivel_actual(e['id_estudiante'], cursor=cur)
                rec = recomendar_nivel_siguiente(e['id_estudiante'], cursor=cur)
                if 'error' in rec:
                    raise RuntimeError(rec['error'])
                if nivel_lectura == actual and rec['nuevo_nivel'] != actual:
                    actual = rec['nuevo_nivel']
                    cur.execute('UPDATE estudiantes SET nivel_actual=%s WHERE id_estudiante=%s', (actual,e['id_estudiante']))
                persistir_progreso(cur, e['id_estudiante'], actual)
        # Verificar la contraseña real con bcrypt y mantener el nivel consolidado.
        cur.execute('SELECT contraseña FROM usuarios WHERE id_usuario=%s', (e['id_usuario'],))
        assert bcrypt.checkpw(b'password123', cur.fetchone()['contraseña'].encode())
        e['nivel_actual'] = obtener_nivel_actual(e['id_estudiante'], cursor=cur)
    # Los registros anteriores del historial y los contenidos deben permanecer intactos.
    for tabla, clave in [('diagnostico','id_diagnostico'), ('respuestas_estudiante','id_respuesta_est'),
                         ('revisiones_criticas','id_respuesta_est'), ('retroalimentacion','id_feedback'),
                         ('textos','id_texto'), ('preguntas','id_pregunta'), ('docentes','id_docente')]:
        for fila in originales[tabla]:
            cur.execute('SELECT * FROM '+identificador(tabla)+' WHERE '+identificador(clave)+'=%s', (fila[clave],))
            if cur.fetchone() != fila:
                raise RuntimeError('Se alteró un registro original en '+tabla)
    marcadores = ','.join(['%s']*len(ids_nuevos))
    cur.execute(f'''SELECT r.*,rv.id_respuesta_est revision,rv.fecha_revision,rv.devolucion,f.tipo feedback
                    FROM respuestas_estudiante r LEFT JOIN revisiones_criticas rv USING(id_respuesta_est)
                    LEFT JOIN retroalimentacion f USING(id_respuesta_est) WHERE r.id_respuesta_est IN ({marcadores})''', ids_nuevos)
    filas = cur.fetchall()
    for r in filas:
        assert r['feedback'] and len(r['respuesta']) <= 100
        if r['es_correcta'] is None:
            assert r['revision'] and r['fecha_revision'] is None and r['feedback'] == 'pendiente_revision'
        elif r['revision']:
            assert r['fecha_revision'] and r['devolucion']
    resumen = {'naturaleza': 'Datos ficticios para demostración; no son resultados de evaluación de estudiantes reales.',
               'respaldo': str(backup), 'sha256_respaldo': hashlib.sha256(backup.read_bytes()).hexdigest(),
               'estudiantes_nuevos': len(NUEVOS), 'estudiantes_existentes': len(estudiantes)-len(NUEVOS),
               'diagnosticos_agregados': diagnosticos_nuevos, 'intentos_agregados': len(filas),
               'revisiones_agregadas': sum(r['revision'] is not None and r['fecha_revision'] is not None for r in filas),
               'pendientes_agregados': sum(r['es_correcta'] is None for r in filas), 'cuentas': estudiantes}
    manifiesto = backup.with_name(backup.stem.replace('antes_carga', 'resumen_carga') + '.json')
    manifiesto.write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    conn.commit()
    cur.close()
    print(json.dumps({k:v for k,v in resumen.items() if k != 'cuentas'}, ensure_ascii=False, indent=2))
    print('Resumen de cuentas:', manifiesto)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    if not args.aplicar:
        print('Plan: 15 estudiantes ficticios nuevos; historial adicional y contraseña compartida para todos los estudiantes; respaldo completo. Sin cambios.')
        return
    if db_config['host'] not in ('localhost','127.0.0.1','::1'):
        raise RuntimeError('La carga se permite únicamente en la base local.')
    conn = get_db_connection()
    try:
        conn.begin()
        cargar(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
