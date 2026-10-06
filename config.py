from dotenv import load_dotenv
import os
import pymysql
import pymysql.cursors
from flask import g, has_request_context

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos 
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    connection = pymysql.connect(**db_config)
    # Todas las rutas, incluidas las antiguas, cierran conexiones aun al fallar.
    if has_request_context():
        g.setdefault('db_connections', []).append(connection)
    return connection
