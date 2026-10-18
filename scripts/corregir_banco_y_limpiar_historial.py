"""Revisión local con respaldo completo, transacción y limpieza explícita.

Sin argumentos solo inspecciona. --aplicar publica nuevas versiones.
--limpiar-historial junto a --aplicar borra el historial de TODOS los estudiantes.
--simular con --aplicar verifica la operación y revierte sin confirmar cambios.
Cerrar el servidor y no utilizar la aplicación durante la operación.
No reinicia AUTO_INCREMENT, elimina cuentas ni desactiva llaves foráneas.
"""
import argparse
from datetime import datetime
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / '.venv' / 'Lib' / 'site-packages'))
sys.path.insert(0, str(RAIZ))

from config import get_db_connection
from services.correcciones_banco import LECTURAS, CONTENIDOS, PREGUNTAS, OPCIONES

HISTORIAL = (
    'revisiones_criticas', 'retroalimentacion', 'respuestas_estudiante',
    'reportes', 'notificaciones', 'diagnostico_detalle', 'diagnostico', 'progreso',
)
BANCO = ('textos', 'preguntas', 'respuestas_correctas', 'opciones_pregunta',
         'preguntas_revision', 'versiones_lecturas')
PRIMERAS = {
    13: 29, 22: 56, 23: 59, 24: 62, 25: 65, 26: 68, 28: 74,
    176: 518, 177: 521, 178: 524, 180: 530, 181: 533,
    183: 539, 184: 542, 186: 548,
}


def nombre_sql(nombre):
    return '`' + nombre.replace('`', '``') + '`'


def leer_lectura(cursor, tid):
    cursor.execute('SELECT id_texto,titulo,contenido,nivel FROM textos WHERE id_texto=%s', (tid,))
    texto = cursor.fetchone()
    if not texto:
        raise RuntimeError(f'No existe la lectura {tid}')
    cursor.execute('''SELECT p.*,rc.respuesta FROM preguntas p
                      JOIN respuestas_correctas rc USING(id_pregunta)
                      WHERE p.id_texto=%s ORDER BY p.orden''', (tid,))
    preguntas = cursor.fetchall()
    if len(preguntas) != 3 or [p['orden'] for p in preguntas] != [1, 2, 3]:
        raise RuntimeError(f'Orden o claves inesperadas en lectura {tid}')
    for p in preguntas:
        cursor.execute('''SELECT texto_opcion,es_correcta FROM opciones_pregunta
                          WHERE id_pregunta=%s ORDER BY id_opcion''', (p['id_pregunta'],))
        p['opciones'] = [(r['texto_opcion'], bool(r['es_correcta'])) for r in cursor.fetchall()]
        cursor.execute('SELECT id_pregunta_original FROM preguntas_revision WHERE id_pregunta=%s',
                       (p['id_pregunta'],))
        marca = cursor.fetchone()
        p['revision_original'] = marca['id_pregunta_original'] if marca else None
    return texto, preguntas


def preparar_plan(cursor):
    planes = []
    encontradas = set()
    for tid, titulo in LECTURAS.items():
        texto, originales = leer_lectura(cursor, tid)
        ids = [p['id_pregunta'] for p in originales]
        if texto['titulo'] != titulo or ids != list(range(PRIMERAS[tid], PRIMERAS[tid]+3)):
            raise RuntimeError(f'La lectura auditada {tid} cambió: revisar antes de continuar')
        nuevas = []
        for p in originales:
            pid = p['id_pregunta']
            enunciado, respuesta = PREGUNTAS.get(pid, (p['enunciado'], p['respuesta']))
            opciones = OPCIONES.get(pid, p['opciones'])
            if pid in PREGUNTAS:
                encontradas.add(pid)
            if not respuesta or (p['tipo_respuesta'] == 'texto' and len(respuesta) > 100):
                raise RuntimeError(f'Referencia inválida en pregunta {pid}')
            if p['tipo'] != texto['nivel']:
                raise RuntimeError(f'Nivel inesperado en pregunta {pid}')
            if p['tipo_respuesta'] == 'opcion':
                if len(opciones) != 3 or sum(o[1] for o in opciones) != 1:
                    raise RuntimeError(f'Opciones inválidas en pregunta {pid}')
                if pid in OPCIONES and respuesta != next(o[0] for o in opciones if o[1]):
                    raise RuntimeError(f'Clave y opción distintas en pregunta {pid}')
            elif opciones:
                raise RuntimeError(f'Opciones en una pregunta abierta: {pid}')
            nuevas.append({**p, 'enunciado': enunciado, 'respuesta': respuesta, 'opciones': opciones})
        esperado = {**texto, 'contenido': CONTENIDOS.get(tid, texto['contenido'])}
        cursor.execute('SELECT id_texto_actual FROM versiones_lecturas WHERE id_texto_original=%s', (tid,))
        version = cursor.fetchone()
        existente = version['id_texto_actual'] if version else None
        if existente:
            actual, ps = leer_lectura(cursor, existente)
            campos = ('enunciado', 'tipo', 'tipo_respuesta', 'orden', 'respuesta', 'opciones', 'revision_original')
            if any(actual[k] != esperado[k] for k in ('titulo', 'contenido', 'nivel')) or any(
                any(a[k] != b[k] for k in campos) for a, b in zip(ps, nuevas)
            ):
                raise RuntimeError(f'Ya existe otra versión de {tid}; no se sobrescribirá')
        planes.append((esperado, nuevas, existente))
    if encontradas != set(PREGUNTAS) or not set(OPCIONES) <= encontradas:
        raise RuntimeError('El plan contiene preguntas que no pertenecen al banco auditado')
    return planes


