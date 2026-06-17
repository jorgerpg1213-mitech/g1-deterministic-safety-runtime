# G1 Deterministic Safety Runtime

**A deterministic, auditable safety-supervision runtime for the Unitree G1 humanoid robot.**

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-build.yml)
[![CI Audit](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml/badge.svg?branch=main)](https://github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime/actions/workflows/ci-audit.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Isaac Sim](https://img.shields.io/badge/Isaac%20Sim-4.5.0-76B900?logo=nvidia)
![Stage](https://img.shields.io/badge/Stage-4F%20qualified%20%C2%B7%205A%20pending-yellow)

---

## Executive Summary

`g1-deterministic-safety-runtime` is a ROS2-native safety supervision framework for the Unitree G1 humanoid robot (37 DOF). It observes robot state in real time, classifies anomalies by severity, monitors data-flow health, and reacts through a deterministic recovery layer — all under a single operational authority that policy and learning layers can never override.

The project is engineered to **laboratory rigor** (MIT / NASA / Boston Dynamics style of review). Its central discipline is **operational honesty**: every claim in this repository is classified by what the evidence actually supports, and non-validated behavior is declared with the same prominence as validated results.

This README is the **master index and initial audit document**. It is intended to let an external reviewer understand the project — scope, evidence, architecture, limits — without opening every file.

**Current state at a glance:**

- Deterministic safety runtime core: implemented and tested (86 local Level-4 tests).
- ROS2 observability of the simulated G1 (Isaac Sim 4.5): validated, observation only.
- Severity-aware observer, health watchdog, integrated recovery, measured latency: validated (Stage 4F, P1–P5).
- Continuous Integration: **CI Build green · CI Audit green** on `main`.
- Not yet done: fault-injection robustness (4F-P6), active postural control, hardware integration, statistical reproducibility.

---

## What This Repository Is

- A **deterministic safety-runtime** for a humanoid: state machine, observer, watchdog, recovery, typed safety events.
- A **reproducible** ROS2 + Docker stack with CI that builds and tests the safety core.
- An **evidence-backed** record: every closed stage has raw logs under `evidence/` and a session report under `docs/`.
- A **navigable audit surface**: structured docs, per-directory READMEs, traceable transition matrix.

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
| 4F | Safety Runtime Enrichment (P1–P5 done, P6 pending) | 🔄 In progress |
| 5A | Isaac Lab Bring-up | 🔒 Blocked (out of T4 critical path) |
| 5–7 | VLA / Embodied behaviors / Autonomy | ⏳ Future |

**Current frontier — Stage 4F:** the framework now decides by severity, detects data-flow degradation, exposes an auditable transition matrix, integrates recovery in a live pipeline, and has latency measured on hardware (Tesla T4). The remaining sub-phase is **4F-P6 (fault injection)**.

---

## Validated Capabilities (with log evidence)

- **Deterministic runtime core (3C):** TransitionEvaluator (TX-001→TX-010), PriorityScheduler (4 buckets), T8Arbitrator, CompoundState. 86 local Level-4 tests; safety core green in CI. Auditable in `docs/audit/TRANSITION_MATRIX_G1.md`.
- **ROS2 observability (4D):** G1 observable over real ROS2 cross-container (joints, base pose, base velocity, IMU, typed foot contacts) on the T4, without the heavy RTX stack. Observation only — no control commands issued.
- **Observer→orchestrator closure (4D-3D):** real `SafetyEvent` consumed and acknowledged by the orchestrator; no improper escalation.
- **Healthy passive baseline (4E):** G1 stands passively from pose P2 + `z_cmd=0.720` + factory drives. Observer yields zero false positives on the healthy baseline (negative control). Healthy→fall transition captured in telemetry.
- **Severity-aware observer (4F-P1):** INFO/WARN/CRITICAL. CRITICAL fires on `abs_w<0.80` sustained over 3 fresh samples, even with one foot still in contact (residual contact ≠ healthy support).
- **Health watchdog (4F-P2):** STALE / FREEZE / NANINF / TIMESTAMP / RATE across 5 topics, on the T4. FREEZE excluded on contacts; 15s startup grace.
- **Transition matrix artifact (4F-P3):** TX-001→TX-010 traced to method + test + action, derived from source, not inferred.
- **Integrated recovery (4F-P4):** end-to-end pipeline, 4 simultaneous components: healthy → silence; fall → observer alarm + recovery reacts; Isaac killed → watchdog STALE + recovery reacts.
- **Latency t1→t2 (4F-P5):** 0.68–8.2 ms on Tesla T4 (2 runs). t1 = SafetyEvent published; t2 = recovery receives.

---

## Explicit Non-Validated Boundaries

These are stated as prominently as the validated results — this is the core discipline of the project.

- **Fault-injection robustness** — Stage 4F-P6, pending.
- **Latency t0→t1** (physical fall → SafetyEvent published) — not measured; requires Isaac↔ROS2 clock sync (DT-4F-005).
- **Definitive thresholds** — all current thresholds (`abs_w=0.80`, STALE=1.0s, FREEZE N=5) are pragmatic and calibrable, not formally justified.
- **Statistical reproducibility** — latency from N=2 runs; N≥5 with mean/stddev pending.
- **Active postural control (PD)** — not achieved by simple means; deferred. The robot does not hold itself against perturbation.
- **Hardware validation** — x86 / simulation only. No physical Unitree SDK integration.
- **Isaac Lab on T4** — undemonstrated, blocked (requires GPU ≥ RTX 4080).
- **Continuous Deployment (CD)** — not applicable yet; no formal release/deploy pipeline. Declared as future work.

---

## Repository Tree

    g1-deterministic-safety-runtime/
    ├── .github/workflows/          # CI definitions
    │   ├── ci-build.yml            # build + safety-core tests (every push)
    │   └── ci-audit.yml            # full build + rosdep + tests (schedule/tag/manual)
    ├── docker/                     # reproducible images (base, dev, runtime, sim)
    ├── docker-compose.yml
    ├── docs/
    │   ├── architecture/           # ADRs (ARCHITECTURE_DECISIONS.md)
    │   ├── audit/                  # AUDIT_READINESS_CHECKLIST, TRANSITION_MATRIX_G1
    │   │   └── archive/            # superseded plans / debt registers
    │   ├── current/                # CURRENT truth: thesis v18, bootstrap v15, 4F report
    │   ├── archive/                # historical: thesis v12, bootstrap v9, 4D-3 report
    │   ├── phases/                 # per-stage notes (4C, 4D, 4E, 4F, 5A)
    │   └── experiments/            # raw experiment folders (e.g. 4E_P4)
    ├── evidence/                   # raw logs — proof of what actually happened
    │   ├── 4C/                     # physical/control characterization
    │   ├── 4D-2/                   # Isaac 4.5 light-path bring-up
    │   └── 4D-3/                   # ROS2 observability per microphase
    ├── sim_runtime/                # Isaac Sim extensions, .kit files, FastDDS profiles
    │   ├── 4D-2/ 4D-3A/ 4D-3B1..B4/
    │   └── common/fastdds_udp.xml
    ├── src/                        # ── SAFETY RUNTIME CORE (ROS2 packages) ──
    │   ├── g1_msgs/                # typed messages: SafetyEvent, …, FootContact
    │   ├── cross_consistency_observer/  # severity-aware cross-domain observer
    │   ├── watchdog_g1/            # data-flow health monitor
    │   ├── safety_orchestrator_g1/ # operational authority — state machine
    │   ├── recovery_g1/            # recovery executor (5 actions)
    │   ├── test_g1_safety_layer/   # Level-4 launch integration tests
    │   └── g1_description/         # robot description (XACRO, TF tree)
    ├── legacy/                     # quarantined AGV heritage (kept for traceability)
    │   ├── agv_bringup/ agv_msgs/ rplidar_ros/
    │   ├── perception_node/ safety_policy_node/
    │   └── backups/                # pre-refactor snapshots
    └── README.md

Every major directory carries its own `README.md` for navigation. Generated artifacts (`build/`, `install/`, `log/`) are git-ignored.

---

## Architecture Overview

    safety_orchestrator_g1            <- operational authority (state machine)
        |-- cross_consistency_observer  <- severity, cross-domain validation
        |-- watchdog_g1                 <- data-flow health detection
        |-- recovery_g1                 <- recovery execution (5 actions)
                |
                /safety_events          <- typed g1_msgs on the event bus
                |
        Isaac Sim 4.5 telemetry (ROS2)  <- embodiment boundary (observation only)
                |
        [future] g1_adapter_node        <- hardware boundary (Unitree SDK, blocked)
                |
        [future] standing policy / VLA / GR00T  <- intelligence layer

**Authority rule:** intelligence and policy layers operate strictly **under** the safety runtime. A learning policy may propose; the safety orchestrator disposes.

**Data path (validated):** Isaac Sim publishes G1 telemetry over ROS2 (cross-container, FastDDS/UDP). Observer and watchdog consume it; on anomaly they emit a typed `SafetyEvent`; the orchestrator arbitrates and recovery reacts — all observation-side, no command issued to the robot.

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
| `g1_description` | Robot description (XACRO, TF tree) — validated in CI Audit (needs rosdep) | 3B |

---

## Evidence Map

Every closed stage is backed by raw logs and a session report. Nothing is asserted without a trace.

| Stage | Raw evidence | Report |
|-------|--------------|--------|
| 4C — physical/control | `evidence/4C/output_4c*.log` | `docs/phases/4C/` |
| 4D-2 — Isaac 4.5 light path | `evidence/4D-2/output_4d2*.log`, `inspect_*.log` | `docs/phases/4D/` |
| 4D-3 — ROS2 observability | `evidence/4D-3/4d3*/` | `docs/archive/informe_etapa_4D3_2026-06-08.md` |
| 4E — healthy baseline | `docs/experiments/4E_P4_2026-06-15/` | `docs/current/` (thesis v18) |
| 4F — safety enrichment | run logs (observer/watchdog/recovery) | `docs/current/informe_etapa_4F_2026-06-16.md` |

Current source-of-truth documents live in `docs/current/`: thesis v18, bootstrap protocol v15, and the 4F session report. Superseded versions are preserved in `docs/archive/` for full traceability.

---

## CI Status and Meaning

| Workflow | Trigger | Scope | Status |
|----------|---------|-------|--------|
| **CI Build** | every push / PR to `main` | build images + test the 6 safety-core packages | ✅ green |
| **CI Audit** | schedule (weekly) · tag `v*` · manual | full `rosdep install` + build + test all packages incl. `g1_description` | ✅ green |

**What green means here:** the safety runtime core compiles and its tests pass in a clean container. **What it does not mean:** it does not validate hardware behavior, physical timing, or locomotion — those are out of scope by design (see Non-Validated Boundaries).

**CD (Continuous Deployment):** not present. There is no runtime artifact to deploy yet; a release/deployment pipeline is future work once a deployable target exists.

---

## Build / Test Commands

Safety-core unit tests (no hardware, no Isaac):

    docker run --rm -v $(pwd):/root/pipeline_ws pipeline-runtime:latest bash -c \
      "cd /root/pipeline_ws && source /opt/ros/humble/setup.bash && \
       source install/setup.bash && \
       python3 -m pytest src/safety_orchestrator_g1/test/test_orchestrator_transitions.py -v"

Full build + test (as CI Audit does it):

    source /opt/ros/humble/setup.bash
    rosdep install --from-paths src --ignore-src -r -y
    colcon build --symlink-install
    source install/setup.bash
    colcon test && colcon test-result --verbose

The end-to-end simulation pipeline (Isaac + observer + watchdog + recovery) is launched manually as four components in strict order; exact commands live in `docs/current/chat_bootstrap_protocol_g1_pipeline_v15.md`. A unified launcher is future work (Stage 4G).

---

## Roadmap: 4F → 5A

- **4F-P6 — Fault injection:** one synthetic fault per run (frozen IMU, frozen contact, NaN joints, regressive timestamp, lost topic). PASS = watchdog emits the correct rule_id and severity.
- **4G — Pipeline hardening:** unified launcher; statistical reproducibility (N≥10, mean/stddev/p95); t0→t1 clock sync.
- **4H — Intelligent recovery:** map rule_id → differentiated action (fall vs stale).
- **4I — Formalization:** recreate semantic models, justify thresholds, threat model.
- **5A — Isaac Lab:** blocked on T4 (needs GPU ≥ RTX 4080); only an execution environment for a ready policy, not a training rig.

---

## Technical Debt / Archived Context

Active debt is tracked in the current thesis (`docs/current/`) and audit checklist (`docs/audit/`). Highlights:

- **DT-4E-001** — canonical semantic models (`SAFETY/RESILIENCE/RECOVERY_MODEL`) pending reconstruction from source evidence; not yet present.
- **DT-4F-005** — t0→t1 latency unmeasured (clock sync).
- **DT-4F-001 / DT-4D-016** — thresholds pragmatic, pending calibration.
- **DT-4D-003** — Isaac Lab on T4 undemonstrated.

Historical plans and debt registers are archived under `docs/audit/archive/` and `docs/archive/`. The AGV-heritage packages are quarantined under `legacy/` — retained for traceability, excluded from the build via `COLCON_IGNORE`.

---

## Review Notes for External Auditors

- **Start here**, then `docs/current/` for the full thesis and latest session report.
- **Verify claims** against `evidence/` (raw logs) and `docs/audit/TRANSITION_MATRIX_G1.md` (TX traced to test).
- **Reproduce** via the CI Audit recipe above; the safety core is container-clean.
- **Scope honestly:** this is a simulation-validated safety runtime, not a hardware-certified or locomotion-capable system. Boundaries are stated in "Explicit Non-Validated Boundaries".
- **Heritage:** the project migrated from an AGV pipeline; that lineage is quarantined, not hidden.

---

*G1 Deterministic Safety Runtime — github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
*Status 2026-06-16: 3C ✅ · 4A–4D ✅ · 4E ✅ · 4F 🔄 (P1–P5 done, P6 pending) · 5A 🔒*
*Audit-readiness mapped to MIT / NASA / Boston Dynamics rigor — not certified compliance.*
