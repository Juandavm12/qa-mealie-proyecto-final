# Diseño de casos de prueba — Mealie v3.25.1

**Estado:** casos manuales **ejecutados** en RUN-MAN-001 (2026-11-17/18; ejecutor JD, ejecución asistida por Claude Code). «Resultado obtenido» y «Estado» resumen esa corrida; el registro crudo y las capturas están en `reports/manual/RUN-MAN-001/` (fuera de Git). Los resultados esperados se conservan tal como se diseñaron; donde el diseño resultó incorrecto se indica la corrección. Fuente de requisitos: `Alcance_requisitos_y_responsabilidades.md` (RF-01..RF-05). Contratos verificados en el código del tag `v3.25.1` (commit `cce7601e`); las referencias `archivo:línea` son relativas a `mealie-v3.25.1/`.

## 1. Ambiente y datos de prueba

| Elemento | Valor |
| --- | --- |
| Instancia | `http://localhost:9925` (UI) y `http://localhost:9925/api` (API, prefijo en `mealie/routes/__init__.py:19`); documentación interactiva en `/docs` |
| Versión | Mealie `v3.25.1`, imagen `sha256:6066c29e…`, SQLite, Docker Desktop (Hyper-V) en Windows 11 |
| Grupo | Grupo por defecto del administrador |
| Hogares | `QA-Hogar-A` y `QA-Hogar-B`, creados por el administrador en el mismo grupo |
| Usuarios sintéticos | `qa_usuario_a` (hogar A), `qa_usuario_b` (hogar B), `qa_usuario_c` (hogar A, exclusivo para el caso de bloqueo); todos sin rol de administrador |
| Credenciales | Contraseñas sintéticas generadas localmente; **no se documentan** ni se capturan en evidencias |
| Datos | Prefijo `QA-RUNxxx-` en recetas, listas y entradas de plan; fecha de plan `2026-11-18` |
| Limpieza | Solo se eliminan datos con prefijo `QA-`; nunca datos del administrador |

**Reglas de contrato que aplican a todos los casos** (verificadas):
- Sin token, las rutas de usuario responden **401** (`mealie/core/dependencies/dependencies.py:103-139`).
- Los repositorios por hogar filtran por `household_id` del usuario (`mealie/routes/_base/base_controllers.py:153-158`, `mealie/repos/repository_generic.py:94-102`): un recurso de otro hogar responde **404**, no 403 (`mealie/routes/_base/mixins.py:106-124`).
- Login: `POST /api/auth/token`, formulario `username`/`password`; acepta usuario o email (`mealie/core/security/providers/auth_provider.py:33-45`).

## 2. Técnicas de diseño aplicadas

### 2.1 Partición de equivalencia — creación de receta (CP-M08)

Regla: `CreateRecipe.name: str` obligatorio sin valor por defecto (`mealie/schema/recipe/recipe.py:113-114`), consumido por `POST /api/recipes` (`mealie/routes/recipe/recipe_crud_routes.py:570-592`).

| Clase | Descripción | Representante | Resultado esperado |
| --- | --- | --- | --- |
| EV1 (válida) | Objeto JSON con `name` string no vacío y con caracteres alfanuméricos | `{"name": "QA-RUN001-particion"}` | **201**, cuerpo = slug `qa-run001-particion`; la receta existe |
| EI1 (inválida) | Objeto JSON sin `name` | `{}` | **422** (validación); no se crea receta |
| EI2 (inválida) | `name` de tipo no string | `{"name": null}` | **422**; no se crea receta |

No se afirma regla para cadena vacía ni longitud máxima: el esquema no las define (no hay `min_length`/`max_length`).

### 2.2 Valores límite — longitud mínima de contraseña nueva (CP-M09)

Regla: `ChangePassword.new_password` con `min_length=8` (`mealie/schema/user/user.py:61-63`), ruta `PUT /api/users/password` (`mealie/routes/users/crud.py:42-63`). Límite inferior L = 8; no existe máximo.

| Subcaso | Longitud | Clase | Resultado esperado |
| --- | --- | --- | --- |
| CP-M09.a | L−1 = 7 | Inválida | **422**; la contraseña no cambia (el login con la anterior sigue funcionando) |
| CP-M09.b | L = 8 | Válida | **200**; login con la nueva funciona |
| CP-M09.c | L+1 = 9 | Válida | **200**; login con la nueva funciona |

