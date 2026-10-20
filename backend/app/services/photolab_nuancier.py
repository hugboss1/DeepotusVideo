"""Nuancier du Photolab (t153, parité L3) : les groupes de nuances que l'écran garde entre deux sessions.

Le moteur 0.3.0 n'avait aucune commande de nuancier (l'amont gardait ses 40 nuances en dur dans l'interface) : la
liste est une donnée Deepotus (0.10 a une bibliothèque de nuances, qui ne sert ici qu'à lire / écrire les fichiers
.aco / .ase : importer, exporter, en bas de ce module), dans `<données>/photolab/nuancier.json`. Une nuance n'est qu'une couleur `#rrggbb` et un nom
facultatif ; choisir une nuance passe par `tools.setColors` (route /executer), jamais par ce fichier. Validation en
liste blanche STRICTE ; la copie JavaScript du défaut (frontend/photolab/js/mod-nuancier.js) est comparée par le banc
test_photolab_panneaux3.
"""
import json
import os
import re
import tempfile
from pathlib import Path

# Les 40 nuances de l'amont (photocraft ui-egui panels.rs, SWATCHES : 4 rangées de 10), en quatre groupes.
DEFAUT_GROUPES = (
    ("gris", ("#000000", "#1a1a1a", "#333333", "#4d4d4d", "#666666", "#808080", "#999999", "#b3b3b3", "#cccccc", "#ffffff")),
    ("pastels", ("#ec8080", "#f4b084", "#fae080", "#d6f080", "#96e896", "#80e8c8", "#80dcf0", "#80b0f4", "#a890f4", "#e890e8")),
    ("vives", ("#e62828", "#f5781e", "#fad21e", "#a0dc28", "#28c850", "#1ec8aa", "#1eaae6", "#2864e6", "#7846dc", "#d232b4")),
    ("foncees", ("#781414", "#823c0a", "#826e0a", "#507814", "#146428", "#0a645a", "#0a5078", "#143278", "#3c1e6e", "#6e145a")),
)
MAX_GROUPES = 40
MAX_NUANCES = 400            # par groupe
MAX_RECENTES = 12
MAX_NOM = 64
_HEX = re.compile(r"#[0-9a-f]{6}")
_ID_GROUPE = re.compile(r"(gris|pastels|vives|foncees|g-[0-9a-z]{1,12})")
_CLES_ETAT = {"version", "groupes", "recentes"}
_CLES_GROUPE = {"id", "nom", "couleurs"}
_CLES_NUANCE = {"hex", "nom"}


def etat_defaut() -> dict:
    """Groupes fournis : `nom` vide = nom traduit par l'écran (photolab.nuancier.groupe_<id>)."""
    return {"version": 1, "recentes": [],
            "groupes": [{"id": i, "nom": "", "couleurs": [{"hex": h, "nom": ""} for h in c]} for i, c in DEFAUT_GROUPES]}


def chemin() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "photolab" / "nuancier.json"


def _objet(v, cles, ou):
    if not isinstance(v, dict):
        raise ValueError(f"{ou} : objet attendu")
    inconnues = set(v) - cles
    if inconnues:
        raise ValueError(f"{ou} : clé(s) inconnue(s) : {', '.join(sorted(map(str, inconnues)))}")
    manquantes = cles - set(v)
    if manquantes:
        raise ValueError(f"{ou} : clé(s) manquante(s) : {', '.join(sorted(manquantes))}")


def _hex(v, ou):
    if not isinstance(v, str) or not _HEX.fullmatch(v):
        raise ValueError(f"{ou} : couleur « #rrggbb » (minuscules) attendue")


def _nom(v, ou, vide_admis):
    if not isinstance(v, str):
        raise ValueError(f"{ou} : texte attendu")
    n = v.strip()
    if (not n and not vide_admis) or len(n) > MAX_NOM or any(ord(c) < 32 for c in n):
        raise ValueError(f"{ou} : {0 if vide_admis else 1} à {MAX_NOM} caractères, sur une ligne")
    return n


