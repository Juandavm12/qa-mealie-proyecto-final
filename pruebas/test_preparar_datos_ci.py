"""Stdlib tests for preparar_datos_ci; the Mealie API is faked."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import preparar_datos_ci as ci
from test_preparar_datos import ADMIN_TOKEN, FakeApi

CI_ENV = {"GITHUB_ACTIONS": "true", "MEALIE_URL": "http://localhost:9925"}


class PrepareCiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmp.name) / ".env.qa"
        self.api = FakeApi()
        self.out = io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_ci(self, environ):
        return ci.main(environ=environ, api=self.api, env_path=self.env_path, out=self.out)

    def passwords(self) -> list[str]:
        lines = self.env_path.read_text(encoding="utf-8").splitlines()
        return [line.split("=", 1)[1] for line in lines if "_PASSWORD=" in line]

    def test_refuses_outside_github_actions(self):
        self.assertEqual(self.run_ci({"MEALIE_URL": "http://localhost:9925"}), 2)
        self.assertEqual(self.api.calls, [])
        self.assertFalse(self.env_path.exists())

    def test_refuses_when_github_actions_flag_is_not_exactly_true(self):
        for value in ("false", "1", "TRUE"):
            self.assertEqual(self.run_ci({**CI_ENV, "GITHUB_ACTIONS": value}), 2, value)
        self.assertEqual(self.api.calls, [])

    def test_refuses_non_local_url(self):
        for url in ("https://mealie.example.com", "http://example.com"):
            self.assertEqual(self.run_ci({**CI_ENV, "MEALIE_URL": url}), 2, url)
        self.assertEqual(self.api.calls, [])

    def test_partial_failure_still_masks_created_passwords(self):
        self.api.fail_user_create = "qa_usuario_b"
        self.assertEqual(self.run_ci(CI_ENV), 2)
        passwords = self.passwords()
        self.assertEqual(len(passwords), 1)
        self.assertIn(f"::add-mask::{passwords[0]}", self.out.getvalue().splitlines())

    def test_refuses_when_instance_is_not_fresh(self):
        self.api.default_admin_ok = False
        self.assertEqual(self.run_ci(CI_ENV), 2)
        self.assertFalse(any(c[0] == "POST" and c[1].startswith("/api/admin") for c in self.api.calls))
        self.assertFalse(self.env_path.exists())

    def test_prepares_users_and_masks_passwords(self):
        self.assertEqual(self.run_ci(CI_ENV), 0)
        self.assertEqual(len(self.api.users), 3)
        passwords = self.passwords()
        self.assertEqual(len(passwords), 3)
        lines = self.out.getvalue().splitlines()
        for password in passwords:
            self.assertIn(f"::add-mask::{password}", lines)
            leaks = [line for line in lines if password in line and not line.startswith("::add-mask::")]
            self.assertEqual(leaks, [])
        self.assertNotIn(ADMIN_TOKEN, self.out.getvalue())


if __name__ == "__main__":
    unittest.main()
