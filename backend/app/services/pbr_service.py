"""Material Forge — derivation des maps PBR a partir d'une image de base.

PIL PUR, zero numpy (le runtime embarque n'a que Pillow). Modele : `pixel_ops`.

Point dur : **toutes les convolutions sont CYCLIQUES**. Une convolution
classique lit du noir hors cadre et casse le raccord des maps derivees : la
normale et l'AO d'une tuile seamless cesseraient d'etre raccordables, ce qui
ruine le seul argument mesurable du Material Forge. Le procede est toujours le
meme (`_cyclic`) : on tuile l'image 3x3, on recadre un cadre de `p` px, on
convolue, on recadre a la taille d'origine. `p` = portee du noyau (>= 1, et
>= ao_radius pour l'AO).

Huit maps produites (la barre Sorceress n'en a que six) :
  basecolor RGB · normal RGB · roughness L · metallic L · ao L · height L ·
  emissive RGB · orm RGB (R=AO, G=Roughness, B=Metallic, glTF-ready).

`seam_score` / `make_seamless` restent dans `pixel_ops` — on ne les reecrit pas.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageFilter, ImageOps

__all__ = [
    "MAP_KINDS", "MAP_MODES", "METALLIC_MODES", "ROUGHNESS_SOURCES",
    "DERIVE_DEFAULTS",
    "DERIVE_RANGES", "normalize_derive", "derive_maps", "resize_maps",
    "luminance", "LEVEL_MAPS", "bake_levels", "level_lut", "level_stats",
    "level_mean",
    "stats", "natural_level", "correlation", "report_channel",
    "FLAT_SPAN", "DEPENDENT_R", "effective_levels",
    "map_report", "seam_report", "SEAM_SCALES", "SEAM_GRADES", "seam_grade",
]


# ── contrat des maps ─────────────────────────────────────────────────────────

MAP_KINDS: tuple[str, ...] = (
    "basecolor", "normal", "roughness", "metallic",
    "ao", "height", "emissive", "orm",
)

MAP_MODES: dict[str, str] = {
    "basecolor": "RGB", "normal": "RGB", "emissive": "RGB", "orm": "RGB",
    "roughness": "L", "metallic": "L", "ao": "L", "height": "L",
}

METALLIC_MODES: tuple[str, ...] = ("auto", "none", "luminance")

# D'ou vient le motif de rugosite. Voir `_roughness` : "micro" est le defaut,
# "albedo" garde l'ancienne formule (1 - luminance) pour comparaison.
ROUGHNESS_SOURCES: tuple[str, ...] = ("micro", "albedo")

# Defauts figes par SPEC.md section 2 (bloc "derive").
DERIVE_DEFAULTS: dict = {
    "normal_strength": 0.8,
    "normal_invert_y": False,
    "roughness_source": "micro",
    "roughness_bias": 0.5,
    "roughness_contrast": 0.5,
    "roughness_invert": False,
    "ao_strength": 1.0,
    "ao_radius": 4.0,
    "metallic_mode": "auto",
    "metallic_threshold": 0.5,
    "emissive_threshold": 0.85,
    "height_detail": 0.5,
}

# Bornes de securite : toute valeur hors bornes est ramenee dedans, jamais
# rejetee (SPEC : "toute valeur absente ou invalide recoit le defaut, jamais
# d'erreur 500").
DERIVE_RANGES: dict[str, tuple[float, float]] = {
    "normal_strength": (0.0, 4.0),
    "roughness_bias": (0.0, 1.0),
    "roughness_contrast": (0.0, 1.0),
    "ao_strength": (0.0, 4.0),
    "ao_radius": (0.5, 32.0),
    "metallic_threshold": (0.0, 1.0),
    "emissive_threshold": (0.0, 1.0),
    "height_detail": (0.0, 1.0),
}

_TRUE = {"1", "true", "yes", "on", "oui", "vrai"}
_FALSE = {"0", "false", "no", "off", "non", "faux", ""}


def _as_bool(raw, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in _TRUE:
            return True
        if s in _FALSE:
            return False
    return default


def _as_float(raw, default: float, lo: float, hi: float) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return default
    if v != v or v in (float("inf"), float("-inf")):   # NaN / inf
        return default
    return lo if v < lo else hi if v > hi else v


def normalize_derive(raw) -> dict:
    """Reglages de derivation complets et bornes. Ne leve jamais : ce qui est
    absent ou illisible recoit le defaut, ce qui deborde est ramene aux bornes.
    Les cles inconnues sont ignorees."""
    out = dict(DERIVE_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    for key, default in DERIVE_DEFAULTS.items():
        if key not in raw or raw[key] is None:
            continue
        val = raw[key]
        if isinstance(default, bool):
            out[key] = _as_bool(val, default)
        elif key == "metallic_mode":
            s = str(val).strip().lower()
            out[key] = s if s in METALLIC_MODES else default
        elif key == "roughness_source":
            s = str(val).strip().lower()
            out[key] = s if s in ROUGHNESS_SOURCES else default
        else:
            lo, hi = DERIVE_RANGES[key]
            out[key] = _as_float(val, default, lo, hi)
    return out


# ── convolution cyclique ─────────────────────────────────────────────────────

def _wrap(img: Image.Image, p: int) -> Image.Image:
    """Image bordee de `p` px preleves cycliquement : tuilage 3x3 recadre."""
    w, h = img.size
    big = Image.new(img.mode, (w + 2 * p, h + 2 * p))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            big.paste(img, (p + dx * w, p + dy * h))
    return big


def _cyclic(img: Image.Image, flt, reach: float) -> Image.Image:
    """Applique `flt` avec des bords cycliques. `reach` = portee du noyau en
    px ; on borde d'autant, on filtre, on recadre. C'est CE detail qui garde
    les maps derivees raccordables."""
    w, h = img.size
    p = max(1, min(int(math.ceil(reach)), w, h))
    return _wrap(img, p).filter(flt).crop((p, p, p + w, p + h))


def _c8(v: float) -> int:
    return 0 if v < 0 else 255 if v > 255 else int(round(v))


def _ramp_lut(lo: float, hi: float, invert: bool = False) -> list[int]:
    """LUT 256 : rampe lineaire 0 -> 255 entre les niveaux normalises lo et hi."""
    if hi <= lo:
        hi = lo + 1e-6
    lut = []
    for i in range(256):
        t = (i / 255.0 - lo) / (hi - lo)
        t = 0.0 if t < 0 else 1.0 if t > 1 else t
        lut.append(_c8(255.0 * ((1.0 - t) if invert else t)))
    return lut


def luminance(img: Image.Image) -> Image.Image:
    """Luminance ITU-R 601 (0.299/0.587/0.114) — c'est exactement ce que fait
    `convert("L")` de Pillow, sans copie inutile si l'image est deja en L."""
    return img if img.mode == "L" else img.convert("L")


