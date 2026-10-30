# -*- coding: utf-8 -*-
"""t378 (30/10/2026, lot « Réglages : chemins & apparence ») — Réglages › Chemins : les EMPLACEMENTS en plus
(dossier, lecteur réseau, UNC, SFTP). Banc SERVEUR (l'écran a son banc : test_emplacements_ecran.py).

Aucun réseau : le client SFTP est un FAUX `sftp.exe` (tests/_faux_sftp.py, posé par DZ_SFTP_EXE) qui joue le lot de
commandes sur un dossier local et EXIGE le mot de passe par SSH_ASKPASS comme OpenSSH.
  [V] validation : chemin absolu (lettre ou UNC complet), jamais dans ni au-dessus des dossiers de l'application ;
      SFTP : hôte, utilisateur sans option déguisée (« -o… »), port, dossier distant absolu sans retour à la ligne,
      guillemet ni barre inverse (il est écrit dans le lot sftp) ; rôles et types connus ;
  [C] créer / modifier / supprimer : fichier SANS secret ; mot de passe sous DZC_<ID>_SECRET (au .env sans coffre),
      jamais renvoyé (`secret_pose`) ; garder / effacer ; supprimé avec l'emplacement ; coffre fermé → 409 ; 20 au plus ;
  [T] « Tester » un dossier : témoin écrit, relu, EFFACÉ, espace libre, résultat gardé ; introuvable ; un emplacement
      « bibliothèque » seul n'est que LU ; `verifier` (Diagnostic) n'écrit jamais ;
  [S] SFTP : mot de passe par SSH_ASKPASS (jamais dans les arguments, le lot ni la sortie), BatchMode=no AVANT -b,
      aucune clé de l'application dans l'environnement de sftp.exe, hôtes connus dans les données, témoin put/get/rm,
      espace libre lu par df ; mauvais mot de passe, hôte introuvable, dossier distant absent : codes clairs ;
      clé SSH seule (-i, BatchMode non levé) ; client absent ;
  [R] routes /api/reglages/chemins : liste, création, brouillon, test, vérification, modification, suppression, 404,
      400, et refus (401/403) depuis un autre appareil ; recherche des Réglages ;
  [E] chaque message d'erreur neuf est traduit (scripts/i18n_l10_traductions.json, i18n_l10_erreurs.py --check).
Run (depuis backend/) : & $PY tests/test_emplacements.py"""
import ast, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzempl_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp / "donnees")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "donnees" / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "donnees" / "outputs")
os.environ["FAL_KEY"] = "fal-cle-du-banc-t378"
(_tmp / "donnees" / "images").mkdir(parents=True)
(_tmp / "donnees" / "outputs").mkdir(parents=True)
(_tmp / "donnees" / ".env").write_text("# banc\n", encoding="utf-8")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

# le faux sftp.exe : un .cmd qui relance ce Python sur tests/_faux_sftp.py
SERVEUR = _tmp / "serveur"
(SERVEUR / "sauvegardes").mkdir(parents=True)
JOURNAL = _tmp / "sftp.jsonl"
FAUX = _tmp / "faux_sftp.cmd"
FAUX.write_text(f'@"{sys.executable}" "{ICI / "_faux_sftp.py"}" %*\r\n', encoding="ascii")
os.environ.update({"DZ_SFTP_EXE": str(FAUX), "FAUX_SFTP_RACINE": str(SERVEUR), "FAUX_SFTP_JOURNAL": str(JOURNAL)})

from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import DATA_ROOT                                    # noqa: E402
from app.services import emplacements as E, coffre                  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def refuse(f, *a):
    try:
        f(*a)
    except ValueError as ex:
        return str(ex)
    return None


def appels():
    if not JOURNAL.exists():
        return []
    return [json.loads(l) for l in JOURNAL.read_text(encoding="utf-8").splitlines() if l.strip()]


