# Active G1 ROS2 Safety Runtime Core

This directory contains the active ROS2 packages for the G1 safety-runtime pipeline.

## Active Core Packages

- `g1_msgs`: custom message definitions for safety, recovery, detections, system state, and foot contacts.
- `cross_consistency_observer`: observes cross-signal consistency and emits safety events.
- `watchdog_g1`: monitors signal health, staleness, freezes, invalid values, and timing anomalies.
- `safety_orchestrator_g1`: evaluates safety events and manages system-level safety transitions.
- `recovery_g1`: consumes safety actions and emits recovery events.
- `test_g1_safety_layer`: smoke/integration tests for the current safety layer.

## Support / Scaffold Package

- `g1_description`: retained as a G1 description scaffold. It is not part of the current CI-selected safety core.

## Excluded Material

Historical AGV, SLAM, LiDAR, perception, and backup material has been moved to `legacy/` and excluded from active colcon builds via `COLCON_IGNORE`.

## Audit Notes

The CI workflows define the current active build/test scope. This directory should be interpreted together with:

- `.github/workflows/ci-build.yml`
- `.github/workflows/ci-audit.yml`
- `AUDIT_READINESS_CHECKLIST.md`
