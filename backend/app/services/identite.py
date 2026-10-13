# -*- coding: utf-8 -*-
"""t206 (Espaces de marque E6, 13/10/2026) — l'IDENTITÉ VISUELLE d'un persona, dans `DATA_ROOT/espaces/<id>/identite/`.

Spec docs/superpowers/specs/2026-10-13-espaces-de-marque.md (D4). Le dossier porte `identite.json` et les images :
  - le logo (1), les références de la mascotte ou du personnage (1 à 6), les photos produit (12 au plus) — PNG
    normalisés par Pillow (qui vérifie que c'est une image), 2048 px au plus de côté ;
  - la palette (hex et rôles), les typographies, un STYLE ÉCRIT (descripteurs seulement : un nom d'artiste ou un « à la
    manière de » est REFUSÉ, doctrine du skill vitrail) ;
  - l'ADN des prompts : les touches que le moteur de prompt ajoute au sujet et au décor, le décor par défaut, les
    repères (mots qui disent que le persona est déjà dans le texte), les éclairages proposés. Un champ absent est
    DÉRIVÉ du persona (style écrit, palette, personnage) ; l'espace `deepotus` lit la graine livrée
    `app/espaces/deepotus_identite.json`, qui reprend le « DNA » autrefois codé en dur dans prompt_engine — ses prompts
    restent identiques à l'octet ;
  - la planche d'identité : composée par Pillow (GRATUIT, aucun tir), puis validée ; elle est « périmée » dès qu'une
    pièce qu'elle montre change ;
  - le kit des contenus de l'espace (`idv_<espace>`, D4) : couleurs et logo tirés de l'identité, sur demande.
Le logo d'un persona sert à SES contenus : il n'habille jamais l'application (décision du 13/10).
Les images de référence sont recopiées dans la Bibliothèque (`identite_<espace>_<nom>`) pour les modèles qui lisent
une image de la Bibliothèque (image→vidéo, avatar) ; la copie est refaite si elle a disparu (le dossier fait foi).
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from app.services import brand_kits, espaces

GRAINE_DEEPOTUS = Path(__file__).resolve().parent.parent / "espaces" / "deepotus_identite.json"
GENRES = {"logo": 1, "mascotte": 6, "produits": 12}
MAX_OCTETS = 8 * 1024 * 1024
COTE_MAX = 2048
MAX_PALETTE, MAX_TYPOS, MAX_STYLE = 12, 6, 600
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_NOM = re.compile(r"^(logo|mascotte|produits)-[0-9a-f]{8}\.png$")
ECLAIRAGES_GENERIQUES = ["soft natural window light", "golden hour rim light", "dark moody chiaroscuro"]
_ADN_LISTES = {"touches_sujet": 8, "touches_decor": 8, "reperes": 20, "eclairages": 8}
_ADN_TEXTES = {"decor_defaut": 200, "explication": 200}
VIDE = {"version": 1, "palette": [], "typographies": [], "style_ecrit": "", "adn": {}, "logo": None, "mascotte": [],
        "produits": [], "planche": None}

# La doctrine (skill vitrail) : jamais de nom d'artiste dans un style. Formules d'imitation + quelques noms qu'on
# colle souvent ; la liste du skill vitrail s'y ajoute quand elle est lisible.
_IMITATION = re.compile(r"(in the style of|\bstyle of\b|à la manière d|a la maniere d|dans le style d|inspired by|"
                        r"inspirée? (?:de|par)|\bfaçon [A-Z]|\bafter [A-Z][a-z]+ [A-Z])", re.IGNORECASE)
_NOMS = ("ghibli", "miyazaki", "van gogh", "picasso", "monet", "warhol", "banksy", "moebius", "mucha", "klimt", "dali",
         "dalí", "rutkowski", "pixar", "disney", "hokusai", "magritte", "basquiat", "frida kahlo", "wes anderson",
         "tim burton", "giger", "artgerm", "mondrian", "rembrandt", "vermeer", "caravaggio")


def _noms_interdits() -> list:
    noms = list(_NOMS)
    try:
        from app.services import style_vitrail
        noms += [n.lower() for n in style_vitrail.charger_fiche()["doctrine"]["artistes_jamais_dans_un_prompt"]]
    except Exception:  # noqa: BLE001 — la fiche vitrail absente ne bloque pas l'identité
        pass
    return noms


def nom_d_artiste(texte: str) -> str | None:
    """Le passage fautif (formule d'imitation ou nom d'artiste) d'un texte, ou None."""
    t = texte or ""
    m = _IMITATION.search(t)
    if m:
        return m.group(0)
    bas = t.lower()
    for n in _noms_interdits():
        if re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", bas):
            return n
    return None