# ── normale : Sobel cycliques + renormalisation 8 bits ───────────────────────

# Piege Pillow (verifie par reponse impulsionnelle, pas suppose) : Kernel
# applique les LIGNES du noyau a l'envers — la 1re ligne ecrite frappe y+1 —
# mais les colonnes a l'endroit. Le noyau Y est donc ecrit "retourne" pour que
# la sortie vaille bien +d(hauteur)/dy en coordonnees image (y vers le bas).
_SOBEL_X = (-1, 0, 1,
            -2, 0, 2,
            -1, 0, 1)
_SOBEL_Y = (1,  2,  1,
            0,  0,  0,
            -1, -2, -1)

# Somme des poids absolus / 2 = 8 : la sortie vaut 128 + d(hauteur)/dx en
# niveaux par pixel, centree sur 128 et lisible en 8 bits.
_SOBEL_SCALE = 8

# (v - 128)/127 au carre, en 0..255 — pour reconstruire Z sans numpy.
_SQ_LUT = [min(255, int(round(255.0 * ((v - 128) / 127.0) ** 2)))
           for v in range(256)]
# 255 * sqrt(max(0, 1 - (x^2 + y^2)))
_Z_LUT = [int(round(255.0 * math.sqrt(max(0.0, 1.0 - v / 255.0))))
          for v in range(256)]


def _renormalize(nx: Image.Image, ny: Image.Image) -> Image.Image:
    """Recompose la normale en imposant x^2 + y^2 + z^2 = 1. Tout se fait en
    8 bits : deux LUT (`Image.point`) et une addition saturante `ImageChops`."""
    sq = ImageChops.add(nx.point(_SQ_LUT), ny.point(_SQ_LUT))
    return Image.merge("RGB", (nx, ny, sq.point(_Z_LUT)))


def _normal(height: Image.Image, d: dict) -> Image.Image:
    strength = d["normal_strength"] * 4.0
    kx = ImageFilter.Kernel((3, 3), _SOBEL_X, scale=_SOBEL_SCALE, offset=128)
    ky = ImageFilter.Kernel((3, 3), _SOBEL_Y, scale=_SOBEL_SCALE, offset=128)
    gx = _cyclic(height, kx, 1)
    gy = _cyclic(height, ky, 1)
    # OpenGL (+Y vers le haut) par defaut ; normal_invert_y bascule en DirectX.
    sign = -1.0 if d["normal_invert_y"] else 1.0
    lut_x = [_c8(128.0 - (v - 128) * strength) for v in range(256)]
    lut_y = [_c8(128.0 + sign * (v - 128) * strength) for v in range(256)]
    return _renormalize(gx.point(lut_x), gy.point(lut_y))


# ── les huit maps ────────────────────────────────────────────────────────────

def _height(lum: Image.Image, d: dict) -> Image.Image:
    """Luminance -> flou gaussien cyclique -> autocontraste doux (clip 1 %).
    `height_detail` 1.0 garde le grain, 0.0 ne garde que les grandes formes."""
    radius = 1.0 + 3.0 * (1.0 - d["height_detail"])
    blurred = _cyclic(lum, ImageFilter.GaussianBlur(radius), radius * 3.0 + 1)
    return ImageOps.autocontrast(blurred, cutoff=1)


# ── rugosite : ce que la surface FAIT, pas ce que la photo montre ───────────
#
# LE DEFAUT QUE CECI CORRIGE. La rugosite valait `1 - luminance` : elle
# recopiait donc l'eclairage cuit dans l'image source. Deux consequences
# mesurees sur nos quinze matieres du disque :
#
#   1. correlation avec la luminance de la basecolor : -0.76 a -0.99
#      (mediane -0.90). Une map qui correle a 0.9 avec la basecolor n'apporte
#      AUCUNE information independante : chaque reflet speculaire deja cuit
#      dans la photo devenait une zone miroir, chaque ombre portee devenait
#      rugueuse. Physiquement a l'envers, et la matiere s'effondre des qu'on la
#      re-eclaire.
#   2. le motif saturait. `bias + (v - 0.5) * 2.0` ecrete tout ce qui sort de
#      [0.25, 0.75] ; sur une image sombre (« acier rouge »), `1 - luminance`
#      valait ~1.0 partout -> motif constant a 255 -> map cuite constante :
#      centiles 5 % et 95 % tous les deux a 64/255, soit 0.0 % de variation
#      utile, presentee comme une map pleine.
#
# CE QU'ON FAIT A LA PLACE. La rugosite ne se lit pas dans le NIVEAU de gris,
# elle se lit dans deux indices differentiels, tous deux insensibles a un
# gradient d'eclairage :
#
#   micro-contraste  |L - flou(L, r)|  : le grain fin. Une surface qui accroche
#                    la lumiere a l'echelle du pixel est rugueuse ; un aplat
#                    lisse est poli. Un degrade d'eclairage est basse
#                    frequence : il disparait dans la soustraction.
#   cavite           flou(H, r) - H    : les creux. Poussiere, usure et
#                    oxydation s'y accumulent — ils sont plus rugueux que les
#                    parties saillantes, qui se polissent au frottement.
#
# Les deux sont normalises (autocontraste, clip 1 %) puis melanges, puis
# recentres par gamma sur 0.5 AVANT le remappage bias/contraste : c'est ce
# recentrage qui empeche le remappage de re-ecreter d'un cote. Le reglage
# `roughness_source = "albedo"` restaure l'ancienne formule (comparaison, et
# les matieres dont l'albedo EST la carte d'usure).
_ROUGH_MICRO_RADIUS = 2.5        # px, echelle du grain
_ROUGH_CAVITY_W = 0.35           # poids de la cavite dans le melange

