"""Stdlib tests for ejecutar_zap; Docker and the Mealie login are faked."""
from __future__ import annotations

import io
import json
import tarfile
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import ejecutar_zap as ez

TOKEN = "fake-session-token-for-tests"
SPEC = {"openapi": "3.1.0", "paths": {
    "/api/admin/users": {"get": {}, "post": {}},
    "/api/auth/refresh": {"post": {}},
    "/api/users/api-tokens": {"post": {}},
    "/api/users/self": {"get": {}},
    "/api/users/{item_id}": {"get": {}, "put": {}},
    "/api/foods": {"get": {}, "post": {}},
    "/api/households/webhooks": {"get": {}, "post": {}},
    "/api/recipes/create/url": {"post": {}},
    "/api/recipes/{slug}/image": {"post": {}, "put": {}},
    "/api/recipes": {"get": {}, "post": {}},
    "/api/households/mealplans/{item_id}": {"get": {}, "put": {}, "delete": {}, "parameters": []},
}}


def tar_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeDocker:
    def __init__(self):
        self.calls: list[tuple[list[str], dict | None]] = []
        self.image_id = ez.ZAP_IMAGE_ID
        self.helper_id = ez.HELPER_IMAGE_ID
        self.mealie_image = ez.MEALIE_IMAGE_ID
        self.health = "healthy"
        self.fail_prefix: str | None = None
        self.inputs: list[bytes] = []
        self.scan_code = 0
        self.scan_output = "PASS: 10 WARN-NEW: 2\n"
        self.report = "<html>report</html>"

    def run(self, argv, env=None, input=None):
        self.calls.append((list(argv), env))
        joined = " ".join(argv)
        if input is not None:
            self.inputs.append(input)
        if self.fail_prefix and joined.startswith(self.fail_prefix):
            return 1, b"failed"
        if argv[:3] == ["docker", "image", "inspect"]:
            image = self.image_id if argv[3] == ez.ZAP_IMAGE else self.helper_id
            return 0, f"{image} linux/amd64\n".encode()
        if argv[:2] == ["docker", "inspect"]:
            return 0, f"running {self.health} {self.mealie_image}\n".encode()
        if "zap-baseline.py" in joined or "zap-api-scan.py" in joined:
            return self.scan_code, self.scan_output.encode()
        if "tar" in argv and "cf" in argv:
            return 0, tar_bytes({"./report.html": self.report, "./report.json": "{}"})
        return 0, b""


class ZapFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reports = Path(self.tmp.name)
        self.docker = FakeDocker()
        self.token_calls = 0
        self.out = io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def get_token(self):
        self.token_calls += 1
        return TOKEN

    def run_main(self, *args):
        deps = ez.Deps(run=self.docker.run, get_token=self.get_token,
                       fetch_spec=lambda: json.loads(json.dumps(SPEC)),
                       reports_root=self.reports, out=self.out)
        return ez.main(list(args), deps=deps)

    def scan_call(self):
        scripts = {"zap-baseline.py", "zap-api-scan.py"}
        return next(c for c in self.docker.calls if scripts & set(c[0]))

class ZapRunnerTests(ZapFixture):
    def test_inert_without_execute(self):
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline"), 0)
        self.assertFalse(any(c[0][:2] == ["docker", "run"] for c in self.docker.calls))
        self.assertEqual(self.token_calls, 0)
        self.assertFalse((self.reports / "RUN-ZAP-001").exists())

    def test_rejects_invalid_run_id(self):
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-1", "--mode", "baseline"), 2)
        self.assertEqual(self.docker.calls, [])

    def test_fails_closed_on_image_drift(self):
        self.docker.image_id = "sha256:other"
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline",
                                       "--execute"), 2)
        self.assertFalse(any(c[0][:2] == ["docker", "run"] for c in self.docker.calls))

    def test_fails_closed_when_mealie_unhealthy(self):
        self.docker.health = "starting"
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline",
                                       "--execute"), 2)
        self.assertFalse(any(c[0][:2] == ["docker", "run"] for c in self.docker.calls))

    def test_refuses_existing_run_dir(self):
        (self.reports / "RUN-ZAP-001").mkdir()
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline",
                                       "--execute"), 2)
        self.assertFalse(any(c[0][:2] == ["docker", "run"] for c in self.docker.calls))

    def test_baseline_is_unauthenticated_and_shares_mealie_network(self):
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline",
                                       "--execute"), 0)
        argv, env = self.scan_call()
        self.assertEqual(self.token_calls, 0)
        self.assertIn(f"container:{ez.MEALIE_CONTAINER}", argv)
        self.assertNotIn("-p", argv)
        self.assertFalse(any("ZAP_AUTH" in a for a in argv))
        self.assertTrue(env is None or "ZAP_AUTH_HEADER_VALUE" not in env)

    def test_api_token_only_through_environment(self):
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-002", "--mode", "api",
                                       "--execute"), 0)
        argv, env = self.scan_call()
        self.assertEqual(env["ZAP_AUTH_HEADER_VALUE"], f"Bearer {TOKEN}")
        self.assertIn("ZAP_AUTH_HEADER_VALUE", argv)
        for call_argv, _ in self.docker.calls:
            self.assertFalse(any(TOKEN in a for a in call_argv))
        self.assertNotIn(TOKEN, self.out.getvalue())

    def test_reports_exported_and_token_redacted(self):
        self.docker.scan_output = f"header Bearer {TOKEN}\n"
        self.docker.report = f"<html>{TOKEN}</html>"
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-002", "--mode", "api",
                                       "--execute"), 0)
        run_dir = self.reports / "RUN-ZAP-002"
        self.assertTrue((run_dir / "report.html").exists())
        for path in run_dir.rglob("*"):
            if path.is_file():
                self.assertNotIn(TOKEN, path.read_text(encoding="utf-8"), path.name)
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["token_absent_from_outputs"])
        self.assertEqual(metadata["zap_exit_code"], 0)
        self.assertEqual(metadata["mode"], "api")

    def test_cleanup_runs_even_when_scan_fails(self):
        self.docker.scan_code = 3
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline",
                                       "--execute"), 3)
        joined = [" ".join(c[0]) for c in self.docker.calls]
        self.assertTrue(any(j.startswith("docker rm") for j in joined))
        self.assertTrue(any(j.startswith("docker volume rm") for j in joined))


