#!/bin/bash
# run_multi.sh <dir>  -- gz + bridges + 3 namespaced Nav2 stacks (own TF trees), then the concurrent shift runner
D=$1
cd /home/claude/gz
source env.sh
LOG=$D/logs; mkdir -p $LOG
gz sim -s -r $D/world.sdf > $LOG/gz.log 2>&1 &
sleep 5
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$D/bridge.yaml > $LOG/bridge.log 2>&1 &
for k in ${ROBOTS:-0 1 2}; do
  NS=/r$k; P=$D/nav2_r$k.yaml
  R="-r /tf:=$NS/tf -r /tf_static:=$NS/tf_static"
  ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id odom --ros-args -r __ns:=$NS $R -p use_sim_time:=true > $LOG/tf$k.log 2>&1 &
  for N in "nav2_map_server map_server" "nav2_planner planner_server" "nav2_controller controller_server" "nav2_behaviors behavior_server" "nav2_bt_navigator bt_navigator"; do
    set -- $N
    ros2 run $1 $2 --ros-args -r __ns:=$NS $R --params-file $P > $LOG/${2}_$k.log 2>&1 &
  done
  ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args -r __ns:=$NS -r __node:=lifecycle_manager_navigation $R --params-file $P > $LOG/lifecycle_$k.log 2>&1 &
done
sleep 20
python3 /home/claude/gz/multi/multi_runner.py $D 2>&1 | tee $LOG/runner.log
pkill -f "gz sim"; pkill -f parameter_bridge; pkill -f static_transform_publisher
pkill -f map_server; pkill -f planner_server; pkill -f controller_server; pkill -f behavior_server
pkill -f bt_navigator; pkill -f lifecycle_manager; pkill -f "ros2 run"
sleep 3
