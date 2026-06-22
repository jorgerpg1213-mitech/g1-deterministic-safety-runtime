# SAFETY_MODEL_G1.md
## G1 Deterministic Safety Runtime — Formal Safety Model
**Version:** 1.0 — 4I-P1
**Date:** 2026-06-21
**Status:** Active — closes DT-4E-001
**Repository:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**Roles:** PM: ChatGPT | Implementor/Auditor: Claude Sonnet 4.6 | Operator: Jorge Padilla

---

## 1. Safety Objective

The G1 Deterministic Safety Runtime provides a deterministic and auditable safety supervision layer for the Unitree G1 humanoid robot asset operating in simulation.

Within the validated simulation scope, the runtime detects physical-instability conditions and signal-level faults, routes safety events through deterministic state-transition logic, and emits documented recovery responses with observable evidence through ROS2 topics, logs, tests, and recorded experiment outputs.

The runtime does not guarantee prevention of physical harm, robot damage, unsafe motion, or successful physical recovery. Its safety claim is limited to detection, escalation, state-transition governance, and documented response behavior under the scope and assumptions defined in this document.

Where implementation behavior and intended safety semantics diverge, the divergence is declared as technical debt and is not hidden as a validated guarantee.

---

## 2. Scope

### 2.1 In Scope

This safety model applies to the validated G1 runtime configuration used in the project evidence set:

- Isaac Sim 4.5 running on x86 infrastructure with Tesla T4 GPU.
- ROS2 Humble runtime inside the `g1-ros-phase-b:humble` Docker container.
- Unitree G1 simulation asset with 37 DOF as used in the validated Isaac Sim experiments.
- Runtime supervision over the following monitored ROS2 telemetry channels:
  - `/g1/imu`
  - `/g1/contact/left`
  - `/g1/contact/right`
  - `/joint_states`
  - `/g1/base_pose`
- Physical-instability detection through `cross_consistency_observer`.
- Signal-health fault detection through `watchdog_g1`.
- Deterministic safety-state transitions TX-001 through TX-011 through `safety_orchestrator_g1`.
- Recovery policy behavior implemented in `recovery_g1`, including direct watchdog-driven recovery handling and governed orchestrator-driven recovery handling, subject to the limitations declared in this document.
- Evidence-backed timing claims for the validated paths only.

### 2.2 Out of Scope

This safety model does not claim coverage for:

- Unitree G1 real hardware operation.
- Real actuator safety, torque safety, or physical injury prevention.
- Active PD control or sustained active standing control. This remains open under DT-4E-006.
- Isaac Lab locomotion training or RL policy deployment. This path is outside the current Tesla T4 critical path and remains blocked by RTX-class GPU requirements.
- Hardware-in-the-loop validation.
- Unitree SDK integration for real robot deployment.
- Full paper-grade end-to-end latency correlation with UUID/event_id tracing. This remains open under DT-4G-002.
- Formal calibration of all thresholds. Threshold values remain pragmatic unless explicitly validated in later stages.
- Certification, qualification, or endorsement under ISO 26262, IEC 61508, NASA, MIT, Boston Dynamics, or equivalent safety standards.
- Any claim that the runtime prevents harm, guarantees recovery success, or provides certified functional safety.

### 2.3 4I-Specific Boundary

Stage 4I is a formalization stage. It documents the actual safety model, contracts, evidence, assumptions, and technical debt of the current runtime.

Stage 4I does not introduce new runtime behavior, does not modify safety logic, does not recalibrate thresholds, does not resolve PD control, and does not alter the orchestrator, watchdog, observer, recovery node, ROS2 messages, launcher, or Isaac simulation setup.

---

## 3. System Architecture

The G1 Deterministic Safety Runtime is organized as four collaborating ROS2 nodes with explicit separation of concerns. Each component has a bounded responsibility: detection, signal supervision, state-transition governance, or recovery execution.

| Component | Domain | Responsibility |
|---|---|---|
| `cross_consistency_observer` | Physical coherence | Evaluates whether the observed physical state of the simulated G1 is coherent across available telemetry, including IMU, contact, joint, and base-pose signals. In the validated experiments, this component detects physical-instability conditions such as fallen or no-support states and publishes `SafetyEvent` messages with the source/channel semantics used by the orchestrator transition model. |
| `watchdog_g1` | Signal health | Detects signal-level faults on the monitored telemetry channels, including STALE, FREEZE, NANINF, TIMESTAMP, and RATE conditions. It publishes `SafetyEvent` messages and encodes watchdog rule identity in `msg.notes` using `rule_id=4F-P2-*` semantics. |
| `safety_orchestrator_g1` | State-transition governance | Evaluates the deterministic transition matrix TX-001 through TX-011. It consumes `SafetyEvent` inputs and publishes `SafetyAction` and `SystemState` outputs. It does not detect physical faults, does not monitor signal health directly, and does not execute recovery actions. |
| `recovery_g1` | Recovery execution | Executes recovery policy from received runtime inputs. It subscribes to `/safety_events` for the direct path and `/safety_actions` for the governed path. It does not determine fault truth. In the direct path, it can dispatch by cause using `SafetyEvent.notes` / `rule_id`. In the governed path, current behavior is constrained by the information carried in `SafetyAction`; the known discrepancy around TX-011 governed recovery execution is tracked as DT-4I-001. |

