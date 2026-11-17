"""Run an OWASP ZAP scan against the local Mealie container.

Modes:
- ``baseline``: unauthenticated spider plus passive scan of the web UI.
- ``api``: OpenAPI import plus active scan, authenticated as synthetic user A,
  restricted to a filtered spec (see ``filter_spec``).

Safety contract:
- inert by default; ``--execute`` is required to start any container;
- ZAP, helper and Mealie images are pinned by ID; ZAP runs by image ID;
- ZAP shares the network namespace of the Mealie container, so it reaches
  only ``http://localhost:9000`` and publishes no port;
- no host directory is bind-mounted: the filtered spec enters the work volume
  through stdin and reports leave it with ``tar`` over stdout;
- the token is checked to belong to non-admin ``qa_usuario_a`` in
  ``QA-Hogar-A`` before use, and is passed only through the ``docker`` process
  environment (``-e NAME`` without value), never in argv;
- the session token and every JWT-shaped string are redacted from the log and
  exported reports; ``metadata.json`` records ``token_absent_from_outputs``;
- the scan container and the work volume are always removed, and a failed
  removal is reported loudly.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TextIO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import preparar_datos as pd  # noqa: E402

ZAP_IMAGE = "ghcr.io/zaproxy/zaproxy:stable"
ZAP_IMAGE_ID = "sha256:9624669db72f54d86c4b46a7064518bd9bf79d8c61a4c31befa9923489f328af"
HELPER_IMAGE = "traslado-qa-mealie/python:3.12-slim-bookworm"
HELPER_IMAGE_ID = "sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df"
MEALIE_CONTAINER = "qa-proyecto-final-mealie-mealie-1"
MEALIE_IMAGE_ID = "sha256:6066c29eca95a6cac640ecadf734799522f3b646ee4a714e0d13ce795d989ba2"
TARGET = "http://localhost:9000"
HOST_URL = "http://127.0.0.1:9925"
RUN_ID_PATTERN = re.compile(r"RUN-ZAP-[0-9]{3}")
JWT_PATTERN = re.compile(rb"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*")
REPORTS_ROOT = Path(__file__).resolve().parents[2] / "reports" / "zap"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env.qa"
SCAN_LIMITS = ("-config scanner.maxScanDurationInMins=45 "
               "-config scanner.maxRuleDurationInMins=4 -config scanner.threadPerHost=2")
REPORT_ARGS = ["-I", "-r", "report.html", "-J", "report.json", "-w", "report.md"]
MODES = {
    "baseline": ["zap-baseline.py", "-t", TARGET, "-m", "3", *REPORT_ARGS],
    "api": ["zap-api-scan.py", "-t", "openapi.json", "-f", "openapi", "-O", TARGET,
            *REPORT_ARGS, "-z", SCAN_LIMITS],
}
REDACTED = b"[REDACTED-TOKEN]"
WRITE_METHODS = {"post", "put", "patch", "delete"}
# Excluded entirely: credentials, sessions, admin, and server-side URL fetching.
DROP_ALL_PREFIXES = (
    "/api/admin/", "/api/auth/", "/api/users/api-tokens", "/api/users/password",
    "/api/users/forgot-password", "/api/users/reset-password", "/api/users/register",
    "/api/recipes/create", "/api/recipes/test-scrape-url",
)
# Read-only: group-wide data, user/household settings, outbound callbacks, public links.
DROP_WRITE_PREFIXES = (
    "/api/users", "/api/groups", "/api/organizers", "/api/foods", "/api/units",
    "/api/households/webhooks", "/api/households/events", "/api/households/recipe-actions",
    "/api/households/invitations", "/api/households/permissions",
    "/api/households/preferences", "/api/shared", "/api/recipes/bulk-actions/export",
)
DROP_ALL_EXACT = {"/api/recipes/{slug}/image"}  # POST downloads an image from a URL


class PreflightError(RuntimeError):
    """A safety check failed before the scan."""


def run_process(argv: list[str], env: dict[str, str] | None = None,
                input: bytes | None = None) -> tuple[int, bytes]:
    """Run a command and return (exit code, combined stdout/stderr bytes)."""
    proc = subprocess.run(argv, env=env, input=input, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False)
    return proc.returncode, proc.stdout


def verify_identity(request: Callable[..., tuple[int, Any]], token: str) -> None:
    """Refuse any token that is not the synthetic non-admin user A."""
    status, me = request("GET", "/api/users/self", token=token)
    if (status != 200 or not isinstance(me, dict) or me.get("admin") is not False
            or me.get("username") != "qa_usuario_a" or me.get("household") != "QA-Hogar-A"):
        raise PreflightError("token is not the synthetic non-admin user A in QA-Hogar-A")


def token_from_env_file() -> str:
    """Log in as synthetic user A with the git-ignored credentials file."""
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    api = pd.Api(HOST_URL)
    status, body = api.request("POST", "/api/auth/token", form={
        "username": values["QA_USER_A_EMAIL"], "password": values["QA_USER_A_PASSWORD"]})
    if status != 200 or not isinstance(body, dict) or not body.get("access_token"):
        raise PreflightError(f"login of synthetic user A failed: HTTP {status}")
    verify_identity(api.request, body["access_token"])
    return body["access_token"]


def fetch_live_spec() -> dict:
    status, spec = pd.Api(HOST_URL).request("GET", "/openapi.json")
    if status != 200 or not isinstance(spec, dict) or "paths" not in spec:
        raise PreflightError(f"could not read Mealie OpenAPI: HTTP {status}")
    return spec


def filter_spec(spec: dict) -> tuple[dict, list[str]]:
    """Keep only operations whose writes stay inside the scanning household.

    Returns:
        The filtered spec and the sorted list of excluded ``METHOD /path``.
    """
    dropped: list[str] = []
    paths: dict[str, dict] = {}
    for path, item in spec["paths"].items():
        methods = [m for m in item if m in WRITE_METHODS | {"get", "head", "options"}]
        if path in DROP_ALL_EXACT or path.startswith(DROP_ALL_PREFIXES):
            dropped += [f"{m.upper()} {path}" for m in methods]
            continue
        kept = dict(item)
        if path.startswith(DROP_WRITE_PREFIXES):
            for method in [m for m in item if m in WRITE_METHODS]:
                dropped.append(f"{method.upper()} {path}")
                kept.pop(method)
        if any(m in kept for m in methods):
            paths[path] = kept
    return {**spec, "paths": paths}, sorted(dropped)


@dataclass
class Deps:
    run: Callable[..., tuple[int, bytes]] = run_process
    get_token: Callable[[], str] = token_from_env_file
    fetch_spec: Callable[[], dict] = fetch_live_spec
    reports_root: Path = REPORTS_ROOT
    out: TextIO = field(default_factory=lambda: sys.stdout)


def preflight(run) -> None:
    for image, expected in ((ZAP_IMAGE, ZAP_IMAGE_ID), (HELPER_IMAGE, HELPER_IMAGE_ID)):
        code, raw = run(["docker", "image", "inspect", image, "--format",
                         "{{.Id}} {{.Os}}/{{.Architecture}}"])
        if code != 0 or raw.decode().split() != [expected, "linux/amd64"]:
            raise PreflightError(f"{image} missing or not the pinned linux/amd64 ID")
    code, raw = run(["docker", "inspect", MEALIE_CONTAINER, "--format",
                     "{{.State.Status}} {{.State.Health.Status}} {{.Image}}"])
    if code != 0 or raw.decode().split() != ["running", "healthy", MEALIE_IMAGE_ID]:
        raise PreflightError("Mealie container is not the pinned image, running and healthy")


def scan_command(mode: str, name: str, volume: str) -> list[str]:
    argv = ["docker", "run", "--name", name, "--network", f"container:{MEALIE_CONTAINER}",
            "--pull", "never", "--memory", "3g", "-v", f"{volume}:/zap/wrk"]
    if mode == "api":
        argv += ["-e", "ZAP_AUTH_HEADER", "-e", "ZAP_AUTH_HEADER_VALUE",
                 "-e", "ZAP_AUTH_HEADER_SITE"]
    return argv + [ZAP_IMAGE_ID] + MODES[mode]


def helper(volume: str, *command: str, mode: str = "rw", stdin: bool = False) -> list[str]:
    return (["docker", "run", "--rm"] + (["-i"] if stdin else [])
            + ["--network", "none", "--pull", "never", "-v", f"{volume}:/w:{mode}",
               HELPER_IMAGE_ID, *command])


def redact(data: bytes, token: str | None) -> bytes:
    if token:
        data = data.replace(token.encode(), REDACTED)
    return JWT_PATTERN.sub(REDACTED, data)


def checked(run, argv: list[str], what: str, **kwargs) -> bytes:
    code, raw = run(argv, **kwargs)
    if code != 0:
        raise OSError(f"{what} failed with exit code {code}")
    return raw


def export_reports(run, volume: str, run_dir: Path, token: str | None) -> None:
    raw = checked(run, helper(volume, "tar", "cf", "-", "-C", "/w", ".", mode="ro"),
                  "report export")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r") as archive:
        archive.extractall(run_dir, filter="data")
    for path in run_dir.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            clean = redact(data, token)
            if clean != data:
                path.write_bytes(clean)


def token_absent(token: str | None, root: Path) -> bool:
    for path in root.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            if (token and token.encode() in data) or JWT_PATTERN.search(data):
                return False
    return True


def cleanup(run, name: str, volume: str) -> None:
    for argv in (["docker", "rm", "-f", name], ["docker", "volume", "rm", volume]):
        try:
            code, _ = run(argv)
        except OSError as error:
            code = f"{type(error).__name__}"
        if code != 0:
            print(f"CLEANUP FAILED ({code}): {' '.join(argv)} - remove it manually",
                  file=sys.stderr)


def main(argv: list[str] | None = None, deps: Deps | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    deps = deps or Deps()
    out = deps.out
    if not RUN_ID_PATTERN.fullmatch(args.run_id):
        print("invalid --run-id, expected RUN-ZAP-NNN", file=sys.stderr)
        return 2
    run_dir = deps.reports_root / args.run_id
    name = f"qa-zap-{args.run_id.lower()}"
    volume = f"{name}-wrk"
    if not args.execute:
        print(f"plan: {' '.join(scan_command(args.mode, name, volume))}", file=out)
        print(f"reports -> {run_dir}; add --execute to run", file=out)
        return 0

    token, env, spec_bytes = None, None, None
    started = datetime.now(timezone.utc).isoformat()
    try:
        if run_dir.exists():
            raise PreflightError(f"{run_dir} already exists")
        preflight(deps.run)
        if args.mode == "api":
            filtered, dropped = filter_spec(deps.fetch_spec())
            spec_bytes = json.dumps(filtered).encode("utf-8")
            token = deps.get_token()
            env = {**os.environ, "ZAP_AUTH_HEADER": "Authorization",
                   "ZAP_AUTH_HEADER_VALUE": f"Bearer {token}", "ZAP_AUTH_HEADER_SITE": "localhost"}
        run_dir.mkdir(parents=True)
        if spec_bytes is not None:
            (run_dir / "openapi-filtrada.json").write_bytes(spec_bytes)
            (run_dir / "operaciones-excluidas.txt").write_text("\n".join(dropped) + "\n",
                                                               encoding="utf-8")
    except (PreflightError, OSError, KeyError, TypeError, ValueError) as error:
        print(f"PREFLIGHT FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2

    zap_code, result = None, 2
    try:
        checked(deps.run, ["docker", "volume", "create", volume], "volume create")
        checked(deps.run, helper(volume, "chown", "1000:1000", "/w"), "volume chown")
        if spec_bytes is not None:
            checked(deps.run, helper(volume, "sh", "-c", "cat > /w/openapi.json", stdin=True),
                    "spec copy", input=spec_bytes)
        print(f"scan {args.mode} started {started}", file=out)
        zap_code, raw = deps.run(scan_command(args.mode, name, volume), env=env)
        result = zap_code
        log = redact(raw, token).decode("utf-8", errors="replace")
        (run_dir / "zap.log").write_text(log, encoding="utf-8")
        print(log[-2000:], file=out)
        export_reports(deps.run, volume, run_dir, token)
    except OSError as error:
        print(f"RUN ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        result = zap_code if zap_code not in (None, 0) else 2
    finally:
        cleanup(deps.run, name, volume)
        metadata = {
            "run_id": args.run_id, "mode": args.mode, "started": started,
            "finished": datetime.now(timezone.utc).isoformat(), "zap_image": ZAP_IMAGE,
            "zap_image_id": ZAP_IMAGE_ID, "mealie_image_id": MEALIE_IMAGE_ID,
            "target": TARGET, "scan_limits": SCAN_LIMITS,
            "command": scan_command(args.mode, name, volume), "zap_exit_code": zap_code,
            "authenticated_as": "qa_usuario_a" if args.mode == "api" else None,
            "token_absent_from_outputs": token_absent(token, run_dir),
        }
        (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(f"zap exit code {zap_code}; reports in {run_dir}", file=out)
    return result


if __name__ == "__main__":
    sys.exit(main())
