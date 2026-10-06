# Tutoría Inteligente

Sistema web local para diagnóstico, actividades adaptativas, retroalimentación y seguimiento de comprensión lectora.

## Configuración

1. Asegúrate de tener MariaDB instalado y ejecutándose.
2. Crea la base de datos indicada en `.env` e importa el esquema o respaldo correspondiente.
3. Actualiza las variables de `.env` con tus credenciales de MariaDB y una clave JWT privada.
4. Instala las dependencias: `pip install -r requirements.txt`
5. Ejecuta la migración idempotente: `python scripts/migrate_feedback_progress.py`
6. Ejecuta la aplicación: `python app.py`

## Verificación

Ejecuta las pruebas automatizadas con:

Las pruebas se conservan únicamente en el entorno local y no se incluyen en el repositorio. Estos comandos requieren disponer de la carpeta local `tests`.

```powershell
python -m unittest discover -s tests -v
```

El registro público crea únicamente estudiantes. Los accesos docentes y administrativos deben ser provisionados por un administrador de la base de datos; el panel de seguimiento no crea cuentas ni modifica roles.

## Seguimiento docente

Las cuentas con rol docente (2) o administrador (3) acceden a `/docente.html` al iniciar sesión. El docente necesita también su registro en `docentes`. El servidor comprueba el rol actual de la cuenta y, para docentes, la existencia del perfil en cada consulta.

El panel permite buscar estudiantes, filtrar por nivel y consultar diagnóstico, desempeño por nivel, lecturas completadas e historial con retroalimentación. Las consultas están paginadas y no modifican resultados ni niveles. El desempeño utiliza el último intento por pregunta; el historial incluye todos los intentos. Una ausencia de respuestas se muestra como falta de datos, no como fracaso.

La base actual no relaciona docentes con aulas o estudiantes asignados. El panel conserva el alcance de consulta existente sobre todos los estudiantes de esta instalación local. No se debe utilizar como aislamiento por aula o como autorización multiinstitución.

## Criterios y pruebas adicionales

El desempeño usa el último intento por pregunta. Una lectura se completa únicamente cuando todas sus preguntas tienen un último intento correcto. El porcentaje de aciertos no representa el porcentaje de implementación del sistema.

`POST /respuestas-lectura` guarda respuestas de una lectura, retroalimentación y progreso en una transacción. `/feedback-sesion` no cambia el nivel; `/aplicar-nivel-recomendado` aplica una recomendación confirmada y validada nuevamente por el servidor.

La evaluación abierta compara palabras normalizadas con alternativas explícitas, no interpreta libremente opiniones o paráfrasis. El tiempo registrado no es fluidez lectora validada.

```powershell
node --test tests/lectura_interfaz.test.cjs
$env:RUN_DB_INTEGRATION='1'
python -m unittest discover -s tests -v
Remove-Item Env:RUN_DB_INTEGRATION
```

Las pruebas de integración requieren la base local de `.env`. Revierten sus filas temporales y no ejecutan DDL; AUTO_INCREMENT puede avanzar. Para futuras verificaciones, preferir una copia de pruebas.

## Archivos locales y Git

El repositorio contiene el código, dependencias, esquema y migración del sistema. `.gitignore` excluye las pruebas, documentación interna, entregables, documentos de trabajo, archivos temporales, entornos virtuales y credenciales locales. Los archivos excluidos permanecen en el equipo, pero no se respaldan con `git push`; mantener una copia de seguridad independiente si se necesitan.
