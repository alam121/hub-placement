#!/bin/bash
# Usage: run_map.sh <map> <outfile>   -- starts gz + bridge + Nav2, runs missions, tears down.
MAP=$1; OUT=$2
cd /home/claude/gz
source env.sh
LOG=logs/$MAP; mkdir -p $LOG
gz sim -s -r worlds/$MAP.sdf > $LOG/gz.log 2>&1 &
sleep 5
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=/home/claude/gz/bridge.yaml > $LOG/bridge.log 2>&1 &
ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id odom --ros-args -p use_sim_time:=true > $LOG/tf.log 2>&1 &
P=/home/claude/gz/nav2_params.yaml
ros2 run nav2_map_server map_server --ros-args --params-file $P -p yaml_filename:=/home/claude/gz/maps/$MAP.yaml > $LOG/map.log 2>&1 &
ros2 run nav2_planner planner_server --ros-args --params-file $P > $LOG/planner.log 2>&1 &
ros2 run nav2_controller controller_server --ros-args --params-file $P > $LOG/controller.log 2>&1 &
ros2 run nav2_behaviors behavior_server --ros-args --params-file $P > $LOG/behavior.log 2>&1 &
ros2 run nav2_bt_navigator bt_navigator --ros-args --params-file $P > $LOG/bt.log 2>&1 &
ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args -r __node:=lifecycle_manager_navigation --params-file $P > $LOG/lifecycle.log 2>&1 &
sleep 12
python3 /home/claude/gz/missions.py $MAP $OUT ${3:-0} 2>&1 | tee $LOG/missions.log
pkill -f "gz sim"; pkill -f parameter_bridge; pkill -f static_transform_publisher
pkill -f map_server; pkill -f planner_server; pkill -f controller_server; pkill -f behavior_server
pkill -f bt_navigator; pkill -f lifecycle_manager; pkill -f "ros2 run"
sleep 3