# ---- lecture / écriture ----------------------------------------------------------------------------------------------

def _espace(eid) -> str:
    if not espaces.id_valide(eid) or eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    return eid


def dossier(eid: str) -> Path:
    return espaces.dossier() / _espace(eid) / "identite"


def _fichier(eid: str) -> Path:
    return dossier(eid) / "identite.json"


def _graine(eid: str) -> dict:
    if eid == "deepotus":
        try:
            return json.loads(GRAINE_DEEPOTUS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return json.loads(json.dumps(VIDE))


def lire(eid: str) -> dict:
    """identite.json de l'espace, complété des clés par défaut ; la graine (Deepotus) ou le vide s'il manque."""
    f = _fichier(eid)
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError
    except (OSError, ValueError):
        doc = _graine(eid)
    out = json.loads(json.dumps(VIDE))
    out.update({k: v for k, v in doc.items() if k in VIDE})
    return out


def _ecrire(eid: str, doc: dict) -> dict:
    f = _fichier(eid)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)
    return doc


def _texte(v, champ: str, n: int) -> str:
    if not isinstance(v, str):
        raise ValueError(f"{champ} doit être un texte")
    return v.strip()[:n]


def _sans_artiste(t: str, champ: str) -> str:
    fautif = nom_d_artiste(t)
    if fautif:
        raise ValueError(f"{champ} : pas de nom d'artiste ni de « à la manière de » (« {fautif} ») — décrivez le style "
                         "par descripteurs : palette, lumière, matière, cadrage, époque")
    return t


def _palette(v) -> list:
    if not isinstance(v, list) or len(v) > MAX_PALETTE:
        raise ValueError(f"palette : une liste de {MAX_PALETTE} couleurs au plus")
    out = []
    for i, c in enumerate(v):
        if not isinstance(c, dict) or not isinstance(c.get("hex"), str) or not _HEX.match(c["hex"].strip()):
            raise ValueError(f"palette n°{i + 1} : couleur #RRGGBB attendue")
        out.append({"hex": c["hex"].strip().upper(), "role": _texte(c.get("role", ""), "palette.role", 40)})
    return out


def _typos(v) -> list:
    if not isinstance(v, list) or len(v) > MAX_TYPOS:
        raise ValueError(f"typographies : {MAX_TYPOS} au plus")
    out = []
    for i, t in enumerate(v):
        if not isinstance(t, dict):
            raise ValueError(f"typographie n°{i + 1} invalide")
        nom = _texte(t.get("nom", ""), "typographies.nom", 60)
        if not nom:
            raise ValueError(f"typographie n°{i + 1} : nom manquant")
        out.append({"nom": nom, "usage": _texte(t.get("usage", ""), "typographies.usage", 40)})
    return out


def _adn(v) -> dict:
    if not isinstance(v, dict):
        raise ValueError("adn doit être un objet")
    out = {}
    for k, val in v.items():
        if k in _ADN_LISTES:
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                raise ValueError(f"adn.{k} doit être une liste de textes")
            out[k] = [_sans_artiste(x.strip()[:120], f"adn.{k}") for x in val if x.strip()][:_ADN_LISTES[k]]
        elif k in _ADN_TEXTES:
            out[k] = _sans_artiste(_texte(val, f"adn.{k}", _ADN_TEXTES[k]), f"adn.{k}")
        else:
            raise ValueError(f"adn.{k} : champ inconnu")
    return out