c = TestClient(app)
cd = TestClient(app, client=("192.168.1.50", 5000))
NAS = _tmp / "nas"
NAS.mkdir()
(NAS / "deja.txt").write_text("là avant", encoding="utf-8")

# ══ [V] validation ═════════════════════════════════════════════════════════════════════════════════════════════
print("[V] validation")
check("V1 un dossier relatif est refusé", refuse(E.creer, {"type": "dossier", "chemin": "sauvegardes"}))
check("V2 un UNC incomplet est refusé", refuse(E.creer, {"type": "dossier", "chemin": "\\\\NAS"}))
check("V3 un UNC complet est accepté à la validation", E.verifier_dossier("\\\\NAS\\partage\\deepotus")
      == "\\\\NAS\\partage\\deepotus")
check("V4 jamais dans les données de l'application", refuse(E.creer, {"type": "dossier",
                                                                       "chemin": str(DATA_ROOT / "copie")}))
check("V5 jamais au-dessus des données de l'application", refuse(E.creer, {"type": "dossier",
                                                                            "chemin": str(_tmp)}))
check("V6 ni dans le dossier des sorties", refuse(E.creer, {"type": "dossier",
                                                            "chemin": str(_tmp / "donnees" / "outputs" / "x")}))
S0 = {"type": "sftp", "hote": "nas.local", "utilisateur": "olivia", "dossier_distant": "/sauvegardes"}
for nom, champs in [("hôte en option déguisée", {"hote": "-oProxyCommand=calc"}),
                    ("utilisateur en option", {"utilisateur": "-oProxyCommand=calc"}),
                    ("utilisateur avec @", {"utilisateur": "a@b"}),
                    ("utilisateur commençant par un tiret (option de ssh)", {"utilisateur": "-v"}),
                    ("port 0", {"port": 0}), ("port texte", {"port": "x"}),
                    ("dossier distant relatif", {"dossier_distant": "sauvegardes"}),
                    ("retour à la ligne (commande ajoutée)", {"dossier_distant": "/a\nrm x"}),
                    ("guillemet", {"dossier_distant": '/a" "b'}),
                    ("barre inverse", {"dossier_distant": "/a\\b"}),
                    ("clé SSH relative", {"cle_ssh": "id_ed25519"})]:
    check(f"V7 sftp : {nom} refusé", refuse(E.creer, {**S0, **champs}))
check("V8 type inconnu refusé", refuse(E.creer, {"type": "s3", "chemin": str(NAS)}))
check("V9 rôle inconnu refusé", refuse(E.creer, {"type": "dossier", "chemin": str(NAS), "roles": ["tout"]}))
check("V10 mot de passe sur un dossier refusé", refuse(E.creer, {"type": "dossier", "chemin": str(NAS),
                                                                  "secret": "x"}))
check("V11 rien n'a été écrit par les refus", not (DATA_ROOT / "emplacements.json").exists() and E.lister() == [])

# ══ [C] créer / modifier / supprimer ═══════════════════════════════════════════════════════════════════════════
print("[C] créer / modifier / supprimer")
MDP = "Mot de passe & ^ ! du NAS"
d = E.creer({"nom": "NAS du bureau", "type": "dossier", "chemin": str(NAS), "roles": ["miroir", "sauvegarde"]})
check("C1 dossier créé, rôles dans l'ordre canonique", d["id"] == "nasdubureau" and d["roles"] == ["sauvegarde", "miroir"]
      and d["adresse"] == str(NAS), d)
s = E.creer({**S0, "nom": "Serveur", "port": 2222, "roles": ["sauvegarde"], "secret": MDP})
FICHIER = (DATA_ROOT / "emplacements.json").read_text(encoding="utf-8")
ENVF = (DATA_ROOT / ".env").read_text(encoding="utf-8")
check("C2 SFTP créé ; adresse lisible", s["adresse"] == "sftp://olivia@nas.local:2222/sauvegardes", s["adresse"])
check("C3 le fichier n'a aucun secret", MDP not in FICHIER and "secret" not in FICHIER.lower())
check("C4 le mot de passe est rangé sous DZC_<ID>_SECRET (au .env : aucun coffre posé)",
      E.nom_secret(s["id"]) == "DZC_SERVEUR_SECRET" and "DZC_SERVEUR_SECRET=" in ENVF, ENVF)