### 2.3 Valores límite — umbral de bloqueo de cuenta (CP-M11)

Regla: `SECURITY_MAX_LOGIN_ATTEMPTS = 5` (`mealie/core/settings/settings.py:231`); cada contraseña errónea incrementa `login_attemps`; con 5 o más se rechaza todo login con **423** (`mealie/core/security/providers/credentials_provider.py:40-52`). Límite L = 5.

| Intento erróneo n.º | Relación con L | Resultado esperado |
| --- | --- | --- |
| 4 | L−1 | **401** (cuenta aún no bloqueada) |
| 5 | L | **401** y la cuenta queda bloqueada |
| 6 (con contraseña **correcta**) | L+1 | **423** `{"detail":"User is locked out"}` |

### 2.4 Tabla de decisión — acceso a una entrada del plan de comidas (CP-M10, CP-A04, CP-A05)

| Condición / regla | R1 | R2 | R3 |
| --- | --- | --- | --- |
| Token válido | No | Sí | Sí |
| Usuario del mismo hogar que la entrada | — | Sí | No |
| **Acción esperada** | 401, sin datos | 200, datos de la entrada | 404, sin datos; la entrada no cambia |
| Casos | CP-M10, CP-A04 | CP-M06 | CP-A05 |

## 3. Casos manuales

> Los casos CP-M08, CP-M09 y CP-M11 se ejecutan **manualmente sobre la API** (Swagger `/docs` o cliente HTTP) porque la UI impide enviar los datos inválidos; siguen siendo ejecuciones manuales.

### CP-M01 — Inicio de sesión válido
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que un usuario con credenciales válidas accede a su sesión |
| Requisito | RF-01.C1 · Técnica: partición de equivalencia (clase válida de credenciales) |
| Precondiciones | `qa_usuario_a` creado y no bloqueado; sesión cerrada en el navegador |
| Datos de entrada | Email de `qa_usuario_a` y su contraseña válida |
| Pasos | 1. Abrir `http://localhost:9925/login`. 2. Ingresar email y contraseña. 3. Pulsar «Login». 4. Abrir el menú de perfil. |
| Resultado esperado | Redirección a la página principal del hogar; el perfil muestra `qa_usuario_a` y el hogar `QA-Hogar-A` |
| Resultado obtenido | Redirección a `/g/home`; la barra lateral y el perfil muestran «QA Usuario A»; la sesión corresponde a `qa_usuario_a`, hogar `QA-Hogar-A`, sin rol de administrador |
| Estado | **Aprobado** |

### CP-M02 — Inicio de sesión con contraseña incorrecta
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que una contraseña incorrecta no crea sesión |
| Requisito | RF-01.C2 · Técnica: partición de equivalencia (clase inválida) |
| Precondiciones | `qa_usuario_a` con 0 intentos fallidos; sesión cerrada |
| Datos de entrada | Email de `qa_usuario_a` y contraseña `QA-incorrecta-1` |
| Pasos | 1. Abrir `/login`. 2. Ingresar los datos. 3. Pulsar «Login». 4. Intentar abrir `http://localhost:9925/g/home` directamente. 5. Iniciar sesión con la contraseña correcta (restablece el contador, `credentials_provider.py:54`). |
| Resultado esperado | Mensaje de error de credenciales; permanece en `/login`; el paso 4 redirige a `/login`; el paso 5 entra normalmente |
| Resultado obtenido | Paso 3: 401 y aviso «Invalid Credentials»; permanece en `/login`. Paso 4: `/g/home` redirige a `/login`. Paso 5: entra normalmente. Dos intentos previos se anularon porque el gestor de contraseñas del navegador sobrescribía el campo; no es defecto de Mealie |
| Estado | **Aprobado** |

