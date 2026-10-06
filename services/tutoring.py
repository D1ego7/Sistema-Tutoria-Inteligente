from config import get_db_connection
import unicodedata

def obtener_nivel_actual(id_estudiante, cursor=None):
    propio = cursor is None
    conn = None
    try:
        if propio:
            conn, cursor = get_db_cursor()

        cursor.execute("""
            SELECT nivel_actual
            FROM progreso
            WHERE id_estudiante = %s
            ORDER BY id_progreso DESC
            LIMIT 1
        """, (id_estudiante,))

        resultado = cursor.fetchone()

        if resultado:
            nivel = resultado['nivel_actual'] if isinstance(resultado, dict) else resultado[0]
            return nivel.strip().lower()

        cursor.execute("""
            SELECT nivel_asignado
            FROM diagnostico
            WHERE id_estudiante = %s
            ORDER BY fecha DESC
            LIMIT 1
        """, (id_estudiante,))

        resultado = cursor.fetchone()

        if resultado:
            nivel = resultado['nivel_asignado'] if isinstance(resultado, dict) else resultado[0]
            return nivel.strip().lower()

        return 'literal'

    except Exception as e:
        if not propio:
            raise
        print(f"Error al obtener nivel actual: {str(e)}")
        raise
    finally:
        if propio and conn:
            cursor.close()
            conn.close()


def calcular_nuevo_nivel(nivel_actual, recomendacion):
    """
    Calcula el nuevo nivel basado en la recomendación

    Args:
        nivel_actual: Nivel actual (ej: 'inferencial')
        recomendacion: Recomendación ('siguiente', 'anterior', 'mantener')

    Returns:
        str: Nuevo nivel
    """
    niveles_lista = ['literal', 'inferencial', 'crítico']

    try:
        indice_actual = niveles_lista.index(nivel_actual)
    except ValueError:
        # Si nivel_actual no es válido, comenzar en literal
        indice_actual = 0

    if recomendacion == 'siguiente':
        # Subir de nivel (máximo crítico)
        nuevo_indice = min(indice_actual + 1, len(niveles_lista) - 1)
    elif recomendacion == 'anterior':
        # Bajar de nivel (mínimo literal)
        nuevo_indice = max(indice_actual - 1, 0)
    else:  # 'mantener'
        nuevo_indice = indice_actual

    return niveles_lista[nuevo_indice]


def comparar_niveles(nivel_actual, nuevo_nivel):
    """
    Compara dos niveles y devuelve si el estudiante sube, baja o se mantiene.
    """
    niveles_lista = ['literal', 'inferencial', 'crítico']
    try:
        actual = niveles_lista.index(nivel_actual)
    except ValueError:
        actual = 0
    try:
        nuevo = niveles_lista.index(nuevo_nivel)
    except ValueError:
        nuevo = actual

    if nuevo > actual:
        return 'sube'
    if nuevo < actual:
        return 'baja'
    return 'mantiene'


def normalizar_texto(texto):
    """
    Normaliza texto removiendo tildes y diacríticos para comparación
    
    Args:
        texto: Texto a normalizar
    
    Returns:
        Texto normalizado en minúsculas
    """
    if not texto:
        return ""
    
    # Usar NFC para normalización unicode
    nfc = unicodedata.normalize('NFD', texto.lower().strip())
    # Remover diacríticos
    sin_diacriticos = ''.join(c for c in nfc if unicodedata.category(c) != 'Mn')
    return sin_diacriticos


