"""Plan Quick T8 (tâche #54, D2, 01/10/2026) — six curseurs chiffrés -> une phrase de caméra, par famille de modèle.

Pourquoi du texte : mesuré le 03/09/2026 (R1), aucun modèle du registre n'expose de `camera_control` via fal (Kling v3
Pro n'en a pas), et Runway a retiré son contrôle chiffré le 30/07/2026 — Gen-4 pilote la caméra par le prompt. Les
curseurs sont donc un dialecte que l'on TRADUIT.

Le vocabulaire de la famille `kling` reprend celui de l'application Kling (six axes en commandes absolues) ; les autres
familles utilisent notre propre anglais de plateau — ce n'est pas une affirmation sur leur API. Si l'API Kling directe
entre un jour au registre, les mêmes curseurs alimenteront `camera_control` sans changer l'écran.

Fonction pure, sans dépendance : arithmétique et tables. La traduction n'existe QU'ICI : l'aperçu de l'écran passe par
la route `/quick/camera-phrase`, pour ne jamais diverger du rendu.
"""
from app.services.fal_service import VIDEO_MODELS

#: ordre d'énonciation — stable, indépendant de l'ordre des clés reçues
AXES = ("zoom", "horizontal", "vertical", "pan", "tilt", "roll")

_NEUTRE = {
    "zoom": ("pushing in", "pulling out"),
    "horizontal": ("tracking right", "tracking left"),
    "vertical": ("craning up", "craning down"),
    "pan": ("panning right", "panning left"),
    "tilt": ("tilting up", "tilting down"),
    "roll": ("rolling clockwise", "rolling counter-clockwise"),
}
_KLING = {
    "zoom": ("zoom in", "zoom out"),
    "horizontal": ("horizontal movement right", "horizontal movement left"),
    "vertical": ("vertical movement up", "vertical movement down"),
    "pan": ("pan right", "pan left"),
    "tilt": ("tilt up", "tilt down"),
    "roll": ("roll clockwise", "roll counter-clockwise"),
}
#: famille (fal_service.VIDEO_MODELS[...]["family"]) -> lexique
FAMILLES: dict = {
    "neutre": _NEUTRE, "kling": _KLING, "seedance1": _NEUTRE,
    "seedance2": _NEUTRE, "seedance25": _NEUTRE, "pixverse": _NEUTRE,
    "veo_fal": _NEUTRE, "veo_google": _NEUTRE,
}
#: |valeur| -> qualificatif. 0 = l'axe est muet.
_FORCE = ((3, "slightly"), (7, ""), (10, "strongly"))


def famille_du_modele(model_id: str | None) -> str:
    """La famille du modèle, `neutre` si l'id est inconnu (jamais d'exception : une phrase de caméra ne doit pas
    pouvoir faire échouer un rendu)."""
    m = VIDEO_MODELS.get((model_id or "").strip()) if isinstance(model_id, str) else None
    fam = (m or {}).get("family") or "neutre"
    return fam if fam in FAMILLES else "neutre"


def _mot(lex: dict, axe: str, v: int) -> str:
    base = lex[axe][0 if v > 0 else 1]
    n = min(10, abs(int(v)))
    q = next(q for seuil, q in _FORCE if n <= seuil)
    return f"{q} {base}".strip()


def phrase(ctrl, family: str = "neutre") -> str:
    """`ctrl` = {axe: -10..10}. Rend `Camera: a, b, c.` ou `""` si tout est nul."""
    if not isinstance(ctrl, dict):
        return ""
    lex = FAMILLES.get(family) or _NEUTRE
    bouts = []
    for axe in AXES:
        try:
            v = int(round(float(ctrl.get(axe) or 0)))
        except (TypeError, ValueError, OverflowError):
            v = 0
        if v:
            bouts.append(_mot(lex, axe, max(-10, min(10, v))))
    return ("Camera: " + ", ".join(bouts) + ".") if bouts else ""


def phrase_pour(ctrl, model_id: str | None) -> str:
    return phrase(ctrl, famille_du_modele(model_id))
