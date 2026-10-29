# -*- coding: utf-8 -*-
"""Décor en calques de parallaxe (t341, lot Scenario B5, 29/10/2026) — une peinture LARGE découpée en 4 ou 5 calques
transparents (ciel, lointain, milieu, proche, premier plan), un facteur de parallaxe par calque, et l'export Godot 4
`ParallaxBackground` (.tscn + PNG) ou les PNG seuls, en ZIP.

DEUX VOIES :
1. LOCALE et gratuite (`decouper_local`), Pillow seul (pas de numpy dans le runtime). Une « proximité » par pixel :
   la HAUTEUR dans l'image (le bas est près, le haut est loin) mêlée à la PERSPECTIVE AÉRIENNE (le lointain est plus
   clair et moins saturé), lissée, puis coupée en bandes de même aire. Le calque k garde sa bande ; sous les bandes
   plus proches, il est REMPLI d'une couleur étalée depuis sa bande (moyenne pondérée à deux échelles), pour qu'aucun
   trou ne s'ouvre quand le premier plan défile plus vite. Le ciel est opaque.
   CE QU'ELLE VAUT, honnêtement : bien pour un décor de défilement horizontal dont la profondeur suit la hauteur
   (ciel en haut, collines, sol en bas) et la brume. Elle ne sépare PAS un arbre du premier plan d'une montagne de
   même ton à la même hauteur, et ses bords suivent la luminance, pas les objets : pour ça, la voie IA.
2. IA, payante (`decomposer_par_ia`, puits du recensement des plafonds), sur fal — pages relues le 29/10/2026 :
   - `fal-ai/qwen-image-layered` : `image_url`, `num_layers` (1 à 10) → `images` (PNG RGBA). Le nombre de calques est
     celui demandé ; l'ordre rendu est pris du fond vers l'avant (réordonnable à l'écran). 0,05 $ « par image ».
   - `bytedance/seedream/v5/pro/layerize` : `image_url` (512² à 6000² px, rapport ≤ 16, 30 Mo) → `layers` : l'image de
     base PUIS 2 à 16 calques séparés, z croissant. Le nombre n'est pas réglable : les calques rendus sont regroupés,
     dans l'ordre, en n paquets contigus. 0,03375 $ ou 0,0675 $ par calque généré selon l'aire.
   Le prix vient de `pricing` (clés `qwen_layered_usd_image`, `seedream_layerize_usd_calque[_2k]`), modifiable.

Rangement : `outputs/parallaxe/<pid>/` (source.png, calques/<k>_<id>.png, meta.json), pid `plx_[0-9a-f]{8}`. Chaque
calque est aussi copié dans la Bibliothèque (`tile_plx_…_<k>_<id>.png`, source « tuiles », parent = la peinture,
relation « parallaxe ») par la route.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageChops, ImageFilter

PID_RE = re.compile(r"^plx_[0-9a-f]{8}$")
#: ids stables des calques, du FOND vers l'AVANT (les libellés affichés viennent du dictionnaire de l'écran)
NOMS_5 = ("ciel", "lointain", "milieu", "proche", "premier_plan")
NOMS = {4: ("ciel", "lointain", "milieu", "premier_plan"), 5: NOMS_5}
#: motion_scale de Godot : 0 = immobile (l'infini), 1 = avance avec la caméra ; > 1 = devant le jeu
FACTEURS = {4: (0.1, 0.3, 0.6, 1.2), 5: (0.1, 0.25, 0.5, 0.8, 1.2)}
FACTEUR_MIN, FACTEUR_MAX = -1.0, 3.0
N_MIN, N_MAX = 4, 5
COTE_MAX = 8192                   # côté le plus long accepté (une peinture 3072 × 1024 tient largement)
COTE_MIN = 64
NOM_MAX = 40

MODELES = {
    "local": {"voie": "local", "libelle": "Découpe locale (bandes de profondeur)", "endpoint": None},
    "qwen-layered": {"voie": "fal", "libelle": "Qwen-Image-Layered", "endpoint": "fal-ai/qwen-image-layered"},
    "seedream-layerize": {"voie": "fal", "libelle": "Seedream 5 Pro Layerize",
                          "endpoint": "bytedance/seedream/v5/pro/layerize"},
}
SEEDREAM_PX_MIN, SEEDREAM_PX_MAX, SEEDREAM_RAPPORT = 512 * 512, 6000 * 6000, 16


# ── le registre et le devis ───────────────────────────────────────────────

def noms_pour(m: int) -> list[str]:
    """Les ids de m calques, du fond vers l'avant : la table pour 4 et 5, sinon répartis sur les cinq."""
    if m in NOMS:
        return list(NOMS[m])
    if m <= 1:
        return ["ciel"][:max(m, 0)]
    pris = [NOMS_5[round(i * 4 / (m - 1))] for i in range(m)]
    vus: dict[str, int] = {}
    out = []
    for p in pris:                       # m > 5 : des doublons, numérotés
        vus[p] = vus.get(p, 0) + 1
        out.append(p if vus[p] == 1 else f"{p}_{vus[p]}")
    return out


