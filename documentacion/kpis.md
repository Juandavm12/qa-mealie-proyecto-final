# Indicadores de calidad (KPIs) — Mealie v3.25.1

**Fecha de corte:** 2026-11-18. Cada valor se calcula sobre corridas identificadas y enlaza su evidencia. Un dato que no se midió figura como «no medido» o «no calculable», nunca como cero.

## 1. Corridas que alimentan los indicadores

| Corrida | Qué ejecutó | Fecha (UTC) | Evidencia |
| --- | --- | --- | --- |
| RUN-MAN-001 | 11 casos manuales CP-M01..CP-M11 | 2026-11-17 22:47–~23:05 y 2026-11-18 14:00–14:10 | `casos-de-prueba.md` §3; registro y capturas en `reports/manual/RUN-MAN-001/` (fuera de Git) |
| CI #4 | 5 casos automatizados CP-A01..CP-A05 y 48 pruebas unitarias de las herramientas propias, contra un Mealie v3.25.1 desechable | 2026-11-18 14:15:15–14:16:32 | [Ejecución 44322226993](https://github.com/Juandavm12/qa-mealie-proyecto-final/actions/runs/44322226993), artefacto JUnit `junit-RUN-API-CI-4` |
| RUN-COV-001 | 58 pruebas unitarias upstream de Mealie con instrumentación `coverage` | 2026-11-17 | `viabilidad_cobertura/evidencias/RUN-COV-001/` (fuera del repositorio público) |
| RUN-SONAR-SCAN-W002 | Análisis SonarQube del backend Python | 2026-11-17 20:09:56–20:12:41 | `seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md`; capturas en `viabilidad_cobertura/evidencias/RUN-SONAR-SCAN-W002/capturas/` |
| RUN-ZAP-002 | Escaneo activo ZAP de la API autenticada | 2026-11-17 21:59:14–22:05:56 | `seguridad/reporte-zap.md` |
| RUN-PERF-001 | Prueba de carga RNF-04 con Locust | 2026-11-17 22:24:55–22:27:28 | `rendimiento/reporte-rendimiento.md` |
| RUN-REL-002 | Protocolo de fiabilidad RNF-03: 10 ciclos durante 15 min | 2026-11-18 16:01:28–16:16:29 | `fiabilidad/reporte-fiabilidad.md` |

## 2. Resumen

| Indicador | Valor | Lectura rápida |
| --- | --- | --- |
| Cobertura de requisitos funcionales | **13/13 subcriterios (100 %)**; 5/5 RF | Todo el alcance funcional se ejecutó al menos una vez |
| Subcriterios con todas sus ejecuciones conformes | **12/13 (92,3 %)** | RF-05.C1 tiene un fallo identificado (CP-M10) |
| Casos aprobados / fallidos | **15 / 1** de 16 (93,75 % / 6,25 %) | Manuales 10/1; automatizados 5/0 |
| Tasa de fallos de pruebas | **6,25 %** (1/16) | Un caso fallido, CP-M10 |
| Tasa de defectos por caso ejecutado | **6,25 %** (1/16) | Un defecto único detectado por los casos: DEF-004 |
| Defectos confirmados (todas las fuentes) | **4**, todos de severidad Menor | 1 por prueba manual, 3 por ZAP y su log |
| Densidad de defectos (backend) | **≈ 0,11 defectos/KLOC** (3 / ≈ 28 KLOC) | Frontend: no calculable |
| Cobertura de código (backend) | **44,3 %** en SonarQube; líneas 52,0 %, ramas 8,9 % | Frontend: no medida |
| Tiempo de ejecución automatizada | **2,11 s** la suite; **77 s** el job de CI completo | Incluye arrancar Mealie y preparar datos |
| Rendimiento (RNF-04) | **p95 = 30 ms**, 0 % de errores | Umbral: p95 ≤ 1500 ms y ≤ 1 % |
| Fiabilidad (RNF-03) | **10/10 ciclos** conformes y 10/10 con sus datos intactos a los 15 min | 0 errores inesperados en 70 peticiones |

## 3. Detalle e interpretación