def ecrire(eid: str, champs) -> dict:
    """Remplace palette / typographies / style_ecrit / adn (ceux donnés). ValueError = rien d'écrit."""
    if not isinstance(champs, dict):
        raise ValueError("l'identité s'écrit en objet JSON")
    inconnus = set(champs) - {"palette", "typographies", "style_ecrit", "adn"}
    if inconnus:
        raise ValueError(f"champ inconnu : {', '.join(sorted(inconnus))}")
    doc = lire(eid)
    if "palette" in champs:
        doc["palette"] = _palette(champs["palette"])
    if "typographies" in champs:
        doc["typographies"] = _typos(champs["typographies"])
    if "style_ecrit" in champs:
        doc["style_ecrit"] = _sans_artiste(_texte(champs["style_ecrit"], "style_ecrit", MAX_STYLE), "style écrit")
    if "adn" in champs:
        doc["adn"] = _adn(champs["adn"])
    _ecrire(eid, doc)
    _suivre_kit(eid)
    return doc


# ---- les images ------------------------------------------------------------------------------------------------------

def _png(data: bytes) -> bytes:
    if len(data) > MAX_OCTETS:
        raise ValueError("image trop lourde (8 Mo au plus)")
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:  # noqa: BLE001 — Pillow décide
        raise ValueError(f"ce n'est pas une image lisible ({type(e).__name__})")
    img = img.convert("RGBA")
    img.thumbnail((COTE_MAX, COTE_MAX))
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def ajouter_image(eid: str, genre: str, data: bytes) -> str:
    """Range une image (le logo REMPLACE le précédent). ValueError = genre, plafond ou image refusés, rien d'écrit."""
    if genre not in GENRES:
        raise ValueError(f"genre inconnu : {genre} — connus : {', '.join(GENRES)}")
    doc = lire(eid)
    actuels = [doc["logo"]] if genre == "logo" and doc["logo"] else ([] if genre == "logo" else list(doc[genre]))
    if genre != "logo" and len(actuels) >= GENRES[genre]:
        raise ValueError(f"{genre} : {GENRES[genre]} images au plus — retirez-en une d'abord")
    png = _png(data)
    nom = f"{genre}-{uuid.uuid4().hex[:8]}.png"
    d = dossier(eid)
    d.mkdir(parents=True, exist_ok=True)
    (d / nom).write_bytes(png)
    if genre == "logo":
        for vieux in actuels:
            _effacer(eid, vieux)
        doc["logo"] = nom
    else:
        doc[genre] = actuels + [nom]
    _ecrire(eid, doc)
    publier(eid, nom)
    if genre == "logo":
        _suivre_kit(eid)
    return nom


def _effacer(eid: str, nom: str) -> None:
    (dossier(eid) / nom).unlink(missing_ok=True)
    from app.config import settings
    (Path(settings.images_path) / nom_bibliotheque(eid, nom)).unlink(missing_ok=True)


def retirer_image(eid: str, nom: str) -> bool:
    doc = lire(eid)
    logo = doc["logo"] == nom
    if logo:
        doc["logo"] = None
    elif nom in doc["mascotte"]:
        doc["mascotte"].remove(nom)
    elif nom in doc["produits"]:
        doc["produits"].remove(nom)
    else:
        return False
    _ecrire(eid, doc)
    _effacer(eid, nom)
    if logo:
        _suivre_kit(eid)
    return True