# Gains FIXES, jamais un autocontraste.
#
# Piege mesure, et c'est le meme des deux cotes : `|L - flou(L)|` comme
# `flou(H) - H` ont une mediane nulle et une amplitude faible. Les normaliser
# par autocontraste revient a multiplier le residu par 6 a 11 — et ce residu
# contient le pas d'echantillonnage de la jonction de tuile. Mesure sur la
# tuile periodique de la recette : raccord 0.28 sur la source, 15.3 sur la
# rugosite ainsi normalisee (la barre du BRIEF est 2.0). Avec un gain fixe,
# l'amplification est bornee et connue : une surface peu texturee sort peu
# rugueuse, ce qui est la verite, au lieu de sortir bruyante.
_ROUGH_MICRO_GAIN = 6.0          # le grain est faible en amplitude
_ROUGH_CAVITY_GAIN = 3.0         # meme gain que l'occlusion (_AO_GAIN)

# Le contraste se mesure en LOGARITHME, pas en niveaux.
#
# Un meme grain photographie a l'ombre et au soleil donne deux amplitudes
# ABSOLUES tres differentes (le contraste est multiplicatif : loi de Weber).
# Mesure de la difference que ca fait, sur les seize matieres du disque,
# |correlation| de la rugosite avec la luminance de la base color :
#     ecart absolu  |L - flou(L)|         mediane 0.52, pire 0.76
#     ecart log     |log L - flou(log L)| mediane 0.14, pire 0.83 (« grain 4K »,
#                                         une texture ou le grain EST la
#                                         luminance — la correlation y est
#                                         legitime, et elle est signalee)
# Le passage au log coute une LUT et rend le grain invariant a l'eclairage,
# ce qui est precisement l'objectif : ne pas cuire l'ombre dans la matiere.
_LOG_FLOOR = 6.0                 # plancher, sinon log(0)
_LOG_LUT = [
    _c8(255.0 * (math.log(max(v, _LOG_FLOOR) / 255.0)
                 - math.log(_LOG_FLOOR / 255.0)) / (-math.log(_LOG_FLOOR / 255.0)))
    for v in range(256)
]


def _micro_contrast(lum: Image.Image, radius: float) -> Image.Image:
    """Energie de contraste local en log : flou(|logL - flou(logL)|), gain fixe.

    Le second flou n'est pas cosmetique. `|logL - flou(logL)|` seul est un
    detecteur de CONTOUR ; floute, il devient une mesure de ZONE — « cette
    region accroche la lumiere a l'echelle du grain » — qui est aussi ce que la
    rugosite decrit physiquement. Un degrade d'eclairage est basse frequence :
    il disparait dans la soustraction, et c'est tout l'interet."""
    lg = lum.point(_LOG_LUT)
    blurred = _cyclic(lg, ImageFilter.GaussianBlur(radius), radius * 3.0 + 1)
    hp = ImageChops.difference(lg, blurred)
    r2 = radius * 2.0
    energy = _cyclic(hp, ImageFilter.GaussianBlur(r2), r2 * 3.0 + 1)
    return energy.point([_c8(v * _ROUGH_MICRO_GAIN) for v in range(256)])


def _cavity(height: Image.Image, radius: float) -> Image.Image:
    """flou(H) - H : ce qui est plus bas que son voisinage. Meme mesure que
    l'occlusion, meme gain — poussiere, usure et oxydation s'accumulent dans
    les creux, les saillies se polissent."""
    blurred = _cyclic(height, ImageFilter.GaussianBlur(radius), radius * 3.0 + 1)
    dips = ImageChops.subtract(blurred, height)
    return dips.point([_c8(v * _ROUGH_CAVITY_GAIN) for v in range(256)])


def _rough_pattern(lum: Image.Image, height: Image.Image, d: dict
                   ) -> tuple[Image.Image, float]:
    """Motif de rugosite et sa moyenne (0-1). La moyenne sert de pivot au
    remappage : c'est elle qui remplace le 0.5 de SPEC, sans quoi un motif
    naturellement faible serait entierement rejete d'un cote de l'ecretage —
    exactement ce qui rendait la map constante sur « acier rouge »."""
    if d["roughness_source"] == "albedo":
        pat = ImageChops.invert(lum)           # ancienne formule, sur demande
        return pat, 0.5                        # pivot d'origine, inchange
    micro = _micro_contrast(lum, _ROUGH_MICRO_RADIUS)
    cav = _cavity(height, max(1.0, d["ao_radius"]))
    mix = Image.blend(micro, cav, _ROUGH_CAVITY_W)
    return mix, stats(mix)["mean"] / 255.0


