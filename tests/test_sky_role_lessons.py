"""Regresiones de memoria de herramientas: clasificación sin filtración de datos."""
from __future__ import annotations
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from neural_core import sky_role_lessons as lessons
from neural_core import sky_verified_roles as roles

class ToolLessonsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict("os.environ", {
            "SKY_ROLE_LESSONS_DB": str(Path(self.temp.name) / "lessons.sqlite"),
            "SKY_VERIFIED_ROLES_DB": str(Path(self.temp.name) / "metrics.sqlite"),
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_failed_tool_generates_lesson_in_next_execution(self):
        first = roles.run_plan([{"id":"fail", "role":"datos","tool":"resumen",
                                 "args":{"values":[1,"private-string"]}}])
        self.assertEqual(first["status"],"FAILED")
        self.assertEqual(first["steps"][0]["issue_category"],"invalid_input")
        memory = lessons.lesson("datos","resumen")
        self.assertEqual(memory["issue"],"invalid_input")
        second = roles.run_plan([{"id":"good", "role":"datos","tool":"resumen",
                                 "args":{"values":[2,4,6]}}])
        self.assertEqual(second["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertEqual(second["steps"][0]["prior_lesson"]["issue"],"invalid_input")
        self.assertEqual(second["steps"][0]["result"]["mean"],4)

    def test_review_mismatch_is_recorded_and_cannot_continue(self):
        def bad(args, prev):
            return {"count":3,"mean":999,"median":2,"minimum":1,"maximum":3}
        with patch.dict(roles.EXECUTORS,{("datos","resumen"):bad}):
            result = roles.run_plan([
                {"id":"a","role":"datos","tool":"resumen","args":{"values":[1,2,3]}},
                {"id":"b","role":"matematicas","tool":"calcular",
                 "depends_on":"a","args":{"expression":"mean+1"}},
            ])
        self.assertEqual(result["completed_steps"],1)
        self.assertEqual(result["steps"][0]["attempts"],2)
        self.assertEqual(result["steps"][0]["issue_category"],"verification_mismatch")
        self.assertEqual(lessons.lesson("datos","resumen")["issue"],"verification_mismatch")

    def test_permissions_fail_closed_and_no_network_attempted(self):
        r=roles.run_plan([{"id":"search","role":"investigacion",
                           "tool":"semantic_scholar","args":{"query":"science"}}])
        self.assertEqual(r["status"],"FAILED")
        self.assertEqual(r["steps"][0]["issue_category"],"permission_required")

    def test_learned_memory_does_not_store_inputs_or_errors(self):
        secret="SUPER_SECRET_ABC_908070"
        roles.run_plan([{"id":"one","role":"programacion","tool":"sintaxis_python",
                         "args":{"source":"x = '"+secret+"' + "}}])
        path=Path(self.temp.name)/"lessons.sqlite"
        self.assertTrue(path.exists())
        self.assertNotIn(secret.encode(),path.read_bytes())
        result=lessons.report()
        self.assertFalse(result["contains_private_inputs"])
        self.assertFalse(result["model_weights_updated"])

    def test_metrics_distinguish_external_unverified(self):
        lessons.record("investigacion","semantic_scholar","RETRIEVED_UNVERIFIED")
        lessons.record("matematicas","calcular","VERIFIED_LIMITED_SCOPE",duration_ms=4)
        lessons.record("matematicas","calcular","FAILED",issue="verification_mismatch",attempts=2)
        health=lessons.report()
        self.assertEqual(health["total_observations"],3)
        tools={(x["role"],x["tool"]):x for x in health["tools"]}
        self.assertEqual(tools[("investigacion","semantic_scholar")]["unverified_external"],1)
        self.assertEqual(tools[("matematicas","calcular")]["retried_operations"],1)
        self.assertEqual(tools[("matematicas","calcular")]["local_verification_rate"],0.5)

    def test_old_observations_are_not_used_for_advice(self):
        lessons.record("datos","resumen","FAILED",issue="invalid_input")
        path=Path(self.temp.name)/"lessons.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("UPDATE role_lessons SET observed_at=0")
        self.assertIsNone(lessons.lesson("datos","resumen"))
        self.assertEqual(lessons.report()["total_observations"],0)

    def test_closed_taxonomy_and_limits(self):
        with self.assertRaises(ValueError):
            lessons.record("datos","resumen","FAILED",issue="private content")
        with self.assertRaises(ValueError):
            lessons.record("datos","resumen","FAILED",issue="invalid_input",attempts=10000)
        with self.assertRaises(ValueError):
            lessons.record("datos","resumen","VERIFIED_LIMITED_SCOPE",issue="invalid_input")
        with self.assertRaises(ValueError):
            lessons.lesson("mal; DELETE FROM data","resumen")

    def test_requires_no_api_credentials_for_memory(self):
        result=roles.run_plan([{"id":"s","role":"quimica","tool":"masa_molar","args":{"formula":"H2O"}}])
        self.assertEqual(result["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertTrue(result["steps"][0]["lesson_recorded"])
        self.assertIsNone(lessons.lesson("quimica","masa_molar"))

if __name__=="__main__":
    unittest.main()
