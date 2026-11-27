# -*- coding: utf-8 -*-
"""t514 (RV4) et t496 (G6), 26/11/2026 — CONTRÔLES PURS et déterministes d'un script court (Reel, Short, TikTok).

Spec 2026-11-09-getripping-design.md (ligne « Script » : CHECKS) et 2026-11-13-reel-reference-design.md (§ 3.4, R8).
Aucun réseau, aucun fichier, aucun modèle : les mêmes entrées donnent toujours le même verdict.

Un script = une liste de LIGNES {texte, ecran?, role?} dites dans l'ordre ; la première est l'accroche, la dernière
l'appel. Les quatre contrôles du script court (G6) :
1. `accroche`   l'accroche se dit en `ACCROCHE_S` secondes au plus (débit `mots_par_minute`) ;
2. `une_idee`   une idée par ligne : au plus une phrase, au plus `MOTS_PAR_LIGNE` mots ;
3. `appel`      la dernière ligne est un appel à l'action (lexique FR/EN) ;
4. `ecran`      les mots à l'écran sont des mots DITS dans la même ligne (rien de neuf ni de contradictoire).
Et ceux du script sur recette (RV4) :
5. `verite`     chaque chiffre du script figure dans les chiffres publiables de la fiche d'offre, sinon il est marqué
                « valeur d'illustration » (R8) ;
6. `distance`   aucune suite de 12 mots de la source (`inspiration_garde`) ni de son empreinte ;
7. `interdits`  aucun mot interdit de l'espace.
`controle_md` met le verdict en Markdown pour `controle.md` du dossier de campagne.
"""
from __future__ import annotations

import re

from app.services import inspiration_garde as G

ACCROCHE_S = 3.0
MOTS_PAR_LIGNE = 12                   # competence-script-court.md : « une ligne de plus de 12 mots se coupe en deux »
MOTS_PAR_MINUTE = 150.0              # competence-script-court.md : 2,5 mots par seconde
APPELS = {
    "fr": ("commente", "commentez", "clique", "cliquez", "abonne", "abonnez", "écris", "écrivez", "écris-nous",
           "lien", "bio", "découvre", "découvrez", "essaie", "essayez", "télécharge", "téléchargez", "réserve",
           "réservez", "achète", "achetez", "profite", "profitez", "enregistre", "enregistrez", "partage", "partagez",
           "inscris", "inscrivez", "rejoins", "rejoignez", "message", "dm", "commande", "commandez"),
    "en": ("comment", "click", "tap", "follow", "subscribe", "link", "bio", "try", "download", "get", "grab", "buy",
           "book", "save", "share", "join", "dm", "message", "order", "sign", "shop", "claim", "start"),
}
_CHIFFRE = re.compile(r"(?<![\w])[-−]?\d+(?:[  .,]\d+)*(?:\s?(?:%|€|\$|x|×|k|K|M))?")
_PHRASE = re.compile(r"[.!?…]+(?=\s+\S)")


def mots(texte: str) -> list[str]:
    return G.mots(texte)


def duree_lue(texte: str, mots_par_minute: float = MOTS_PAR_MINUTE) -> float:
    """Secondes pour dire `texte` au débit donné."""
    n = len(mots(texte))
    return round(n * 60.0 / max(60.0, float(mots_par_minute or MOTS_PAR_MINUTE)), 2)


def lignes_de(script) -> list[dict]:
    """Un script en texte (une ligne par idée) ou en liste -> [{texte, ecran, role}] sans lignes vides."""
    if isinstance(script, str):
        brut = [{"texte": l} for l in script.splitlines()]
    else:
        brut = [x if isinstance(x, dict) else {"texte": str(x or "")} for x in script or []]
    out = []
    for x in brut:
        t = " ".join(str(x.get("texte") or "").split())
        if t:
            out.append({"texte": t, "ecran": " ".join(str(x.get("ecran") or "").split()), "role": str(x.get("role") or "")})
    return out


def chiffres(texte: str) -> list[str]:
    """Les nombres écrits dans un texte, normalisés (espaces fines et insécables retirées, virgule décimale -> point)."""
    out = []
    for m in _CHIFFRE.finditer(str(texte or "")):
        v = m.group(0).strip().replace(" ", "").replace(" ", "").replace(" ", "").replace("−", "-")
        v = re.sub(r"(\d),(\d)", r"\1.\2", v)
        if re.search(r"\d", v):
            out.append(v)
    return out


def _nombre(v: str) -> str:
    return re.sub(r"[^\d.]", "", v).rstrip(".")


