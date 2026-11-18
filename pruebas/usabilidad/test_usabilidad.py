"""Pruebas del preparador de datos de usabilidad RNF-02 contra un Mealie simulado en memoria."""
from __future__ import annotations

import io
import unittest
from datetime import date
from urllib.parse import parse_qs, urlsplit

import preparar_usabilidad as pu

TOKEN_FALSO = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJxYSJ9.firma-falsa"
FECHA = date(2026, 11, 20)


class Respuesta:
    def __init__(self, status_code: int, cuerpo=None):
        self.status_code = status_code
        self._cuerpo = cuerpo

    def json(self):
        return self._cuerpo


class MealieFalso:
    """Simula las rutas de recetas, listas de compras y plan de comidas del hogar A."""

    def __init__(self):
        self.recetas: dict[str, dict] = {}
        self.listas: dict[str, dict] = {}
        self.entradas: dict[str, dict] = {}
        self.siguiente = 1
        self.fallar: dict[tuple[str, str], int] = {}

    def _id(self) -> str:
        self.siguiente += 1
        return f"id-{self.siguiente}"

    # Ayudas para simular lo que hace una persona participante en la interfaz.
    def crear_receta(self, nombre: str) -> dict:
        slug = nombre.lower().replace(" ", "-")
        while slug in self.recetas:
            slug += "-1"
        receta = {"id": self._id(), "name": nombre, "slug": slug}
        self.recetas[slug] = receta
        return receta

    def crear_lista(self, nombre: str) -> dict:
        lista = {"id": self._id(), "name": nombre, "listItems": []}
        self.listas[lista["id"]] = lista
        return lista

    def planificar(self, fecha: date, nombre_receta: str | None, titulo: str = "") -> None:
        receta = next((r for r in self.recetas.values() if r["name"] == nombre_receta), None)
        entrada = {"id": self._id(), "date": fecha.isoformat(), "entryType": "dinner",
                   "title": titulo, "recipeId": receta["id"] if receta else None}
        self.entradas[entrada["id"]] = entrada

    def agregar_item(self, nombre_lista: str, nota: str) -> None:
        lista = next(l for l in self.listas.values() if l["name"] == nombre_lista)
        lista["listItems"].append({"id": self._id(), "note": nota, "display": nota, "checked": False})

    def request(self, metodo: str, ruta: str, **kw) -> Respuesta:
        partes_url = urlsplit(ruta)
        if (metodo, partes_url.path) in self.fallar:
            return Respuesta(self.fallar[(metodo, partes_url.path)], {"detail": "error"})
        query = {k: v[0] for k, v in parse_qs(partes_url.query).items()}
        partes = partes_url.path.strip("/").split("/")
        if partes[:2] == ["api", "recipes"]:
            return self._recetas(metodo, partes[2:], query, kw)
        if partes[:4] == ["api", "households", "shopping", "lists"]:
            return self._listas(metodo, partes[4:], kw)
        if partes[:3] == ["api", "households", "mealplans"]:
            return self._plan(metodo, partes[3:], query)
        return Respuesta(404)

    def _recetas(self, metodo, resto, query, kw):
        if metodo == "POST" and not resto:
            return Respuesta(201, self.crear_receta(kw["json"]["name"])["slug"])
        if metodo == "GET" and not resto:
            buscado = query.get("search", "").lower()
            return Respuesta(200, {"items": [dict(r) for r in self.recetas.values()
                                             if buscado in r["name"].lower()]})
        if metodo == "DELETE" and len(resto) == 1 and resto[0] in self.recetas:
            receta = self.recetas.pop(resto[0])
            for clave in [k for k, e in self.entradas.items() if e["recipeId"] == receta["id"]]:
                del self.entradas[clave]
            return Respuesta(200, receta)
        return Respuesta(404)

    def _listas(self, metodo, resto, kw):
        if metodo == "POST" and not resto:
            return Respuesta(201, self.crear_lista(kw["json"]["name"]))
        if metodo == "GET" and not resto:
            return Respuesta(200, {"items": [{"id": l["id"], "name": l["name"]}
                                             for l in self.listas.values()]})
        if len(resto) == 1 and resto[0] in self.listas:
            if metodo == "GET":
                return Respuesta(200, self.listas[resto[0]])
            if metodo == "DELETE":
                return Respuesta(200, self.listas.pop(resto[0]))
        return Respuesta(404)

    def _plan(self, metodo, resto, query):
        if metodo == "GET" and not resto:
            desde, hasta = query.get("start_date", "0000"), query.get("end_date", "9999")
            return Respuesta(200, {"items": [dict(e) for e in self.entradas.values()
                                             if desde <= e["date"] <= hasta]})
        return Respuesta(404)


