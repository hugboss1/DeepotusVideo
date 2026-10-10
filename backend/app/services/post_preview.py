"""Compose a 'final post' preview image — the hero image + caption laid out
like an X (Twitter) post or a Telegram channel message. The Scheduler shows
this so the user can visualize the published post before it goes out, honoring
each platform's usage format (X: handle + 280-char card; Telegram: channel
bubble with image-then-caption, longer text).

Pure Pillow, no network. Fonts resolve from the OS (Windows) with a built-in
fallback; emoji render in color via Segoe UI Emoji when present.
"""
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from app.i18n import msg

_FONT_DIR = Path(r"C:\Windows\Fonts")


def _font(names, size):
    for n in names:
        p = _FONT_DIR / n
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()


def _regular(size):
    return _font(["segoeui.ttf", "arial.ttf"], size)


def _bold(size):
    return _font(["segoeuib.ttf", "arialbd.ttf"], size)


def _emoji(size):
    p = _FONT_DIR / "seguiemj.ttf"
    if p.is_file():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            return None
    return None


# Broad emoji/pictograph ranges — enough to segment text from color glyphs.
_EMOJI_RE = re.compile(
    "([\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0000200D\U000024C2"
    "\U00002190-\U000021AA]+)",
    flags=re.UNICODE,
)


def _segments(s: str):
    """Split a string into (run, is_emoji) chunks."""
    out = []
    last = 0
    for m in _EMOJI_RE.finditer(s):
        if m.start() > last:
            out.append((s[last:m.start()], False))
        out.append((m.group(), True))
        last = m.end()
    if last < len(s):
        out.append((s[last:], False))
    return out


def _run_width(run, is_emoji, fr, fe, size):
    if not is_emoji:
        return fr.getlength(run)
    if fe is not None:
        try:
            return fe.getlength(run)
        except Exception:
            pass
    return size * 1.15 * max(1, len(run))


def _line_width(line, fr, fe, size):
    return sum(_run_width(r, e, fr, fe, size) for r, e in _segments(line))


def _wrap(text, fr, fe, size, max_w):
    lines = []
    for para in (text or "").split("\n"):
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if not cur or _line_width(trial, fr, fe, size) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def _draw_line(draw, x, y, line, fr, fe, fill, size):
    for run, is_emoji in _segments(line):
        if is_emoji and fe is not None:
            try:
                draw.text((x, y), run, font=fe, embedded_color=True)
                x += _run_width(run, True, fr, fe, size)
                continue
            except Exception:
                pass
        draw.text((x, y), run, font=fr, fill=fill)
        x += fr.getlength(run)


