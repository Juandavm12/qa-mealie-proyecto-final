"""Prepare synthetic QA data on the throwaway Mealie service of a CI job.

Runs only inside GitHub Actions against a local URL. It logs in with the
default administrator that a *fresh* Mealie instance creates on first start
(public documented defaults, not a secret) and then reuses
``preparar_datos.main`` unchanged, so households, users, checks and the
git-ignored ``.env.qa`` are produced exactly as in the interactive script.
Generated passwords are registered with ``::add-mask::`` so the runner
redacts them from later log output.

Refuses to run outside GitHub Actions, against a non-local URL, or when the
default administrator cannot log in (the instance is not fresh).
"""
from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Mapping, TextIO

import preparar_datos as pd

DEFAULT_ADMIN_EMAIL = "changeme@example.com"  # mealie/core/settings/settings.py:266
DEFAULT_ADMIN_PASSWORD = "MyPassword"  # mealie/core/settings/settings.py:271
LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def main(environ: Mapping[str, str] | None = None, api: Any = None,
         env_path: Path = pd.ENV_PATH, out: TextIO | None = None) -> int:
    """Run the CI bootstrap.

    Args:
        environ: Environment variables (defaults to ``os.environ``).
        api: API client; defaults to ``preparar_datos.Api`` on ``MEALIE_URL``.
        env_path: Destination of the credentials file.
        out: Stream for progress and mask commands (defaults to stdout).

    Returns:
        0 on success, 2 when a guard or a setup step fails.
    """
    environ = os.environ if environ is None else environ
    out = out or sys.stdout
    url = environ.get("MEALIE_URL", pd.DEFAULT_URL)
    if environ.get("GITHUB_ACTIONS") != "true":
        print("CI SETUP REFUSED: runs only inside GitHub Actions", file=sys.stderr)
        return 2
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS:
        print(f"CI SETUP REFUSED: {url!r} is not the local CI service", file=sys.stderr)
        return 2

    api = api or pd.Api(url)
    status, body = api.request("POST", "/api/auth/token", form={
        "username": DEFAULT_ADMIN_EMAIL, "password": DEFAULT_ADMIN_PASSWORD})
    if status != 200 or not isinstance(body, dict) or not body.get("access_token"):
        print(f"CI SETUP REFUSED: default admin login returned HTTP {status}; "
              "the instance is not fresh", file=sys.stderr)
        return 2
    token = body["access_token"]

    deps = pd.Deps(api=api, read_token=lambda _prompt: token, isatty=lambda: True,
                   env_path=env_path, out=out)
    code = pd.main(["--url", url], deps=deps)
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "_PASSWORD=" in line:
                print(f"::add-mask::{line.split('=', 1)[1]}", file=out)
    return code


if __name__ == "__main__":
    sys.exit(main())
