# Plan de pruebas — Mealie v3.25.1

| Campo | Valor |
| --- | --- |
| Identificador | PP-MEALIE-001 |
| Versión | 1.0, 2026-11-18 |
| Sistema bajo prueba | Mealie v3.25.1 (imagen Docker `sha256:6066c29e…`, commit `cce7601e`) |
| Referencia normativa | Estructura basada en el plan de pruebas de ISO/IEC/IEEE 29119-3 (documentación de pruebas), que reemplaza a IEEE 829. Se usa como guía de contenido; no se afirma conformidad formal con la norma |
| Documentos relacionados | [`casos-de-prueba.md`](casos-de-prueba.md), [`defectos/registro-defectos.md`](defectos/registro-defectos.md), [`kpis.md`](kpis.md), [`responsabilidades.md`](responsabilidades.md), reportes de [seguridad](seguridad/) y [rendimiento](rendimiento/) |

El plan se redactó con los criterios ya congelados en el documento de alcance del grupo, antes de cada corrida evaluativa, y se consolida aquí con el estado real de cada actividad al 2026-11-18.

## 1. Objetivos de prueba

1. Verificar que las funciones centrales de Mealie (autenticación, recetas, plan de comidas y listas de compras) cumplen sus criterios de aceptación.
2. Verificar que un usuario no puede leer ni modificar el plan de comidas privado de otro hogar, ni acceder a él sin sesión.
3. Evaluar los seis atributos de calidad de la guía: funcionalidad, usabilidad, fiabilidad, rendimiento, seguridad y mantenibilidad.
4. Identificar vulnerabilidades según OWASP Top 10:2025 con análisis estático (SonarQube) y dinámico (OWASP ZAP), y proponer mitigaciones.
5. Automatizar casos representativos e integrarlos en un pipeline de CI reproducible.
6. Registrar los defectos con su ciclo de vida y medir la calidad con indicadores trazables a corridas identificadas.

## 2. Alcance

### 2.1 Elementos y funciones bajo prueba

| Requisito | Función | Prioridad |
| --- | --- | --- |
| RF-01 | Autenticación: inicio de sesión, credenciales inválidas, cambio de contraseña y bloqueo de cuenta | Alta |
| RF-02 | CRUD de recetas por interfaz y API, incluida la validación del cuerpo de creación | Alta |
| RF-03 | Asociar una receta a una fecha del plan de comidas | Alta |
| RF-04 | Listas de compras: agregar ítems y marcarlos como comprados | Alta |
| RF-05 | Protección del plan de comidas sin sesión y entre hogares | Alta |
| RNF-01..06 | Funcionalidad, usabilidad, fiabilidad, rendimiento, seguridad y mantenibilidad | — |

Los subcriterios y sus criterios de aceptación están en `casos-de-prueba.md` (§3 a §5).

### 2.2 Fuera de alcance

IA, OIDC, LDAP, SMTP, pagos, importaciones reales de terceros, comparación de motores de base de datos (SQLite frente a PostgreSQL), pruebas de estrés destructivas, caídas o reinicios de servicios, y accesibilidad completa. Los resultados son locales y no se generalizan como garantías o SLA de Mealie.

## 3. Niveles de prueba