def _rounded(im, radius):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, im.size[0] - 1, im.size[1] - 1], radius=radius, fill=255)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def _load_hero(hero_path: Optional[str], width: int, max_h: int):
    """Return an RGBA image fit to `width` (contain, letterboxed on black if
    taller than max_h), or None."""
    if not hero_path:
        return None
    p = Path(hero_path)
    if not p.is_file():
        return None
    try:
        im = Image.open(p).convert("RGBA")
    except Exception:
        return None
    iw, ih = im.size
    nh = int(ih * (width / iw))
    if nh <= max_h:
        return im.resize((width, nh), Image.LANCZOS)
    scale = max_h / ih
    nw = int(iw * scale)
    canvas = Image.new("RGBA", (width, max_h), (0, 0, 0, 255))
    canvas.paste(im.resize((nw, max_h), Image.LANCZOS), ((width - nw) // 2, 0))
    return canvas


def _placeholder(width, height, label=None):
    label = label or msg("apercu.vide")
    im = Image.new("RGBA", (width, height), (12, 18, 28, 255))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([1, 1, width - 2, height - 2], radius=14,
                        outline=(60, 76, 100, 255), width=2)
    f = _regular(20)
    tw = f.getlength(label)
    d.text(((width - tw) / 2, height / 2 - 12), label, font=f,
           fill=(120, 140, 165, 255))
    return im


def _initial(name):
    name = (name or "D").strip()
    return name[0].upper() if name else "D"


def _render_x(caption, hero_path, display_name, handle, lang="fr"):
    W, pad = 680, 28
    CW = W - 2 * pad
    ink, sub, accent = (15, 20, 25, 255), (83, 100, 113, 255), (29, 155, 240, 255)
    f_name, f_handle = _bold(26), _regular(21)
    f_cap, f_small, f_av = _regular(27), _regular(19), _bold(26)
    ef = _emoji(27)
    cap_lines = _wrap(caption, f_cap, ef, 27, CW)
    line_h = 39
    header_h = 56
    hero = _load_hero(hero_path, CW, 520) or _placeholder(CW, 300, msg("apercu.vide", lang))
    hero = _rounded(hero, 16)
    y = pad
    cap_h = len(cap_lines) * line_h
    H = pad + header_h + 14 + cap_h + 16 + hero.size[1] + 16 + 44 + pad
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    # avatar
    d.ellipse([pad, y, pad + 48, y + 48], fill=(201, 53, 53, 255))
    iw = f_av.getlength(_initial(display_name))
    d.text((pad + 24 - iw / 2, y + 9), _initial(display_name), font=f_av,
           fill=(255, 255, 255, 255))
    # name + verified, handle
    nx = pad + 60
    d.text((nx, y + 2), display_name, font=f_name, fill=ink)
    nw = f_name.getlength(display_name)
    d.ellipse([nx + nw + 8, y + 6, nx + nw + 28, y + 26], fill=accent)
    d.text((nx + nw + 13, y + 5), "✓", font=_bold(15), fill=(255, 255, 255, 255))
    d.text((nx, y + 30), f"@{handle} · now", font=f_handle, fill=sub)
    y += header_h + 14
    # caption
    for ln in cap_lines:
        _draw_line(d, pad, y, ln, f_cap, ef, ink, 27)
        y += line_h
    y += 16
    # hero
    img.paste(hero, (pad, y), hero)
    y += hero.size[1] + 16
    # footer: timestamp + char counter chip (X usage format = 280)
    n = len(caption or "")
    over = n > 280
    d.text((pad, y + 8), datetime.now().strftime("%I:%M %p · %d %b %Y · X"),
           font=f_small, fill=sub)
    chip = f"{n}/280"
    cw = f_small.getlength(chip)
    cx = W - pad - cw - 20
    chip_col = (244, 33, 46, 255) if over else sub
    d.rounded_rectangle([cx - 6, y + 4, W - pad, y + 34], radius=14,
                        outline=chip_col, width=2)
    d.text((cx + 4, y + 8), chip, font=f_small, fill=chip_col)
    return img


def _render_telegram(caption, hero_path, display_name, lang="fr"):
    W, pad = 680, 22
    bubble_x, bubble_w = pad, W - 2 * pad
    inner = bubble_w - 24
    bg = (14, 22, 33, 255)            # telegram dark chat
    bubble = (24, 37, 51, 255)
    ink, sub, accent = (236, 240, 244, 255), (122, 143, 166, 255), (106, 179, 243, 255)
    f_name = _bold(22)
    f_cap, f_small = _regular(25), _regular(18)
    ef = _emoji(25)
    cap_lines = _wrap(caption, f_cap, ef, 25, inner)
    line_h = 36
    hero = _load_hero(hero_path, bubble_w, 540)
    hero_h = hero.size[1] if hero else 0
    cap_h = len(cap_lines) * line_h
    bubble_h = 44 + hero_h + (14 + cap_h if caption else 0) + 36
    H = pad + bubble_h + pad
    img = Image.new("RGBA", (W, H), bg)
    d = ImageDraw.Draw(img)
    # bubble
    d.rounded_rectangle([bubble_x, pad, bubble_x + bubble_w, pad + bubble_h],
                        radius=16, fill=bubble)
    y = pad + 12
    d.text((bubble_x + 12, y), display_name, font=f_name, fill=accent)
    y += 32
    # image (full bubble width, rounded)
    if hero:
        hr = _rounded(hero, 12)
        img.paste(hr, (bubble_x, y), hr)
        y += hero_h + 14
    else:
        ph = _placeholder(inner, 220, msg("apercu.vide", lang))
        img.paste(ph, (bubble_x + 12, y), ph)
        y += 220 + 14
    # caption
    for ln in cap_lines:
        _draw_line(d, bubble_x + 12, y, ln, f_cap, ef, ink, 25)
        y += line_h
    # footer: views + time (telegram channel style), char count subtle
    n = len(caption or "")
    foot = datetime.now().strftime("%H:%M")
    fw = f_small.getlength(foot)
    d.text((bubble_x + bubble_w - fw - 14, pad + bubble_h - 28), foot,
           font=f_small, fill=sub)
    d.text((bubble_x + 14, pad + bubble_h - 28), msg("apercu.telegram", lang, n=n),
           font=f_small, fill=sub)
    return img


# plan scheduler T9 (tâche #30, 30/09/2026) — aperçus des lecteurs VERTICAUX. Zones d'interface en fraction du cadre
# 9:16 : de mémoire (03/09/2026), à corriger sur des captures d'un vrai téléphone ; le bandeau de l'aperçu le rappelle
# (« zones indicatives »).
SAFE_ZONES = {
    "instagram": {"top": 0.06, "bottom": 0.17, "right": 0.12, "label": "Reels"},
    "youtube": {"top": 0.07, "bottom": 0.15, "right": 0.12, "label": "Shorts"},
    "tiktok": {"top": 0.08, "bottom": 0.20, "right": 0.14, "label": "TikTok"},
}
CANVAS = (540, 960)


def _cover(im, w, h):
    iw, ih = im.size
    s = max(w / iw, h / ih)
    im = im.resize((max(1, int(iw * s)), max(1, int(ih * s))), Image.LANCZOS)
    x, y = (im.size[0] - w) // 2, (im.size[1] - h) // 2
    return im.crop((x, y, x + w, y + h))


def _render_vertical(caption, hero_path, handle, network, lang="fr"):
    W, H = CANVAS
    z = SAFE_ZONES[network]
    hero = None
    if hero_path and Path(hero_path).is_file():
        try:
            hero = _cover(Image.open(hero_path).convert("RGBA"), W, H)
        except Exception:
            hero = None
    img = hero or _placeholder(W, H, msg("apercu.vide_vertical", lang))
    top, bot, right = int(H * z["top"]), int(H * z["bottom"]), int(W * z["right"])
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, top], fill=(0, 0, 0, 130))
    d.rectangle([0, H - bot, W, H], fill=(0, 0, 0, 160))
    d.rectangle([W - right, top, W, H - bot], fill=(0, 0, 0, 130))
    for y in range(top, H - bot, 18):              # hachures = masqué par l'interface du lecteur
        d.line([(W - right, y), (W, y + 18)], fill=(244, 33, 46, 90), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    d = ImageDraw.Draw(img)
    f_name, f_cap, f_small = _bold(20), _regular(19), _regular(14)
    ef = _emoji(19)
    white = (255, 255, 255, 255)
    d.text((16, 12), msg("apercu.zones", lang, reseau=z['label'], n=len(caption or '')), font=f_small, fill=white)
    d.text((16, H - bot + 12), f"@{handle}", font=f_name, fill=white)
    y = H - bot + 42
    for ln in _wrap(caption or "", f_cap, ef, 19, W - right - 32)[:3]:
        _draw_line(d, 16, y, ln, f_cap, ef, white, 19)
        y += 26
    return img


def render_preview(*, channel: str, caption: str, hero_path: Optional[str],
                   display_name: str = "Deepotus", handle: str = "deepotus", lang: str = "fr") -> bytes:
    ch = (channel or "x").lower()
    if ch in ("telegram", "tg"):
        img = _render_telegram(caption or "", hero_path, display_name, lang)
    elif ch in SAFE_ZONES:
        img = _render_vertical(caption or "", hero_path, handle, ch, lang)
    else:
        img = _render_x(caption or "", hero_path, display_name, handle, lang)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
