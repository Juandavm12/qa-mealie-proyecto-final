"""Ejecuta el protocolo de fiabilidad RNF-03 contra Mealie y lo evalúa.

Protocolo definido por el grupo antes de la primera corrida evaluativa: diez
ciclos secuenciales crear receta → consultar → editar → planificar →
consultar, con datos nuevos por ciclo, durante al menos 15 minutos. Al final
se vuelven a leer las recetas y entradas de todos los ciclos para comprobar
que nada se perdió.

Criterio: Aprobado si los 10 ciclos son conformes, la verificación final
encuentra todos los datos y la observación dura al menos 15 minutos. Un ciclo
abortado o una observación más corta invalidan la corrida.

Por defecto no hace nada; ``--execute`` comprueba que el contenedor de Mealie
es la imagen fijada, está en ejecución y sano, ejecuta los ciclos como
``qa_usuario_a`` (credenciales de ``.env.qa``, nunca impresas) y borra al final
los datos sintéticos. Las salidas van a ``reports/fiabilidad/<run-id>/``,
carpeta ignorada por Git. Solo se registran códigos de estado y valores
propios, nunca cuerpos de respuesta.

Códigos de salida: 0 Aprobado, 1 Fallido, 2 corrida inválida o preflight fallido.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, TextIO

import requests

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE.parents[1] / ".env.qa"
REPORTS_ROOT = HERE.parents[1] / "reports" / "fiabilidad"
# Mismo contenedor e imagen fijada que el ejecutor de rendimiento.
MEALIE_CONTAINER = "qa-proyecto-final-mealie-mealie-1"
MEALIE_IMAGE_ID = "sha256:6066c29eca95a6cac640ecadf734799522f3b646ee4a714e0d13ce795d989ba2"
HOST_URL = "http://127.0.0.1:9925"
RUN_ID_PATTERN = re.compile(r"RUN-REL-[0-9]{3}")
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*")

CICLOS = 10
INTERVALO_S = 90
OBSERVACION_MIN_S = 900
FECHA_BASE = date(2026, 12, 1)
TIMEOUT = 30


class Cliente:
    """Sesión HTTP de un usuario autenticado, ligada a la URL base."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def request(self, metodo: str, ruta: str, **kw) -> requests.Response:
        kw.setdefault("timeout", TIMEOUT)
        kw.setdefault("allow_redirects", False)
        return self.session.request(metodo, self.base_url + ruta, **kw)


def crear_cliente(base_url: str) -> Cliente:
    """Inicia sesión como ``qa_usuario_a`` con las credenciales de ``.env.qa``."""
    valores = {}
    for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            valores[clave.strip()] = valor.strip()
    respuesta = requests.post(f"{base_url}/api/auth/token", timeout=TIMEOUT,
                              data={"username": valores["QA_USER_A_EMAIL"],
                                    "password": valores["QA_USER_A_PASSWORD"]})
    if respuesta.status_code != 200:
        raise RuntimeError(f"el login de qa_usuario_a respondió {respuesta.status_code}")
    return Cliente(base_url, respuesta.json()["access_token"])


def run_process(argv: list[str]) -> tuple[int, bytes]:
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return proc.returncode, proc.stdout


@dataclass
class Deps:
    run: Callable[[list[str]], tuple[int, bytes]] = run_process
    crear_cliente: Callable[[str], Any] = crear_cliente
    ahora: Callable[[], float] = time.monotonic
    dormir: Callable[[float], None] = time.sleep
    reports_root: Path = REPORTS_ROOT
    out: TextIO = field(default_factory=lambda: sys.stdout)


def _paso(cliente, registro: dict, nombre: str, esperado: int, metodo: str, ruta: str,
          **kw) -> Any:
    """Ejecuta un paso; devuelve el cuerpo JSON si el código es el esperado, o None."""
    try:
        respuesta = cliente.request(metodo, ruta, **kw)
        obtenido: int | str = respuesta.status_code
    except requests.RequestException as error:
        respuesta, obtenido = None, f"excepción {type(error).__name__}"
    ok = obtenido == esperado
    registro["pasos"].append({"paso": nombre, "esperado": esperado, "obtenido": obtenido, "ok": ok})
    return respuesta.json() if ok and respuesta is not None else None


def _fallar(registro: dict, detalle: str) -> dict:
    registro["pasos"][-1]["ok"] = False
    registro["pasos"][-1]["detalle"] = detalle
    registro["ok"] = False
    return registro


def nuevo_registro(prefijo: str, n: int) -> dict:
    """Registro vacío del ciclo ``n``, con los datos nuevos que usará."""
    return {"ciclo": n, "inicio": datetime.now(timezone.utc).isoformat(),
            "nombre": f"{prefijo}-{n:02d}",
            "fecha": (FECHA_BASE + timedelta(days=n - 1)).isoformat(),
            "pasos": [], "ok": False}


