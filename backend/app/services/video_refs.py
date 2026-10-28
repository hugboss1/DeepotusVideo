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

t335 (A5 du lot Scenario, 28/10/2026) — BRANCHÉ : les routes /shots/{id}/previs (mode « Previs → plan » de la fiche
du plan) l'appellent ; ce module reste PUR (aucun client réseau, aucun tir : il livre l'argument et le prix). Le
registre gagne Seedance 2.5 reference-to-video, le video-to-video de scenario.com (« @Video1 clay + @Image1 still »),
relu sur fal.ai le 28/10/2026 :
  - `bytedance/seedance-2.5/reference-to-video` (il n'existe PAS d'endpoint « video-to-video » Seedance chez fal : le
    v2v passe par CET endpoint, `video_urls` + `image_urls`) : `task` auto | reference | editing | extension (editing =
    garde le mouvement et la caméra du clip, durée et cadre « auto » ; reference = s'inspire du clip, durée choisie
    4-30 s), `image_urls` (30 au plus ; 4 est notre prudence), `video_urls` (MP4/MOV, 1,8 à 30,2 s chacune et au
    total, côtés 300 à 6 000 px, rapport 0,4 à 2,5, 24 à 60 i/s, 200 Mo), `resolution` 480p | 720p | 1080p,
    `duration` auto | 4-30, `aspect_ratio` auto…, `generate_audio` (même prix : coupé, la bande son reste à l'app),
    `seed`. Les références se nomment @Video1, @Image1, @Image2… dans le prompt.
  - PRIX : 0,0214 $ / 1 000 jetons en 480p et 720p (≈ 0,2205 $/s et 0,4730 $/s, cas 16:9), et « si une vidéo de
    référence est fournie, le prix est multiplié par 0,6 » ; les secondes du clip d'ENTRÉE sont facturées en plus de
    celles de SORTIE. Devis = (entrée + sortie) × tarif × 0,6. 1080p (≈ 1,164 $/s, autre tarif aux jetons) reste HORS
    registre, comme pour seedance-2.5 dans fal_service.
Kling (éléments) garde un prix NON PUBLIÉ : la route le refuse en 400 plutôt que de tirer sans devis.
"""
from __future__ import annotations

VERIFIE_LE = "2026-10-02"
VERIFIE_SEEDANCE_LE = "2026-10-28"   # t335 : Seedance 2.5 reference-to-video, schéma et prix relus

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
    # t335 — le video-to-video « previs → plan » : UN clip (@Video1) + des style frames (@Image1…)
    "seedance-2.5-v2v": {
        "label": "Seedance 2.5 previs → plan (fal)",
        "endpoint": "bytedance/seedance-2.5/reference-to-video",
        "grammaire": "video", "champ": "image_urls", "champ_video": "video_urls",
        "refs": (1, 4),                       # style frames ; fal en accepte 30 : 4 est notre prudence
        "taches": ("editing", "reference"),   # editing = garde le mouvement et la caméra du clip (défaut)
        "clip_s": (1.8, 30.2),                # durée d'un clip d'entrée (et du total), schéma fal
        "clip_cotes": (300, 6000), "clip_rapport": (0.4, 2.5), "clip_fps": (24, 60),
        "clip_octets": 200 * 1024 * 1024, "clip_ext": (".mp4", ".mov"),
        "durees": tuple(range(4, 31)), "ratios": None, "resolutions": ("480p", "720p"),
        "audio_param": "generate_audio",
        "usd_s": {"480p": 0.2205, "720p": 0.473},   # par seconde (entrée + sortie), AVANT le × 0,6
        "mult_video": 0.6,
    },
}

# t335 — les modèles que les routes « previs → plan » savent chiffrer et tirer (Kling : prix non publié, refusé)
MODELES_PREVIS = ("seedance-2.5-v2v", "veo-3.1-ref")
DEFAUT_PREVIS = "seedance-2.5-v2v"


def cout_estime(model_id: str, duree: int, audio: bool = False, *, entree_s: float = 0.0,
                resolution: str | None = None) -> float | None:
    """Le coût annoncé avant tout tir : durée × tarif à la seconde, ou None (inconnu, et l'écran le dira).
    t335 — Seedance v2v : (secondes du clip d'ENTRÉE + secondes de SORTIE) × tarif de la résolution × 0,6."""
    m = REGISTRE_REFS[model_id]
    if not m["usd_s"]:
        return None
    if m["grammaire"] == "video":
        taux = m["usd_s"].get(resolution or "720p")
        if taux is None:
            return None
        return round((max(0.0, float(entree_s)) + max(0.0, float(duree))) * taux * m["mult_video"], 4)
    return round(duree * m["usd_s"]["avec_audio" if audio else "sans_audio"], 2)


def ligne(op: dict) -> dict:
    """t335 — UNE ligne de pricing.estimate pour le kind « video_refs » : {modele, secondes_sortie, secondes_entree?,
    resolution?, audio?}. Modèle inconnu ou prix non publié : une ligne à 0 QUI LE DIT (jamais un prix inventé)."""
    from app.services.pricing import _line
    mid = str(op.get("modele") or "")
    m = REGISTRE_REFS.get(mid)
    try:
        sortie = max(0.0, float(op.get("secondes_sortie") or 0))
        entree = max(0.0, float(op.get("secondes_entree") or 0))
    except (TypeError, ValueError):
        sortie = entree = 0.0
    if m is None:
        return _line("fal", f"Références vidéo : modèle inconnu {mid[:24]!r} (non chiffré)", sortie, "s", 0.0)
    usd = cout_estime(mid, sortie, bool(op.get("audio")), entree_s=entree, resolution=op.get("resolution"))
    if usd is None:
        return _line("fal", f"{m['label']} (prix non publié)", sortie + entree, "s", 0.0)
    return _line("fal", m["label"], sortie + entree, "s", usd)


def op_devis(model_id: str, secondes_sortie: float, *, secondes_entree: float = 0.0, resolution: str | None = None,
             audio: bool = False) -> dict:
    """t335 — l'op de pricing.estimate / plafonds.verifier d'un tir du registre (devis = garde = coût rendu)."""
    return {"kind": "video_refs", "modele": model_id, "secondes_sortie": round(float(secondes_sortie), 3),
            "secondes_entree": round(float(secondes_entree), 3), "resolution": resolution, "audio": bool(audio)}


def clip_refuse(model_id: str, *, nom: str, secondes, largeur, hauteur, fps, octets) -> str | None:
    """t335 — le PREMIER écart du clip d'entrée aux bornes du schéma (texte à montrer), ou None. Le conform
    automatique (étirer / compléter / transcoder) est la tâche t336 (A6) : il se branchera AVANT ce contrôle
    (`previs_plan.conformer_clip`)."""
    m = REGISTRE_REFS[model_id]
    if m["grammaire"] != "video":
        return None
    ext = ("." + nom.rsplit(".", 1)[-1].lower()) if "." in nom else ""
    if ext not in m["clip_ext"]:
        return f"format {ext or '?'} : MP4 ou MOV attendu"
    lo, hi = m["clip_s"]
    if not secondes or not (lo <= float(secondes) <= hi):
        return f"durée {float(secondes or 0):.2f} s hors de {lo} à {hi} s"
    clo, chi = m["clip_cotes"]
    if not largeur or not hauteur or not (clo <= largeur <= chi and clo <= hauteur <= chi):
        return f"côtés {largeur or '?'}×{hauteur or '?'} px hors de {clo} à {chi} px"
    rlo, rhi = m["clip_rapport"]
    if not (rlo <= largeur / hauteur <= rhi):
        return f"rapport {largeur / hauteur:.2f} hors de {rlo} à {rhi}"
    flo, fhi = m["clip_fps"]
    if fps is None or not (flo - 0.01 <= float(fps) <= fhi + 0.01):
        return f"cadence {float(fps or 0):.2f} i/s hors de {flo} à {fhi} i/s"
    if octets is not None and octets > m["clip_octets"]:
        return f"{octets // (1024 * 1024)} Mo : {m['clip_octets'] // (1024 * 1024)} Mo au plus"
    return None


def _duree(m: dict, d: int, notes: list) -> int:
    if d in m["durees"]:
        return d
    proche = min(m["durees"], key=lambda x: (abs(x - d), x))
    notes.append(f"durée {d}s -> {proche}s ({m['label']})")
    return proche


def _construire_video(m: dict, prompt: str, entites: list[dict], video_url: str | None, tache: str | None,
                      duree: int, resolution: str | None, audio: bool) -> tuple[str, dict, list[str]]:
    """t335 — Seedance 2.5 reference-to-video : `video_urls` = [le clip], `image_urls` = les style frames (la face de
    chaque entrée, dans l'ordre), `task`, et la durée SEULEMENT en « reference » (« editing » suit le clip)."""
    if not video_url:
        raise ValueError(f"{m['label']} exige un clip de previs (@Video1).")
    lo, hi = m["refs"]
    notes: list[str] = []
    urls: list[str] = []
    for e in entites:
        u = e.get("face")
        if u and u not in urls:
            urls.append(u)
    if len(urls) < lo:
        raise ValueError(f"{m['label']} demande au moins {lo} style frame(s) ({len(urls)} fournie(s)).")
    if len(urls) > hi:
        notes.append(f"{len(urls)} style frames -> {hi} (plafond {m['label']})")
        urls = urls[:hi]
    t = tache or m["taches"][0]
    if t not in m["taches"]:
        raise ValueError(f"tâche « {t} » refusée ({', '.join(m['taches'])}).")
    args: dict = {"prompt": prompt, "task": t, m["champ_video"]: [video_url], m["champ"]: urls}
    if t == "reference":
        args["duration"] = _duree(m, int(duree), notes)
    if resolution in m["resolutions"]:
        args["resolution"] = resolution
    else:
        notes.append(f"résolution {resolution} -> {m['resolutions'][-1]} ({m['label']})")
        args["resolution"] = m["resolutions"][-1]
    args[m["audio_param"]] = bool(audio)
    absents = (["@Video1"] if "@Video1" not in prompt else []) + [
        f"@Image{i}" for i in range(1, len(urls) + 1) if f"@Image{i}" not in prompt]
    if absents:
        notes.append("le prompt ne nomme pas " + ", ".join(absents) + " : Seedance ne saura pas quel rôle leur donner")
    return m["endpoint"], args, notes


def construire(model_id: str, prompt: str, entites: list[dict], *, start_image_url: str | None = None,
               duree: int = 8, aspect_ratio: str = "9:16", resolution: str | None = "1080p",
               audio: bool = False, video_url: str | None = None,
               tache: str | None = None) -> tuple[str, dict, list[str]]:
    """(endpoint, arguments, notes) — fonction PURE. `entites` : [{"nom", "face": url, "vues": [url, …]}] dans
    l'ordre du plan. Veo reçoit une liste plate (la face de chacune d'abord, entrelacée) ; Kling un élément par
    entité (face + 1 à 3 vues), nommé @ElementN dans le prompt. t335 — Seedance v2v : `video_url` (le clip de
    previs) + une entrée par style frame (sa `face`), `tache` editing | reference."""
    m = REGISTRE_REFS.get(model_id)
    if not m:
        raise ValueError(f"« {model_id} » n'est pas au registre des références.")
    if m["grammaire"] == "video":
        return _construire_video(m, prompt, entites, video_url, tache, duree, resolution, audio)
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
