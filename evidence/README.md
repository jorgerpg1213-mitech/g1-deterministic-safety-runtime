# Evidence Directory

This directory contains tracked experimental evidence generated during the G1 ROS2 Pipeline qualification phases.

## Purpose

The `evidence/` tree is preserved to support auditability, reproducibility, and traceability of engineering decisions. These files are not runtime code. They are logs and artifacts used to justify phase conclusions.

## Scope

### `4C/`
Evidence from initial Isaac Sim / G1 physical characterization.

Main purpose:
- Validate that the G1 asset could be loaded and stepped.
- Characterize early physics behavior.
- Record instability, contact, damping, and pose-hold experiments.
- Preserve negative and partial results.

### `4D-2/`
Evidence from Isaac Sim 4.5 migration and minimal runtime bring-up.

Main purpose:
- Validate headless Isaac Sim execution.
- Inspect extension loading and SimulationApp behavior.
- Capture deterministic stepping evidence.
- Record why RTX/Isaac Lab was not used as the critical path.

### `4D-3/`
Evidence from ROS2 observability bridge work.

Main purpose:
- Validate publication/subscription behavior.
- Confirm G1 state, joint, pose, velocity, IMU, and contact signal extraction.
- Preserve bridge and subscriber traces used to connect simulation telemetry into the safety runtime.

## Audit Notes

- These artifacts are historical evidence, not active source code.
- They are intentionally retained because several project decisions depend on failed, partial, or negative experiments.
- Active source code lives under `src/`.
- Isaac Sim experimental runtime scaffolding lives under `sim_runtime/`.
- Legacy AGV/SLAM material lives under `legacy/` and is excluded from active colcon builds via `COLCON_IGNORE`.

## Current Relevance

For the current 4F safety-runtime qualification state, the most relevant evidence is:

- `4D-3/` for ROS2 observability and signal publication/subscription.
- `docs/experiments/4E_P4_2026-06-15/` for healthy baseline and fall-transition evidence.
- `docs/current/informe_etapa_4F_2026-06-16.md` for current runtime-stage conclusions.

