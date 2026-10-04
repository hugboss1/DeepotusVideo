# -*- coding: utf-8 -*-
"""Profils d'imprimante (tâche #88 PR B, plan-etabli T3-T4, 04/10/2026) — la Centauri Carbon 2 INTÉGRÉE, ceux
d'OrcaSlicer / ElegooSlicer IMPORTÉS EN LECTURE SEULE, ceux de l'utilisateur saisis à la main.

DÉCISIONS DE L'UTILISATEUR (04/10) : la Centauri Carbon 2 intégrée est le profil par défaut ; l'import liste les
presets INSTANCIABLES d'OrcaSlicer, groupés par marque (Elegoo en tête) ; le choix de l'utilisateur est RETENU et
jamais remplacé en douce par le preset actif du slicer — celui-ci est seulement PROPOSÉ (`actif_slicer`).

Format relevé le 04/10/2026 dans %APPDATA%\\OrcaSlicer :
  * presets `system/<Marque>/machine/**.json` et `user/<compte>/machine/*.json`, `"type": "machine"` ;
  * `printable_area` = quatre "XxY" en mm, `printable_height`, `bed_exclude_area`, `inherits` (le preset 0.2 ne porte
    pas de plateau : l'héritage DOIT se résoudre) ;
  * les presets COMMUNS (`fdm_elegoo_common`…) portent un plateau mais `"instantiation": "false"` : ce ne sont pas des
    imprimantes, ils sont écartés (le plan les aurait listés) ;
  * `OrcaSlicer.conf` n'est pas du JSON pur : une ligne `# MD5 checksum …` le suit ; on lit jusqu'à la dernière
    accolade ; `presets.machine` dit le preset actif (« … 0.2 nozzle » sur cette machine le 04/10).
ElegooSlicer n'est PAS installé ici : son dossier est un candidat non mesuré (« based on Orca Slicer »).

Le SEUL fichier écrit est le nôtre : `<outputs>/../print3d/profils.json` (écriture atomique).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

INTEGRES = [{"id": "integre:elegoo-centauri-carbon-2", "nom": "Elegoo Centauri Carbon 2", "marque": "Elegoo",
             "origine": "integre", "plateau_mm": [256.0, 256.0], "hauteur_mm": 256.0,
             "exclusions_mm": [[246.0, 0.0, 256.0, 20.0]]}]
_SLICERS = (("OrcaSlicer", "orcaslicer"), ("ElegooSlicer", "elegooslicer"))
_CACHE: dict = {}


def _dossiers_slicers() -> list:
    base = Path(os.environ.get("APPDATA", ""))
    return [(base / nom, tag) for nom, tag in _SLICERS if str(base) and (base / nom).is_dir()]


def _aire(chaines) -> list:
    pts = []
    for c in chaines or []:
        try:
            x, y = str(c).lower().split("x")
            pts.append((float(x), float(y)))
        except ValueError:
            continue
    return pts


def _lire(p: Path) -> dict:
    d = json.loads(p.read_text("utf-8"))
    return d if isinstance(d, dict) else {}


def _resoudre(d: dict, par_nom: dict, cle: str, profondeur: int = 0):
    if cle in d:
        return d[cle]
    parent = par_nom.get(str(d.get("inherits") or ""))
    return None if parent is None or profondeur > 8 else _resoudre(parent, par_nom, cle, profondeur + 1)


def _fichiers_machine(racine: Path) -> list:
    out = []
    for sous in ("system", "user"):
        r = racine / sous
        if not r.is_dir():
            continue
        for p in r.rglob("*.json"):
            if "machine" in p.relative_to(r).parts[:-1]:
                out.append(p)
    return out


def _marque(racine: Path, p: Path) -> str:
    parts = p.relative_to(racine).parts
    return parts[1] if parts[0] == "system" and len(parts) > 2 else "Mes profils du slicer"


def importer(racine: Path, origine: str) -> list:
    """Les imprimantes d'un slicer : presets `machine` INSTANCIABLES dont le plateau se résout. LECTURE SEULE."""
    fichiers = _fichiers_machine(racine)
    sig = (str(racine), len(fichiers), max((p.stat().st_mtime_ns for p in fichiers), default=0))
    if _CACHE.get(origine, (None,))[0] == sig:
        return [dict(x) for x in _CACHE[origine][1]]
    docs = {}
    for p in fichiers:
        try:
            d = _lire(p)
        except (ValueError, OSError):
            continue
        if d.get("type") == "machine" and d.get("name"):
            docs[str(d["name"])] = (d, p)
    par_nom = {n: d for n, (d, _p) in docs.items()}
    out = []
    for nom, (d, p) in docs.items():
        if str(d.get("instantiation", "true")).lower() == "false":
            continue                                   # un preset COMMUN n'est pas une imprimante
        aire = _aire(_resoudre(d, par_nom, "printable_area"))
        if len(aire) < 3:
            continue
        xs, ys = [q[0] for q in aire], [q[1] for q in aire]
        excl = _aire(_resoudre(d, par_nom, "bed_exclude_area") or [])
        h = _resoudre(d, par_nom, "printable_height")
        try:
            hauteur = float(h) if h not in (None, "") else None
        except (TypeError, ValueError):
            hauteur = None
        out.append({"id": f"{origine}:{nom}", "nom": nom, "marque": _marque(racine, p), "origine": origine,
                    "plateau_mm": [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3)], "hauteur_mm": hauteur,
                    "exclusions_mm": ([[min(q[0] for q in excl), min(q[1] for q in excl), max(q[0] for q in excl),
                                        max(q[1] for q in excl)]] if len(excl) >= 3 else [])})
    out.sort(key=lambda x: (x["marque"] != "Elegoo", x["marque"].lower(), x["nom"].lower()))
    _CACHE[origine] = (sig, [dict(x) for x in out])
    return out