### 3.1 Architectural Rule

`recovery_g1` does not decide what happened. Fault truth is established upstream by the detector that produced the event:

- `cross_consistency_observer` is responsible for physical-coherence fault detection.
- `watchdog_g1` is responsible for signal-health fault detection.
- `safety_orchestrator_g1` is responsible for deterministic state-transition governance.
- `recovery_g1` is responsible for executing the configured recovery policy from the information it receives.

### 3.2 Two Runtime Paths

The architecture contains two active recovery paths.

**Governed Path**

The governed path routes physical-instability events through the orchestrator before recovery:

```
cross_consistency_observer
  → SafetyEvent
    → safety_orchestrator_g1
      → SafetyAction
        → recovery_g1
```

This path is used for orchestrated safety-state transitions, including TX-011 in the validated G1 instability experiments. The orchestrator governs the transition and emits a `SafetyAction`.

Known limitation: the governed path currently carries less causal detail into `recovery_g1` than the direct `SafetyEvent` path. The discrepancy between declared `SafetyAction.action_name` and the apparent internal recovery dispatch result for TX-011 is tracked as DT-4I-001.

**Direct Path**

The direct path routes watchdog and fallback events directly to recovery:

```
watchdog_g1 or cross_consistency_observer
  → SafetyEvent
    → recovery_g1
```

This path preserves `SafetyEvent.notes`, including watchdog `rule_id` values. It is therefore used by `recovery_g1` to dispatch signal-health recovery policy by cause:

- `STALE` → `wait_for_primary_restore`
- `FREEZE` → `operator_intervention`
- `NANINF` → `operator_intervention`
- `TIMESTAMP` → `operator_intervention`

Terminal manual causes (FREEZE, NANINF, TIMESTAMP) bypass cooldown and retry counters according to the 4H-P2 recovery policy hardening.

---

## 4. Fault and Threat Model

The runtime monitors two primary fault families:

- physical-instability faults, detected by `cross_consistency_observer`;
- signal-health faults, detected by `watchdog_g1`.

This model defines what the current runtime detects and routes. It does not claim that the thresholds are physically optimal, certified, or fully calibrated. Threshold calibration remains open under DT-4F-001.

### 4.1 Fault Family 1 — Physical Instability

Physical-instability faults are produced by `cross_consistency_observer` when the observed simulated G1 state becomes inconsistent with the expected healthy standing/contact condition.

| Fault class | Detection condition | Current parameterization | Status |
|---|---|---|---|
| Fallen / severe support loss | Sustained low orientation confidence, represented by `abs(q.w) < FALLEN_W_CRITICAL` over consecutive fresh samples | `FALLEN_W_CRITICAL = 0.80`; `FALLEN_CONSECUTIVE_N = 3` | Validated as a pragmatic runtime detector in the simulation evidence set |
| Moderate instability / warning band | Orientation enters warning band or support/contact consistency degrades without satisfying the critical fallen condition | `FALLEN_W_WARN = 0.85` | Pragmatic threshold; calibration pending |
| Input freshness failure for physical-coherence evaluation | Required observer inputs are older than the accepted freshness window | Freshness window currently approximately 0.5 s | Runtime assumption; calibration pending |

The physical-instability model is based on simulation telemetry and validated experiment behavior. It should not be interpreted as a certified biomechanical or hardware-safety model.

### 4.2 Fault Family 2 — Signal Health

Signal-health faults are produced by `watchdog_g1` when one of the monitored telemetry streams becomes stale, frozen, corrupted, temporally inconsistent, or rate-degraded.

| Fault | rule_id | Detection condition | Severity policy | Recovery-route status |
|---|---|---|---|---|
| STALE | 4F-P2-STALE | No fresh message is received within the watchdog timeout window after startup/warmup behavior is accounted for | CRITICAL for high-priority streams or prolonged absence; otherwise WARN | Direct recovery path validated: `wait_for_primary_restore` |
| FREEZE | 4F-P2-FREEZE | A monitored signal repeats identical values over the configured freeze window | WARN | Direct recovery path validated: terminal manual cause → `operator_intervention`; bypasses cooldown/retry |
| NANINF | 4F-P2-NANINF | A numeric field contains NaN or Inf | CRITICAL | Direct recovery path covered by terminal manual policy → `operator_intervention`; bypasses cooldown/retry |
| TIMESTAMP | 4F-P2-TIMESTAMP | Timestamp moves backward or becomes temporally inconsistent | WARN | Direct recovery path covered by terminal manual policy → `operator_intervention`; bypasses cooldown/retry |
| RATE | 4F-P2-RATE | Effective message rate drops below the configured minimum after warmup | WARN | Detection exists, but explicit recovery dispatch is not formally validated; declared as limitation under DT-4F-001 |

