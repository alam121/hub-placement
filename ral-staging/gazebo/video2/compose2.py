"""Revised RA-L video (1280x720, 30 fps). One encoded file per scene, joined with the concat demuxer.
Usage: compose2.py stills   -> writes scene PNGs for inspection only
       compose2.py render   -> encodes every scene and joins them"""
import glob, re, json, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
sys.path.insert(0, "/home/claude/gz/video")
from proj import project

V = "/home/claude/gz/video"; OUTD = "/home/claude/gz/video2/scenes"; os.makedirs(OUTD, exist_ok=True)
W, H, FPS = 1280, 720, 30
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = lambda s, b=False: ImageFont.truetype(FB if b else F, s)
INK, INK2, BG = (31, 31, 30), (92, 91, 85), (247, 247, 245)
RED, GREEN, BLUE = (200, 30, 30), (20, 130, 60), (42, 120, 214)
meta = json.load(open(f"{V}/episodes.json"))
e0, e1 = meta["episodes"][0], meta["episodes"][1]
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS)]


def frames(k):
    return sorted(glob.glob(f"{V}/frames_ep{k}/*.png"), key=lambda f: int(re.findall(r"_(\d+)\.png", f)[0]))


# ---------- drawing helpers
SC, OX, OY = 0.82, int((1280 - 1280 * 0.82) / 2), 94
RCOL = [(242, 184, 13), (26, 158, 77), (128, 51, 204)]
P = lambda x, y: (lambda u, v: (OX + SC * u, OY + SC * v))(*project(x, y, 0.0))


def canvas(frame_path):
    bg = Image.new("RGB", (W, H), BG)
    bg.paste(Image.open(frame_path).convert("RGB").resize((int(1280 * SC), int(720 * SC))), (OX, OY)); return bg


def header(img, title, sub, foot):
    d = ImageDraw.Draw(img, "RGBA")
    d.text((24, 12), title, font=font(26, True), fill=INK); d.text((24, 48), sub, font=font(19), fill=INK2)
    x = W - 400
    for c, t in [((42, 120, 214), "active dock"), ((235, 104, 52), "zone"), ((230, 15, 15), "alarm"), ((150, 150, 150), "robot")]:
        d.ellipse([x, 54, x + 14, 68], fill=c); d.text((x + 20, 50), t, font=font(16), fill=INK); x += 30 + int(d.textlength(t, font=font(16)))
    d.text((OX, H - 24), foot, font=font(14), fill=INK2); return d


def alarm_labels(d, ep):
    for j in ep["loaded"]:
        u, v = P(*meta["zones"][j]); d.ellipse([u - 18, v - 18, u + 18, v + 18], outline=(220, 20, 20), width=3)
        lab = f"{ep['attack'][j]} alarm" + ("s" if ep["attack"][j] > 1 else "")
        d.rounded_rectangle([u + 20, v - 30, u + 26 + d.textlength(lab, font=font(15)), v - 10], 4, fill=(255, 255, 255, 230))
        d.text((u + 23, v - 29), lab, font=font(15, True), fill=(200, 20, 20))


def routes(d, ep):
    for ri, r in enumerate(ep["robots"]):
        if r["path"]:
            d.line([P(x, y) for (x, y) in r["path"]], fill=RCOL[ri] + (200,), width=4)


def note(d, x, y, w, title, line, col):
    d.rounded_rectangle([x, y, x + w, y + 80], 10, fill=(255, 255, 255, 240))
    d.text((x + 20, y + 8), title, font=font(24, True), fill=col); d.text((x + 20, y + 44), line, font=font(18), fill=INK)


