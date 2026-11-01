#!/bin/bash
# Kill simulator, bridge, Nav2 and helper processes. Patterns are anchored at the start of the full command line,
# so they never match a calling shell (whose command line starts with /bin/bash or bash).
pkill -f "^/home/claude/gz/mamba/envs/ros/lib/" 2>/dev/null
pkill -f "^gz sim" 2>/dev/null
pkill -f "^ruby .*gz sim" 2>/dev/null
pkill -f "^python3 /home/claude/gz/multi/(fleet_scan|exact_runner|multi_runner).py" 2>/dev/null
pkill -f "^/home/claude/gz/mamba/envs/ros/bin/python[0-9.]* /home/claude/gz/mamba/envs/ros/bin/ros2 run" 2>/dev/null
sleep 2
pkill -9 -f "^/home/claude/gz/mamba/envs/ros/lib/" 2>/dev/null; pkill -9 -f "^gz sim" 2>/dev/null
rm -rf /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_* 2>/dev/null
