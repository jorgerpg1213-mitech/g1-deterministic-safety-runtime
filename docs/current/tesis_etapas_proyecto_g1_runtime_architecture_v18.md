# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 18 — Actualizada 2026-06-16 (cierre 4E + microfase 4F P1→P5)

> **Nota de versión (v18):** cambios respecto a v17 —
> (1) **4E CERRADA**: baseline sano pasivo (P4E PASS), observer sin falsos positivos (P4F PASS), transición sano→caída capturada (P4G). 4E-P5 (control activo PD) diferido — no bloqueante para paper.
> (2) **4F abierta y avanzada**: Safety Runtime Enrichment. P1 (observer severidad) ✅, P2 (watchdog) ✅, P3 (transition matrix) ✅, P4 (recovery integrado) ✅, P5 (latencia medida) ✅. P6 (fault injection) 🔲.
> (3) Deudas nuevas DT-4F-001…005. Anti-patterns nuevos #60–#62.
> (4) Criterio honesto: pipeline end-to-end validado con evidencia; thresholds pragmáticos; t0→t1 no medido.
> v17 cerró 4D-3D. El resto se mantiene.

---

## Etapa 1 — Infraestructura Base
**Estado:** ✅ Cerrada

## Etapa 2 — Disciplina Operacional
**Estado:** ✅ Cerrada

## Etapa 3 — Safety Runtime Architecture + Runtime Components
**Estado General:** ✅ Cerrada

### Etapa 3A — Modelos Semánticos + ADRs — ✅ Cerrada
`SAFETY_MODEL_G1.md`, `RESILIENCE_MODEL_G1.md`, `RECOVERY_MODEL_G1.md`, `ADR-002`, `ADR-003`.
> ⚠️ **DT-4E-001:** `SAFETY_MODEL_G1.md` ausente en VM — recrear/localizar.

### Etapa 3B — Skeleton Runtime ROS2 — ✅ Cerrada
`g1_msgs`, `watchdog_g1`, `cross_consistency_observer`, `safety_orchestrator_g1`, `recovery_g1`.

### Etapa 3C — Level 4 Runtime Validation — ✅ Cerrada
TX-001→TX-010, scheduler determinista, recovery real, 86 tests Level 4, CI green.

---

## Etapa 4 — Simulación e Integración Runtime
**Estado General:** 🔄 En progreso

### Etapa 4A — Infrastructure & DDS — ✅ Cerrada (2026-05-26)
### Etapa 4B — Isaac Headless Bring-up (4.2.0) — ✅ Cerrada (2026-05-29)
### Etapa 4C — Caracterización Física (4.2.0) — ✅ Cerrada (2026-06-01)
### Etapa 4D — ROS2 Feasibility + Observabilidad + Lazo — ✅ Cerrada
4D-1, 4D-2A–2H, 4D-3A–3D completas. Commit `64d9045`.

---

### Etapa 4E — Baseline Sano + Validación de Estado del Runtime
**Estado:** ✅ CERRADA (2026-06-16)

**Resultado:** baseline sano pasivo establecido (P2 + z_cmd=0.720 + drives fábrica). Observer sin falsos positivos (P4F). Transición sano→caída capturada (P4G). Control activo PD negativo por vías simples (4E-P5 diferido).

**Regla congelada:** todo control/baseline arranca desde P2 + z_cmd=0.720, orient [1,0,0,0]. NUNCA z=0.8.

**4E-P5 diferido:** PD por torque desde baseline válido — no bloqueante para paper. Tabla de signos: left_hip=-1, resto=+1.

---

### Etapa 4F — Safety Runtime Enrichment
**Estado:** 🔄 EN PROGRESO AVANZADO (P1–P5 completas; P6 pendiente)

**Motivación:** convertir el framework que observa en uno que decide, actúa y se puede medir. Prerequisito para publicación.

#### 4F-P1 — Observer con severidad — ✅ PASS
Regla rediseñada a INFO/WARN/CRITICAL. CRITICAL dispara `abs_w<0.80` sostenido 3 muestras frescas, aunque un pie siga en contacto (contacto residual ≠ soporte sano). Dos bugs corregidos: umbral 0.75→0.80, orden CRITICAL antes que WARN. Commits: `f34d95b`, `9eef532`, fix severity.

#### 4F-P2 — Watchdog de salud — ✅ PASS
`watchdog_g1` implementado desde cero: STALE/FREEZE/NANINF/TIMESTAMP/RATE en 5 topics. FREEZE excluido en contactos. STARTUP_GRACE_S=15s. Severidad escalonada: IMU/contactos → CRITICAL inmediato. Commits: `562c9ba`, `875838b`.

#### 4F-P3 — Transition Matrix audit artifact — ✅ PASS
`docs/TRANSITION_MATRIX_G1.md`: TX-001→TX-010 trazadas a método+test+acción. No inferido — derivado del código y 86 tests CI green. Orchestrator no tocado.

#### 4F-P4 — Recovery pasivo seguro — ✅ PASS
`recovery_g1` ya implementado (779 líneas, 5 acciones). Corrida de integración 4 terminales: baseline sano → silencio; caída → observer alarma, recovery reacciona; Isaac muerto → watchdog STALE, recovery reacciona. Sin tocar robot físico.

#### 4F-P5 — Latencia t1→t2 — ✅ PASS
Instrumentación en recovery y extensión Isaac. Latencias en Tesla T4: **0.68–8.2ms** (2 corridas). t0→t1 pendiente (DT-4F-005).

