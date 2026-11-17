# QA de Mealie — proyecto final

Base documental del proyecto académico de Aseguramiento de Calidad del Software
sobre **Mealie v3.25.1**, una aplicación de recetas, planificación de comidas y
listas de compras. El objetivo es preparar una evaluación reproducible con
trazabilidad entre requisitos, casos, ejecuciones, hallazgos y conclusiones.

## Estado real

Este repositorio contiene inicialmente documentación y exclusiones locales.
**No hay tests implementados o ejecutados, pipeline, análisis SonarQube/ZAP ni
métricas obtenidas aquí.** Las herramientas indicadas son propuestas, no resultados.
Las comprobaciones de una instalación personal previa no equivalen a la evaluación
académica ni a una ejecución de CI.

Repositorio público: <https://github.com/Juandavm12/qa-mealie-proyecto-final>.

## Alcance propuesto

| Área | Evaluación prevista |
| --- | --- |
| Autenticación | Acceso válido, rechazo de credenciales inválidas y contraseña propia |
| Recetas | Crear, consultar, editar y eliminar datos sintéticos por UI/API |
| Plan de comidas | Asociar recetas a fechas y comprobar persistencia |
| Listas de compras | Crear listas y actualizar ítems y su estado |
| Plan privado | Rechazar lectura/modificación sin sesión o desde otro hogar |

Antes de probar autorización se verificarán privacidad, permisos efectivos y
cuentas sintéticas en hogares separados. Un recurso público no demuestra un
fallo de aislamiento. Los contratos y resultados esperados se fijarán antes de ejecutar.

Quedan fuera IA, OIDC, LDAP, SMTP, pagos, importaciones reales de terceros,
comparaciones de motores de base de datos y estrés destructivo.
No se generalizarán resultados locales como garantías o SLA de Mealie.

## Herramientas y requisitos previstos

| Necesidad | Propuesta pendiente de preparar y validar |
| --- | --- |
| Automatización API | Python, Pytest y cliente HTTP; dependencias y versiones fijadas |
| CI propio | Preparación de ambiente, ejecución y artefactos saneados |
| Análisis estático | SonarQube sobre código Mealie del tag/commit registrado |
| Seguridad dinámica | OWASP ZAP con objetivo y autorización delimitados |
| Carga básica | Locust o k6; elección, recursos y umbrales antes de medir |

Se necesitarán Git para colaborar, un entorno de contenedores compatible,
recursos suficientes y cuentas/datos exclusivamente sintéticos.
Las versiones, compatibilidad, comandos reproducibles y límites de recursos se
documentarán al implementar; aquí no se indican instalaciones ni arranques.
La cobertura deberá instrumentar código real de Mealie: probar HTTP no mide por
sí solo cobertura del backend ni del sistema completo.

## Flujo de colaboración previsto

Clonar el repositorio:

```bash
git clone https://github.com/Juandavm12/qa-mealie-proyecto-final.git
cd qa-mealie-proyecto-final
```

Leer primero este README y revisar el contenido realmente disponible.
Los casos, dependencias, configuración y comandos de ejecución se incorporarán
cuando existan; no hay todavía una suite que ejecutar ni carpetas de plantilla.
El código upstream se obtendrá por separado, fijando tag y commit, sin copiarlo aquí.

**CI deberá crear su propia instancia aislada y datos desechables.** Nunca apuntará
a la instancia personal `localhost:9925`, ni utilizará sus cuentas, volumen o datos.
El futuro pipeline deberá esperar salud, preparar datos sintéticos, ejecutar,
recoger artefactos saneados y cerrar únicamente su entorno aislado.

## Publicación segura

- No publicar secretos, cookies, tokens, claves, bases de datos ni respaldos.
- Revisar capturas, logs y metadatos antes de incluirlos; `.gitignore` no sanea archivos.
- Añadir informe y evidencias solo en versiones explícitamente sanitizadas.
  Para resultados revisados se reservan las rutas `evidencias/sanitizadas/` y
  `reportes/sanitizados/`; todavía no se crean esas carpetas.
- No publicar por ahora nombres completos de integrantes, el PDF del profesor
  ni copias de los planes internos. El registro de esfuerzo queda en la carpeta
  padre, fuera del repositorio público y sin enlaces locales desde este README.

## Referencias y licencia

- [Mealie v3.25.1: versión oficial](https://github.com/mealie-recipes/mealie/releases/tag/v3.25.1).
- [Código del tag fijado](https://github.com/mealie-recipes/mealie/tree/v3.25.1).
- [Documentación oficial](https://docs.mealie.io/): puede describir versiones posteriores.
- [Licencia upstream del tag](https://github.com/mealie-recipes/mealie/blob/v3.25.1/LICENSE):
  Mealie se distribuye bajo **AGPL-3.0-only**.

Este repositorio no incluye una copia de Mealie ni sustituye sus avisos legales.
No se asigna aquí una licencia a los aportes del grupo sin decisión expresa.

## Límites y próximos pasos

1. Confirmar colaboradores y disponibilidad; revisar el contenido publicado antes de ampliarlo.
2. Confirmar viabilidad, versiones, recursos y contratos del alcance antes de implementar.
3. Diseñar y revisar casos; después preparar automatización y CI aislado.
4. Ejecutar evaluaciones autorizadas y conservar resultados reales, incluidos fallos y límites.
5. Publicar únicamente informe y evidencias saneados con trazabilidad verificable.
