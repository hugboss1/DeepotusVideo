"""FAUX photocraft-cli serve pour les bancs du Photolab (t136) : même protocole JSON lignes, aucun calcul.
Commandes de banc : dz.dormir (ne répond pas), dz.mourir (quitte), dz.erreur (ok:false), dz.bruit (ligne non JSON
avant la réponse), dz.desordre (une réponse à un AUTRE id avant la bonne). doc.render/doc.save écrivent un petit
fichier sous la racine d'écriture. Le pid est rendu par `dz.pid` (pour voir un redémarrage).

t137 (Photolab P2, écran) : le faux porte aussi un petit ÉTAT de documents — calques, révision, historique, document
actif — pour les routes session / historique / vignettes. `dz.compte` (via engine.execute) rend les compteurs et le
journal des appels (dans l'ordre) ; `dz.modifier` incrémente la révision du document actif ; `dz.casseRendu` fait
échouer le prochain rendu de vignette (pour éprouver la fermeture de la copie)."""
import json, os, sys, time

args = sys.argv[1:]
ecriture = args[args.index("--automation-write-root") + 1] if "--automation-write-root" in args else "."
docs = []                        # les paramètres d'ouverture (forme historique : doc.inspect rend {"documents": docs})
etats = []                       # un état par document : nom, calques, révision, historique
actif = None
journal = []                     # « méthode » ou « engine.execute:commande », dans l'ordre d'arrivée
compte = {"duplicate": 0, "batches": [], "selections": []}
# t138 : `etape` = la prochaine commande d'aperçu (filtre, réglage, style) répond ok:false, pour éprouver la fermeture
# de la copie quand le MOTEUR refuse une étape que le pont avait admise.
casse = {"rendu": False, "sans_index": False, "etape": False}
FAMILLES_ETAPE = ("filter.", "image.adjustments.", "layer.layerStyle.", "layer.setAdjustment")
_ids = [100]


def repondre(i, ok, val):
    cle = "result" if ok else "error"
    sys.stdout.write(json.dumps({"id": i, "ok": ok, cle: val}) + "\n")
    sys.stdout.flush()


def calques_neufs():
    return [{"id": 1, "name": "Fond", "kind": "Pixel", "visible": True},
            {"id": 2, "name": "Calque 1", "kind": "Pixel", "visible": True},
            {"id": 3, "name": "Groupe", "kind": "Group", "visible": True, "expanded": True,
             "children": [{"id": 4, "name": "Dans le groupe", "kind": "Pixel", "visible": True},
                          # t138 : un réglage Niveaux DANS le groupe (le kind se trouve en descendant dans children)
                          {"id": 6, "name": "Levels 1", "kind": "Adjustment", "visible": True,
                           "adjustment": {"Levels": {"master": {"gamma": 1.0}, "space": "Rgb"}}}]},
            # pas de vignette : rien à montrer seul. t138 : un Color Lookup avec sa LUT (élaguée par le pont) et son
            # kind, pour layer.setAdjustment
            {"id": 5, "name": "Réglage", "kind": "Adjustment", "visible": True,
             "adjustment": {"ColorLookup": {"lut": [0.5] * 300, "name": "Warm Filter", "size": 10, "tetrahedral": False,
                                            "dither": True}}}]


def a_plat(calques):
    for c in calques:
        yield c
        yield from a_plat(c.get("children") or [])


def reperer(calques, cid):
    for c in a_plat(calques):
        if c["id"] == cid:
            return c
    return None


def liste():
    return {"active": actif, "foreground": [0.0, 0.0, 0.0, 1.0], "background": [1.0, 1.0, 1.0, 1.0],
            "documents": [{"index": k, "name": e["name"], "revision": e["revision"]} for k, e in enumerate(etats)]}


def nouveau_doc(p, nom):
    global actif
    docs.append(p)
    etats.append({"name": nom, "calques": calques_neufs(), "revision": 1, "history": ["Open"], "rejouer": []})
    actif = len(etats) - 1
    return len(docs) - 1