### 4.3 Watchdog Runtime Assumptions

The watchdog operates with startup/warmup protection before evaluating startup-sensitive conditions. This prevents startup transients from being treated as validated runtime failures.

Contact topics are excluded from FREEZE detection in the current policy. This avoids treating a physically plausible steady contact state as a frozen-signal fault.

### 4.4 Calibration Status

The thresholds in this section are implementation parameters, not certified safety limits. They are sufficient for the validated simulation experiments completed through 4H, but they remain pragmatic and calibration-pending.

Open calibration and modeling limitations include:

- DT-4F-001 — pragmatic thresholds are not fully calibrated.
- DT-4F-004 — potential FREEZE false positive for IMU when the simulated robot is physically still.
- RATE fault recovery behavior is not formally validated as a recovery policy.

---

## 5. Compound State Model

The orchestrator maintains a compound safety state composed of two dimensions:

`(risk_level, restriction_level)`

- The `risk_level` represents the severity of the current safety condition.
- The `restriction_level` represents the operational restriction or corrective posture associated with that condition.

This model is evaluated by `safety_orchestrator_g1` through the deterministic transition matrix TX-001 through TX-011.

### 5.1 Risk Levels

| Risk level | Order | Description |
|---|---|---|
| SAFE | 0 | Nominal supervised operation. No active safety degradation is present. |
| CAUTION | 1 | Minor anomaly or early warning condition. The system remains operational but under elevated supervision. |
| DANGER | 2 | Active safety concern requiring stronger restriction or transition toward recovery handling. |
| STABILITY_RISK | 3 | Physical or logical stability risk. Stabilization-oriented behavior may be requested. |
| FAULT_CRITICAL | 4 | Critical fault state. Manual intervention, terminal handling, or high-restriction behavior may be required depending on the transition and restriction level. |

### 5.2 Restriction Levels

| Restriction level | Order | Description |
|---|---|---|
| NONE | 0 | No runtime restriction. |
| R1 | 1 | Minor restriction. Used for low-severity degraded operation. |
| R2 | 2 | Stronger operational restriction, such as locomotion hold or equivalent constrained behavior. |
| R3 | 3 | Stabilization-oriented restriction. Used when the system enters or approaches stability-risk handling. |
| R4-halt | 4 | Controlled halt variant of R4-level restriction. |
| R4-sit | 5 | Emergency-sit variant of R4-level restriction. |
| R5 | 6 | Terminal torque-release / maximum restriction state. |

R4-halt and R4-sit are treated as distinct operational variants within the R4 restriction family. R5 is the terminal restriction level.

### 5.3 Terminal Commitment

The terminal commitment path is represented by TX-005, which transitions the system into a critical terminal handling state associated with torque release / R5-level restriction.

Once the system reaches `(FAULT_CRITICAL, R5)` through TX-005, the safety model treats this as a terminal commitment state. Automatic recovery from this state is not claimed by this document.

Any return from this condition would require explicit operator intervention, runtime reset, or a separately validated transition path. No automatic recovery guarantee is made for `(FAULT_CRITICAL, R5)`.

### 5.4 Recovery Eligibility Guard

`recovery_g1` includes a recovery-eligibility policy that constrains whether recovery actions are allowed under high-risk compound states.

The model-level interpretation is:

- lower-risk states may permit automatic or semi-automatic recovery behavior;
- high-risk states such as STABILITY_RISK or FAULT_CRITICAL with R3 or higher restriction must be treated conservatively;
- recovery behavior under these states must not be described as universally available unless explicitly validated by code and evidence.

This document does not claim universal auto-recovery from high-risk or terminal compound states.

### 5.5 Audit Note

The compound state model describes the orchestrator's safety-state abstraction. It does not by itself prove that every downstream recovery action executes the intended physical or logical behavior.

The known governed-recovery discrepancy for TX-011 is tracked separately as DT-4I-001 and must be considered when interpreting recovery execution claims.

---

## 6. Transition Model TX-001 → TX-011

The orchestrator evaluates safety transitions through the `TransitionEvaluator` logic in `safety_orchestrator_g1.py`.

The transition model is deterministic in the sense that transition selection is governed by explicit transition rules, priority classes, source authority, current compound state, and event/action conditions. The runtime as a whole is not stateless: it maintains the current compound state `(risk_level, restriction_level)` and evaluates transitions relative to that state.

The transition matrix TX-001 through TX-011 is auditable through the project transition matrix and the 3C/4G/4H evidence set. TX-001 through TX-010 are covered by the Level-4 runtime validation tests, and TX-011 is covered by the G1 simulation pipeline evidence.

### 6.1 Transition Priority Classes

The implemented transition model uses the following priority classes:

- CRITICAL_INTERRUPT
- COMMIT_TERMINAL
- NORMAL
- RECOVERY
- POLICY_GATED

