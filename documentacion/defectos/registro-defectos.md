# Registro de defectos — Mealie v3.25.1

## Ciclo de vida

```text
Nuevo → Confirmado → Analizado → Reportado → Corregido → Verificado → Cerrado
              ↘ Rechazado (no reproducible o comportamiento esperado)
                         ↘ Diferido (fuera del control del equipo)
```

| Estado | Significado | Responsable |
| --- | --- | --- |
| Nuevo | Hallazgo registrado con su evidencia de origen (prueba, herramienta o log) | Quien lo detecta |
| Confirmado | Reproducido de forma independiente con pasos documentados | Ejecutor distinto o reproducción manual |
| Analizado | Causa raíz localizada en el código, con severidad y prioridad asignadas | Equipo de análisis |
| Reportado | Comunicado a quien puede corregirlo (equipo de Mealie) | Integrante designado |
| Corregido | Existe una corrección (parche o versión nueva) | Desarrollo |
| Verificado | La prueba de regresión pasa sobre la versión corregida | QA |
| Cerrado | Verificado y documentado | QA |

**Severidad:** Crítica (pérdida de datos o seguridad explotable) · Mayor (función principal inutilizable) · Menor (función secundaria o con alternativa) · Trivial. **Prioridad:** Alta · Media · Baja.

Mealie es software de terceros: el equipo no corrige su código. Un defecto confirmado y analizado pasa a **Reportado** si el grupo decide comunicarlo al proyecto, o a **Diferido** con su corrección propuesta.

## Resumen

| ID | Título | Severidad | Prioridad | Estado | OWASP 2025 |
| --- | --- | --- | --- | --- | --- |
| DEF-001 | Tag o herramienta inexistente por slug responde 500 en lugar de 404 | Menor | Media | Analizado | A10 |
| DEF-002 | Comentarios de una receta inexistente responden 500 en lugar de 404 | Menor | Media | Analizado | A10 |
| DEF-003 | El 11.º recetario con el mismo nombre falla y expone un error interno | Menor | Media | Analizado | A10 |
| DEF-004 | El planificador de comidas se abre sin sesión y no redirige al login | Menor | Baja | Analizado | — |
| DEF-005 | El plan de comidas acepta una receta inexistente y guarda una entrada sin nombre | Menor | Baja | Analizado | — |

## DEF-001 — Tag o herramienta inexistente por slug responde 500

| Campo | Contenido |
| --- | --- |
| Detectado | 2026-11-17, RUN-ZAP-002 (alerta 100000, `GET /api/organizers/tags/slug/tag_slug` → 500) |
| Ambiente | Mealie v3.25.1 local, usuario `qa_usuario_a` |
| Pasos | 1. Obtener un token de `qa_usuario_a`. 2. `GET /api/organizers/tags/slug/qa-no-existe`. 3. `GET /api/organizers/tools/slug/qa-no-existe`. 4. Comparar con `GET /api/organizers/categories/slug/qa-no-existe`. |
| Resultado esperado | 404 «Not found.» en los tres casos, como responde `categories` |
| Resultado obtenido | Pasos 2 y 3: **500** «Internal Server Error». Paso 4: 404 |
| Causa raíz | `mealie/routes/organizers/controller_tags.py:135` y `controller_tools.py:58` llaman a `self.repo.get_one(...)`, que devuelve `None` si no hay coincidencia; FastAPI no puede validar `None` contra el `response_model` y responde 500. `controller_categories.py:144` usa `self.mixins.get_one(...)`, que lanza 404. |
| Corrección propuesta | Usar `self.mixins.get_one(slug, "slug")` también en tags y herramientas |
| Impacto | Respuesta incorrecta para el cliente y ruido en logs; no expone datos |

**Historial:** Nuevo 2026-11-17 22:06 (ZAP) → Confirmado 22:09 (reproducción manual, 4 peticiones GET) → Analizado 22:11 (causa raíz).

## DEF-002 — Comentarios de una receta inexistente responden 500

