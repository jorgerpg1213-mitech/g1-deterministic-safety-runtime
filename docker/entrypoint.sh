#!/bin/bash
set -e

source /opt/ros/humble/setup.bash

if [ -f /root/pipeline_ws/install/setup.bash ]; then
    source /root/pipeline_ws/install/setup.bash
fi

exec "$@"
