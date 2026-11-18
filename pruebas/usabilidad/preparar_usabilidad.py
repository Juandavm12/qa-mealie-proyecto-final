"""Prepara, verifica y limpia los datos de la prueba de usabilidad RNF-02 (RUN-USA-001).

Trabaja como ``qa_usuario_a`` (credenciales de ``.env.qa``, nunca impresas) y
solo sobre datos con el prefijo ``QA-USAB``; nunca toca otros datos del hogar.

Subcomandos:

- ``preparar``: borra los datos ``QA-USAB`` que existan y crea el estado inicial
  del protocolo (tres recetas y la lista de compras vacía). Se ejecuta antes de
  cada sesión, así P1 y P2 parten del mismo estado.
- ``verificar``: comprueba, sin modificar nada, el estado final de la sección 5
  de la hoja de registro para la fecha indicada (por defecto, mañana).
- ``limpiar``: borra todos los datos ``QA-USAB`` al terminar las sesiones.

Solo acepta una instancia local. Códigos de salida: 0 correcto, 1 la
verificación encontró objetivos sin cumplir o ``preparar`` detectó entradas del
plan sin receta ``QA-USAB`` en la fecha de mañana (no las borra), 2 error.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, TextIO
from urllib.parse import quote, urlsplit

import requests

# Reutiliza el login y el saneamiento del ejecutor de fiabilidad.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fiabilidad"))
from ejecutar_fiabilidad import HOST_URL, _sanear, crear_cliente  # noqa: E402

PREFIJO = "QA-USAB"
RECETA_OBJETIVO = "QA-USAB Lentejas guisadas"
RECETAS = (RECETA_OBJETIVO, "QA-USAB Lentejas con arroz", "QA-USAB Sopa de verduras")
LISTA = "QA-USAB Compras"
ITEM = "Leche"
HOSTS_LOCALES = {"127.0.0.1", "localhost", "::1"}


class ErrorMealie(RuntimeError):
    """Respuesta inesperada de Mealie."""


def _llamar(cliente, esperado: int, metodo: str, ruta: str, **kw) -> Any:
    respuesta = cliente.request(metodo, ruta, **kw)
    if respuesta.status_code != esperado:
        raise ErrorMealie(f"{metodo} {ruta.split('?')[0]} respondió {respuesta.status_code} "
                          f"(se esperaba {esperado})")
    return respuesta.json()


def _es_qa(nombre: Any) -> bool:
    return str(nombre or "").startswith(f"{PREFIJO} ")


def recetas_qa(cliente) -> list[dict]:
    cuerpo = _llamar(cliente, 200, "GET", f"/api/recipes?search={quote(PREFIJO)}&perPage=100")
    return [r for r in cuerpo.get("items", []) if _es_qa(r.get("name"))]


def listas_qa(cliente) -> list[dict]:
    cuerpo = _llamar(cliente, 200, "GET", "/api/households/shopping/lists?perPage=100")
    return [lista for lista in cuerpo.get("items", []) if _es_qa(lista.get("name"))]


def limpiar(cliente) -> dict:
    """Borra las recetas (y con ellas sus entradas del plan) y las listas ``QA-USAB``."""
    recetas, listas = recetas_qa(cliente), listas_qa(cliente)
    for receta in recetas:
        _llamar(cliente, 200, "DELETE", f"/api/recipes/{receta['slug']}")
    for lista in listas:
        _llamar(cliente, 200, "DELETE", f"/api/households/shopping/lists/{lista['id']}")
    return {"recetas": len(recetas), "listas": len(listas)}


def _entradas(cliente, fecha: date) -> list[dict]:
    return _llamar(cliente, 200, "GET",
                   f"/api/households/mealplans?start_date={fecha.isoformat()}"
                   f"&end_date={fecha.isoformat()}&perPage=100").get("items", [])


def preparar(cliente, fecha: date) -> dict:
    """Deja el estado inicial del protocolo y comprueba que quedó exacto.

    Las entradas del plan sin receta ``QA-USAB`` no se pueden atribuir a la
    prueba, así que no se borran: se cuentan para que el facilitador las revise.
    """
    borrado = limpiar(cliente)
    for nombre in RECETAS:
        _llamar(cliente, 201, "POST", "/api/recipes", json={"name": nombre})
    _llamar(cliente, 201, "POST", "/api/households/shopping/lists", json={"name": LISTA})

    nombres = sorted(r["name"] for r in recetas_qa(cliente))
    listas = listas_qa(cliente)
    if nombres != sorted(RECETAS) or [lista["name"] for lista in listas] != [LISTA]:
        raise ErrorMealie("el estado inicial no coincide con el protocolo")
    detalle = _llamar(cliente, 200, "GET", f"/api/households/shopping/lists/{listas[0]['id']}")
    if detalle.get("listItems"):
        raise ErrorMealie("la lista de compras no quedó vacía")
    borrado["entradas_en_fecha"] = len(_entradas(cliente, fecha))
    return borrado


def _es_item(item: dict) -> bool:
    """El ítem es exactamente ``ITEM``: como nota, como alimento o en el texto mostrado.

    El texto mostrado incluye la cantidad («1 Leche»), que se descarta. Una
    coincidencia parcial («dulce de leche») no cuenta.
    """
    candidatos = [item.get("note"), (item.get("food") or {}).get("name"),
                  re.sub(r"^[\d.,/\s]+", "", item.get("display") or "")]
    return any(str(c or "").strip().casefold() == ITEM.casefold() for c in candidatos)


def verificar(cliente, fecha: date) -> list[tuple[str, bool]]:
    """Objetivos del estado final para ``fecha``; no modifica nada."""
    recetas = recetas_qa(cliente)
    ids = {r["name"]: r["id"] for r in recetas}
    entradas = _entradas(cliente, fecha)
    objetivo = ids.get(RECETA_OBJETIVO)
    listas = [lista for lista in listas_qa(cliente) if lista["name"] == LISTA]
    items = []
    if len(listas) == 1:
        items = _llamar(cliente, 200, "GET",
                        f"/api/households/shopping/lists/{listas[0]['id']}").get("listItems", [])

    return [
        (f"Las tres recetas {PREFIJO} siguen intactas", sorted(ids) == sorted(RECETAS)),
        (f"El plan del {fecha.isoformat()} contiene {RECETA_OBJETIVO}",
         objetivo is not None and any(e.get("recipeId") == objetivo for e in entradas)),
        (f"El plan del {fecha.isoformat()} no tiene otras entradas",
         objetivo is not None and all(e.get("recipeId") == objetivo for e in entradas)
         and len(entradas) == 1),
        (f"La lista {LISTA} contiene {ITEM}",
         any(_es_item(i) for i in items)),
        (f"La lista {LISTA} no tiene otros ítems y no hay listas {PREFIJO} adicionales",
         len(listas) == 1 and len(items) == 1),
    ]


def _formato(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


def main(argv: list[str] | None = None,
         crear_cliente: Callable[[str], Any] = crear_cliente,
         out: TextIO | None = None,
         hoy: Callable[[], date] = date.today) -> int:
    if out is None:
        out = sys.stdout
        if hasattr(out, "reconfigure"):  # las consolas de Windows no usan UTF-8 por defecto
            out.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=HOST_URL, help="URL de la instancia local de Mealie")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("preparar", help="crear el estado inicial (antes de cada sesión)")
    verif = sub.add_parser("verificar", help="comprobar el estado final sin modificar nada")
    verif.add_argument("--fecha", type=date.fromisoformat, default=None,
                       help="fecha del plan en formato AAAA-MM-DD (por defecto, mañana)")
    sub.add_parser("limpiar", help="borrar todos los datos QA-USAB")
    # Acepta --url antes o después del subcomando.
    for nombre in ("preparar", "verificar", "limpiar"):
        sub.choices[nombre].add_argument("--url", default=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if urlsplit(args.url).hostname not in HOSTS_LOCALES:
        print(f"Error: solo se permite una instancia local; se recibió {args.url}", file=out)
        return 2

    manana = hoy() + timedelta(days=1)
    try:
        cliente = crear_cliente(args.url.rstrip("/"))
        if args.comando == "preparar":
            borrado = preparar(cliente, manana)
            print(f"Datos anteriores borrados: {borrado['recetas']} recetas, "
                  f"{borrado['listas']} listas.", file=out)
            print(f"Estado inicial listo: {len(RECETAS)} recetas y la lista {LISTA} vacía.",
                  file=out)
            print(f"Fecha para la instrucción (mañana): {_formato(manana)}", file=out)
            if borrado["entradas_en_fecha"]:
                print(f"[ATENCIÓN] El plan del {_formato(manana)} tiene "
                      f"{borrado['entradas_en_fecha']} entradas sin receta {PREFIJO}; "
                      "bórrelas desde la interfaz antes de la sesión.", file=out)
                return 1
            return 0
        if args.comando == "limpiar":
            borrado = limpiar(cliente)
            print(f"Borrado: {borrado['recetas']} recetas y {borrado['listas']} listas {PREFIJO}.",
                  file=out)
            return 0
        fecha = args.fecha or manana
        resultados = verificar(cliente, fecha)
        for descripcion, ok in resultados:
            print(f"[{'OK' if ok else 'NO'}] {descripcion}", file=out)
        print("Solo se revisa la fecha indicada y los datos con el prefijo; los cambios en otras "
              "pantallas se anotan en la hoja.", file=out)
        return 0 if all(ok for _, ok in resultados) else 1
    except (ErrorMealie, RuntimeError, KeyError, ValueError, requests.RequestException) as error:
        print(f"Error: {_sanear(str(error))}", file=out)
        return 2


if __name__ == "__main__":
    sys.exit(main())
