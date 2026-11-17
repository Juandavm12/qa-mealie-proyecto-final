"""Stdlib tests for preparar_datos; the Mealie API, getpass and TTY are faked."""
from __future__ import annotations

import io
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import preparar_datos as pd

ADMIN_TOKEN = "fake-admin-token-for-tests"
GROUP_ID = "11111111-1111-1111-1111-111111111111"


class FakeApi:
    """In-memory stand-in for the subset of the Mealie API the script uses."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.admin = True
        self.users: list[dict] = []
        self.households = [{"id": "h0", "name": "Family", "groupId": GROUP_ID}]
        self.passwords: dict[str, str] = {}
        self.fail_user_create: str | None = None
        self.default_admin_ok = True

    def request(self, method, path, *, token=None, json=None, form=None):
        self.calls.append((method, path, token, json, form))
        if path == "/api/users/self" and token == ADMIN_TOKEN:
            return 200, {"admin": self.admin, "groupId": GROUP_ID, "group": "Home",
                         "username": "admin"}
        if path == "/api/users/self":
            user = next(u for u in self.users if u["token"] == token)
            return 200, {"username": user["username"], "household": user["household"],
                         "admin": False, "groupId": GROUP_ID}
        if path.startswith("/api/admin/users") and method == "GET":
            return 200, {"items": [{"username": u["username"], "email": u["email"]}
                                   for u in self.users]}
        if path.startswith("/api/admin/households") and method == "GET":
            return 200, {"items": self.households}
        if path == "/api/admin/households" and method == "POST":
            household = {"id": f"h{len(self.households)}", **json}
            self.households.append(household)
            return 201, household
        if path == "/api/admin/users" and method == "POST":
            if json["username"] == self.fail_user_create:
                return 500, {"detail": "boom"}
            self.passwords[json["email"]] = json["password"]
            self.users.append({**json, "token": "tok-" + json["username"]})
            return 201, {"username": json["username"]}
        if path == "/api/auth/token" and form["username"] == "changeme@example.com":
            if self.default_admin_ok and form["password"] == "MyPassword":
                return 200, {"access_token": ADMIN_TOKEN, "token_type": "bearer"}
            return 401, {"detail": "Unauthorized"}
        if path == "/api/auth/token":
            user = next(u for u in self.users if u["email"] == form["username"])
            if self.passwords[form["username"]] != form["password"]:
                return 401, {"detail": "Unauthorized"}
            return 200, {"access_token": user["token"], "token_type": "bearer"}
        raise AssertionError(f"unexpected call {method} {path}")


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmp.name) / ".env.qa"
        self.api = FakeApi()
        self.tty = True
        self.token_reads = 0
        self.out = io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self):
        def read_token(prompt):
            self.token_reads += 1
            return ADMIN_TOKEN

        deps = pd.Deps(api=self.api, read_token=read_token, isatty=lambda: self.tty,
                       env_path=self.env_path, out=self.out)
        return pd.main([], deps=deps)

    def env(self) -> dict[str, str]:
        lines = self.env_path.read_text(encoding="utf-8").splitlines()
        return dict(line.split("=", 1) for line in lines if line and not line.startswith("#"))

    def test_creates_households_users_and_env(self):
        self.assertEqual(self.run_main(), 0)
        names = {h["name"] for h in self.api.households}
        self.assertTrue({"QA-Hogar-A", "QA-Hogar-B"} <= names)
        by_name = {u["username"]: u for u in self.api.users}
        self.assertEqual(by_name["qa_usuario_a"]["household"], "QA-Hogar-A")
        self.assertEqual(by_name["qa_usuario_b"]["household"], "QA-Hogar-B")
        self.assertEqual(by_name["qa_usuario_c"]["household"], "QA-Hogar-A")
        self.assertTrue(all(u["admin"] is False for u in self.api.users))
        env = self.env()
        self.assertEqual(env["QA_USER_A_EMAIL"], by_name["qa_usuario_a"]["email"])
        self.assertEqual(env["QA_USER_B_PASSWORD"], self.api.passwords[env["QA_USER_B_EMAIL"]])
        self.assertGreaterEqual(len(env["QA_USER_A_PASSWORD"]), 20)
        self.assertEqual(len({env[f"QA_USER_{k}_PASSWORD"] for k in "ABC"}), 3)

    def test_admin_token_never_written(self):
        self.run_main()
        self.assertNotIn(ADMIN_TOKEN, self.env_path.read_text(encoding="utf-8"))
        self.assertNotIn(ADMIN_TOKEN, self.out.getvalue())

    def test_passwords_never_printed(self):
        self.run_main()
        for key, value in self.env().items():
            if key.endswith("_PASSWORD"):
                self.assertNotIn(value, self.out.getvalue())

    def test_reuses_existing_household(self):
        self.api.households.append({"id": "hx", "name": "QA-Hogar-A", "groupId": GROUP_ID})
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(sum(h["name"] == "QA-Hogar-A" for h in self.api.households), 1)

    def test_refuses_when_env_file_exists(self):
        self.env_path.write_text("x=1\n", encoding="utf-8")
        self.assertEqual(self.run_main(), 2)
        self.assertEqual(self.token_reads, 0)
        self.assertEqual(self.env_path.read_text(encoding="utf-8"), "x=1\n")

    def test_requires_tty(self):
        self.tty = False
        self.assertEqual(self.run_main(), 2)
        self.assertEqual(self.token_reads, 0)

    def test_refuses_non_admin_token(self):
        self.api.admin = False
        self.assertEqual(self.run_main(), 2)
        self.assertFalse(any(c[0] == "POST" for c in self.api.calls))

    def test_refuses_when_synthetic_user_exists(self):
        self.api.users.append({"username": "qa_usuario_b", "email": "x@example.com",
                               "token": "t", "household": "QA-Hogar-B"})
        self.assertEqual(self.run_main(), 2)
        self.assertFalse(any(c[0] == "POST" for c in self.api.calls))
        self.assertFalse(self.env_path.exists())

    def test_partial_failure_keeps_created_credentials(self):
        self.api.fail_user_create = "qa_usuario_b"
        self.assertEqual(self.run_main(), 2)
        env = self.env()
        self.assertIn("QA_USER_A_PASSWORD", env)
        self.assertNotIn("QA_USER_B_PASSWORD", env)

    def test_validation_error_never_echoes_password(self):
        original = self.api.request

        def echoing(method, path, **kwargs):
            if path == "/api/admin/users" and method == "POST":
                body = kwargs["json"]
                return 422, {"detail": [{"loc": ["body", "x"], "msg": "Field required",
                                         "input": body}]}
            return original(method, path, **kwargs)

        self.api.request = echoing
        err = io.StringIO()
        with unittest.mock.patch("sys.stderr", err):
            self.assertEqual(self.run_main(), 2)
        self.assertIn("Field required", err.getvalue())
        self.assertNotIn("password", err.getvalue().lower().replace("passwords", ""))

    def test_rejects_privilege_drift_after_login(self):
        original = self.api.request

        def drifting(method, path, **kwargs):
            status, body = original(method, path, **kwargs)
            if path == "/api/users/self" and kwargs.get("token") != ADMIN_TOKEN:
                body = {**body, "admin": True}
            return status, body

        self.api.request = drifting
        self.assertEqual(self.run_main(), 2)

    def test_refuses_plain_http_to_remote_host(self):
        def read_token(prompt):
            self.token_reads += 1
            return ADMIN_TOKEN

        deps = pd.Deps(api=self.api, read_token=read_token, isatty=lambda: True,
                       env_path=self.env_path, out=self.out)
        self.assertEqual(pd.main(["--url", "http://example.com"], deps=deps), 2)
        self.assertEqual(self.token_reads, 0)
        self.assertEqual(self.api.calls, [])
        self.assertFalse(self.env_path.exists())

    def test_env_write_failure_reports_usernames_only(self):
        original = pd.write_env

        def failing(path, base_url, created):
            raise PermissionError("denied")

        pd.write_env = failing
        err = io.StringIO()
        try:
            with unittest.mock.patch("sys.stderr", err):
                self.assertEqual(self.run_main(), 0)
        finally:
            pd.write_env = original
        self.assertIn("qa_usuario_a", err.getvalue())
        for password in self.api.passwords.values():
            self.assertNotIn(password, err.getvalue())

    def test_verifies_each_login_and_household(self):
        self.assertEqual(self.run_main(), 0)
        logins = [c for c in self.api.calls if c[1] == "/api/auth/token"]
        self.assertEqual(len(logins), 3)
        self.assertIn("verified", self.out.getvalue())


if __name__ == "__main__":
    unittest.main()
