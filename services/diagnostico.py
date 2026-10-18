"""Diagnóstico original de ubicación inicial para quinto de primaria.

Tres preguntas por proceso lector. No es un instrumento estandarizado ni
validado por especialistas. Las claves y justificaciones nunca se publican.
"""
from services.lectura import entero_positivo

DIAGNOSTICO_INICIAL = {
    'version': 'primaria5_v2',
    'titulo': 'Diagnóstico inicial de comprensión lectora',
    'instrucciones': 'Lee cada texto y marca una alternativa por pregunta. Puedes volver a leer los textos antes de finalizar.',
    'lecturas': [
        {
            'id': 1,
            'titulo': 'Un nuevo lugar para leer',
            'contenido': [
                'Un lunes, el aula de quinto grado recibió una caja de libros de la biblioteca escolar. '
                'La profesora propuso organizar un rincón de lectura para el recreo. Camila quería '
                'colocarlo en el patio, cerca de la cancha, mientras que Mateo prefería el corredor '
                'techado junto al aula. El grupo decidió probar primero en el patio.',
                'Durante el primer recreo, varios estudiantes se acercaron a los libros. Sin embargo, '
                'algunos volvían a empezar el mismo párrafo cada vez que sus compañeros gritaban un gol. '
                'Al terminar, dos libros habían quedado en el suelo. Al día siguiente, encontraron '
                'la caja húmeda por la llovizna de la noche. Algunos propusieron guardar los libros '
                'y suspender la actividad.',
                'Camila observó los libros y sugirió llevar el rincón al corredor techado. Mateo '
                'propuso anotar el nombre de quien se llevara un libro y revisarlo al devolverlo. '
                'La clase aceptó ambas ideas. También acordaron guardar la caja dentro del aula '
                'al finalizar la jornada.',
                'El viernes, Inés leyó un cuento en voz alta a dos compañeros. Otros eligieron '
                'libros sobre animales y viajes. Antes de volver a clases, varios preguntaron '
                'si la biblioteca podía prestarles títulos diferentes para la semana siguiente.',
            ],
        },
        {
            'id': 2,
            'titulo': 'Una lonchera con menos residuos',
            'contenido': [
                'Después del recreo, las envolturas y las bolsas de un solo uso llenaban parte '
                'de los tachos de un colegio. Por eso, quinto grado preparó una campaña para '
                'reducir los residuos de las loncheras. La propuesta incluía llevar los alimentos '
                'en recipientes lavables y el agua en un tomatodo que pudiera utilizarse muchas veces.',
                'La campaña no pedía comprar todos los útiles de nuevo. Cada familia podía utilizar '
                'los recipientes adecuados que ya tuviera en casa, limpios y en buen estado. '
                'Si todavía no contaba con ellos, podía acordar otros cambios con la profesora, '
                'como evitar colocar una bolsa adicional a un producto que ya venía envuelto.',
                'Para conocer los resultados, cada aula anotaría diariamente cuántas envolturas '
                'desechables quedaban después del recreo y cuántos estudiantes habían asistido. '
                'El registro se haría antes de comenzar la campaña y durante las semanas siguientes.',
                'Tras la primera semana, quinto A registró menos envolturas que al inicio. '
                'Todavía no se habían reunido los registros de las otras aulas. La profesora '
                'propuso continuar observando los resultados antes de presentar las conclusiones '
                'de la campaña a todo el colegio.',
            ],
        },
    ],
    'preguntas': [
        {
            'id': 101, 'id_lectura': 1, 'tipo': 'literal',
            'pregunta': '¿Dónde quedó instalado el rincón de lectura después de los cambios?',
            'opciones': [
                {'id': 1, 'texto': 'En el patio, junto a la cancha.'},
                {'id': 2, 'texto': 'En el corredor techado, junto al aula.'},
                {'id': 3, 'texto': 'En la biblioteca, junto a la entrada.'},
            ],
            'respuesta_correcta': 2,
            'justificacion': 'Camila sugirió trasladarlo al corredor techado y la clase aceptó la idea.',
        },
        {
            'id': 102, 'id_lectura': 1, 'tipo': 'literal',
            'pregunta': '¿Qué acordaron hacer con la caja al finalizar la jornada?',
            'opciones': [
                {'id': 1, 'texto': 'Guardarla dentro del aula.'},
                {'id': 2, 'texto': 'Llevarla de vuelta a la biblioteca.'},
                {'id': 3, 'texto': 'Dejarla debajo de un banco del patio.'},
            ],
            'respuesta_correcta': 1,
            'justificacion': 'El tercer párrafo expresa el acuerdo de guardar la caja dentro del aula.',
        },
        {
            'id': 103, 'id_lectura': 1, 'tipo': 'inferencial',
            'pregunta': '¿Por qué algunos estudiantes volvían a empezar el mismo párrafo en el patio?',
            'opciones': [
                {'id': 1, 'texto': 'Porque querían leer el párrafo en voz alta a sus compañeros.'},
                {'id': 2, 'texto': 'Porque el párrafo les indicaba cómo jugar en la cancha.'},
                {'id': 3, 'texto': 'Porque los gritos del partido interrumpían su concentración.'},
            ],
            'respuesta_correcta': 3,
            'justificacion': 'Se relaciona la repetición del párrafo con los gritos de gol, sin que el texto nombre la distracción.',
        },
        {
            'id': 104, 'id_lectura': 1, 'tipo': 'inferencial',
            'pregunta': '¿Qué permite deducir el pedido de títulos diferentes para la siguiente semana?',
            'opciones': [
                {'id': 1, 'texto': 'Que varios estudiantes querían continuar explorando otras lecturas.'},
                {'id': 2, 'texto': 'Que la biblioteca había pedido devolver todos los libros ese viernes.'},
                {'id': 3, 'texto': 'Que la clase prefería reemplazar la lectura por los partidos del patio.'},
            ],
            'respuesta_correcta': 1,
            'justificacion': 'Pedir nuevas lecturas para la semana siguiente permite inferir interés en continuar, no una obligación de devolución.',
        },
        {
            'id': 105, 'id_lectura': 1, 'tipo': 'crítico',
            'pregunta': '¿Qué argumento sustenta mejor trasladar el rincón en vez de suspenderlo?',
            'opciones': [
                {'id': 1, 'texto': 'Cerrar la actividad habría evitado tener que organizar los préstamos.'},
                {'id': 2, 'texto': 'El patio debía conservarse porque había sido la primera elección del grupo.'},
                {'id': 3, 'texto': 'El traslado permitía continuar leyendo y proteger mejor los libros.'},
            ],
            'respuesta_correcta': 3,
            'justificacion': 'Se evalúan las alternativas frente a dos necesidades del relato: conservar la actividad y cuidar los libros.',
        },
        {
            'id': 106, 'id_lectura': 2, 'tipo': 'literal',
            'pregunta': '¿Qué dos datos debía anotar cada aula diariamente?',
            'opciones': [
                {'id': 1, 'texto': 'El precio de los recipientes y el número de loncheras nuevas.'},
                {'id': 2, 'texto': 'La cantidad de envolturas desechables y de estudiantes asistentes.'},
                {'id': 3, 'texto': 'El peso de los alimentos y la cantidad de agua que bebían.'},
            ],
            'respuesta_correcta': 2,
            'justificacion': 'Ambos datos se indican explícitamente en el tercer párrafo.',
        },
        {
            'id': 107, 'id_lectura': 2, 'tipo': 'inferencial',
            'pregunta': '¿Por qué ayudaría registrar también cuántos estudiantes asistieron?',
            'opciones': [
                {'id': 1, 'texto': 'Porque la asistencia indicaría cuántas familias compraron recipientes.'},
                {'id': 2, 'texto': 'Porque permitiría reemplazar el recuento de envolturas por una lista de nombres.'},
                {'id': 3, 'texto': 'Porque menos asistentes también podrían producir menos envolturas.'},
            ],
            'respuesta_correcta': 3,
            'justificacion': 'Se deduce una explicación alternativa para la disminución de residuos al relacionar asistencia y recuento.',
        },
        {
            'id': 108, 'id_lectura': 2, 'tipo': 'crítico',
            'pregunta': '¿Qué conclusión está mejor sustentada por los resultados disponibles?',
            'opciones': [
                {'id': 1, 'texto': 'Quinto A registró una disminución inicial; falta revisar otras aulas y más días.'},
                {'id': 2, 'texto': 'Todas las aulas del colegio redujeron sus residuos durante la primera semana.'},
                {'id': 3, 'texto': 'Quinto A mantendrá la misma disminución durante todas las semanas siguientes.'},
            ],
            'respuesta_correcta': 1,
            'justificacion': 'Se juzga el alcance de la evidencia y se descartan generalizaciones sobre aulas o periodos no observados.',
        },
        {
            'id': 109, 'id_lectura': 2, 'tipo': 'crítico',
            'pregunta': '¿Qué propuesta cumple mejor el propósito de la campaña sin exigir nuevas compras?',
            'opciones': [
                {'id': 1, 'texto': 'Pedir el mismo modelo de tomatodo para revisar las loncheras con rapidez.'},
                {'id': 2, 'texto': 'Aprovechar recipientes disponibles y acordar cambios posibles con cada familia.'},
                {'id': 3, 'texto': 'Comprar recipientes nuevos para premiar a quienes se sumen primero.'},
            ],
            'respuesta_correcta': 2,
            'justificacion': 'Se evalúa la coherencia de las propuestas con reducir residuos y respetar las posibilidades familiares.',
        },
    ],
}


