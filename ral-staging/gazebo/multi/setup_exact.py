"""R7 setup: Gazebo world with 3 robots (namespaced r0..r2) for a map layout, per-robot Nav2 params and
bridge config, and the shift list (paired streams, same construction as sim.Sim.run without relocation).
Exact-expectation variant: every (placement, attack) pair the policy can produce, with its probability.
Usage: setup_exact.py <map> <layout> <model|verified> <rtf>"""
import sys, json, itertools, zlib, math
import numpy as np
import yaml
class NoAlias(yaml.SafeDumper):
    def ignore_aliases(self, data): return True
sys.path.insert(0, "/home/claude/ral"); sys.path.insert(0, "/home/claude/gz")
from sim import scenario, Sim
from leakage import solve_q
from make_worlds import boxes, nav2_map

KIND, LAY, MODE, RTF = sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4])
VERIFIED = MODE in ("verified", "verified2")
Q = 0.25
D = f"/home/claude/gz/multi/exact/{MODE}/{KIND}{LAY}"
import os; os.makedirs(D, exist_ok=True)
sc = scenario(KIND, 700 + LAY, density=0.20, priority="skewed", c=1)
if VERIFIED:
    # Nav2-verified reachability: keep only arcs with slack >= p95 Nav2 timing error (3.82 s) and drop arcs
    # that Nav2 failed to complete in the concurrent run; zones left without an arc are simply unreachable.
    P95 = json.load(open("/home/claude/gz/near_deadline.json"))["summary"]["abs_err_s_p95"]
    # arcs Nav2 failed to complete on time in the model-reachability concurrent run (round 1)
    FAILED = [tuple(a) for a in json.load(open("/home/claude/gz/multi/exact/failed_arcs.json")).get(f"{KIND}{LAY}", [])]
    slack = sc["dl_mat"] - (sc["Dsz"] / sc["speed"] + sc["service"])
    A = ((sc["A"] == 1) & (slack >= P95)).astype(np.int64)
    for (i, j) in FAILED: A[i, j] = 0
    print("verified reachability: removed", int(sc["A"].sum() - A.sum()), "of", int(sc["A"].sum()), "arcs")
    sc = dict(sc, A=A)
    if MODE == "verified2":
        # zones receiving >= 2 robots: require slack >= the shared-zone delay bound measured in the model round
        SH = json.load(open("/home/claude/gz/multi/exact/shared_margin.json"))["p95_shared_zone_delay_s"]
        sc["A2"] = ((A == 1) & (slack >= SH)).astype(np.int64)
        print("shared-zone margin %.2f s: A2 keeps" % SH, int(sc["A2"].sum()), "of", int(A.sum()), "arcs")
s = Sim(sc, 3)
H, W = sc["obst"].shape
RESP = sc.get("res", 1.0)          # planning-grid cell size (m): 1 for synthetic maps, 0.1 for the real floor plan
to_xy = lambda yx: ((yx[1] + 0.5) * RESP, (H - yx[0] - 0.5) * RESP)
sites = [to_xy(p) for p in sc["sites"]]; zones = [to_xy(p) for p in sc["zones"]]

# ---- world
links = []
FINE = KIND == "willow"          # real floor plan: Gazebo world and Nav2 map from the 0.2 m building geometry
if FINE:
    sys.path.insert(0, "/home/claude/realmaps"); from willow_fine import fine_grid, snap, RES
    occ_f = fine_grid(); Hf = occ_f.shape[0]
    assert occ_f.shape == sc["obst"].shape and RES == RESP
    geo, gres, gH = occ_f, RES, Hf
else:
    geo, gres, gH = sc["obst"], 1.0, H
