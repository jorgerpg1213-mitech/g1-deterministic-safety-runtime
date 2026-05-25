# G1 ROS2 Pipeline

<div align="center">

**Reproducible · Auditable · Operationally Honest**

*Safety Runtime Architecture for the Unitree G1 Humanoid Robot*
*Built on ROS2 Humble · Docker · Isaac Sim integration planned*

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml/badge.svg)](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Platform](https://img.shields.io/badge/Platform-x86__64-lightgrey)
![Status](https://img.shields.io/badge/Etapa-3C%20Cerrada-green)

</div>

---

## Overview

`g1-ros2-pipeline` is a production-grade ROS2 pipeline for the **Unitree G1** humanoid robot (29 DOF), designed for reproducible deployment across:

- **Physical robot** — Unitree G1 via SDK adapter (pending)
- **Isaac Sim** — NVIDIA simulation environment (pending MIT VM)
- **x86 development** — full stack validation without hardware

The pipeline derives from a battle-tested AGV baseline (`agv-pipeline-lab @ v1.0-audit-x86`) and has been formally audited before migration to the G1 humanoid context.

**Etapa 3C cerrada (2026-05-24):** transition logic real implementada — TransitionEvaluator con Transition Matrix completa (TX-001 a TX-010), PriorityScheduler con 4 buckets, T8Arbitrator DRAFT, recovery runtime con subprocess isolation, y 86 tests validados (Level 1 a Level 4).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    G1 ROS2 Pipeline                         │
│              Etapa 3C — Safety Runtime Layer                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  g1_description ──► robot_state_publisher                   │
│       (XACRO)            │                                  │
│                          ▼                                  │
│                      /tf_static (TRANSIENT_LOCAL)           │
│                                                             │
├──────────── Safety Layer (Etapas 3B + 3C) ─────────────────┤
│                                                             │
│  watchdog_g1 ──────────────────────────────────────────►   │
│  cross_consistency_observer ───────────────────────────►   │
│                                          /safety_events     │
│                                               │             │
│                                               ▼             │
│                               safety_orchestrator_g1        │
│                          (TransitionEvaluator + Scheduler   │
│                           + T8Arbitrator + CompoundState)   │
│                               /system_state (TRANSIENT)     │
│                               /safety_actions               │
│                                               │             │
│                                               ▼             │
│                                         recovery_g1         │
│                              (subprocess isolation real +   │
│                               retry policy + escalation)    │
│                                         /recovery_events    │
│                                                             │
├──────────── Legacy / Transicional (activos) ────────────────┤
│                                                             │
│  safety_policy_node    [LEGACY — reemplazado por           │
│                         safety_orchestrator_g1 en 3C]       │
│  agv_watchdog_node     [LEGACY — en agv_bringup/scripts]   │
│  agv_recovery_manager  [LEGACY — en agv_bringup/scripts]   │
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

## Docker Images

| Image | Purpose | Contents |
|-------|---------|----------|
| `pipeline-base` | Shared foundation | ROS2 Humble + slam-toolbox + nav2 + xacro |
| `pipeline-dev` | Local development | Base + RViz2 + debug tools |
| `pipeline-runtime` | Production / CI | Base + workspace compiled — `install/` baked in |
| `pipeline-sim` | Isaac Sim bridge | Base + sim-time configuration — BLOQUEADO MIT VM |

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
├── docker-compose.yml
├── ARCHITECTURE_DECISIONS.md
├── TECHNICAL_DEBT_3C.md          # Deuda técnica post-auditoría 3C
├── README.md
└── src/
    ├── g1_description/              # ✅ Robot description (XACRO Phase 4A)
    │   ├── xacro/g1.xacro           # Phase 4B pending USD oficial Unitree
    │   ├── launch/description.launch.py
    │   └── test/                    # Level 3 launch integration tests
    ├── g1_msgs/                     # ✅ Custom messages — 6 mensajes ROSIDL
    │   └── msg/
    │       ├── Detection3D.msg      # PROVISIONAL — pending Gemini API
    │       ├── DetectionArray3D.msg # PROVISIONAL — pending Gemini API
    │       ├── SafetyEvent.msg      # ✅ Etapa 3B
    │       ├── SystemState.msg      # ✅ Etapa 3B
    │       ├── SafetyAction.msg     # ✅ Etapa 3B
    │       └── RecoveryEvent.msg    # ✅ Etapa 3B
    ├── watchdog_g1/                 # ✅ Etapa 3B — detector y reporter de condiciones
    ├── cross_consistency_observer/  # ✅ Etapa 3B — observador cross-domain PRIMARY
    ├── safety_orchestrator_g1/      # ✅ Etapa 3C — runtime semántico real
    │   ├── safety_orchestrator_g1/
    │   │   └── safety_orchestrator_g1.py  # TransitionEvaluator + PriorityScheduler + T8Arbitrator
    │   └── test/
    │       └── test_orchestrator_transitions.py  # 60 unit tests Level 4
    ├── recovery_g1/                 # ✅ Etapa 3C — recovery runtime real
    │   └── recovery_g1/
    │       └── recovery_g1.py       # subprocess isolation + retry policy + escalation
    ├── test_g1_safety_layer/        # ✅ Etapa 3C — Level 4 launch integration tests (15 tests)
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
    ├── safety_policy_node/          # ⚠️ LEGACY — reemplazado semánticamente por safety_orchestrator_g1
    ├── agv_msgs/                    # 🔄 TRANSICIONAL — dependencia viva de nodos legacy
    ├── perception_node/             # 🔲 BLOQUEADO — Gemini API Phase 10
    └── rplidar_ros/                 # 🔄 LEGACY — LiDAR AGV, condicional
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
| Level 4 | Safety Layer Launch | `test_g1_safety_layer` | 15 | ✅ PASS |
| Level 4 | Transition Logic Unit | `test_orchestrator_transitions` | 60 | ✅ PASS |
| Level 5 | Certification | Hardware G1 + Isaac Sim | — | ⏳ Blocked — SDK/VM |

**Total: 86 tests, 0 failures.**

> **Level 4 launch scope:** valida que los 4 nodos del safety layer levantan, publican heartbeat en `/diagnostics`, exponen `/system_state` con QoS Transient Local, y producen eventos observables en `/safety_events` y `/recovery_events`.

> **Level 4 unit scope:** valida TransitionEvaluator (TX-001 a TX-010), PriorityScheduler (4 buckets, FIFO, drain order), T8Arbitrator (reglas R1-R4, ARBITRATION_PENDING), edge cases (R5 committed, T1 no-skip, overflow), y precondición universal de recovery. Sin ROS2 — lógica pura.

---

## Safety Runtime — Componentes 3C

### TransitionEvaluator

Evalúa la Transition Matrix del SAFETY_MODEL_G1. Implementa las 12 filas (TX-001 a TX-010 incluyendo TX-006a/b/c) con fidelidad semántica completa. Sin side effects — recibe `(event, state)`, retorna `dict` o `None`.

### PriorityScheduler

4 buckets independientes: `CRITICAL_INTERRUPT` → `COMMIT_TERMINAL` → `NORMAL` → `RECOVERY`. Drain en orden de prioridad + FIFO dentro del bucket.

### T8Arbitrator (DRAFT — PH-001)

Conflict resolution entre transiciones de igual prioridad. Reglas: (1) CRITICAL_INTERRUPT: mayor `authority_effectiveness` gana. (2) NORMAL: mayor `target_risk_level` gana. (3) RECOVERY: más conservadora gana. (4) Empate: `ARBITRATION_PENDING` observable.

### CompoundState

Par `(Risk Level, Restriction Level)` — unidad de estado del sistema. Propiedad exclusiva de Thread 2. `r5_committed` flag irreversible post TX-005.

### recovery_g1 Runtime

5 RecoveryActions reales ejecutables en x86: `restart_noncritical_node`, `restart_critical_node`, `request_operator_intervention`, `restore_nav_stack`, `wait_for_primary_restore`. Subprocess isolation con tracking y cleanup. Retry policy con cooldown real.

---

## Key Topics

| Topic | Type | Source | QoS | Status |
|-------|------|--------|-----|--------|
| `/tf_static` | `TFMessage` | `robot_state_publisher` | TRANSIENT_LOCAL | ✅ |
| `/safety_events` | `g1_msgs/SafetyEvent` | `watchdog_g1`, `cross_consistency_observer`, `safety_orchestrator_g1` | Reliable depth 50 | ✅ 3C |
| `/system_state` | `g1_msgs/SystemState` | `safety_orchestrator_g1` | TRANSIENT_LOCAL depth 1 | ✅ 3C |
| `/safety_actions` | `g1_msgs/SafetyAction` | `safety_orchestrator_g1` | Reliable depth 10 | ✅ 3C |
| `/recovery_events` | `g1_msgs/RecoveryEvent` | `recovery_g1` | Reliable depth 50 | ✅ 3C |
| `/diagnostics` | `DiagnosticArray` | Todos los nodos | Best Effort depth 10 | ✅ |
| `/imu` | `Imu` | `g1_adapter_node` | Best Effort | ⏳ SDK |
| `/odom` | `Odometry` | `g1_adapter_node` | Best Effort | ⏳ SDK |
| `/cmd_vel_safe` | `Twist` | `safety_policy_node` | — | ⚠️ LEGACY |

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
| Etapa 3C | Transition Logic Real — TransitionEvaluator, Scheduler, T8, recovery runtime, 86 tests | ✅ Cerrada |
| Etapa 4 | SDK Integration — SDK G1, thresholds reales, locomotion semantics, ActionExecutor | ⏳ Bloqueado — SDK |
| Etapa 5 | Isaac Sim Integration — MIT VM, Phase 4B URDF real, pipeline-sim validation | ⏳ Bloqueado — MIT VM |
| Etapa 6 | Perception Layer — Gemini Robotics API, gemini_perception_node, Phase 10 | ⏳ Bloqueado — API |
| Etapa 7 | Certification — hardware validation, thresholds reales, safety audit | ⏳ Post-SDK |

---

## Technical Debt (Post-3C)

Registrado en `TECHNICAL_DEBT_3C.md`. Deudas identificadas en auditoría post-3C:

| Deuda | Componente | Urgencia |
|-------|-----------|---------|
| `_state_lock` no garantiza thread-safety formal | `safety_orchestrator_g1` | Capa 4 |
| No usa process groups / `setsid` — riesgo orphan subprocess | `recovery_g1` | Capa 4 |
| `_execute_transition()` requiere `ActionExecutor` antes de SDK | `safety_orchestrator_g1` | Pre-SDK |
| `wait_for_primary_restore` mezcla poller y reactor | `recovery_g1` | Post-SDK |
| `launch_testing` real pendiente bajo DDS real | Todos | Post-SDK |

---

## Design Standards

- **Reproducibility** — any machine running Docker can bring up the identical stack
- **Honest validation** — tests classified by what they actually validate, not what sounds impressive
- **Traceable decisions** — all architectural decisions documented in ADRs and Model documents
- **Transicional integrity** — legacy components explicitly marked, migration path documented
- **No hidden hardcodes** — all paths parametrizable via `LaunchConfiguration`
- **Epistemic honesty** — `RECOVERY_WINDOW_TBD` and all provisional thresholds explicitly declared

---

## Invalid Claims

The following claims are **NOT valid** for this repository in its current state:

- ❌ Safety is validated on hardware — x86 runtime only, no physical validation
- ❌ Thresholds are defined — all `RECOVERY_WINDOW_TBD` pending SDK G1 characterization
- ❌ SDK G1 is integrated — `g1_adapter_node` blocked, no real `/imu` or `/odom`
- ❌ Isaac Lab is ready — `pipeline-sim` image exists, integration blocked pending MIT VM
- ❌ T8 arbitration is complete — DRAFT, PH-001 open
- ❌ Recovery actions work on hardware — subprocess isolation validated x86 only
- ✅ Recovery runtime implementado con subprocess isolation — sin SDK, sin hardware

---

## Baseline Reference

This pipeline migrates from:

```
agv-pipeline-lab @ v1.0-audit-x86
```

The AGV baseline remains frozen as an audited reference. The G1 pipeline inherits the Nav2 stack, slam_toolbox, and EKF localization pattern — all hardware-agnostic components.

---

*G1 ROS2 Pipeline — github.com/jorgerpg1213-mitech/g1-ros2-pipeline*
*Etapa 3A ✅ | Etapa 3B ✅ | Etapa 3C ✅ | Commit: a6d2efe*
