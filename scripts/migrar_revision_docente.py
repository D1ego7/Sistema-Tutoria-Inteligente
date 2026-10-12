"""Migración local idempotente: respaldo, versionado y revisión cualitativa.

Ejecutar con el servidor detenido. El respaldo SQL contiene datos privados y
queda en respaldos/, excluido de Git. DDL idempotente; el banco se publica en
una sola transacción. No se modifica ningún intento ni diagnóstico existente.
"""
import sys
from pathlib import Path
from datetime import datetime

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / '.venv' / 'Lib' / 'site-packages'))
sys.path.insert(0, str(RAIZ))
from config import get_db_connection
from services.banco_versionado import CRITICAS, AJUSTES

ESQUEMA = [
    '''CREATE TABLE IF NOT EXISTS versiones_lecturas (
       id_texto_original INT PRIMARY KEY, id_texto_actual INT NOT NULL UNIQUE,
       fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (id_texto_original) REFERENCES textos(id_texto),
       FOREIGN KEY (id_texto_actual) REFERENCES textos(id_texto)) ENGINE=InnoDB''',
    '''CREATE TABLE IF NOT EXISTS preguntas_revision (
       id_pregunta INT PRIMARY KEY, id_pregunta_original INT NOT NULL,
       FOREIGN KEY (id_pregunta) REFERENCES preguntas(id_pregunta),
       FOREIGN KEY (id_pregunta_original) REFERENCES preguntas(id_pregunta)) ENGINE=InnoDB''',
    '''CREATE TABLE IF NOT EXISTS revisiones_criticas (
       id_respuesta_est INT PRIMARY KEY, id_usuario_revisor INT NULL,
       pertinencia BOOLEAN NULL, sustento BOOLEAN NULL, coherencia BOOLEAN NULL,
       devolucion VARCHAR(500) NULL, fecha_revision DATETIME NULL,
       FOREIGN KEY (id_respuesta_est) REFERENCES respuestas_estudiante(id_respuesta_est),
       FOREIGN KEY (id_usuario_revisor) REFERENCES usuarios(id_usuario)) ENGINE=InnoDB''',
]

def respaldar(conn):
    carpeta = RAIZ / 'respaldos'
    carpeta.mkdir(exist_ok=True)
    archivo = carpeta / ('antes_revision_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.sql')
    with conn.cursor() as c, archivo.open('x', encoding='utf-8') as f:
        c.execute('SHOW TABLES')
        tablas = [next(iter(r.values())) for r in c.fetchall()]
        f.write('SET FOREIGN_KEY_CHECKS=0;\n')
        for tabla in tablas:
            nombre = '`' + tabla.replace('`', '``') + '`'
            c.execute('SHOW CREATE TABLE ' + nombre)
            ddl = c.fetchone()['Create Table']
            f.write('DROP TABLE IF EXISTS ' + nombre + ';\n' + ddl + ';\n')
            c.execute('SELECT * FROM ' + nombre)
            for r in c.fetchall():
                columnas = ','.join('`'+k.replace('`','``')+'`' for k in r)
                valores = ','.join(conn.escape(v) for v in r.values())
                f.write('INSERT INTO '+nombre+' ('+columnas+') VALUES ('+valores+');\n')
        f.write('SET FOREIGN_KEY_CHECKS=1;\n')
    conn.rollback()
    return archivo

def migrar():
    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='respuestas_estudiante' AND COLUMN_NAME='es_correcta'")
            if c.fetchone()['IS_NULLABLE'] != 'YES':
                raise RuntimeError('es_correcta debe admitir NULL para respuestas pendientes')
        print('Respaldo local:', respaldar(conn))
        with conn.cursor() as c:
            for ddl in ESQUEMA: c.execute(ddl)
        conn.begin()
        creadas = 0
        with conn.cursor() as c:
            c.execute('SELECT * FROM textos WHERE id_texto IN (10,11,12,15,29,30,31,32,33,34,35) ORDER BY id_texto FOR UPDATE')
            textos = c.fetchall()
            if len(textos) != 11: raise RuntimeError('El banco no coincide con la revisión prevista')
            for t in textos:
                c.execute('SELECT id_texto_actual FROM versiones_lecturas WHERE id_texto_original=%s', (t['id_texto'],))
                if c.fetchone(): continue
                c.execute('SELECT p.*,rc.respuesta FROM preguntas p LEFT JOIN respuestas_correctas rc ON rc.id_pregunta=p.id_pregunta WHERE p.id_texto=%s ORDER BY p.orden', (t['id_texto'],))
                preguntas = c.fetchall()
                if len(preguntas) != 3: raise RuntimeError('Lectura sin tres preguntas únicas')
                contenido = t['contenido']
                if t['id_texto']==10:
                    if 'amused' not in contenido: raise RuntimeError('El texto 10 cambió; revisar antes de migrar')
                    contenido = contenido.replace('amused','divertido')
                c.execute('INSERT INTO textos (titulo,contenido,nivel) VALUES (%s,%s,%s)', (t['titulo'],contenido,t['nivel']))
                tid = c.lastrowid
                for p in preguntas:
                    pid = p['id_pregunta']
                    enunciado, clave = (CRITICAS.get(pid) or AJUSTES.get(pid) or (p['enunciado'],p['respuesta']))
                    if pid in CRITICAS and (p['tipo']!='crítico' or p['tipo_respuesta']!='texto'):
                        raise RuntimeError('La pregunta crítica original cambió')
                    c.execute('INSERT INTO preguntas (id_texto,enunciado,tipo,tipo_respuesta,orden) VALUES (%s,%s,%s,%s,%s)', (tid,enunciado,p['tipo'],p['tipo_respuesta'],p['orden']))
                    nuevo = c.lastrowid
                    c.execute('INSERT INTO respuestas_correctas (id_pregunta,respuesta) VALUES (%s,%s)', (nuevo,clave))
                    c.execute('INSERT INTO opciones_pregunta (id_pregunta,texto_opcion,es_correcta) SELECT %s,texto_opcion,es_correcta FROM opciones_pregunta WHERE id_pregunta=%s ORDER BY id_opcion', (nuevo,pid))
                    if pid in CRITICAS:
                        c.execute('INSERT INTO preguntas_revision VALUES (%s,%s)', (nuevo,pid))
                c.execute('INSERT INTO versiones_lecturas (id_texto_original,id_texto_actual) VALUES (%s,%s)', (t['id_texto'],tid))
                creadas += 1
        conn.commit()
        print('Lecturas nuevas publicadas:', creadas)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__': migrar()
