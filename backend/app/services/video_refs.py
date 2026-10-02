"""Tâche #62 (plan chapitres T9, 02/10/2026) — la vidéo MULTI-RÉFÉRENCES : le constructeur d'arguments, rien d'autre.

DÉCISION DE L'UTILISATEUR (02/10) : « constructeur, registre à part ». Ce registre n'est PAS `fal_service.VIDEO_MODELS`
(il n'apparaît donc dans aucun sélecteur du Studio ni du Quick), ce module n'importe aucun client réseau et aucune
route ne l'appelle : il livre l'ARGUMENT, pas la facture. Le brancher sera une décision à part, coût annoncé.

Champs relus sur fal.ai le 02/10/2026 (le plan du 03/09 en avait deux faux) :
  - Veo 3.1 reference-to-video — `fal-ai/veo3.1/reference-to-video` : `image_urls` (liste plate ; le plan disait
    `reference_image_urls`), `duration` "8s", `aspect_ratio` 16:9 | 9:16, `resolution` 720p | 1080p | 4k,
    `generate_audio` (vrai par défaut : on le met à faux, la moitié du prix), pas de `seed`. 0,20 $/s sans audio,
    0,40 $/s avec. fal ne documente AUCUN maximum d'images : 3 est notre prudence (le « ingredients » de Veo 3.1).
  - Kling v3 Pro — `fal-ai/kling-video/v3/pro/image-to-video` : `elements`, des objets {frontal_image_url,
    reference_image_urls (1 à 3)} (le plan disait {image_url}), nommés @Element1… dans le prompt ; `start_image_url`
    REQUIS ; pas de `seed`. Aucun maximum d'éléments documenté : 4 est notre prudence. Prix non publié : inconnu.
Au-delà d'un plafond, on TRONQUE et on le DIT dans `notes` — jamais d'échec silencieux ni de facture surprise.
"""
from __future__ import annotations

VERIFIE_LE = "2026-10-02"

REGISTRE_REFS: dict[str, dict] = {
    "veo-3.1-ref": {
        "label": "Veo 3.1 références (fal)",
        "endpoint": "fal-ai/veo3.1/reference-to-video",
        "grammaire": "liste", "champ": "image_urls",
        "refs": (1, 3),                       # prudence : fal ne publie pas de maximum
        "durees": (8,), "ratios": ("16:9", "9:16"), "resolutions": ("720p", "1080p", "4k"),
        "audio_param": "generate_audio",
        "usd_s": {"sans_audio": 0.20, "avec_audio": 0.40},
    },
    "kling-v3-pro-elements": {
        "label": "Kling v3 Pro éléments (fal)",
        "endpoint": "fal-ai/kling-video/v3/pro/image-to-video",
        "grammaire": "elements", "champ": "elements",
        "refs": (1, 4),                       # éléments ; prudence : fal ne publie pas de maximum
        "vues_par_element": (1, 3),           # reference_image_urls : au moins une, au plus trois
        "durees": tuple(range(3, 16)), "ratios": None, "resolutions": None,
        "audio_param": "generate_audio",
        "usd_s": None,                        # prix non publié : le coût sera DIT inconnu
    },
}


def cout_estime(model_id: str, duree: int, audio: bool = False) -> float | None:
    """Le coût annoncé avant tout tir : durée × tarif à la seconde, ou None (inconnu, et l'écran le dira)."""
    m = REGISTRE_REFS[model_id]
    if not m["usd_s"]:
        return None
    return round(duree * m["usd_s"]["avec_audio" if audio else "sans_audio"], 2)


def _duree(m: dict, d: int, notes: list) -> int:
    if d in m["durees"]:
        return d
    proche = min(m["durees"], key=lambda x: (abs(x - d), x))
    notes.append(f"durée {d}s -> {proche}s ({m['label']})")
    return proche


def construire(model_id: str, prompt: str, entites: list[dict], *, start_image_url: str | None = None,
               duree: int = 8, aspect_ratio: str = "9:16", resolution: str | None = "1080p",
               audio: bool = False) -> tuple[str, dict, list[str]]:
    """(endpoint, arguments, notes) — fonction PURE. `entites` : [{"nom", "face": url, "vues": [url, …]}] dans
    l'ordre du plan. Veo reçoit une liste plate (la face de chacune d'abord, entrelacée) ; Kling un élément par
    entité (face + 1 à 3 vues), nommé @ElementN dans le prompt."""
    m = REGISTRE_REFS.get(model_id)
    if not m:
        raise ValueError(f"« {model_id} » n'est pas au registre des références.")
    lo, hi = m["refs"]
    notes: list[str] = []
    args: dict = {"prompt": prompt}
    if m["grammaire"] == "liste":
        files = [[u for u in [e.get("face")] + list(e.get("vues") or []) if u] for e in entites]
        urls: list[str] = []
        for rang in range(max((len(f) for f in files), default=0)):
            for f in files:
                if rang < len(f) and f[rang] not in urls:
                    urls.append(f[rang])
        if len(urls) < lo:
            raise ValueError(f"{m['label']} demande au moins {lo} image(s) de référence ({len(urls)} fournie(s)).")
        if len(urls) > hi:
            notes.append(f"{len(urls)} références -> {hi} (plafond {m['label']})")
            urls = urls[:hi]
        args[m["champ"]] = urls
    else:
        if not start_image_url:
            raise ValueError(f"{m['label']} exige une image de départ (start_image_url).")
        args["start_image_url"] = start_image_url
        vlo, vhi = m["vues_par_element"]
        elements = []
        for e in entites:
            vues = [u for u in (e.get("vues") or []) if u and u != e.get("face")]
            if not e.get("face") or len(vues) < vlo:
                notes.append(f"{e.get('nom') or '?'} écartée : il faut une face et au moins {vlo} autre vue")
                continue
            if len(vues) > vhi:
                notes.append(f"{e.get('nom') or '?'} : {len(vues)} vues -> {vhi}")
            elements.append({"frontal_image_url": e["face"], "reference_image_urls": vues[:vhi]})
        if len(elements) < lo:
            raise ValueError(f"{m['label']} demande au moins {lo} élément complet de référence.")
        if len(elements) > hi:
            notes.append(f"{len(elements)} éléments -> {hi} (plafond {m['label']})")
            elements = elements[:hi]
        args["elements"] = elements
        absents = [f"@Element{i}" for i in range(1, len(elements) + 1) if f"@Element{i}" not in prompt]
        if absents:
            notes.append("le prompt ne nomme pas " + ", ".join(absents) + " : Kling ne saura pas qui est qui")
    d = _duree(m, int(duree), notes)
    args["duration"] = f"{d}s" if m["grammaire"] == "liste" else d
    if m["ratios"] and aspect_ratio in m["ratios"]:
        args["aspect_ratio"] = aspect_ratio
    if m["resolutions"] and resolution in m["resolutions"]:
        args["resolution"] = resolution
    args[m["audio_param"]] = bool(audio)
    return m["endpoint"], args, notes
