"""t283 (23/10/2026) — la RECETTE d'un rendu, unifiée : ce qu'il faut pour le refaire dans Quick ou dans Studio.

Trois sources, lues dans cet ordre et sans rien inventer :
  1. la recette Quick (`quick_recipe`, le formulaire exact : prompt SAISI, ambiance, modèle…) ;
  2. les colonnes du job : `final_prompt` est le prompt EXACT envoyé au modèle (prompt libre + caméra + curseurs,
     `prompt_engine.build_prompt`), `negative_prompt`, modèle, durée, format, graine, images, style, espace, parent ;
  3. la recette d'un IMPORT (`/api/videos/upload`) : jointe à l'upload (`_recipes/{job}.import.json`) ou posée à côté
     de la vidéo (`<nom>.recette.json`) — par exemple une composition HyperFrames et les prompts de ses clips.
AUCUN coût n'est repris : l'écran réestime au tarif du jour (décision du brief : « le coût est réestimé, jamais
repris tel quel »)."""
import json
from pathlib import Path

from app.config import settings
from app.services import quick_recipe

TAILLE_MAX = quick_recipe.TAILLE_MAX          # 64 Ko : une recette est un formulaire, pas un fichier


class RecetteInvalide(ValueError):
    """Une recette d'import illisible (JSON cassé, pas un objet, trop grosse) : l'upload la refuse en 400."""


def lire_import_brut(texte) -> dict | None:
    """Le champ `recette` de l'upload : None s'il est absent ou vide, un objet sinon ; RecetteInvalide s'il ne l'est
    pas. Contrôlé AVANT d'écrire la vidéo : un upload refusé ne laisse aucun fichier."""
    if texte is None or not str(texte).strip():
        return None
    brut = str(texte)
    if len(brut.encode("utf-8")) > TAILLE_MAX:
        raise RecetteInvalide(f"recette trop grosse ({len(brut)} car., {TAILLE_MAX // 1024} Ko au plus)")
    try:
        v = json.loads(brut)
    except ValueError as e:
        raise RecetteInvalide(f"recette illisible : {e}") from e
    if not isinstance(v, dict):
        raise RecetteInvalide("la recette doit être un objet JSON")
    return v


def _chemin_import(job_id: str) -> Path | None:
    nom = Path(str(job_id or "")).name
    if not nom or nom in (".", ".."):
        return None
    d = settings.outputs_path / "_recipes"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{nom}.import.json"


def enregistrer_import(job_id: str, recette: dict) -> bool:
    p = _chemin_import(job_id)
    if p is None or not isinstance(recette, dict) or not recette:
        return False
    p.write_text(json.dumps(recette, ensure_ascii=False), encoding="utf-8")
    return True


def _json_fichier(p: Path) -> dict | None:
    try:
        if p.is_file() and p.stat().st_size <= TAILLE_MAX:
            v = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None
    return None


def recette_import(job) -> dict | None:
    """La recette jointe à l'upload, sinon le fichier `<nom>.recette.json` posé à côté de la vidéo importée."""
    p = _chemin_import(job.id)
    r = _json_fichier(p) if p else None
    if r:
        return r
    fp = job.final_video_path or job.video_path
    if fp:
        v = Path(fp)
        return _json_fichier(v.with_name(v.stem + ".recette.json"))
    return None


def _graphe_studio(job_id: str) -> bool:
    nom = Path(str(job_id or "")).name
    return bool(nom) and (settings.outputs_path / "_graphs" / f"{nom}.json").is_file()


def _vide(v):
    return None if v in (None, "") else v


def recette(job) -> dict:
    """La recette unifiée d'un `JobRecord`."""
    q = quick_recipe.load(job.id)
    imp = recette_import(job) if (job.provider or "") == "ugc" else None
    sd = (q or {}).get("seedance") or {}
    out = {
        "job_id": job.id,
        "source": "quick" if q else ("import" if imp else ("aucune" if (job.provider or "") == "ugc" else "job")),
        "prompt": _vide(sd.get("prompt")) if q and sd.get("prompt") else _vide(job.final_prompt),
        "prompt_envoye": _vide(job.final_prompt),       # le prompt EXACT reçu par le modèle (graphe Studio)
        "negative": _vide(job.negative_prompt),
        "model": _vide(sd.get("model")) or _vide(job.video_model),
        "duration_s": (int(sd["duration"]) if q and str(sd.get("duration") or "").isdigit() else job.duration_s),
        "aspect_ratio": _vide(sd.get("aspect")) or _vide(job.aspect_ratio),
        "seed": job.seed,
        "style": _vide(job.style),
        "template_id": _vide(job.template_id),
        "image": _vide(sd.get("image")) or _vide(job.image_filename),
        "image_end": _vide(sd.get("end")) or _vide(job.image_filename_end),
        "provider": _vide(job.provider),
        "espace_id": _vide(getattr(job, "espace_id", None)),
        "parent_job_id": _vide(getattr(job, "parent_job_id", None)),
        "studio": _graphe_studio(job.id),
        "quick": q,
        "import": imp,
    }
    if out["source"] in ("import", "aucune"):
        # un import n'a ni prompt propre ni modèle : seulement ce que sa recette jointe dit (affichée telle quelle)
        # l'upload écrit « 9:16 » en dur (routes.upload_video) : le format d'un import vient de SA recette, sinon rien
        out["aspect_ratio"] = _vide((imp or {}).get("aspect_ratio") or (imp or {}).get("format"))
        out.update({"prompt": None, "prompt_envoye": None, "negative": None, "model": None, "seed": None, "style": None, "image": None,
                    "image_end": None})
    return out
