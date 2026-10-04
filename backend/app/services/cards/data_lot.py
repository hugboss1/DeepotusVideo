# -*- coding: utf-8 -*-
"""Card Forge — pièce 04, sidecar « art du deck » (tâche #87 PR A, plan-cartes T14-T15, 04/10/2026).

SIDECAR : aucun `router` (règle 8 — les routes vivent dans data.py, LE TIR aussi : le recensement des routes
payantes ne suit que les fonctions du module de la route). Ici, rien ne coûte : le devis et les prompts.

LE DEVIS COMPTE LES LIGNES, PAS LES CARTES. Trois Colosses partagent UNE illustration : facturer trois fois la
même image serait l'erreur la plus chère du plan. Et il ne calcule AUCUN prix lui-même — `face.prix_usd` lit la
table de l'application et rend `None` pour un modèle non tabulé (pricing.estimate retomberait EN SILENCE sur le
tarif de FLUX).

LA COLONNE D'ART EST CELLE DU MAPPAGE (`map[col] == "art"`), jamais devinée à son nom : c'est elle que /build
lit, c'est donc elle qu'on remplit.

FLUX N'EST PAS SERVI : la façade `image_providers.generate` ne le connaît pas (les routes Images le servent
elles-mêmes) — le proposer, ce serait un échec garanti à chaque ligne, après la confirmation.

AUCUN NOM D'ARTISTE : le prompt final passe par `face.sans_nom_d_artiste`, qui LÈVE (400) au lieu de nettoyer.
"""
from __future__ import annotations

import re
from typing import Any

from .data import BLANK, read_qty

__all__ = ["LOT_MUR_USD", "LOT_MUR_MAX", "LOT_N_MAX", "LOT_LIGNES_MAX", "TAILLES", "servi", "modeles",
           "colonne_art", "remplir", "prompts_lot", "devis", "mur"]

LOT_MUR_USD = 10.0      # LE MUR PAR LOT (décision 04/10) : un devis au-dessus ne part pas
LOT_MUR_MAX = 100.0     # le mur se règle, mais pas au-delà
LOT_N_MAX = 4           # variantes par ligne
LOT_LIGNES_MAX = 12     # lignes par demande : une requête de 12 tirs tient en quelques minutes ; le reste attend
TAILLES = ("portrait_4_3", "square_hd", "portrait_16_9", "landscape_4_3")
_CHAMP = re.compile(r"\{([^{}]{1,80})\}")


def _clean(v: Any) -> str:
    return str(v if v is not None else "").replace(BLANK, "").strip()


def servi(model: str) -> bool:
    """Le modèle passe-t-il par la façade ? Tout le registre des tarifs, sauf FLUX."""
    from app.services import pricing
    m = str(model or "")
    return m != "flux" and m in getattr(pricing, "_IMAGE_MODELS", {})


def modeles() -> list:
    """Les modèles du lot : servis par la façade, avec leur tarif ET la clé qu'il leur faut."""
    from app.config import settings
    from . import face
    cles = {"fal": bool(getattr(settings, "FAL_KEY", "")), "openai": bool(getattr(settings, "OPENAI_API_KEY", ""))}
    out = []
    for mid, spec in sorted(face.price_table().items()):
        if not servi(mid):
            continue
        out.append({"id": mid, "label": spec["label"], "provider": spec["provider"], "usd_par_image": spec["usd"],
                    "cle": cles.get(spec["provider"], False)})
    return out


def colonne_art(columns: list, real_map: Any) -> str:
    cols = [str(c) for c in (columns or ())]
    for c, slot in (real_map or {}).items():
        if slot == "art" and str(c) in cols:
            return str(c)
    raise ValueError("Aucune colonne n'est mappée sur l'illustration (card.art) : mappez-en une dans la table")


def _off(off: Any) -> set:
    s = set()
    for v in (off if isinstance(off, list) else ()):
        try:
            s.add(int(v))
        except (TypeError, ValueError):
            pass
    return s


def remplir(gabarit: str, val: dict) -> str:
    """« {prompt}, {espece} » avec les cellules de la ligne. Une substitution PLATE : `str.format` lirait
    `{x.__class__}` — un gabarit est une saisie, pas du code. Une colonne inconnue lève (400)."""
    def sub(m):
        k = m.group(1)
        if k not in val:
            raise ValueError(f"Le gabarit cite une colonne absente : « {k} »")
        return val[k]
    return _CHAMP.sub(sub, str(gabarit or ""))