### CP-M03 — Crear y consultar una receta
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que una receta creada persiste y se puede consultar |
| Requisito | RF-02.C1 |
| Precondiciones | Sesión de `qa_usuario_a` |
| Datos de entrada | Nombre `QA-RUN001-receta`; ingrediente `200 g arroz`; paso «Cocinar 15 minutos» |
| Pasos | 1. «+ Create» → «Create Recipe». 2. Escribir el nombre y crear. 3. Agregar ingrediente y paso; guardar. 4. Recargar la página (F5). 5. Buscar `QA-RUN001` en el listado de recetas. |
| Resultado esperado | Tras recargar, la receta conserva nombre, ingrediente y paso; aparece en la búsqueda con URL `/recipe/qa-run001-receta` |
| Resultado obtenido | Tras recargar conserva nombre, ingrediente `200 g arroz` y paso «Cocinar 15 minutos»; la búsqueda devuelve 1 resultado. **Corrección del diseño:** la URL real es `/g/home/r/qa-run001-receta` (rutas v3 `/g/{grupo}/r/{slug}`), no `/recipe/…` |
| Estado | **Aprobado** |

### CP-M04 — Editar una receta
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que la edición del nombre persiste |
| Requisito | RF-02.C2 |
| Precondiciones | CP-M03 aprobado; receta `QA-RUN001-receta` existente |
| Datos de entrada | Nuevo nombre `QA-RUN001-receta-editada` |
| Pasos | 1. Abrir la receta. 2. Editar. 3. Cambiar el nombre y guardar. 4. Recargar. 5. Abrir la URL anterior `/recipe/qa-run001-receta`. |
| Resultado esperado | Se muestra el nombre nuevo y la URL pasa a `/recipe/qa-run001-receta-editada` (el slug se regenera al renombrar, `mealie/repos/repository_recipes.py:208-209`); la URL anterior ya no muestra la receta |
| Resultado obtenido | Nombre y slug pasan a `qa-run001-receta-editada`; la URL anterior ya no muestra la receta (API 404). Observaciones de usabilidad: la URL anterior muestra una página vacía sin mensaje, y en modo edición la barra de direcciones conserva el slug anterior. Un primer intento se anuló por un clic fallido del ejecutor |
| Estado | **Aprobado** |

### CP-M05 — Eliminar una receta propia
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que una receta eliminada deja de estar disponible |
| Requisito | RF-02.C3 |
| Precondiciones | CP-M04 aprobado |
| Datos de entrada | Receta `QA-RUN001-receta-editada` |
| Pasos | 1. Abrir la receta. 2. Menú «⋮» → «Delete» → confirmar. 3. Buscar `QA-RUN001` en el listado. 4. Abrir `/recipe/qa-run001-receta-editada`. |
| Resultado esperado | La receta no aparece en la búsqueda; la URL muestra que no existe (API: `GET /api/recipes/{slug}` → 404, `recipe_crud_routes.py:102-106`) |
| Resultado obtenido | La receta no aparece en la búsqueda y la API responde 404. La URL muestra una página vacía, sin mensaje de que la receta no existe (misma observación que CP-M04) |
| Estado | **Aprobado con observación** |

### CP-M06 — Asociar una receta al plan de comidas
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que una entrada del plan conserva fecha, tipo y receta |
| Requisito | RF-03.C1–C2 · Tabla de decisión R2 |
| Precondiciones | Sesión de `qa_usuario_a`; receta `QA-RUN001-plan` creada |
| Datos de entrada | Fecha `2026-11-18`, tipo `Dinner`, receta `QA-RUN001-plan` |
| Pasos | 1. Abrir «Meal Planner». 2. Ubicar `2026-11-18`; agregar entrada tipo Dinner con la receta. 3. Recargar. 4. Comparar con `2026-11-19`. |
| Resultado esperado | Tras recargar, `2026-11-18` muestra la receta como Dinner; `2026-11-19` no tiene esa entrada |
| Resultado obtenido | Tras recargar, el 18 de noviembre muestra la receta como Dinner y el 19 no tiene entradas; la API devuelve una sola entrada (id 1, `dinner`) |
| Estado | **Aprobado** |

### CP-M07 — Lista de compras: agregar y marcar ítem
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que un ítem y su estado «comprado» persisten sin duplicarse |
| Requisito | RF-04.C1–C2 |
| Precondiciones | Sesión de `qa_usuario_a` |
| Datos de entrada | Lista `QA-RUN001-lista`; ítem `QA-arroz`, cantidad 2 |
| Pasos | 1. «Shopping Lists» → crear la lista. 2. Agregar el ítem con cantidad 2. 3. Recargar. 4. Marcar el ítem como comprado. 5. Recargar. |
| Resultado esperado | Paso 3: un solo ítem `QA-arroz` con cantidad 2. Paso 5: el ítem aparece marcado/en comprados, sin duplicados |
| Resultado obtenido | Paso 3: un solo ítem `QA-arroz`, cantidad 2. Paso 5: el ítem queda en «One item checked» (API `checked: true`), sin duplicados |
| Estado | **Aprobado** |

