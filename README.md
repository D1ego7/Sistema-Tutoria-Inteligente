# Tutoría Inteligente

Sistema web local para diagnóstico, actividades adaptativas, retroalimentación y seguimiento de comprensión lectora.

## Configuración

1. Asegúrate de tener MariaDB instalado y ejecutándose.
2. Crea la base de datos indicada en `.env` e importa el esquema o respaldo correspondiente.
3. Actualiza las variables de `.env` con tus credenciales de MariaDB y una clave JWT privada.
4. Instala las dependencias: `pip install -r requirements.txt`
5. Con el servidor detenido, ejecuta `python scripts/migrar_revision_docente.py`. Esta migración corresponde al banco de lecturas de esta tesis: crea las tablas de revisión y publica versiones nuevas sin modificar los intentos anteriores. Guarda primero un respaldo privado en `respaldos/`.
6. Ejecuta la migración idempotente: `python scripts/migrate_feedback_progress.py`
7. Ejecuta la aplicación: `python app.py`

## Verificación

Ejecuta las pruebas automatizadas con:

Las pruebas se conservan únicamente en el entorno local y no se incluyen en el repositorio. Estos comandos requieren disponer de la carpeta local `tests`.

```powershell
python -m unittest discover -s tests -v
```

El registro público crea únicamente estudiantes. Los accesos docentes y administrativos deben ser provisionados por un administrador de la base de datos; el panel de seguimiento no crea cuentas ni modifica roles.

Para esta instalación se usan correos con dominio `@gmail.com`. `/register` valida el formato y exige ese dominio sin transformar una dirección de otro proveedor. Al provisionar docentes o administradores también debe respetarse esta política; las inserciones directas en la base no pasan por la validación de la API. Cambiar el correo de acceso no crea una cuenta real de Gmail ni verifica su propiedad.

## Seguimiento docente

Las cuentas con rol docente (2) o administrador (3) acceden a `/docente.html` al iniciar sesión. El docente necesita también su registro en `docentes`. El servidor comprueba el rol actual de la cuenta y, para docentes, la existencia del perfil en cada consulta.

El panel permite buscar estudiantes, filtrar por nivel y consultar diagnóstico, desempeño por nivel, lecturas completadas e historial con retroalimentación. Las consultas están paginadas y no modifican resultados ni niveles. El desempeño utiliza el último intento por pregunta; el historial incluye todos los intentos. Una ausencia de respuestas se muestra como falta de datos, no como fracaso.

Las nuevas respuestas abiertas a preguntas inferenciales o críticas quedan pendientes de revisión, independientemente del nivel del texto: no cuentan como aciertos ni errores y suspenden recomendaciones de cambio de nivel hasta su evaluación. Las preguntas de opción múltiple y las abiertas literales conservan su evaluación automática. El docente selecciona un único resultado obligatorio, «Cumple» o «No cumple», y puede añadir retroalimentación de hasta 500 caracteres. Ya no se exige una rúbrica de tres criterios ni un comentario. `POST /api/docente/respuestas/<id>/revision` recibe `cumple` como booleano y `devolucion` como texto opcional; guarda resultado, comentario, autor, fecha y progreso en una transacción, sin cambiar automáticamente el nivel. Una revisión ya guardada no puede sobrescribirse desde este flujo. No se recalifican intentos anteriores ni se requiere otra migración: se reutiliza la tabla existente `revisiones_criticas` también para inferenciales, conservando las columnas históricas de la rúbrica sin usarlas para nuevas revisiones. Esta decisión docente no constituye por sí misma una validación del instrumento.

El catálogo ofrece solo versiones vigentes. Las lecturas archivadas conservan sus textos, preguntas, claves e intentos en el historial, pero no admiten nuevas respuestas ni participan en el desempeño vigente. Una versión nueva empieza sin respuestas: no hereda la finalización de la anterior. Las nuevas respuestas abiertas del estudiante, incluido el diagnóstico, se limitan a 100 caracteres; la devolución docente admite hasta 500. El historial conserva las respuestas anteriores sin recortarlas.

El nivel actual del estudiante y del panel docente usa la misma consulta: nivel de `progreso`, o nivel del diagnóstico más reciente si no hay progreso, o literal si no hay ninguno. El diagnóstico mostrado conserva su resultado inicial. Los cambios de nivel guardan conjuntamente perfil y progreso, sin recalificar intentos.

La base actual no relaciona docentes con aulas o estudiantes asignados. El panel conserva el alcance de consulta existente sobre todos los estudiantes de esta instalación local. No se debe utilizar como aislamiento por aula o como autorización multiinstitución.

## Criterios y pruebas adicionales

El desempeño usa el último intento por pregunta. Una lectura se completa únicamente cuando todas sus preguntas tienen un último intento correcto. El porcentaje de aciertos no representa el porcentaje de implementación del sistema.

`POST /respuestas-lectura` guarda respuestas de una lectura, retroalimentación y progreso en una transacción. `/feedback-sesion` no cambia el nivel; `/aplicar-nivel-recomendado` aplica una recomendación confirmada y validada nuevamente por el servidor.

La evaluación abierta compara palabras normalizadas con alternativas explícitas, no interpreta libremente opiniones o paráfrasis. El tiempo registrado no es fluidez lectora validada.

Las variantes de respuesta se mantienen en `services/respuestas_aceptadas.py`. La evaluación automática de preguntas abiertas literales las aplica únicamente si coinciden el enunciado, tipo y clave vigente; las variantes inferenciales anteriores se conservan, pero ya no califican nuevas respuestas inferenciales sujetas a revisión docente. No se recalifica el historial ni se modifica el diagnóstico. Las opciones de las actividades se mezclan al mostrarse y conservan su orden durante la sesión. Este ajuste no requiere migraciones de base de datos.

```powershell
node --test tests/lectura_interfaz.test.cjs
$env:RUN_DB_INTEGRATION='1'
python -m unittest discover -s tests -v
Remove-Item Env:RUN_DB_INTEGRATION
```

Las pruebas de integración requieren la base local de `.env`. Revierten sus filas temporales y no ejecutan DDL; AUTO_INCREMENT puede avanzar. Para futuras verificaciones, preferir una copia de pruebas.

## Archivos locales y Git

El repositorio contiene el código, dependencias, esquema y migración del sistema. `.gitignore` excluye las pruebas, documentación interna, entregables, documentos de trabajo, archivos temporales, entornos virtuales y credenciales locales. Los archivos excluidos permanecen en el equipo, pero no se respaldan con `git push`; mantener una copia de seguridad independiente si se necesitan.
