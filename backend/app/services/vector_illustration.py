"""Vectorlab — l'illustration IA : les moteurs, et le SVG rendu ÉDITABLE.

Trois remontées de l'utilisateur, le 07/09/2026, sur la première version :

1. « les moteurs de génération doivent refléter TOUS les moteurs dont je
   possède les clés, ou qui sont présents dans le reste de l'application. »
   Mesuré : la route ne lisait que `summarizer._available_providers()`, qui
   omet **ollama** — pourtant connu du reste de l'application
   (`marketing._PLAN_PRIORITY` le liste, `settings.has_ollama` le mesure).
   Et elle n'offrait qu'UN modèle par fournisseur, celui des Réglages.
   Ici : chaque fournisseur configuré est INTERROGÉ pour sa vraie liste de
   modèles (`/v1/models` chez Anthropic et OpenAI, `/v1beta/models` chez
   Google, `/api/tags` chez Ollama). Aucune liste n'est recopiée en dur —
   une liste recopiée ment le jour où le fournisseur en publie un autre.

2. « l'image générée ne correspond pas à ce que j'ai demandé. » Le modèle
   par défaut des Réglages est un PETIT modèle (rapide et bon marché, choisi
   pour résumer des articles) ; le SVG est une tâche difficile. Le choix du
   modèle est donc porté jusqu'à l'appel, et le sujet demandé est REPRIS
   dans la consigne (« le sujet doit être RECONNAISSABLE »).

3. « une fois générée l'illustration doit pouvoir être éditable
   vectoriellement, les lignes, les formes… et je dois pouvoir la
   sélectionner, la déplacer, la redimensionner comme toute autre forme. »
   Mesuré : le client posait les tracés bruts sous un groupe portant un
   `transform` d'échelle — un déplacement de 100 px du document en valait
   100 × k à l'écran, et l'outil Nœuds ne lit que M/L/C/Q/Z absolus, alors
   que les modèles écrivent `m`, `h`, `v`, `s`, `a`… Ce module NORMALISE
   donc : toute commande devient M/L/C/Q/Z **absolue** (les arcs sont
   convertis en cubiques), et les `rect`/`circle`/`ellipse`/`polygon` sont
   rendus comme des objets typés du document. Le client peut alors les
   poser SANS transform : ils se déplacent, se redimensionnent et s'éditent
   au nœud comme un rectangle tracé à la main.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

import httpx
from loguru import logger

from app.config import SSL_VERIFY, settings

# ── les moteurs ────────────────────────────────────────────────────────
# L'ordre est celui du reste de l'application (marketing._PLAN_PRIORITY).
MOTEURS = ("anthropic", "openai", "gemini", "ollama")

_CATALOGUE: dict[str, list[str]] = {}      # cache de session, par moteur


def cle_de(moteur: str) -> str:
    return {
        "anthropic": settings.ANTHROPIC_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
        "ollama": settings.OLLAMA_MODEL,     # local : le modèle EST la clé
    }.get(moteur, "").strip()


def modele_defaut(moteur: str) -> str:
    return {
        "anthropic": settings.ANTHROPIC_MODEL,
        "openai": settings.OPENAI_MODEL,
        "gemini": settings.GEMINI_MODEL,
        "ollama": settings.OLLAMA_MODEL,
    }.get(moteur, "").strip()


def moteurs_configures() -> list[str]:
    return [m for m in MOTEURS if cle_de(m)]


# Les modèles qu'un fournisseur publie et qui ne savent pas tenir une
# conversation (plongements, images, audio, modération) : le sélecteur d'une
# illustration VECTORIELLE n'a rien à en faire.
_HORS_TEXTE = ("embed", "embedding", "whisper", "tts", "audio", "moderation",
               "dall-e", "image", "vision-preview", "realtime", "search",
               "aqa", "veo", "imagen")


def _texte_seulement(ids: list[str]) -> list[str]:
    return [i for i in ids if not any(h in i.lower() for h in _HORS_TEXTE)]


def modeles_de(moteur: str, *, timeout: float = 6.0) -> list[str]:
    """La VRAIE liste du fournisseur, jamais une liste recopiée.

    Le modèle des Réglages est toujours en tête : c'est celui que le reste
    de l'application emploie, et il doit rester à un clic. Le réseau peut
    échouer (hors ligne, jeton périmé) — dans ce cas la liste se réduit à ce
    seul modèle, et l'écran reste utilisable.
    """
    if moteur in _CATALOGUE:
        return _CATALOGUE[moteur]
    defaut = modele_defaut(moteur)
    ids: list[str] = []
    try:
        if moteur == "anthropic":
            r = httpx.get("https://api.anthropic.com/v1/models?limit=100",
                          headers={"x-api-key": settings.ANTHROPIC_API_KEY,
                                   "anthropic-version": "2023-06-01"},
                          timeout=timeout, verify=SSL_VERIFY)
            if r.status_code == 200:
                ids = [m.get("id", "") for m in (r.json().get("data") or [])]
        elif moteur == "openai":
            r = httpx.get("https://api.openai.com/v1/models",
                          headers={"Authorization":
                                   f"Bearer {settings.OPENAI_API_KEY}"},
                          timeout=timeout, verify=SSL_VERIFY)
            if r.status_code == 200:
                ids = [m.get("id", "") for m in (r.json().get("data") or [])]
        elif moteur == "gemini":
            from app.services.gemini_llm import _headers
            from app.services.google_video import GOOGLE_API_BASE
            r = httpx.get(f"{GOOGLE_API_BASE}/models", headers=_headers(),
                          timeout=timeout, verify=SSL_VERIFY)
            if r.status_code == 200:
                ids = [str(m.get("name", "")).split("/")[-1]
                       for m in (r.json().get("models") or [])
                       if "generateContent" in (m.get(
                           "supportedGenerationMethods") or [])]
        elif moteur == "ollama":
            r = httpx.get(f"{settings.OLLAMA_URL.rstrip('/')}/api/tags",
                          timeout=timeout, verify=SSL_VERIFY)
            if r.status_code == 200:
                ids = [m.get("name", "") for m in (r.json().get("models") or [])]
    except Exception as e:                                  # noqa: BLE001
        logger.warning(f"vectorlab: liste des modèles {moteur} indisponible: {e}")
    ids = _texte_seulement([i for i in ids if i])
    ids.sort()
    if defaut:
        ids = [defaut] + [i for i in ids if i != defaut]
    if not ids and defaut:
        ids = [defaut]
    _CATALOGUE[moteur] = ids
    return ids


def catalogue(*, timeout: float = 6.0) -> list[dict]:
    """`[{moteur, modeles: [...], defaut}]` pour les moteurs configurés."""
    out = []
    for m in moteurs_configures():
        mods = modeles_de(m, timeout=timeout)
        out.append({"moteur": m, "modeles": mods,
                    "defaut": modele_defaut(m) or (mods[0] if mods else "")})
    return out


def tirer(moteur: str, modele: str, prompt: str, systeme: str,
          max_tokens: int = 4000, *, timeout: float = 90.0) -> str:
    """UN appel, au moteur ET au modèle demandés — jamais un repli muet.

    Lève `RuntimeError` avec la cause : l'écran vient d'afficher le nom du
    modèle qui va dépenser la clé, un repli silencieux le ferait mentir.
    """
    mod = (modele or modele_defaut(moteur)).strip()
    if not mod:
        raise RuntimeError(f"aucun modèle pour « {moteur} »")
    if moteur == "anthropic":
        body = {"model": mod, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        if systeme:
            body["system"] = systeme
        r = httpx.post("https://api.anthropic.com/v1/messages",
                       headers={"x-api-key": settings.ANTHROPIC_API_KEY,
                                "anthropic-version": "2023-06-01",
                                "content-type": "application/json"},
                       json=body, timeout=timeout, verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"Anthropic HTTP {r.status_code} — "
                               f"{r.text[:200]}")
        return "".join(b.get("text", "") for b in (r.json().get("content") or [])
                       if b.get("type") == "text")
    if moteur == "openai":
        msgs = ([{"role": "system", "content": systeme}] if systeme else []) \
            + [{"role": "user", "content": prompt}]
        r = httpx.post("https://api.openai.com/v1/chat/completions",
                       headers={"Authorization":
                                f"Bearer {settings.OPENAI_API_KEY}",
                                "Content-Type": "application/json"},
                       json={"model": mod, "max_tokens": max_tokens,
                             "messages": msgs},
                       timeout=timeout, verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"OpenAI HTTP {r.status_code} — {r.text[:200]}")
        ch = r.json().get("choices") or []
        return (ch[0].get("message", {}).get("content", "") if ch else "")
    if moteur == "gemini":
        from app.services.gemini_llm import _headers
        from app.services.google_video import GOOGLE_API_BASE
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens}}
        if systeme:
            body["systemInstruction"] = {"parts": [{"text": systeme}]}
        r = httpx.post(f"{GOOGLE_API_BASE}/models/{mod}:generateContent",
                       headers=_headers(), json=body, timeout=timeout,
                       verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"Gemini HTTP {r.status_code} — {r.text[:200]}")
        cand = r.json().get("candidates") or []
        parts = (cand[0].get("content", {}).get("parts", []) if cand else [])
        return "".join(p.get("text", "") for p in parts)
    if moteur == "ollama":
        r = httpx.post(f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
                       json={"model": mod, "prompt": prompt, "system": systeme,
                             "stream": False},
                       timeout=timeout, verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {r.status_code} — {r.text[:200]}")
        return str(r.json().get("response") or "")
    raise RuntimeError(f"moteur inconnu : {moteur}")


# ── le SVG rendu ÉDITABLE ──────────────────────────────────────────────
# `chemin_parser` du client (mod-doc.js) ne lit que M/L/C/Q/Z ABSOLUS : sans
# la normalisation qui suit, l'outil Nœuds ne peut pas mordre sur ce que le
# modèle écrit (`m`, `h`, `v`, `s`, `t`, `a`, minuscules et implicites).

_NOMBRE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_JETON = re.compile(r"([MmZzLlHhVvCcSsQqTtAa])|"
                    r"([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)")
_ARITE = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2,
          "A": 7, "Z": 0}


def _nb(x: float) -> str:
    """Arrondi à deux décimales, sans le piège flottant, sans zéro final.

    Même convention que `chemin_serialiser` du client : les deux écritures
    doivent se relire l'une l'autre sans dérive."""
    v = round(float(f"{x * 100:.12g}")) / 100
    return f"{v:g}"


def _arc_en_cubiques(x0, y0, rx, ry, phi, grand, sens, x, y):
    """Arc elliptique SVG → suite de cubiques (F.6.5 de la spec SVG).

    Les modèles écrivent des `a` pour arrondir un pétale ; le client ne sait
    pas les lire. La conversion est exacte à la découpe en quadrants près.
    """
    if rx == 0 or ry == 0 or (x0 == x and y0 == y):
        return [("L", [x, y])]
    rx, ry = abs(rx), abs(ry)
    ph = math.radians(phi % 360)
    cos_p, sin_p = math.cos(ph), math.sin(ph)
    dx2, dy2 = (x0 - x) / 2.0, (y0 - y) / 2.0
    x1 = cos_p * dx2 + sin_p * dy2
    y1 = -sin_p * dx2 + cos_p * dy2
    lam = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if grand == sens:
        co = -co
    cx1 = co * rx * y1 / ry
    cy1 = -co * ry * x1 / rx
    cx = cos_p * cx1 - sin_p * cy1 + (x0 + x) / 2.0
    cy = sin_p * cx1 + cos_p * cy1 + (y0 + y) / 2.0

    def ang(ux, uy, vx, vy):
        n = math.hypot(ux, uy) * math.hypot(vx, vy)
        if n == 0:
            return 0.0
        c = max(-1.0, min(1.0, (ux * vx + uy * vy) / n))
        a = math.acos(c)
        return -a if ux * vy - uy * vx < 0 else a

    th1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dth = ang((x1 - cx1) / rx, (y1 - cy1) / ry,
              (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sens and dth > 0:
        dth -= 2 * math.pi
    elif sens and dth < 0:
        dth += 2 * math.pi
    n = max(1, int(math.ceil(abs(dth) / (math.pi / 2))))
    d = dth / n
    t = 4.0 / 3.0 * math.tan(d / 4.0)
    out = []
    th = th1
    px, py = x0, y0
    for _ in range(n):
        th2 = th + d
        c1, s1 = math.cos(th), math.sin(th)
        c2, s2 = math.cos(th2), math.sin(th2)

        def pt(c, s):
            return (cos_p * rx * c - sin_p * ry * s + cx,
                    sin_p * rx * c + cos_p * ry * s + cy)

        ex, ey = pt(c2, s2)
        d1x, d1y = (-rx * s1, ry * c1)
        d2x, d2y = (-rx * s2, ry * c2)
        k1x = px + t * (cos_p * d1x - sin_p * d1y)
        k1y = py + t * (sin_p * d1x + cos_p * d1y)
        k2x = ex - t * (cos_p * d2x - sin_p * d2y)
        k2y = ey - t * (sin_p * d2x + cos_p * d2y)
        out.append(("C", [k1x, k1y, k2x, k2y, ex, ey]))
        px, py, th = ex, ey, th2
    return out


def normaliser_chemin(d: str) -> str:
    """Tout `d` SVG → M/L/C/Q/Z **absolus**, lisibles par le client.

    Rend `""` si rien d'exploitable : l'appelant écarte le tracé plutôt que
    de poser une forme muette.
    """
    jetons = []
    for m in _JETON.finditer(d or ""):
        jetons.append(m.group(1) or float(m.group(2)))
    if not jetons or not isinstance(jetons[0], str):
        return ""
    out: list[tuple[str, list[float]]] = []
    i, cmd = 0, ""
    cx = cy = sx = sy = 0.0
    prev_c = prev_q = None
    while i < len(jetons):
        if isinstance(jetons[i], str):
            cmd = jetons[i]
            i += 1
            if cmd in "Zz":
                out.append(("Z", []))
                cx, cy = sx, sy
                prev_c = prev_q = None
                continue
        if not cmd:
            break
        maj = cmd.upper()
        rel = cmd.islower()
        n = _ARITE.get(maj, 0)
        if i + n > len(jetons):
            break
        a = jetons[i:i + n]
        if any(isinstance(v, str) for v in a):
            break
        i += n
        if maj == "M":
            x, y = (cx + a[0], cy + a[1]) if rel else (a[0], a[1])
            out.append(("M", [x, y]))
            cx, cy = sx, sy = x, y
            cmd = "l" if rel else "L"      # implicites SVG : M puis L
            prev_c = prev_q = None
        elif maj == "L":
            x, y = (cx + a[0], cy + a[1]) if rel else (a[0], a[1])
            out.append(("L", [x, y]))
            cx, cy = x, y
            prev_c = prev_q = None
        elif maj == "H":
            x = cx + a[0] if rel else a[0]
            out.append(("L", [x, cy]))
            cx = x
            prev_c = prev_q = None
        elif maj == "V":
            y = cy + a[0] if rel else a[0]
            out.append(("L", [cx, y]))
            cy = y
            prev_c = prev_q = None
        elif maj == "C":
            p = [cx + a[0], cy + a[1], cx + a[2], cy + a[3],
                 cx + a[4], cy + a[5]] if rel else list(a)
            out.append(("C", p))
            prev_c = (p[2], p[3])
            prev_q = None
            cx, cy = p[4], p[5]
        elif maj == "S":
            k1 = (2 * cx - prev_c[0], 2 * cy - prev_c[1]) if prev_c else (cx, cy)
            p2 = [cx + a[0], cy + a[1], cx + a[2], cy + a[3]] if rel else list(a)
            p = [k1[0], k1[1], p2[0], p2[1], p2[2], p2[3]]
            out.append(("C", p))
            prev_c = (p[2], p[3])
            prev_q = None
            cx, cy = p[4], p[5]
        elif maj == "Q":
            p = [cx + a[0], cy + a[1], cx + a[2], cy + a[3]] if rel else list(a)
            out.append(("Q", p))
            prev_q = (p[0], p[1])
            prev_c = None
            cx, cy = p[2], p[3]
        elif maj == "T":
            k = (2 * cx - prev_q[0], 2 * cy - prev_q[1]) if prev_q else (cx, cy)
            x, y = (cx + a[0], cy + a[1]) if rel else (a[0], a[1])
            out.append(("Q", [k[0], k[1], x, y]))
            prev_q = k
            prev_c = None
            cx, cy = x, y
        elif maj == "A":
            x, y = (cx + a[5], cy + a[6]) if rel else (a[5], a[6])
            for seg in _arc_en_cubiques(cx, cy, a[0], a[1], a[2],
                                        bool(a[3]), bool(a[4]), x, y):
                out.append(seg)
            cx, cy = x, y
            prev_c = prev_q = None
    if not out or out[0][0] != "M":
        return ""
    return " ".join(c + ("" if not p else " " + " ".join(_nb(v) for v in p))
                    for c, p in out)


_FILL = re.compile(r"fill:\s*([^;]+)")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_HEX3 = re.compile(r"^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$")
# Le fond de secours quand le modèle n'en donne pas : l'or du vitrail.
FOND_DEFAUT = "#c9a33f"


def _fond(el) -> str | None:
    f = el.get("fill")
    if not f:
        m = _FILL.search(el.get("style") or "")
        f = m.group(1).strip() if m else None
    if not f:
        return FOND_DEFAUT
    f = f.strip()
    if f.lower() in ("none", "transparent"):
        return None
    if _HEX.match(f):
        return f.lower()
    m3 = _HEX3.match(f)
    if m3:
        return ("#" + m3.group(1) * 2 + m3.group(2) * 2 + m3.group(3) * 2).lower()
    return FOND_DEFAUT       # `red`, `rgb(…)`, un dégradé : on ne devine pas


def _f(el, nom, defaut=0.0) -> float:
    try:
        return float(str(el.get(nom, defaut)).strip() or defaut)
    except ValueError:
        return defaut


MAX_FORMES = 60


def formes_du_svg(txt: str) -> tuple[list[dict], list[float]]:
    """Le SVG du modèle → formes TYPÉES du document, et son viewBox.

    Chaque forme est déjà au vocabulaire de `mod-doc` : `path` (M/L/C/Q/Z
    absolus), `rect`, `ellipse`. Rien de la réponse brute ne franchit cette
    fonction : ni style, ni contour, ni transform, ni élément inconnu.
    """
    txt = re.sub(r"```[a-z]*", "", str(txt or ""), flags=re.I)
    m = re.search(r"<svg[\s\S]*?</svg>", txt, re.I)
    vb = [0.0, 0.0, 100.0, 100.0]
    formes: list[dict] = []
    racine = None
    if m:
        try:
            racine = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", m.group(0)))
        except ET.ParseError as e:
            logger.warning(f"vectorlab: SVG du modèle illisible ({e})")
    if racine is not None:
        try:
            raw = [float(v) for v in re.split(r"[\s,]+",
                                              (racine.get("viewBox") or "").strip())
                   if v]
            if len(raw) == 4 and raw[2] > 0 and raw[3] > 0:
                vb = raw
        except ValueError:
            pass
        for el in racine.iter():
            if len(formes) >= MAX_FORMES:
                break
            bal = el.tag.split("}")[-1].lower()
            if bal not in ("path", "polygon", "polyline", "rect", "circle",
                           "ellipse", "line"):
                continue
            fond = _fond(el)
            if fond is None:
                continue
            if bal == "path":
                d = normaliser_chemin(el.get("d") or "")
                if d:
                    formes.append({"type": "path", "d": d,
                                   "style": {"fond": fond}})
            elif bal in ("polygon", "polyline"):
                pts = [float(v) for v in
                       re.findall(_NOMBRE, el.get("points") or "")]
                if len(pts) >= 6:
                    d = "M " + " L ".join(
                        f"{_nb(pts[k])} {_nb(pts[k + 1])}"
                        for k in range(0, len(pts) - 1, 2))
                    formes.append({"type": "path", "d": d + " Z",
                                   "style": {"fond": fond}})
            elif bal == "rect":
                w, h = _f(el, "width"), _f(el, "height")
                if w > 0 and h > 0:
                    o = {"type": "rect", "x": _f(el, "x"), "y": _f(el, "y"),
                         "w": w, "h": h, "style": {"fond": fond}}
                    rx = _f(el, "rx")
                    if rx > 0:
                        o["rx"] = rx
                    formes.append(o)
            elif bal == "circle":
                r = _f(el, "r")
                if r > 0:
                    formes.append({"type": "ellipse", "cx": _f(el, "cx"),
                                   "cy": _f(el, "cy"), "rx": r, "ry": r,
                                   "style": {"fond": fond}})
            elif bal == "ellipse":
                rx, ry = _f(el, "rx"), _f(el, "ry")
                if rx > 0 and ry > 0:
                    formes.append({"type": "ellipse", "cx": _f(el, "cx"),
                                   "cy": _f(el, "cy"), "rx": rx, "ry": ry,
                                   "style": {"fond": fond}})
            elif bal == "line":
                formes.append({"type": "path",
                               "d": f"M {_nb(_f(el, 'x1'))} {_nb(_f(el, 'y1'))}"
                                    f" L {_nb(_f(el, 'x2'))} {_nb(_f(el, 'y2'))}",
                               "style": {"fond": "none", "contour": fond,
                                         "epaisseur": 1}})
    if not formes:
        # Repli : le modèle a répondu hors balise (texte nu, SVG tronqué).
        for mm in re.finditer(r'<path[^>]*\sd="([^"]+)"[^>]*>', txt, re.I):
            d = normaliser_chemin(mm.group(1))
            if not d:
                continue
            mf = re.search(r'fill="(#[0-9a-fA-F]{3,6})"', mm.group(0))
            formes.append({"type": "path", "d": d,
                           "style": {"fond": (mf.group(1).lower() if mf
                                              else FOND_DEFAUT)}})
            if len(formes) >= MAX_FORMES:
                break
    return formes, vb


def consigne(sujet: str) -> str:
    """La consigne envoyée au modèle.

    Le §9 du handoff la fixe presque mot pour mot ; deux ajouts, motivés par
    la remontée « l'image générée ne correspond pas à ce que j'ai demandé » :
    le sujet est REDIT à la fin (les modèles suivent mieux une contrainte
    quand la cible ferme la consigne), et la reconnaissance du sujet est
    posée comme critère explicite.
    """
    s = (sujet or "").strip()[:400]
    return (
        "Illustration vectorielle pour un atelier de vitrail. Sujet : "
        + s + ".\n"
        "Réponds UNIQUEMENT par le code SVG, rien avant, rien après, pas de "
        "bloc de code.\n"
        'Format exact : <svg viewBox="0 0 100 100"> puis uniquement des '
        '<path d="..." fill="#rrggbb"/> puis </svg>.\n'
        "Contraintes : de 5 à 22 tracés ; chemins fermés remplis, aucun "
        "stroke, aucun gradient, aucune opacité ; masses simples comme des "
        "pièces de verre découpées ; palette de 4 à 6 couleurs saturées de "
        "verre coloré.\n"
        "Le sujet doit être RECONNAISSABLE au premier coup d'œil : compose "
        "les masses en une silhouette lisible de « " + s + " », occupe tout "
        "le viewBox, et n'ajoute aucun décor qui ne serve pas ce sujet.")
