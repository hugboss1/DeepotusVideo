# -*- coding: utf-8 -*-
"""SVH (14/11/2026) — l'HABILLAGE du studio virtuel : le catalogue du « décorateur d'intérieur ».
Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md (lot SVH).

Le décorateur propose, pour un décor de l'espace :
- des MATIÈRES réelles (cartes couleur, normale, rugosité), de trois sources, toutes désignées par une RÉFÉRENCE
  que la recette garde (`studiov.REF_TEXTURE`) :
    `stu:<slug>`  le pack d'intérieur du studio (app/studiov/textures, Poly Haven CC0, scripts/studiov/composer_textures.py)
    `cat:<slug>`  le catalogue de démarrage de la Forge (app/assets/materials, Poly Haven CC0)
    `mat:<8hex>`  une matière de l'UTILISATEUR dans la Forge (Material Forge : générée, photographiée, importée —
                  dont celles CUITES DEPUIS BLENDER : `cuire_blender` lance app/studiov/cuire_matiere_blender.py sur
                  un fichier .blend, sans fenêtre, et range les cartes cuites dans la Forge)
- des FINITIONS sans image (laque, métal brossé, chrome, or…) ;
- des AMBIANCES LUMINEUSES (couleurs de la clé, de l'appoint, du contre, des néons et rubans) ;
- des STYLES complets (« sets ») : une matière par usage (sol, mur, plafond, bois, tissu, cuir, métal) + une ambiance.

Ce module ne fait que DÉCRIRE : c'est l'écran (dz-studiov-logique.js, `appliquerStyle` / `appliquerAmbiance`) qui
applique un style à la recette, et `studiov.normaliser` reste seul juge de ce qui s'enregistre.
Aucun réseau, aucune dépense. Blender n'est lancé que sur la demande de l'utilisateur (cuisson)."""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from app.services import studiov as S

TEXTURES = Path(__file__).resolve().parent.parent / "studiov" / "textures"
SCRIPT_CUISSON = TEXTURES.parent / "cuire_matiere_blender.py"
MAX_CUISSONS = 12                          # matières cuites par appel
DELAI_BLENDER = 900                        # secondes
SLUG = re.compile(r"^[a-z0-9_]{2,40}$")
CARTES = ("basecolor", "normal", "roughness")
_VERROU = threading.Lock()
_pack: dict | None = None
_vignettes: dict = {}                      # (source, id, mtime) -> octets JPEG
_moyennes: dict = {}                       # chemin -> #rrggbb (couleur moyenne d'une carte de couleur de la Forge)
MAX_VIGNETTES = 400


class RefusHabillage(ValueError):
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


# ── les matières ──

def pack() -> dict:
    """Le pack d'intérieur livré ; absent (dépôt sans build) = pack vide, jamais une exception."""
    global _pack
    with _VERROU:
        if _pack is None:
            try:
                d = json.loads((TEXTURES / "catalog.json").read_text("utf-8"))
                _pack = d if isinstance(d, dict) and isinstance(d.get("textures"), list) else {}
            except (OSError, ValueError):
                _pack = {}
        return _pack


def oublier() -> None:
    global _pack
    with _VERROU:
        _pack = None
        _vignettes.clear()


FAMILLES_TEXTURE = [
    {"id": "sols", "nom": "Sols", "nom_en": "Floors"},
    {"id": "murs", "nom": "Murs", "nom_en": "Walls"},
    {"id": "bois", "nom": "Bois et placages", "nom_en": "Wood and veneers"},
    {"id": "tissus", "nom": "Tissus et cuirs", "nom_en": "Fabrics and leathers"},
    {"id": "metaux", "nom": "Métaux", "nom_en": "Metals"},
    {"id": "beton", "nom": "Béton et terrains", "nom_en": "Concrete and ground"},
    {"id": "forge", "nom": "Mes matières (Forge)", "nom_en": "My materials (Forge)"},
]
# le catalogue de la Forge range par famille ; le décorateur propose par USAGE
_USAGES_FORGE = {"sols": ["sol"], "murs": ["mur"], "metaux": ["metal"], "bois": ["bois", "mur"], "tissus": ["tissu"],
                 "beton_terrain": ["sol", "mur"]}
