# Evaluación de mantenibilidad RNF-06 — Mealie v3.25.1

**Fecha:** 2026-11-18. **Código analizado:** backend Python de Mealie v3.25.1 (tag `v3.25.1`, commit `cce7601e`). **Fuentes:** lectura del código (todas las rutas `archivo:línea` son relativas a la raíz del código de Mealie) y SonarQube RUN-SONAR-SCAN-W002.

## 1. Criterio

Tomado de RNF-06 en el documento de alcance del grupo:

- evaluar la capacidad de **comprender y localizar** cambios de validación y autorización, trazando dos rutas del alcance hasta el esquema y la persistencia, con los módulos, las responsabilidades y los acoplamientos observados;
- interpretar code smells, duplicación, deuda y Maintainability Rating, con **dos ejemplos concretos**.

No se fijó un rating exigido, porque no había línea base. Como no se implementaron cambios, no se mide el esfuerzo real de modificación.

## 2. Ruta A — validación: `POST /api/recipes`

| Capa | Ubicación | Responsabilidad |
| --- | --- | --- |
| Router | `mealie/routes/recipe/recipe_crud_routes.py:89` | `UserAPIRouter(prefix="/recipes")`; exige sesión a nivel de router (`mealie/routes/_base/routers.py:20-24`) |
| Handler | `recipe_crud_routes.py:570-575` | `create_one(data: CreateRecipe)` delega en el servicio y publica un evento |
| Mapeo de errores | `recipe_crud_routes.py:94-129` | `IntegrityError` → 400 «Recipe already exists»; `SlugError` → 400; resto → 500 |
| Esquema de entrada | `mealie/schema/recipe/recipe.py:113-114` | `CreateRecipe.name: str`, obligatorio |
| Servicio | `mealie/services/recipe/recipe_service.py:198-242` | Arma la receta con usuario, hogar y grupo, aplica preferencias del hogar y llama al repositorio |
| Slug | `recipe.py:40-57`, `recipe.py:242-247` | Genera el slug desde el nombre dentro de un validador Pydantic |
| Repositorio | `mealie/repos/repository_recipes.py:95-108` | Reintenta hasta 10 veces ante `IntegrityError`, renombrando a «nombre (i)» |
| Modelo | `mealie/db/models/recipe/recipe.py:45, 81` | Restricción única `(slug, group_id)` y `name` no nulo |

**Dónde vive la validación:** en **cinco lugares**. El `name` ausente lo rechaza Pydantic con un 422 antes de llegar al handler (lo confirmó CP-M08). Las reglas del slug están en validadores del esquema, la unicidad en la base de datos, la deduplicación en el repositorio y la traducción a códigos HTTP en el controlador. No hay un módulo único de validación.

**Archivos a abrir para cambiar la regla:** 1 para endurecer solo `name` (`recipe.py`); unos 5 para cambiarla de forma coherente, incluidos el slug, la unicidad y el mapeo de errores.

## 3. Ruta B — autorización: `GET /api/households/mealplans/{id}`

| Capa | Ubicación | Responsabilidad |
| --- | --- | --- |
| Router | `mealie/routes/households/controller_mealplan.py:26` | `APIRouter` simple: el router **no** exige sesión |
| Handler | `controller_mealplan.py:173-175` | `get_one` delega en `self.mixins.get_one(item_id)` |
| Autenticación | `mealie/routes/_base/base_controllers.py:139` → `mealie/core/dependencies/dependencies.py:103-139` | `Depends(get_current_user)` como atributo de la clase base; sin token válido, 401 |
| Inyección del hogar | `base_controllers.py:152-158` | Crea los repositorios con el `group_id` y el `household_id` del usuario autenticado |
| Mixin | `mealie/routes/_base/mixins.py:106-115` | Si el repositorio devuelve `None`, responde 404 «Not found.» |
| Filtro | `mealie/repos/repository_generic.py:94-102` | `_filter_builder` agrega `group_id` y `household_id` a toda consulta |
| Modelo | `mealie/db/models/household/mealplan.py:55-76` | `household_id` es un proxy de asociación a través del usuario dueño |

**Dónde vive la autorización:** la autenticación, en una dependencia inyectada por la clase base del controlador; la autorización por hogar, en un **único filtro** del repositorio genérico. Por eso un plan de otro hogar responde 404 y no 403 (lo confirmó CP-A05). El controlador no contiene ningún control de permisos explícito.

**Archivos a abrir para cambiar la regla:** unos 6 (controlador, controlador base, mixin, fábrica de repositorios, repositorio genérico y modelo), o 7 si también cambia la autenticación. La regla está centralizada, pero para encontrarla hay que conocer la capa genérica.

## 4. Acoplamientos y rasgos observados

| # | Observación | Evidencia | Efecto en la mantenibilidad |
| --- | --- | --- | --- |
| 1 | Repositorio genérico con fábrica: el aislamiento por hogar se cambia en un solo lugar, pero es invisible desde el controlador. Que un controlador quede filtrado depende de su clase base: `BaseAdminController` quita ambos filtros | `repository_generic.py:94-102`; `base_controllers.py:184-189` | Positivo para la reutilización; negativo para la legibilidad de la seguridad |
| 2 | Manejo de «no encontrado» inconsistente: unos controladores usan `self.mixins.get_one`, que lanza 404, y otros `self.repo.get_one`, que devuelve `None` | `mealie/routes/organizers/controller_categories.py:144` frente a `controller_tags.py:135` | Es la causa raíz de **DEF-001**: un tag inexistente responde 500 |
| 3 | El mismo error de base de datos produce códigos distintos: `IntegrityError` → 400 en recetas y → 409 en los controladores que usan el mixin | `recipe_crud_routes.py:107-111` frente a `mixins.py:84-90` | Un cliente no puede tratar el conflicto de forma uniforme |
| 4 | Línea sin efecto: `q.filter(...)` descarta su resultado, así que el filtro `household_id IS NOT NULL` que pretende aplicar nunca se aplica | `repository_generic.py:82-83` | Código que aparenta una protección que no existe. No se observó impacto funcional, porque el filtro principal de §3 sí se aplica |

