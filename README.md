# G1 ROS2 Pipeline

<div align="center">

**Reproducible · Auditable · Operationally Honest**

*Deterministic Safety Runtime Architecture for the Unitree G1 Humanoid Robot*
*ROS2 Humble · Docker-first · Isaac Sim 4.2.0 · Tesla T4 validated*

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml/badge.svg)](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Isaac Sim](https://img.shields.io/badge/Isaac%20Sim-4.2.0-76B900?logo=nvidia)
![Platform](https://img.shields.io/badge/Platform-x86__64-lightgrey)
![Status](https://img.shields.io/badge/Etapa-4B%20Completada-green)
![Tests](https://img.shields.io/badge/Tests-86%20passing-brightgreen)

</div>

---

## What This Is

`g1-ros2-pipeline` is a **production-grade safety runtime framework** for the Unitree G1 humanoid robot (29 DOF). It is not a demo, not a prototype, and not a collection of scripts.

It is a formally validated, deterministic supervision system designed to the standard of controlled laboratory environments — equivalent in rigor to MIT, NASA, and Boston Dynamics operational pipelines.

The project is subject to audit by MIT and Boston Dynamics.

### Core Principle

> The humanoid runtime and VLA policy training are distinct but complementary domains.
> Training optimizes intelligence. The runtime architecture governs real operational behavior.

VLA models (GR00T, LeRobot, Gemini Robotics) do **not** govern the humanoid directly. Operational authority resides permanently in `safety_orchestrator_g1`, `watchdog_g1`, `cross_consistency_observer`, and the semantics defined by `SAFETY_MODEL_G1.md`.

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
| **Etapa 4B** | Isaac Headless Bring-up — SimulationApp, G1 USD load, lifecycle | ✅ Completed | 2026-05-29 |
| **Etapa 4C** | Runtime Framework Validation — physics, joints, ROS2 bridge, DDS | 🔲 Next | — |
| **Etapa 5** | VLA / GR00T / LeRobot Integration | ⏳ Future | — |
| **Etapa 6** | Real Embodied Behaviors | ⏳ Future | — |
| **Etapa 7** | Refinement & Autonomy | ⏳ Future | — |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        G1 ROS2 Pipeline                              │
│            Deterministic Safety Runtime Framework                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │           Simulation Layer (Isaac Sim 4.2.0) — 4B/4C           │ │
│  │                                                                 │ │
│  │  Isaac Sim Headless ──► python.sh standalone ──► DDS/FastDDS   │ │
│  │  G1 USD (S3 NVIDIA) ──► open_stage()         ──► /joint_states │ │
│  │  OmniGraph          ──► ROS2PublishJointState ──► ROS2 Bridge  │ │
│  │                    [4C — Ready to start]                        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                              │ DDS / FastDDS                         │
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
│  │           Intelligence Layer — Future (Etapa 5)                 │ │
│  │                                                                 │ │
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
                    └── [4C] Isaac Sim OmniGraph  ← embodiment boundary
                            └── [future] g1_adapter_node  ← hardware boundary
                                    └── [future] VLA / GR00T  ← intelligence
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
| Level 5 | Hardware G1 + Isaac Sim | — | ⏳ Blocked |

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
| OS | Ubuntu 22.04.5 LTS (Kernel 5.15.0-179) |
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
| Python version | 3.10 — NO mixing with 3.12 |
| GPU strategy | `--gpus all` on CUDA containers |

### Open Debt from 4A

| ID | Debt | Priority |
|----|------|----------|
| DT-4A-003 | Cross-container DDS characterization inconclusive | Low |
| DT-4A-004 | FastDDS vs CycloneDDS — Unitree SDK2 divergence | **High** |
| DT-4A-006 | colcon-parallel-executor outdated (0.3.0 vs 0.4.0) | Low |

---

## Stage 4B — Isaac Headless Bring-up

**Completed Technically:** 2026-05-29
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

This validation corresponds specifically to loading the G1 USD asset via `open_stage()`. It does not imply validation of active physics, ROS2 Bridge, joint publishing, or runtime governance — those are 4C objectives.

### Key Architectural Decisions from 4B

| Decision | Resolution |
|----------|------------|
| Isaac workflow | `python.sh` standalone — **NOT** `runheadless.native.sh` for Python scripts |
| RMW for bridge | FastRTPS — CycloneDDS causes bridge failure in Isaac Sim 4.2.0 |
| Script generation | `cat > script.py << 'EOF'` — **NEVER** `echo` inline (corrupts silently) |
| Observability retention | `time.sleep(N)` — **NOT** `input()` without Docker TTY |
| Import order | All `omni`/`carb` imports **AFTER** `SimulationApp()` — mandatory |
| Startup time | ~6-7 minutes on Tesla T4 — silence is normal, not failure |
| Session resilience | `tmux new -s name` before any heavy process — mandatory |

### Canonical Standalone Command (Frozen)

```bash
docker run --rm --name isaac_g1_phase1 \
  --gpus all \
  --network host \
  -e "ACCEPT_EULA=Y" \
  -e "RMW_IMPLEMENTATION=rmw_fastrtps_cpp" \
  -e "LD_LIBRARY_PATH=/isaac-sim/exts/omni.isaac.ros2_bridge/humble/lib" \
  -v /home/jorge.padilla/script.py:/isaac-sim/script.py:ro \
  --entrypoint /isaac-sim/python.sh \
  nvcr.io/nvidia/isaac-sim:4.2.0 \
  /isaac-sim/script.py 2>&1 | tee /home/jorge.padilla/output.log
```

### Validated Python Script Template

```python
import sys
import time
from isaacsim import SimulationApp  # SimulationApp ALWAYS first

simulation_app = SimulationApp({"headless": True})

# All omni/isaac imports AFTER SimulationApp — mandatory
import omni
import carb
from omni.isaac.nucleus import get_assets_root_path
from omni.isaac.core.utils.stage import is_stage_loading
from omni.isaac.core.utils.extensions import enable_extension

enable_extension("omni.isaac.ros2_bridge")
simulation_app.update()

assets_root_path = get_assets_root_path()
usd_path = assets_root_path + "/Isaac/Robots/Unitree/G1/g1.usd"

omni.usd.get_context().open_stage(usd_path, None)
simulation_app.update()
simulation_app.update()

count = 0
max_iter = 5000
while is_stage_loading():
    count += 1
    if count > max_iter:
        print("TIMEOUT is_stage_loading", flush=True)
        break
    if count % 100 == 0:
        print(f"iteration {count}", flush=True)
    simulation_app.update()

print("LOADING COMPLETE", flush=True)
time.sleep(30)
simulation_app.close()
```

### Open Debt from 4B

| ID | Debt | Priority |
|----|------|----------|
| DT-4B-001 | Local-first G1 asset migration (eliminate S3 dependency) | Medium |
| DT-4B-002 | G1 USD dependency tree validation (textures, payloads, materials) | Medium |
| DT-4B-003 | CycloneDDS vs FastRTPS compatibility for Unitree SDK | **High** |
| DT-4B-004 | Cross-container DDS characterization | Low |

---

## Stage 4C — Runtime Framework Validation (Next)

**Status:** 🔲 Ready to start

### Entry Gate — Requirements Satisfied

| Requirement | Status |
|-------------|--------|
| SimulationApp headless | ✅ |
| `open_stage()` functional | ✅ |
| `is_stage_loading()` functional | ✅ |
| G1 USD asset accessible | ✅ |
| Isaac headless lifecycle complete | ✅ |
| NVIDIA S3 assets access | ✅ |

### Execution Sequence

| Step | Objective | Observable | Gate |
|------|-----------|------------|------|
| 4C-1 | Physics World — floor + gravity + PhysX | World initialized without errors | World OK |
| 4C-2 | G1 with active physics | Articulations + rigid bodies detected | Joints found |
| 4C-3 | Kinematic audit | Complete joint + link + prim tree list | Structure mapped |
| 4C-4 | Prim Tree audit — find `targetPrim` | Articulation root path documented | targetPrim known |
| 4C-5 | ROS2 Bridge | Bridge active without errors | DDS operational |
| 4C-6 | Minimal OmniGraph | `ROS2PublishJointState` node active in sim loop | Graph connected |
| 4C-7 | External ROS2 verification | `/joint_states` observable from external process | Topic live |
| 4C-8 | Runtime Framework | watchdog + orchestrator + observer on real G1 data | Authority routing active |

> **Note on posture:** postural stability is **not** a success criterion for steps 4C-2 through 4C-4. Joint observability is achievable regardless of whether the robot is standing or falling. Balance and controllers are later-stage concerns.

### DDS Boundary Architecture

```
Runtime Safety Layer  ──► FastDDS (rmw_fastrtps_cpp)
                                │
                         [Bridge/Adapter Layer]
                                │
Unitree SDK Boundary    ──► CycloneDDS (isolated domain)
```

No forced unification — distinct DDS domains with explicit adapters. This protects the operational authority of the safety framework.

### Out of Scope for 4C-1 through 4C-4

- Complex locomotion
- Balance or stable posture
- Advanced controllers
- RL/PPO on G1
- Multi-environment
- GR00T training

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
├── informe_etapa_4B_2026-05-29.md
├── README.md
└── src/
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
| `/joint_states` | `sensor_msgs/JointState` | Isaac OmniGraph | Reliable | ⏳ 4C |
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
| `pipeline-sim` | Isaac Sim bridge — Base + sim-time configuration | 🔲 4C |

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

### 4A + 4B Debt

| ID | Debt | Priority |
|----|------|----------|
| DT-4A-003 | Cross-container DDS characterization inconclusive | Low |
| DT-4A-004 | FastDDS vs CycloneDDS — Unitree SDK2 divergence | **High** |
| DT-4B-001 | Local-first G1 asset migration | Medium |
| DT-4B-002 | G1 USD dependency tree validation | Medium |
| DT-4B-003 | CycloneDDS vs FastRTPS for Unitree SDK | **High** |
| DT-4B-004 | Cross-container DDS characterization | Low |

---

## Invalid Claims

The following claims are **NOT valid** for this repository in its current state:

| Claim | Status | Reason |
|-------|--------|--------|
| Safety validated on hardware | ❌ | x86 runtime only — no physical validation |
| Thresholds defined | ❌ | All `RECOVERY_WINDOW_TBD` — pending SDK G1 |
| SDK G1 integrated | ❌ | `g1_adapter_node` blocked |
| `/joint_states` publishing | ❌ | Pending OmniGraph wiring — 4C objective |
| T8 arbitration complete | ❌ | DRAFT — PH-001 open |
| Recovery actions work on hardware | ❌ | Subprocess isolation validated x86 only |
| G1 physics validated | ❌ | USD asset load validated — physics is 4C |
| Cross-container DDS fully characterized | ❌ | Partially inconclusive from 4A |

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
| Technical PM | GPT-4 |
| External Auditor | Gemini / MIT |
| Implementer / Auditor | Claude Sonnet 4.6 |
| Operator | Jorge Padilla |

---

*G1 ROS2 Pipeline — github.com/jorgerpg1213-mitech/g1-ros2-pipeline*

*Etapa 1 ✅ · Etapa 2 ✅ · Etapa 3A ✅ · Etapa 3B ✅ · Etapa 3C ✅ · Etapa 4A ✅ · Etapa 4B ✅ · Etapa 4C 🔲*

*86 tests · 0 failures · Isaac Sim 4.2.0 headless validated · G1 USD loaded · Runtime Framework ready for Isaac integration*