_FAMILLE_FORGE = {"beton_terrain": "beton"}


def _moyenne(f: Path) -> str | None:
    """La couleur moyenne d'une carte de couleur : ce que le décor montre le temps que la texture arrive."""
    cle = str(f)
    if cle not in _moyennes:
        try:
            from PIL import Image
            with Image.open(f) as im:
                im.draft("RGB", (64, 64))
                r, g, b = im.convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))
            _moyennes[cle] = f"#{r:02x}{g:02x}{b:02x}"
        except Exception:                               # noqa: BLE001 — carte absente ou illisible : pas de moyenne
            _moyennes[cle] = None
    return _moyennes[cle]


def _du_pack() -> list:
    out = []
    for t in pack().get("textures", []):
        sid = t.get("id")
        if not (isinstance(sid, str) and SLUG.match(sid)):
            continue
        base = f"/api/studiov/textures/stu/{sid}"
        out.append({"ref": f"stu:{sid}", "nom": t.get("nom") or sid, "nom_en": t.get("nom_en") or t.get("nom") or sid,
                    "famille": t.get("famille") or "sols", "usages": list(t.get("usages") or []),
                    "taille_m": float(t.get("taille_m") or 1.0), "moyenne": t.get("moyenne") or "#808080",
                    "vignette": f"{base}/vignette.jpg", "source": "studio", "licence": "CC0",
                    "cartes": {c: f"{base}/{c}.jpg" for c in CARTES}})
    return out


def _de_la_forge() -> list:
    """Les trente matières du catalogue de démarrage de la Forge (lues, jamais recopiées)."""
    try:
        from app.services import starter_materials as SM
        items = SM.load().get("materials", [])
    except Exception:                                   # noqa: BLE001 — catalogue absent : rien à proposer
        return []
    out = []
    for m in items:
        sid = m.get("id")
        if not (isinstance(sid, str) and SLUG.match(sid)):
            continue
        fam = m.get("family") or ""
        usages = list(_USAGES_FORGE.get(fam, []))
        if "leather" in sid:
            usages = ["cuir"]
        dims = m.get("dimensions") or [1000, 1000]
        try:
            taille = max(0.05, float(dims[0]) / 1000.0)
        except (TypeError, ValueError, IndexError):
            taille = 1.0
        base = f"/api/materials/catalog/{sid}"
        out.append({"ref": f"cat:{sid}", "nom": m.get("name") or sid, "nom_en": m.get("polyhaven_name") or m.get("name") or sid,
                    "famille": _FAMILLE_FORGE.get(fam, fam or "sols"), "usages": usages, "taille_m": round(min(taille, 6.0), 3),
                    "moyenne": _moyenne(SM.STARTER_DIR / sid / "basecolor.jpg"),
                    "vignette": f"/api/studiov/textures/cat/{sid}/vignette.jpg", "source": "forge",
                    "licence": "CC0", "cartes": {c: f"{base}/{c}.jpg" for c in CARTES}})
    return out


def _de_l_utilisateur() -> list:
    """Les matières de l'utilisateur dans la Forge : la sienne, à son image (photo, IA, cuisson Blender)."""
    try:
        from app.services import material_store as MS
        items = MS.list_materials()
    except Exception:                                   # noqa: BLE001 — dossier absent ou illisible : rien à proposer
        return []
    out = []
    for m in items[:200]:
        mid = m.get("id") or ""
        if not MS.is_valid_mid(mid) or "basecolor" not in (m.get("maps") or []):
            continue
        court, base = mid[4:], f"/api/materials/{mid}/map"
        cartes = {c: f"{base}/{c}.png?res=1024" for c in CARTES if c in (m.get("maps") or [])}
        out.append({"ref": f"mat:{court}", "nom": S.K._texte(m.get("name"), mid, 60) or mid, "nom_en": S.K._texte(m.get("name"), mid, 60) or mid,
                    "famille": "forge", "usages": [], "taille_m": 1.0, "moyenne": None,
                    "vignette": f"/api/studiov/textures/mat/{court}/vignette.jpg", "source": "utilisateur",
                    "licence": "", "cartes": cartes})
    return out


