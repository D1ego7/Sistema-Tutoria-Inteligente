"""Contenido de la revisión local del 12/10/2026; no cambia datos al importar.

Los identificadores son los de las lecturas auditadas. Se conservan modalidades
y niveles; las abiertas inferenciales y críticas siguen con revisión docente.
Las referencias abiertas ilustran una respuesta, no imponen una opinión única.
"""

# id_pregunta: (enunciado, referencia). Las opciones se declaran aparte.
PREGUNTAS = {
    29: ('¿Qué ocurriría si las raíces no pudieran absorber agua?',
         'Las hojas tendrían menos agua disponible para producir azúcar.'),
    30: ('¿Por qué una planta podría crecer menos si recibe poca luz?',
         'Porque tendría menos luz para producir el azúcar que le sirve de alimento.'),
    31: ('¿Cómo podría afectar a los animales que disminuyeran muchas plantas? Explica.',
         'Podrían disponer de menos alimento y oxígeno para vivir.'),
    56: ('¿Qué sugiere la prisa de Sofía sobre cómo preparó sus útiles para el recreo?',
         'Que pudo salir sin comprobar si había guardado todos sus útiles.'),
    57: ('¿Por qué Sofía necesitaba recuperar el cuaderno antes de revisar la tarea?',
         'Porque allí podía tener la tarea de matemática que la profesora iba a revisar.'),
    58: ('¿Qué podría hacer Sofía antes de salir para evitar que vuelva a ocurrir?',
         'Revisar si guardó todos sus útiles antes de salir.'),
    60: ('¿Qué podría haber ocurrido si jugaban sin limpiar la cancha?',
         'Los jugadores podrían resbalarse en la cancha mojada.'),
    63: ('¿Qué podría pasar si Mateo volviera a olvidarse de regar durante varios días?',
         'La planta podría volver a marchitarse por falta de agua.'),
    66: ('¿Qué relación hay entre repartir las tareas y terminar una presentación ordenada?',
         'Cada integrante pudo centrarse en una parte y organizaron mejor el trabajo.'),
    67: ('¿Qué enseñanza deja el texto?',
         'Que coordinar y repartir las tareas ayuda a trabajar mejor en equipo.'),
    69: ('¿Cómo ayudó el horario a reducir el peso de la mochila de Carlos?',
         'Le permitió elegir solo los materiales que necesitaba ese día.'),
    74: ('¿Qué se puede deducir de que Luis añadiera monedas durante dos meses?',
         'Que necesitó reunir pequeñas cantidades para alcanzar su meta.'),
    75: ('¿Qué habría pasado con su meta si Luis gastaba toda su propina cada semana?',
         'No habría reunido el dinero necesario para comprar la pelota.'),
    76: ('¿Qué valor demuestra Luis?',
         'Mostró perseverancia al ahorrar cada semana hasta reunir el dinero.'),
    518: ('¿Qué indica que el león se divirtiera con la promesa del ratón?',
          'Que le parecía poco probable necesitar la ayuda de un animal tan pequeño.'),
    519: ('¿Qué enseñanza se puede deducir de cómo el ratón ayudó al león?',
          'Que no importa el tamaño: todos podemos ayudar a los demás.'),
    521: ('Según el texto, ¿sobre qué temas nos enseñan lecciones los libros?',
          'Sobre la vida, la amistad y el coraje.'),
    522: ('¿Qué lugares menciona el texto para dedicar tiempo a leer?',
          'La escuela, la biblioteca y la casa.'),
    526: ('¿Es valioso cuidar al árbol aunque ya esté débil? Justifica con el relato.',
          'Sí, porque aún podía disfrutar de la compañía y el cuidado de la niña.'),
    532: ('¿Sería mejor prohibir todo uso del celular en clase? Justifica con el texto.',
          'No necesariamente: también servía para buscar información durante las tareas.'),
    534: ('¿Sería justo exigirle a Renato que entregue toda su comida? Justifica.',
          'No, porque él también necesitaba comer y pudo ayudar compartiendo un pan.'),
    541: ('¿Fue responsable pedir más tiempo para hacer la tarea? Justifica.',
          'Sí, porque reconoció su falta y pidió tiempo para hacerla en vez de copiar.'),
    544: ('¿Ayuda explicar la falta de agua además de colocar carteles? Justifica.',
          'Sí, permite comprender por qué importa no desperdiciarla, más allá del aviso.'),
    550: ('¿Fue razonable esperar y ahorrar en vez de comprar de inmediato? Justifica.',
          'Sí, pudo elegir un juego para compartir y evitar uno que podía durar poco.'),
}