| Campo | Contenido |
| --- | --- |
| Detectado | 2026-11-17, RUN-ZAP-002 (alerta 100000, `GET /api/recipes/slug/comments` → 500) |
| Ambiente | Mealie v3.25.1 local, usuario `qa_usuario_a` |
| Pasos | 1. Token de `qa_usuario_a`. 2. `GET /api/recipes/qa-no-existe` (control). 3. `GET /api/recipes/qa-no-existe/comments`. |
| Resultado esperado | 404 en ambos pasos |
| Resultado obtenido | Paso 2: 404 «No Entry Found». Paso 3: **500** «Internal Server Error» |
| Causa raíz | `mealie/routes/recipe/comments.py:13-14`: `recipe = self.repos.recipes.get_one(slug)` devuelve `None` y la línea siguiente accede a `recipe.id`, lo que lanza `AttributeError` |
| Corrección propuesta | Comprobar `if recipe is None` y lanzar `HTTPException(404)` antes de consultar los comentarios |
| Impacto | Respuesta incorrecta; no expone datos |

**Historial:** Nuevo 2026-11-17 22:06 (ZAP) → Confirmado 22:09 → Analizado 22:11.

## DEF-003 — El 11.º recetario con el mismo nombre falla y expone un error interno

| Campo | Contenido |
| --- | --- |
| Detectado | 2026-11-17, log de Mealie durante RUN-ZAP-002 (`RuntimeError: No active exception to reraise` en `repository_cookbooks.py`, línea 29) |
| Ambiente | Mealie v3.25.1 local, usuario `qa_usuario_a` |
| Pasos | 1. Token de `qa_usuario_a`. 2. Enviar 12 veces `POST /api/households/cookbooks` con `{"name": "QA-DEF-recetario"}`. |
| Resultado esperado | Todas las creaciones con slug único o, si se fija un límite, un error claro y sin detalles internos |
| Resultado obtenido | Intentos 1–10: 201. Intentos 11–12: **400** con cuerpo `{"message":"An unexpected error occurred", …, "exception":"No active exception to reraise"}` |
| Causa raíz | `mealie/repos/repository_cookbooks.py:21-29` (y `:43-50` en `update`): el bucle reintenta 10 slugs (`nombre`, `nombre (1)` … `nombre (9)`); al agotarlos ejecuta un `raise` sin excepción activa, fuera del bloque `except`, y Python lanza `RuntimeError`. El manejador de la ruta lo convierte en 400 y devuelve el mensaje interno al cliente (CWE-209). |
| Corrección propuesta | Guardar la última `IntegrityError` y relanzarla, o generar un sufijo sin límite fijo; responder 409 con un mensaje controlado |
| Impacto | No se pueden crear más de 10 recetarios con el mismo nombre en un hogar; el cliente recibe detalles internos |

**Historial:** Nuevo 2026-11-17 22:06 (log) → Confirmado 22:10 (reproducción manual; se había previsto un 500 en el intento 12, el resultado real fue 400 en el 11) → Analizado 22:11.

## DEF-004 — El planificador de comidas se abre sin sesión y no redirige al login

| Campo | Contenido |
| --- | --- |
| Detectado | 2026-11-17, RUN-MAN-001, caso CP-M10 paso 3 |
| Ambiente | Mealie v3.25.1 local, navegador sin sesión (después de cerrar la sesión de `qa_usuario_a`) |
| Pasos | 1. Cerrar sesión. 2. Abrir `http://localhost:9925/household/mealplan/planner/view`. |
| Resultado esperado | Redirección a `/login`, como ocurre con `/g/home` (CP-M02, paso 4) |
| Resultado obtenido | La página carga la grilla de la semana (17–23 nov) vacía, con barra lateral reducida y un botón «Login». La entrada existente del 18 de noviembre no aparece y la API responde 401, así que **no se exponen datos** |
| Causa raíz | `frontend/app/pages/household/mealplan/planner.vue` y `planner/view.vue` no declaran `definePageMeta`/`middleware`; otras páginas protegidas sí lo hacen (p. ej. `pages/g/[groupSlug]/cookbooks/index.vue:146-148`, `middleware: ["group-only"]`). No existe una redirección global al login para estas rutas |
| Corrección propuesta | Declarar en esas páginas un middleware que exija sesión y redirija a `/login` |
| Impacto | Inconsistencia de navegación: un visitante ve una pantalla funcional vacía en lugar del login; sin pérdida ni exposición de datos |

