Multimedia material for the RA-L submission
"When Should Robots Hide Where They Wait? Leakage-Aware Randomized Staging
for Capacity-Constrained Multi-Robot Response" (anonymized for review)

CONTENTS
  video.mp4   Video (100 s, 1280x720, H.264, no audio). Plays in any
              standard player (VLC, QuickTime, Windows Media Player, browser).
  code/       Source code and raw result data (Python 3.13, NumPy, SciPy,
              numba; Gazebo Harmonic + ROS 2 Jazzy Nav2 for the robot runs).
              The same material is mirrored at
              https://anonymous.4open.science/r/leakage-aware-staging-ral

USING THE CODE
  1. cd code && python3 localize.py      (rewrites development paths)
  2. pip install -r requirements.txt
  3. Exact games and figures:   core/run_grid.py, core/analyze.py
     Closed-loop simulation:    core/sim_experiment.py
     Matrix-free solver:        core/scale_solver.py, core/run_scale.py
     Solver ablation:           core/ablation.py
     Real-building map study:   core/willow_study.py (map in realmaps/)
     Concurrent Nav2 runs:      gazebo/multi/setup_exact.py, run_batch.sh,
                                analyze_exact.py (needs Gazebo + Nav2)
  Raw results are stored as .json/.jsonl next to the scripts that produce
  them; code/README.md lists every script and output file.

The paper is self-contained; this material is not needed to read it.