def textures() -> list:
    return _du_pack() + _de_la_forge() + _de_l_utilisateur()


def refs_livrees() -> set:
    """Les références qu'un décor LIVRÉ ou un style peut employer : celles qui sont dans l'installeur."""
    return {t["ref"] for t in _du_pack() + _de_la_forge()}


def chemin_carte(slug: str, carte: str) -> Path:
    """Une carte du pack du studio, CONFINÉE à son dossier."""
    if not (isinstance(slug, str) and SLUG.match(slug)) or carte not in CARTES + ("vignette",):
        raise RefusHabillage("Matière ou carte inconnue.", 404)
    if slug not in {t.get("id") for t in pack().get("textures", [])}:
        raise RefusHabillage("Matière ou carte inconnue.", 404)
    f = (TEXTURES / slug / f"{carte}.jpg").resolve()
    if not f.is_relative_to(TEXTURES.resolve()) or not f.is_file():
        raise RefusHabillage("Matière ou carte inconnue.", 404)
    return f


def vignette(source: str, ident: str) -> bytes:
    """La vignette (96 px, JPEG) d'une matière de la Forge — catalogue (`cat`) ou utilisateur (`mat`) — fabriquée à la
    demande depuis sa carte de couleur et gardée en mémoire."""
    from PIL import Image
    if source == "cat" and isinstance(ident, str) and SLUG.match(ident):
        from app.services import starter_materials as SM
        try:
            f = SM.carte_path(ident, "basecolor")
        except SM.StarterError:
            raise RefusHabillage("Matière ou carte inconnue.", 404) from None
    elif source == "mat" and isinstance(ident, str) and re.match(r"^[0-9a-f]{8}$", ident):
        from app.services import material_store as MS
        try:
            f = MS.map_path(f"mat_{ident}", "basecolor")
        except ValueError:
            raise RefusHabillage("Matière ou carte inconnue.", 404) from None
    else:
        raise RefusHabillage("Matière ou carte inconnue.", 404)
    try:
        cle = (source, ident, f.stat().st_mtime_ns)
    except OSError:
        raise RefusHabillage("Matière ou carte inconnue.", 404) from None
    with _VERROU:
        if cle in _vignettes:
            return _vignettes[cle]
    with Image.open(f) as im:
        im.draft("RGB", (192, 192))
        im = im.convert("RGB").resize((96, 96), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=78)
    with _VERROU:
        if len(_vignettes) >= MAX_VIGNETTES:
            _vignettes.clear()
        _vignettes[cle] = buf.getvalue()
    return buf.getvalue()


# ── depuis Blender : cuire une matière d'un fichier .blend et la ranger dans la Forge ──

def _blender() -> str:
    from app.services import passes_blender as PB
    e = PB.etat_blender()
    if not e.get("dispo") or not e.get("exe"):
        raise RefusHabillage("Blender est introuvable : indiquez son chemin dans Réglages › Moteurs et logiciels 3D.", 409)
    return str(e["exe"])


def _fichier_blend(chemin) -> Path:
    if not isinstance(chemin, str) or not chemin.strip():
        raise RefusHabillage("Indiquez le chemin d'un fichier .blend.", 400)
    f = Path(chemin.strip().strip('"'))
    if f.suffix.lower() != ".blend" or not f.is_file():
        raise RefusHabillage("Fichier .blend introuvable.", 404)
    return f


def _lancer_blender(blend: Path, arguments: list) -> str:      # couture : remplacée au banc
    """Blender sans fenêtre, scripts du fichier NON exécutés (--disable-autoexec) ; rend ce qu'il imprime."""
    argv = [_blender(), "--background", "--disable-autoexec", str(blend), "--python", str(SCRIPT_CUISSON), "--"] + arguments
    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=DELAI_BLENDER)
    except subprocess.TimeoutExpired:
        raise RefusHabillage("La cuisson a pris trop de temps : essayez une matière à la fois.", 504) from None
    except OSError:
        raise RefusHabillage("Blender n'a pas pu être lancé.", 502) from None
    return r.stdout or ""


