"""Pick video episodes from the paper's warehouse layout 0 (sparse, skewed, m=3, c=1) and write one
Gazebo world per episode: coloured shelves, staging pads, zone discs, alarm beacons, 3 robots at the
episode's docks, an overview camera. Also writes routes (grid shortest paths) for the controller."""
import sys, json, itertools
import numpy as np
sys.path.insert(0, "/home/claude/ral"); sys.path.insert(0, "/home/claude/gz")
from sim import scenario, Sim, dijkstra
from leakage import solve_q
from make_worlds import boxes

Q = 0.25
KIND, LAYOUT = "warehouse", 1
sc = scenario(KIND, 700 + LAYOUT, density=0.20, priority="skewed", c=1)
s = Sim(sc, 3)
U, mvec = s.U, s.mvec
H, W = sc["obst"].shape
to_xy = lambda yx: (yx[1] + 0.5, H - yx[0] - 0.5)
P = float(mvec.max()); d_fix = int(np.argmax(mvec))
x = solve_q(U, Q)["x"]
blind = int(np.argmin(U.T @ x))
Vx = (1 - Q) * float((U.T @ x).min()) + Q * float(x @ mvec)
supp = [int(d) for d in np.argsort(-x) if x[d] > 1e-6]
rand_ds = [d for d in supp if d != d_fix][:2]


def path(src, dst):
    dist = dijkstra(sc["obst"], dst)
    y, xx = src; pts = [(y, xx)]
    while (y, xx) != tuple(dst):
        best = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == dx == 0: continue
                yy, x2 = y + dy, xx + dx
                if sc["obst"][yy, x2]: continue
                if dy and dx and (sc["obst"][y + dy, xx] or sc["obst"][y, xx + dx]): continue
                c = dist[yy, x2] + (np.sqrt(2) if dy and dx else 1)
                if best is None or c < best[0]: best = (c, yy, x2)
        y, xx = best[1], best[2]; pts.append((y, xx))
    return [to_xy(p) for p in pts]


episodes = []
specs = [("fixed", d_fix, int(s.obs_attack[d_fix]), "Fixed staging: the attacker has seen where the robots wait"),
         ("random", rand_ds[0], blind, "Randomized staging (leakage-aware, q = 0.25): the attacker only knows the policy"),
         ("random", rand_ds[1], blind, "Next shift: a different configuration is drawn from the same policy")]
for k, (kind, d, a, caption) in enumerate(specs):
    pl = [int(i) for i in s.P[d]]; w = [int(v) for v in s.W[a]]
    S, route = s.get_plan(d, a)
    robots = [dict(dock=i, xy=to_xy(sc["sites"][i])) for i in pl]
    for r in robots:
        tgt = [j for (i, j) in route if i == r["dock"]]
        r["zone"] = tgt[0] if tgt else None
        r["path"] = path(sc["sites"][r["dock"]], sc["zones"][r["zone"]]) if tgt else []
    ep = dict(k=k, kind=kind, d=d, attack=w, served=[int(j) for j in S], caption=caption,
              value=float(U[d, a]), robots=robots,
              loaded=[j for j in range(len(w)) if w[j] > 0])
    episodes.append(ep)

meta = dict(kind=KIND, layout=LAYOUT, P=P, Vx=Vx, q=Q, x_support=len(supp), v=sc["v"].tolist(),
            sites=[to_xy(p) for p in sc["sites"]], zones=[to_xy(p) for p in sc["zones"]], episodes=episodes,
            policy_value_fixed_vs_observer=P, gain_pct=100 * (Vx - P) / P)
json.dump(meta, open("/home/claude/gz/video/episodes.json", "w"), indent=1)

COL = ["0.95 0.72 0.05", "0.1 0.62 0.3", "0.5 0.2 0.8"]


