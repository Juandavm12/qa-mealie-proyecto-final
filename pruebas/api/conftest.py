"""Fixtures for the Mealie API suite (CP-A01..CP-A05).

Configuration comes from environment variables or, when absent, from the
git-ignored ``.env.qa`` written by ``pruebas/preparar_datos.py``. Secret values
are never printed: fixtures expose them only to the HTTP client.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

ENV_FILE = Path(__file__).resolve().parents[2] / ".env.qa"
REQUIRED = [f"QA_USER_{k}_{f}" for k in "AB" for f in ("USERNAME", "EMAIL", "PASSWORD")]
TIMEOUT = 30
MEAL_DATE = "2026-11-18"


def _load_config() -> dict[str, str]:
    config: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    for key in ["MEALIE_URL", *REQUIRED]:
        if os.environ.get(key):
            config[key] = os.environ[key]
    config.setdefault("MEALIE_URL", "http://localhost:9925")
    return config


@pytest.fixture(scope="session")
def config() -> dict[str, str]:
    config = _load_config()
    missing = [key for key in REQUIRED if not config.get(key)]
    if missing:
        pytest.skip(f"API suite needs synthetic credentials; missing: {', '.join(missing)}")
    return config


@pytest.fixture(scope="session")
def base_url(config) -> str:
    return config["MEALIE_URL"].rstrip("/")


@pytest.fixture(scope="session")
def run_id() -> str:
    return os.environ.get("QA_RUN_ID") or datetime.now(timezone.utc).strftime("RUNA%Y%m%d%H%M%S")


class Client:
    """Thin requests wrapper bound to the base URL and an optional bearer token."""

    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", TIMEOUT)
        kwargs.setdefault("allow_redirects", False)
        return self.session.request(method, self.base_url + path, **kwargs)

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def patch(self, path, **kw):
        return self.request("PATCH", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)


def login(base_url: str, email: str, password: str) -> requests.Response:
    return requests.post(f"{base_url}/api/auth/token", data={"username": email, "password": password},
                         timeout=TIMEOUT, allow_redirects=False)


def _token(base_url: str, config: dict[str, str], key: str) -> str:
    response = login(base_url, config[f"QA_USER_{key}_EMAIL"], config[f"QA_USER_{key}_PASSWORD"])
    assert response.status_code == 200, f"login of synthetic user {key} failed: {response.status_code}"
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def anon(base_url) -> Client:
    return Client(base_url)


@pytest.fixture(scope="session")
def user_a(base_url, config) -> Client:
    return Client(base_url, _token(base_url, config, "A"))


@pytest.fixture(scope="session")
def user_b(base_url, config) -> Client:
    return Client(base_url, _token(base_url, config, "B"))


@pytest.fixture
def meal_entry(user_a, run_id):
    """A private dinner entry of user A on MEAL_DATE, removed with its recipe afterwards."""
    created = user_a.post("/api/recipes", json={"name": f"QA-{run_id}-plan"})
    assert created.status_code == 201, created.text
    slug = created.json()
    recipe = user_a.get(f"/api/recipes/{slug}").json()
    entry = user_a.post("/api/households/mealplans", json={
        "date": MEAL_DATE, "entryType": "dinner", "recipeId": recipe["id"],
        "title": f"QA-{run_id}-entrada",
    })
    assert entry.status_code == 201, entry.text
    yield entry.json()
    user_a.delete(f"/api/households/mealplans/{entry.json()['id']}")
    user_a.delete(f"/api/recipes/{slug}")