check("C5 la vue dit secret_pose sans jamais rendre le secret", s["secret_pose"] is True
      and MDP not in json.dumps(E.lister(), ensure_ascii=False))
m = E.modifier(s["id"], {"nom": "Serveur maison", "secret": ""})
check("C6 modifier sans secret garde le mot de passe", m["secret_pose"] and m["nom"] == "Serveur maison")
m = E.modifier(s["id"], {"type": "dossier", "port": 22})
check("C7 le type ne change pas ; port modifié", m["type"] == "sftp" and m["adresse"].startswith("sftp://olivia@nas.local/"))
m = E.modifier(s["id"], {"effacer_secret": True})
check("C8 effacer_secret retire le mot de passe", not m["secret_pose"]
      and "DZC_SERVEUR_SECRET" not in (DATA_ROOT / ".env").read_text(encoding="utf-8"))
E.modifier(s["id"], {"secret": MDP})
try:
    E.modifier("inconnu", {})
    check("C9 modifier un inconnu → EmplacementInconnu", False)
except E.EmplacementInconnu:
    check("C9 modifier un inconnu → EmplacementInconnu", True)
x = E.creer({"type": "dossier", "chemin": str(NAS / "sous")})
check("C10 sans nom : l'adresse sert de nom ; id unique", x["nom"] == str(NAS / "sous") and x["id"] not in
      ("nasdubureau", "serveur"), x)
E.supprimer(x["id"])
check("C11 supprimé", all(v["id"] != x["id"] for v in E.lister()))
check("C12 avec_role (t379) : les emplacements d'un rôle", [v["id"] for v in E.avec_role("miroir")] == ["nasdubureau"]
      and E.avec_role("bibliotheque") == [])
# coffre posé mais fermé : un mot de passe ne s'écrit pas
coffre.poser("motdepasse-du-banc", {})
check("C13 coffre posé et fermé → verrouille()", coffre.verrouille())
r = c.post("/api/reglages/chemins", json={**S0, "nom": "Autre", "secret": "abc"})
check("C14 POST avec mot de passe, coffre fermé → 409, rien d'écrit", r.status_code == 409
      and all(v["nom"] != "Autre" for v in E.lister()), r.text)
r = c.delete(f"/api/reglages/chemins/{s['id']}")
check("C15 supprimer un SFTP à mot de passe, coffre fermé → 409", r.status_code == 409, r.text)
coffre.ouvrir("motdepasse-du-banc")
t = E.creer({**S0, "nom": "Au coffre", "secret": "secret-au-coffre"})
check("C16 coffre ouvert : le mot de passe va AU COFFRE, pas au .env", coffre.lire_cle("DZC_AUCOFFRE_SECRET")
      == "secret-au-coffre" and "DZC_AUCOFFRE_SECRET" not in (DATA_ROOT / ".env").read_text(encoding="utf-8"))
E.supprimer(t["id"])
check("C17 supprimer efface le secret du coffre", coffre.lire_cle("DZC_AUCOFFRE_SECRET") is None)
coffre.fermer()
coffre.FICHIER.unlink()
check("C18 coffre retiré pour la suite", not coffre.verrouille())
for i in range(18):
    E.creer({"type": "dossier", "chemin": str(NAS / f"n{i}")})
check("C19 20 emplacements au plus", refuse(E.creer, {"type": "dossier", "chemin": str(NAS / "n99")}))
for v in E.lister():
    if v["id"] not in ("nasdubureau", "serveur"):
        E.supprimer(v["id"])

