"""Inspección reproducible de semántica inicial y pares de contraste seleccionados.

No sustituye la revisión en navegador ni acredita conformidad WCAG completa.
No conecta a la base de datos ni modifica cuentas.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / '.venv/Lib/site-packages'))
from lxml import html


def luminancia(color):
    rgb = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    lineal = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(v*p for v, p in zip(lineal, (.2126, .7152, .0722)))


def contraste(a, b):
    mayor, menor = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (mayor+.05)/(menor+.05)


def inspeccionar():
    paginas = []
    for archivo in sorted((RAIZ/'frontend').rglob('*.html')):
        contenido = archivo.read_text(encoding='utf-8')
        if '<html' not in contenido.lower():
            continue
        doc = html.document_fromstring(contenido)
        ids = doc.xpath('//@id')
        campos = []
        for campo in doc.xpath('//input|//select|//textarea'):
            if campo.get('type') in ('hidden', 'submit', 'button', 'reset'):
                continue
            nombre = campo.get('id', campo.tag)
            etiqueta = (campo.xpath('ancestor::label') or
                        doc.xpath('//label[@for=$id]', id=campo.get('id', '')) or
                        campo.get('aria-label'))
            referencias = campo.get('aria-labelledby', '').split()
            if referencias:
                etiqueta = all(ref in ids for ref in referencias)
            if not etiqueta:
                campos.append(nombre)
        saltos = doc.xpath('//a[contains(@class,"saltar-contenido")]/@href')
        destino = saltos and doc.xpath('//*[@id=$id]', id=saltos[0].lstrip('#'))
        comprobaciones = {
            'idioma_espanol': doc.get('lang', '').startswith('es'),
            'titulo_no_vacio': bool(doc.xpath('//title[normalize-space()]')),
            'viewport_sin_bloquear_zoom': bool(doc.xpath('//meta[@name="viewport"]')) and
                not re.search(r'user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?:\.0)?(?:[,"\s])', contenido),
            'ids_unicos': len(ids) == len(set(ids)),
            'salto_con_destino_enfocable': bool(destino) and destino[0].get('tabindex') == '-1',
            'campos_con_etiqueta': not campos,
            'imagenes_con_alternativa': not doc.xpath('//img[not(@alt)]'),
            'sin_tabindex_positivo': not any(int(v) > 0 for v in doc.xpath('//@tabindex')),
            'estilos_accesibilidad_al_final': doc.xpath('//link[@rel="stylesheet"]/@href')[-1:] == ['/accesibilidad.css'],
            'cabeceras_tabla_con_scope': not doc.xpath('//th[not(@scope)]'),
        }
        paginas.append({'archivo': archivo.relative_to(RAIZ).as_posix(),
                        'sha256': hashlib.sha256(archivo.read_bytes()).hexdigest(),
                        'comprobaciones': comprobaciones, 'campos_sin_etiqueta': campos})

    css = (RAIZ/'frontend/common/accesibilidad.css').read_text(encoding='utf-8')
    variables = dict(re.findall(r'(--[\w-]+):\s*(#[0-9a-fA-F]{6})', css))
    pares = [
        ('Texto secundario / blanco', variables['--texto-secundario-accesible'], '#ffffff', 4.5),
        ('Texto secundario / azul claro', variables['--texto-secundario-accesible'], '#f1f6ff', 4.5),
        ('Botón azul / blanco', variables['--azul-accesible'], '#ffffff', 4.5),
        ('Botón violeta / blanco', variables['--violeta-accesible'], '#ffffff', 4.5),
        ('Foco / blanco', variables['--foco-accesible'], '#ffffff', 3),
        ('Marcador de posición / blanco', '#637086', '#ffffff', 4.5),
        ('Error / blanco', '#b42338', '#ffffff', 4.5),
        ('Botón verde / blanco', '#15803d', '#ffffff', 4.5),
        ('Acción naranja / texto oscuro', '#422006', '#f59e0b', 4.5),
        ('Borde de campo / blanco', '#7b8799', '#ffffff', 3),
    ]
    colores = [{'par': nombre, 'color_1': a, 'color_2': b, 'relacion': round(contraste(a,b), 3),
                'minimo': minimo, 'aprobado': contraste(a,b) >= minimo}
               for nombre, a, b, minimo in pares]
    # Muestras de la interpolación sRGB del gradiente principal, no solo extremos.
    a, b = variables['--azul-accesible'], variables['--violeta-accesible']
    muestras = []
    for paso in range(101):
        rgb = [round(int(a[i:i+2],16)*(1-paso/100)+int(b[i:i+2],16)*paso/100) for i in (1,3,5)]
        muestras.append(contraste('#'+''.join(f'{v:02x}' for v in rgb), '#ffffff'))
    return {'alcance': 'HTML inicial de siete páginas y pares de colores seleccionados. '
            'Los estados dinámicos se verifican por separado en navegador. '
            'No es una certificación ni una evaluación completa de conformidad WCAG.',
            'paginas': paginas, 'contrastes': colores,
            'gradiente_principal': {'muestras': 101, 'contraste_minimo': round(min(muestras),3),
                                    'aprobado': min(muestras) >= 4.5},
            'aprobado': all(all(p['comprobaciones'].values()) for p in paginas)
                        and all(c['aprobado'] for c in colores) and min(muestras) >= 4.5}


if __name__ == '__main__':
    salida = RAIZ/'docs/evidencias_accesibilidad'
    salida.mkdir(parents=True, exist_ok=True)
    datos = inspeccionar()
    (salida/'auditoria_estatica.json').write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(datos, ensure_ascii=False, indent=2))
    sys.exit(0 if datos['aprobado'] else 1)
