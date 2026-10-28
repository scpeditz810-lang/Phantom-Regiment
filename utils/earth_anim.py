"""
Virtual Earth Tactical Animation & Audio Generator
Generates high-definition, animated visual broadcast cards and tactical procedural audio
for Virtual Earth geopolitics:
- War Declarations & Frontline Clashes (with Emergency Air-Raid Siren audio)
- War Conclusions & Surrenders (with Armistice Fanfare / Peace Bell audio)
- Imperial Throne / Ruler Inception (with Sovereign Imperial Trumpet audio)
- Sovereign Annihilation / Country Fallen (with Defeat / Requiem audio)
"""

import io
import math
import struct
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

# ── Procedural Sound Effects Engine (Pure Python standard library) ─────────────

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
                # Emergency war air-raid siren wailing (480Hz to 820Hz) + heavy rumble
                freq = 650.0 + 190.0 * math.sin(2.0 * math.pi * 1.1 * t)
                wave_sample = math.sin(2.0 * math.pi * freq * t)
                sub_drone = 0.35 * math.sin(2.0 * math.pi * 65.0 * t)
                val = (wave_sample * 0.65 + sub_drone)
                
            elif sound_type == "victory_fanfare":
                # Majestic ascending triumph brass chord (Do-Mi-Sol chords)
                # Notes: C4 (261.6), E4 (329.6), G4 (392.0), C5 (523.2)
                step = int(t / 0.4)
                notes = [261.63, 329.63, 392.00, 523.25, 659.25, 783.99]
                curr_freq = notes[min(step, len(notes) - 1)]
                harmonic = 0.6 * math.sin(2 * math.pi * curr_freq * t) + 0.3 * math.sin(4 * math.pi * curr_freq * t)
                envelope = math.exp(-2.5 * (t % 0.4)) if step < len(notes) - 1 else math.exp(-0.8 * (t - 2.0))
                val = harmonic * envelope
                
            elif sound_type == "ruler_inauguration":
                # Sovereign royal trumpet brass fanfare
                tones = [349.23, 440.0, 523.25, 698.46]
                tone_idx = min(int(t / 0.5), len(tones) - 1)
                f = tones[tone_idx]
                brass = 0.65 * math.sin(2 * math.pi * f * t) + 0.3 * math.sin(3 * math.pi * f * t)
                val = brass * min(1.0, (duration - t) * 0.8)
                
            elif sound_type == "surrender_conceded":
                # Somber armistice peace chime / gong bell with decaying resonance
                freq1 = 440.0
                freq2 = 554.37
                bell = (0.5 * math.sin(2 * math.pi * freq1 * t) + 0.5 * math.sin(2 * math.pi * freq2 * t))
                envelope = math.exp(-1.4 * t)
                val = bell * envelope

            elif sound_type == "alliance_treaty":
                # Diplomatic harmony fanfare (dual-tone brass and noble chime)
                f1 = 349.23 if t < 1.0 else (440.0 if t < 2.0 else 523.25)
                f2 = 440.0 if t < 1.0 else (523.25 if t < 2.0 else 698.46)
                brass = 0.45 * math.sin(2 * math.pi * f1 * t) + 0.35 * math.sin(2 * math.pi * f2 * t)
                val = brass * min(1.0, (duration - t) * 0.9)

            elif sound_type == "commander_march":
                # Martial military brass call and march pulse
                step = int(t / 0.35)
                notes = [196.0, 261.63, 329.63, 392.0, 523.25]
                f = notes[min(step, len(notes) - 1)]
                pulse = 0.7 * math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t)
                snare = 0.15 * math.sin(2 * math.pi * 120.0 * (t % 0.35))
                val = (pulse + snare) * min(1.0, (duration - t) * 0.85)
                
            else: # fallen_requiem
                # Deep dramatic defeat boom & sorrow resonance
                f = max(40.0, 110.0 - (t * 22.0))
                drone = 0.7 * math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * (f * 1.5) * t)
                decay = math.exp(-0.9 * t)
                val = drone * decay

            sample_int = int(val * 28000)
            sample_int = max(-32767, min(32767, sample_int))
            wf.writeframes(struct.pack("<h", sample_int))
            
    buf.seek(0)
    return buf

# ── Animated Tactical Visual Cards & Video Pipeline ────────────────────────────

import re