def _roughness(lum: Image.Image, height: Image.Image, d: dict) -> Image.Image:
    """Motif de rugosite remappe : v' = clamp(bias + (v - pivot) * (0.5 + 3*contrast))."""
    gain = 0.5 + 3.0 * d["roughness_contrast"]
    bias, invert = d["roughness_bias"], d["roughness_invert"]
    pattern, pivot = _rough_pattern(lum, height, d)
    lut = []
    for i in range(256):
        v = i / 255.0
        o = bias + (v - pivot) * gain
        o = 0.0 if o < 0 else 1.0 if o > 1 else o
        lut.append(_c8(255.0 * ((1.0 - o) if invert else o)))
    return pattern.point(lut)


# Octaves de l'AO : rayons r, 2r, 4r et leur poids. Une seule échelle ne voit
# que les creux de la taille du noyau ; une cavité large passe inaperçue parce
# que son fond est aussi bas que sa moyenne locale.
_AO_OCTAVES = ((1.0, 0.5), (2.0, 0.3), (4.0, 0.2))

# Gain de la creusée. MESURÉ, pas supposé : avec l'ancien gain de 1.0 et une
# seule octave, l'AO de « pierre moussue » et « écorce sombre » mesurait
# moy=251.5 / centile 1 % = 225 sur 255 — soit une occlusion de 1.4 % en
# moyenne, c'est-à-dire du blanc. Trois octaves à ce gain donnent moy≈233 et
# centile 1 %≈120 : les creux descendent à 0.47, ce qu'un AO cuit produit
# effectivement. Le réglage `ao_strength` multiplie ce gain (0 = blanc pur).
_AO_GAIN = 3.0


def _ao(height: Image.Image, d: dict) -> Image.Image:
    """Occlusion de cavité : ce qui est plus bas que son voisinage est occlus,
    mesuré à TROIS échelles (r, 2r, 4r) et cumulé.

        occl = Σ w_k · max(0, flou(height, r_k) − height)
        ao   = clamp(1 − gain · ao_strength · occl)

    Les flous sont CYCLIQUES, sinon les bords de tuile s'assombrissent et le
    raccord saute. `ao_strength = 0` rend un blanc uniforme (aucune occlusion),
    ce que l'interface doit alors annoncer comme une map sans information."""
    k = d["ao_strength"]
    if k <= 0.0:
        return Image.new("L", height.size, 255)
    radius = d["ao_radius"]
    occl = None
    for mult, weight in _AO_OCTAVES:
        r = radius * mult
        blurred = _cyclic(height, ImageFilter.GaussianBlur(r), r * 3.0 + 1)
        dips = ImageChops.subtract(blurred, height)    # = max(0, blur - height)
        part = dips.point([_c8(v * weight * _AO_GAIN * k) for v in range(256)])
        occl = part if occl is None else ImageChops.add(occl, part)
    return ImageChops.invert(occl)


_SAT_LUT = [_c8(255.0 * (1.0 - v / 64.0)) for v in range(256)]


def _metallic(rgb: Image.Image, lum: Image.Image, d: dict) -> Image.Image:
    mode = d["metallic_mode"]
    if mode == "none":
        return Image.new("L", rgb.size, 0)
    thr = d["metallic_threshold"]
    bright = lum.point(_ramp_lut(thr - 0.1, thr + 0.1))
    if mode == "luminance":
        return bright
    # "auto" : faible saturation + forte luminance = metal. Saturation HSV
    # calculee sans numpy : max(R,G,B) - min(R,G,B) via ImageChops.
    r, g, b = rgb.split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    grey = ImageChops.subtract(mx, mn).point(_SAT_LUT)
    return ImageChops.multiply(grey, bright)


def _emissive(rgb: Image.Image, lum: Image.Image, d: dict) -> Image.Image:
    """Basecolor masquee par luminance > seuil (rampe sur 0.1), noir ailleurs."""
    thr = d["emissive_threshold"]
    mask = lum.point(_ramp_lut(thr, min(1.0, thr + 0.1)))
    return Image.merge("RGB", tuple(ImageChops.multiply(ch, mask)
                                    for ch in rgb.split()))


# ── entree publique ──────────────────────────────────────────────────────────

def _needed(want: list[str]) -> set[str]:
    need = set(want)
    if "orm" in need:
        need |= {"ao", "roughness", "metallic"}
    # la rugosite lit la cavite, donc la hauteur (voir `_rough_pattern`)
    if need & {"normal", "ao", "roughness"}:
        need.add("height")
    return need


def derive_maps(base: Image.Image, derive: dict | None = None,
                want: list[str] | None = None) -> dict[str, Image.Image]:
    """Derive les maps PBR de `base`. Retourne uniquement les maps demandees
    (dans l'ordre de `MAP_KINDS`), mais calcule leurs dependances
    (orm -> ao/roughness/metallic, normal & ao -> height).

    Aucune erreur sur `derive` : il passe par `normalize_derive`."""
    d = normalize_derive(derive)
    if want:
        asked = [k for k in MAP_KINDS if k in set(want)]
    else:
        asked = list(MAP_KINDS)
    if not asked:
        return {}
    need = _needed(asked)

    rgb = base.convert("RGB")
    lum = luminance(rgb)                        # ITU-R 601

    built: dict[str, Image.Image] = {}
    if "basecolor" in need:
        built["basecolor"] = rgb
    if "height" in need:
        built["height"] = _height(lum, d)
    if "normal" in need:
        built["normal"] = _normal(built["height"], d)
    if "roughness" in need:
        built["roughness"] = _roughness(lum, built["height"], d)
    if "ao" in need:
        built["ao"] = _ao(built["height"], d)
    if "metallic" in need:
        built["metallic"] = _metallic(rgb, lum, d)
    if "emissive" in need:
        built["emissive"] = _emissive(rgb, lum, d)
    if "orm" in need:
        built["orm"] = Image.merge(
            "RGB", (built["ao"], built["roughness"], built["metallic"]))

    return {k: built[k] for k in asked}


