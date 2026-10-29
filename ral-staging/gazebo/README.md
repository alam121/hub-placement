# Gazebo/Nav2 validation (ROS 2 Jazzy, Gazebo Harmonic 8.10, Nav2)

make_worlds.py   paper maps -> worlds/*.sdf (Gazebo) + maps/*.pgm/.yaml (Nav2, 0.25 m) + maps/meta.json
robot/           Jackal-scale diff-drive model (DiffDrive + ground-truth OdometryPublisher)
nav2_params.yaml NavFn A* planner, Regulated Pure Pursuit 1.5 m/s, static-map costmaps, recoveries
bridge.yaml      ros_gz_bridge: /clock, /odom, /tf (ground truth), /cmd_vel
run_map.sh       starts gz + bridge + Nav2 for one world, runs missions.py, tears down
missions.py      40-leg site/zone tour, logs sim-time travel per leg -> results/<map>.json
analyze_gz.py    Nav2 vs model fit, reachability agreement, re-evaluation on 15 layouts -> gz_summary.json
figs_gz.py       paper Fig. 6

Environment used here (headless, cloud): micromamba env with
  conda-forge + robostack-jazzy: ros-jazzy-ros-base ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-ros-gz
On Ubuntu 24.04 with apt ROS 2 Jazzy, `sudo apt install ros-jazzy-navigation2 ros-jazzy-ros-gz` is equivalent.

## Recording the RA-L video on your machine (needs a display/GPU)
1. Edit paths in run_map.sh / make_worlds.py (/home/claude/...) to your checkout.
2. In run_map.sh replace `gz sim -s -r` with `gz sim -r` (opens the GUI), then run:
     ./run_map.sh warehouse results/demo.json 10
3. Optionally add RViz: `ros2 run rviz2 rviz2` with Fixed Frame = map, add Map, Path (/plan), RobotModel/TF.
4. Record the screen (e.g. OBS / SimpleScreenRecorder). For the multi-robot story, overlay the
   staging configuration drawn by the policy per shift (sim.py) on the same world.

## Supplementary video (video/)
episodes.py   picks episodes from the representative warehouse layout 1 and writes Gazebo worlds with camera
drive.py      path-following controller (gz-transport) for the episode robots
record.sh     headless software rendering (Mesa llvmpipe via EGL) -> frames_ep*/
proj.py       world->image projection for overlays
compose.py    assembles RAL_video_leakage_aware_staging.mp4 (1280x720, 30 fps)
Needs: apt install libegl-mesa0 libgl1-mesa-dri libgbm1 (for headless rendering).
