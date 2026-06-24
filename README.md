# G1 Deterministic Safety Runtime

**A deterministic, auditable safety-supervision runtime for the Unitree G1 humanoid robot.**

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml)
[![CI Audit](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Isaac Sim](https://img.shields.io/badge/Isaac%20Sim-4.5.0-76B900?logo=nvidia)
![Stage](https://img.shields.io/badge/Stage-4J%20in%20progress%20%C2%B7%20P4--A%20done-yellow)

---

## Executive Summary

`g1-deterministic-safety-runtime` is a ROS2-native safety supervision framework for the Unitree G1 humanoid robot (37 DOF). It observes robot state in real time, classifies anomalies by severity, monitors data-flow health, and reacts through a deterministic, **fully governed** recovery layer — all under a single operational authority that policy and learning layers can never override.

The project is engineered to **laboratory rigor** (MIT / NASA / Boston Dynamics style of review). Its central discipline is **operational honesty**: every claim in this repository is classified by what the evidence actually supports, and non-validated behavior is declared with the same prominence as validated results.

This README is the **master index and initial audit document**. It is intended to let an external reviewer understand the project — scope, evidence, architecture, limits — without opening every file.

**Current state at a glance:**

- Deterministic runtime core: implemented and tested (65 tests, CI green).
- ROS2 observability of the simulated G1 (Isaac Sim 4.5): validated.
- Severity-aware observer, health watchdog, integrated recovery, measured latency: validated (Stage 4F, P1–P6 done).
- **Unified launcher** (4G-P1): single command brings up Isaac + observer + watchdog + recovery + orchestrator in strict order, with preflight, objective signal, and robust teardown.
- **Statistical reproducibility — healthy baseline** (4G-P2-A): N=10, 100% PASS, 0 false positives.
- **Statistical reproducibility — induced fall** (4G-P2-B): N=10, 100% PASS. Deterministic fall trigger (it=450, t=54.67s).
- **Governed path TX-011** (4G-P2-C): N=13, 100% PASS. `CONDITION_DETECTED + SECONDARY + EFFECTIVE` → `STABILITY_RISK/R3`.
- **Physical latency t0→t1** (4G-P3-C): N=10, 100% PASS. Fall trigger → SafetyEvent: mean=2474ms, min=2046ms, max=3511ms.
- **Governed orchestrator→recovery path** (4G-P4-D): N=10, 100% PASS. `SafetyAction(/safety_actions)` → recovery: mean t1→t2=1.19ms. DT-4G-003 closed.
- **Operational hygiene** (4G-P5 / DT-4G-004A): active container teardown + blocking preflight.
- **Cause-aware recovery** (4H-P1): recovery differentiates fallen, STALE, FREEZE, NANINF, and TIMESTAMP, with causal logs and validated actions.
- **Recovery policy hardening** (4H-P2): terminal causes (FREEZE/NANINF/TIMESTAMP) bypass cooldown/retry at attempt=1. Policy documented and validated focally.
- **Formalization** (4I): `SAFETY_MODEL_G1.md`, `TRACEABILITY_MATRIX_G1.md`, `POLICY_CLARIFICATION_G1.md` published under `docs/audit/`. DT-4I-001 closed in 4J-P0.
- **Causal traceability** (4J-P1/P2): SafetyEvent → SafetyAction → RecoveryEvent linked by `parent_event_id` across all three routes (R1 governed, R2 direct, R3 terminal).
- **Extended fault injection matrix** (4J-P2-A): 7 fault rows, 4 routes, single-fault experimental control. See `docs/audit/4J_FAULT_INJECTION_MATRIX.md`.
- **Timing traceability** (4J-P3): 6 routes measured. R3 terminal: mean ~3.7ms dispatch. R2 direct: ~1005ms (includes wait_for_primary_restore). TX-011 e2e: 6.130ms (T_e2a=3.503ms + T_a2r=2.627ms). See `docs/audit/4J_TIMING_TRACEABILITY_REPORT.md`.
- **Threshold inventory** (4J-P4-A): 20+ constants extracted from source code, evidence levels assigned, structural findings H1–H5 documented. See `docs/audit/4J_THRESHOLD_CHARACTERIZATION.md`.
- Continuous Integration: **CI Build green · CI Audit green** on `main`.

---

## What This Repository Is

- A **deterministic safety-runtime** for a humanoid: state machine, observer, watchdog, recovery, typed safety events.
- A **reproducible** ROS2 + Docker stack with CI that builds and tests the safety core.
- An **evidence-backed** record: every closed stage has raw logs under `evidence/` and a session report under `docs/current/`.
- A **navigable audit surface**: structured docs, traceable transition matrix, per-session commit history.

## What This Repository Is Not

- **Not** a locomotion or walking controller. The G1 does not yet hold itself upright under active control (passive baseline only).
- **Not** a claim of physical control of a real G1. All current work is simulation / x86 — no Unitree SDK hardware integration.
- **Not** certified compliance with any MIT / NASA / aerospace / medical standard. The repository is *structured for rigorous audit*; it does not claim a certification.
- **Not** a VLA/policy training rig. Learning layers (GR00T, LeRobot, Gemini Robotics) are future and operate **under** safety authority, never above it.

---

## Current Project Stage

| Stage | Description | Status |
|-------|-------------|--------|
| 1 | Infrastructure Base (ROS2, Docker, CI) | ✅ Closed |
| 2 | Operational Discipline (anti-patterns, reproducibility) | ✅ Closed |
| 3A | Semantic Models + ADRs | ✅ Closed |
| 3B | ROS2 Runtime Skeleton (nodes + g1_msgs) | ✅ Closed |
| 3C | Deterministic Transition Logic — 65 tests | ✅ Closed |
| 4A | Infrastructure & DDS characterization | ✅ Closed |
| 4B | Isaac Headless Bring-up (4.2.0) | ✅ Closed |
| 4C | Physical & Control characterization | ✅ Closed |
| 4D | ROS2 feasibility + observability + loop closure | ✅ Closed |
| 4E | Healthy passive baseline + state validation | ✅ Closed |
| 4F | Safety Runtime Enrichment (P1–P6) | ✅ Closed |
| 4G-P0 | Repo migration + portable build + CI hardening | ✅ Closed |
| 4G-P1 | Unified launcher (preflight, objective signal, teardown) | ✅ Closed |
| 4G-P2-A | Statistical reproducibility — healthy baseline N=10 | ✅ Closed |
| 4G-P2-B | Statistical reproducibility — induced fall N=10 | ✅ Closed |
| 4G-P2-C | Governed path TX-011 (SECONDARY/fallen escalation) N=13 | ✅ Closed |
| 4G-P3-C | Physical latency t0→t1 N=10 · mean=2474ms | ✅ Closed |
| 4G-P3-D | End-to-end latency t1→t2 governed path N=10 · mean=1.19ms | ✅ Closed |
| 4G-P4-D | Governed orchestrator→recovery path N=10 · DT-4G-003 closed | ✅ Closed |
| 4G-P5 | Blocking preflight + post-teardown hygiene | ✅ Closed |
| 4H-P1 | Cause-aware intelligent recovery (rule_id/source → differentiated action) | ✅ Closed |
| 4H-P2 | Recovery policy hardening — terminal causes bypass cooldown/retry | ✅ Closed |
| 4I | Formalization (SAFETY_MODEL, TRACEABILITY_MATRIX, POLICY_CLARIFICATION) | ✅ Closed |
| 4J-P0 | Runtime Alignment / DT-4I-001 closure — governed TX-011 self-sufficient | ✅ Closed |
| 4J-P1 | Causal traceability minimum — parent_event_id across R1/R2/R3 | ✅ Closed |
| 4J-P2-prep | Direct path traceability enablement | ✅ Closed |
| 4J-P2-A | Extended Fault Injection Matrix — 7 fault rows, 4 routes | ✅ Closed |
| 4J-P3 | Timing Traceability Report — 6 routes measured | ✅ Closed |
| **4J-P4-A** | **Threshold Inventory — 20+ constants, H1–H5 findings** | **✅ Closed** |
| 4J-P4-B/D/E/F | Threshold controls, boundary sweep, false positive matrix | 🔲 Pending |
| 4J-P5 | Assurance Case + Paper Package | 🔲 Pending |
| 5A | Isaac Lab Bring-up | 🔒 Blocked (GPU ≥ RTX 4080) |
| 5–7 | VLA / Embodied behaviors / Autonomy | ⏳ Future |

---

## Validated Capabilities (with log evidence)

- **Deterministic runtime core (3C):** TransitionEvaluator (TX-001→TX-011), PriorityScheduler (4 buckets), T8Arbitrator, CompoundState. 65 tests; safety core green in CI.
- **ROS2 observability (4D):** G1 observable over real ROS2 cross-container (joints, base pose, IMU, typed foot contacts) on the T4, without the heavy RTX stack.
- **Healthy passive baseline (4E):** G1 stands passively from pose P2 + `z_cmd=0.720` + factory drives. Observer yields zero false positives.
- **Severity-aware observer (4F-P1):** INFO/WARN/CRITICAL. CRITICAL fires on `abs(q.w)<0.80` sustained over 3 fresh consecutive samples (rule 3C2b).
- **Health watchdog (4F-P2):** STALE / FREEZE / NANINF / TIMESTAMP / RATE across 5 topics.
- **Transition matrix (4F-P3):** TX-001→TX-011 traced to method + test + action, derived from source.
- **Integrated pipeline (4F-P4):** 4-component end-to-end: healthy→silence; fall→alarm; Isaac killed→STALE→recovery.
- **Latency t1→t2 direct (4F-P5):** 0.68–8.2 ms on Tesla T4 (observer→recovery direct, ROS timestamps).
- **Fault injection (4F-P6):** 5/5 PASS — frozen IMU, frozen contact, NaN joints, regressive timestamp, lost topic.
- **Unified launcher (4G-P1):** single command, preflight, objective signal wait, 4 nodes + 8 topics verified, robust teardown.
- **Reproducibility baseline sano (4G-P2-A):** N=10, 100% PASS, 0 FP.
- **Reproducibility caída inducida (4G-P2-B):** N=10, 100% PASS. Fall trigger deterministic at it=450, t=54.67s.
- **Governed path TX-011 (4G-P2-C):** N=13, 100% PASS. `CONDITION_DETECTED + SECONDARY + EFFECTIVE` → `(STABLE,NONE)→(STABILITY_RISK,R3)`.
- **Physical latency t0→t1 (4G-P3-C):** N=10, 100% PASS. Fall injection → SafetyEvent: mean=2474ms, min=2046ms, max=3511ms. Includes physical dynamics, sensors, DDS transport, 3-sample rule 3C2b.
- **End-to-end governed latency (4G-P3-D/P4-D):** N=10, 100% PASS. SafetyAction(orchestrator) → recovery: mean=1.19ms, min=0.83ms, max=2.02ms.
- **Operational hygiene (4G-P5 / DT-4G-004A):** active teardown inside `boring_noether` plus blocking preflight.
- **Cause-aware recovery (4H-P1):** recovery differentiates `fallen`, `STALE`, `FREEZE`, `NANINF`, and `TIMESTAMP`. Validated chain: topic/SafetyEvent → watchdog/observer → recovery log `[4H-P1] cause=...` → expected action.
- **Recovery policy hardening (4H-P2):** `TERMINAL_MANUAL_RULE_IDS = {4F-P2-FREEZE, 4F-P2-NANINF, 4F-P2-TIMESTAMP}` bypass cooldown/retry at attempt=1. Focal validation + policy documented.
- **Formalization (4I):** `SAFETY_MODEL_G1.md` (master safety contract), `TRACEABILITY_MATRIX_G1.md` (fault→event→action traceability), `POLICY_CLARIFICATION_G1.md` (TX-009 POLICY_GATED, DT-4F-003 closed).
- **Causal traceability (4J-P1/P2):** `parent_event_id` field propagated SafetyEvent → SafetyAction → RecoveryEvent.notes across R1 governed, R2 direct, and R3 terminal routes.
- **Extended fault injection matrix (4J-P2-A):** 7 fault rows (STALE, FREEZE, NANINF, TIMESTAMP, FALLEN_DIRECT, RATE declared, TX-011 governed). One fault · one route · one trace · one verdict.
- **Timing traceability (4J-P3):** 6 routes. R3 terminal (FREEZE/NANINF/TIMESTAMP): mean 3.7–3.9ms dispatch. R2 direct (STALE/FALLEN_DIRECT): ~1005ms (includes `wait_for_primary_restore` ~1s). TX-011 R1: T_e2e=6.130ms. Limitations declared: N=3 for R2 (MAX_AUTO_RETRIES), N=1 for TX-011 (one-shot orchestrator).
- **Threshold inventory (4J-P4-A):** 20+ threshold constants extracted from source (watchdog_g1, cross_consistency_observer, safety_orchestrator_g1, recovery_g1). Evidence levels assigned. Structural findings H1–H5 documented. See `docs/audit/4J_THRESHOLD_CHARACTERIZATION.md`.

---

## End-to-End Latency Summary

| Tramo | Description | N | Mean | Min | Max |
|-------|-------------|---|------|-----|-----|
| t0→t1 | Fall injection → SafetyEvent (physical + DDS + 3C2b rule) | 10 | 2474ms | 2046ms | 3511ms |
| t1→t2 | SafetyEvent → recovery action (governed path via /safety_actions) | 10 | 1.19ms | 0.83ms | 2.02ms |
| t1→t2 | SafetyEvent → recovery action (direct fallback path) | varies | ~1ms | 0.68ms | 8.2ms |
| Internal dispatch R3 | watchdog emit → RecoveryEvent (terminal routes, harness) | 10 | ~3.8ms | 3.5ms | 4.6ms |
| TX-011 e2e | SafetyEvent → SafetyAction → RecoveryEvent (governed) | 1 | 6.130ms | — | — |
| dispatch t1→t2 internal | recovery_g1 internal dispatch (log-based, 4F-P5) | varies | ~0.86ms | — | — |

> **Note on R2 ~1005ms:** includes `wait_for_primary_restore` (~1s simulated). Not dispatch pure. Internal dispatch is ~0.86ms — these two metrics measure different things and must not be mixed in paper claims.

---

## State-of-the-Art Vision — 10 Pillars

| # | Pillar | What it requires | Closure criterion | Microphase | Status |
|---|---|---|---|---|---|
| 1 | Governed Runtime Assurance | Every critical detection passes through orchestrator → recovery | Governed transition verifiable in `/system_state` or `/safety_actions` | 4G-P2-C + 4G-P4-D | ✅ **Closed** |
| 2 | Semantic event contract | `event_type`, `source_authority`, `rule_id`, `severity` compatible across nodes | Formal contract table + tests | 4G-P2-C / 4I / 4J-P1 | Partial — causal traceability added 4J-P1; native `action_id` deferred (DT-4J-001) |
| 3 | Physical latency t0→t1 | Measure physical event → ROS detection with aligned clocks | min/mean/std/max/p95 of fall→SafetyEvent | 4G-P3-C | ✅ **Closed** |
| 4 | End-to-end latency t0→t3 | t0→t1→t2→t3 measured per stage | Per-stage report, not mixed | 4G-P3-D + P4-D + 4J-P3 | Partial — t0→t2 closed; internal dispatch R1/R2/R3 measured 4J-P3; t3 pending |
| 5 | Deterministic safety-first scheduling | Callback priority measurable | Measured profile: lower jitter, lower p95 | 4G-P4 | Partial |
| 6 | Runtime verification | Formal property monitors | "If FALL_TRIGGER → SafetyEvent"; "If CRITICAL → recovery before deadline D" | 4J-P5 | 🔲 Pending |
| 7 | Intelligent recovery | Recovery differentiated by rule_id/cause | Fallen/STALE/FREEZE/NANINF/TIMESTAMP trigger distinct tested actions | 4H-P1 | ✅ **Closed** |
| 8 | Formal lifecycle supervisor | configure→activate→monitor→recover→shutdown | Supervisor detects dead node, recovers in order | 4H/4G-P5 | Partial (P5 hygiene) |
| 9 | Auditable assurance case | Claim→Evidence→Limitations→Mitigation | Document what is proven, what is not | 4I + 4J-P4 | ✅ Closed (4I) — threshold characterization adds depth (4J-P4) |
| 10 | Expanded fault-injection matrix | Freeze, stale, NaN, contact inconsistency, DDS latency, duplicates | N≥10 per fault class | 4J-P2-A | Partial — 7 fault rows closed; threshold controls (P4-B/C) pending |

---

## Explicit Non-Validated Boundaries

These are stated as prominently as the validated results — this is the core discipline of the project.

- **Deadline D for recovery** — t0→t1=~2474ms and t1→t2=~1.19ms are measured, but no formal SLA or deadline has been defined.
- **UUID end-to-end traceability** (DT-4G-002) — causal `parent_event_id` added in 4J-P1/P2. Native `action_id` and `parent_action_id` fields deferred (DT-4J-001).
- **Container reaper limitation** (DT-4G-004B) — `<defunct>` zombie processes accumulate because PID1 in `boring_noether` does not reap children. Non-blocking for normal runs. Fix deferred to `--init` flag.
- **Thresholds** — `FALLEN_W_CRITICAL=0.80`, `FREEZE_N=5`, `MIN_RATE_HZ=3.0` and others are pragmatic values (DT-4F-001). Partially characterized in 4J-P4-A; boundary sweep pending P4-D.
- **FREEZE IMU false positive** (DT-4F-004) — robot immobile with repeating IMU values may trigger FREEZE. Not reproduced but not formally excluded. Negative control experiment pending P4-B.
- **Active PD control** (DT-4E-006) — the G1 does not yet stand under active control. Passive baseline only.
- **Hardware** — no Unitree SDK integration. All results are simulation (Isaac Sim 4.5.0, Tesla T4).

---

## Architecture Overview

The runtime is composed of five ROS2 nodes operating under a **single authority hierarchy**:

```
Isaac Sim (physics + telemetry publisher)
        │
        ▼  /g1/imu · /g1/contact/* · /joint_states
cross_consistency_observer  ──SafetyEvent──▶  safety_orchestrator_g1
        │                                              │
        │  (direct fallback)                    TX-011 SafetyAction
        │                                              │
        └──────────────────────────────────▶  recovery_g1
                                                       │
                                               /recovery_events
watchdog_g1 ──SafetyEvent──▶ safety_orchestrator_g1
```

**Authority rule:** observer detects → orchestrator governs transition → recovery acts. The orchestrator is the single point of state authority; no node can modify safety state without passing through it.

---

## Package Map

| Package | Role | Validated in |
|---------|------|-------------|
| `g1_msgs` | Typed safety vocabulary (SafetyEvent, SystemState, SafetyAction, RecoveryEvent, FootContact) | 3B |
| `cross_consistency_observer` | IMU × foot-contact coherence, severity INFO/WARN/CRITICAL, 3C2b rule, `parent_event_id` propagation | 4F-P1 / 4G-P2-B/C / 4J-P2 |
| `watchdog_g1` | STALE / FREEZE / NANINF / TIMESTAMP / RATE across 5 topics | 4F-P2 / 4J-P2-A |
| `safety_orchestrator_g1` | TX-001→TX-011 evaluator, compound state, `/safety_actions` publisher, `parent_event_id` in SafetyAction | 3C / 4G-P2-C / 4G-P4 / 4J-P1 |
| `recovery_g1` | Recovery executor — governed `/safety_actions` + direct fallback, cause-aware routing, 5 actions, `parent_event_id` in RecoveryEvent.notes | 3C / 4F-P4 / 4G-P4-D / 4H-P1 / 4J-P2 |
| `test_g1_safety_layer` | Level-4 launch integration tests | 3C / 4G-P2-C |
| `g1_description` | Robot description (XACRO, TF tree) | 3B |

---

## Repository Tree

    g1-deterministic-safety-runtime/
    ├── .github/workflows/          # CI definitions (ci-build.yml, ci-audit.yml)
    ├── docs/
    │   ├── architecture/           # ADRs (ARCHITECTURE_DECISIONS.md)
    │   ├── audit/                  # TRANSITION_MATRIX_G1, TRACEABILITY_MATRIX_G1,
    │   │                           # POLICY_CLARIFICATION_G1, 4J_FAULT_INJECTION_MATRIX,
    │   │                           # 4J_TIMING_TRACEABILITY_REPORT, 4J_THRESHOLD_CHARACTERIZATION
    │   ├── current/                # thesis v28, bootstrap v26, session reports 4J-P0 through P4-A
    │   ├── archive/                # historical versions (fully traceable)
    │   └── phases/                 # per-stage notes
    ├── evidence/                   # raw logs — proof of what actually happened
    │   └── 4J/                     # P3_TIMING/ (6 CSVs + summaries), P4_THRESHOLDS/ (pending P4-B+)
    ├── runs/                       # 4G run logs (launcher + A/B/C/D/E per corrida)
    ├── sim_runtime/
    │   ├── 4F/                     # Isaac extension (g1ext_combo), .kit file, FALL_TRIGGER it=450
    │   ├── 4G/                     # launch_pipeline.py (P5 blocking preflight), analyze_runs.py
    │   ├── 4J/                     # harnesses: P3 timing matrix, P4 threshold inventory (pending P4-B+)
    │   └── common/fastdds_udp.xml
    ├── src/                        # ── SAFETY RUNTIME CORE (ROS2 packages) ──
    │   ├── g1_msgs/
    │   ├── cross_consistency_observer/
    │   ├── watchdog_g1/
    │   ├── safety_orchestrator_g1/
    │   ├── recovery_g1/
    │   └── test_g1_safety_layer/
    └── legacy/                     # AGV-heritage packages (COLCON_IGNORE, history preserved)

---

## Evidence Map

| Stage | Raw evidence | Report |
|-------|--------------|--------|
| 4C — physical/control | `evidence/4C/` | `docs/phases/4C/` |
| 4D-3 — ROS2 observability | `evidence/4D-3/` | `docs/archive/informe_etapa_4D3_2026-06-08.md` |
| 4E — healthy baseline | `docs/experiments/4E_P4_2026-06-15/` | `docs/current/` |
| 4F — safety enrichment | run logs per phase | `docs/current/informe_etapa_4F_2026-06-16.md` |
| 4G-P2-A — baseline N=10 | `runs/4G/20260617_131144…135740` | `docs/current/informe_etapa_4G_parcial_2026-06-17.md` |
| 4G-P2-B — fall N=10 | `runs/4G/20260617_145141…162117` | `docs/current/informe_etapa_4G_P2B_2026-06-17.md` |
| 4G-P2-C — TX-011 N=13 | `runs/4G/20260618_081905…101200` | `docs/current/informe_etapa_4G_P2C_2026-06-18.md` |
| 4G-P3-C — t0→t1 N=10 | `runs/4G/20260618_133215…135904` | `docs/current/informe_etapa_4G_P3_P5_2026-06-18.md` |
| 4G-P4-D — governed path N=10 | `runs/4G/20260618_160555…164129` | `docs/current/informe_etapa_4G_P3_P5_2026-06-18.md` |
| 4H-P1/P2 + DT-4G-004 | harness logs + launcher regression | `docs/current/informe_etapa_4G_004_4H_P1_2026-06-19.md` |
| 4I — formalization | — | `docs/audit/TRACEABILITY_MATRIX_G1.md` · `POLICY_CLARIFICATION_G1.md` · `docs/current/SAFETY_MODEL_G1.md` |
| 4J-P2-A — fault injection | harness logs | `docs/audit/4J_FAULT_INJECTION_MATRIX.md` |
| **4J-P3 — timing** | **`evidence/4J/P3_TIMING/`** | **`docs/audit/4J_TIMING_TRACEABILITY_REPORT.md`** |
| **4J-P4-A — threshold inventory** | **code audit (HEAD 9777103)** | **`docs/audit/4J_THRESHOLD_CHARACTERIZATION.md`** |

---

## CI Status

| Workflow | Trigger | Scope | Status |
|----------|---------|-------|--------|
| **CI Build** | every push / PR to `main` | build images + test safety-core packages | ✅ green |
| **CI Audit** | weekly · tag `v*` · manual | full `rosdep install` + build + test all packages | ✅ green |

**What green means:** the safety runtime core compiles and its tests pass in a clean container. It does not validate hardware behavior, physical timing, or locomotion.

---

## Build / Test Commands

Safety-core unit tests (no hardware, no Isaac):

    docker exec boring_noether bash -c \
      "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && \
       python3 -m pytest src/safety_orchestrator_g1/test/test_orchestrator_transitions.py -v"

Unified launcher (4G, with P5 blocking preflight and DT-4G-004A active teardown):

    cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py

Full build + test (as CI Audit):

    source /opt/ros/humble/setup.bash
    rosdep install --from-paths src --ignore-src -r -y
    colcon build
    source install/setup.bash
    colcon test && colcon test-result --verbose

> **Note:** use `colcon build` without `--symlink-install` when `install/g1_msgs` is mounted into another container (Isaac Sim). Symlinks break cross-container imports.

---

## Active Technical Debt

| ID | Description | Priority | Status |
|----|-------------|----------|--------|
| DT-4E-001 | SAFETY_MODEL_G1.md | High | ✅ Closed — 4I-P1 |
| DT-4E-006 | Active PD control deferred | High | Open |
| DT-4F-001 | Thresholds pragmatic, pending calibration | Medium | Partially characterized — 4J-P4-A inventory complete; boundary sweep pending P4-D |
| DT-4F-002 | TX-006b/c without explicit test | Medium | Open |
| DT-4F-003 | TX-009 POLICY_GATED exact condition | Low | ✅ Closed — 4I-P3 |
| DT-4F-004 | FREEZE IMU potential false positive | Medium | Characterized (4J-P4-A); negative control pending P4-B |
| DT-4F-005 | t0→t1 latency | Medium | ✅ Closed — 4G-P3-C |
| DT-4G-001 | TX-011 governed escalation SECONDARY/fallen | High | ✅ Closed |
| DT-4G-002 | t1→t2 UUID/event_id traceability (paper-grade) | Medium | Partial — 4J-P1 causal traceability; native fields deferred |
| DT-4G-003 | Governed path orchestrator→recovery | High | ✅ Closed — 4G-P4-D |
| DT-4G-004A | Active teardown + defunct-aware hygiene | Medium | ✅ Closed — 4G-P5 |
| DT-4G-004B | Zombies `<defunct>` by PID1/reaper in `boring_noether` | Low | Open, non-blocking |
| DT-4I-001 | Discrepancy TX-011 governed recovery routing | High | ✅ Closed — 4J-P0 |
| **DT-4J-001** | **Full native traceability** (`action_id`, `parent_action_id`, `RecoveryEvent.parent_event_id` native fields) | **Medium** | **Open** |

---

## Roadmap

- **4H-P1 — Intelligent recovery:** ✅ Closed. Recovery action differentiated by cause: fallen, STALE, FREEZE, NANINF, TIMESTAMP.
- **4H-P2 — Recovery policy hardening:** ✅ Closed. Terminal causes bypass cooldown/retry. Policy documented.
- **4I — Formalization:** ✅ Closed. SAFETY_MODEL_G1.md, TRACEABILITY_MATRIX_G1.md, POLICY_CLARIFICATION_G1.md — see `docs/audit/` and `docs/current/`.
- **4J — Paper preparation:** 🔄 In progress. Causal traceability ✅ · Fault injection matrix ✅ · Timing traceability ✅ · Threshold inventory ✅ · Threshold controls / false positive matrix / assurance case: pending.
- **5A — Isaac Lab:** 🔒 Blocked on T4 (needs GPU ≥ RTX 4080).

---

## Review Notes for External Auditors

- **Start here**, then `docs/current/` for the thesis (v28) and latest session reports.
- **Safety contract:** `docs/current/SAFETY_MODEL_G1.md` (master contract), `docs/audit/TRACEABILITY_MATRIX_G1.md` (fault traceability), `docs/audit/POLICY_CLARIFICATION_G1.md` (operational policies).
- **4J paper evidence:** `docs/audit/4J_FAULT_INJECTION_MATRIX.md` · `4J_TIMING_TRACEABILITY_REPORT.md` · `4J_THRESHOLD_CHARACTERIZATION.md`.
- **Verify claims** against `evidence/4J/` (timing raw data) and `docs/audit/TRANSITION_MATRIX_G1.md`.
- **Reproduce** via the CI Audit recipe above; the safety core is container-clean.
- **Scope honestly:** this is a simulation-validated safety runtime, not hardware-certified. Boundaries are explicit in "Explicit Non-Validated Boundaries".
- **Heritage:** the project migrated from an AGV pipeline; that lineage is quarantined under `legacy/`, not hidden.

---

*G1 Deterministic Safety Runtime — github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
*Status 2026-06-23: 3C ✅ · 4A–4I ✅ · 4J 🔄 (P0✅ P1✅ P2-prep✅ P2-A✅ P3✅ P4-A✅) · 5A 🔒*
*Audit-readiness mapped to MIT / NASA / Boston Dynamics rigor — not certified compliance.*
