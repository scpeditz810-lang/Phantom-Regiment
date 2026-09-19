"""
Pillow-based rank card generator.
Produces a 934×282 PNG matching the reference screenshot style:
  - Dark gradient background (special tints for top 3)
  - Circular avatar with coloured border
  - Username, rank badge, level, global rank, XP bar
"""

import io
import os
from PIL import Image, ImageDraw, ImageFont
import aiohttp

from utils.constants import CARD_WIDTH, CARD_HEIGHT, ACCENT_GOLD, XP_BAR_BG, XP_BAR_FILL


# ── Font helpers ────────────────────────────────────────────────────────────────

_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # Linux / Docker
    "C:/Windows/Fonts/arialbd.ttf",                            # Windows
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",       # macOS
]
_REGULAR_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for p in (_BOLD_PATHS if bold else _REGULAR_PATHS):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    # Fallback
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


# ── Background generator ───────────────────────────────────────────────────────

def _gradient(top: tuple[int, ...], bot: tuple[int, ...]) -> Image.Image:
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(CARD_HEIGHT):
        r = y / CARD_HEIGHT
        draw.line(
            [(0, y), (CARD_WIDTH, y)],
            fill=tuple(int(t * (1 - r) + b * r) for t, b in zip(top, bot)),
        )
    return img


def _get_banner(global_rank: int, active_banner: str | None = None) -> Image.Image:
    """Return a custom file banner if present, otherwise a generated gradient."""
    banner_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "banners")
    
    # Priority 1: User's custom purchased banner
    if active_banner:
        path = os.path.join(banner_dir, f"{active_banner}.png")
        if os.path.exists(path):
            return Image.open(path).resize((CARD_WIDTH, CARD_HEIGHT))
            
    # Priority 2: Top 3 Leaderboard specific banners
    lookup = {
        1: ("banner_top1.png", (50, 42, 10), (15, 12, 5)),    # gold
        2: ("banner_top2.png", (42, 42, 50), (14, 14, 20)),   # silver
        3: ("banner_top3.png", (50, 34, 18), (18, 12, 6)),    # bronze
    }
    if global_rank in lookup:
        fname, top, bot = lookup[global_rank]
        path = os.path.join(banner_dir, fname)
        if os.path.exists(path):
            return Image.open(path).resize((CARD_WIDTH, CARD_HEIGHT))
        return _gradient(top, bot)

    # Priority 3: Default banner
    path = os.path.join(banner_dir, "banner_default.png")
    if os.path.exists(path):
        return Image.open(path).resize((CARD_WIDTH, CARD_HEIGHT))
    return _gradient((35, 35, 42), (12, 12, 16))


# ── Circle-crop avatar ─────────────────────────────────────────────────────────

def _circle_avatar(img: Image.Image, size: int, border_col: tuple, bw: int = 6) -> Image.Image:
    img = img.resize((size, size)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    total = size + bw * 2
    bordered = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    ImageDraw.Draw(bordered).ellipse([0, 0, total - 1, total - 1], fill=border_col)
    bordered.paste(out, (bw, bw), out)
    return bordered


# ── Public API ──────────────────────────────────────────────────────────────────

async def generate_rank_card(
    username: str,
    avatar_url: str,
    level: int,
    xp: int,
    required_xp: int,
    global_rank: int,
    rank_name: str,
    rank_color: tuple[int, int, int] = ACCENT_GOLD,
    active_banner: str | None = None,
) -> io.BytesIO:
    """Generate a rank card PNG and return it as a BytesIO buffer."""

    card = _get_banner(global_rank, active_banner).convert("RGBA")
    draw = ImageDraw.Draw(card)

    font_xl   = _load_font(36, bold=True)
    font_lg   = _load_font(24, bold=True)
    font_md   = _load_font(20)
    font_tag  = _load_font(16, bold=True)

    # ── Avatar ──────────────────────────────────────────────────────────────
    async with aiohttp.ClientSession() as s:
        async with s.get(str(avatar_url)) as r:
            avatar_data = await r.read()

    avatar = _circle_avatar(Image.open(io.BytesIO(avatar_data)), 160, rank_color)
    ay = (CARD_HEIGHT - avatar.height) // 2
    card.paste(avatar, (30, ay), avatar)

    text_x = 230

    # ── Username ────────────────────────────────────────────────────────────
    draw.text((text_x, 55), username, fill=(255, 255, 255), font=font_xl)
    ubox = draw.textbbox((text_x, 55), username, font=font_xl)

    # ── Rank badge ──────────────────────────────────────────────────────────
    tag_x = ubox[2] + 15
    tag_y = 62
    tag_text = rank_name
    tb = draw.textbbox((0, 0), tag_text, font=font_tag)
    tw, th = tb[2] - tb[0] + 16, tb[3] - tb[1] + 10
    draw.rounded_rectangle((tag_x, tag_y, tag_x + tw, tag_y + th), radius=4, fill=rank_color)
    brightness = (rank_color[0] * 299 + rank_color[1] * 587 + rank_color[2] * 114) / 1000
    tc = (0, 0, 0) if brightness > 128 else (255, 255, 255)
    draw.text((tag_x + 8, tag_y + 3), tag_text, fill=tc, font=font_tag)

    # ── Level ───────────────────────────────────────────────────────────────
    draw.text((text_x, 110), f"LEVEL {level}", fill=ACCENT_GOLD, font=font_lg)

    # ── Global rank (top-right) ─────────────────────────────────────────────
    gr_text = f"#{global_rank} GLOBAL"
    grb = draw.textbbox((0, 0), gr_text, font=font_lg)
    draw.text((CARD_WIDTH - (grb[2] - grb[0]) - 30, 25), gr_text, fill=ACCENT_GOLD, font=font_lg)

    # ── XP text (right-aligned) ─────────────────────────────────────────────
    xp_text = f"{xp} / {required_xp} - XP"
    xpb = draw.textbbox((0, 0), xp_text, font=font_md)
    draw.text((CARD_WIDTH - (xpb[2] - xpb[0]) - 30, 175), xp_text, fill=(200, 200, 200), font=font_md)

    # ── XP progress bar ────────────────────────────────────────────────────
    bar_x, bar_y, bar_h = text_x, 215, 28
    bar_w = CARD_WIDTH - bar_x - 30
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=14, fill=XP_BAR_BG)
    if required_xp > 0:
        fill_w = max(int(xp / required_xp * bar_w), bar_h)
        fill_w = min(fill_w, bar_w)
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=14, fill=XP_BAR_FILL)

    # ── Output ──────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf
