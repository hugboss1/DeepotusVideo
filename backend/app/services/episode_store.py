# -*- coding: utf-8 -*-
"""Store des épisodes narrés (P1 t132 — lot B de #6, 28/09/2026).

Spec 2026-06-22 « Épisodes narrés » : un épisode vit en JSON sous
`outputs/_episodes/{id}.json` (comme `outputs/_graphs/`), ses médias sous
`outputs/episodes/{id}/`. Jusqu'ici rien n'était enregistré : l'état de la
page se perdait au changement de vue, et chaque assemblage repayait la
narration de TOUTES les scènes.

Le document est gardé TEL QU'ÉCRIT (leçon de la tâche #4 : une recopie champ
par champ perd tout champ qu'elle ne connaît pas) ; seuls `id`, `created_at`
et `updated_at` appartiennent au store. Les identifiants sont validés par
expression régulière AVANT de toucher au disque : jamais un chemin hors du
store.

Narration par scène (décision de l'utilisateur, 28/09) : un mp3 par clé
(texte + voix + langue) sous `outputs/episodes/{id}/narr/{clé}.mp3`. Le
rendu (`run_episode(episode_id=…)`) et `/episodes/{id}/narrate` le LISENT et
le REMPLISSENT : une scène déjà narrée n'est jamais repayée.
"""
import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

ID_RE = re.compile(r"ep_[0-9a-f]{12}")
TAILLE_MAX = 4 * 1024 * 1024     # un chapitre + ses scènes tient très en dessous
_RESERVES = ("id", "created_at", "updated_at")


def _dossier() -> Path:
    d = settings.outputs_path / "_episodes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def dossier_media(ep_id: str) -> Path:
    if not isinstance(ep_id, str) or not ID_RE.fullmatch(ep_id):
        raise ValueError(f"identifiant d'épisode invalide : {ep_id!r}")
    return settings.outputs_path / "episodes" / ep_id


def _chemin(ep_id) -> Path | None:
    if not isinstance(ep_id, str) or not ID_RE.fullmatch(ep_id):
        return None
    return _dossier() / f"{ep_id}.json"


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ecrire(doc: dict) -> dict:
    brut = json.dumps(doc, ensure_ascii=False)
    if len(brut.encode("utf-8")) > TAILLE_MAX:
        raise ValueError(f"épisode trop gros (> {TAILLE_MAX // (1024 * 1024)} Mo)")
    p = _chemin(doc["id"])
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(brut, encoding="utf-8")
    tmp.replace(p)
    return doc


def _corps(brut) -> dict:
    if not isinstance(brut, dict):
        raise ValueError("le corps d'un épisode est un objet JSON")
    return {k: v for k, v in brut.items() if k not in _RESERVES}


def creer(brut: dict) -> dict:
    t = _maintenant()
    doc = {"id": "ep_" + uuid.uuid4().hex[:12], **_corps(brut),
           "created_at": t, "updated_at": t}
    return _ecrire(doc)


def lire(ep_id) -> dict | None:
    p = _chemin(ep_id)
    if p is None or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def remplacer(ep_id: str, brut: dict) -> dict | None:
    ancien = lire(ep_id)
    if ancien is None:
        return None
    doc = {"id": ep_id, **_corps(brut), "created_at": ancien.get("created_at"),
           "updated_at": _maintenant()}
    return _ecrire(doc)


def completer(ep_id: str, **champs) -> dict | None:
    """Fusionne des champs du serveur (last_job_id, narration…) sans toucher
    au reste du document."""
    ancien = lire(ep_id)
    if ancien is None:
        return None
    ancien.update({k: v for k, v in champs.items() if k not in _RESERVES})
    ancien["updated_at"] = _maintenant()
    return _ecrire(ancien)


def lister() -> list[dict]:
    out = []
    for p in _dossier().glob("ep_*.json"):
        if not ID_RE.fullmatch(p.stem):
            continue
        d = lire(p.stem)
        if not d:
            continue
        out.append({"id": d["id"], "title": d.get("title") or "",
                    "language": d.get("language") or "",
                    "scene_count": len(d.get("scenes") or []),
                    "updated_at": d.get("updated_at") or "",
                    "last_job_id": d.get("last_job_id") or ""})
    out.sort(key=lambda x: x["updated_at"], reverse=True)
    return out


def supprimer(ep_id) -> bool:
    p = _chemin(ep_id)
    if p is None or not p.is_file():
        return False
    p.unlink()
    shutil.rmtree(dossier_media(ep_id), ignore_errors=True)
    return True


# ── narration par scène ───────────────────────────────────────────────────

def cle_narration(texte: str, voice_id, langue) -> str:
    base = f"{str(langue or '').lower()}|{voice_id or ''}|{(texte or '').strip()}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def chemin_narration(ep_id: str, cle: str) -> Path:
    return dossier_media(ep_id) / "narr" / f"{cle}.mp3"
