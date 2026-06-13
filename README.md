# G1 ROS2 Pipeline

<div align="center">

**Reproducible · Auditable · Operationally Honest**

*Deterministic Safety Runtime Architecture for the Unitree G1 Humanoid Robot*
*ROS2 Humble · Docker-first · Isaac Sim 4.5.0 · Tesla T4 validated*

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml/badge.svg)](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Isaac Sim](https://img.shields.io/badge/Isaac%20Sim-4.5.0-76B900?logo=nvidia)
![Platform](https://img.shields.io/badge/Platform-x86__64-lightgrey)
![Status](https://img.shields.io/badge/Etapa-4D--3%20Closed-brightgreen)
![Tests](https://img.shields.io/badge/Tests-86%20passing-brightgreen)

</div>

---

## What This Is

`g1-ros2-pipeline` is a **production-grade safety runtime framework** for the Unitree G1 humanoid robot (37 DOF). It is not a demo, not a prototype, and not a collection of scripts.

It is a formally validated, deterministic supervision system designed to the standard of controlled laboratory environments — equivalent in rigor to MIT, NASA, and Boston Dynamics operational pipelines.

The project is subject to audit by MIT and Boston Dynamics.

### Core Principle

> The humanoid runtime and VLA policy training are distinct but complementary domains.
> Training optimizes intelligence. The runtime architecture governs real operational behavior.

VLA models (GR00T, LeRobot, Gemini Robotics) do **not** govern the humanoid directly. Operational authority resides permanently in `safety_orchestrator_g1`, `watchdog_g1`, `cross_consistency_observer`, and the semantics defined by `SAFETY_MODEL_G1.md`.

---

## Audit Portal — Where Everything Lives

This README is the **master index**. Full evidence and reproducible artifacts are organized in three layers:

| Layer | Path | Contains |
|-------|------|----------|
| **Reports** | [`docs/`](docs/) | Full session reports, thesis, bootstrap protocol — the audited narrative |
| **Evidence** | [`evidence/`](evidence/) | Raw logs per phase — the proof of what actually happened |
| **Sim Runtime Code** | [`sim_runtime/`](sim_runtime/) | Isaac Sim extensions, `.kit` files, ROS2 subscribers, FastDDS profiles — reproducible |
| **Runtime Framework** | [`src/`](src/) | The deterministic safety runtime (ROS2 packages) — Stage 3C |

### Reports Index (`docs/`)

| Document | Scope |
|----------|-------|
| [`informe_etapa_4D3_2026-06-08.md`](docs/informe_etapa_4D3_2026-06-08.md) | Block 4D-3 — ROS2 feasibility, custom mini-bridge, cross-container DDS, minimal state, physical sensors |
| [`tesis_etapas_proyecto_g1_runtime_architecture_v12.md`](docs/tesis_etapas_proyecto_g1_runtime_architecture_v12.md) | Full stage thesis (v12) — all stages, frozen decisions, declared debt |
| [`chat_bootstrap_protocol_g1_pipeline_v9.md`](docs/chat_bootstrap_protocol_g1_pipeline_v9.md) | Operational bootstrap (v9) — rules, confirmed paths, anti-patterns |

> Prior reports (`informe_etapa_4B/4C/4D2`) are referenced historically; the current frontier is documented in the 4D-3 report above.

---

## Project Status

| Stage | Description | Status | Closed |
|-------|-------------|--------|--------|
| **Etapa 1** | Infrastructure Base — ROS2, Docker, CI, runtime discipline | ✅ Closed | — |
| **Etapa 2** | Operational Discipline — anti-patterns, observability, reproducibility | ✅ Closed | — |
| **Etapa 3A** | Semantic Models + ADRs — SAFETY/RESILIENCE/RECOVERY MODEL | ✅ Closed | — |
| **Etapa 3B** | ROS2 Runtime Skeleton — 4 nodes + g1_msgs + threading architecture | ✅ Closed | — |
| **Etapa 3C** | Transition Logic — TransitionEvaluator, Scheduler, T8, recovery, 86 tests | ✅ Closed | 2026-05-24 · `861a8b6` |
| **Etapa 4A** | Infrastructure & DDS Characterization — VM, Docker, FastDDS, ROS2 | ✅ Closed | 2026-05-26 |
| **Etapa 4B** | Isaac Headless Bring-up (4.2.0) — SimulationApp, G1 USD load, lifecycle | ✅ Closed | 2026-05-29 |
| **Etapa 4C** | Physical & Control Characterization (4.2.0) — 37 DOF, KP/KD, toppling | ✅ Closed | 2026-06-01 |
| **Etapa 4D-1** | Disk / Baseline Preservation Audit — image swap 4.2→4.5, 4C backup | ✅ Closed | 2026-06-08 |
| **Etapa 4D-2** | Isaac Sim 4.5 Feasibility on T4 — light path, G1 load + stepping (600 steps) | ✅ Closed | 2026-06-08 |
| **Etapa 4D-3** | ROS2 Feasibility + Sensor Observability + Observer→Orchestrator closure | ✅ Closed | 2026-06-12 |
| **Etapa 4E** | Standing Policy Plug-and-Play + Runtime Validation | 🔄 Next | — |
| **Etapa 5A** | Isaac Lab Bring-up / G1 Validation | 🔒 Blocked | — |
| **Etapa 5** | VLA / GR00T / LeRobot Integration | ⏳ Future | — |
| **Etapa 6** | Real Embodied Behaviors | ⏳ Future | — |
| **Etapa 7** | Refinement & Autonomy | ⏳ Future | — |

### Latest Closed Frontier (4D-3) / Next Frontier (4E)

Stage 4D-3 is now closed. The G1 is observable over real ROS2 (joints + base pose + base velocity + IMU + typed foot contacts), the cross-consistency observer consumes real telemetry, emits a real `SafetyEvent`, and the `safety_orchestrator_g1` receives and acknowledges it with `event_type=SCHEDULED`. This is still **observation only** — no control commands are issued to the robot.

| Microphase | Description | Status |
|------------|-------------|--------|
| 4D-3A | ROS2 feasibility → custom mini-bridge (internal `rclpy`) | ✅ Closed |
| 4D-3B1 | G1 + `rclpy` coexist in the same Kit process | ✅ Closed |
| 4D-3B2 | Publisher `/joint_states` + external reception (resolved DT-4A-003) | ✅ Closed |
| 4D-3B3 | Minimal state — joints + base pose + base velocity (3 topics) | ✅ Closed |
| 4D-3B4 | Probe physical sensors (load without crash — "RTX tolerated") | ✅ Closed |
| 4D-3B4A | IMU + 2 ContactSensors read during fall (+ live stream) | ✅ Closed |
| 4D-3B4B | Publish IMU + contacts with dedicated ROS2 types | ✅ Closed |
| 4D-3C | Deterministic Runtime in OBSERVER mode — real telemetry consumed, mock disabled | ✅ Closed |
| 4D-3D | Observer→orchestrator closure — real SafetyEvent ACKed by orchestrator | ✅ Closed |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        G1 ROS2 Pipeline                              │
│            Deterministic Safety Runtime Framework                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │        Simulation Layer (Isaac Sim 4.5.0) — 4D-2 / 4D-3        │ │
│  │                                                                 │ │
│  │  kit directo + .kit mínimo ──► extensión Python async         │ │
│  │  G1 USD (S3 NVIDIA 4.5)    ──► 37 DOF, stepping 600 steps      │ │
│  │  custom mini-bridge (rclpy internal) ──► /joint_states         │ │
│  │  IMU + ContactSensors      ──► /g1/imu, /g1/feet              │ │
│  │             [4D-3 — observation validated]                      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                    │ DDS / FastDDS (UDP forced, cross-container)     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │               Safety Runtime Layer — Etapa 3C                  │ │
│  │                                                                 │ │
│  │  watchdog_g1 ──────────────────────────────────────────────►   │ │
│  │  cross_consistency_observer ───────────────────────────────►   │ │
│  │                                         /safety_events          │ │
│  │                                              │                  │ │
│  │                                              ▼                  │ │
│  │                              safety_orchestrator_g1             │ │
│  │                    (TransitionEvaluator · PriorityScheduler     │ │
│  │                     T8Arbitrator · CompoundState)               │ │
│  │                              /system_state (TRANSIENT_LOCAL)    │ │
│  │                              /safety_actions                    │ │
│  │                                              │                  │ │
│  │                                              ▼                  │ │
│  │                                        recovery_g1              │ │
│  │                             (subprocess isolation · retry       │ │
│  │                              policy · escalation)               │ │
│  │                                        /recovery_events         │ │
│  │              [4D-3D — observer→orchestrator ACK validated]      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              Hardware Adapter Layer — Blocked                   │ │
│  │                                                                 │ │
│  │  g1_adapter_node        [BLOCKED — Unitree SDK G1]              │ │
│  │  gemini_perception_node [BLOCKED — Gemini API]                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │           Intelligence Layer — Future (Etapa 4E / 5)            │ │
│  │                                                                 │ │
│  │  Standing policy (plug-and-play) → "healthy" baseline (4E)      │ │
│  │  GR00T / LeRobot / Gemini Robotics                              │ │
│  │  Policy layers operate UNDER safety authority — never above     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Authority Hierarchy

```
SAFETY_MODEL_G1.md  (semantic authority — source of truth)
    └── safety_orchestrator_g1        ← operational authority
            ├── watchdog_g1           ← condition detection
            ├── cross_consistency_observer  ← cross-domain validation
            └── recovery_g1          ← recovery execution
                    └── [4D-3] Isaac Sim telemetry (ROS2)  ← embodiment boundary (observation)
                            └── [future] g1_adapter_node  ← hardware boundary
                                    └── [4E/future] standing policy / VLA / GR00T  ← intelligence
```

---

## Stage 3C — Deterministic Safety Runtime Framework

**Commit:** `861a8b6` | **Branch:** main | **Closed:** 2026-05-24

The core of the project. A formally validated, deterministic semantic supervision framework. Hardware-agnostic. Validated on x86 Dockerized environment. Headless execution oriented.

### Technical Designation

> **Deterministic Safety Runtime Framework** — deterministic semantic supervision framework, hardware-agnostic, validated in Dockerized x86 environment, headless execution oriented.

### Components

#### `safety_orchestrator_g1`

Central authority node. Implements:

- **TransitionEvaluator** — evaluates the complete Transition Matrix from `SAFETY_MODEL_G1`. Implements all 12 rows (TX-001 to TX-010 including TX-006a/b/c) with full semantic fidelity. Pure function — receives `(event, state)`, returns `dict` or `None`. No side effects.
- **PriorityScheduler** — 4 independent buckets: `CRITICAL_INTERRUPT` → `COMMIT_TERMINAL` → `NORMAL` → `RECOVERY`. Drain in priority order + FIFO within bucket.
- **T8Arbitrator (DRAFT — PH-001)** — conflict resolution between equal-priority transitions. Rules: (1) CRITICAL_INTERRUPT: highest `authority_effectiveness` wins. (2) NORMAL: highest `target_risk_level` wins. (3) RECOVERY: most conservative wins. (4) Tie: `ARBITRATION_PENDING` observable.
- **CompoundState** — `(Risk Level, Restriction Level)` pair — system state unit. Exclusive property of Thread 2. `r5_committed` flag irreversible post TX-005.

#### `watchdog_g1`

Condition detector and reporter. Monitors operational boundaries defined by the Safety Model. Emits `SafetyEvent` messages to the event bus.

#### `cross_consistency_observer`

Cross-domain validator. PRIMARY observer. Monitors consistency between independent sensor domains and the declared system state.

#### `recovery_g1`

Recovery runtime executor. 5 real RecoveryActions executable on x86:

- `restart_noncritical_node`
- `restart_critical_node`
- `request_operator_intervention`
- `restore_nav_stack`
- `wait_for_primary_restore`

Subprocess isolation with tracking and cleanup. Retry policy with real cooldown. Escalation semantics.

### Test Results

| Level | Suite | Tests | Result |
|-------|-------|-------|--------|
| Level 1 | `smoke_test_watchdog` | 4 | ✅ PASS |
| Level 1 | `smoke_test_recovery_manager` | 5 | ✅ PASS |
| Level 2 | `colcon build` — `pipeline-runtime` | — | ✅ PASS |
| Level 2 | CI `ci-build.yml` | — | ✅ Green |
| Level 3 | `test_description_launch.py` | 2 | ✅ PASS |
| Level 4 | `test_g1_safety_layer` (launch integration) | 15 | ✅ PASS |
| Level 4 | `test_orchestrator_transitions` (unit) | 60 | ✅ PASS |
| Level 5 | Hardware G1 + Isaac Sim | — | ⏳ In progress (4D-3 observation) |

**Total: 86 tests · 0 failures.**

> **Level 4 launch scope:** validates that the 4 safety layer nodes start, publish heartbeat on `/diagnostics`, expose `/system_state` with Transient Local QoS, and produce observable events on `/safety_events` and `/recovery_events`.

> **Level 4 unit scope:** validates TransitionEvaluator (TX-001 to TX-010), PriorityScheduler (4 buckets, FIFO, drain order), T8Arbitrator (rules R1-R4, ARBITRATION_PENDING), edge cases (R5 committed, T1 no-skip, overflow), and universal recovery precondition. No ROS2 — pure logic.

### Deferred to Stage 4+

- Experimental thresholds → pending Unitree SDK G1
- Real physical timing → pending Unitree SDK G1
- Arbitration under real hardware → pending Unitree SDK G1
- Real locomotion semantics → pending Unitree SDK G1

---

## Stage 4A — Infrastructure & DDS Characterization

**Closed:** 2026-05-26

### VM Environment (Characterized and Validated)

| Component | Value |
|-----------|-------|
| OS | Ubuntu 22.04.5 LTS |
| GPU | NVIDIA Tesla T4 · 16GB VRAM |
| Driver | 580.x |
| CUDA | 13.0 |
| Docker | 29.1.3 + NVIDIA Container Toolkit |
| RMW | FastDDS (`rmw_fastrtps_cpp` 6.2.10) |
| Disk | 58GB total · 21GB available post-Isaac |

### Validated in 4A

- ROS2 Humble bootstrap from OSRF official sources
- Docker-first ROS2 runtime baseline (`ubuntu:jammy` → ros-core → ros-base)
- `g1-ros-phase-a:humble` (651MB) — ROS2 Humble operational
- `g1-ros-phase-b:humble` (1.02GB) — colcon 21 modules validated
- Intra-container DDS communication (5/5 messages published and received)
- Host-network ROS2 orchestration baseline
- Deterministic cleanup behavior
- GPU passthrough to containers (`--gpus all`)

### Frozen Decisions from 4A

| Decision | Resolution |
|----------|------------|
| ROS2 installation | Docker-first — NO host contamination |
| Base image | `ubuntu:jammy` → OSRF ros-core → ros-base |
| ROS2 distro | Humble (22.04 Jammy) |
| DDS vendor | FastDDS (`rmw_fastrtps_cpp`) |
| **DDS cross-container** | **UDPv4 transport forced via XML profile (shm does not cross containers) — resolved in 4D-3B2** |
| Python version | 3.10 — NO mixing with 3.12 |
| GPU strategy | `--gpus all` on CUDA containers |

### Debt from 4A

| ID | Debt | Priority | Status |
|----|------|----------|--------|
| DT-4A-003 | Cross-container DDS characterization | — | ✅ **RESOLVED in 4D-3B2** (UDP forced) |
| DT-4A-004 | FastDDS vs CycloneDDS — Unitree SDK2 divergence | **High** | Open — for physical robot |
| DT-4A-006 | colcon-parallel-executor outdated (0.3.0 vs 0.4.0) | Low | Open |

> **DT-4A-003 resolution:** root cause was FastDDS defaulting to shared memory, which does not cross between distinct Docker containers even under `--network=host`. Fix: force UDPv4 transport via XML profile (`FASTRTPS_DEFAULT_PROFILES_FILE`) in both containers. Validated with real G1 telemetry and 1:1 temporal traceability. See [`docs/informe_etapa_4D3_2026-06-08.md`](docs/informe_etapa_4D3_2026-06-08.md) §8.

---

## Stage 4B — Isaac Headless Bring-up (Isaac Sim 4.2.0)

**Closed:** 2026-05-29
**Reference:** `informe_etapa_4B_2026-05-29.md`

### What Was Validated

The core question of 4B:

> **Can this VM load the G1 USD asset inside Isaac Sim headless?**

Answer: **Yes. With evidence.**

| Component | Status |
|-----------|--------|
| `python.sh` standalone workflow | ✅ |
| `SimulationApp({"headless": True})` | ✅ |
| Bind mounts `-v` | ✅ |
| `get_assets_root_path()` → S3 NVIDIA 4.2 | ✅ |
| `open_stage()` functional | ✅ |
| `is_stage_loading()` functional | ✅ |
| `G1/g1.usd` loaded from S3 | ✅ |
| Isaac headless lifecycle complete | ✅ |

This validation corresponds specifically to loading the G1 USD asset via `open_stage()`. It does not imply validation of active physics, ROS2 Bridge, joint publishing, or runtime governance — those were 4C+ objectives.

### Key Architectural Decisions from 4B

| Decision | Resolution |
|----------|------------|
| Isaac workflow (4.2) | `python.sh` standalone — **NOT** `runheadless.native.sh` for Python scripts |
| RMW for bridge | FastRTPS — CycloneDDS causes bridge failure in Isaac Sim 4.2.0 |
| Script generation | `cat > script.py << 'EOF'` — **NEVER** `echo` inline (corrupts silently) |
| Observability retention | `time.sleep(N)` — **NOT** `input()` without Docker TTY |
| Import order | All `omni`/`carb` imports **AFTER** `SimulationApp()` — mandatory |
| Startup time | ~6-7 minutes on Tesla T4 — silence is normal, not failure |
| Session resilience | `tmux new -s name` before any heavy process — mandatory |

### Open Debt from 4B

| ID | Debt | Priority | Status |
|----|------|----------|--------|
| DT-4B-001 | Local-first G1 asset migration (eliminate S3 dependency) | Medium | Open |
| DT-4B-002 | G1 USD dependency tree validation (textures, payloads, materials) | Medium | Open |
| DT-4B-003 | CycloneDDS vs FastRTPS compatibility for Unitree SDK | **High** | Open |
| DT-4B-004 | Cross-container DDS characterization | Low | ✅ Resolved (see DT-4A-003) |

---

## Stage 4C — Physical & Control Characterization (Isaac Sim 4.2.0)

**Closed:** 2026-06-01
**Reference:** `informe_etapa_4C_4D_2026-06-01.md`

Complete local characterization block in Isaac Sim 4.2.0. Summary:

- G1 confirmed as a valid articulation: **37 DOF**, 176 prims, 44 rigid bodies, 40 colliders, 43 joints (37 with `DriveAPI:angular`)
- KP runtime ≈ 572,957,824 = KP_USD × (180/π); the controller operates in radians. KD runtime = 0.0
- KD has observable physical effect; the curve {0, 5.7M, 10M, 20M} is non-monotonic; KD=5.7M best local point — NOT approved as production
- Eliminated hypotheses: kinematic pose-hold, "ArticulationController is enough", "more KD always improves"
- Live hypothesis (external evidence, not locally validated): stability requires active policy/control (Isaac Lab issue #2682)

### Inherited Debt from 4C (active)

| ID | Debt | Priority | Status |
|----|------|----------|--------|
| DT-4C-001 | UsdStage reference count warning | Low | Open — non-blocking |
| DT-4C-002 | Local G1 asset migration | Medium | Deferred |
| DT-4C-003 | PhysX/TGS velocity iteration warning | Low | Open — non-blocking |
| DT-4C-004 | `physics_dt` default of `World()` not characterized | Low | Open — non-blocking |
| DT-4C-005 | `add_default_ground_plane()` defaults not characterized | Low | Open — non-blocking |
| DT-4C-006 | Cause of Z -8.17mm offset Isaac Core vs USD authored | Low | Open — non-blocking |

---

## Stage 4D-1 — Disk / Baseline Preservation Audit

**Closed:** 2026-06-08

- Confirmed: single 58GB disk, ~21–23GB free, no LVM, no second disk
- Approved Plan B executed: Isaac Sim 4.2.0 image replaced by 4.5.0 (4.2.0 reconstructible via NGC re-pull)
- 44 scripts/logs from 4C backed up in `~/backup_4c/`
- External incident resolved: GPU `RmInitAdapter failed` after admin force-reboot (NAS/iSCSI) → full VM Stop/Start restored the GPU

---

## Stage 4D-2 — Isaac Sim 4.5 Feasibility on Tesla T4

**Closed:** 2026-06-08
**Reference:** [`docs/informe_etapa_4D3_2026-06-08.md`](docs/informe_etapa_4D3_2026-06-08.md) (§4-5) and prior `informe_etapa_4D2_2026-06-08.md`

### The Blocker and the Solution

`SimulationApp({"headless": True})` on 4.5 loads, in practice on this image, the heavy experience `isaacsim.exp.full.streaming.kit` (RTX renderer + ROS2), which crashes on the T4 (`DescriptorSet` errors). The exact cause is undemonstrated and frozen (DT-4D-001).

A **custom, reproducible light path** was built: launch the `kit` binary directly with a minimal `.kit` (no `exp.base` inheritance, no `kit/community`) plus a custom Python extension (`isaacsim.g1.runtime`) running async code in `on_startup`. Via this path, the G1 loads with `num_dof = 37`, performs physical stepping, and reports pose/joints in a sustained manner — without crash, on the T4.

### Confirmed Results (2A–2H)

| Microphase | Result |
|------------|--------|
| 4D-2A | Blocker diagnosed — `full.streaming` loads despite `experience=`; all factory experiences inherit heavy `exp.base` |
| 4D-2B | Minimal `.kit` without `exp.base` → `app ready` via direct `kit` (requires `omni.kit.loop-isaac`) |
| 4D-2C | Custom Python extension executes `on_startup` without `SimulationApp` |
| 4D-2D | G1 loads — `num_dof: 37` (reconfirmed in 4.5) |
| 4D-2E | Physical stepping smoke test (60 steps) — `world.step(render=False)` synchronous |
| 4D-2F | Repeatability — bit-identical between two independent runs |
| 4D-2G | Stability series 4.5 vs 4.2 — same dynamics (documentary analysis, no new run) |
| 4D-2H | Sustained readout 600 steps — stable rest from ~step 150 (Z≈0.1618, W≈0.671), bit-identical repeat |

### Confirmed API for Isaac Sim 4.5

| Method / Symbol | Notes 4.5 |
|-----------------|-----------|
| `world.step(render=False)` | synchronous — `step_async()` is NOT awaitable (returns None) |
| `get_world_poses()` | plural — singular `get_world_pose()` does not exist |
| Robot load | async: `create_new_stage_async` / `initialize_simulation_context_async` / `reset_async` |
| Extension pattern | `class Extension(omni.ext.IExt)` with `on_startup` → `asyncio.ensure_future` |

### Debt from 4D-2

| ID | Debt | Priority | Status |
|----|------|----------|--------|
| DT-4D-001 | Exact cause of `SimulationApp` → `full.streaming` despite `experience=` | Medium | Frozen — avoided via direct `kit` |
| DT-4D-002 | `app ready` requires `omni.kit.loop-isaac`; minimal lifecycle not fully characterized | Low | Open — non-blocking |
| DT-4D-003 | T4 viability for RTX render / Isaac Lab / RL not demonstrated | **High** | Open — mitigated (T4 tolerated sensor RTX without crash, see 4D-3B4) |
| DT-4D-004 | `add_default_ground_plane()` / `World()` defaults in async extension | Low | Open — non-blocking |
| DT-4D-005 | "No heavy RTX" is log inference, not GPU profiling | Low | Open — non-blocking |

---

## Stage 4D-3 — ROS2 Feasibility + Runtime Observer Closure (Closed)

**Reference:** [`docs/informe_etapa_4D3_2026-06-08.md`](docs/informe_etapa_4D3_2026-06-08.md)

### Result

The G1 is **fully observable over real ROS2** (joints + base pose + base velocity + IMU + foot contacts) toward external processes, cross-container, without the heavy RTX stack, on the T4. Live streaming validated with 1:1 temporal traceability. **Observation only** — no control commands issued.

### What Was Validated

| Microphase | Result |
|------------|--------|
| 4D-3A | Official ROS2 bridge **discarded** (hard RTX dependency on `sensors.rtx` → `hydra.rtx`, no off-flag, not tied to Isaac Lab). Custom mini-bridge built with Isaac's internal `rclpy` (`/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy`), loaded via `sys.path.append` inside `on_startup` (Kit does not inherit PYTHONPATH). `RCLPY IN KIT OK`. |
| 4D-3B1 | G1 + `rclpy` coexist in the same Kit process; `rclpy` alive across 300 steps |
| 4D-3B2 | Publisher `/joint_states` — 1542 messages (37/37/37); external reception confirmed cross-container after the DDS UDP fix. **Resolved DT-4A-003.** Temporal traceability (3B2-T): `first_frame_id=159` (live capture, not cache), 1:1 correlation per second, 1383 messages received |
| 4D-3B3 | Minimal state — `/joint_states` (JointState) + `/g1/base_pose` (PoseStamped) + `/g1/base_velocity` (TwistStamped). Base velocity via `get_linear_velocities()` + `get_angular_velocities()` **separated** to avoid order ambiguity |
| 4D-3B4 | Physical sensors probe — `isaacsim.sensors.physics` (IMUSensor + ContactSensor) loads without crash. Pulls an RTX plugin (`rtx.neuraylib`) that warns about ECC but does **not** crash → "RTX tolerated" |
| 4D-3B4A | IMU (torso) + 2 ContactSensors (feet) read during the full fall (300 steps), physically coherent. Live stream `/g1/imu` + `/g1/feet` validated frame-by-frame |
| 4D-3B4B | IMU + foot contacts published with dedicated ROS2 types (`sensor_msgs/Imu`, `g1_msgs/FootContact`) and externally received cross-container |
| 4D-3C | `cross_consistency_observer` connected to real G1 telemetry; first real coherence rule implemented: fallen/no-support detection with freshness gating and mock disabled |
| 4D-3D | End-to-end runtime closure validated: observer emitted real `CONDITION_DETECTED`; orchestrator received it and published ACK `SCHEDULED`; no improper state escalation |

### Confirmed ROS2 Path (custom mini-bridge)

| Element | Value |
|---------|-------|
| Internal `rclpy` | `/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy` (load via `sys.path.append` in `on_startup`) |
| numpy for external subscriber | `/isaac-sim/extscache/omni.kit.pip_archive-0.0.0+d02c707b.lx64.cp310/pip_prebundle` |
| DDS cross-container | force UDPv4 via XML + `FASTRTPS_DEFAULT_PROFILES_FILE` in both containers |
| `ros2` CLI | does NOT exist in the image — use a Python `rclpy` subscriber |
| Sensors | `isaacsim.sensors.physics` (RTX tolerated, no crash) |

Reproducible code: [`sim_runtime/4D-3A`](sim_runtime/4D-3A) … [`sim_runtime/4D-3B4`](sim_runtime/4D-3B4). FastDDS UDP profile: [`sim_runtime/common/fastdds_udp.xml`](sim_runtime/common/fastdds_udp.xml).

### New Debt from 4D-3

| ID | Debt | Priority | Status |
|----|------|----------|--------|
| DT-4D-006 | `get_contact_sensor_raw_data` deprecated in 4.5 (works) | Low | New — migrate before production |
| DT-4D-007 | `estado()` label in `sub_live.py` miscalibrated (data correct, label lies) | Low | New — 3-line fix |
| DT-4D-008 | Contacts initially published as raw `Float32MultiArray` | Medium | Resolved in 4D-3B4B with `g1_msgs/FootContact` |
| DT-4D-009 | Orchestrator ACK is observable on `/safety_events`, not printed in C terminal logs | Low | Documented — use topic monitor for evidence |

### Strategic Reorientation (clarified during 4D-3)

The immediate goal is to **validate the Deterministic Safety Runtime Framework** against G1 states. This requires, at minimum, the robot **standing/stable** (the "healthy" factory baseline) to contrast against anomalous states under controlled perturbations. With the robot permanently fallen there is no "healthy vs faulty" contrast.

The operator will **not** train locomotion (no local RL). A **plug-and-play standing policy** is sought (already trained, executable). This reclassifies Isaac Lab (5A) as **no longer the critical path** — it would only be an execution environment for a ready policy, not a training rig, which lowers the T4 risk. Proposed microphase **4E** captures this.

---

## Stage 4E — Standing Policy Plug-and-Play + Runtime Validation (Next)

**Status:** 🔄 Next — opened after 4D-3D closure

Investigate/verify a plug-and-play standing policy for the G1 that keeps it upright (the "healthy" baseline), then inject controlled perturbations to validate the runtime's state detection (healthy → "OK"; perturbed/fallen → detected). This is the prerequisite for full runtime validation and is independent of training. See thesis v12 §4E.

---

## Stage 5A — Isaac Lab Bring-up / G1 Environment Validation

**Status:** 🔒 Blocked — reclassified: no longer the critical path if 4E resolves the "healthy" baseline via plug-and-play.

Risk note: T4 viability for Isaac Lab (RL, RTX sensors, replicator, training) is undemonstrated (DT-4D-003). Mitigating evidence from 4D-3B4: the T4 **tolerated** the sensor RTX plugin without crashing — this weakens "RTX on T4 = absolute wall" but does not prove Isaac Lab runs.

---

## Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.x
- Ubuntu 22.04 (x86_64)
- 8GB RAM minimum (16GB recommended for Isaac Sim)
- NVIDIA GPU with CUDA support (for Isaac Sim stages)

### 1. Clone

```bash
git clone https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline.git
cd g1-ros2-pipeline
```

### 2. Build Docker images

```bash
docker build -f docker/Dockerfile.base -t pipeline-base:latest .
docker build -f docker/Dockerfile.runtime -t pipeline-runtime:latest .
```

### 3. Launch the G1 pipeline

```bash
docker run --rm -it \
  -e ROS_DOMAIN_ID=0 \
  -e PIPELINE_WS=/root/pipeline_ws \
  -e PIPELINE_SHARE=/mnt/g1_share \
  -v $(pwd)/g1_share:/mnt/g1_share \
  pipeline-runtime:latest \
  ros2 launch agv_bringup system_g1.launch.py
```

### 4. Run the full test suite

```bash
docker run --rm \
  -v $(pwd):/root/pipeline_ws \
  pipeline-runtime:latest bash -c \
  "cd /root/pipeline_ws && source /opt/ros/humble/setup.bash && \
   source install/setup.bash && \
   colcon test && colcon test-result --verbose --all"
```

### 5. Run transition logic unit tests (no hardware required)

```bash
docker run --rm \
  -v $(pwd):/root/pipeline_ws \
  pipeline-runtime:latest bash -c \
  "cd /root/pipeline_ws && source /opt/ros/humble/setup.bash && \
   source install/setup.bash && \
   python3 -m pytest src/safety_orchestrator_g1/test/test_orchestrator_transitions.py -v"
```

### 6. Reproduce the Isaac Sim 4.5 light path (T4)

Full commands (publisher + external subscriber, FastDDS UDP profile) are documented in [`docs/chat_bootstrap_protocol_g1_pipeline_v9.md`](docs/chat_bootstrap_protocol_g1_pipeline_v9.md). Extensions and `.kit` files live under [`sim_runtime/`](sim_runtime/). Raw run logs are under [`evidence/`](evidence/).

---

## Repository Structure

```
g1-ros2-pipeline/
├── docker/
│   ├── Dockerfile.base          # ROS2 Humble + slam-toolbox + nav2 + xacro
│   ├── Dockerfile.dev           # Base + RViz2 + debug tools
│   ├── Dockerfile.runtime       # Base + compiled workspace (install/ baked in)
│   ├── Dockerfile.sim           # Base + sim-time config [BLOCKED — 4C]
│   └── entrypoint.sh
├── docker-compose.yml
├── ARCHITECTURE_DECISIONS.md
├── SAFETY_MODEL_G1.md           # Canonical semantic authority — source of truth
├── RESILIENCE_MODEL_G1.md
├── RECOVERY_MODEL_G1.md
├── TECHNICAL_DEBT_3C.md
├── README.md
├── docs/                        # ── AUDIT REPORTS ──
│   ├── informe_etapa_4D3_2026-06-08.md          # Block 4D-3 full report
│   ├── tesis_etapas_proyecto_..._v12.md         # Stage thesis (v12)
│   └── chat_bootstrap_protocol_..._v9.md        # Bootstrap protocol (v9)
├── evidence/                    # ── RAW LOGS (proof) ──
│   ├── 4C/                      # output_4c*.log — physical characterization
│   ├── 4D-2/                    # output_4d2*, output_g1*, inspect_* — light path
│   └── 4D-3/                    # per-microphase run logs
│       ├── 4d2h/  4d3a/  4d3b1/  4d3b1step/
│       ├── 4d3b2/ 4d3b3/ 4d3b4probe/ 4d3b4a/ 4d3b4live/
├── sim_runtime/                 # ── ISAAC SIM CODE (reproducible) ──
│   ├── 4D-2/                    # baseline runtime ext + minimal .kit files
│   ├── 4D-3A/                   # rclpy probe ext + .kit
│   ├── 4D-3B1/                  # G1 + rclpy coexistence ext
│   ├── 4D-3B2/                  # jointpub ext + subscribers + fastdds_udp.xml
│   ├── 4D-3B3/                  # statepub ext (3 topics) + subscriber
│   ├── 4D-3B4/                  # sensor probe/read/live exts + subscriber
│   └── common/                  # fastdds_udp.xml (reference)
└── src/                         # ── RUNTIME FRAMEWORK (Stage 3C) ──
    ├── g1_description/              # ✅ Robot description (XACRO)
    │   ├── xacro/g1.xacro
    │   ├── launch/description.launch.py
    │   └── test/                    # Level 3 launch integration tests
    ├── g1_msgs/                     # ✅ Custom messages — 6 ROSIDL messages
    │   └── msg/
    │       ├── Detection3D.msg      # PROVISIONAL — pending Gemini API
    │       ├── DetectionArray3D.msg # PROVISIONAL — pending Gemini API
    │       ├── SafetyEvent.msg      # ✅ Etapa 3B
    │       ├── SystemState.msg      # ✅ Etapa 3B
    │       ├── SafetyAction.msg     # ✅ Etapa 3B
    │       └── RecoveryEvent.msg    # ✅ Etapa 3B
    ├── watchdog_g1/                 # ✅ Etapa 3B
    ├── cross_consistency_observer/  # ✅ Etapa 3B — PRIMARY cross-domain observer
    ├── safety_orchestrator_g1/      # ✅ Etapa 3C — semantic runtime core
    │   ├── safety_orchestrator_g1/
    │   │   └── safety_orchestrator_g1.py
    │   └── test/
    │       └── test_orchestrator_transitions.py  # 60 unit tests Level 4
    ├── recovery_g1/                 # ✅ Etapa 3C — real recovery runtime
    │   └── recovery_g1/
    │       └── recovery_g1.py
    ├── test_g1_safety_layer/        # ✅ Etapa 3C — 15 Level 4 launch integration tests
    ├── agv_bringup/                 # ✅ Launch system + legacy AGV scripts
    │   ├── launch/
    │   │   ├── system_g1.launch.py        # ← CANONICAL G1 ENTRYPOINT
    │   │   ├── system_nav2_slam.launch.py # [LEGACY AGV]
    │   │   ├── system.launch.py           # [LEGACY AGV]
    │   │   ├── localization.launch.py     # [LEGACY AGV]
    │   │   └── navigation.launch.py       # [LEGACY AGV]
    │   └── scripts/
    │       ├── agv_watchdog_node.py       # [LEGACY AGV]
    │       └── agv_recovery_manager.py    # [LEGACY AGV]
    ├── safety_policy_node/          # ⚠️ LEGACY — replaced by safety_orchestrator_g1
    ├── agv_msgs/                    # 🔄 LEGACY — used ONLY by AGV legacy nodes
    ├── perception_node/             # 🔲 BLOCKED — Gemini API (Etapa 5+)
    └── rplidar_ros/                 # 🔄 LEGACY — AGV LiDAR, conditional
```

---

## Key Topics

| Topic | Type | Source | QoS | Status |
|-------|------|--------|-----|--------|
| `/tf_static` | `TFMessage` | `robot_state_publisher` | TRANSIENT_LOCAL | ✅ |
| `/safety_events` | `g1_msgs/SafetyEvent` | `watchdog_g1`, `cco`, `orchestrator` | Reliable depth 50 | ✅ 3C |
| `/system_state` | `g1_msgs/SystemState` | `safety_orchestrator_g1` | TRANSIENT_LOCAL depth 1 | ✅ 3C |
| `/safety_actions` | `g1_msgs/SafetyAction` | `safety_orchestrator_g1` | Reliable depth 10 | ✅ 3C |
| `/recovery_events` | `g1_msgs/RecoveryEvent` | `recovery_g1` | Reliable depth 50 | ✅ 3C |
| `/diagnostics` | `DiagnosticArray` | All nodes | Best Effort depth 10 | ✅ |
| `/joint_states` | `sensor_msgs/JointState` | Isaac custom mini-bridge | Reliable | ✅ 4D-3 (observation) |
| `/g1/base_pose` | `geometry_msgs/PoseStamped` | Isaac custom mini-bridge | Reliable | ✅ 4D-3 |
| `/g1/base_velocity` | `geometry_msgs/TwistStamped` | Isaac custom mini-bridge | Reliable | ✅ 4D-3 |
| `/g1/imu` | `sensor_msgs/Imu` | Isaac sensor read | Reliable | ✅ 4D-3 |
| `/g1/feet` | `std_msgs/Float32MultiArray` | Isaac sensor read | Reliable | ✅ 4D-3 (raw — DT-4D-008) |
| `/imu` | `Imu` | `g1_adapter_node` | Best Effort | ⏳ SDK |
| `/odom` | `Odometry` | `g1_adapter_node` | Best Effort | ⏳ SDK |
| `/cmd_vel_safe` | `Twist` | `safety_policy_node` | — | ⚠️ LEGACY |

---

## Custom Messages (`g1_msgs`)

| Message | Paradigm | Status |
|---------|----------|--------|
| `Detection3D` | 3D pose — `geometry_msgs/Pose` | PROVISIONAL — pending Gemini API |
| `DetectionArray3D` | Array of Detection3D | PROVISIONAL |
| `SafetyEvent` | Safety event bus | ✅ Etapa 3B |
| `SystemState` | Compound state `(Risk, Restriction)` | ✅ Etapa 3B |
| `SafetyAction` | Operational Vocabulary primitive | ✅ Etapa 3B |
| `RecoveryEvent` | Recovery event with retry semantics | ✅ Etapa 3B |

---

## Docker Images

| Image | Purpose | Status |
|-------|---------|--------|
| `pipeline-base` | Shared foundation — ROS2 Humble + slam + nav2 + xacro | ✅ |
| `pipeline-dev` | Local development — Base + RViz2 + debug tools | ✅ |
| `pipeline-runtime` | Production / CI — Base + compiled workspace | ✅ |
| `pipeline-sim` | Isaac Sim bridge — Base + sim-time configuration | 🔲 4D+ |

---

## Technical Debt Summary

### Post-3C Debt (`TECHNICAL_DEBT_3C.md`)

| Debt | Component | Priority |
|------|-----------|----------|
| `_state_lock` does not guarantee formal thread-safety | `safety_orchestrator_g1` | Layer 4 |
| No process groups / `setsid` — orphan subprocess risk | `recovery_g1` | Layer 4 |
| `_execute_transition()` requires `ActionExecutor` before SDK | `safety_orchestrator_g1` | Pre-SDK |
| `wait_for_primary_restore` mixes poller and reactor | `recovery_g1` | Post-SDK |
| Real `launch_testing` pending under real DDS | All | Post-SDK |

### Simulation / Infrastructure Debt (4A–4D)

| ID | Debt | Priority | Status |
|----|------|----------|--------|
| DT-4A-003 | Cross-container DDS characterization | — | ✅ Resolved (UDP forced, 4D-3B2) |
| DT-4A-004 | FastDDS vs CycloneDDS — Unitree SDK2 divergence | **High** | Open |
| DT-4B-003 | CycloneDDS vs FastRTPS for Unitree SDK | **High** | Open |
| DT-4C-004/005 | `World()` / ground-plane defaults not characterized | Low | Open |
| DT-4D-001 | `SimulationApp` → `full.streaming` exact cause | Medium | Frozen — avoided via direct `kit` |
| DT-4D-003 | T4 viability for RTX / Isaac Lab / RL | **High** | Open — mitigated (sensor RTX tolerated) |
| DT-4D-005 | "No heavy RTX" is log inference, not profiling | Low | Open |
| DT-4D-006 | `get_contact_sensor_raw_data` deprecated | Low | New |
| DT-4D-007 | `sub_live.py` `estado()` label miscalibrated | Low | New (3-line fix) |
| DT-4D-008 | Contacts as raw `Float32MultiArray`, not dedicated type | Medium | New |

---

## Invalid Claims

The following claims are **NOT valid** for this repository in its current state:

| Claim | Status | Reason |
|-------|--------|--------|
| Safety validated on hardware | ❌ | x86 runtime only — no physical validation |
| Thresholds defined | ❌ | All `RECOVERY_WINDOW_TBD` — pending SDK G1 |
| SDK G1 integrated | ❌ | `g1_adapter_node` blocked |
| Runtime **controls** the G1 | ❌ | 4D-3 is observation only — no commands issued |
| G1 standing / stable | ❌ | Falls without policy (expected); standing requires 4E |
| T8 arbitration complete | ❌ | DRAFT — PH-001 open |
| Recovery actions work on hardware | ❌ | Subprocess isolation validated x86 only |
| Isaac Lab runs on T4 | ❌ | Undemonstrated — DT-4D-003 |
| Zero RTX in sim | ❌ | Sensors pull a tolerated RTX plugin — "RTX tolerated", not zero |

---

## Design Standards

- **Reproducibility** — any machine running Docker can bring up the identical stack
- **Honest validation** — tests classified by what they actually validate, not what sounds impressive
- **Traceable decisions** — all architectural decisions documented in ADRs and Model documents
- **Transitional integrity** — legacy components explicitly marked, migration path documented
- **No hidden hardcodes** — all paths parametrizable via `LaunchConfiguration`
- **Epistemic honesty** — all provisional thresholds (`RECOVERY_WINDOW_TBD`) explicitly declared
- **One variable per experiment** — each validation step changes exactly one variable
- **Evidence first** — no conclusion without log evidence
- **Observation ≠ control** — telemetry validated; no command is issued to the robot until explicitly authorized

---

## Baseline Reference

This pipeline migrates from:

```
agv-pipeline-lab @ v1.0-audit-x86
```

The AGV baseline remains frozen as an audited reference. The G1 pipeline inherits the Nav2 stack, slam_toolbox, and EKF localization pattern — all hardware-agnostic components.

---

## Team

| Role | Responsible |
|------|-------------|
| Technical PM | ChatGPT |
| External Auditor | Gemini / MIT |
| Implementer / Auditor | Claude |
| Operator | Jorge Padilla |

---

*G1 ROS2 Pipeline — github.com/jorgerpg1213-mitech/g1-ros2-pipeline*

*Etapa 1 ✅ · 2 ✅ · 3A ✅ · 3B ✅ · 3C ✅ · 4A ✅ · 4B ✅ · 4C ✅ · 4D-1 ✅ · 4D-2 ✅ · 4D-3 ✅ · 4E 🔄 · 5A 🔒*

*86 tests · 0 failures · Isaac Sim 4.5.0 light path validated on T4 · G1 observable over ROS2 · Observer→orchestrator SafetyEvent ACK validated (4D-3D) · Next: 4E healthy standing baseline with plug-and-play policy*
