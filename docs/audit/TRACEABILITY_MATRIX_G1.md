# TRACEABILITY_MATRIX_G1.md
## G1 Deterministic Safety Runtime — Fault Traceability Matrix
**Version:** 1.0 — 4I-P2
**Date:** 2026-06-21
**Status:** Active
**Derived from:** SAFETY_MODEL_G1.md (4I-P1), code audit 4I, evidence set 4E→4H
**Repository:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**Roles:** PM: ChatGPT | Implementor/Auditor: Claude Sonnet 4.6 | Operator: Jorge Padilla

---

## Purpose

This matrix provides a complete fault-to-action traceability table for all active runtime paths in the G1 Deterministic Safety Runtime.

Each row maps one fault or triggering condition to its detector, published event, routing path, recovery or governance action, supporting evidence, and traceability status.

**Claim constraints inherited from SAFETY_MODEL_G1.md:**
- No claim is made that every emitted action is executed downstream as named.
- TX-011 downstream recovery execution is caveated by DT-4I-001.
- RATE fault recovery dispatch is not formally validated.
- All timing values are focal engineering measurements, not certified bounds.

---

## Status Legend

| Status | Meaning |
|---|---|
| `Validated` | Direct experimental or test evidence exists in the project evidence set. |
| `Covered by structural equivalence` | Covered by the same code path as a validated case; no separate N-formal battery. |
| `Declared limitation` | Present in code or architecture, but semantically weaker or not formally validated. |
| `Pending audit` | Requires explicit code-level or evidence-level verification. |
| `Caveated by DT-*` | Covered partially; open technical debt affects the claim. |

---

## Traceability Matrix

### Row 1 — Physical Instability / Fallen (Governed Path)

| Field | Value |
|---|---|
| **Fault / Condition** | Physical instability / fallen / no-support in simulated G1 |
| **Detector** | `cross_consistency_observer` |
| **Detection rule** | `abs(q.w) < FALLEN_W_CRITICAL (0.80)` sustained over `FALLEN_CONSECUTIVE_N = 3` fresh consecutive samples |
| **Published event** | `SafetyEvent`: `event_type=CONDITION_DETECTED`, `source_authority=SECONDARY`, `authority_effectiveness=EFFECTIVE` |
| **Routing path** | Governed: `SafetyEvent → safety_orchestrator_g1 → TX-011 → SafetyAction → recovery_g1` |
| **Governance action** | TX-011 fires; orchestrator emits `SafetyAction.action_name=stabilization_mode` |
| **Recovery action** | Orchestrator emits `SafetyAction.action_name=stabilization_mode`. Downstream execution inside `recovery_g1` is not claimed as verified until DT-4I-001 is resolved. |
| **Evidence** | 4G-P2-C N=13, 4G-P4-D N=10, 4H-P1 |
| **Status** | `Caveated by DT-4I-001` — validated for orchestrator emission; downstream recovery execution not claimed |

---

### Row 2 — Physical Instability / Fallen (Direct Fallback Path)

| Field | Value |
|---|---|
| **Fault / Condition** | Physical instability / fallen event reaching `recovery_g1` directly via `SafetyEvent` |
| **Detector** | `cross_consistency_observer` |
| **Published event** | `SafetyEvent`: `source=cross_consistency_observer`, direct to `/safety_events` |
| **Routing path** | Direct: `SafetyEvent → recovery_g1._on_safety_event() → _dispatch_recovery(source='cross_consistency_observer')` |
| **Recovery action** | `wait_for_primary_restore` |
| **Evidence** | 4H-P1 audit — log `[4H-P1] cause=fallen route=direct_fallback action=wait_for_primary_restore` |
| **Status** | `Declared limitation` — semantically weaker than governed TX-011 path; `wait_for_primary_restore` is not the correct physical-fall recovery action; the correct path is governed via TX-011 |

---

### Row 3 — STALE

