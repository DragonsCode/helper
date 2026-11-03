"""Exercise application credential expressions without importing network clients."""
import ast
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPECS = [('helper/config.py', 'TOKEN', 'TELEGRAM_BOT_TOKEN'), ('helper/config.py', 'INVOICE_TOKEN', 'TELEGRAM_INVOICE_TOKEN'), ('helper/api/app.py', 'Configuration.secret_key', 'YOOKASSA_SECRET_KEY'), ('helper/api/app.py', 'Configuration.account_id', 'YOOKASSA_SHOP_ID')]


def expression(path, target):
    tree = ast.parse((ROOT / path).read_text())
    if target.startswith("pos:"):
        _, function, index = target.split(":")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == function:
                return ast.Expression(node.args[int(index)])
    elif target.startswith("call:"):
        _, function, keyword = target.split(":")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == function:
                for arg in node.keywords:
                    if arg.arg == keyword:
                        return ast.Expression(arg.value)
    else:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any((isinstance(t, ast.Name) and t.id == target) or (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id + "." + t.attr == target) for t in node.targets):
                return ast.Expression(node.value)
    raise AssertionError("Application credential expression was not found")


def read_setting(path, target):
    namespace = {"os": os}
    helper = ROOT / "helper/runtime_config.py"
    if helper.exists():
        exec(compile(helper.read_text(), str(helper), "exec"), namespace)
    return eval(compile(expression(path, target), path, "eval"), namespace)


class SecretConfigurationTests(unittest.TestCase):
    def test_application_uses_environment_credentials(self):
        for path, target, name in SPECS:
            with self.subTest(setting=name), patch.dict(os.environ, {name: "synthetic-test-value"}, clear=True):
                self.assertTrue(read_setting(path, target) == "synthetic-test-value", "Credential must come from the environment")

    def test_missing_and_blank_credentials_fail_without_values(self):
        for path, target, name in SPECS:
            for environment in ({}, {name: "  "}):
                with self.subTest(setting=name, blank=bool(environment)), patch.dict(os.environ, environment, clear=True):
                    with self.assertRaises(RuntimeError) as raised:
                        read_setting(path, target)
                    self.assertIn(name, str(raised.exception))

    def test_no_provider_credentials_in_python_source(self):
        patterns = (r"\b[0-9]{6,12}:[A-Za-z0-9_-]{30,}", r"vk1\.[A-Za-z0-9_-]{30,}", r"(?:mysql|postgres(?:ql)?)(?:\+\w+)?://[^{}\s/:]+:[^{}\s/@]+@")
        for path in ROOT.rglob("*.py"):
            if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
                continue
            content = path.read_text()
            for pattern in patterns:
                self.assertFalse(bool(re.search(pattern, content)), f"Credential-shaped value in {path.relative_to(ROOT)}")


if __name__ == "__main__":
    unittest.main()
