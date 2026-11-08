# -*- coding: utf-8 -*-
"""t435b (lot M2 « Méthodes », 08/11/2026) — B4 : la CHAÎNE D'ÉDITIONS VIDÉO → VIDÉO (conception
docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §4 ; méthodes change-only-x, alter,
change-only-x-product / -fashion).

Une chaîne part d'une prise APPROUVÉE ; chaque étape édite la sortie de l'étape précédente en ne changeant QU'UNE chose
(la consigne), tout le reste tenu : caméra, cadrage, timing, personnages, lumière. Le moteur est Seedance 2.5
reference-to-video, tâche « editing » (video_refs : « seedance-2.5-v2v »), déjà branché pour « Previs → plan » (t335) :
même devis (`video_refs.cout_estime`), même conform avant l'envoi et même recalage après (t336), même tir
(`previs_plan.tirer_previs`). Les références : les ancres d'identité données (B2), sinon l'image du milieu du parent.

Après le rendu : la sortie est RECALÉE au nombre d'images du parent puis MESURÉE contre lui (B3 `comparer` : dérive
image par image) — la preuve que la caméra et le timing ont tenu.

Stockage : <données>/briques/chaines/<id>.json ; les vidéos rendues dans <données>/briques/chaines/<id>/.
Le devis est gratuit ; le tir est PAYANT et passe par la route (clé 503, confirmation 409, plafond 402 AVANT).
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services import briques as BR

MODELE = "seedance-2.5-v2v"
RESOLUTIONS = ("480p", "720p")
MAX_ETAPES = 12
MAX_CONSIGNE = 400
MAX_NOM = 80
_ID = re.compile(r"^ch_[0-9a-f]{12}$")
_VERROU = threading.Lock()

GARDE = ("Keep everything else exactly as in the input video: camera move, framing, timing, every other person and "
         "object, their motion, lighting and colours. Do not add or remove anything else.")


def _dossier() -> Path:
    return BR.racine() / "briques" / "chaines"


def _fichier(cid: str) -> Path:
    if not _ID.match(cid or ""):
        raise ValueError("Chaîne inconnue.")
    return _dossier() / f"{cid}.json"


def _ecrire(ch: dict) -> None:
    f = _fichier(ch["id"])
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(ch, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def _rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(BR.racine())).replace("\\", "/")


def creer(source: str, nom: str = "") -> dict:
    """Une chaîne neuve sur une vidéo approuvée (copiée : la chaîne ne dépend plus de l'original)."""
    import shutil
    p = BR.confiner(source)
    if BR.nature(p) != "video":
        raise ValueError("Une chaîne d'éditions part d'une vidéo.")
    cid = "ch_" + uuid4().hex[:12]
    d = _dossier() / cid
    d.mkdir(parents=True, exist_ok=True)
    copie = d / f"00_source{p.suffix.lower()}"
    shutil.copy2(p, copie)
    ch = {"id": cid, "nom": " ".join(str(nom or p.stem).split())[:MAX_NOM], "source": _rel(copie),
          "origine": _rel(p), "cree": datetime.now(timezone.utc).isoformat(timespec="seconds"), "etapes": []}
    _ecrire(ch)
    return ch


def lire(cid: str) -> dict | None:
    try:
        return json.loads(_fichier(cid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lister() -> list[dict]:
    out = []
    for f in sorted(_dossier().glob("ch_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:100]:
        try:
            ch = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"id": ch["id"], "nom": ch["nom"], "etapes": len(ch["etapes"]), "dernier": parent(ch)})
    return out


def parent(ch: dict) -> str:
    """La vidéo que la prochaine étape éditera : la dernière sortie FAITE, sinon la source."""
    faites = [e for e in ch["etapes"] if e.get("statut") == "fait" and e.get("sortie")]
    return faites[-1]["sortie"] if faites else ch["source"]


def prompt_etape(consigne: str) -> str:
    """PUR — l'invite d'une étape : la seule chose à changer, puis la garde de tout le reste (méthode change-only-x)."""
    c = " ".join(str(consigne or "").split())[:MAX_CONSIGNE]
    if not c:
        raise ValueError("Dis la seule chose à changer.")
    return f"Change only this: {c}. {GARDE}"


def devis_etape(cid: str, consigne: str, ancres: list[str] | None = None, resolution: str = "720p") -> dict:
    """Le devis GRATUIT de la prochaine étape : {chaine, parent, prompt, resolution, secondes_entree, secondes_sortie,
    conform, usd, refus, references, n}. Rien n'est écrit ni envoyé. `refus` = ce qui bloquerait le tir."""
    from app.services import ancres as AN
    from app.services import previs_plan as PV
    from app.services import video_refs as VR
    ch = lire(cid)
    if ch is None:
        raise ValueError("Chaîne inconnue.")
    if resolution not in RESOLUTIONS:
        raise ValueError("Résolution inconnue (480p ou 720p).")
    prompt = prompt_etape(consigne)
    refs = AN.references(list(ancres or [])[:4]) if ancres else []
    par = BR.confiner(parent(ch))
    infos = PV.infos_clip(par)
    envoi, inf_env, notes = PV.conformer_clip(par, infos, MODELE, float(infos.get("secondes") or 4.0))
    m = VR.REGISTRE_REFS[MODELE]
    refus = None
    if sum(1 for e in ch["etapes"] if e.get("statut") in ("fait", "en_cours")) >= MAX_ETAPES:
        refus = f"{MAX_ETAPES} étapes au plus par chaîne."
    elif any(e.get("statut") == "en_cours" for e in ch["etapes"]):
        refus = "Une étape est déjà en cours sur cette chaîne."
    else:
        refus = VR.clip_refuse(MODELE, nom=inf_env.get("nom_envoye") or par.name, secondes=inf_env.get("secondes"),
                               largeur=inf_env.get("largeur"), hauteur=inf_env.get("hauteur"), fps=inf_env.get("fps"),
                               octets=inf_env.get("octets"))
    s_in = float(inf_env.get("secondes") or 0.0)
    s_out = max(float(m.get("duree_min_s") or 4.0), round(s_in))
    usd = VR.cout_estime(MODELE, int(round(s_out)), entree_s=s_in, resolution=resolution)
    return {"chaine": cid, "parent": _rel(par), "prompt": prompt, "consigne": " ".join(str(consigne).split())[:MAX_CONSIGNE],
            "resolution": resolution, "secondes_entree": round(s_in, 3), "secondes_sortie": s_out,
            "conform": inf_env.get("conform"), "notes": notes, "usd": round(float(usd or 0.0), 4),
            "op": VR.op_devis(MODELE, s_out, secondes_entree=s_in, resolution=resolution),
            "references": [_rel(r) for r in refs] or ["(image du milieu du parent)"], "ancres": list(ancres or [])[:4],
            "refus": refus, "n": len(ch["etapes"]) + 1, "modele": MODELE, "label": m["label"]}


def reserver(cid: str, d: dict) -> int:
    """Inscrit l'étape « en_cours » (avant le tir) ; rend son numéro. ValueError si une autre est en cours."""
    with _VERROU:
        ch = lire(cid)
        if ch is None:
            raise ValueError("Chaîne inconnue.")
        if any(e.get("statut") == "en_cours" for e in ch["etapes"]):
            raise ValueError("Une étape est déjà en cours sur cette chaîne.")
        n = len(ch["etapes"]) + 1
        ch["etapes"].append({"n": n, "parent": d["parent"], "consigne": d["consigne"], "prompt": d["prompt"],
                             "resolution": d["resolution"], "ancres": d["ancres"], "usd": d["usd"],
                             "statut": "en_cours", "debut": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        _ecrire(ch)
        return n


def terminer(cid: str, n: int, **champs) -> dict:
    with _VERROU:
        ch = lire(cid)
        if ch is None:
            raise ValueError("Chaîne inconnue.")
        e = next(x for x in ch["etapes"] if x["n"] == n)
        e.update(champs, fin=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        _ecrire(ch)
        return e


async def tirer(cid: str, n: int, d: dict) -> dict:
    """PAYANT — le tir d'une étape RÉSERVÉE (la route a passé clé, confirmation et plafond). Conform, tir, recalage au
    nombre d'images du parent, mesure (B3) ; l'étape passe « fait » (sortie, mesure, graine) ou « echec » (raison)."""
    import asyncio
    from app.services import ancres as AN
    from app.services import previs_plan as PV
    from app.services import revue_plan as RV
    par = BR.confiner(d["parent"])
    dossier = _dossier() / cid
    tmp: list[Path] = []
    try:
        infos = PV.infos_clip(par)
        envoi, _inf, _notes = await asyncio.to_thread(PV.conformer_clip, par, infos, MODELE,
                                                      float(infos.get("secondes") or 4.0), None, True, dossier)
        if envoi != par:
            tmp.append(Path(envoi))
        refs = AN.references(d["ancres"]) if d["ancres"] else []
        if not refs:
            im = await asyncio.to_thread(RV.image_a, par, 0.5)
            ref = dossier / f"ref_{n:02d}.png"
            im.save(ref)
            tmp.append(ref)
            refs = [ref]
        res = await PV.tirer_previs(MODELE, clip=envoi, frames=refs, prompt=d["prompt"], tache="editing",
                                    resolution=d["resolution"], duree=int(d["secondes_sortie"]), dossier=dossier)
        v = Path(res["video"])
        recalage = None
        try:
            rc = await asyncio.to_thread(PV.recaler, v, par, infos, d.get("conform"))
            Path(rc["video"]).replace(v)
            recalage = {k: rc[k] for k in ("derive_images", "fiable", "images")}
        except Exception as e:  # noqa: BLE001 — le rendu payé reste ; la raison est rangée
            recalage = {"erreur": str(e)[:300]}
        sortie = dossier / f"{n:02d}_etape{v.suffix}"
        v.replace(sortie)
        try:
            mesure = (await asyncio.to_thread(BR.comparer, d["parent"], _rel(sortie)))["resume"]
        except Exception as e:  # noqa: BLE001
            mesure = {"erreur": str(e)[:300]}
        return terminer(cid, n, statut="fait", sortie=_rel(sortie), recalage=recalage, mesure=mesure,
                        seed=res.get("seed"), endpoint=res.get("endpoint"))
    except Exception as e:  # noqa: BLE001 — jamais d'étape fantôme « en_cours »
        return terminer(cid, n, statut="echec", erreur=str(e)[:500])
    finally:
        for t in tmp:
            t.unlink(missing_ok=True)
