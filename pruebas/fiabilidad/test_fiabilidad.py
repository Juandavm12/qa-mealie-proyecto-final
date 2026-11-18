"""Pruebas del ejecutor de fiabilidad RNF-03 contra un Mealie simulado en memoria."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

import requests

import ejecutar_fiabilidad as ef

TOKEN_FALSO = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJxYSJ9.firma-falsa"


class Respuesta:
    def __init__(self, status_code: int, cuerpo=None, es_json: bool = True):
        self.status_code = status_code
        self._cuerpo = cuerpo
        self._es_json = es_json

    def json(self):
        if not self._es_json:
            raise ValueError("el cuerpo no es JSON")
        return self._cuerpo


class MealieFalso:
    """Simula las rutas de recetas y plan de comidas que usa el ejecutor."""

    def __init__(self):
        self.recetas: dict[str, dict] = {}
        self.entradas: dict[int, dict] = {}
        self.siguiente = 1
        self.fallar: dict[tuple[str, str], int] = {}
        self.excepcion_en: tuple[str, str] | None = None
        self.llamadas: list[tuple[str, str]] = []
        self.cuerpo_error: dict = {"detail": "error"}
        self.no_json_en: tuple[str, str] | None = None

    def request(self, metodo: str, ruta: str, **kw) -> Respuesta:
        self.llamadas.append((metodo, ruta))
        clave = (metodo, ruta.split("/")[2] if ruta.count("/") >= 2 else ruta)
        if self.excepcion_en == clave:
            raise requests.ConnectionError("conexión cortada")
        if clave in self.fallar:
            return Respuesta(self.fallar[clave], self.cuerpo_error)
        if self.no_json_en == (metodo, ruta.split("?")[0]):
            return Respuesta(200, None, es_json=False)
        partes = ruta.split("?")[0].strip("/").split("/")
        if partes[:2] == ["api", "recipes"]:
            return self._recetas(metodo, partes[2:], ruta, kw)
        if partes[:3] == ["api", "households", "mealplans"]:
            return self._plan(metodo, partes[3:], kw)
        return Respuesta(404)

    def _recetas(self, metodo, resto, ruta, kw):
        if metodo == "POST" and not resto:
            nombre = kw["json"]["name"]
            slug = nombre.lower()
            self.recetas[slug] = {"id": f"id-{self.siguiente}", "name": nombre, "slug": slug}
            self.siguiente += 1
            return Respuesta(201, slug)
        if metodo == "GET" and not resto:
            busqueda = ruta.split("search=")[1].split("&")[0].lower()
            items = [r for s, r in self.recetas.items() if s.startswith(busqueda)]
            return Respuesta(200, {"items": items, "total": len(items)})
        slug = resto[0]
        if slug not in self.recetas:
            return Respuesta(404)
        if metodo == "GET":
            return Respuesta(200, dict(self.recetas[slug]))
        if metodo == "PATCH":
            receta = self.recetas.pop(slug)
            receta["name"] = kw["json"]["name"]
            receta["slug"] = receta["name"].lower()
            self.recetas[receta["slug"]] = receta
            return Respuesta(200, dict(receta))
        if metodo == "DELETE":
            receta = self.recetas.pop(slug)
            self.entradas = {i: e for i, e in self.entradas.items()
                             if e["recipeId"] != receta["id"]}
            return Respuesta(200, receta)
        return Respuesta(405)

    def _plan(self, metodo, resto, kw):
        if metodo == "POST" and not resto:
            entrada = {"id": self.siguiente, **kw["json"]}
            self.entradas[self.siguiente] = entrada
            self.siguiente += 1
            return Respuesta(201, dict(entrada))
        ident = int(resto[0])
        if ident not in self.entradas:
            return Respuesta(404)
        if metodo == "GET":
            return Respuesta(200, dict(self.entradas[ident]))
        if metodo == "DELETE":
            return Respuesta(200, self.entradas.pop(ident))
        return Respuesta(405)


class Reloj:
    """Reloj falso que avanza un poco en cada lectura y rechaza esperas negativas,
    igual que ``time.monotonic`` y ``time.sleep``."""

    PASO = 0.001

    def __init__(self):
        self.t = 0.0

    def ahora(self) -> float:
        self.t += self.PASO
        return self.t

    def dormir(self, segundos: float) -> None:
        if segundos < 0:
            raise ValueError("sleep length must be non-negative")
        self.t += segundos


def ciclos_ok(n: int = ef.CICLOS) -> list[dict]:
    return [{"ciclo": i, "ok": True, "pasos": []} for i in range(1, n + 1)]


def verificacion_ok(n: int = ef.CICLOS) -> list[dict]:
    return [{"ciclo": i, "ok": True} for i in range(1, n + 1)]


class EvaluarTests(unittest.TestCase):
    def test_diez_ciclos_persistidos_y_quince_minutos_aprueban(self):
        resultado = ef.evaluar(ciclos_ok(), verificacion_ok(), ef.OBSERVACION_MIN_S)
        self.assertEqual(resultado["verdict"], "Aprobado")
        self.assertEqual(resultado["ciclos_conformes"], 10)

    def test_un_ciclo_fallido_reprueba_y_lo_nombra(self):
        ciclos = ciclos_ok()
        ciclos[3]["ok"] = False
        resultado = ef.evaluar(ciclos, verificacion_ok(), ef.OBSERVACION_MIN_S)
        self.assertEqual(resultado["verdict"], "Fallido")
        self.assertEqual(resultado["ciclos_conformes"], 9)
        self.assertIn("ciclo 4", " ".join(resultado["reasons"]))

    def test_dato_perdido_en_la_verificacion_final_reprueba(self):
        verificacion = verificacion_ok()
        verificacion[6]["ok"] = False
        resultado = ef.evaluar(ciclos_ok(), verificacion, ef.OBSERVACION_MIN_S)
        self.assertEqual(resultado["verdict"], "Fallido")
        self.assertIn("ciclo 7", " ".join(resultado["reasons"]))

    def test_menos_de_diez_ciclos_es_invalido(self):
        resultado = ef.evaluar(ciclos_ok(9), verificacion_ok(9), ef.OBSERVACION_MIN_S)
        self.assertEqual(resultado["verdict"], "Invalido")

    def test_observacion_menor_a_quince_minutos_es_invalida(self):
        resultado = ef.evaluar(ciclos_ok(), verificacion_ok(), ef.OBSERVACION_MIN_S - 1)
        self.assertEqual(resultado["verdict"], "Invalido")


class CicloTests(unittest.TestCase):
    def setUp(self):
        self.mealie = MealieFalso()

    def test_ciclo_completo_crea_edita_planifica_y_persiste(self):
        registro = ef.ejecutar_ciclo(self.mealie, "QA-RUN-REL-900", 3)
        self.assertTrue(registro["ok"], registro)
        self.assertEqual([p["paso"] for p in registro["pasos"]],
                         ["crear", "consultar", "editar", "planificar", "consultar_final"])
        self.assertEqual(registro["nombre"], "QA-RUN-REL-900-03-editada")
        entrada = self.mealie.entradas[registro["entrada_id"]]
        self.assertEqual(entrada["date"], registro["fecha"])
        self.assertEqual(entrada["recipeId"], registro["receta_id"])

    def test_codigo_inesperado_detiene_el_ciclo(self):
        self.mealie.fallar[("PATCH", "recipes")] = 500
        registro = ef.ejecutar_ciclo(self.mealie, "QA-RUN-REL-900", 1)
        self.assertFalse(registro["ok"])
        self.assertEqual(registro["pasos"][-1]["paso"], "editar")
        self.assertEqual(registro["pasos"][-1]["obtenido"], 500)
        self.assertNotIn(("POST", "/api/households/mealplans"), self.mealie.llamadas)

    def test_excepcion_de_red_se_registra_sin_propagarse(self):
        self.mealie.excepcion_en = ("POST", "households")
        registro = ef.ejecutar_ciclo(self.mealie, "QA-RUN-REL-900", 1)
        self.assertFalse(registro["ok"])
        self.assertEqual(registro["pasos"][-1]["obtenido"], "excepción ConnectionError")


class VerificarYLimpiarTests(unittest.TestCase):
    def setUp(self):
        self.mealie = MealieFalso()
        self.registros = [ef.ejecutar_ciclo(self.mealie, "QA-RUN-REL-900", n) for n in (1, 2)]

    def test_verificacion_detecta_una_entrada_perdida(self):
        del self.mealie.entradas[self.registros[1]["entrada_id"]]
        verificacion = ef.verificar(self.mealie, self.registros)
        self.assertEqual([v["ok"] for v in verificacion], [True, False])

    def test_limpieza_borra_huerfanas_del_prefijo_y_respeta_datos_ajenos(self):
        self.mealie.recetas["qa-run-rel-900-99"] = {"id": "h", "name": "QA-RUN-REL-900-99",
                                                    "slug": "qa-run-rel-900-99"}
        self.mealie.recetas["receta-ajena"] = {"id": "a", "name": "Receta ajena",
                                               "slug": "receta-ajena"}
        limpieza = ef.limpiar(self.mealie, self.registros, "QA-RUN-REL-900")
        self.assertEqual(limpieza["restantes"], 0)
        self.assertEqual(list(self.mealie.recetas), ["receta-ajena"])

    def test_limpieza_borra_todo_y_reporta_cero_restantes(self):
        limpieza = ef.limpiar(self.mealie, self.registros, "QA-RUN-REL-900")
        self.assertEqual(limpieza["restantes"], 0)
        self.assertEqual(self.mealie.recetas, {})
        self.assertEqual(self.mealie.entradas, {})


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mealie = MealieFalso()
        self.reloj = Reloj()
        self.salida = io.StringIO()
        self.deps = ef.Deps(
            run=lambda argv: (0, f"running healthy {ef.MEALIE_IMAGE_ID}".encode()),
            crear_cliente=lambda url: self.mealie,
            ahora=self.reloj.ahora, dormir=self.reloj.dormir,
            reports_root=Path(self.tmp.name), out=self.salida)

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_id_invalido_devuelve_2(self):
        self.assertEqual(ef.main(["--run-id", "RUN-X", "--execute"], self.deps), 2)

    def test_sin_execute_solo_muestra_el_plan(self):
        self.assertEqual(ef.main(["--run-id", "RUN-REL-900"], self.deps), 0)
        self.assertEqual(self.mealie.llamadas, [])
        self.assertIn("--execute", self.salida.getvalue())

    def test_preflight_fallido_devuelve_2_sin_tocar_mealie(self):
        self.deps.run = lambda argv: (0, b"exited unhealthy sha256:otra")
        self.assertEqual(ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps), 2)
        self.assertEqual(self.mealie.llamadas, [])

    def test_corrida_completa_aprueba_limpia_y_escribe_resultado(self):
        codigo = ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps)
        self.assertEqual(codigo, 0, self.salida.getvalue())
        resultado = json.loads(
            (Path(self.tmp.name) / "RUN-REL-900" / "resultado.json").read_text(encoding="utf-8"))
        self.assertEqual(resultado["verdict"], "Aprobado")
        self.assertEqual(len(resultado["ciclos"]), 10)
        self.assertGreaterEqual(resultado["duracion_s"], ef.OBSERVACION_MIN_S)
        self.assertEqual(resultado["limpieza"]["restantes"], 0)
        self.assertEqual(self.mealie.recetas, {})

    def test_ciclos_espaciados_por_el_intervalo(self):
        inicios: list[float] = []
        original = ef.ejecutar_ciclo
        ef.ejecutar_ciclo = lambda *a, **k: (inicios.append(self.reloj.t), original(*a, **k))[1]
        try:
            ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps)
        finally:
            ef.ejecutar_ciclo = original
        for i, inicio in enumerate(inicios):
            self.assertAlmostEqual(inicio - inicios[0], i * ef.INTERVALO_S, delta=0.1)

    def test_corrida_fallida_devuelve_1(self):
        self.mealie.fallar[("PATCH", "recipes")] = 500
        self.assertEqual(ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps), 1)

    def test_excepcion_a_mitad_de_ciclo_limpia_y_queda_invalida(self):
        self.mealie.no_json_en = ("GET", "/api/recipes/qa-run-rel-900-03")
        codigo = ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps)
        self.assertEqual(codigo, 2)
        self.assertEqual(self.mealie.recetas, {})
        resultado = json.loads(
            (Path(self.tmp.name) / "RUN-REL-900" / "resultado.json").read_text(encoding="utf-8"))
        self.assertEqual(resultado["verdict"], "Invalido")
        self.assertIn("ciclo 3", " ".join(resultado["reasons"]))

    def test_interrupcion_durante_la_verificacion_queda_invalida(self):
        original = ef.verificar

        def interrumpir(*_a, **_k):
            raise KeyboardInterrupt

        ef.verificar = interrumpir
        try:
            codigo = ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps)
        finally:
            ef.verificar = original
        self.assertEqual(codigo, 2)
        self.assertEqual(self.mealie.recetas, {})

    def test_login_fallido_devuelve_2_sin_crear_carpeta(self):
        def sin_login(url):
            raise RuntimeError("el login de qa_usuario_a respondió 401")

        self.deps.crear_cliente = sin_login
        self.assertEqual(ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps), 2)
        self.assertFalse((Path(self.tmp.name) / "RUN-REL-900").exists())

    def test_carpeta_existente_devuelve_2(self):
        (Path(self.tmp.name) / "RUN-REL-900").mkdir()
        self.assertEqual(ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps), 2)

    def test_ningun_token_queda_en_las_salidas(self):
        self.mealie.fallar[("PATCH", "recipes")] = 500
        self.mealie.cuerpo_error = {"detail": f"Bearer {TOKEN_FALSO}"}
        ef.main(["--run-id", "RUN-REL-900", "--execute"], self.deps)
        for archivo in (Path(self.tmp.name) / "RUN-REL-900").iterdir():
            self.assertNotIn("eyJ", archivo.read_text(encoding="utf-8"))
        self.assertNotIn("eyJ", self.salida.getvalue())


if __name__ == "__main__":
    unittest.main()
