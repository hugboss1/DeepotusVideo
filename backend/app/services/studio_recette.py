# -*- coding: utf-8 -*-
"""Plan-studio T9 (tache #71 du suivi, PR A, 03/10/2026) — la RECETTE : un graphe du Studio fige, relancable avec
d'autres sources sans rouvrir le Studio.

Le compilateur vit dans le bundle : le serveur ne compile pas un graphe. Une recette est donc la COMPILATION FIGEE —
la requete de rendu exacte que le Studio envoie (slots, epingles et node_id compris : la capture se fait APRES la
preparation des epingles, decision de l'utilisateur) — plus ses TROUS, que le serveur derive lui-meme de la
compilation (rien du client n'est cru) : les images (depart et fin d'un Seedance, image d'un slot) et les textes
(prompt et voix off d'un Seedance, script d'un avatar, texte d'un slot). Un trou = une VALEUR d'origine ; une meme image
qui nourrit deux slots est un seul trou, rempli une fois, pose a tous ses chemins.

Lancer = recopier la compilation, poser les valeurs, et passer par la route de rendu EXISTANTE : memes gardes
(epingles verifiees, garde de cout, plafond mensuel) — un noeud epingle dont la requete ne bouge pas est reemploye
gratuitement, un noeud qui depend d'un trou change d'empreinte et se regenere. Le graphe enregistre avec le rendu est
celui de la recette, valeurs TIREES posees (« Rouvrir dans Studio » montre la verite).
"""
import copy
import json
from pathlib import Path

IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_TEXTE = 4900
# (source_kind, chemin dans le slot, nature, libelle)
CHAMPS = (
    ("seedance", ("seedance", "image_filename"), "image", "image de départ"),
    ("seedance", ("seedance", "image_filename_end"), "image", "image de fin"),
    ("seedance", ("seedance", "custom_prompt"), "texte", "prompt"),
    ("seedance", ("seedance", "voiceover_script"), "texte", "voix off"),
    ("heygen", ("heygen", "script"), "texte", "script de l'avatar"),
    ("upload", ("upload_filename",), "image", "image"),
    ("text", ("text",), "texte", "texte"),
)
_REGISTRE = Path(__file__).resolve().parent.parent / "assets" / "studio_nodes.json"


def _titres() -> dict:
    try:
        return {k: v.get("title", k) for k, v in json.loads(_REGISTRE.read_bytes().decode("utf-8"))["types"].items()}
    except (OSError, ValueError, KeyError):
        return {}


def _lire(d, chemin):
    for k in chemin:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _poser(d, chemin, v):
    for k in chemin[:-1]:
        d = d[k]
    d[chemin[-1]] = v


def _noeuds_de(graphe, valeur):
    """Les noeuds du graphe dont une prop vaut EXACTEMENT `valeur` (la ou le Studio l'a prise)."""
    out = []
    for n in (graphe or {}).get("nodes") or []:
        p = n.get("props") if isinstance(n, dict) else None
        if isinstance(p, dict) and any(isinstance(v, str) and v == valeur for v in p.values()):
            out.append(n)
    return out


def trous(slot_values: dict, graphe: dict | None = None) -> list:
    """Les trous d'une compilation, groupes par (nature, valeur d'origine), dans l'ordre des slots."""
    titres, par_cle, ordre = _titres(), {}, []
    for sn in sorted(slot_values or {}):
        sv = slot_values[sn] or {}
        for kind, chemin, nature, quoi in CHAMPS:
            if sv.get("source_kind") != kind:
                continue
            v = _lire(sv, chemin)
            if not isinstance(v, str) or not v.strip():
                continue
            if nature == "image" and kind == "upload" and not v.lower().endswith(IMAGES):
                continue                      # une video posee en slot n'est pas un trou (les rendus ne le sont pas)
            cle = (nature, v)
            if cle not in par_cle:
                ns = _noeuds_de(graphe, v)
                ou = ", ".join(f"{titres.get(n.get('type'), n.get('type'))} {n.get('id')}" for n in ns[:3])
                par_cle[cle] = {"id": f"t{len(ordre) + 1}", "nature": nature, "valeur": v,
                                "libelle": (ou + " — " if ou else "") + quoi, "chemins": []}
                ordre.append(cle)
            par_cle[cle]["chemins"].append([sn, *chemin])
    return [par_cle[c] for c in ordre]


