-- ===========================================
-- SCRIPT PARA DATOS DE PRUEBA
-- Usar este archivo para insertar datos de ejemplo en la base de datos
-- Ejecutar después de crear las tablas con creacion_bd.sql
-- ===========================================

--- ROLES
CREATE TABLE roles (
  id_rol INT AUTO_INCREMENT PRIMARY KEY,
  nombre_rol VARCHAR(50)
);
-- USUARIOS
CREATE TABLE usuarios (
  id_usuario INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  contraseña VARCHAR(255) NOT NULL,
  id_rol INT NOT NULL,
  fecha_registro DATE,
  FOREIGN KEY (id_rol) REFERENCES roles(id_rol)
);

-- ESTUDIANTES
CREATE TABLE estudiantes (
  id_estudiante INT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NOT NULL UNIQUE,
  nivel_actual VARCHAR(20),
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);

-- DOCENTES
CREATE TABLE docentes (
  id_docente INT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NOT NULL UNIQUE,
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);

-- TEXTOS
CREATE TABLE textos (
  id_texto INT AUTO_INCREMENT PRIMARY KEY,
  titulo VARCHAR(100),
  contenido TEXT,
  nivel VARCHAR(20)
);

-- PREGUNTAS
CREATE TABLE preguntas (
  id_pregunta INT AUTO_INCREMENT PRIMARY KEY,
  id_texto INT NOT NULL,
  enunciado TEXT NOT NULL,
  tipo VARCHAR(20) NOT NULL,
  tipo_respuesta ENUM('opcion', 'texto') NOT NULL DEFAULT 'texto',
  orden TINYINT,
  FOREIGN KEY (id_texto) REFERENCES textos(id_texto)
);

-- OPCIONES PARA PREGUNTAS DE SELECCIÓN
CREATE TABLE opciones_pregunta (
  id_opcion INT AUTO_INCREMENT PRIMARY KEY,
  id_pregunta INT NOT NULL,
  texto_opcion VARCHAR(500) NOT NULL,
  es_correcta BOOLEAN NOT NULL DEFAULT FALSE,
  FOREIGN KEY (id_pregunta) REFERENCES preguntas(id_pregunta) ON DELETE CASCADE
);

-- RESPUESTAS CORRECTAS
CREATE TABLE respuestas_correctas (
  id_respuesta INT AUTO_INCREMENT PRIMARY KEY,
  id_pregunta INT,
  respuesta TEXT,
  FOREIGN KEY (id_pregunta) REFERENCES preguntas(id_pregunta)
);

-- RESPUESTAS DEL ESTUDIANTE
CREATE TABLE respuestas_estudiante (
  id_respuesta_est INT AUTO_INCREMENT PRIMARY KEY,
  id_estudiante INT,
  id_pregunta INT,
  respuesta TEXT,
  es_correcta BOOLEAN,
  tiempo_respuesta INT,
  fecha DATE,
  FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiante),
  FOREIGN KEY (id_pregunta) REFERENCES preguntas(id_pregunta)
);

-- DIAGNOSTICO
CREATE TABLE diagnostico (
  id_diagnostico INT AUTO_INCREMENT PRIMARY KEY,
  id_estudiante INT,
  puntaje INT,
  nivel_asignado VARCHAR(20),
  fecha DATE,
  FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiante)
);

-- PROGRESO
CREATE TABLE progreso (
  id_progreso INT AUTO_INCREMENT PRIMARY KEY,
  id_estudiante INT NOT NULL UNIQUE,
  nivel_actual VARCHAR(20),
  porcentaje_avance FLOAT,
  FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiante)
);

-- RETROALIMENTACION
CREATE TABLE retroalimentacion (
  id_feedback INT AUTO_INCREMENT PRIMARY KEY,
  id_respuesta_est INT NOT NULL UNIQUE,
  mensaje TEXT NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  FOREIGN KEY (id_respuesta_est) REFERENCES respuestas_estudiante(id_respuesta_est)
);

-- REPORTES
CREATE TABLE reportes (
  id_reporte INT AUTO_INCREMENT PRIMARY KEY,
  id_docente INT,
  id_estudiante INT,
  resumen TEXT,
  fecha DATE,
  FOREIGN KEY (id_docente) REFERENCES docentes(id_docente),
  FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiante)
);

-- NOTIFICACIONES
CREATE TABLE notificaciones (
  id_notificacion INT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT,
  mensaje TEXT,
  leido BOOLEAN,
  fecha DATE,
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);