def facteurs_pour(m: int) -> list[float]:
    if m in FACTEURS:
        return list(FACTEURS[m])
    if m <= 1:
        return [0.1][:max(m, 0)]
    return [round(0.1 + i * (1.2 - 0.1) / (m - 1), 2) for i in range(m)]


def lire_n(v) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"nombre de calques : entier attendu ({N_MIN} ou {N_MAX})")
    if not N_MIN <= n <= N_MAX:
        raise ValueError(f"nombre de calques : {N_MIN} ou {N_MAX}")
    return n


def devis(modele: str, n: int, w: int, h: int) -> dict:
    """Le devis AVANT le clic (aucune dépense) : les lignes de `pricing.estimate`."""
    from app.services import pricing
    if modele not in MODELES:
        raise ValueError(f"modèle inconnu : {modele}")
    e = pricing.estimate({"kind": "parallaxe_calques", "modele": modele, "n": n, "w": w, "h": h})
    m = MODELES[modele]
    return {"modele": modele, "voie": m["voie"], "endpoint": m["endpoint"], "usd": round(float(e["total_usd"]), 4),
            "lignes": e["breakdown"], "estimation": m["voie"] != "local", "n": n}


def verifier_taille(modele: str, w: int, h: int) -> None:
    """Les bornes du modèle, AVANT la dépense."""
    if max(w, h) > COTE_MAX or min(w, h) < COTE_MIN:
        raise ValueError(f"image de {w} × {h} px : de {COTE_MIN} à {COTE_MAX} px de côté")
    if modele == "seedream-layerize":
        if not SEEDREAM_PX_MIN <= w * h <= SEEDREAM_PX_MAX or max(w, h) > SEEDREAM_RAPPORT * min(w, h):
            raise ValueError("Seedream Layerize : de 512 × 512 à 6000 × 6000 px, rapport 16 au plus")


# ── la voie locale (Pillow seul) ──────────────────────────────────────────

def _proximite(img: Image.Image) -> Image.Image:
    """L'image « proximité » (L, 0 = loin, 255 = près) : perspective aérienne 65 % (sombre et saturé = près), hauteur
    35 % (le bas est près : elle départage deux tons égaux), légèrement lissée pour que le grain ne morcelle pas."""
    w, h = img.size
    hauteur = Image.linear_gradient("L").resize((w, h), Image.BILINEAR)   # 0 en haut, 255 en bas
    _h, s, v = img.convert("RGB").convert("HSV").split()
    aerienne = Image.blend(ImageChops.invert(v), s, 0.5)
    p = Image.blend(hauteur, aerienne, 0.65)
    return p.filter(ImageFilter.GaussianBlur(max(1.5, h / 160)))


