# Simulation Runtime Artifacts

This directory contains Isaac Sim experimental runtime scaffolding used during G1 Pipeline phases 4D-2 and 4D-3.

## Purpose

`sim_runtime/` preserves the minimal Isaac Sim extensions, `.kit` files, DDS configuration files, and subscriber probes used to validate simulation-to-ROS2 observability.

These files are retained for reproducibility and audit traceability. They are not the active ROS2 safety-runtime core.

## Scope

### `4D-2/`
Isaac Sim 4.5 minimal runtime bring-up and deterministic stepping experiments.

### `4D-3A/`
ROS2/rclpy probing inside the Isaac Sim extension environment.

### `4D-3B1/` to `4D-3B4/`
Incremental bridge experiments for publishing and validating G1 telemetry:

- joint states
- base pose
- base velocity
- IMU/contact sensor access
- live publisher/subscriber traces

### `common/`
Shared DDS configuration used by the simulation bridge experiments.

## Audit Notes

- Active ROS2 safety-runtime packages live under `src/`.
- Experimental logs live under `evidence/`.
- Current project conclusions are documented under `docs/current/`.
- This directory is historical and reproducibility-oriented, not a production runtime entrypoint.