def profil_actif_du_slicer(racine: Path) -> str | None:
    """Le preset machine sélectionné dans le slicer, ou None. Le .conf porte `# MD5 checksum …` APRÈS le JSON."""
    for nom in ("OrcaSlicer.conf", "ElegooSlicer.conf"):
        p = racine / nom
        if p.is_file():
            txt = p.read_text("utf-8", errors="replace")
            try:
                v = (json.loads(txt[:txt.rindex("}") + 1]).get("presets") or {}).get("machine")
            except ValueError:
                return None
            return str(v) if v else None
    return None


def _fichier() -> Path:
    from app.config import settings
    return settings.outputs_path.parent / "print3d" / "profils.json"


def _etat() -> dict:
    p = _fichier()
    if p.is_file():
        try:
            e = json.loads(p.read_text("utf-8"))
            if isinstance(e, dict) and isinstance(e.get("manuels"), list) and e.get("actif"):
                return e
        except ValueError:
            pass
    return {"actif": INTEGRES[0]["id"], "manuels": []}


def _fr(v) -> str:
    return ("%g" % round(float(v), 1)).replace(".", ",")


def resume(p: dict) -> str:
    """Le profil EN CHIFFRES, rédigé ici : la page de l'Établi n'écrit aucune abréviation d'unité (sa doctrine :
    un seul littéral, dans uniteCourante())."""
    l, pr = p.get("plateau_mm") or [0, 0]
    s = f"plateau {_fr(l)} × {_fr(pr)} mm"
    if p.get("hauteur_mm"):
        s += f" · hauteur {_fr(p['hauteur_mm'])} mm"
    n = len(p.get("exclusions_mm") or [])
    if n:
        s += f" · {n} zone(s) exclue(s), en rouge sur la plaque"
    return s


def lister() -> dict:
    etat = _etat()
    profils = [dict(p) for p in INTEGRES] + [{**m, "origine": "manuel", "marque": "Saisis à la main"}
                                             for m in etat["manuels"]]
    slicer = None
    for dossier, tag in _dossiers_slicers():
        profils += importer(dossier, tag)
        nom = profil_actif_du_slicer(dossier)
        if nom and slicer is None:
            slicer = {"nom": nom, "id": f"{tag}:{nom}"}
    ids = {p["id"] for p in profils}
    actif = etat["actif"] if etat["actif"] in ids else INTEGRES[0]["id"]     # un preset disparu retombe sur l'intégré
    if slicer and slicer["id"] not in ids:
        slicer = None
    for p in profils:
        p["resume"] = resume(p)
        # le CONTOUR pour la plaque de l'Établi (mêmes valeurs, en mm) : la page lit `contour` et
        # jamais un champ suffixé de l'unité — sa doctrine compte chaque jeton « mm » qu'elle écrit.
        pl = p.get("plateau_mm") or [0.0, 0.0]
        p["contour"] = {"l": pl[0], "p": pl[1], "zones": [list(z) for z in (p.get("exclusions_mm") or [])]}
    return {"profils": profils, "actif": actif, "actif_slicer": slicer}


