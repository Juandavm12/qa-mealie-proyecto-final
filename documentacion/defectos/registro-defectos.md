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

## Observaciones pendientes de reproducir

- **OBS-001:** el log de Mealie registró `badly formed hexadecimal UUID string` (`sqlalchemy.exc.StatementError`) durante RUN-ZAP-002: identificadores con formato inválido que llegan a la consulta en lugar de rechazarse con 422. Falta aislar la ruta y el cuerpo exactos antes de registrarlo como defecto.

## Hallazgos estáticos (SonarQube)

Los hallazgos de `../seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md` no se registran como defectos mientras ninguna prueba reproduzca su efecto.