def chemin_image(eid: str, nom: str) -> Path | None:
    """Le fichier d'une image NOMMÉE dans identite.json (ou la planche), jamais un autre chemin."""
    doc = lire(eid)
    connus = set(doc["mascotte"]) | set(doc["produits"]) | ({doc["logo"]} if doc["logo"] else set())
    if (doc.get("planche") or {}).get("fichier"):
        connus.add(doc["planche"]["fichier"])
    if nom not in connus:
        return None
    p = dossier(eid) / nom
    return p if p.is_file() else None


def nom_bibliotheque(eid: str, nom: str) -> str:
    return f"identite_{eid}_{nom}"


def publier(eid: str, nom: str) -> str | None:
    """La copie de Bibliothèque d'une image d'identité (refaite si absente). Rend son nom, ou None."""
    from app.config import settings
    src = chemin_image(eid, nom)
    if src is None:
        return None
    dest = Path(settings.images_path) / nom_bibliotheque(eid, nom)
    if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    return dest.name


def references(eid: str, genres=("mascotte", "produits"), n: int = 9) -> list:
    """Les chemins des images de référence, dans l'ordre (mascotte d'abord), n au plus."""
    doc = lire(eid)
    out = []
    for g in genres:
        noms = [doc["logo"]] if g == "logo" and doc["logo"] else ([] if g == "logo" else doc[g])
        for nom in noms:
            p = chemin_image(eid, nom)
            if p is not None:
                out.append(p)
    return out[:max(0, n)]


def references_bibliotheque(eid: str, genres=("mascotte", "produits"), n: int = 3) -> list:
    """Les noms de Bibliothèque des références (copies refaites au besoin) — pour les routes qui lisent la Bibliothèque."""
    return [x for x in (publier(eid, p.name) for p in references(eid, genres, n)) if x]


def importer_bibliotheque(eid: str, genre: str, fichiers) -> list:
    """Range des images DÉJÀ dans la Bibliothèque (références de l'onboarding, par exemple)."""
    from app.config import settings
    if not isinstance(fichiers, list) or not all(isinstance(f, str) for f in fichiers):
        raise ValueError("fichiers : une liste de noms de la Bibliothèque")
    faits = []
    for f in fichiers:
        if not f or "/" in f or "\\" in f or f in (".", "..") or ".." in f:
            raise ValueError(f"nom de fichier invalide : {f}")
        p = Path(settings.images_path) / f
        if not p.is_file():
            raise ValueError(f"absent de la Bibliothèque : {f}")
        faits.append(ajouter_image(eid, genre, p.read_bytes()))
    return faits


# ---- l'ADN des prompts -----------------------------------------------------------------------------------------------

def _descripteurs(texte: str) -> list:
    return [s.strip() for s in re.split(r"[,;\n]", texte or "") if s.strip()]


def adn(eid=None) -> dict:
    """Ce que le moteur de prompt injecte pour l'espace (courant par défaut) : chaque champ de `adn` donné est pris tel
    quel, sinon dérivé du persona. Clés : touches_sujet, touches_decor, decor_defaut, reperes, eclairages, explication."""
    eid = espaces.resoudre(eid)
    doc = lire(eid)
    p = espaces.persona(eid)
    vis = p.get("visuel") or {}
    pers = vis.get("personnage") or {}
    nom = p.get("display_name") or eid
    desc = _descripteurs(doc["style_ecrit"] or vis.get("style_ecrit", "")) or list(p.get("vibe_keywords") or [])
    hexs = [c["hex"] for c in doc["palette"]][:3]
    reperes = [x.lower() for x in (nom, pers.get("nom", "")) if isinstance(x, str) and len(x.strip()) > 2]
    derive = {
        "touches_sujet": desc[:4],
        "touches_decor": ([f"with brand colors {' and '.join(hexs)}"] if hexs else []) + desc[4:6],
        "decor_defaut": "",
        "reperes": list(dict.fromkeys(r.strip() for r in reperes)),
        "eclairages": [],
        "explication": f"{nom} identity injected (persona descriptors)",
    }
    a = doc.get("adn") or {}
    out = {k: (a[k] if k in a else v) for k, v in derive.items()}
    out["eclairages"] = out["eclairages"] or list(ECLAIRAGES_GENERIQUES)
    return out


