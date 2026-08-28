"""Contrôle qualité d'un maillage — spec Magnific §9.2 étapes 3 et 7.

  étape 3 : « Inspecter silhouette, proportions, revers et zones invisibles. »
  étape 7 : « Comparer l'image rendue à la référence maître. »

Choix de méthode, et pourquoi il diffère de `proportion_qc` :
`proportion_qc` interroge un LLM de vision parce que « combien de têtes fait
ce personnage » n'a pas de formule. Ici, la question EST calculable — la
silhouette du maillage se projette (mesh_report), celle de la référence
s'extrait du fond propre que les prompts de vues imposent — donc le score
principal est **local, gratuit et déterministe** : une IoU. La passe vision
reste disponible en appoint pour ce qu'un masque ne voit pas (l'identité),
sur le même patron best-effort : sans clé, elle rend None, jamais d'exception.

Comparaison invariante en position et en échelle : les deux masques sont
recadrés sur leur boîte englobante puis ajustés dans le même carré. On
compare une FORME, pas un cadrage.
"""
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from app.config import settings

# Seuils de départ, à CALIBRER sur les premiers assets réels (la spec §5.2
# les veut configurables ; ces valeurs sont un point de départ, pas une
# vérité mesurée). Surchargeables par le corps de la requête.
SEUILS = {
    "silhouette": 70,     # IoU × 100 entre la face du maillage et la référence
    "proportions": 85,    # accord des rapports largeur/hauteur
    "fermeture": 60,      # part des arêtes qui ne sont PAS des bords
}

MARGE = 0.04              # identique à mesh_report.silhouettes — sinon l'IoU ment
PX = 512


# ── masques ──────────────────────────────────────────────────────────────────

def _bbox_masque(img):
    """Boîte englobante des pixels allumés, ou None si le masque est vide."""
    return img.getbbox()