def ejecutar_ciclo(cliente, prefijo: str, n: int, registro: dict | None = None) -> dict:
    """Un ciclo crear → consultar → editar → planificar → consultar con datos nuevos.

    Si se recibe ``registro``, se completa en el lugar: así quien llama conserva
    los IDs creados aunque una excepción interrumpa el ciclo.
    """
    if registro is None:
        registro = nuevo_registro(prefijo, n)
    nombre, fecha = registro["nombre"], registro["fecha"]

    slug = _paso(cliente, registro, "crear", 201, "POST", "/api/recipes", json={"name": nombre})
    if slug is None:
        return registro
    registro["slug"] = slug
    receta = _paso(cliente, registro, "consultar", 200, "GET", f"/api/recipes/{slug}")
    if receta is None:
        return registro
    if receta.get("name") != nombre:
        return _fallar(registro, "el nombre consultado no coincide con el creado")
    registro["receta_id"] = receta["id"]

    editado = f"{nombre}-editada"
    receta = _paso(cliente, registro, "editar", 200, "PATCH", f"/api/recipes/{slug}",
                   json={"name": editado})
    if receta is None:
        return registro
    registro["slug"], registro["nombre"] = receta["slug"], editado

    entrada = _paso(cliente, registro, "planificar", 201, "POST", "/api/households/mealplans",
                    json={"date": fecha, "entryType": "dinner",
                          "recipeId": registro["receta_id"], "title": editado})
    if entrada is None:
        return registro
    registro["entrada_id"] = entrada["id"]

    receta = _paso(cliente, registro, "consultar_final", 200, "GET",
                   f"/api/recipes/{registro['slug']}")
    if receta is None:
        return registro
    if receta.get("name") != editado:
        return _fallar(registro, "la edición del nombre no persistió")
    registro["ok"] = True
    return registro


def verificar(cliente, registros: list[dict]) -> list[dict]:
    """Vuelve a leer la receta y la entrada de cada ciclo completo."""
    resultados = []
    for registro in registros:
        if not registro["ok"]:
            continue
        fila: dict = {"ciclo": registro["ciclo"], "pasos": []}
        receta = _paso(cliente, fila, "receta", 200, "GET", f"/api/recipes/{registro['slug']}")
        entrada = _paso(cliente, fila, "entrada", 200, "GET",
                        f"/api/households/mealplans/{registro['entrada_id']}")
        fila["ok"] = bool(
            receta and entrada and receta.get("name") == registro["nombre"]
            and entrada.get("date") == registro["fecha"]
            and entrada.get("recipeId") == registro["receta_id"])
        resultados.append(fila)
    return resultados


def _recetas_del_prefijo(cliente, prefijo: str) -> list[dict]:
    """Recetas cuyo nombre empieza con el prefijo de esta corrida (nunca otras)."""
    respuesta = cliente.request("GET", f"/api/recipes?search={prefijo}&perPage=50")
    return [r for r in respuesta.json().get("items", [])
            if str(r.get("name", "")).startswith(f"{prefijo}-")]


def _borrar(cliente, ruta: str) -> bool:
    try:
        return cliente.request("DELETE", ruta).status_code == 200
    except Exception:  # la limpieza nunca debe ocultar el error original de la corrida
        return False


def limpiar(cliente, registros: list[dict], prefijo: str) -> dict:
    """Borra lo creado por la corrida, incluidas recetas huérfanas de su prefijo.

    Primero borra las entradas y recetas registradas; después busca recetas del
    prefijo que hayan quedado sin registrar (por ejemplo, creadas por una petición
    que expiró) y las borra. Borrar una receta borra también sus entradas del plan.
    """
    borrados = 0
    for registro in registros:
        if registro.get("entrada_id") is not None:
            borrados += _borrar(cliente, f"/api/households/mealplans/{registro['entrada_id']}")
        if registro.get("slug") is not None:
            borrados += _borrar(cliente, f"/api/recipes/{registro['slug']}")
    try:
        for receta in _recetas_del_prefijo(cliente, prefijo):
            borrados += _borrar(cliente, f"/api/recipes/{receta.get('slug')}")
        restantes: int | str = len(_recetas_del_prefijo(cliente, prefijo))
    except Exception:
        restantes = "no verificado"
    return {"borrados": borrados, "restantes": restantes}


def evaluar(ciclos: list[dict], verificacion: list[dict], duracion_s: float,
            aborto: str | None = None) -> dict:
    conformes = sum(1 for c in ciclos if c["ok"])
    if aborto:
        return {"verdict": "Invalido", "ciclos_conformes": conformes, "reasons": [aborto]}
    if len(ciclos) < CICLOS:
        return {"verdict": "Invalido", "ciclos_conformes": conformes,
                "reasons": [f"solo se ejecutaron {len(ciclos)} de {CICLOS} ciclos"]}
    if duracion_s < OBSERVACION_MIN_S:
        return {"verdict": "Invalido", "ciclos_conformes": conformes,
                "reasons": [f"observación de {duracion_s:.0f} s, menor a {OBSERVACION_MIN_S} s"]}
    razones = [f"ciclo {c['ciclo']} no conforme" for c in ciclos if not c["ok"]]
    razones += [f"ciclo {v['ciclo']}: datos no encontrados en la verificación final"
                for v in verificacion if not v["ok"]]
    return {"verdict": "Fallido" if razones else "Aprobado", "ciclos_conformes": conformes,
            "reasons": razones}


