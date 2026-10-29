"""Assemble the RA-L video (1280x720, 30 fps) from Gazebo frames and paper figures."""
import glob, re, json, os, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

OUT = "/home/claude/gz/video/out_frames"
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
W, H, FPS = 1280, 720, 30
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, INK2, BG, ACC = (31, 31, 30), (92, 91, 85), (247, 247, 245), (42, 120, 214)
meta = json.load(open("/home/claude/gz/video/episodes.json"))
n = [0]


def emit(img, count=1):
    img = img.convert("RGB")
    for _ in range(count):
        img.save(f"{OUT}/f{n[0]:05d}.png"); n[0] += 1


def frames(k):
    fs = glob.glob(f"/home/claude/gz/video/frames_ep{k}/*.png")
    return sorted(fs, key=lambda f: int(re.findall(r"_(\d+)\.png", f)[0]))


def text_block(d, xy, lines, size=26, color=INK, gap=12, bold_first=False):
    x, y = xy
    for i, l in enumerate(lines):
        f = font(size + (6 if bold_first and i == 0 else 0), bold_first and i == 0)
        d.text((x, y), l, font=f, fill=color); y += f.size + gap
    return y


def banner(img, title, sub=None, foot=None):
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, 64 if sub is None else 92], fill=(255, 255, 255, 225))
    d.text((24, 14), title, font=font(28, True), fill=INK)
    if sub:
        d.text((24, 56), sub, font=font(20), fill=INK2)
    if foot:
        d.rectangle([0, H - 34, W, H], fill=(255, 255, 255, 215))
        d.text((24, H - 28), foot, font=font(16), fill=INK2)
    return d


def legend(d, x=W - 300, y=110):
    d.rounded_rectangle([x, y, x + 280, y + 150], 10, fill=(255, 255, 255, 230))
    items = [((42, 120, 214), "staging dock (active)"), ((235, 104, 52), "zone (size = priority)"),
             ((230, 15, 15), "alarm (one disc per alarm)"), ((120, 120, 120), "robot (coloured sphere)")]
    for i, (c, t) in enumerate(items):
        cy = y + 22 + 32 * i
        d.ellipse([x + 16, cy - 9, x + 34, cy + 9], fill=c)
        d.text((x + 46, cy - 11), t, font=font(18), fill=INK)


from proj import project
SC, OX, OY = 0.82, int((1280 - 1280 * 0.82) / 2), 94
RCOL = [(242, 184, 13), (26, 158, 77), (128, 51, 204)]
def P(x, y, z=0.0):
    u, v = project(x, y, z); return (OX + SC * u, OY + SC * v)

def canvas(frame_path):
    bg = Image.new("RGB", (W, H), (247, 247, 245))
    fr = Image.open(frame_path).convert("RGB").resize((int(1280 * SC), int(720 * SC)))
    bg.paste(fr, (OX, OY)); return bg

def header(img, title, sub, foot):
    d = ImageDraw.Draw(img, "RGBA")
    d.text((24, 12), title, font=font(26, True), fill=INK)
    d.text((24, 48), sub, font=font(19), fill=INK2)
    x = W - 400
    for c, t in [((42, 120, 214), "active dock"), ((235, 104, 52), "zone"), ((230, 15, 15), "alarm"), ((150, 150, 150), "robot")]:
        d.ellipse([x, 54, x + 14, 68], fill=c); d.text((x + 20, 50), t, font=font(16), fill=INK); x += 30 + int(d.textlength(t, font=font(16)))
    d.text((OX, H - 24), foot, font=font(14), fill=INK2)
    return d

def alarm_labels(d, ep):
    for j in ep["loaded"]:
        u, v = P(*meta["zones"][j])
        d.ellipse([u - 18, v - 18, u + 18, v + 18], outline=(220, 20, 20), width=3)
        lab = f"{ep['attack'][j]} alarm" + ("s" if ep["attack"][j] > 1 else "")
        d.rounded_rectangle([u + 20, v - 30, u + 26 + d.textlength(lab, font=font(15)), v - 10], 4, fill=(255, 255, 255, 230))
        d.text((u + 23, v - 29), lab, font=font(15, True), fill=(200, 20, 20))

def routes(d, ep):
    for ri, r in enumerate(ep["robots"]):
        if r["path"]:
            pts = [P(x, y) for (x, y) in r["path"]]
            d.line(pts, fill=RCOL[ri] + (200,), width=4)

def slide(lines, secs, title=None, img=None, img_box=None):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    y = 60
    if title:
        d.text((60, 50), title, font=font(36, True), fill=INK); y = 120
    if img:
        fig = Image.open(img).convert("RGB"); fig.thumbnail(img_box[2:]); im.paste(fig, img_box[:2])
    text_block(d, (60, y), lines, size=26)
    emit(im, int(secs * FPS))


# 1. title
im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
d.text((80, 200), "When Should Robots Hide Where They Wait?", font=font(46, True), fill=INK)
d.text((80, 270), "Leakage-Aware Randomized Staging for Capacity-Constrained Multi-Robot Response", font=font(26), fill=INK2)
d.text((80, 360), "Syed Muhammad Alam (KAUST)   Hamza Rafique (LUMS)", font=font(24), fill=INK)
d.text((80, 400), "Supplementary video, IEEE Robotics and Automation Letters submission", font=font(20), fill=INK2)
emit(im, 4 * FPS)

