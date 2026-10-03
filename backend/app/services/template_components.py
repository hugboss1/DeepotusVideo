# -*- coding: utf-8 -*-
"""Plan-templates T8 / D1 (tache #76 du suivi, PR E, 03/10/2026) — COMPOSANTS : des groupes de regions reutilisables.

Un composant : {"id", "name", "width", "height", "regions": [...]} — ses regions sont placees dans SA boite
(0..width, 0..height). Livres dans app/templates/_components/ (immuables), crees par l'utilisateur dans
DATA_ROOT/assets/user_components/.
Une INSTANCE dans un gabarit : {"type": "component", "component": id, "x", "y", "width", "height",
"overrides": {id_de_sous_region: {"text"|"default_text"|"color"|"background_color"|"border_color": ...}}}.
Decisions de l'utilisateur (03/10) : une instance garde la FORME du composant ; on n'y change que les textes et les
couleurs ; « Enregistrer comme composant » depuis l'editeur ; pas de composant dans un composant.
Expansion (resoudre) : chaque instance devient les regions du composant, mises a l'echelle de sa boite (positions
par axe, textes a l'echelle du plus petit rapport — la meme regle que le reagencement), ids « inst__sous », slots
« inst_slot » ; l'animation de l'instance passe a chacune. Rendu, image fixe, vignettes et slots voient le meme
contenu. Sous-regions VISUELLES seulement : ni case video (fournisseurs payes, format HeyGen lus sur le gabarit non
deplie) ni piste son.
Le plan visait des modes de contrainte anglais, des effets plats et des jetons de marque inexistants : ici le schema
reel du moteur.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

SOUS_TYPES = ("text", "text_slot", "badge", "ticker", "sticker", "separator", "brand_strip", "image_slot")
SURCHARGES = ("text", "default_text", "color", "background_color", "border_color")
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def dossier_livre() -> Path:
    return Path(__file__).resolve().parent.parent / "templates" / "_components"


def dossier_utilisateur() -> Path:
    from app.config import DATA_ROOT
    d = Path(DATA_ROOT) / "assets" / "user_components"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lister() -> list:
    out, vus = [], set()
    for livre, dossier in ((True, dossier_livre()), (False, dossier_utilisateur())):
        if not dossier.is_dir():
            continue
        for f in sorted(dossier.glob("*.json")):
            try:
                c = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            cid = c.get("id") or f.stem
            if cid in vus:
                continue               # un livre ne se masque pas
            vus.add(cid)
            c["id"], c["builtin"] = cid, livre
            out.append(c)
    return out


def lire(cid: str) -> dict:
    if not isinstance(cid, str) or not _ID.match(cid):
        raise ValueError(f"Composant inconnu : {cid!r}.")
    for livre, dossier in ((True, dossier_livre()), (False, dossier_utilisateur())):
        f = dossier / f"{cid}.json"
        if f.is_file():
            c = json.loads(f.read_text(encoding="utf-8"))
            c["id"], c["builtin"] = cid, livre
            return c
    raise ValueError(f"Composant inconnu : {cid}.")


def verifier_composant(c: dict, engine) -> None:
    """ValueError parlante : nom, boite, sous-regions visuelles valides (le moteur les valide dans une toile a la
    taille du composant), pas d'imbrication."""
    if not isinstance(c, dict):
        raise ValueError("Un composant est un objet.")
    if not str(c.get("name") or "").strip():
        raise ValueError("Un composant a un nom.")
    for k in ("width", "height"):
        if not (isinstance(c.get(k), (int, float)) and 8 <= c[k] <= 4096):
            raise ValueError(f"Composant : {k} doit être entre 8 et 4096 px.")
    regs = c.get("regions")
    if not isinstance(regs, list) or not regs:
        raise ValueError("Un composant contient au moins une région.")
    for r in regs:
        if not isinstance(r, dict):
            raise ValueError("Composant : chaque région est un objet.")
        if r.get("type") == "component":
            raise ValueError(f"Composant : la région {r.get('id')} est un composant (pas de composant dans un composant).")
        if r.get("type") not in SOUS_TYPES:
            raise ValueError(f"Composant : la région {r.get('id')} est un {r.get('type')} — un composant contient {', '.join(SOUS_TYPES)}.")
    engine._validate({"name": c["name"], "canvas": {"width": c["width"], "height": c["height"]}, "regions": regs})