def _seuils(p: Image.Image, n: int) -> list[int]:
    """n − 1 seuils aux COUPURES NATURELLES de la proximité (Otsu à plusieurs niveaux : la variance dans chaque bande
    est minimale, par programmation dynamique sur les 256 niveaux) — une bande suit une masse de ton, pas une aire
    fixe. Une bande garde au moins 2 % de l'image quand c'est possible. Croissants, jamais inversés."""
    hist = p.histogram()
    total = sum(hist) or 1
    c0, c1, c2 = [0.0] * 257, [0.0] * 257, [0.0] * 257      # cumuls : effectif, somme, somme des carrés
    for i, x in enumerate(hist):
        c0[i + 1], c1[i + 1], c2[i + 1] = c0[i] + x, c1[i] + x * i, c2[i] + x * i * i
    mini = total * 0.02

    def cout(a, b):                                         # variance × effectif des niveaux [a, b)
        w = c0[b] - c0[a]
        if w <= 0:
            return 0.0
        m = c1[b] - c1[a]
        return (c2[b] - c2[a]) - m * m / w + (0.0 if w >= mini else total * 1e4)
    inf = float("inf")
    D = [[inf] * 257 for _ in range(n + 1)]
    A = [[0] * 257 for _ in range(n + 1)]
    D[0][0] = 0.0
    for k in range(1, n + 1):
        for b in range(k, 257):
            meilleur, arg = inf, k - 1
            for a in range(k - 1, b):
                if D[k - 1][a] < inf:
                    v = D[k - 1][a] + cout(a, b)
                    if v < meilleur:
                        meilleur, arg = v, a
            D[k][b], A[k][b] = meilleur, arg
    seuils, b = [], 256
    for k in range(n, 1, -1):
        b = A[k][b]
        seuils.append(b)
    seuils = sorted(min(255, max(1, s)) for s in seuils)
    for i in range(1, len(seuils)):                          # une image uniforme : des bandes vides, jamais inversées
        seuils[i] = max(seuils[i], seuils[i - 1])
    return seuils


def _masque_sup(p: Image.Image, seuil: int) -> Image.Image:
    return p.point(lambda x, s=seuil: 255 if x >= s else 0)