def ejecutar(fake: MealieFalso, *argv: str) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = pu.main(list(argv), crear_cliente=lambda url: fake, out=salida, hoy=lambda: FECHA)
    return codigo, salida.getvalue()


def preparado() -> MealieFalso:
    fake = MealieFalso()
    assert ejecutar(fake, "preparar")[0] == 0
    return fake


class TestPreparar(unittest.TestCase):
    def test_crea_las_tres_recetas_y_la_lista_vacia(self):
        fake = MealieFalso()
        codigo, salida = ejecutar(fake, "preparar")
        self.assertEqual(codigo, 0)
        self.assertEqual(sorted(r["name"] for r in fake.recetas.values()), sorted(pu.RECETAS))
        self.assertEqual([(l["name"], l["listItems"]) for l in fake.listas.values()],
                         [(pu.LISTA, [])])
        self.assertIn("Estado inicial listo", salida)

    def test_muestra_la_fecha_de_manana_para_la_instruccion(self):
        _, salida = ejecutar(MealieFalso(), "preparar")
        self.assertIn("21/11/2026", salida)

    def test_restaura_el_estado_inicial_despues_de_una_sesion(self):
        fake = preparado()
        fake.planificar(date(2026, 11, 21), pu.RECETA_OBJETIVO)
        fake.agregar_item(pu.LISTA, "Leche")
        fake.crear_receta("QA-USAB Lentejas guisadas")  # duplicado creado por error
        codigo, _ = ejecutar(fake, "preparar")
        self.assertEqual(codigo, 0)
        self.assertEqual(sorted(r["name"] for r in fake.recetas.values()), sorted(pu.RECETAS))
        self.assertEqual([l["listItems"] for l in fake.listas.values()], [[]])
        self.assertEqual(fake.entradas, {})

    def test_no_toca_datos_que_no_tienen_el_prefijo(self):
        fake = MealieFalso()
        fake.crear_receta("Lentejas de la abuela")
        fake.crear_lista("Compras del mes")
        fake.planificar(date(2026, 11, 21), "Lentejas de la abuela")
        ejecutar(fake, "preparar")
        ejecutar(fake, "limpiar")
        self.assertEqual([r["name"] for r in fake.recetas.values()], ["Lentejas de la abuela"])
        self.assertEqual([l["name"] for l in fake.listas.values()], ["Compras del mes"])
        self.assertEqual(len(fake.entradas), 1)

    def test_avisa_si_queda_una_entrada_ajena_en_la_fecha_de_manana(self):
        fake = MealieFalso()
        fake.planificar(date(2026, 11, 21), None, titulo="Cena")
        codigo, salida = ejecutar(fake, "preparar")
        self.assertEqual(codigo, 1)
        self.assertIn("ATENCIÓN", salida)
        self.assertEqual(len(fake.entradas), 1)

    def test_un_error_http_termina_con_codigo_2(self):
        fake = MealieFalso()
        fake.fallar[("POST", "/api/households/shopping/lists")] = 500
        codigo, salida = ejecutar(fake, "preparar")
        self.assertEqual(codigo, 2)
        self.assertIn("500", salida)