class ZapHardeningTests(ZapFixture):
    def test_filter_spec_keeps_only_household_scoped_writes(self):
        filtered, dropped = ez.filter_spec(json.loads(json.dumps(SPEC)))
        paths = filtered["paths"]
        self.assertNotIn("/api/admin/users", paths)
        self.assertNotIn("/api/auth/refresh", paths)
        self.assertNotIn("/api/users/api-tokens", paths)
        self.assertNotIn("/api/recipes/create/url", paths)
        self.assertEqual(set(paths["/api/users/{item_id}"]), {"get"})
        self.assertEqual(set(paths["/api/foods"]), {"get"})
        self.assertEqual(set(paths["/api/households/webhooks"]), {"get"})
        self.assertNotIn("/api/recipes/{slug}/image", paths)
        self.assertEqual(set(paths["/api/recipes"]), {"get", "post"})
        self.assertEqual(set(paths["/api/households/mealplans/{item_id}"]),
                         {"get", "put", "delete", "parameters"})
        self.assertIn("POST /api/users/api-tokens", dropped)

    def test_api_scan_uses_filtered_spec_and_host_override(self):
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-002", "--mode", "api",
                                       "--execute"), 0)
        argv, _ = self.scan_call()
        self.assertIn(ez.ZAP_IMAGE_ID, argv)
        self.assertEqual(argv[argv.index("-t") + 1], "openapi.json")
        self.assertEqual(argv[argv.index("-O") + 1], ez.TARGET)
        written = json.loads(self.docker.inputs[0])
        self.assertNotIn("/api/users/api-tokens", written["paths"])
        run_dir = self.reports / "RUN-ZAP-002"
        self.assertTrue((run_dir / "openapi-filtrada.json").exists())
        self.assertIn("POST /api/users/api-tokens",
                      (run_dir / "operaciones-excluidas.txt").read_text(encoding="utf-8"))

    def test_jwt_shaped_strings_are_redacted(self):
        minted = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJxYSJ9.c2lnbmF0dXJl"
        self.docker.report = f"<html>{minted}</html>"
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-002", "--mode", "api",
                                       "--execute"), 0)
        html = (self.reports / "RUN-ZAP-002" / "report.html").read_text(encoding="utf-8")
        self.assertNotIn(minted, html)
        metadata = json.loads((self.reports / "RUN-ZAP-002" / "metadata.json")
                              .read_text(encoding="utf-8"))
        self.assertTrue(metadata["token_absent_from_outputs"])

    def test_fails_closed_when_volume_preparation_fails(self):
        self.docker.fail_prefix = "docker run --rm --network none --pull never -v"
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline",
                                       "--execute"), 2)
        scripts = {"zap-baseline.py", "zap-api-scan.py"}
        self.assertFalse(any(scripts & set(c[0]) for c in self.docker.calls))
        self.assertTrue(any(c[0][:3] == ["docker", "volume", "rm"] for c in self.docker.calls))

    def test_fails_closed_on_mealie_image_drift(self):
        self.docker.mealie_image = "sha256:other"
        self.assertEqual(self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline",
                                       "--execute"), 2)
        self.assertFalse(any(c[0][:2] == ["docker", "run"] for c in self.docker.calls))

    def test_cleanup_failure_is_reported(self):
        self.docker.fail_prefix = "docker rm -f"
        err = io.StringIO()
        with unittest.mock.patch("sys.stderr", err):
            self.run_main("--run-id", "RUN-ZAP-001", "--mode", "baseline", "--execute")
        self.assertIn("CLEANUP FAILED", err.getvalue())
        self.assertTrue((self.reports / "RUN-ZAP-001" / "metadata.json").exists())

    def test_verify_identity_requires_synthetic_non_admin_user_a(self):
        def fake(body):
            return lambda method, path, token=None, **kw: (200, body)

        good = {"username": "qa_usuario_a", "household": "QA-Hogar-A", "admin": False}
        ez.verify_identity(fake(good), TOKEN)
        for bad in ({**good, "admin": True}, {**good, "household": "Family"},
                    {**good, "username": "admin"}):
            with self.assertRaises(ez.PreflightError):
                ez.verify_identity(fake(bad), TOKEN)


if __name__ == "__main__":
    unittest.main()