def capturar_y_respaldar(conn, cursor):
    cursor.execute('''SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES
                      WHERE TABLE_SCHEMA=DATABASE()''')
    tablas = cursor.fetchall()
    if any(t['ENGINE'] != 'InnoDB' for t in tablas):
        raise RuntimeError('Todas las tablas deben ser InnoDB para poder revertir')
    nombres = sorted(t['TABLE_NAME'] for t in tablas)
    if not set((*HISTORIAL, *BANCO, 'estudiantes', 'usuarios', 'docentes', 'roles')) <= set(nombres):
        raise RuntimeError('Faltan tablas requeridas para respaldar y verificar')
    snapshot, esquemas = {}, {}
    # Bloquea las filas y rangos durante respaldo, publicación y limpieza.
    for nombre in nombres:
        cursor.execute('SELECT * FROM ' + nombre_sql(nombre) + ' FOR UPDATE')
        snapshot[nombre] = cursor.fetchall()
        cursor.execute('SHOW CREATE TABLE ' + nombre_sql(nombre))
        esquemas[nombre] = cursor.fetchone()['Create Table']
    carpeta = RAIZ / 'respaldos'
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / ('antes_correcciones_y_limpieza_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.sql')
    with destino.open('x', encoding='utf-8') as salida:
        salida.write('-- Respaldo privado anterior a las correcciones y limpieza.\n')
        salida.write('SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n')
        for nombre in nombres:
            identificador = nombre_sql(nombre)
            salida.write('DROP TABLE IF EXISTS ' + identificador + ';\n' + esquemas[nombre] + ';\n')
            for fila in snapshot[nombre]:
                columnas = ','.join(nombre_sql(k) for k in fila)
                valores = ','.join(conn.escape(v) for v in fila.values())
                salida.write(f'INSERT INTO {identificador} ({columnas}) VALUES ({valores});\n')
        salida.write('SET FOREIGN_KEY_CHECKS=1;\n')
        salida.flush()
    if destino.stat().st_size == 0:
        raise RuntimeError('Respaldo vacío: no se continuará')
    return snapshot, destino


def publicar(cursor, planes):
    publicados = []
    for texto, preguntas, existente in planes:
        if existente:
            continue
        cursor.execute('INSERT INTO textos (titulo,contenido,nivel) VALUES (%s,%s,%s)',
                       (texto['titulo'], texto['contenido'], texto['nivel']))
        nuevo_texto = cursor.lastrowid
        for p in preguntas:
            cursor.execute('''INSERT INTO preguntas (id_texto,enunciado,tipo,tipo_respuesta,orden)
                              VALUES (%s,%s,%s,%s,%s)''',
                           (nuevo_texto, p['enunciado'], p['tipo'], p['tipo_respuesta'], p['orden']))
            nuevo_pid = cursor.lastrowid
            cursor.execute('INSERT INTO respuestas_correctas (id_pregunta,respuesta) VALUES (%s,%s)',
                           (nuevo_pid, p['respuesta']))
            for opcion, correcta in p['opciones']:
                cursor.execute('''INSERT INTO opciones_pregunta (id_pregunta,texto_opcion,es_correcta)
                                  VALUES (%s,%s,%s)''', (nuevo_pid, opcion, correcta))
            if p['revision_original'] is not None:
                cursor.execute('INSERT INTO preguntas_revision VALUES (%s,%s)',
                               (nuevo_pid, p['revision_original']))
        cursor.execute('INSERT INTO versiones_lecturas (id_texto_original,id_texto_actual) VALUES (%s,%s)',
                       (texto['id_texto'], nuevo_texto))
        publicados.append((texto['id_texto'], nuevo_texto))
    return publicados


