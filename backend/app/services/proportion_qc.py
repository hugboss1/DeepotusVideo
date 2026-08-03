"""v1.25 (Atelier DA) — contrôle qualité des PROPORTIONS + leçons apprises.

Leçon des tests A/B canons (2026-07-08): même avec le cadre vertical et des
prompts renforcés, la diffusion peut rendre un corps tassé (grosse tête,
jambes courtes) ou couper les pieds. Boucle de contrôle:
1. measure()  — un LLM vision estime le nombre de TÊTES du personnage en
   pied (hauteur totale / hauteur de tête) et si les pieds sont visibles;
2. judge()    — verdict contre la plage attendue du canon (canon["heads"]);
3. hors canon → l'appelant régénère UNE fois avec corrective_clause() et
   garde la meilleure tentative (better());
4. record_lesson() — l'erreur est persistée par canon (réglage atelier
   "canon_lessons"); lesson_hint() ré-applique d'office la consigne
   corrective aux générations suivantes du même canon: l'agent apprend de
   ses erreurs et ne les reproduit plus.

Toujours best-effort: sans clé vision ou sur erreur, measure() rend None et
le pipeline continue sans QC (jamais bloquant).
"""
import base64
import json
import re

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

_VISION_PROMPT = (
    "You are a strict art-school proportion checker. Look at the standing "
    "character in this reference image. Estimate the figure's proportions "
    "in HEAD-LENGTHS: total visible body height divided by head height "
    "(top of skull to chin, hair volume excluded). Also report whether the "
    "FULL body is visible. Return ONLY JSON: {\"heads\": <float>, "
    "\"full_body\": <true|false>, \"feet_visible\": <true|false>}")


def _img_payload(path) -> tuple[str, str]:
    data = path.read_bytes()
    media = "image/png" if data[:8].startswith(b"\x89PNG") else "image/jpeg"
    return base64.b64encode(data).decode(), media


def _parse(out: str) -> dict | None:
    m = re.search(r"\{.*\}", out or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        heads = float(d.get("heads"))
        return {"heads": heads, "full_body": bool(d.get("full_body")),
                "feet_visible": bool(d.get("feet_visible", d.get("full_body")))}
    except Exception:
        return None


def _anthropic_vision(b64: str, media: str) -> str | None:
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": settings.ANTHROPIC_MODEL, "max_tokens": 200,
                  "messages": [{"role": "user", "content": [
                      {"type": "image", "source": {
                          "type": "base64", "media_type": media,
                          "data": b64}},
                      {"type": "text", "text": _VISION_PROMPT}]}]},
            timeout=45.0, verify=SSL_VERIFY)
        if r.status_code != 200:
            logger.warning(f"proportion_qc[anthropic] HTTP {r.status_code}")
            return None
        return "".join(b.get("text", "") for b in r.json().get("content", [])
                       if b.get("type") == "text")
    except Exception as e:
        logger.warning(f"proportion_qc[anthropic] {e}")
        return None


def _openai_vision(b64: str, media: str) -> str | None:
    try:
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={"model": "gpt-4o-mini", "max_tokens": 200,
                  "messages": [{"role": "user", "content": [
                      {"type": "text", "text": _VISION_PROMPT},
                      {"type": "image_url", "image_url": {
                          "url": f"data:{media};base64,{b64}"}}]}]},
            timeout=45.0, verify=SSL_VERIFY)
        if r.status_code != 200:
            logger.warning(f"proportion_qc[openai] HTTP {r.status_code}")
            return None
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"proportion_qc[openai] {e}")
        return None


def measure(image_path) -> dict | None:
    """Mesure vision {heads, full_body, feet_visible} — None si indisponible.
    Appel SYNCHRONE (2-5 s): l'appelant async passe par asyncio.to_thread."""
    try:
        b64, media = _img_payload(image_path)
    except Exception as e:
        logger.warning(f"proportion_qc read {image_path}: {e}")
        return None
    out = None
    if (settings.ANTHROPIC_API_KEY or "").strip():
        out = _anthropic_vision(b64, media)
    if not out and (settings.OPENAI_API_KEY or "").strip():
        out = _openai_vision(b64, media)
    return _parse(out) if out else None