# ── niveaux : la map PORTE la valeur reglee ─────────────────────────────────
#
# LE DEFAUT QUE CECI CORRIGE. L'inspecteur affichait « Metallique 1.00 » pour
# « or martele » ; la carte metallic derivee mesurait moy=1.17/255 et le canal
# B de l'ORM 1.17 aussi. Or la specification glTF pose
#     metalness effective = metallicFactor x metallicRoughnessTexture.B
# donc 1.0 x 0.0046 = 0.0046 : du plastique jaune, dans l'apercu COMME dans le
# GLB exporte (verifie : les deux fichiers portent le meme couple facteur x
# texture). Et le ZIP livrait un metallic.png noir, sans aucun facteur pour le
# rattraper — un moteur n'y voyait aucun metal.
#
# LA MEME CHOSE VAUT POUR LA RUGOSITE, et pour la meme raison :
#     rugosite effective = roughnessFactor x metallicRoughnessTexture.G
# Les deux niveaux sont donc cuits ici, les deux facteurs valent 1.0 dans le
# GLB, et `effective_levels` mesure le resultat sur les octets encodes pour que
# la valeur affichee sous le curseur soit une MESURE, pas une promesse.
#
# La regle retenue : **le niveau vit dans la MAP**, pas dans le facteur. Le
# motif derive n'est plus qu'une VARIATION autour de ce niveau :
#     sortie = clamp(niveau + amplitude x (motif - moyenne(motif)))
# la moyenne de la sortie vaut donc exactement le niveau regle (verifie par
# test a +/- 2/255), et l'amplitude est reduite d'office pour qu'aucun pixel ne
# soit ecrete — sans quoi la moyenne derivait. Le GLB met alors ses facteurs a
# 1.0 (gltf_builder) : apercu, GLB exporte et PNG du ZIP donnent la meme
# valeur, celle que l'utilisateur a reglee.
LEVEL_MAPS: tuple[str, ...] = ("metallic", "roughness")

# Amplitude de la variation conservee autour du niveau. 1.0 = on garde le
# motif TEL QUEL tant qu'il tient dans [0, 1] ; l'amplitude n'est reduite que
# de ce qu'il faut pour atteindre la moyenne demandee sans ecreter. Consequence
# assumee : aux extremes (metallique 0.00, rugosite 1.00) aucune variation ne
# tient — une map uniforme est alors la verite, et `map_report` le dit au lieu
# de compter la map comme pleine.
_LEVEL_SPREAD = 1.0


def natural_level(img: Image.Image) -> float:
    """Niveau que la map porte NATURELLEMENT (sa moyenne, en 0-1).

    C'est la valeur d'initialisation honnete d'une matiere fraiche : le
    curseur affiche alors ce que la texture vaut vraiment, et le cuire ne
    change rien (amplitude = 1.0). Regler le curseur ailleurs deplace la
    moyenne et comprime la variation d'autant — ce qui se voit, se mesure, et
    s'annonce."""
    return round(stats(img)["mean"] / 255.0, 3)


def _quantiles(hist: list[int], qs) -> list[int]:
    """Centiles d'un histogramme 256 classes, en une passe."""
    n = sum(hist) or 1
    want = [(q, i) for i, q in enumerate(qs)]
    out = [255] * len(qs)
    acc = 0
    k = 0
    for level, c in enumerate(hist):
        acc += c
        while k < len(want) and acc >= n * want[k][0]:
            out[want[k][1]] = level
            k += 1
        if k >= len(want):
            break
    return out


def stats(img: Image.Image) -> dict:
    """Moyenne / mediane / min / max / centiles 1, 5, 95 % d'une image L, par
    histogramme (aucune boucle par pixel, aucun numpy).

    `p5` et `p95` sont la mesure qui compte pour decider si une map porte une
    information : `min`/`max` sont des extremes, et une poignee de pixels
    aberrants suffit a les ouvrir. « Acier rouge » avait min=0 max=64 — 64
    niveaux d'amplitude apparente — pour p5 = p95 = 64 : la map etait
    RIGOUREUSEMENT constante sur 90 % de sa surface, et se comptait pleine."""
    if img.mode != "L":
        img = img.convert("L")
    h = img.histogram()
    n = sum(h) or 1
    mean = sum(i * c for i, c in enumerate(h)) / n
    p1, p5, med, p95 = _quantiles(h, (0.01, 0.05, 0.5, 0.95))
    lo = next((i for i, c in enumerate(h) if c), 0)
    hi = next((i for i in range(255, -1, -1) if h[i]), 0)
    return {"mean": round(mean, 2), "median": med, "min": lo, "max": hi,
            "p1": p1, "p5": p5, "p95": p95, "span": p95 - p5}


# ── information independante : la map dit-elle autre chose que la photo ? ────
#
# La reference (Sorceress Material Forge) derive sa rugosite de l'albedo
# inverse : correlation -0.987 avec la luminance de la base color. Une map qui
# correle a ce point ne porte pas d'information PBR, elle porte une copie de
# l'eclairage deja cuit dans l'image. On mesure donc, pour CHACUNE de nos maps,
# le coefficient de Pearson entre son canal utile et la luminance de la base
# color, et on l'affiche. Au-dela de |r| = 0.90, la map est declaree dependante
# — c'est dit, pas cache.
DEPENDENT_R = 0.90

# Cote de l'echantillon pour la correlation. 192x192 en reduction BOX = une
# moyenne de blocs : c'est la structure qu'on compare, pas le bruit de capteur,
# et le calcul reste sous 40 ms a 4096 (mesure).
_CORR_SIDE = 192


