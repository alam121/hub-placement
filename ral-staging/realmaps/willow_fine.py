"""Willow Garage office (stage_ros willow-full.pgm, 0.1 m laser map of a real building) at native resolution.
fine_grid():     building geometry for the Gazebo world and the Nav2 map.
planning_grid(): the same geometry with obstacles inflated by the robot radius (0.35 m), restricted to the largest
                 connected free region: the planning model's shortest paths are paths the robot footprint fits through.
Occupied = wall/obstacle pixels and unknown (grey) area; isolated laser specks (<= 20 pixels, 0.2 m^2) are removed."""
import numpy as np
from PIL import Image
from scipy.ndimage import label, binary_dilation

RES = 0.1
ROBOT_R = 0.35


def _raw():
    im = np.array(Image.open("/home/claude/realmaps/willow-full.pgm")).astype(int)[:580, :540]
    occ = im < 230
    ol, on = label(occ)
    sz = np.bincount(ol.ravel())
    occ[np.isin(ol, np.where(sz <= 20)[0]) & (ol > 0)] = False
    occ[0, :] = occ[-1, :] = occ[:, 0] = occ[:, -1] = True
    return occ


def _inflate(occ):
    r = ROBOT_R / RES
    k = int(np.ceil(r))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    return binary_dilation(occ, structure=(xx ** 2 + yy ** 2) <= r * r)


def planning_grid():
    infl = _inflate(_raw())
    lab, n = label(~infl)
    sz = np.bincount(lab.ravel()); sz[0] = 0
    return lab != sz.argmax()                                   # True = blocked for the robot centre


def fine_grid():
    """raw free space restricted to the component that contains the planning region (drops laser streaks outside)"""
    occ = _raw()
    plan_free = ~planning_grid()
    lab, n = label(~occ)
    ids = np.unique(lab[plan_free]); ids = ids[ids > 0]
    return ~np.isin(lab, ids)                                   # True = occupied


def snap(occ, xy, max_m=1.0):
    """nearest free cell centre of grid occ to world point xy (m); None if farther than max_m"""
    H = occ.shape[0]
    r0, c0 = int((H * RES - xy[1]) / RES), int(xy[0] / RES)
    rad = int(max_m / RES); best = None
    for r in range(max(0, r0 - rad), min(H, r0 + rad + 1)):
        for c in range(max(0, c0 - rad), min(occ.shape[1], c0 + rad + 1)):
            if not occ[r, c]:
                p = ((c + 0.5) * RES, (H - r - 0.5) * RES); d = np.hypot(p[0] - xy[0], p[1] - xy[1])
                if d <= max_m and (best is None or d < best[0]): best = (d, p)
    return None if best is None else best[1]
