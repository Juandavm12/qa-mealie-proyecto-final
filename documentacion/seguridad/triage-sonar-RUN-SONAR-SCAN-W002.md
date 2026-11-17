# Triage de hallazgos SonarQube — RUN-SONAR-SCAN-W002

**Análisis:** SonarQube Community Build 26.11.0.134175, modo Standard Experience, proyecto `mealie-3-25-1-piloto-local-backend`, alcance backend Python (`**/*.py`) de Mealie v3.25.1 (commit `cce7601ef3ff3fddb3932918cd9d59b6c7158c39`). Fecha: 2026-11-17. Evidencias: `viabilidad_cobertura/evidencias/RUN-SONAR-SCAN-W002/capturas/04..07`.

**Edición OWASP:** Top 10:2025, códigos y nombres verificados en https://top10.owasp.org/2025 el 2026-11-17; no se mezcla con la edición 2021.

## Vulnerabilidades (6)

| ID | Archivo:línea | Regla / severidad Sonar | Lectura del código | Clasificación | OWASP 2025 | Mitigación / recomendación |
| --- | --- | --- | --- | --- | --- | --- |
| SEG-001 | `mealie/app.py:166` | Vincular la app a todas las interfaces — Blocker | `main()` es el arranque de desarrollo (`reload=True`, `reload_dirs`); la imagen Docker define `ENV HOST=0.0.0.0` (`docker/Dockerfile:153`), necesario dentro de un contenedor | Patrón real, **no explotable en el despliegue evaluado**: el Compose publica solo `127.0.0.1:9925` | A02:2025 Security Misconfiguration | Publicar el puerto solo en loopback o detrás de proxy inverso con TLS; no exponer `0.0.0.0:9925` en el host; parametrizar `host` en `main()` |
| SEG-002 | `mealie/repos/repository_generic.py:450` | PRNG no criptográfico — Major | `random.seed(pagination_seed)` + `shuffle`: orden aleatorio reproducible de resultados paginados | **Falso positivo justificado**: necesita ser determinista por semilla; no protege ningún secreto | A04:2025 Cryptographic Failures (evaluada, sin hallazgo) | Ninguna; documentar la intención con un comentario o marcar como revisado |
| SEG-003 | `mealie/repos/repository_recipes.py:157` | PRNG — Major | `randint(0, 255)` como marcador de versión de imagen (rompe la caché del navegador) | Falso positivo justificado | A04:2025 (sin hallazgo) | Ninguna |
| SEG-004 | `mealie/pkgs/cache/cache_key.py:8` | PRNG — Major | Clave de 4 caracteres para la caché de datos del frontend | Falso positivo justificado: no es un token de acceso | A04:2025 (sin hallazgo) | Ninguna; si alguna vez se usara como secreto, migrar a `secrets` |
| SEG-005 | `mealie/repos/repository_users.py:41` | PRNG — Major | `random.choice` entre 3 imágenes de perfil por defecto | Falso positivo justificado | A04:2025 (sin hallazgo) | Ninguna |
| SEG-006 | `mealie/pkgs/safehttp/fetch.py:214` | PRNG — Major | `random.shuffle` del orden de suplantación de navegador al descargar recetas | Falso positivo justificado | A04:2025 (sin hallazgo) | Ninguna |

**Contraste que respalda el triage:** los valores sensibles sí usan generación criptográfica: `secrets.token_urlsafe(24)` en `mealie/core/security/security.py:51` y `secrets.token_hex(32)` en `mealie/core/settings/settings.py:84`.

**Lectura:** el Security Rating E se debe a un único Blocker (SEG-001) cuyo riesgo depende del despliegue; las 5 alertas de PRNG no representan riesgo real. Cero Security Hotspots. Este análisis estático no evalúa autorización entre hogares ni sesiones: eso corresponde a ZAP y a las pruebas CP-M10 / CP-A04 / CP-A05.

## Bugs (6, todos Major)

| ID | Archivo:línea | Regla | Efecto probable | Alcance de la evaluación |
| --- | --- | --- | --- | --- |
| BUG-S01 | `mealie/routes/recipe/recipe_crud_routes.py:296` | Tarea asyncio sin referencia | La tarea puede ser recolectada antes de terminar (comportamiento documentado de `asyncio.create_task`) | Dentro (recetas) |
| BUG-S02 | `mealie/services/scheduler/scheduler_service.py:27` | Tarea asyncio sin referencia | Tareas programadas podrían no completarse | Transversal |
| BUG-S03 | `mealie/services/scheduler/runner.py:79` | Tarea asyncio sin referencia | Igual que BUG-S02 | Transversal |
| BUG-S04 | `mealie/services/recipe/ai_recipe_service.py:62` | `open()` síncrono en función async | Bloquea el event loop durante la E/S | Fuera (IA excluida del alcance) |
| BUG-S05 | `mealie/services/openai/openai.py:335` | `open()` síncrono en función async | Igual que BUG-S04 | Fuera (IA) |
| BUG-S06 | `mealie/services/openai/openai.py:350` | `open()` síncrono en función async | Igual que BUG-S04 | Fuera (IA) |

Son defectos de fiabilidad del código, no fallos funcionales observados: no se convierten en `DEF-xxx` salvo que una prueba reproduzca su efecto.