def _ajuster(img, px: int = PX, marge: float = MARGE):
    """Recadre sur la boîte englobante puis ajuste dans un carré de `px`,
    échelle UNIFORME et centrage — exactement le cadrage de
    `mesh_report.silhouettes`, sans quoi l'IoU comparerait deux cadrages."""
    from PIL import Image
    bb = _bbox_masque(img)
    if bb is None:
        return Image.new("L", (px, px), 0)
    crop = img.crop(bb)
    utile = px * (1 - 2 * marge)
    ech = utile / max(crop.width, crop.height)
    w, h = max(1, round(crop.width * ech)), max(1, round(crop.height * ech))
    crop = crop.resize((w, h), Image.NEAREST)
    fond = Image.new("L", (px, px), 0)
    fond.paste(crop, ((px - w) // 2, (px - h) // 2))
    return fond


def masque_reference(path: Path, px: int = PX, seuil_fond: int = 32):
    """Masque binaire du sujet d'une image de référence.

    Deux voies, dans l'ordre : (1) le canal alpha s'il porte de la
    transparence réelle ; (2) sinon, distance à la couleur de fond estimée
    sur les quatre coins — ce qui marche précisément parce que les prompts
    de vues imposent « plain flat neutral background, no cast shadow ».
    Une image sans fond propre donnera un masque bruité : c'est dit dans le
    résultat (`methode`), pas caché.
    """
    from PIL import Image
    im = Image.open(path)
    im.load()

    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        a = im.convert("RGBA").getchannel("A")
        mini, maxi = a.getextrema()
        if mini < 200:                       # alpha réellement utilisé
            return a.point(lambda v: 255 if v > 127 else 0), "alpha"

    rgb = im.convert("RGB")
    # la boucle par pixel est en Python pur : on réduit d'abord au format de
    # comparaison (le masque est de toute façon réajusté à `px` ensuite), ce
    # qui divise le travail par ~4 sur une planche 1024² sans changer l'IoU
    if max(rgb.size) > px:
        rgb.thumbnail((px, px), Image.LANCZOS)
    w, h = rgb.size
    coins = [rgb.getpixel(p) for p in
             ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    fond = tuple(sum(c[i] for c in coins) // 4 for i in range(3))

    gris = Image.new("L", (w, h))
    src = rgb.load()
    dst = gris.load()
    for y in range(h):
        for x in range(w):
            p = src[x, y]
            d = abs(p[0] - fond[0]) + abs(p[1] - fond[1]) + abs(p[2] - fond[2])
            dst[x, y] = 255 if d > seuil_fond * 3 else 0
    return gris, f"fond {fond}"


def iou(a, b) -> float:
    """Intersection sur union de deux masques de MÊME taille."""
    if a.size != b.size:
        raise ValueError("masques de tailles différentes")
    da, db = a.getdata(), b.getdata()
    inter = union = 0
    for va, vb in zip(da, db):
        pa, pb = va > 127, vb > 127
        if pa or pb:
            union += 1
            if pa and pb:
                inter += 1
    return (inter / union) if union else 0.0


# ── compatibilité runtime (§13 phase D : « tester le GLB dans le runtime ») ──
#
# Verdict FACTUEL, tiré du document glTF, jamais d'une supposition : ce qui
# est déclaré dans `extensionsRequired` doit être décodé par le lecteur, et
# un buffer externe casse la distribution en fichier unique.

_DECODEURS = {
    "KHR_draco_mesh_compression": {
        "three": "DRACOLoader à câbler", "blender": "natif",
        "unity": "selon l'importateur glTF", "unreal": "non garanti",
    },
    "EXT_meshopt_compression": {
        "three": "MeshoptDecoder à câbler", "blender": "non natif",
        "unity": "selon l'importateur glTF", "unreal": "non garanti",
    },
    "KHR_texture_basisu": {
        "three": "KTX2Loader à câbler", "blender": "non natif",
        "unity": "selon l'importateur glTF", "unreal": "non garanti",
    },
}
RUNTIMES = ("three", "blender", "unity", "unreal")


def compat_runtime(fiche: dict) -> dict:
    """Ce que le GLB exige de chaque cible, d'après sa propre déclaration.

    On rend des EXIGENCES, pas des promesses : « natif » veut dire que le
    format de base suffit, pas que l'asset sera beau.
    """
    g = fiche.get("gltf") or {}
    if g.get("erreur"):
        return {"lisible": False, "raison": g["erreur"], "cibles": {}}

    requises = list(g.get("extensions_required") or [])
    externes = [i for i in (g.get("images") or []) if i.get("externe")]
    cibles = {r: [] for r in RUNTIMES}

    for ext in requises:
        table = _DECODEURS.get(ext)
        for r in RUNTIMES:
            cibles[r].append(f"{ext} : " + (table[r] if table else "extension "
                                            "inconnue de ce registre — vérifier"))
    if externes:
        for r in RUNTIMES:
            cibles[r].append(f"{len(externes)} image(s) en URI externe — "
                             "le .glb n'est pas autonome")
    if g.get("animations"):
        cibles["unreal"].append(
            f"{g['animations']} animation(s) : import glTF animé à vérifier")
    if not (g.get("textures") or 0) and (fiche.get("geometry") or {}).get("materials"):
        for r in RUNTIMES:
            cibles[r].append("matériaux sans texture — maillage nu (brouillon ?)")

    return {
        "lisible": True,
        "gltf_version": g.get("gltf_version"),
        "autonome": not externes,
        "extensions_required": requises,
        "cibles": {r: (v or ["rien à câbler — glTF 2.0 de base"])
                   for r, v in cibles.items()},
    }


# ── le contrôle complet ──────────────────────────────────────────────────────

def _fiche_du_job(job: str, version: int | None):
    from app.services import mesh_report
    reg = mesh_report.read_registry(job)
    entries = reg.get("entries") or []
    if not entries:
        raise FileNotFoundError("registre vide")
    if version is None:
        version = reg.get("current_version") or entries[-1].get("version")
    for e in entries:
        if int(e.get("version") or 0) == int(version):
            return e, reg
    raise FileNotFoundError(f"version {version} absente du registre")


def controler(job: str, *, ref_image: str | None = None,
              version: int | None = None, seuils: dict | None = None) -> dict:
    """Scores 0-100 du maillage contre sa référence maître.

    `ref_image` : nom d'un fichier de la Library ; par défaut la vue source
    du job (`shot_0.png`), qui EST la référence maître de ce maillage.
    """
    from app.services import mesh_report
    s = {**SEUILS, **(seuils or {})}
    d = mesh_report.job_dir(job)
    fiche, _reg = _fiche_du_job(job, version)
    v = int(fiche.get("version") or 1)

    scores: dict = {}
    detail: dict = {"version": v, "file": fiche.get("file")}

    # 1. fermeture / revers (étape 3) — purement local, déjà calculé
    topo = ((fiche.get("geometry") or {}).get("topologie") or {})
    if topo.get("calcule"):
        scores["fermeture"] = round(100.0 - float(topo.get("bord_pct") or 0.0), 1)
        detail["topologie"] = {
            "aretes_de_bord": topo.get("aretes_de_bord"),
            "aretes_non_manifold": topo.get("aretes_non_manifold"),
            "triangles_degeneres": topo.get("triangles_degeneres"),
            "ferme": topo.get("ferme"),
        }
    else:
        detail["topologie"] = {"calcule": False,
                               "raison": topo.get("raison") or "non calculée"}

    # 2. silhouette + proportions (étape 7) — IoU contre la référence maître
    sil = fiche.get("silhouettes") or {}
    vue = (sil.get("face") or {}).get("file") if isinstance(sil, dict) else None
    sil_path = d / (fiche.get("silhouettes_dir") or f"sil_v{v}") / (vue or "")
    ref_name = Path(ref_image).name if ref_image else "shot_0.png"
    ref_path = (settings.images_path / ref_name) if ref_image else (d / ref_name)

    if not vue or not sil_path.is_file():
        detail["silhouette"] = {"compare": False,
                                "raison": (sil.get("erreur")
                                           if isinstance(sil, dict) else None)
                                or "silhouette absente de la fiche"}
    elif not ref_path.is_file():
        detail["silhouette"] = {"compare": False,
                                "raison": f"référence introuvable : {ref_name}"}
    else:
        from PIL import Image
        m_mesh = _ajuster(Image.open(sil_path).convert("L"))
        brut, methode = masque_reference(ref_path)
        m_ref = _ajuster(brut)
        score = iou(m_mesh, m_ref)
        scores["silhouette"] = round(score * 100, 1)

        bb_m, bb_r = _bbox_masque(m_mesh), _bbox_masque(m_ref)
        ar_m = ((bb_m[2] - bb_m[0]) / max(1, bb_m[3] - bb_m[1])) if bb_m else 0
        ar_r = ((bb_r[2] - bb_r[0]) / max(1, bb_r[3] - bb_r[1])) if bb_r else 0
        if ar_r:
            ecart = min(1.0, abs(ar_m - ar_r) / ar_r)
            scores["proportions"] = round(100.0 * (1 - ecart), 1)
        detail["silhouette"] = {
            "compare": True, "reference": ref_name, "methode_masque": methode,
            "iou": round(score, 4),
            "ratio_largeur_hauteur": {"maillage": round(ar_m, 4),
                                      "reference": round(ar_r, 4)},
            "vue": "face",
        }

    # 3. verdict — au-dessus des seuils sur TOUT ce qui a pu être mesuré
    manquants = [k for k in s if k not in scores]
    echecs = {k: {"score": scores[k], "seuil": s[k]}
              for k in scores if scores[k] < s[k]}
    return {
        "job": job, "version": v,
        "scores": scores, "seuils": s,
        "non_mesure": manquants,
        "echecs": echecs,
        "verdict": ("approuvable" if not echecs and not manquants
                    else "a_revoir" if echecs else "partiel"),
        "compat": compat_runtime(fiche),
        "detail": detail,
    }


def comparer(job_a: str, job_b: str, *, version_a: int | None = None,
             version_b: int | None = None) -> dict:
    """Compare deux maillages — la brique de « image unique vs quatre vues »
    (§13 phase D). Rend les écarts mesurés, pas un gagnant : c'est l'humain
    qui tranche, avec les chiffres sous les yeux.
    """
    from PIL import Image
    from app.services import mesh_report
    from app.services import asset3d_service as A3

    out = {}
    fiches = {}
    for cle, (j, v) in (("a", (job_a, version_a)), ("b", (job_b, version_b))):
        f, _ = _fiche_du_job(j, v)
        fiches[cle] = f
        g = f.get("geometry") or {}
        t = g.get("topologie") or {}
        man = {}
        try:
            man = A3.read_manifest(j)
        except Exception:
            pass                          # job antérieur au manifeste
        # `asset.json` est ÉCRASÉ à chaque raffinement : s'y fier étiquetterait
        # la v1 avec le moteur et la texture de la v2. La fiche de CETTE
        # version porte sa propre provenance (`source`, posée à l'écriture) —
        # elle fait foi ; le manifeste ne sert que de repli pour les jobs
        # antérieurs à ce champ.
        prov = f.get("source") or {}
        out[cle] = {
            "job": j, "version": f.get("version"), "file": f.get("file"),
            "engine": prov.get("engine") or man.get("engine"),
            "texture_mode": prov.get("texture_mode") or man.get("texture_mode"),
            "provenance": "fiche" if prov else ("manifeste" if man else "inconnue"),
            "vues": (len(prov["shots"]) - 1 if prov.get("shots")
                     else (man.get("views") if man.get("views") is not None
                           else (len(man.get("shots") or []) - 1
                                 if man.get("shots") else None))),
            "tris": g.get("tris"), "verts": g.get("verts"),
            "bytes": f.get("bytes"), "sha256": (f.get("sha256") or "")[:12],
            "textures": (f.get("gltf") or {}).get("textures"),
            "texture_bytes": (f.get("gltf") or {}).get("texture_bytes"),
            "aretes_de_bord": t.get("aretes_de_bord"),
            "ferme": t.get("ferme"),
            "dims_normalisees": g.get("dims_normalisees"),
        }

    # IoU des silhouettes entre les deux maillages : mesure directe de
    # « les quatre vues ont-elles changé la forme ? »
    sils = {}
    for cle, (j, f) in (("a", (job_a, fiches["a"])), ("b", (job_b, fiches["b"]))):
        v = int(f.get("version") or 1)
        nom = ((f.get("silhouettes") or {}).get("face") or {}).get("file")
        p = mesh_report.job_dir(j) / (f.get("silhouettes_dir") or f"sil_v{v}") / (nom or "")
        sils[cle] = p if nom and p.is_file() else None

    if sils["a"] and sils["b"]:
        ma = _ajuster(Image.open(sils["a"]).convert("L"))
        mb = _ajuster(Image.open(sils["b"]).convert("L"))
        out["silhouette_iou"] = round(iou(ma, mb), 4)
    else:
        out["silhouette_iou"] = None
        out["silhouette_note"] = "au moins une silhouette manque — non comparé"

    a, b = out["a"], out["b"]
    out["deltas"] = {
        "tris": (b["tris"] - a["tris"]) if a["tris"] and b["tris"] else None,
        "bytes": (b["bytes"] - a["bytes"]) if a["bytes"] and b["bytes"] else None,
        "aretes_de_bord": ((b["aretes_de_bord"] - a["aretes_de_bord"])
                           if a["aretes_de_bord"] is not None
                           and b["aretes_de_bord"] is not None else None),
    }
    return out


# ── passe vision optionnelle (identité) — patron proportion_qc ───────────────

_VISION_PROMPT = (
    "You compare a 3D asset render against its master reference image. "
    "Ignore differences of lighting, background and image style: judge only "
    "whether it is the SAME object/character — silhouette, proportions, "
    "distinctive shapes, costume or part layout. Return ONLY JSON: "
    "{\"identity\": <0-100>, \"missing\": [\"...\"], \"added\": [\"...\"], "
    "\"note\": \"<one short sentence>\"}")


def identite(render_path: Path, ref_path: Path) -> dict | None:
    """Score d'identité par LLM de vision. Best-effort strict, comme
    `proportion_qc.measure` : sans clé ou sur erreur, rend None et
    l'appelant continue. Appel SYNCHRONE bloquant — passer par to_thread.
    """
    from app.services.proportion_qc import _img_payload
    import httpx
    from app.config import SSL_VERIFY

    try:
        b64a, mediaa = _img_payload(Path(render_path))
        b64b, mediab = _img_payload(Path(ref_path))
    except Exception as e:
        logger.warning(f"asset3d_qc identite lecture : {e}")
        return None

    cle = (settings.ANTHROPIC_API_KEY or "").strip()
    out = None
    if cle:
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": cle, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                # MÊME modèle que proportion_qc (settings.ANTHROPIC_MODEL) :
                # un identifiant codé en dur ici se périmerait en silence et
                # la passe vision mourrait sans que personne le voie.
                json={"model": settings.ANTHROPIC_MODEL, "max_tokens": 300,
                      "messages": [{"role": "user", "content": [
                          {"type": "text", "text": "RENDER:"},
                          {"type": "image", "source": {
                              "type": "base64", "media_type": mediaa, "data": b64a}},
                          {"type": "text", "text": "MASTER REFERENCE:"},
                          {"type": "image", "source": {
                              "type": "base64", "media_type": mediab, "data": b64b}},
                          {"type": "text", "text": _VISION_PROMPT}]}]},
                timeout=60, verify=SSL_VERIFY)
            if r.status_code == 200:
                out = "".join(b.get("text", "")
                              for b in (r.json().get("content") or []))
        except Exception as e:
            logger.warning(f"asset3d_qc identite anthropic : {e}")

    if not out:
        return None
    txt = out.strip()
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(txt[i:j + 1])
    except Exception:
        return None
    try:
        d["identity"] = max(0, min(100, int(round(float(d.get("identity"))))))
    except (TypeError, ValueError):
        return None
    return d
