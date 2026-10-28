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
import re
import struct
import urllib.parse
import wave
import requests
from PIL import Image, ImageDraw, ImageFont

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

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



# ── Spoken Voice Narration (Text-to-Speech) Engine ─────────────────────────────

def clean_for_speech(text: str) -> str:
    """Sanitize text by removing Discord emojis, mentions, links, and markdown for crisp speech."""
    if not text:
        return ""
    text = re.sub(r'<a?:\w+:\d+>', '', text)
    text = re.sub(r'<[@#]&?(\d+)>', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[*_~`#|>]', '', text)
    text = re.sub(r'[^\w\s.,!?:;\-\'"]+', ' ', text)
    return ' '.join(text.split())

def generate_spoken_narration(text: str, tld: str = "co.uk") -> io.BytesIO:
    """Generate high-definition spoken broadcast narration (.mp3) from text using keyless TTS."""
    cleaned = clean_for_speech(text)
    if not cleaned:
        cleaned = "Attention citizens. Geopolitical status update on the world stage."

    buf = io.BytesIO()

    # Primary: gTTS
    if gTTS is not None:
        try:
            tts = gTTS(text=cleaned, lang='en', tld=tld)
            tts.write_to_fp(buf)
            buf.seek(0)
            if len(buf.getvalue()) > 500:
                return buf
        except Exception as e:
            print(f"⚠️ gTTS synthesis notice: {e}, attempting direct HTTP fallback...", flush=True)

    # Secondary: direct Google Translate TTS stream
    try:
        encoded_query = urllib.parse.quote_plus(cleaned[:300])
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en-GB&q={encoded_query}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 500:
            buf = io.BytesIO(resp.content)
            buf.seek(0)
            return buf
    except Exception as e2:
        print(f"⚠️ Direct TTS synthesis notice: {e2}", flush=True)

    # Fallback to tactical audio if network TTS is completely unavailable
    return generate_tactical_audio("surrender_conceded")

def generate_ruler_speech(country_name: str, ruler_name: str) -> io.BytesIO:
    """Generate spoken voice announcement for a newly emerged sovereign ruler."""
    c_clean = clean_for_speech(country_name)
    r_clean = clean_for_speech(ruler_name)
    script = (
        f"Attention citizens of the world. A new sovereign ruler has emerged! "
        f"President {r_clean} has assumed the supreme leadership of {c_clean}. "
        f"National defense command and imperial authority are now established."
    )
    return generate_spoken_narration(script, tld="co.uk")

def generate_war_speech(attacker_name: str, defender_name: str, scale: str = "border") -> io.BytesIO:
    """Generate spoken voice announcement for a declaration of war."""
    atk = clean_for_speech(attacker_name)
    dfn = clean_for_speech(defender_name)
    scl = clean_for_speech(scale)
    script = (
        f"Emergency tactical alert. Hostilities have commenced on Virtual Earth. "
        f"{atk} has officially declared a {scl} campaign of war against {dfn}. "
        f"Frontline divisions and battle groups are deployed for combat."
    )
    return generate_spoken_narration(script, tld="co.uk")

def generate_surrender_speech(winner_name: str, loser_name: str, reparations: int = 0) -> io.BytesIO:
    """Generate spoken voice announcement for a formal war concession and surrender."""
    win = clean_for_speech(winner_name)
    los = clean_for_speech(loser_name)
    script = (
        f"Geopolitical armistice dispatch. The war has concluded. "
        f"{los} has formally conceded and surrendered to {win}. "
        f"Frontline combat ceases immediately, and reparations are enforced."
    )
    return generate_spoken_narration(script, tld="co.uk")

def generate_victory_speech(winner_name: str, loser_name: str) -> io.BytesIO:
    """Generate spoken voice announcement for a decisive campaign victory."""
    win = clean_for_speech(winner_name)
    los = clean_for_speech(loser_name)
    script = (
        f"Conflict victory announcement. Frontline operations have concluded. "
        f"{win} has achieved a decisive victory over {los}. "
        f"Sovereignty and territorial dominance are enforced."
    )
    return generate_spoken_narration(script, tld="co.uk")

def generate_country_fallen_speech(country_name: str, conqueror_name: str) -> io.BytesIO:
    """Generate spoken voice announcement for a fallen sovereign state / annexation."""
    cntry = clean_for_speech(country_name)
    conq = clean_for_speech(conqueror_name)
    script = (
        f"Emergency global alert. A sovereign capital has fallen! "
        f"{cntry} has collapsed and been annexed into the imperial dominion of {conq}."
    )
    return generate_spoken_narration(script, tld="co.uk")

# ── Animated Tactical Visual Cards ─────────────────────────────────────────────

def create_war_declared_gif(atk_name: str, atk_flag: str, dfn_name: str, dfn_flag: str, scale: str, domain: str) -> io.BytesIO:
    w, h = 640, 220
    font_title = _get_font(22)
    font_bold = _get_font(18)
    font_sub = _get_font(13)
    
    frames = []
    num_frames = 10
    for i in range(num_frames):
        bg_val = 14 + int(i * 1.5)
        im = Image.new("RGB", (w, h), (bg_val, bg_val + 5, bg_val + 15))
        draw = ImageDraw.Draw(im)
        
        # Red warning borders
        draw.rectangle([(0, 0), (w, 5)], fill=(220, 38, 38))
        draw.rectangle([(0, h - 5), (w, h)], fill=(220, 38, 38))
        
        # Moving scanner line
        scan_y = int((i / num_frames) * h)
        draw.line([(0, scan_y), (w, scan_y)], fill=(239, 68, 68), width=2)
        
        # Header title
        title_text = "🚨 WAR DECLARED // HOSTILITIES COMMENCED 🚨"
        draw.text((w // 2 - 200, 18), title_text, fill=(239, 68, 68), font=font_title)
        
        # Attacker vs Defender
        draw.text((40, 68), f"⚔️ {atk_flag} {atk_name}", fill=(255, 255, 255), font=font_bold)
        draw.text((w // 2 - 18, 68), "VS", fill=(245, 158, 11), font=font_bold)
        draw.text((w // 2 + 50, 68), f"🛡️ {dfn_flag} {dfn_name}", fill=(255, 255, 255), font=font_bold)
        
        # Sub details
        domain_str = f"🌐 CAMPAIGN: {domain.upper()}  |  SCALE: {scale.upper()}"
        draw.text((40, 120), domain_str, fill=(148, 163, 184), font=font_sub)
        draw.text((40, 150), "⚡ TACTICAL COMMAND: Deploy armored divisions and air/naval support on Virtual Earth.", fill=(203, 213, 225), font=font_sub)
        
        # Pulse indicator
        draw.ellipse([(w - 35, 18), (w - 20, 33)], fill=(220, 38, 38) if i % 2 == 0 else (120, 20, 20))
        
        frames.append(im)
        
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=110, loop=0)
    buf.seek(0)
    return buf

def create_war_ended_gif(winner_name: str, winner_flag: str, loser_name: str, loser_flag: str, reason: str = "VICTORY", reparations: int = 0) -> io.BytesIO:
    w, h = 640, 220
    font_title = _get_font(22)
    font_bold = _get_font(18)
    font_sub = _get_font(13)
    
    frames = []
    num_frames = 10
    is_surrender = "SURRENDER" in reason.upper()
    
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (15, 23, 42))
        draw = ImageDraw.Draw(im)
        
        border_color = (234, 179, 8) if is_surrender else (16, 185, 129)
        draw.rectangle([(0, 0), (w, 5)], fill=border_color)
        draw.rectangle([(0, h - 5), (w, h)], fill=border_color)
        
        header = f"🏳️ CONFLICT CONCLUDED // {reason.upper()} 🏆"
        draw.text((w // 2 - 210, 18), header, fill=border_color, font=font_title)
        
        draw.text((40, 68), f"👑 VICTOR: {winner_flag} {winner_name}", fill=(56, 189, 248), font=font_bold)
        draw.text((40, 105), f"🏳️ CONCEDED: {loser_flag} {loser_name}", fill=(148, 163, 184), font=font_bold)
        
        rep_text = f"💰 WAR INDEMNITY / REPARATIONS: +{reparations:,} Medals Plundered!" if reparations else "🕊️ TERRITORIAL INTEGRITY ENFORCED // FRONTS CLOSED"
        draw.text((40, 150), rep_text, fill=(245, 158, 11), font=font_sub)
        
        frames.append(im)
        
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=120, loop=0)
    buf.seek(0)
    return buf

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

def create_country_fallen_gif(country_name: str, country_flag: str, conqueror_name: str, conqueror_flag: str) -> io.BytesIO:
    w, h = 640, 220
    font_title = _get_font(21)
    font_bold = _get_font(18)
    font_sub = _get_font(13)
    
    frames = []
    num_frames = 10
    for i in range(num_frames):
        im = Image.new("RGB", (w, h), (25, 10, 10))
        draw = ImageDraw.Draw(im)
        
        draw.rectangle([(0, 0), (w, 6)], fill=(185, 28, 28))
        draw.rectangle([(0, h - 6), (w, h)], fill=(185, 28, 28))
        
        draw.text((40, 18), "⚠️ SOVEREIGN CAPITAL FALLEN // ANNEXATION COMPLETE", fill=(239, 68, 68), font=font_title)
        draw.text((40, 65), f"🏚️ Fallen State: {country_flag} {country_name}", fill=(148, 163, 184), font=font_bold)
        draw.text((40, 105), f"⚔️ Conquered by Empire: {conqueror_flag} {conqueror_name}", fill=(245, 158, 11), font=font_bold)
        draw.text((40, 155), "🌍 SOVEREIGNTY UPDATE: Territory has been annexed into the imperial dominion.", fill=(226, 232, 240), font=font_sub)
        
        frames.append(im)
        
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=120, loop=0)
    buf.seek(0)
    return buf
