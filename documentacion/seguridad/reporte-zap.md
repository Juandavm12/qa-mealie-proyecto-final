# Análisis dinámico con OWASP ZAP — Mealie v3.25.1

**Fecha:** 2026-11-17. **Herramienta:** OWASP ZAP 2.17.0 (`ghcr.io/zaproxy/zaproxy:stable`, imagen `sha256:9624669d…`, linux/amd64). **Objetivo:** instancia local de Mealie v3.25.1 (imagen `sha256:6066c29e…`, SQLite). **Edición OWASP:** Top 10:2025, verificada en https://top10.owasp.org/2025.

Los reportes crudos (HTML, JSON, Markdown y log) quedan fuera del repositorio, en `reports/zap/RUN-ZAP-00x/`. Este documento es su resumen saneado: no contiene tokens ni credenciales.

## 1. Configuración de las corridas

| Corrida | Tipo | Autenticación | Alcance | Duración |
| --- | --- | --- | --- | --- |
| RUN-ZAP-001 | Baseline: *spider* (3 min máx.) + escaneo pasivo | Ninguna | Interfaz web (`/`) | 34 s (21:50:12–21:50:46 UTC) |
| RUN-ZAP-002 | API: importación OpenAPI + escaneo **activo** (política `API-Minimal`) | Token de sesión de `qa_usuario_a` (no admin, hogar `QA-Hogar-A`), verificado antes de usarlo | 143 operaciones de la especificación OpenAPI 3.1.0 filtrada | 6 min 42 s (21:59:14–22:05:56 UTC) |

**Aislamiento:** ZAP compartió el espacio de red del contenedor de Mealie (`--network container:…`), así que solo alcanzó `http://localhost:9000` y no publicó puertos. El token viajó solo por variables de entorno del proceso `docker`, se redactó de logs y reportes (incluida cualquier cadena con forma de JWT), y en ambas corridas se verificó `token_absent_from_outputs: true`. El contenedor y el volumen de trabajo se eliminaron al terminar.

**Filtro de la especificación (RUN-ZAP-002):** un escaneo activo ejecuta escrituras reales. Para no crear credenciales ni tocar datos compartidos, de las 264 operaciones de Mealie se excluyeron 121 (lista completa en `zap-operaciones-excluidas.txt`):
- **Excluidas por completo:** `/api/admin/*`, `/api/auth/*`, tokens de API, cambio/recuperación de contraseña, registro, creación de recetas desde URL y *scraping*.
- **Solo lectura:** usuarios, grupo, organizadores, alimentos y unidades (datos de todo el grupo), webhooks, notificaciones y *recipe-actions* (llamadas salientes), invitaciones, permisos y preferencias del hogar, y enlaces públicos.

Se mantuvieron 46 escrituras, todas dentro del hogar: recetas, plan de comidas y sus reglas, listas de compras, recetarios, comentarios y línea de tiempo.

**Límites del escaneo activo:** 45 min máx. por escaneo, 4 min máx. por regla, 2 hilos por host.

## 2. Resultados

| Corrida | URL | FAIL | WARN | PASS |
| --- | --- | --- | --- | --- |
| RUN-ZAP-001 | 122 | 0 | 7 | 61 |
| RUN-ZAP-002 | 464 (180 importadas de OpenAPI) | 0 | 9 | 113 |

Ninguna alerta de riesgo alto en ninguna corrida.