# ══ [T] tester un dossier ══════════════════════════════════════════════════════════════════════════════════════
print("[T] tester un dossier")
avant = sorted(p.name for p in NAS.iterdir())
r = E.tester("nasdubureau")
check("T1 écriture et lecture réussies, espace libre lu", r["ok"] and r["code"] == "ecrit_lu"
      and isinstance(r["libre_octets"], int) and r["libre_octets"] > 0, r)
check("T2 le fichier témoin est effacé", sorted(p.name for p in NAS.iterdir()) == avant)
check("T3 le résultat est gardé (dernier_test)", E.obtenir("nasdubureau")["dernier_test"]["code"] == "ecrit_lu")
ECRITS = []
_wb = pathlib.Path.write_bytes


def _espion(self, data):
    ECRITS.append(str(self))
    return _wb(self, data)


pathlib.Path.write_bytes = _espion
try:
    E.modifier("nasdubureau", {"roles": ["bibliotheque"]})
    r = E.tester("nasdubureau")
    check("T4 « bibliothèque » seul : joignable, RIEN d'écrit là-bas", r["ok"] and r["code"] == "joignable"
          and not [p for p in ECRITS if p.startswith(str(NAS))], ECRITS)
    E.modifier("nasdubureau", {"roles": ["sauvegarde", "miroir"]})
    v = E.verifier()
    check("T5 verifier (Diagnostic) : rien d'écrit là-bas, une ligne par emplacement",
          not [p for p in ECRITS if p.startswith(str(NAS))] and [x["id"] for x in v] == ["nasdubureau", "serveur"], v)
finally:
    pathlib.Path.write_bytes = _wb
check("T6 verifier : le dossier est joignable", v[0]["ok"] and v[0]["code"] == "joignable")
g = E.creer({"type": "dossier", "chemin": str(_tmp / "absent")})
r = E.tester(g["id"])
check("T7 dossier absent → introuvable", not r["ok"] and r["code"] == "introuvable", r)
E.supprimer(g["id"])
check("T8 changer l'adresse oublie l'ancien test", "dernier_test" not in json.loads(
    (DATA_ROOT / "emplacements.json").read_text(encoding="utf-8"))["emplacements"]["nasdubureau"]
      or E.modifier("nasdubureau", {"chemin": str(NAS / "..") + "\\nas"})["dernier_test"] is None)

# ══ [S] SFTP par le faux client ════════════════════════════════════════════════════════════════════════════════
print("[S] SFTP")
os.environ["FAUX_SFTP_MDP"] = MDP
JOURNAL.unlink(missing_ok=True)
r = E.tester("serveur")
a = appels()[-1] if appels() else {}
check("S1 SFTP : écriture et lecture réussies, espace libre par df", r["ok"] and r["code"] == "ecrit_lu"
      and r["libre_octets"] == 600000 * 1024, r)
check("S2 le mot de passe est passé par SSH_ASKPASS et relu exactement", a.get("askpass_lu_ok") is True, a)
check("S3 jamais dans les arguments ni dans le lot", a and MDP not in json.dumps(a["args"], ensure_ascii=False)
      and MDP not in "\n".join(a["commandes"]))
check("S4 BatchMode=no AVANT -b", a and a["args"].index("BatchMode=no") < a["args"].index("-b"))
check("S5 aucune clé de l'application dans l'environnement de sftp.exe", a and "FAL_KEY" not in a["env"]
      and not [k for k in a["env"] if k.startswith("DZC_") and k != "DZC_ASKPASS"], [k for k in a.get("env", [])
                                                                                    if "KEY" in k or "DZC" in k])
check("S6 hôtes connus dans les données de l'application, accept-new", a and any(
    x.startswith("UserKnownHostsFile=") and str(DATA_ROOT) in x for x in a["args"])
      and "StrictHostKeyChecking=accept-new" in a["args"])
check("S7 le lot : cd, put, get, rm du témoin, df toléré", a and a["commandes"][0] == 'cd "/sauvegardes"'
      and [l.split()[0] for l in a["commandes"]] == ["cd", "put", "get", "rm", "-df"], a.get("commandes"))
