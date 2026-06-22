# G1 Deterministic Safety Runtime

**A deterministic, auditable safety-supervision runtime for the Unitree G1 humanoid robot.**

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml)
[![CI Audit](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Isaac Sim](https://img.shields.io/badge/Isaac%20Sim-4.5.0-76B900?logo=nvidia)
![Stage](https://img.shields.io/badge/Stage-4I%20closed%20%C2%B7%204J%20next-green)

---

## Executive Summary

`g1-deterministic-safety-runtime` is a ROS2-native safety supervision framework for the Unitree G1 humanoid robot (37 DOF). It observes robot state in real time, classifies anomalies by severity, monitors data-flow health, and reacts through a deterministic, **fully governed** recovery layer — all under a single operational authority that policy and learning layers can never override.

The project is engineered to **laboratory rigor** (MIT / NASA / Boston Dynamics style of review). Its central discipline is **operational honesty**: every claim in this repository is classified by what the evidence actually supports, and non-validated behavior is declared with the same prominence as validated results.

This README is the **master index and initial audit document**. It is intended to let an external reviewer understand the project — scope, evidence, architecture, limits — without opening every file.

**Current state at a glance:**

- Deterministic safety runtime core: implemented and tested (65 tests, CI green).
- ROS2 observability of the simulated G1 (Isaac Sim 4.5): validated.
- Severity-aware observer, health watchdog, integrated recovery, measured latency: validated (Stage 4F, P1–P6 done).
- **Unified launcher** (4G-P1): single command brings up Isaac + observer + watchdog + recovery + orchestrator in strict order, with preflight, objective signal, and robust teardown.
- **Statistical reproducibility — healthy baseline** (4G-P2-A): N=10, 100% PASS, 0 false positives.
- **Statistical reproducibility — induced fall** (4G-P2-B): N=10, 100% PASS. Deterministic fall trigger (it=450, t=54.67s).
- **Governed path TX-011** (4G-P2-C): N=13, 100% PASS. `CONDITION_DETECTED + SECONDARY + EFFECTIVE` → `STABILITY_RISK/R3`.
- **Physical latency t0→t1** (4G-P3-C): N=10, 100% PASS. Fall trigger → SafetyEvent: mean=2474ms, min=2046ms, max=3511ms.
- **Governed orchestrator→recovery path** (4G-P4-D): N=10, 100% PASS. `SafetyAction(/safety_actions)` → recovery: mean t1→t2=1.19ms. DT-4G-003 closed.
- **Operational hygiene** (4G-P5 / DT-4G-004A): active container teardown + blocking preflight; no `docker restart` required for normal consecutive runs due to ACTIVE processes or `/safety_events` publishers.
- **Cause-aware recovery** (4H-P1): recovery differentiates fallen, STALE, FREEZE, NANINF, and TIMESTAMP, with causal logs and validated actions.
- Continuous Integration: **CI Build green · CI Audit green** on `main`.

---

## What This Repository Is

- A **deterministic safety-runtime** for a humanoid: state machine, observer, watchdog, recovery, typed safety events.
- A **reproducible** ROS2 + Docker stack with CI that builds and tests the safety core.
- An **evidence-backed** record: every closed stage has raw logs under `runs/` and a session report under `docs/current/`.
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
| **4G-P5** | **Blocking preflight + post-teardown hygiene** | **✅ Closed** |
| **4H-P1** | **Cause-aware intelligent recovery (rule_id/source → differentiated action)** | **✅ Closed** |
| **4H-P2** | **Recovery policy hardening — terminal causes bypass cooldown/retry** | **✅ Closed** |
| 4I | Formalization (semantic models, thresholds, assurance case) | ✅ Closed |
| 4J | Paper preparation + fault injection matrix | 🔲 Pending |
| 5A | Isaac Lab Bring-up | 🔒 Blocked (out of T4 critical path) |
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
- **End-to-end governed latency t1→t2 (4G-P3-D/P4-D):** N=10, 100% PASS. SafetyAction(orchestrator) → recovery: mean=1.19ms, min=0.83ms, max=2.02ms.
- **Governed orchestrator→recovery path (4G-P4-D):** `SafetyAction` subscriber in `recovery_g1` consuming `/safety_actions`. TX-011 → `stabilization_mode` → recovery in all 10 runs. Temporal dedup guard (5s window). DT-4G-003 closed.
- **Operational hygiene (4G-P5 / DT-4G-004A):** active teardown inside `boring_noether` plus blocking preflight. Consecutive normal runs no longer require `docker restart` for ACTIVE process or `/safety_events` publisher residue. Remaining `<defunct>` zombies are classified as DT-4G-004B, non-blocking.
- **Cause-aware recovery (4H-P1):** recovery differentiates `fallen`, `STALE`, `FREEZE`, `NANINF`, and `TIMESTAMP`. Validated chain: topic/SafetyEvent → watchdog/observer → recovery log `[4H-P1] cause=...` → expected action.

---

## End-to-End Latency Summary

| Tramo | Description | N | Mean | Min | Max |
|-------|-------------|---|------|-----|-----|
| t0→t1 | Fall injection → SafetyEvent (physical + DDS + 3C2b rule) | 10 | 2474ms | 2046ms | 3511ms |
| t1→t2 | SafetyEvent → recovery action (governed path via /safety_actions) | 10 | 1.19ms | 0.83ms | 2.02ms |
| t1→t2 | SafetyEvent → recovery action (direct fallback path) | varies | ~1ms | 0.68ms | 8.2ms |

---

## State-of-the-Art Vision — 10 Pillars

| # | Pillar | What it requires | Closure criterion | Microphase | Status |
|---|---|---|---|---|---|
| 1 | Governed Runtime Assurance | Every critical detection passes through orchestrator → recovery | Governed transition verifiable in `/system_state` or `/safety_actions` | 4G-P2-C + 4G-P4-D | ✅ **Closed** |
| 2 | Semantic event contract | `event_type`, `source_authority`, `rule_id`, `severity` compatible across nodes | Formal contract table + tests | 4G-P2-C ✅ / 4I | Partial |
| 3 | Physical latency t0→t1 | Measure physical event → ROS detection with aligned clocks | min/mean/std/max/p95 of fall→SafetyEvent | 4G-P3-C | ✅ **Closed** |
| 4 | End-to-end latency t0→t3 | t0→t1→t2→t3 measured per stage | Per-stage report, not mixed | 4G-P3-D + P4-D | ✅ t0→t2 closed / t3 pending |
| 5 | Deterministic safety-first scheduling | Callback priority measurable | Measured profile: lower jitter, lower p95 | 4G-P4 | Partial |
| 6 | Runtime verification | Formal property monitors | "If FALL_TRIGGER → SafetyEvent"; "If CRITICAL → recovery before deadline D" | 4I/4J | 🔲 Pending |
| 7 | Intelligent recovery | Recovery differentiated by rule_id/cause | Fallen/STALE/FREEZE/NANINF/TIMESTAMP trigger distinct tested actions | 4H-P1 | ✅ **Closed** |
| 8 | Formal lifecycle supervisor | configure→activate→monitor→recover→shutdown | Supervisor detects dead node, recovers in order | 4H/4G-P5 | Partial (P5 hygiene) |
| 9 | Auditable assurance case | Claim→Evidence→Limitations→Mitigation | Document what is proven, what is not | 4I | ✅ Closed |
| 10 | Expanded fault-injection matrix | Freeze, stale, NaN, contact inconsistency, DDS latency, duplicates | N≥10 per fault class | 4H/4J | 🔲 Pending |

---

## Explicit Non-Validated Boundaries

These are stated as prominently as the validated results — this is the core discipline of the project.

- **Deadline D for recovery** — t0→t1=~2474ms and t1→t2=~1.19ms are measured, but no formal SLA or deadline has been defined. This requires calibration from 4H recovery experiments and threat model in 4I.
- **UUID end-to-end traceability** (DT-4G-002) — t1→t2 is measured but not correlated by UUID/event_id across the full pipeline. Parser infrastructure exists; formal traceability deferred to paper phase.
- **Container reaper limitation** (DT-4G-004B) — `<defunct>` zombie processes can accumulate because PID1 in `boring_noether` does not reap children. They do not execute or publish; non-blocking for normal runs. Real fix deferred to container lifecycle / `--init`.
- **Thresholds** — `FALLEN_W_CRITICAL=0.80` and `FALLEN_W_WARN=0.85` are pragmatic calibration values (DT-4F-001), not derived from a formal threat model.
- **Recovery policy tuning** — 4H-P1 differentiates recovery by cause, but policy hardening closed in 4H-P2: terminal causes bypass cooldown/retry. Simultaneous fault priority and larger N deferred to 4J.
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
| `cross_consistency_observer` | IMU × foot-contact coherence, severity INFO/WARN/CRITICAL, 3C2b rule | 4F-P1 / 4G-P2-B/C |
| `watchdog_g1` | STALE / FREEZE / NANINF / TIMESTAMP / RATE across 5 topics | 4F-P2 |
| `safety_orchestrator_g1` | TX-001→TX-011 evaluator, compound state, `/safety_actions` publisher | 3C / 4G-P2-C / 4G-P4 |
| `recovery_g1` | Recovery executor — governed `/safety_actions` subscriber + direct fallback, cause-aware 4H-P1 routing, 5 actions, subprocess isolation | 3C / 4F-P4 / 4G-P4-D / 4H-P1 |
| `test_g1_safety_layer` | Level-4 launch integration tests | 3C / 4G-P2-C |
| `g1_description` | Robot description (XACRO, TF tree) | 3B |

---

## Repository Tree

    g1-deterministic-safety-runtime/
    ├── .github/workflows/          # CI definitions (ci-build.yml, ci-audit.yml)
    ├── docs/
    │   ├── architecture/           # ADRs (ARCHITECTURE_DECISIONS.md)
    │   ├── audit/                  # AUDIT_READINESS_CHECKLIST, TRANSITION_MATRIX_G1
    │   ├── current/                # source-of-truth: thesis v24, bootstrap v21, current session reports
    │   ├── archive/                # historical versions (fully traceable)
    │   └── phases/                 # per-stage notes
    ├── evidence/                   # raw logs — proof of what actually happened
    ├── runs/                       # 4G run logs (launcher + A/B/C/D/E per corrida)
    ├── sim_runtime/
    │   ├── 4F/                     # Isaac extension (g1ext_combo), .kit file, FALL_TRIGGER it=450
    │   ├── 4G/                     # launch_pipeline.py (P5 blocking preflight), analyze_runs.py (--phase p3b)
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
| 4E — healthy baseline | `docs/experiments/4E_P4_2026-06-15/` | `docs/current/` (thesis v23) |
| 4F — safety enrichment | run logs per phase | `docs/current/informe_etapa_4F_2026-06-16.md` |
| 4G-P2-A — baseline N=10 | `~/runs/4G/20260617_131144…135740` | `docs/current/informe_etapa_4G_parcial_2026-06-17.md` |
| 4G-P2-B — fall N=10 | `~/runs/4G/20260617_145141…162117` | `docs/current/informe_etapa_4G_P2B_2026-06-17.md` |
| 4G-P2-C — TX-011 N=13 | `~/runs/4G/20260618_081905…101200` | `docs/current/informe_etapa_4G_P2C_2026-06-18.md` |
| **4G-P3-C — t0→t1 N=10** | **`~/runs/4G/20260618_133215…135904`** | **`docs/current/informe_etapa_4G_P3_P5_2026-06-18.md`** |
| **4G-P4-D — governed path N=10** | **`~/runs/4G/20260618_160555…164129`** | **`docs/current/informe_etapa_4G_P3_P5_2026-06-18.md`** |
| **DT-4G-004 + 4H-P1 — teardown + cause-aware recovery** | **harness logs + launcher regression** | **`docs/current/informe_etapa_4G_004_4H_P1_2026-06-19.md`** |

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

    # Normal consecutive runs no longer require docker restart for ACTIVE residue.
    # If DT-4G-004B zombie accumulation becomes operationally noisy, restart remains allowed as lab hygiene.
    cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py

Run analysis (P3/P4 metrics):

    python3 sim_runtime/4G/analyze_runs.py --phase p3b --since <YYYYMMDD_HHMMSS>

Full build + test (as CI Audit):

    source /opt/ros/humble/setup.bash
    rosdep install --from-paths src --ignore-src -r -y
    colcon build
    source install/setup.bash
    colcon test && colcon test-result --verbose

> **Note:** use `colcon build` without `--symlink-install` when `install/g1_msgs` is mounted into another container (Isaac Sim). Symlinks break cross-container imports.

---

## Active Technical Debt

| ID | Description | Priority |
|----|-------------|----------|
| DT-4E-001 | SAFETY_MODEL_G1.md — `docs/current/SAFETY_MODEL_G1.md` | ✅ Closed by 4I-P1 |
| DT-4E-006 | Active PD control deferred | High |
| DT-4G-001 | TX-011 governed escalation SECONDARY/fallen | ✅ Closed |
| DT-4G-002 | t1→t2 UUID/event_id traceability (paper-grade) | Medium |
| DT-4G-003 | Governed path orchestrator→recovery | ✅ Closed |
| DT-4G-004A | Active teardown + defunct-aware hygiene; no restart required for normal consecutive runs | ✅ Closed |
| **DT-4G-004B** | **Zombies `<defunct>` by PID1/reaper in `boring_noether`** | **Low** |
| DT-4F-001 | Thresholds pragmatic, pending calibration | Medium |
| DT-4F-002 | TX-006b/c without explicit test | Medium |
| DT-4F-004 | FREEZE IMU potential false positive | Medium |
| DT-4F-005 | t0→t1 latency | ✅ Closed (4G-P3-C) |
| DT-4F-003 | TX-009 POLICY_GATED exact condition clarified — `docs/audit/POLICY_CLARIFICATION_G1.md` | ✅ Closed by 4I-P3 |

---

## Roadmap

- **4H-P1 — Intelligent recovery:** ✅ Closed. Recovery action differentiated by cause: fallen, STALE, FREEZE, NANINF, TIMESTAMP.
- **4H-P2 — Recovery policy hardening:** ✅ Closed. Terminal causes (FREEZE/NANINF/TIMESTAMP) bypass cooldown/retry. Validated focally. Policy documented.
- **4I — Formalization:** ✅ Closed. SAFETY_MODEL_G1.md, TRACEABILITY_MATRIX_G1.md, POLICY_CLARIFICATION_G1.md — see `docs/audit/` and `docs/current/`.
- **4J — Paper preparation:** fault injection matrix extended (N≥10 per fault class), runtime verification properties.
- **5A — Isaac Lab:** blocked on T4 (needs GPU ≥ RTX 4080).

---

## Review Notes for External Auditors

- **Start here**, then `docs/current/` for the full thesis (v23) and latest session reports.
- **Start with the formal safety model:** `docs/current/SAFETY_MODEL_G1.md` (master contract), `docs/audit/TRACEABILITY_MATRIX_G1.md` (fault traceability), `docs/audit/POLICY_CLARIFICATION_G1.md` (operational policies).
- **Verify claims** against `runs/4G/` (raw logs per corrida) and `docs/audit/TRANSITION_MATRIX_G1.md`.
- **Reproduce** via the CI Audit recipe above; the safety core is container-clean.
- **Scope honestly:** this is a simulation-validated safety runtime, not hardware-certified. Boundaries are explicit in "Explicit Non-Validated Boundaries".
- **Heritage:** the project migrated from an AGV pipeline; that lineage is quarantined under `legacy/`, not hidden.

---

*G1 Deterministic Safety Runtime — github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
*Status 2026-06-21: 3C ✅ · 4A–4F ✅ · 4G ✅ · 4H ✅ · 4I ✅ · 4J 🔲 · 5A 🔒*
*Audit-readiness mapped to MIT / NASA / Boston Dynamics rigor — not certified compliance.*
