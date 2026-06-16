# PLAN DE CALIFICACIÓN DEL REPOSITORIO — G1 ROS2 Pipeline
## Repo Qualification / Audit Readiness Plan — v1
**Fecha:** 2026-06-16
**Estado:** PLAN — NO EJECUCIÓN
**Alcance:** trabajo sobre copia `~/g1-repo-cleanup`. El repo original `~/g1-ros2-pipeline` NO se toca.
**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla
**Aprobación requerida:** PM + Operador antes de CUALQUIER movimiento.

---

## 0. Propósito

Llevar el repositorio a estado **audit-ready** (nivel MIT / NASA / médico-espacial):
coherente, reproducible, sin afirmaciones falsas, sin dependencias legacy ocultas,
con CI que audite de verdad el núcleo de seguridad.

Esto NO es "limpieza" cosmética: es **calificación estructural**.

Principios no negociables de este plan:
- No se borra nada de valor: el legacy se ARCHIVA (trazabilidad > repo "limpio a golpes").
- No se inventa contenido: los modelos ausentes se recrean desde evidencia real, no "bonito".
- No se rompe el build: el legacy no se toca hasta desacoplar el entrypoint G1.
- Una variable por fase, cada fase reversible, build verde verificado entre fases.

---

## 1. Inventario de Hallazgos (verificados con evidencia, cero suposición)

| # | Hallazgo | Evidencia | Gravedad |
|---|---|---|---|
| H1 | Docs viejos trackeados (bootstrap v9, tesis v12) vs realidad v15/v18 | `git ls-files docs/` | Alta |
| H2 | `README.md.bak_4d3d_*` trackeado = basura versionada | `git ls-files` | Media |
| H3 | 5 paquetes ajenos/cascarón: agv_bringup, agv_msgs, rplidar_ros, perception_node, safety_policy_node | `package.xml` + conteo .py | Alta |
| H4 | `g1_description/config/interfaces.md` fósil "Phase 5" describe robot Nav2/SLAM inexistente | head interfaces.md (2026-05-14) | Media |
| H5 | README cita 3 modelos canónicos (SAFETY/RESILIENCE/RECOVERY_MODEL) que NO existen | `ls *.md` + `git ls-files` vacío | ROJA |
| H6 | Badge "86 tests passing" NO cubierto por ci-build: solo testea agv_bringup, g1_msgs, g1_description — sin el core de seguridad | ci-build.yml packages-select | ROJA |
| H7 | ci-audit nunca corrió (solo dispara en tags v*, no hay tags) | `git tag` vacío | Alta |
| H8 | Entrypoint G1 (system_g1.launch.py) vive DENTRO de agv_bringup → limpiar legacy rompe build y arranque | README + ci-build | Alta |
| H9 | `.gitignore` ignora *.bak pero el .bak ya estaba trackeado antes de la regla | `.gitignore` + git ls-files | Media |
| H10 | README congelado en 4D-3 / "4E Next"; falta toda 4E (cerrada) y toda 4F (P1-P5) | README vs tesis v18 | ROJA |
| H11 | ADR-007 declara CI con tests unitarios + integración que el CI real no cumple (refuerza H6/H7) | ARCHITECTURE_DECISIONS.md | Media |
| H12 | ADR-008 menciona flujo Isaac viejo (system_sim.launch.py / use_sim_time) ya superado por kit directo | ARCHITECTURE_DECISIONS.md | Baja |

**Nota perception_node:** ADR-010 lo respalda como stub futuro (Gemini, Fase 5+). Decisión pendiente del PM: archivar como legacy o conservar como stub declarado.


---

## 2. Clasificación en 4 Capas

### Capa 1 — Core G1 (CONSERVAR, intocable)
Validado, documentado en tesis v18, cubierto por tests reales.

| Elemento | Acción | Nota |
|---|---|---|
| g1_msgs | CONSERVAR | depurar msgs PROVISIONAL (Detection3D/Array) en fase posterior |
| cross_consistency_observer | CONSERVAR | observer con severidad (4F-P1) |
| watchdog_g1 | CONSERVAR | watchdog real (4F-P2) |
| safety_orchestrator_g1 | CONSERVAR | core que el CI hoy NO testea (H6) |
| recovery_g1 | CONSERVAR | recovery integrado (4F-P4) |
| test_g1_safety_layer | CONSERVAR | tests Level 4 |
| g1_description | CONSERVAR* | *mover config/interfaces.md a archivo (fósil H4) |

### Capa 2 — Legacy / ajeno (CUARENTENA, NO borrado)
Cuarentena = mover a `legacy/` dentro del repo, conservando historia. Borrado real NO se aplica aquí.

