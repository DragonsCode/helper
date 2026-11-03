import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid


class PaymentInputTests(unittest.IsolatedAsyncioTestCase):
    def load_handler(self, payment, database):
        path = Path(__file__).resolve().parents[1] / "helper/api/app.py"
        tree = ast.parse(path.read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "pay")
        fn.decorator_list = []
        namespace = {"Payment": payment, "sqlite3": database, "uuid": uuid}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
        return namespace["pay"]

    async def test_invalid_usernames_do_not_create_payments(self):
        payment = SimpleNamespace(create=Mock(side_effect=AssertionError("Payment must not be called")))
        database = SimpleNamespace(connect=Mock(side_effect=AssertionError("Database must not be called")))
        handler = self.load_handler(payment, database)
        for username in ("", "a", "abc", "   "):
            with self.subTest(username=username):
                self.assertEqual(await handler(username), {"error": "invalid username"})
        payment.create.assert_not_called()
        database.connect.assert_not_called()

    async def test_valid_username_is_normalized(self):
        payment = SimpleNamespace(create=Mock(return_value=SimpleNamespace(id="synthetic-payment-id", confirmation=SimpleNamespace(confirmation_url="https://example.test/checkout"))))
        connection = Mock()
        connection.cursor.return_value.execute.return_value.fetchall.return_value = []
        database = SimpleNamespace(connect=Mock(return_value=connection), PARSE_DECLTYPES=1, PARSE_COLNAMES=2)
        result = await self.load_handler(payment, database)(" ValidUser ")
        self.assertEqual(result, "https://example.test/checkout")
        connection.cursor.return_value.execute.assert_any_call('INSERT INTO site (id, username) VALUES (?, ?)', ("synthetic-payment-id", "validuser"))
        connection.close.assert_called_once()