The exact ordering and tie-breaking behavior must be read from the audited implementation. This document does not infer priority behavior beyond the verified transition table.

### 6.2 Transition Matrix

| TX | Priority class | Origin condition | Target condition | Action emitted | Trigger condition | Evidence / status |
|---|---|---|---|---|---|---|
| TX-001 | CRITICAL_INTERRUPT | Any eligible non-terminal state | At least STABILITY_RISK / stabilization restriction | `stabilization_mode` | Primary-domain severe stability anomaly such as STABILITY_ANOMALY, JOINT_OSCILLATION, or IMU_OUT_OF_RANGE | 3C tests |
| TX-002 | NORMAL | SAFE | CAUTION | `velocity_clamp` / `gait_slowdown` | Degraded sensing or obstacle-related condition such as SENSOR_DEGRADED or OBSTACLE_DETECTED | 3C tests |
| TX-003 | NORMAL | DANGER | STABILITY_RISK | `stabilization_mode` | Stability anomaly from primary-domain evidence | 3C tests |
| TX-004 | NORMAL | STABILITY_RISK | FAULT_CRITICAL | `controlled_halt` | Primary recovery/mitigation ineffective or unreliable | 3C tests |
| TX-005 | COMMIT_TERMINAL | FAULT_CRITICAL | (FAULT_CRITICAL, R5) | `torque_release` | Authorized R5 terminal policy gate requiring human-level commitment | 3C tests |
| TX-006a | RECOVERY | (FAULT_CRITICAL, R4-halt) | DANGER / reduced restriction | `release_controlled_halt` | Primary restored and effective | 3C tests |
| TX-006b | RECOVERY | (STABILITY_RISK, R3) | DANGER / reduced restriction | `reduce_stabilization_to_locomotion_hold` | Primary stable condition | 3C tests; DT-4F-002 remains active for explicit subcase coverage |
| TX-006c | RECOVERY | (DANGER, R2) | CAUTION / reduced restriction | `release_locomotion_hold` | Primary stable and effective | 3C tests; DT-4F-002 remains active for explicit subcase coverage |
| TX-007 | NORMAL | CAUTION | DANGER | `freeze_navigation` | Escalating obstacle, latency, or secondary-domain condition | 3C tests |
| TX-008 | CRITICAL_INTERRUPT | SAFE | STABILITY_RISK | `stabilization_mode` | Severe immediate stability or impact-related condition from primary-domain evidence | 3C tests |
| TX-009 | POLICY_GATED | Eligible R4-halt / high-restriction state | R4-sit variant | `emergency_sit` | POLICY_GATE_AUTHORIZED_EMERGENCY_SIT | 3C tests; exact policy-gate condition pending 4I-P3 audit under DT-4F-003 |
| TX-010 | RECOVERY | (CAUTION, R1) | SAFE / NONE | `release_all_constraints` | ALL_CLEAR and effective recovery condition | 3C tests |
| TX-011 | NORMAL | Eligible non-(STABILITY_RISK, R3) state | (STABILITY_RISK, R3) | `stabilization_mode` as `SafetyAction.action_name` | CONDITION_DETECTED + SECONDARY + EFFECTIVE | 4G-P2-C N=13, 4G-P4-D N=10, 4H-P1; downstream recovery execution discrepancy tracked as DT-4I-001 |

### 6.3 TX-011 Interpretation

TX-011 must not be defined merely as "fallen" in the abstract. Its implementation-level trigger is:

`CONDITION_DETECTED + SECONDARY + EFFECTIVE`

In the validated G1 experiments, this trigger corresponded to the physical-instability path emitted by `cross_consistency_observer`, including fallen/stability-risk behavior. The correct contract is therefore:

- **Implementation trigger:** `CONDITION_DETECTED + SECONDARY + EFFECTIVE`
- **Validated interpretation:** physical-instability / fallen path in the G1 simulation evidence set
- **Emitted action:** `SafetyAction.action_name=stabilization_mode`
- **Downstream caveat:** actual `recovery_g1` execution for the governed TX-011 path is under DT-4I-001

### 6.4 Audit Constraints

This transition model documents the orchestrator's transition behavior. It does not claim that every emitted `SafetyAction` is executed downstream exactly as named.

The known governed-recovery discrepancy for TX-011 is tracked as DT-4I-001 and must remain visible in the recovery and evidence sections.

---

## 7. Component Contracts

### 7.1 cross_consistency_observer Contract

`cross_consistency_observer` is responsible for detecting physical-coherence and physical-instability conditions from the simulated G1 telemetry available to the runtime.

It publishes `SafetyEvent` messages on `/safety_events` when the current physical state violates the validated observer condition.

**Current validated instability rule:**

`abs(q.w) < FALLEN_W_CRITICAL`

sustained for `FALLEN_CONSECUTIVE_N = 3` fresh consecutive samples.

The currently documented critical threshold is `FALLEN_W_CRITICAL = 0.80`.

The observer requires fresh input data before asserting the condition. Stale or missing input data is treated as outside the validated physical-coherence claim and is handled by `watchdog_g1` as signal-health supervision.

