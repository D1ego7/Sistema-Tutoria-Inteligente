"""Variantes acotadas del banco actual; no son una evaluación semántica libre.

Cada registro vincula enunciado, capacidad y clave. Si cambia cualquiera,
se usa únicamente la clave configurada hasta revisar el catálogo.
Se excluyen opiniones críticas y preguntas con enunciado/clave ambiguos.
"""
from services.tutoring import normalizar_texto


# (Enunciado, tipo, clave vigente, redacciones equivalentes explícitas).
REGISTROS = [
    ('¿Por qué el ratón tendría motivos para ayudar al león?', 'inferencial',
     'porque el león lo había liberado y él le había prometido ayudarlo', [
         'porque el león lo liberó y el ratón prometió ayudarlo',
         'porque le debía un favor al león y había prometido ayudarlo']),
    ('Según el texto, ¿qué tres aspectos mejora la lectura?', 'literal',
     'concentración vocabulario y creatividad', [
         'concentración creatividad y vocabulario', 'vocabulario concentración y creatividad',
         'vocabulario creatividad y concentración', 'creatividad concentración y vocabulario',
         'creatividad vocabulario y concentración', 'la concentración el vocabulario y la creatividad',
         'concentración vocabulario creatividad', 'concentración creatividad vocabulario',
         'vocabulario concentración creatividad', 'vocabulario creatividad concentración',
         'creatividad concentración vocabulario', 'creatividad vocabulario concentración']),
    ('¿Por qué lo respetaban todos los animales?', 'literal',
     'porque era inteligente y encontraba soluciones', [
         'porque siempre encontraba soluciones creativas a los problemas',
         'porque encontraba soluciones creativas a los problemas',
         'porque encontraba soluciones a los problemas',
         'porque era inteligente y resolvía problemas']),
    ('¿Quién ayuda al autor con las tareas?', 'literal', 'su hermano mayor', [
        'el hermano mayor', 'su hermano mayor lo ayuda', 'lo ayuda su hermano mayor']),
    ('¿A qué hora abre la biblioteca?', 'literal', 'a las ocho', [
        'a las ocho de la mañana', 'ocho de la mañana', 'a las 8', 'a las 8 de la mañana',
        '8 de la mañana', '8:00', 'a las 8:00', 'a las 8:00 de la mañana',
        'la biblioteca abre a las ocho de la mañana']),
    ('¿Quién ayudó a regar las plantas?', 'literal', 'el profesor miguel', [
        'Miguel', 'el profesor Miguel ayudó', 'Miguel ayudó a regar las plantas']),
    ('¿Qué recibió Lucía al final?', 'literal', 'un diploma', [
        'un diploma por su participación', 'recibió un diploma', 'Lucía recibió un diploma']),
    ('¿Por qué Diego tomó apuntes?', 'literal', 'para preparar una exposición', [
        'porque debía preparar una exposición', 'porque tenía que preparar una exposición',
        'para preparar una exposición para su clase', 'porque debía preparar una exposición para su clase']),
    ('¿Cuándo participarán en el campeonato?', 'literal', 'el próximo viernes', [
        'próximo viernes', 'el viernes próximo', 'participarán el próximo viernes']),
    ('¿Quién felicitó a los alumnos?', 'literal', 'la directora', [
        'la directora de la escuela', 'la directora del colegio', 'la directora los felicitó']),
    ('¿Quién recomienda desayunar frutas?', 'literal', 'la profesora elena', [
        'Elena', 'la profesora Elena recomienda desayunar frutas']),
    ('¿Cuál es la lección principal de la historia?', 'inferencial',
     'que no importa el tamaño, todos podemos ayudar', [
         'no importa el tamaño todos podemos ayudar',
         'todos podemos ayudar sin importar nuestro tamaño',
         'todos pueden ayudar sin importar su tamaño',
         'los pequeños también pueden ayudar a los grandes']),
    ('¿Qué pasaría sin la fotosíntesis?', 'inferencial', 'no habría vida en el planeta', [
        'no habría vida en nuestro planeta', 'no habría vida en la Tierra']),
    ('¿Dónde dejó Sofía su cuaderno?', 'inferencial', 'en la biblioteca', [
        'en la mesa de la biblioteca', 'sobre la mesa de la biblioteca',
        'lo dejó en la biblioteca', 'Sofía lo dejó en la biblioteca']),
    ('¿Cómo se sintió Sofía al recuperar su cuaderno?', 'inferencial', 'más tranquila', [
        'tranquila', 'se sintió más tranquila', 'Sofía se sintió más tranquila']),
    ('¿Por qué limpiaron la cancha?', 'inferencial', 'para evitar resbalones', [
        'para no resbalarse', 'para evitar que se resbalaran',
        'para que los jugadores no se resbalaran']),
    ('¿Qué demuestra la decisión del profesor?', 'inferencial', 'responsabilidad', [
        'que es responsable', 'que el profesor es responsable', 'demuestra responsabilidad']),
    ('¿Qué aprendió Mateo?', 'inferencial', 'que las plantas necesitan cuidado', [
        'que las plantas necesitan cuidados', 'que las plantas necesitan agua luz y cuidado constante',
        'que debe cuidar la planta', 'que debe regar y cuidar la planta']),
    ('¿Por qué la planta volvió a verse mejor?', 'inferencial', 'porque mateo la regó', [
        'porque Mateo empezó a regarla', 'porque Mateo la regó cada mañana',
        'porque empezó a recibir agua', 'porque Mateo empezó a regarla cada mañana']),
    ('¿Qué hicieron para mejorar el trabajo?', 'inferencial', 'repartirse las tareas', [
        'se repartieron las tareas', 'repartieron las tareas', 'dividieron las tareas',
        'decidieron repartirse las tareas']),
    ('¿Qué enseñanza deja el texto?', 'inferencial', 'trabajar en equipo', [
        'que debemos trabajar en equipo', 'que es importante trabajar en equipo',
        'que trabajar en equipo ayuda', 'la importancia de trabajar en equipo']),
    ('¿Qué le enseñó su tutor?', 'inferencial', 'ordenar sus materiales', [
        'a ordenar sus materiales', 'ordenar los materiales según sus clases',
        'a ordenar sus materiales según las clases', 'ordenar sus materiales según las clases']),
    ('¿Por qué Carlos llegó con mejor ánimo?', 'inferencial', 'porque llevó menos peso', [
        'porque llevaba menos peso', 'porque su mochila pesaba menos',
        'porque llevó menos libros', 'porque cargaba menos peso']),
    ('¿Para qué publicaron un aviso?', 'inferencial', 'para encontrar al dueño', [
        'para encontrar al dueño del perro', 'para que el dueño encontrara al perro',
        'para ayudar a encontrar al dueño', 'para encontrar a la familia del perro']),
    ('¿Qué cualidad mostró Valeria?', 'inferencial', 'solidaridad', [
        'mostró solidaridad', 'fue solidaria', 'que es solidaria']),
    ('¿Qué dejó de comprar Luis?', 'inferencial', 'golosinas', [
        'dejó de comprar golosinas', 'Luis dejó de comprar golosinas']),
    ('¿Qué valor demuestra Luis?', 'inferencial', 'perseverancia', [
        'demuestra perseverancia', 'fue perseverante', 'que es perseverante']),
]


def _identidad(enunciado, tipo, clave):
    return tuple(normalizar_texto(valor).strip() for valor in (enunciado, tipo, clave))


CATALOGO = {_identidad(enunciado, tipo, clave): tuple(variantes)
            for enunciado, tipo, clave, variantes in REGISTROS}


def alternativas_para_pregunta(pregunta):
    """Preserva la clave; solo añade equivalencias de literal/inferencia acotada."""
    clave = pregunta.get('respuesta')
    if not clave:
        return []
    if pregunta.get('tipo') not in ('literal', 'inferencial'):
        return [clave]
    identidad = _identidad(pregunta.get('enunciado', ''), pregunta['tipo'], clave)
    return [clave, *CATALOGO.get(identidad, ())]
