"""
Virtual Earth Tactical Animation & Audio Generator
Generates high-definition, animated visual broadcast cards and tactical procedural audio
for Virtual Earth geopolitics:
- War Declarations & Frontline Clashes (with Emergency Air-Raid Siren audio & deep announcer video)
- War Conclusions & Surrenders (with Armistice Fanfare / Peace Bell audio & deep announcer video)
- Sovereign Alliances & Treaties (with Maritime Convoy / Ocean Sunrise video)
- Imperial Throne / Ruler Inception (with Sovereign Imperial Trumpet audio)
- Sovereign Annihilation / Country Fallen (with Defeat / Requiem audio)
"""

import io
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.parse
import urllib.request
import wave
from PIL import Image, ImageDraw, ImageFont

def _get_font(size: int = 18):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except Exception:
            return ImageFont.load_default()

def _get_font_bold(size: int = 18):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except Exception:
        return _get_font(size)

# === Procedural Sound Effects Engine (Pure Python standard library) ============

def generate_tactical_audio(sound_type: str = "war_siren", duration: float = 3.5, sample_rate: int = 44100) -> io.BytesIO:
    """Generate cinematic tactical audio for Discord dispatches (Air-Raid, Trumpet, Armistice, Requiem)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_samples = int(duration * sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            val = 0.0

            if sound_type == "war_siren":
                freq = 650.0 + 190.0 * math.sin(2.0 * math.pi * 1.1 * t)
                wave_sample = math.sin(2.0 * math.pi * freq * t)
                sub_drone = 0.35 * math.sin(2.0 * math.pi * 65.0 * t)
                val = (wave_sample * 0.65 + sub_drone)
            elif sound_type == "victory_fanfare":
                step = int(t / 0.4)
                notes = [261.63, 329.63, 392.00, 523.25, 659.25, 783.99]
                curr_freq = notes[min(step, len(notes) - 1)]
                harmonic = 0.6 * math.sin(2 * math.pi * curr_freq * t) + 0.3 * math.sin(4 * math.pi * curr_freq * t)
                envelope = math.exp(-2.5 * (t % 0.4)) if step < len(notes) - 1 else math.exp(-0.8 * (t - 2.0))
                val = harmonic * envelope
            elif sound_type == "ruler_inauguration":
                tones = [349.23, 440.0, 523.25, 698.46]
                tone_idx = min(int(t / 0.5), len(tones) - 1)
                f = tones[tone_idx]
                brass = 0.65 * math.sin(2 * math.pi * f * t) + 0.3 * math.sin(3 * math.pi * f * t)
                val = brass * min(1.0, (duration - t) * 0.8)
            elif sound_type == "surrender_conceded":
                freq1 = 440.0
                freq2 = 554.37
                bell = (0.5 * math.sin(2 * math.pi * freq1 * t) + 0.5 * math.sin(2 * math.pi * freq2 * t))
                envelope = math.exp(-1.4 * t)
                val = bell * envelope
            elif sound_type == "alliance_treaty":
                f1 = 349.23 if t < 1.0 else (440.0 if t < 2.0 else 523.25)
                f2 = 440.0 if t < 1.0 else (523.25 if t < 2.0 else 698.46)
                brass = 0.45 * math.sin(2 * math.pi * f1 * t) + 0.35 * math.sin(2 * math.pi * f2 * t)
                val = brass * min(1.0, (duration - t) * 0.9)
            elif sound_type == "commander_march":
                step = int(t / 0.35)
                notes = [196.0, 261.63, 329.63, 392.0, 523.25]
                f = notes[min(step, len(notes) - 1)]
                pulse = 0.7 * math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t)
                snare = 0.15 * math.sin(2 * math.pi * 120.0 * (t % 0.35))
                val = (pulse + snare) * min(1.0, (duration - t) * 0.85)
            else:
                f = max(40.0, 110.0 - (t * 22.0))
                drone = 0.7 * math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * (f * 1.5) * t)
                decay = math.exp(-0.9 * t)
                val = drone * decay

            sample_int = int(val * 28000)
            sample_int = max(-32767, min(32767, sample_int))
            wf.writeframes(struct.pack("<h", sample_int))

    buf.seek(0)
    return buf

# === Text Sanitization ========================================================

def clean_tactical_text(text: str) -> str:
    """Strip Unicode emojis and flag characters that render as boxes in Pillow."""
    if not text:
        return ""
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    clean = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55]', '', clean)
    return clean.strip()

# === Audio Duration Probe =====================================================

def probe_audio_duration(audio_bytes: io.BytesIO) -> float:
    """Accurately determine audio duration in seconds using FFmpeg probe."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if not exe or not os.path.exists(exe):
            return 8.0
        audio_bytes.seek(0)
        data = audio_bytes.read()
        audio_bytes.seek(0)
        if not data or len(data) < 200:
            return 8.0
        td = tempfile.mkdtemp()
        try:
            p = os.path.join(td, "probe.mp3")
            with open(p, "wb") as f:
                f.write(data)
            res = subprocess.run([exe, "-i", p], capture_output=True, text=True, errors="replace", timeout=10)
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
            if m:
                h, mins, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
                return h * 3600 + mins * 60 + s
        finally:
            shutil.rmtree(td, ignore_errors=True)
    except Exception:
        pass
    return 8.0

# === Video Render Engine (FFmpeg H.264 / 48kHz Stereo AAC) ====================

def render_frames_to_mp4(frames, audio_bytes=None, fps: int = 10, width: int = 640, height: int = 360) -> io.BytesIO | None:
    """Render Pillow frames (generator or list) and optional audio into a faststart H.264 MP4 with 48kHz Stereo AAC.
    Uses stdin rawvideo streaming and ultrafast preset for minimal peak RAM (<15MB) on memory-constrained servers."""
    if frames is None:
        return None
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if not exe or not os.path.exists(exe):
            return None
    except Exception:
        return None

    td = tempfile.mkdtemp()
    try:
        audio_path = None
        audio_dur = None
        if audio_bytes is not None:
            audio_bytes.seek(0)
            data = audio_bytes.read()
            if len(data) > 100:
                audio_path = os.path.join(td, "audio.mp3")
                with open(audio_path, "wb") as f:
                    f.write(data)
                try:
                    probe_cmd = [exe, "-i", audio_path]
                    p_res = subprocess.run(probe_cmd, capture_output=True, text=True, errors="replace", timeout=10)
                    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p_res.stderr)
                    if dur_match:
                        h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
                        audio_dur = h * 3600 + m * 60 + s
                except Exception:
                    pass

        out_path = os.path.join(td, "out.mp4")
        cmd = [
            exe, "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-",
        ]

        if audio_path and os.path.exists(audio_path):
            cmd.extend([
                "-i", audio_path,
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-ac", "2",
                "-shortest"
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "fastdecode",
            "-crf", "26",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            out_path
        ])

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        last_frame_bytes = None
        count = 0
        for frame in frames:
            fb = frame.tobytes()
            proc.stdin.write(fb)
            last_frame_bytes = fb
            count += 1

        if audio_dur and last_frame_bytes:
            needed = int(math.ceil(audio_dur * fps))
            if needed > count:
                for _ in range(needed - count):
                    proc.stdin.write(last_frame_bytes)

        proc.stdin.close()
        proc.wait(timeout=40)

        if proc.returncode == 0 and os.path.exists(out_path):
            with open(out_path, "rb") as f:
                buf = io.BytesIO(f.read())
            buf.seek(0)
            return buf
    except Exception as e:
        print(f"⚠️ MP4 render notice: {e}", flush=True)
    finally:
        shutil.rmtree(td, ignore_errors=True)

    return None

# === Procedural Cinematic Frame Renderers =====================================