| Alerta ZAP (id) | Riesgo (confianza) | 001 | 002 | CWE | OWASP 2025 | Clasificación |
| --- | --- | --- | --- | --- | --- | --- |
| Content Security Policy no definida (10038) | Medio (Alta) | 2 | 3 | 693 | A02 Security Misconfiguration | Confirmada |
| Falta cabecera anti-clickjacking (10020) | Medio (Media) | 2 | 3 | 1021 | A02 | Confirmada |
| X-Content-Type-Options ausente (10021) | Bajo | 4 | 12 | 693 | A02 | Confirmada |
| Permissions-Policy ausente (10063) | Bajo | 5 | 3 | 693 | A02 | Confirmada |
| Cross-Origin-Resource/Opener/Embedder-Policy (90004) | Bajo | 5 | 12 | 693 | A02 | Confirmada |
| Respuesta de error de servidor 500 (100000) | Bajo (Alta) | — | 14 | 388 | A10 Mishandling of Exceptional Conditions | **Confirmada: DEF-001, DEF-002** |
| Divulgación de error de aplicación (90022) | Bajo | — | 5 | 550 | A10 | Parcial: los 500 devuelven el texto genérico «Internal Server Error», sin traza |
| Mensajes de depuración (10023) | Bajo | — | 5 | 1295 | A10 | Falso positivo: misma evidencia genérica |
| Content-Type inesperado (100001) | Bajo | — | 247 | — | — | Informativa: respuestas de error a datos generados por ZAP |
| Información sensible en URL (10024) | Info | — | 1 | 598 | A02 | Por diseño: `/api/utils/download?token=` usa un token de descarga de corta vida |
| Errores de cliente 4xx (100000) | Info | — | 221 | 388 | — | Esperado: validación (422), 404 y 403 ante entradas inválidas |
| Aplicación web moderna / contenido cacheable | Info | 2 / 5 | 3 / 6 | — / 524 | — | Informativa |

## 3. Hallazgos convertidos en defectos

Los errores 500 se reprodujeron manualmente como `qa_usuario_a` y se rastrearon hasta el código (detalle en `../defectos/registro-defectos.md`):

- **DEF-001:** `GET /api/organizers/tags/slug/{slug}` y `/tools/slug/{slug}` responden 500 ante un slug inexistente; `categories` responde 404.
- **DEF-002:** `GET /api/recipes/{slug}/comments` responde 500 ante una receta inexistente.
- **DEF-003:** el 11.º recetario con el mismo nombre falla con 400 y expone el mensaje interno `No active exception to reraise`. Lo detectó el log de Mealie durante el escaneo; se reprodujo a mano.

El log de Mealie también registró errores `badly formed hexadecimal UUID string`: identificadores mal formados que llegan a la base de datos en lugar de rechazarse con 422. Quedan como observación, pendiente de reproducir.

## 4. Controles de seguridad que se cumplieron

- **Control de acceso (A01):** el escaneo autenticado no reveló acceso a datos de otros hogares. La prueba dirigida CP-A05 confirma que B recibe **404** al leer, editar o borrar la entrada del plan de A.
- **Autenticación (A07):** las rutas protegidas responden 401 sin token (CP-A04). El bloqueo tras 5 intentos fallidos se evalúa en CP-M11.
- **Cookies:** sin alertas de `HttpOnly` ni `Secure` en la cookie de sesión (reglas 10010/10011 en PASS).

## 5. Impacto en los datos y restauración

El escaneo activo dejó datos sintéticos en el hogar A: 115 recetas, 114 recetarios, 88 reglas del plan y 115 eventos de línea de tiempo. Los datos del administrador no se modificaron. Se restauró el respaldo tomado justo antes del escaneo (SHA-256 `a327bda3…`); el volumen quedó idéntico al respaldo (`diff -r` limpio, `integrity_check` ok) y la suite API pasó 5/5 después de restaurar.

## 6. Límites de la evaluación

- La UI es una SPA (Nuxt): el *spider* sin sesión ve la carcasa y los recursos JS, no los flujos autenticados de la interfaz.
- El filtro excluyó a propósito autenticación, administración y endpoints con llamadas salientes; esas superficies no se atacaron activamente.
- Se usó la política `API-Minimal` con límites de tiempo: la ausencia de alertas no demuestra la ausencia de vulnerabilidades.
- Instancia local publicada solo en `127.0.0.1`, sin TLS ni proxy inverso: las cabeceras ausentes deberían añadirse en el despliegue (proxy) de producción.
