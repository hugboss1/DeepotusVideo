"""Fiches modèle (t475, lot F0 du plan « Fiches modèle », 09/11/2026).

Une fiche par FAMILLE de modèles (`docs/agent/modeles/<langue>/<famille>.md`) dit comment bien se servir de ses
membres : prompt, pièges, choix, coût. Les PARAMÈTRES (durées, formats, résolutions, prix, clé) n'y sont jamais
écrits : `fiche()` y ajoute un bloc « Membres » généré depuis `catalogue_ia`, si bien qu'un chiffre de registre
n'existe qu'une fois. Contrat d'écriture : `docs/agent/modeles/MODELES.md` ; banc : `tests/test_modeles_fiches.py`.

Gratuit, sans réseau : lit des fichiers du dépôt et les registres en mémoire.
"""
from __future__ import annotations

import re
from pathlib import Path

DOSSIER = Path(__file__).resolve().parents[3] / "docs" / "agent" / "modeles"
LANGUES = ("fr", "en")
COMMUN = "_commun"
TITRES = {"fr": ("Aperçu", "Référence rapide", "Exemple", "Erreurs fréquentes"),
          "en": ("Overview", "Quick reference", "Example", "Common mistakes")}
_MEMBRES = {"fr": "Membres", "en": "Members"}
# natures dont les entrées se complètent par la réponse de /api/video-models (durées, formats…)
_NATURES_VIDEO = ("video_i2v", "video_fl")


def _langue(langue: str) -> str:
    return langue if langue in LANGUES else "fr"


def lire_entete(texte: str) -> tuple[dict, str]:
    """Le front-matter (`clé: valeur`, listes `[a, b]`) et le corps. Pas de YAML : le format est volontairement
    réduit à ces deux formes, que le banc contrôle."""
    texte = texte.replace("\r\n", "\n")
    if not texte.startswith("---\n"):
        return {}, texte
    fin = texte.find("\n---\n", 4)
    if fin < 0:
        return {}, texte
    meta = {}
    for ligne in texte[4:fin].split("\n"):
        if not ligne.strip():
            continue
        cle, _, val = ligne.partition(":")
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            meta[cle.strip()] = [x.strip() for x in val[1:-1].split(",") if x.strip()]
        else:
            meta[cle.strip()] = val
    return meta, texte[fin + 5:].lstrip("\n")


def _fichiers(langue: str) -> list[Path]:
    d = DOSSIER / _langue(langue)
    return sorted(d.glob("*.md")) if d.is_dir() else []


def charger(langue: str = "fr") -> dict[str, dict]:
    """Toutes les fiches de familles d'une langue (sans le tronc commun) : famille -> {meta, corps, chemin}."""
    out = {}
    for p in _fichiers(langue):
        if p.stem == COMMUN:
            continue
        meta, corps = lire_entete(p.read_text(encoding="utf-8"))
        out[p.stem] = {"meta": meta, "corps": corps, "chemin": p}
    return out


def commun(langue: str = "fr") -> dict | None:
    p = DOSSIER / _langue(langue) / f"{COMMUN}.md"
    if not p.is_file():
        return None
    meta, corps = lire_entete(p.read_text(encoding="utf-8"))
    return {"meta": meta, "corps": corps, "chemin": p}


def index(langue: str = "fr") -> list[dict]:
    """La liste courte, toujours lisible : famille, description, natures, ids."""
    return [{"famille": f, "description": v["meta"].get("description", ""),
             "natures": v["meta"].get("natures") or [], "ids": v["meta"].get("ids") or []}
            for f, v in charger(langue).items()]


def famille_de(mid: str, langue: str = "fr") -> str | None:
    for f, v in charger(langue).items():
        if mid in (v["meta"].get("ids") or []):
            return f
    return None


