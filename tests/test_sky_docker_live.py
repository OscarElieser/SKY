"""REAL Docker integration checks. Run only with SKY_LIVE_DOCKER_TEST=1.

No mocking: compile and run actual source in network-disabled, no-mount containers.
Pre-pull python:3.12-alpine and node:22-alpine explicitly outside this suite.
"""
import os
import pytest

from neural_core import sky_docker_builder as runner

pytestmark = pytest.mark.skipif(
    os.environ.get("SKY_LIVE_DOCKER_TEST") != "1",
    reason="Live Docker only on configured isolated CI/owner device",
)


def test_python_compile_run_and_unittest_really_pass():
    result = runner.build(
        "Python",
        {"main.py": "def suma(a, b):\n    return a+b\n\nprint(suma(19,23))\n",
         "tests/test_main.py":
            "import unittest\nfrom main import suma\n\n"
            "class SumTest(unittest.TestCase):\n"
            "    def test_suma(self):\n"
            "        self.assertEqual(suma(20,22),42)\n"},
        approved=True, expected_stdout="42", timeout_seconds=18,
    )
    assert result["ok"] is True, result
    assert result["compile"]["verified"] is True
    assert result["run"]["verified"] is True
    assert result["run"]["expected_stdout_matched"] is True
    assert result["tests"]["verified"] is True
    assert result["offline"] is True and result["host_execution"] is False


def test_python_compile_failure_is_not_silent():
    result = runner.build(
        "Python", {"main.py": "def roto(:\n    pass\n"}, approved=True,
    )
    assert result["status"] == "compile_failed"
    assert result["ok"] is False
    assert result["compile"]["verified"] is False
    assert result["run"] is None


def test_javascript_node_syntax_run_and_test_real():
    result = runner.build(
        "JavaScript",
        {"main.js": "function multiply(a,b){return a*b;}\n"
                    "module.exports={multiply};console.log(multiply(6,7));\n",
         "tests/main.test.js":
            "const test=require('node:test');\n"
            "const assert=require('node:assert/strict');\n"
            "test('multiplication',()=>{assert.equal(7*6,42);});\n"},
        approved=True, expected_stdout="42", timeout_seconds=18,
    )
    assert result["ok"] is True, result
    assert result["compile"]["verified"] is True
    assert result["run"]["verified"] is True
    assert result["tests"]["verified"] is True


def test_javascript_bad_syntax_is_rejected():
    result = runner.build(
        "JavaScript", {"main.js": "const a = ;\n"}, approved=True,
    )
    assert result["status"] == "compile_failed"
    assert result["ok"] is False


def test_javascript_expected_output_wrong_is_failure():
    result = runner.build(
        "JavaScript", {"main.js": "console.log('ERROR');"}, approved=True,
        expected_stdout="CORRECTO",
    )
    assert result["compile"]["verified"] is True
    assert result["run"]["verified"] is True
    assert result["run"]["expected_stdout_matched"] is False
    assert result["ok"] is False


def test_c_real_compilation_and_execution():
    result = runner.build(
        "C",
        {"main.c": '#include <stdio.h>\nint main(void){printf("42\\n");return 0;}\n'},
        approved=True, expected_stdout="42", timeout_seconds=22,
    )
    assert result["ok"] is True, result
    assert result["compile"]["verified"] is True
    assert result["run"]["verified"] is True


def test_cpp_real_compilation_and_execution():
    result = runner.build(
        "C++",
        {"main.cpp": '#include <iostream>\nint main(){std::cout << 6*7 << "\\n";return 0;}\n'},
        approved=True, expected_stdout="42", timeout_seconds=22,
    )
    assert result["ok"] is True, result
    assert result["compile"]["verified"] is True
    assert result["run"]["verified"] is True


def test_typescript_real_compile_transpile_and_execute_offline():
    result = runner.build(
        "TypeScript",
        {"main.ts": "const resultado: number = 6 * 7;\nconsole.log(resultado);\n"},
        approved=True, expected_stdout="42", timeout_seconds=22,
    )
    assert result["ok"] is True, result
    assert result["compile"]["verified"] is True
    assert result["run"]["verified"] is True


def test_c_compilation_error_does_not_run():
    result = runner.build(
        "C", {"main.c": "int main( { syntax error }\n"}, approved=True,
    )
    assert result["ok"] is False
    assert result["status"] == "compile_failed"
    assert result["run"] is None