def _ligne(sortie: str, marque: str):
    for ligne in reversed(sortie.splitlines()):
        if ligne.startswith(marque + " "):
            try:
                return json.loads(ligne[len(marque) + 1:])
            except ValueError:
                return None
    return None


def matieres_blender(chemin) -> list:
    """Les matières (à nœuds) d'un fichier .blend."""
    noms = _ligne(_lancer_blender(_fichier_blend(chemin), ["--liste"]), "MATIERES")
    if not isinstance(noms, list):
        raise RefusHabillage("Blender n'a pas pu lire ce fichier.", 502)
    return [n for n in noms if isinstance(n, str)][:200]


def _vers_la_forge(dossier: Path, nom: str, fichier: str) -> dict:
    """Trois (ou quatre) cartes cuites -> une matière ordinaire de la Forge ; les autres cartes sont dérivées."""
    from PIL import Image
    from app.services import material_store as MS
    from app.services import pbr_service as PBR
    with Image.open(dossier / "basecolor.png") as im:
        base = im.convert("RGB")
    res = base.size[0] if base.size[0] == base.size[1] and base.size[0] in MS.RESOLUTIONS else 1024
    if base.size != (res, res):
        base = base.resize((res, res), Image.LANCZOS)
    mat = MS.create_material(name=S.K._texte(nom, "Matière de Blender", 60) or "Matière de Blender", prompt="", full_prompt="", res=res,
                             seamless=True, seam={"before": None, "after": None},
                             source={"kind": "upload", "model": None, "filename": f"blender:{fichier}"[:120], "prep": None})
    mid = mat["id"]
    maps = PBR.derive_maps(base, mat["derive"], list(MS.SECONDARY_MAPS))
    maps["basecolor"] = base
    for carte, mode in (("normal", "RGB"), ("roughness", "L"), ("metallic", "L")):
        f = dossier / f"{carte}.png"
        if f.is_file():
            with Image.open(f) as im:
                maps[carte] = im.convert(mode).resize((res, res))
    maps["orm"] = Image.merge("RGB", (maps["ao"].convert("L"), maps["roughness"].convert("L"), maps["metallic"].convert("L")))
    MS.save_maps(mid, maps)
    MS.write_source(mid, base)
    mat = MS.read_material(mid)
    mat["props"] = MS.merge_props(mat["props"], MS.natural_levels(maps))
    mat = MS.refresh_report(mat, maps)
    MS.write_material(mat)
    return {"ref": f"mat:{mid[4:]}", "id": mid, "nom": mat.get("name") or mid}


def cuire_blender(chemin, matiere=None, metres=1.0) -> list:
    """Cuit une matière (ou toutes, MAX_CUISSONS au plus) d'un fichier .blend et la range dans la Forge. Rend
    [{ref, id, nom}] : la référence `mat:` se pose aussitôt sur une surface du décor."""
    blend = _fichier_blend(chemin)
    arguments = ["--taille", "1024", "--metres", str(S._n(metres, 1.0, 0.05, 20.0))]
    if isinstance(matiere, str) and matiere.strip():
        arguments += ["--matiere", matiere.strip()[:120]]
    tmp = Path(tempfile.mkdtemp(prefix="dzcuisson_"))
    try:
        faits = _ligne(_lancer_blender(blend, ["--sortie", str(tmp)] + arguments), "CUISSON_OK")
        if not isinstance(faits, list) or not faits:
            raise RefusHabillage("La cuisson n'a rien produit : la matière existe-t-elle dans ce fichier ?", 502)
        out = []
        for x in faits[:MAX_CUISSONS]:
            d = (tmp / str(x.get("dossier") or "")).resolve()
            if d.is_relative_to(tmp.resolve()) and (d / "basecolor.png").is_file():
                out.append(_vers_la_forge(d, str(x.get("nom") or d.name), blend.name))
        if not out:
            raise RefusHabillage("La cuisson n'a rien produit : la matière existe-t-elle dans ce fichier ?", 502)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── les finitions sans image : couleur + rugosité + métal (+ motif dessiné) ──