### CP-M08 — Crear receta por API: particiones de `name`
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que la API acepta la clase válida y rechaza las inválidas sin crear recetas |
| Requisito | RF-02.C4 · Técnica: **partición de equivalencia** (§2.1) |
| Precondiciones | Token de `qa_usuario_a` (obtenido en `/docs` con «Authorize») |
| Datos de entrada | EV1 `{"name":"QA-RUN001-particion"}`, EI1 `{}`, EI2 `{"name":null}` |
| Pasos | 1. En `/docs`, `POST /api/recipes` con EV1. 2. Repetir con EI1. 3. Repetir con EI2. 4. `GET /api/recipes?search=QA-RUN001-particion`. |
| Resultado esperado | EV1 → 201 con slug; EI1 → 422; EI2 → 422; el paso 4 devuelve exactamente 1 receta |
| Resultado obtenido | EV1 → 201 `"qa-run001-particion"`; EI1 → 422 `missing`; EI2 → 422 `string_type`. Paso 4: la búsqueda devuelve 2 recetas porque no es exacta (también coincide `QA-RUN001-plan`); el hogar tiene solo esas 2 recetas, así que las clases inválidas no crearon nada. **Corrección del diseño:** el oráculo del paso 4 debe contar recetas con nombre exacto (resultado: 1) |
| Estado | **Aprobado** (EV1, EI1, EI2) |

### CP-M09 — Cambio de contraseña: valores límite 7/8/9
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar el límite inferior de longitud de la contraseña nueva |
| Requisito | RF-01.C3 · Técnica: **valores límite** (§2.2) |
| Precondiciones | Token de `qa_usuario_c` (no `qa_usuario_a`: la automatización usa sus credenciales); ejecutar después de CP-M11 y del desbloqueo; contraseña actual conocida; contraseñas candidatas generadas fuera del documento |
| Datos de entrada | Contraseñas nuevas de 7, 8 y 9 caracteres |
| Pasos | Por subcaso: 1. `PUT /api/users/password` con `currentPassword` y `newPassword`. 2. Verificar login con la contraseña vigente esperada. 3. Pedir un token nuevo antes del siguiente subcaso (el cambio invalida sesiones previas, `mealie/db/models/users/users.py:207-213`). |
| Resultado esperado | 7 → 422 y la anterior sigue válida; 8 → 200 y login con la nueva; 9 → 200 y login con la nueva |
| Resultado obtenido | 7 → 422 `string_too_short` y la anterior sigue válida (login 200); 8 → 200 y login con la nueva 200; 9 → 200 y login con la nueva 200. Se restauró la contraseña original de `qa_usuario_c` |
| Estado | **Aprobado** (a, b, c) |

### CP-M10 — Plan de comidas sin sesión
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar que el plan no se expone sin autenticación |
| Requisito | RF-05.C1 · Tabla de decisión R1 |
| Precondiciones | Entrada de CP-M06 existente (anotar su `id`); ventana privada sin sesión |
| Datos de entrada | `id` de la entrada |
| Pasos | 1. En ventana privada abrir `http://localhost:9925/api/households/mealplans/{id}`. 2. Abrir `http://localhost:9925/api/households/mealplans`. 3. Abrir la UI del planificador. |
| Resultado esperado | Pasos 1–2: 401 `{"detail":"Not authenticated"}` sin datos del plan; paso 3: redirección a `/login` |
| Resultado obtenido | Pasos 1–2: 401 sin datos del plan, con mensaje `Could not validate credentials` (**corrección del diseño:** no «Not authenticated»; `dependencies.py:29-31, 76-89`). Paso 3: **no redirige a `/login`**: muestra la grilla de la semana vacía con un botón «Login». El plan no se expone, pero no se cumple el resultado esperado → **DEF-004** |
| Estado | **Fallido** (paso 3) |