def registre():
    """t138 : le VRAI registre de photocraft-cli 0.3.0 (copie tests/photocraft_commandes_0.3.0.json), pour que la
    liste blanche du pont soit éprouvée sur ce qu'elle verra, plus les commandes de banc dz.* (sans paramètres) :
    sans elles le pont refuserait « commande inconnue du moteur »."""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "photocraft_commandes_0.3.0.json"),
              encoding="utf-8") as f:
        reel = json.load(f)
    return reel + [{"id": d, "label": d, "menu": [], "shortcut": None, "params": "{}", "enabled": True} for d in BANC]


BANC = ("dz.dormir", "dz.mourir", "dz.erreur", "dz.bruit", "dz.desordre", "dz.pid", "dz.compte", "dz.modifier",
        "dz.casseRendu", "dz.dupliquerSansIndex", "dz.actif", "dz.echecEtape", "dz.reglage")


def inspecter():
    e = etats[actif]
    return {"documents": docs, "name": e["name"], "revision": e["revision"], "layers": e["calques"],
            "history": e["history"], "canUndo": len(e["history"]) > 1, "canRedo": bool(e["rejouer"]),
            "width": 64, "height": 32, "activeLayer": e.get("actif", 1)}


for ligne in sys.stdin:
    ligne = ligne.strip()
    if not ligne:
        continue
    try:
        req = json.loads(ligne)
    except ValueError:
        repondre(None, False, "bad JSON")
        continue
    i, m, p = req.get("id"), req.get("method"), req.get("params") or {}
    if m != "engine.execute" or p.get("command") != "dz.compte":
        journal.append(m if m != "engine.execute" else "engine.execute:" + str(p.get("command")))
    if m == "engine.execute":
        c = p.get("command")
        if c == "dz.dormir":
            time.sleep(30)
        elif c == "dz.mourir":
            sys.exit(3)
        elif c == "dz.erreur":
            repondre(i, False, "no active layer")
        elif c == "dz.bruit":
            sys.stdout.write("pas du JSON\n")
            repondre(i, True, {"ok": True})
        elif c == "dz.desordre":
            repondre(i + 1000, True, {"autre": True})
            repondre(i, True, {"bon": True})
        elif c == "dz.pid":
            repondre(i, True, {"pid": os.getpid()})
        elif c == "dz.compte":
            repondre(i, True, {"duplicate": compte["duplicate"], "batches": compte["batches"], "journal": journal,
                               "selections": compte["selections"]})
        elif c == "dz.modifier":
            etats[actif]["revision"] += 1
            etats[actif]["history"].append("Modifier")
            repondre(i, True, {"revision": etats[actif]["revision"]})
        elif c == "dz.actif":                             # banc : change le calque actif (appel direct, hors pont)
            etats[actif]["actif"] = (p.get("params") or {}).get("layer")
            repondre(i, True, {})
        elif c == "dz.reglage":                           # banc : pose l'`adjustment` d'un calque (le crée au sommet s'il manque)
            q = p.get("params") or {}
            cal = reperer(etats[actif]["calques"], q.get("layer"))
            if cal is None:
                cal = {"id": q.get("layer"), "name": f"Réglage {q.get('layer')}", "kind": "Adjustment", "visible": True}
                etats[actif]["calques"].append(cal)
            cal["adjustment"] = q.get("adjustment")
            repondre(i, True, {})
        elif c == "dz.casseRendu":
            casse["rendu"] = True
            repondre(i, True, {})
        elif c == "dz.dupliquerSansIndex":
            casse["sans_index"] = True
            repondre(i, True, {})
        elif c == "dz.echecEtape":
            casse["etape"] = True
            repondre(i, True, {})
        elif casse["etape"] and str(c).startswith(FAMILLES_ETAPE):
            casse["etape"] = False
            repondre(i, False, "filtre refusé (banc)")
        elif c == "layer.select":
            # t138 : le calque actif suit, et le banc lit le NOM choisi (preuve de l'appariement par position, les
            # ids de la copie étant renumérotés)
            cal = reperer(etats[actif]["calques"], p.get("params", {}).get("layer"))
            if cal is None:
                repondre(i, False, "no such layer")
            else:
                etats[actif]["actif"] = cal["id"]
                compte["selections"].append(cal["name"])
                repondre(i, True, {})
        elif c == "image.duplicate":
            compte["duplicate"] += 1
            src = etats[actif]
            neufs = json.loads(json.dumps(src["calques"]))
            for cal in a_plat(neufs):                     # le vrai moteur redonne des identifiants aux calques copiés
                _ids[0] += 1
                cal["id"] = _ids[0]
            docs.append({"copie": True})
            etats.append({"name": p.get("name"), "calques": neufs, "revision": 1, "history": ["Open"], "rejouer": []})
            actif = len(etats) - 1
            if casse["sans_index"]:                       # le moteur crée la copie mais ne dit pas son index
                casse["sans_index"] = False
                repondre(i, True, {})
            else:
                repondre(i, True, {"document": actif, "name": p.get("name")})
        elif c == "layer.setProps":
            cal = reperer(etats[actif]["calques"], p.get("params", {}).get("layer"))
            if cal is None:
                repondre(i, False, "no such layer")
            else:
                if "visible" in p["params"]:
                    cal["visible"] = bool(p["params"]["visible"])
                repondre(i, True, {"nomCalque": cal["name"]})        # t138 : le banc de l'aperçu lit le calque visé
        else:
            r = {"command": c, "params": p.get("params")}
            cible = (p.get("params") or {}).get("layer")
            if isinstance(cible, int) and actif is not None:
                # t138 : le nom du calque visé dans le document ACTIF, pour vérifier la traduction des ids vers la copie
                cal = reperer(etats[actif]["calques"], cible)
                r["nomCalque"] = cal["name"] if cal else None
            repondre(i, True, r)
    elif m == "doc.new":
        repondre(i, True, {"document": nouveau_doc(p, p.get("name") or "Untitled")})
    elif m == "doc.open":
        repondre(i, True, {"document": nouveau_doc({"path": p.get("path")}, "Ouvert"), "path": p.get("path")})
    elif m == "doc.inspect":
        repondre(i, True, inspecter() if actif is not None else {"documents": docs})
    elif m == "session.list":
        repondre(i, True, liste())
    elif m == "doc.select":
        k = p.get("index")
        if not isinstance(k, int) or not 0 <= k < len(etats):
            repondre(i, False, f"no document at index {k}")
        else:
            actif = k
            repondre(i, True, liste())
    elif m == "doc.close":
        k = p.get("index", actif)
        if not isinstance(k, int) or not 0 <= k < len(etats):
            repondre(i, False, f"no document at index {k}")
        else:
            del etats[k]
            del docs[k]
            actif = (min(k, len(etats) - 1) if etats else None) if actif == k else (actif - 1 if actif > k else actif)
            repondre(i, True, liste())
    elif m == "batch":
        pas = p.get("steps") or []
        compte["batches"].append(len(pas))
        ok_n = 0
        for st in pas:
            e = etats[actif]
            if st.get("command") == "edit.undo" and len(e["history"]) > 1:
                e["rejouer"].append(e["history"].pop())
                ok_n += 1
            elif st.get("command") == "edit.redo" and e["rejouer"]:
                e["history"].append(e["rejouer"].pop())
                ok_n += 1
            elif p.get("stopOnError"):
                break
        repondre(i, True, {"completed": ok_n, "failed": len(pas) - ok_n, "results": []})
    elif m in ("doc.render", "doc.save"):
        chemin = p.get("path") or "rendus/sans_nom.png"
        if m == "doc.render" and casse["rendu"] and chemin.startswith("rendus/vig-"):
            casse["rendu"] = False
            repondre(i, False, "render failed")
            continue
        if chemin.startswith("rendus/vig-"):
            time.sleep(0.08)                              # laisse à un appel concurrent le temps de se présenter
        os.makedirs(os.path.dirname(os.path.join(ecriture, chemin)), exist_ok=True)
        with open(os.path.join(ecriture, chemin), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nFAUX")
        repondre(i, True, {"path": chemin, "bytes": 12})
    elif m == "engine.commands":
        repondre(i, True, registre())
    else:
        repondre(i, False, f"unknown method `{m}` (try `methods`)")
