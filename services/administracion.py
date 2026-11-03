"""Administración de cuentas sin modificar la evaluación ni el banco de lecturas."""
import bcrypt
from pymysql import IntegrityError
from services.actividades import ActivityError
from services.correos import validar_correo_gmail
from services.lectura import entero_positivo


def validar_administrador(cursor, usuario):
    if usuario['rol'] != 3:
        raise ActivityError('Solo el administrador puede gestionar cuentas.', 403)
    cursor.execute('SELECT id_rol FROM usuarios WHERE id_usuario=%s LOCK IN SHARE MODE', (usuario['id_usuario'],))
    cuenta = cursor.fetchone()
    if not cuenta or cuenta['id_rol'] != 3:
        raise ActivityError('La cuenta ya no tiene permisos de administración.', 403)


def validar_datos(data, crear=False):
    if not isinstance(data, dict):
        raise ValueError('Se requiere un objeto JSON válido.')
    nombre = data.get('nombre')
    if not isinstance(nombre, str):
        raise ValueError('Escribe el nombre completo.')
    nombre = ' '.join(nombre.split())
    if (not 2 <= len(nombre) <= 100 or not any(c.isalpha() for c in nombre)
            or not all(c.isalpha() or c in " '-." for c in nombre)):
        raise ValueError('El nombre admite de 2 a 100 caracteres y debe contener solo letras y separadores de nombres.')
    correo = validar_correo_gmail(data.get('email')).lower()
    password = data.get('password', '')
    if not isinstance(password, str):
        raise ValueError('La contraseña debe ser texto.')
    if crear or password:
        if len(password) < 8 or len(password.encode('utf-8')) > 72 or not password.strip():
            raise ValueError('La contraseña debe tener al menos 8 caracteres y como máximo 72 bytes UTF-8.')
    if crear:
        rol = entero_positivo(data.get('rol'), 'Rol')
        if rol not in (1, 2):
            raise ValueError('Solo puedes crear estudiantes o docentes.')
    return nombre, correo, password


def resumen(cursor):
    cursor.execute('''SELECT
        (SELECT COUNT(*) FROM usuarios WHERE id_rol=1) estudiantes,
        (SELECT COUNT(*) FROM usuarios WHERE id_rol=2) docentes,
        (SELECT COUNT(*) FROM respuestas_estudiante WHERE es_correcta IS NULL) pendientes,
        (SELECT COUNT(*) FROM textos t WHERE NOT EXISTS
          (SELECT 1 FROM versiones_lecturas v WHERE v.id_texto_original=t.id_texto)) lecturas''')
    return cursor.fetchone()


def listar_cuentas(cursor, args):
    rol = entero_positivo(args.get('rol', '1'), 'Rol')
    pagina = entero_positivo(args.get('pagina', '1'), 'Página')
    buscar = args.get('buscar', '').strip()
    if rol not in (1, 2) or pagina > 100000 or len(buscar) > 100:
        raise ValueError('Filtros de consulta inválidos.')
    # Búsqueda literal: los signos de porcentaje no se interpretan como comodines.
    buscar = buscar.replace('!', '!!').replace('%', '!%').replace('_', '!_')
    filtro = "u.id_rol=%s AND (u.nombre LIKE %s ESCAPE '!' OR u.email LIKE %s ESCAPE '!')"
    params = (rol, '%' + buscar + '%', '%' + buscar + '%')
    cursor.execute('SELECT COUNT(*) total FROM usuarios u WHERE ' + filtro, params)
    total = cursor.fetchone()['total']
    cursor.execute('''SELECT u.id_usuario,u.nombre,u.email,u.id_rol,u.fecha_registro,
        e.id_estudiante,d.id_docente,
        (SELECT COUNT(*) FROM respuestas_estudiante r WHERE r.id_estudiante=e.id_estudiante) respuestas,
        (SELECT COUNT(*) FROM revisiones_criticas rv WHERE rv.id_usuario_revisor=u.id_usuario) revisiones
        FROM usuarios u LEFT JOIN estudiantes e ON e.id_usuario=u.id_usuario
        LEFT JOIN docentes d ON d.id_usuario=u.id_usuario WHERE ''' + filtro +
        ' ORDER BY u.nombre,u.id_usuario LIMIT %s OFFSET %s', (*params, 10, (pagina-1)*10))
    cuentas = cursor.fetchall()
    for c in cuentas:
        c['fecha_registro'] = str(c['fecha_registro']) if c['fecha_registro'] else None
    return {'cuentas': cuentas, 'pagina': pagina, 'por_pagina': 10, 'total': total}


