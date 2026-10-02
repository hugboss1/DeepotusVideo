"""Tâche #67 (plan-studio T1-T2, 02/10/2026) — ÉPINGLER le résultat d'un nœud du Studio pour ne pas le repayer.

DÉCISIONS DE L'UTILISATEUR (02/10) :
  - l'épingle vaut tant que l'EMPREINTE DE LA REQUÊTE RÉELLE n'a pas bougé : ce que le serveur enverrait VRAIMENT au
    fournisseur pour ce nœud — modèle effectif (le défaut résolu), format (pour HeyGen : celui de la RÉGION), durée,
    prompt, voix, mode voix effectif (celui du rendu quand le nœud n'en a pas), et le CONTENU des fichiers d'entrée
    (une image réécrite sous le même nom change l'empreinte). L'empreinte du graphe amont (le plan du 03/09) ratait le
    format venu du nœud Rendu, le modèle par défaut et le mode voix : un clip au mauvais format était réemployé ;
  - l'épingle est posée automatiquement après un rendu, un geste « Regénérer » la retire (côté éditeur) ;
  - un nœud seul (parti par /generate, hors rendu de graphe) n'a pas d'épingle.

Le réemploi est GRATUIT : un slot épinglé valide devient la vidéo du sous-rendu déjà payé (comme la branche « job »),
et la garde de coût ne le compte pas. Le serveur est la SEULE source de l'empreinte : l'éditeur la reçoit (manifeste
des parties, route de vérification), il ne la recalcule jamais.

Le manifeste des parties (outputs/_parts/<rendu>.json) dit quel nœud a produit quel sous-rendu, avec son empreinte —
écrit À CHAQUE sous-rendu fini : un échec plus loin ne perd pas ce qui est déjà payé.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from app.config import settings

# ce qui ne change pas le clip produit (garde de coût, notes, graphe source, recette Quick)
EXCLUS = {"max_usd", "notes", "source_graph", "quick_recipe"}
_ID_SUR = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _sha1_fichier(nom: str | None, dossiers: tuple[Path, ...]) -> str | None:
    if not nom:
        return None
    for d in dossiers:
        p = Path(d) / Path(str(nom)).name
        if p.is_file():
            h = hashlib.sha1()
            with open(p, "rb") as f:
                for bloc in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloc)
            return h.hexdigest()
    return "absent"


def _audio_dir() -> Path:
    try:
        from app.services.montage_service import _audio_dir as _ad
        return _ad()
    except Exception:
        return settings.images_path.parent / "audio"


def _contenus(d: dict) -> dict:
    """Les empreintes des FICHIERS cités par la requête (images de départ/fin, fichiers audio des sous-objets)."""
    out = {}
    img = (settings.images_path, settings.outputs_path)
    for k in ("image_filename", "image_filename_end"):
        if d.get(k):
            out[k] = _sha1_fichier(d[k], img)
    for k, v in d.items():
        if isinstance(v, dict) and v.get("file"):
            out[f"{k}.file"] = _sha1_fichier(v["file"], (_audio_dir(),))
    return out


def charge_utile(sv, *, voice_mode=None, heygen_aspect: str | None = None) -> dict | None:
    """La requête RÉELLE d'un slot Seedance / HeyGen, normalisée ; None pour tout autre slot."""
    kind = getattr(sv, "source_kind", None)
    vm = getattr(voice_mode, "value", voice_mode)
    if kind == "seedance" and getattr(sv, "seedance", None) is not None:
        from app.services.fal_service import resolve_video_model
        d = {k: v for k, v in sv.seedance.model_dump(mode="json").items() if k not in EXCLUS}
        d["video_model"] = resolve_video_model(d.get("video_model"))["id"]
        if not d.get("voice_mode") and vm:
            d["voice_mode"] = vm
    elif kind == "heygen" and getattr(sv, "heygen", None) is not None:
        d = {k: v for k, v in sv.heygen.model_dump(mode="json").items() if k not in EXCLUS}
        if heygen_aspect:
            d["aspect_ratio"] = heygen_aspect
        if not d.get("voice_mode") and vm:
            d["voice_mode"] = vm
    else:
        return None
    return {"kind": kind, "requete": d, "fichiers": _contenus(d)}


def empreinte(sv, *, voice_mode=None, heygen_aspect: str | None = None) -> str | None:
    c = charge_utile(sv, voice_mode=voice_mode, heygen_aspect=heygen_aspect)
    if c is None:
        return None
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:32]


async def verifier(sv, emp: str | None) -> tuple[bool, str, Path | None]:
    """(valide, raison, vidéo) de l'épingle d'un slot. Valide = même empreinte ET sous-rendu fini dont la vidéo existe."""
    from app.services.storage import JobRecord, async_session_factory
    from app.models.schemas import JobStatus
    pin = getattr(sv, "pin", None)
    if not isinstance(pin, dict) or not pin.get("job_id"):
        return False, "pas d'épingle", None
    if not emp:
        return False, "slot sans empreinte (ni Seedance ni HeyGen)", None
    if pin.get("empreinte") != emp:
        return False, "la requête a changé (réglages, entrées, modèle, format ou fichiers)", None
    async with async_session_factory() as s:
        jr = await s.get(JobRecord, str(pin["job_id"]))
    if jr is None or jr.status != JobStatus.DONE.value:
        return False, "le rendu épinglé n'existe plus (ou n'est pas fini)", None
    fp = jr.final_video_path or jr.video_path
    if not fp or not Path(fp).is_file():
        return False, "la vidéo épinglée a disparu du disque", None
    return True, "réemploi : même requête, déjà payée", Path(fp)


# ─────────────────────────────────────────── le manifeste des parties ───────────────────────────────────────────

def _dossier_parts() -> Path:
    d = settings.outputs_path / "_parts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chemin_parts(rendu_id: str) -> Path | None:
    if not _ID_SUR.match(rendu_id or ""):
        return None
    return _dossier_parts() / f"{rendu_id}.json"


def ecrire_partie(rendu_id: str, partie: dict) -> None:
    """Ajoute UNE partie au manifeste du rendu, tout de suite (écriture atomique)."""
    p = chemin_parts(rendu_id)
    if p is None:
        return
    doc = lire_parts(rendu_id) or {"rendu": rendu_id, "parts": []}
    doc["parts"] = [x for x in doc["parts"] if x.get("slot") != partie.get("slot")] + [
        dict(partie, ecrit_le=datetime.utcnow().isoformat(timespec="seconds") + "Z")]
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def lire_parts(rendu_id: str) -> dict | None:
    p = chemin_parts(rendu_id)
    if p is None or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