| Nivel | Qué se prueba | Cómo | Estado |
| --- | --- | --- | --- |
| **Unitarias** | Funciones aisladas de Mealie y de las herramientas propias del grupo | 58 pruebas unitarias upstream de Mealie con instrumentación de cobertura (RUN-COV-001); 48 pruebas unitarias de los scripts propios (preparación de datos, ZAP, rendimiento), ejecutadas en el CI | Ejecutado |
| **Integración** | API + autenticación + autorización por hogar + persistencia en SQLite, ejercitadas juntas | Casos automatizados CP-A01..CP-A05 por HTTP contra el backend real con su base de datos | Ejecutado (CI #1–#4) |
| **Sistema** | La aplicación desplegada completa: interfaz Vue, API y base de datos | 11 casos manuales por la interfaz (RUN-MAN-001); escaneo ZAP (RUN-ZAP-001/002); prueba de carga (RUN-PERF-001); protocolo de fiabilidad (RUN-REL-002) | Ejecutado |
| **Aceptación** | Cumplimiento de los criterios de aceptación de cada RF y de los objetivos RNF | Regla de RNF-01: un RF se acepta solo si todos sus subcriterios tienen una ejecución trazable y conforme; protocolos de usabilidad (RNF-02) y fiabilidad (RNF-03) | Parcial: RF evaluados con un fallo (CP-M10); RNF-02 y RNF-03 cumplidos |

**Justificación:** las pruebas unitarias upstream son la única forma de medir cobertura del código real de Mealie, porque las pruebas HTTP no instrumentan el servidor. Las pruebas de integración por API verifican de forma repetible la regla más sensible del alcance, el aislamiento entre hogares, que depende de la cooperación entre autenticación, filtros por `household_id` y persistencia. Las pruebas de sistema por la interfaz detectan fallos que la API no muestra; por ejemplo, DEF-004 solo es visible en el navegador. La aceptación la evalúa el equipo con criterios definidos antes de ejecutar, porque no hay usuarios finales disponibles.

## 4. Estrategias de prueba

| Estrategia | Aplicación | Justificación |
| --- | --- | --- |
| **Funcionales** | 11 casos manuales y 5 automatizados sobre RF-01..RF-05 | Verifican el comportamiento observable contra criterios de aceptación explícitos |
| **No funcionales** | Rendimiento con Locust (RNF-04); seguridad con SonarQube y ZAP (RNF-05); mantenibilidad con métricas de SonarQube (RNF-06); usabilidad y fiabilidad con protocolos propios (RNF-02/03) | La guía exige evaluar los seis atributos; cada uno necesita una técnica y una herramienta distintas |
| **Automatizadas** | Pytest + `requests` para CP-A01..CP-A05; CI en GitHub Actions contra un Mealie desechable | Las reglas de autorización y CRUD se deben reverificar en cada cambio; el CI las ejecuta en 77 s sin intervención |
| **Exploratorias** | Exploración no guionizada durante la ejecución manual y revisión de los logs de Mealie durante el escaneo ZAP | Encuentran comportamientos fuera de los casos diseñados: así surgieron DEF-003 (log), OBS-002 y OBS-003. No se hicieron sesiones exploratorias formales con misión y duración fijas; queda como limitación |

**Enfoque basado en riesgo:** la mayor parte del esfuerzo se dedicó a autenticación y aislamiento entre hogares (RF-01 y RF-05: 5 casos manuales y 4 automatizados), porque un fallo ahí expone datos privados de otros usuarios. RF-03 y RF-04, de menor impacto, tienen un caso cada uno.

## 5. Técnicas de diseño

| Técnica | Caso | Aplicación | Justificación |
| --- | --- | --- | --- |
| **Partición de equivalencia** | CP-M08 | Cuerpo de creación de receta: objeto con `name` de tipo string (clase válida) frente a `{}` sin `name` (clase inválida) | El esquema `CreateRecipe` exige `name: str` sin valor por defecto; todas las entradas de cada clase deben comportarse igual, así que basta un representante por clase |
| | CP-M01, CP-M02 | Credenciales válidas frente a inválidas | Dos clases con resultados opuestos (sesión frente a rechazo) |
| **Valores límite** | CP-M09 | Longitud de la contraseña nueva: 7 (L−1), 8 (L) y 9 (L+1) | El mínimo `min_length=8` está en el código; los errores de implementación se concentran en la frontera (`<` frente a `≤`) |
| | CP-M11 | Bloqueo de cuenta: intentos fallidos 4, 5 y 6 | El umbral de bloqueo es una frontera numérica; se verifica justo antes, en y después del límite |
| **Tabla de decisión** | CP-M10, CP-A04, CP-A05, CP-M06 | Acceso a una entrada del plan según dos condiciones: ¿hay sesión? y ¿el usuario es del mismo hogar? | Combinaciones de condiciones con acciones distintas (401, 404 o acceso); la tabla asegura que cada regla tenga al menos un caso |

El detalle de cada técnica, con sus clases, valores y reglas, está en `casos-de-prueba.md` §2.

## 6. Criterios

### 6.1 Entrada

- Mealie v3.25.1 en ejecución con la imagen fijada por digest y respondiendo en `/api/app/about`.
- Hogares `QA-Hogar-A` y `QA-Hogar-B` y usuarios sintéticos creados y verificados con `pruebas/preparar_datos.py`.
- Casos diseñados y revisados, con el resultado esperado escrito **antes** de ejecutar.
- Versiones de herramientas e imágenes registradas.

### 6.2 Aprobación y fallo

- **Caso:** aprobado si todos sus pasos producen el resultado esperado; fallido si algún paso no lo produce. Un error del ejecutor (por ejemplo, un clic que no llegó al botón) anula ese intento y se repite; no cuenta como resultado.
- **Requisito:** aceptado solo si todos sus subcriterios tienen al menos una ejecución trazable y conforme.
- **RNF-04:** p95 ≤ 1500 ms y respuestas inesperadas ≤ 1 %.
- **RNF-05:** cero lecturas o modificaciones no autorizadas en CP-M10, CP-A04 y CP-A05, y toda alerta alta o crítica de SonarQube o ZAP triada como confirmada, falso positivo o pendiente.
- Los umbrales no se relajan después de ver los resultados para convertir un fallo en éxito.

### 6.3 Salida

- Los 13 subcriterios funcionales ejecutados al menos una vez.
- Cada caso fallido vinculado a un defecto o a una observación.
- Evidencia de cada corrida guardada (registro, capturas, JUnit o reporte).
- Datos sintéticos eliminados al terminar: cero recetas, listas o entradas `QA-` remanentes.

### 6.4 Suspensión y reanudación

| Se suspende si | Se reanuda cuando |
| --- | --- |
| La prueba de carga degrada otros servicios del equipo | Se liberan recursos; se repite con un identificador de corrida nuevo |
| Un escaneo o un caso puede tocar datos que no son sintéticos | Se filtra el alcance (por ejemplo, las 121 operaciones excluidas del escaneo ZAP) y se restauran los datos desde la copia previa |
| Se expone una credencial o un token en una salida | Se rota la credencial, se sanean las salidas y se repite la corrida |
| Mealie deja de responder | Se recupera el contenedor sin borrar volúmenes y se repite desde el caso interrumpido |

Una corrida suspendida no se declara aprobada, y sus resultados no se recalculan retroactivamente.

## 7. Recursos

### 7.1 Humanos

| Integrante | Frente principal |
| --- | --- |
| JD | API, automatización, CI, ambiente y cobertura |
| Paula | Diseño y ejecución manual, plan de pruebas, defectos e integración editorial |
| Alejandra | Seguridad dinámica (ZAP) y OWASP |
| Sara | Rendimiento, usabilidad, fiabilidad, SonarQube y KPIs |

Los respaldos, los revisores y quién ejecutó cada corrida están en `responsabilidades.md`.

### 7.2 Herramientas

| Propósito | Herramienta y versión |
| --- | --- |
| Automatización | Python 3.14, Pytest 9.2.0, requests 2.34.2 (versiones fijadas en `pruebas/requirements.txt`) |
| Integración continua | GitHub Actions (`.github/workflows/qa-api.yml`), acciones fijadas por SHA |
| Pruebas unitarias y cobertura | Pytest 9.1.1, coverage 7.16.0, Python 3.12.16 dentro de un contenedor |
| Análisis estático | SonarQube Community Build 26.11.0.134175 y SonarScanner |
| Análisis dinámico | OWASP ZAP 2.17.0 (imagen `ghcr.io/zaproxy/zaproxy:stable`) |
| Rendimiento | Locust 2.47.0 |
| Ejecución manual | Google Chrome (versión no registrada) y la documentación interactiva de la API en `/docs` |
| Gestión de defectos | Registro Markdown versionado en Git (`defectos/registro-defectos.md`), con identificadores estables DEF-xxx |
| Contenedores | Docker Desktop 29.9.3 (backend Hyper-V) |

### 7.3 Ambientes

| Ambiente | Uso | Configuración |
| --- | --- | --- |
| Local | Casos manuales, ZAP, rendimiento y SonarQube | Windows 11 Pro; Mealie v3.25.1 con SQLite en `http://localhost:9925`, puerto publicado solo en `127.0.0.1`; VM de Docker con 5 GiB |
| CI | Casos automatizados | Runner de GitHub Actions con un servicio Mealie v3.25.1 desechable por ejecución y datos sintéticos creados en cada corrida |
| Cobertura | Pruebas unitarias upstream | Contenedor aislado con el código del tag `v3.25.1` |

## 8. Datos de prueba

- Solo datos sintéticos con prefijo `QA-` (por ejemplo `QA-RUN001-receta`), fecha de plan `2026-11-18`.
- Tres usuarios sin rol de administrador: `qa_usuario_a` y `qa_usuario_c` en el hogar A, y `qa_usuario_b` en el hogar B.
- Las contraseñas se generan al azar y se guardan solo en `.env.qa`, que Git ignora. No aparecen en documentos, capturas ni logs.
- Nunca se modifican ni se borran datos del administrador ni de otros usuarios.

## 9. Riesgos y contingencias

| Riesgo | Impacto | Contingencia aplicada |
| --- | --- | --- |
| El escaneo activo de ZAP ejecuta escrituras reales | Pérdida o alteración de datos | Especificación OpenAPI filtrada (121 de 264 operaciones excluidas), usuario sin privilegios y copia de seguridad previa restaurada al final |
| Filtración de credenciales o tokens | Acceso indebido | `.env.qa` ignorado por Git, token de administrador leído sin eco y escaneo de secretos antes de cada commit |
| Recursos limitados del equipo (5 GiB para Docker) | Mediciones distorsionadas o servicios caídos | Herramientas por fases; SonarQube detenido durante la prueba de carga; límites de memoria y CPU en los contenedores |
| Mealie es software de terceros | El equipo no puede corregir los defectos | Se registra la causa raíz y una corrección propuesta; el defecto queda Analizado y puede pasar a Reportado o Diferido |
| Disponibilidad de los integrantes | Protocolos sin ejecutar (RNF-02 exige dos participantes) | Priorizar lo que no depende de terceros y agendar la sesión de usabilidad |
| Errores en el diseño de los casos | Resultados esperados incorrectos | Las correcciones se anotan junto al resultado esperado original, sin reescribirlo (tres casos en RUN-MAN-001) |

## 10. Entregables

| Entregable | Ubicación |
| --- | --- |
| Plan de pruebas | Este documento |
| Diseño y resultados de los casos | `casos-de-prueba.md` |
| Scripts automatizados y pipeline | `pruebas/` (incluido `pruebas/fiabilidad/`) y `.github/workflows/qa-api.yml` |
| Reportes de JUnit del CI | Artefactos `junit-RUN-API-CI-<n>` de GitHub Actions |
| Registro de defectos | `defectos/registro-defectos.md` |
| Reportes de seguridad | `seguridad/reporte-zap.md` y `seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md` |
| Reporte de rendimiento | `rendimiento/reporte-rendimiento.md` |
| Reporte de fiabilidad | `fiabilidad/reporte-fiabilidad.md` |
| Reporte de mantenibilidad | `mantenibilidad/reporte-mantenibilidad.md` |
| Indicadores de calidad | `kpis.md` |
| Informe final | PDF con las 13 secciones de la guía, entregado en Teams |

## 11. Cronograma

La única fecha impuesta es la entrega del **22/11/2026 a las 23:59**. «Responsable» sigue el reparto del documento de alcance; «Ejecutado por» y las fechas reales provienen de los registros de cada corrida (horas en UTC).

| Actividad | Responsable | Fecha planificada | Fecha real | Ejecutado por | Estado |
| --- | --- | --- | --- | --- | --- |
| Alcance, requisitos, criterios y roles | Paula (RF), Sara (RNF) | 17/11 | Antes de la primera corrida | Grupo | Completo |
| Viabilidad del ambiente, cobertura y SonarQube | JD, Sara | 17/11 | 17/11 (RUN-COV-001 02:46; RUN-SONAR-SCAN-W002 20:09–20:12) | JD (asistido) | Completo |
| Diseño de casos manuales y automatizados | Paula, JD | 18/11 | 17/11 (commit 21:21) | JD (asistido) | Completo |
| Automatización de API y CI | JD | 18/11–20/11 | 17/11 (RUN-API-001 21:09; CI #1–#3 desde 22:19) | JD (asistido) | Completo |
| Escaneo ZAP y triage OWASP | Alejandra | 20/11 | 17/11 (RUN-ZAP-002 21:59–22:05) | JD (asistido) | Completo |
| Reproducción y análisis de defectos | Paula | 21/11 | 17/11 (22:06–22:11) | JD (asistido) | Completo |
| Prueba de rendimiento | Sara | 20/11 | 17/11 (RUN-PERF-001 22:24–22:27) | JD (asistido) | Completo |
| Ejecución manual | Paula | 18/11 | 17/11 22:47 – 18/11 14:10 (RUN-MAN-001) | JD (asistido) | Completo |
| KPIs y matriz de responsabilidades | Sara | 21/11 | 18/11 | JD (asistido) | Completo |
| Plan de pruebas | Paula | 17/11 | 18/11 | JD (asistido) | Completo |
| Fiabilidad (RNF-03) | Sara | 20/11 | 18/11 (RUN-REL-002 16:01–16:16; RUN-REL-001 inválida) | JD (asistido) | Completo |
| Usabilidad (RNF-02), con dos participantes | Sara | 20/11 | 18/11 (RUN-USA-001 ~18:38–~19:00) | JD (facilitador, asistido); participantes Alejandra y Paula | Completo |
| Mantenibilidad (RNF-06): trazado de dos rutas | Sara | 19/11 | 18/11 | JD (asistido) | Completo |
| Borrador integral del informe | Paula | 21/11 | — | — | Pendiente |
| Auditoría de la rúbrica y revisión del PDF | Paula, Alejandra, Sara | 22/11 antes de las 19:00 | — | — | Pendiente |
| Entrega en Teams | JD (Paula como suplente) | 22/11 antes de las 23:59 | — | — | Pendiente |

«JD (asistido)» indica ejecución con apoyo de un asistente de IA bajo su supervisión (ver `responsabilidades.md`). Las actividades técnicas se adelantaron respecto del plan porque el ambiente quedó listo antes de lo previsto.

## 12. Gestión de defectos

Cada hallazgo se registra en `defectos/registro-defectos.md` con identificador, descripción, pasos, resultado esperado y obtenido, severidad, prioridad, estado, evidencia y causa raíz. Ciclo de vida: Nuevo → Confirmado → Analizado → Reportado → Corregido → Verificado → Cerrado, con las salidas Rechazado y Diferido. Las alertas de herramientas y los hallazgos estáticos solo se convierten en defecto cuando una prueba reproduce su efecto.
