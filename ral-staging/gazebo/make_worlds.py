"""Convert the paper's occupancy-grid maps (sim.make_map) into Gazebo SDF worlds + Nav2 map files.
Grid cell = 1 m. World frame: x right, y up; grid row 0 is the top (y = H)."""
import sys, json
import numpy as np
sys.path.insert(0, "/home/claude/ral")
from sim import scenario

UPS = 4  # Nav2 map resolution 0.25 m


def boxes(obst):
    """Merge obstacle cells into row runs, then merge identical runs vertically -> rectangles."""
    H, W = obst.shape
    runs = {}
    for y in range(H):
        x = 0
        while x < W:
            if obst[y, x]:
                x0 = x
                while x < W and obst[y, x]:
                    x += 1
                runs.setdefault((x0, x), []).append(y)
            else:
                x += 1
    rects = []
    for (x0, x1), ys in runs.items():
        ys = sorted(ys); s = ys[0]; prev = s
        for y in ys[1:] + [None]:
            if y is not None and y == prev + 1:
                prev = y; continue
            rects.append((x0, x1, s, prev + 1)); s = y; prev = y
    return rects


def world_sdf(name, obst, robot_xy):
    H, W = obst.shape
    links = []
    for k, (x0, x1, y0, y1) in enumerate(boxes(obst)):
        cx, cy = (x0 + x1) / 2, H - (y0 + y1) / 2
        sx, sy = x1 - x0, y1 - y0
        links.append(f"""<link name="w{k}"><pose>{cx} {cy} 0.5 0 0 0</pose>
<collision name="c"><geometry><box><size>{sx} {sy} 1</size></box></geometry></collision>
<visual name="v"><geometry><box><size>{sx} {sy} 1</size></box></geometry></visual></link>""")
    rx, ry = robot_xy
    return f"""<?xml version="1.0"?>
<sdf version="1.9"><world name="{name}">
<physics name="p" type="ignored"><max_step_size>0.004</max_step_size><real_time_factor>1.0</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<model name="ground"><static>true</static><link name="l">
<collision name="c"><geometry><plane><normal>0 0 1</normal><size>400 400</size></plane></geometry>
<surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision></link></model>
<model name="walls"><static>true</static>{''.join(links)}</model>
<include><uri>file:///home/claude/gz/robot</uri><name>robot</name><pose>{rx} {ry} 0.0 0 0 0</pose></include>
</world></sdf>"""


def nav2_map(name, obst):
    up = np.kron(obst.astype(np.uint8), np.ones((UPS, UPS), np.uint8))
    img = np.where(up == 1, 0, 254).astype(np.uint8)
    h, w = img.shape
    with open(f"maps/{name}.pgm", "wb") as f:
        f.write(f"P5\n{w} {h}\n255\n".encode()); f.write(img.tobytes())
    open(f"maps/{name}.yaml", "w").write(
        f"image: {name}.pgm\nmode: trinary\nresolution: {1.0/UPS}\norigin: [0.0, 0.0, 0.0]\n"
        "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n")


if __name__ == "__main__":
    import os
    os.makedirs("maps", exist_ok=True); os.makedirs("worlds", exist_ok=True)
    meta = {}
    for kind in ("warehouse", "office", "campus"):
        sc = scenario(kind, 700, density=0.20, priority="skewed", c=1)
        H, W = sc["obst"].shape
        to_xy = lambda yx: (yx[1] + 0.5, H - yx[0] - 0.5)
        sites = [to_xy(s) for s in sc["sites"]]; zones = [to_xy(z) for z in sc["zones"]]
        open(f"worlds/{kind}.sdf", "w").write(world_sdf(kind, sc["obst"], sites[0]))
        nav2_map(kind, sc["obst"])
        meta[kind] = dict(sites=sites, zones=zones, Dsz=sc["Dsz"].tolist(), Dss=sc["Dss"].tolist(),
                          A=sc["A"].tolist(), deadline=sc["deadline"], n_boxes=len(boxes(sc["obst"])))
        print(kind, "boxes", meta[kind]["n_boxes"])
    json.dump(meta, open("maps/meta.json", "w"))