In the validated TX-011 path, observer-produced `SafetyEvent` messages use the source/channel semantics consumed by `safety_orchestrator_g1` as SECONDARY evidence. This is the basis for the validated `CONDITION_DETECTED + SECONDARY + EFFECTIVE` TX-011 trigger.

The observer is rate-limited by the current implementation parameter `OBSERVER_MAX_PUBLISH_HZ = 1.0`.

This document claims only the validated fallen/stability-risk detection behavior used in the 4G/4H evidence set. Additional cross-consistency rules beyond the validated instability detector are not claimed as validated safety behavior in this model.

### 7.2 watchdog_g1 Contract

`watchdog_g1` is responsible for signal-health supervision. It monitors the runtime telemetry channels declared in the scope of this document and publishes `SafetyEvent` messages when a signal becomes stale, frozen, corrupted, temporally inconsistent, or rate-degraded.

It publishes fault events on `/safety_events`. For watchdog-originated faults, the fault identity is encoded in `SafetyEvent.notes` using the rule-id convention `rule_id=4F-P2-*`.

| Fault | Rule ID | Contract |
|---|---|---|
| STALE | 4F-P2-STALE | No fresh message is observed within the configured timeout/warmup policy. |
| FREEZE | 4F-P2-FREEZE | A monitored signal repeats identical values over the configured freeze window. |
| NANINF | 4F-P2-NANINF | A numeric field contains NaN or Inf. |
| TIMESTAMP | 4F-P2-TIMESTAMP | Message timestamps regress or become temporally inconsistent. |
| RATE | 4F-P2-RATE | Effective publish rate falls below the configured minimum after warmup. |

The watchdog operates with a startup grace period before evaluating startup-sensitive conditions: `STARTUP_GRACE_S = 15`.

The watchdog uses per-rule latching to avoid repeatedly publishing the same active fault condition while that condition remains uncleared. The latch resets when the condition clears.

This latching behavior is separate from `recovery_g1` cooldown and retry policy. Watchdog latching controls duplicate fault publication; recovery cooldown/retry controls repeated recovery execution.

Contact topics are excluded from FREEZE detection in the current policy. This prevents physically plausible steady contact from being treated as a frozen-signal fault.

RATE detection is part of watchdog signal supervision, but its explicit downstream recovery dispatch is not formally validated in the current evidence set and remains declared as a limitation under DT-4F-001.

### 7.3 safety_orchestrator_g1 Contract

`safety_orchestrator_g1` is responsible for deterministic safety-state transition governance.

It consumes incoming `SafetyEvent` messages and evaluates them against the current compound state `(risk_level, restriction_level)` using the transition model TX-001 through TX-011.

It publishes runtime governance outputs on:
- `/safety_actions`
- `/system_state`

and may publish safety-event evidence or transition-related events on `/safety_events`.

The orchestrator does not detect physical faults and does not perform signal-health monitoring. Fault truth is established upstream by `cross_consistency_observer` or `watchdog_g1`.

The orchestrator does not execute recovery actions. Its responsibility is to evaluate whether a safety transition is allowed, select the applicable transition, update the compound safety state, and emit the corresponding `SafetyAction` / `SystemState`.

The compound state is maintained internally by the orchestrator and accessed through synchronized state handling. The safety model treats this state as the authoritative runtime state for transition evaluation.

The orchestrator includes a self-source guard so that it does not recursively act on its own emitted safety-event outputs.

Transition arbitration and priority handling are implemented through the transition-evaluation logic and associated scheduler/arbitration mechanisms. However, conflict resolution between simultaneous equal-priority transitions is not claimed as certified behavior in this document unless explicitly covered by tests and evidence.

If T8 arbitration remains draft or partially validated, it must be declared as a limitation rather than treated as a certified scheduler property.

### 7.4 recovery_g1 Contract

`recovery_g1` is responsible for executing the recovery policy from received runtime inputs.

It subscribes to `/safety_events` and `/safety_actions`, and publishes recovery outputs on `/recovery_events`.

The recovery node does not determine fault truth. It executes recovery behavior from the event or action information it receives.

**Direct Recovery Path**

The direct path consumes `SafetyEvent` messages directly from watchdog or fallback event sources. For watchdog-originated faults, `recovery_g1` extracts the watchdog cause from `SafetyEvent.notes` using the rule-id convention `rule_id=4F-P2-*`.

| Cause | Rule ID / source | Recovery behavior | Policy status |
|---|---|---|---|
| STALE | 4F-P2-STALE | `wait_for_primary_restore` | Recoverable; subject to retry/cooldown |
| FREEZE | 4F-P2-FREEZE | `operator_intervention` | Terminal manual cause; bypasses retry/cooldown |
| NANINF | 4F-P2-NANINF | `operator_intervention` | Terminal manual cause; bypasses retry/cooldown |
| TIMESTAMP | 4F-P2-TIMESTAMP | `operator_intervention` | Terminal manual cause; bypasses retry/cooldown |
| Direct fallen fallback | `cross_consistency_observer` direct event | `wait_for_primary_restore` | Declared fallback; semantically weaker than governed TX-011 path |