def _f(fid, couleur, rugosite, metal=0.0, motif="uni", usages=()):
    return {"id": fid, "couleur": couleur, "rugosite": rugosite, "metal": metal, "motif": motif, "usages": list(usages)}


FINITIONS = [
    _f("laque_blanche", "#f2f2ee", 0.16, usages=("bois", "plastique", "mur")),
    _f("laque_noire", "#0c0c0e", 0.12, usages=("bois", "plastique", "sol")),
    _f("blanc_mat", "#e9e7e2", 0.9, usages=("mur", "plafond", "bois")),
    _f("noir_mat", "#141416", 0.85, usages=("mur", "plafond", "bois", "metal")),
    _f("anthracite", "#2a2d33", 0.7, usages=("mur", "plafond", "metal")),
    _f("bleu_nuit", "#141d33", 0.85, usages=("mur", "plafond")),
    _f("vert_sapin", "#1d3329", 0.85, usages=("mur",)),
    _f("terracotta", "#b3583c", 0.9, usages=("mur",)),
    _f("acier_brosse", "#9aa3ad", 0.36, 0.9, "metal", usages=("metal",)),
    _f("alu_noir", "#22252a", 0.42, 0.8, usages=("metal",)),
    _f("chrome", "#dfe5ea", 0.06, 1.0, usages=("metal",)),
    _f("or", "#d9a941", 0.22, 1.0, usages=("metal",)),
    _f("laiton", "#b8923a", 0.36, 1.0, usages=("metal",)),
    _f("cuivre", "#b56b3a", 0.3, 1.0, usages=("metal",)),
    _f("verre_fume", "#1c2530", 0.05, 0.6, usages=("plastique", "sol")),
    _f("couleur_marque", "principale", 0.55, usages=("mur", "plastique", "tissu", "cuir")),
    _f("couleur_accent", "accent", 0.55, usages=("mur", "plastique", "tissu", "cuir")),
]


# ── les ambiances lumineuses ──
# cle / appoint / contre : les trois points ; neons : les couleurs que se partagent, à tour de rôle, les néons, les
# rubans LED et les objets lumineux ; ambiance : la lumière d'ensemble. Règle des plateaux : pas de couleur vive
# sur le visage — la clé et l'appoint restent proches du blanc, la couleur vit dans le contre et dans le fond.

def _a(aid, cle, appoint, contre, neons, ambiance):
    return {"id": aid, "cle": cle, "appoint": appoint, "contre": contre, "neons": list(neons), "ambiance": ambiance}


AMBIANCES = [
    _a("marque", "#fff1dc", "#dfe9ff", "accent", ("principale", "accent"), "#8fa3c8"),
    _a("studio_neutre", "#ffffff", "#eef3ff", "#ffffff", ("#ffffff", "#dfe9ff"), "#dfe6f0"),
    _a("tungstene", "#ffd9a8", "#ffe8cf", "#ffb46b", ("#ffb46b", "#ffd9a0"), "#ffb070"),
    _a("jour_doux", "#fff4e0", "#e8f1ff", "#ffe2b8", ("#fff0d0", "#cfe4ff"), "#f3ede2"),
    _a("sarcelle_orange", "#ffe6c8", "#cfeeea", "#19c4c0", ("#19c4c0", "#ff7a2a"), "#1d6f78"),
    _a("magenta_cyan", "#ecdcff", "#c8f4ff", "#ff2bd6", ("#ff2bd6", "#00e5ff"), "#5a2bd0"),
    _a("violet_bleu", "#e6dcff", "#cfe0ff", "#8a4bff", ("#8a4bff", "#2b7bff"), "#3a2a90"),
    _a("coucher", "#ffe0c0", "#ffd0d8", "#ff6a3d", ("#ff3d7f", "#ffb03d"), "#b0503c"),
    _a("or_chaud", "#fff0d8", "#fff6e8", "#ffc24a", ("#ffc24a", "#fff0c8"), "#8a6a30"),
    _a("vert_matrice", "#eaffea", "#d8ffe8", "#2bff88", ("#2bff88", "#b6ff3d"), "#104a2c"),
    _a("rouge_direct", "#fff4ec", "#ffe9e4", "#ff2b2b", ("#ff2b2b", "#ffffff"), "#5a1414"),
    _a("glace", "#f4fbff", "#e2f4ff", "#7fdcff", ("#7fdcff", "#ffffff"), "#9fd4ee"),
    _a("pastel", "#fff6f0", "#f0f6ff", "#ff9ecb", ("#ff9ecb", "#9ee7ff"), "#e8d8f0"),
    _a("arcade", "#f0e4ff", "#d8f0ff", "#ff3df0", ("#ff3df0", "#ffe23d", "#3df0ff"), "#40208a"),
    _a("feu_de_bois", "#ffcf9a", "#ffdcb4", "#ff8a3c", ("#ff9a4a", "#ffc070"), "#a04a20"),
    _a("stade", "#ffffff", "#eaf2ff", "#ffffff", ("#ffffff", "#9fc0ff"), "#9fc0ff"),
]


