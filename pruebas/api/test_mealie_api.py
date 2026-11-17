"""Automated cases CP-A01..CP-A05 (documentacion/casos-de-prueba.md, section 4)."""
from __future__ import annotations

import requests

from conftest import MEAL_DATE, TIMEOUT, login

ENTRY_FIELDS = ("recipeId", "entryType", "title", "date")


def test_cp_a01_valid_login_returns_usable_token_and_identity(base_url, config):
    """RF-01.C1: valid credentials yield a bearer token bound to user A."""
    response = login(base_url, config["QA_USER_A_EMAIL"], config["QA_USER_A_PASSWORD"])
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    me = requests.get(f"{base_url}/api/users/self", timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == config["QA_USER_A_USERNAME"]
    assert me.json()["household"] == "QA-Hogar-A"
    assert me.json()["admin"] is False


def test_cp_a02_invalid_login_gives_no_usable_session(base_url, config, anon):
    """RF-01.C2: a wrong password yields 401 and no token; a forged token is rejected."""
    try:
        response = login(base_url, config["QA_USER_B_EMAIL"], "QA-incorrecta-1")
        assert response.status_code == 401
        assert "access_token" not in response.json()

        forged = anon.get("/api/users/self", headers={"Authorization": "Bearer QA-token-inventado"})
        assert forged.status_code == 401
    finally:
        # A successful login resets the failed-attempt counter (lockout threshold is 5).
        reset = login(base_url, config["QA_USER_B_EMAIL"], config["QA_USER_B_PASSWORD"])
        assert reset.status_code == 200


def test_cp_a03_recipe_crud_lifecycle(user_a, run_id):
    """RF-02.C1-C3: create, read, rename, delete; the deleted recipe is gone (404)."""
    name = f"QA-{run_id}-crud"
    created = user_a.post("/api/recipes", json={"name": name})
    assert created.status_code == 201
    slug = created.json()
    final_slug = slug
    try:
        read = user_a.get(f"/api/recipes/{slug}")
        assert read.status_code == 200
        assert read.json()["name"] == name

        renamed = user_a.patch(f"/api/recipes/{slug}", json={"name": f"{name}-editada"})
        assert renamed.status_code == 200
        final_slug = renamed.json()["slug"]
        assert final_slug != slug

        reread = user_a.get(f"/api/recipes/{final_slug}")
        assert reread.status_code == 200
        assert reread.json()["name"] == f"{name}-editada"

        deleted = user_a.delete(f"/api/recipes/{final_slug}")
        assert deleted.status_code == 200
        assert user_a.get(f"/api/recipes/{final_slug}").status_code == 404
    finally:
        user_a.delete(f"/api/recipes/{final_slug}")


def test_cp_a04_meal_plan_requires_authentication(anon, meal_entry):
    """RF-05.C1 / decision rule R1: no token -> 401 and no entry data."""
    for path in (f"/api/households/mealplans/{meal_entry['id']}", "/api/households/mealplans"):
        response = anon.get(path)
        assert response.status_code == 401, path
        assert not any(field in response.text for field in ("recipeId", meal_entry["title"])), path


def test_cp_a05_other_household_cannot_read_or_modify_entry(user_a, user_b, meal_entry):
    """RF-05.C2 / decision rule R3: user B (household B) gets 404 and A's entry is unchanged."""
    path = f"/api/households/mealplans/{meal_entry['id']}"

    read = user_b.get(path)
    assert read.status_code == 404
    assert meal_entry["title"] not in read.text

    tampered = {**meal_entry, "title": "QA-modificado-por-B"}
    assert user_b.put(path, json=tampered).status_code == 404
    assert user_b.delete(path).status_code == 404

    after = user_a.get(path)
    assert after.status_code == 200
    assert {k: after.json()[k] for k in ENTRY_FIELDS} == {k: meal_entry[k] for k in ENTRY_FIELDS}
    assert after.json()["date"] == MEAL_DATE