def verifier_instances(tpl: dict) -> None:
    """Les instances d'un gabarit : composant connu, surcharges de textes et couleurs sur des sous-regions reelles."""
    for r in (tpl or {}).get("regions") or []:
        if r.get("type") != "component":
            continue
        rid = r.get("id")
        c = lire(r.get("component"))                 # ValueError : composant inconnu
        ids = {s.get("id") for s in c.get("regions") or []}
        ov = r.get("overrides") or {}
        if not isinstance(ov, dict):
            raise ValueError(f"Region {rid} : overrides attend {{sous-région : {{champ : valeur}}}}.")
        for sid, champs in ov.items():
            if sid not in ids:
                raise ValueError(f"Region {rid} : « {sid} » n'est pas une région du composant {c['id']}.")
            if not isinstance(champs, dict) or set(champs) - set(SURCHARGES):
                raise ValueError(f"Region {rid} : on ne change que {', '.join(SURCHARGES)} d'une instance (la forme reste celle du composant).")
            for k, v in champs.items():
                if k.endswith("color") and not (isinstance(v, str) and _COULEUR.match(v)):
                    raise ValueError(f"Region {rid} : overrides.{sid}.{k} doit être #RRGGBB.")
                if k in ("text", "default_text") and not isinstance(v, str):
                    raise ValueError(f"Region {rid} : overrides.{sid}.{k} est un texte.")


def deplier(tpl: dict) -> dict:
    """Le gabarit sans instance : chaque composant remplace par ses sous-regions a l'echelle de sa boite. Sans
    instance, le gabarit est rendu TEL QUEL (meme objet)."""
    regs = (tpl or {}).get("regions") or []
    if not any(r.get("type") == "component" for r in regs):
        return tpl
    from app.services.template_layout import _echelle_textes
    out = copy.deepcopy(tpl)
    nouvelles = []
    for r in out.get("regions") or []:
        if r.get("type") != "component":
            nouvelles.append(r)
            continue
        c = lire(r.get("component"))
        cw, ch = float(c["width"]), float(c["height"])
        bx, by, bw, bh = (float(r.get(k) or 0) for k in ("x", "y", "width", "height"))
        sx, sy = bw / cw, bh / ch
        ov = r.get("overrides") or {}
        for s in copy.deepcopy(c.get("regions") or []):
            sid = s.get("id")
            for k, v in (ov.get(sid) or {}).items():
                s[k] = v
            x0, y0 = round(bx + float(s.get("x") or 0) * sx), round(by + float(s.get("y") or 0) * sy)
            x1, y1 = round(bx + (float(s.get("x") or 0) + float(s.get("width") or 0)) * sx), round(by + (float(s.get("y") or 0) + float(s.get("height") or 0)) * sy)
            # pas de bornage : une sous-region tient dans la boite du composant (verifie a l'enregistrement) et la boite
            # d'instance est entiere — l'arrondi ne deborde pas (mesure par le banc K4 et la table de mutations)
            s["x"], s["y"], s["width"], s["height"] = x0, y0, max(1, x1 - x0), max(1, y1 - y0)
            _echelle_textes(s, min(sx, sy))
            s["id"] = f"{r['id']}__{sid}"
            if s.get("slot_name"):
                s["slot_name"] = f"{r['id']}_{s['slot_name']}"
            s["z_index"] = float(r.get("z_index") or 0) + float(s.get("z_index") or 0) / 1000
            if r.get("animation") and not s.get("animation"):
                s["animation"] = copy.deepcopy(r["animation"])
            nouvelles.append(s)
    out["regions"] = nouvelles
    return out


def enregistrer(c: dict, engine) -> str:
    """Un composant UTILISATEUR (id tire du nom, jamais celui d'un livre)."""
    verifier_composant(c, engine)
    base = re.sub(r"[^a-z0-9]+", "_", str(c["name"]).lower()).strip("_")[:40] or "composant"
    cid, k = f"cmp_{base}", 2
    livres = {f.stem for f in dossier_livre().glob("*.json")} if dossier_livre().is_dir() else set()
    while cid in livres or (dossier_utilisateur() / f"{cid}.json").exists():
        cid, k = f"cmp_{base}_{k}", k + 1
    propre = {"id": cid, "name": str(c["name"]).strip()[:80], "width": c["width"], "height": c["height"], "regions": c["regions"]}
    (dossier_utilisateur() / f"{cid}.json").write_text(json.dumps(propre, ensure_ascii=False, indent=1), encoding="utf-8")
    return cid


def utilisateurs_de(cid: str, engine) -> list:
    """Les gabarits (noms) qui posent ce composant."""
    return [t.get("name") or t.get("id") for t in engine.list_templates()
            if any(r.get("type") == "component" and r.get("component") == cid for r in t.get("regions") or [])]


def supprimer(cid: str, engine) -> None:
    """ValueError : livre (immuable) ou inconnu ; RuntimeError : encore pose dans des gabarits."""
    c = lire(cid)
    if c.get("builtin"):
        raise ValueError(f"Le composant « {c.get('name')} » est livré avec l'application : il ne se supprime pas.")
    noms = utilisateurs_de(cid, engine)
    if noms:
        raise RuntimeError(f"Le composant « {c.get('name')} » est posé dans : {', '.join(map(str, noms))}. Retirez-le d'abord.")
    (dossier_utilisateur() / f"{cid}.json").unlink()
