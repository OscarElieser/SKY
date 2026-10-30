"""Pruebas aisladas: sin red real, ni permisos de dispositivo."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from neural_core import sky_verified_roles as roles

class RealRolesTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.env = patch.dict("os.environ", {"SKY_VERIFIED_ROLES_DB": str(Path(self.dir.name) / "events.sqlite")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.dir.cleanup()

    def test_multiagent_chain_real(self):
        r = roles.run_plan([
            {"id": "stats", "role": "datos", "tool": "resumen", "args": {"values": [2, 4, 6]}},
            {"id": "calc", "role": "matematicas", "tool": "calcular",
             "depends_on": "stats", "args": {"expression": "mean * 3"}},
        ])
        self.assertEqual(r["status"], "VERIFIED_LIMITED_SCOPE")
        self.assertEqual(r["steps"][1]["result"]["value"], 12)
        self.assertEqual(sum(x["count"] for x in roles.metrics()["events"]), 2)

    def test_no_eval_in_arithmetic(self):
        result = roles.run_plan([{"id": "x", "role": "matematicas", "tool": "calcular",
                                  "args": {"expression": "__import__('os').system('whoami')"}}])
        self.assertEqual(result["status"], "FAILED")

    def test_audit_detects_real_pattern_but_not_full_security(self):
        r = roles.run_plan([{"id": "x", "role": "ciberseguridad", "tool": "auditoria_python",
                             "args": {"source": "import subprocess\nsubprocess.run('ls',shell=True)\neval('x')"}}])
        self.assertEqual(len(r["steps"][0]["result"]["findings"]), 2)
        self.assertFalse(r["steps"][0]["result"]["code_executed"])

    def test_python_syntax_without_execution(self):
        r = roles.run_plan([{"id": "x", "role": "programacion", "tool": "sintaxis_python",
                             "args": {"source": "def hola(): return 1"}}])
        self.assertEqual(r["steps"][0]["result"]["functions"], ["hola"])

    def test_network_denied_without_consent(self):
        r = roles.run_plan([{"id": "x", "role": "investigacion", "tool": "semantic_scholar",
                             "args": {"query": "learning science"}}])
        self.assertEqual(r["status"], "FAILED")

    def test_external_sources_are_not_fact_checked(self):
        fake = types.ModuleType("neural_core.sky_research_connectors")
        fake.semantic_scholar = lambda query, limit: {"items": [{"title": "Test paper", "year": 2024}]}
        with patch.dict(sys.modules, {"neural_core.sky_research_connectors": fake}):
            r = roles.run_plan([{"id": "x", "role": "investigacion", "tool": "semantic_scholar",
                                 "args": {"query": "learning science"}}], allow_network=True)
        self.assertEqual(r["status"], "REQUIRES_SOURCE_VERIFICATION")
        self.assertEqual(r["steps"][0]["status"], "RETRIEVED_UNVERIFIED")

    def test_unimplemented_role_is_not_executable(self):
        with self.assertRaises(roles.RoleError):
            roles.run_plan([{"id": "x", "role": "educacion", "tool": "fingir_clase", "args": {}}])
        self.assertTrue(any(x["id"] == "viajes" and x["execution"] == "catalogue_only"
                            for x in roles.catalogue()["roles"]))

    def test_forward_dependency_rejected(self):
        with self.assertRaises(roles.RoleError):
            roles.run_plan([{"id": "x", "role": "datos", "tool": "resumen",
                             "depends_on": "futuro", "args": {"values": [1]}}])

    def test_private_code_not_saved_to_sqlite(self):
        secret = "my-private-secret-token"
        roles.run_plan([{"id": "x", "role": "programacion", "tool": "sintaxis_python",
                         "args": {"source": "key = '" + secret + "'"}}])
        self.assertNotIn(secret.encode(), (Path(self.dir.name) / "events.sqlite").read_bytes())

    def test_backend_route_registered(self):
        self.assertIn("sky_verified_roles_router",
                      Path("metaverse/api.py").read_text(encoding="utf8"))

if __name__ == "__main__":
    unittest.main()
