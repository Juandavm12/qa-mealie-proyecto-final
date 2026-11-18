# Matriz de responsabilidades — Mealie v3.25.1

**Fecha de corte:** 2026-11-18.

Esta matriz separa dos cosas que no deben confundirse:

- **Responsable:** quién responde por cada frente, según el reparto acordado en el documento de alcance del grupo.
- **Ejecutado por:** quién realizó cada corrida, según el registro de esa corrida. Es evidencia de trazabilidad y no se modifica para reflejar el reparto.

**Integrantes:** JD, Paula, Alejandra y Sara. Los nombres completos figuran en la portada del informe.

**Ejecución asistida:** «JD (asistido)» indica que JD ejecutó la corrida con apoyo de un asistente de IA (Claude Code), que operó el navegador y los scripts bajo su supervisión; las contraseñas de la interfaz las escribió JD. Se declara para que la evidencia sea verificable.

## 1. Frentes de trabajo

| Frente | Responsable | Respaldo / revisión | Ejecutado por | Corridas y artefactos | Estado |
| --- | --- | --- | --- | --- | --- |
| API con Pytest, cinco casos automatizados y CI | JD | Sara / Paula | JD (asistido) | RUN-API-001, CI #1–#4; `pruebas/api/`, `.github/workflows/qa-api.yml` | Completo |
| Ambiente e instrumentación de cobertura | JD | Alejandra / Sara | JD (asistido) | RUN-COV-001 | Completo |
| Diseño y ejecución manual | Paula | Sara / JD | JD (asistido) | `casos-de-prueba.md`, RUN-MAN-001 | Completo |
| Plan de pruebas IEEE/ISO | Paula | Sara / JD | — | — | Pendiente |
| Registro de defectos | Paula | Alejandra / Sara | JD (asistido) | `defectos/registro-defectos.md` (DEF-001..004) | Completo |
| Integración editorial del informe | Paula | Alejandra / Sara | — | — | Pendiente |
| ZAP, OWASP, triage y mitigaciones | Alejandra | JD / Paula | JD (asistido) | RUN-ZAP-001, RUN-ZAP-002; `seguridad/reporte-zap.md` | Completo |
| Rendimiento | Sara | Paula / Alejandra | JD (asistido) | RUN-PERF-001; `rendimiento/reporte-rendimiento.md` | Completo |
| Usabilidad (RNF-02) | Sara | Paula / Alejandra | — | — | Pendiente |
| Fiabilidad (RNF-03) | Sara | Paula / Alejandra | JD (asistido) | RUN-REL-002 (RUN-REL-001 inválida); `fiabilidad/reporte-fiabilidad.md` | Completo |
| SonarQube | Sara | Alejandra (seguridad estática), JD (cobertura) / Paula | JD (asistido) | RUN-SONAR-SCAN-W002; `seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md` | Completo |
| Mantenibilidad (RNF-06) | Sara | Alejandra / Paula | — | Métricas de SonarQube disponibles; falta trazar dos rutas del alcance | Parcial |
| KPIs | Sara | JD (cobertura), Paula (casos) / Alejandra | JD (asistido) | `kpis.md` | Completo |
| Entrega en Teams | JD | Paula como suplente / Alejandra y Sara | — | — | Pendiente |

**Restricción de RNF-02:** el protocolo de usabilidad exige dos participantes del grupo distintos del diseñador de la tarea. No puede ejecutarlo una sola persona.

## 2. Secciones del informe

El responsable integra la sección; quien produjo cada resultado conserva la responsabilidad por sus datos.

| # | Sección | Integra | Aportes / revisión |
| --- | --- | --- | --- |
| 1 | Portada | Paula | Nombres confirmados / Alejandra |
| 2 | Introducción | Paula | Justificación del equipo / Sara |
| 3 | Contexto del proyecto | JD | Alcance y arquitectura verificable / Alejandra |
| 4 | Requerimientos y criterios de calidad | Paula | Sara (RNF), Alejandra (permisos) / JD |
| 5 | Plan de pruebas | Paula | Recursos y estrategia de cada frente / Sara |
| 6 | Diseño de casos de prueba | Paula | JD (automatizados), Alejandra (seguridad) / Sara |
| 7 | Ejecución y evidencias | Sara | Cada ejecutor redacta sus resultados / Alejandra |
| 8 | Automatización de pruebas | JD | Sara (instrumentación) / Paula |
| 9 | Gestión de defectos | Paula | Alejandra (triage) y cada descubridor / Sara |
| 10 | Pruebas de seguridad | Alejandra | Sara (SonarQube) / JD |
| 11 | Métricas de calidad | Sara | JD (cobertura), Paula (casos) / Alejandra |
| 12 | Reflexión y lecciones aprendidas | Alejandra | Relato propio de los cuatro / Paula |
| 13 | Anexos | Sara | Cada responsable entrega sus artefactos saneados / JD |

La aceptación individual de estos roles sigue pendiente de confirmación por cada integrante.