Terminal manual causes (FREEZE, NANINF, TIMESTAMP) are implemented through the 4H-P2 terminal bypass policy. These causes do not consume retry counters and are not blocked by recovery cooldown.

Recoverable causes such as STALE and direct fallen fallback remain subject to the configured retry/cooldown policy: `RETRY_COOLDOWN_S = 5`, `MAX_AUTO_RETRIES = 3`.

**Governed Recovery Path**

The governed path consumes `SafetyAction` messages emitted by the orchestrator:

```
SafetyEvent → safety_orchestrator_g1 → SafetyAction → recovery_g1
```

Known limitation: the governed path currently carries less causal detail into `recovery_g1` than the direct `SafetyEvent` path. The TX-011 evidence confirms that the orchestrator emits `SafetyAction.action_name=stabilization_mode`; however, the current internal dispatch behavior inside `recovery_g1` is not claimed to execute `stabilization_mode` as a verified downstream action.

This discrepancy is tracked as **DT-4I-001 — Discrepancy in governed TX-011 recovery execution.**

Until DT-4I-001 is resolved, this document distinguishes between:
- orchestrator emits `SafetyAction.action_name=stabilization_mode` *(validated)*
- `recovery_g1` executes `stabilization_mode` *(not claimed)*

**Recovery Eligibility Guard**

`recovery_g1` includes a recovery-eligibility guard that constrains recovery behavior under high-risk compound states. High-risk states such as STABILITY_RISK or FAULT_CRITICAL with R3 or higher restriction are not claimed to support unrestricted automatic recovery. Terminal states such as `(FAULT_CRITICAL, R5)` have no automatic recovery guarantee.

---

## 8. Recovery Policy

The recovery policy defines how `recovery_g1` dispatches recovery behavior from incoming safety inputs.

| Cause / condition | Route | Recovery behavior | Type | Cooldown | Retry / escalation |
|---|---|---|---|---|---|
| Physical instability / fall through TX-011 | Governed | `SafetyAction.action_name=stabilization_mode` is emitted by the orchestrator. Downstream execution inside `recovery_g1` remains under DT-4I-001. | REC-AUTO intent | Deduplication window documented for governed action path | N/A |
| Direct fallen fallback | Direct | `wait_for_primary_restore` | REC-AUTO | `RETRY_COOLDOWN_S = 5 s` | `MAX_AUTO_RETRIES = 3` |
| STALE | Direct | `wait_for_primary_restore` | REC-AUTO | `RETRY_COOLDOWN_S = 5 s` | `MAX_AUTO_RETRIES = 3` |
| FREEZE | Direct — terminal bypass | `operator_intervention` | REC-MANUAL | None | None |
| NANINF | Direct — terminal bypass | `operator_intervention` | REC-MANUAL | None | None |
| TIMESTAMP | Direct — terminal bypass | `operator_intervention` | REC-MANUAL | None | None |
| RATE | Direct detection only | No formally validated explicit recovery dispatch in current model | Not claimed | Not claimed | Not claimed |

Terminal manual causes are FREEZE, NANINF, and TIMESTAMP. These causes bypass cooldown and retry counters. They are treated as manual-intervention conditions from the first occurrence and do not consume automatic retry attempts.

### 8.1 Governed Path vs Direct Path

The runtime contains two recovery routes with different properties.

**Governed Path**

```
SafetyEvent
  → safety_orchestrator_g1
    → SafetyAction
      → recovery_g1
```

The governed path preserves deterministic state-transition governance. It is the path used for orchestrated transitions such as TX-011. `SafetyAction` currently carries less causal detail than the original `SafetyEvent`. In particular, watchdog-style `rule_id` information is not preserved in the same way.

For TX-011, the validated claim is limited to: orchestrator emits `SafetyAction.action_name=stabilization_mode`. This document does not claim verified downstream execution of `stabilization_mode` inside `recovery_g1` until DT-4I-001 is resolved.

**Direct Path**

```
SafetyEvent
  → recovery_g1
```

The direct path preserves causal detail carried in `SafetyEvent.notes`, including watchdog `rule_id` values. This path allows `recovery_g1` to dispatch by cause. The direct path bypasses orchestrator state-transition governance and is treated as a separate recovery route.

### 8.2 Simultaneity Policy

`recovery_g1` uses a single-flight policy through `_recovery_active`. The first accepted recovery event is executed to completion. A second event arriving while recovery is active is discarded with logging. There is no internal priority queue or recovery scheduler inside `recovery_g1`. This behavior is documented as current policy; it was not redesigned in 4H-P2.

---

## 9. Timing Model

The timing model describes measured runtime latency for the validated simulation evidence set. These measurements are useful for engineering characterization, but they are not claimed as paper-grade end-to-end latency proof.