def slide(title, lines, img=None, box=None, lines_y=None):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.text((60, 46), title, font=font(36, True), fill=INK)
    y = 112 if lines_y is None else lines_y
    for l in lines:
        d.text((60, y), l, font=font(24), fill=INK); y += 36
    if img:
        fig = Image.open(img).convert("RGB"); fig.thumbnail(box[2:], Image.LANCZOS); im.paste(fig, (box[0] + (box[2] - fig.width) // 2, box[1]))
    return im


# ---------- scenes: (name, kind, payload). kind "still": (image, seconds); "anim": generator of frames
FOOT = "Gazebo Harmonic, physics-simulated differential-drive robots, software-rendered"


def scenes():
    out = []
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.text((80, 200), "When Should Robots Hide Where They Wait?", font=font(46, True), fill=INK)
    d.text((80, 270), "Leakage-Aware Randomized Staging for Capacity-Constrained Multi-Robot Response", font=font(26), fill=INK2)
    d.text((80, 360), "Syed Muhammad Alam (KAUST)   Hamza Rafique (LUMS)", font=font(24), fill=INK)
    d.text((80, 400), "Supplementary video, IEEE Robotics and Automation Letters submission", font=font(20), fill=INK2)
    out.append(("01_title", "still", (im, 4.0)))

    dim = ImageEnhance.Brightness(Image.open(frames(1)[5]).convert("RGB")).enhance(0.45)
    d = ImageDraw.Draw(dim, "RGBA"); d.rectangle([40, 140, 920, 600], fill=(255, 255, 255, 235))
    y = 165
    for i, l in enumerate(["The problem", "Robots wait at a few staging docks (one robot per dock).",
                           "An adversary triggers a burst of simultaneous alarms.",
                           "A zone is restored only if ALL its alarms are served.",
                           "If the adversary has seen where robots wait, it loads",
                           "exactly the zones they cannot reach in time.",
                           "Randomizing the staging helps only while it stays hidden."]):
        f_ = font(32, True) if i == 0 else font(26); d.text((70, y), l, font=f_, fill=INK); y += f_.size + 14
    out.append(("02_problem", "still", (dim, 9.0)))

    def shiftA():
        f0 = frames(0)[min(20, len(frames(0)) - 1)]
        for t in range(int(8 * FPS)):
            im = canvas(f0); d = header(im, "Shift A: fixed staging, the attacker has observed the docks",
                                         "It places alarms where no docked robot can complete a zone", FOOT)
            if t > 1.0 * FPS: alarm_labels(d, e0)
            if t > 3.0 * FPS: note(d, OX + 20, H - 120, 620, "Zones restored: 0", f"Value {e0['value']:.1f}: only the unloaded zones keep their value", RED)
            yield im
    out.append(("03_shiftA", "anim", shiftA))

    T1 = "Shift B: randomized staging (leakage-aware policy, q = 0.25)"; S1 = "The attacker knows the policy, not today's docks"
    F1 = FOOT + "; 3x speed; planned routes overlaid"
    def shiftB():
        fr = frames(1)
        for f in fr:
            im = canvas(f); d = header(im, T1, S1, F1); alarm_labels(d, e1); routes(d, e1); yield im
        for _ in range(int(4.5 * FPS)):
            im = canvas(fr[-1]); d = header(im, T1, S1, F1); alarm_labels(d, e1); routes(d, e1)
            for j in e1["served"]:
                u, v = P(*meta["zones"][j]); d.ellipse([u - 28, v - 28, u + 28, v + 28], outline=(20, 150, 60), width=5)
            note(d, OX + 20, H - 120, 680, "Two robots jointly restore the 2-alarm zone", f"Value {e1['value']:.1f} vs {e0['value']:.1f} for fixed staging (this shift)", GREEN)
            yield im
    out.append(("04_shiftB", "anim", shiftB))

    out.append(("05_policy", "still", (slide("What one shift does not show", [
        "Representative warehouse layout (gain near the mean of 15 layouts):",
        f"best fixed staging guarantees {meta['P']:.2f};",
        f"leakage-aware randomization at q = {meta['q']} guarantees {meta['Vx']:.2f}  (+{meta['gain_pct']:.1f}%).",
        "", "Single shifts vary; the guarantee is over the policy's distribution."]), 6.5)))
    out.append(("06_qcurve", "still", (slide("When does hiding pay?", [
        "The advantage shrinks as the attacker is more likely to observe the staging",
        "(probability q), and vanishes at a threshold q* computable by one LP."],
        "/home/claude/ral/fig_q_curves.png", (60, 200, 1160, 480)), 8.0)))
    out.append(("07_sim", "still", (slide("Randomize, but optimize the distribution", [
        "Closed-loop simulation, 15 layouts, paired random scenarios:",
        "optimized randomization +8.1%, +5.8%, +2.6% at q = 0, 0.25, 0.5;",
        "uniform randomization -12% to -18%."],
        "/home/claude/ral/fig_sim_bars.png", (60, 236, 1160, 460)), 9.0)))
    out.append(("08_limits", "still", (slide("Where it stops paying", [
        "The benefit relies on all-or-nothing restoration with reliable robots.",
        "It also shrinks with dense reachability, uniform priorities, larger fleets (to 3-4%)."],
        "/home/claude/gz/video2/chart_response.png", (60, 196, 1160, 500)), 9.0)))
    out.append(("09_gazebo_multi", "still", (slide("Concurrent Nav2 robots: verify reachability first", [
        "Three robots, one Nav2 stack each. Arrivals 0.95 s later than the model on average.",
        "One route Nav2 could not complete erased the office gain; Nav2-verified routes restore it."],
        "/home/claude/gz/video2/chart_gazebo.png", (60, 196, 1160, 500)), 10.0)))
    out.append(("10_nav2", "still", (slide("Travel times validated with Nav2", [
        "92 measured legs: Nav2 time = 0.997 x model + 1.0 s (R^2 = 0.995)."],
        "/home/claude/gz/fig_gazebo.png", (60, 170, 1160, 520)), 6.5)))
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    y = 170
    for l in ["Randomize robot staging only when", "  - zones need all their alarms served, by reliable robots,",
              "  - reachability is sparse and capacity tight,", "  - the chance the staging leaks is below q*, and",
              "  - reachability has been verified with the navigation stack.", "", "Code and data: github.com/alam121/hub-placement"]:
        d.text((80, y), l, font=font(30, l.startswith("Randomize")), fill=INK); y += 46
    out.append(("11_close", "still", (im, 7.0)))
    return out


def encode_still(name, im, secs):
    png = f"{OUTD}/{name}.png"; im.save(png); tmp = f"{OUTD}/{name}.tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", png,
                    "-vf", f"format=yuv420p,loop=-1:1,trim=duration={secs}"] + ENC + [tmp], check=True)
    os.replace(tmp, f"{OUTD}/{name}.mp4")


def encode_anim(name, gen):
    tmp = f"{OUTD}/{name}.tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-"] + ENC + [tmp], stdin=subprocess.PIPE)
    for im in gen():
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError(name)
    os.replace(tmp, f"{OUTD}/{name}.mp4")


if __name__ == "__main__":
    S = scenes()
    if sys.argv[1] == "stills":
        for name, kind, pay in S:
            if kind == "still": pay[0].save(f"/home/claude/gz/video2/check_{name}.png")
            else:
                fr = list(pay()); fr[-1].save(f"/home/claude/gz/video2/check_{name}.png")
    else:
        for name, kind, pay in S:
            encode_still(name, *pay) if kind == "still" else encode_anim(name, pay)
        with open(f"{OUTD}/list.txt", "w") as f:
            for name, _, _ in S: f.write(f"file '{OUTD}/{name}.mp4'\n")
        tmp = "/home/claude/RAL_video.tmp.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{OUTD}/list.txt", "-c", "copy", tmp], check=True)
        os.replace(tmp, "/home/claude/RAL_video_leakage_aware_staging.mp4")
        print("done")
