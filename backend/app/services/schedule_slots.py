"""Créneaux par canal (plan scheduler P3, T8 — tâche #30, 30/09/2026) : heures LOCALES par réseau dans
DATA_ROOT/scheduler/slots.json ({"_tz": getTimezoneOffset du navigateur, "x": [...]}).

Défauts = ceux du skill deepotus-comms (account-config.md) ; TikTok de mémoire. Un canal dont aucune heure n'est valide
garde ses défauts (jamais une liste vide) ; un fichier illisible rend les défauts. `suggest` ne propose une heure qu'à
partir de 5 posts mesurés sur le canal (metrics_service.analytics → items)."""
import json
import re
from datetime import datetime, timedelta

from app.config import DATA_ROOT

DEFAULTS = {"x": ["08:30", "13:00", "19:30"], "telegram": ["10:00", "18:00"],
            "instagram": ["12:30", "18:30"], "youtube": ["09:30", "19:00"], "tiktok": ["12:00", "19:00"]}
_FILE = DATA_ROOT / "scheduler" / "slots.json"
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _raw() -> dict:
    try:
        d = json.loads(_FILE.read_text("utf-8")) or {}
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _clean(d: dict) -> dict:
    out = {}
    for ch, hs in (d or {}).items():
        if ch in DEFAULTS and isinstance(hs, list):
            hs = sorted({h for h in hs if isinstance(h, str) and _HHMM.match(h)})
            if hs:
                out[ch] = hs
    try:
        out["_tz"] = int((d or {}).get("_tz", 0))
    except (TypeError, ValueError):
        out["_tz"] = 0
    return out


def load() -> dict[str, list[str]]:
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in _clean(_raw()).items() if k != "_tz"})
    return merged


def tz_offset() -> int:
    return _clean(_raw())["_tz"]


def save(d: dict) -> dict[str, list[str]]:
    clean = _clean(d)
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(clean, indent=1), "utf-8")
    tmp.replace(_FILE)
    return load()


def assign(posts: list[dict], slots: dict | None = None) -> list[dict]:
    """k-ième post du jour sur son PREMIER canal → k-ième créneau (modulo)."""
    slots = slots or load()
    seen: dict = {}
    for p in posts:
        ch = (p.get("channels") or ["x"])[0]
        hs = slots.get(ch) or DEFAULTS.get(ch) or DEFAULTS["x"]
        key = (p.get("day_offset", 0), ch)
        k = seen.get(key, 0)
        seen[key] = k + 1
        p["time"] = hs[k % len(hs)]
    return posts


def suggest(items: list[dict], tz_offset_minutes: int = 0, min_posts: int = 5) -> dict:
    """Par canal : demi-heure LOCALE au meilleur engagement MOYEN si ≥ min_posts posts mesurés, sinon None."""
    buckets: dict = {}
    for it in items:
        try:
            t = datetime.fromisoformat(str(it["posted_at"]).replace("Z", "")) - timedelta(minutes=tz_offset_minutes)
        except (KeyError, ValueError):
            continue
        hh = f"{t.hour:02d}:{'30' if t.minute >= 30 else '00'}"
        b = buckets.setdefault(it.get("channel", "x"), {}).setdefault(hh, [0, 0])
        b[0] += int(it.get("engagement", 0))
        b[1] += 1
    out = {}
    for ch, hs in buckets.items():
        n = sum(c for _s, c in hs.values())
        out[ch] = None if n < min_posts else max(hs.items(), key=lambda kv: kv[1][0] / kv[1][1])[0]
    return out
