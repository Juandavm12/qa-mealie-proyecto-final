"""Stdlib tests for the RNF-04 performance runner and its evaluator."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

import ejecutar_rendimiento as er
import evaluar_rendimiento as ev

HEADER = ("Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,"
          "Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,"
          "50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%")


def stats_csv(requests: int, failures: int, p50: str, p95: str) -> str:
    row = f",Aggregated,{requests},{failures},{p50},40,10,900,5000,4.9,0.0,{p50},50,55,60,80,{p95},120,150,300,900,900"
    task = f"GET,GET /api/recipes,{requests},{failures},{p50},40,10,900,5000,4.9,0.0,{p50},50,55,60,80,{p95},120,150,300,900,900"
    return "\n".join([HEADER, task, row]) + "\n"


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "stats_stats.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def evaluate(self, text):
        self.path.write_text(text, encoding="utf-8")
        return ev.evaluate(self.path)

    def test_passes_when_both_thresholds_hold(self):
        result = self.evaluate(stats_csv(590, 0, "35", "1500"))
        self.assertEqual(result["verdict"], "Aprobado")
        self.assertEqual(result["p95_ms"], 1500)
        self.assertEqual(result["error_rate"], 0.0)
        self.assertEqual(result["requests"], 590)
        self.assertEqual(result["p50_ms"], 35)

    def test_fails_when_p95_exceeds_threshold(self):
        result = self.evaluate(stats_csv(590, 0, "35", "1501"))
        self.assertEqual(result["verdict"], "Fallido")
        self.assertIn("p95", " ".join(result["reasons"]))

    def test_fails_when_error_rate_exceeds_one_percent(self):
        result = self.evaluate(stats_csv(500, 6, "35", "100"))
        self.assertEqual(result["verdict"], "Fallido")
        self.assertAlmostEqual(result["error_rate"], 0.012)

    def test_error_rate_exactly_one_percent_passes(self):
        self.assertEqual(self.evaluate(stats_csv(500, 5, "35", "100"))["verdict"], "Aprobado")

    def test_invalid_without_requests_or_percentiles(self):
        self.assertEqual(self.evaluate(stats_csv(0, 0, "N/A", "N/A"))["verdict"], "Invalido")

    def test_invalid_when_aggregated_row_missing(self):
        self.assertEqual(self.evaluate(HEADER + "\n")["verdict"], "Invalido")


class FakeRun:
    def __init__(self):
        self.calls: list[tuple[list[str], dict | None]] = []
        self.mealie = f"running healthy {er.MEALIE_IMAGE_ID}"
        self.locust_code = 0

    def __call__(self, argv, env=None):
        self.calls.append((list(argv), env))
        if argv[:2] == ["docker", "inspect"]:
            return 0, self.mealie.encode()
        if "locust" in argv[0] or (len(argv) > 2 and argv[2] == "locust"):
            prefix = argv[argv.index("--csv") + 1]
            Path(prefix + "_stats.csv").write_text(stats_csv(590, 0, "35", "90"), encoding="utf-8")
            Path(argv[argv.index("--html") + 1]).write_text("<html></html>", encoding="utf-8")
            return self.locust_code, b"summary"
        return 0, b""


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run = FakeRun()
        self.out = io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, *args):
        deps = er.Deps(run=self.run, sample=lambda: "mealie,1.0%,300MiB / 1000MiB",
                       reports_root=self.root, out=self.out, sample_interval=0.01)
        return er.main(list(args), deps=deps)

    def test_inert_without_execute(self):
        self.assertEqual(self.main("--run-id", "RUN-PERF-001"), 0)
        self.assertEqual(self.run.calls, [])
        self.assertFalse((self.root / "RUN-PERF-001").exists())

    def test_rejects_invalid_run_id(self):
        self.assertEqual(self.main("--run-id", "RUN-PERF-1", "--execute"), 2)

    def test_refuses_existing_run_dir(self):
        (self.root / "RUN-PERF-001").mkdir()
        self.assertEqual(self.main("--run-id", "RUN-PERF-001", "--execute"), 2)
        self.assertFalse(any("locust" in " ".join(c[0]) for c in self.run.calls))

    def test_fails_closed_when_mealie_is_not_the_pinned_healthy_image(self):
        self.run.mealie = "running starting sha256:other"
        self.assertEqual(self.main("--run-id", "RUN-PERF-001", "--execute"), 2)
        self.assertFalse(any("locust" in " ".join(c[0]) for c in self.run.calls))

    def test_execute_runs_locust_and_writes_verdict(self):
        self.assertEqual(self.main("--run-id", "RUN-PERF-001", "--execute"), 0)
        argv, env = next(c for c in self.run.calls if "locust" in " ".join(c[0]))
        self.assertIn("--headless", argv)
        self.assertEqual(argv[argv.index("--host") + 1], er.HOST_URL)
        self.assertEqual(env["QA_PERF_PREFIX"], "QA-RUN-PERF-001")
        run_dir = self.root / "RUN-PERF-001"
        result = json.loads((run_dir / "resultado.json").read_text(encoding="utf-8"))
        self.assertEqual(result["verdict"], "Aprobado")
        self.assertEqual(result["criteria"], {"p95_ms_max": 1500, "error_rate_max": 0.01})
        self.assertTrue((run_dir / "recursos.csv").read_text(encoding="utf-8").strip())
        self.assertTrue(result["token_absent_from_outputs"])

    def test_failed_verdict_returns_one(self):
        def slow(argv, env=None):
            code, raw = FakeRun.__call__(self.run, argv, env)
            if "--csv" in argv:
                prefix = argv[argv.index("--csv") + 1]
                Path(prefix + "_stats.csv").write_text(stats_csv(590, 0, "35", "2400"),
                                                       encoding="utf-8")
            return code, raw

        deps = er.Deps(run=slow, sample=lambda: "x", reports_root=self.root, out=self.out,
                       sample_interval=0.01)
        self.assertEqual(er.main(["--run-id", "RUN-PERF-002", "--execute"], deps=deps), 1)


if __name__ == "__main__":
    unittest.main()
