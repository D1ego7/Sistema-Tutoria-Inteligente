"""
Módulo de Tutoría Inteligente
Contiene la lógica para adaptación de dificultad, evaluación de desempeño
y generación de recomendaciones personalizadas
"""

from config import get_db_connection
import unicodedata

def obtener_nivel_actual(id_estudiante):
    """
    Obtiene el nivel actual del estudiante
    
    Args:
        id_estudiante: ID del estudiante
    
    Returns:
        str: Nivel actual ('literal', 'inferencial', 'crítico', 'metacognitivo')
        o None si no existe
    """
    try:
        conn, cursor = get_db_cursor()
        
        # Intentar obtener del progreso
        cursor.execute("SELECT nivel_actual FROM progreso WHERE id_estudiante = %s", (id_estudiante,))
        resultado = cursor.fetchone()
        
        if resultado:
            nivel = resultado['nivel_actual'] if isinstance(resultado, dict) else resultado[0]
            cursor.close()
            conn.close()
            return nivel
        
        # Si no existe en progreso, intentar en diagnostico
        cursor.execute("""SELECT nivel_asignado FROM diagnostico 
                         WHERE id_estudiante = %s 
                         ORDER BY fecha DESC LIMIT 1""", (id_estudiante,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            return resultado['nivel_asignado'] if isinstance(resultado, dict) else resultado[0]
        
        # Por defecto, comenzar en literal
        return 'literal'
    except Exception as e:
        print(f"Error al obtener nivel actual: {str(e)}")
        return 'literal'


def calcular_nuevo_nivel(nivel_actual, recomendacion):
    """
    Calcula el nuevo nivel basado en la recomendación
    
    Args:
        nivel_actual: Nivel actual (ej: 'inferencial')
        recomendacion: Recomendación ('siguiente', 'anterior', 'mantener')
    
    Returns:
        str: Nuevo nivel
    """
    niveles_lista = ['literal', 'inferencial', 'crítico', 'metacognitivo']
    
    try:
        indice_actual = niveles_lista.index(nivel_actual)
    except ValueError:
        # Si nivel_actual no es válido, comenzar en literal
        indice_actual = 0
    
    if recomendacion == 'siguiente':
        # Subir de nivel (máximo metacognitivo)
        nuevo_indice = min(indice_actual + 1, len(niveles_lista) - 1)
    elif recomendacion == 'anterior':
        # Bajar de nivel (mínimo literal)
        nuevo_indice = max(indice_actual - 1, 0)
    else:  # 'mantener'
        nuevo_indice = indice_actual
    
    return niveles_lista[nuevo_indice]


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


def calcular_puntuacion_estudiante(id_estudiante, limite_respuestas=None):
    """
    Calcula la puntuación general y por nivel de un estudiante
    
    Args:
        id_estudiante: ID del estudiante
        limite_respuestas: Número máximo de respuestas a considerar (últimas N)
    
    Returns:
        dict con estadísticas de desempeño
    """
    try:
        conn, cursor = get_db_cursor()
        
        # Obtener todas las respuestas del estudiante
        query = """
            SELECT re.id_respuesta_est, re.es_correcta, p.tipo, re.fecha
            FROM respuestas_estudiante re
            JOIN preguntas p ON re.id_pregunta = p.id_pregunta
            WHERE re.id_estudiante = %s
            ORDER BY re.fecha DESC
        """
        
        if limite_respuestas:
            query += f" LIMIT {limite_respuestas}"
        
        cursor.execute(query, (id_estudiante,))
        respuestas = cursor.fetchall()
        cursor.close()
        conn.close()
        
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
        correctas = sum(1 for r in respuestas if r[1])  # r[1] es es_correcta
        porcentaje = (correctas / total * 100) if total > 0 else 0
        
        # Desglose por nivel
        por_nivel = {}
        for r in respuestas:
            nivel = r[2]  # r[2] es tipo
            if nivel not in por_nivel:
                por_nivel[nivel] = {'total': 0, 'correctas': 0}
            por_nivel[nivel]['total'] += 1
            if r[1]:
                por_nivel[nivel]['correctas'] += 1
        
        # Calcular tendencia (últimas 5 respuestas)
        ultimas = respuestas[:5]
        ultimas_correctas = sum(1 for r in ultimas if r[1])
        if ultimas_correctas >= 4:
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
        return {'error': str(e)}


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
            SELECT p.id_pregunta, p.enunciado, p.tipo, re.respuesta, rc.respuesta as respuesta_correcta, re.tiempo_respuesta
            FROM respuestas_estudiante re
            JOIN preguntas p ON re.id_pregunta = p.id_pregunta
            JOIN respuestas_correctas rc ON p.id_pregunta = rc.id_pregunta
            WHERE re.id_estudiante = %s AND re.es_correcta = FALSE
            ORDER BY re.fecha DESC
            LIMIT %s
        """
        
        cursor.execute(query, (id_estudiante, limite_respuestas))
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
            tiempo_total += error['tiempo_respuesta']
        
        tiempo_promedio_error = tiempo_total / len(errores) if errores else 0
        
        patrones['niveles_con_dificultad'] = errores_por_nivel
        patrones['tiempo_promedio_error'] = round(tiempo_promedio_error, 2)
        
        # Identificar tipo de error (falta respuesta, respuesta corta, respuesta completamente diferente)
        for error in errores[:5]:  # Analizar hasta 5 errores recientes
            respuesta_usuario = error['respuesta']
            respuesta_correcta = error['respuesta_correcta']
            
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
                'Observamos que tardas mucho tiempo. Intenta leer más rápido sin perder comprensión.'
            )
        
        if patrones['tipos_de_error'] and patrones['tipos_de_error'][0]['tipo'] == 'respuesta_incompleta':
            patrones['recomendaciones'].append(
                'Lee cuidadosamente y responde de forma completa. No dejes respuestas a mitad.'
            )
        
        return patrones
    except Exception as e:
        return {'error': str(e)}


def recomendar_nivel_siguiente(id_estudiante):
    """
    Recomienda el siguiente nivel de dificultad basado en desempeño
    
    Args:
        id_estudiante: ID del estudiante
    
    Returns:
        dict con recomendación de nivel y nuevo_nivel calculado
    """
    try:
        puntuacion = calcular_puntuacion_estudiante(id_estudiante, limite_respuestas=10)
        
        if 'error' in puntuacion:
            return {'error': puntuacion['error']}
        
        # Obtener nivel actual
        nivel_actual = obtener_nivel_actual(id_estudiante)
        
        if puntuacion['total_respuestas'] == 0:
            nuevo_nivel = 'literal'
            return {
                'nivel_actual': nivel_actual,
                'recomendacion': 'mantener',
                'nuevo_nivel': nuevo_nivel,
                'razon': 'Primer diagnóstico. Comenzar con nivel básico.',
                'confianza': 'baja'
            }
        
        porcentaje = puntuacion['porcentaje_acierto']
        tendencia = puntuacion['tendencia']
        
        # Lógica de recomendación
        if porcentaje >= 80 and tendencia in ['mejorando', 'estable']:
            recomendacion_accion = 'siguiente'
            razon = f'Desempeño excelente ({porcentaje}%). Listo para aumentar dificultad.'
            confianza = 'alta'
        elif porcentaje >= 60 and tendencia == 'mejorando':
            recomendacion_accion = 'mantener'
            razon = f'Desempeño aceptable ({porcentaje}%). Sigues mejorando, mantén el nivel.'
            confianza = 'media'
        elif porcentaje < 40:
            recomendacion_accion = 'anterior'
            razon = f'Desempeño bajo ({porcentaje}%). Vuelve a practicar el nivel anterior.'
            confianza = 'alta'
        else:
            recomendacion_accion = 'mantener'
            razon = f'Desempeño en desarrollo ({porcentaje}%). Sigue practicando en este nivel.'
            confianza = 'media'
        
        # Calcular nuevo nivel
        nuevo_nivel = calcular_nuevo_nivel(nivel_actual, recomendacion_accion)
        
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
            'literal': '¡Correcto! Identificaste bien la información explícita del texto.',
            'inferencial': '¡Excelente! Realizaste una buena inferencia del contenido.',
            'crítico': '¡Muy bien! Emitiste un juicio crítico acertado.',
            'metacognitivo': '¡Perfecto! Reflexionaste correctamente sobre tu comprensión.'
        }
        feedback['mensaje'] = mensajes_exito.get(tipo_pregunta, '¡Respuesta correcta!')
    else:
        if not respuesta_usuario or respuesta_usuario.strip() == '':
            feedback['mensaje'] = 'Por favor, responde la pregunta. No dejes espacios en blanco.'
            feedback['pista'] = 'Lee nuevamente el texto y piensa en la respuesta.'
        else:
            mensajes_error = {
                'literal': 'No es correcta. Lee nuevamente la información explícita en el texto.',
                'inferencial': 'No es correcta. Piensa en lo que el autor quiere decir indirectamente.',
                'crítico': 'No es correcta. Evalúa el contenido de forma más reflexiva.',
                'metacognitivo': 'No es correcta. Piensa en tu proceso de comprensión.'
            }
            feedback['mensaje'] = mensajes_error.get(tipo_pregunta, 'Esa no es la respuesta correcta.')
            feedback['explicacion'] = f'La respuesta correcta es: {respuesta_correcta}'
            feedback['pista'] = 'Intenta de nuevo o avanza a la siguiente pregunta.'
    
    return feedback


def actualizar_nivel_estudiante(id_estudiante, nuevo_nivel):
    """
    Actualiza el nivel actual del estudiante en la tabla progreso
    
    Args:
        id_estudiante: ID del estudiante
        nuevo_nivel: Nuevo nivel (literal, inferencial, crítico, metacognitivo)
    
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
