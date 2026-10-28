"""
Virtual Earth Tactical Animation Generator
Generates high-definition, animated GIF/video cards for Virtual Earth geopolitics:
- War Declarations & Frontline Clashes
- War Conclusions & Surrenders
- Imperial Throne / Ruler Inception
- Sovereign Annihilation / Country Fallen
"""

import io
from PIL import Image, ImageDraw, ImageFont

def _get_font(size: int = 18):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except Exception:
            return ImageFont.load_default()

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
