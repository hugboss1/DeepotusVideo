"""Template engine for v1.6 — node-based composition templates.

A template is a pure-JSON layout graph (canvas + regions). Both the visual
editor and the renderer operate on this format; there is no hidden DB state.

Phase A scope: load / list / get / save / delete / slot extraction +
validation. Rendering (build_ffmpeg_command / render) is added in Phase B.

Built-in templates ship inside the codebase at backend/app/templates/*.json
and are immutable. User-created templates live under assets/user_templates/.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.config import settings
from app.services.composition_service import _run_ffmpeg


def _run_ffmpeg_in(cmd: list[str], output: Path, cwd: Path) -> Path:
    """Like composition_service._run_ffmpeg but with an explicit cwd.

    Used for the spatial renderer so drawtext can reference fontfile/textfile
    by bare filename (no Windows drive-colon to escape in the filtergraph).
    """
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True,
                               text=True, cwd=str(cwd))
        if not output.exists():
            raise RuntimeError(f"ffmpeg succeeded but output missing: {output}")
        logger.info(f"ffmpeg OK: {output} ({output.stat().st_size // 1024} KB)")
        return output
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffmpeg failed (exit {e.returncode}):\n{(e.stderr or '')[-1500:]}"
        ) from e
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found in PATH. Install ffmpeg first.")

SLOT_TYPES = ("video_slot", "image_slot", "text_slot")
# audio_slot has no geometry (timeline audio track); still a fillable slot.
FILLABLE_TYPES = SLOT_TYPES + ("audio_slot",)

# Font name (as written in templates) -> shipped TTF under templates/_fonts/
_FONT_FILES = {
    "space grotesk": "SpaceGrotesk.ttf",
    "inter": "Inter.ttf",
    "jetbrains mono": "JetBrainsMono.ttf",
    # Design fonts (OFL / Apache, redistributable) shipped for Studio overlays.
    "bebas neue": "BebasNeue.ttf",
    "anton": "Anton.ttf",
    "archivo black": "ArchivoBlack.ttf",
    "righteous": "Righteous.ttf",
    "bungee": "Bungee.ttf",
    "staatliches": "Staatliches.ttf",
    "abril fatface": "AbrilFatface.ttf",
    "pacifico": "Pacifico.ttf",
    "permanent marker": "PermanentMarker.ttf",
    "monoton": "Monoton.ttf",
    "press start 2p": "PressStart2P.ttf",
    "cinzel": "Cinzel.ttf",  # OFL Roman-capitals serif (Trajan-style)
    # User-supplied free fonts (Freeware / Public Domain / CC-BY / FFC).
    "dripping marker": "DrippingMarker.ttf",
    "graffiti brush": "GraffitiBrush.ttf",
    "distant galaxy": "DistantGalaxy.ttf",
    "hacked": "Hacked.ttf",
    "super pencil": "SuperPencil.ttf",
    "poland kaito": "PolandKaito.otf",
    "super feel": "SuperFeel.ttf",
}
_DEFAULT_FONT = "SpaceGrotesk.ttf"


def _hex(color: str | None, default: str = "ffffff") -> str:
    return (color or f"#{default}").lstrip("#")


def _has_audio(path: Path) -> bool:
    """True if `path` has at least one audio stream (via ffprobe)."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            check=False, capture_output=True, text=True,
        )
        return bool(out.stdout.strip())
    except FileNotFoundError:
        # ffprobe missing -> assume audio present; ffmpeg will error clearly if not.
        return True


def _scale_filter(fit: str, w: int, h: int, bg: str) -> str:
    if fit == "contain":
        return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x{bg}")
    if fit == "stretch":
        return f"scale={w}:{h}"
    if fit == "crop":
        return (f"scale='if(gt({w},iw),{w},iw)':'if(gt({h},ih),{h},ih)',"
                f"crop={w}:{h}")
    # cover (default)
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}")