#### 4F-P6 — Fault injection matrix — 🔲 PENDIENTE
Una falla sintética por corrida: IMU congelada, contacto frozen, NaN, timestamp regresivo, topic perdido. Cierra la validación de robustez del watchdog.

#### Deuda técnica 4F

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4F-001 | Thresholds watchdog pragmáticos | Media | Calibrar con más corridas |
| DT-4F-002 | TX-006b/c sin test nombrado explícito | Media | Verificar cobertura |
| DT-4F-003 | TX-009 POLICY_GATED condición exacta pendiente | Baja | Leer líneas 507-525 |
| DT-4F-004 | FREEZE en IMU posible falso positivo con robot caído | Media | Vigilar |
| DT-4F-005 | t0→t1 latencia física→observer no medida | Alta | Sync clocks Isaac↔ROS2 |

---

### Etapa 5A — Isaac Lab Bring-up
**Estado:** 🔒 Bloqueada — fuera de ruta crítica y del T4.

---

## Etapa 5 — Integración VLA / GR00T / LeRobot — Futura
## Etapa 6 — Behaviors Embodied Reales — Futura
## Etapa 7 — Refinamiento y Autonomía — Futura

---

### Etapa 4G — Pipeline Hardening
**Estado:** 🔲 Pendiente (después de cerrar 4F)

- **4G-P1** — Launcher unificado: un solo script que levante las 4 terminales en orden correcto con validación de que cada nodo está vivo antes de arrancar el siguiente.
- **4G-P2** — Reproducibilidad estadística: N≥10 corridas del pipeline completo, tabla de latencias con media/desviación/percentil 95.
- **4G-P3** — t0→t1 sync de clocks: sincronizar clock Isaac↔ROS2 para medir latencia física→observer. Cierra el end-to-end real (DT-4F-005).

---

### Etapa 4H — Recovery Inteligente
**Estado:** 🔲 Pendiente

- **4H-P1** — Mapeo rule_id→acción: recovery distingue caída (observer) vs stale (watchdog) y actúa diferente según tipo de falla. Hoy responde igual a todo.

---

### Etapa 4I — Formalización
**Estado:** 🔲 Pendiente

- **4I-P1** — `SAFETY_MODEL_G1.md`: recrear contrato del orchestrator ausente en VM (DT-4E-001).
- **4I-P2** — Calibración de thresholds: justificar con evidencia abs_w=0.80, STALE=1.0s, FREEZE=5 muestras. Declarar condiciones de recalibración.
- **4I-P3** — Human factors mínimos: log estructurado o dashboard para el operador.
- **4I-P4** — Threat model declarativo: fuentes autorizadas de SafetyEvent, riesgo de spoofing, mitigación futura. Solo declarativo, no implementación.
- **4I-P5 (opcional)** — Control negativo extendido: robot sano en movimiento/perturbaciones pequeñas → sin alarmas. Depende de avance en 4E-P5.

---

### Etapa 4J — Paper Prep
**Estado:** 🔲 Pendiente (cuando 4G y 4H estén cerradas)

- **4J-P1** — Tabla consolidada de resultados: latencias, escenarios validados, hardware, condiciones.
- **4J-P2** — Sección de limitaciones honesta: T4, thresholds pragmáticos, sin robot físico.
- **4J-P3** — Reproducibilidad externa: instrucciones para que un tercero reproduzca el pipeline desde cero.

---

### Diferido (no bloqueante para paper)
- **4E-P5** — Control activo PD desde baseline P2+z0.720 (tabla de signos por joint confirmada).
- **5A** — Isaac Lab — bloqueado por T4 (GPU ≥ RTX 4080 requerida).

---

## Resolución General

El proyecto construye:
> una arquitectura/runtime donde sistemas tipo GR00T puedan operar de forma gobernable, reproducible y segura.

**Aprendizaje 4F:** el framework no solo observa — ahora decide con severidad, detecta degradación del flujo de datos, tiene tabla de transiciones auditable, integra recovery en pipeline real, y tiene latencias medidas en hardware. Lo que resta para publicación: fault injection (4F-P6), reproducibilidad estadística, y t0→t1.

---

## Criterios de éxito (actualizados)

```
4D-3D (logrado):     orchestrator consume SafetyEvent SECONDARY, no escala
4E baseline (logrado): P2 + z_cmd=0.720 + drives fábrica = robot sano pasivo
4E neg-control (logrado): observer sin falsos positivos sobre baseline sano
4E transición (logrado): caída capturada en telemetría
4F-P1 (logrado):     observer con severidad CRITICAL aunque un pie en contacto
4F-P2 (logrado):     watchdog detecta STALE/FREEZE en T4
4F-P3 (logrado):     TX-001→TX-010 auditables en TRANSITION_MATRIX_G1.md
4F-P4 (logrado):     pipeline 4 componentes end-to-end validado
4F-P5 (logrado):     latencia t1→t2 0.68–8.2ms en T4
4F-P6 (PENDIENTE):   fault injection matrix
4E-P5 (diferido):    control activo PD
5A (bloqueada):      Isaac Lab fuera del T4
```

---

*G1 ROS2 Pipeline — Tesis de Etapas v18*
*Actualizado: 2026-06-16*
*3C ✅ | 4A ✅ | 4B ✅ | 4C ✅ | 4D ✅ | 4E ✅ | 4F 🔄 (P1✅ P2✅ P3✅ P4✅ P5✅ P6🔲) | 5A 🔒*
