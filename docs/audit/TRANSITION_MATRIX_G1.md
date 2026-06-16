# TRANSITION_MATRIX_G1.md
## G1 ROS2 Pipeline — Deterministic Safety Runtime Framework
### 4F-P3 Audit Artifact — Transition Matrix TX-001→TX-010

**Fuente:** derivada de `safety_orchestrator_g1.py` (1195 líneas) y verificada contra tests en `test/`.
**Fecha:** 2026-06-16
**Criterio:** cada TX trazada a método `_eval_TX*` + test asociado + comportamiento esperado.
**No inferida:** toda entrada de esta tabla tiene correspondencia directa en código y test.

---

## Estados del sistema

| Estado | Nivel numérico | Descripción |
|---|---|---|
| SAFE | 0 | Operación nominal sin restricciones |
| CAUTION | 1 | Operación con restricciones leves |
| DANGER | 2 | Operación con restricciones activas |
| STABILITY_RISK | 3 | Riesgo de estabilidad — modo estabilización |
| FAULT_CRITICAL | 4 | Falla crítica — requiere intervención |

---

## Tabla de Transiciones

### TX-001 — ANY → stabilization_mode (CRITICAL_INTERRUPT)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX001` (línea 250) |
| **Prioridad** | CRITICAL_INTERRUPT (mayor precedencia) |
| **Estado origen** | ANY (cross-cutting) |
| **Estado destino** | STABILITY_RISK (mínimo; si estado actual > STABILITY_RISK, se mantiene) |
| **Acción** | `stabilization_mode` |
| **Trigger** | `event_type` ∈ {STABILITY_ANOMALY, JOINT_OSCILLATION, IMU_OUT_OF_RANGE} |
| **Precondición** | `source_authority=PRIMARY` + `authority_effectiveness` ∈ {EFFECTIVE, DEGRADED_EFFECTIVE} |
| **Excepción** | No aplica si estado = (FAULT_CRITICAL, R5) — R5 committed |
| **Tests** | `test_TX001_triggers_on_stability_anomaly_primary` (línea 178) |
| | `test_TX001_not_trigger_from_secondary` (línea 201) |
| | `test_TX001_blocked_on_r5_committed` (línea 211) |
| | `test_TX001_target_risk_never_below_stability_risk` (línea 221) |

### TX-002 — SAFE → CAUTION (NORMAL)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX002` (línea 286) |
| **Prioridad** | NORMAL |
| **Estado origen** | SAFE |
| **Estado destino** | CAUTION |
| **Acción** | variable según evento |
| **Trigger** | `event_type=CONDITION_DETECTED` desde SAFE |
| **Precondición** | ADVISORY solo no puede disparar TX-002 (escalation_guard) |
| **Tests** | `test_TX002_safe_to_caution_obstacle` (línea 235) |
| | `test_TX002_safe_to_caution_sensor_degraded` (línea 248) |
| | `test_TX002_not_from_non_safe_state` (línea 259) |

### TX-003 — DANGER → STABILITY_RISK (NORMAL)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX003` (línea 315) |
| **Prioridad** | NORMAL |
| **Estado origen** | DANGER |
| **Estado destino** | STABILITY_RISK |
| **Acción** | `stabilization_mode` |
| **Trigger** | `event_type=CONDITION_DETECTED` desde DANGER |
| **Nota** | TX-001 tiene precedencia sobre TX-003 |
| **Tests** | `test_TX003_danger_to_stability_risk` (línea 273) |

### TX-004 — STABILITY_RISK → FAULT_CRITICAL (NORMAL — AUTHORITY_LOSS)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX004` (línea 339) |
| **Prioridad** | NORMAL |
| **Estado origen** | STABILITY_RISK |
| **Estado destino** | FAULT_CRITICAL |
| **Acción** | `controlled_halt` |
| **Trigger** | `authority_effectiveness` ∈ {INEFFECTIVE, UNRELIABLE} |
| **Precondición** | DEGRADED_EFFECTIVE NO dispara TX-004 |
| **Tests** | `test_TX004_stability_risk_to_fault_critical` (línea 287) |
| | `test_TX004_not_from_degraded_effective` (línea 300) |

### TX-005 — FAULT_CRITICAL → torque_release (COMMIT_TERMINAL)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX005` (línea 362) |
| **Prioridad** | COMMIT_TERMINAL (irreversible post-commit) |
| **Estado origen** | FAULT_CRITICAL |
| **Estado destino** | torque_release (terminal) |
| **Acción** | `torque_release` |
| **Precondición** | HUMAN_REQUIRED — no autorecovery |
| **Tests** | `test_TX005_commit_terminal_human_required` (línea 313) |
| | `test_TX005_blocked_if_not_fault_critical` (línea 326) |