| Field | Value |
|---|---|
| **Fault / Condition** | Monitored topic receives no message within timeout window after startup grace period |
| **Detector** | `watchdog_g1` |
| **Detection rule** | No fresh message within `STALE_TIMEOUT_S = 1.0 s`; CRITICAL if topic in `CRITICAL_STALE_TOPICS` or duration ≥ `STALE_CRITICAL_S = 3.0 s` |
| **Published event** | `SafetyEvent`: `notes=rule_id=4F-P2-STALE ...` |
| **Routing path** | Direct: `SafetyEvent → recovery_g1._on_safety_event() → _dispatch_recovery(rule_id='4F-P2-STALE')` |
| **Recovery action** | `wait_for_primary_restore` |
| **Retry/cooldown policy** | Subject to `RETRY_COOLDOWN_S = 5 s`, `MAX_AUTO_RETRIES = 3` |
| **Evidence** | 4H-P1 harness — log `[4H-P1] cause=STALE target=/g1/imu action=wait_for_primary_restore` |
| **Status** | `Validated` |

---

### Row 4 — FREEZE

| Field | Value |
|---|---|
| **Fault / Condition** | Monitored signal repeats identical values over `FREEZE_N = 5` consecutive samples |
| **Detector** | `watchdog_g1` |
| **Detection rule** | `freeze_buf` of depth `FREEZE_N`; all values equal; contact topics excluded |
| **Published event** | `SafetyEvent`: `notes=rule_id=4F-P2-FREEZE ...` |
| **Routing path** | Direct terminal: `SafetyEvent → recovery_g1._on_safety_event() → _dispatch_recovery()` → terminal bypass via `TERMINAL_MANUAL_RULE_IDS` |
| **Recovery action** | `operator_intervention` |
| **Retry/cooldown policy** | Bypassed — terminal manual cause does not consume retry counters and is not blocked by cooldown |
| **Evidence** | 4H-P1 harness + 4H-P2 focal validation: FREEZE ×2 within <5 s without "Cooldown activo"; STALE post-FREEZE without counter contamination |
| **Status** | `Validated` — terminal bypass confirmed strong |

---

### Row 5 — NANINF

| Field | Value |
|---|---|
| **Fault / Condition** | NaN or Inf detected in numeric fields of monitored topic |
| **Detector** | `watchdog_g1` |
| **Detection rule** | `_has_naninf(values)` called on received message fields |
| **Published event** | `SafetyEvent`: `notes=rule_id=4F-P2-NANINF ...` |
| **Routing path** | Direct terminal: same branch as FREEZE via `TERMINAL_MANUAL_RULE_IDS` |
| **Recovery action** | `operator_intervention` |
| **Retry/cooldown policy** | Bypassed — terminal manual cause |
| **Evidence** | 4H-P1 harness — log `[4H-P1] cause=NANINF target=/g1/imu action=operator_intervention`; covered by `TERMINAL_MANUAL_RULE_IDS = {'4F-P2-FREEZE', '4F-P2-NANINF', '4F-P2-TIMESTAMP'}` |
| **Status** | `Covered by structural equivalence` — same terminal bypass branch as FREEZE; no separate N-formal battery |

---

### Row 6 — TIMESTAMP

| Field | Value |
|---|---|
| **Fault / Condition** | Message timestamp regresses or becomes temporally inconsistent |
| **Detector** | `watchdog_g1` |
| **Detection rule** | `stamp_sec < last_stamp_sec - 1e-6` |
| **Published event** | `SafetyEvent`: `notes=rule_id=4F-P2-TIMESTAMP ...` |
| **Routing path** | Direct terminal: same branch as FREEZE via `TERMINAL_MANUAL_RULE_IDS` |
| **Recovery action** | `operator_intervention` |
| **Retry/cooldown policy** | Bypassed — terminal manual cause |
| **Evidence** | 4H-P1 harness — log `[4H-P1] cause=TIMESTAMP target=/g1/imu action=operator_intervention`; covered by `TERMINAL_MANUAL_RULE_IDS` |
| **Status** | `Covered by structural equivalence` — same terminal bypass branch as FREEZE; no separate N-formal battery |

---

### Row 7 — RATE

