"""Contenido revisado y selección de la versión vigente, sin borrar originales."""
SQL_TEXTO_ACTIVO = 'NOT EXISTS (SELECT 1 FROM versiones_lecturas v WHERE v.id_texto_original=t.id_texto)'

CRITICAS = {
    26: ('¿Crees que ser generoso hizo feliz al árbol? Justifica con un hecho del relato.', 'No siempre: dudó de su generosidad cuando los demás se fueron.'),
    27: ('¿El relato demuestra que la generosidad siempre se recompensa? Explica.', 'No: una niña lo cuidó, pero eso no demuestra que siempre haya recompensa.'),
    28: ('¿Es seguro que nadie cuidaría al árbol si no fuera generoso? Explica.', 'No: el relato no dice que la niña lo cuidara por haber recibido algo.'),
    77: ('¿Fue adecuada la propuesta de la profesora sobre el celular? Da una razón.', 'Sí, porque permitía buscar información sin distraerse durante las explicaciones.'),
    78: ('¿Bastaría con pedir que no jueguen con el celular? Justifica con el texto.', 'No, porque los mensajes también distraían a los estudiantes.'),
    79: ('¿Te parece adecuado usar el celular solo para tareas? Da una razón del texto.', 'Sí, ayuda a buscar información y evita usarlo para juegos durante la clase.'),
    80: ('¿Renato tomó una buena decisión al compartir? Explica con un hecho del texto.', 'Sí, porque Pablo había olvidado su comida y él tenía dos panes.'),
    81: ('¿Basta con decir que Renato fue solidario? Sustenta tu opinión con su acción.', 'No, hay que explicar que compartió un pan con Pablo, que no tenía comida.'),
    82: ('¿Su alegría basta para decir que Renato actuó bien? Da una razón.', 'No por sí sola: también importa que compartió comida con Pablo.'),
    83: ('¿Fue adecuada la iniciativa de los vecinos? Justifica con su resultado.', 'Sí, porque recogieron la basura y el parque quedó limpio y agradable.'),
    84: ('¿El cuidado del parque corresponde solo a la municipalidad? Justifica.', 'No, niños y adultos también pudieron ayudar a limpiarlo.'),
    85: ('¿Limpiar una vez basta para cuidar el parque? Sustenta con el texto.', 'No, también colocaron carteles y prometieron cuidar mejor el lugar.'),
    86: ('¿Mariana actuó con honestidad? Explica con una acción del texto.', 'Sí, dijo la verdad a la profesora en vez de copiar las respuestas.'),
    87: ('¿Habría sido adecuado copiar para evitar una mala nota? Explica.', 'No, porque Mariana sabía que así no aprendería nada.'),
    88: ('¿Decir la verdad resuelve toda la tarea pendiente? Explica con el texto.', 'No, Mariana todavía debía entregar la tarea al día siguiente.'),
    89: ('¿Era necesario cuidar el agua en el colegio? Da una razón del texto.', 'Sí, se desperdiciaba y muchas familias no tenían agua todos los días.'),
    90: ('¿Los carteles por sí solos garantizan que no se desperdicie agua? Explica.', 'No, los estudiantes también deben cerrar los caños y dejar de jugar con el agua.'),
    91: ('¿Te parece adecuada la propuesta de quinto grado? Justifica.', 'Sí, recordaba no desperdiciar agua y explicaba que a otras familias les faltaba.'),
    92: ('¿Andrea actuó correctamente? Justifica con una acción del texto.', 'Sí, pidió que dejaran de burlarse e invitaran a Tomás otra vez al juego.'),
    93: ('¿Fue adecuado reírse del error de Tomás? Explica usando el texto.', 'No, Tomás se alejó triste y dejó de querer jugar.'),
    94: ('¿Decir que todos se equivocan era suficiente para ayudar a Tomás? Explica.', 'No, Andrea también pidió parar las burlas e invitarlo al juego.'),
    95: ('¿Daniel tomó una decisión responsable? Da una razón del texto.', 'Sí, evitó un juguete que duraba poco y prefirió un juego para compartir.'),
    96: ('¿Que un juguete sea llamativo basta para decidir comprarlo? Explica.', 'No, el primero era llamativo, pero usaba muchas pilas y se rompía fácilmente.'),
    97: ('¿Fue razonable elegir el juego de mesa? Justifica con la historia.', 'Sí, podía compartirlo con su familia en lugar de comprar algo que duraba poco.'),
}
AJUSTES = {
    22: ('¿Por qué el ratón tendría motivos para ayudar al león?', 'porque el león lo había liberado y él le había prometido ayudarlo'),
    25: ('Según el texto, ¿qué tres aspectos mejora la lectura?', 'concentración vocabulario y creatividad'),
    36: ('¿Por cuánto tiempo puede llevarse un libro cada alumno?', 'una semana'),
}