def membres(meta: dict) -> list[dict]:
    """Les entrées de `catalogue_ia` des ids de la fiche, dans l'ordre du front-matter ; un id absent de ses natures
    n'apparaît pas (le banc le refuse en amont)."""
    from app.services import catalogue_ia as C
    ids = list(meta.get("ids") or [])
    vues: dict[str, dict] = {}
    for nature in meta.get("natures") or []:
        try:
            entrees = C.lister(nature)
        except KeyError:
            continue
        for e in entrees:
            if e.get("id") in ids:
                vues.setdefault(e["id"], dict(e, natures=[]))["natures"].append(nature)
    if any(n in _NATURES_VIDEO for n in meta.get("natures") or []):
        from app.services.fal_service import VIDEO_MODELS
        for m in C.modeles_video().get("models") or []:
            if m["id"] in vues:
                vues[m["id"]].update({k: m.get(k) for k in ("durations", "ratios", "resolutions", "end_image",
                                                             "seed", "usd_per_s")})
                r = VIDEO_MODELS.get(m["id"]) or {}
                # t477 (épreuve d'application F2) : le champ négatif et l'interrupteur de son, que l'app coupe
                # toujours ; sans interrupteur, le fournisseur décide de la piste livrée
                vues[m["id"]].update(negatif=bool(r.get("negatif")), son_coupe=bool(r.get("audio_param")),
                                     son_retire=bool(r.get("audio_force")))   # t483 : piste retirée au téléchargement
    return [vues[i] for i in ids if i in vues]


def _plage(v) -> str:
    if not v:
        return "—"
    if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v) and len(v) > 2:
        return f"{min(v)}–{max(v)}"
    return ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)


def _paliers(d) -> str:
    """t490 : « low $0.0064 · high $0.053 » — chaque palier (qualité, résolution) avec son prix au catalogue."""
    if not isinstance(d, dict) or not d:
        return "—"
    return " · ".join(f"{k} ${float(v):g}" if v else str(k) for k, v in d.items())