def correlation(a: Image.Image, b: Image.Image, side: int = _CORR_SIDE
                ) -> float:
    """Coefficient de Pearson entre deux images, sur un echantillon reduit.

    Pur Python : `tobytes()` d'une image L donne un octet par pixel."""
    if a is None or b is None:
        return 0.0
    n = max(8, int(side))
    A = a.convert("L").resize((n, n), Image.BOX).tobytes()
    B = b.convert("L").resize((n, n), Image.BOX).tobytes()
    if len(A) != len(B) or not A:
        return 0.0
    cnt = len(A)
    ma = sum(A) / cnt
    mb = sum(B) / cnt
    sa = sb = sab = 0.0
    for x, y in zip(A, B):
        dx = x - ma
        dy = y - mb
        sa += dx * dx
        sb += dy * dy
        sab += dx * dy
    if sa <= 1e-9 or sb <= 1e-9:
        return 0.0                      # une constante ne correle avec rien
    return round(sab / math.sqrt(sa * sb), 3)


def level_lut(hist: list[int], level: float, spread: float = _LEVEL_SPREAD
              ) -> list[int]:
    """LUT 256 qui recentre un motif sur `level` sans jamais ecreter.

    `hist` est l'histogramme du motif (256 classes). On calcule sa moyenne et
    ses extremes reels, puis on choisit l'amplitude la plus grande qui tienne
    dans [0, 1] des deux cotes : la moyenne de sortie reste `level` exactement.
    """
    level = 0.0 if level < 0.0 else 1.0 if level > 1.0 else float(level)
    n = sum(hist) or 1
    mean = sum(i * c for i, c in enumerate(hist)) / n / 255.0
    lo = next((i for i, c in enumerate(hist) if c), 0) / 255.0
    hi = next((i for i in range(255, -1, -1) if hist[i]), 255) / 255.0
    amp = max(0.0, float(spread))
    # marge disponible de part et d'autre du niveau, en unites de motif
    down, up = mean - lo, hi - mean
    if down > 1e-6:
        amp = min(amp, level / down)
    if up > 1e-6:
        amp = min(amp, (1.0 - level) / up)
    return [_c8(255.0 * (level + amp * (v / 255.0 - mean))) for v in range(256)]


def level_mean(hist: list[int], level: float, spread: float = _LEVEL_SPREAD
               ) -> float:
    """Moyenne EXACTE (0-1) des octets de la map cuite au niveau `level`.

    LE DEFAUT QUE CECI CORRIGE. `level_stats` predit la moyenne par la loi
    affine : elle vaut `level`. Les octets, eux, passent par une LUT arrondie a
    l'entier ; a 4096 la moyenne reellement encodee sortait a 0.402 pour un
    curseur a 0.400. Publier 0.400 comme « mesure » etait faux de 0.5/255.
    Ici on somme `LUT[i] x effectif[i]` sur l'histogramme du motif : c'est la
    moyenne des octets qui partiront, au bit pres, sans relire un seul pixel
    (1.46 s de decodage evitees a 4096, mesure)."""
    if not hist or len(hist) < 256:
        return 0.0
    lut = level_lut(hist, level, spread)
    n = sum(hist)
    if not n:
        return 0.0
    return sum(lut[i] * c for i, c in enumerate(hist)) / n / 255.0


def level_stats(pattern: dict, level: float, spread: float = _LEVEL_SPREAD
                ) -> dict:
    """Statistiques de la map cuite, calculees SANS relire l'image.

    `bake_levels` est affine : sortie = niveau + amp x (motif - moyenne), avec
    amp choisie pour ne rien ecreter. Connaissant moyenne/min/max du motif, la
    map cuite se deduit exactement. C'est ce qui permet a un simple reglage de
    curseur de mettre a jour ce que l'ecran annonce, sans relire 16 M pixels.
    """
    def _g(key, default):
        try:
            return float(pattern.get(key, default)) / 255.0
        except (TypeError, ValueError, AttributeError):
            return float(default) / 255.0

    mean = _g("mean", 0.0)
    lo, hi = _g("min", 0), _g("max", 255)
    q5, q95 = _g("p5", pattern.get("min", 0) if isinstance(pattern, dict)
                 else 0), _g("p95", pattern.get("max", 255)
                             if isinstance(pattern, dict) else 255)
    level = 0.0 if level < 0.0 else 1.0 if level > 1.0 else float(level)
    amp = max(0.0, float(spread))
    if mean - lo > 1e-6:
        amp = min(amp, level / (mean - lo))
    if hi - mean > 1e-6:
        amp = min(amp, (1.0 - level) / (hi - mean))

    def _out(v):
        return _c8(255.0 * (level + amp * (v - mean)))

    out_lo, out_hi = _out(lo), _out(hi)
    o5, o95 = _out(q5), _out(q95)
    return {"mean": round(255.0 * level, 2), "median": None,
            "min": out_lo, "max": out_hi, "p1": out_lo,
            "p5": o5, "p95": o95, "span": o95 - o5,
            # meme critere que `map_report` : l'amplitude UTILE, pas les
            # extremes. Sans quoi le curseur annoncerait « map pleine » sur une
            # map dont 90 % de la surface tient en un seul niveau.
            "informative": (o95 - o5) > _FLAT_SPAN}


def _level(img: Image.Image, level: float, spread: float = _LEVEL_SPREAD
           ) -> Image.Image:
    if img.mode != "L":
        img = img.convert("L")
    return img.point(level_lut(img.histogram(), level, spread))


