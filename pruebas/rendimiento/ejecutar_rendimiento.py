"""Run the RNF-04 load test with Locust and evaluate it.

Inert by default; ``--execute`` checks that the Mealie container is the pinned
image, running and healthy, runs ``locustfile.py`` headless against
``http://127.0.0.1:9925``, samples the Mealie container's CPU and memory every
few seconds, and writes ``resultado.json`` with the verdict against the frozen
criteria. Outputs go to the git-ignored ``reports/rendimiento/<run-id>/``.

Exit codes: 0 Aprobado, 1 Fallido, 2 preflight failure or invalid run.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TextIO

import evaluar_rendimiento as ev

HERE = Path(__file__).resolve().parent
MEALIE_CONTAINER = "qa-proyecto-final-mealie-mealie-1"
MEALIE_IMAGE_ID = "sha256:6066c29eca95a6cac640ecadf734799522f3b646ee4a714e0d13ce795d989ba2"
HOST_URL = "http://127.0.0.1:9925"
RUN_ID_PATTERN = re.compile(r"RUN-PERF-[0-9]{3}")
REPORTS_ROOT = HERE.parents[1] / "reports" / "rendimiento"
JWT_PATTERN = re.compile(rb"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*")


def run_process(argv: list[str], env: dict[str, str] | None = None) -> tuple[int, bytes]:
    proc = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          check=False)
    return proc.returncode, proc.stdout


def docker_sample() -> str:
    _, raw = run_process(["docker", "stats", "--no-stream", "--format",
                          "{{.Name}},{{.CPUPerc}},{{.MemUsage}}", MEALIE_CONTAINER])
    return raw.decode("utf-8", errors="replace").strip()


@dataclass
class Deps:
    run: Callable[..., tuple[int, bytes]] = run_process
    sample: Callable[[], str] = docker_sample
    reports_root: Path = REPORTS_ROOT
    out: TextIO = field(default_factory=lambda: sys.stdout)
    sample_interval: float = 5.0


def locust_command(run_dir: Path) -> list[str]:
    return [sys.executable, "-m", "locust", "-f", str(HERE / "locustfile.py"), "--headless",
            "--host", HOST_URL, "--csv", str(run_dir / "locust"), "--csv-full-history",
            "--html", str(run_dir / "reporte.html"), "--only-summary"]


def sampler(deps: Deps, stop: threading.Event, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("utc,name,cpu,memory\n")
        while True:
            stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
            handle.write(f"{stamp},{deps.sample()}\n")
            handle.flush()
            if stop.wait(deps.sample_interval):
                break


def main(argv: list[str] | None = None, deps: Deps | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    deps = deps or Deps()
    out = deps.out
    if not RUN_ID_PATTERN.fullmatch(args.run_id):
        print("invalid --run-id, expected RUN-PERF-NNN", file=sys.stderr)
        return 2
    run_dir = deps.reports_root / args.run_id
    if not args.execute:
        print(f"plan: {' '.join(locust_command(run_dir))}", file=out)
        print("add --execute to run", file=out)
        return 0
    if run_dir.exists():
        print(f"PREFLIGHT FAILED: {run_dir} already exists", file=sys.stderr)
        return 2
    code, raw = deps.run(["docker", "inspect", MEALIE_CONTAINER, "--format",
                          "{{.State.Status}} {{.State.Health.Status}} {{.Image}}"])
    if code != 0 or raw.decode().split() != ["running", "healthy", MEALIE_IMAGE_ID]:
        print("PREFLIGHT FAILED: Mealie is not the pinned image, running and healthy",
              file=sys.stderr)
        return 2
    run_dir.mkdir(parents=True)

    env = {**os.environ, "QA_PERF_PREFIX": f"QA-{args.run_id}"}
    started = datetime.now(timezone.utc).isoformat()
    stop = threading.Event()
    thread = threading.Thread(target=sampler, args=(deps, stop, run_dir / "recursos.csv"))
    thread.start()
    try:
        locust_code, raw = deps.run(locust_command(run_dir), env=env)
    finally:
        stop.set()
        thread.join()
    log = JWT_PATTERN.sub(b"[REDACTED-TOKEN]", raw).decode("utf-8", errors="replace")
    (run_dir / "locust.log").write_text(log, encoding="utf-8")
    print(log[-1500:], file=out)

    stats = run_dir / "locust_stats.csv"
    result = (ev.evaluate(stats) if stats.exists()
              else {"verdict": "Invalido", "reasons": ["locust wrote no stats CSV"]})
    result.update({
        "run_id": args.run_id, "started": started,
        "finished": datetime.now(timezone.utc).isoformat(),
        "criteria": {"p95_ms_max": ev.P95_MS_MAX, "error_rate_max": ev.ERROR_RATE_MAX},
        "profile": "warm-up 1 user 30 s (stats reset), then 5 users 120 s, 1 s wait",
        "endpoint": "GET /api/recipes?search=<prefix>&perPage=50 (20 synthetic recipes)",
        "locust_exit_code": locust_code, "mealie_image_id": MEALIE_IMAGE_ID,
        "client": {"python": platform.python_version(), "os": platform.platform(),
                   "cpus": os.cpu_count()},
        "token_absent_from_outputs": not any(
            JWT_PATTERN.search(p.read_bytes()) for p in run_dir.rglob("*") if p.is_file()),
    })
    (run_dir / "resultado.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"verdict: {result['verdict']} {result.get('reasons', [])}", file=out)
    return {"Aprobado": 0, "Fallido": 1}.get(result["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