def bloc_membres(liste: list[dict], langue: str = "fr") -> str:
    """Le tableau « Membres » en markdown, NEUTRE de langue hors titres (ids, chiffres, unités codées)."""
    en = _langue(langue) == "en"
    video = any("durations" in m for m in liste)
    # t490 (F3) : les modèles d'image portent leurs capacités au catalogue (F6) — palier de qualité, résolution,
    # nombre de références, fond transparent, retouche : ce qui décide d'un choix, lu au catalogue, jamais recopié
    image = not video and any(m.get("sortie") in ("raster", "svg") for m in liste)
    # t491 (F4) : le son (voix, effets, musique) et la 3D disent aussi ce qui décide d'un choix, lu au catalogue
    natures = {n for m in liste for n in (m.get("natures") or [])}
    son = not video and not image and bool(natures & {"voix", "sfx_texte", "sfx_video", "musique"})
    trois_d = not video and not image and not son and "modele3d" in natures
    tete = ["id", "label", "route" if en else "voie", "price" if en else "prix", "key" if en else "clé"]
    if image:
        tete += ["quality" if en else "qualité", "res.", "refs" if en else "réf.", "transp.", "edit" if en else "retouche"]
    if video:
        tete += ["s", "ratios", "res.", "end" if en else "fin", "seed", "neg." if en else "nég.", "audio" if en else "son"]
    if son:
        tete += ["s", "prompt req." if en else "prompt requis", "lyrics" if en else "paroles",
                 "chars max" if en else "car. max",
                 "tags" if en else "balises"]
    if trois_d:
        tete += ["formats", "views" if en else "vues", "text" if en else "texte", "PBR", "T-pose",
                 "draft" if en else "brouillon"]
    lignes = ["## " + _MEMBRES[_langue(langue)], "", "| " + " | ".join(tete) + " |",
              "|" + "---|" * len(tete)]
    for m in liste:
        # sans prix : « prix à mesurer », jamais « gratuit » — sauf la voie LOCALE, gratuite pour de vrai (comme
        # DzModelesIA, t186)
        prix = f"${float(m.get('usd') or 0):g}/{m.get('unite') or ''}" if m.get("usd") else (
            ("free (local)" if en else "gratuit (local)") if m.get("voie") == "local" else
            ("price to be measured" if en else "prix à mesurer"))
        cle = (m.get("cle") or ("none" if en else "aucune")) + ("" if m.get("dispo") else (" (missing)" if en
                                                                                          else " (absente)"))
        if m.get("usd_paroles") is not None:     # t491 : Mureka, prix AVEC paroles
            prix += f" · {'lyrics' if en else 'paroles'} ${float(m['usd_paroles']):g}"
        cells = [m["id"], m.get("label") or "", m.get("voie") or "", prix, cle]
        if image:
            oui, non = ("yes", "no") if en else ("oui", "non")
            cells += [_paliers(m.get("qualites")), _paliers(m.get("resolutions")),
                      str(m.get("refs_max") if m.get("refs_max") is not None else "—"),
                      oui if m.get("transparent") else non,
                      ("SVG, no" if en else "SVG, non") if m.get("sortie") == "svg" else (oui if m.get("edit") else non)]
        if video:
            oui, non = ("yes", "no") if en else ("oui", "non")
            cells += [_plage(m.get("durations")), _plage(m.get("ratios")), _plage(m.get("resolutions")),
                      oui if m.get("end_image") else non, oui if m.get("seed") else non,
                      oui if m.get("negatif") else non,
                      ("off" if en else "coupé") if m.get("son_coupe")
                      else ("removed" if en else "retiré") if m.get("son_retire")
                      else ("no switch" if en else "sans interrupteur")]
        if son:
            oui, non = ("yes", "no") if en else ("oui", "non")
            d = m.get("duree") or m.get("video_s")
            cells += [("—" if not d else f"{d[0]:g}" if d[0] == d[-1] else f"{d[0]:g}–{d[-1]:g}"),
                      "—" if "prompt" not in m else (oui if m.get("prompt") else non),
                      "—" if "paroles" not in m else (oui if m.get("paroles") else non),
                      str(m.get("car_max")) if m.get("car_max") else "—",
                      "—" if "balises" not in m else (oui if m.get("balises") else non)]
        if trois_d:
            oui, non = ("yes", "no") if en else ("oui", "non")
            cells += [", ".join(m.get("formats") or []) or "—", str(m.get("vues") or 1),
                      oui if m.get("texte") else non,
                      ("opt-in" if en else "au choix") if m.get("pbr") == "reglage" else oui if m.get("pbr") else non,
                      oui if m.get("tpose") else non, oui if m.get("brouillon") else non]
        lignes.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    return "\n".join(lignes) + "\n"


def fiche(cle: str, langue: str = "fr") -> dict | None:
    """La fiche d'une famille, ou de la famille d'un id : corps + bloc « Membres » + tronc commun. None si inconnue."""
    langue = _langue(langue)
    fiches = charger(langue)
    if langue != "fr" and not fiches:
        langue, fiches = "fr", charger("fr")
    fam = cle if cle in fiches else famille_de(cle, langue)
    if fam is None:
        return None
    v = fiches[fam]
    liste = membres(v["meta"])
    c = commun(langue)
    texte = v["corps"].rstrip() + "\n\n" + bloc_membres(liste, langue)
    return {"famille": fam, "langue": langue, "description": v["meta"].get("description", ""),
            "natures": v["meta"].get("natures") or [], "ids": v["meta"].get("ids") or [],
            "releve": v["meta"].get("releve", ""), "source": v["meta"].get("source", ""),
            "corps": v["corps"], "membres": liste, "commun": c["corps"] if c else "", "texte": texte}


def mots(corps: str) -> int:
    """Le compte de mots d'un corps (hors blocs de code), celui que le banc borne."""
    sans_code = re.sub(r"```.*?```", " ", corps, flags=re.S)
    return len(re.findall(r"\S+", sans_code))