### 3.1 Cobertura de requisitos

**Cálculo:** subcriterios ejecutados / subcriterios cerrados del alcance (`Alcance_requisitos_y_responsabilidades.md` §3). Un RF cuenta como ejecutado solo si se ejercitaron todos sus subcriterios.

| RF | Subcriterios | Ejecutados por | Todas las ejecuciones conformes |
| --- | --- | --- | --- |
| RF-01 Autenticación | C1, C2, C3 | CP-M01, CP-M02, CP-M09, CP-M11; CP-A01, CP-A02 | 3/3 |
| RF-02 Recetas | C1, C2, C3, C4 | CP-M03, CP-M04, CP-M05, CP-M08; CP-A03 | 4/4 |
| RF-03 Plan de comidas | C1, C2 | CP-M06 | 2/2 |
| RF-04 Listas de compras | C1, C2 | CP-M07 | 2/2 |
| RF-05 Protección del plan | C1, C2 | CP-M10; CP-A04, CP-A05 | 1/2 (C1: CP-M10 falló; CP-A04 aprobó) |
| **Total** | **13** | **13 ejecutados, 0 pendientes** | **12/13** |

**Interpretación:** el alcance funcional quedó cubierto por completo, pero no se declara aceptación total, porque RF-05.C1 tiene un fallo identificado. El fallo es de navegación (DEF-004: la página del planificador no redirige al login) y no de exposición de datos: la API respondió 401 en CP-M10 y en CP-A04. Esta cobertura mide requisitos ejercitados, no porcentaje de aprobación ni cobertura de código.

**Requisitos no funcionales:** RNF-01, RNF-03, RNF-04, RNF-05 y RNF-06 tienen evaluación ejecutada (5/6). **RNF-02 (usabilidad) sigue pendiente.**

### 3.2 Casos aprobados y fallidos

