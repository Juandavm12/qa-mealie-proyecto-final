# QA de Mealie — proyecto final

Proyecto académico de Aseguramiento de Calidad del Software sobre **Mealie v3.25.1**,
una aplicación de recetas, planificación de comidas y listas de compras. El
repositorio reúne los casos de prueba, la automatización, el CI y los reportes de
la evaluación, con trazabilidad entre requisitos, casos, corridas, hallazgos y
conclusiones.

## Estado

**Fecha de corte:** 2026-11-18.

| Frente | Estado | Resultado principal |
| --- | --- | --- |
| Plan de pruebas | Completo | [PP-MEALIE-001](documentacion/plan-de-pruebas.md), basado en ISO/IEC/IEEE 29119-3 |
| Diseño de casos | Completo | 11 casos manuales y 5 automatizados; partición de equivalencia, valores límite y tabla de decisión |
| Ejecución manual | Completo (RUN-MAN-001) | 10 de 11 aprobados; CP-M10 fallido (DEF-004) |
| Automatización y CI | Completo | CP-A01..CP-A05 en GitHub Actions contra un Mealie desechable: 5/5 |
| Seguridad estática | Completo (RUN-SONAR-SCAN-W002) | 6 vulnerabilidades triadas; ninguna explotable confirmada en el despliegue evaluado |
| Seguridad dinámica | Completo (RUN-ZAP-001/002) | 0 alertas de riesgo alto; 3 defectos detectados: DEF-001 y DEF-002 por el escaneo y DEF-003 en el log de Mealie |
| Rendimiento (RNF-04) | Completo (RUN-PERF-001) | p95 de 30 ms frente a un umbral de 1500 ms; 0 % de errores |
| Defectos | Completo | DEF-001..DEF-005, todos de severidad Menor, con ciclo de vida y causa raíz |
| KPIs | Completo | Cobertura de requisitos 13/13; 15 de 16 casos aprobados |
| Fiabilidad (RNF-03) | Completo (RUN-REL-002) | 10/10 ciclos con sus datos intactos durante 15 min |
| Mantenibilidad (RNF-06) | Completo | Rating A con 10 code smells; validación repartida en 5 capas y autorización centralizada en el repositorio genérico |
| Usabilidad (RNF-02) | Completo (RUN-USA-001) | 2/2 participantes completaron la tarea, en 4:30 y 3:30, sin errores bloqueantes |

## Documentación

| Documento | Contenido |
| --- | --- |
| [`documentacion/plan-de-pruebas.md`](documentacion/plan-de-pruebas.md) | Plan de pruebas basado en ISO/IEC/IEEE 29119-3: objetivos, niveles, estrategias, técnicas, criterios, recursos, riesgos y cronograma |
| [`documentacion/casos-de-prueba.md`](documentacion/casos-de-prueba.md) | Ambiente, técnicas de diseño, casos manuales y automatizados con resultado obtenido, y trazabilidad |
| [`documentacion/defectos/registro-defectos.md`](documentacion/defectos/registro-defectos.md) | Ciclo de vida, defectos DEF-001..DEF-005 y observaciones |
| [`documentacion/seguridad/reporte-zap.md`](documentacion/seguridad/reporte-zap.md) | Escaneos ZAP y correspondencia con OWASP Top 10:2025 |
| [`documentacion/seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md`](documentacion/seguridad/triage-sonar-RUN-SONAR-SCAN-W002.md) | Triage de vulnerabilidades y bugs de SonarQube |
| [`documentacion/rendimiento/reporte-rendimiento.md`](documentacion/rendimiento/reporte-rendimiento.md) | Prueba de carga RUN-PERF-001 |
| [`documentacion/fiabilidad/reporte-fiabilidad.md`](documentacion/fiabilidad/reporte-fiabilidad.md) | Protocolo de fiabilidad RUN-REL-002 |
| [`documentacion/usabilidad/reporte-usabilidad.md`](documentacion/usabilidad/reporte-usabilidad.md) | Prueba de usabilidad RUN-USA-001, con su protocolo, instrucción y hoja de registro |
| [`documentacion/mantenibilidad/reporte-mantenibilidad.md`](documentacion/mantenibilidad/reporte-mantenibilidad.md) | Trazado de dos rutas hasta la persistencia y code smells de SonarQube |
| [`documentacion/kpis.md`](documentacion/kpis.md) | Indicadores de calidad e interpretación de las métricas de SonarQube |
| [`documentacion/responsabilidades.md`](documentacion/responsabilidades.md) | Responsables por frente y quién ejecutó cada corrida |

