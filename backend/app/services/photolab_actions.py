# -*- coding: utf-8 -*-
"""t255 (Photolab M6, photocraft 0.10) — le panneau Actions : ce que le pont fait AUTOUR des actions.* du moteur.

Le moteur enregistre, rejoue et édite les actions lui-même (actions.record / play / insert…) ; le pont y ajoute
trois gardes et une mémoire :
- **lecture vérifiée en profondeur** : avant actions.play, chaque étape allumée (et celles des actions qu'elle appelle,
  directement ou par une Condition) passe la liste blanche du Photolab (photolab_registre.verifier_etape). Le moteur
  ne vérifie rien de ce qu'on insère (relevé du 20/10) : sans cela, Insérer puis Jouer ferait jouer au moteur ce que
  /executer refuse (file.saveAs, prefs.*, commande 0.10 fermée…).
- **étapes éteintes** : à la fin d'un enregistrement et à l'import d'un .atn, les étapes que le pont refuse sont
  éteintes (actions.toggle) et l'écran le dit ; on ne peut pas les rallumer.
- **séquences internes hors enregistrement** : SessionMoteur.sequence suspend l'enregistrement (vignettes, aperçus…).
- **réserve** `<données>/photolab/actions.json` : le moteur `serve` ne garde rien entre deux démarrages ; la réserve
  est réécrite après chaque édition et rejouée dans un moteur neuf (record + stop d'une action vide, puis insert,
  toggle, dialog, setColor, assignSet). Forme propre (étapes [id, params]) : un .atn perdrait les étapes sans
  équivalent.
Traitement par lots (lot_une) : une image de la Bibliothèque copiée sous entrees/, ouverte, action jouée, enregistrée
sous exports/, refermée ; le document actif de l'utilisateur est rendu. file.automate.batch est refusé par le moteur
en automation (« ambient filesystem paths »)."""
import json
import os
import tempfile
import threading
from pathlib import Path

from app.services import photolab_moteur as PM
from app.services import photolab_registre as PR

VERSION = 1
MAX_ACTIONS = 500
MAX_ETAPES = 1000
MAX_OCTETS = 5_000_000
MAX_PROFONDEUR = 16                       # imbrication de actions.play admise par le moteur
CLES_ACTION = ("name", "set", "color", "steps", "disabled", "dialogs")
# Commandes après lesquelles la réserve est réécrite (le moteur a changé ses actions).
EDITIONS = frozenset({"actions.stop", "actions.delete", "actions.toggle", "actions.dialog", "actions.rename",
                      "actions.setColor", "actions.move", "actions.assignSet", "actions.insert", "actions.load"})
# Arrêt TEMPORAIRE posé à la fin d'un segment (lecture pas à pas) puis retiré dans la même séquence.
MARQUE_SEGMENT = "dz-photolab-segment"
_VERROU = threading.Lock()
_RESTAUREE = {"session": None, "gen": None}


def chemin() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "photolab" / "actions.json"


def vide() -> dict:
    return {"version": VERSION, "actions": []}


def _rangs(v, n) -> bool:
    return (isinstance(v, list) and all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < n for i in v)
            and v == sorted(set(v)))


def valider_action(a) -> dict:
    """Une action de la réserve (forme de actions.get), sinon ValueError."""
    if not isinstance(a, dict) or set(a) != set(CLES_ACTION):
        raise ValueError("réserve des actions illisible : clés d'une action")
    if not PR._nom_juste(a["name"]) or (a["set"] is not None and not PR._nom_juste(a["set"])):
        raise ValueError("réserve des actions illisible : nom d'une action ou d'un jeu")
    if a["color"] not in PR.COULEURS_ACTION:
        raise ValueError("réserve des actions illisible : couleur d'une action")
    st = a["steps"]
    if not isinstance(st, list) or len(st) > MAX_ETAPES or not all(
            isinstance(e, list) and len(e) == 2 and isinstance(e[0], str) and PM._ID_COMMANDE.fullmatch(e[0])
            and isinstance(e[1], dict) for e in st):
        raise ValueError("réserve des actions illisible : étapes d'une action")
    if not _rangs(a["disabled"], len(st)) or not _rangs(a["dialogs"], len(st)):
        raise ValueError("réserve des actions illisible : rangs d'étapes")
    return a