def bake_levels(maps: dict[str, Image.Image], props: dict | None = None,
                spread: float = _LEVEL_SPREAD) -> dict[str, Image.Image]:
    """Applique les niveaux `props["metallic"]` / `props["roughness"]` aux maps
    concernees — metallic, roughness ET les canaux B/V de l'ORM.

    C'est le SEUL endroit qui transforme un motif en map livrable. Toutes les
    sorties passent par lui : l'apercu GLB, le GLB/glTF exporte, le ZIP et la
    vignette de map servie par l'API. Ce que l'ecran montre est donc, au pixel
    pres, ce que le moteur recevra.
    """
    p = props if isinstance(props, dict) else {}

    def lvl(key: str, default: float) -> float:
        try:
            v = float(p.get(key, default))
        except (TypeError, ValueError):
            return default
        if v != v:
            return default
        return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v

    m_lv, r_lv = lvl("metallic", 0.0), lvl("roughness", 1.0)
    out = dict(maps)
    if "metallic" in out and out["metallic"] is not None:
        out["metallic"] = _level(out["metallic"], m_lv, spread)
    if "roughness" in out and out["roughness"] is not None:
        out["roughness"] = _level(out["roughness"], r_lv, spread)
    orm = out.get("orm")
    if orm is not None:
        r, g, b = orm.convert("RGB").split()
        out["orm"] = Image.merge("RGB", (r, _level(g, r_lv, spread),
                                         _level(b, m_lv, spread)))
    return out


# ── ce que chaque map contient VRAIMENT ─────────────────────────────────────
#
# « 8 MAPS PBR » est un compte honnete seulement si les huit portent une
# information. Une map uniforme (AO toute blanche, emissive toute noire) n'en
# porte aucune : elle est neutre, et le dire vaut mieux que la compter.
# Le seuil est l'ecart type equivalent en 8 bits : en dessous de 2 niveaux
# d'amplitude utile, un moteur ne verra jamais la difference avec une constante.
# Amplitude UTILE = p95 - p5, en niveaux 0-255. Volontairement pas max - min :
# voir `stats`. En dessous de 2 niveaux sur 90 % de la surface, un moteur ne
# verra jamais la difference avec une constante.
_FLAT_SPAN = 2
FLAT_SPAN = _FLAT_SPAN

_MAP_NOTE_UNIFORM = {
    "metallic": "uniforme — métallicité {v} partout",
    "roughness": "uniforme — rugosité {v} partout",
    "ao": "uniforme — aucune occlusion (force à 0 ?)",
    "emissive": "éteinte — cette matière n'émet pas de lumière",
    "height": "uniforme — surface parfaitement plate",
    "normal": "plate — aucun relief",
}


def report_channel(kind: str, img: Image.Image) -> tuple[Image.Image, str]:
    """Le canal qui DECIDE de l'utilite de cette map, et son libelle.

    Sur une map packee, une moyenne nue laisse croire qu'elle porte sur les
    trois canaux (l'ORM etait annonce a 71.4 alors que ses canaux valent
    241.8 / 71.4 / 255)."""
    if kind == "normal":
        return img.convert("RGB").split()[0], "canal R — relief X"
    if kind == "orm":
        return img.convert("RGB").split()[1], "canal V — rugosité"
    if kind in ("basecolor", "emissive"):
        return img.convert("L"), "luminance"
    return (img if img.mode == "L" else img.convert("L")), ""


def map_report(maps: dict[str, Image.Image],
               base: Image.Image | None = None) -> dict:
    """Par map : statistiques du canal utile, information portee, et
    correlation avec la luminance de la base color.

    Retourne aussi le compte `informative` / `total` : c'est ce compte-la que
    l'ecran doit afficher, pas un « 8 » de principe.

    `base` (la base color) active la colonne `corr_lum`. Une map qui correle a
    plus de |0.90| avec la luminance de la photo n'apporte pas d'information
    independante — elle recopie l'eclairage cuit dans l'image — et c'est dit
    dans `note`, pas tu.
    """
    src_base = base if base is not None else maps.get("basecolor")
    lum = luminance(src_base.convert("RGB")) if src_base is not None else None
    out: dict = {}
    for kind, img in maps.items():
        if img is None:
            continue
        ch, chan = report_channel(kind, img)
        st = stats(ch)
        flat = st["span"] <= _FLAT_SPAN
        if kind == "emissive":
            # une emissive noire n'emet rien, meme si elle a du grain
            flat = flat or st["mean"] < 1.0
        elif kind == "metallic":
            # 0.5/255 de moyenne avec quelques pixels clairs, c'est du bruit :
            # la matiere est dielectrique, la map ne porte rien d'utile.
            flat = flat or st["mean"] < 1.5
        note = ""
        if flat:
            tpl = _MAP_NOTE_UNIFORM.get(kind, "uniforme — aucune variation")
            note = tpl.format(v=f"{st['mean'] / 255.0:.2f}")
            if kind == "metallic" and st["mean"] < 1.5:
                note = "métallicité nulle — cette matière est diélectrique"
        r = 0.0
        dependent = False
        if lum is not None and kind != "basecolor" and not flat:
            r = correlation(ch, lum)
            dependent = abs(r) >= DEPENDENT_R
            if dependent and not note:
                sens = "suit" if r > 0 else "suit à l'inverse"
                note = (f"{sens} la luminance de la base color (r = {r:+.2f}) "
                        f"— information peu indépendante de l'image source")
        out[kind] = {**st, "informative": not flat, "note": note,
                     "channel": chan, "corr_lum": r, "dependent": dependent}
    n_inf = sum(1 for v in out.values() if v["informative"])
    return {"maps": out, "informative": n_inf, "total": len(out),
            "dependent": sum(1 for v in out.values() if v["dependent"])}


# ── ce que le moteur verra vraiment ─────────────────────────────────────────