def a_le_persona(texte: str, reperes) -> bool:
    bas = (texte or "").lower()
    return any(r in bas for r in reperes if r)


# ---- la planche d'identité -------------------------------------------------------------------------------------------

def empreinte(eid: str) -> str:
    """Ce que la planche montre : palette, typographies, style écrit et le CONTENU des images."""
    doc = lire(eid)
    h = hashlib.sha256(json.dumps([doc["palette"], doc["typographies"], doc["style_ecrit"]], ensure_ascii=False,
                                  sort_keys=True).encode("utf-8"))
    for nom in ([doc["logo"]] if doc["logo"] else []) + doc["mascotte"] + doc["produits"]:
        p = dossier(eid) / nom
        h.update(nom.encode())
        h.update(p.read_bytes() if p.is_file() else b"-")
    return h.hexdigest()[:16]


def etat_planche(eid: str) -> str:
    """absente | a_valider | validee | perimee"""
    pl = lire(eid).get("planche") or {}
    if not pl.get("fichier") or not (dossier(eid) / pl["fichier"]).is_file():
        return "absente"
    if pl.get("empreinte") != empreinte(eid):
        return "perimee"
    return "validee" if pl.get("validee") else "a_valider"


POLICES = Path(__file__).resolve().parent.parent / "templates" / "_fonts"


def _police(t: int, nom: str = "Inter"):
    """Une police TrueType livrée (Inter par défaut : la police bitmap de Pillow n'a pas les accents) ; la typographie
    nommée par l'identité si elle est livrée (nom sans espaces, ex. « Space Grotesk » -> SpaceGrotesk.ttf)."""
    from PIL import ImageFont
    for n in (nom, "Inter"):
        for ext in (".ttf", ".otf"):
            f = POLICES / (re.sub(r"[^0-9A-Za-z]", "", n or "") + ext)
            if f.is_file():
                try:
                    return ImageFont.truetype(str(f), t)
                except OSError:
                    pass
    return ImageFont.load_default(size=t)


def _lignes(dr, texte: str, police, largeur: int) -> list:
    out, cour = [], ""
    for mot in texte.split():
        essai = (cour + " " + mot).strip()
        if dr.textlength(essai, font=police) <= largeur:
            cour = essai
        else:
            out.append(cour)
            cour = mot
    if cour:
        out.append(cour)
    return out