class TestVerificar(unittest.TestCase):
    def test_estado_final_correcto_devuelve_0(self):
        fake = preparado()
        fake.planificar(FECHA, pu.RECETA_OBJETIVO)
        fake.agregar_item(pu.LISTA, "leche")
        codigo, salida = ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())
        self.assertEqual(codigo, 0)
        self.assertNotIn("[NO]", salida)

    def test_usa_la_fecha_de_manana_por_defecto(self):
        fake = preparado()
        fake.planificar(date(2026, 11, 21), pu.RECETA_OBJETIVO)
        fake.agregar_item(pu.LISTA, "Leche")
        self.assertEqual(ejecutar(fake, "verificar")[0], 0)

    def test_receta_distractora_en_el_plan_falla(self):
        fake = preparado()
        fake.planificar(FECHA, "QA-USAB Lentejas con arroz")
        fake.agregar_item(pu.LISTA, "Leche")
        codigo, salida = ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())
        self.assertEqual(codigo, 1)
        self.assertIn("[NO]", salida)

    def test_entrada_adicional_en_la_fecha_falla(self):
        fake = preparado()
        fake.planificar(FECHA, pu.RECETA_OBJETIVO)
        fake.planificar(FECHA, None, titulo="Cena")
        fake.agregar_item(pu.LISTA, "Leche")
        self.assertEqual(ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())[0], 1)

    def test_otra_fecha_falla(self):
        fake = preparado()
        fake.planificar(date(2026, 11, 22), pu.RECETA_OBJETIVO)
        fake.agregar_item(pu.LISTA, "Leche")
        self.assertEqual(ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())[0], 1)

    def test_falta_el_item_falla(self):
        fake = preparado()
        fake.planificar(FECHA, pu.RECETA_OBJETIVO)
        self.assertEqual(ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())[0], 1)

    def test_dulce_de_leche_no_cuenta_como_leche(self):
        fake = preparado()
        fake.planificar(FECHA, pu.RECETA_OBJETIVO)
        fake.agregar_item(pu.LISTA, "dulce de leche")
        self.assertEqual(ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())[0], 1)

    def test_acepta_leche_con_cantidad_o_como_alimento(self):
        for item in ({"note": "", "display": "1 Leche", "food": {"name": "Leche"}},
                     {"note": "Leche ", "display": "2 Leche", "food": None}):
            fake = preparado()
            fake.planificar(FECHA, pu.RECETA_OBJETIVO)
            next(l for l in fake.listas.values() if l["name"] == pu.LISTA)["listItems"].append(item)
            self.assertEqual(ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())[0], 0, item)

    def test_receta_renombrada_falla(self):
        fake = preparado()
        objetivo = next(r for r in fake.recetas.values() if r["name"] == pu.RECETA_OBJETIVO)
        fake.planificar(FECHA, pu.RECETA_OBJETIVO)
        fake.agregar_item(pu.LISTA, "Leche")
        objetivo["name"] = "QA-USAB Lentejas"
        self.assertEqual(ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())[0], 1)

    def test_no_modifica_nada(self):
        fake = preparado()
        fake.planificar(FECHA, pu.RECETA_OBJETIVO)
        antes = (repr(fake.recetas), repr(fake.listas), repr(fake.entradas))
        ejecutar(fake, "verificar", "--fecha", FECHA.isoformat())
        self.assertEqual(antes, (repr(fake.recetas), repr(fake.listas), repr(fake.entradas)))


class TestLimpiar(unittest.TestCase):
    def test_borra_todos_los_datos_del_prefijo(self):
        fake = preparado()
        fake.planificar(FECHA, pu.RECETA_OBJETIVO)
        codigo, _ = ejecutar(fake, "limpiar")
        self.assertEqual(codigo, 0)
        self.assertEqual((fake.recetas, fake.listas, fake.entradas), ({}, {}, {}))


class TestSeguridad(unittest.TestCase):
    def test_rechaza_una_url_que_no_es_local(self):
        llamadas = []
        salida = io.StringIO()
        codigo = pu.main(["preparar", "--url", "https://mealie.example.com"],
                         crear_cliente=lambda url: llamadas.append(url), out=salida)
        self.assertEqual(codigo, 2)
        self.assertEqual(llamadas, [])

    def test_no_imprime_tokens_en_los_errores(self):
        def login_fallido(url):
            raise RuntimeError(f"fallo con {TOKEN_FALSO}")
        salida = io.StringIO()
        codigo = pu.main(["preparar"], crear_cliente=login_fallido, out=salida)
        self.assertEqual(codigo, 2)
        self.assertNotIn(TOKEN_FALSO, salida.getvalue())


if __name__ == "__main__":
    unittest.main()