def get_db_cursor():
    """
    Obtiene conexión y cursor en una sola llamada
    
    Returns:
        tuple (conn, cursor)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    return conn, cursor


def calcular_puntuacion_estudiante(id_estudiante, limite_respuestas=None, cursor=None):
    """
    Calcula la puntuación general y por nivel de un estudiante
    
    Args:
        id_estudiante: ID del estudiante
        limite_respuestas: Número máximo de respuestas a considerar (últimas N)
    
    Returns:
        dict con estadísticas de desempeño
    """
    propio = cursor is None
    conn = None
    try:
        if propio:
            conn, cursor = get_db_cursor()
        
        # Consolidar el desempeño usando únicamente el intento más reciente
        # de cada pregunta. Así, los reintentos no inflan ni castigan el avance.
        query = """
            SELECT re.id_respuesta_est, re.es_correcta, p.tipo, re.fecha
            FROM respuestas_estudiante re
            JOIN preguntas p ON re.id_pregunta = p.id_pregunta
            JOIN (
                SELECT id_pregunta, MAX(id_respuesta_est) AS ultima_respuesta
                FROM respuestas_estudiante
                WHERE id_estudiante = %s
                GROUP BY id_pregunta
            ) ultimas ON ultimas.ultima_respuesta = re.id_respuesta_est
            WHERE re.id_estudiante = %s
            ORDER BY re.id_respuesta_est DESC
        """
        parametros = [id_estudiante, id_estudiante]

        if limite_respuestas:
            query += " LIMIT %s"
            parametros.append(int(limite_respuestas))
        
        cursor.execute(query, tuple(parametros))
        respuestas = cursor.fetchall()
        
        if not respuestas:
            return {
                'total_respuestas': 0,
                'respuestas_correctas': 0,
                'porcentaje_acierto': 0,
                'por_nivel': {},
                'tendencia': 'sin_datos'
            }
        
        # Analizar respuestas
        total = len(respuestas)
        correctas = sum(1 for r in respuestas if r['es_correcta'])  # r['es_correcta'] es es_correcta
        porcentaje = (correctas / total * 100) if total > 0 else 0
        
        # Desglose por nivel
        por_nivel = {}
        for r in respuestas:
            nivel = r['tipo']  # r['tipo'] es tipo
            if nivel not in por_nivel:
                por_nivel[nivel] = {'total': 0, 'correctas': 0}
            por_nivel[nivel]['total'] += 1
            if r['es_correcta']:
                por_nivel[nivel]['correctas'] += 1
        
        # Calcular tendencia (últimas 5 respuestas)
        ultimas = respuestas[:5]
        ultimas_correctas = sum(1 for r in ultimas if r['es_correcta'])
        if len(ultimas) < 3:
            tendencia = 'datos_insuficientes'
        elif ultimas_correctas >= 4:
            tendencia = 'mejorando'
        elif ultimas_correctas <= 1:
            tendencia = 'empeorando'
        else:
            tendencia = 'estable'
        
        return {
            'total_respuestas': total,
            'respuestas_correctas': correctas,
            'porcentaje_acierto': round(porcentaje, 2),
            'por_nivel': {
                nivel: {
                    'porcentaje': round((datos['correctas'] / datos['total'] * 100), 2) if datos['total'] > 0 else 0,
                    'correctas': datos['correctas'],
                    'total': datos['total']
                }
                for nivel, datos in por_nivel.items()
            },
            'tendencia': tendencia
        }
    except Exception as e:
        if not propio:
            raise
        return {'error': str(e)}
    finally:
        if propio and conn:
            cursor.close()
            conn.close()


def detectar_patrones_error(id_estudiante, limite_respuestas=20):
    """
    Detecta patrones recurrentes en los errores del estudiante
    
    Args:
        id_estudiante: ID del estudiante
        limite_respuestas: Últimas N respuestas a analizar
    
    Returns:
        dict con patrones identificados
    """
    try:
        conn, cursor = get_db_cursor()
        
        # Obtener respuestas incorrectas recientes con tiempo de respuesta
        query = """
            SELECT p.id_pregunta, p.enunciado, p.tipo, re.respuesta,
                   COALESCE(rc.respuesta, op.texto_opcion) AS respuesta_correcta,
                   re.tiempo_respuesta
            FROM respuestas_estudiante re
            JOIN preguntas p ON re.id_pregunta = p.id_pregunta
            JOIN (
                SELECT id_pregunta, MAX(id_respuesta_est) AS ultima_respuesta
                FROM respuestas_estudiante
                WHERE id_estudiante = %s
                GROUP BY id_pregunta
            ) ultimas ON ultimas.ultima_respuesta = re.id_respuesta_est
            LEFT JOIN respuestas_correctas rc ON p.id_pregunta = rc.id_pregunta
            LEFT JOIN opciones_pregunta op
                ON p.id_pregunta = op.id_pregunta AND op.es_correcta = TRUE
            WHERE re.id_estudiante = %s AND re.es_correcta = FALSE
            ORDER BY re.id_respuesta_est DESC
            LIMIT %s
        """
        
        cursor.execute(query, (id_estudiante, id_estudiante, limite_respuestas))
        errores = cursor.fetchall()
        cursor.close()
        conn.close()
        
        patrones = {
            'total_errores': len(errores),
            'niveles_con_dificultad': {},
            'tipos_de_error': [],
            'tiempo_promedio_error': 0,
            'recomendaciones': []
        }
        
        if not errores:
            patrones['recomendaciones'].append('¡Excelente desempeño! Sigue así.')
            return patrones
        
        # Contar errores por nivel y calcular tiempo promedio
        errores_por_nivel = {}
        tiempo_total = 0
        for error in errores:
            nivel = error['tipo']
            errores_por_nivel[nivel] = errores_por_nivel.get(nivel, 0) + 1
            tiempo_total += error['tiempo_respuesta'] or 0
        
        tiempo_promedio_error = tiempo_total / len(errores) if errores else 0
        
        patrones['niveles_con_dificultad'] = errores_por_nivel
        patrones['tiempo_promedio_error'] = round(tiempo_promedio_error, 2)
        
        # Identificar tipo de error (falta respuesta, respuesta corta, respuesta completamente diferente)
        for error in errores[:5]:  # Analizar hasta 5 errores recientes
            respuesta_usuario = error['respuesta']
            respuesta_correcta = error['respuesta_correcta'] or ''
            
            if not respuesta_usuario or respuesta_usuario.strip() == '':
                tipo_error = 'respuesta_vacia'
            elif len(respuesta_usuario) < len(respuesta_correcta) / 2:
                tipo_error = 'respuesta_incompleta'
            else:
                tipo_error = 'respuesta_incorrecta'
            
            patrones['tipos_de_error'].append({
                'pregunta_id': error['id_pregunta'],
                'tipo': tipo_error,
                'nivel': error['tipo'],
                'tiempo_respuesta': error['tiempo_respuesta']
            })
        
        # Generar recomendaciones
        nivel_critico = max(errores_por_nivel.items(), key=lambda x: x[1])[0] if errores_por_nivel else None
        
        if nivel_critico:
            patrones['recomendaciones'].append(
                f"Necesitas practicar más con preguntas de nivel '{nivel_critico}'. Practica regularmente."
            )
        
        if tiempo_promedio_error > 120:  # Si tarda más de 2 minutos
            patrones['recomendaciones'].append(
                'Tómate el tiempo que necesites y revisa el texto antes de responder. El tiempo registrado no mide tu velocidad lectora.'
            )
        
        if patrones['tipos_de_error'] and patrones['tipos_de_error'][0]['tipo'] == 'respuesta_incompleta':
            patrones['recomendaciones'].append(
                'Lee cuidadosamente y responde de forma completa. No dejes respuestas a mitad.'
            )
        
        return patrones
    except Exception as e:
        return {'error': str(e)}


def recomendar_nivel_siguiente(id_estudiante, cursor=None):
    """
    Recomienda el siguiente nivel de dificultad basado en desempeño
    
    Args:
        id_estudiante: ID del estudiante
    
    Returns:
        dict con recomendación de nivel y nuevo_nivel calculado
    """
    try:
        puntuacion = calcular_puntuacion_estudiante(id_estudiante, limite_respuestas=10, cursor=cursor)
        
        if 'error' in puntuacion:
            return {'error': puntuacion['error']}
        
        # Obtener nivel actual
        nivel_actual = obtener_nivel_actual(id_estudiante, cursor=cursor)
        
        if puntuacion['total_respuestas'] == 0:
            nuevo_nivel = nivel_actual
            return {
                'nivel_actual': nivel_actual,
                'recomendacion': 'mantener',
                'nuevo_nivel': nuevo_nivel,
                'razon': 'Vamos a empezar con un nivel sencillo para que te sientas cómodo.',
                'confianza': 'baja'
            }
        
        datos_nivel_actual = puntuacion.get('por_nivel', {}).get(nivel_actual, {})
        total_nivel_actual = datos_nivel_actual.get('total', 0)
        porcentaje = datos_nivel_actual.get('porcentaje', puntuacion['porcentaje_acierto'])
        tendencia = puntuacion['tendencia']

        if total_nivel_actual < 5:
            return {
                'nivel_actual': nivel_actual,
                'recomendacion': 'mantener',
                'nuevo_nivel': nivel_actual,
                'razon': f'Resuelve al menos 5 preguntas de nivel {nivel_actual} para generar una recomendación confiable.',
                'confianza': 'baja',
                'porcentaje_acierto': porcentaje,
                'respuestas_nivel_actual': total_nivel_actual
            }
        
        # Lógica de recomendación
        if porcentaje >= 80 and tendencia in ['mejorando', 'estable']:
            recomendacion_accion = 'siguiente'
            razon = '¡Muy bien! Estás respondiendo bien. Puedes intentar un ejercicio un poco más difícil.'
            confianza = 'alta'
        elif porcentaje >= 60 and tendencia == 'mejorando':
            recomendacion_accion = 'mantener'
            razon = '¡Buen trabajo! Estás mejorando. Sigue practicando en este nivel.'
            confianza = 'media'
        elif porcentaje < 40:
            recomendacion_accion = 'anterior'
            razon = 'Todavía te cuesta un poco. Practica más en este nivel para sentirte mejor.'
            confianza = 'alta'
        else:
            recomendacion_accion = 'mantener'
            razon = 'Estás progresando. Sigue practicando en este nivel para mejorar.'
            confianza = 'media'
        
        # Calcular nuevo nivel
        nuevo_nivel = calcular_nuevo_nivel(nivel_actual, recomendacion_accion)
        if nuevo_nivel == nivel_actual and recomendacion_accion in ('siguiente', 'anterior'):
            recomendacion_accion = 'mantener'
        
        return {
            'nivel_actual': nivel_actual,
            'recomendacion': recomendacion_accion,
            'nuevo_nivel': nuevo_nivel,
            'razon': razon,
            'confianza': confianza,
            'porcentaje_acierto': porcentaje
        }
    except Exception as e:
        return {'error': str(e)}


def generar_feedback_personalizado(id_pregunta, es_correcta, respuesta_usuario, respuesta_correcta, tipo_pregunta):
    """
    Genera feedback personalizado basado en la respuesta
    
    Args:
        id_pregunta: ID de la pregunta
        es_correcta: Si la respuesta fue correcta
        respuesta_usuario: Respuesta del estudiante
        respuesta_correcta: Respuesta correcta esperada
        tipo_pregunta: Tipo de pregunta (literal, inferencial, crítico)
    
    Returns:
        dict con feedback personalizado
    """
    
    feedback = {
        'es_correcta': es_correcta,
        'mensaje': '',
        'explicacion': '',
        'pista': ''
    }
    
    if es_correcta:
        mensajes_exito = {
            'literal': '¡Muy bien! Encontraste la respuesta en el texto.',
            'inferencial': '¡Bien hecho! Pensaste en lo que el texto quiere decir.',
            'crítico': '¡Genial! Usaste tus ideas para entender el texto mejor.'
        }
        feedback['mensaje'] = mensajes_exito.get(tipo_pregunta, '¡Muy bien! Tu respuesta es correcta.')
    else:
        if not respuesta_usuario or respuesta_usuario.strip() == '':
            feedback['mensaje'] = 'No escribiste una respuesta. Intenta responder con calma.'
            feedback['pista'] = 'Lee otra vez el texto y escribe lo que piensas.'
        else:
            mensajes_error = {
                'literal': 'No es correcta. Busca la respuesta en el texto otra vez.',
                'inferencial': 'No es correcta. Trata de entender el mensaje del texto y responde con tus palabras.',
                'crítico': 'No es correcta. Piensa con calma y responde lo que tú opinas sobre el texto.'
            }
            feedback['mensaje'] = mensajes_error.get(tipo_pregunta, 'Esa no es la respuesta correcta.')
            feedback['explicacion'] = f'La respuesta correcta es: {respuesta_correcta}'
            feedback['pista'] = 'Inténtalo de nuevo con calma y revisa el texto otra vez.'
    
    return feedback


def actualizar_nivel_estudiante(id_estudiante, nuevo_nivel):
    """
    Actualiza el nivel actual del estudiante en la tabla progreso

    Args:
        id_estudiante: ID del estudiante
        nuevo_nivel: Nuevo nivel (literal, inferencial, crítico)

    Returns:
        bool: True si se actualizó, False si error
    """
    try:
        conn, cursor = get_db_cursor()
        
        # Verificar si existe registro en progreso
        cursor.execute("SELECT id_progreso FROM progreso WHERE id_estudiante = %s", (id_estudiante,))
        progreso = cursor.fetchone()
        
        if progreso:
            # Actualizar nivel existente
            cursor.execute("""UPDATE progreso SET nivel_actual = %s 
                            WHERE id_estudiante = %s""",
                          (nuevo_nivel, id_estudiante))
        else:
            # Crear nuevo registro de progreso
            cursor.execute("""INSERT INTO progreso (id_estudiante, nivel_actual, porcentaje_avance) 
                            VALUES (%s, %s, %s)""",
                          (id_estudiante, nuevo_nivel, 0))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al actualizar nivel: {str(e)}")
        return False


def sincronizar_progreso_estudiante(id_estudiante):
    """Actualiza el resumen persistido con el cálculo consolidado vigente."""
    evaluacion = calcular_puntuacion_estudiante(id_estudiante)
    if 'error' in evaluacion:
        return evaluacion

    nivel_actual = obtener_nivel_actual(id_estudiante)
    porcentaje = evaluacion.get('porcentaje_acierto', 0)

    try:
        conn, cursor = get_db_cursor()
        cursor.execute(
            "SELECT id_progreso FROM progreso WHERE id_estudiante = %s ORDER BY id_progreso DESC LIMIT 1",
            (id_estudiante,)
        )
        progreso = cursor.fetchone()
        if progreso:
            cursor.execute(
                "UPDATE progreso SET nivel_actual = %s, porcentaje_avance = %s WHERE id_progreso = %s",
                (nivel_actual, porcentaje, progreso['id_progreso'])
            )
        else:
            cursor.execute(
                "INSERT INTO progreso (id_estudiante, nivel_actual, porcentaje_avance) VALUES (%s, %s, %s)",
                (id_estudiante, nivel_actual, porcentaje)
            )
        conn.commit()
        cursor.close()
        conn.close()
        return {
            'nivel_actual': nivel_actual,
            'porcentaje_avance': porcentaje,
            'evaluacion': evaluacion
        }
    except Exception as e:
        return {'error': str(e)}


def calcular_nivel_lector_diagnostico(respuestas_diagnostico):
    """
    Calcula el nivel lector inicial basado en test diagnóstico
    
    Args:
        respuestas_diagnostico: Lista de resultados del test (True/False)
    
    Returns:
        dict con nivel asignado y explicación
    """
    if not respuestas_diagnostico:
        return {'nivel': 'literal', 'confianza': 0, 'razon': 'Sin datos'}
    
    total = len(respuestas_diagnostico)
    correctas = sum(respuestas_diagnostico)
    porcentaje = (correctas / total * 100) if total > 0 else 0
    
    if porcentaje >= 75:
        nivel = 'crítico'
        confianza = 'alta'
    elif porcentaje >= 50:
        nivel = 'inferencial'
        confianza = 'media'
    else:
        nivel = 'literal'
        confianza = 'media'
    
    return {
        'nivel': nivel,
        'confianza': confianza,
        'porcentaje': round(porcentaje, 2),
        'razon': f'Basado en tu desempeño ({correctas}/{total} correctas), iniciamos en nivel {nivel}.'
    }

def crear_plan_reforzamiento(id_estudiante):
    """
    Crea un plan de reforzamiento según el desempeño por nivel lector.
    """
    evaluacion = calcular_puntuacion_estudiante(id_estudiante)

    if 'error' in evaluacion:
        return evaluacion

    por_nivel = evaluacion.get('por_nivel', {})
    porcentaje_general = evaluacion.get('porcentaje_acierto', 0)

    niveles = ['literal', 'inferencial', 'crítico']

    # Detectar nivel con menor desempeño
    nivel_bajo = None
    menor_porcentaje = 101

    for nivel in niveles:
        datos = por_nivel.get(nivel)
        if datos and datos.get('total', 0) > 0:
            porcentaje = datos.get('porcentaje', 0)
            if porcentaje < menor_porcentaje:
                menor_porcentaje = porcentaje
                nivel_bajo = nivel

    # Si no hay datos suficientes
    if not nivel_bajo:
        return {
            "nivel_reforzar": "literal",
            "mensaje": "Aún necesitas resolver más actividades para generar un plan personalizado.",
            "textos_recomendados": "literal",
            "desbloquear_siguiente": False
        }

    # Buen desempeño
    if porcentaje_general >= 80:
        recomendacion_nivel = recomendar_nivel_siguiente(id_estudiante)
        if 'error' in recomendacion_nivel:
            return recomendacion_nivel
        nuevo_nivel = recomendacion_nivel.get('nuevo_nivel', nivel_bajo)

        return {
            "nivel_reforzar": None,
            "mensaje": recomendacion_nivel.get('razon', 'Continúa practicando en tu nivel actual.'),
            "textos_recomendados": nuevo_nivel,
            "desbloquear_siguiente": recomendacion_nivel.get('recomendacion') == 'siguiente'
        }

    # Bajo desempeño por nivel
    mensajes = {
        "literal": "Necesitas reforzar la identificación de información explícita del texto. Se recomiendan textos de nivel literal.",
        "inferencial": "Necesitas reforzar la deducción de ideas implícitas. Se recomiendan textos de nivel inferencial.",
        "crítico": "Necesitas reforzar la opinión, valoración y análisis del texto. Se recomiendan textos de nivel crítico."
    }

    return {
        "nivel_reforzar": nivel_bajo,
        "mensaje": mensajes.get(nivel_bajo),
        "textos_recomendados": nivel_bajo,
        "desbloquear_siguiente": False
    }