def render_order_parchment_frame(
    frame_idx: int,
    total_frames: int,
    doc_type: str,
    party_a: str,
    party_b: str,
    decree: str,
    seal_text: str = "RATIFIED",
    seal_color = (185, 28, 28)
) -> Image.Image:
    """Scene 1: Official parchment decree on mahogany desk, hand writing cursive signature, and wax seal stamping down."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (32, 20, 14))
    draw = ImageDraw.Draw(im)

    # Wood grain planks on mahogany desk
    for y in range(0, h, 24):
        draw.line([(0, y), (w, y)], fill=(24, 15, 10), width=1)
        draw.line([(0, y + 1), (w, y + 1)], fill=(40, 26, 18), width=1)

    # Parchment shadow and sheet
    px0, py0, px1, py1 = 70, 25, 570, 335
    draw.rectangle([px0 + 5, py0 + 6, px1 + 5, py1 + 6], fill=(16, 10, 7))
    draw.rectangle([px0, py0, px1, py1], fill=(247, 240, 222))
    draw.rectangle([px0 + 6, py0 + 6, px1 - 6, py1 - 6], outline=(190, 165, 120), width=2)
    draw.rectangle([px0 + 10, py0 + 10, px1 - 10, py1 - 10], outline=(220, 195, 150), width=1)

    for cx, cy in [(px0+10, py0+10), (px1-10, py0+10), (px0+10, py1-10), (px1-10, py1-10)]:
        draw.rectangle([cx-3, cy-3, cx+3, cy+3], fill=(180, 145, 90))

    font_hdr = _get_font_bold(18)
    font_bold = _get_font_bold(14)
    font_sub = _get_font(12)
    font_sig = _get_font(11)
    font_seal = _get_font_bold(10)

    # Header Emblem & Title
    draw.text((320, 48), "***", fill=(160, 120, 60), font=font_hdr, anchor="mm")
    draw.text((320, 72), doc_type.upper(), fill=(110, 30, 20), font=font_bold, anchor="mm")
    draw.line([(px0 + 40, 88), (px1 - 40, 88)], fill=(180, 150, 100), width=2)
    draw.polygon([(320, 84), (325, 88), (320, 92), (315, 88)], fill=(150, 110, 50))

    # Decree body
    draw.text((px0 + 35, 114), "ISSUED UNDER SUPREME SOVEREIGN AUTHORITY:", fill=(100, 80, 60), font=font_sub)
    draw.text((px0 + 35, 138), f"PRIMARY BELLIGERENT: {party_a.upper()[:28]}", fill=(25, 25, 30), font=font_bold)
    draw.text((px0 + 35, 168), f"TARGET NATION: {party_b.upper()[:28]}", fill=(25, 25, 30), font=font_bold)
    draw.text((px0 + 35, 198), f"DECREE: {decree.upper()[:36]}", fill=(140, 30, 20), font=font_bold)
    draw.text((px0 + 35, 226), "TOTAL MILITARY & DIPLOMATIC RATIFICATION IN EFFECT", fill=(90, 80, 70), font=font_sub)

    # Signature line
    sig_x0, sig_y, sig_x1 = 310, 275, 520
    draw.line([(sig_x0, sig_y), (sig_x1, sig_y)], fill=(130, 110, 90), width=1)
    draw.text((sig_x0, sig_y + 6), "Authorized Sovereign Ratification", fill=(120, 105, 90), font=font_sig)

    t = frame_idx / max(1, total_frames - 1)

    # Signature animation (t: 0.15 to 0.65)
    sig_progress = max(0.0, min(1.0, (t - 0.15) / 0.50))
    if sig_progress > 0:
        sig_pts = []
        n_steps = int(sig_progress * 100)
        for s in range(n_steps):
            frac = s / 100.0
            x = sig_x0 + 10 + frac * (sig_x1 - sig_x0 - 30)
            y = sig_y - 12 + math.sin(frac * 28.0) * 8 - math.cos(frac * 14.0) * 4
            sig_pts.append((x, y))
        if len(sig_pts) > 1:
            draw.line(sig_pts, fill=(15, 25, 60), width=2)

    # Executive Hand & Fountain Pen
    if 0.10 <= t <= 0.78:
        if t < 0.15:
            in_t = (t - 0.10) / 0.05
            pen_x = sig_x0 + 10
            pen_y = (sig_y - 40) + in_t * 28
        elif t <= 0.65:
            pen_x = sig_x0 + 10 + sig_progress * (sig_x1 - sig_x0 - 30)
            pen_y = sig_y - 12 + math.sin(sig_progress * 28.0) * 8 - math.cos(sig_progress * 14.0) * 4
        else:
            out_t = (t - 0.65) / 0.13
            pen_x = (sig_x1 - 20) + out_t * 60
            pen_y = sig_y - 12 - out_t * 40

        draw.polygon([(pen_x, pen_y), (pen_x + 12, pen_y - 16), (pen_x + 18, pen_y - 12)], fill=(234, 179, 8), outline=(180, 130, 20))
        bx0, by0 = pen_x + 14, pen_y - 14
        bx1, by1 = bx0 + 65, by0 - 65
        draw.line([(bx0, by0), (bx1, by1)], fill=(20, 25, 35), width=8)
        draw.line([(bx0 + 2, by0 - 2), (bx1 + 2, by1 - 2)], fill=(45, 55, 72), width=4)
        draw.line([(bx0 + 10, by0 - 10), (bx0 + 14, by0 - 6)], fill=(234, 179, 8), width=3)

        hx, hy = bx1 + 10, by1 - 10
        draw.rectangle([hx - 8, hy - 8, hx + 14, hy + 14], fill=(245, 245, 250), outline=(200, 200, 210))
        draw.ellipse([hx, hy, hx + 6, hy + 6], fill=(234, 179, 8))
        draw.polygon([(hx + 5, hy - 12), (hx + 80, hy - 40), (hx + 90, hy + 30), (hx + 10, hy + 15)], fill=(30, 36, 45))

    # Imperial Wax Seal Stamp
    if t >= 0.70:
        seal_x, seal_y = px0 + 85, py1 - 65
        seal_t = (t - 0.70) / 0.30
        scale = 1.0 if seal_t >= 0.3 else 1.0 + (0.3 - seal_t) * 2.0
        rad = int(32 * scale)
        draw.ellipse([seal_x - rad + 3, seal_y - rad + 3, seal_x + rad + 3, seal_y + rad + 3], fill=(120, 100, 80))
        draw.ellipse([seal_x - rad, seal_y - rad, seal_x + rad, seal_y + rad], fill=seal_color, outline=(120, 15, 15), width=2)
        inner_rad = int(rad * 0.78)
        draw.ellipse([seal_x - inner_rad, seal_y - inner_rad, seal_x + inner_rad, seal_y + inner_rad], outline=(245, 215, 170), width=1)
        if scale < 1.15:
            draw.text((seal_x, seal_y - 6), "SOVEREIGN", fill=(255, 240, 220), font=font_seal, anchor="mm")
            draw.text((seal_x, seal_y + 6), seal_text, fill=(255, 240, 220), font=font_seal, anchor="mm")

    return im

def render_war_scene_frame(
    frame_idx: int,
    total_frames: int,
    atk_name: str,
    dfn_name: str,
    scale_name: str = "MAJOR WAR",
    domain: str = "SOVEREIGN CLASH"
) -> Image.Image:
    """Scene 2: Long, continuous cinematic battle progression with multi-wave air sorties, advancing armor column, and artillery."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (20, 10, 8))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_tag = _get_font_bold(10)

    # Fiery Sky Gradient
    for y in range(220):
        frac = y / 220.0
        r = int(25 + frac * (220 - 25))
        g = int(10 + frac * (80 - 10))
        b = int(15 + frac * (20 - 15))
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Continuous Rising Smoke Plumes
    for s_idx, (sx, sy_base) in enumerate([(90, 210), (220, 205), (380, 212), (520, 208)]):
        for puff in range(10):
            t_puff = (frame_idx * 0.7 + puff * 3.5) % 35
            py = sy_base - t_puff * 5.5
            px = sx + math.sin(t_puff * 0.4 + s_idx * 1.5) * 16 + (puff * 1.8)
            rad = int(7 + t_puff * 1.6)
            alpha_col = int(max(0, 75 - t_puff * 2.1))
            draw.ellipse([px - rad, py - rad, px + rad, py + rad], fill=(alpha_col, alpha_col - 4, alpha_col - 8))

    # Distant Mountains
    mountains = [(0, 210), (90, 175), (190, 205), (280, 165), (390, 210), (490, 170), (580, 205), (640, 185), (640, 220), (0, 220)]
    draw.polygon(mountains, fill=(45, 20, 16))

    # Distant Artillery Flash on Ridge (fires periodically at frames 25, 70, 120, 165)
    for art_f in [25, 70, 120, 165]:
        if 0 <= frame_idx - art_f < 6:
            decay = (frame_idx - art_f)
            ax, ay = (280 if art_f % 2 == 0 else 490), (165 if art_f % 2 == 0 else 170)
            a_rad = int(22 - decay * 3)
            draw.ellipse([ax - a_rad, ay - a_rad, ax + a_rad, ay + a_rad], fill=(255, 240, 120))
            draw.ellipse([ax - a_rad//2, ay - a_rad//2, ax + a_rad//2, ay + a_rad//2], fill=(255, 255, 255))

    # Scorched Ground
    for y in range(220, 360):
        frac = (y - 220) / 140.0
        draw.line([(0, y), (w, y)], fill=(int(50 - frac * 30), int(32 - frac * 18), int(22 - frac * 12)))

    # Shell craters
    for cx, cy, rx, ry in [(140, 245, 28, 7), (380, 255, 35, 9), (560, 248, 24, 6)]:
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(22, 12, 8))

    # AIRCRAFT SORTIES IN PROGRESSIVE WAVES (No 5-second loop resets)
    # Wave 1: Supersonic Fighters (enters at frame 0, exits by frame 45)
    if 0 <= frame_idx <= 45:
        j_prog = frame_idx * 19.0
        jx1, jy1 = -80 + j_prog, 75 + math.sin(frame_idx * 0.25) * 8
        jx2, jy2 = jx1 - 85, jy1 + 32
        for jx, jy, scale_j in [(jx1, jy1, 1.0), (jx2, jy2, 0.75)]:
            if -80 <= jx <= w + 80:
                draw.polygon([(jx - 24 * scale_j, jy), (jx - 45 * scale_j, jy - 3), (jx - 55 * scale_j, jy), (jx - 45 * scale_j, jy + 3)], fill=(255, 140, 0))
                draw.polygon([(jx - 24 * scale_j, jy), (jx - 38 * scale_j, jy - 2), (jx - 42 * scale_j, jy), (jx - 38 * scale_j, jy + 2)], fill=(255, 240, 120))
                draw.polygon([(jx + 32 * scale_j, jy), (jx - 15 * scale_j, jy - 14 * scale_j), (jx - 24 * scale_j, jy - 6 * scale_j), (jx - 24 * scale_j, jy + 6 * scale_j), (jx - 15 * scale_j, jy + 14 * scale_j)], fill=(30, 35, 45), outline=(60, 70, 85))
                draw.ellipse([jx + 5 * scale_j, jy - 3 * scale_j, jx + 18 * scale_j, jy + 3 * scale_j], fill=(130, 190, 230))

    # Wave 2: Rocket Barrage launching diagonally (frames 45 to 90)
    if 45 <= frame_idx <= 90:
        r_step = frame_idx - 45
        for r_idx in range(4):
            launch_t = r_step - r_idx * 7
            if 0 <= launch_t <= 32:
                rx = 180 + r_idx * 35 + launch_t * 12
                ry = 230 - launch_t * 5.5
                draw.line([(rx - launch_t * 12, 230), (rx, ry)], fill=(220, 220, 230), width=2)
                draw.ellipse([rx - 2, ry - 2, rx + 4, ry + 2], fill=(255, 220, 80))
                draw.polygon([(rx, ry), (rx - 12, ry + 3), (rx - 12, ry - 3)], fill=(255, 100, 0))

    # Wave 3: Heavy Stealth Bomber with Escort (frames 85 to 155)
    if 85 <= frame_idx <= 155:
        b_step = frame_idx - 85
        bx = -110 + b_step * 11.5
        by = 60 + math.sin(b_step * 0.15) * 5
        if -120 <= bx <= w + 120:
            wing_poly = [
                (bx + 40, by),
                (bx - 30, by - 26),
                (bx - 20, by - 12),
                (bx - 45, by),
                (bx - 20, by + 12),
                (bx - 30, by + 26)
            ]
            draw.polygon(wing_poly, fill=(24, 28, 36), outline=(50, 60, 75))
            draw.ellipse([bx - 25, by - 5, bx - 18, by - 2], fill=(255, 140, 0))
            draw.ellipse([bx - 25, by + 2, bx - 18, by + 5], fill=(255, 140, 0))
            fx = bx - 65
            fy = by - 32
            draw.polygon([(fx + 22, fy), (fx - 10, fy - 9), (fx - 15, fy), (fx - 10, fy + 9)], fill=(40, 48, 60))

    # Wave 4: Late-phase supersonic sweep (frames 145+)
    if frame_idx >= 145:
        l_step = frame_idx - 145
        lx = -70 + l_step * 21.0
        ly = 85 + math.sin(l_step * 0.3) * 6
        if -80 <= lx <= w + 80:
            draw.polygon([(lx - 24, ly), (lx - 45, ly - 3), (lx - 55, ly), (lx - 45, ly + 3)], fill=(255, 140, 0))
            draw.polygon([(lx + 32, ly), (lx - 15, ly - 14), (lx - 24, ly - 6), (lx - 24, ly + 6), (lx - 15, ly + 14)], fill=(30, 35, 45))

    # ADVANCING ARMORED DIVISION (Continuous non-resetting progression)
    t1_x = -100 + frame_idx * 3.3
    t1_y = 300
    t2_x = t1_x - 175
    t2_y = 265
    t3_x = t1_x - 340
    t3_y = 295

    for tx, ty, sc, is_lead in [(t3_x, t3_y, 0.9, False), (t2_x, t2_y, 0.75, False), (t1_x, t1_y, 1.0, True)]:
        if -160 <= tx <= w + 160:
            tw, th = int(120 * sc), int(22 * sc)
            draw.rounded_rectangle([tx - tw//2, ty - th//2, tx + tw//2, ty + th//2], radius=int(8*sc), fill=(25, 25, 25), outline=(50, 50, 50), width=2)
            n_wheels = 5
            wheel_spacing = tw // (n_wheels + 1)
            for widx in range(n_wheels):
                wx = (tx - tw//2) + (widx + 1) * wheel_spacing
                wy = ty
                wrad = int(7 * sc)
                draw.ellipse([wx - wrad, wy - wrad, wx + wrad, wy + wrad], fill=(45, 45, 45), outline=(80, 80, 80))
                rot = frame_idx * 0.35
                spk_x = wx + math.cos(rot) * (wrad - 2)
                spk_y = wy + math.sin(rot) * (wrad - 2)
                draw.line([(wx, wy), (spk_x, spk_y)], fill=(160, 160, 160), width=1)

            hw, hh = int(110 * sc), int(18 * sc)
            draw.polygon([
                (tx - hw//2 - 10*sc, ty - th//2),
                (tx + hw//2 + 5*sc, ty - th//2),
                (tx + hw//2 - 8*sc, ty - th//2 - hh),
                (tx - hw//2, ty - th//2 - hh)
            ], fill=(55, 65, 50), outline=(35, 42, 32))

            tur_w, tur_h = int(55 * sc), int(16 * sc)
            tur_y = ty - th//2 - hh - tur_h
            draw.polygon([
                (tx - tur_w//2, ty - th//2 - hh),
                (tx + tur_w//2, ty - th//2 - hh),
                (tx + tur_w//2 - 8*sc, tur_y),
                (tx - tur_w//2 + 5*sc, tur_y)
            ], fill=(65, 78, 60), outline=(40, 50, 36))

            bar_len = int(75 * sc)
            bar_y = tur_y + int(7 * sc)
            draw.line([(tx + tur_w//2 - 8*sc, bar_y), (tx + tur_w//2 + bar_len, bar_y)], fill=(45, 52, 40), width=int(5*sc))

            firing = any(0 <= frame_idx - fire_f < 4 for fire_f in [28, 75, 125, 175])
            if is_lead and firing:
                mf_x = tx + tur_w//2 + bar_len
                draw.ellipse([mf_x - 8, bar_y - 10, mf_x + 22, bar_y + 10], fill=(255, 230, 80))
                draw.polygon([(mf_x, bar_y - 5), (mf_x + 30, bar_y), (mf_x, bar_y + 5)], fill=(255, 120, 0))

    # Top HUD Banner
    draw.rectangle([0, 0, w, 38], fill=(15, 10, 12))
    draw.line([(0, 38), (w, 38)], fill=(220, 38, 38), width=2)
    beacon_col = (255, 50, 50) if (frame_idx % 6 < 3) else (150, 20, 20)
    draw.ellipse([14, 12, 26, 24], fill=beacon_col)
    draw.text((36, 11), f"MILITARY MOBILIZATION: {atk_name.upper()} VS {dfn_name.upper()}", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), f"[{scale_name.upper()}]", fill=(255, 80, 80), font=font_tag, anchor="rt")

    return im

def render_surrender_scene_frame(
    frame_idx: int,
    total_frames: int,
    winner_name: str,
    loser_name: str,
    reparations: int = 0
) -> Image.Image:
    """Scene 2: Gloomy dusk ruins, crumbling buildings, smoke, and a fluttering white truce flag with continuous physics."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (18, 18, 22))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_tag = _get_font_bold(10)

    # Gloomy Dusk Overcast Sky
    for y in range(230):
        frac = y / 230.0
        draw.line([(0, y), (w, y)], fill=(int(24 + frac * 46), int(24 + frac * 41), int(28 + frac * 47)))

    # Distant Ruined Skyline
    buildings = [
        (40, 110, 50, 120), (105, 140, 45, 90), (170, 95, 60, 135),
        (330, 130, 40, 100), (385, 80, 55, 150), (455, 115, 65, 115),
        (540, 90, 70, 140)
    ]
    for bx, by, bw, bh in buildings:
        roof_jag = [
            (bx, by + bh),
            (bx, by + 10),
            (bx + bw//3, by),
            (bx + bw//2, by + 18),
            (bx + (bw*2)//3, by + 8),
            (bx + bw, by + 25),
            (bx + bw, by + bh)
        ]
        draw.polygon(roof_jag, fill=(35, 35, 42))
        for wy in range(by + 30, by + bh - 20, 22):
            for wx in range(bx + 8, bx + bw - 10, 14):
                if (wx + wy) % 3 != 0:
                    draw.rectangle([wx, wy, wx + 7, wy + 11], fill=(15, 15, 20))

    # Smoldering rubble ground
    for y in range(230, 360):
        frac = (y - 230) / 130.0
        draw.line([(0, y), (w, y)], fill=(int(45 - frac * 20), int(42 - frac * 18), int(40 - frac * 16)))

    for rx, ry, rw, rh in [(70, 290, 110, 40), (280, 305, 140, 35), (490, 285, 130, 45)]:
        draw.ellipse([rx, ry, rx + rw, ry + rh], fill=(28, 26, 25))

    # Continuous Upward Drifting Ash Embers
    for e_idx in range(30):
        ex = (e_idx * 37 + frame_idx * 2.2) % w
        ey = 330 - ((e_idx * 29 + frame_idx * 2.5) % 310)
        e_sz = (e_idx % 3) + 1
        e_col = (200, 200, 210) if e_idx % 4 != 0 else (255, 120, 40)
        draw.ellipse([ex, ey, ex + e_sz, ey + e_sz], fill=e_col)

    # Steel Flagpole & White Surrender Truce Flag
    px = 220
    py_top = 90
    py_bot = 325

    draw.line([(px, py_top), (px, py_bot)], fill=(180, 185, 195), width=4)
    draw.line([(px - 1, py_top), (px - 1, py_bot)], fill=(230, 235, 245), width=1)
    draw.ellipse([px - 5, py_top - 6, px + 5, py_top + 4], fill=(234, 179, 8))

    flag_len = 130
    flag_h = 75
    flag_top_pts = []
    flag_bot_pts = []

    for step in range(0, flag_len + 1, 5):
        wx = px + 2 + step
        wave1 = math.sin((frame_idx * 0.28) + (step * 0.05)) * 8
        wave2 = math.cos((frame_idx * 0.17) + (step * 0.07)) * 4
        ty = py_top + 6 + (wave1 + wave2)
        by = ty + flag_h
        flag_top_pts.append((wx, ty))
        flag_bot_pts.append((wx, by))

    flag_poly = flag_top_pts + list(reversed(flag_bot_pts))
    draw.polygon(flag_poly, fill=(245, 245, 250), outline=(190, 195, 205), width=1)

    for step in range(15, flag_len - 10, 25):
        wx = px + 2 + step
        w1 = math.sin((frame_idx * 0.28) + (step * 0.05)) * 8
        w2 = math.cos((frame_idx * 0.17) + (step * 0.07)) * 4
        ty = py_top + 6 + (w1 + w2)
        draw.line([(wx, ty + 5), (wx + 8, ty + flag_h - 5)], fill=(215, 220, 230), width=3)

    # Abandoned helmet
    draw.ellipse([px - 45, py_bot - 12, px - 25, py_bot + 4], fill=(55, 60, 52), outline=(30, 35, 28))

    # Top HUD Banner
    draw.rectangle([0, 0, w, 38], fill=(18, 18, 22))
    draw.line([(0, 38), (w, 38)], fill=(160, 165, 175), width=2)
    draw.text((15, 11), "***", fill=(255, 255, 255), font=font_hud)
    draw.text((40, 11), f"WAR CONCLUDED: {loser_name.upper()} SURRENDERS TO {winner_name.upper()}", fill=(255, 255, 255), font=font_hud)
    if reparations > 0:
        draw.text((w - 15, 12), f"+{reparations:,} MEDALS", fill=(234, 179, 8), font=font_tag, anchor="rt")

    return im

def render_treaty_scene_frame(
    frame_idx: int,
    total_frames: int,
    country_a: str,
    country_b: str,
    alliance_name: str = "MUTUAL ALLIANCE"
) -> Image.Image:
    """Scene 2: Radiant sunrise over open ocean waves, continuous maritime container convoy voyage."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (15, 25, 45))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_tag = _get_font_bold(10)

    # Sunrise Sky Gradient
    for y in range(195):
        frac = y / 195.0
        draw.line([(0, y), (w, y)], fill=(int(220 + frac * 35), int(90 + frac * 120), int(70 + frac * 60)))

    # Rising Sun & Corona
    sx, sy = 380, 195
    for rad, col in [(90, (255, 240, 180)), (65, (255, 245, 200)), (42, (255, 255, 240))]:
        draw.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=col)

    # Gliding Seabirds across dawn sky
    for b_idx in range(4):
        bx = 40 + b_idx * 140 + frame_idx * 3.2
        by = 65 + b_idx * 18 + math.sin(frame_idx * 0.25 + b_idx) * 6
        flap = math.sin(frame_idx * 0.5 + b_idx) * 4
        if -20 <= bx <= w + 20:
            draw.line([(bx - 8, by - flap), (bx, by)], fill=(255, 255, 255), width=2)
            draw.line([(bx, by), (bx + 8, by - flap)], fill=(255, 255, 255), width=2)

    # Ocean Horizon & Water
    for y in range(195, 360):
        frac = (y - 195) / 165.0
        draw.line([(0, y), (w, y)], fill=(int(12 - frac * 4), int(55 - frac * 20), int(115 - frac * 35)))

    # Sunlight reflection on water
    for y in range(195, 360, 4):
        ref_w = int(25 + (y - 195) * 0.8)
        draw.line([(sx - ref_w, y), (sx + ref_w, y)], fill=(255, 240, 160), width=1)

    # Rolling Ocean Waves
    for wy in range(215, 360, 18):
        wave_pts = []
        for wx in range(0, w + 10, 15):
            w_disp = math.sin(frame_idx * 0.25 + wx * 0.04 + wy * 0.1) * 4
            wave_pts.append((wx, wy + w_disp))
        draw.line(wave_pts, fill=(56, 189, 248), width=2)
        for wx, wdisp_y in wave_pts[::3]:
            if (wx + wy) % 5 == 0:
                draw.ellipse([wx - 3, wdisp_y - 2, wx + 5, wdisp_y + 2], fill=(255, 255, 255))

    # Continuous Maritime Voyage (No modulo wrapping)
    ship_x = -160 + frame_idx * 2.6
    ship_y = 280
    hw, hh = 220, 36

    if -240 <= ship_x <= w + 240:
        draw.polygon([
            (ship_x - hw//2, ship_y),
            (ship_x + hw//2 - 25, ship_y),
            (ship_x + hw//2 + 20, ship_y - hh),
            (ship_x - hw//2, ship_y - hh)
        ], fill=(185, 28, 28), outline=(130, 15, 15), width=2)
        draw.line([(ship_x - hw//2, ship_y - 6), (ship_x + hw//2, ship_y - 6)], fill=(30, 41, 59), width=4)

        cont_colors = [(37, 99, 235), (22, 163, 74), (202, 138, 4), (220, 38, 38), (147, 51, 234)]
        stack_x_start = ship_x - hw//2 + 25
        for c_col_idx in range(6):
            cx = stack_x_start + c_col_idx * 22
            for c_tier in range(3):
                cy = ship_y - hh - (c_tier + 1) * 14
                col = cont_colors[(c_col_idx + c_tier * 2) % len(cont_colors)]
                draw.rectangle([cx, cy, cx + 20, cy + 12], fill=col, outline=(30, 30, 30), width=1)

        bx = ship_x - hw//2 + 10
        by = ship_y - hh - 52
        draw.rectangle([bx, by, bx + 22, by + 52], fill=(245, 245, 250), outline=(180, 180, 190), width=1)
        draw.rectangle([bx + 4, by + 8, bx + 18, by + 16], fill=(30, 41, 59))
        draw.line([(bx + 11, by), (bx + 11, by - 14)], fill=(120, 120, 130), width=2)
        draw.line([(bx + 5, by - 10), (bx + 17, by - 10)], fill=(120, 120, 130), width=2)

        bow_x = ship_x + hw//2 + 18
        bow_y = ship_y - 4
        for sp_idx in range(8):
            sp_x = bow_x + sp_idx * 4 + math.sin(frame_idx * 0.4 + sp_idx) * 4
            sp_y = bow_y - (sp_idx % 3) * 3
            draw.ellipse([sp_x - 3, sp_y - 3, sp_x + 5, sp_y + 3], fill=(255, 255, 255))
        draw.line([(ship_x - hw//2 - 40, ship_y), (ship_x - hw//2, ship_y)], fill=(240, 250, 255), width=3)

    # Naval Escort Cutter
    esc_x = ship_x + 210
    esc_y = 235
    if -100 <= esc_x <= w + 100:
        draw.polygon([(esc_x - 45, esc_y), (esc_x + 35, esc_y), (esc_x + 50, esc_y - 14), (esc_x - 45, esc_y - 14)], fill=(71, 85, 105))
        draw.rectangle([esc_x - 15, esc_y - 26, esc_x + 5, esc_y - 14], fill=(203, 213, 225))
        draw.line([(esc_x + 50, esc_y - 2), (esc_x + 65, esc_y - 2)], fill=(255, 255, 255), width=2)

    # Top HUD Banner
    draw.rectangle([0, 0, w, 38], fill=(15, 23, 42))
    draw.line([(0, 38), (w, 38)], fill=(14, 165, 233), width=2)
    draw.text((15, 11), "***", fill=(255, 255, 255), font=font_hud)
    draw.text((40, 11), f"SOVEREIGN ALLIANCE: {country_a.upper()} + {country_b.upper()}", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), f"[{alliance_name.upper()}]", fill=(56, 189, 248), font=font_tag, anchor="rt")

    return im

def render_ruler_scene_frame(
    frame_idx: int,
    total_frames: int,
    country_name: str,
    ruler_name: str
) -> Image.Image:
    """Scene 2: Imperial throne room with velvet carpet, golden pillars, and royal crown."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (20, 15, 30))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_tag = _get_font_bold(10)

    for y in range(250):
        frac = y / 250.0
        draw.line([(0, y), (w, y)], fill=(int(45 + frac * 45), int(15 + frac * 10), int(25 + frac * 15)))

    for px in [60, 160, 480, 580]:
        draw.rectangle([px - 14, 38, px + 14, 250], fill=(180, 140, 50), outline=(234, 179, 8), width=2)
        draw.rectangle([px - 20, 38, px + 20, 52], fill=(217, 119, 6))
        draw.rectangle([px - 20, 236, px + 20, 250], fill=(217, 119, 6))

    for y in range(250, 360):
        frac = (y - 250) / 110.0
        draw.line([(0, y), (w, y)], fill=(int(80 - frac * 40), int(15 - frac * 5), int(20 - frac * 10)))

    draw.polygon([(260, 360), (380, 360), (350, 250), (290, 250)], fill=(185, 28, 28), outline=(234, 179, 8), width=2)

    tx, ty = 320, 220
    draw.polygon([(tx - 35, ty + 30), (tx - 40, ty - 65), (tx, ty - 90), (tx + 40, ty - 65), (tx + 35, ty + 30)], fill=(202, 138, 4), outline=(245, 158, 11), width=3)
    draw.rectangle([tx - 26, ty - 45, tx + 26, ty + 10], fill=(153, 27, 27))

    crown_y = ty - 40 + math.sin(frame_idx * 0.25) * 4
    draw.polygon([(tx - 20, crown_y), (tx - 24, crown_y - 18), (tx - 10, crown_y - 8), (tx, crown_y - 22), (tx + 10, crown_y - 8), (tx + 24, crown_y - 18), (tx + 20, crown_y)], fill=(234, 179, 8), outline=(255, 235, 120))
    for jx in [tx - 16, tx, tx + 16]:
        draw.ellipse([jx - 2, crown_y - 4, jx + 2, crown_y], fill=(220, 38, 38))

    for d_idx in range(25):
        dx = (d_idx * 31 + frame_idx * 1.8) % w
        dy = 240 - ((d_idx * 17 + frame_idx * 2.2) % 200)
        draw.ellipse([dx, dy, dx + 2, dy + 2], fill=(255, 230, 100))

    draw.rectangle([0, 0, w, 38], fill=(18, 12, 28))
    draw.line([(0, 38), (w, 38)], fill=(234, 179, 8), width=2)
    draw.text((15, 11), "***", fill=(255, 255, 255), font=font_hud)
    draw.text((40, 11), f"SOVEREIGN CORONATION: {ruler_name.upper()} ACCEDES TO {country_name.upper()}", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), "[SUPREME SOVEREIGN]", fill=(234, 179, 8), font=font_tag, anchor="rt")

    return im

def render_fallen_scene_frame(
    frame_idx: int,
    total_frames: int,
    country_name: str,
    conqueror_name: str
) -> Image.Image:
    """Scene 2: Conquered capital ruins, fallen flag, and emergency red strobe."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (25, 12, 14))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_tag = _get_font_bold(10)

    for y in range(230):
        frac = y / 230.0
        draw.line([(0, y), (w, y)], fill=(int(25 + frac * 120), int(10 + frac * 20), int(12 + frac * 15)))

    draw.polygon([(80, 240), (140, 150), (170, 240)], fill=(35, 20, 22))
    draw.polygon([(260, 240), (320, 110), (380, 240)], fill=(45, 25, 28))
    draw.polygon([(460, 240), (510, 160), (550, 240)], fill=(35, 20, 22))

    draw.line([(310, 240), (390, 290)], fill=(120, 120, 130), width=3)
    draw.polygon([(360, 270), (410, 260), (430, 305), (380, 295)], fill=(185, 28, 28), outline=(120, 15, 15))

    strobe = (255, 30, 30) if (frame_idx % 6 < 3) else (120, 10, 10)
    draw.rectangle([0, 38, w, 44], fill=strobe)

    for y in range(230, 360):
        frac = (y - 230) / 130.0
        draw.line([(0, y), (w, y)], fill=(int(45 - frac * 25), int(18 - frac * 10), int(18 - frac * 10)))

    draw.rectangle([0, 0, w, 38], fill=(20, 10, 12))
    draw.line([(0, 38), (w, 38)], fill=(220, 38, 38), width=2)
    draw.text((15, 11), "***", fill=(255, 255, 255), font=font_hud)
    draw.text((40, 11), f"SOVEREIGNTY EXTINGUISHED: {country_name.upper()} FALLEN TO {conqueror_name.upper()}", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), "[ANNEXED]", fill=(239, 68, 68), font=font_tag, anchor="rt")

    return im

def render_commander_scene_frame(
    frame_idx: int,
    total_frames: int,
    country_name: str,
    commander_name: str
) -> Image.Image:
    """Scene 2: Strategic war room map table with rotating radar sweep beam and tactical markers."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (10, 15, 24))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_tag = _get_font_bold(10)

    for x in range(0, w, 32):
        draw.line([(x, 38), (x, h)], fill=(15, 25, 40), width=1)
    for y in range(38, h, 32):
        draw.line([(0, y), (w, y)], fill=(15, 25, 40), width=1)

    rx, ry, rad = 320, 200, 110
    draw.ellipse([rx - rad, ry - rad, rx + rad, ry + rad], outline=(16, 185, 129), width=2)
    draw.ellipse([rx - rad//2, ry - rad//2, rx + rad//2, ry + rad//2], outline=(10, 120, 80), width=1)
    draw.line([(rx - rad, ry), (rx + rad, ry)], fill=(10, 120, 80), width=1)
    draw.line([(rx, ry - rad), (rx, ry + rad)], fill=(10, 120, 80), width=1)

    sweep_ang = frame_idx * 0.12
    beam_x = rx + math.cos(sweep_ang) * rad
    beam_y = ry + math.sin(sweep_ang) * rad
    draw.line([(rx, ry), (beam_x, beam_y)], fill=(52, 211, 153), width=3)

    for bx, by in [(rx + 45, ry - 35), (rx - 60, ry + 25), (rx + 20, ry + 60)]:
        draw.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=(239, 68, 68))
        draw.ellipse([bx - 7, by - 7, bx + 7, by + 7], outline=(248, 113, 113), width=1)

    draw.rectangle([0, 0, w, 38], fill=(15, 23, 42))
    draw.line([(0, 38), (w, 38)], fill=(16, 185, 129), width=2)
    draw.text((15, 11), "***", fill=(255, 255, 255), font=font_hud)
    draw.text((40, 11), f"WAR ROOM HIGH COMMAND: {commander_name.upper()} APPOINTED FOR {country_name.upper()}", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), "[SUPREME COMMANDER]", fill=(52, 211, 153), font=font_tag, anchor="rt")

    return im

def render_martial_law_scene_frame(
    frame_idx: int,
    total_frames: int,
    country_name: str
) -> Image.Image:
    """Scene 2: Armored military riot control convoy with tanks, flashing red/blue strobe sirens, searchlight, and riot shields."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (12, 16, 24))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_sub = _get_font(11)
    font_tag = _get_font_bold(10)

    # 1. Dark stormy urban night sky
    for y in range(195):
        frac = y / 195.0
        r = int(10 + frac * 22)
        g = int(14 + frac * 24)
        b = int(24 + frac * 32)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 2. Silhouetted skyscrapers
    buildings = [
        (10, 80, 55, 195),
        (60, 50, 75, 195),
        (130, 95, 60, 195),
        (185, 40, 80, 195),
        (260, 70, 70, 195),
        (325, 45, 85, 195),
        (405, 85, 65, 195),
        (465, 30, 90, 195),
        (550, 65, 80, 195),
    ]
    for bx, by, bw, bh in buildings:
        draw.rectangle([bx, by, bx + bw, bh], fill=(22, 28, 42), outline=(32, 40, 58))
        for wx in range(bx + 6, bx + bw - 6, 12):
            for wy in range(by + 10, bh - 10, 16):
                seed = (wx * 17 + wy * 31) % 11
                if seed in (0, 1):
                    draw.rectangle([wx, wy, wx + 6, wy + 8], fill=(245, 205, 95))
                elif seed == 2:
                    draw.rectangle([wx, wy, wx + 6, wy + 8], fill=(96, 165, 250))
                else:
                    draw.rectangle([wx, wy, wx + 6, wy + 8], fill=(30, 38, 55))

    # 3. Oscillating military searchlight beam from rooftop
    spot_orig = (510, 32)
    sweep_ang = math.sin(frame_idx * 0.12) * 0.45 - 0.3
    tgt_x = spot_orig[0] + math.sin(sweep_ang) * 290
    tgt_y = 310
    for i in range(-25, 26, 3):
        frac = 1.0 - abs(i) / 25.0
        c_val = int(45 + frac * 85)
        draw.line([spot_orig, (tgt_x + i, tgt_y)], fill=(c_val, c_val, int(c_val * 0.85)), width=2)

    # 4. Asphalt roadway & perspective lines
    for y in range(195, h):
        frac = (y - 195) / (h - 195)
        gr = int(28 + frac * 14)
        gg = int(32 + frac * 14)
        gb = int(38 + frac * 14)
        draw.line([(0, y), (w, y)], fill=(gr, gg, gb))

    # Road lane markings
    lane_t = (frame_idx * 3) % 40
    for offset in range(-40, w + 80, 70):
        lx = offset - lane_t
        draw.line([(lx, 265), (lx + 35, 265)], fill=(120, 125, 135), width=3)

    # 5. Barricades on left & right flank with hazard stripes
    for bar_x, bar_y in [(30, 240), (530, 240)]:
        draw.rectangle([bar_x, bar_y, bar_x + 80, bar_y + 35], fill=(35, 35, 40), outline=(80, 80, 90), width=2)
        for s in range(bar_x, bar_x + 80, 14):
            draw.line([(s, bar_y + 35), (s + 12, bar_y)], fill=(234, 179, 8), width=4)
        draw.line([(bar_x + 10, bar_y + 35), (bar_x + 5, bar_y + 55)], fill=(100, 100, 110), width=3)
        draw.line([(bar_x + 70, bar_y + 35), (bar_x + 75, bar_y + 55)], fill=(100, 100, 110), width=3)

    # 6. Heavy Armored Personnel Carrier / Tank (Patrolling Center-Left)
    apc_x = 200 + int(math.sin(frame_idx * 0.1) * 6)
    apc_y = 205 + int(math.sin(frame_idx * 0.8) * 1.5)

    # Tank shadow
    draw.ellipse([apc_x - 10, apc_y + 60, apc_x + 230, apc_y + 82], fill=(15, 18, 22))

    # Headlight Beams (casting bright light forward onto asphalt)
    h_beam = [(apc_x + 200, apc_y + 40), (w, apc_y + 15), (w, apc_y + 115), (apc_x + 200, apc_y + 52)]
    draw.polygon(h_beam, fill=(55, 55, 45))
    h_beam_core = [(apc_x + 200, apc_y + 42), (w, apc_y + 35), (w, apc_y + 90), (apc_x + 200, apc_y + 48)]
    draw.polygon(h_beam_core, fill=(90, 88, 65))

    # Treads
    draw.rectangle([apc_x + 10, apc_y + 45, apc_x + 200, apc_y + 72], fill=(30, 32, 36), outline=(60, 65, 75), width=2)
    wheel_rot = (frame_idx * 0.3) % (math.pi * 2)
    for wx in range(apc_x + 28, apc_x + 195, 34):
        draw.ellipse([wx - 12, apc_y + 48, wx + 12, apc_y + 70], fill=(45, 50, 58), outline=(85, 90, 100), width=2)
        draw.ellipse([wx - 4, apc_y + 55, wx + 4, apc_y + 63], fill=(20, 22, 25))
        sx = wx + math.cos(wheel_rot) * 8
        sy = apc_y + 59 + math.sin(wheel_rot) * 8
        draw.line([(wx, apc_y + 59), (sx, sy)], fill=(120, 130, 145), width=2)

    # Hull (Sloped Armored Steel)
    hull_pts = [
        (apc_x + 5, apc_y + 46),
        (apc_x + 35, apc_y + 18),
        (apc_x + 185, apc_y + 18),
        (apc_x + 215, apc_y + 46)
    ]
    draw.polygon(hull_pts, fill=(55, 68, 62), outline=(75, 90, 82), width=2)
    draw.line([(apc_x + 75, apc_y + 18), (apc_x + 85, apc_y + 46)], fill=(40, 50, 45), width=2)
    draw.line([(apc_x + 145, apc_y + 18), (apc_x + 155, apc_y + 46)], fill=(40, 50, 45), width=2)

    # Turret & Heavy Suppression Cannon
    turret_pts = [(apc_x + 65, apc_y + 18), (apc_x + 80, apc_y - 8), (apc_x + 145, apc_y - 8), (apc_x + 155, apc_y + 18)]
    draw.polygon(turret_pts, fill=(65, 80, 74), outline=(85, 102, 95), width=2)
    draw.rectangle([apc_x + 145, apc_y - 2, apc_x + 235, apc_y + 8], fill=(45, 52, 48), outline=(70, 80, 75))
    draw.rectangle([apc_x + 230, apc_y - 5, apc_x + 242, apc_y + 11], fill=(30, 35, 32))

    # 7. Flashing Police & Military Strobe Light on Turret Roof!
    strobe_state = (frame_idx // 3) % 4
    siren_x, siren_y = apc_x + 112, apc_y - 12
    draw.rectangle([siren_x - 12, siren_y, siren_x + 12, siren_y + 5], fill=(30, 32, 38))

    if strobe_state in (0, 1):
        # Bright Red Flash
        draw.ellipse([siren_x - 35, siren_y - 30, siren_x + 35, siren_y + 25], fill=(80, 15, 15))
        draw.ellipse([siren_x - 18, siren_y - 18, siren_x + 18, siren_y + 12], fill=(220, 30, 30))
        draw.ellipse([siren_x - 8, siren_y - 10, siren_x + 8, siren_y + 4], fill=(255, 230, 230))
        draw.ellipse([apc_x + 60, apc_y + 70, apc_x + 170, apc_y + 90], fill=(60, 20, 20))
    else:
        # Bright Blue Flash
        draw.ellipse([siren_x - 35, siren_y - 30, siren_x + 35, siren_y + 25], fill=(15, 30, 80))
        draw.ellipse([siren_x - 18, siren_y - 18, siren_x + 18, siren_y + 12], fill=(30, 120, 255))
        draw.ellipse([siren_x - 8, siren_y - 10, siren_x + 8, siren_y + 4], fill=(230, 240, 255))
        draw.ellipse([apc_x + 60, apc_y + 70, apc_x + 170, apc_y + 90], fill=(20, 30, 65))

    # 8. Tactical Infantry Riot Squad Advancing Behind APC
    for s_idx, (sx_off, sy_off) in enumerate([(apc_x - 65, apc_y + 15), (apc_x - 110, apc_y + 25)]):
        soldier_x = sx_off + int(math.sin(frame_idx * 0.15 + s_idx) * 4)
        soldier_y = sy_off
        leg_step = math.sin(frame_idx * 0.35 + s_idx * 1.5) * 6
        draw.line([(soldier_x - 4, soldier_y + 35), (soldier_x - 8 + leg_step, soldier_y + 55)], fill=(30, 35, 42), width=5)
        draw.line([(soldier_x + 4, soldier_y + 35), (soldier_x + 8 - leg_step, soldier_y + 55)], fill=(25, 30, 38), width=5)
        draw.rectangle([soldier_x - 10, soldier_y + 12, soldier_x + 10, soldier_y + 36], fill=(45, 52, 60), outline=(65, 75, 88), width=2)
        draw.ellipse([soldier_x - 8, soldier_y - 4, soldier_x + 8, soldier_y + 12], fill=(35, 40, 48))
        draw.rectangle([soldier_x - 5, soldier_y + 2, soldier_x + 7, soldier_y + 6], fill=(16, 185, 129))
        sh_x = soldier_x + 10
        draw.rectangle([sh_x, soldier_y + 6, sh_x + 7, soldier_y + 48], fill=(180, 200, 220), outline=(220, 235, 250), width=2)
        draw.rectangle([sh_x + 1, soldier_y + 12, sh_x + 6, soldier_y + 22], fill=(40, 50, 65))

    # 9. Top Tactical HUD Bar
    draw.rectangle([0, 0, w, 38], fill=(15, 23, 42))
    draw.line([(0, 38), (w, 38)], fill=(239, 68, 68), width=2)
    alert_dot_col = (239, 68, 68) if (frame_idx // 3) % 2 == 0 else (255, 255, 255)
    draw.ellipse([14, 13, 26, 25], fill=alert_dot_col)
    clean_title = f"STATE OF EMERGENCY // MARTIAL LAW: {country_name.upper()[:24]}"
    draw.text((36, 11), clean_title, fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), "[MILITARY CURFEW]", fill=(248, 113, 113), font=font_tag, anchor="rt")

    # 10. Bottom Alert HUD Ribbon
    draw.rectangle([0, h - 28, w, h], fill=(20, 24, 33))
    draw.line([(0, h - 28), (w, h - 28)], fill=(185, 28, 28), width=1)
    draw.text((15, h - 22), "🚨 ARMED DIVISIONS DEPLOYED // STRICT CURFEW ACTIVE // CIVIL UNREST SUPPRESSED", fill=(252, 165, 165), font=font_sub)

    return im

# === Frame Generation Pipelines (Long, unbroken animations, memory-streaming) =

def generate_war_declared_frames(attacker_name: str, defender_name: str, scale: str, domain: str = "TERRESTRIAL", total_frames: int = 80):
    c_atk = clean_tactical_text(attacker_name)
    c_dfn = clean_tactical_text(defender_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(i, parchment_count, "DECLARATION OF WAR", c_atk, c_dfn, f"Operation {scale.upper()} Mobilization", "DECREED", (185, 28, 28))
    for i in range(action_count):
        yield render_war_scene_frame(i, action_count, c_atk, c_dfn, scale, domain)

def create_war_declared_frames(attacker_name: str, defender_name: str, scale: str, domain: str = "TERRESTRIAL", total_frames: int = 80) -> list[Image.Image]:
    return list(generate_war_declared_frames(attacker_name, defender_name, scale, domain, total_frames))

def create_war_declared_gif(attacker_name: str, attacker_flag: str, defender_name: str, defender_flag: str, scale: str = "border") -> io.BytesIO:
    frames = create_war_declared_frames(attacker_name, defender_name, scale, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_war_declared_media(attacker_name: str, defender_name: str, scale: str, domain: str = "TERRESTRIAL", audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_war_declared_frames(attacker_name, defender_name, scale, domain, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_war_declared_gif(attacker_name, "⚔️", defender_name, "🛡️", scale)
    return gif_buf, mp4_buf

def generate_war_ended_frames(winner_name: str, loser_name: str, reason: str = "VICTORY", reparations: int = 0, total_frames: int = 80):
    c_win = clean_tactical_text(winner_name)
    c_los = clean_tactical_text(loser_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(i, parchment_count, "INSTRUMENT OF SURRENDER", c_win, c_los, "Unconditional Capitulation & Truce", "SURRENDERED", (100, 110, 125))
    for i in range(action_count):
        yield render_surrender_scene_frame(i, action_count, c_win, c_los, reparations)

def create_war_ended_frames(winner_name: str, loser_name: str, reason: str = "VICTORY", reparations: int = 0, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_war_ended_frames(winner_name, loser_name, reason, reparations, total_frames))

def create_war_ended_gif(winner_name: str, winner_flag: str, loser_name: str, loser_flag: str, reason: str = "VICTORY", reparations: int = 0) -> io.BytesIO:
    frames = create_war_ended_frames(winner_name, loser_name, reason, reparations, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_war_ended_media(winner_name: str, loser_name: str, reason: str = "VICTORY", reparations: int = 0, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_war_ended_frames(winner_name, loser_name, reason, reparations, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_war_ended_gif(winner_name, "👑", loser_name, "🏳️", reason, reparations)
    return gif_buf, mp4_buf

def generate_country_allied_frames(country_a_name: str, country_b_name: str, alliance_name: str, total_frames: int = 80):
    c_a = clean_tactical_text(country_a_name)
    c_b = clean_tactical_text(country_b_name)
    c_al = clean_tactical_text(alliance_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(i, parchment_count, "TREATY OF ALLIANCE", c_a, c_b, f"{c_al} Mutual Security", "ALLIED", (14, 165, 233))
    for i in range(action_count):
        yield render_treaty_scene_frame(i, action_count, c_a, c_b, c_al)

def create_country_allied_frames(country_a_name: str, country_b_name: str, alliance_name: str, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_country_allied_frames(country_a_name, country_b_name, alliance_name, total_frames))

def create_country_allied_gif(country_a_name: str, country_a_flag: str, country_b_name: str, country_b_flag: str, alliance_name: str) -> io.BytesIO:
    frames = create_country_allied_frames(country_a_name, country_b_name, alliance_name, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_country_allied_media(country_a_name: str, country_a_flag: str, country_b_name: str, country_b_flag: str, alliance_name: str, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_country_allied_frames(country_a_name, country_b_name, alliance_name, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_country_allied_gif(country_a_name, country_a_flag, country_b_name, country_b_flag, alliance_name)
    return gif_buf, mp4_buf

def generate_new_ruler_frames(country_name: str, ruler_name: str, total_frames: int = 80):
    c_c = clean_tactical_text(country_name)
    c_r = clean_tactical_text(ruler_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(i, parchment_count, "CORONATION DECREE", c_c, c_r, "Supreme Sovereign Authority", "IMPERIAL", (202, 138, 4))
    for i in range(action_count):
        yield render_ruler_scene_frame(i, action_count, c_c, c_r)

def create_new_ruler_frames(country_name: str, ruler_name: str, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_new_ruler_frames(country_name, ruler_name, total_frames))

def create_new_ruler_gif(country_name: str, country_flag: str, ruler_name: str) -> io.BytesIO:
    frames = create_new_ruler_frames(country_name, ruler_name, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_new_ruler_media(country_name: str, country_flag: str, ruler_name: str, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_new_ruler_frames(country_name, ruler_name, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_new_ruler_gif(country_name, country_flag, ruler_name)
    return gif_buf, mp4_buf

def generate_country_fallen_frames(loser_name: str, winner_name: str, total_frames: int = 80):
    c_los = clean_tactical_text(loser_name)
    c_win = clean_tactical_text(winner_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(i, parchment_count, "DECREE OF ANNEXATION", c_win, c_los, "National Sovereignty Extinguished", "ANNEXED", (153, 27, 27))
    for i in range(action_count):
        yield render_fallen_scene_frame(i, action_count, c_los, c_win)

def create_country_fallen_frames(loser_name: str, winner_name: str, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_country_fallen_frames(loser_name, winner_name, total_frames))

def create_country_fallen_gif(country_name: str, country_flag: str, conqueror_name: str, conqueror_flag: str) -> io.BytesIO:
    frames = create_country_fallen_frames(country_name, conqueror_name, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_country_fallen_media(loser_name: str, winner_name: str, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_country_fallen_frames(loser_name, winner_name, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_country_fallen_gif(loser_name, "🏳️", winner_name, "👑")
    return gif_buf, mp4_buf

def generate_new_commander_frames(country_name: str, commander_name: str, total_frames: int = 80):
    c_c = clean_tactical_text(country_name)
    c_m = clean_tactical_text(commander_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(i, parchment_count, "MILITARY COMMISSION", c_c, c_m, "Armed Forces High Command", "APPOINTED", (71, 85, 105))
    for i in range(action_count):
        yield render_commander_scene_frame(i, action_count, c_c, c_m)

def create_new_commander_frames(country_name: str, commander_name: str, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_new_commander_frames(country_name, commander_name, total_frames))

def create_new_commander_gif(country_name: str, country_flag: str, commander_name: str) -> io.BytesIO:
    frames = create_new_commander_frames(country_name, commander_name, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_new_commander_media(country_name: str, country_flag: str, commander_name: str, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_new_commander_frames(country_name, commander_name, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_new_commander_gif(country_name, country_flag, commander_name)
    return gif_buf, mp4_buf

def generate_martial_law_frames(country_name: str, total_frames: int = 80):
    c_name = clean_tactical_text(country_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(
            i, parchment_count,
            "MARTIAL LAW DECREE",
            c_name,
            "CIVIL RIOT & UNREST SECTORS",
            "ARMED MILITARY CURFEW ENFORCEMENT",
            "ENFORCED",
            (220, 38, 38)
        )
    for i in range(action_count):
        yield render_martial_law_scene_frame(i, action_count, c_name)

def create_martial_law_frames(country_name: str, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_martial_law_frames(country_name, total_frames))

def create_martial_law_gif(country_name: str, country_flag: str) -> io.BytesIO:
    frames = create_martial_law_frames(country_name, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_martial_law_media(country_name: str, country_flag: str, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_martial_law_frames(country_name, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_martial_law_gif(country_name, country_flag)
    return gif_buf, mp4_buf

# === Spoken Voice Narration (TTS) & Deep Male Broadcaster DSP Engine ==========

def clean_for_speech(text: str) -> str:
    """Strip markdown, discord mentions, URLs and special symbols for clean vocal speech."""
    text = re.sub(r'<@&?[0-9]+>', '', text)
    text = re.sub(r'<#[0-9]+>', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[*_`~#\[\]\(\)>|]', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return ' '.join(text.split())

def transform_to_deep_male_voice(raw_audio_buf: io.BytesIO) -> io.BytesIO:
    """Transform speech audio into a deep, resonant, authoritative male military news anchor voice using FFmpeg DSP."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if not exe or not os.path.exists(exe):
            return raw_audio_buf
    except Exception:
        return raw_audio_buf

    raw_audio_buf.seek(0)
    data = raw_audio_buf.read()
    if not data or len(data) < 200:
        return raw_audio_buf

    td = tempfile.mkdtemp()
    try:
        in_path = os.path.join(td, "in.mp3")
        out_path = os.path.join(td, "out.mp3")
        with open(in_path, "wb") as f:
            f.write(data)

        # Audio DSP filter chain for deep authoritative male broadcaster voice:
        # 1. asetrate: pitch shifts down by ~23% into deep masculine baritone range (0.77x)
        # 2. aresample: re-establishes clean standard 48kHz sampling rate
        # 3. atempo: compensates speed (1 / 0.77 ~ 1.298x) so speech tempo is natural and articulate
        # 4. equalizer at 120Hz (+8dB): adds deep chest resonance and sub-bass weight
        # 5. equalizer at 250Hz (+4dB): warm radio body
        # 6. equalizer at 2800Hz (+3dB): crisp military announcer consonant clarity
        # 7. volume: broadcast normalization
        # 8. aformat: stereo 2-channel layout
        af = (
            "asetrate=24000*0.77,"
            "aresample=48000,"
            "atempo=1.298,"
            "equalizer=f=120:t=q:w=1.2:g=8,"
            "equalizer=f=250:t=q:w=1.2:g=4,"
            "equalizer=f=2800:t=q:w=1.5:g=3,"
            "volume=1.35,"
            "aformat=channel_layouts=stereo"
        )
        cmd = [
            exe, "-y",
            "-i", in_path,
            "-af", af,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            out_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=20)
        if res.returncode == 0 and os.path.exists(out_path):
            with open(out_path, "rb") as f:
                deep_buf = io.BytesIO(f.read())
            deep_buf.seek(0)
            return deep_buf
    except Exception as e:
        print(f"?? Deep male voice transform notice: {e}", flush=True)
    finally:
        shutil.rmtree(td, ignore_errors=True)

    raw_audio_buf.seek(0)
    return raw_audio_buf

def generate_voice_narration(text: str, voice_lang: str = "en") -> io.BytesIO:
    """Generate realistic spoken announcer voice audio (.mp3) for geopolitical events."""
    clean = clean_for_speech(text)
    if not clean:
        clean = "Geopolitical broadcast alert on Virtual Earth."

    buf = io.BytesIO()

    # 1. Attempt gTTS library (British English announcer voice)
    try:
        from gtts import gTTS
        tts = gTTS(text=clean, lang=voice_lang, tld="co.uk")
        tts.write_to_fp(buf)
        buf.seek(0)
        if len(buf.getvalue()) > 500:
            return transform_to_deep_male_voice(buf)
    except Exception:
        buf = io.BytesIO()

    # 2. Fallback to direct Google Translate TTS endpoint via urllib standard library
    try:
        words = clean.split()
        chunks = []
        curr = []
        curr_len = 0
        for w in words:
            if curr_len + len(w) + 1 > 110:
                chunks.append(" ".join(curr))
                curr = [w]
                curr_len = len(w)
            else:
                curr.append(w)
                curr_len += len(w) + 1
        if curr:
            chunks.append(" ".join(curr))

        for c in chunks:
            url = "https://translate.google.com/translate_tts?ie=UTF-8&tl=en-gb&client=tw-ob&q=" + urllib.parse.quote(c)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                buf.write(resp.read())
        buf.seek(0)
        if len(buf.getvalue()) > 500:
            return transform_to_deep_male_voice(buf)
    except Exception:
        buf = io.BytesIO()

    # 3. Last-resort fallback to procedural synth audio if offline
    return generate_tactical_audio("ruler_inauguration")

def generate_ruler_speech(country_name: str, ruler_name: str) -> io.BytesIO:
    clean_c = clean_for_speech(country_name)
    clean_r = clean_for_speech(ruler_name)
    speech = (
        f"Attention all citizens of Virtual Earth. A supreme ruler of {clean_c} has emerged! "
        f"All hail {clean_r}, who has assumed absolute sovereign authority and supreme command "
        f"over the national treasury and armed forces."
    )
    return generate_voice_narration(speech)

def generate_war_speech(attacker_name: str, defender_name: str, scale: str) -> io.BytesIO:
    clean_atk = clean_for_speech(attacker_name)
    clean_dfn = clean_for_speech(defender_name)
    speech = (
        f"Emergency broadcast. Sovereign war has been declared on Virtual Earth! "
        f"{clean_atk} has commenced armed hostilities against {clean_dfn} in an active {scale} campaign. "
        f"Front line combat operations are active. All armed forces mobilize for battle!"
    )
    return generate_voice_narration(speech)

def generate_surrender_speech(winner_name: str, loser_name: str, reparations: int = 0) -> io.BytesIO:
    clean_w = clean_for_speech(winner_name)
    clean_l = clean_for_speech(loser_name)
    speech = (
        f"Official geopolitical dispatch. Armed conflict between {clean_w} and {clean_l} has ended. "
        f"{clean_l} has formally conceded and surrendered! "
        f"{clean_w} claims decisive sovereign victory and {reparations:,} Medals in war reparations."
    )
    return generate_voice_narration(speech)

def generate_victory_speech(winner_name: str, loser_name: str, reparations: int = 0) -> io.BytesIO:
    clean_w = clean_for_speech(winner_name)
    clean_l = clean_for_speech(loser_name)
    speech = (
        f"Front line bulletin. The military campaign between {clean_w} and {clean_l} has concluded. "
        f"{clean_w} has secured decisive victory over {clean_l}, receiving {reparations:,} Medals in war indemnities."
    )
    return generate_voice_narration(speech)

def generate_country_fallen_speech(country_name: str, conqueror_name: str) -> io.BytesIO:
    clean_c = clean_for_speech(country_name)
    clean_w = clean_for_speech(conqueror_name)
    speech = (
        f"Urgent geopolitical warning. The sovereign nation of {clean_c} has fallen! "
        f"Its sovereign capital and borders have been annexed into the imperial dominion of {clean_w}."
    )
    return generate_voice_narration(speech)

def generate_trade_speech(country_a_name: str, country_b_name: str) -> io.BytesIO:
    clean_a = clean_for_speech(country_a_name)
    clean_b = clean_for_speech(country_b_name)
    speech = (
        f"International trade bulletin. A bilateral maritime trade treaty has been officially ratified! "
        f"The sovereign nations of {clean_a} and {clean_b} have established active ocean sealanes. "
        f"Commercial shipping fleets are now in transit, compounding hourly tariff revenues and economic prosperity."
    )
    return generate_voice_narration(speech)

def generate_alliance_speech(country_a_name: str, country_b_name: str, alliance_name: str) -> io.BytesIO:
    clean_a = clean_for_speech(country_a_name)
    clean_b = clean_for_speech(country_b_name)
    clean_al = clean_for_speech(alliance_name)
    speech = (
        f"Diplomatic bulletin. An international strategic alliance has been officially ratified! "
        f"The sovereign nations of {clean_a} and {clean_b} have united under the {clean_al} coalition. "
        f"A mutual defense pact is now active, securing territorial borders and collective armed defense across Virtual Earth."
    )
    return generate_voice_narration(speech)

def generate_commander_speech(country_name: str, commander_name: str) -> io.BytesIO:
    clean_c = clean_for_speech(country_name)
    clean_cm = clean_for_speech(commander_name)
    speech = (
        f"Supreme military command alert. A new commander has taken charge of the armed forces of {clean_c}! "
        f"General {clean_cm} has officially assumed office as Supreme Army Commander and Minister of Defense. "
        f"All armored divisions, air squadrons, and naval fleets are now mobilizing under their direct strategic command."
    )
    return generate_voice_narration(speech)

def generate_martial_law_speech(country_name: str) -> io.BytesIO:
    clean_c = clean_for_speech(country_name)
    speech = (
        f"Attention citizens of {clean_c}. By executive decree of Supreme Sovereign Command, "
        f"an emergency state of martial law has been enacted! Armed military divisions and armored units "
        f"have mobilized across all domestic sectors to crush civil unrest and enforce strict curfews. "
        f"Return to your quarters immediately. Sovereign order is being restored by force."
    )
    return generate_voice_narration(speech)


# ═══════════════════════════════════════════════════════════════════════════════
# ☢️ NUCLEAR ATTACK ANIMATED BROADCAST PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def render_nuclear_strike_scene_frame(
    frame_idx: int,
    total_frames: int,
    attacker_name: str,
    target_name: str
) -> Image.Image:
    """Apocalyptic ICBM launch & thermonuclear fireball mushroom cloud detonation."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (10, 8, 14))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_title = _get_font_bold(16)
    font_sub = _get_font(11)
    font_tag = _get_font_bold(10)

    t = frame_idx / max(1, total_frames - 1)

    # 1. Dark apocalyptic burning sky gradient
    for y in range(240):
        frac = y / 240.0
        r = int(12 + frac * 85)
        g = int(8 + frac * 28)
        b = int(14 + frac * 18)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 2. Silhouetted mountains & defense radar station
    mountains = [
        [(0, 240), (80, 180), (160, 220), (260, 160), (360, 215), (480, 150), (580, 205), (640, 175), (640, 240)]
    ]
    for m in mountains:
        draw.polygon(m, fill=(24, 16, 22))

    # Ground plain
    draw.rectangle([0, 235, w, h], fill=(18, 14, 20))
    for gy in range(240, h, 14):
        draw.line([(0, gy), (w, gy)], fill=(28, 22, 32), width=1)

    if t < 0.45:
        # Phase 1: Silo launch & rocket ascent
        sub_t = t / 0.45
        silo_x, silo_y = 160, 260
        draw.rectangle([silo_x - 35, silo_y - 8, silo_x + 35, silo_y + 12], fill=(45, 45, 55), outline=(90, 90, 110))
        door_slide = int(sub_t * 22)
        draw.rectangle([silo_x - 35 - door_slide, silo_y - 12, silo_x - door_slide, silo_y - 4], fill=(70, 75, 90))
        draw.rectangle([silo_x + door_slide, silo_y - 12, silo_x + 35 + door_slide, silo_y - 4], fill=(70, 75, 90))

        for si in range(8):
            sp_x = silo_x + int(math.sin(si * 1.2 + frame_idx * 0.3) * (20 + si * 6))
            sp_y = silo_y + 2 + int(math.cos(si * 0.9) * 10)
            sp_r = int(12 + si * 4)
            draw.ellipse([sp_x - sp_r, sp_y - sp_r, sp_x + sp_r, sp_y + sp_r], fill=(120, 80, 50), outline=(160, 110, 60))

        missile_progress = sub_t ** 1.3
        mx = silo_x + int(missile_progress * 260)
        my = silo_y - int(missile_progress * 210)

        trail_pts = []
        for step in range(15):
            st_frac = step / 14.0
            tx = silo_x + int((missile_progress * st_frac) * 260) + int(math.sin(step + frame_idx) * 3)
            ty = silo_y - int((missile_progress * st_frac) * 210)
            trail_pts.append((tx, ty))
        if len(trail_pts) > 1:
            draw.line(trail_pts, fill=(245, 158, 11), width=4)
            draw.line(trail_pts, fill=(255, 255, 255), width=2)

        draw.polygon([(mx - 6, my + 8), (mx + 6, my + 8), (mx, my + 26)], fill=(255, 200, 50))
        draw.polygon([(mx - 3, my + 6), (mx + 3, my + 6), (mx, my + 18)], fill=(255, 255, 255))

        draw.rectangle([mx - 4, my - 12, mx + 4, my + 6], fill=(220, 225, 235), outline=(100, 110, 130))
        draw.polygon([(mx - 4, my - 12), (mx + 4, my - 12), (mx, my - 22)], fill=(40, 45, 55))
        draw.polygon([(mx - 4, my + 2), (mx - 9, my + 7), (mx - 4, my + 7)], fill=(80, 85, 95))
        draw.polygon([(mx + 4, my + 2), (mx + 9, my + 7), (mx + 4, my + 7)], fill=(80, 85, 95))

        draw.rectangle([20, 48, 390, 86], fill=(20, 25, 35), outline=(245, 158, 11))
        draw.text((28, 52), f"ICBM LAUNCH SEQUENCE: {attacker_name.upper()}", fill=(255, 255, 255), font=font_hud)
        draw.text((28, 68), f"BOOSTER BURNOUT IN T+{int(sub_t * 60)}s • TARGETING {target_name.upper()}", fill=(245, 158, 11), font=font_sub)
    else:
        # Phase 2: Detonation & mushroom cloud
        det_t = (t - 0.45) / 0.55
        cx, cy = 340, 240

        ring_r = int(det_t * 260)
        draw.ellipse([cx - ring_r, cy - int(ring_r * 0.35), cx + ring_r, cy + int(ring_r * 0.35)], outline=(245, 158, 11), width=2)
        if ring_r > 40:
            draw.ellipse([cx - ring_r + 30, cy - int((ring_r - 30) * 0.35), cx + ring_r - 30, cy + int((ring_r - 30) * 0.35)], outline=(239, 68, 68), width=3)

        stem_h = int(min(1.0, det_t * 1.5) * 150)
        stem_top_y = cy - stem_h
        for sy in range(cy, stem_top_y, -12):
            sw = int(18 + math.sin((sy - stem_top_y) * 0.1) * 8)
            col_r = int(220 + math.sin(sy * 0.2 + frame_idx) * 35)
            col_g = int(120 + math.cos(sy * 0.3) * 30)
            draw.ellipse([cx - sw, sy - 14, cx + sw, sy + 14], fill=(col_r, col_g, 40), outline=(239, 68, 68))

        cap_w = int(35 + det_t * 140)
        cap_h = int(25 + det_t * 70)
        cap_y = stem_top_y - cap_h // 2
        for ci in range(12):
            ang = ci * (2 * math.pi / 12) + frame_idx * 0.05
            puff_x = cx + int(math.cos(ang) * (cap_w * 0.75))
            puff_y = cap_y + int(math.sin(ang) * (cap_h * 0.65))
            pr = int(22 + math.sin(ci + frame_idx * 0.2) * 8)
            draw.ellipse([puff_x - pr, puff_y - pr, puff_x + pr, puff_y + pr], fill=(180, 70, 30), outline=(245, 158, 11))

        core_r = int(25 + math.sin(frame_idx * 0.5) * 8)
        draw.ellipse([cx - cap_w//2, cap_y - cap_h//2, cx + cap_w//2, cap_y + cap_h//2], fill=(255, 180, 50))
        draw.ellipse([cx - core_r, cap_y - core_r//2, cx + core_r, cap_y + core_r//2], fill=(255, 255, 230))

        for di in range(16):
            dx = cx + int(math.sin(di * 1.7 + frame_idx * 0.4) * (cap_w + 30))
            dy = cap_y + int(math.cos(di * 2.3 + frame_idx * 0.3) * (cap_h + 40))
            draw.ellipse([dx - 2, dy - 2, dx + 2, dy + 2], fill=(255, 240, 120))

        draw.rectangle([w//2 - 225, 48, w//2 + 225, 86], fill=(40, 10, 15), outline=(239, 68, 68), width=2)
        draw.text((w//2, 54), "*** THERMONUCLEAR DETONATION CONFIRMED ***", fill=(255, 255, 255), font=font_title, anchor="mt")
        draw.text((w//2, 71), f"TARGET GROUND ZERO: {target_name.upper()} • CATASTROPHIC IMPACT", fill=(252, 165, 165), font=font_sub, anchor="mt")

    # Top cinematic HUD bar
    draw.rectangle([0, 0, w, 38], fill=(15, 10, 15))
    draw.line([(0, 38), (w, 38)], fill=(239, 68, 68), width=2)
    draw.text((15, 11), "[!]", fill=(239, 68, 68), font=font_hud)
    draw.text((38, 11), f"STRATEGIC STRIKE: {attacker_name.upper()} -> {target_name.upper()}", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), "[DEFCON 1: NUCLEAR DETONATION]", fill=(239, 68, 68), font=font_tag, anchor="rt")

    # Bottom ticker bar
    draw.rectangle([0, h - 24, w, h], fill=(10, 8, 12))
    draw.line([(0, h - 24), (w, h - 24)], fill=(245, 158, 11), width=1)
    draw.text((15, h - 18), "HIGH CASUALTIES REPORTED • NATIONAL INFRASTRUCTURE DAMAGED • CIVIL UNREST ERUPTING", fill=(203, 213, 225), font=font_tag)

    return im

def generate_nuclear_strike_frames(attacker_name: str, target_name: str, total_frames: int = 80):
    atk_c = clean_tactical_text(attacker_name)
    tgt_c = clean_tactical_text(target_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(
            i, parchment_count,
            "STRATEGIC NUCLEAR ORDER",
            atk_c,
            tgt_c,
            "TACTICAL ICBM STRIKE AUTHORIZED",
            "WARHEAD DETONATED",
            (220, 38, 38)
        )
    for i in range(action_count):
        yield render_nuclear_strike_scene_frame(i, action_count, atk_c, tgt_c)

def create_nuclear_strike_frames(attacker_name: str, target_name: str, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_nuclear_strike_frames(attacker_name, target_name, total_frames))

def create_nuclear_strike_gif(attacker_name: str, attacker_flag: str, target_name: str, target_flag: str) -> io.BytesIO:
    frames = create_nuclear_strike_frames(attacker_name, target_name, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_nuclear_strike_media(attacker_name: str, attacker_flag: str, target_name: str, target_flag: str, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_nuclear_strike_frames(attacker_name, target_name, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_nuclear_strike_gif(attacker_name, attacker_flag, target_name, target_flag)
    return gif_buf, mp4_buf

def generate_nuclear_strike_speech(attacker_name: str, target_name: str) -> io.BytesIO:
    clean_atk = clean_for_speech(attacker_name)
    clean_tgt = clean_for_speech(target_name)
    speech = (
        f"Attention all sovereign nations. A tactical nuclear strike has been authorized and launched by {clean_atk} "
        f"against {clean_tgt}! Severe structural destruction, radiation fallout, and civilian unrest reported across the target territory. "
        f"All global powers are ordered to maximum defense readiness."
    )
    return generate_voice_narration(speech)


# ═══════════════════════════════════════════════════════════════════════════════
# 🚪 COMMANDER RESIGNATION ANIMATED BROADCAST PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def render_commander_resigned_scene_frame(
    frame_idx: int,
    total_frames: int,
    country_name: str,
    commander_name: str,
    role_title: str = "Supreme Army Commander"
) -> Image.Image:
    """War room briefing table with relinquished commission and sovereign cabinet transition."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (14, 18, 28))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_hero = _get_font_bold(18)
    font_sub = _get_font(12)
    font_tag = _get_font_bold(10)

    for x in range(0, w, 32):
        draw.line([(x, 38), (x, h - 24)], fill=(22, 28, 42), width=1)
    for y in range(38, h - 24, 32):
        draw.line([(0, y), (w, y)], fill=(22, 28, 42), width=1)

    rx, ry, rad = 320, 195, 100
    draw.ellipse([rx - rad, ry - rad, rx + rad, ry + rad], outline=(45, 55, 75), width=2)
    draw.ellipse([rx - rad//2, ry - rad//2, rx + rad//2, ry + rad//2], outline=(35, 45, 65), width=1)
    draw.line([(rx - rad, ry), (rx + rad, ry)], fill=(35, 45, 65), width=1)
    draw.line([(rx, ry - rad), (rx, ry + rad)], fill=(35, 45, 65), width=1)

    pw, ph = 490, 150
    px, py = w//2 - pw//2, 105
    draw.rectangle([px, py, px + pw, py + ph], fill=(18, 24, 38), outline=(239, 68, 68), width=2)
    draw.rectangle([px + 4, py + 4, px + pw - 4, py + ph - 4], outline=(71, 85, 105), width=1)

    draw.text((w//2, py + 18), "RESIGNATION TENDERED // HIGH COMMAND", fill=(248, 113, 113), font=font_hud, anchor="mt")
    draw.text((w//2, py + 46), f"{commander_name.upper()}", fill=(255, 255, 255), font=font_hero, anchor="mt")
    draw.text((w//2, py + 78), f"Stepped down as {role_title} of {country_name}", fill=(148, 163, 184), font=font_sub, anchor="mt")
    draw.text((w//2, py + 106), "Authority & portfolio duties have reverted to the Head of State", fill=(245, 158, 11), font=font_sub, anchor="mt")

    draw.polygon([(px + 10, py + 10), (px + 26, py + 10), (px + 10, py + 26)], fill=(239, 68, 68))
    draw.polygon([(px + pw - 10, py + 10), (px + pw - 26, py + 10), (px + pw - 10, py + 26)], fill=(239, 68, 68))

    draw.rectangle([0, 0, w, 38], fill=(15, 23, 42))
    draw.line([(0, 38), (w, 38)], fill=(239, 68, 68), width=2)
    draw.text((15, 11), "[!]", fill=(239, 68, 68), font=font_hud)
    draw.text((38, 11), f"CABINET DISPATCH: {country_name.upper()} HIGH COMMAND VACANCY", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), "[COMMISSION RELINQUISHED]", fill=(248, 113, 113), font=font_tag, anchor="rt")

    draw.rectangle([0, h - 24, w, h], fill=(10, 14, 22))
    draw.line([(0, h - 24), (w, h - 24)], fill=(71, 85, 105), width=1)
    draw.text((15, h - 18), "MINISTERIAL PORTFOLIO RETURNED TO SOVEREIGN HEAD OF STATE • SUCCESSOR PENDING", fill=(148, 163, 184), font=font_tag)

    return im

def generate_commander_resigned_frames(country_name: str, commander_name: str, role_title: str = "Supreme Army Commander", total_frames: int = 80):
    c_c = clean_tactical_text(country_name)
    c_m = clean_tactical_text(commander_name)
    c_r = clean_tactical_text(role_title)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(
            i, parchment_count,
            "OFFICIAL RESIGNATION DECREE",
            c_c,
            c_m,
            f"Relinquished {c_r} Portfolio",
            "COMMISSION TENDERED",
            (239, 68, 68)
        )
    for i in range(action_count):
        yield render_commander_resigned_scene_frame(i, action_count, c_c, c_m, c_r)

def create_commander_resigned_frames(country_name: str, commander_name: str, role_title: str = "Supreme Army Commander", total_frames: int = 80) -> list[Image.Image]:
    return list(generate_commander_resigned_frames(country_name, commander_name, role_title, total_frames))

def create_commander_resigned_gif(country_name: str, country_flag: str, commander_name: str, role_title: str = "Supreme Army Commander") -> io.BytesIO:
    frames = create_commander_resigned_frames(country_name, commander_name, role_title, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_commander_resigned_media(country_name: str, country_flag: str, commander_name: str, role_title: str = "Supreme Army Commander", audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_commander_resigned_frames(country_name, commander_name, role_title, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_commander_resigned_gif(country_name, country_flag, commander_name, role_title)
    return gif_buf, mp4_buf

def generate_commander_resigned_speech(country_name: str, commander_name: str, role_title: str = "Supreme Army Commander") -> io.BytesIO:
    clean_c = clean_for_speech(country_name)
    clean_cm = clean_for_speech(commander_name)
    clean_rt = clean_for_speech(role_title)
    speech = (
        f"Official sovereign announcement. {clean_cm} has formally tendered their resignation and stepped down as {clean_rt} of {clean_c}. "
        f"High command and ministerial portfolio duties have temporarily reverted to the Head of State."
    )
    return generate_voice_narration(speech)


# ═══════════════════════════════════════════════════════════════════════════════
# 🔥 POPULAR REVOLUTION / PROTEST OVERTHROW ANIMATED PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def render_revolution_scene_frame(
    frame_idx: int,
    total_frames: int,
    country_name: str,
    ousted_ruler_name: str
) -> Image.Image:
    """Presidential Palace breached by rebel crowds, burning barricades, toppled regime."""
    w, h = 640, 360
    im = Image.new("RGB", (w, h), (18, 10, 10))
    draw = ImageDraw.Draw(im)

    font_hud = _get_font_bold(13)
    font_hero = _get_font_bold(16)
    font_sub = _get_font(11)
    font_tag = _get_font_bold(10)

    # 1. Dark stormy fiery sky gradient
    for y in range(210):
        frac = y / 210.0
        r = int(24 + frac * 80)
        g = int(12 + frac * 28)
        b = int(10 + frac * 12)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 2. Silhouetted Presidential Palace with dome & columns
    palace_pts = [
        (220, 210), (220, 130), (250, 130), (250, 95), (290, 95),
        (320, 60), (350, 95), (390, 95), (390, 130), (420, 130), (420, 210)
    ]
    draw.polygon(palace_pts, fill=(28, 20, 22))
    for cx in range(260, 385, 20):
        draw.rectangle([cx, 130, cx + 8, 210], fill=(42, 30, 34))

    # Broken ornate gates bent open
    draw.line([(180, 210), (210, 150)], fill=(80, 60, 65), width=3)
    draw.line([(460, 210), (430, 150)], fill=(80, 60, 65), width=3)

    # 3. Ground / plaza pavement
    draw.rectangle([0, 210, w, h], fill=(16, 12, 14))
    for gy in range(215, h, 16):
        draw.line([(0, gy), (w, gy)], fill=(32, 22, 24), width=1)

    # 4. Flaming rebel barricades & fires (flickering)
    flame_phase = frame_idx * 0.4
    fire_positions = [(120, 210), (240, 215), (400, 215), (520, 210)]
    for fx, fy in fire_positions:
        draw.rectangle([fx - 14, fy - 18, fx + 14, fy], fill=(40, 40, 45), outline=(70, 70, 75))
        fl_h = int(28 + math.sin(flame_phase + fx) * 10)
        fl_pts = [
            (fx - 12, fy - 18),
            (fx - 5, fy - 18 - fl_h + 6),
            (fx, fy - 18 - fl_h),
            (fx + 6, fy - 18 - fl_h + 8),
            (fx + 12, fy - 18)
        ]
        draw.polygon(fl_pts, fill=(245, 158, 11))
        fl_core = [
            (fx - 6, fy - 18),
            (fx, fy - 18 - int(fl_h * 0.65)),
            (fx + 6, fy - 18)
        ]
        draw.polygon(fl_core, fill=(255, 255, 200))

    # 5. Crowd of protesters / rebel silhouettes with raised banners
    crowd_x = [40, 75, 155, 185, 290, 320, 350, 450, 480, 560, 595]
    for idx, cx in enumerate(crowd_x):
        cy = 210 + int(math.sin(idx + frame_idx * 0.2) * 3)
        draw.ellipse([cx - 5, cy - 26, cx + 5, cy - 16], fill=(12, 8, 10))
        draw.polygon([(cx - 7, cy), (cx - 7, cy - 16), (cx + 7, cy - 16), (cx + 7, cy)], fill=(12, 8, 10))
        if idx % 3 == 0:
            draw.line([(cx + 4, cy - 12), (cx + 12, cy - 32)], fill=(12, 8, 10), width=2)
            flag_w = int(18 + math.sin(frame_idx * 0.3 + idx) * 4)
            draw.polygon([(cx + 12, cy - 32), (cx + 12 + flag_w, cy - 36), (cx + 12 + flag_w, cy - 24), (cx + 12, cy - 20)], fill=(220, 38, 38))

    # 6. Central decree plaque / deposed ruler alert
    pw, ph = 490, 110
    px, py = w//2 - pw//2, 85
    draw.rectangle([px, py, px + pw, py + ph], fill=(35, 12, 14), outline=(239, 68, 68), width=2)
    draw.rectangle([px + 4, py + 4, px + pw - 4, py + ph - 4], outline=(245, 158, 11), width=1)

    draw.text((w//2, py + 12), "*** POPULAR REVOLUTION // PALACE BREACHED ***", fill=(255, 255, 255), font=font_hud, anchor="mt")
    draw.text((w//2, py + 34), f"{ousted_ruler_name.upper()} DEPOSED FROM POWER", fill=(248, 113, 113), font=font_hero, anchor="mt")
    draw.text((w//2, py + 58), f"Protesters & Rebel Factions Topple the Government of {country_name}", fill=(254, 240, 138), font=font_sub, anchor="mt")
    draw.text((w//2, py + 80), "State sovereignty vacated • Reverted to Autonomous State Trust", fill=(203, 213, 225), font=font_sub, anchor="mt")

    draw.polygon([(px + 8, py + 8), (px + 22, py + 8), (px + 8, py + 22)], fill=(239, 68, 68))
    draw.polygon([(px + pw - 8, py + 8), (px + pw - 22, py + 8), (px + pw - 8, py + 22)], fill=(239, 68, 68))

    # 7. Top cinematic HUD bar
    draw.rectangle([0, 0, w, 38], fill=(20, 10, 12))
    draw.line([(0, 38), (w, 38)], fill=(239, 68, 68), width=2)
    draw.text((15, 11), "[!]", fill=(239, 68, 68), font=font_hud)
    draw.text((38, 11), f"CIVIL REBELLION: {country_name.upper()} PALACE FALLEN", fill=(255, 255, 255), font=font_hud)
    draw.text((w - 15, 12), "[REGIME TOPPLED]", fill=(248, 113, 113), font=font_tag, anchor="rt")

    # 8. Bottom ticker bar
    draw.rectangle([0, h - 24, w, h], fill=(12, 8, 10))
    draw.line([(0, h - 24), (w, h - 24)], fill=(245, 158, 11), width=1)
    draw.text((15, h - 18), "CITIZEN PROTESTERS BREACH HIGH GATES • SOVEREIGN RULER OUSTED • TRANSITIONAL REGIME DECLARED", fill=(252, 165, 165), font=font_tag)

    return im

def generate_revolution_frames(country_name: str, ousted_ruler_name: str, total_frames: int = 80):
    c_c = clean_tactical_text(country_name)
    c_r = clean_tactical_text(ousted_ruler_name)
    parchment_count = 35
    action_count = max(45, total_frames - parchment_count)

    for i in range(parchment_count):
        yield render_order_parchment_frame(
            i, parchment_count,
            "POPULAR REVOLUTION DECREE",
            c_c,
            c_r,
            "CIVIL PROTESTERS & REBEL FACTIONS",
            "REGIME OVERTHROWN",
            (239, 68, 68)
        )
    for i in range(action_count):
        yield render_revolution_scene_frame(i, action_count, c_c, c_r)

def create_revolution_frames(country_name: str, ousted_ruler_name: str, total_frames: int = 80) -> list[Image.Image]:
    return list(generate_revolution_frames(country_name, ousted_ruler_name, total_frames))

def create_revolution_gif(country_name: str, country_flag: str, ousted_ruler_name: str) -> io.BytesIO:
    frames = create_revolution_frames(country_name, ousted_ruler_name, total_frames=45)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_revolution_media(country_name: str, country_flag: str, ousted_ruler_name: str, audio_bytes=None) -> tuple[io.BytesIO | None, io.BytesIO | None]:
    target_frames = 80
    if audio_bytes is not None:
        dur = probe_audio_duration(audio_bytes)
        if dur and dur > 0:
            target_frames = max(80, int(math.ceil(dur * 10)))

    mp4_buf = render_frames_to_mp4(
        generate_revolution_frames(country_name, ousted_ruler_name, total_frames=target_frames),
        audio_bytes=audio_bytes,
        fps=10
    )
    gif_buf = None
    if mp4_buf is None:
        gif_buf = create_revolution_gif(country_name, country_flag, ousted_ruler_name)
    return gif_buf, mp4_buf

def generate_revolution_speech(country_name: str, ousted_ruler_name: str) -> io.BytesIO:
    clean_c = clean_for_speech(country_name)
    clean_r = clean_for_speech(ousted_ruler_name)
    speech = (
        f"Emergency geopolitical bulletin! A popular revolution has erupted in {clean_c}! "
        f"Protesters and armed citizen rebels have breached the presidential palace and forcibly removed {clean_r} from power! "
        f"All ministerial authority has collapsed, and sovereign leadership has reverted to an emergency state trust. The regime has fallen!"
    )
    return generate_voice_narration(speech)