def valider(obj) -> dict:
    """L'état tel quel (noms rendus sans espaces autour) s'il est admis ; sinon ValueError (message français)."""
    _objet(obj, _CLES_ETAT, "nuancier")
    if obj["version"] != 1 or isinstance(obj["version"], bool):
        raise ValueError("nuancier.version : 1 attendu")
    if not isinstance(obj["recentes"], list) or len(obj["recentes"]) > MAX_RECENTES:
        raise ValueError(f"nuancier.recentes : liste de {MAX_RECENTES} couleurs au plus")
    for i, h in enumerate(obj["recentes"]):
        _hex(h, f"nuancier.recentes[{i}]")
    if not isinstance(obj["groupes"], list) or len(obj["groupes"]) > MAX_GROUPES:
        raise ValueError(f"nuancier.groupes : liste de {MAX_GROUPES} groupes au plus")
    ids = set()
    for i, g in enumerate(obj["groupes"]):
        o = f"nuancier.groupes[{i}]"
        _objet(g, _CLES_GROUPE, o)
        if not isinstance(g["id"], str) or not _ID_GROUPE.fullmatch(g["id"]):
            raise ValueError(f"{o}.id : mal formé")
        if g["id"] in ids:
            raise ValueError(f"{o}.id : en double")
        ids.add(g["id"])
        # Un groupe fourni peut garder un nom vide (traduit par l'écran) ; un groupe créé porte un nom.
        g["nom"] = _nom(g["nom"], f"{o}.nom", vide_admis=not g["id"].startswith("g-"))
        if not isinstance(g["couleurs"], list) or len(g["couleurs"]) > MAX_NUANCES:
            raise ValueError(f"{o}.couleurs : liste de {MAX_NUANCES} nuances au plus")
        for j, n in enumerate(g["couleurs"]):
            on = f"{o}.couleurs[{j}]"
            _objet(n, _CLES_NUANCE, on)
            _hex(n["hex"], f"{on}.hex")
            n["nom"] = _nom(n["nom"], f"{on}.nom", vide_admis=True)
    return obj


