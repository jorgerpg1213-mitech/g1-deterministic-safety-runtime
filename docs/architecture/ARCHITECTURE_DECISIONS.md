# ARCHITECTURE_DECISIONS.md
## Pipeline G1 / ROS2 / Isaac Sim — Decisiones de Arquitectura de Runtime
**Fecha:** 2026-05-14
**Estado:** Aprobado
**Repo:** g1-ros2-pipeline

## ADR-001 — Nombre del workspace
**Decisión:** pipeline_ws
**Razón:** Neutro, escala a G1, Isaac Sim, Gemini y futuros robots.
**Impacto:** Todos los Dockerfiles, compose y launchers usan /root/pipeline_ws.

## ADR-002 — Mounted vs Immutable
**Decisión:** Híbrido.
- Dev: workspace montado por volumen, build incremental.
- Prod/MIT: workspace baked en imagen, reproducible.
**Implementación:** docker-compose profiles (dev / prod).

## ADR-003 — Multi-image
**Decisión:** 4 imágenes con base compartida.
- pipeline-base: deps comunes, sin workspace, sin visualización.
- pipeline-dev: base + RViz2 + rqt + tools, workspace montado.
- pipeline-runtime: base + workspace baked, entregable MIT.
- pipeline-sim: runtime + use_sim_time, para Isaac Sim.

## ADR-004 — RViz
**Decisión:** Solo en pipeline-dev, no en runtime.
**Razón:** Runtime no garantiza display. Con multi-image no se pierde capacidad de inspección.

## ADR-005 — Volúmenes
**Decisión:** Explícitos. Nunca /dev completo.
- ./src montado solo en dev, baked en prod.
- g1_share y logs montados siempre.
- /dev completo prohibido — solo devices explícitos.

## ADR-006 — Logs
**Decisión:** Persistidos fuera del contenedor via volumen ./logs.
**Razón:** Sobreviven reinicios. Evidencia de auditoría MIT.

## ADR-007 — CI/CD
**Decisión:** GitHub Actions.
- ci-build.yml: cada push — build + colcon + tests unitarios.
- ci-audit.yml: manual/tag — build completo + integración + reporte.

## ADR-008 — Isaac Sim
**Decisión:** Proceso nativo en VM, NO dentro del contenedor.
**Integración:** ROS2 bridge con ROS_DOMAIN_ID compartido.
**Config:** use_sim_time true, system_sim.launch.py.

## ADR-009 — Unitree G1 SDK
**Decisión:** g1_adapter_node — paquete ROS2 independiente.
**Responsabilidad:** SDK G1 <-> ROS2 + safety layer + emergency stop.
**Estado:** Interfaces se definen en Fase 5.

## ADR-010 — Gemini Robotics
**Decisión:** gemini_perception_node independiente.
**Estado:** Pendiente confirmar API, latencias y requisitos GPU.

## Resumen
| ADR | Decisión | Estado |
|-----|----------|--------|
| 001 | pipeline_ws | Aprobado |
| 002 | Hibrido mounted/immutable | Aprobado |
| 003 | Multi-image base/dev/runtime/sim | Aprobado |
| 004 | RViz solo en dev | Aprobado |
| 005 | Volumenes explicitos sin /dev | Aprobado |
| 006 | Logs persistidos | Aprobado |
| 007 | GitHub Actions CI/CD | Aprobado |
| 008 | Isaac Sim proceso separado | Aprobado |
| 009 | G1 SDK adapter node | Aprobado |
| 010 | Gemini pendiente API | Pendiente |

*Aprobado: 2026-05-14*