| Field | Value |
|---|---|
| **Fault / Condition** | Effective message rate drops below `MIN_RATE_HZ = 3.0 Hz` after warmup (`RATE_WARMUP_N = 5`) |
| **Detector** | `watchdog_g1` |
| **Detection rule** | `effective_rate()` computed over `RATE_WINDOW_S = 2.0 s`; evaluated only after `warmed_up()` |
| **Published event** | `SafetyEvent`: `notes=rule_id=4F-P2-RATE ...` |
| **Routing path** | Direct detection only — `SafetyEvent` is published; no explicit recovery dispatch branch exists in current `_dispatch_recovery()` for `4F-P2-RATE` |
| **Recovery action** | None formally validated |
| **Evidence** | Watchdog code audit (`watchdog_g1.py`, `_check()` method); SAFETY_MODEL_G1.md Section 4.2 |
| **Status** | `Declared limitation` — detection claimed; recovery dispatch not formally validated; open under DT-4F-001 |

---

### Row 8 — TX-006 Recovery Transitions

| Field | Value |
|---|---|
| **Fault / Condition** | System in elevated risk state; primary source restored or stable |
| **Detector / Governor** | `safety_orchestrator_g1` |
| **Routing path** | Governed: recovery transition evaluated by `TransitionEvaluator` |
| **Governance actions** | TX-006a: `(FAULT_CRITICAL, R4-halt)` → DANGER via `release_controlled_halt`; TX-006b: `(STABILITY_RISK, R3)` → DANGER via `reduce_stabilization_to_locomotion_hold`; TX-006c: `(DANGER, R2)` → CAUTION via `release_locomotion_hold` |
| **Evidence** | 3C runtime validation tests |
| **Status** | `Caveated by DT-4F-002` — covered by 3C tests; explicit named subcase coverage for TX-006b and TX-006c pending under DT-4F-002 |

---

### Row 9 — TX-009 Emergency Sit

| Field | Value |
|---|---|
| **Fault / Condition** | System in R4-halt restriction state; authorized emergency-sit policy gate |
| **Detector / Governor** | `safety_orchestrator_g1` |
| **Trigger** | `event_type=POLICY_GATE_AUTHORIZED_EMERGENCY_SIT` + `restriction_level='R4-halt'` |
| **Routing path** | Governed: TX-009 evaluated by `TransitionEvaluator._eval_TX009()` |
| **Governance action** | TX-009 fires; `emergency_sit`; target `(current_risk_level, R4-sit)` |
| **Evidence** | 3C runtime validation tests |
| **Status** | `Caveated by DT-4F-003` — 3C tested; exact policy-gate condition requires explicit code-level clarification; pending 4I-P3 audit |

---

## Summary — Status by Row

| Row | Fault / Path | Status |
|---|---|---|
| 1 | Physical instability — governed TX-011 | Caveated by DT-4I-001 |
| 2 | Physical instability — direct fallback | Declared limitation |
| 3 | STALE | Validated |
| 4 | FREEZE | Validated |
| 5 | NANINF | Covered by structural equivalence |
| 6 | TIMESTAMP | Covered by structural equivalence |
| 7 | RATE | Declared limitation |
| 8 | TX-006 recovery transitions | Caveated by DT-4F-002 |
| 9 | TX-009 emergency sit | Caveated by DT-4F-003 |

---

## Open Items Requiring Follow-up

| Item | Debt | Target |
|---|---|---|
| Governed TX-011 downstream recovery execution | DT-4I-001 | Post-4I fix phase |
| TX-006b/c explicit named subcase test coverage | DT-4F-002 | Open |
| TX-009 exact POLICY_GATED condition | DT-4F-003 | 4I-P3 |
| RATE recovery dispatch | DT-4F-001 | 4J / calibration |

---

*G1 Deterministic Safety Runtime — TRACEABILITY_MATRIX_G1.md*
*Version 1.0 — Stage 4I-P2 — 2026-06-21*
*PM: ChatGPT | Implementor/Auditor: Claude Sonnet 4.6 | Operator: Jorge Padilla*
*Repository: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
