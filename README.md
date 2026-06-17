# G1 Deterministic Safety Runtime

**Reproducible · Auditable · Operationally Honest**

*Deterministic Safety Runtime Architecture for the Unitree G1 Humanoid Robot*
*ROS2 Humble · Docker-first · Isaac Sim 4.5.0 · Tesla T4*


![CI Audit](https://img.shields.io/badge/CI%20Audit-enabled-brightgreen)
![CI Build](https://img.shields.io/badge/CI%20Build-enabled-brightgreen)

![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros)
![Docker](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker)
![Isaac Sim](https://img.shields.io/badge/Isaac%20Sim-4.5.0-76B900?logo=nvidia)
![Stage](https://img.shields.io/badge/Stage-4F%20in%20progress-yellow)



---

## What This Is

`g1-deterministic-safety-runtime` is a **deterministic safety runtime framework** for the Unitree G1 humanoid robot (37 DOF): a supervision system that observes robot state, decides by severity, acts through recovery, and measures its own latency.

It is engineered to **laboratory rigor** — reproducible, evidence-based, with validated and non-validated claims explicitly separated. This repository targets **audit-readiness mapped to MIT / NASA / Boston Dynamics standards of rigor**. It does not claim certified medical or aerospace compliance.

### Core Principle

> Training optimizes intelligence. The runtime architecture governs operational behavior.

VLA models (GR00T, LeRobot, Gemini Robotics) do **not** govern the humanoid directly. Operational authority resides in `safety_orchestrator_g1`, `cross_consistency_observer`, `watchdog_g1`, and `recovery_g1`.

---

## Project Status (2026-06-16)

| Stage | Description | Status |
|-------|-------------|--------|
| Etapa 1 | Infrastructure Base | ✅ Closed |
| Etapa 2 | Operational Discipline | ✅ Closed |
| Etapa 3A | Semantic Models + ADRs | ✅ Closed |
| Etapa 3B | ROS2 Runtime Skeleton | ✅ Closed |
| Etapa 3C | Transition Logic — 86 tests | ✅ Closed |
| Etapa 4A | Infrastructure & DDS | ✅ Closed |
| Etapa 4B | Isaac Headless Bring-up (4.2.0) | ✅ Closed |
| Etapa 4C | Physical & Control Characterization | ✅ Closed |
| Etapa 4D | ROS2 Feasibility + Observability + Loop closure | ✅ Closed |
| Etapa 4E | Healthy passive baseline + state validation | ✅ Closed for runtime/paper scope; active PD deferred |
| Etapa 4F | Safety Runtime Enrichment (P1–P5 done, P6 pending) | 🔄 In progress |
| Etapa 5A | Isaac Lab Bring-up | 🔒 Blocked (out of T4 critical path) |
| Etapa 5–7 | VLA / Embodied / Autonomy | ⏳ Future |

**Current frontier:** Stage 4F — the framework now decides by severity, detects data-flow degradation, has an auditable transition matrix, integrates recovery in a real pipeline, and has measured latency on hardware. Stage 4F-P6 (fault injection) is pending.

---

## What Is Validated vs Not Validated

Honest separation is the core discipline of this project. Claims are classified by what the evidence actually supports.

### Validated (with log evidence)

- **Deterministic runtime core (3C):** TransitionEvaluator (TX-001 to TX-010), PriorityScheduler, T8Arbitrator, CompoundState. 86 local tests reported green; CI coverage is not yet aligned. Auditable in `docs/TRANSITION_MATRIX_G1.md`.
- **ROS2 observability (4D):** G1 observable over real ROS2 cross-container (joints, base pose, base velocity, IMU, typed foot contacts) on the T4, without the heavy RTX stack. Observation only — no control commands issued.
- **Observer to orchestrator closure (4D-3D):** real `SafetyEvent` consumed and acknowledged by the orchestrator; no improper escalation.
- **Healthy passive baseline (4E):** G1 stands passively from pose P2 + `z_cmd=0.720` + factory drives. Observer produces zero false positives on the healthy baseline (negative control). Healthy-to-fall transition captured in telemetry.
- **Observer with severity (4F-P1):** INFO/WARN/CRITICAL. CRITICAL fires on `abs_w<0.80` sustained 3 fresh samples, even if one foot remains in contact (residual contact is not healthy support).
- **Watchdog (4F-P2):** detects STALE / FREEZE / NANINF / TIMESTAMP / RATE on 5 topics, on the T4. FREEZE excluded on contacts. 15s startup grace.
- **Transition matrix audit artifact (4F-P3):** TX-001 to TX-010 traced to method + test + action, derived from source, not inferred.
- **Recovery integrated (4F-P4):** end-to-end pipeline with 4 simultaneous components validated: healthy is silence; fall triggers observer alarm + recovery reacts; Isaac killed triggers watchdog STALE + recovery reacts.
- **Latency t1 to t2 (4F-P5):** 0.68 to 8.2 ms on Tesla T4 (2 runs). t1 = SafetyEvent published; t2 = recovery receives.

### Not Validated (explicitly out of scope today)

- **Fault injection robustness** — Stage 4F-P6, pending.
- **Latency t0 to t1** (physical fall to SafetyEvent published) — not measured; requires Isaac/ROS2 clock sync (DT-4F-005).
- **Definitive thresholds** — all current thresholds (`abs_w=0.80`, STALE=1.0s, FREEZE N=5) are pragmatic and calibrable, not formally justified (DT-4D-016, DT-4F-001).
- **Statistical reproducibility** — latency from N=2 runs only; N>=5 with mean/stddev pending.
- **Active postural control (PD)** — not achieved by simple means; deferred (4E-P5, DT-4E-006). The robot does not hold itself against perturbation.
- **Hardware validation** — x86 / simulation only. No physical Unitree SDK integration.
- **Isaac Lab on T4** — undemonstrated, blocked (DT-4D-003).

### Deferred (not blocking for paper)

- **4E-P5** — active PD control from the P2+z0.720 baseline.
- **5A** — Isaac Lab (requires GPU >= RTX 4080).

---

## Runtime Components (`src/`)

| Component | Role | Stage |
|-----------|------|-------|
| `g1_msgs` | Custom messages: SafetyEvent, SystemState, SafetyAction, RecoveryEvent, FootContact | 3B |
| `cross_consistency_observer` | observer component — cross-domain validation, severity rule (INFO/WARN/CRITICAL) | 3B / 4F-P1 |
| `watchdog_g1` | Health monitor — STALE/FREEZE/NANINF/TIMESTAMP/RATE over 5 topics | 4F-P2 |
| `safety_orchestrator_g1` | Operational authority — TransitionEvaluator, PriorityScheduler, T8Arbitrator, CompoundState | 3C |
| `recovery_g1` | Recovery executor — 5 actions, subprocess isolation, retry with cooldown | 3C / 4F-P4 |
| `g1_description` | Robot description (XACRO), TF tree, Level 3 launch tests | 3B |
| `test_g1_safety_layer` | Level 4 launch integration tests | 3C |

> Note: `safety_orchestrator_g1`, `watchdog_g1`, and `recovery_g1` are real implementations, not skeletons. The watchdog was implemented from scratch in 4F-P2; recovery was already implemented (5 actions) and integrated into the live pipeline in 4F-P4.

## Authority Hierarchy

    safety_orchestrator_g1                  <- operational authority (state machine)
        |-- cross_consistency_observer      <- cross-domain validation (severity)
        |-- watchdog_g1                     <- data-flow health detection
        |-- recovery_g1                     <- recovery execution
                |-- Isaac Sim telemetry (ROS2)      <- embodiment boundary (observation only)
                        |-- [future] g1_adapter_node        <- hardware boundary (Unitree SDK, blocked)
                                |-- [future] standing policy / VLA / GR00T  <- intelligence layer

Policy layers operate **under** safety authority, never above it.

> **Semantic models:** the canonical safety/resilience/recovery model documents (`SAFETY_MODEL_G1.md`, etc.) are **pending reconstruction** from source evidence (orchestrator code, transition matrix, session reports). They are tracked as debt DT-4E-001 and are **not currently present** in the repository. No component depends on them at runtime; they are documentation artifacts to be recreated, not invented.

---

## How to Run / Audit

### Unit tests (no hardware, no Isaac)

The deterministic transition logic is testable in isolation:

```bash
docker run --rm -v $(pwd):/root/pipeline_ws pipeline-runtime:latest bash -c \
  "cd /root/pipeline_ws && source /opt/ros/humble/setup.bash && \
   source install/setup.bash && \
   python3 -m pytest src/safety_orchestrator_g1/test/test_orchestrator_transitions.py -v"
```

### Full validated pipeline (4 terminals)

The end-to-end pipeline validated in 4D/4F is launched **manually as 4 components**, in strict order (a unified launcher is future work — see Stage 4G). Exact commands live in the bootstrap protocol (see Key Documents).

    Terminal A — Isaac Sim (robot)      -> wait for "P2+z0.720 SET"
    Terminal B — cross_consistency_observer
    Terminal C — watchdog_g1
    Terminal D — recovery_g1

Mandatory order: A first -> wait for baseline set -> then B + C + D. Launching B/C/D before Isaac is ready triggers an immediate (correct) STALE.

> The launch file `system_g1.launch.py` currently in `agv_bringup` is a transitional AGV-to-G1 artifact and does **not** start this validated core. It is slated for archival (see PLAN_REPO_QUALIFICATION). Do not treat it as the canonical entrypoint.

### Continuous Integration


> The "86 tests" figure refers to local Level 4 validation, not to current CI coverage. CI alignment with the declared audit scope (ADR-007) is pending.

---

## Key Documents

| Document | Scope |
|----------|-------|
| `docs/tesis_etapas_..._v18.md` | Full stage thesis (current) — all stages, frozen decisions, debt |
| `docs/chat_bootstrap_protocol_..._v15.md` | Operational bootstrap (current) — rules, confirmed paths, anti-patterns |
| `docs/informe_etapa_4F_2026-06-16.md` | Stage 4F session report — observer severity, watchdog, transition matrix, recovery integration, latency |
| `docs/TRANSITION_MATRIX_G1.md` | TX-001 to TX-010 traced to method + test + action |
| `ARCHITECTURE_DECISIONS.md` | ADR-001 to 010 (ADR-007/008 under revision) |
| `TECHNICAL_DEBT_3C.md` | Post-3C debt register |

> Historical reports (v9, v12, 4D-3, earlier informes) are retained under `docs/archive/` for traceability.

---

## Baseline Reference

This pipeline migrates from an earlier AGV project (`agv-pipeline-lab`). Components carrying the `agv_` prefix, `rplidar_ros`, `perception_node`, and `safety_policy_node` are **legacy/transitional** and slated for quarantine under `legacy/` — retained for traceability, not part of the active G1 safety core.

---

## Team

| Role | Responsible |
|------|-------------|
| Technical PM | ChatGPT |
| Implementer / Auditor | Claude |
| Operator | Jorge Padilla |

---

*G1 ROS2 Pipeline — github.com/jorgerpg1213-mitech/g1-ros2-pipeline*
*Status 2026-06-16: 3C OK · 4A-4D OK · 4E OK · 4F in progress (P1-P5 done, P6 pending) · 5A blocked*
*Audit-readiness mapped to MIT/NASA/Boston Dynamics rigor — not certified compliance.*
