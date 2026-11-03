"""Comprueba sintaxis JavaScript y recursos HTML servidos por Flask, sin escribir datos."""
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / '.venv/Lib/site-packages')]
from lxml import html
from app import app

node = shutil.which('node')
if not node:
    candidato = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    node = str(candidato) if candidato.is_file() else None
if not node:
    raise SystemExit('Se necesita Node.js para verificar JavaScript.')
fallos = []
archivos = sorted((RAIZ / 'frontend').rglob('*.js'))
for archivo in archivos:
    r = subprocess.run([node, '--check', str(archivo)], capture_output=True, text=True)
    if r.returncode:
        fallos.append(f'{archivo.relative_to(RAIZ)}: {r.stderr}')
recursos = set()
for archivo in (RAIZ / 'frontend').rglob('*.html'):
    doc = html.fromstring(archivo.read_text(encoding='utf-8'))
    for valor in doc.xpath('//script/@src | //link[@rel="stylesheet"]/@href | //img/@src'):
        url = urlsplit(valor)
        if not url.scheme and not url.netloc and url.path.startswith('/'):
            recursos.add(url.path)
with app.test_client() as cliente:
    for ruta in sorted(recursos):
        respuesta = cliente.get(ruta)
        if respuesta.status_code != 200:
            fallos.append(f'{ruta}: HTTP {respuesta.status_code}')
print(f'JavaScript: {len(archivos)} archivos. Recursos enlazados: {len(recursos)}.')
if fallos:
    raise SystemExit('\n'.join(fallos))
print('Comprobaciones aprobadas.')