for k, (x0, x1, y0, y1) in enumerate(boxes(geo)):
    cx, cy = gres * (x0 + x1) / 2, gres * (gH - (y0 + y1) / 2)
    if FINE:   # thousands of wall boxes: one static link with many collision shapes (one physics body)
        links.append(f'<collision name="c{k}"><pose>{cx} {cy} 0.5 0 0 0</pose><geometry><box><size>{gres*(x1-x0)} {gres*(y1-y0)} 1</size></box></geometry></collision>')
    else:
        links.append(f'<link name="w{k}"><pose>{cx} {cy} 0.5 0 0 0</pose><collision name="c"><geometry><box><size>{gres*(x1-x0)} {gres*(y1-y0)} 1</size></box></geometry></collision></link>')
if FINE:
    # thousands of static shapes stall the physics engine's first step, so walls are not physical here; Nav2 plans on
    # the map as usual, and the runner records each robot's clearance from the real walls to detect any contact
    links = []
    from scipy.ndimage import distance_transform_edt
    np.save(f"{D}/clearance.npy", distance_transform_edt(~occ_f) * RES)
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
<physics name="p" type="ignored"><max_step_size>0.004</max_step_size><real_time_factor>{RTF}</real_time_factor></physics>
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
cwd = os.getcwd(); os.chdir(D); os.makedirs("maps", exist_ok=True)
if FINE:
    img = np.where(occ_f, 0, 254).astype(np.uint8); h, w = img.shape
    with open("maps/map.pgm", "wb") as f:
        f.write(f"P5\n{w} {h}\n255\n".encode()); f.write(img.tobytes())
    open("maps/map.yaml", "w").write(f"image: map.pgm\nmode: trinary\nresolution: {RES}\norigin: [0.0, 0.0, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n")
else:
    nav2_map("map", sc["obst"])
os.chdir(cwd)
base = yaml.safe_load(open("/home/claude/gz/nav2_params.yaml"))
base["bt_navigator"]["ros__parameters"]["odom_topic"] = "odom"
base["map_server"]["ros__parameters"]["yaml_filename"] = f"{D}/maps/map.yaml"
OBST = dict(plugin="nav2_costmap_2d::ObstacleLayer", enabled=True, observation_sources="fleet",
            fleet=dict(topic="fleet_scan", data_type="LaserScan", marking=True, clearing=True, inf_is_valid=True,
                       raytrace_max_range=6.0, obstacle_max_range=5.5, max_obstacle_height=2.0, min_obstacle_height=-1.0))
for cm in ("local_costmap", "global_costmap"):
    pr = base[cm][cm]["ros__parameters"]
    if KIND == "willow":     # real floor plan: native map resolution and the robot's true 0.5 x 0.4 m footprint
        pr["resolution"] = 0.1
        pr.pop("robot_radius", None); pr["footprint"] = "[[0.25, 0.2], [0.25, -0.2], [-0.25, -0.2], [-0.25, 0.2]]"
        pr["inflation_layer"] = dict(pr["inflation_layer"], inflation_radius=0.55, cost_scaling_factor=5.0)
    pr["plugins"] = ["static_layer", "obstacle_layer", "inflation_layer"]; pr["obstacle_layer"] = OBST
for k in range(3):
    out = {}
    for node, val in base.items():
        if node in ("local_costmap", "global_costmap"):
            out[f"/r{k}/{node}/{node}"] = val[node]
        else:
            out[f"/r{k}/{node}"] = val
    open(f"{D}/nav2_r{k}.yaml", "w").write(yaml.dump(out, Dumper=NoAlias).replace("topic: fleet_scan", f"topic: /r{k}/fleet_scan"))
bridge = [dict(ros_topic_name="/clock", gz_topic_name="/clock", ros_type_name="rosgraph_msgs/msg/Clock", gz_type_name="gz.msgs.Clock", direction="GZ_TO_ROS")]
for k in range(3):
    bridge += [dict(ros_topic_name=f"/r{k}/odom", gz_topic_name=f"/r{k}/odom", ros_type_name="nav_msgs/msg/Odometry", gz_type_name="gz.msgs.Odometry", direction="GZ_TO_ROS"),
               dict(ros_topic_name=f"/r{k}/tf", gz_topic_name=f"/r{k}/tf_gt", ros_type_name="tf2_msgs/msg/TFMessage", gz_type_name="gz.msgs.Pose_V", direction="GZ_TO_ROS"),
               dict(ros_topic_name=f"/r{k}/cmd_vel", gz_topic_name=f"/r{k}/cmd_vel", ros_type_name="geometry_msgs/msg/Twist", gz_type_name="gz.msgs.Twist", direction="ROS_TO_GZ")]
