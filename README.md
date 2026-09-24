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

```powershell
python -m unittest discover -s tests -v
```

El registro público crea únicamente estudiantes. Los accesos docentes y administrativos deben ser provisionados por un administrador de la base de datos hasta que se implemente su panel de gestión.