def composer_planche(eid: str) -> dict:
    """Compose la planche (PNG 1600×1000) avec Pillow — gratuit — et la pose « à valider »."""
    from PIL import Image, ImageDraw
    doc = lire(eid)
    nom = espaces.lire()["espaces"][eid].get("nom") or eid
    W, H = 1600, 1000
    img = Image.new("RGB", (W, H), "#14161c")
    dr = ImageDraw.Draw(img)
    dr.text((48, 30), nom, font=_police(52), fill="#f4f4f5")
    dr.text((48, 96), "Identité du persona", font=_police(24), fill="#a1a1aa")

    def coller(nom_img, x, y, cote):
        p = dossier(eid) / nom_img
        try:
            with Image.open(p) as im:
                im = im.convert("RGBA")
                im.thumbnail((cote, cote))
                fond = Image.new("RGB", (cote, cote), "#1f232b")
                fond.paste(im, ((cote - im.width) // 2, (cote - im.height) // 2), im)
                img.paste(fond, (x, y))
        except Exception:  # noqa: BLE001 — une image illisible laisse sa case vide
            dr.rectangle((x, y, x + cote, y + cote), outline="#3f3f46")

    if doc["logo"]:
        coller(doc["logo"], W - 48 - 160, 32, 160)
    y = 150
    for titre, noms in (("Personnage", doc["mascotte"]), ("Produits", doc["produits"][:6])):
        dr.text((48, y), titre, font=_police(22), fill="#e4e4e7")
        for i, n in enumerate(noms[:6]):
            coller(n, 48 + i * 170, y + 30, 160)
        if not noms:
            dr.text((48, y + 34), "—", font=_police(22), fill="#71717a")
        y += 220
    x0 = 1100
    dr.text((x0, 150), "Palette", font=_police(22), fill="#e4e4e7")
    for i, c in enumerate(doc["palette"][:8]):
        yy = 182 + i * 44
        dr.rectangle((x0, yy, x0 + 36, yy + 36), fill=c["hex"], outline="#3f3f46")
        dr.text((x0 + 48, yy + 6), f"{c['hex']}  {c['role']}", font=_police(20), fill="#d4d4d8")
    yy = 182 + max(1, min(8, len(doc["palette"]))) * 44 + 20
    dr.text((x0, yy), "Typographies", font=_police(22), fill="#e4e4e7")
    for i, t in enumerate(doc["typographies"][:6]):
        dr.text((x0, yy + 34 + i * 34), f"{t['nom']} — {t['usage']}".strip(" —"), font=_police(22, t["nom"]), fill="#d4d4d8")
    dr.text((48, 600), "Style écrit", font=_police(22), fill="#e4e4e7")
    for i, ligne in enumerate(_lignes(dr, doc["style_ecrit"] or "—", _police(20), 1000)[:12]):
        dr.text((48, 636 + i * 28), ligne, font=_police(20), fill="#d4d4d8")
    fichier = f"planche-{uuid.uuid4().hex[:8]}.png"
    d = dossier(eid)
    d.mkdir(parents=True, exist_ok=True)
    img.save(d / fichier, format="PNG")
    ancienne = (doc.get("planche") or {}).get("fichier")
    if ancienne and ancienne != fichier:
        (d / ancienne).unlink(missing_ok=True)
    doc["planche"] = {"fichier": fichier, "empreinte": empreinte(eid), "validee": False,
                      "faite_le": datetime.now().isoformat(timespec="seconds"), "validee_le": None}
    _ecrire(eid, doc)
    return doc["planche"]


def valider_planche(eid: str) -> dict:
    """ValueError si la planche manque ou ne montre plus l'identité actuelle (périmée : la recomposer)."""
    etat = etat_planche(eid)
    if etat == "absente":
        raise ValueError("aucune planche : composez-la d'abord")
    if etat == "perimee":
        raise ValueError("la planche est périmée (l'identité a changé depuis) : recomposez-la avant de la valider")
    doc = lire(eid)
    doc["planche"]["validee"] = True
    doc["planche"]["validee_le"] = datetime.now().isoformat(timespec="seconds")
    _ecrire(eid, doc)
    return doc["planche"]


def vue(eid: str) -> dict:
    """Ce que l'écran lit : l'identité, l'état de la planche, l'ADN effectif et le nom de chaque copie de Bibliothèque."""
    doc = lire(eid)
    doc["etat_planche"] = etat_planche(eid)
    doc["adn_effectif"] = adn(eid)
    doc["bibliotheque"] = {n: nom_bibliotheque(eid, n) for n in
                           ([doc["logo"]] if doc["logo"] else []) + doc["mascotte"] + doc["produits"]}
    doc["plafonds"] = dict(GENRES)
    k = espaces.kit_de_l_espace(eid)
    doc["kit"] = {"id": k["id"], "name": k.get("name"), "brand_color": k.get("brand_color"),
                  "accent_color": k.get("accent_color"), "logo": bool(k.get("logo")), "depuis_identite": k["id"] == kit_id(eid),
                  "branding": not (espaces.lire()["espaces"][eid].get("kit_id"))}
    return doc


# ---- le kit des CONTENUS de l'espace, tiré de l'identité (D4) ---------------------------------------------------------
# Un vrai kit de marque `idv_<espace>` (Réglages › Branding le liste) : couleur de marque = rôle « primaire », accent =
# rôle « accent » (sinon les deux premières couleurs), logo du persona, nom et accroches du PERSONA (jamais celles de
# Deepotus). Associé à l'espace pour SES contenus (kit_de_l_espace) ; il n'est JAMAIS activé (le logo et le nom de
# l'application ne suivent pas l'espace) et s'il habille l'application (activé à la main dans Branding), on n'y touche
# plus. Tant que l'espace l'utilise, il suit l'identité (palette, logo) à chaque enregistrement.

def kit_id(eid: str) -> str:
    return ("idv_" + eid)[:40]


def _hex_role(pal: list, *roles) -> str | None:
    for c in pal:
        if c.get("role", "").strip().lower() in roles:
            return c["hex"]
    return None


def _kit_champs(eid: str) -> dict:
    doc = lire(eid)
    p = espaces.persona(eid)
    e = espaces.lire()["espaces"][eid]
    nom_esp = e.get("nom") or eid
    nom = (p.get("display_name") or nom_esp).strip()
    pal = doc["palette"]
    marque = _hex_role(pal, "primaire", "primary", "principale", "principal", "marque", "brand") \
        or (pal[0]["hex"] if pal else e.get("couleur") or "#ef4444")
    autres = [c["hex"] for c in pal if c["hex"] != marque]
    accent = _hex_role(pal, "accent", "secondaire", "secondary") or (autres[0] if autres else marque)
    ec, idt = p.get("ecran") or {}, p.get("identite") or {}
    handle = (ec.get("handle") or "").strip()
    produits = [x for x in (idt.get("produits") or []) if isinstance(x, str) and x.strip()]
    return {"name": f"{nom_esp} (identité)", "app_name": nom, "app_sub": produits[0] if produits else nom,
            "tagline_1": (ec.get("catchphrase") or idt.get("mission") or nom).strip(),
            "tagline_2": (handle if handle not in ("", "@") else idt.get("url") or nom).strip(),
            "brand_color": marque, "accent_color": accent}


def kit_de_l_identite(eid: str) -> dict | None:
    """La vue du kit idv_<espace> s'il existe."""
    kid = kit_id(eid)
    return next((v for v in brand_kits.lister() if v["id"] == kid), None)


def synchroniser_kit(eid: str, associer: bool = False) -> dict:
    """Crée ou met à jour le kit idv_<espace> depuis l'identité ; `associer` en fait le kit des contenus de l'espace.
    ValueError si ce kit habille l'application (activé dans Réglages › Branding) : on ne touche pas à l'interface."""
    kid = kit_id(eid)
    if brand_kits.lire()["actif"] == kid:
        raise ValueError("ce kit habille l'application (Réglages › Identité visuelle) : activez-y un autre kit "
                         "d'abord — le logo et le nom de l'application ne suivent jamais un persona")
    brand_kits.enregistrer(dict(_kit_champs(eid), id=kid))
    dest = brand_kits.dossier() / "logos" / f"{kid}.png"
    doc = lire(eid)
    src = chemin_image(eid, doc["logo"]) if doc["logo"] else None
    if src is not None:
        shutil.copyfile(src, dest)
    else:
        dest.unlink(missing_ok=True)
    if associer:
        espaces.modifier(eid, {"kit_id": kid})
    return kit_de_l_identite(eid)


def _suivre_kit(eid: str) -> None:
    """Après une écriture de l'identité : le kit suit, si l'espace l'utilise encore et qu'il n'habille pas l'app."""
    kid = kit_id(eid)
    try:
        if (espaces.lire()["espaces"][eid].get("kit_id") == kid and kid in brand_kits.lire()["kits"]
                and brand_kits.lire()["actif"] != kid):
            synchroniser_kit(eid)
    except Exception as e:  # noqa: BLE001 — l'identité est écrite ; le kit se resynchronise au prochain geste
        from loguru import logger
        logger.warning(f"kit de l'identité {eid} : {e}")