yaml.safe_dump(bridge, open(f"{D}/bridge.yaml", "w"))

# ---- exact dispatch set: leakage-aware policy (q = Q) and best fixed placement
U, mvec = s.U, s.mvec
fd = int(np.argmax(mvec))
xq = solve_q(U, Q, mvec)["x"]; xq[xq < 1e-9] = 0; xq /= xq.sum()
blind = int(np.argmin(U.T @ xq))
probs = {}
for d in np.where(xq > 0)[0]:
    for a, w in ((blind, (1 - Q) * xq[d]), (int(s.obs_attack[d]), Q * xq[d])):
        probs.setdefault((int(d), a), [0.0, 0.0])[0] += float(w)
probs.setdefault((fd, int(np.argmin(U[fd]))), [0.0, 0.0])[1] += 1.0
free = sc["obst"] == 0
def service_points(j, n):
    """zone centre first, then nearby free cells at least 1.4 m from chosen points: cells with all 8 neighbours
    free within 3 m first; if a narrow corridor leaves too few, cells with their 4 direct neighbours free within 5 m"""
    zr, zc = sc["zones"][j]; pts = [zones[j]]
    def ok8(r, c): return free[r - 1:r + 2, c - 1:c + 2].all()
    def ok4(r, c): return free[r, c] and free[r - 1, c] and free[r + 1, c] and free[r, c - 1] and free[r, c + 1]
    for rad_m, ok in ((3, ok8), (5, ok4)):
        rad = int(round(rad_m / RESP))
        cand = sorted(((r, c) for r in range(max(1, zr - rad), min(H - 1, zr + rad + 1)) for c in range(max(1, zc - rad), min(W - 1, zc + rad + 1))
                       if ok(r, c)), key=lambda rc: math.hypot(rc[0] - zr, rc[1] - zc))
        for rc in cand:
            if len(pts) == n: return pts
            p = to_xy(rc)
            if all(math.dist(p, q) >= 1.4 for q in pts): pts.append(p)
    assert len(pts) == n, (j, n, len(pts))
    return pts
pairs = []
for (d, a), (pl, pf) in probs.items():
    S, route = s.get_plan(d, a)
    docks = [int(i) for i in s.P[d]]
    cnt = {}
    for (i, j) in route: cnt[j] = cnt.get(j, 0) + 1
    sp = {j: service_points(j, n) for j, n in cnt.items()}; used = {}
    goal = []
    for (i, j) in route:
        goal.append(sp[j][used.get(j, 0)]); used[j] = used.get(j, 0) + 1
    pairs.append(dict(d=d, a=a, prob_la=pl, prob_fixed=pf, docks=docks, dock_xy=[sites[i] for i in docks],
                      attack=[int(x) for x in s.W[a]], served=[int(j) for j in S], model_value=float(U[d, a]),
                      route=[dict(robot=docks.index(i), dock=int(i), zone=int(j), zone_xy=goal[ri], offset_m=float(math.dist(goal[ri], zones[j])),
                                  model_time=float(sc["Dsz"][i, j] / sc["speed"]), deadline=float(sc["dl_mat"][i, j]) - sc["service"])
                             for ri, (i, j) in enumerate(route)]))
json.dump(dict(map=KIND, layout=LAY, mode=MODE, q=Q, rtf=RTF, v=sc["v"].tolist(), p=sc["p"], P=float(mvec.max()),
               Vx=float((1 - Q) * (U.T @ xq).min() + Q * xq @ mvec), pairs=pairs), open(f"{D}/pairs.json", "w"), indent=1)
print(KIND, LAY, MODE, "pairs", len(pairs), "movers", [len(p["route"]) for p in pairs])