def effective_levels(maps: dict[str, Image.Image]) -> dict:
    """Metallicite et rugosite EFFECTIVES des maps livrees, en 0-1.

    glTF pose `rugosite = roughnessFactor x metallicRoughnessTexture.G` et
    `metalness = metallicFactor x metallicRoughnessTexture.B`. Nos facteurs
    valent 1.0 des qu'une texture porte le canal (gltf_builder), donc la
    valeur effective est la moyenne de la map — c'est CE chiffre qu'on mesure
    ici, sur les octets reellement encodes, et qu'on republie a cote du
    curseur. Aucune re-lecture des props : si les deux divergent un jour, la
    mesure le dira."""
    out: dict = {}
    orm = maps.get("orm")
    ch_r = ch_m = None
    if orm is not None:
        _, ch_r, ch_m = orm.convert("RGB").split()
    if maps.get("roughness") is not None:
        ch_r = maps["roughness"]
    if maps.get("metallic") is not None:
        ch_m = maps["metallic"]
    if ch_r is not None:
        out["roughness"] = round(stats(ch_r)["mean"] / 255.0, 3)
    if ch_m is not None:
        out["metallic"] = round(stats(ch_m)["mean"] / 255.0, 3)
    return out


# ── raccord : un score qui ne peut pas se donner 0 tout seul ────────────────
#
# LE DEFAUT QUE CECI CORRIGE. `pixel_ops.seam_score` compare la colonne 0 a la
# colonne w-1 ; `make_seamless` termine par `_close_loop`, qui rend ces deux
# colonnes IDENTIQUES. Le « apres » valait donc 0.00 pour les quinze matieres
# du disque : la mesure verifiait exactement ce que la correction impose, elle
# ne pouvait rien apprendre. Et l'ecran affichait l'AVANT (0.1, 1.5, 5.9, 23.2)
# sous une pastille verte « corrigee » — le style disait reussite la ou la
# legende disait defaut.
#
# Ce qu'on mesure ici : la jonction est-elle plus visible qu'une jonction
# QUELCONQUE de la meme image ? A trois echelles (2, 8, 32 px), on compare la
# marche au bord a la marche mediane a l'interieur. Le rapport est sans unite :
# 1.00 = la couture ne depasse pas le grain normal du materiau.
#
# CALIBRATION (mesuree, pas supposee). Neuf tuiles reelles, test a deux
# alternatives en aveugle : deux fenetres de 256 px a la meme echelle, l'une a
# cheval sur la jonction, l'autre non ; l'observateur designe celle qui porte
# la jonction.
#     ratio 0.96 / 0.98 / 1.36  -> 0 detection sur 3 (hasard)
#     ratio 1.27 / 2.03 / 3.22 / 5.78 / 5.81 / 6.23 -> 6 detections sur 6
# La detection est donc certaine des 2.0, et la zone 1.0-2.0 est incertaine
# (1.27 detecte sur un motif a texte lisible, 1.36 manque). D'ou les paliers.
SEAM_SCALES = (2, 8, 32)
SEAM_GRADES = ((1.0, "invisible"), (2.0, "discret"), (4.0, "visible"))


def seam_grade(ratio: float) -> str:
    for limit, label in SEAM_GRADES:
        if ratio <= limit:
            return label
    return "cassé"


def _band_v(img: Image.Image, x0: int, x1: int) -> Image.Image:
    return img.crop((x0, 0, x1, img.height)).resize((1, img.height), Image.BOX)


def _band_h(img: Image.Image, y0: int, y1: int) -> Image.Image:
    return img.crop((0, y0, img.width, y1)).resize((img.width, 1), Image.BOX)


def _diff100(a: Image.Image, b: Image.Image) -> float:
    from PIL import ImageStat
    d = ImageStat.Stat(ImageChops.difference(a, b)).mean
    return sum(d) / len(d) / 255.0 * 100.0


def seam_report(img: Image.Image, samples: int = 24) -> dict:
    """Rapport de raccord d'une tuile : marche au bord, marche interieure de
    reference et rapport, a trois echelles. `ratio` = le pire des trois.

    Ne remplace pas `pixel_ops.seam_score` (garde tel quel, et republie ici
    comme `edge`) : il le complete par ce que la correction ne peut pas
    fabriquer."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    scales = []
    worst = 0.0
    for n in SEAM_SCALES:
        if w < 4 * n or h < 4 * n:
            continue
        step = (_diff100(_band_v(rgb, w - n, w), _band_v(rgb, 0, n))
                + _diff100(_band_h(rgb, h - n, h), _band_h(rgb, 0, n))) / 2.0
        vals = []
        for k in range(1, samples + 1):
            x = int(k * (w - 2 * n) / (samples + 1)) + n
            vals.append(_diff100(_band_v(rgb, x - n, x), _band_v(rgb, x, x + n)))
            y = int(k * (h - 2 * n) / (samples + 1)) + n
            vals.append(_diff100(_band_h(rgb, y - n, y), _band_h(rgb, y, y + n)))
        vals.sort()
        inner = vals[len(vals) // 2] or 1e-6
        ratio = step / inner
        worst = max(worst, ratio)
        scales.append({"px": n, "step": round(step, 2),
                       "inner": round(inner, 2), "ratio": round(ratio, 2)})
    worst = round(worst, 2)
    return {"ratio": worst, "grade": seam_grade(worst), "scales": scales}


def resize_maps(maps: dict[str, Image.Image], res: int) -> dict[str, Image.Image]:
    """Ramene toutes les maps a res x res. LANCZOS pour ce qui est vu
    (basecolor, emissive), BICUBIC pour les maps de donnees — LANCZOS y cree
    des halos (overshoot) qui se voient dans le relief. La normale est
    renormalisee apres coup : un redimensionnement casse la longueur unite."""
    res = max(1, int(res))
    out: dict[str, Image.Image] = {}
    for kind, img in maps.items():
        if img.size == (res, res):
            out[kind] = img
            continue
        flt = (Image.LANCZOS if kind in ("basecolor", "emissive")
               else Image.BICUBIC)
        small = img.resize((res, res), flt)
        if kind == "normal":
            nx, ny, _ = small.convert("RGB").split()
            small = _renormalize(nx, ny)
        out[kind] = small
    return out