def limpiar_historial(cursor):
    eliminados = {}
    # Hijas antes que padres. No se desactivan restricciones ni se usa TRUNCATE.
    for tabla in HISTORIAL:
        cursor.execute('DELETE FROM ' + nombre_sql(tabla))
        eliminados[tabla] = cursor.rowcount
    cursor.execute("UPDATE estudiantes SET nivel_actual='literal'")
    return eliminados


def comprobar_preservacion(cursor, snapshot, limpieza):
    for tabla in ('usuarios', 'docentes', 'roles', *BANCO):
        cursor.execute('SELECT * FROM ' + nombre_sql(tabla))
        filas = cursor.fetchall()
        if any(fila not in filas for fila in snapshot[tabla]):
            raise RuntimeError(f'Se modificaron registros anteriores de {tabla}')
        if tabla in ('usuarios', 'docentes', 'roles') and len(filas) != len(snapshot[tabla]):
            raise RuntimeError(f'Cambió la cantidad de registros de {tabla}')
    cursor.execute('SELECT * FROM estudiantes')
    estudiantes = cursor.fetchall()
    esperados = [{**e, 'nivel_actual': 'literal'} for e in snapshot['estudiantes']] if limpieza else snapshot['estudiantes']
    if len(estudiantes) != len(esperados) or any(e not in estudiantes for e in esperados):
        raise RuntimeError('Las cuentas de estudiantes no se conservaron correctamente')
    for tabla in HISTORIAL:
        cursor.execute('SELECT * FROM ' + nombre_sql(tabla))
        filas = cursor.fetchall()
        if (limpieza and filas) or (not limpieza and (
            len(filas) != len(snapshot[tabla]) or any(f not in filas for f in snapshot[tabla])
        )):
            raise RuntimeError(f'Estado inesperado del historial: {tabla}')
    cursor.execute('''SELECT t.nivel,COUNT(*) cantidad FROM textos t WHERE NOT EXISTS
                      (SELECT 1 FROM versiones_lecturas v WHERE v.id_texto_original=t.id_texto)
                      GROUP BY t.nivel''')
    if {r['nivel']: r['cantidad'] for r in cursor.fetchall()} != {'literal': 10, 'inferencial': 9, 'crítico': 8}:
        raise RuntimeError('Cambió la cantidad de lecturas activas por nivel')


def ejecutar(aplicar=False, limpiar=False, simular=False):
    if (limpiar or simular) and not aplicar:
        raise ValueError('La limpieza y la simulación requieren --aplicar')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            planes = preparar_plan(cursor)
            print('Lecturas por publicar:', sum(existente is None for _, _, existente in planes))
            if not aplicar:
                print('Solo inspección: no se escribió ningún dato.')
                return
            conn.rollback()
            conn.begin()
            snapshot, respaldo = capturar_y_respaldar(conn, cursor)
            print('Respaldo privado:', respaldo)
            # Revalida tras adquirir bloqueos, antes de realizar cambios.
            planes = preparar_plan(cursor)
            publicadas = publicar(cursor, planes)
            eliminados = limpiar_historial(cursor) if limpiar else {}
            preparar_plan(cursor)  # Idempotencia y contenido publicado exacto.
            comprobar_preservacion(cursor, snapshot, limpiar)
            if simular:
                conn.rollback()
                print('Simulación verificada y revertida; no se confirmaron cambios.')
            else:
                conn.commit()
                print('Cambios confirmados.')
            print('Versiones publicadas:', publicadas)
            print('Historial eliminado' if not simular else 'Eliminación simulada', eliminados)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    parser.add_argument('--limpiar-historial', action='store_true')
    parser.add_argument('--simular', action='store_true')
    args = parser.parse_args()
    ejecutar(args.aplicar, args.limpiar_historial, args.simular)
