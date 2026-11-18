# Prueba de fiabilidad RNF-03 — RUN-REL-002

**Fecha:** 2026-11-18, 16:01:28–16:16:29 UTC. **Herramienta:** script propio `pruebas/fiabilidad/ejecutar_fiabilidad.py` (Python 3.14, requests). **Objetivo:** Mealie v3.25.1 local (imagen `sha256:6066c29e…`, SQLite), `http://127.0.0.1:9925`, como `qa_usuario_a`. **Resultado: Aprobado.**

## 1. Criterios (congelados antes de la corrida)

Tomados de RNF-03 en el documento de alcance del grupo, sección 5. Son objetivos propios de esta evaluación local, no una garantía de disponibilidad de Mealie.

| Elemento | Valor |
| --- | --- |
| Ciclo | Crear receta → consultarla → editar su nombre → asociarla al plan de comidas → volver a consultarla |
| Datos | Nuevos en cada ciclo: receta `QA-RUN-REL-002-NN`, renombrada a `QA-RUN-REL-002-NN-editada`, y entrada `dinner` en la fecha `2026-12-NN` |
| Repeticiones | 10 ciclos secuenciales, uno cada 90 s |
| Observación | Al menos 15 min; a los 900 s se vuelven a leer la receta y la entrada de todos los ciclos |
| Umbral | 10/10 ciclos conformes, 10/10 ciclos con sus datos intactos en la verificación final y cero errores inesperados |

Un paso es conforme si devuelve el código esperado (201 al crear o planificar, 200 al consultar o editar) y el dato leído coincide con el escrito: el nombre tras crear, el nombre editado tras editar, y la fecha y el ID de receta en la entrada del plan. Una excepción de red cuenta como error inesperado. Un ciclo abortado o una observación menor a 15 min invalidan la corrida.

## 2. Resultados

| Métrica | Valor | Umbral | Cumple |
| --- | --- | --- | --- |
| Ciclos conformes | **10/10** | 10/10 | Sí |
| Ciclos con datos intactos a los 900 s | **10/10** | 10/10 | Sí |
| Errores inesperados | **0** de 70 peticiones de prueba | 0 | Sí |
| Duración de la observación | 900,7 s | ≥ 900 s | Sí |

Todos los pasos devolvieron el código esperado: `crear=201 consultar=200 editar=200 planificar=201 consultar_final=200` en los 10 ciclos, que empezaron en t = 0,1 s, 90,1 s, …, 810,1 s. La verificación final, a los 900,4 s, encontró las 10 recetas con su nombre editado y las 10 entradas del plan con su fecha y receta. El primer ciclo quedó expuesto a 15 minutos de actividad posterior sin perder datos.

**Limpieza:** se borraron las 10 entradas y las 10 recetas (20 respuestas 200), y la búsqueda posterior del prefijo devolvió 0 recetas. No apareció ningún token en las salidas.

## 3. Corridas anteriores

| Corrida | Resultado | Causa |
| --- | --- | --- |
| RUN-REL-001 | **Inválida**, abortada antes del primer ciclo | Defecto del script: la primera espera calculaba unos microsegundos negativos y `time.sleep` los rechaza (`ValueError`). No se creó ningún dato |

La corrección agrega una espera que no acepta tiempos negativos y una prueba unitaria con un reloj falso que, igual que `time.sleep`, rechaza esperas negativas. RUN-REL-001 se conserva y no se recalifica.

**Robustez agregada después de RUN-REL-002.** Una verificación independiente del script, realizada después de la corrida, encontró dos defectos en el camino de error, que RUN-REL-002 no recorrió:
- si una excepción interrumpía un ciclo a la mitad, la receta de ese ciclo no se limpiaba;
- una corrida abortada terminaba con código 1, que significa «Fallido», en lugar de «Inválido» (código 2), y sin `resultado.json`.

Se corrigieron con pruebas que reproducen cada caso: el script tiene 22 pruebas unitarias. Los cambios solo afectan al aborto y a la limpieza; los pasos y las comprobaciones de un ciclo normal son idénticos, por lo que el resultado de RUN-REL-002 sigue siendo válido. Antes de RUN-REL-002 se ejecutó una prueba de humo de un ciclo (`QA-RUN-REL-SMOKE`), limpiada después, para confirmar los nombres de los campos de la API; no cuenta como resultado.

## 4. Ambiente

- Windows 11 Pro, Docker Desktop 29.9.3 con backend Hyper-V; el contenedor de Mealie llevaba 18 h en ejecución y estaba sano.
- Cliente y servidor en el mismo equipo, por loopback.
- Durante la corrida no se ejecutó ninguna otra prueba contra Mealie.

## 5. Interpretación y límites

- Durante 15 minutos de uso secuencial, Mealie conservó todas las escrituras y respondió sin errores. RNF-03 se cumple.
- Mide la persistencia y la consistencia de lecturas tras escrituras en condiciones normales. **No** prueba caídas, reinicios, cortes de energía, concurrencia, recuperación ante desastres ni disponibilidad a largo plazo, que quedan fuera del alcance.
- Se ejecutó por API, no por la interfaz. «Recargar» equivale aquí a una nueva lectura independiente del recurso.
- Una sola corrida con volumen pequeño (10 recetas): no se extrapola a producción.

## 6. Reproducción

```bash
python pruebas/fiabilidad/ejecutar_fiabilidad.py --run-id RUN-REL-003 --execute
```

Requiere las credenciales sintéticas de `.env.qa` (ver `pruebas/preparar_datos.py`) y el contenedor de Mealie con la imagen fijada. Sin `--execute` solo muestra el plan. Las salidas (`registro.log` y `resultado.json`, con los códigos de cada paso y los IDs sintéticos) se guardan en `reports/fiabilidad/<run-id>/`, carpeta ignorada por Git.
