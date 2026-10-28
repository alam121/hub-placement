import numpy as np
W, H, HFOV = 1280, 720, 1.1
CAM = np.array([60.0, 22.0, 125.0]); PITCH, YAW = 1.42, 1.5708
def _R(p, y):
    cy, sy, cp, sp = np.cos(y), np.sin(y), np.cos(p), np.sin(p)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]); Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    return Rz @ Ry
R = _R(PITCH, YAW); f = (W / 2) / np.tan(HFOV / 2)
def project(x, y, z=0.0):
    pc = R.T @ (np.array([x, y, z]) - CAM)
    return (W / 2 - f * pc[1] / pc[0], H / 2 - f * pc[2] / pc[0])