## Alcance

| Área | Qué se evalúa |
| --- | --- |
| Autenticación | Acceso válido, rechazo de credenciales inválidas, cambio de contraseña y bloqueo de cuenta |
| Recetas | Crear, consultar, editar y eliminar datos sintéticos por interfaz y API |
| Plan de comidas | Asociar recetas a fechas y comprobar la persistencia |
| Listas de compras | Crear listas y actualizar ítems y su estado |
| Plan privado | Rechazar lectura o modificación sin sesión o desde otro hogar |

Quedan fuera IA, OIDC, LDAP, SMTP, pagos, importaciones reales de terceros,
comparaciones de motores de base de datos y pruebas de estrés destructivas. Los
resultados locales no se generalizan como garantías o SLA de Mealie.

## Estructura

```text
.github/workflows/qa-api.yml   # CI: suite de API contra un Mealie v3.25.1 desechable
documentacion/                 # Plan, casos, defectos, seguridad, rendimiento, fiabilidad, usabilidad, mantenibilidad, KPIs y responsabilidades
pruebas/
├── api/                       # Casos automatizados CP-A01..CP-A05 (Pytest)
├── fiabilidad/                # Protocolo de fiabilidad RNF-03 (10 ciclos en 15 min)
├── preparar_datos.py          # Crea hogares y usuarios sintéticos en una instancia local
├── preparar_datos_ci.py       # Versión no interactiva para el CI
├── rendimiento/               # Prueba de carga con Locust (RNF-04)
├── usabilidad/                # Datos sintéticos de la sesión de usabilidad RNF-02
├── zap/                       # Ejecutor aislado de OWASP ZAP
└── requirements.txt           # Dependencias fijadas de la suite
reports/                       # Salidas crudas de cada corrida (ignorada por Git)
```

## Cómo ejecutar

Requisitos: Python 3.14 (la versión que usa el CI), Docker y una instancia local de Mealie v3.25.1
en `http://localhost:9925` (configurable con `MEALIE_URL`).

```bash
git clone https://github.com/Juandavm12/qa-mealie-proyecto-final.git
cd qa-mealie-proyecto-final
python -m pip install -r pruebas/requirements.txt

# 1. Crear los hogares y usuarios sintéticos (pide el token de administrador sin mostrarlo)
python pruebas/preparar_datos.py

# 2. Ejecutar la suite: casos de API y pruebas unitarias de las herramientas
python -m pytest -v
```

Las credenciales generadas quedan solo en `.env.qa`, que Git ignora. Los casos de
API se omiten si no hay credenciales configuradas.

Pruebas no funcionales (cada una exige `--execute` para correr de verdad):

```bash
# Seguridad dinámica: escaneo baseline o escaneo autenticado de la API
python pruebas/zap/ejecutar_zap.py --run-id RUN-ZAP-003 --mode baseline --execute

# Fiabilidad: 10 ciclos durante 15 minutos
python pruebas/fiabilidad/ejecutar_fiabilidad.py --run-id RUN-REL-003 --execute

# Rendimiento
python -m pip install -r pruebas/rendimiento/requirements.txt
python pruebas/rendimiento/ejecutar_rendimiento.py --run-id RUN-PERF-002 --execute
```

**El CI crea su propia instancia aislada y datos desechables.** Nunca apunta a
una instancia personal ni usa sus cuentas, volúmenes o datos.

## Publicación segura

- No se publican secretos, cookies, tokens, claves, bases de datos ni respaldos.
- Las salidas crudas de cada corrida quedan en `reports/`, ignorada por Git. Solo
  se publican reportes revisados y saneados.
- Las capturas y logs se revisan antes de incluirlos; `.gitignore` no sanea archivos.
- No se publican nombres completos de integrantes, el PDF del profesor ni los
  planes internos del grupo.

## Referencias y licencia

- [Mealie v3.25.1: versión oficial](https://github.com/mealie-recipes/mealie/releases/tag/v3.25.1).
- [Código del tag fijado](https://github.com/mealie-recipes/mealie/tree/v3.25.1).
- [Documentación oficial](https://docs.mealie.io/): puede describir versiones posteriores.
- [Licencia upstream del tag](https://github.com/mealie-recipes/mealie/blob/v3.25.1/LICENSE):
  Mealie se distribuye bajo **AGPL-3.0-only**.

Este repositorio no incluye una copia de Mealie ni sustituye sus avisos legales.