| Elemento | Acción | Riesgo / razón |
|---|---|---|
| agv_bringup | DESACOPLAR primero, luego CUARENTENA | contiene entrypoint G1 → ROMPE BUILD si se mueve antes (H8) |
| agv_msgs | CUARENTENA | cascarón 0 .py |
| rplidar_ros | CUARENTENA | driver lidar externo (LICENSE propia) |
| safety_policy_node | CUARENTENA | README: "replaced by orchestrator" |
| perception_node | PENDIENTE PM | ADR-010 lo respalda como stub futuro Gemini — archivar vs conservar stub |

### Capa 3 — Docs (ACTUALIZAR / ARCHIVAR / CREAR)
| Doc | Acción |
|---|---|
| README.md | REESCRIBIR a estado 4F (hoy congelado en 4D-3, H10) |
| chat_bootstrap_..._v9.md | ARCHIVAR → entra v15 |
| tesis_..._v12.md | ARCHIVAR → entra v18 |
| informe_etapa_4D3_2026-06-08.md | ARCHIVAR (histórico) → entra informe 4F |
| g1_description/config/interfaces.md | ARCHIVAR (fósil Phase 5) |
| SAFETY_MODEL_G1.md + RESILIENCE + RECOVERY | CREAR desde evidencia real (H5/DT-4E-001) — NO inventar |
| TRANSITION_MATRIX_G1.md | CONSERVAR (correcto) |
| ARCHITECTURE_DECISIONS.md | CONSERVAR + nota revisión ADR-007/008 (H11/H12) — sin borrar original |
| TECHNICAL_DEBT_3C.md | CONSERVAR (sano, vigente) |
| README.md.bak_* | BORRAR + git rm --cached (basura, H2/H9) |

### Capa 4 — CI (CORREGIR = alinear con ADR-007)
| Workflow | Problema | Acción |
|---|---|---|
| ci-build.yml | solo 3 paquetes, sin core de seguridad (H6) | ampliar packages-select al core; desacoplar de agv_bringup |
| ci-audit.yml | nunca corrió, solo tags v* (H7) | disparar en push/PR o schedule; quitar apt Nav2/slam si sale el legacy |


---

## 3. Orden de Ejecución por Fases (con rollback)

Regla transversal: una fase = una variable. Build verde verificado antes de pasar a la siguiente.
Verificación de build = colcon build + colcon test del core, en verde.

### FASE 0 — Baseline de respaldo (OBLIGATORIA, antes de mover nada)
**Objetivo:** punto de retorno maestro.
- Acción: rama + tag de referencia sobre el estado actual de la copia.
  - `git checkout -b pre-repo-qualification-4f`
  - `git add -A && git commit -m "baseline: pre repo qualification (4F state)"`
  - `git tag pre-repo-qualification-4f`
- Verificación: `git tag` muestra el tag; `git status` limpio.
- ROLLBACK global del proyecto completo: `git checkout pre-repo-qualification-4f`.

### FASE 1 — Desacoplar entrypoint G1 de agv_bringup (punto crítico H8)
**Objetivo:** que el arranque y el build del G1 no dependan del paquete legacy.
- Acción: crear paquete G1 propio (ej. `g1_bringup`) y mover `system_g1.launch.py` ahí.
- Verificación: build verde + `ros2 launch g1_bringup system_g1.launch.py` resuelve sin agv_bringup.
- ROLLBACK: borrar `g1_bringup`, restaurar referencia en agv_bringup (git checkout del path).

### FASE 2 — Corregir CI (prioridad roja, alinear con ADR-007)
**Objetivo:** que el CI audite el core real.
- Acción: ci-build packages-select = g1_msgs, observer, watchdog, orchestrator, recovery, test_g1_safety_layer; ci-audit dispara en push/PR o schedule.
- Verificación: lógica revisada localmente (no romper sintaxis YAML). CI remoto se valida al pushear (decisión posterior).
- ROLLBACK: `git checkout .github/workflows/`.

### FASE 3 — Cuarentena del legacy
**Objetivo:** sacar lo ajeno de la ruta activa sin perder trazabilidad.
- Acción: mover agv_*, rplidar_ros, safety_policy_node a `legacy/` (perception_node según decisión PM).
- Verificación: build verde SIN esos paquetes (confirma desacople de Fase 1 correcto).
- ROLLBACK: mover de vuelta desde `legacy/` (git mv inverso).

### FASE 4 — Docs a estado 4F
**Objetivo:** que el repo cuente la verdad actual.
- Acción: archivar v9/v12/informe-4D3/interfaces.md en `docs/archive/`; entrar v15/v18/informe-4F; reescribir README a 4F; nota de revisión ADR-007/008.
- Verificación: README sin afirmaciones falsas (cero referencias a archivos inexistentes); índice apunta a docs vigentes.
- ROLLBACK: `git checkout` de los docs afectados.

