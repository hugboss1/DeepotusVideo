# -*- coding: utf-8 -*-
"""t319 (28/10/2026) (lot D5 « tutoriels et parcours partagés depuis les captures ») — plan
docs/superpowers/plans/2026-10-28-t319-tutoriels.md, spec 2026-10-25-boite-a-outils-design.md §8.7.

1. Le BROUILLON DE TUTORIEL d'une capture close (t315) : un chapitre par écran, une étape par geste (un zoom du montage
   de t317), sa fiche du catalogue de « Demander » (celle du clic non masqué le plus proche), un titre et une phrase
   courte FR/EN, ses trois temps (t0, t, t1 en ms de la source). Gardé dans `captures/<id>/tutoriel.json`.
2. La FABRICATION des brouillons dans les formats existants, sans rien publier : scènes du guide (`scene.json` à trois
   temps + fragment de chapitre), fiches didactiques des labs (`index.json` + WebP 320 × 200 à trois images), exemples
   de parcours réels pour le catalogue. Dans `tutoriels/<id>/`, refait à chaque fois.
3. Le PARCOURS PARTAGÉ `.dzparcours` (zip : parcours.json, clics.json, video.webm|mp4) : export, et import dans une
   autre installation. Un parcours importé est une DONNÉE NON FIABLE : noms d'entrées en liste blanche, tailles bornées
   EN LISANT, JSON relu champ par champ, vidéo reconnue par ses octets magiques, aucun chemin de l'archive repris. Le
   rejeu ne garde du fichier que l'identifiant de fiche : l'action (sélecteur, texte cherché) vient du catalogue LOCAL.

Aucun réseau, aucune dépense. Journaux : identifiants et nombres seulement."""
from __future__ import annotations

import html
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import unicodedata
import zipfile
from pathlib import Path

from app.config import DATA_ROOT
from app.services import capture as C
from app.services import capture_montage as M

VERSION = 1
MAX_ETAPES = 60
MAX_CHAPITRES = 100
MAX_TITRE = 80
MAX_PHRASE = 200
MAX_MOTS = 25                        # la phrase « pour un enfant de cinq ans » des fiches didactiques
MAX_DUREE = 24 * 3600 * 1000
FICHE = re.compile(r"^[a-z0-9_-]+(\.[A-Za-z0-9_-]+){1,5}$")
ID_ETAPE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
PID = re.compile(r"^[a-f0-9]{16}$")
LABS = ("vectorlab", "spritelab", "tilelab", "photolab")
# un élément du catalogue sans localisateur : on le cherche parmi les contrôles par son libellé (catalogue LOCAL)
SELECTEUR_GENERIQUE = "button, a, [role=button], [role=tab], [role=menuitem], select, label"

# l'archive .dzparcours
NOM_PARCOURS, NOM_CLICS = "parcours.json", "clics.json"
VIDEOS = {"video.webm": b"\x1a\x45\xdf\xa3", "video.mp4": b"ftyp"}
MAX_PARCOURS_JSON = 512 * 1024
MAX_CLICS_JSON = 8 * 1024 * 1024
MAX_VIDEO = 2 * 1024 * 1024 * 1024        # 2 Go
MAX_ZIP = MAX_VIDEO + 16 * 1024 * 1024
MAX_EVTS = 20000

_VERROU = threading.Lock()


class RefusTutoriel(ValueError):
    """Un brouillon ou un parcours refusé : `statut` = le code HTTP. Levée avec un message littéral (L10)."""
    def __init__(self, message: str, statut: int = 400):
        super().__init__(message)
        self.statut = statut


def racine_brouillons() -> Path:
    return DATA_ROOT / "tutoriels"


def racine_parcours() -> Path:
    return DATA_ROOT / "parcours"


# ── petits outils ──

