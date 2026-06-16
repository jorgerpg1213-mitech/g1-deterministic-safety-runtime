# Docker Environment

This directory contains Docker definitions used to build and validate the G1 ROS2 Pipeline in reproducible environments.

## Files

- `Dockerfile.base`: base ROS2/runtime dependencies.
- `Dockerfile.runtime`: CI/runtime image used for core package build and smoke tests.
- `Dockerfile.dev`: development-oriented image.
- `Dockerfile.sim`: simulation-oriented image scaffold.
- `entrypoint.sh`: container entrypoint support script.

## Audit Notes

The current CI build path uses:

- `docker/Dockerfile.base`
- `docker/Dockerfile.runtime`

The active validation scope is defined in:

- `.github/workflows/ci-build.yml`
- `.github/workflows/ci-audit.yml`

Docker images are not committed to the repository. They are built by CI or by a reviewer when needed.
