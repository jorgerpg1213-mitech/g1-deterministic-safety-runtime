# Legacy Components

This directory contains historical AGV, SLAM, LiDAR, perception, and backup code retained for traceability.

## Purpose

`legacy/` preserves earlier project components that are no longer part of the active G1 safety-runtime core.

These files are kept to maintain audit history and engineering context. They are not active runtime packages.

## Active Build Exclusion

This directory contains `COLCON_IGNORE`, so its packages are excluded from active colcon builds.

## Contents

- `agv_bringup/`: historical AGV/Nav2/SLAM launch and configuration material.
- `agv_msgs/`: historical AGV message definitions.
- `rplidar_ros/`: historical RPLidar integration package.
- `perception_node/`: future/stub perception package, not active in current G1 core.
- `safety_policy_node/`: historical safety policy scaffold.
- `backups/`: archived code backups removed from active source paths.

## Current Active Core

The active G1 safety-runtime packages live under `src/` and are limited to the current CI-selected core packages.