# 2. problem over a dimmed Gazebo frame
base = Image.open(frames(1)[5]).convert("RGB")
dim = ImageEnhance.Brightness(base).enhance(0.45)
d = ImageDraw.Draw(dim, "RGBA"); d.rectangle([40, 140, 900, 560], fill=(255, 255, 255, 235))
text_block(d, (70, 165), ["The problem",
                          "Robots wait at a few staging docks (one robot per dock).",
                          "An adversary triggers a burst of simultaneous alarms.",
                          "A zone is restored only if ALL its alarms are served.",
                          "If the adversary has seen where robots wait, it loads",
                          "exactly the zones they cannot reach in time."], size=26, bold_first=True)
emit(dim, 9 * FPS)

# 3. fixed staging (ep0): hold
e0, e1 = meta["episodes"][0], meta["episodes"][1]
f0 = frames(0)[min(20, len(frames(0)) - 1)]
FOOT = "Gazebo Harmonic, physics-simulated differential-drive robots, software-rendered"
for t in range(int(8 * FPS)):
    im = canvas(f0)
    d = header(im, "Shift A: fixed staging, the attacker has observed the docks",
               "It places alarms where no docked robot can complete a zone", FOOT)
    if t > 1.0 * FPS:
        alarm_labels(d, e0)
    if t > 3.0 * FPS:
        d.rounded_rectangle([OX + 20, H - 120, OX + 640, H - 40], 10, fill=(255, 255, 255, 240))
        d.text((OX + 40, H - 112), "Zones restored: 0", font=font(24, True), fill=(200, 30, 30))
        d.text((OX + 40, H - 76), f"Value {e0['value']:.1f}: only the unloaded zones keep their value", font=font(18), fill=INK)
    emit(im)

# 4. randomized staging (ep1): footage at 10 Hz sim -> 30 fps (about 3x)
fr1 = frames(1)
T1 = "Shift B: randomized staging (leakage-aware policy, q = 0.25)"
S1 = "The attacker knows the policy, not today's docks"
F1 = FOOT + "; 3x speed; planned routes overlaid"
for i, f in enumerate(fr1):
    im = canvas(f); d = header(im, T1, S1, F1); alarm_labels(d, e1); routes(d, e1)
    emit(im)
for t in range(int(4.5 * FPS)):
    im = canvas(fr1[-1]); d = header(im, T1, S1, F1); alarm_labels(d, e1); routes(d, e1)
    for j in e1["served"]:
        u, v = P(*meta["zones"][j]); d.ellipse([u - 28, v - 28, u + 28, v + 28], outline=(20, 150, 60), width=5)
    d.rounded_rectangle([OX + 20, H - 120, OX + 700, H - 40], 10, fill=(255, 255, 255, 240))
    d.text((OX + 40, H - 112), "Two robots jointly restore the 2-alarm zone", font=font(24, True), fill=(20, 130, 60))
    d.text((OX + 40, H - 76), f"Value {e1['value']:.1f} vs {e0['value']:.1f} for fixed staging (this shift)", font=font(18), fill=INK)
    emit(im)

# 5. what the policy guarantees on this layout
slide([f"Representative warehouse layout (gain near the mean of 15 layouts):",
       f"best fixed staging guarantees {meta['P']:.2f};",
       f"leakage-aware randomization at q = {meta['q']} guarantees {meta['Vx']:.2f}  (+{meta['gain_pct']:.1f}%).",
       "",
       "Single shifts vary; the guarantee is over the policy's distribution."], 7, title="What one shift does not show")

# 6. key theory + results figures
slide(["Advantage shrinks as the attacker is more likely to observe the staging",
       "(probability q) and vanishes at a computable threshold q*."], 8, title="When does hiding pay?",
      img="/home/claude/ral/fig_q_curves.png", img_box=(330, 230, 640, 460))
slide(["Closed-loop simulation, 15 layouts: optimized randomization helps;",
       "uniform randomization hurts (-12% to -18%)."], 8, title="Randomize, but optimize the distribution",
      img="/home/claude/ral/fig_sim_bars.png", img_box=(90, 220, 1100, 480))
slide(["Gazebo + Nav2: measured travel times match the planning model (R^2 = 0.995),",
       "so reachability, and the computed policies, carry over."], 8, title="Validated with Nav2 in Gazebo",
      img="/home/claude/gz/fig_gazebo.png", img_box=(120, 210, 1040, 480))

# 7. close
im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
text_block(d, (80, 210), ["Randomize robot staging only where reachability is sparse,",
                          "capacity is tight, and leakage is below q*.",
                          "", "Code and data: github.com/alam121/hub-placement"], size=30)
emit(im, 5 * FPS)

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{OUT}/f%05d.png",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "/home/claude/RAL_video_leakage_aware_staging.mp4"], check=True)
print("frames", n[0], "seconds", n[0] / FPS)
