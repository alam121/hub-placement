"""Concurrent multi-robot shifts in Gazebo with three Nav2 stacks.
Per shift: teleport robots to the shift's docks (gz set_pose), let them settle, send all dispatch goals at once,
record each robot's arrival (sim time), aborts, and the minimum pairwise distance between robots while any is
moving. Value = unloaded zones + zones whose every alarm is reached before its deadline and succeeds
(paired success uniforms from the shift list). Usage: multi_runner.py <dir>"""
import sys, json, math, time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
import gz.transport13 as gt
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.twist_pb2 import Twist

D = sys.argv[1]
import os
ACTIVE = [int(k) for k in os.environ.get("ROBOTS", "0 1 2").split()]
cfg = json.load(open(f"{D}/shifts.json"))
SERVICE = 30.0


class Runner(Node):
    def __init__(self):
        super().__init__("multi_runner", parameter_overrides=[rclpy.parameter.Parameter("use_sim_time", value=True)])
        self.ac = {k: ActionClient(self, NavigateToPose, f"/r{k}/navigate_to_pose") for k in ACTIVE}
        self.pose = [None] * 3; self.t = 0.0
        self.create_subscription(Clock, "/clock", lambda m: setattr(self, "t", m.clock.sec + m.clock.nanosec * 1e-9), 10)
        for k in range(3):
            self.create_subscription(Odometry, f"/r{k}/odom", lambda m, k=k: self.on_odom(k, m), 20)
        self.gz = gt.Node()
        self.cmd = [self.gz.advertise(f"/r{k}/cmd_vel", Twist) for k in range(3)]

    def on_odom(self, k, m):
        self.pose[k] = (m.pose.pose.position.x, m.pose.pose.position.y)

    def spin_for(self, sim_secs):
        t0 = self.t
        while rclpy.ok() and self.t - t0 < sim_secs:
            rclpy.spin_once(self, timeout_sec=0.05)

    def teleport(self, k, xy):
        for _ in range(3):
            self.cmd[k].publish(Twist())
        req = Pose(); req.name = f"robot{k}"; req.position.x, req.position.y, req.position.z = float(xy[0]), float(xy[1]), 0.0
        req.orientation.w = 1.0
        ok, rep = self.gz.request("/world/multi/set_pose", req, Pose, Boolean, 3000)
        return ok and rep.data


def main():
    rclpy.init(); r = Runner()
    for a in r.ac.values():
        while not a.wait_for_server(timeout_sec=2.0):
            rclpy.spin_once(r, timeout_sec=0.1)
    while any(p is None for p in r.pose) or r.t == 0.0:
        rclpy.spin_once(r, timeout_sec=0.1)
    # require every bt_navigator to be ACTIVE (lifecycle state id 3) before any shift
    from lifecycle_msgs.srv import GetState
    for k in ACTIVE:
        cli = r.create_client(GetState, f"/r{k}/bt_navigator/get_state")
        t0 = time.time()
        while True:
            if cli.wait_for_service(timeout_sec=2.0):
                f = cli.call_async(GetState.Request())
                while rclpy.ok() and not f.done():
                    rclpy.spin_once(r, timeout_sec=0.1)
                if f.result().current_state.id == 3:
                    break
            if time.time() - t0 > 180:
                print(f"NAV2 r{k} NOT ACTIVE", flush=True); sys.exit(2)
            time.sleep(2.0)
    print("ready (all navigators active)", flush=True)
    results = []
    for sh in cfg["shifts"]:
        for k, xy in enumerate(sh["dock_xy"]):
            r.teleport(k, xy)
        r.spin_for(3.0)
        routes = sh["route"]; t_start = r.t
        goals = {}
        for leg in routes:
            g = NavigateToPose.Goal(); g.pose.header.frame_id = "map"
            g.pose.pose.position.x, g.pose.pose.position.y = map(float, leg["zone_xy"]); g.pose.pose.orientation.w = 1.0
            goals[leg["robot"]] = (leg, r.ac[leg["robot"]].send_goal_async(g))
        handles, results_f, arrive, status = {}, {}, {}, {}
        min_d = math.inf; wall0 = time.time()
        limit = max([leg["deadline"] for leg in routes] + [0]) + 60.0
        while rclpy.ok() and goals and len(status) < len(goals) and r.t - t_start < limit and time.time() - wall0 < 600:
            rclpy.spin_once(r, timeout_sec=0.05)
            for k, (leg, f) in goals.items():
                if k not in handles and f.done():
                    handles[k] = f.result(); results_f[k] = handles[k].get_result_async()
                if k in results_f and k not in status and results_f[k].done():
                    st = results_f[k].result().status
                    status[k] = {4: "succeeded", 5: "canceled", 6: "aborted"}.get(st, str(st)); arrive[k] = r.t - t_start
            if all(p is not None for p in r.pose):
                for a in range(3):
                    for b in range(a + 1, 3):
                        min_d = min(min_d, math.dist(r.pose[a], r.pose[b]))
        for k in goals:
            if k not in status:
                status[k] = "timeout"; arrive[k] = r.t - t_start
                if k in handles: handles[k].cancel_goal_async()
        # value with paired success draws
        ok_cnt = {}
        legs_out = []
        for leg in routes:
            k = leg["robot"]
            on_time = status[k] == "succeeded" and arrive[k] <= leg["deadline"]
            succ = on_time and sh["success_u"][k] < cfg["p"]
            ok_cnt[leg["zone"]] = ok_cnt.get(leg["zone"], 0) + int(succ)
            legs_out.append(dict(robot=k, zone=leg["zone"], status=status[k], arrival=arrive[k], model_time=leg["model_time"],
                                 deadline=leg["deadline"], on_time=on_time))
        v = cfg["v"]; w = sh["attack"]
        val = sum(v[j] for j in range(len(w)) if w[j] == 0) + sum(v[j] for j in sh["served"] if ok_cnt.get(j, 0) == w[j])
        model_draw = sum(v[j] for j in range(len(w)) if w[j] == 0) + sum(
            v[j] for j in sh["served"] if sum(1 for leg in routes if leg["zone"] == j and sh["success_u"][leg["robot"]] < cfg["p"]) == w[j])
        res = dict(policy=sh["policy"], shift=sh["shift"], movers=len(routes), legs=legs_out, value=val,
                   model_value_same_draws=model_draw, model_expected=sh["model_value"],
                   min_pair_dist=None if min_d == math.inf else min_d)
        results.append(res)
        print(sh["policy"], sh["shift"], "movers", len(routes), [(l["status"], round(l["arrival"], 1), round(l["model_time"], 1), l["on_time"]) for l in legs_out],
              "value", round(val, 2), "model(same draws)", round(model_draw, 2), "min_d", None if min_d == math.inf else round(min_d, 2), flush=True)
        json.dump(results, open(f"{D}/gazebo_results.json", "w"), indent=1)
    rclpy.shutdown()


main()
