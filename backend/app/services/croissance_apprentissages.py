# -*- coding: utf-8 -*-
"""t499 (G9, 26/11/2026) — `apprentissages.md` d'un espace, alimenté par les MESURES (boucle de croissance).

`bilan(items)` est PUR : à partir des posts mesurés d'un espace (le multiplicateur de t491 : vues au jalon contre
l'habituel du même compte, même canal, même format, même âge), il dit ce qui bat l'habituel :
- les FORMATS dont la médiane des multiplicateurs dépasse 1 (au moins `MIN_GROUPE` posts mesurés) ;
- les HEURES de mise en ligne (heure locale, `tz_min`) dont la médiane dépasse 1 (même minimum) ;
- les ACCROCHES des posts au-dessus de l'habituel (la `hook` du post, à défaut son titre), du plus fort au plus faible ;
- les gagnants (au moins `croissance.SEUIL_GAGNANT` fois l'habituel).
Rien n'est estimé ni prévu : un groupe trop petit n'est pas cité, et « pas assez de recul » est dit tel quel.

`bilan_md` le met en quelques lignes datées (un fait mesuré + ce qu'on en fait) ; `ajouter` les range sous
`campagnes/<espace>/apprentissages.md` (le fichier de l'ESPACE, à côté de ses dossiers de campagne), section par
section, le plus ancien retiré au-delà de `MAX_OCTETS`. `items_espace` lit les posts mesurés (lecture seule, aucun
relevé, aucune dépense)."""
from __future__ import annotations

import os
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import config
from app.services import croissance

MIN_GROUPE = 2                 # un format ou une heure se cite à partir de deux posts mesurés
MAX_ACCROCHES = 5
MAX_TEXTE = 140                # caractères d'une accroche citée
MAX_NOTES = 5                  # lignes ajoutées par l'agent (3 à 5 au bilan)
MAX_NOTE = 300
MAX_OCTETS = 40_000            # au-delà, les sections les plus anciennes partent
FICHIER = "apprentissages.md"
_ESPACE_OK = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_SECTION = re.compile(r"(?m)^## ")


def _mult(d: dict):
    m = (d.get("croissance") or {}).get("multiplicateur")
    return m if isinstance(m, (int, float)) and not isinstance(m, bool) else None