def _etaler(rgb: Image.Image, masque: Image.Image) -> Image.Image:
    """Remplit tout le cadre en PROLONGEANT les pixels du masque colonne par colonne : sous la bande, la dernière
    couleur vue au-dessus descend (le sol continue sous ce qui le cache) ; au-dessus de la première, la première
    remonte ; une colonne vide prend sa voisine. Calculé au quart, adouci en largeur, puis agrandi."""
    w, h = rgb.size
    pw, ph = max(1, w // 4), max(1, h // 4)
    r = rgb.convert("RGB").resize((pw, ph), Image.BILINEAR).tobytes()
    m0 = masque.convert("L").resize((pw, ph), Image.BILINEAR)
    # le masque RONGÉ : la couleur prolongée vient du cœur de la bande, pas de son bord mêlé à la bande voisine
    # (sinon des traînées verticales) ; une bande trop fine pour être rongée garde son masque
    mr = m0.filter(ImageFilter.MinFilter(5))
    m = (mr if mr.getbbox() else m0).tobytes()
    out = bytearray(pw * ph * 3)
    colonnes = [None] * pw
    for x in range(pw):
        der, premiere = None, None
        trous = []
        for y in range(ph):
            i = y * pw + x
            if m[i] >= 128:
                der = r[3 * i:3 * i + 3]
                if premiere is None:
                    premiere = der
                    for j in trous:                          # au-dessus de la première : la première remonte
                        out[3 * j:3 * j + 3] = der
                    trous = []
                out[3 * i:3 * i + 3] = der
            elif der is not None:
                out[3 * i:3 * i + 3] = der
            else:
                trous.append(i)
        colonnes[x] = premiere is not None
        if premiere is None:
            colonnes[x] = False
    pleines = [x for x in range(pw) if colonnes[x]]
    if pleines:
        for x in range(pw):                                  # une colonne sans pixel du masque : la plus proche
            if not colonnes[x]:
                v = min(pleines, key=lambda c: abs(c - x))
                for y in range(ph):
                    i, j = y * pw + x, y * pw + v
                    out[3 * i:3 * i + 3] = out[3 * j:3 * j + 3]
    im = Image.frombytes("RGB", (pw, ph), bytes(out))
    im = im.filter(ImageFilter.BoxBlur(1)).resize((w, h), Image.BILINEAR)
    return im


def decouper_local(img: Image.Image, n: int) -> list[Image.Image]:
    """n calques RGBA de la taille de la source, du fond vers l'avant. Le calque 0 (ciel) est opaque."""
    n = lire_n(n)
    src = img.convert("RGB")
    p = _proximite(src)
    seuils = _seuils(p, n)
    sup = [Image.new("L", src.size, 255)] + [_masque_sup(p, s) for s in seuils]   # sup[k] : bandes k et plus proches
    calques = []
    for k in range(n):
        propre = ImageChops.subtract(sup[k], sup[k + 1]) if k + 1 < n else sup[k]
        douce = propre.filter(ImageFilter.GaussianBlur(1.5))
        if propre.getbbox() is None:                       # bande vide (image uniforme) : un calque transparent
            calques.append(Image.new("RGBA", src.size, (0, 0, 0, 0)))
            continue
        fond = _etaler(src, propre) if k + 1 < n else src
        rgb = Image.composite(src, fond, douce)
        alpha = Image.new("L", src.size, 255) if k == 0 else sup[k].filter(ImageFilter.GaussianBlur(1.5))
        c = rgb.convert("RGBA")
        c.putalpha(alpha)
        calques.append(c)
    return calques


def fondu_bords(img: Image.Image, part: float = 0.08) -> Image.Image:
    """Rend un calque BOUCLABLE à l'horizontale (motion_mirroring) par fondu enchaîné : la bande de droite (largeur b)
    est retirée et fondue DANS la bande de gauche — la colonne 0 devient la suite exacte de la dernière colonne.
    Le calque perd b colonnes ; alpha compris."""
    img = img.convert("RGBA")
    w, h = img.size
    b = max(1, int(w * part))
    if b * 2 >= w:
        return img
    gauche = img.crop((0, 0, b, h))
    droite = img.crop((w - b, 0, w, h))
    rampe = Image.linear_gradient("L").rotate(90, expand=True).resize((b, h))   # 0 à gauche → 255 à droite
    out = img.crop((0, 0, w - b, h))
    out.paste(Image.composite(gauche, droite, rampe), (0, 0))
    return out


def boucher_fond(img: Image.Image) -> Image.Image:
    """Le calque du fond rendu OPAQUE : ses trous (alpha < 255) reçoivent la couleur étalée de ses pixels pleins."""
    img = img.convert("RGBA")
    a = img.getchannel("A")
    if a.getextrema()[0] == 255:
        return img
    plein = a.point(lambda x: 255 if x >= 250 else 0)
    if plein.getbbox() is None:
        return img
    fond = _etaler(img.convert("RGB"), plein)
    out = Image.composite(img.convert("RGB"), fond, a).convert("RGBA")
    out.putalpha(255)
    return out


# ── la voie IA : rendu du modèle → n calques ──────────────────────────────

def regrouper(calques: list[Image.Image], n: int, taille: tuple[int, int]) -> list[Image.Image]:
    """Les calques rendus (fond → avant) ramenés à n au plus : paquets CONTIGUS fusionnés (alpha_composite), chacun
    à la taille de la source. Moins de n rendus : on garde ce qu'il y a."""
    cs = [c.convert("RGBA").resize(taille, Image.LANCZOS) if c.size != taille else c.convert("RGBA") for c in calques]
    if len(cs) <= n:
        return cs
    out = []
    for g in range(n):
        a, z = round(g * len(cs) / n), round((g + 1) * len(cs) / n)
        base = Image.new("RGBA", taille, (0, 0, 0, 0))
        for c in cs[a:z]:
            base = Image.alpha_composite(base, c)
        out.append(base)
    return out


def lire_reponse(modele: str, res) -> list[str]:
    """Les URL des calques dans la réponse de fal, du fond vers l'avant (l'image de base de Seedream écartée)."""
    if not isinstance(res, dict):
        raise RuntimeError("réponse de fal illisible")
    if modele == "seedream-layerize":
        couches = res.get("layers") or []
        urls = [((c or {}).get("image") or {}).get("url") for c in couches[1:]]
    else:
        urls = [(c or {}).get("url") for c in (res.get("images") or [])]
    urls = [u for u in urls if u]
    if not urls:
        raise RuntimeError("le modèle n'a rendu aucun calque")
    return urls


async def decomposer_par_ia(src: Path, modele: str, n: int) -> list[Image.Image]:
    """Envoie la peinture à fal et rapatrie ses calques (n au plus, fond → avant). N'APPELER QU'APRÈS la garde des
    plafonds : c'est la route qui la pose, et le recensement AST (test_plafonds_garde) le vérifie."""
    import tempfile
    from app.services import asset3d_service as A3
    import fal_client
    m = MODELES[modele]
    url = await A3._upload(src)
    args = {"image_url": url}
    if modele == "qwen-layered":
        args.update({"num_layers": int(n), "output_format": "png"})
    try:
        res = await fal_client.subscribe_async(m["endpoint"], arguments=args, with_logs=False)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"fal.ai : {e}") from e
    with Image.open(src) as im:
        taille = im.size
    images = []
    with tempfile.TemporaryDirectory(prefix="dzplx_") as tmp:
        for i, u in enumerate(lire_reponse(modele, res)):
            d = Path(tmp) / f"c{i}.png"
            A3._download(u, d)
            with Image.open(d) as c:
                images.append(c.convert("RGBA"))
    cs = regrouper(images, n, taille)
    if cs:
        cs[0] = boucher_fond(cs[0])
    return cs