def _entite(nom: str, entites: Any) -> dict | None:
    n = nom.strip().lower()
    if not n:
        return None
    for e in (entites or ()):
        noms = [str(e.get("name") or "")] + [str(a) for a in (e.get("aliases") or ())]
        if any(x.strip().lower() == n for x in noms if x.strip()):
            return e
    return None


def prompts_lot(columns: list, rows: list, real_map: Any, off: Any, gabarit: str = "{prompt}", style: str = "",
                entites: Any = None, col_entite: str = "", qty_col: Any = None) -> dict:
    """Un prompt par LIGNE à illustrer (art vide, ligne gardée), dans l'ordre de la table. Une ligne sans texte
    n'est PAS inventée : elle est listée dans `manque` — payer pour une image faite de rien ne rend rien."""
    cols = [str(c) for c in (columns or ())]
    ia = cols.index(colonne_art(cols, real_map))
    iq = cols.index(str(qty_col)) if qty_col and str(qty_col) in cols else -1
    ie = cols.index(str(col_entite)) if col_entite and str(col_entite) in cols else -1
    if col_entite and ie < 0:
        raise ValueError(f"Colonne d'entité inconnue : « {col_entite} »")
    hors = _off(off)
    st = _clean(style)
    out, deja, couvertes = [], 0, 0
    for k, r in enumerate(rows or ()):
        if k in hors or not isinstance(r, list):
            continue
        if ia < len(r) and _clean(r[ia]):
            deja += 1
            continue
        val = {c: (_clean(r[i]) if i < len(r) else "") for i, c in enumerate(cols)}
        base = remplir(gabarit or "{prompt}", val).strip(" ,;")
        ent = _entite(val[cols[ie]], entites) if ie >= 0 else None
        cartes = read_qty(r[iq]) if 0 <= iq < len(r) else 1
        couvertes += cartes
        p = {"ligne": k + 1, "cartes": cartes, "entite": (ent or {}).get("name", ""), "references": [],
             "manque": [] if base else ["prompt"], "prompt": ""}
        if base:
            morceaux = [base]
            if ent and _clean(ent.get("description")):
                morceaux.append(_clean(ent["description"]))
            if st:
                morceaux.append(st)
            p["prompt"] = ", ".join(morceaux)
            if ent and _clean(ent.get("ref_image")):
                p["references"] = [_clean(ent["ref_image"])]
        out.append(p)
    return {"prompts": out, "lignes": len(out), "incomplets": sum(1 for p in out if p["manque"]),
            "deja_illustrees": deja, "cartes_couvertes": couvertes}


def mur(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return LOT_MUR_USD
    if not (x > 0):
        return LOT_MUR_USD
    return min(LOT_MUR_MAX, x)


def devis(lot: dict, model: str, n: int, mur_usd: Any = None) -> dict:
    """Le coût du lot AVANT le tir : les lignes complètes de CETTE demande (au plus LOT_LIGNES_MAX), × n."""
    from . import face
    m = str(model or "")
    if not servi(m):
        raise ValueError(f"Modèle non servi pour le lot : « {m} »" + (" (FLUX ne passe que par l'écran Images)"
                                                                      if m == "flux" else ""))
    n = max(1, min(LOT_N_MAX, int(n or 1)))
    pretes = [p for p in lot["prompts"] if not p["manque"]]
    a_tirer = pretes[:LOT_LIGNES_MAX]
    unit = face.prix_usd(m, 1)
    if unit is None:
        raise ValueError(f"Modèle « {m} » absent de la table de tarifs : aucun tir sans son prix")
    total = face.prix_usd(m, len(a_tirer) * n) if a_tirer else 0.0
    plafond = mur(mur_usd)
    return {"lignes_a_generer": lot["lignes"], "incomplets": lot["incomplets"], "deja_illustrees": lot["deja_illustrees"],
            "cartes_couvertes": lot["cartes_couvertes"], "lignes_de_ce_lot": len(a_tirer),
            "restants": len(pretes) - len(a_tirer), "n_par_ligne": n, "images": len(a_tirer) * n, "model": m,
            "usd_par_image": unit, "total_usd": round(float(total or 0.0), 4), "mur_usd": plafond,
            "sous_le_mur": float(total or 0.0) <= plafond + 1e-9}