### CP-M11 — Bloqueo de cuenta: valores límite 4/5/6
| Campo | Contenido |
| --- | --- |
| Objetivo | Verificar el umbral de bloqueo por intentos fallidos |
| Requisito | RF-01.C2 (protección de autenticación) · Técnica: **valores límite** (§2.3) |
| Precondiciones | `qa_usuario_c` con 0 intentos; el administrador puede desbloquear (`POST /api/admin/users/unlock`) |
| Datos de entrada | Contraseña errónea `QA-incorrecta-1`; contraseña correcta en el 6.º intento |
| Pasos | 1. Enviar 4 logins erróneos a `POST /api/auth/token`. 2. Enviar el 5.º erróneo. 3. Enviar el 6.º con la contraseña correcta. 4. El administrador desbloquea a `qa_usuario_c`. |
| Resultado esperado | Intentos 1–5: 401; intento 6: 423 «User is locked out» aun con la contraseña correcta; tras desbloquear, login correcto → 200 |
| Resultado obtenido | Intentos 1–5: 401 `Unauthorized`; intento 6 con la contraseña correcta: 423 «User is locked out»; tras «Reset Locked Users» del administrador («1 user(s) unlocked»), login correcto → 200 |
| Estado | **Aprobado** |

## 4. Casos automatizados (Pytest + cliente HTTP)

Implementación: `pruebas/api/test_mealie_api.py` y `pruebas/api/conftest.py`. La configuración es externa: variables de entorno o el archivo ignorado `.env.qa`, nunca el repositorio. Dependencias fijadas en `pruebas/requirements.txt` (pytest 9.2.0, requests 2.34.2). Reporte JUnit XML con `pytest --junitxml=reports/RUN-API-xxx.xml`. Sin credenciales, los casos API se omiten (*skip*) con el motivo, para que el CI sin instancia no falle en falso.

Primera ejecución local: `RUN-API-001` (2026-11-17), 5/5 casos API aprobados en 22 s; luego se verificó que no quedaran datos sintéticos residuales (0 recetas `QA-RUNA*`, 0 entradas del plan el 2026-11-18).

| ID | Nombre | Requisito | Precondiciones | Pasos y aserciones | Resultado esperado |
| --- | --- | --- | --- | --- | --- |
| CP-A01 | Login API válido e identidad | RF-01.C1 | `qa_usuario_a` activo | `POST /api/auth/token` → usar `access_token` en `GET /api/users/self` | 200 con `token_type="bearer"`; `/self` 200 con `username="qa_usuario_a"` y `household` del hogar A |
| CP-A02 | Login API inválido | RF-01.C2 | `qa_usuario_b` con 0 intentos | Login con contraseña errónea; luego `GET /api/users/self` con un token inventado; finalmente login correcto (restablece contador) | 401 sin `access_token`; `/self` 401; login correcto 200 |
| CP-A03 | Ciclo CRUD de receta | RF-02.C1–C3 | Token de A | Crear `QA-RUNxxx-crud` → GET por slug → PATCH nombre → GET → DELETE → GET | 201, 200 con nombre, 200 con nombre nuevo, 200 en DELETE y **404** final |
| CP-A04 | Plan de comidas sin token | RF-05.C1 | Entrada del plan de A creada por fixture | `GET /api/households/mealplans/{id}` y `GET /api/households/mealplans` sin cabecera `Authorization` | 401 y el cuerpo no contiene campos de la entrada |
| CP-A05 | Usuario de otro hogar sobre el plan de A | RF-05.C2 | Entrada de A; token de B (hogar B) | B hace GET, PUT y DELETE sobre la entrada de A; A vuelve a leerla | GET/PUT/DELETE de B → **404**; la lectura de A devuelve la entrada sin cambios |

Un escenario con varias aserciones cuenta como **un** caso. Los datos creados se eliminan en el *teardown* del fixture.

## 5. Trazabilidad

| Requisito | Manuales | Automatizados | Técnica |
| --- | --- | --- | --- |
| RF-01 Autenticación | CP-M01, CP-M02, CP-M09, CP-M11 | CP-A01, CP-A02 | EP, BVA (×2) |
| RF-02 Recetas | CP-M03, CP-M04, CP-M05, CP-M08 | CP-A03 | EP |
| RF-03 Plan de comidas | CP-M06 | — | Tabla de decisión R2 |
| RF-04 Listas de compras | CP-M07 | — | — |
| RF-05 Protección del plan | CP-M10 | CP-A04, CP-A05 | Tabla de decisión R1/R3 |

Totales: **11 manuales** (mínimo exigido 10) y **5 automatizados** (mínimo 5).