def valider(obj) -> dict:
    if not isinstance(obj, dict) or set(obj) != {"version", "actions"} or obj["version"] != VERSION \
            or isinstance(obj["version"], bool):
        raise ValueError("réserve des actions illisible : version")
    acts = obj["actions"]
    if not isinstance(acts, list) or len(acts) > MAX_ACTIONS:
        raise ValueError("réserve des actions illisible : liste des actions")
    for a in acts:
        valider_action(a)
    if len({a["name"] for a in acts}) != len(acts):
        raise ValueError("réserve des actions illisible : doublon")
    if len(json.dumps(obj, ensure_ascii=False).encode("utf-8")) > MAX_OCTETS:
        raise ValueError("réserve des actions illisible : taille")
    return obj


def lire() -> dict:
    """La réserve ; vide si le fichier manque, est illisible ou refusé (jamais d'exception)."""
    try:
        return valider(json.loads(chemin().read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, AttributeError):
        return vide()


def ecrire(obj) -> dict:
    """Valide puis écrit d'un seul tenant (fichier temporaire du même dossier puis os.replace)."""
    d = valider(obj)
    f = chemin()
    f.parent.mkdir(parents=True, exist_ok=True)
    with _VERROU:
        fd, tmp = tempfile.mkstemp(prefix="actions-", suffix=".tmp", dir=f.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as h:
                json.dump(d, h, ensure_ascii=False, indent=1)
            os.replace(tmp, f)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
    return d


def _ex(appel, cid, params=None):
    return appel("engine.execute", {"command": cid, "params": params or {}})


def _forme(g) -> dict:
    return {"name": g.get("name"), "set": g.get("set"), "color": g.get("color") or "",
            "steps": [[e[0], e[1] if isinstance(e[1], dict) else {}] for e in (g.get("steps") or [])],
            "disabled": sorted(set(g.get("disabled") or [])), "dialogs": sorted(set(g.get("dialogs") or []))}


def tout(appel) -> dict:
    """{"actions": [forme de actions.get…], "recording": nom|None} — le contenu complet du panneau."""
    lst = _ex(appel, "actions.list") or {}
    acts = [_forme(_ex(appel, "actions.get", {"action": i})) for i in range(len(lst.get("actions") or []))]
    return {"actions": acts, "recording": lst.get("recording")}


def _sauver(appel):
    """Réécrit la réserve depuis le moteur. Une action que la réserve ne sait pas garder (nom trop long venu d'un .atn,
    trop d'étapes) en est laissée hors ; une écriture impossible ne fait pas échouer la commande déjà jouée."""
    garder = []
    for a in tout(appel)["actions"]:
        try:
            garder.append(valider_action(a))
        except ValueError:
            continue
    try:
        ecrire({"version": VERSION, "actions": garder[:MAX_ACTIONS]})
    except (OSError, ValueError):
        pass


def sauver(s):
    return s.sequence(lambda appel, gen: _sauver(appel), pause_actions=False)


def restaurer(appel, donnees) -> int:
    """Rejoue la réserve dans le moteur : les actions absentes (par leur nom) sont recréées dans l'ordre. -> nombre."""
    presentes = {a.get("name") for a in (_ex(appel, "actions.list") or {}).get("actions") or []}
    a_faire = [a for a in donnees.get("actions") or [] if a["name"] not in presentes]
    creees = []
    for a in a_faire:                     # d'abord toutes les actions vides : une étape peut appeler la suivante
        try:
            _ex(appel, "actions.record", {"name": a["name"]})
            _ex(appel, "actions.stop")
            creees.append(a)
        except PM.MoteurErreur:
            continue
    for a in creees:
        n = a["name"]
        try:
            for cid, p in a["steps"]:
                _ex(appel, "actions.insert", {"action": n, "id": cid, "params": p})
            for i in a["disabled"]:
                _ex(appel, "actions.toggle", {"action": n, "step": i, "enabled": False})
            for i in a["dialogs"]:
                _ex(appel, "actions.dialog", {"action": n, "step": i, "enabled": True})
            if a["color"]:
                _ex(appel, "actions.setColor", {"action": n, "color": a["color"]})
            if a["set"] is not None:
                _ex(appel, "actions.assignSet", {"action": n, "set": a["set"]})
        except PM.MoteurErreur:
            try:
                _ex(appel, "actions.delete", {"action": n})       # jamais une action à moitié refaite
            except PM.MoteurErreur:
                pass
    return len(creees)


def assurer(appel, gen, s):
    """Une fois par démarrage du moteur : la réserve est rejouée avant la première commande d'action."""
    if _RESTAUREE["session"] is s and _RESTAUREE["gen"] == gen:
        return
    d = lire()
    if d["actions"]:
        restaurer(appel, d)
    _RESTAUREE.update({"session": s, "gen": gen})


def _kinds(appel) -> dict:
    """{id de calque: kind} des calques de réglage du document actif ({} sans document)."""
    try:
        insp = appel("doc.inspect") or {}
    except PM.MoteurErreur:
        return {}
    return {c.get("id"): PR.kind_de(c) for c in PM._a_plat(insp.get("layers")) if PR.kind_de(c)}


def refus_lecture(appel, reg, action, depuis=0) -> list:
    """Les étapes ALLUMÉES qu'une lecture de `action` (depuis l'étape `depuis`) ferait jouer et que le pont refuse,
    actions appelées comprises (Exécuter l'action, Condition) : [(nom de l'action, n° d'étape à partir de 1, raison)…]."""
    kinds = _kinds(appel)
    refus = []

    def visite(ref, debut, pile, racine):
        try:
            g = _ex(appel, "actions.get", {"action": ref})
        except PM.MoteurErreur:
            if racine:
                raise
            return                        # action appelée absente : le moteur s'arrêtera sur cette étape en le disant
        nom = g.get("name")
        if nom in pile or len(pile) >= MAX_PROFONDEUR:
            return                        # cycle ou trop profond : le moteur le refuse à la lecture
        eteintes = set(g.get("disabled") or [])
        for i, (cid, p) in enumerate(g.get("steps") or []):
            if i < debut or i in eteintes:
                continue
            p = p if isinstance(p, dict) else {}
            kind = kinds.get(p.get("layer")) if cid == "layer.setAdjustment" else None
            raison = PR.refus_etape(reg, cid, p, kind)
            if raison:
                refus.append((nom, i + 1, raison))
            elif cid == "actions.play":
                visite(p.get("action"), p.get("from", 0), pile + [nom], False)
            elif cid == "actions.conditional":
                for k in ("then", "else"):
                    if p.get(k):
                        visite(p[k], 0, pile + [nom], False)
    visite(action, depuis, [], True)
    return refus


def verifier_lecture(appel, reg, action, depuis=0):
    refus = refus_lecture(appel, reg, action, depuis)
    if refus:
        nom, n, raison = refus[0]
        raise ValueError(f"lecture refusée par le Photolab : « {nom} », étape {n} : {raison}")


def eteindre(appel, reg, noms=None) -> list:
    """Éteint les étapes allumées que le pont refuse, dans les actions `noms` (toutes sans nom) :
    [{"action", "step", "raison"}…]."""
    if noms is None:
        noms = [a.get("name") for a in (_ex(appel, "actions.list") or {}).get("actions") or []]
    kinds = _kinds(appel)
    faites = []
    for n in noms:
        g = _ex(appel, "actions.get", {"action": n})
        eteintes = set(g.get("disabled") or [])
        for i, (cid, p) in enumerate(g.get("steps") or []):
            if i in eteintes:
                continue
            p = p if isinstance(p, dict) else {}
            raison = PR.refus_etape(reg, cid, p, kinds.get(p.get("layer")) if cid == "layer.setAdjustment" else None)
            if raison:
                _ex(appel, "actions.toggle", {"action": n, "step": i, "enabled": False})
                faites.append({"action": n, "step": i, "raison": raison})
    return faites


def _segment(appel, params):
    """actions.play de `from` à `until` (exclu) : un Arrêt temporaire posé à `until`, la lecture, puis l'Arrêt retiré
    (toujours, sous le même verrou : jamais il ne reste dans l'action ni dans la réserve). -> résultat de actions.play,
    sans le `failed` de l'Arrêt temporaire."""
    a = params["action"]
    n = len((_ex(appel, "actions.get", {"action": a}) or {}).get("steps") or [])
    lecture = {"action": a, "from": params.get("from", 0)}
    if params["until"] >= n:
        return _ex(appel, "actions.play", lecture)
    if (_ex(appel, "actions.list") or {}).get("recording") is not None:
        raise ValueError("actions.play : lecture pas à pas impossible pendant un enregistrement")
    _ex(appel, "actions.insert", {"action": a, "id": "actions.stopMessage", "at": params["until"],
                                  "params": {"message": MARQUE_SEGMENT, "allowContinue": False}})
    try:
        r = _ex(appel, "actions.play", lecture) or {}
    finally:
        _ex(appel, "actions.delete", {"action": a, "step": params["until"]})
    f = r.get("failed") if isinstance(r, dict) else None
    if f and f.get("id") == "actions.stopMessage" and f.get("step") == params["until"]:
        r = {k: v for k, v in r.items() if k != "failed"}
    return r


def _remplacer(appel, params):
    """Modifier l'étape : la nouvelle est insérée à `at`, l'ancienne (poussée en at+1) retirée, ses options (éteinte,
    dialogue) reportées sur la nouvelle."""
    a, at = params["action"], params["at"]
    g = _ex(appel, "actions.get", {"action": a}) or {}
    if at >= len(g.get("steps") or []):
        raise ValueError(f"actions.insert : at : aucune étape {at} à remplacer")
    r = _ex(appel, "actions.insert", {k: v for k, v in params.items() if k != "replace"})
    _ex(appel, "actions.delete", {"action": a, "step": at + 1})
    if at in (g.get("disabled") or []):
        _ex(appel, "actions.toggle", {"action": a, "step": at, "enabled": False})
    if at in (g.get("dialogs") or []):
        _ex(appel, "actions.dialog", {"action": a, "step": at, "enabled": True})
    return r


def executer(s, reg, cid, params):
    """Une commande actions.* de l'écran -> (résultat du moteur [+ "eteintes"], génération). Liste blanche, réserve
    rejouée au premier appel d'un moteur neuf, lecture vérifiée en profondeur, étapes refusées éteintes, réserve
    réécrite après une édition — d'un seul tenant sous le verrou du moteur."""
    params = PR.verifier(reg, cid, params)

    def fn(appel, gen):
        assurer(appel, gen, s)
        if cid == "actions.play":
            verifier_lecture(appel, reg, params["action"], params.get("from", 0))
        if cid == "actions.conditional":
            for k in ("then", "else"):
                if params.get(k):
                    verifier_lecture(appel, reg, params[k], 0)
        if cid == "actions.toggle" and "step" in params and params.get("enabled") is not False:
            g = _ex(appel, "actions.get", {"action": params["action"]})
            st = g.get("steps") or []
            i = params["step"]
            if i < len(st) and (params.get("enabled") is True or i in (g.get("disabled") or [])):
                kind = _kinds(appel).get(st[i][1].get("layer")) if st[i][0] == "layer.setAdjustment" else None
                raison = PR.refus_etape(reg, st[i][0], st[i][1], kind)
                if raison:
                    raise ValueError(f"étape refusée par le Photolab, elle reste éteinte : {raison}")
        if cid == "actions.play" and "until" in params:
            r = _segment(appel, params)
        elif cid == "actions.insert" and params.get("replace") is True:
            r = _remplacer(appel, params)
        else:
            r = _ex(appel, cid, {k: v for k, v in params.items() if not (cid == "actions.insert" and k == "replace")})
        if cid == "actions.record":
            s.actions_gen = gen
        eteintes = []
        if cid == "actions.stop" and isinstance(r, dict) and r.get("action"):
            eteintes = eteindre(appel, reg, [r["action"]])
        elif cid == "actions.load" and isinstance(r, dict):
            eteintes = eteindre(appel, reg, list(r.get("actions") or []))
        elif cid == "actions.toggle":
            eteindre(appel, reg, [params["action"]])          # « tout basculer » ne rallume jamais une étape refusée
        if cid in EDITIONS:
            _sauver(appel)
        if eteintes and isinstance(r, dict):
            r = {**r, "eteintes": eteintes}
        return r
    return s.sequence(fn, pause_actions=False)


def dupliquer(s, reg, action, nom):
    """Dupliquer : une nouvelle action `nom` avec les étapes, options, couleur et jeu de `action` (copie du moteur à
    lui-même, aucune étape neuve) ; ses étapes refusées restent éteintes. -> (actions.get de la copie, génération)."""
    PR._ref_action("actions.get", "action", action)
    PR._nom_action("actions.record", "name", nom)

    def fn(appel, gen):
        assurer(appel, gen, s)
        g = _forme(_ex(appel, "actions.get", {"action": action}) or {})
        _ex(appel, "actions.record", {"name": nom})
        _ex(appel, "actions.stop")
        restaurer_dans = {**g, "name": nom}
        try:
            for cid, p in restaurer_dans["steps"]:
                _ex(appel, "actions.insert", {"action": nom, "id": cid, "params": p})
            for i in restaurer_dans["disabled"]:
                _ex(appel, "actions.toggle", {"action": nom, "step": i, "enabled": False})
            for i in restaurer_dans["dialogs"]:
                _ex(appel, "actions.dialog", {"action": nom, "step": i, "enabled": True})
            if restaurer_dans["color"]:
                _ex(appel, "actions.setColor", {"action": nom, "color": restaurer_dans["color"]})
            if restaurer_dans["set"] is not None:
                _ex(appel, "actions.assignSet", {"action": nom, "set": restaurer_dans["set"]})
        except PM.MoteurErreur:
            _ex(appel, "actions.delete", {"action": nom})
            raise
        eteindre(appel, reg, [nom])
        _sauver(appel)
        return _forme(_ex(appel, "actions.get", {"action": nom}) or {})
    return s.sequence(fn, pause_actions=False)


def lister(s):
    """Le contenu complet du panneau (tout), réserve rejouée si le moteur est neuf."""
    def fn(appel, gen):
        assurer(appel, gen, s)
        return tout(appel)
    return s.sequence(fn, pause_actions=False)


def lot_une(s, reg, action, chemin_entree, base, fmt, quality=None):
    """Traitement par lots, UNE image : `chemin_entree` (relatif au dossier du moteur) ouverte, `action` jouée (vérifiée
    en profondeur AVANT d'ouvrir quoi que ce soit), enregistrée sous exports/<base>.<fmt> ; les documents ouverts ou
    créés par le lot sont refermés et le document actif de l'utilisateur rendu. -> (nom sous exports/, génération)."""
    PR._ref_action("actions.play", "action", action)
    chemin_entree = PM.relatif(chemin_entree)

    def fn(appel, gen):
        assurer(appel, gen, s)
        verifier_lecture(appel, reg, action, 0)
        avant = appel("session.list") or {}
        n0 = len(avant.get("documents") or [])
        actif = avant.get("active")
        try:
            ouvert = appel("doc.open", {"path": chemin_entree}) or {}
            idx = ouvert.get("index", n0)
            r = _ex(appel, "actions.play", {"action": action}) or {}
            f = r.get("failed")
            if f:
                raise PM.MoteurErreur(f"« {action} », étape {int(f.get('step', 0)) + 1} ({f.get('id')}) : {f.get('error')}")
            appel("doc.select", {"index": idx})
            fichier = PM.nom_libre(PM.dossier_travail() / "exports", base, fmt)
            p = {"path": PM.relatif(f"exports/{fichier}"), "format": fmt}
            if quality is not None:
                p["quality"] = quality
            appel("doc.save", p)
            return fichier
        finally:
            apres = appel("session.list") or {}
            for i in range(len(apres.get("documents") or []) - 1, n0 - 1, -1):
                appel("doc.close", {"index": i})          # du dernier au premier : les rangs ne bougent pas
            if isinstance(actif, int) and not isinstance(actif, bool):
                appel("doc.select", {"index": actif})
    return s.sequence(fn)
