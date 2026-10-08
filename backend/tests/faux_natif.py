"""FAUX `photocraft.exe --control` pour les bancs du repli natif (t140) : même protocole que le vrai (relevé dans
apps/photocraft/src/main.rs et control_server.rs, tag v0.3.0) — serveur JSON lignes sur 127.0.0.1:<port>, jeton de
64 hex lu dans --control-token-file (créé s'il manque), 1re ligne {"method":"auth","params":{"token":…}} sinon la
connexion est refusée, puis app.open / app.save (chemins RELATIFS aux racines d'automatisation), ui.focus, app.quit.
Banc : chaque requête est journalisée (une ligne JSON) dans <racine d'écriture>/natif/.journal-faux ; `dz.pid` rend le
pid ; `dz.casse` fait échouer la prochaine requête."""
import json, os, secrets, socket, sys

args = sys.argv[1:]


def opt(n):
    return args[args.index(n) + 1] if n in args else None


port = int(opt("--control") or 0)
jeton_f = opt("--control-token-file")
lecture, ecriture = opt("--automation-read-root") or ".", opt("--automation-write-root") or "."
if jeton_f and os.path.isfile(jeton_f):
    jeton = open(jeton_f, encoding="utf-8").read().strip().lower()
else:
    jeton = secrets.token_hex(32)
    if jeton_f:
        open(jeton_f, "w", encoding="utf-8").write(jeton)
journal = os.path.join(ecriture, "natif", ".journal-faux")
os.makedirs(os.path.dirname(journal), exist_ok=True)


def noter(d):
    with open(journal, "a", encoding="utf-8") as f:
        f.write(json.dumps(d) + "\n")


noter({"demarrage": True, "pid": os.getpid(), "args": args})


def sous(racine, rel):
    if not isinstance(rel, str) or os.path.isabs(rel) or ".." in rel.replace("\\", "/").split("/") or ":" in rel:
        return None
    return os.path.join(racine, rel)


srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", port))
srv.listen(4)
casse = False
while True:
    c, _ = srv.accept()
    f = c.makefile("rwb")
    auth = False
    for brut in f:
        try:
            req = json.loads(brut.decode("utf-8"))
        except ValueError:
            break
        i, m, p = req.get("id"), req.get("method"), req.get("params") or {}
        noter({"method": m, "params": p, "auth": auth})
        if not auth:
            auth = m == "auth" and p.get("token") == jeton
            rep = {"id": i, "ok": True, "result": {"authenticated": True}} if auth else {"id": i, "ok": False, "error": "authentication required"}
            f.write((json.dumps(rep) + "\n").encode()); f.flush()
            if not auth:
                break
            continue
        if casse:
            casse = False
            rep = {"id": i, "ok": False, "error": "panne simulée"}
        elif m == "app.open":
            chemin = sous(lecture, p.get("path"))
            rep = ({"id": i, "ok": True, "result": {"name": os.path.basename(chemin), "warnings": []}} if chemin and os.path.isfile(chemin)
                   else {"id": i, "ok": False, "error": f"cannot open {p.get('path')}"})
        elif m == "app.save":
            chemin = sous(ecriture, p.get("path"))
            if chemin:
                os.makedirs(os.path.dirname(chemin), exist_ok=True)
                open(chemin, "wb").write(b"FAUXNATIF")
                rep = {"id": i, "ok": True, "result": {"path": p.get("path"), "warnings": []}}
            else:
                rep = {"id": i, "ok": False, "error": "path outside the automation root"}
        elif m == "ui.focus":
            rep = {"id": i, "ok": True, "result": None}
        elif m == "dz.pid":
            rep = {"id": i, "ok": True, "result": os.getpid()}
        elif m == "dz.casse":
            casse = True
            rep = {"id": i, "ok": True, "result": None}
        elif m == "app.quit":
            f.write((json.dumps({"id": i, "ok": True, "result": None}) + "\n").encode()); f.flush()
            sys.exit(0)
        else:
            rep = {"id": i, "ok": False, "error": f"unknown method `{m}`"}
        f.write((json.dumps(rep) + "\n").encode()); f.flush()
    try:
        c.close()
    except OSError:
        pass