def contenido_publico():
    return {
        **{k: DIAGNOSTICO_INICIAL[k] for k in ('version', 'titulo', 'instrucciones', 'lecturas')},
        'preguntas': [
            {k: p[k] for k in ('id', 'id_lectura', 'pregunta', 'opciones')}
            for p in DIAGNOSTICO_INICIAL['preguntas']
        ],
    }


def evaluar_respuestas_diagnostico(respuestas):
    """Exige las nueve preguntas y una opción propia; no recibe aciertos del cliente."""
    if not isinstance(respuestas, list):
        raise ValueError('respuestas debe ser una lista')
    preguntas = {p['id']: p for p in DIAGNOSTICO_INICIAL['preguntas']}
    por_id = {}
    for item in respuestas:
        if not isinstance(item, dict) or set(item) != {'id', 'id_opcion'}:
            raise ValueError('Cada respuesta debe incluir únicamente id e id_opcion')
        pid = entero_positivo(item['id'], 'ID de pregunta')
        opcion = entero_positivo(item['id_opcion'], 'ID de opción')
        if pid in por_id:
            raise ValueError('No se permiten preguntas duplicadas')
        if pid not in preguntas or opcion not in {o['id'] for o in preguntas[pid]['opciones']}:
            raise ValueError('La opción o pregunta no pertenece al diagnóstico')
        por_id[pid] = opcion
    if set(por_id) != set(preguntas):
        raise ValueError('Debes responder exactamente las nueve preguntas del diagnóstico')
    return [por_id[p['id']] == p['respuesta_correcta'] for p in DIAGNOSTICO_INICIAL['preguntas']]


def detalle_evaluacion(respuestas, resultados):
    por_id = {int(r['id']): int(r['id_opcion']) for r in respuestas}
    detalle, por_nivel = [], {}
    for p, correcta in zip(DIAGNOSTICO_INICIAL['preguntas'], resultados):
        detalle.append({'id': p['id'], 'id_opcion': por_id[p['id']], 'tipo': p['tipo'], 'es_correcta': correcta})
        datos = por_nivel.setdefault(p['tipo'], {'total': 0, 'correctas': 0})
        datos['total'] += 1
        datos['correctas'] += int(correcta)
    for datos in por_nivel.values():
        datos['porcentaje'] = round(datos['correctas'] * 100 / datos['total'], 2)
    return detalle, por_nivel
