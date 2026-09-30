"""P1 (plan Quick T1, tâche #48 du suivi, 01/10/2026) — la RECETTE d'un rendu Quick : le JSON exact que l'écran a
envoyé, écrit à côté du graphe Studio (`outputs/_graphs`), même patron. Un fichier et pas une colonne : la recette
grossit à chaque tâche du plan (sous-titres, lip-sync, caméra) et un JSON par job ne demande aucune migration.
Écrit AVANT tout appel payant : si le fournisseur échoue, la recette existe quand même."""
import json
from pathlib import Path

from loguru import logger

from app.config import settings

TAILLE_MAX = 64 * 1024     # une recette est un formulaire, pas un fichier : au-delà, on n'écrit pas


def _dir() -> Path:
    d = settings.outputs_path / "_recipes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _chemin(job_id: str) -> Path | None:
    nom = Path(str(job_id or "")).name
    if not nom or nom in (".", ".."):
        return None
    return _dir() / f"{nom}.json"


def save(job_id: str, recipe) -> bool:
    """Silencieux sur échec (un log) : une recette perdue ne vaut pas un rendu perdu. Rend True si écrite."""
    if not isinstance(recipe, dict) or not recipe:
        return False
    p = _chemin(job_id)
    if p is None:
        return False
    try:
        texte = json.dumps(recipe, ensure_ascii=False)
        if len(texte.encode("utf-8")) > TAILLE_MAX:
            logger.warning(f"quick_recipe: recette de {job_id} trop grosse ({len(texte)} car.) - non ecrite")
            return False
        p.write_text(texte, encoding="utf-8")
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"quick_recipe save failed for {job_id}: {e}")
        return False


def load(job_id: str) -> dict | None:
    p = _chemin(job_id)
    if p is None or not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) else None