| Conjunto | Ejecutados | Aprobados | Fallidos | % aprobación |
| --- | --- | --- | --- | --- |
| Manuales (RUN-MAN-001) | 11 | 10 | 1 (CP-M10) | 90,9 % |
| Automatizados contra Mealie (CI #4) | 5 | 5 | 0 | 100 % |
| **Casos de prueba de Mealie** | **16** | **15** | **1** | **93,75 %** |
| Pruebas unitarias de las herramientas propias (CI #4) | 48 | 48 | 0 | 100 % |

- CP-M05 se aprobó con una observación de usabilidad (OBS-002); cuenta como aprobado porque cumplió su resultado esperado.
- Las 48 pruebas unitarias verifican los scripts del grupo (preparación de datos, ZAP y rendimiento), no el comportamiento de Mealie, por lo que **no se suman** a los casos de prueba. CI #4 reportó `53 passed` en total (5 + 48).
- En RUN-MAN-001 se corrigieron tres errores de diseño (ruta de la receta en CP-M03, oráculo de búsqueda en CP-M08 y mensaje 401 en CP-M10). Los resultados esperados originales se conservan junto a cada corrección; ningún caso cambió de estado por esas correcciones.

### 3.3 Tasa de fallos y tasa de defectos

- **Tasa de fallos de pruebas** = casos fallidos / casos ejecutados = 1/16 = **6,25 %**.
- **Tasa de defectos** = defectos únicos confirmados que detectaron los casos de prueba / casos ejecutados = 1/16 = **6,25 %**. Coincide con la tasa de fallos solo porque el único caso fallido produjo un único defecto; son indicadores distintos.

**Defectos por fuente y severidad** (`defectos/registro-defectos.md`):

| Fuente | Defectos | Severidad |
| --- | --- | --- |
| Prueba manual (CP-M10) | DEF-004 | Menor |
| Escaneo ZAP (RUN-ZAP-002) | DEF-001, DEF-002 | Menor |
| Log de Mealie durante RUN-ZAP-002 | DEF-003 | Menor |
| **Total** | **4** | 0 críticos, 0 mayores, 4 menores, 0 triviales |

Las alertas de ZAP, los hallazgos de SonarQube y las observaciones de usabilidad (OBS-001..003) **no se cuentan como defectos**: solo entra un hallazgo reproducido de forma independiente y con causa localizada. Para la clasificación de la guía (Crítico, Alto, Medio, Bajo) se usa la equivalencia Crítica → Crítico, Mayor → Alto, Menor → Medio, Trivial → Bajo.

### 3.4 Densidad de defectos

**Cálculo:** defectos confirmados del componente / KLOC del mismo componente.

- **Backend:** DEF-001, DEF-002 y DEF-003 / ≈ 28 KLOC → **≈ 0,11 defectos por KLOC**. El tamaño es el valor «28k Lines of code» del dashboard de SonarQube (RUN-SONAR-SCAN-W002, `**/*.py`), que está redondeado a miles.
- **Frontend:** DEF-004 pertenece al frontend Vue, cuyas líneas no se midieron. Su densidad es **no calculable**.

Una densidad baja con 16 casos y un escaneo acotado no indica un código casi libre de defectos: indica que el esfuerzo de prueba cubrió una parte pequeña del backend.

### 3.5 Cobertura de código

| Medida | Valor | Fuente |
| --- | --- | --- |
| Cobertura SonarQube (líneas y condiciones combinadas) | **44,3 %** sobre 20 k líneas por cubrir | Dashboard W002 |
| Líneas cubiertas | 52,0 % (10 357 / 19 928) | `RUN-COV-001/coverage.xml` |
| Ramas cubiertas | 8,9 % (363 / 4074) | `RUN-COV-001/coverage.xml` |

**Cómo se midió:** `coverage run -m pytest` sobre dos archivos de pruebas unitarias upstream de Mealie (`tests/unit_tests/services_tests/scraper_tests/test_cleaner.py` y `tests/unit_tests/ingredient_parser/test_unit_utils.py`), con `source = mealie`: 58 pruebas aprobadas en 22,65 s, Python 3.12.16, coverage 7.16.0. El reporte XML se importó a SonarQube.

**Interpretación:**
- Es cobertura **solo del backend**; el frontend no tiene cobertura medida.
- Las pruebas HTTP del grupo (CP-A01..A05) ejercitan el servidor desde fuera y no están instrumentadas, así que no aportan a este número.
- La diferencia entre 52 % de líneas y 8,9 % de ramas sugiere que buena parte de las líneas cubiertas son definiciones que se ejecutan al importar los módulos, no lógica recorrida por las pruebas. Es una interpretación del dato, no una medición separada.
- No se fijó un objetivo de cobertura (por ejemplo 80 %), porque no existía una línea base acordada.

### 3.6 Tiempo de ejecución

| Corrida | Duración | Observación |
| --- | --- | --- |
| Suite Pytest en CI #4 (53 pruebas) | 2,11 s | Solo la ejecución de pytest |
| Job completo de CI #4 | 77 s | Incluye levantar Mealie, esperar que esté sano y crear los usuarios sintéticos |
| RUN-COV-001 (58 pruebas instrumentadas) | 22,65 s | Dentro del contenedor de cobertura |
| RUN-SONAR-SCAN-W002 | 2 min 45 s | Desde el arranque del scanner hasta su salida |
| RUN-ZAP-002 | 6 min 42 s | Escaneo activo de 143 operaciones |
| RUN-REL-002 | 15 min 1 s | 10 ciclos espaciados 90 s y verificación final a los 900 s; la duración la fija el protocolo |
| RUN-PERF-001 | 2 min 33 s | 30 s de calentamiento, 120 s de medición, preparación y limpieza |
| RUN-MAN-001 | ≈ 28 min en dos sesiones | 22:47–~23:05 UTC del 17/11 y 14:00–14:10 UTC del 18/11 |

La suite automatizada tarda segundos y el job completo de CI poco más de un minuto, mientras que los 11 casos manuales tomaron cerca de media hora, sin contar la espera entre sesiones. Los conjuntos no son idénticos (5 casos automatizados frente a 11 manuales), por lo que la comparación es orientativa.

### 3.7 Métricas de SonarQube (RUN-SONAR-SCAN-W002)

SonarQube Community Build 26.11.0.134175, modo Standard Experience, backend Python de Mealie v3.25.1 (commit `cce7601e`). Pestaña **Overall Code** (captura `03-dashboard-overall-standard-experience.png`).

| Métrica | Valor | Rating | Interpretación técnica |
| --- | --- | --- | --- |
| Bugs | 6 | Reliability **C** | 3 tareas `asyncio` creadas sin referencia (pueden terminar antes de tiempo) y 3 `open()` síncronos dentro de funciones `async`, estos últimos en el módulo de IA, fuera del alcance. No se reprodujeron como fallos funcionales |
| Vulnerabilidades | 6 | Security **E** | 1 Blocker (SEG-001: la aplicación escucha en todas las interfaces), no explotable en el despliegue evaluado porque el puerto solo se publica en `127.0.0.1`; 5 usos de PRNG no criptográfico, todos falsos positivos justificados |
| Code Smells | 10 (4 Blocker, 1 Critical, 5 Major) | Maintainability **A** | Deuda de 1 h 49 min para ≈ 28 KLOC; dos ejemplos analizados en `mantenibilidad/reporte-mantenibilidad.md` |
| Duplicación | 0,6 % sobre 39 k líneas | — | Prácticamente sin código duplicado |
| Coverage | 44,3 % | — | Ver §3.5 |
| Security Hotspots | 0 | **A** | Ningún punto sensible pendiente de revisión |
| Quality Gate | Passed | — | El gate por defecto evalúa solo el *New Code*; al ser el primer análisis no hay código nuevo, por eso aprueba aunque el Security Rating sea E |

**Lectura:** el Security Rating E proviene de una sola regla Blocker cuyo riesgo depende del despliegue; una vez triada, no queda ninguna vulnerabilidad explotable confirmada en el análisis estático. La mantenibilidad es el atributo mejor evaluado. El análisis cubre solo Python: el frontend no se analizó.

### 3.8 Seguridad dinámica, rendimiento y fiabilidad

- **ZAP (RUN-ZAP-002):** 0 alertas de riesgo alto, 9 advertencias (WARN) y 113 reglas superadas sobre 464 URL. Las alertas confirmadas de riesgo medio (sin Content Security Policy y sin cabecera anti-clickjacking) corresponden a A02:2025 Security Misconfiguration. Además, el escaneo reveló 2 defectos funcionales (DEF-001, DEF-002) y, en el log, un tercero (DEF-003).
- **Rendimiento (RUN-PERF-001):** 591 peticiones medidas con 5 usuarios durante 120 s; p50 14 ms, p95 30 ms, p99 55 ms, 0 fallos. RNF-04 se cumple con un margen de ~50× sobre el umbral de 1500 ms, en una medición local por loopback que no se extrapola a producción.
- **Fiabilidad (RUN-REL-002):** 10 ciclos crear → consultar → editar → planificar → consultar, uno cada 90 s; los 10 fueron conformes y, a los 900 s, las 10 recetas y entradas seguían intactas. RNF-03 se cumple. No se probaron caídas, reinicios ni concurrencia. La corrida RUN-REL-001 quedó inválida por un defecto del script y se conserva sin recalificar.

## 4. Conclusiones

- **Respaldado por evidencia:** el alcance funcional se ejecutó completo (13/13 subcriterios) con 93,75 % de casos aprobados; RNF-04 se cumple con holgura; RNF-03 se cumple con 10/10 ciclos sin pérdida de datos; no hay alertas de riesgo alto ni vulnerabilidades estáticas explotables confirmadas.
- **Falló:** CP-M10, por DEF-004. El planificador sin sesión muestra una pantalla vacía en lugar del login, sin exponer datos.
- **No se puede concluir:** la cobertura de código del frontend, la densidad de defectos del frontend, ni la usabilidad (RNF-02), que necesita dos participantes del grupo.
- **Riesgo principal:** 4 defectos menores en manejo de errores y navegación, tres de ellos en respuestas de error de la API (500 o detalles internos en lugar de 404 o 409). Son baratos de corregir y no comprometen datos.