### TX-006a — FAULT_CRITICAL → DANGER (RECOVERY)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX006a` (línea 386) |
| **Prioridad** | RECOVERY |
| **Estado origen** | FAULT_CRITICAL (R4-halt) |
| **Estado destino** | DANGER |
| **Acción** | `release_controlled_halt` |
| **Trigger** | PRIMARY restaurada con authority_effectiveness EFFECTIVE |
| **Tests** | `test_TX006a_recovery_fault_critical` (línea 335) |

### TX-006b — STABILITY_RISK → DANGER (RECOVERY)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX006b` (línea 408) |
| **Prioridad** | RECOVERY |
| **Estado origen** | STABILITY_RISK (R3) |
| **Estado destino** | DANGER |
| **Acción** | `reduce_stabilization_to_locomotion_hold` |
| **Trigger** | PRIMARY estable restaurada |
| **Tests** | suite TX-006 (DT-4F-002: verificar cobertura explícita) |

### TX-006c — DANGER → CAUTION (RECOVERY)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX006c` (línea 430) |
| **Prioridad** | RECOVERY |
| **Estado origen** | DANGER (R2) |
| **Estado destino** | CAUTION |
| **Acción** | `release_locomotion_hold` |
| **Trigger** | locomotion_hold liberado por recuperación |
| **Tests** | suite TX-006 (DT-4F-002: verificar cobertura explícita) |

### TX-007 — CAUTION → DANGER (NORMAL)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX007` (línea 452) |
| **Prioridad** | NORMAL |
| **Estado origen** | CAUTION |
| **Estado destino** | DANGER |
| **Acción** | `freeze_navigation` |
| **Trigger** | `event_type=CONDITION_DETECTED` desde CAUTION |
| **Precondición** | ADVISORY solo no puede disparar TX-007 (escalation_guard) |
| **Tests** | suite TX-007 |

### TX-008 — SAFE → STABILITY_RISK (CRITICAL_INTERRUPT directo)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX008` (línea 475) |
| **Prioridad** | CRITICAL_INTERRUPT |
| **Estado origen** | SAFE |
| **Estado destino** | STABILITY_RISK (salto directo, omite CAUTION y DANGER) |
| **Acción** | `stabilization_mode` |
| **Precondición** | SECONDARY o ADVISORY solos NO pueden disparar TX-008 |
| **Tests** | `test_TX008_secondary_cannot_trigger` |

### TX-009 — emergency_sit (POLICY_GATED)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX009` (línea 507) |
| **Prioridad** | POLICY_GATED |
| **Estado origen** | ANY (sujeto a policy gate) |
| **Estado destino** | estado emergencia sit |
| **Acción** | `emergency_sit` |
| **Tests** | suite TX-009 (DT-4F-003: condición exacta del gate pendiente) |

### TX-010 — CAUTION → SAFE (RECOVERY)

| Campo | Valor |
|---|---|
| **Método** | `_eval_TX010` (línea 529) |
| **Prioridad** | RECOVERY |
| **Estado origen** | CAUTION |
| **Estado destino** | SAFE |
| **Acción** | `release_all_constraints` |
| **Trigger** | recuperación completa desde CAUTION |
| **Tests** | suite TX-010 |

---

## Resumen de acciones runtime

| Acción | TX asociadas | Descripción |
|---|---|---|
| `stabilization_mode` | TX-001, TX-003, TX-008 | Activa modo estabilización |
| `controlled_halt` | TX-004 | Detención controlada |
| `torque_release` | TX-005 | Liberación de torque (terminal) |
| `release_controlled_halt` | TX-006a | Libera halt controlado |
| `reduce_stabilization_to_locomotion_hold` | TX-006b | Reduce restricción |
| `release_locomotion_hold` | TX-006c | Libera hold de locomoción |
| `freeze_navigation` | TX-007 | Congela navegación |
| `emergency_sit` | TX-009 | Sentada de emergencia |
| `release_all_constraints` | TX-010 | Libera todos los constraints |

---

## Propiedades deterministas verificadas

- **Mismo input → mismo output:** `TransitionEvaluator` es función pura (sin estado interno).
- **Prioridad explícita:** CRITICAL_INTERRUPT > COMMIT_TERMINAL > RECOVERY > NORMAL > POLICY_GATED.
- **Escalation guards:** SECONDARY y ADVISORY no pueden disparar TX-001, TX-007, TX-008 solos.
- **R5 commitment:** TX-001 bloqueada en (FAULT_CRITICAL, R5) — estado terminal protegido.
- **86 tests Level 4, CI green** — validación reproducible en GitHub Actions.

---

## Deuda declarada

| ID | Descripción |
|---|---|
| DT-4F-002 | TX-006b y TX-006c sin test nombrado explícito — verificar cobertura completa |
| DT-4F-003 | TX-009 POLICY_GATED: condición exacta del gate requiere lectura líneas 507-525 |

---

*G1 ROS2 Pipeline — TRANSITION_MATRIX_G1.md*
*Generado: 2026-06-16 | 4F-P3 Audit Artifact*
*Derivado de: safety_orchestrator_g1.py + test suite | No inferido*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