def _date(v):
    if isinstance(v, datetime):
        return v if v.tzinfo is None else v.astimezone(timezone.utc).replace(tzinfo=None)
    try:
        d = datetime.fromisoformat(str(v).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d.astimezone(timezone.utc).replace(tzinfo=None) if d.tzinfo else d


def _groupes(items: list, cle) -> list[dict]:
    g: dict = {}
    for d in items:
        m = _mult(d)
        k = cle(d)
        if m is None or k is None:
            continue
        g.setdefault(k, []).append(m)
    out = [{"cle": k, "posts": len(v), "mediane": round(statistics.median(v), 2)} for k, v in g.items()]
    return sorted(out, key=lambda x: (-x["mediane"], str(x["cle"])))


def _texte(v) -> str:
    t = re.sub(r"\s+", " ", str(v or "")).strip()
    return t[:MAX_TEXTE - 1] + "…" if len(t) > MAX_TEXTE else t


def bilan(items: list, *, tz_min: int = 0, seuil: float = croissance.SEUIL_GAGNANT) -> dict:
    """PUR. `items` : [{id, channel, format, posted_at, title, hook?, croissance: {multiplicateur, ...}}]."""
    items = [d for d in (items or []) if isinstance(d, dict)]
    mesures = [d for d in items if _mult(d) is not None]
    formats = _groupes(mesures, lambda d: str(d.get("format") or "post"))
    canaux = _groupes(mesures, lambda d: str(d.get("channel") or ""))

    def heure(d):
        p = _date(d.get("posted_at"))
        return None if p is None else (p + timedelta(minutes=int(tz_min or 0))).hour

    heures = _groupes(mesures, heure)
    vus, accroches = set(), []
    for d in sorted(mesures, key=lambda d: -_mult(d)):
        if _mult(d) <= 1:
            break
        t = _texte(d.get("hook") or d.get("title"))
        if not t or t.lower() in vus:
            continue
        vus.add(t.lower())
        accroches.append({"texte": t, "multiplicateur": round(_mult(d), 2), "canal": d.get("channel"),
                          "format": d.get("format") or "post", "id": d.get("id")})
        if len(accroches) >= MAX_ACCROCHES:
            break
    tous = [_mult(d) for d in mesures]
    return {
        "posts": len(items), "mesures": len(mesures),
        "sans_recul": sum(1 for d in items if (d.get("croissance") or {}).get("raison") == "peu_de_recul"),
        "mediane": round(statistics.median(tous), 2) if tous else None,
        "gagnants": sum(1 for m in tous if croissance.gagnant(m, seuil)), "seuil": seuil,
        "formats": [f for f in formats if f["posts"] >= MIN_GROUPE and f["mediane"] > 1],
        "heures": [h for h in heures if h["posts"] >= MIN_GROUPE and h["mediane"] > 1],
        "canaux": [c for c in canaux if c["posts"] >= MIN_GROUPE],
        "accroches": accroches,
    }


def _x(v: float, langue: str) -> str:
    s = f"{v:.1f}"
    return (s if langue == "en" else s.replace(".", ",")) + "×"


def bilan_md(b: dict, quand: datetime | None = None, langue: str = "fr", jours: int | None = None,
             notes: list | None = None) -> str:
    """Une section datée de quelques lignes ; chaque ligne = un fait mesuré + ce qu'on en fait."""
    en = langue == "en"
    jour = (quand or datetime.now()).strftime("%Y-%m-%d")
    fen = f" ({jours} {'days' if en else 'jours'})" if jours else ""
    l = [f"## {jour}{fen} — {'measured' if en else 'mesuré'}", ""]
    if not b.get("mesures"):
        l.append("- " + ("Not enough history yet: no post compared with its usual. Nothing to conclude."
                         if en else "Pas assez de recul : aucun post comparé à son habituel. Rien à conclure."))
    else:
        med = b.get("mediane")
        l.append("- " + (f"{b['mesures']} measured post(s), median {_x(med, langue)} the usual; {b['gagnants']} winner(s) "
                         f"(≥ {_x(b['seuil'], langue)})." if en else
                         f"{b['mesures']} post(s) mesuré(s), médiane {_x(med, langue)} l'habituel ; {b['gagnants']} "
                         f"gagnant(s) (≥ {_x(b['seuil'], langue)})."))
        for f in b.get("formats") or []:
            l.append("- " + (f"Format {f['cle']}: {_x(f['mediane'], langue)} over {f['posts']} posts → keep it."
                             if en else f"Format {f['cle']} : {_x(f['mediane'], langue)} sur {f['posts']} posts → "
                                        "le garder."))
        for h in b.get("heures") or []:
            l.append("- " + (f"Posted around {h['cle']}:00: {_x(h['mediane'], langue)} over {h['posts']} posts → keep "
                             "this slot." if en else
                             f"Mis en ligne vers {h['cle']} h : {_x(h['mediane'], langue)} sur {h['posts']} posts → "
                             "garder ce créneau."))
        for a in b.get("accroches") or []:
            l.append("- " + (f"Hook « {a['texte']} »: {_x(a['multiplicateur'], langue)} ({a['canal']}, {a['format']}) "
                             "→ reuse its angle." if en else
                             f"Accroche « {a['texte']} » : {_x(a['multiplicateur'], langue)} ({a['canal']}, "
                             f"{a['format']}) → en reprendre l'angle."))
        if b.get("sans_recul"):
            l.append("- " + (f"{b['sans_recul']} post(s) without enough history: not compared."
                             if en else f"{b['sans_recul']} post(s) sans assez de recul : non comparé(s)."))
    for n in (notes or [])[:MAX_NOTES]:
        t = re.sub(r"\s+", " ", str(n or "")).strip()[:MAX_NOTE]
        if t:
            l.append("- " + t)
    return "\n".join(l) + "\n"


def chemin(espace_id: str) -> Path:
    if not isinstance(espace_id, str) or not _ESPACE_OK.match(espace_id):
        raise ValueError(f"espace_id invalide : {espace_id!r}")
    return config.DATA_ROOT / "campagnes" / espace_id / FICHIER


def lire(espace_id: str) -> str:
    try:
        return chemin(espace_id).read_text(encoding="utf-8")
    except OSError:
        return ""


def ajouter(espace_id: str, section: str) -> dict:
    """Ajoute la section à la fin du fichier de l'espace (créé au besoin) ; au-delà de MAX_OCTETS, les sections les plus
    anciennes partent (l'en-tête reste)."""
    f = chemin(espace_id)
    ancien = lire(espace_id)
    entete = "# Apprentissages\n\n" if not ancien.strip() else ""
    texte = (ancien.rstrip("\n") + "\n\n" if ancien.strip() else entete) + section.strip("\n") + "\n"
    retirees = 0
    while len(texte.encode("utf-8")) > MAX_OCTETS:
        debuts = [m.start() for m in _SECTION.finditer(texte)]
        if len(debuts) < 2:
            break
        texte = texte[:debuts[0]] + texte[debuts[1]:]
        retirees += 1
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(texte, encoding="utf-8")
    os.replace(tmp, f)
    return {"chemin": f"campagnes/{espace_id}/{FICHIER}", "octets": len(texte.encode("utf-8")),
            "sections_retirees": retirees}


def tz_local_min() -> int:
    """Le décalage de l'heure locale de la machine, en minutes (les heures de mise en ligne se lisent en local)."""
    o = datetime.now().astimezone().utcoffset()
    return int(o.total_seconds() // 60) if o else 0


async def items_espace(espace_id: str, jours: int = 30) -> list[dict]:
    """Les posts mesurés de l'espace sur `jours` jours (metrics_service.analytics), avec leur accroche. Lecture seule."""
    from sqlalchemy import select
    from app.services import metrics_service as MS
    from app.services.storage import ScheduledPost, async_session_factory
    a = await MS.analytics(jours)
    items = [dict(d) for d in a.get("items") or [] if d.get("espace_id") == espace_id]
    ids = list({d["id"] for d in items})
    if ids:
        async with async_session_factory() as s:
            hooks = dict((await s.execute(select(ScheduledPost.id, ScheduledPost.hook)
                                          .where(ScheduledPost.id.in_(ids)))).all())
        for d in items:
            d["hook"] = hooks.get(d["id"])
    return items
