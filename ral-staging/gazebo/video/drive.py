"""Pure-pursuit controller for the episode robots (gz-transport). Usage: drive.py <episode k>"""
import sys, json, math, time
import gz.transport13 as gt
from gz.msgs10.twist_pb2 import Twist
from gz.msgs10.odometry_pb2 import Odometry

k = int(sys.argv[1])
ep = json.load(open("/home/claude/gz/video/episodes.json"))["episodes"][k]
node = gt.Node()
state = {}
pubs = {}
for ri, r in enumerate(ep["robots"]):
    if not r["path"]:
        continue
    pubs[ri] = node.advertise(f"/r{ri}/cmd_vel", Twist)

    def cb(msg, ri=ri):
        p = msg.pose.position; o = msg.pose.orientation
        yaw = math.atan2(2 * (o.w * o.z + o.x * o.y), 1 - 2 * (o.y * o.y + o.z * o.z))
        state[ri] = (p.x, p.y, yaw)
    node.subscribe(Odometry, f"/r{ri}/odom", cb)
wp = {ri: 1 for ri in pubs}
done = {ri: False for ri in pubs}
t0 = time.time()
while not all(done.values()) and time.time() - t0 < 400:
    for ri, pub in pubs.items():
        if done[ri] or ri not in state:
            continue
        x, y, yaw = state[ri]
        path = ep["robots"][ri]["path"]
        while wp[ri] < len(path) - 1 and math.hypot(path[wp[ri]][0] - x, path[wp[ri]][1] - y) < 1.3:
            wp[ri] += 1
        gx, gy = path[wp[ri]]
        dist_goal = math.hypot(path[-1][0] - x, path[-1][1] - y)
        msg = Twist()
        if dist_goal < 0.7:
            done[ri] = True
        else:
            err = math.atan2(gy - y, gx - x) - yaw
            err = math.atan2(math.sin(err), math.cos(err))
            v = 1.5 * max(0.0, math.cos(err)) if abs(err) < 1.2 else 0.0
            msg.linear.x = min(v, 0.6 * dist_goal + 0.3)
            msg.angular.z = max(-2.0, min(2.0, 2.5 * err))
        pub.publish(msg)
    time.sleep(0.05)
for ri, pub in pubs.items():
    pub.publish(Twist())
print("done", done, round(time.time() - t0, 1), "s", flush=True)
