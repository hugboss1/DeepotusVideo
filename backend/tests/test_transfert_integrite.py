# -*- coding: utf-8 -*-
"""Transfert entre machines : intégrité sha256 et lots cochables (tâche #19, plan Settings T12, 29/09/2026).
Banc-miroir : les empreintes sont recalculées ICI sur les octets relus (hashlib), jamais prises dans la réponse ;
les fichiers posés à l'import sont relus sur disque. Témoin : la base 02bdff4 n'a ni lots, ni empreintes, ni
vérification. Zéro réseau, deux racines de données jetables (machine A et machine B).
Run : & $PY tests/test_transfert_integrite.py   (depuis backend/)"""
import hashlib, json, os, pathlib, sqlite3, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dztri_"))
A = _tmp / "machineA"
A.mkdir()
os.environ["DEEPOTUS_DATA_DIR"] = str(A)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(A / 'deepotus.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.services import transfert as TR                            # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def ecrire(p, octets):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(octets)


def semer(racine):
    c = sqlite3.connect(str(racine / "deepotus.db"))
    c.execute("create table notes (id text primary key, texte text)")
    c.execute("insert into notes values ('n1', 'bonjour')")
    c.commit(); c.close()
    ecrire(racine / "assets" / "images" / "a.png", b"A" * 4096)
    ecrire(racine / "assets" / "images" / "b.png", b"B" * 100)
    ecrire(racine / "pricing.json", b'{"flux_image_usd": 0.003}')
    ecrire(racine / "logs" / "deepotus-2026-09-29.log", b"L" * 10)
    ecrire(racine / "rebut_decks_2026-08-26" / "gros.bin", b"R" * 5000)
    ecrire(racine / ".env", b"FAL_KEY=secret-a-ne-jamais-copier\n")

semer(A)
racine_git = pathlib.Path(__file__).resolve().parents[2]
vieux = subprocess.run(["git", "show", "02bdff4:backend/app/services/transfert.py"], cwd=racine_git, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 02bdff4")
check("0.1 TÉMOIN : ni lots, ni empreintes, ni vérification ; les rebuts partaient JAMAIS",
      vieux and "empreintes" not in vieux and "def verifier(" not in vieux and "LOTS =" not in vieux and '"rebut_*/*"' in vieux, "")

print("\n[1] lots")
pl = TR.poids_lots()
check("1.1 poids par lot en un parcours : créations (a, b, pricing), journaux, rebuts ; le .env n'est dans AUCUN",
      pl == {"creations": {"fichiers": 3, "octets": 4096 + 100 + 25}, "journaux": {"fichiers": 1, "octets": 10},
             "rebuts": {"fichiers": 1, "octets": 5000}}, json.dumps(pl))
check("1.2 un secret reste exclu même si l'on coche tout", TR.exclu(".env", {"journaux": True, "rebuts": True})[0] is True
      and TR.exclu("rebut_x/.env", {"rebuts": True})[0] is True, "")

print("\n[2] export par défaut : empreintes, sans journaux ni rebuts")
D1 = _tmp / "usb1"; D1.mkdir()
m = TR.exporter(D1, TR.Etat(), quand=0)
P1 = pathlib.Path(m["dossier"])
man = json.loads((P1 / TR.MANIFESTE).read_text(encoding="utf-8"))
check("2.1 lots décochés par défaut, écrits au manifeste", man["lots"] == {"journaux": False, "rebuts": False}, json.dumps(man.get("lots")))
check("2.2 ni journaux, ni rebuts, ni .env dans le paquet", not (P1 / "donnees" / "logs").exists()
      and not list(P1.rglob("gros.bin")) and not list(P1.rglob(".env")), "")
check("2.3 une empreinte par fichier, ÉGALE au sha256 des octets écrits (relus ici)",
      sorted(man["empreintes"]) == ["assets/images/a.png", "assets/images/b.png", "pricing.json"]
      and all(man["empreintes"][r] == sha(P1 / "donnees" / r) == sha(A / r) for r in man["empreintes"]), "")
check("2.4 l'empreinte de l'instantané de la base aussi", man["base_sha256"] == sha(P1 / "base" / "deepotus.db"), "")

print("\n[3] export avec les rebuts cochés")
D2 = _tmp / "usb2"; D2.mkdir()
m2 = TR.exporter(D2, TR.Etat(), quand=60, lots={"rebuts": True})
P2 = pathlib.Path(m2["dossier"])
check("3.1 rebuts partis (avec empreinte), journaux toujours pas", (P2 / "donnees" / "rebut_decks_2026-08-26" / "gros.bin").is_file()
      and "rebut_decks_2026-08-26/gros.bin" in m2["empreintes"] and not (P2 / "donnees" / "logs").exists()
      and m2["lots"] == {"journaux": False, "rebuts": True}, json.dumps(m2["lots"]))

print("\n[4] vérification")
e = TR.Etat()
v = TR.verifier(P1, e)
check("4.1 paquet intact : 4/4 (3 fichiers + la base), empreintes identiques", v["ok"] is True and v["verifies"] == 4
      and v["attendus"] == 4 and e.phase == "fini" and "identiques" in e.detail, json.dumps(v))
ecrire(P1 / "donnees" / "assets" / "images" / "b.png", b"C" * 100)
v = TR.verifier(P1)
check("4.2 un fichier altéré (même taille !) est vu et NOMMÉ", v["ok"] is False and v["divergents"] == ["assets/images/b.png"], json.dumps(v))
(P1 / "donnees" / "assets" / "images" / "a.png").unlink()
v = TR.verifier(P1)
check("4.3 un fichier disparu est vu et nommé", v["manquants"] == ["assets/images/a.png"], json.dumps(v))
with open(P2 / "base" / "deepotus.db", "ab") as f:
    f.write(b"x")
v = TR.verifier(P2)
check("4.4 une base altérée est nommée", v["divergents"] == ["base/deepotus.db"], json.dumps(v))
mv = json.loads((P2 / TR.MANIFESTE).read_text(encoding="utf-8")); mv.pop("empreintes")
(P2 / TR.MANIFESTE).write_text(json.dumps(mv), encoding="utf-8")
v = TR.verifier(P2)
check("4.5 paquet antérieur (sans empreintes) : dit, pas deviné", v["ok"] is False and v["sans_empreintes"] is True, json.dumps(v))

print("\n[5] import : un fichier abîmé n'entre pas")
D3 = _tmp / "usb3"; D3.mkdir()
P3 = pathlib.Path(TR.exporter(D3, TR.Etat(), quand=120, lots={"rebuts": True, "journaux": True})["dossier"])
ecrire(P3 / "donnees" / "assets" / "images" / "b.png", b"Z" * 100)         # abîmé en route, même taille
ecrire(P3 / "donnees" / ".env", b"FAL_KEY=vole\n")                        # paquet bricolé
B = _tmp / "machineB"; B.mkdir()
c = sqlite3.connect(str(B / "deepotus.db")); c.execute("create table notes (id text primary key, texte text)"); c.commit(); c.close()
TR.DATA_ROOT = B
TR.racine = lambda: pathlib.Path(B)
res = TR.importer(P3, TR.Etat())
check("5.1 le fichier abîmé est écarté et NOMMÉ ; il n'est pas posé", res["fichiers_abimes"] == ["assets/images/b.png"]
      and not (B / "assets" / "images" / "b.png").exists(), json.dumps(res.get("fichiers_abimes")))
check("5.2 les fichiers sains sont posés, octet pour octet", sha(B / "assets" / "images" / "a.png") == sha(A / "assets" / "images" / "a.png")
      and res["fichiers_ajoutes"] == 4, str(res.get("fichiers_ajoutes")))
check("5.3 les lots cochés à l'export sont repris (rebuts, journaux)", (B / "rebut_decks_2026-08-26" / "gros.bin").is_file()
      and (B / "logs" / "deepotus-2026-09-29.log").is_file(), "")
check("5.4 un .env glissé dans un paquet n'est JAMAIS repris", not (B / ".env").exists(), "")
check("5.5 aucun fichier provisoire laissé", not list(B.rglob("*.dztransfert")), "")
check("5.6 la base fusionne toujours", sqlite3.connect(str(B / "deepotus.db")).execute("select count(*) from notes").fetchone()[0] == 1, "")

print("\n[6] routes")
TR.DATA_ROOT = A
TR.racine = lambda: pathlib.Path(A)
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402


def attendre(c, jid):
    for _ in range(100):
        j = c.get(f"/api/transfer/jobs/{jid}").json()
        if j.get("statut") != "en cours":
            return j
        time.sleep(0.1)
    return j

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    d = c.get("/api/transfer/destinations").json()
    check("6.1 destinations : poids par lot + aperçu des créations seules", d["lots"]["rebuts"]["octets"] == 5000
          and d["apercu"] == d["lots"]["creations"], json.dumps(d.get("lots")))
    D4 = _tmp / "usb4"; D4.mkdir()
    j = attendre(c, c.post("/api/transfer/export", json={"destination": str(D4), "lots": {"journaux": True}}).json()["job_id"])
    check("6.2 export avec lots : les lots demandés, et seulement eux", j["statut"] == "fini"
          and j["resultat"]["lots"] == {"journaux": True, "rebuts": False}, json.dumps(j.get("resultat", {}).get("lots")))
    check("6.3 lots illisibles : 400", c.post("/api/transfer/export", json={"destination": str(D4), "lots": ["rebuts"]}).status_code == 400, "")
    jv = attendre(c, c.post("/api/transfer/verify", json={"dossier": j["resultat"]["dossier"]}).json()["job_id"])
    check("6.4 /transfer/verify : un job « verification », résultat intact", jv["sens"] == "verification" and jv["statut"] == "fini"
          and jv["resultat"]["ok"] is True and jv["etat"]["phase"] == "fini", json.dumps(jv)[:300])
    check("6.4b les réponses sondées portent le NOMBRE d'empreintes, pas la liste (export, inspect)",
          j["resultat"]["empreintes"] == 5 and c.post("/api/transfer/inspect", json={"dossier": j["resultat"]["dossier"]}).json()["manifeste"]["empreintes"] == 5,
          json.dumps(j["resultat"].get("empreintes")))
    check("6.5 /transfer/verify sans manifeste : 400 parlant", c.post("/api/transfer/verify", json={"dossier": str(_tmp)}).status_code == 400, "")
with TestClient(app, client=("192.168.1.20", 50000)) as c2:
    check("6.6 hors boucle locale : vérification refusée", c2.post("/api/transfer/verify", json={"dossier": "x"}).status_code == 403, "")

print("\n[7] l'écran (couche transfert livrée dans le bundle)")
_b = (racine_git / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(encoding="utf-8")
_c = _b[_b.find("/*__DZ_TRANSFERT_BEGIN__*/"):_b.find("/*__DZ_TRANSFERT_END__*/")]
check("7.1 lots décochés par défaut, envoyés avec l'export", "x.useState({ journaux: false, rebuts: false })" in _c
      and "{ destination: dest, lots: lots }" in _c, "")
check("7.2 une case par lot optionnel, avec son poids servi par /transfer/destinations",
      _c.count('dztCase("journaux"') == 1 and _c.count('dztCase("rebuts"') == 1 and "pl[k].octets" in _c, "")
check("7.3 « Contrôler l'intégrité » : un seul appel à /transfer/verify, proposé après un export ET avant un import",
      _c.count('"/api/transfer/verify"') == 1 and _c.count("controler(res.dossier)") == 1 and _c.count("controler(dossier)") == 1, "")
check("7.4 contrôle avant import désactivé pour un paquet sans empreintes (dit, pas caché)",
      "disabled: !(apercu && apercu.empreintes)" in _c and "exporté avant les empreintes" in _c, "")
check("7.5 verdict affiché ; fichiers abîmés d'un import affichés", '"data-dzt-verdict"' in _c and "res.fichiers_abimes.join" in _c, "")

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