def judge(m: dict | None, canon: dict) -> dict | None:
    """Verdict contre la plage canon["heads"]. None = QC indisponible.

    Leçon éval 2026-07-08: l'estimation vision du nombre de têtes est
    fiable sur les canons réalistes/élancés mais BRUITÉE sur les canons
    caricaturaux à grosse tête (chibi, gros nez: ±2 têtes mesurées sur des
    figures pourtant correctes). Pour les canons courts (hi ≤ 6) on ne
    juge donc que le cadrage (figure entière, pieds visibles) — le
    comptage strict est réservé aux canons ≥ 6 têtes, là où le tassement
    est réellement le risque."""
    rng = canon.get("heads")
    if not m or not rng:
        return None
    lo, hi = rng
    if not m.get("full_body") or not m.get("feet_visible"):
        return {"ok": False, "heads": m["heads"], "range": rng,
                "note": "figure coupée (pieds hors cadre)"}
    if hi <= 6:      # canon caricatural: cadrage seul (comptage bruité)
        return {"ok": True, "heads": m["heads"], "range": rng, "note": "ok"}
    if m["heads"] < lo:
        return {"ok": False, "heads": m["heads"], "range": rng,
                "note": f"corps tassé: {m['heads']:.1f} têtes mesurées, "
                        f"canon {lo}-{hi}"}
    if m["heads"] > hi:
        return {"ok": False, "heads": m["heads"], "range": rng,
                "note": f"corps trop étiré: {m['heads']:.1f} têtes, "
                        f"canon {lo}-{hi}"}
    return {"ok": True, "heads": m["heads"], "range": rng, "note": "ok"}


def corrective_clause(verdict: dict, canon: dict) -> str:
    """Consigne corrective ajoutée au prompt de régénération — nommant
    l'erreur mesurée (le modèle corrige mieux une erreur explicite)."""
    lo, hi = verdict["range"]
    if "coupée" in verdict["note"]:
        return ("PREVIOUS ATTEMPT FAILED: the feet were cropped out of "
                "frame. Zoom out further: the whole figure including the "
                "feet MUST be inside the frame with empty space below the "
                "feet")
    if verdict["heads"] < lo:
        return (f"PREVIOUS ATTEMPT FAILED: the figure was squashed at only "
                f"{verdict['heads']:.1f} head-lengths tall. Render the SAME "
                f"character but STRETCHED to {lo}-{hi} heads tall: much "
                f"smaller head, much longer legs, elongated silhouette")
    return (f"PREVIOUS ATTEMPT FAILED: the figure was stretched to "
            f"{verdict['heads']:.1f} head-lengths. Render the SAME "
            f"character but at {lo}-{hi} heads tall, natural canon "
            f"proportions")


def better(v2: dict | None, v1: dict) -> bool:
    """La tentative 2 est-elle meilleure? (v2 ok, ou plus proche du canon)"""
    if not v2:
        return False
    if v2["ok"]:
        return True
    if v1["ok"]:
        return False

    def dist(v):
        lo, hi = v["range"]
        h = v.get("heads") or 0
        return lo - h if h < lo else (h - hi if h > hi else 0)
    return dist(v2) < dist(v1)


# ───────────── leçons persistées (réglage atelier "canon_lessons") ─────────
# {canon_id: {"fails": n, "streak_ok": n, "last_heads": x, "hint": "…"}}

def load_lessons(raw: str) -> dict:
    try:
        d = json.loads(raw or "{}")
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def dump_lessons(lessons: dict) -> str:
    return json.dumps(lessons, ensure_ascii=False)


def lesson_hint(lessons: dict, canon_key: str) -> str:
    """Consigne corrective apprise pour ce canon (vide si aucune)."""
    return (lessons.get(canon_key) or {}).get("hint") or ""


def record_lesson(lessons: dict, canon_key: str, verdict: dict,
                  fix: str) -> dict:
    """Échec QC: mémorise la consigne corrective — appliquée d'office aux
    prochaines générations de ce canon (l'erreur n'est plus reproduite)."""
    entry = lessons.get(canon_key) or {}
    entry["fails"] = int(entry.get("fails") or 0) + 1
    entry["streak_ok"] = 0
    entry["last_heads"] = verdict.get("heads")
    # la consigne apprise, débarrassée du préambule d'échec ponctuel
    entry["hint"] = ("PROPORTION GUARD (learned): "
                     + fix.split("FAILED: ", 1)[-1])
    lessons[canon_key] = entry
    return lessons


def record_success(lessons: dict, canon_key: str) -> dict:
    """QC ok: trace la réussite (la consigne apprise reste active — c'est
    souvent elle qui a corrigé le tir)."""
    entry = lessons.get(canon_key) or {}
    entry["streak_ok"] = int(entry.get("streak_ok") or 0) + 1
    lessons[canon_key] = entry
    return lessons
