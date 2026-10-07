"""FAUX photocraft-cli serve pour les bancs du Photolab (t136) : même protocole JSON lignes, aucun calcul.
Commandes de banc : dz.dormir (ne répond pas), dz.mourir (quitte), dz.erreur (ok:false), dz.bruit (ligne non JSON
avant la réponse), dz.desordre (une réponse à un AUTRE id avant la bonne). doc.render/doc.save écrivent un petit
fichier sous la racine d'écriture. Le pid est rendu par `dz.pid` (pour voir un redémarrage)."""
import json, os, sys, time

args = sys.argv[1:]
ecriture = args[args.index("--automation-write-root") + 1] if "--automation-write-root" in args else "."
docs = []


def repondre(i, ok, val):
    cle = "result" if ok else "error"
    sys.stdout.write(json.dumps({"id": i, "ok": ok, cle: val}) + "\n")
    sys.stdout.flush()


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
        else:
            repondre(i, True, {"command": c, "params": p.get("params")})
    elif m == "doc.new":
        docs.append(p)
        repondre(i, True, {"document": len(docs) - 1})
    elif m == "doc.open":
        docs.append({"path": p.get("path")})
        repondre(i, True, {"document": len(docs) - 1, "path": p.get("path")})
    elif m == "doc.inspect":
        repondre(i, True, {"documents": docs})
    elif m in ("doc.render", "doc.save"):
        chemin = p.get("path") or "rendus/sans_nom.png"
        os.makedirs(os.path.dirname(os.path.join(ecriture, chemin)), exist_ok=True)
        with open(os.path.join(ecriture, chemin), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nFAUX")
        repondre(i, True, {"path": chemin, "bytes": 12})
    elif m == "engine.commands":
        repondre(i, True, [{"id": "filter.blur.gaussianBlur", "label": "Gaussian Blur…", "menu": ["Filter", "Blur"],
                            "shortcut": None, "params": "{radius}", "enabled": bool(docs)}])
    else:
        repondre(i, False, f"unknown method `{m}` (try `methods`)")