OPCIONES = {
    29: [
        ('Las hojas tendrían menos agua disponible para producir azúcar.', True),
        ('Las hojas producirían más azúcar al recibir menos agua.', False),
        ('La planta podría sustituir el agua por el oxígeno del aire.', False),
    ],
    56: [
        ('Que pudo salir sin comprobar si había guardado todos sus útiles.', True),
        ('Que revisó con cuidado cada cuaderno antes de salir del aula.', False),
        ('Que pidió a sus amigas comprobar el contenido de su mochila.', False),
    ],
    74: [
        ('Que necesitó reunir pequeñas cantidades para alcanzar su meta.', True),
        ('Que recibió todo el dinero de la pelota el primer día.', False),
        ('Que consiguió la pelota sin utilizar las monedas ahorradas.', False),
    ],
    518: [
        ('Que le parecía poco probable necesitar la ayuda de un animal tan pequeño.', True),
        ('Que ya había comprobado que el ratón sabía romper las redes.', False),
        ('Que buscaba aprender del ratón cómo escapar de una trampa.', False),
    ],
    521: [
        ('Sobre la vida, la amistad y el coraje.', True),
        ('Sobre la velocidad, la fuerza y el equilibrio.', False),
        ('Sobre la limpieza, el orden y la puntualidad.', False),
    ],
    522: [
        ('La escuela, la biblioteca y la casa.', True),
        ('El parque, el mercado y el estadio.', False),
        ('El museo, el teatro y el hospital.', False),
    ],
}

CONTENIDOS = {
    13: ('Las plantas producen su alimento mediante un proceso llamado fotosíntesis. '
         'En sus hojas verdes utilizan la energía de la luz del sol, el agua que absorben '
         'las raíces y el dióxido de carbono del aire para producir azúcar. Ese azúcar '
         'les sirve de alimento para crecer. Durante el proceso también liberan oxígeno. '
         'Muchos animales se alimentan de plantas, y las personas y otros animales '
         'utilizamos oxígeno al respirar. La fotosíntesis aporta alimento y oxígeno '
         'esenciales para muchos seres vivos.'),
    176: ('Un pequeño ratón estaba jugando cuando accidentalmente despertó a un enorme '
          'león que dormía bajo un árbol. El león, furioso, atrapó al ratón entre sus '
          'garras. El ratón le rogó que lo liberara, prometiendo que algún día le '
          'ayudaría. El león, divertido por la idea, lo dejó libre. Tiempo después, '
          'el león quedó atrapado en una red. El ratón, fiel a su promesa, royó la red '
          'con sus dientes y liberó al león.'),
    186: ('En una tienda, Daniel quería comprar un juguete muy llamativo. Al revisar '
          'la etiqueta, notó que necesitaba muchas pilas. Su madre le recordó que '
          'habían comprado uno parecido y se había roto a los pocos días. Le explicó '
          'que algunas compras deben pensarse bien para evitar gastar dinero en '
          'objetos que duran poco. Daniel decidió ahorrar un poco más y comprar un '
          'juego de mesa que podía compartir con su familia.'),
}

# Una nueva referencia conserva los hechos que se mantienen en la lectura revisada.
PREGUNTAS[549] = (
    '¿Que un juguete sea llamativo basta para decidir comprarlo? Explica.',
    'No, también importa que use muchas pilas y que uno parecido haya durado poco.',
)
PREGUNTAS[548] = (
    '¿Daniel tomó una decisión responsable? Da una razón del texto.',
    'Sí, consideró las pilas y la experiencia con un juguete parecido antes de comprar.',
)

LECTURAS = {
    13: 'Cómo Funciona la Fotosíntesis',
    22: 'El cuaderno olvidado',
    23: 'El partido bajo la lluvia',
    24: 'La planta marchita',
    25: 'El trabajo en equipo',
    26: 'La mochila pesada',
    28: 'El ahorro de Luis',
    176: 'El Ratón y el León',
    177: 'La Importancia de la Lectura',
    178: 'El Árbol Generoso',
    180: 'El uso del celular en clase',
    181: 'La decisión de compartir',
    183: 'La tarea copiada',
    184: 'El agua del colegio',
    186: 'La compra responsable',
}
