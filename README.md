# G1 ROS2 Pipeline

<div align="center">

**Reproducible · Switchable · Auditable**

*Autonomous navigation and perception pipeline for the Unitree G1 humanoid robot*
*Built on ROS2 Humble · Docker · Isaac Sim ready*

[![CI Build](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml/badge.svg)](https://github.com/jorgerpg1213-mitech/g1-ros2-pipeline/actions/workflows/ci-build.yml)
![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Platform](https://img.shields.io/badge/Platform-x86__64-lightgrey)
![Status](https://img.shields.io/badge/Status-Phase%206%20Active-orange)

</div>

---

## Overview

`g1-ros2-pipeline` is a production-grade ROS2 pipeline for the **Unitree G1** humanoid robot (29 DOF), designed for reproducible deployment across:

- **Physical robot** — Unitree G1 via SDK adapter
- **Isaac Sim** — NVIDIA simulation environment
- **x86 development** — full stack validation without hardware

The pipeline derives from a battle-tested AGV baseline (`agv-pipeline-lab @ v1.0-audit-x86`) and has been formally audited before migration to the G1 humanoid context.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  G1 ROS2 Pipeline                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  g1_description ──► robot_state_publisher           │
│       (XACRO)            │                          │
│                          ▼                          │
│                      /tf_static                     │
│                          │                          │
│              ┌───────────┴────────────┐             │
│              ▼                        ▼             │
│         slam_toolbox            ekf_filter_node     │
│           /map                 /odometry/filtered   │
│              │                        │             │
│              └───────────┬────────────┘             │
│                          ▼                          │
│                    safety_policy_node               │
│                    /cmd_vel_safe                    │
│                          │                          │
│              ┌───────────┴────────────┐             │
│              ▼                        ▼             │
│        agv_watchdog_node      agv_recovery_manager  │
│        (transicional)         (transicional)        │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  PENDING SDK (Phase 10)                      │   │
│  │  g1_adapter_node ◄──► Unitree G1 SDK         │   │
│  │  gemini_perception_node ◄──► Gemini API      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
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
# Build base image
docker build -f docker/Dockerfile.base -t pipeline-base:latest .

# Build runtime image (includes colcon build)
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

### 4. Run the test suite

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
│   ├── Dockerfile.base         # Shared ROS2 foundation
│   ├── Dockerfile.dev          # Development image
│   ├── Dockerfile.runtime      # Production image
│   ├── Dockerfile.sim          # Isaac Sim image
│   └── entrypoint.sh           # Container entrypoint
├── src/
│   ├── g1_description/         # ✅ Robot description (XACRO Phase 4A)
│   │   ├── xacro/g1.xacro      # G1 skeleton — Phase 4B pending USD
│   │   ├── launch/             # description.launch.py
│   │   └── test/               # Level 3 launch integration tests
│   ├── g1_msgs/                # ✅ G1 custom messages (Detection3D, DetectionArray3D)
│   ├── agv_bringup/            # ✅ Launch system + watchdog + recovery
│   │   ├── launch/
│   │   │   ├── system_g1.launch.py        # ← CANONICAL G1 ENTRYPOINT
│   │   │   ├── system_nav2_slam.launch.py # [LEGACY AGV]
│   │   │   ├── system.launch.py           # [LEGACY AGV]
│   │   │   ├── localization.launch.py     # [LEGACY AGV]
│   │   │   └── navigation.launch.py       # [LEGACY AGV]
│   │   ├── config/             # Nav2, EKF, SLAM params
│   │   └── test/               # Level 1 smoke tests
│   ├── safety_policy_node/     # 🔄 Safety filter (transicional — 2D→3D pending)
│   ├── perception_node/        # 🔲 Gemini perception placeholder (Phase 10)
│   ├── agv_msgs/               # 🔄 Legacy messages (transicional dependency)
│   └── rplidar_ros/            # 🔄 LiDAR driver (conditional — external LiDAR)
└── .github/
    └── workflows/
        ├── ci-build.yml        # CI using pipeline-runtime:ci
        └── ci-audit.yml        # Audit workflow (tags)
```

---

## Testing

The pipeline uses a 5-level testing hierarchy:

| Level | Type | Suite | Status |
|-------|------|-------|--------|
| Level 1 | Smoke / Structural | `smoke_test_watchdog` (4 tests) | ✅ PASS |
| Level 1 | Smoke / Structural | `smoke_test_recovery_manager` (5 tests) | ✅ PASS |
| Level 2 | Build Validation | `colcon build` in `pipeline-runtime` | ✅ PASS |
| Level 2 | CI Representativo | `ci-build.yml` — `pipeline-runtime:ci` | ✅ Configured |
| Level 3 | Launch Integration | `test_description_launch.py` (2 tests) | ✅ PASS |
| Level 4 | Reliability | Watchdog/Recovery ROS2 real | ⏳ Phase 6 pending |
| Level 5 | Certification | Hardware G1 + Isaac Sim | ⏳ Blocked — SDK/VM |

> **Design principle:** Level 1 smoke tests validate structural integrity. Level 3+ tests validate real ROS2 graph behavior with DDS communication.

---

## Key Topics

| Topic | Type | Source | Notes |
|-------|------|--------|-------|
| `/tf_static` | `TFMessage` | `robot_state_publisher` | QoS: TRANSIENT_LOCAL |
| `/tf` | `TFMessage` | `slam_toolbox` | map → odom → base_link |
| `/scan` | `LaserScan` | External LiDAR / Isaac | Conditional |
| `/imu` | `Imu` | `g1_adapter_node` | ⏳ Pending SDK |
| `/odom` | `Odometry` | `g1_adapter_node` | ⏳ Pending SDK |
| `/odometry/filtered` | `Odometry` | `ekf_filter_node` | Placeholder — no data until SDK |
| `/cmd_vel_safe` | `Twist` | `safety_policy_node` | Safety-filtered commands |

---

## Custom Messages

### `g1_msgs/Detection3D`
```
string class_name
float32 confidence
geometry_msgs/Pose pose
geometry_msgs/Vector3 dimensions
float64 timestamp
```

### `g1_msgs/DetectionArray3D`
```
Detection3D[] detections
```

> **Note:** `g1_msgs` uses a 3D spatial paradigm (`geometry_msgs/Pose`) distinct from the legacy AGV 2D pixel-based schema. These are not interchangeable.

---

## Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Repository bootstrap + clean migration from AGV | ✅ Complete |
| 2 | Multi-image Docker + formal architecture (10 ADRs) | ✅ Complete |
| 3 | Docker Compose with profiles | ✅ Complete |
| 4A | G1 robot description — XACRO skeleton | ✅ Complete |
| 5 | Interface contracts — `g1_msgs`, `interfaces.md` | ✅ Complete |
| 6 | CI/CD + Testing — Foundation Validation Layer | 🔄 Active |
| 4B | Full URDF from official Unitree USD | ⏳ Blocked — MIT VM + Isaac Lab |
| 7 | Auditable parameters | ⏳ Pending |
| 8 | Isaac Sim integration | ⏳ Blocked — MIT VM |
| 9 | Production documentation | ⏳ Pending |
| 10 | G1 + Gemini Robotics end-to-end | ⏳ Blocked — SDK + hardware |

---

## Design Standards

This pipeline is built to the following standards:

- **Reproducibility** — any machine running Docker can bring up the identical stack
- **Honest validation** — tests are classified by what they actually validate, not what sounds impressive
- **Traceable decisions** — all architectural decisions documented in ADRs
- **Transicional integrity** — legacy components explicitly marked, migration path documented
- **No hidden hardcodes** — all paths parametrizable via `LaunchConfiguration` or environment variables

---

## Baseline Reference

This pipeline migrates from:

```
agv-pipeline-lab @ v1.0-audit-x86
```

The AGV baseline remains frozen as an audited reference. The G1 pipeline inherits:
- Nav2 stack (hardware-agnostic)
- slam_toolbox (hardware-agnostic)
- EKF localization pattern
- Watchdog + recovery architecture (semantic refactor pending Phase 6)
- Launch file structure

---

## License

Internal research pipeline — MiTech Robotics Lab

---

<div align="center">

*Built with ROS2 Humble · Unitree G1 · NVIDIA Isaac Sim*
*Audit standard: MIT / NASA / Boston Dynamics*

</div>