**Historial (UTC):** Nuevo 2026-11-17 ~23:00 (CP-M10) → Confirmado ~23:00 (segunda observación de la grilla vacía sin sesión; captura `CP-M10-planificador-sin-sesion.jpg`) → Analizado 23:01 (causa en el frontend).

## DEF-005 — El plan de comidas acepta una receta inexistente y guarda una entrada sin nombre

| Campo | Contenido |
| --- | --- |
| Detectado | 2026-11-18, RUN-USA-001, sesión P1: tras *Add to Plan* desde la tarjeta de la receta, la entrada del 19/11 apareció sin nombre en el planificador |
| Ambiente | Mealie v3.25.1 local con SQLite (motor por defecto), usuario `qa_usuario_a` |
| Pasos | 1. Token de `qa_usuario_a`. 2. `POST /api/households/mealplans` con `{"date": "2026-12-15", "entryType": "dinner", "recipeId": "<UUID aleatorio>", "title": ""}`. 3. `GET /api/households/mealplans/{id}` de la entrada creada. |
| Resultado esperado | Rechazo con 404 o 422, porque la receta no existe |
| Resultado obtenido | Paso 2: **201**; la entrada guarda el `recipeId` inventado y `recipe` es `null`. Paso 3: 200 con `recipe: null`. En el planificador la entrada se ve sin nombre. La entrada de prueba se borró |
| Causa raíz | `mealie/db/models/household/mealplan.py:70` declara `ForeignKey("recipes.id")`, pero SQLite solo aplica claves foráneas con `PRAGMA foreign_keys=ON`, y `mealie/db/db_setup.py:15-31` solo configura `journal_mode=WAL`. Además, `CreatePlanEntry` (`mealie/schema/meal_plan/new_meal.py:34-46`) solo exige `recipe_id` o `title`, y `create_one` (`mealie/routes/households/controller_mealplan.py:102-104`) no comprueba que la receta exista. Con PostgreSQL la restricción debería aplicarse; no se probó |
| Corrección propuesta | Comprobar en `create_one` y `update_one` que la receta exista y responder 404 si no, o habilitar `PRAGMA foreign_keys=ON` en la conexión SQLite |
| Impacto | Entradas huérfanas en el plan que el usuario debe corregir a mano; no expone datos |
| Disparo en la sesión | No reproducido desde la interfaz. Hipótesis: la pestaña conservaba identificadores de recetas que se borraron y recrearon al preparar los datos. En P2, sin ese cambio de identificadores, no ocurrió |

**Historial (UTC):** Nuevo 2026-11-18 ~18:39 (sesión P1) → Confirmado ~18:54 (reproducción por API con un identificador inventado) → Analizado ~19:15 (causa en el modelo y la conexión SQLite).

## Observaciones de usabilidad (RUN-MAN-001)

- **OBS-002:** la URL de una receta inexistente o eliminada (`/g/home/r/<slug>`) muestra una página vacía, sin mensaje de que la receta no existe (CP-M04, CP-M05). La API sí responde 404.
- **OBS-003:** al renombrar una receta en modo edición, la barra de direcciones conserva el slug anterior hasta navegar de nuevo (CP-M04).

## Observaciones de usabilidad (RUN-USA-001)

- **OBS-004:** en la lista de compras, al escribir «Leche» en el campo *Food*, el autocompletado no ofrece «Leche» y resalta «dulce de leche» como primera opción. Les pasó a las dos participantes; ninguna lo eligió, porque usaron el campo *Note*.

## Observaciones pendientes de reproducir

- **OBS-001:** el log de Mealie registró `badly formed hexadecimal UUID string` (`sqlalchemy.exc.StatementError`) durante RUN-ZAP-002: identificadores con formato inválido que llegan a la consulta en lugar de rechazarse con 422. Falta aislar la ruta y el cuerpo exactos antes de registrarlo como defecto.

## Hallazgos estáticos (SonarQube)

Los hallazgos de `../seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md` no se registran como defectos mientras ninguna prueba reproduzca su efecto.
