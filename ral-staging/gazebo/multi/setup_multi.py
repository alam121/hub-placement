"""R7 setup: Gazebo world with 3 robots (namespaced r0..r2) for a map layout, per-robot Nav2 params and
bridge config, and the shift list (paired streams, same construction as sim.Sim.run without relocation).
Usage: setup_multi.py <map> <layout> <n_shifts>"""
import sys, json, itertools, zlib
import numpy as np
import yaml
sys.path.insert(0, "/home/claude/ral"); sys.path.insert(0, "/home/claude/gz")
from sim import scenario, Sim
from leakage import solve_q
from make_worlds import boxes, nav2_map

KIND, LAY, NSH = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
VERIFIED = len(sys.argv) > 4 and sys.argv[4] == "verified"
Q = 0.25
D = f"/home/claude/gz/multi/{KIND}{LAY}" + ("_verified" if VERIFIED else "")
import os; os.makedirs(D, exist_ok=True)
sc = scenario(KIND, 700 + LAY, density=0.20, priority="skewed", c=1)
if VERIFIED:
    # Nav2-verified reachability: keep only arcs with slack >= p95 Nav2 timing error (3.82 s) and drop arcs
    # that Nav2 failed to complete in the concurrent run; zones left without an arc are simply unreachable.
    P95 = json.load(open("/home/claude/gz/near_deadline.json"))["summary"]["abs_err_s_p95"]
    FAILED = {("office", 0): [(7, 8)]}.get((KIND, LAY), [])
    slack = sc["dl_mat"] - (sc["Dsz"] / sc["speed"] + sc["service"])
    A = ((sc["A"] == 1) & (slack >= P95)).astype(np.int64)
    for (i, j) in FAILED: A[i, j] = 0
    print("verified reachability: removed", int(sc["A"].sum() - A.sum()), "of", int(sc["A"].sum()), "arcs")
    sc = dict(sc, A=A)
s = Sim(sc, 3)
H, W = sc["obst"].shape
to_xy = lambda yx: (yx[1] + 0.5, H - yx[0] - 0.5)
sites = [to_xy(p) for p in sc["sites"]]; zones = [to_xy(p) for p in sc["zones"]]

# ---- world
links = []
for k, (x0, x1, y0, y1) in enumerate(boxes(sc["obst"])):
    cx, cy = (x0 + x1) / 2, H - (y0 + y1) / 2
    links.append(f'<link name="w{k}"><pose>{cx} {cy} 0.5 0 0 0</pose><collision name="c"><geometry><box><size>{x1-x0} {y1-y0} 1</size></box></geometry></collision></link>')
robot = open("/home/claude/gz/robot/model.sdf").read()
body = robot[robot.index("<model name=\"robot\">") + len("<model name=\"robot\">"):robot.index("</model>")]
models = []
for k in range(3):
    b = body.replace("<topic>/cmd_vel</topic>", f"<topic>/r{k}/cmd_vel</topic>") \
            .replace("<odom_topic>/wheel_odom</odom_topic>", f"<odom_topic>/r{k}/wheel_odom</odom_topic>") \
            .replace("<tf_topic>/wheel_tf</tf_topic>", f"<tf_topic>/r{k}/wheel_tf</tf_topic>") \
            .replace("<odom_topic>/odom</odom_topic>", f"<odom_topic>/r{k}/odom</odom_topic>") \
            .replace("<tf_topic>/tf_gt</tf_topic>", f"<tf_topic>/r{k}/tf_gt</tf_topic>")
    x, y = sites[k]
    models.append(f'<model name="robot{k}"><pose>{x} {y} 0 0 0 0</pose>{b}</model>')
open(f"{D}/world.sdf", "w").write(f"""<?xml version="1.0"?><sdf version="1.9"><world name="multi">
<physics name="p" type="ignored"><max_step_size>0.004</max_step_size><real_time_factor>1.0</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher"/>
<model name="ground"><static>true</static><link name="l"><collision name="c"><geometry><plane><normal>0 0 1</normal><size>400 400</size></plane></geometry>
<surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision></link></model>
<model name="walls"><static>true</static>{''.join(links)}</model>
{''.join(models)}
</world></sdf>""")