### 9.1 t0→t1 — Physical Event to SafetyEvent Publication

t0→t1 measures the elapsed time from the physical instability event in Isaac Sim to publication of a corresponding `SafetyEvent` by `cross_consistency_observer`.

| Dataset | N | Mean | Min | Max | Scope |
|---|---|---|---|---|---|
| 4G-P3-C | 10 | 2474.60 ms | 2046.47 ms | 3511.02 ms | Focal engineering measurement; not paper-grade |
| 4G-P4-D | 10 | 2583.61 ms | 2055.00 ms | 3009.17 ms | Focal engineering measurement; not paper-grade |

This measurement includes: Isaac Sim physics progression; sensor update cadence; ROS2/DDS transport; observer freshness policy; and the `FALLEN_CONSECUTIVE_N = 3` consecutive-sample requirement.

### 9.2 t1→t2 — SafetyEvent to Governed Runtime Handling

t1→t2 measures the elapsed time from `SafetyEvent` publication to downstream governed runtime handling observed in the orchestrator/recovery path.

| Dataset | N | Mean | Min | Max | Scope |
|---|---|---|---|---|---|
| 4G-P4-D | 10 | 1.19 ms | 0.83 ms | 2.02 ms | Focal engineering measurement; not paper-grade |

This measurement characterizes the runtime handoff latency in the validated governed path. It does not, by itself, prove that the downstream recovery behavior executed the exact semantic action named in `SafetyAction.action_name`. The TX-011 governed recovery execution caveat is tracked separately as DT-4I-001.

### 9.3 Direct-Path t1→t2 Evidence

The 4H-P2 focal harness produced direct-path latency observations for watchdog-driven events in the approximate range 0.7 ms to 0.9 ms. Observed examples: 0.890 ms, 0.777 ms, 0.867 ms. These values were collected during focal validation of the terminal-bypass policy and are not treated as a formal N-sample latency dataset.

### 9.4 Timing Limitations

- No UUID/event_id paper-grade correlation is currently implemented. This remains open under DT-4G-002.
- The measurements are focal engineering measurements, not certified timing bounds.
- The current timing model assumes same-host monotonic timing behavior for the measurement harness unless otherwise stated by experiment evidence.
- t0→t1 includes detector policy delay, including the consecutive-sample requirement; it is not only transport latency.
- t1→t2 governed-path evidence must be interpreted together with DT-4I-001.
- No timing claim is made for real Unitree G1 hardware.

---

## 10. Known Limitations and Assumptions

These items are not hidden exceptions. They are part of the safety model boundary.

### 10.1 Active Limitations

| Limitation | Origin | Status |
|---|---|---|
| Governed TX-011 recovery execution discrepancy: `SafetyAction.action_name=stabilization_mode` is emitted, but downstream execution inside `recovery_g1` is not claimed as verified. | DT-4I-001 | Open |
| Active PD control is absent; the simulated G1 does not sustain active standing through validated PD control. | DT-4E-006 | Deferred |
| Runtime thresholds are pragmatic implementation parameters, not experimentally calibrated safety limits. | DT-4F-001 | Open |
| TX-006b/c lack explicit named subcase test coverage. | DT-4F-002 | Open |
| TX-009 POLICY_GATED exact condition remains pending code audit. | DT-4F-003 | Pending 4I-P3 |
| Potential FREEZE false positive exists when the robot is physically still, especially for low-motion IMU conditions. | DT-4F-004 | Open |
| Paper-grade t1→t2 correlation using UUID/event_id is absent. | DT-4G-002 | Deferred to 4J |
| Zombie `<defunct>` process accumulation occurs at approximately two per run due to missing PID1 reaper behavior in the container. | DT-4G-004B | Open, non-blocking |
| RATE fault detection exists, but explicit recovery dispatch is not formally validated. | DT-4F-001 | Open |
| Direct fallen fallback uses `wait_for_primary_restore`, which is semantically weaker than the governed TX-011 physical-instability path. | 4H-P1 audit | Declared limitation |

### 10.2 Assumptions

| Assumption | Scope |
|---|---|
| The timing measurements are focal engineering measurements, not certified timing bounds. | Timing model |
| Same-host monotonic timing behavior is assumed for the measurement harness unless explicitly stated otherwise by experiment evidence. | Timing model |
| Isaac Sim telemetry and ROS2 messages are treated as the validated simulation signal source. | Simulation scope |
| Watchdog and observer thresholds are sufficient for the validated experiments through 4H, but not certified or fully calibrated. | Runtime detection |
| `recovery_g1` single-flight behavior is treated as current policy, not as a certified priority scheduler. | Recovery policy |

### 10.3 Out of Scope

| Out-of-scope item | Reason |
|---|---|
| Unitree G1 real hardware validation | Not part of current evidence set |
| Real actuator safety or injury-prevention guarantee | Not validated and not claimed |
| Formal certification under ISO 26262, IEC 61508, NASA, MIT, Boston Dynamics, or equivalent safety frameworks | No certification, qualification, or endorsement is claimed |
| Isaac Lab locomotion training or RL policy deployment | Outside current Tesla T4 critical path; RTX-class GPU requirement remains blocker |
| Hardware-in-the-loop validation | Not performed |
| Unitree SDK integration for real robot deployment | Not part of current runtime evidence |
| Guaranteed physical recovery success | Not validated and not claimed |