def _esperar_hasta(deps: Deps, objetivo: float) -> None:
    """Espera hasta el instante ``objetivo``; si ya pasó, no espera (``sleep`` no acepta negativos)."""
    restante = objetivo - deps.ahora()
    if restante > 0:
        deps.dormir(restante)


def _sanear(texto: str) -> str:
    return JWT_PATTERN.sub("[TOKEN-REDACTADO]", texto)


def main(argv: list[str] | None = None, deps: Deps | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    deps = deps or Deps()
    out = deps.out
    if not RUN_ID_PATTERN.fullmatch(args.run_id):
        print("--run-id inválido; se espera RUN-REL-NNN", file=sys.stderr)
        return 2
    run_dir = deps.reports_root / args.run_id
    if not args.execute:
        print(f"plan: {CICLOS} ciclos cada {INTERVALO_S} s contra {HOST_URL}, verificación "
              f"final a los {OBSERVACION_MIN_S} s; salidas en {run_dir}", file=out)
        print("agregar --execute para ejecutar", file=out)
        return 0
    if run_dir.exists():
        print(f"PREFLIGHT FALLIDO: {run_dir} ya existe", file=sys.stderr)
        return 2
    codigo, raw = deps.run(["docker", "inspect", MEALIE_CONTAINER, "--format",
                            "{{.State.Status}} {{.State.Health.Status}} {{.Image}}"])
    if codigo != 0 or raw.decode().split() != ["running", "healthy", MEALIE_IMAGE_ID]:
        print("PREFLIGHT FALLIDO: Mealie no es la imagen fijada, en ejecución y sana",
              file=sys.stderr)
        return 2
    try:
        cliente = deps.crear_cliente(HOST_URL)
    except Exception as error:
        print(f"PREFLIGHT FALLIDO: no se pudo iniciar sesión ({error})", file=sys.stderr)
        return 2
    run_dir.mkdir(parents=True)

    prefijo = f"QA-{args.run_id}"
    inicio_utc = datetime.now(timezone.utc).isoformat()
    t0 = deps.ahora()
    ciclos: list[dict] = []
    verificacion: list[dict] = []
    aborto: str | None = None
    etapa = "antes del primer ciclo"
    log = run_dir / "registro.log"
    try:
        with log.open("w", encoding="utf-8", newline="\n") as handle:
            try:
                for n in range(1, CICLOS + 1):
                    _esperar_hasta(deps, t0 + (n - 1) * INTERVALO_S)
                    etapa = f"en el ciclo {n}"
                    registro = nuevo_registro(prefijo, n)
                    ciclos.append(registro)  # antes de ejecutar: la limpieza ve sus IDs
                    ejecutar_ciclo(cliente, prefijo, n, registro)
                    registro["t_s"] = round(deps.ahora() - t0, 1)
                    pasos = " ".join(f"{p['paso']}={p['obtenido']}" for p in registro["pasos"])
                    linea = _sanear(f"ciclo {n:02d} t={registro['t_s']}s "
                                    f"{'conforme' if registro['ok'] else 'NO CONFORME'} {pasos}")
                    handle.write(linea + "\n")
                    handle.flush()
                    print(linea, file=out)
                etapa = "durante la espera de la verificación final"
                _esperar_hasta(deps, t0 + OBSERVACION_MIN_S)
                etapa = "durante la verificación final"
                verificacion = verificar(cliente, ciclos)
                handle.write(_sanear(f"verificación final t={deps.ahora() - t0:.1f}s: "
                                     f"{sum(v['ok'] for v in verificacion)}/{len(verificacion)} "
                                     "ciclos con sus datos intactos") + "\n")
            except (Exception, KeyboardInterrupt) as error:
                # Solo el tipo de excepción: su mensaje podría incluir un cuerpo de respuesta.
                aborto = f"corrida abortada {etapa} (excepción {type(error).__name__})"
                handle.write(aborto + "\n")
                print(aborto, file=out)
    finally:
        limpieza = limpiar(cliente, ciclos, prefijo)
    duracion = deps.ahora() - t0
    resultado = evaluar(ciclos, verificacion, duracion, aborto)
    resultado.update({
        "run_id": args.run_id, "inicio": inicio_utc,
        "fin": datetime.now(timezone.utc).isoformat(), "duracion_s": round(duracion, 1),
        "criterio": {"ciclos": CICLOS, "intervalo_s": INTERVALO_S,
                     "observacion_min_s": OBSERVACION_MIN_S},
        "mealie_image_id": MEALIE_IMAGE_ID, "ciclos": ciclos, "verificacion": verificacion,
        "limpieza": limpieza,
    })
    (run_dir / "resultado.json").write_text(
        _sanear(json.dumps(resultado, indent=2, ensure_ascii=False)), encoding="utf-8")
    print(f"veredicto: {resultado['verdict']} {resultado['reasons']} "
          f"limpieza: {limpieza}", file=out)
    return {"Aprobado": 0, "Fallido": 1}.get(resultado["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