# ── les styles complets : une matière par usage + une ambiance ──

def _m(texture="", couleur=None, teinte=False, rugosite=None, metal=None, finition=None):
    d = {"texture": texture, "teinte": teinte}
    if finition:
        f = next(x for x in FINITIONS if x["id"] == finition)
        d.update({"couleur": f["couleur"], "rugosite": f["rugosite"], "metal": f["metal"], "motif": f["motif"]})
    if couleur:
        d["couleur"] = couleur
    if rugosite is not None:
        d["rugosite"] = rugosite
    if metal is not None:
        d["metal"] = metal
    return d


def _s(sid, ambiance, **matieres):
    return {"id": sid, "ambiance": ambiance, "matieres": matieres}


STYLES = [
    _s("scandinave", "jour_doux", sol=_m("stu:laminate_floor_02"), mur=_m("stu:plastered_wall", "#f1ede6", True),
       plafond=_m(finition="blanc_mat"), bois=_m("stu:oak_veneer_01"), tissu=_m("stu:curly_teddy_natural"),
       cuir=_m("stu:leather_white"), metal=_m(finition="noir_mat")),
    _s("industriel", "tungstene", sol=_m("stu:concrete_floor_worn_001"), mur=_m("stu:factory_brick"),
       plafond=_m(finition="noir_mat"), bois=_m("stu:wood_cabinet_worn_long"), tissu=_m("cat:denim_fabric"),
       cuir=_m("cat:brown_leather"), metal=_m(finition="acier_brosse")),
    _s("loft_brique", "coucher", sol=_m("stu:herringbone_parquet"), mur=_m("cat:brick_wall_001"),
       plafond=_m(finition="blanc_mat"), bois=_m("stu:rosewood_veneer1"), tissu=_m("cat:rough_linen"),
       cuir=_m("stu:fabric_leather_02"), metal=_m(finition="alu_noir")),
    _s("tasseaux_noyer", "sarcelle_orange", sol=_m("stu:wood_floor"), mur=_m("stu:plastered_wall", "#23262b", True),
       plafond=_m(finition="noir_mat"), bois=_m("stu:wood_table_001"), tissu=_m("stu:poly_wool_herringbone"),
       cuir=_m("stu:leather_red_02"), metal=_m(finition="alu_noir")),
    _s("cyberpunk", "magenta_cyan", sol=_m(finition="laque_noire"), mur=_m("stu:concrete_wall_008", "#1a1626", True),
       plafond=_m(finition="noir_mat"), bois=_m(finition="noir_mat"), tissu=_m("stu:velour_velvet", "#5a2bd0", True),
       cuir=_m("stu:leather_white", "#15151a", True), metal=_m(finition="chrome")),
    _s("luxe_noir_or", "or_chaud", sol=_m("stu:marble_01", "#2a2a2e", True, rugosite=0.25),
       mur=_m("stu:plastered_wall", "#17171a", True), plafond=_m(finition="noir_mat"), bois=_m("stu:rosewood_veneer1"),
       tissu=_m("stu:velour_velvet", "#23232a", True), cuir=_m("stu:leather_white", "#101012", True),
       metal=_m(finition="or")),
    _s("chalet", "feu_de_bois", sol=_m("stu:plank_flooring_02"), mur=_m("cat:brown_planks_03"),
       plafond=_m("stu:wood_cabinet_worn_long"), bois=_m("stu:wood_table_001"), tissu=_m("stu:fabric_pattern_07"),
       cuir=_m("cat:brown_leather"), metal=_m(finition="laiton")),
    _s("minimal_blanc", "studio_neutre", sol=_m("stu:concrete_floor_worn_001", "#d9d9d6", True),
       mur=_m("stu:plastered_wall", "#f4f3f0", True), plafond=_m(finition="blanc_mat"), bois=_m("stu:plywood"),
       tissu=_m("stu:poly_wool_herringbone", "#e6e2da", True), cuir=_m("stu:leather_white"), metal=_m(finition="chrome")),
    _s("pastel", "pastel", sol=_m("stu:laminate_floor_02"), mur=_m("stu:plastered_wall", "#f3d9e4", True),
       plafond=_m(finition="blanc_mat"), bois=_m(finition="laque_blanche"), tissu=_m("stu:cotton_jersey"),
       cuir=_m("stu:leather_white", "#cfe8e0", True), metal=_m(finition="laiton")),
    _s("bibliotheque", "tungstene", sol=_m("stu:diagonal_parquet"), mur=_m("stu:plastered_wall", "#1d3329", True),
       plafond=_m(finition="blanc_mat"), bois=_m("stu:dark_wood"), tissu=_m("stu:book_pattern"),
       cuir=_m("stu:leather_red_02"), metal=_m(finition="laiton")),
    _s("beton_brut", "sarcelle_orange", sol=_m("cat:brushed_concrete"), mur=_m("stu:concrete_wall_008"),
       plafond=_m("stu:concrete_wall_008"), bois=_m("stu:plywood"), tissu=_m("stu:poly_wool_herringbone"),
       cuir=_m("stu:leather_white", "#2a2a2c", True), metal=_m(finition="acier_brosse")),
    _s("arcade_retro", "arcade", sol=_m("stu:checkered_pavement_tiles"), mur=_m("stu:plastered_wall", "#1c1436", True),
       plafond=_m(finition="noir_mat"), bois=_m(finition="laque_noire"), tissu=_m("stu:velour_velvet"),
       cuir=_m("stu:leather_white", "#c0162c", True), metal=_m(finition="chrome")),
    _s("salle_de_sport", "stade", sol=_m("stu:rubber_tiles"), mur=_m("stu:painted_brick"),
       plafond=_m(finition="anthracite"), bois=_m("stu:plywood"), tissu=_m("cat:denim_fabric"),
       cuir=_m("stu:leather_white", "#15151a", True), metal=_m(finition="acier_brosse")),
    _s("marque", "marque", sol=_m("stu:concrete_floor_worn_001", "#3a3c40", True),
       mur=_m("stu:plastered_wall", "principale", True), plafond=_m(finition="noir_mat"), bois=_m(finition="laque_noire"),
       tissu=_m("stu:velour_velvet", "accent", True), cuir=_m("stu:leather_white", "accent", True),
       metal=_m(finition="chrome")),
]


def habillage() -> dict:
    """Tout ce que le décorateur propose. Les noms des styles, ambiances, finitions, familles et objets sont dans le
    dictionnaire de l'écran (studiov.style.<id>, studiov.ambiance.<id>…) ; ceux des matières viennent avec elles."""
    return {"textures": textures(), "familles_texture": FAMILLES_TEXTURE, "finitions": FINITIONS,
            "ambiances": AMBIANCES, "styles": STYLES, "catalogue": S.catalogue()}