---

## 11. Active Technical Debt

| ID | Description | Priority | Target / status |
|---|---|---|---|
| DT-4E-001 | `SAFETY_MODEL_G1.md` was absent from the VM/repo state prior to 4I. | High | Closed by 4I-P1 through this document |
| DT-4E-006 | Active PD control remains deferred; the simulated G1 does not sustain validated active standing control. | High | Future control/actuation phase |
| DT-4F-001 | Runtime thresholds are pragmatic and not experimentally calibrated as safety limits. | Medium | 4J / calibration work |
| DT-4F-002 | TX-006b/c lack explicit named subcase test coverage. | Medium | Open |
| DT-4F-003 | TX-009 POLICY_GATED exact condition requires explicit code-level clarification. | Low | 4I-P3 candidate for closure |
| DT-4F-004 | Potential FREEZE false positive exists for IMU or low-motion signals when the robot is physically still. | Medium | Open |
| DT-4G-002 | Paper-grade t1→t2 correlation using UUID/event_id is absent. | Medium | 4J |
| DT-4G-004B | Zombie `<defunct>` accumulation occurs due to missing PID1/reaper behavior in `boring_noether`. | Low | Deferred; non-blocking |
| DT-4I-001 | Governed TX-011 recovery execution discrepancy: `SafetyAction.action_name=stabilization_mode` is emitted, but downstream `recovery_g1` execution is not claimed as verified. | High | Post-4I runtime alignment / fix phase |

---

## 12. Evidence Map

| Claim | Evidence source | Evidence type | Claim strength |
|---|---|---|---|
| TX-001 through TX-010 are implemented and covered by deterministic runtime validation. | 65 tests total: 63 orchestrator tests + 2 launch integration tests; CI green. | Unit and integration tests | Strong for tested runtime logic |
| TX-011 governed path is observed in the G1 simulation pipeline. | 4G-P2-C N=13, 4G-P4-D N=10, 4H-P1. | Simulation runs / governed-path evidence | Strong for orchestrator emission; downstream recovery execution caveated by DT-4I-001 |
| Observer fallen/stability-risk rule triggers under validated G1 simulation conditions. | 4G-P2-C / 4G-P4-D evidence. | Simulation runs | Strong within simulation scope |
| t0→t1 latency is characterized for focal simulation runs. | 4G-P3-C N=10, 4G-P4-D N=10. | Focal timing measurement | Engineering characterization, not paper-grade |
| Governed-path t1→t2 handoff latency is characterized. | 4G-P4-D N=10, mean approximately 1.19 ms. | Focal timing measurement | Engineering characterization; interpret with DT-4I-001 |
| Direct-path t1→t2 latency is observed in watchdog/recovery harness validation. | 4H-P2 harness examples approximately 0.7–0.9 ms. | Focal observation | Non-formal N; useful engineering evidence |
| STALE direct recovery dispatch maps to `wait_for_primary_restore`. | 4H-P1 harness validation. | Focal validation | Validated direct-path behavior |
| FREEZE direct recovery dispatch maps to terminal `operator_intervention`. | 4H-P1 and 4H-P2 harness validation. | Focal validation | Validated; terminal bypass confirmed |
| NANINF direct recovery dispatch maps to terminal `operator_intervention`. | 4H-P1 harness; terminal-bypass policy equivalence via `TERMINAL_MANUAL_RULE_IDS`. | Focal validation + structural equivalence | Covered, not a separate N-formal battery |
| TIMESTAMP direct recovery dispatch maps to terminal `operator_intervention`. | 4H-P1 harness; terminal-bypass policy equivalence via `TERMINAL_MANUAL_RULE_IDS`. | Focal validation + structural equivalence | Covered, not a separate N-formal battery |
| Terminal manual causes bypass cooldown and retry counters. | 4H-P2 focal validation: FREEZE ×2 within <5 s, followed by STALE without counter contamination. | Focal validation | Strong for FREEZE; NANINF/TIMESTAMP covered by same terminal set implementation |
| Recovery simultaneity is single-flight. | 4H-P2 policy audit of `_recovery_active`. | Code/policy audit | Documented policy, not redesigned scheduler |
| RATE fault detection exists but recovery dispatch is not formally validated. | Watchdog model and 4I limitation review. | Code/model audit | Detection claimed; recovery not claimed |

---

*G1 Deterministic Safety Runtime — SAFETY_MODEL_G1.md*
*Version 1.0 — Stage 4I-P1 — 2026-06-21*
*Closes: DT-4E-001*
*PM: ChatGPT | Implementor/Auditor: Claude Sonnet 4.6 | Operator: Jorge Padilla*
*Repository: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