def _nb(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def _borne(v, lo, hi):
    return max(lo, min(hi, v))


def texte(v, n: int) -> str:
    """Un texte affichable : sans contrôle ni format Unicode (U+202E, zéro-largeur…), espaces réduits, borné."""
    if not isinstance(v, str):
        return ""
    v = "".join(" " if c.isspace() else c for c in v if c.isspace() or not unicodedata.category(c).startswith("C"))
    return " ".join(v.split())[:n]


def _bilingue(v, n: int) -> dict:
    v = v if isinstance(v, dict) else {}
    return {"fr": texte(v.get("fr"), n), "en": texte(v.get("en"), n)}


def mots(phrase: str, n: int = MAX_MOTS) -> str:
    m = phrase.split()
    return " ".join(m[:n]) if len(m) > n else phrase


def _fiche(v) -> str | None:
    return v if isinstance(v, str) and len(v) <= 80 and FICHE.match(v) else None


def _ecran(v) -> str:
    return v if isinstance(v, str) and C.ECRAN_SUR.match(v) else ""


def _catalogue() -> dict:
    try:
        from app.services import agent_aide
        return agent_aide.catalogue()
    except Exception:  # noqa: BLE001 — un catalogue illisible ne perd pas le brouillon
        return {}


def nom_fiche(fiche: str | None) -> dict:
    """Le nom affiché d'une fiche du catalogue LOCAL : libellé, sinon infobulle ({fr, en}, vides si inconnue)."""
    x = _catalogue().get(fiche or "") or {}
    lib, tip = x.get("libelle") or {}, x.get("infobulle") or {}
    return {k: texte(lib.get(k) or tip.get(k) or "", 60) for k in ("fr", "en")}


# ── 1. le brouillon ──

def _clic_proche(clics: list, z: dict) -> dict | None:
    dedans = [c for c in clics if z["t0"] <= c["t"] <= z["t1"]]
    pool = dedans or clics
    if not pool:
        return None
    mil = (z["t0"] + z["t1"]) / 2
    return min(pool, key=lambda c: (abs(c["t"] - mil), c["t"]))


def proposer(clics_doc, montage: dict | None = None) -> dict:
    """Le brouillon proposé d'après la piste des clics et le montage (enregistré, sinon proposé par t317)."""
    doc = clics_doc if isinstance(clics_doc, dict) else {}
    m = montage if isinstance(montage, dict) else M.proposer(doc)
    evts = [e for e in (doc.get("evenements") or []) if isinstance(e, dict)] \
        if isinstance(doc.get("evenements"), list) else []
    clics = [e for e in evts if e.get("type") == "clic" and not e.get("secret")
             and _nb(e.get("t")) is not None and _nb(e.get("x")) is not None and _nb(e.get("y")) is not None]
    etapes = []
    for i, z in enumerate(sorted(m.get("zooms") or [], key=lambda z: z["t0"])[:MAX_ETAPES]):
        c = _clic_proche(clics, z)
        if c is None:
            continue
        fiche = _fiche(c.get("fiche"))
        nom = nom_fiche(fiche)
        lu = texte(((c.get("cible") or {}).get("t") or (c.get("cible") or {}).get("i") or ""), 60)
        n = len(etapes) + 1
        titre = {"fr": f"Cliquer « {nom['fr'] or lu} »" if (nom["fr"] or lu) else f"Étape {n}",
                 "en": f"Click “{nom['en'] or lu}”" if (nom["en"] or lu) else f"Step {n}"}
        role = (_catalogue().get(fiche or "") or {}).get("role") or {}
        phrase = {k: mots(texte(role.get(k) or "", MAX_PHRASE)) for k in ("fr", "en")}
        t = int(c["t"])
        etapes.append({"id": f"e{n}", "garde": True, "t0": int(min(z["t0"], t)), "t": t, "t1": int(max(z["t1"], t)),
                       "x": round(float(c["x"]), 4), "y": round(float(c["y"]), 4), "ecran": _ecran(c.get("ecran")),
                       "fiche": fiche, "titre": titre, "phrase": phrase})
    chapitres = [{"t": int(h["t"]), "ecran": _ecran(h.get("ecran")), "titre": texte(h.get("titre"), MAX_TITRE)}
                 for h in sorted(m.get("chapitres") or [], key=lambda h: h["t"])][:MAX_CHAPITRES]
    cid = doc.get("id") if isinstance(doc.get("id"), str) and C.ID.match(doc["id"]) else ""
    return {"version": VERSION, "capture_id": cid, "titre": {"fr": "", "en": ""}, "chapitres": chapitres,
            "etapes": etapes}


def valider(doc, duree_ms) -> dict:
    """Le brouillon (envoyé par l'écran ou lu dans un parcours importé), relu par LISTE BLANCHE ; RefusTutoriel(400)
    s'il est illisible. Les champs inconnus sont retirés, les nombres bornés, les textes nettoyés."""
    if not isinstance(doc, dict) or doc.get("version") != VERSION or not isinstance(doc.get("etapes"), list) \
            or not isinstance(doc.get("chapitres", []), list):
        raise RefusTutoriel("Brouillon de tutoriel illisible.", 400)
    duree = int(_borne(_nb(duree_ms) or 0, 0, MAX_DUREE))
    if len(doc["etapes"]) > MAX_ETAPES or len(doc.get("chapitres") or []) > MAX_CHAPITRES:
        raise RefusTutoriel("Brouillon de tutoriel trop long.", 400)
    vus: set[str] = set()
    etapes = []
    for e in doc["etapes"]:
        if not isinstance(e, dict):
            raise RefusTutoriel("Brouillon de tutoriel illisible.", 400)
        t = _nb(e.get("t"))
        x, y = _nb(e.get("x")), _nb(e.get("y"))
        if t is None or x is None or y is None:
            raise RefusTutoriel("Brouillon de tutoriel illisible.", 400)
        t = int(_borne(t, 0, duree))
        t0 = int(_borne(_nb(e.get("t0")) if _nb(e.get("t0")) is not None else t, 0, t))
        t1 = int(_borne(_nb(e.get("t1")) if _nb(e.get("t1")) is not None else t, t, duree))
        i = e.get("id") if isinstance(e.get("id"), str) and ID_ETAPE.match(e["id"]) and e["id"] not in vus \
            else f"e{len(etapes) + 1}x{secrets.token_hex(2)}"
        vus.add(i)
        etapes.append({"id": i, "garde": e.get("garde") is not False, "t0": t0, "t": t, "t1": t1,
                       "x": round(float(_borne(x, 0, 1)), 4), "y": round(float(_borne(y, 0, 1)), 4),
                       "ecran": _ecran(e.get("ecran")), "fiche": _fiche(e.get("fiche")),
                       "titre": _bilingue(e.get("titre"), MAX_TITRE), "phrase": _bilingue(e.get("phrase"), MAX_PHRASE)})
    etapes.sort(key=lambda e: e["t"])
    chapitres = []
    for h in doc.get("chapitres") or []:
        if not isinstance(h, dict) or _nb(h.get("t")) is None:
            continue
        chapitres.append({"t": int(_borne(h["t"], 0, duree)), "ecran": _ecran(h.get("ecran")),
                          "titre": texte(h.get("titre"), MAX_TITRE)})
    chapitres.sort(key=lambda h: h["t"])
    cid = doc.get("capture_id")
    return {"version": VERSION, "capture_id": cid if isinstance(cid, str) and C.ID.match(cid) else "",
            "titre": _bilingue(doc.get("titre"), MAX_TITRE), "chapitres": chapitres, "etapes": etapes}


def _close(cid: str) -> dict:
    r = C.lire(cid)
    if r["session"].get("etat") != "terminee" or r["clics"] is None:
        raise C.RefusCapture("Cette capture n'est pas terminée.", 409)
    return r


def duree(r: dict) -> int:
    return int(r["clics"].get("duree_ms") or r["session"].get("duree_ms") or 0)


def _montage(cid: str, r: dict) -> dict:
    m = M.lire_montage(cid)
    try:
        return M.valider(m, duree(r), cid) if m is not None else M.proposer(r["clics"])
    except M.RefusMontage:
        return M.proposer(r["clics"])


def proposer_pour(cid: str) -> dict:
    r = _close(cid)
    b = proposer(r["clics"], _montage(cid, r))
    b["capture_id"] = cid
    return valider(b, duree(r))


def lire_brouillon(cid: str) -> tuple[dict, bool]:
    """(brouillon, propose) : l'enregistré relu par le serveur, sinon (absent ou abîmé) celui proposé."""
    r = _close(cid)
    f = C._dossier(cid) / "tutoriel.json"
    try:
        doc = json.loads(f.read_text("utf-8")) if f.is_file() else None
        if doc is not None:
            b = valider(doc, duree(r))
            b["capture_id"] = cid
            return b, False
    except (ValueError, OSError):
        pass
    return proposer_pour(cid), True


def ecrire_brouillon(cid: str, doc) -> dict:
    r = _close(cid)
    b = valider(doc, duree(r))
    b["capture_id"] = cid
    d = C._dossier(cid)
    fd, nom = tempfile.mkstemp(prefix="tutoriel.", suffix=".json.tmp", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(b, fh, ensure_ascii=False, indent=1)
    Path(nom).replace(d / "tutoriel.json")
    return b


# ── 2. la fabrication des brouillons (guide, fiches didactiques, exemples du catalogue) ──

def _image(src: Path, t_ms: int):
    """L'image de la vidéo à l'instant t (Pillow, RGB) ; la dernière image si t dépasse la fin."""
    from PIL import Image
    for decal in (0, 300, 1000):
        s = max(0.0, (t_ms - decal) / 1000)
        try:
            r = subprocess.run([M._ffmpeg(), "-v", "error", "-ss", f"{s:.3f}", "-i", str(src), "-frames:v", "1",
                                "-f", "image2pipe", "-vcodec", "png", "pipe:1"], capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            r = None
        if r is not None and r.returncode == 0 and r.stdout:
            im = Image.open(io.BytesIO(r.stdout))
            im.load()
            return im.convert("RGB")
    raise RefusTutoriel("La vidéo de la capture est illisible.", 422)


def _reduire(im, largeur_max: int = 1440):
    from PIL import Image
    if im.width <= largeur_max:
        return im
    h = round(im.height * largeur_max / im.width)
    return im.resize((largeur_max, h), Image.LANCZOS)


def _halo(im, x: float, y: float):
    """Le geste surligné : un anneau à la couleur de la marque autour du clic (x, y en 0..1)."""
    from PIL import ImageDraw
    im = im.copy()
    d = ImageDraw.Draw(im)
    r = max(12, round(min(im.width, im.height) * 0.035))
    cx, cy = x * im.width, y * im.height
    for k, couleur in ((r + 6, (240, 180, 41)), (r, (240, 180, 41))):
        d.ellipse([cx - k, cy - k, cx + k, cy + k], outline=couleur, width=max(3, r // 6))
    return im


def _vignette(im, x: float, y: float, l: int = 320, h: int = 200):
    """La fiche didactique : une fenêtre 16:10 autour du clic (40 % de la largeur), ramenée à 320 × 200."""
    from PIL import Image
    w = max(l, round(im.width * 0.4))
    hh = round(w * h / l)
    if hh > im.height:
        hh = im.height
        w = round(hh * l / h)
    x0 = int(_borne(x * im.width - w / 2, 0, max(0, im.width - w)))
    y0 = int(_borne(y * im.height - hh / 2, 0, max(0, im.height - hh)))
    return im.crop((x0, y0, x0 + w, y0 + hh)).resize((l, h), Image.LANCZOS)


def _ident_fiche(fiche: str | None, n: int) -> str:
    """L'id d'une fiche didactique : l'id DOM du localisateur local (« #outil »), sinon le dernier segment de la fiche."""
    x = _catalogue().get(fiche or "") or {}
    sel = ((x.get("localisateur") or {}).get("selecteur") or "") if isinstance(x.get("localisateur"), dict) else ""
    m = re.fullmatch(r"#([A-Za-z][A-Za-z0-9_-]{0,40})", sel or "")
    if m:
        return m.group(1)
    return (fiche.split(".")[-1] if fiche else f"etape{n}")[:40]


def _chapitre_html(b: dict, gardees: list, dossier_scene: str, lang: str) -> str:
    e_ = html.escape
    titre = b["titre"][lang] or ("Tutoriel" if lang == "fr" else "Tutorial")
    out = [f"<!-- brouillon t319 (capture {b['capture_id']}) : à relire avant publication (t320) -->",
           f"<h2>{e_(titre)}</h2>"]
    chap = b["chapitres"] or [{"t": 0, "ecran": "", "titre": ""}]
    for i, h in enumerate(chap):
        fin = chap[i + 1]["t"] if i + 1 < len(chap) else float("inf")
        dedans = [(n, e) for n, e in gardees if h["t"] <= e["t"] < fin]
        if not dedans:
            continue
        nomh = h["titre"] or (h["ecran"].replace("_", " ").replace("-", " ").capitalize() if h["ecran"] else str(i + 1))
        out.append(f"<h3>{e_(nomh)}</h3>")
        for n, e in dedans:
            out.append(f'<figure class="scene" data-scene="{e_(dossier_scene)}/etape-{n}"></figure>')
        out.append('<ol class="etapes">')
        for n, e in dedans:
            ph = e["phrase"][lang]
            out.append(f"<li>{e_(e['titre'][lang])}" + (f" : {e_(ph)}" if ph else "") + "</li>")
        out.append("</ol>")
    return "\n".join(out) + "\n"


def fabriquer(cid: str, doc=None) -> dict:
    """Écrit les brouillons de la capture dans `tutoriels/<cid>/` (dossier refait) : {scenes, fiches, exemples,
    dossier}. Rien n'est publié : le guide, les labs et le catalogue de l'application ne sont pas touchés."""
    r = _close(cid)
    b = valider(doc, duree(r)) if doc is not None else lire_brouillon(cid)[0]
    b["capture_id"] = cid
    gardees = [(n + 1, e) for n, e in enumerate([e for e in b["etapes"] if e["garde"]])]
    if not gardees:
        raise RefusTutoriel("Aucune étape gardée dans ce brouillon.", 409)
    src = M.remuxer(cid)
    base = racine_brouillons()
    base.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{cid}.", dir=base))
    try:
        sc = f"tuto-{cid[:8]}"
        fiches: dict[str, list] = {}
        exemples, vus = [], set()
        parcours = [e["fiche"] for _, e in gardees if e["fiche"]]
        for n, e in gardees:
            avant, geste, apres = (_reduire(_image(src, t)) for t in (e["t0"], e["t"], e["t1"]))
            geste_h = _halo(geste, e["x"], e["y"])
            ds = tmp / "guide" / "scenes" / sc / f"etape-{n}"
            ds.mkdir(parents=True)
            for nom, im in (("avant", avant), ("geste", geste_h), ("apres", apres)):
                im.save(ds / f"{nom}.webp", "WEBP", quality=82)
            bulle2 = e["phrase"] if (e["phrase"]["fr"] or e["phrase"]["en"]) else e["titre"]
            scene = {"titre": e["titre"], "legende": e["phrase"],
                     "captures": [{"fr": f"{k}.webp", "en": f"{k}.webp"} for k in ("avant", "geste", "apres")],
                     "taille": [geste.width, geste.height],
                     "temps": [{"capture": 0, "duree": 1.4},
                               {"capture": 1, "duree": 1.6, "curseur": [round(e["x"] * geste.width),
                                                                        round(e["y"] * geste.height)],
                                "clic": True, "bulle": e["titre"]},
                               {"capture": 2, "duree": 2.0, "bulle": bulle2}],
                     "brouillon": True, "source": {"capture": cid, "t": e["t"], "fiche": e["fiche"]}}
            (ds / "scene.json").write_text(json.dumps(scene, ensure_ascii=False, indent=2), "utf-8")
            if e["ecran"] in LABS:
                ident = _ident_fiche(e["fiche"], n)
                da = tmp / "aide" / e["ecran"]
                da.mkdir(parents=True, exist_ok=True)
                nomf = f"{e['ecran']}.{ident}.webp"
                if not any(x["id"] == ident for x in fiches.get(e["ecran"], [])):
                    ims = [_vignette(avant, e["x"], e["y"]), _vignette(geste_h, e["x"], e["y"]),
                           _vignette(apres, e["x"], e["y"])]
                    ims[0].save(da / nomf, "WEBP", save_all=True, append_images=ims[1:], duration=[1200, 1400, 1800],
                                loop=0, quality=85)
                    fiches.setdefault(e["ecran"], []).append({
                        "id": ident, "titre": texte(nom_fiche(e["fiche"])["fr"] or e["titre"]["fr"], 40),
                        "phrase": mots(e["phrase"]["fr"] or e["titre"]["fr"]), "fichier": nomf, "version": 1,
                        "titre_en": texte(nom_fiche(e["fiche"])["en"] or e["titre"]["en"], 40),
                        "phrase_en": mots(e["phrase"]["en"] or e["titre"]["en"]), "fichier_en": nomf,
                        "brouillon": True, "fiche": e["fiche"]})
            if e["fiche"] and e["fiche"] not in vus:
                vus.add(e["fiche"])
                i = parcours.index(e["fiche"])
                exemples.append({"fiche": e["fiche"], "ecran": e["ecran"], "etape": n, "t": e["t"],
                                 "titre": e["titre"], "parcours": parcours[max(0, i - 3):i + 4]})
        for lab, liste in fiches.items():
            (tmp / "aide" / lab / "index.json").write_text(
                json.dumps(sorted(liste, key=lambda x: x["id"]), ensure_ascii=False, indent=1), "utf-8")
        (tmp / "catalogue").mkdir()
        (tmp / "catalogue" / "exemples.json").write_text(json.dumps(
            {"version": 1, "capture": cid, "brouillon": True, "exemples": exemples}, ensure_ascii=False, indent=1), "utf-8")
        for lang in ("fr", "en"):
            (tmp / "guide" / f"chapitre.{lang}.html").write_text(_chapitre_html(b, gardees, sc, lang), "utf-8")
        (tmp / "brouillon.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), "utf-8")
        with _VERROU:
            final = base / cid
            vieux = None
            if final.exists():
                vieux = base / f".{cid}.vieux.{secrets.token_hex(3)}"
                final.replace(vieux)
            tmp.replace(final)
            if vieux is not None:
                shutil.rmtree(vieux, ignore_errors=True)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return {"scenes": len(gardees), "fiches": sum(len(v) for v in fiches.values()), "exemples": len(exemples),
            "dossier": f"tutoriels/{cid}"}


# ── 3. le parcours partagé .dzparcours ──

def _clics_reduits(evts, duree_ms: int) -> list[dict]:
    """La piste du parcours : clics (instant, place, écran, fiche), écrans et générations — ni libellé lu, ni job, ni
    chemin. Sert à l'export ET à la relecture d'un import (liste blanche)."""
    out = []
    fin = int(duree_ms) + 5000
    for e in (evts if isinstance(evts, list) else [])[:MAX_EVTS]:
        if not isinstance(e, dict):
            continue
        t = _nb(e.get("t"))
        if t is None or not 0 <= t <= fin:
            continue
        ty = e.get("type")
        if ty == "clic":
            x, y = _nb(e.get("x")), _nb(e.get("y"))
            if x is None or y is None:
                continue
            c = {"type": "clic", "t": int(t), "x": round(float(_borne(x, 0, 1)), 4),
                 "y": round(float(_borne(y, 0, 1)), 4), "ecran": _ecran(e.get("ecran")), "fiche": _fiche(e.get("fiche"))}
            if e.get("secret") is True:
                c["secret"], c["fiche"] = True, None
            out.append(c)
        elif ty == "ecran" and _ecran(e.get("ecran")):
            out.append({"type": "ecran", "t": int(t), "ecran": _ecran(e.get("ecran"))})
        elif ty in ("generation_debut", "generation_fin"):
            out.append({"type": ty, "t": int(t)})
    out.sort(key=lambda x: x["t"])
    return out


def _doc_parcours(b: dict, duree_ms: int, cadre, video: str) -> dict:
    cadre = cadre if isinstance(cadre, dict) else {}
    etapes = [dict((k, e[k]) for k in ("id", "t0", "t", "t1", "x", "y", "ecran", "fiche", "titre", "phrase"))
              for e in b["etapes"] if e.get("garde", True)]
    return {"format": "dzparcours", "version": VERSION, "titre": b["titre"], "duree_ms": int(duree_ms),
            "cadre": {"largeur": int(_borne(_nb(cadre.get("largeur")) or 0, 0, 16384)),
                      "hauteur": int(_borne(_nb(cadre.get("hauteur")) or 0, 0, 16384))},
            "video": video, "chapitres": b["chapitres"], "etapes": etapes}


def exporter(cid: str, doc=None) -> Path:
    """Écrit `tutoriels/<cid>/parcours-<cid8>.dzparcours` (zip : parcours.json, clics.json, vidéo de la scène)."""
    r = _close(cid)
    b = valider(doc, duree(r)) if doc is not None else lire_brouillon(cid)[0]
    if not any(e["garde"] for e in b["etapes"]):
        raise RefusTutoriel("Aucune étape gardée dans ce brouillon.", 409)
    src = M.remuxer(cid)
    video = "video.mp4" if src.suffix == ".mp4" else "video.webm"
    if src.stat().st_size > MAX_VIDEO:
        raise RefusTutoriel("Vidéo trop lourde pour un parcours.", 413)
    d = racine_brouillons() / f"export-{cid}"
    d.mkdir(parents=True, exist_ok=True)
    final = d / f"parcours-{cid[:8]}.dzparcours"
    fd, nom = tempfile.mkstemp(prefix="parcours.", suffix=".tmp", dir=d)
    os.close(fd)
    try:
        with zipfile.ZipFile(nom, "w") as z:
            z.writestr(zipfile.ZipInfo(NOM_PARCOURS, (2026, 1, 1, 0, 0, 0)),
                       json.dumps(_doc_parcours(b, duree(r), r["clics"].get("cadre"), video), ensure_ascii=False,
                                  indent=1), compress_type=zipfile.ZIP_DEFLATED)
            z.writestr(zipfile.ZipInfo(NOM_CLICS, (2026, 1, 1, 0, 0, 0)),
                       json.dumps({"version": 1, "duree_ms": duree(r),
                                   "evenements": _clics_reduits(r["clics"].get("evenements"), duree(r))},
                                  ensure_ascii=False), compress_type=zipfile.ZIP_DEFLATED)
            z.write(src, video, compress_type=zipfile.ZIP_STORED)
        Path(nom).replace(final)
    except BaseException:
        Path(nom).unlink(missing_ok=True)
        raise
    return final


def _lire_entree(z: zipfile.ZipFile, info: zipfile.ZipInfo, limite: int, dest=None) -> bytes | None:
    """Lit une entrée en s'arrêtant à `limite` octets RÉELS (la taille déclarée peut mentir) ; vers `dest` si donné."""
    lu, morceaux = 0, []
    with z.open(info) as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            lu += len(b)
            if lu > limite:
                raise RefusTutoriel("Parcours trop lourd.", 413)
            if dest is not None:
                dest.write(b)
            else:
                morceaux.append(b)
    return None if dest is not None else b"".join(morceaux)


def _json(octets: bytes):
    try:
        return json.loads(octets.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise RefusTutoriel("Parcours illisible.", 400) from None


def importer(chemin: Path) -> str:
    """Importe un `.dzparcours` (fichier local reçu par la route) : rend l'id du parcours. Liste blanche stricte."""
    try:
        z = zipfile.ZipFile(chemin)
    except (zipfile.BadZipFile, OSError):
        raise RefusTutoriel("Parcours illisible.", 400) from None
    with z:
        infos = z.infolist()
        noms = [i.filename for i in infos]
        if len(noms) != len(set(noms)) or any(n not in (NOM_PARCOURS, NOM_CLICS, *VIDEOS) for n in noms) \
                or any(i.is_dir() for i in infos):
            raise RefusTutoriel("Parcours refusé : entrée inattendue dans l'archive.", 400)
        vids = [n for n in noms if n in VIDEOS]
        if NOM_PARCOURS not in noms or len(vids) != 1:
            raise RefusTutoriel("Parcours refusé : il faut parcours.json et une seule vidéo.", 400)
        par = {i.filename: i for i in infos}
        try:
            p = _json(_lire_entree(z, par[NOM_PARCOURS], MAX_PARCOURS_JSON))
            cl = _json(_lire_entree(z, par[NOM_CLICS], MAX_CLICS_JSON)) if NOM_CLICS in par else {"evenements": []}
        except (zipfile.BadZipFile, RuntimeError, EOFError, OSError, NotImplementedError):
            raise RefusTutoriel("Parcours illisible.", 400) from None
        if not isinstance(p, dict) or p.get("format") != "dzparcours" or p.get("video") != vids[0]:
            raise RefusTutoriel("Parcours illisible.", 400)
        d_ms = int(_borne(_nb(p.get("duree_ms")) or 0, 0, MAX_DUREE))
        b = valider({"version": p.get("version"), "titre": p.get("titre"), "chapitres": p.get("chapitres") or [],
                     "etapes": p.get("etapes")}, d_ms)
        if not b["etapes"]:
            raise RefusTutoriel("Parcours illisible.", 400)
        doc = _doc_parcours(b, d_ms, p.get("cadre"), vids[0])
        doc["capture_id"] = ""
        evts = _clics_reduits(cl.get("evenements") if isinstance(cl, dict) else None, d_ms)
        base = racine_parcours()
        base.mkdir(parents=True, exist_ok=True)
        pid = secrets.token_hex(8)
        tmp = Path(tempfile.mkdtemp(prefix=f".{pid}.", dir=base))
        try:
            with open(tmp / vids[0], "wb") as f:
                try:
                    _lire_entree(z, par[vids[0]], MAX_VIDEO, f)
                except (zipfile.BadZipFile, RuntimeError, EOFError, OSError, NotImplementedError):
                    raise RefusTutoriel("Parcours illisible.", 400) from None
            with open(tmp / vids[0], "rb") as f:
                tete = f.read(12)
            magie = VIDEOS[vids[0]]
            if not (tete.startswith(magie) if magie != b"ftyp" else tete[4:8] == magie):
                raise RefusTutoriel("Parcours refusé : la vidéo n'est pas une vidéo WebM ou MP4.", 415)
            (tmp / NOM_PARCOURS).write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
            (tmp / NOM_CLICS).write_text(json.dumps({"version": 1, "duree_ms": d_ms, "evenements": evts},
                                                    ensure_ascii=False), "utf-8")
            tmp.replace(base / pid)
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
    return pid


def _dossier_parcours(pid: str) -> Path:
    if not isinstance(pid, str) or not PID.match(pid):
        raise RefusTutoriel("Identifiant de parcours invalide.", 400)
    d = racine_parcours() / pid
    if not (d / NOM_PARCOURS).is_file():
        raise RefusTutoriel("Parcours introuvable.", 404)
    return d


def action_locale(fiche: str | None) -> dict | None:
    """L'action « Montrer » d'une étape, construite UNIQUEMENT depuis les données de cette installation : ancre ou
    fiche localisée (`agent_aide._action`), sinon recherche par le libellé local parmi les contrôles. None si la fiche
    n'existe pas ici."""
    if not fiche or not _fiche(fiche):
        return None
    try:
        from app.services import agent_aide
        a = agent_aide._action("POINT", fiche)
    except Exception:  # noqa: BLE001
        a = None
    if a:
        return a
    x = _catalogue().get(fiche)
    if not x:
        return None
    nom = nom_fiche(fiche)
    if not (nom["fr"] or nom["en"]):
        return None
    return {"type": "point", "cible": fiche, "ecran": None if x.get("ecran") == "commun" else x.get("ecran"),
            "selecteur": SELECTEUR_GENERIQUE, "texte": {"fr": nom["fr"] or nom["en"], "en": nom["en"] or nom["fr"]},
            "cadre": x.get("cadre"), "reglages": None, "partout": x.get("ecran") == "commun", "libelle": None,
            "fr": nom["fr"] or nom["en"], "en": nom["en"] or nom["fr"]}


def lire_parcours(pid: str) -> dict:
    d = _dossier_parcours(pid)
    try:
        doc = json.loads((d / NOM_PARCOURS).read_text("utf-8"))
        b = valider({"version": doc.get("version"), "titre": doc.get("titre"), "chapitres": doc.get("chapitres") or [],
                     "etapes": doc.get("etapes")}, doc.get("duree_ms"))
    except (ValueError, OSError, AttributeError):
        raise RefusTutoriel("Parcours illisible.", 400) from None
    etapes = [dict(e, action=action_locale(e["fiche"])) for e in b["etapes"]]
    return {"id": pid, "titre": b["titre"], "duree_ms": int(_nb(doc.get("duree_ms")) or 0),
            "cadre": doc.get("cadre") if isinstance(doc.get("cadre"), dict) else {}, "chapitres": b["chapitres"],
            "etapes": etapes, "video": doc.get("video") if doc.get("video") in VIDEOS else "video.webm"}


def liste_parcours() -> list[dict]:
    out = []
    base = racine_parcours()
    if not base.is_dir():
        return out
    for d in base.iterdir():
        if not PID.match(d.name) or not (d / NOM_PARCOURS).is_file():
            continue
        try:
            p = lire_parcours(d.name)
        except RefusTutoriel:
            continue
        out.append({"id": d.name, "titre": p["titre"], "duree_ms": p["duree_ms"], "etapes": len(p["etapes"]),
                    "montrables": sum(1 for e in p["etapes"] if e["action"]),
                    "importe_ms": int((d / NOM_PARCOURS).stat().st_mtime * 1000)})
    out.sort(key=lambda x: x["importe_ms"], reverse=True)
    return out[:200]


def video_parcours(pid: str) -> Path:
    d = _dossier_parcours(pid)
    for n in VIDEOS:
        if (d / n).is_file():
            return d / n
    raise RefusTutoriel("Parcours introuvable.", 404)


def retirer_parcours(pid: str) -> None:
    d = _dossier_parcours(pid)
    shutil.rmtree(d)
