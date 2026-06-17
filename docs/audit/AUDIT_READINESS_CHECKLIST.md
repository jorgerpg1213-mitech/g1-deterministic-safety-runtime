# Audit Readiness Checklist — G1 ROS2 Pipeline

## Repository State

- [x] Main README updated to current 4F state.
- [x] Current documentation isolated under `docs/current/`.
- [x] Audit artifacts isolated under `docs/audit/`.
- [x] Historical documents archived under `docs/archive/`.
- [x] Experimental evidence documented under `evidence/`.
- [x] Isaac Sim runtime artifacts documented under `sim_runtime/`.
- [x] Legacy AGV/SLAM components quarantined under `legacy/`.
- [x] Local scratch outputs ignored via `.gitignore`.

## Active Core Scope

The active G1 safety-runtime core is limited to:

- `g1_msgs`
- `cross_consistency_observer`
- `watchdog_g1`
- `safety_orchestrator_g1`
- `recovery_g1`
- `test_g1_safety_layer`

## CI Scope

- [x] `ci-build.yml` builds and tests the G1 core package set.
- [x] `ci-audit.yml` is aligned with the G1 core audit scope.
- [x] Legacy AGV/Nav2/SLAM components are excluded from active builds.

## Validated

- [x] Core safety messages.
- [x] Observer/watchdog/orchestrator/recovery package structure.
- [x] 4E healthy baseline and fall-transition evidence.
- [x] 4F observer, watchdog, transition matrix, recovery, and partial latency evidence.
- [x] Isaac Sim experimental telemetry path documented.

## Not Claimed

- [ ] Medical certification.
- [ ] NASA certification.
- [ ] Boston Dynamics certification.
- [ ] Hardware G1 deployment.
- [ ] Full end-to-end latency from Isaac event to recovery completion.
- [ ] Isaac Lab locomotion training.

## Deferred

- [ ] 4F-P6 fault injection matrix.
- [ ] 4G pipeline hardening and repeated-run validation.
- [ ] 4H recovery intelligence mapping.
- [ ] 4I formal safety/resilience/recovery models.
- [ ] 5A Isaac Lab, blocked by RTX/GPU constraints.

## Audit Position

This repository is organized for preliminary audit-readiness review. It is not presented as certified, complete, production-safe, or compliant with any external standard. The current repository state emphasizes traceability, reproducibility, explicit scope boundaries, and clear separation between active code, historical evidence, legacy material, and deferred work.