check("S8 le témoin n'est pas resté sur le serveur", list((SERVEUR / "sauvegardes").iterdir()) == [])
check("S9 l'utilisateur et l'hôte après --", a and a["args"][a["args"].index("--") + 1] == "olivia@nas.local")
os.environ["FAUX_SFTP_MDP"] = "autre"
r = E.tester("serveur")
check("S10 mauvais mot de passe → acces_refuse", not r["ok"] and r["code"] == "acces_refuse", r)
os.environ["FAUX_SFTP_MDP"] = MDP
os.environ["FAUX_SFTP_BAVARD"] = "1"                                # un serveur qui recopie ce qu'il a lu
r = E.tester("serveur")
check("S10b une sortie de sftp qui contient le mot de passe est masquée", not r["ok"] and r["code"] == "echec"
      and MDP not in json.dumps(r, ensure_ascii=False) and "•••" in r["detail"], r)
os.environ.pop("FAUX_SFTP_BAVARD")
E.modifier("serveur", {"dossier_distant": "/absent"})
r = E.tester("serveur")
check("S11 dossier distant absent → distant_introuvable", not r["ok"] and r["code"] == "distant_introuvable", r)
E.modifier("serveur", {"dossier_distant": "/sauvegardes", "hote": "injoignable.test"})
r = E.tester("serveur")
check("S12 hôte introuvable → hote_introuvable", not r["ok"] and r["code"] == "hote_introuvable", r)
E.modifier("serveur", {"hote": "nas.local", "roles": ["bibliotheque"]})
JOURNAL.unlink(missing_ok=True)
r = E.tester("serveur")
check("S13 SFTP « bibliothèque » seul : cd + ls, aucun put", r["ok"] and r["code"] == "joignable"
      and not [l for l in appels()[-1]["commandes"] if l.startswith(("put", "rm"))], appels()[-1:])
os.environ.pop("FAUX_SFTP_MDP")
k = E.creer({**S0, "nom": "Par clé", "cle_ssh": "C:\\Users\\olivia\\.ssh\\id_ed25519", "roles": ["miroir"]})
JOURNAL.unlink(missing_ok=True)
r = E.tester(k["id"])
a = appels()[-1]
check("S14 clé SSH seule : -i, BatchMode laissé à sftp (aucune invite)", r["ok"] and "-i" in a["args"]
      and "BatchMode=no" not in a["args"] and "SSH_ASKPASS" not in a["env"], a["args"])
r = E.tester_brouillon({**S0, "secret": "zz"})
check("S15 brouillon : testé sans rien enregistrer", r["ok"] and len(E.lister()) == 3)
os.environ["DZ_SFTP_EXE"] = str(_tmp / "absent.exe")
r = E.tester(k["id"])
check("S16 client absent → client_absent", not r["ok"] and r["code"] == "client_absent", r)
check("S17 GET dit sftp_disponible false", c.get("/api/reglages/chemins").json()["sftp_disponible"] is False)
os.environ["DZ_SFTP_EXE"] = str(FAUX)
E.supprimer(k["id"])

# ══ [R] routes ═════════════════════════════════════════════════════════════════════════════════════════════════
print("[R] routes")
j = c.get("/api/reglages/chemins").json()
check("R1 GET : emplacements, types, rôles, sftp_disponible", [v["id"] for v in j["emplacements"]] ==
      ["nasdubureau", "serveur"] and j["types"] == ["dossier", "sftp"]
      and j["roles"] == ["sauvegarde", "miroir", "bibliotheque"] and j["sftp_disponible"] is True, j)
check("R2 GET ne rend aucun secret", MDP not in json.dumps(j, ensure_ascii=False))
r = c.post("/api/reglages/chemins", json={"nom": "Clé USB", "type": "dossier", "chemin": str(NAS / "usb"),
                                          "roles": ["sauvegarde"]})
