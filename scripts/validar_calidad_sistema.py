"""Genera evidencias reproducibles de pruebas y rendimiento sin alterar cuentas.

Las pruebas de integración revierten sus transacciones. La medición HTTP usa
solamente consultas GET contra un servidor efímero enlazado a 127.0.0.1.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / '.venv/Lib/site-packages'), str(RAIZ / 'tests'), str(RAIZ)]

import argparse
import contextlib
import hashlib
import io
import json
import logging
import math
import os
import platform
import statistics
import subprocess
import threading
import time
import unittest
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from lxml import html


class ResultadoDetallado(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.casos = []
        self.inicios = {}

    def startTest(self, test):
        self.inicios[test.id()] = time.perf_counter()
        super().startTest(test)

    def registrar(self, test, estado, detalle=''):
        self.casos.append({'caso': test.id(), 'resultado': estado, 'detalle': detalle,
                           'segundos': round(time.perf_counter() - self.inicios.get(test.id(), time.perf_counter()), 6)})

    def addSuccess(self, test): super().addSuccess(test); self.registrar(test, 'aprobado')
    def addFailure(self, test, err): super().addFailure(test, err); self.registrar(test, 'fallido', self._exc_info_to_string(err, test))
    def addError(self, test, err): super().addError(test, err); self.registrar(test, 'error', self._exc_info_to_string(err, test))
    def addSkip(self, test, reason): super().addSkip(test, reason); self.registrar(test, 'omitido', reason)


def ejecutar_pruebas(salida, node):
    os.environ['RUN_DB_INTEGRATION'] = '1'
    registro = io.StringIO()
    manejador = logging.StreamHandler(registro)
    logging.getLogger().addHandler(manejador)
    try:
        suite = unittest.defaultTestLoader.discover(str(RAIZ / 'tests'), pattern='test_*.py')
        with contextlib.redirect_stdout(registro), contextlib.redirect_stderr(registro):
            resultado = unittest.TextTestRunner(stream=registro, verbosity=2, resultclass=ResultadoDetallado).run(suite)
    finally:
        logging.getLogger().removeHandler(manejador)
    (salida / 'pruebas_python.txt').write_text(registro.getvalue(), encoding='utf-8')
    archivos = sorted(str(p) for p in (RAIZ / 'tests').glob('*.test.cjs'))
    proceso = subprocess.run([node, '--test', '--test-reporter=junit', *archivos], cwd=RAIZ, capture_output=True, text=True, encoding='utf-8')
    (salida / 'pruebas_interfaz.xml').write_text(proceso.stdout, encoding='utf-8')
    if proceso.stderr: (salida / 'pruebas_interfaz_errores.txt').write_text(proceso.stderr, encoding='utf-8')
    raiz = ET.fromstring(proceso.stdout)
    casos_js = [{'caso': c.get('name'), 'resultado': 'fallido' if c.find('failure') is not None or c.find('error') is not None
                 else 'omitido' if c.find('skipped') is not None else 'aprobado', 'segundos': float(c.get('time', '0'))}
                for c in raiz.iter('testcase')]
    datos = {'python': resultado.casos, 'javascript': casos_js,
             'correcto': resultado.wasSuccessful() and not resultado.skipped and proceso.returncode == 0}
    (salida / 'casos_prueba.json').write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')
    return datos


def auditar_html():
    datos = []
    for archivo in sorted((RAIZ / 'frontend').rglob('*.html')):
        contenido = archivo.read_text(encoding='utf-8')
        if '<html' not in contenido.lower(): continue  # El encabezado es un fragmento.
        s = html.document_fromstring(contenido)
        sin_etiqueta = []
        for campo in s.xpath('//input|//select|//textarea'):
            if campo.get('type') in ('hidden', 'submit', 'button', 'reset'): continue
            identificado = campo.get('id') and s.xpath('//label[@for=$id]', id=campo.get('id'))
            if not (identificado or campo.xpath('ancestor::label') or campo.get('aria-label') or campo.get('aria-labelledby')):
                sin_etiqueta.append(campo.get('id', campo.tag))
        datos.append({'archivo': str(archivo.relative_to(RAIZ)).replace('\\', '/'),
                      'idioma_es': s.get('lang', '').startswith('es'),
                      'titulo': bool(s.xpath('//title/text()')),
                      'campos_sin_etiqueta': sin_etiqueta,
                      'imagenes_sin_alternativa': len(s.xpath('//img[not(@alt)]'))})
    return {'alcance': 'Inspección estática de HTML inicial. No acredita conformidad WCAG completa ni interacción asistida.', 'paginas': datos}


def medir_http():
    import app as aplicacion
    from config import get_db_connection
    from flask_jwt_extended import create_access_token
    from werkzeug.serving import make_server, WSGIRequestHandler

    conexion = get_db_connection()
    try:
        with conexion.cursor() as c:
            c.execute('SELECT VERSION() version'); version_bd = c.fetchone()['version']
            c.execute('SELECT id_usuario,id_rol FROM usuarios WHERE id_rol IN (1,2,3) ORDER BY id_usuario')
            usuarios = c.fetchall()
            c.execute('SELECT id_estudiante FROM estudiantes ORDER BY id_estudiante LIMIT 1')
            sid = c.fetchone()['id_estudiante']
    finally: conexion.close()
    tokens = {}
    with aplicacion.app.app_context():
        for rol in (1, 2, 3):
            usuario = next(u for u in usuarios if u['id_rol'] == rol)
            tokens[rol] = create_access_token(identity=str(usuario['id_usuario']), additional_claims={'rol': rol})

    class Silencioso(WSGIRequestHandler):
        def log(self, *args, **kwargs): pass
    servidor = make_server('127.0.0.1', 0, aplicacion.app, threaded=True, request_handler=Silencioso)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True); hilo.start()
    base = f'http://127.0.0.1:{servidor.server_port}'
    rutas = [('Protección de diagnóstico completado', '/diagnostico-preguntas', 1, 409),
             ('Inicio del estudiante', '/api/estudiante/dashboard', 1, 200),
             ('Lista del seguimiento', '/api/docente/estudiantes', 2, 200),
             ('Detalle del seguimiento', f'/api/docente/estudiantes/{sid}', 2, 200),
             ('Resumen administrativo', '/api/administrador/resumen', 3, 200),
             ('Lista administrativa', '/api/administrador/usuarios?rol=1', 3, 200)]
    resultados = []
    try:
        for nombre, ruta, rol, esperado in rutas:
            def solicitar(_=None):
                peticion = urllib.request.Request(base + ruta, headers={'Authorization': 'Bearer ' + tokens[rol]})
                inicio = time.perf_counter()
                try:
                    with urllib.request.urlopen(peticion, timeout=10) as r:
                        r.read(); estado = r.status
                except urllib.error.HTTPError as error:
                    estado = error.code; error.read(); error.close()
                except Exception: estado = 0
                return (time.perf_counter() - inicio) * 1000, estado
            for _ in range(5): solicitar()
            for modo, n, trabajadores in [('Secuencial', 30, 1), ('Concurrente', 40, 4)]:
                inicio = time.perf_counter()
                with ThreadPoolExecutor(max_workers=trabajadores) as ejecutor:
                    muestras = list(ejecutor.map(solicitar, range(n)))
                segundos = time.perf_counter() - inicio
                tiempos = sorted(t for t, _ in muestras)
                errores = sum(estado != esperado for _, estado in muestras)
                p95 = tiempos[math.ceil(n * .95) - 1]
                resultados.append({'escenario': nombre, 'modo': modo, 'muestras': n, 'concurrencia': trabajadores,
                    'estado_esperado': esperado, 'media_ms': round(statistics.mean(tiempos), 2), 'p95_ms': round(p95, 2),
                    'maximo_ms': round(max(tiempos), 2), 'errores': errores, 'solicitudes_segundo': round(n / segundos, 2),
                    'cumple_umbral_proyecto': errores == 0 and p95 <= 1000})
    finally:
        servidor.shutdown(); hilo.join(); servidor.server_close()
    return {'entorno': {'sistema': platform.system(), 'python': platform.python_version(),
                        'procesadores_logicos': os.cpu_count(), 'mariadb': version_bd},
            'metodo': 'HTTP real sobre servidor WSGI de desarrollo en loopback; 5 calentamientos y 30/40 solicitudes por escenario. Solo GET.',
            'umbral': 'Criterio técnico del proyecto fijado antes de medir: p95 <= 1000 ms y cero errores. ISO no establece este valor.',
            'alcance': 'Caracteriza este equipo y carga reducida. No mide navegador, red escolar, capacidad máxima ni usuarios reales.',
            'resultados': resultados}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--salida', type=Path, required=True)
    parser.add_argument('--node', required=True)
    args = parser.parse_args(); args.salida.mkdir(parents=True, exist_ok=True)
    pruebas = ejecutar_pruebas(args.salida, args.node)
    rendimiento = medir_http()
    accesibilidad = auditar_html()
    archivos = [RAIZ / 'app.py', *sorted((RAIZ / 'services').glob('*.py')), *sorted((RAIZ / 'frontend').rglob('*'))]
    manifiesto = {str(p.relative_to(RAIZ)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in archivos if p.is_file() and p.suffix in ('.py', '.html', '.js', '.css')}
    for nombre, datos in [('rendimiento', rendimiento), ('accesibilidad', accesibilidad), ('version_evaluada', manifiesto)]:
        (args.salida / (nombre + '.json')).write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'python': len(pruebas['python']), 'javascript': len(pruebas['javascript']),
                      'pruebas_aprobadas': pruebas['correcto'], 'rendimiento': rendimiento['resultados'],
                      'accesibilidad': accesibilidad['paginas']}, ensure_ascii=False, indent=2))
    if not pruebas['correcto']: raise SystemExit(1)


if __name__ == '__main__': main()