def clean_tactical_text(text: str) -> str:
    """Strip Unicode emojis and flag characters that render as boxes in Pillow."""
    if not text:
        return ""
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    clean = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55]', '', clean)
    return clean.strip()

def render_frames_to_mp4(frames: list, audio_bytes=None, fps: int = 10) -> io.BytesIO | None:
    """Render Pillow frames and optional audio into an H.264 MP4 video buffer."""
    import tempfile, subprocess, os, shutil
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if not exe or not os.path.exists(exe):
            return None
    except Exception:
        return None

    td = tempfile.mkdtemp()
    try:
        for idx, frame in enumerate(frames):
            frame.save(os.path.join(td, f"frame_{idx:04d}.png"), "PNG")

        out_path = os.path.join(td, "out.mp4")
        cmd = [
            exe, "-y",
            "-stream_loop", "-1",
            "-framerate", str(fps),
            "-i", os.path.join(td, "frame_%04d.png")
        ]

        if audio_bytes is not None:
            audio_bytes.seek(0)
            data = audio_bytes.read()
            if len(data) > 0:
                audio_path = os.path.join(td, "audio.mp3")
                with open(audio_path, "wb") as f:
                    f.write(data)
                cmd.extend([
                    "-i", audio_path,
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-shortest"
                ])

        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            out_path
        ])

        res = subprocess.run(cmd, capture_output=True, timeout=25)
        if res.returncode == 0 and os.path.exists(out_path):
            with open(out_path, "rb") as f:
                buf = io.BytesIO(f.read())
            buf.seek(0)
            return buf
    except Exception as e:
        print(f"⚠️ MP4 render notice: {e}", flush=True)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return None