check("R3 POST crée", r.status_code == 200 and r.json()["emplacement"]["id"] == "cleusb", r.text)
r = c.post("/api/reglages/chemins", json={"type": "dossier", "chemin": "relatif"})
check("R4 POST invalide → 400", r.status_code == 400, r.text)
r = c.post("/api/reglages/chemins/tester", json={"type": "dossier", "chemin": str(NAS)})
check("R5 brouillon → ok", r.status_code == 200 and r.json()["ok"], r.text)
r = c.post("/api/reglages/chemins/cleusb/tester")
check("R6 tester un emplacement → introuvable (dossier pas encore créé)", r.status_code == 200
      and r.json()["code"] == "introuvable", r.text)
r = c.post("/api/reglages/chemins/cleusb", json={"roles": ["miroir"]})
check("R7 modifier → rôles", r.status_code == 200 and r.json()["emplacement"]["roles"] == ["miroir"], r.text)
check("R8 inconnu → 404", c.post("/api/reglages/chemins/zz/tester").status_code == 404
      and c.delete("/api/reglages/chemins/zz").status_code == 404)
r = c.get("/api/reglages/chemins/verifier")
check("R9 vérification : une ligne par emplacement", r.status_code == 200
      and [x["id"] for x in r.json()["emplacements"]] == ["nasdubureau", "serveur", "cleusb"], r.text)
r = c.delete("/api/reglages/chemins/cleusb")
check("R10 DELETE", r.status_code == 200 and len(E.lister()) == 2)
for meth, url in (("get", "/api/reglages/chemins"), ("post", "/api/reglages/chemins"),
                  ("post", "/api/reglages/chemins/tester"), ("get", "/api/reglages/chemins/verifier"),
                  ("post", "/api/reglages/chemins/serveur/tester"), ("delete", "/api/reglages/chemins/serveur")):
    kw = {"json": {}} if meth == "post" else {}
    check(f"R11 {meth.upper()} {url} refusé depuis un autre appareil", getattr(cd, meth)(url, **kw).status_code in (401, 403))
# le refus d'appairage (401) passe avant la garde locale : chaque route doit AUSSI appeler _local d'entrée
_sr = ast.parse((ICI.parent / "app" / "api" / "settings_routes.py").read_text(encoding="utf-8"))
_ch = [f for f in _sr.body if isinstance(f, ast.AsyncFunctionDef) and any(
    isinstance(d, ast.Call) and d.args and isinstance(d.args[0], ast.Constant)
    and str(d.args[0].value).startswith("/chemins") for d in f.decorator_list)]
_sans = [f.name for f in _ch if not any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_local"
                                        for st in f.body[:3] for n in ast.walk(st))]
check(f"R11b les {len(_ch)} routes /chemins appellent _local d'entrée", len(_ch) == 7 and not _sans, _sans)
idx = c.get("/api/reglages/index").json()
check("R12 la recherche des Réglages trouve « Emplacements » (rubrique Chemins)", any(
    x.get("section") == "paths" and x.get("libelle") == "Emplacements" and "sftp" in x.get("mots", "")
    for x in (idx.get("entrees") or [])), str(idx)[:300])

# ══ [E] traductions L10 ════════════════════════════════════════════════════════════════════════════════════════
print("[E] traductions L10")
tr = json.loads((RACINE / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
src = (ICI.parent / "app" / "services" / "emplacements.py").read_text(encoding="utf-8")
msgs = set()
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and getattr(n.exc.func, "id", "") == "ValueError" \
            and n.exc.args and isinstance(n.exc.args[0], ast.Constant) and isinstance(n.exc.args[0].value, str):
        msgs.add(n.exc.args[0].value)
manque = sorted(m for m in msgs if m not in tr)
check(f"E1 les {len(msgs)} messages fixes du service sont traduits", msgs and not manque, manque)
check("E2 « Emplacement inconnu : {v} » traduit", "Emplacement inconnu : {v}" in tr)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                   env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
check("E3 i18n_l10_erreurs.py --check", r.returncode == 0, (r.stdout + r.stderr)[-600:])

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