def normaliser(capture, graphe) -> dict:
    """La recette enregistree, a partir de la capture du Studio. Leve ValueError avec une phrase si elle ne tient pas."""
    from app.models.schemas import TemplateRenderRequest
    if not isinstance(capture, dict):
        raise ValueError("La recette n'est pas un objet JSON.")
    corps = {k: capture.get(k) for k in ("template_id", "slot_values", "voice_mode", "template", "title", "voiceover")}
    if not isinstance(corps["template_id"], str) or not corps["template_id"].strip():
        raise ValueError("La recette n'a pas de template (« template_id »).")
    if not isinstance(corps["slot_values"], dict) or not corps["slot_values"]:
        raise ValueError("La recette n'a aucun slot : rien à rendre.")
    try:
        req = TemplateRenderRequest(**{k: v for k, v in corps.items() if v is not None})
    except Exception as e:                                         # pydantic : la phrase de la premiere erreur
        msg = getattr(e, "errors", lambda: [{"msg": str(e)}])()[0].get("msg", str(e))
        raise ValueError(f"La compilation figée n'est pas une requête de rendu valide : {msg}")
    # seules six cles entrent (pas de source_graph ni de max_usd : fixes au lancement) ; `preview` a un defaut, on l'ote
    figee = json.loads(req.model_dump_json(exclude_none=True, exclude={"preview"}))
    g = copy.deepcopy(graphe) if isinstance(graphe, dict) else {}
    g.pop("id", None)
    return {"v": 1, "requete": figee, "graphe": g, "trous": trous(figee.get("slot_values") or {}, g)}


def appliquer(recette: dict, valeurs: dict | None) -> tuple:
    """(requete a rendre, graphe aux valeurs tirees, valeurs retenues). Un trou absent de `valeurs` garde sa valeur
    d'origine ; un id de trou inconnu, une image qui n'est pas un nom de fichier image, un texte vide ou trop long :
    ValueError qui le nomme. L'existence des fichiers est verifiee par la route (elle connait les dossiers)."""
    valeurs = valeurs or {}
    if not isinstance(valeurs, dict):
        raise ValueError("« valeurs » doit être un objet {id du trou: valeur}.")
    ts = {t["id"]: t for t in recette.get("trous") or []}
    inconnus = sorted(set(valeurs) - set(ts))
    if inconnus:
        raise ValueError(f"Trou(s) inconnu(s) dans cette recette : {', '.join(inconnus)}.")
    req, g, retenues = copy.deepcopy(recette["requete"]), copy.deepcopy(recette.get("graphe") or {}), {}
    for tid, t in ts.items():
        v = valeurs.get(tid, t["valeur"])
        if not isinstance(v, str):
            raise ValueError(f"{t['libelle']} : une chaîne est attendue.")
        if t["nature"] == "image":
            v = v.strip()
            if v != Path(v).name or not v.lower().endswith(IMAGES):
                raise ValueError(f"{t['libelle']} : « {v} » n'est pas un nom de fichier image de la Bibliothèque.")
        elif not v.strip() or len(v) > MAX_TEXTE:
            raise ValueError(f"{t['libelle']} : le texte doit faire entre 1 et {MAX_TEXTE} caractères.")
        retenues[tid] = v
        for ch in t["chemins"]:
            _poser(req["slot_values"], ch, v)
        if v != t["valeur"]:
            for n in _noeuds_de(g, t["valeur"]):
                for k, pv in list(n["props"].items()):
                    if isinstance(pv, str) and pv == t["valeur"]:
                        n["props"][k] = v
    return req, g, retenues
