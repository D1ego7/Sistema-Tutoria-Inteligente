import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
sys.path.insert(0, str(SITE_PACKAGES))
sys.path.insert(0, str(ROOT))

import app as app_module
from flask_jwt_extended import create_access_token


class FakeConnection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self):
        self.lastrowid = None
        self.executed = []
        self._result = None
        self.closed = False

    def execute(self, query, params=None):
        compact = " ".join(query.split())
        self.executed.append((compact, params))
        if "FROM estudiantes WHERE id_usuario" in compact:
            self._result = {"id_estudiante": 4}
        elif "FROM preguntas p" in compact and "JOIN textos" in compact:
            self._result = {
                "tipo": "literal",
                "tipo_respuesta": "texto",
                "id_texto": 9,
                "nivel": "literal",
                "respuesta": "en el bosque"
            }
        elif "INSERT INTO respuestas_estudiante" in compact:
            self.lastrowid = 501
            self._result = None
        elif "SELECT COUNT(*) FROM respuestas_estudiante" in compact:
            self._result = {"COUNT(*)": 1}
        else:
            self._result = None
        return 1

    def fetchone(self):
        return self._result

    def close(self):
        self.closed = True


class AppSecurityTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()
        with app_module.app.app_context():
            self.student_token = create_access_token(
                identity="8",
                additional_claims={"rol": 1, "nombre": "Estudiante"}
            )

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.student_token}"}

    def test_protected_route_uses_consistent_jwt_identity(self):
        response = self.client.get("/protected", headers=self.auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertIn("Estudiante", response.get_json()["message"])

    def test_diagnostic_rejects_client_calculated_booleans(self):
        response = self.client.post(
            "/diagnostico-inicial",
            headers=self.auth_headers(),
            json={"respuestas": [True, True, True, True]}
        )
        self.assertEqual(response.status_code, 400)

    def test_diagnostic_is_scored_on_server(self):
        respuestas = [
            {"id": 1, "respuesta": "El ratón"},
            {"id": 2, "respuesta": "Bajo un árbol"},
            {"id": 3, "respuesta": "Porque le prometió ayudarlo"},
            {"id": 4, "respuesta": "Hasta los más pequeños pueden ayudar"},
        ]
        self.assertEqual(app_module.evaluar_respuestas_diagnostico(respuestas), [True] * 4)

    def test_feedback_is_persisted_with_the_response(self):
        connection = FakeConnection()
        cursor = FakeCursor()
        progress = {
            "evaluacion": {
                "total_respuestas": 1,
                "respuestas_correctas": 1,
                "porcentaje_acierto": 100
            }
        }

        with patch.object(app_module, "get_db_cursor", return_value=(connection, cursor)), \
             patch.object(app_module, "obtener_nivel_actual", return_value="literal"), \
             patch.object(app_module, "sincronizar_progreso_estudiante", return_value=progress):
            response = self.client.post(
                "/respuesta-con-feedback",
                headers=self.auth_headers(),
                json={
                    "id_pregunta": 17,
                    "respuesta": "en el bosque",
                    "tiempo_respuesta": 12
                }
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(any("INSERT INTO retroalimentacion" in query for query, _ in cursor.executed))
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)


if __name__ == "__main__":
    unittest.main()