def controler_script(script, *, mots_par_minute: float = MOTS_PAR_MINUTE, langue: str = "fr") -> dict:
    """Les quatre contrôles du script court. {ok, controles: {nom: {ok, detail}}, duree_s, lignes}."""
    L = lignes_de(script)
    c = {}
    if not L:
        vide = {"ok": False, "detail": "vide"}
        return {"ok": False, "controles": {k: dict(vide) for k in ("accroche", "une_idee", "appel", "ecran")},
                "duree_s": 0.0, "lignes": 0}
    d0 = duree_lue(L[0]["texte"], mots_par_minute)
    c["accroche"] = {"ok": d0 <= ACCROCHE_S, "detail": {"secondes": d0, "maxi": ACCROCHE_S}}
    trop = []
    for i, l in enumerate(L):
        n = len(mots(l["texte"]))
        phrases = len(_PHRASE.findall(l["texte"])) + 1
        if n > MOTS_PAR_LIGNE or phrases > 1:
            trop.append({"ligne": i + 1, "mots": n, "phrases": phrases})
    c["une_idee"] = {"ok": not trop, "detail": trop}
    lex = set(APPELS.get(langue, ()) + APPELS["fr" if langue == "en" else "en"])
    fin = set(mots(L[-1]["texte"]))
    c["appel"] = {"ok": bool(fin & {G.mots(x)[0] for x in lex if G.mots(x)}), "detail": {"ligne": len(L)}}
    ecarts = []
    for i, l in enumerate(L):
        if not l["ecran"]:
            continue
        neufs = [m for m in mots(l["ecran"]) if m not in set(mots(l["texte"]))]
        if neufs:
            ecarts.append({"ligne": i + 1, "mots": neufs[:8]})
    c["ecran"] = {"ok": not ecarts, "detail": ecarts}
    total = round(sum(duree_lue(l["texte"], mots_par_minute) for l in L), 1)
    return {"ok": all(x["ok"] for x in c.values()), "controles": c, "duree_s": total, "lignes": len(L)}


def controler_verite(script, chiffres_publiables: list) -> dict:
    """Chaque chiffre du script figure dans la fiche d'offre (valeur), sinon il doit être marqué « illustration »."""
    connus = {_nombre(v) for x in chiffres_publiables or [] for v in chiffres(str((x or {}).get("valeur") or ""))}
    fautes = []
    for i, l in enumerate(lignes_de(script)):
        for v in chiffres(l["texte"] + " " + l["ecran"]):
            if _nombre(v) and _nombre(v) not in connus:
                fautes.append({"ligne": i + 1, "chiffre": v})
    return {"ok": not fautes, "detail": fautes}


def controler_distance(script, source: str = "", empreinte: list | None = None) -> dict:
    """Aucune suite de 12 mots de la source (texte, ou son empreinte après la purge R4)."""
    from app.services import inspiration_recette as IR
    texte = "\n".join(l["texte"] + "\n" + l["ecran"] for l in lignes_de(script))
    g = G.juger(source, texte) if source else {"suite": 0, "proximite": 0, "extrait": "", "ok": True}
    dans = IR.suite_dans_empreinte(empreinte or [], texte)
    return {"ok": g["ok"] and not dans, "detail": {"suite": g["suite"], "proximite": g["proximite"],
                                                  "extrait": g["extrait"], "empreinte": dans}}


def controler_interdits(script, interdits: list) -> dict:
    from app.services.marketing import apply_forbidden
    texte = " ".join(l["texte"] + " " + l["ecran"] for l in lignes_de(script))
    trouves = sorted(set(apply_forbidden([{"caption": texte}], list(interdits or []))[1])) if interdits else []
    return {"ok": not trouves, "detail": trouves}


_NOMS = {"fr": {"accroche": "Accroche en 3 s", "une_idee": "Une idée par ligne", "appel": "Fin sur un appel",
                "ecran": "Mêmes mots à l'écran", "verite": "Chiffres réels et sourcés", "distance": "Distance à la source",
                "interdits": "Mots interdits"},
         "en": {"accroche": "Hook within 3 s", "une_idee": "One idea per line", "appel": "Ends on a call to action",
                "ecran": "Same words on screen", "verite": "Real, sourced figures", "distance": "Distance from the source",
                "interdits": "Forbidden words"}}


def controle_md(resultat: dict, langue: str = "fr", titre: str = "") -> str:
    """Le verdict en Markdown (controle.md du dossier de campagne)."""
    noms = _NOMS.get(langue, _NOMS["fr"])
    oui, non = ("conforme", "à revoir") if langue != "en" else ("pass", "to fix")
    lignes = [f"# {titre or ('Contrôle du script' if langue != 'en' else 'Script check')}", ""]
    for k, v in (resultat.get("controles") or {}).items():
        lignes.append(f"- **{noms.get(k, k)}** : {oui if v.get('ok') else non}"
                      + ("" if v.get("ok") or not v.get("detail") else f" — `{v['detail']}`"))
    if "duree_s" in resultat:
        lignes += ["", (f"Durée lue estimée : {resultat['duree_s']} s" if langue != "en"
                        else f"Estimated read time: {resultat['duree_s']} s")]
    return "\n".join(lignes) + "\n"