def create_war_declared_frames(atk_name: str, dfn_name: str, scale: str, domain: str) -> list[Image.Image]:
    w, h = 640, 240
    font_title = _get_font(18)
    font_bold = _get_font(17)
    font_sub = _get_font(12)

    c_atk = clean_tactical_text(atk_name)
    c_dfn = clean_tactical_text(dfn_name)

    frames = []
    num_frames = 20
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (18, 10, 15))
        draw = ImageDraw.Draw(im)

        # Pulsing crimson warning border
        glow = int(180 + 75 * math.sin(i * (math.pi / 10.0)))
        draw.rectangle([(0, 0), (w, 5)], fill=(glow, 28, 28))
        draw.rectangle([(0, h - 5), (w, h)], fill=(glow, 28, 28))

        # Moving horizontal scanner line
        scan_y = int((i / float(num_frames)) * h)
        draw.line([(0, scan_y), (w, scan_y)], fill=(239, 68, 68), width=2)

        # Header
        hdr = "WAR DECLARED // HOSTILITIES COMMENCED"
        bbox = draw.textbbox((0, 0), hdr, font=font_title)
        draw.text(((w - bbox[2]) // 2, 20), hdr, fill=(239, 68, 68), font=font_title)

        # Combatants
        draw.text((40, 68), f"[AGGRESSOR]  {c_atk}", fill=(248, 113, 113), font=font_bold)
        draw.text((40, 108), f"[TARGET]     {c_dfn}", fill=(56, 189, 248), font=font_bold)

        # Campaign details
        draw.text((40, 150), f"[CAMPAIGN]   DOMAIN: {domain.upper()}  |  SCALE: {scale.upper()}", fill=(148, 163, 184), font=font_sub)
        draw.text((40, 180), "[STATUS]     ARMORED DIVISIONS CLASHING ON FRONTLINE", fill=(245, 158, 11), font=font_sub)

        # Alert pulse indicator
        draw.ellipse([(w - 35, 18), (w - 20, 33)], fill=(220, 38, 38) if i % 4 < 2 else (80, 20, 20))
        frames.append(im)
    return frames

def create_war_declared_gif(atk_name: str, atk_flag: str, dfn_name: str, dfn_flag: str, scale: str, domain: str) -> io.BytesIO:
    frames = create_war_declared_frames(atk_name, dfn_name, scale, domain)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_war_declared_media(atk_name: str, dfn_name: str, scale: str, domain: str, audio_bytes=None) -> tuple[io.BytesIO, io.BytesIO | None]:
    frames = create_war_declared_frames(atk_name, dfn_name, scale, domain)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    mp4_buf = render_frames_to_mp4(frames, audio_bytes, fps=10)
    return buf, mp4_buf

def create_war_ended_frames(winner_name: str, loser_name: str, reason: str = "VICTORY", reparations: int = 0) -> list[Image.Image]:
    w, h = 640, 240
    font_title = _get_font(18)
    font_bold = _get_font(17)
    font_sub = _get_font(12)

    c_win = clean_tactical_text(winner_name)
    c_los = clean_tactical_text(loser_name)
    is_surrender = "SURRENDER" in reason.upper()

    frames = []
    num_frames = 20
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (10, 16, 26))
        draw = ImageDraw.Draw(im)

        # Pulsing glowing tactical borders
        glow = int(175 + 80 * math.sin(i * (math.pi / 10.0)))
        border_col = (234, glow, 8) if is_surrender else (16, glow, 129)
        draw.rectangle([(0, 0), (w, 5)], fill=border_col)
        draw.rectangle([(0, h - 5), (w, h)], fill=border_col)

        # Moving tactical laser scanline
        scan_x = int((i / float(num_frames)) * w)
        draw.line([(scan_x, 0), (scan_x, h)], fill=(56, 189, 248), width=2)

        # Header title
        header_text = f"CONFLICT CONCLUDED // {reason.upper()}"
        bbox = draw.textbbox((0, 0), header_text, font=font_title)
        hdr_x = max(20, (w - bbox[2]) // 2)
        draw.text((hdr_x, 22), header_text, fill=border_col, font=font_title)

        # Victor & Conceded blocks
        draw.text((40, 68), f"[VICTOR]     {c_win}", fill=(56, 189, 248), font=font_bold)
        draw.text((40, 108), f"[CONCEDED]   {c_los}", fill=(248, 113, 113), font=font_bold)

        # Reparations / Indemnity
        rep_text = f"[INDEMNITY]  +{reparations:,} Medals Plundered" if reparations else "[TERRITORY]  STATUS QUO ENFORCED"
        draw.text((40, 150), rep_text, fill=(245, 158, 11), font=font_sub)
        draw.text((40, 180), "[ARMISTICE]  ALL ACTIVE HOSTILITIES CEASED // BORDERS STABILIZED", fill=(148, 163, 184), font=font_sub)

        # Animated status beacon
        beacon_color = (234, 179, 8) if (i % 4 < 2) else (80, 60, 10)
        draw.ellipse([(w - 35, 18), (w - 20, 33)], fill=beacon_color)

        frames.append(im)
    return frames

def create_war_ended_gif(winner_name: str, winner_flag: str, loser_name: str, loser_flag: str, reason: str = "VICTORY", reparations: int = 0) -> io.BytesIO:
    frames = create_war_ended_frames(winner_name, loser_name, reason, reparations)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_war_ended_media(winner_name: str, loser_name: str, reason: str = "VICTORY", reparations: int = 0, audio_bytes=None) -> tuple[io.BytesIO, io.BytesIO | None]:
    frames = create_war_ended_frames(winner_name, loser_name, reason, reparations)
    gif_buf = io.BytesIO()
    frames[0].save(gif_buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    gif_buf.seek(0)
    mp4_buf = render_frames_to_mp4(frames, audio_bytes, fps=10)
    return gif_buf, mp4_buf

def create_new_ruler_gif(country_name: str, country_flag: str, ruler_name: str) -> io.BytesIO:
    w, h = 640, 220
    font_title = _get_font(21)
    font_bold = _get_font(19)
    font_sub = _get_font(13)
    
    frames = []
    num_frames = 12
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (10, 20, 35))
        draw = ImageDraw.Draw(im)
        
        draw.rectangle([(0, 0), (w, 6)], fill=(245, 158, 11))
        draw.rectangle([(0, h - 6), (w, h)], fill=(245, 158, 11))
        
        pulse = int(180 + 70 * (i / num_frames))
        draw.text((40, 18), "👑 SOVEREIGN INAUGURATION // NEW SUPREME RULER", fill=(pulse, 175, 40), font=font_title)
        draw.text((40, 65), f"🏛️ {country_flag} {country_name}", fill=(255, 255, 255), font=font_bold)
        draw.text((40, 105), f"🎖️ President / Supreme Sovereign: {ruler_name}", fill=(56, 189, 248), font=font_bold)
        draw.text((40, 155), "🌐 NATIONAL TELEMETRY: Full sovereign authority, military & treasury control assumed.", fill=(148, 163, 184), font=font_sub)
        
        frames.append(im)
        
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_country_fallen_frames(loser_name: str, winner_name: str) -> list[Image.Image]:
    w, h = 640, 240
    font_title = _get_font(18)
    font_bold = _get_font(17)
    font_sub = _get_font(12)

    c_los = clean_tactical_text(loser_name)
    c_win = clean_tactical_text(winner_name)

    frames = []
    num_frames = 20
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (25, 10, 10))
        draw = ImageDraw.Draw(im)

        glow = int(180 + 75 * math.sin(i * (math.pi / 10.0)))
        draw.rectangle([(0, 0), (w, 5)], fill=(glow, 28, 28))
        draw.rectangle([(0, h - 5), (w, h)], fill=(glow, 28, 28))

        scan_y = int((i / float(num_frames)) * h)
        draw.line([(0, scan_y), (w, scan_y)], fill=(220, 38, 38), width=2)

        hdr = "SOVEREIGN CAPITAL FALLEN // ANNEXATION COMPLETE"
        bbox = draw.textbbox((0, 0), hdr, font=font_title)
        hdr_x = max(20, (w - bbox[2]) // 2)
        draw.text((hdr_x, 22), hdr, fill=(239, 68, 68), font=font_title)

        draw.text((40, 68), f"[FALLEN]     {c_los}", fill=(148, 163, 184), font=font_bold)
        draw.text((40, 108), f"[CONQUEROR]  {c_win}", fill=(245, 158, 11), font=font_bold)

        draw.text((40, 150), "[STATUS]     NATIONAL SOVEREIGNTY EXTINGUISHED", fill=(239, 68, 68), font=font_sub)
        draw.text((40, 180), "[TERRITORY]  INTEGRATED DIRECTLY INTO IMPERIAL DOMINION", fill=(203, 213, 225), font=font_sub)

        beacon_col = (220, 38, 38) if (i % 4 < 2) else (80, 20, 20)
        draw.ellipse([(w - 35, 18), (w - 20, 33)], fill=beacon_col)
        frames.append(im)
    return frames

def create_country_fallen_gif(country_name: str, country_flag: str, conqueror_name: str, conqueror_flag: str) -> io.BytesIO:
    frames = create_country_fallen_frames(country_name, conqueror_name)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_country_fallen_media(loser_name: str, winner_name: str, audio_bytes=None) -> tuple[io.BytesIO, io.BytesIO | None]:
    frames = create_country_fallen_frames(loser_name, winner_name)
    gif_buf = io.BytesIO()
    frames[0].save(gif_buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    gif_buf.seek(0)
    mp4_buf = render_frames_to_mp4(frames, audio_bytes, fps=10)
    return gif_buf, mp4_buf

def create_country_allied_frames(country_a_name: str, country_b_name: str, alliance_name: str) -> list[Image.Image]:
    w, h = 640, 240
    font_title = _get_font(18)
    font_bold = _get_font(17)
    font_sub = _get_font(12)

    c_a = clean_tactical_text(country_a_name)
    c_b = clean_tactical_text(country_b_name)
    c_al = clean_tactical_text(alliance_name)

    frames = []
    num_frames = 20
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (10, 22, 20))
        draw = ImageDraw.Draw(im)

        glow = int(170 + 75 * math.sin(i * (math.pi / 10.0)))
        border_col = (16, glow, 129)
        draw.rectangle([(0, 0), (w, 5)], fill=border_col)
        draw.rectangle([(0, h - 5), (w, h)], fill=border_col)

        scan_x = int((i / float(num_frames)) * w)
        draw.line([(scan_x, 0), (scan_x, h)], fill=(52, 211, 153), width=2)

        hdr = f"STRATEGIC ALLIANCE RATIFIED // {c_al.upper()}"
        bbox = draw.textbbox((0, 0), hdr, font=font_title)
        hdr_x = max(20, (w - bbox[2]) // 2)
        draw.text((hdr_x, 22), hdr, fill=(52, 211, 153), font=font_title)

        draw.text((40, 68), f"[ALLIED]     {c_a}", fill=(255, 255, 255), font=font_bold)
        draw.text((40, 108), f"[ALLIED]     {c_b}", fill=(255, 255, 255), font=font_bold)

        draw.text((40, 150), "[DEFENSE]    COLLECTIVE SECURITY PACT ACTIVE (+25 DEFENSE)", fill=(245, 158, 11), font=font_sub)
        draw.text((40, 180), "[INTEGRITY]  MUTUAL BORDERS & SOVEREIGNTY SAFEGUARDED", fill=(148, 163, 184), font=font_sub)

        beacon_col = (16, 185, 129) if (i % 4 < 2) else (10, 80, 50)
        draw.ellipse([(w - 35, 18), (w - 20, 33)], fill=beacon_col)
        frames.append(im)
    return frames

def create_country_allied_gif(country_a_name: str, country_a_flag: str, country_b_name: str, country_b_flag: str, alliance_name: str) -> io.BytesIO:
    frames = create_country_allied_frames(country_a_name, country_b_name, alliance_name)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_country_allied_media(country_a_name: str, country_a_flag: str, country_b_name: str, country_b_flag: str, alliance_name: str, audio_bytes=None) -> tuple[io.BytesIO, io.BytesIO | None]:
    frames = create_country_allied_frames(country_a_name, country_b_name, alliance_name)
    gif_buf = io.BytesIO()
    frames[0].save(gif_buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    gif_buf.seek(0)
    mp4_buf = render_frames_to_mp4(frames, audio_bytes, fps=10)
    return gif_buf, mp4_buf

def create_new_commander_frames(country_name: str, commander_name: str) -> list[Image.Image]:
    w, h = 640, 240
    font_title = _get_font(18)
    font_bold = _get_font(17)
    font_sub = _get_font(12)

    c_c = clean_tactical_text(country_name)
    c_m = clean_tactical_text(commander_name)

    frames = []
    num_frames = 20
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (24, 14, 20))
        draw = ImageDraw.Draw(im)

        glow = int(180 + 75 * math.sin(i * (math.pi / 10.0)))
        draw.rectangle([(0, 0), (w, 5)], fill=(glow, 29, 72))
        draw.rectangle([(0, h - 5), (w, h)], fill=(glow, 29, 72))

        radar_x = int((i / float(num_frames)) * w)
        draw.line([(radar_x, 5), (radar_x, h - 5)], fill=(244, 63, 94), width=2)

        hdr = "SUPREME COMMAND APPOINTMENT // HIGH COMMAND"
        bbox = draw.textbbox((0, 0), hdr, font=font_title)
        hdr_x = max(20, (w - bbox[2]) // 2)
        draw.text((hdr_x, 22), hdr, fill=(244, 63, 94), font=font_title)

        draw.text((40, 68), f"[NATION]     {c_c}", fill=(255, 255, 255), font=font_bold)
        draw.text((40, 108), f"[COMMANDER]  {c_m}", fill=(245, 158, 11), font=font_bold)

        draw.text((40, 150), "[AUTHORITY]  ARMORED DIVISIONS & AIR SUPERIORITY UNDER COMMAND", fill=(226, 232, 240), font=font_sub)
        draw.text((40, 180), "[READINESS]  DEFCON 1 PROTOCOLS ACTIVE // FRONTLINES MOBILIZED", fill=(148, 163, 184), font=font_sub)

        badge_col = (245, 158, 11) if i % 4 < 2 else (225, 29, 72)
        draw.ellipse([(w - 35, 18), (w - 20, 33)], fill=badge_col)
        frames.append(im)
    return frames

def create_new_commander_gif(country_name: str, country_flag: str, commander_name: str) -> io.BytesIO:
    frames = create_new_commander_frames(country_name, commander_name)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    buf.seek(0)
    return buf

def create_new_commander_media(country_name: str, country_flag: str, commander_name: str, audio_bytes=None) -> tuple[io.BytesIO, io.BytesIO | None]:
    frames = create_new_commander_frames(country_name, commander_name)
    gif_buf = io.BytesIO()
    frames[0].save(gif_buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    gif_buf.seek(0)
    mp4_buf = render_frames_to_mp4(frames, audio_bytes, fps=10)
    return gif_buf, mp4_buf


# ── Spoken Voice Narration (TTS) Engine ───────────────────────────────────────

import re
import urllib.request
import urllib.parse

def clean_for_speech(text: str) -> str:
    """Strip markdown, discord mentions, URLs and special symbols for clean vocal speech."""
    text = re.sub(r'<@&?[0-9]+>', '', text)
    text = re.sub(r'<#[0-9]+>', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[*_`~#\[\]\(\)>|]', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return ' '.join(text.split())

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
            return buf
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
            return buf
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
