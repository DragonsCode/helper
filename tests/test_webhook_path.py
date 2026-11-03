import ast
import hashlib
from pathlib import Path
import unittest


class WebhookPathTests(unittest.TestCase):
    def test_webhook_path_does_not_expose_bot_api_token(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / "helper/api/app.py").read_text())
        value = next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WEBHOOK_PATH" for t in n.targets))
        paths = []
        for token in ["synthetic-bot-token-one", "synthetic-bot-token-two"]:
            path = eval(compile(ast.Expression(value), "app.py", "eval"), {"TOKEN": token, "hashlib": hashlib})
            self.assertTrue(path.startswith("/bot/"))
            self.assertNotIn(token, path)
            paths.append(path)
        self.assertNotEqual(*paths)
