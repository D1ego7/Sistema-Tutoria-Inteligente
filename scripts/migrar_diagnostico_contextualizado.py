"""Almacenamiento del nuevo diagnóstico sin alterar resultados previos.

Con --aplicar respalda la base, conserva decimales en el porcentaje y crea una
tabla de detalle para nuevas evaluaciones. El DDL de MariaDB no se revierte
mediante rollback; ejecutar con el servidor detenido. Sin argumentos inspecciona.
"""
import argparse
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / '.venv' / 'Lib' / 'site-packages'))
sys.path.insert(0, str(RAIZ))
from config import get_db_connection
from scripts.migrar_revision_docente import respaldar

DDL = '''CREATE TABLE IF NOT EXISTS diagnostico_detalle (
    id_diagnostico INT PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    instrumento_json LONGTEXT NOT NULL,
    respuestas_json LONGTEXT NOT NULL,
    FOREIGN KEY (id_diagnostico) REFERENCES diagnostico(id_diagnostico)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''


def migrar(aplicar=False):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM diagnostico ORDER BY id_diagnostico')
            anteriores = cursor.fetchall()
            if any(r['puntaje'] is not None and not 0 <= r['puntaje'] <= 100 for r in anteriores):
                raise RuntimeError('Hay puntajes fuera de rango; revisar antes de migrar')
            cursor.execute("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='diagnostico' AND COLUMN_NAME='puntaje'")
            tipo = cursor.fetchone()['COLUMN_TYPE'].lower()
            cursor.execute("SELECT COUNT(*) n FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='diagnostico_detalle'")
            existe = cursor.fetchone()['n'] == 1
            print('Diagnósticos previos que se conservarán:', len(anteriores))
            print('Porcentaje decimal:', tipo == 'decimal(5,2)', 'Tabla de detalle:', existe)
            if not aplicar:
                return
            print('Respaldo privado:', respaldar(conn))
            if tipo != 'decimal(5,2)':
                cursor.execute('ALTER TABLE diagnostico MODIFY COLUMN puntaje DECIMAL(5,2) NULL')
            cursor.execute(DDL)
            cursor.execute('SELECT * FROM diagnostico ORDER BY id_diagnostico')
            if cursor.fetchall() != anteriores:
                raise RuntimeError('La comprobación de conservación del diagnóstico no coincide')
            conn.commit()
            print('Esquema preparado; diagnósticos anteriores conservados.')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    migrar(parser.parse_args().aplicar)