def robot_sdf(name, xy, col, topic):
    return f"""<model name="{name}"><pose>{xy[0]} {xy[1]} 0 0 0 0</pose>
<link name="base_link"><pose>0 0 0.12 0 0 0</pose>
<inertial><mass>15</mass><inertia><ixx>0.25</ixx><iyy>0.4</iyy><izz>0.5</izz></inertia></inertial>
<collision name="c"><geometry><box><size>0.5 0.4 0.15</size></box></geometry></collision>
<visual name="body"><pose>0 0 0.4 0 0 0</pose><geometry><box><size>2.6 2.0 0.8</size></box></geometry>
<material><ambient>{col} 1</ambient><diffuse>{col} 1</diffuse></material></visual>
<visual name="mast"><pose>0 0 2.6 0 0 0</pose><geometry><sphere><radius>1.5</radius></sphere></geometry>
<material><ambient>{col} 1</ambient><diffuse>{col} 1</diffuse><emissive>{col} 1</emissive></material></visual></link>
<link name="caster"><pose>-0.2 0 0.05 0 0 0</pose><inertial><mass>0.5</mass><inertia><ixx>0.001</ixx><iyy>0.001</iyy><izz>0.001</izz></inertia></inertial>
<collision name="c"><geometry><sphere><radius>0.05</radius></sphere></geometry><surface><friction><ode><mu>0</mu><mu2>0</mu2></ode></friction></surface></collision></link>
<joint name="cj" type="ball"><parent>base_link</parent><child>caster</child></joint>
<link name="lw"><pose>0.1 0.25 0.1 -1.5707 0 0</pose><inertial><mass>1</mass><inertia><ixx>0.003</ixx><iyy>0.003</iyy><izz>0.005</izz></inertia></inertial>
<collision name="c"><geometry><cylinder><radius>0.1</radius><length>0.05</length></cylinder></geometry></collision></link>
<link name="rw"><pose>0.1 -0.25 0.1 -1.5707 0 0</pose><inertial><mass>1</mass><inertia><ixx>0.003</ixx><iyy>0.003</iyy><izz>0.005</izz></inertia></inertial>
<collision name="c"><geometry><cylinder><radius>0.1</radius><length>0.05</length></cylinder></geometry></collision></link>
<joint name="lj" type="revolute"><parent>base_link</parent><child>lw</child><axis><xyz expressed_in="__model__">0 1 0</xyz></axis></joint>
<joint name="rj" type="revolute"><parent>base_link</parent><child>rw</child><axis><xyz expressed_in="__model__">0 1 0</xyz></axis></joint>
<plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive"><left_joint>lj</left_joint><right_joint>rj</right_joint>
<wheel_separation>0.5</wheel_separation><wheel_radius>0.1</wheel_radius><max_linear_acceleration>1.0</max_linear_acceleration>
<max_angular_acceleration>3.0</max_angular_acceleration><topic>/{topic}/cmd_vel</topic><odom_topic>/{topic}/wheel_odom</odom_topic><tf_topic>/{topic}/wtf</tf_topic></plugin>
<plugin filename="gz-sim-odometry-publisher-system" name="gz::sim::systems::OdometryPublisher"><odom_frame>odom</odom_frame>
<robot_base_frame>{name}</robot_base_frame><odom_topic>/{topic}/odom</odom_topic><tf_topic>/{topic}/tf</tf_topic><dimensions>2</dimensions></plugin>
</model>"""


def disc(name, xy, r, h, col, z=0.0, emis=False):
    e = f"<emissive>{col} 1</emissive>" if emis else ""
    return f"""<model name="{name}"><static>true</static><pose>{xy[0]} {xy[1]} {z + h / 2} 0 0 0</pose><link name="l">
<visual name="v"><geometry><cylinder><radius>{r}</radius><length>{h}</length></cylinder></geometry>
<material><ambient>{col} 1</ambient><diffuse>{col} 1</diffuse>{e}</material></visual></link></model>"""


