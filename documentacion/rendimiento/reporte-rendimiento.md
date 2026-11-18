# Prueba de rendimiento RNF-04 — RUN-PERF-001

**Fecha:** 2026-11-17, 22:24:55–22:27:28 UTC. **Herramienta:** Locust 2.47.0 (Python 3.14.7). **Objetivo:** Mealie v3.25.1 local (imagen `sha256:6066c29e…`, SQLite), `http://127.0.0.1:9925`. **Resultado: Aprobado.**

## 1. Criterios (congelados antes de la primera corrida)

Tomados de RNF-04, según los criterios definidos por el grupo. Son objetivos propios de esta evaluación local, no un SLA de Mealie.

| Elemento | Valor |
| --- | --- |
| Operación medida | Lectura autenticada del listado de recetas: `GET /api/recipes?search=<prefijo>&perPage=50` |
| Datos | 20 recetas sintéticas `QA-RUN-PERF-001-01..20`, creadas antes de medir y eliminadas al final |
| Perfil | 1 usuario virtual durante 30 s de calentamiento (estadísticas reiniciadas al terminar), luego 5 usuarios durante 120 s, con 1 s de pausa entre peticiones por usuario |
| Umbrales | p95 ≤ 1500 ms y tasa de respuestas inesperadas ≤ 1 % |

Una respuesta cuenta como inesperada si no es 200 o si el listado no contiene exactamente 20 recetas. La preparación y la limpieza usan un cliente HTTP aparte, fuera de las estadísticas.

## 2. Resultados

| Métrica | Valor | Umbral | Cumple |
| --- | --- | --- | --- |
| Peticiones medidas | 591 | — | — |
| Fallos | 0 (0,00 %) | ≤ 1 % | Sí |
| p50 | 14 ms | — | — |
| p95 | **30 ms** | ≤ 1500 ms | Sí |
| p99 | 55 ms | — | — |
| Máximo | 190 ms | — | — |
| Rendimiento | 4,90 peticiones/s | — | — |

**Control del calentamiento:** con 5 usuarios, 120 s y 1 s de pausa más ~15 ms de respuesta se esperan 5 × 120 / 1,015 ≈ 591 peticiones; se midieron exactamente 591. Las peticiones del calentamiento no entraron en la medición.

**Recursos del contenedor de Mealie** (25 muestras de `docker stats` cada 5 s): CPU media 4,7 %, máxima 8,5 %; memoria entre 276 y 282 MiB de un límite de 1000 MiB.

## 3. Ambiente

- Windows 11 Pro, Docker Desktop 29.9.3 con backend Hyper-V; VM de Docker con 5 GiB.
- Locust corrió en el mismo equipo que Mealie, por loopback: la medición no incluye red real.
- Servicios concurrentes durante la corrida: solo Mealie. SonarQube estaba detenido y los contenedores de otros proyectos también.

## 4. Interpretación y límites

- Con 5 usuarios y 20 recetas, Mealie responde con un margen de ~50× sobre el umbral (p95 30 ms frente a 1500 ms) y apenas usa CPU. El objetivo de RNF-04 se cumple con holgura.
- Es una medición de API desde el cliente, no del tiempo de renderizado de la interfaz.
- Una sola corrida con carga baja y un volumen de datos pequeño: no se extrapola a producción, a más usuarios ni a bases de datos grandes, ni se compara SQLite con PostgreSQL.
- El cliente y el servidor compartían CPU, lo que puede afectar ligeramente los tiempos medidos.

## 5. Reproducción

```bash
python -m pip install -r pruebas/rendimiento/requirements.txt
python pruebas/rendimiento/ejecutar_rendimiento.py --run-id RUN-PERF-002 --execute
```

Requiere las credenciales sintéticas de `.env.qa` (ver `pruebas/preparar_datos.py`). Los resultados crudos (`resultado.json`, CSV de Locust, `reporte.html`, `recursos.csv`) se guardan en `reports/rendimiento/<run-id>/`, carpeta ignorada por Git. En RUN-PERF-001 no apareció ningún token en esas salidas (`token_absent_from_outputs: true`).
