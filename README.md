# G1 ROS2 Pipeline

<div align="center">

**Reproducible · Auditable · Operationally Honest**

*Safety Runtime Architecture for the Unitree G1 Humanoid Robot*
*Built on ROS2 Humble · Docker · Isaac Sim integration planned*

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml/badge.svg)](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Platform](https://img.shields.io/badge/Platform-x86__64-lightgrey)
![Status](https://img.shields.io/badge/Etapa-3C%20En%20Progreso-orange)

</div>

---

## Overview

`g1-ros2-pipeline` is a production-grade ROS2 pipeline for the **Unitree G1** humanoid robot (29 DOF), designed for reproducible deployment across:

- **Physical robot** — Unitree G1 via SDK adapter
- **Isaac Sim** — NVIDIA simulation environment
- **x86 development** — full stack validation without hardware

The pipeline derives from a battle-tested AGV baseline (`agv-pipeline-lab @ v1.0-audit-x86`) and has been formally audited before migration to the G1 humanoid context.

Current focus: **Etapa 3 — Safety Runtime Architecture**. The semantic models, ADRs, skeleton runtime nodes, and Level 4 integration tests are complete. Transition to full runtime logic is in progress.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    G1 ROS2 Pipeline                         │
│              Etapa 3 — Safety Runtime Layer                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  g1_description ──► robot_state_publisher                   │
│       (XACRO)            │                                  │
│                          ▼                                  │
│                      /tf_static (TRANSIENT_LOCAL)           │
│                                                             │
├──────────────── Safety Layer (Etapa 3B) ────────────────────┤
│                                                             │
│  watchdog_g1 ──────────────────────────────────────────►   │
│  cross_consistency_observer ───────────────────────────►   │
│                                          /safety_events     │
│                                               │             │
│                                               ▼             │
│                               safety_orchestrator_g1        │
│                               /system_state (TRANSIENT)     │
│                               /safety_actions               │
│                                               │             │
│                                               ▼             │
│                                         recovery_g1         │
│                                         /recovery_events    │
│                                                             │
├──────────── Transicional / Legacy (activos) ────────────────┤
│                                                             │
│  safety_policy_node    [TRANSICIONAL — rediseño en 3C]      │
│  agv_watchdog_node     [TRANSICIONAL — reemplazar 3C]       │
│  agv_recovery_manager  [TRANSICIONAL — reemplazar 3C]       │
│  agv_msgs              [TRANSICIONAL — dependencia viva]    │
│                                                             │
├──────────── Bloqueado — Dependencias Externas ──────────────┤
│                                                             │
│  g1_adapter_node       [BLOQUEADO — SDK Unitree G1]         │
│  gemini_perception_node [BLOQUEADO — Gemini API]            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.x
- Ubuntu 22.04 (x86_64)
- 8GB RAM minimum

### 1. Clone the repository

```bash
git clone https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline.git
cd g1-ros2-pipeline
```

### 2. Build the Docker images

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

---

## Docker Images

| Image | Purpose | Contents |
|-------|---------|----------|
| `pipeline-base` | Shared foundation | ROS2 Humble + slam-toolbox + nav2 + xacro |
| `pipeline-dev` | Local development | Base + RViz2 + debug tools |
| `pipeline-runtime` | Production / CI | Base + workspace compiled — `install/` baked in |
| `pipeline-sim` | Isaac Sim bridge | Base + sim-time configuration |

---

## Repository Structure

```
g1-ros2-pipeline/
├── docker/
│   ├── Dockerfile.base
│   ├── Dockerfile.dev
│   ├── Dockerfile.runtime
│   ├── Dockerfile.sim
│   └── entrypoint.sh
├── src/
│   ├── g1_description/              # ✅ Robot description (XACRO Phase 4A)
│   │   ├── xacro/g1.xacro           # Phase 4B pending USD oficial Unitree
│   │   ├── launch/description.launch.py
│   │   └── test/                    # Level 3 launch integration tests
│   ├── g1_msgs/                     # ✅ Custom messages — 6 mensajes ROSIDL
│   │   └── msg/
│   │       ├── Detection3D.msg      # PROVISIONAL — pending Gemini API
│   │       ├── DetectionArray3D.msg # PROVISIONAL — pending Gemini API
│   │       ├── SafetyEvent.msg      # ✅ Etapa 3B
│   │       ├── SystemState.msg      # ✅ Etapa 3B
│   │       ├── SafetyAction.msg     # ✅ Etapa 3B
│   │       └── RecoveryEvent.msg    # ✅ Etapa 3B
│   ├── watchdog_g1/                 # ✅ Etapa 3B — skeleton runtime
│   ├── cross_consistency_observer/  # ✅ Etapa 3B — skeleton runtime
│   ├── safety_orchestrator_g1/      # ✅ Etapa 3B — skeleton runtime
│   ├── recovery_g1/                 # ✅ Etapa 3B — skeleton runtime
│   ├── test_g1_safety_layer/        # ✅ Etapa 3C — Level 4 tests (15 tests)
│   ├── agv_bringup/                 # ✅ Launch system
│   │   └── launch/
│   │       ├── system_g1.launch.py        # ← CANONICAL G1 ENTRYPOINT
│   │       ├── system_nav2_slam.launch.py # [LEGACY AGV]
│   │       ├── system.launch.py           # [LEGACY AGV]
│   │       ├── localization.launch.py     # [LEGACY AGV]
│   │       └── navigation.launch.py       # [LEGACY AGV]
│   ├── safety_policy_node/          # 🔄 TRANSICIONAL — rediseño en Etapa 3C
│   ├── agv_msgs/                    # 🔄 TRANSICIONAL — dependencia viva
│   ├── agv_bringup/ (watchdog/recovery legacy) # 🔄 TRANSICIONAL
│   ├── perception_node/             # 🔲 Placeholder — Gemini API Phase 10
│   └── rplidar_ros/                 # 🔄 Condicional — LiDAR externo
└── .github/
    └── workflows/
        ├── ci-build.yml             # CI usando pipeline-runtime:ci
        └── ci-audit.yml             # Audit workflow (tags)
```

---

## Testing

| Level | Type | Suite | Tests | Status |
|-------|------|-------|-------|--------|
| Level 1 | Smoke | `smoke_test_watchdog` | 4 | ✅ PASS |
| Level 1 | Smoke | `smoke_test_recovery_manager` | 5 | ✅ PASS |
| Level 2 | Build | `colcon build` en `pipeline-runtime` | — | ✅ PASS |
| Level 2 | CI | `ci-build.yml` — `pipeline-runtime:ci` | — | ✅ Configured |
| Level 3 | Launch Integration | `test_description_launch.py` | 2 | ✅ PASS |
| Level 4 | Safety Layer Runtime | `test_g1_safety_layer` | 15 | ✅ PASS |
| Level 5 | Certification | Hardware G1 + Isaac Sim | — | ⏳ Blocked — SDK/VM |

**Total: 26 tests, 0 failures.**

> **Level 4 scope:** valida que los 4 nodos del safety layer levantan, publican heartbeat en `/diagnostics`, exponen `/system_state` con QoS Transient Local, y producen eventos observables en `/safety_events` y `/recovery_events`. No valida safety físico, thresholds reales, ni hardware G1.

---

## Key Topics

| Topic | Type | Source | QoS | Status |
|-------|------|--------|-----|--------|
| `/tf_static` | `TFMessage` | `robot_state_publisher` | TRANSIENT_LOCAL | ✅ |
| `/safety_events` | `g1_msgs/SafetyEvent` | `watchdog_g1`, `cross_consistency_observer`, `safety_orchestrator_g1` | Reliable depth 50 | ✅ Skeleton |
| `/system_state` | `g1_msgs/SystemState` | `safety_orchestrator_g1` | TRANSIENT_LOCAL depth 1 | ✅ Skeleton |
| `/safety_actions` | `g1_msgs/SafetyAction` | `safety_orchestrator_g1` | Reliable depth 10 | ✅ Skeleton |
| `/recovery_events` | `g1_msgs/RecoveryEvent` | `recovery_g1` | Reliable depth 50 | ✅ Skeleton |
| `/diagnostics` | `DiagnosticArray` | Todos los nodos | Best Effort depth 10 | ✅ |
| `/imu` | `Imu` | `g1_adapter_node` | Best Effort | ⏳ SDK |
| `/odom` | `Odometry` | `g1_adapter_node` | Best Effort | ⏳ SDK |
| `/cmd_vel_safe` | `Twist` | `safety_policy_node` | — | 🔄 Transicional |

---

## Custom Messages (`g1_msgs`)

| Mensaje | Paradigma | Estado |
|---------|-----------|--------|
| `Detection3D` | 3D pose — `geometry_msgs/Pose` | PROVISIONAL — pending Gemini API |
| `DetectionArray3D` | Array de Detection3D | PROVISIONAL |
| `SafetyEvent` | Bus de eventos de safety | ✅ Etapa 3B |
| `SystemState` | Compound state `(Risk, Restriction)` | ✅ Etapa 3B |
| `SafetyAction` | Primitiva del Vocabulario Operacional | ✅ Etapa 3B |
| `RecoveryEvent` | Evento de recovery con retry semantics | ✅ Etapa 3B |

---

## Development Roadmap

| Etapa | Descripción | Estado |
|-------|-------------|--------|
| Etapa 1 | Infraestructura Base — ROS2, Docker, CI, runtime discipline | ✅ Cerrada |
| Etapa 2 | Disciplina Operacional — anti-patterns, observabilidad, reproducibilidad | ✅ Cerrada |
| Etapa 3A | Modelos Semánticos + ADRs — SAFETY/RESILIENCE/RECOVERY MODEL, ADR-002/003 | ✅ Cerrada |
| Etapa 3B | Skeleton Runtime ROS2 — 4 nodos + g1_msgs + threading architecture | ✅ Cerrada |
| Etapa 3C | Level 4 Runtime Validation + Integration — transition logic, scheduler, T8 | 🔄 En progreso |
| Etapa 4 | Simulación e Integración — Isaac Lab, SDK G1, thresholds reales | ⏳ Futura |
| Etapa 5 | Integración VLA/GR00T/LeRobot — policy layers, embodied AI | ⏳ Futura |
| Etapa 6 | Behaviors Embodied Reales — locomoción, manipulation, navigation | ⏳ Futura |
| Etapa 7 | Refinamiento y Autonomía — policy tuning, long-horizon behaviors | ⏳ Futura |

---

## Design Standards

- **Reproducibility** — any machine running Docker can bring up the identical stack
- **Honest validation** — tests classified by what they actually validate, not what sounds impressive
- **Traceable decisions** — all architectural decisions documented in ADRs and Model documents
- **Transicional integrity** — legacy components explicitly marked, migration path documented
- **No hidden hardcodes** — all paths parametrizable via `LaunchConfiguration`

---

## Invalid Claims

The following claims are **NOT valid** for this repository in its current state:

- ❌ Safety is validated on hardware — skeleton runtime only, no physical validation
- ❌ Recovery logic is implemented — mock events only, no real RecoveryActions
- ❌ Thresholds are defined — all `TBD` pending SDK G1 characterization
- ❌ SDK G1 is integrated — `g1_adapter_node` blocked, no real `/imu` or `/odom`
- ❌ Isaac Lab is ready — `pipeline-sim` image exists, integration blocked pending MIT VM
- ❌ T8 arbitration is complete — DRAFT, PH-001 open

---

## Baseline Reference

This pipeline migrates from:

```
agv-pipeline-lab @ v1.0-audit-x86
```

The AGV baseline remains frozen as an audited reference. The G1 pipeline inherits the Nav2 stack, slam_toolbox, and EKF localization pattern — all hardware-agnostic components.

---

*G1 ROS2 Pipeline — github.com/jorgerpg1213-mitech/g1-ros2-pipeline*
*Etapa 3A ✅ | Etapa 3B ✅ | Etapa 3C 🔄 | Commit: 26833ac*
