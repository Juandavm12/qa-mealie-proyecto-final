"""RNF-04 load profile: authenticated read of the synthetic recipe list.

On test start, synthetic user A logs in (credentials from the git-ignored
``.env.qa``) and 20 recipes ``<prefix>-01..20`` are created; the run aborts if
the search does not return exactly 20. Profile: 1 user for 30 s of warm-up,
statistics reset, then 5 users for 120 s, each waiting 1 s between requests.
Only ``GET /api/recipes`` is measured; setup and teardown use ``requests``
outside Locust's statistics. The recipes are deleted on test stop.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests
from locust import HttpUser, LoadTestShape, constant, events, task

ENV_FILE = Path(__file__).resolve().parents[2] / ".env.qa"
PREFIX = os.environ.get("QA_PERF_PREFIX", "QA-PERF-LOCAL")
RECIPES = 20
WARM_UP_S, MEASURE_S = 30, 120
STATE: dict = {"token": None, "slugs": []}
TIMEOUT = 30


def _credentials() -> tuple[str, str]:
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values["QA_USER_A_EMAIL"], values["QA_USER_A_PASSWORD"]


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {STATE['token']}"}


@events.test_start.add_listener
def create_dataset(environment, **_kwargs):
    host = environment.host.rstrip("/")
    email, password = _credentials()
    login = requests.post(f"{host}/api/auth/token", data={"username": email, "password": password},
                          timeout=TIMEOUT)
    login.raise_for_status()
    STATE["token"] = login.json()["access_token"]
    for i in range(1, RECIPES + 1):
        created = requests.post(f"{host}/api/recipes", json={"name": f"{PREFIX}-{i:02d}"},
                                headers=_headers(), timeout=TIMEOUT)
        created.raise_for_status()
        STATE["slugs"].append(created.json())
    found = requests.get(f"{host}/api/recipes", params={"search": PREFIX, "perPage": 50},
                         headers=_headers(), timeout=TIMEOUT).json()["total"]
    if found != RECIPES:
        environment.runner.quit()
        raise RuntimeError(f"dataset check failed: search returned {found}, expected {RECIPES}")


@events.test_stop.add_listener
def delete_dataset(environment, **_kwargs):
    host = environment.host.rstrip("/")
    for slug in STATE["slugs"]:
        requests.delete(f"{host}/api/recipes/{slug}", headers=_headers(), timeout=TIMEOUT)
    STATE["slugs"].clear()


class RecipeReader(HttpUser):
    wait_time = constant(1)

    @task
    def list_synthetic_recipes(self):
        with self.client.get("/api/recipes", params={"search": PREFIX, "perPage": 50},
                             headers=_headers(), name="GET /api/recipes (20 sinteticas)",
                             catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
            elif response.json().get("total") != RECIPES:
                response.failure(f"unexpected total {response.json().get('total')}")
            else:
                response.success()


class WarmUpThenMeasure(LoadTestShape):
    """1 user for the warm-up, reset statistics, then 5 users for the measurement."""

    reset_done = False

    def tick(self):
        elapsed = self.get_run_time()
        if elapsed < WARM_UP_S:
            return 1, 1
        if not self.reset_done:
            self.runner.stats.reset_all()
            self.reset_done = True
        if elapsed < WARM_UP_S + MEASURE_S:
            return 5, 5
        return None