# ---- Règles du contrat (MODELES.md), partagées par le banc ----------------------------------------------------------
BUDGET_FICHE, BUDGET_COMMUN, DESCRIPTION_MAX = 1200, 700, 500
DEBUT_DESCRIPTION = {"fr": "À utiliser quand", "en": "Use when"}
_NOM_FAMILLE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# Un plafond de durée recopié dans un corps (« jusqu'à 15 s », « 4 à 12 secondes ») : il vit dans le registre.
CAPS_DUREE = re.compile(
    r"(?i)(?:jusqu['’]à|up to|max(?:imum)?\.?|entre|between)\s*\d+(?:[.,]\d+)?\s*(?:s|sec|secondes?|seconds?)\b"
    r"|\b\d+(?:[.,]\d+)?\s*(?:à|-|–|to)\s*\d+(?:[.,]\d+)?\s*(?:s|sec|secondes?|seconds?)\b")
# Un prix en dollars recopié dans un corps : il vit dans le registre (pricing) et le bloc « Membres » l'affiche.
PRIX = re.compile(r"\$\s?\d")
# Noms de modèles génératifs interdits dans les rôles métier et le TEXTE des méthodes (règle 3 de MODELES.md).
# « FLUX » en capitales seulement : « flux » est un mot français.
NOMS_MODELES = re.compile(
    r"\b(?i:seedance|kling|veo|nano ?banana|gpt[- ]?image|seedream|ideogram|hailuo|minimax|meshy|rodin|"
    r"tripo(?:sr)?|elevenlabs|lyria|wan ?\d|luma|runway|vidu|grok|recraft|hunyuan|trellis|pixverse|ltx|sora|"
    r"midjourney|mureka|ace-step|stable audio|qwen[- ]image|gemini omni)\b|\bFLUX\b|\bFlux[ .-]?\d")
_CHAMPS_TEXTE_METHODES = ("titre", "resume", "etapes", "controles", "pieges")   # pas `exemples` : les mots de
#                                                                                  l'utilisateur ; pas les données
ROLES = DOSSIER.parent / "metiers"
METHODES = Path(__file__).resolve().parents[1] / "knowledge" / "methodes.json"


def _lire_dossier(dossier: Path) -> dict[str, dict[str, tuple[dict, str]]]:
    out = {}
    for lg in LANGUES:
        d = dossier / lg
        out[lg] = {p.stem: lire_entete(p.read_text(encoding="utf-8"))
                   for p in (sorted(d.glob("*.md")) if d.is_dir() else [])}
    return out


def _verifier_fiche(lg: str, fam: str, meta: dict, corps: str) -> list[str]:
    pb, tag = [], f"{lg}/{fam}"
    if fam != COMMUN and not _NOM_FAMILLE.fullmatch(fam):
        pb.append(f"{tag}: nom de famille invalide")
    if meta.get("famille") != fam:
        pb.append(f"{tag}: « famille » diffère du nom de fichier")
    desc = meta.get("description", "")
    if not isinstance(desc, str) or not desc.startswith(DEBUT_DESCRIPTION[lg]):
        pb.append(f"{tag}: la description doit commencer par « {DEBUT_DESCRIPTION[lg]} »")
    elif len(desc) > DESCRIPTION_MAX:
        pb.append(f"{tag}: description de {len(desc)} caractères (> {DESCRIPTION_MAX})")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(meta.get("releve", ""))):
        pb.append(f"{tag}: « releve » absent ou mal daté")
    if not meta.get("source"):
        pb.append(f"{tag}: « source » absente")
    titres = re.findall(r"^## (.+?)\s*$", corps, re.M)
    if titres != list(TITRES[lg]):
        pb.append(f"{tag}: parties {titres} au lieu de {list(TITRES[lg])}")
    n, lim = mots(corps), (BUDGET_COMMUN if fam == COMMUN else BUDGET_FICHE)
    if n > lim:
        pb.append(f"{tag}: {n} mots (> {lim})")
    if fam == COMMUN:
        return pb
    for cle in ("ids", "natures", "voies"):
        if not isinstance(meta.get(cle), list) or not meta.get(cle):
            pb.append(f"{tag}: « {cle} » doit être une liste non vide")
    if PRIX.search(corps):
        pb.append(f"{tag}: prix recopié ({PRIX.search(corps).group(0)!r}) : il vit dans le registre")
    if any(n in _NATURES_VIDEO for n in meta.get("natures") or []) and CAPS_DUREE.search(corps):
        pb.append(f"{tag}: plafond de durée recopié ({CAPS_DUREE.search(corps).group(0)!r}) : il vit dans le registre")
    return pb