def guardar_cuenta(cursor, data, uid=None):
    nombre, correo, password = validar_datos(data, crear=uid is None)
    if uid is not None:
        cuenta = obtener_cuenta(cursor, uid)
        if 'rol' in data and data['rol'] != cuenta['id_rol']:
            raise ValueError('No se puede cambiar el tipo de una cuenta que ya existe.')
    cursor.execute('SELECT id_usuario FROM usuarios WHERE email=%s', (correo,))
    existente = cursor.fetchone()
    if existente and existente['id_usuario'] != uid:
        raise ActivityError('Ya existe una cuenta con ese correo.', 409)
    if uid is None:
        rol = int(data['rol'])
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
        cursor.execute('INSERT INTO usuarios (nombre,email,contraseña,id_rol,fecha_registro) VALUES (%s,%s,%s,%s,CURDATE())',
                       (nombre, correo, password_hash, rol))
        uid = cursor.lastrowid
        if rol == 1:
            cursor.execute("INSERT INTO estudiantes (id_usuario,nivel_actual) VALUES (%s,'literal')", (uid,))
        else:
            cursor.execute('INSERT INTO docentes (id_usuario) VALUES (%s)', (uid,))
    else:
        cursor.execute('UPDATE usuarios SET nombre=%s,email=%s WHERE id_usuario=%s', (nombre, correo, uid))
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
            cursor.execute('UPDATE usuarios SET contraseña=%s WHERE id_usuario=%s', (password_hash, uid))
    return {'id_usuario': uid, 'nombre': nombre, 'email': correo, 'mensaje': 'Cuenta guardada correctamente.'}


def obtener_cuenta(cursor, uid):
    cursor.execute('SELECT id_usuario,id_rol,nombre,email FROM usuarios WHERE id_usuario=%s FOR UPDATE', (uid,))
    cuenta = cursor.fetchone()
    if not cuenta:
        raise ActivityError('La cuenta no existe. Actualiza la lista.', 404)
    if cuenta['id_rol'] not in (1, 2):
        raise ActivityError('La cuenta administradora está protegida.', 403)
    return cuenta


def eliminar_cuenta(cursor, uid, data):
    cuenta = obtener_cuenta(cursor, uid)
    if not isinstance(data, dict) or data.get('confirmacion') != cuenta['email']:
        raise ValueError('Debes confirmar la eliminación de esta cuenta.')
    if cuenta['id_rol'] == 1:
        cursor.execute('SELECT id_estudiante FROM estudiantes WHERE id_usuario=%s FOR UPDATE', (uid,))
        perfil = cursor.fetchone()
        if not perfil:
            raise ActivityError('La cuenta no tiene un perfil de estudiante válido.', 409)
        sid = perfil['id_estudiante']
        for tabla in ('revisiones_criticas', 'retroalimentacion'):
            cursor.execute('DELETE FROM ' + tabla + ' WHERE id_respuesta_est IN '
                           '(SELECT id_respuesta_est FROM respuestas_estudiante WHERE id_estudiante=%s)', (sid,))
        cursor.execute('DELETE FROM respuestas_estudiante WHERE id_estudiante=%s', (sid,))
        cursor.execute('DELETE FROM diagnostico_detalle WHERE id_diagnostico IN '
                       '(SELECT id_diagnostico FROM diagnostico WHERE id_estudiante=%s)', (sid,))
        for tabla in ('diagnostico', 'progreso', 'reportes'):
            cursor.execute('DELETE FROM ' + tabla + ' WHERE id_estudiante=%s', (sid,))
        cursor.execute('DELETE FROM estudiantes WHERE id_estudiante=%s', (sid,))
    else:
        cursor.execute('SELECT id_docente FROM docentes WHERE id_usuario=%s FOR UPDATE', (uid,))
        perfil = cursor.fetchone()
        if not perfil:
            raise ActivityError('La cuenta no tiene un perfil docente válido.', 409)
        # Se conserva la valoración y el comentario, aunque se elimine la cuenta revisora.
        cursor.execute('UPDATE revisiones_criticas SET id_usuario_revisor=NULL WHERE id_usuario_revisor=%s', (uid,))
        cursor.execute('DELETE FROM reportes WHERE id_docente=%s', (perfil['id_docente'],))
        cursor.execute('DELETE FROM docentes WHERE id_docente=%s', (perfil['id_docente'],))
    cursor.execute('DELETE FROM notificaciones WHERE id_usuario=%s', (uid,))
    cursor.execute('DELETE FROM usuarios WHERE id_usuario=%s', (uid,))
    return {'mensaje': 'Cuenta eliminada correctamente.'}


def ejecutar(usuario, get_cursor, operacion, escritura=False):
    if usuario['rol'] != 3:
        raise ActivityError('Solo el administrador puede gestionar cuentas.', 403)
    conn, cursor = get_cursor()
    try:
        validar_administrador(cursor, usuario)
        resultado = operacion(cursor)
        if escritura:
            conn.commit()
        return resultado
    except IntegrityError as exc:
        conn.rollback()
        if exc.args[0] == 1062:
            raise ActivityError('Ya existe una cuenta con ese correo.', 409) from exc
        raise ActivityError('La cuenta tiene registros asociados que impiden esta operación.', 409) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