# ── le rangement ──────────────────────────────────────────────────────────

def racine() -> Path:
    from app.config import settings
    p = Path(settings.outputs_path) / "parallaxe"
    p.mkdir(parents=True, exist_ok=True)
    return p


def dossier(pid: str) -> Path:
    if not isinstance(pid, str) or not PID_RE.match(pid):
        raise ValueError(f"décor inconnu : {str(pid)[:40]}")
    d = (racine() / pid).resolve()
    if d.parent != racine().resolve():
        raise ValueError(f"décor inconnu : {str(pid)[:40]}")
    return d


def nouveau_pid() -> str:
    for _ in range(64):
        pid = "plx_" + uuid4().hex[:8]
        if not (racine() / pid).exists():
            return pid
    raise RuntimeError("impossible d'allouer un identifiant de décor")


def nom_sur(v, defaut: str = "") -> str:
    s = re.sub(r"[\x00-\x1f<>\"\\/|?*]", "", str(v or "")).strip()[:NOM_MAX]
    return s or defaut


def enregistrer(pid: str, source_nom: str, src: Image.Image, calques: list[Image.Image], *, modele: str,
                devis_usd: float, boucler: bool, nom: str = "") -> dict:
    """Écrit le décor (source, calques, meta) et rend sa méta."""
    from datetime import datetime, timezone
    d = dossier(pid)
    (d / "calques").mkdir(parents=True, exist_ok=True)
    src.convert("RGB").save(d / "source.png", format="PNG")
    ids, fs = noms_pour(len(calques)), facteurs_pour(len(calques))
    liste = []
    if boucler:
        calques = [fondu_bords(c) for c in calques]
    w, h = calques[0].size          # le fondu retire des colonnes : la largeur est celle des calques
    for k, (c, cid, f) in enumerate(zip(calques, ids, fs)):
        fichier = f"{k + 1}_{cid}.png"
        c.save(d / "calques" / fichier, format="PNG")
        liste.append({"id": cid, "nom": "", "fichier": fichier, "facteur": f, "devant": cid == "premier_plan",
                      "visible": True})
    meta = {"pid": pid, "nom": nom_sur(nom, Path(source_nom).stem[:NOM_MAX]), "source": Path(source_nom).name,
            "largeur": w, "hauteur": h, "modele": modele, "voie": MODELES[modele]["voie"],
            "devis_usd": devis_usd, "boucler": bool(boucler), "repeter": True, "calques": liste,
            "cree_le": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    ecrire_meta(pid, meta)
    return meta


def ecrire_meta(pid: str, meta: dict) -> None:
    (dossier(pid) / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def lire_meta(pid: str) -> dict:
    p = dossier(pid) / "meta.json"
    if not p.is_file():
        raise FileNotFoundError(f"décor introuvable : {pid}")
    return json.loads(p.read_text(encoding="utf-8"))


def lister() -> list[dict]:
    out = []
    for d in sorted(racine().iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if PID_RE.match(d.name) and (d / "meta.json").is_file():
            try:
                m = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            out.append({k: m.get(k) for k in ("pid", "nom", "source", "largeur", "hauteur", "modele", "cree_le")}
                       | {"n": len(m.get("calques") or [])})
    return out


def modifier(pid: str, corps: dict) -> dict:
    """Réordonne, renomme, règle les facteurs, « devant le jeu », la visibilité, la répétition et le nom du décor.
    `calques` : la liste COMPLÈTE dans le nouvel ordre (fond → avant), chaque entrée désignée par son `id`."""
    meta = lire_meta(pid)
    if "calques" in corps:
        neufs = corps.get("calques")
        if not isinstance(neufs, list):
            raise ValueError("calques : liste attendue")
        par_id = {c["id"]: c for c in meta["calques"]}
        ids = [str((c or {}).get("id")) for c in neufs if isinstance(c, dict)]
        if len(ids) != len(neufs) or sorted(ids) != sorted(par_id):
            raise ValueError("calques : chaque calque une fois, ni plus ni moins")
        liste = []
        for c in neufs:
            e = dict(par_id[str(c["id"])])
            if "facteur" in c:
                try:
                    f = float(c["facteur"])
                except (TypeError, ValueError):
                    raise ValueError("facteur : nombre attendu")
                if not FACTEUR_MIN <= f <= FACTEUR_MAX or f != f:
                    raise ValueError(f"facteur : de {FACTEUR_MIN:g} à {FACTEUR_MAX:g}")
                e["facteur"] = round(f, 3)
            if "nom" in c:
                e["nom"] = nom_sur(c["nom"])
            for b in ("devant", "visible"):
                if b in c:
                    e[b] = bool(c[b])
            liste.append(e)
        meta["calques"] = liste
    if "nom" in corps:
        meta["nom"] = nom_sur(corps["nom"], meta.get("nom") or pid)
    if "repeter" in corps:
        meta["repeter"] = bool(corps["repeter"])
    ecrire_meta(pid, meta)
    return meta


def chemin_calque(pid: str, cid: str) -> Path:
    meta = lire_meta(pid)
    for c in meta["calques"]:
        if c["id"] == cid:
            return dossier(pid) / "calques" / c["fichier"]
    raise FileNotFoundError(f"calque introuvable : {str(cid)[:40]}")


# ── l'export ──────────────────────────────────────────────────────────────

def _noeud(c: dict, vus: set) -> str:
    """Nom de nœud Godot : celui de l'utilisateur, sinon l'id en CamelCase ; sans . : @ / " % ; unique."""
    brut = c.get("nom") or "".join(x.capitalize() for x in c["id"].split("_"))
    base = re.sub(r'[.:@/"%\x00-\x1f]+', "_", brut).strip("_") or "Calque"
    nom, i = base, 2
    while nom in vus:
        nom, i = f"{base}{i}", i + 1
    vus.add(nom)
    return nom


def _flottant(v: float) -> str:
    s = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0" if s not in ("-0",) else "0.0"


def scene_tscn(meta: dict) -> str:
    """La scène Godot 4 (format=3) : un Node2D « Decor » et un ou deux `ParallaxBackground` — `Fond` (couche −100 par
    défaut, derrière le jeu) et `DevantLeJeu` (couche 1) pour les calques marqués « devant » : un ParallaxBackground est
    un CanvasLayer, il ne peut pas être à la fois derrière et devant. Un `ParallaxLayer` par calque visible, dans
    l'ordre fond → avant : motion_scale = (facteur, facteur), motion_mirroring = (largeur, 0) si « répéter », et un
    Sprite2D non centré. Les textures sont désignées par un chemin RELATIF (`calques/…png`) : le chargeur texte de
    Godot 4 le résout depuis le dossier de la scène, on dépose donc le dossier du ZIP tel quel dans le projet. Pas
    d'`uid://` : Godot en attribue un à l'import."""
    w = int(meta["largeur"])
    visibles = [c for c in meta["calques"] if c.get("visible", True)]
    L = [f"[gd_scene load_steps={len(visibles) + 1} format=3]", ""]
    ids = {}
    for i, c in enumerate(visibles, start=1):
        ids[c["id"]] = f"{i}_{c['id']}"
        L.append(f'[ext_resource type="Texture2D" path="calques/{c["fichier"]}" id="{ids[c["id"]]}"]')
    L += ["", '[node name="Decor" type="Node2D"]']
    vus: set = set()
    for groupe, couche, devant in (("Fond", None, False), ("DevantLeJeu", 1, True)):
        membres = [c for c in visibles if bool(c.get("devant")) == devant]
        if not membres:
            continue
        L += ["", f'[node name="{groupe}" type="ParallaxBackground" parent="."]']
        if couche is not None:
            L.append(f"layer = {couche}")
        vus.add(groupe)
        for c in membres:
            nom = _noeud(c, vus)
            f = _flottant(c["facteur"])
            L += ["", f'[node name="{nom}" type="ParallaxLayer" parent="{groupe}"]', f"motion_scale = Vector2({f}, {f})"]
            if meta.get("repeter", True):
                L.append(f"motion_mirroring = Vector2({w}, 0)")
            L += ["", f'[node name="Sprite2D" type="Sprite2D" parent="{groupe}/{nom}"]',
                  f'texture = ExtResource("{ids[c["id"]]}")', "centered = false"]
    L.append("")
    return "\n".join(L)


def _slug(meta: dict) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", meta.get("nom") or meta["pid"]).strip("_")
    return (s or meta["pid"])[:40]


def archive(pid: str, format: str) -> tuple[str, bytes]:
    """(nom du zip, octets). `godot` : <dossier>/parallaxe.tscn + <dossier>/calques/*.png ; `png` : les PNG seuls
    (tous, numérotés fond → avant), avec un calques.json des facteurs."""
    if format not in ("godot", "png"):
        raise ValueError("format : godot ou png")
    meta = lire_meta(pid)
    d = dossier(pid)
    slug = _slug(meta)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if format == "godot":
            z.writestr(f"{slug}/parallaxe.tscn", scene_tscn(meta))
            for c in meta["calques"]:
                if c.get("visible", True):
                    z.write(d / "calques" / c["fichier"], f"{slug}/calques/{c['fichier']}")
        else:
            for k, c in enumerate(meta["calques"], start=1):
                z.write(d / "calques" / c["fichier"], f"{slug}/{k}_{c['id']}.png")
            z.writestr(f"{slug}/calques.json", json.dumps(
                {"largeur": meta["largeur"], "hauteur": meta["hauteur"], "repeter": meta.get("repeter", True),
                 "calques": [{"ordre": k, "id": c["id"], "nom": c.get("nom") or c["id"], "fichier": f"{k}_{c['id']}.png",
                              "facteur": c["facteur"], "devant": bool(c.get("devant"))}
                             for k, c in enumerate(meta["calques"], start=1)]}, ensure_ascii=False, indent=1))
    return f"{slug}_{'godot' if format == 'godot' else 'png'}.zip", buf.getvalue()
