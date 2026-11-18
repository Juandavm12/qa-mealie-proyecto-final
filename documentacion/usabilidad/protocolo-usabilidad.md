# Protocolo de usabilidad RNF-02 — RUN-USA-001

Prueba simple de usabilidad: dos integrantes del grupo realizan una tarea corta en la interfaz de Mealie mientras el facilitador observa y registra lo que ocurre.

## 1. Tarea y criterio

**Tarea:** iniciar sesión, localizar una receta sintética, agregarla al plan de comidas de una fecha y agregar un ítem a una lista de compras.

**Criterio:** 2/2 participantes completan la tarea en un máximo de 5 minutos cada una, con 0 errores bloqueantes.

## 2. Roles

| Rol | Quién |
| --- | --- |
| Responsable de RNF-02 | Sara |
| Diseñador de la tarea y facilitador | JD |
| Participantes P1 y P2 | Dos integrantes entre Paula, Alejandra y Sara que no hayan visto la tarea antes |

P1 es la primera persona que hace la prueba y P2 la segunda. La integrante restante queda como reserva si una sesión resulta inválida.

## 3. Ambiente

- Mealie v3.25.1 local en la computadora del facilitador, la misma imagen fijada del resto de las corridas.
- Sesión presencial, o remota con pantalla compartida y control cedido. La modalidad se anota en la hoja.
- La instancia no se expone a internet.
- Navegador abierto en la página de inicio de sesión, sin sesión iniciada y sin contraseñas guardadas.

## 4. Datos de la sesión

Todos los datos son sintéticos, con prefijo `QA-USAB`, y pertenecen al hogar del usuario sintético A.

| Dato | Valor |
| --- | --- |
| Usuario | Usuario sintético A de `.env.qa`. El facilitador entrega el correo y la contraseña al empezar; no se escriben en la hoja |
| Receta a localizar | `QA-USAB Lentejas guisadas` |
| Recetas distractoras | `QA-USAB Lentejas con arroz` y `QA-USAB Sopa de verduras` |
| Lista de compras | `QA-USAB Compras`, creada y vacía |
| Ítem a agregar | `Leche`. Vale como nota o como alimento; crear el alimento «Leche» desde el campo *Food* es un camino válido |
| Fecha del plan | El día siguiente a la sesión |

El script `pruebas/usabilidad/preparar_usabilidad.py` gestiona estos datos, solo con el prefijo `QA-USAB` y solo contra una instancia local:

| Momento | Comando | Efecto |
| --- | --- | --- |
| Antes de cada sesión | `python pruebas/usabilidad/preparar_usabilidad.py preparar` | Deja el estado inicial e imprime la fecha que se escribe en la instrucción |
| Al terminar cada sesión | `python pruebas/usabilidad/preparar_usabilidad.py verificar` | Comprueba el estado final sin modificar nada |
| Al terminar ambas sesiones | `python pruebas/usabilidad/preparar_usabilidad.py limpiar` | Borra todos los datos `QA-USAB` |

## 5. Desarrollo de cada sesión

1. Anotar la experiencia previa de la persona participante (sección 2 de la hoja).
2. Entregar la instrucción escrita (`instruccion-participante.md`) con la fecha completada.
3. Cronometrar desde «empiezo» hasta «terminé», con un máximo de 5:00.
4. Observar y anotar tiempos, errores y cualquier apoyo que dé el facilitador.
5. Verificar el estado final con `verificar` y completar la hoja.
6. La persona participante revisa la hoja y confirma que refleja lo ocurrido.

## 6. Definiciones

| Término | Definición |
| --- | --- |
| Completó la tarea | Los cuatro pasos quedaron verificados en el estado final dentro de 5:00 |
| Error | Acción que se aparta del camino hacia el objetivo y se corrige durante la tarea (por ejemplo, abrir la receta equivocada) |
| Error bloqueante | Error que impide terminar la tarea dentro de 5:00 o que deja un estado final incorrecto (por ejemplo, agregar «dulce de leche» en lugar de «Leche») |

## 7. Evaluación

| Resultado | Condición |
| --- | --- |
| **Aprobado** | 2/2 participantes completan la tarea y hay 0 errores bloqueantes |
| **Fallido** | Al menos una persona participante no completa la tarea o comete un error bloqueante |
| **Inválida** (sesión) | Falla técnica ajena a la interfaz (Mealie caído, corte de la llamada). Se repite con la integrante de reserva |

## 8. Entregables

| Entregable | Quién lo produce |
| --- | --- |
| Hoja de registro completada por participante (`hoja-registro.md`), identificada como P1 o P2 | Facilitador |
| Confirmación de cada participante de que su hoja es correcta | Cada participante |
| Reporte de usabilidad con el resultado de RUN-USA-001 | Facilitador, revisado por Sara |

Los registros crudos quedan en `reports/usabilidad/RUN-USA-001/`, que Git ignora. Solo se publica el reporte saneado.

## 9. Limitaciones

Es una muestra de conveniencia de dos personas del propio grupo: no representa a la población de usuarios ni evalúa la accesibilidad. Las participantes conocen el proyecto, y esa experiencia se registra. La interfaz de Mealie está en inglés y la instrucción en español.