class TemplateEngine:
    """Load, validate, save, and (Phase B+) render template graphs."""

    def __init__(self):
        # User-created templates: assets/user_templates/ (sibling of assets/outputs)
        self.templates_dir = settings.outputs_path.parent / "user_templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        # Built-ins ship with the app and are immutable.
        self.builtin_dir = Path(__file__).parent.parent / "templates"
        self.builtin_dir.mkdir(parents=True, exist_ok=True)

    # ----- discovery -----

    def _builtin_ids(self) -> set[str]:
        return {f.stem for f in self.builtin_dir.glob("*.json")}

    def is_builtin(self, template_id: str) -> bool:
        return (self.builtin_dir / f"{template_id}.json").exists()

    def list_templates(self) -> list[dict]:
        """Return all templates (built-in first, then user-created).

        A user template whose id collides with a built-in is skipped — built-ins
        are authoritative and cannot be shadowed.
        """
        out: list[dict] = []
        seen: set[str] = set()
        for f in sorted(self.builtin_dir.glob("*.json")):
            try:
                tpl = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Built-in template {f.name} is invalid JSON: {e}")
                continue
            tpl["_builtin"] = True
            out.append(tpl)
            seen.add(tpl.get("id", f.stem))
        for f in sorted(self.templates_dir.glob("*.json")):
            try:
                tpl = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"User template {f.name} is invalid JSON: {e}")
                continue
            if tpl.get("id", f.stem) in seen:
                continue
            tpl["_builtin"] = False
            out.append(tpl)
        return out

    def get_template(self, template_id: str) -> dict:
        """Built-ins win over user files of the same id (immutability)."""
        builtin_path = self.builtin_dir / f"{template_id}.json"
        if builtin_path.exists():
            tpl = json.loads(builtin_path.read_text(encoding="utf-8"))
            tpl["_builtin"] = True
            return tpl
        user_path = self.templates_dir / f"{template_id}.json"
        if user_path.exists():
            tpl = json.loads(user_path.read_text(encoding="utf-8"))
            tpl["_builtin"] = False
            return tpl
        raise FileNotFoundError(f"Template not found: {template_id}")

    # ----- mutation -----

    def save_template(self, template: dict) -> str:
        """Validate and persist a user template.

        If the requested id is empty or collides with a built-in, a fresh
        id `tpl_user_<hex>` is generated. Built-ins are never overwritten.
        """
        self._validate(template)
        tid = template.get("id") or ""
        if not tid or self.is_builtin(tid):
            tid = f"tpl_user_{uuid4().hex[:8]}"
        template["id"] = tid
        template.pop("_builtin", None)
        path = self.templates_dir / f"{tid}.json"
        path.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Template saved: {tid} -> {path}")
        return tid

    def delete_template(self, template_id: str) -> str:
        """Delete a user template.

        Returns "deleted" on success, "builtin" if the id is a protected
        built-in, "missing" if no such user template exists. Render/job history
        is untouched (templates and jobs are independent records).
        """
        if self.is_builtin(template_id):
            return "builtin"
        path = self.templates_dir / f"{template_id}.json"
        if path.exists():
            path.unlink()
            logger.info(f"Template deleted: {template_id}")
            return "deleted"
        return "missing"

    # ----- validation -----

    _ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")

    def _validate(self, template: dict) -> None:
        """Raise ValueError if the template is malformed."""
        for k in ("name", "canvas", "regions"):
            if k not in template:
                raise ValueError(f"Template missing required field: {k}")

        tid = template.get("id")
        if tid is not None and tid != "" and not self._ID_RE.match(str(tid)):
            raise ValueError(
                f"Template id must match [A-Za-z0-9_-]+ (got {tid!r})"
            )

        canvas = template["canvas"]
        for k in ("width", "height"):
            if k not in canvas:
                raise ValueError(f"Canvas missing required field: {k}")
        if canvas["width"] <= 0 or canvas["height"] <= 0:
            raise ValueError("Canvas dimensions must be positive")

        regions = template["regions"]
        if not isinstance(regions, list) or len(regions) == 0:
            raise ValueError("Template must have at least one region")

        # Sequential/montage acts are nominal full-frame placeholders that
        # get cover-scaled to whatever canvas/format is chosen — their
        # geometry must not be bounds-checked against the canvas.
        is_seq = template.get("render_mode") == "sequential"
        seen_ids: set[str] = set()
        seen_slot_names: set[str] = set()
        for r in regions:
            for k in ("id", "type"):
                if k not in r:
                    raise ValueError(
                        f"Region missing field '{k}': {r.get('id', '<no id>')}"
                    )
            if r["id"] in seen_ids:
                raise ValueError(f"Duplicate region id: {r['id']}")
            seen_ids.add(r["id"])
            if r["type"] != "audio_slot":
                # audio_slot is a timeline track, not a placed region.
                for k in ("x", "y", "width", "height"):
                    if k not in r:
                        raise ValueError(
                            f"Region missing field '{k}': {r['id']}")
                if r["width"] <= 0 or r["height"] <= 0:
                    raise ValueError(
                        f"Region {r['id']} has non-positive size")
                if r["x"] < 0 or r["y"] < 0:
                    raise ValueError(
                        f"Region {r['id']} has negative origin")
                if not (is_seq and r["type"] in FILLABLE_TYPES):
                    if r["x"] + r["width"] > canvas["width"]:
                        raise ValueError(
                            f"Region {r['id']} exceeds canvas width")
                    if r["y"] + r["height"] > canvas["height"]:
                        raise ValueError(
                            f"Region {r['id']} exceeds canvas height")
            if r["type"] in FILLABLE_TYPES:
                sn = r.get("slot_name")
                if not sn:
                    raise ValueError(
                        f"Region {r['id']} is a {r['type']} but has no slot_name"
                    )
                if sn in seen_slot_names:
                    raise ValueError(f"Duplicate slot_name: {sn}")
                seen_slot_names.add(sn)

    # ----- slot extraction -----

    def slots_from(self, tpl: dict) -> list[dict]:
        """Extract input slots from a template dict (id or inline)."""
        slots: list[dict] = []
        for r in tpl.get("regions", []):
            if r["type"] not in FILLABLE_TYPES:
                continue
            slot = {
                "slot_name": r["slot_name"],
                "slot_label": r.get("slot_label", r["slot_name"]),
                "region_id": r["id"],
                "type": r["type"],
                "default_provider": r.get("default_provider"),
            }
            if r["type"] == "text_slot":
                slot["default_text"] = r.get("default_text", "")
                slot["max_chars"] = r.get("max_chars")
            slots.append(slot)
        return slots

    def list_slots(self, template_id: str) -> list[dict]:
        """Extract the input slots a template needs filled at render time."""
        return self.slots_from(self.get_template(template_id))

    # ----- asset resolution -----

    def font_path(self, name: str | None) -> Path:
        fn = _FONT_FILES.get((name or "").strip().lower(), _DEFAULT_FONT)
        p = self.builtin_dir / "_fonts" / fn
        if not p.exists():
            p = self.builtin_dir / "_fonts" / _DEFAULT_FONT
        return p

    def mark_path(self, src: str) -> Path | None:
        """Resolve a brand-strip mark `src` (relative to the templates dir).

        Returns None if the asset is absent so the renderer can degrade
        gracefully instead of failing the whole job.
        """
        p = (self.builtin_dir / src).resolve()
        if p.exists():
            return p
        logger.warning(f"Brand mark asset missing, skipping: {src}")
        return None

    def image_path(self, src: str | None) -> Path | None:
        """Resolve a sticker image `src` — a bare filename in the images dir
        (where /images/upload and /images/generate save). Returns None if
        absent so the renderer degrades gracefully."""
        if not src:
            return None
        safe = Path(str(src)).name
        p = (settings.images_path / safe).resolve()
        if p.exists():
            return p
        logger.warning(f"Sticker image missing, skipping: {src}")
        return None

    # ----- rendering -----

    def render(
        self,
        template_id: str,
        slot_values: dict[str, dict],
        output_path: Path,
        template: dict | None = None,
    ) -> Path:
        """Render a template with filled slots into a final MP4.

        If `template` (an inline dict) is given it is rendered as-is — so
        unsaved editor edits (ticker color/text, etc.) render exactly as
        seen. Otherwise the saved template `template_id` is loaded.
        slot_values: {slot_name: {"path": Path}} for video/image slots,
                     {slot_name: {"text": str}} for text slots.
        Synchronous (subprocess); the pipeline calls it via run_in_executor.
        """
        tpl = template if template is not None else self.get_template(
            template_id)
        self._validate(tpl)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work = Path(settings.outputs_path) / "_tmp_render" / output_path.stem
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)

        logger.info(f"Rendering template {template_id} -> {output_path}")
        try:
            if tpl.get("render_mode") == "sequential":
                cmd, _ = build_sequential_command(self, tpl, slot_values,
                                                  output_path)
                # No filtergraph paths in the sequential graph; cwd irrelevant.
                _run_ffmpeg(cmd, output_path)
            else:
                cmd = build_ffmpeg_command(self, tpl, slot_values,
                                           output_path, work)
                # drawtext fontfile/textfile are bare names resolved in `work`.
                _run_ffmpeg_in(cmd, output_path, cwd=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        return output_path


# ---- ffmpeg command builders (module-level, testable in isolation) ----

_VIDEO_LIKE = ("video_slot", "image_slot")


def _slot_path(slot_values: dict, name: str) -> Path:
    sv = slot_values.get(name)
    if not sv or not sv.get("path"):
        raise ValueError(f"Slot '{name}' has no source path")
    p = Path(sv["path"])
    if not p.exists():
        raise FileNotFoundError(f"Slot '{name}' source not found: {p}")
    return p


def _slot_text(slot_values: dict, name: str, default: str) -> str:
    sv = slot_values.get(name) or {}
    return (sv.get("text") if sv.get("text") is not None else default) or ""


def _drawtext(cur: str, out: str, *, font_name: str, textfile_name: str,
              size: int, color: str, x: str, y: str,
              alpha: str | None = None) -> str:
    """Build a drawtext filter. font_name / textfile_name are bare filenames
    resolved against ffmpeg's cwd (the per-render work dir) so no Windows
    drive-colon ever appears in the filtergraph. x / y are single-quoted so
    time expressions (scrolling) with commas survive the filtergraph parser.
    `alpha` is an optional expression (e.g. a pulse).
    """
    extra = f":alpha='{alpha}'" if alpha else ""
    return (
        f"[{cur}]drawtext=fontfile={font_name}:textfile={textfile_name}:"
        f"fontsize={size}:fontcolor=0x{color}:x='{x}':y='{y}':"
        f"borderw=3:bordercolor=0x02060d@0.65{extra}[{out}]"
    )


_EMOJI_DIR = Path(__file__).resolve().parent.parent / "assets" / "emoji"

import re as _re_emoji
from app.config import DATA_ROOT as _DATA_ROOT
# User-imported custom emojis live in the DATA dir (survive reinstall), keyed by
# a :shortcode: that the picker inserts and the renderer resolves to its PNG.
_EMOJI_CUSTOM_DIR = _DATA_ROOT / "assets" / "emoji_custom"
_SHORTCODE_RE = _re_emoji.compile(r":([a-z0-9_-]{1,40}):")


def _custom_emoji_path(name: str) -> Path:
    return _EMOJI_CUSTOM_DIR / (str(name) + ".png")


def _is_emoji_cp(o: int) -> bool:
    return (0x1F000 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF
            or 0x2B00 <= o <= 0x2BFF or 0x2190 <= o <= 0x21FF
            or 0x2300 <= o <= 0x23FF or o == 0xFE0F or o == 0x20E3
            or 0x1F1E6 <= o <= 0x1F1FF)


def _has_emoji(s) -> bool:
    s = s or ""
    if any(_is_emoji_cp(ord(c)) for c in s):
        return True
    return any(_custom_emoji_path(m.group(1)).exists()
               for m in _SHORTCODE_RE.finditer(s))


def _emoji_file(unit: str) -> str:
    return "-".join("%x" % ord(c) for c in unit if ord(c) != 0xFE0F)


def _seg_unicode(s: str, units: list):
    """Append unicode text/emoji runs from `s` onto `units`. VS16 / ZWJ /
    skin-tone modifiers stick to the preceding emoji unit."""
    for ch in s or "":
        o = ord(ch)
        if (o == 0xFE0F or o == 0x200D or 0x1F3FB <= o <= 0x1F3FF) \
                and units and units[-1][0] == "emoji":
            units[-1] = ("emoji", units[-1][1] + ch)
        elif _is_emoji_cp(o):
            units.append(("emoji", ch))
        elif units and units[-1][0] == "text":
            units[-1] = ("text", units[-1][1] + ch)
        else:
            units.append(("text", ch))


def _segment_emoji(s: str):
    """Split into [(kind, value)] runs: 'text', 'emoji' (unicode char), or
    'cemoji' (custom emoji :shortcode: whose PNG exists in the data dir).
    Unknown shortcodes stay as literal text."""
    s = s or ""
    units: list[tuple[str, str]] = []
    pos = 0
    for m in _SHORTCODE_RE.finditer(s):
        if _custom_emoji_path(m.group(1)).exists():
            _seg_unicode(s[pos:m.start()], units)
            units.append(("cemoji", m.group(1)))
            pos = m.end()
    _seg_unicode(s[pos:], units)
    return units


def render_emoji_text_png(text, font_file, size, color_hex, out_path, stroke=3):
    """Render one line of text + color emojis (bundled Twemoji PNGs) to a
    transparent PNG. ffmpeg drawtext cannot draw color emoji, so emoji regions
    are pre-rendered here and overlaid. Unbundled emojis are skipped.
    Returns (width, height)."""
    from PIL import Image, ImageDraw, ImageFont
    size = int(size)
    f = ImageFont.truetype(str(font_file), size)
    pad = stroke + 2
    height = size + 2 * pad
    gap = max(2, size // 12)
    plan, x = [], pad
    for kind, val in _segment_emoji(text or ""):
        if kind == "text":
            plan.append(("text", val, x, 0))
            x += int(f.getlength(val))
        elif kind == "emoji":
            p = _EMOJI_DIR / (_emoji_file(val) + ".png")
            if p.exists():
                plan.append(("emoji", str(p), x, size))
                x += size + gap
        else:  # cemoji — user-imported, aspect preserved (height = size)
            p = _custom_emoji_path(val)
            if p.exists():
                cw = size
                try:
                    with Image.open(p) as _im:
                        w0, h0 = _im.size
                    cw = max(1, min(int(round(size * (w0 / max(1, h0)))), size * 3))
                except Exception:
                    cw = size
                plan.append(("cemoji", str(p), x, cw))
                x += cw + gap
    width = max(x + pad, 1)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill = "#" + (color_hex or "ffffff")
    for kind, val, px, w in plan:
        if kind == "text":
            d.text((px, pad), val, font=f, fill=fill,
                   stroke_width=stroke, stroke_fill=(2, 6, 13, 180))
        else:
            try:
                dims = (size, size) if kind == "emoji" else (w, size)
                e = Image.open(val).convert("RGBA").resize(dims, Image.LANCZOS)
                img.alpha_composite(e, (px, pad))
            except Exception:
                pass
    img.save(out_path)
    return img.width, img.height


def build_ffmpeg_command(engine, template, slot_values, output_path, work):
    """Compile a (spatial) template + slot values into an ffmpeg command.

    `work` is a per-render scratch dir that ffmpeg runs with as its cwd; text
    files and the needed font(s) are written there and referenced by bare
    filename so no Windows drive-colon appears in the filtergraph. Returns the
    command list. Regions compose in z-index order via successive
    overlay/drawbox/drawtext filters; audio is mixed per region volume with
    fades + loudness normalization from the template's `audio` block.
    """
    work = Path(work)
    _font_cache: dict[str, str] = {}
    _txt_n = [0]

    def _font_in_work(name: str | None) -> str:
        src = engine.font_path(name)
        if src.name not in _font_cache:
            shutil.copyfile(src, work / src.name)
            _font_cache[src.name] = src.name
        return _font_cache[src.name]

    def _textfile(content: str) -> str:
        _txt_n[0] += 1
        fn = f"t{_txt_n[0]}.txt"
        (work / fn).write_text(content, encoding="utf-8")
        return fn

    canvas = template["canvas"]
    w, h = int(canvas["width"]), int(canvas["height"])
    duration = float(canvas.get("duration_s", 8))
    fps = int(canvas.get("fps", 30))
    bg = _hex(canvas.get("background_color"), "000000")
    regions = sorted(template["regions"], key=lambda r: r.get("z_index", 0))
    audio_blk = template.get("audio") or {}

    # --- Duration master: avoid cutting a talking avatar ------------------
    # When audio.master_track == "from_slot:<name>", the rendered length is
    # driven by that slot's real media duration (ffprobe) instead of the
    # fixed canvas.duration_s, plus an adjustable tail pad so the speech is
    # never clipped on the last word. canvas.duration_s stays a floor so
    # shorter avatars don't shrink an intentionally long post.
    tail_pad = float(
        audio_blk.get("tail_pad_s",
                       canvas.get("tail_pad_s", 0.30)) or 0.0)
    mt = str(audio_blk.get("master_track") or "")
    if mt.startswith("from_slot:"):
        mt_name = mt.split(":", 1)[1].strip()
        try:
            mt_dur = _probe_duration(_slot_path(slot_values, mt_name))
            duration = max(duration, round(mt_dur + tail_pad, 3))
        except (ValueError, FileNotFoundError):
            pass

    inputs: list[str] = ["-f", "lavfi", "-i",
                         f"color=c=0x{bg}:s={w}x{h}:d={duration}:r={fps}"]
    idx = 1
    region_input: dict[str, int] = {}
    mark_inputs: list[tuple[str, int, dict]] = []  # (region_id, idx, item)
    audio_streams: list[tuple[int, float]] = []

    def _add_input(path: Path, *, still: bool) -> int:
        nonlocal idx
        if still:
            inputs.extend(["-loop", "1", "-t", str(duration), "-i", str(path)])
        else:
            inputs.extend(["-i", str(path)])
        i = idx
        idx += 1
        return i

    for r in regions:
        if r["type"] in _VIDEO_LIKE:
            p = _slot_path(slot_values, r["slot_name"])
            region_input[r["id"]] = _add_input(p, still=(r["type"] == "image_slot"))
            if r["type"] == "video_slot" and float(r.get("audio_volume", 0)) > 0:
                if _has_audio(p):
                    audio_streams.append((region_input[r["id"]],
                                          float(r["audio_volume"])))
        elif r["type"] == "brand_strip":
            for j, item in enumerate(r.get("items", [])):
                if item.get("type") == "mark":
                    mp = engine.mark_path(item.get("src", ""))
                    if mp is not None:
                        mark_inputs.append((r["id"], _add_input(mp, still=True),
                                            {**item, "_j": j}))

    parts = [f"[0:v]format=yuv420p[base]"]
    cur = "base"
    n = 0

    def _w(filter_str: str, label: str) -> None:
        nonlocal cur
        parts.append(filter_str)
        cur = label

    for r in regions:
        rid = r["id"]
        rx, ry = int(r["x"]), int(r["y"])
        rw, rh = int(r["width"]), int(r["height"])
        if r["type"] in _VIDEO_LIKE:
            i = region_input[rid]
            sf = _scale_filter(r.get("fit", "cover"), rw, rh, bg)
            n += 1
            eff = r.get("effect")
            zp = ""
            if eff in ("zoom_in", "zoom_out"):
                T = max(int(round(duration * fps)), 1)
                if eff == "zoom_in":
                    z = f"1+0.15*on/{T}"
                else:
                    z = f"1.15-0.15*on/{T}"
                zp = (f",zoompan=z='{z}':"
                      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                      f"d=1:s={rw}x{rh}:fps={fps}")
            parts.append(
                f"[{i}:v]{sf},setsar=1,fps={fps}{zp},format=yuv420p[s{n}]")
            _w(f"[{cur}][s{n}]overlay={rx}:{ry}:eof_action=repeat[o{n}]", f"o{n}")
        elif r["type"] in ("text", "text_slot"):
            if r["type"] == "text_slot":
                txt = _slot_text(slot_values, r["slot_name"],
                                 r.get("default_text", ""))
            else:
                txt = r.get("text", "")
            mc = r.get("max_chars")
            if mc:
                txt = txt[: int(mc)]
            n += 1
            size = int(r.get("size", 48))
            color = _hex(r.get("color"), "ffffff")
            if _has_emoji(txt):
                ep = work / f"emojitxt{n}.png"
                pw, _ph = render_emoji_text_png(
                    txt, engine.font_path(r.get("font")), size, color, ep)
                ox = rx + (rw - pw) // 2 if r.get("align") == "center" else rx
                ei = _add_input(ep, still=True)
                parts.append(f"[{ei}:v]format=rgba[ev{n}]")
                _w(f"[{cur}][ev{n}]overlay={int(ox)}:{ry}[oe{n}]", f"oe{n}")
            else:
                if r.get("align") == "center":
                    x_expr = f"{rx}+(({rw})-tw)/2"
                else:
                    x_expr = str(rx)
                alpha = None
                if r.get("effect") == "pulse":
                    sp = float(r.get("effect_speed", 1.0))
                    alpha = f"0.5+0.5*sin(2*PI*t*{sp})"
                _w(_drawtext(cur, f"d{n}",
                             font_name=_font_in_work(r.get("font")),
                             textfile_name=_textfile(txt), size=size, color=color,
                             x=x_expr, y=str(ry), alpha=alpha), f"d{n}")
        elif r["type"] == "brand_strip":
            sbg = _hex(r.get("background_color"), bg)
            n += 1
            _w(f"[{cur}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
               f"color=0x{sbg}@1:t=fill[b{n}]", f"b{n}")
            for (owner, mi, item) in mark_inputs:
                if owner != rid:
                    continue
                scale = float(item.get("scale", 1.0))
                ix = rx + int(item.get("x", 0))
                iy = ry + int(item.get("y", 0))
                n += 1
                parts.append(
                    f"[{mi}:v]scale=iw*{scale}:ih*{scale},format=rgba[m{n}]")
                _w(f"[{cur}][m{n}]overlay={ix}:{iy}:eof_action=repeat[mo{n}]",
                   f"mo{n}")
            for item in r.get("items", []):
                if item.get("type") != "text":
                    continue
                n += 1
                _w(_drawtext(cur, f"bt{n}",
                             font_name=_font_in_work(item.get("font")),
                             textfile_name=_textfile(item.get("text", "")),
                             size=int(item.get("size", 32)),
                             color=_hex(item.get("color"), "00e5ff"),
                             x=str(rx + int(item.get("x", 0))),
                             y=str(ry + int(item.get("y", 0)))), f"bt{n}")
        elif r["type"] == "separator":
            scol = _hex(r.get("color"), "00e5ff")
            n += 1
            _w(f"[{cur}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
               f"color=0x{scol}@1:t=fill[sep{n}]", f"sep{n}")
        elif r["type"] == "badge":
            # Corner pill: bg box (@opacity) + optional border + centered text.
            # effect=="pulse" animates the text alpha (the "LIVE" badge).
            bcol = _hex(r.get("background_color"), "0b0f1a")
            bop = float(r.get("bg_opacity", 0.82))
            n += 1
            _w(f"[{cur}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
               f"color=0x{bcol}@{bop}:t=fill[bd{n}]", f"bd{n}")
            bbor = r.get("border_color")
            if bbor:
                n += 1
                _w(f"[{cur}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
                   f"color=0x{_hex(bbor)}@1:t=2[bdb{n}]", f"bdb{n}")
            btxt = r.get("text", "")
            bsize = int(r.get("size", 34))
            btcol = _hex(r.get("color"), "ffffff")
            balpha = None
            if r.get("effect") == "pulse":
                bsp = float(r.get("effect_speed", 1.2))
                balpha = f"0.5+0.5*sin(2*PI*t*{bsp})"
            if _has_emoji(btxt):
                ep = work / f"emojibd{n}.png"
                pw, ph = render_emoji_text_png(
                    btxt, engine.font_path(r.get("font")), bsize, btcol, ep)
                ox = rx + (rw - pw) // 2
                oy = ry + (rh - ph) // 2
                ei = _add_input(ep, still=True)
                parts.append(f"[{ei}:v]format=rgba[bev{n}]")
                _w(f"[{cur}][bev{n}]overlay={int(ox)}:{int(oy)}[bdo{n}]",
                   f"bdo{n}")
            else:
                bx = f"{rx}+(({rw})-tw)/2"
                by = f"{ry}+(({rh})-th)/2"
                _w(_drawtext(cur, f"bdt{n}",
                             font_name=_font_in_work(r.get("font")),
                             textfile_name=_textfile(btxt), size=bsize,
                             color=btcol, x=bx, y=by, alpha=balpha), f"bdt{n}")
        elif r["type"] == "sticker":
            # Corner image overlay (uploaded or AI-generated PNG), scaled to
            # fit the region box preserving aspect, centered.
            sp = engine.image_path(r.get("image_src") or r.get("src"))
            if sp is not None:
                i = _add_input(sp, still=True)
                n += 1
                parts.append(
                    f"[{i}:v]scale={rw}:{rh}:force_original_aspect_ratio="
                    f"decrease,format=rgba[stk{n}]")
                _w(f"[{cur}][stk{n}]overlay="
                   f"{rx}+({rw}-overlay_w)/2:{ry}+({rh}-overlay_h)/2:"
                   f"eof_action=repeat[sto{n}]", f"sto{n}")
        elif r["type"] == "ticker":
            _tbgv = r.get("background_color")
            if _tbgv:  # empty/None -> no bar (the "none" background option)
                tbg = _hex(_tbgv, bg)
                n += 1
                _w(f"[{cur}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
                   f"color=0x{tbg}@1:t=fill[tk{n}]", f"tk{n}")
            speed = float(r.get("speed", 120))
            size = int(r.get("size", 40))
            tcol = _hex(r.get("color"), "00e5ff")
            tk_text = r.get("text", "")
            if _has_emoji(tk_text):
                ep = work / f"emojitk{n}.png"
                pw, ph = render_emoji_text_png(
                    tk_text, engine.font_path(r.get("font")), size, tcol, ep)
                ei = _add_input(ep, still=True)
                oy = ry + (rh - ph) // 2
                if r.get("direction") == "right":
                    xe = f"{rx}-{pw}+mod(t*{speed},{rw}+{pw})"
                else:
                    xe = f"{rx}+{rw}-mod(t*{speed},{rw}+{pw})"
                n += 1
                parts.append(f"[{ei}:v]format=rgba[ev{n}]")
                _w(f"[{cur}][ev{n}]overlay=x='{xe}':y={oy}[ot{n}]", f"ot{n}")
            else:
                y_expr = f"{ry}+({rh}-th)/2"
                if r.get("direction") == "right":
                    x_expr = f"{rx}-tw+mod(t*{speed},{rw}+tw)"
                else:
                    x_expr = f"{rx}+{rw}-mod(t*{speed},{rw}+tw)"
                alpha = None
                if r.get("effect") == "pulse":
                    sp = float(r.get("effect_speed", 1.0))
                    alpha = f"0.5+0.5*sin(2*PI*t*{sp})"
                n += 1
                _w(_drawtext(cur, f"tt{n}",
                             font_name=_font_in_work(r.get("font")),
                             textfile_name=_textfile(tk_text),
                             size=size, color=tcol,
                             x=x_expr, y=y_expr, alpha=alpha), f"tt{n}")

    parts.append(f"[{cur}]format=yuv420p[outv]")

    has_audio = len(audio_streams) > 0
    if has_audio:
        alabels = []
        for k, (ai, vol) in enumerate(audio_streams):
            parts.append(f"[{ai}:a]volume={vol},aresample=async=1[av{k}]")
            alabels.append(f"[av{k}]")
        if len(alabels) > 1:
            parts.append(f"{''.join(alabels)}amix=inputs={len(alabels)}:"
                          f"duration=longest:normalize=0[amx]")
            amx = "amx"
        else:
            amx = alabels[0].strip("[]")
        fi = float(audio_blk.get("fade_in_s", 0) or 0)
        fo = float(audio_blk.get("fade_out_s", 0) or 0)
        lufs = audio_blk.get("loudness_target_lufs")
        achain = f"[{amx}]"
        seg = []
        if fi > 0:
            seg.append(f"afade=t=in:st=0:d={fi}")
        if fo > 0:
            seg.append(f"afade=t=out:st={max(duration - fo, 0)}:d={fo}")
        if lufs is not None:
            seg.append(f"loudnorm=I={lufs}:TP=-1.5:LRA=11")
        if seg:
            parts.append(f"{achain}{','.join(seg)}[outa]")
        else:
            parts.append(f"{achain}anull[outa]")

    cmd = ["ffmpeg", "-y", *inputs,
           "-filter_complex", ";".join(parts), "-map", "[outv]"]
    if has_audio:
        cmd += ["-map", "[outa]", "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]
    cmd += [
        "-t", str(duration),
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(fps), "-movflags", "+faststart",
        str(output_path),
    ]
    return cmd


def _probe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            check=False, capture_output=True, text=True).stdout.strip()
        return max(0.5, float(out))
    except (ValueError, FileNotFoundError):
        return 5.0


# Montage transition -> (xfade transition name, fixed duration or None).
# "cut" is a ~1-frame xfade so the whole chain stays one uniform code path.
_XFADE = {
    "cut": ("fade", 0.04),
    "crossfade": ("fade", None),
    "fade": ("fade", None),
    "dissolve": ("dissolve", None),
    "fadeblack": ("fadeblack", None),
    "glitch": ("pixelize", None),
    "slide": ("slideleft", None),
    "flash": ("fadewhite", None),
    "cyan_flash": ("fadewhite", None),  # legacy default
}


def build_sequential_command(engine, template, slot_values, output_path):
    """Compile a `render_mode: sequential` montage: 2..N clips chained with
    per-act `transition` ({type,duration_s}) via the xfade filter.

    Acts whose slot was not filled are skipped (so one montage template
    supports 2..N clips). Audio is a silent track (montage is visual —
    Seedance has no audio; pair with a voiceover/avatar separately).
    Returns (cmd, []).
    """
    canvas = template["canvas"]
    w, h = int(canvas["width"]), int(canvas["height"])
    fps = int(canvas.get("fps", 30))
    bg = _hex(canvas.get("background_color"), "000000")
    all_acts = sorted(
        [r for r in template["regions"] if r["type"] in _VIDEO_LIKE],
        key=lambda r: (r.get("act", 0), r.get("z_index", 0)),
    )
    # Only acts whose slot was actually filled by the user.
    acts = [r for r in all_acts
            if (slot_values.get(r["slot_name"]) or {}).get("path")]
    if not acts:
        raise ValueError("Montage has no filled clips")

    inputs: list[str] = []
    durs: list[float] = []          # exact timeline length of each clip
    forced: list[float] = []        # per-act forced length_s (0 = natural)
    in_idx: list[int] = []
    # Per-act source audio (the avatar): (act_index, ffmpeg_input, volume).
    voice_acts: list[tuple[int, int, float]] = []
    idx = 0
    for r in acts:
        p = _slot_path(slot_values, r["slot_name"])
        ln = float(r.get("length_s") or 0)
        # length_mode "source" => play the clip's full real duration (no
        # trim), so a talking avatar is never clipped. The user calibrates
        # the sibling animation clips to that length (the timeline UI
        # surfaces each clip's real duration). "fixed" keeps length_s.
        lm = str(r.get("length_mode") or "fixed")
        tail_pad = float(r.get("tail_pad_s", 0) or 0)
        if r["type"] == "image_slot":
            d = ln if ln > 0 else float(r.get("duration_s", 4))
            inputs.extend(["-loop", "1", "-t", str(d), "-i", str(p)])
            durs.append(d)
            forced.append(0.0)  # already exactly d via -t
        else:
            inputs.extend(["-i", str(p)])
            if lm == "source" or ln <= 0:
                d = round(_probe_duration(p) + tail_pad, 3)
                durs.append(d)
                # tail_pad needs an explicit freeze; raw source needs none.
                forced.append(d if tail_pad > 0 else 0.0)
            else:
                durs.append(ln)
                forced.append(ln)
        in_idx.append(idx)
        if r["type"] != "image_slot" and float(r.get("audio_volume", 0)) > 0 \
                and _has_audio(p):
            voice_acts.append((len(in_idx) - 1, idx,
                               float(r.get("audio_volume", 1.0))))
        idx += 1

    sf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},setsar=1,fps={fps},format=yuv420p")
    parts: list[str] = []
    for k, r in enumerate(acts):
        chain = sf
        if forced[k] > 0:
            # Trim if longer; freeze last frame if shorter -> exact length.
            chain += (f",tpad=stop_mode=clone:stop_duration={forced[k]},"
                      f"trim=0:{forced[k]}")
        chain += ",setpts=PTS-STARTPTS"
        parts.append(f"[{in_idx[k]}:v]{chain}[n{k}]")

    starts: list[float] = [0.0] * len(acts)  # timeline start of each clip
    if len(acts) == 1:
        parts.append("[n0]format=yuv420p[outv]")
        total = durs[0]
    else:
        cur = "n0"
        cumulative = durs[0]
        for k in range(1, len(acts)):
            tr = (acts[k].get("transition") or {})
            ttype = tr.get("type", "crossfade")
            name, fixed = _XFADE.get(ttype, _XFADE["crossfade"])
            tau = fixed if fixed is not None else float(
                tr.get("duration_s", 0.5))
            tau = max(0.04, min(tau, max(0.1, durs[k] - 0.1),
                                max(0.1, cumulative - 0.1)))
            offset = max(0.0, round(cumulative - tau, 3))
            starts[k] = offset
            out = f"x{k}"
            parts.append(
                f"[{cur}][n{k}]xfade=transition={name}:"
                f"duration={round(tau,3)}:offset={offset}[{out}]")
            cur = out
            cumulative = cumulative + durs[k] - tau
        parts.append(f"[{cur}]format=yuv420p[outv]")
        total = cumulative

    # Audio: an optional audio_slot track (upload/existing) mixed at its
    # volume and looped to cover the montage; else a silent stereo track.
    audio_reg = next(
        (r for r in template["regions"]
         if r["type"] == "audio_slot"
         and (slot_values.get(r["slot_name"]) or {}).get("path")),
        None,
    )
    a_labels: list[str] = []
    # Avatar / voice clips keep their own audio, each delayed to its
    # timeline position so the speech lands under the right clip and is
    # never dropped or cut by the montage.
    for vn, (ak, vin, vvol) in enumerate(voice_acts):
        dly = int(round(starts[ak] * 1000))
        parts.append(
            f"[{vin}:a]aresample=async=1,"
            f"aformat=sample_rates=44100:channel_layouts=stereo,"
            f"volume={vvol},adelay={dly}|{dly}[va{vn}]")
        a_labels.append(f"[va{vn}]")

    if audio_reg is not None:
        ap = _slot_path(slot_values, audio_reg["slot_name"])
        vol = float(audio_reg.get("volume", 0.8))
        a_in = idx
        inputs.extend(["-stream_loop", "-1", "-i", str(ap)])
        parts.append(
            f"[{a_in}:a]aresample=async=1,"
            f"aformat=sample_rates=44100:channel_layouts=stereo,"
            f"volume={vol}[mtrk]")
        a_labels.append("[mtrk]")
        idx += 1

    if a_labels:
        if len(a_labels) > 1:
            parts.append(
                f"{''.join(a_labels)}amix=inputs={len(a_labels)}:"
                f"duration=longest:normalize=0,"
                f"aresample=async=1[outa]")
        else:
            parts.append(f"{a_labels[0]}aresample=async=1[outa]")
        audio_map = "[outa]"
    else:
        a_in = idx
        inputs.extend(["-f", "lavfi", "-i",
                       "anullsrc=channel_layout=stereo:sample_rate=44100"])
        audio_map = f"{a_in}:a"

    cmd = ["ffmpeg", "-y", *inputs,
           "-filter_complex", ";".join(parts),
           "-map", "[outv]", "-map", audio_map,
           "-t", str(round(total, 3)),
           "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
           "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(output_path)]
    return cmd, []