def verifier(dossier: Path | None = None) -> list[str]:
    """Les écarts au contrat des fiches d'un dossier (par défaut celui du dépôt) ; [] = conforme."""
    from app.services import catalogue_ia as C
    toutes = _lire_dossier(dossier or DOSSIER)
    pb = []
    for lg in LANGUES:
        if COMMUN not in toutes[lg]:
            pb.append(f"{lg}/{COMMUN}.md absent")
        for fam, (meta, corps) in toutes[lg].items():
            pb += _verifier_fiche(lg, fam, meta, corps)
    fr, en = toutes["fr"], toutes["en"]
    for fam in sorted(set(fr) ^ set(en)):
        pb.append(f"parité : {fam} existe en {'fr' if fam in fr else 'en'} seulement")
    for fam in sorted((set(fr) & set(en)) - {COMMUN}):
        for cle in ("ids", "natures", "voies"):
            if fr[fam][0].get(cle) != en[fam][0].get(cle):
                pb.append(f"parité : « {cle} » de {fam} diffère entre fr et en")
    connues = set(C.natures())
    proprietaire: dict[str, str] = {}
    couvertes: set[str] = set()
    for fam, (meta, _) in fr.items():
        if fam == COMMUN:
            continue
        natures = meta.get("natures") if isinstance(meta.get("natures"), list) else []
        for n in natures:
            if n not in connues:
                pb.append(f"fr/{fam}: nature inconnue « {n} »")
        natures = [n for n in natures if n in connues]
        couvertes.update(natures)
        servis = {e["id"] for n in natures for e in C.lister(n)}
        for i in meta.get("ids") or []:
            if i in proprietaire:
                pb.append(f"fr/{fam}: id « {i} » déjà rangé dans {proprietaire[i]}")
            proprietaire.setdefault(i, fam)
            if i not in servis:
                pb.append(f"fr/{fam}: id « {i} » absent des natures {natures}")
    for n in sorted(couvertes):
        for e in C.lister(n):
            if e["id"] not in proprietaire:
                pb.append(f"couverture : « {e['id']} » ({n}) n'est rangé dans aucune fiche")
    return pb


def _textes(v) -> list[str]:
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for e in v for x in _textes(e)]
    if isinstance(v, dict):
        return [x for e in v.values() for x in _textes(e)]
    return []


def verifier_noms(roles: Path | None = None, methodes: Path | None = None) -> list[str]:
    """Règle 3 : aucun nom de modèle génératif dans les rôles métier ni dans le TEXTE des méthodes."""
    import json
    pb = []
    for p in sorted((roles or ROLES).glob("*.md")):
        for i, ligne in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            m = NOMS_MODELES.search(ligne)
            if m:
                pb.append(f"{p.name}:{i}: « {m.group(0)} »")
    data = json.loads((methodes or METHODES).read_text(encoding="utf-8"))
    for f in data.get("methodes") or []:
        for champ in _CHAMPS_TEXTE_METHODES:
            for t in _textes(f.get(champ)):
                m = NOMS_MODELES.search(t)
                if m:
                    pb.append(f"methodes.json {f.get('slug')}.{champ}: « {m.group(0)} »")
    return pb