# ---- nav2 map + per-robot params (fully qualified node names, relative topics)
cwd = os.getcwd(); os.chdir(D); os.makedirs("maps", exist_ok=True); nav2_map("map", sc["obst"]); os.chdir(cwd)
base = yaml.safe_load(open("/home/claude/gz/nav2_params.yaml"))
base["bt_navigator"]["ros__parameters"]["odom_topic"] = "odom"
base["map_server"]["ros__parameters"]["yaml_filename"] = f"{D}/maps/map.yaml"
for k in range(3):
    out = {}
    for node, val in base.items():
        if node in ("local_costmap", "global_costmap"):
            out[f"/r{k}/{node}/{node}"] = val[node]
        else:
            out[f"/r{k}/{node}"] = val
    yaml.safe_dump(out, open(f"{D}/nav2_r{k}.yaml", "w"))
bridge = [dict(ros_topic_name="/clock", gz_topic_name="/clock", ros_type_name="rosgraph_msgs/msg/Clock", gz_type_name="gz.msgs.Clock", direction="GZ_TO_ROS")]
for k in range(3):
    bridge += [dict(ros_topic_name=f"/r{k}/odom", gz_topic_name=f"/r{k}/odom", ros_type_name="nav_msgs/msg/Odometry", gz_type_name="gz.msgs.Odometry", direction="GZ_TO_ROS"),
               dict(ros_topic_name=f"/r{k}/tf", gz_topic_name=f"/r{k}/tf_gt", ros_type_name="tf2_msgs/msg/TFMessage", gz_type_name="gz.msgs.Pose_V", direction="GZ_TO_ROS"),
               dict(ros_topic_name=f"/r{k}/cmd_vel", gz_topic_name=f"/r{k}/cmd_vel", ros_type_name="geometry_msgs/msg/Twist", gz_type_name="gz.msgs.Twist", direction="ROS_TO_GZ")]
yaml.safe_dump(bridge, open(f"{D}/bridge.yaml", "w"))

# ---- shifts: same random-stream construction as Sim.run (no relocation: robots start docked)
U, mvec = s.U, s.mvec
fixed = np.zeros(len(U)); fixed[int(np.argmax(mvec))] = 1
xq = solve_q(U, Q, mvec)["x"]
shifts = []
for name, x, nsh in (("fixed", fixed, 3), ("leakage_aware", xq, NSH)):
    g = np.random.default_rng(zlib.crc32(f"{KIND}|{LAY}|gazebo|{Q}".encode()))
    cdf = np.cumsum(x); blind = int(np.argmin(U.T @ x))
    Up, Uo, SUC = g.random(nsh), g.random(nsh), g.random((nsh, 3))
    for t in range(nsh):
        di = int(min(np.searchsorted(cdf, Up[t] * cdf[-1], side="right"), len(x) - 1))
        sees = bool(Uo[t] < Q)
        ai = int(s.obs_attack[di]) if sees else blind
        S, route = s.get_plan(di, ai)
        docks = [int(i) for i in s.P[di]]
        shifts.append(dict(policy=name, shift=t, docks=docks, dock_xy=[sites[i] for i in docks], observed=sees,
                           attack=[int(a) for a in s.W[ai]], served=[int(j) for j in S],
                           route=[dict(robot=docks.index(i), dock=i, zone=j, zone_xy=zones[j],
                                       model_time=float(sc["Dsz"][i, j] / sc["speed"]), deadline=float(sc["dl_mat"][i, j]) - sc["service"])
                                  for (i, j) in route],
                           success_u=SUC[t].tolist(), model_value=float(U[di, ai])))
json.dump(dict(map=KIND, layout=LAY, q=Q, v=sc["v"].tolist(), p=sc["p"], sites=sites, zones=zones,
               P=float(mvec.max()), Vx=float((1 - Q) * (U.T @ xq).min() + Q * xq @ mvec), shifts=shifts),
          open(f"{D}/shifts.json", "w"), indent=1)
print(KIND, LAY, "shifts", len(shifts), "movers per shift", [len(sh["route"]) for sh in shifts])
