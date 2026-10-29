"""Drive a Nav2 tour through alternating staging sites and zones; record sim-time travel per leg.
Every consecutive (site, zone) or (zone, site) leg is one measured site-zone pair; some site->site
legs measure relocation. Usage: missions.py <map> <out.json> [n_legs]"""
import sys, json, math, time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock

MAP, OUT = sys.argv[1], sys.argv[2]
NLEGS = int(sys.argv[3]) if len(sys.argv) > 3 and int(sys.argv[3]) > 0 else 30
meta = json.load(open("/home/claude/gz/maps/meta.json"))[MAP]
S, Z = meta["sites"], meta["zones"]
Dsz, Dss = np.array(meta["Dsz"]), np.array(meta["Dss"])


def tour(n, rng):
    """Start at site 0. Mostly alternate site<->zone; every 5th leg is site->site (relocation)."""
    legs, cur = [], ("s", 0)
    for k in range(n):
        if cur[0] == "s" and k % 5 == 4:
            nxt = ("s", int(rng.choice([i for i in range(len(S)) if i != cur[1]])))
        elif cur[0] == "s":
            nxt = ("z", int(rng.integers(len(Z))))
        else:
            nxt = ("s", int(rng.integers(len(S))))
        legs.append((cur, nxt)); cur = nxt
    return legs


def model_len(a, b):
    if a[0] == "s" and b[0] == "z": return Dsz[a[1], b[1]]
    if a[0] == "z" and b[0] == "s": return Dsz[b[1], a[1]]
    return Dss[a[1], b[1]]


class Runner(Node):
    def __init__(self):
        super().__init__("mission_runner", parameter_overrides=[rclpy.parameter.Parameter("use_sim_time", value=True)])
        self.ac = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.t = 0.0; self.pose = None; self.dist = 0.0; self.traj = []
        self.create_subscription(Clock, "/clock", self.on_clock, 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 50)

    def on_clock(self, m):
        self.t = m.clock.sec + m.clock.nanosec * 1e-9

    def on_odom(self, m):
        p = (m.pose.pose.position.x, m.pose.pose.position.y)
        if self.pose is not None:
            self.dist += math.hypot(p[0] - self.pose[0], p[1] - self.pose[1])
        self.pose = p
        if not self.traj or math.hypot(p[0] - self.traj[-1][0], p[1] - self.traj[-1][1]) > 0.5:
            self.traj.append(p)

    def spin_until(self, fut, timeout):
        t0 = time.time()
        while rclpy.ok() and not fut.done() and time.time() - t0 < timeout:
            rclpy.spin_once(self, timeout_sec=0.05)
        return fut.done()

    def go(self, xy, timeout_wall=400):
        g = NavigateToPose.Goal()
        g.pose.header.frame_id = "map"
        g.pose.pose.position.x, g.pose.pose.position.y = float(xy[0]), float(xy[1])
        g.pose.pose.orientation.w = 1.0
        d0, t0 = self.dist, self.t
        fut = self.ac.send_goal_async(g)
        if not self.spin_until(fut, 30) or not fut.result().accepted:
            return dict(status="rejected")
        res = fut.result().get_result_async()
        ok = self.spin_until(res, timeout_wall)
        status = res.result().status if ok else -1
        return dict(status={4: "succeeded", 5: "canceled", 6: "aborted"}.get(status, f"timeout/{status}"),
                    sim_time=self.t - t0, odom_dist=self.dist - d0,
                    final=self.pose)


def main():
    rclpy.init()
    r = Runner()
    t0 = time.time()
    while not r.ac.wait_for_server(timeout_sec=2.0):
        rclpy.spin_once(r, timeout_sec=0.1)
        if time.time() - t0 > 120:
            print("NO NAV2"); sys.exit(1)
    while r.pose is None or r.t == 0.0:
        rclpy.spin_once(r, timeout_sec=0.1)
    print("nav2 ready, robot at", r.pose, flush=True)
    rng = np.random.default_rng({"warehouse": 1, "office": 2, "campus": 3}[MAP])
    out = []
    for k, (a, b) in enumerate(tour(NLEGS, rng)):
        xy = S[b[1]] if b[0] == "s" else Z[b[1]]
        res = r.go(xy)
        res.update(map=MAP, leg=k, frm=list(a), to=list(b), model_len=float(model_len(a, b)),
                   kind="relocation" if a[0] == b[0] == "s" else "response")
        if res["status"] == "succeeded":
            res["err_to_goal"] = math.hypot(res["final"][0] - xy[0], res["final"][1] - xy[1])
        out.append(res)
        print(k, a, b, res["status"], round(res.get("sim_time", -1), 1), "model_len", round(res["model_len"], 1), flush=True)
        json.dump(dict(legs=out, traj=r.traj), open(OUT, "w"))
    rclpy.shutdown()


main()