def profil_courant() -> dict:
    l = lister()
    return next((p for p in l["profils"] if p["id"] == l["actif"]), INTEGRES[0])


def _slug(nom: str) -> str:
    """ASCII : « Ma résine » → « ma-resine » (un id lisible, sans accent dans le JSON ni dans une URL)."""
    import unicodedata
    a = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode("ascii").lower()
    out = "".join(c if c.isalnum() else "-" for c in a)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:40] or "imprimante"


def _nombre(v, quoi: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi} : un nombre de millimètres")
    if not (lo < x <= hi):
        raise ValueError(f"{quoi} : entre {lo:g} et {hi:g} mm")
    return x


def choisir(pid: str, manuel: dict | None = None) -> dict:
    """Retient `pid` (ou crée/remplace un profil MANUEL et le retient). -> l'état écrit."""
    etat = _etat()
    if manuel is not None:
        if not isinstance(manuel, dict):
            raise ValueError("`manuel` doit être un objet")
        pl = manuel.get("plateau_mm")
        if not isinstance(pl, list) or len(pl) != 2:
            raise ValueError("plateau_mm attend deux nombres (largeur, profondeur)")
        pl = [_nombre(v, "plateau", 0, 2000) for v in pl]
        h = manuel.get("hauteur_mm")
        nom = str(manuel.get("nom") or "imprimante").strip()[:60] or "imprimante"
        m = {"id": f"manuel:{_slug(nom)}", "nom": nom, "plateau_mm": pl,
             "hauteur_mm": _nombre(h, "hauteur", 0, 2000) if h not in (None, "") else None,
             "exclusions_mm": [[float(v) for v in e] for e in (manuel.get("exclusions_mm") or [])
                               if isinstance(e, list) and len(e) == 4]}
        etat["manuels"] = [x for x in etat["manuels"] if x["id"] != m["id"]] + [m]
        pid = m["id"]
    ids = ({p["id"] for p in INTEGRES} | {m["id"] for m in etat["manuels"]}
           | {p["id"] for d, t in _dossiers_slicers() for p in importer(d, t)})
    if pid not in ids:
        raise ValueError(f"profil inconnu : {pid}")
    etat["actif"] = pid
    p = _fichier()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(p)
    return etat


SUITE_EXPORT = "le slicer devra couper ou réduire"
SUITE_LOT = "imprimer les pièces séparément (un STL par tuile)"


def garde(bb, profil: dict | None = None, suite: str = SUITE_EXPORT) -> str | None:
    """L'AVERTISSEMENT du plateau (il n'interdit jamais : couper est le métier du slicer). `bb` = ((x0,x1),(y0,y1),
    (z0,z1)) en mm, Z en haut (le STL écrit par print3d). L'empreinte XY se compare en dimensions TRIÉES (la pièce peut
    tourner sur le plateau) ; la hauteur à part. Sans profil : la Centauri Carbon 2, message historique inchangé."""
    pf = profil or INTEGRES[0]
    nom = pf.get("nom") or "imprimante"
    lx, ly, lz = (b[1] - b[0] for b in bb)
    p1, p2 = sorted((float(v) for v in (pf.get("plateau_mm") or [256.0, 256.0])), reverse=True)
    a1, a2 = sorted((lx, ly), reverse=True)
    h = pf.get("hauteur_mm")
    if profil is None or pf.get("id") == INTEGRES[0]["id"]:
        nom_dit = "la Centauri Carbon 2"
    else:
        nom_dit = nom
    carre = abs(p1 - p2) < 0.5
    if a1 > p1 + 1e-6 or a2 > p2 + 1e-6:
        if carre:
            return f"{a1:.0f} mm dépasse le plateau de {nom_dit} ({p1:.0f} mm) — {suite}"
        return f"{a1:.0f} x {a2:.0f} mm dépasse le plateau de {nom_dit} ({p1:.0f} x {p2:.0f} mm) — {suite}"
    if h and lz > float(h) + 1e-6:
        return f"{lz:.0f} mm de haut dépasse la hauteur de {nom_dit} ({float(h):.0f} mm) — {suite}"
    return None
