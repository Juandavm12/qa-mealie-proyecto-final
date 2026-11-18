# Reporte de usabilidad — RUN-USA-001

**Resultado: Aprobado.** Las dos participantes completaron la tarea dentro de los 5 minutos y sin errores bloqueantes.

| Campo | Valor |
| --- | --- |
| Requisito | RNF-02 Usabilidad |
| Protocolo | [`protocolo-usabilidad.md`](protocolo-usabilidad.md), con la instrucción [`instruccion-participante.md`](instruccion-participante.md) y la hoja [`hoja-registro.md`](hoja-registro.md) |
| Fecha | 2026-11-18. P1 desde ~18:38 UTC; P2 desde 18:56:39 UTC |
| Ambiente | Mealie v3.25.1 local (`localhost:9925`), Chrome 157 en Windows, sesiones presenciales |
| Facilitador | JD |
| Participantes | P1: Alejandra. P2: Paula |
| Responsable de RNF-02 | Sara |

## 1. Tarea y criterio

La persona participante inicia sesión con el usuario sintético A y debe:

1. buscar la receta `QA-USAB Lentejas guisadas`;
2. agregarla al plan de comidas del 19/11/2026;
3. agregar `Leche` a la lista de compras `QA-USAB Compras`.

**Criterio:** 2/2 participantes completan la tarea en un máximo de 5 minutos cada una, con 0 errores bloqueantes.

## 2. Resultados

| | P1 | P2 |
| --- | --- | --- |
| Experiencia previa con Mealie | Lo vio en el proyecto | Lo vio en el proyecto |
| Usa apps de recetas o listas | A veces | Nunca |
| Sesión iniciada | 00:20 | 00:20 |
| Receta encontrada y abierta | 00:30 | 00:30 |
| Receta agregada al plan | 01:00 en el primer intento; corregida hacia 02:00 (DEF-005) | 01:00 |
| Ítem agregado a la lista | 03:00 | 02:00 |
| Tiempo total | **4:30** | **3:30** |
| Errores no bloqueantes | 2 | 1 |
| Errores bloqueantes | 0 | 0 |
| Apoyo del facilitador | No hubo | No hubo |
| Estado final verificado (`verificar`) | 5/5 objetivos, 18:53:20 UTC | 5/5 objetivos, 19:11:03 UTC |
| Completó la tarea | **Sí** | **Sí** |

**Los tiempos son aproximados.** Los registró el facilitador a ojo, redondeados a 10 o 30 segundos. Como referencia exacta, Mealie registró la creación del ítem de la lista a las 18:40:40 UTC en P1 y a las 18:57:56 UTC en P2. En P2 eso equivale a 1:17 desde el inicio, frente a los 02:00 anotados en la hoja.

**Comentarios de las participantes:**
- P1: «Estuvo fácil de usar la app».
- P2: «El único error fue lo de la leche, que me cortó tiempo; de resto todo fue muy fácil de encontrar y fluido».

## 3. Errores observados

| Sesión | Qué ocurrió | Recuperación |
| --- | --- | --- |
| P1 y P2 | Al escribir «Leche» en el campo *Food*, el autocompletado no ofrece «Leche» y deja resaltado «dulce de leche» como primera opción. Si se presiona Enter, el ítem queda mal | Las dos vaciaron *Food* y escribieron «Leche» en *Note*. Registrado como **OBS-004** |
| P1 | Con *Add to Plan* desde la tarjeta de la receta, la entrada del plan quedó sin nombre, porque se guardó con un identificador de receta que no existía | Abrió la entrada en el planificador, eligió la receta correcta y guardó. Registrado como **DEF-005** |

## 4. Hallazgos

**OBS-004: «dulce de leche» desplaza a «Leche».** Es el hallazgo de usabilidad más claro, porque les pasó a las dos participantes. La base de alimentos que trae Mealie incluye «dulce de leche», pero no «leche», y el autocompletado resalta la primera coincidencia parcial. Ninguna cometió un error bloqueante, aunque a P2 le costó tiempo según su propio comentario.

**DEF-005: el plan acepta recetas inexistentes.** Se reprodujo por API, independientemente de la sesión: `POST /api/households/mealplans` con un `recipeId` inventado responde 201 y guarda una entrada sin receta. La causa está localizada en el código y se documenta en el [registro de defectos](../defectos/registro-defectos.md). Lo que no está probado es por qué la interfaz envió en P1 un identificador inexistente. La hipótesis más probable es que la pestaña venía abierta desde el piloto del ambiente y conservaba los identificadores de las recetas anteriores, que se habían borrado y recreado al preparar los datos. En P2 los identificadores no cambiaron y el problema no apareció.

## 5. Piloto del ambiente

Antes de las sesiones se recorrió la tarea completa para comprobar el ambiente. Este recorrido no cuenta como sesión ni aporta al resultado. Detectó el riesgo de «dulce de leche» y un defecto en el script de verificación, que aceptaba «dulce de leche» como «Leche». El script se corrigió y se agregaron pruebas que reproducen el caso antes de las sesiones reales.

## 6. Conclusión

RNF-02 se cumple: 2/2 participantes completaron la tarea, en 4:30 y 3:30, sin errores bloqueantes ni apoyo del facilitador. La interfaz resultó fácil de recorrer para personas que solo conocían Mealie de vista. El principal punto de fricción es el autocompletado de alimentos, que ofrece una coincidencia parcial antes que el término buscado.

## 7. Limitaciones

- Es una muestra de conveniencia de dos personas del propio grupo: no representa a la población de usuarios ni evalúa la accesibilidad.
- Las participantes conocían el proyecto, aunque no habían visto la tarea.
- La interfaz de Mealie está en inglés y la instrucción en español.
- La lista de compras se abre directamente cuando es la única del hogar. Con más listas, la tarea podría resultar más difícil.
- Los tiempos son aproximados (ver sección 2).

Los registros crudos (hojas, salidas de `verificar` y el piloto) están en `reports/usabilidad/RUN-USA-001/`, carpeta que Git ignora.
