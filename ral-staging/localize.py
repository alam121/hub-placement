"""Rewrite the absolute paths used during development (/home/claude/ral, /home/claude/gz) to this checkout.
Run once after cloning:  python3 localize.py"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
MAP = [("/home/claude/RAL_video_leakage_aware_staging.mp4", os.path.join(HERE, "video", "RAL_video_leakage_aware_staging.mp4")),
       ("/home/claude/ral", os.path.join(HERE, "core")), ("/home/claude/gz", os.path.join(HERE, "gazebo"))]
n = 0
for root, _, files in os.walk(HERE):
    for f in files:
        if f.endswith((".py", ".sh", ".sdf", ".yaml", ".md")) and f != "localize.py":
            p = os.path.join(root, f); s = open(p).read(); t = s
            for a, b in MAP:
                t = t.replace(a, b)
            if t != s:
                open(p, "w").write(t); n += 1
print("updated", n, "files")
