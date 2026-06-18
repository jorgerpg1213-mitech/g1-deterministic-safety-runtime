# G1 Deterministic Safety Runtime

**A deterministic, auditable safety-supervision runtime for the Unitree G1 humanoid robot.**

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml)
[![CI Audit](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Isaac Sim](https://img.shields.io/badge/Isaac%20Sim-4.5.0-76B900?logo=nvidia)
![Stage](https://img.shields.io/badge/Stage-4G%20P2--B%20closed%20%C2%B7%20P2--C%20pending-yellow)

---

## Executive Summary

`g1-deterministic-safety-runtime` is a ROS2-native safety supervision framework for the Unitree G1 humanoid robot (37 DOF). It observes robot state in real time, classifies anomalies by severity, monitors data-flow health, and reacts through a deterministic recovery layer — all under a single operational authority that policy and learning layers can never override.

The project is engineered to **laboratory rigor** (MIT / NASA / Boston Dynamics style of review). Its central discipline is **operational honesty**: every claim in this repository is classified by what the evidence actually supports, and non-validated behavior is declared with the same prominence as validated results.

This README is the **master index and initial audit document**. It is intended to let an external reviewer understand the project — scope, evidence, architecture, limits — without opening every file.

**Current state at a glance:**

- Deterministic safety runtime core: implemented and tested (86 local Level-4 tests, CI green).
- ROS2 observability of the simulated G1 (Isaac Sim 4.5): validated.
- Severity-aware observer, health watchdog, integrated recovery, measured latency: validated (Stage 4F, P1–P6 done).
- **Unified launcher** (4G-P1): single command brings up Isaac + observer + watchdog + recovery + orchestrator in strict order, with preflight, objective signal, and robust teardown.
- **Statistical reproducibility — healthy baseline** (4G-P2-A): N=10, 100% PASS, 0 false positives, stable timing.
- **Statistical reproducibility — induced fall** (4G-P2-B): N=10, 100% PASS. Deterministic fall trigger (it=450, t=54.67s). Direct path observer→recovery latency 1–156ms. Governed path (observer→orchestrator→recovery) identified as architectural debt (DT-4G-001 / TX-011).
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
| 3C | Deterministic Transition Logic — 86 tests | ✅ Closed |
| 4A | Infrastructure & DDS characterization | ✅ Closed |
| 4B | Isaac Headless Bring-up (4.2.0) | ✅ Closed |
| 4C | Physical & Control characterization | ✅ Closed |
| 4D | ROS2 feasibility + observability + loop closure | ✅ Closed |
| 4E | Healthy passive baseline + state validation | ✅ Closed |
| 4F | Safety Runtime Enrichment (P1–P6) | ✅ Closed |
| 4G-P0 | Repo migration + portable build + CI hardening | ✅ Closed |
| 4G-P1 | Unified launcher (5-terminal, preflight, objective signal) | ✅ Closed |
| 4G-P2-A | Statistical reproducibility — healthy baseline N=10 | ✅ Closed |
| 4G-P2-B | Statistical reproducibility — induced fall N=10 | ✅ Closed |
| 4G-P2-C | Governed path TX-011 (SECONDARY/fallen escalation) | 🔲 Pending |
| 4G-P3 | t0→t1 clock sync Isaac↔ROS2 | 🔲 Pending |
| 4H | Intelligent recovery (rule_id → differentiated action) | 🔲 Pending |
| 4I | Formalization (semantic models, thresholds, threat model) | 🔲 Pending |
| 5A | Isaac Lab Bring-up | 🔒 Blocked (out of T4 critical path) |
| 5–7 | VLA / Embodied behaviors / Autonomy | ⏳ Future |

---

## Validated Capabilities (with log evidence)

- **Deterministic runtime core (3C):** TransitionEvaluator (TX-001→TX-010), PriorityScheduler (4 buckets), T8Arbitrator, CompoundState. 86 local Level-4 tests; safety core green in CI.
- **ROS2 observability (4D):** G1 observable over real ROS2 cross-container (joints, base pose, IMU, typed foot contacts) on the T4, without the heavy RTX stack.
- **Healthy passive baseline (4E):** G1 stands passively from pose P2 + `z_cmd=0.720` + factory drives. Observer yields zero false positives. Healthy→fall transition captured in telemetry.
- **Severity-aware observer (4F-P1):** INFO/WARN/CRITICAL. CRITICAL fires on `abs_w<0.80` sustained over 3 fresh samples.
- **Health watchdog (4F-P2):** STALE / FREEZE / NANINF / TIMESTAMP / RATE across 5 topics.
- **Transition matrix (4F-P3):** TX-001→TX-010 traced to method + test + action, derived from source.
- **Integrated pipeline (4F-P4):** 4-component end-to-end: healthy→silence; fall→alarm; Isaac killed→STALE→recovery.
- **Latency t1→t2 (4F-P5):** 0.68–8.2 ms on Tesla T4 (observer→recovery, ROS timestamps).
- **Fault injection (4F-P6):** 5/5 PASS — frozen IMU, frozen contact, NaN joints, regressive timestamp, lost topic.
- **Unified launcher (4G-P1):** single command, preflight 7/7, objective signal wait, 4 nodes + 8 topics verified, robust teardown. Commit `7a604ab`.
- **Reproducibility baseline sano (4G-P2-A):** N=10, 100% PASS, 0 FP, t_marker=34–36s, t_bcd=12–13s. Commit `ce9b715`.
- **Reproducibility caída inducida (4G-P2-B):** N=10, 100% PASS. Fall trigger deterministic at it=450, t=54.67s from baseline. Observer CRITICAL detected in all runs (abs_w 0.57–0.71). Direct path observer→recovery latency 1–156ms. Commits `497f0a4`, `86a32c6`.

---

## Explicit Non-Validated Boundaries

These are stated as prominently as the validated results — this is the core discipline of the project.

- **Governed recovery path (TX-011)** — observer→orchestrator→recovery path not yet operational. The orchestrator receives events and publishes ACK, but the TransitionEvaluator has no match for `SECONDARY + CONDITION_DETECTED`. Registered as DT-4G-001, to be addressed in 4G-P2-C.
- **Latency t0→t1** (physical fall → SafetyEvent published) — not measured; requires Isaac↔ROS2 clock sync (DT-4F-005).
- **Definitive thresholds** — all current thresholds (`abs_w=0.80`, STALE=1.0s, FREEZE N=5) are pragmatic, not formally justified.
- **Active postural control (PD)** — deferred. The robot does not hold itself against perturbation.
- **Hardware validation** — x86 / simulation only. No physical Unitree SDK integration.
- **Isaac Lab on T4** — blocked (requires GPU ≥ RTX 4080).

---

## Architecture Overview

```
safety_orchestrator_g1            ← operational authority (state machine, TX-001→TX-010)
    │
    ├── cross_consistency_observer  ← severity-aware cross-domain validator (INFO/WARN/CRITICAL)
    ├── watchdog_g1                 ← data-flow health monitor (STALE/FREEZE/NANINF/RATE)
    └── recovery_g1                 ← recovery executor (5 actions, subprocess isolation)
            │
    /safety_events  /system_state  /safety_actions  /recovery_events
            │
    Isaac Sim 4.5 telemetry (ROS2)  ← embodiment boundary (observation only, T4)
            │
    [future] g1_adapter_node        ← hardware boundary (Unitree SDK, blocked)
            │
    [future] standing policy / VLA / GR00T  ← intelligence layer (under safety authority)
```

**Authority rule:** intelligence and policy layers operate strictly **under** the safety runtime. A learning policy may propose; the safety orchestrator disposes.

**Known architectural debt:** the observer emits `event_type=CONDITION_DETECTED` with `source_authority=SECONDARY`. TX-001 of the orchestrator requires `STABILITY_ANOMALY` and `PRIMARY_IMU/PRIMARY_JOINT_STATES`. This mismatch means the governed path does not yet activate on fall events. Direct path observer→recovery is operational and validated. Governed path is DT-4G-001.

---

## Active ROS2 Packages (`src/`)

| Package | Role | Stage |
|---------|------|-------|
| `g1_msgs` | Typed messages: SafetyEvent, SystemState, SafetyAction, RecoveryEvent, FootContact | 3B |
| `cross_consistency_observer` | Cross-domain validation, severity rule (INFO/WARN/CRITICAL) | 3B / 4F-P1 |
| `watchdog_g1` | Health monitor — STALE/FREEZE/NANINF/TIMESTAMP/RATE over 5 topics | 4F-P2 |
| `safety_orchestrator_g1` | Operational authority — TransitionEvaluator, PriorityScheduler, T8Arbitrator, CompoundState | 3C |
| `recovery_g1` | Recovery executor — 5 actions, subprocess isolation, retry with cooldown | 3C / 4F-P4 |
| `test_g1_safety_layer` | Level-4 launch integration tests | 3C |
| `g1_description` | Robot description (XACRO, TF tree) — validated in CI Audit | 3B |

---

## Repository Tree

    g1-deterministic-safety-runtime/
    ├── .github/workflows/          # CI definitions (ci-build.yml, ci-audit.yml)
    ├── docs/
    │   ├── architecture/           # ADRs (ARCHITECTURE_DECISIONS.md)
    │   ├── audit/                  # AUDIT_READINESS_CHECKLIST, TRANSITION_MATRIX_G1
    │   ├── current/                # source-of-truth: thesis v21, bootstrap v18, session reports
    │   ├── archive/                # historical versions (fully traceable)
    │   └── phases/                 # per-stage notes
    ├── evidence/                   # raw logs — proof of what actually happened
    ├── runs/                       # 4G run logs (launcher + A/B/C/D/E per corrida)
    ├── sim_runtime/
    │   ├── 4F/                     # Isaac extension (g1ext_combo), .kit file, FALL_TRIGGER it=450
    │   ├── 4G/                     # launch_pipeline.py, analyze_runs.py
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
| 4E — healthy baseline | `docs/experiments/4E_P4_2026-06-15/` | `docs/current/` (thesis v21) |
| 4F — safety enrichment | run logs per phase | `docs/current/informe_etapa_4F_2026-06-16.md` |
| 4G-P2-A — baseline N=10 | `~/runs/4G/20260617_131144…135740` | `docs/current/informe_etapa_4G_parcial_2026-06-17.md` |
| 4G-P2-B — fall N=10 | `~/runs/4G/20260617_145141…162117` | `docs/current/informe_etapa_4G_P2B_2026-06-17.md` |

---

## CI Status

| Workflow | Trigger | Scope | Status |
|----------|---------|-------|--------|
| **CI Build** | every push / PR to `main` | build images + test 6 safety-core packages | ✅ green |
| **CI Audit** | weekly · tag `v*` · manual | full `rosdep install` + build + test all packages | ✅ green |

**What green means:** the safety runtime core compiles and its tests pass in a clean container. It does not validate hardware behavior, physical timing, or locomotion.

---

## Build / Test Commands

Safety-core unit tests (no hardware, no Isaac):

    docker exec boring_noether bash -c \
      "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && \
       python3 -m pytest src/safety_orchestrator_g1/test/test_orchestrator_transitions.py -v"

Unified launcher (4G, recommended):

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

| ID | Description | Priority |
|----|-------------|----------|
| DT-4E-001 | SAFETY_MODEL_G1.md absent — to recreate in Stage 4I | High |
| DT-4E-006 | Active PD control deferred | High |
| DT-4F-005 | t0→t1 latency unmeasured (clock sync Isaac↔ROS2) | High |
| **DT-4G-001** | **TX-011: governed escalation for SECONDARY/fallen not yet implemented** | **High** |
| DT-4F-001 | Thresholds pragmatic, pending calibration | Medium |
| DT-4F-002 | TX-006b/c without explicit test | Medium |
| DT-4F-004 | FREEZE IMU potential false positive | Medium |
| DT-4F-003 | TX-009 POLICY_GATED exact condition | Low |

---

## Roadmap

- **4G-P2-C — TX-011:** create explicit transition for `SECONDARY + STABILITY_ANOMALY/fallen` in the orchestrator's evaluator. Design before implementation. Tests before pilot.
- **4G-P3 — t0→t1:** define t0 formally, implement Isaac↔ROS2 clock sync, measure physical-to-observer latency.
- **4H — Intelligent recovery:** map rule_id → differentiated action (fall vs stale vs freeze).
- **4I — Formalization:** recreate semantic models, justify thresholds, threat model.
- **5A — Isaac Lab:** blocked on T4 (needs GPU ≥ RTX 4080).

---

## Review Notes for External Auditors

- **Start here**, then `docs/current/` for the full thesis (v21) and latest session reports.
- **Verify claims** against `runs/4G/` (raw logs per corrida) and `docs/audit/TRANSITION_MATRIX_G1.md`.
- **Reproduce** via the CI Audit recipe above; the safety core is container-clean.
- **Scope honestly:** this is a simulation-validated safety runtime, not hardware-certified. Boundaries are explicit in "Explicit Non-Validated Boundaries".
- **Heritage:** the project migrated from an AGV pipeline; that lineage is quarantined under `legacy/`, not hidden.

---

*G1 Deterministic Safety Runtime — github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
*Status 2026-06-17: 3C ✅ · 4A–4F ✅ · 4G-P0/P1/P2-A/P2-B ✅ · 4G-P2-C 🔲 · 5A 🔒*
*Audit-readiness mapped to MIT / NASA / Boston Dynamics rigor — not certified compliance.*