Una inferencia del análisis sostenía que la observación 2 producía un 200 con cuerpo nulo. La reproducción de DEF-001 mostró que la respuesta real es **500**: FastAPI no puede validar `None` contra el modelo de respuesta. Prevalece el dato medido.

## 5. Métricas de SonarQube

| Métrica | Valor |
| --- | --- |
| Maintainability Rating | **A** |
| Code Smells | 10 (4 Blocker, 1 Critical, 5 Major) |
| Deuda técnica | 1 h 49 min (109 min) |
| Duplicación | 0,6 % sobre 39 k líneas |
| Tamaño | ≈ 28 KLOC |

**Los 10 code smells** (capturas `08-issues-code-smells.jpg`, `09-…` y `10-…` en `viabilidad_cobertura/evidencias/RUN-SONAR-SCAN-W002/capturas/`):

| Regla | Ubicación | Severidad | Esfuerzo |
| --- | --- | --- | --- |
| S1845 — nombres que difieren solo en mayúsculas | `mealie/repos/repository_generic.py:55` (`model` / `Model`) | Blocker | 10 min |
| S1845 | `mealie/repos/repository_generic.py:56` (`schema` / `Schema`) | Blocker | 10 min |
| S1845 | `mealie/core/settings/settings.py:186` (`allowed_iframe_hosts` / `ALLOWED_IFRAME_HOSTS`) | Blocker | 10 min |
| S8413 — prefijo del router definido en `include_router()` | `mealie/routes/_base/controller.py:165` | Blocker | 2 min |
| S8510 — variable de bucle que oculta la del bucle externo | `mealie/services/query_filter/builder.py:509` | Critical | 2 min |
| S8786 — expresión regular con backtracking superlineal | `mealie/services/parser_services/parser_utils/string_utils.py:6, 80, 81` (3 casos) | Major | 20 min c/u |
| S8514 — atributo de dataclass sin anotación de tipo | `mealie/pkgs/i18n/provider_factory.py:18` | Major | 5 min |
| S7484 — espera activa con `sleep` en lugar de un `Event` | `mealie/services/scheduler/runner.py:64` | Major | 10 min |

### Ejemplo 1 — S1845 en el repositorio genérico

En `repository_generic.py:33` la clase se declara genérica con los parámetros de tipo `Schema` y `Model`; en las líneas 55-56 guarda `self.model = sql_model` y `self.schema = schema`. El código funciona, pero `Model` y `model`, o `Schema` y `schema`, son cosas distintas (un tipo y una instancia) con el mismo nombre. Es el archivo central de la Ruta B: quien busque cómo se filtra por hogar lee este código y tiene que distinguir los dos nombres. Corrección: renombrar los atributos, por ejemplo `self.sql_model`. Esfuerzo estimado por Sonar: 10 min cada uno.

### Ejemplo 2 — S8510 en el constructor de filtros de consulta

En `builder.py:451` un bucle recorre `for component in components:` y, dentro de él, en la línea 509, otro bucle reutiliza el nombre: `for component in new_components:`. Después del bucle interno, `component` ya no es el elemento del bucle externo. Sonar lo marca como **Critical** con impacto alto en fiabilidad y en mantenibilidad, porque cualquier código agregado después del bucle interno usaría el valor equivocado sin que nada lo advierta. Corrección: renombrar la variable interna. Esfuerzo: 2 min.

## 6. Interpretación

- **El rating A es coherente con la deuda medida:** 109 minutos de deuda para ≈ 28 KLOC es muy poco, y la duplicación (0,6 %) es casi nula. Los 10 smells se corrigen con renombres o cambios locales.
- **El rating no refleja los riesgos estructurales.** Lo que más dificulta entender y cambiar el código son decisiones de diseño, no smells: validación repartida en cinco capas, autorización implícita en la clase base y el repositorio genérico, y tres formas distintas de traducir errores a HTTP. Dos de los cuatro defectos confirmados (DEF-001 y DEF-003) nacen de esa inconsistencia en el manejo de errores.
- **Fortaleza principal:** la autorización por hogar está centralizada en un único filtro. Cambiarla o auditarla toca un solo punto, y las pruebas CP-A05 y CP-M10 confirmaron que funciona.
- **Riesgo principal:** como la protección depende de la clase base que hereda cada controlador y no se ve en el controlador, una ruta nueva que herede de la clase equivocada podría quedar sin filtro por hogar sin que la revisión lo note. Es una inferencia del diseño; no se observó ningún caso.

## 7. Límites

- Solo backend Python; el frontend Vue no se analizó con SonarQube.
- Sin cambios implementados no se mide el esfuerzo real de modificación: los conteos de archivos son estimaciones a partir del trazado.
- Las observaciones marcadas como inferencia no se ejecutaron. La línea sin efecto de la observación 4 se verificó leyendo el código, no con una prueba.
