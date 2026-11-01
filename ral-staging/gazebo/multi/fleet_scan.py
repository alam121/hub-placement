"""Fleet pose sharing as a virtual range sensor: for each robot k, publish /rk/fleet_scan (LaserScan in base_link)
containing only the other robots (discs of radius 0.35 m), computed from the poses robots broadcast over the fleet
network (here: ground-truth odometry). Walls are already in the static map. inf = free beam (clears the costmap)."""
import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

R, NB, RMAX = 0.35, 180, 6.0


class Fleet(Node):
    def __init__(self):
        super().__init__("fleet_scan", parameter_overrides=[rclpy.parameter.Parameter("use_sim_time", value=True)])
        self.pose = [None] * 3
        for k in range(3):
            self.create_subscription(Odometry, f"/r{k}/odom", lambda m, k=k: self.cb(k, m), 20)
        self.pub = [self.create_publisher(LaserScan, f"/r{k}/fleet_scan", 10) for k in range(3)]
        self.create_timer(0.1, self.tick)

    def cb(self, k, m):
        q = m.pose.pose.orientation
        self.pose[k] = (m.pose.pose.position.x, m.pose.pose.position.y, math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))

    def tick(self):
        if any(p is None for p in self.pose):
            return
        now = self.get_clock().now().to_msg()
        for k in range(3):
            x, y, th = self.pose[k]
            rng = [math.inf] * NB
            for o in range(3):
                if o == k:
                    continue
                dx, dy = self.pose[o][0] - x, self.pose[o][1] - y
                d = math.hypot(dx, dy)
                if d > RMAX + R or d < 1e-6:
                    continue
                for b in range(NB):
                    a = th - math.pi + 2 * math.pi * b / NB
                    ux, uy = math.cos(a), math.sin(a)
                    t = dx * ux + dy * uy
                    if t <= 0:
                        continue
                    h2 = d * d - t * t
                    if h2 <= R * R:
                        hit = t - math.sqrt(R * R - h2)
                        if 0.05 < hit < rng[b]:
                            rng[b] = hit
            m = LaserScan(); m.header.stamp = now; m.header.frame_id = "base_link"
            m.angle_min, m.angle_increment = -math.pi, 2 * math.pi / NB; m.angle_max = m.angle_min + (NB - 1) * m.angle_increment
            m.range_min, m.range_max, m.scan_time = 0.05, RMAX, 0.1
            m.ranges = rng
            self.pub[k].publish(m)


rclpy.init(); rclpy.spin(Fleet())