def lire() -> dict:
    """L'état enregistré ; le défaut si le fichier manque, est illisible ou refusé (jamais d'exception)."""
    try:
        return valider(json.loads(chemin().read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, AttributeError):
        return etat_defaut()


def ecrire(obj) -> dict:
    """Valide puis écrit d'un seul tenant (fichier temporaire du même dossier puis os.replace)."""
    etat = valider(obj)
    f = chemin()
    f.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="nuancier-", suffix=".tmp", dir=f.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as h:
            json.dump(etat, h, ensure_ascii=False, indent=1)
        os.replace(tmp, f)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return etat


# ── t256 (M7 PR 2) : échanger le nuancier avec un fichier .aco / .ase ─────────────────────────────────────────────
# Le moteur 0.10 lit et écrit ces formats (swatches.import / swatches.export, octets en base64 : les chemins sont
# désactivés en automation). Sa bibliothèque n'est qu'un passage : remplie, lue, puis remise aux défauts d'usine
# (swatches.reset), d'un seul tenant (SessionMoteur.sequence : aucun appel ne s'intercale, aucune action n'enregistre).
# NOTRE nuancier reste la référence.
import re as _re                                                 # noqa: E402

FORMATS_ECHANGE = ("aco", "ase")
MODES_IMPORT = ("append", "replace")
MAX_OCTETS_FICHIER = 2_000_000
_B64 = _re.compile(r"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")
_HEX_MOTEUR = _re.compile(r"#[0-9a-fA-F]{6}")


def _nom_libre(v, defaut):
    n = " ".join(str(v if isinstance(v, str) else "").split())[:MAX_NOM]
    return n or defaut


def groupes_depuis_moteur(liste: dict, ids_pris=()) -> list[dict]:
    """swatches.list du moteur -> nos groupes {id g-n libre, nom, couleurs [{hex minuscules, nom}]} ; groupes vides
    et nuances illisibles écartés, bornes du nuancier appliquées (MAX_GROUPES, MAX_NUANCES, MAX_NOM)."""
    pris = set(ids_pris)
    sortie, n = [], 1
    for g in (liste or {}).get("groups") or []:
        couleurs = [{"hex": s["hex"].lower(), "nom": _nom_libre(s.get("name"), "")}
                    for s in (g.get("swatches") or []) if isinstance(s, dict) and isinstance(s.get("hex"), str)
                    and _HEX_MOTEUR.fullmatch(s["hex"])][:MAX_NUANCES]
        if not couleurs:
            continue
        while f"g-{n}" in pris:
            n += 1
        pris.add(f"g-{n}")
        sortie.append({"id": f"g-{n}", "nom": _nom_libre(g.get("name"), f"g-{n}"), "couleurs": couleurs})
        if len(sortie) >= MAX_GROUPES:
            break
    return sortie


def fusionner(etat: dict, groupes: list[dict], mode: str) -> dict:
    """`append` : les groupes importés à la suite (jusqu'à MAX_GROUPES) ; `replace` : ils remplacent les groupes
    (les couleurs récentes restent)."""
    garde = [] if mode == "replace" else list(etat["groupes"])
    return {**etat, "groupes": (garde + groupes)[:MAX_GROUPES]}


def _donnees(v) -> str:
    if not isinstance(v, str) or not v or len(v) > (MAX_OCTETS_FICHIER * 4) // 3 + 4 or not _B64.fullmatch(v):
        raise ValueError(f"nuancier : fichier attendu en base64 ({MAX_OCTETS_FICHIER} octets au plus)")
    return v


def importer(s, corps: dict) -> dict:
    """{"data": base64, "format"?: aco|ase, "mode"?: append|replace} -> le nuancier enregistré après import, plus
    {"importees": n} ; ValueError si la demande ou le fichier est illisible (message du moteur)."""
    if not isinstance(corps, dict) or set(corps) - {"data", "format", "mode"}:
        raise ValueError("nuancier : clés admises : data, format, mode")
    data = _donnees(corps.get("data"))
    fmt, mode = corps.get("format"), corps.get("mode", "append")
    if fmt is not None and fmt not in FORMATS_ECHANGE:
        raise ValueError("nuancier : format aco ou ase attendu")
    if mode not in MODES_IMPORT:
        raise ValueError("nuancier : mode append ou replace attendu")
    params = {"data": data, "mode": "replace", **({"format": fmt} if fmt else {})}

    def fn(appel, gen):
        ex = lambda c, p: appel("engine.execute", {"command": c, "params": p})
        try:
            ex("swatches.import", params)
            return ex("swatches.list", {})
        finally:
            ex("swatches.reset", {"append": False})
    liste, _ = s.sequence(fn)
    etat = lire()
    groupes = groupes_depuis_moteur(liste, [g["id"] for g in etat["groupes"]] if mode == "append" else ())
    if not groupes:
        raise ValueError("nuancier : le fichier ne contient aucune couleur lisible")
    nouveau = ecrire(fusionner(etat, groupes, mode))
    return {**nouveau, "importees": sum(len(g["couleurs"]) for g in groupes)}


def exporter(s, corps: dict) -> dict:
    """{"format": aco|ase, "groupes": [{nom, couleurs: [{hex, nom}]}]} (les groupes TELS QUE L'ÉCRAN LES NOMME : un
    groupe fourni porte un nom traduit) -> {"format", "data" base64, "count"}."""
    if not isinstance(corps, dict) or set(corps) - {"format", "groupes"}:
        raise ValueError("nuancier : clés admises : format, groupes")
    fmt = corps.get("format")
    if fmt not in FORMATS_ECHANGE:
        raise ValueError("nuancier : format aco ou ase attendu")
    groupes = corps.get("groupes")
    if not isinstance(groupes, list) or not 0 < len(groupes) <= MAX_GROUPES:
        raise ValueError(f"nuancier : 1 à {MAX_GROUPES} groupes attendus")
    propres = []
    for i, g in enumerate(groupes):
        o = f"nuancier.groupes[{i}]"
        _objet(g, {"nom", "couleurs"}, o)
        nom = _nom(g["nom"], f"{o}.nom", vide_admis=False)
        if not isinstance(g["couleurs"], list) or len(g["couleurs"]) > MAX_NUANCES:
            raise ValueError(f"{o}.couleurs : liste de {MAX_NUANCES} nuances au plus")
        cs = []
        for j, c in enumerate(g["couleurs"]):
            _objet(c, _CLES_NUANCE, f"{o}.couleurs[{j}]")
            _hex(c["hex"], f"{o}.couleurs[{j}].hex")
            cs.append({"hex": c["hex"], "nom": _nom(c["nom"], f"{o}.couleurs[{j}].nom", vide_admis=True)})
        propres.append({"nom": nom, "couleurs": cs})
    if not any(g["couleurs"] for g in propres):
        raise ValueError("nuancier : aucune couleur à exporter")

    def fn(appel, gen):
        ex = lambda c, p: appel("engine.execute", {"command": c, "params": p})
        try:
            for g in (ex("swatches.list", {}) or {}).get("groups") or []:
                ex("swatches.deleteGroup", {"group": g["name"]})
            for g in propres:
                if not g["couleurs"]:
                    continue
                nom = (ex("swatches.newGroup", {"name": g["nom"]}) or {}).get("group", g["nom"])
                for c in g["couleurs"]:
                    ex("swatches.add", {"color": c["hex"], "group": nom, **({"name": c["nom"]} if c["nom"] else {})})
            return ex("swatches.export", {"format": fmt})
        finally:
            ex("swatches.reset", {"append": False})
    r, _ = s.sequence(fn)
    r = r or {}
    if not isinstance(r.get("data"), str):
        raise ValueError("nuancier : le moteur n'a rendu aucun fichier")
    return {"format": fmt, "data": r["data"], "count": int(r.get("count") or 0)}