for ep in episodes:
    obst = sc["obst"]
    walls = []
    for kk, (x0, x1, y0, y1) in enumerate(boxes(obst)):
        cx, cy = (x0 + x1) / 2, H - (y0 + y1) / 2
        walls.append(f"""<link name="w{kk}"><pose>{cx} {cy} 1.0 0 0 0</pose>
<collision name="c"><geometry><box><size>{x1 - x0} {y1 - y0} 2</size></box></geometry></collision>
<visual name="v"><geometry><box><size>{x1 - x0} {y1 - y0} 2</size></box></geometry>
<material><ambient>0.45 0.5 0.58 1</ambient><diffuse>0.55 0.6 0.68 1</diffuse></material></visual></link>""")
    items = []
    for i, xy in enumerate(meta["sites"]):
        active = i in [r["dock"] for r in ep["robots"]]
        items.append(disc(f"site{i}", xy, 2.4, 0.06, "0.16 0.47 0.84" if active else "0.62 0.72 0.85"))
    for j, xy in enumerate(meta["zones"]):
        rad = 1.4 + 0.15 * sc["v"][j]
        items.append(disc(f"zone{j}", xy, rad, 0.05, "0.92 0.41 0.2"))
        for b in range(ep["attack"][j]):  # alarm beacon: one stacked red disc per alarm
            items.append(disc(f"alarm{j}_{b}", xy, 1.1, 1.6, "0.9 0.05 0.05", z=0.1 + 1.8 * b, emis=True))
    for ri, r in enumerate(ep["robots"]):
        items.append(robot_sdf(f"robot{ri}", r["xy"], COL[ri], f"r{ri}"))
    world = f"""<?xml version="1.0"?><sdf version="1.9"><world name="ep{ep['k']}">
<physics name="p" type="ignored"><max_step_size>0.004</max_step_size><real_time_factor>1.0</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
<scene><ambient>0.55 0.55 0.55 1</ambient><background>0.93 0.94 0.96 1</background><grid>false</grid><shadows>true</shadows></scene>
<light type="directional" name="sun"><cast_shadows>true</cast_shadows><pose>0 0 80 0 0 0</pose><diffuse>0.85 0.85 0.85 1</diffuse>
<specular>0.1 0.1 0.1 1</specular><direction>-0.35 0.25 -0.9</direction></light>
<model name="ground"><static>true</static><link name="l">
<collision name="c"><geometry><plane><normal>0 0 1</normal><size>400 400</size></plane></geometry></collision>
<visual name="v"><pose>{W / 2} {H / 2} 0 0 0 0</pose><geometry><plane><normal>0 0 1</normal><size>{W} {H}</size></plane></geometry>
<material><ambient>0.9 0.9 0.88 1</ambient><diffuse>0.92 0.92 0.9 1</diffuse></material></visual></link></model>
<model name="walls"><static>true</static>{''.join(walls)}</model>
{''.join(items)}
<model name="cam"><static>true</static><pose>60 22 125 0 1.42 1.5708</pose><link name="l">
<sensor name="cam" type="camera"><update_rate>10</update_rate><topic>overview</topic>
<camera><horizontal_fov>1.1</horizontal_fov><image><width>1280</width><height>720</height></image><clip><near>0.5</near><far>400</far></clip>
<save enabled="true"><path>/home/claude/gz/video/frames_ep{ep['k']}</path></save></camera></sensor></link></model>
</world></sdf>"""
    open(f"/home/claude/gz/video/ep{ep['k']}.sdf", "w").write(world)
    print(ep["k"], ep["kind"], "docks", [r["dock"] for r in ep["robots"]], "attack loaded", ep["loaded"],
          "served", ep["served"], "value %.2f" % ep["value"], "routes", [(r["dock"], r["zone"], len(r["path"])) for r in ep["robots"]])
print("P %.2f  V_x(q=0.25) %.2f  gain %.1f%%" % (P, Vx, meta["gain_pct"]))