### FASE 5 — Recrear modelos ausentes (H5)
**Objetivo:** que SAFETY/RESILIENCE/RECOVERY_MODEL existan, derivados de evidencia.
- Acción: recrear los 3 modelos trazando código real (orchestrator, recovery) + informes. NO redactar "bonito".
- Bloqueante: requiere material fuente confirmado con PM/Operador. NO se ejecuta sin él.
- Verificación: cada afirmación del modelo mapea a código o informe existente.
- ROLLBACK: borrar los 3 archivos creados.

### FASE 6 — Borrado de basura pura
**Objetivo:** eliminar lo que no tiene valor de trazabilidad.
- Acción: `git rm --cached README.md.bak_*` y borrar del disco (ya está en historia git + cubierto por .gitignore).
- Verificación: `git ls-files | grep .bak` vacío.
- ROLLBACK: recuperable desde historia git (`git checkout <commit> -- <archivo>`).

---

## 4. Criterio de "Audit-Ready" (definición de terminado)

- [ ] CI corre y cubre el core de seguridad en verde (H6/H7 cerrados).
- [ ] Cero afirmaciones falsas en README (H5/H10 cerrados).
- [ ] Legacy archivado, no en ruta activa; build verde sin él (H3/H8 cerrados).
- [ ] Docs vigentes (v15/v18/informe-4F) en el repo; viejos en archive (H1 cerrado).
- [ ] Modelos canónicos existen y son trazables (H5 cerrado).
- [ ] Basura fuera (H2/H9 cerrados).
- [ ] Baseline tag `pre-repo-qualification-4f` disponible como rollback global.

---

## 5. Lo que este plan NO hace
- No ejecuta movimientos hasta aprobación PM + Operador, fase por fase.
- No borra legacy.
- No inventa contenido de modelos.
- No toca el repo original `~/g1-ros2-pipeline`.
- No toca código del core (solo se mueve/clasifica, no se reescribe lógica validada).

---

*PLAN_REPO_QUALIFICATION_v1 — G1 ROS2 Pipeline*
*Generado en VM: 2026-06-16 — Estado: PLAN, pendiente aprobación*

---

## 6. Hallazgo H13 (detectado en auditoría de Fase 1)

| # | Hallazgo | Evidencia | Gravedad |
|---|---|---|---|
| H13 | `system_g1.launch.py` (marcado "CANONICAL G1 ENTRYPOINT" en README) NO lanza el core de seguridad real (observer/watchdog_g1/orchestrator/recovery_g1). Lanza stack AGV legacy: slam_toolbox, ekf_node, safety_policy_node + scripts agv_watchdog_node.py / agv_recovery_manager.py. | cat system_g1.launch.py | ROJA |

**Implicación:** el arranque validado en 4D/4F NO es este launch — son las 4 terminales manuales del bootstrap v15 (Isaac + observer + watchdog + recovery).

**Decisión PM (aprobada):** Opción 1 — archivar el launch AGV como legacy; construir `g1_bringup` que lance el core real DESPUÉS del MIT, con tiempo de probarlo. No se reescribe launch sin probar antes del MIT.

**Referencias a corregir (en Fase 4, README):**
- README.md:523 — Quick Start invoca `ros2 launch agv_bringup system_g1.launch.py` (arranque falso).
- README.md:615 — árbol etiqueta el archivo "CANONICAL G1 ENTRYPOINT".

**Estado:** registrado. Ejecución de archivado diferida a Fase 3 (cuarentena agv_bringup completo). Corrección README en Fase 4.

---

## 7. Hallazgo H14 (detectado al verificar CI en Fase 2)

| # | Hallazgo | Evidencia | Gravedad |
|---|---|---|---|
| H14 | `g1_description` launch test falla con `No module named 'tf2_msgs'` en la imagen runtime `g1-ros-phase-b:humble`. La dependencia no está en esa imagen; sí se resuelve vía `rosdep install` en `ci-audit` (imagen `ros:humble-ros-base`). | colcon test g1_description | Media |

**Resolución aplicada:** `g1_description` (TF tree, no core de seguridad) se retira de `ci-build` (rápido, por push, imagen runtime). Su validación de launch queda en `ci-audit` (completo, con rosdep). `ci-build` ahora cubre los 6 paquetes del core de seguridad: g1_msgs, cross_consistency_observer, watchdog_g1, safety_orchestrator_g1, recovery_g1, test_g1_safety_layer — todos PASS verificados localmente.

**Estado:** resuelto en Fase 2.
