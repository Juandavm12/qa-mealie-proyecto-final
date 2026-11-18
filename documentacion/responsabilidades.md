# Matriz de responsabilidades — Mealie v3.25.1

**Fecha de corte:** 2026-11-18.

Esta matriz separa dos cosas que no deben confundirse:

- **Responsable:** quién responde por cada frente, según el reparto acordado por el grupo.
- **Ejecutado por:** quién realizó cada corrida, según el registro de esa corrida. Es evidencia de trazabilidad y no se modifica para reflejar el reparto.

**Integrantes:** JD, Paula, Alejandra y Sara.

## 1. Frentes de trabajo

| Frente | Responsable | Respaldo / revisión | Ejecutado por | Corridas y artefactos | Estado |
| --- | --- | --- | --- | --- | --- |
| API con Pytest, cinco casos automatizados y CI | JD | Sara / Paula | JD | RUN-API-001, CI #1–#10; `pruebas/api/`, `.github/workflows/qa-api.yml` | Completo |
| Ambiente e instrumentación de cobertura | JD | Alejandra / Sara | JD | RUN-COV-001 | Completo |
| Diseño y ejecución manual | Paula | Sara / JD | JD | `casos-de-prueba.md`, RUN-MAN-001 | Completo |
| Plan de pruebas IEEE/ISO | Paula | Sara / JD | JD | `plan-de-pruebas.md` (PP-MEALIE-001) | Completo |
| Registro de defectos | Paula | Alejandra / Sara | JD | `defectos/registro-defectos.md` (DEF-001..005) | Completo |
| ZAP, OWASP, triage y mitigaciones | Alejandra | JD / Paula | JD | RUN-ZAP-001, RUN-ZAP-002; `seguridad/reporte-zap.md` | Completo |
| Rendimiento | Sara | Paula / Alejandra | JD | RUN-PERF-001; `rendimiento/reporte-rendimiento.md` | Completo |
| Usabilidad (RNF-02) | Sara | Paula / Alejandra | JD (facilitador); participantes Alejandra (P1) y Paula (P2) | RUN-USA-001; `usabilidad/reporte-usabilidad.md` | Completo |
| Fiabilidad (RNF-03) | Sara | Paula / Alejandra | JD | RUN-REL-002 (RUN-REL-001 inválida); `fiabilidad/reporte-fiabilidad.md` | Completo |
| SonarQube | Sara | Alejandra (seguridad estática), JD (cobertura) / Paula | JD | RUN-SONAR-SCAN-W002; `seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md` | Completo |
| Mantenibilidad (RNF-06) | Sara | Alejandra / Paula | JD | `mantenibilidad/reporte-mantenibilidad.md`; capturas 08–10 de RUN-SONAR-SCAN-W002 | Completo |
| KPIs | Sara | JD (cobertura), Paula (casos) / Alejandra | JD | `kpis.md` | Completo |

**RNF-02:** el diseñador de la tarea (JD) no participó; las participantes no habían visto la tarea antes de su sesión.

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
