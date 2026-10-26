# -*- coding: utf-8 -*-
"""t309 (26/10/2026) — Boite a outils, lot A4 : les REGLES d'un client (services/regles_client.py). Ce que ce banc garde :
un espace sans client responsable (Deepotus, marque) n'a aucune regle ; un client exige un consentement EN COURS par canal
(canal_id de la verification t308), la validation datee en mode `valide_par_client`, la confirmation nominative en mode
`publie_en_son_nom` ; un produit suit les regles de son client parent ; une revocation met le post en pause ; la lecture
BRUTE (boucle de fond) rend les memes verdicts sans ecrire un octet ; deux colonnes neuves sur scheduled_posts ; les
messages de refus traduits par L10. Data-dir isole, aucun reseau (verifications posees par comptes.noter_verification).
Sections : R1 marque, R2 a valider, R3 consentement, R4 confirmation, R5 produit, R6 revocation, R7 lecture brute,
R8 colonnes, R9 L10.
Run (depuis backend/) : & $PY tests/test_regles_client.py"""
import asyncio, json, os, pathlib, sqlite3, subprocess, sys, tempfile
from datetime import datetime
from types import SimpleNamespace
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrgc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import espaces as E, fiche_client as F, comptes as C   # noqa: E402
try:
    from app.services import regles_client as R                     # noqa: E402
except ImportError as ex:
    check("regles_client importable", False, str(ex))
    print(f"\n{ok} passed, {fail} failed")
    sys.exit(1)


def post(espace_id, comptes, valide=None, confirme=None):
    return SimpleNamespace(espace_id=espace_id, comptes=json.dumps(comptes), valide_client_le=valide, confirme_client=confirme)


def refus(p, confirme=None, brut=False):
    """L'exception RefusClient levee par controler, ou None s'il passe."""
    try:
        R.controler(p, confirme=confirme, brut=brut)
    except R.RefusClient as e:
        return e
    return None


ECARTS, POSTS = [], []
def verdict(p, confirme=None):
    """Le verdict de controler (brut=False), compare a celui de la lecture brute (R7)."""
    def v(brut):
        try:
            ex = R.controler(p, confirme=confirme, brut=brut)
            return ("ok", ex["client"] if ex else None)
        except R.RefusClient as e:
            return (e.code, e.client, e.nom, sorted(e.canaux))
    a, b = v(False), v(True)
    if a != b:
        ECARTS.append((a, b))
    POSTS.append((p, confirme))
    return a


MAINTENANT = datetime(2026, 10, 26, 12, 0, 0)

# ---- les espaces et les comptes ------------------------------------------------------------------------------------------
m = E.creer({"nom": "Marque Soleil", "type": "marque"})["id"]
cm = C.creer({"espace_id": m, "plateforme": "x", "libelle": "X Soleil"})["id"]
C.noter_verification(cm, {"etat": "vert", "id_distant": "900"})
c = E.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
F.ecrire(c, {"societe": "Lune SARL"})
ca = C.creer({"espace_id": c, "plateforme": "x", "libelle": "X Lune"})["id"]
C.noter_verification(ca, {"etat": "vert", "id_distant": "111"})
F.ajouter_consentement(c, "x:111", ["publier"], "ecrit")
cb = C.creer({"espace_id": c, "plateforme": "telegram", "libelle": "TG Lune"})["id"]        # jamais verifie

print("[R1] espace marque, Deepotus : aucune regle")
check("R1a exigences None (marque)", R.exigences(m, [cm]) is None and R.exigences(m, [cm], brut=True) is None)
check("R1b controler rend None (marque)", R.controler(post(m, [cm])) is None and verdict(post(m, [cm])) == ("ok", None))
check("R1c statut_initial draft (marque)", R.statut_initial(m, "draft") == "draft")
check("R1d Deepotus (espace vide) : aucune regle", R.exigences(None, []) is None and R.exigences("", [], brut=True) is None
      and verdict(post(None, [])) == ("ok", None))

print("[R2] client valide_par_client : a valider")
p2 = post(c, [ca])
e = refus(p2)
check("R2a non valide : RefusClient code a_valider", e is not None and e.code == "a_valider", repr(e and e.code))
check("R2b RefusClient est un PermissionError, porte client/nom/canaux",
      isinstance(e, PermissionError) and e.client == c and e.nom == "Lune SARL" and "X Lune" in e.canaux, repr(e and vars(e)))
check("R2c message FR nomme le client", e is not None and str(e) == "post à valider par le client « Lune SARL » avant d'être programmé",
      str(e))
verdict(p2)
p2.valide_client_le = MAINTENANT
ex = R.controler(p2)
check("R2d valide : passe et rend les exigences", isinstance(ex, dict) and ex["client"] == c and ex["mode"] == "valide_par_client"
      and ex["nom"] == "Lune SARL" and ex["non_couverts"] == []
      and ex["canaux"] == [{"compte": ca, "libelle": "X Lune", "canal_id": "x:111", "couvert": True}], repr(ex))
check("R2e verdict valide", verdict(p2) == ("ok", c))
check("R2f statut_initial : draft -> a_valider, scheduled garde", R.statut_initial(c, "draft") == "a_valider"
      and R.statut_initial(c, "scheduled") == "scheduled")
check("R2g comptes en liste (pas en JSON) acceptes", R.controler(SimpleNamespace(espace_id=c, comptes=[ca], valide_client_le=MAINTENANT,
                                                                                confirme_client=None))["client"] == c)

print("[R3] canal non verifie : consentement")
p3 = post(c, [ca, cb], valide=MAINTENANT)
e3 = refus(p3)
check("R3a code consentement, canaux = le compte non couvert", e3 is not None and e3.code == "consentement"
      and e3.canaux == ["TG Lune"], repr(e3 and vars(e3)))
check("R3b message FR", e3 is not None and str(e3) == "aucun consentement en cours du client « Lune SARL » pour : TG Lune", str(e3))
ex3 = R.exigences(c, [ca, cb])
check("R3c exigences : canal_id None, non couvert", ex3["non_couverts"] == ["TG Lune"]
      and ex3["canaux"][1] == {"compte": cb, "libelle": "TG Lune", "canal_id": None, "couvert": False}, repr(ex3))
check("R3d verdict consentement (aussi avant validation : consentement d'abord)",
      verdict(p3)[0] == "consentement" and verdict(post(c, [ca, cb]))[0] == "consentement")
e3b = refus(post(c, [], valide=MAINTENANT))
check("R3e aucun compte cible : consentement", e3b is not None and e3b.code == "consentement" and verdict(post(c, [], valide=MAINTENANT))[0] == "consentement")
check("R3f compte inconnu : consentement", verdict(post(c, ["c00000000"], valide=MAINTENANT))[0] == "consentement")

print("[R4] client publie_en_son_nom : confirmation nominative")
c2 = E.creer({"nom": "Studio Nord", "type": "client"})["id"]
F.ecrire(c2, {"mode_publication": "publie_en_son_nom"})
cc = C.creer({"espace_id": c2, "plateforme": "x", "libelle": "X Nord"})["id"]
C.noter_verification(cc, {"etat": "vert", "id_distant": "222"})
F.ajouter_consentement(c2, "x:222", ["publier"], "doigt")
p4 = post(c2, [cc])
e4 = refus(p4)
check("R4a sans confirmation : code confirmation, nom = nom de l'espace (pas de societe), canaux = canal_id",
      e4 is not None and e4.code == "confirmation" and e4.nom == "Studio Nord" and e4.canaux == ["x:222"] and e4.client == c2,
      repr(e4 and vars(e4)))
check("R4b message FR", e4 is not None and str(e4) == "confirmez la publication au nom du client « Studio Nord » sur : x:222", str(e4))
check("R4c confirme=<id client> : passe", R.controler(p4, confirme=c2)["client"] == c2 and verdict(p4, c2) == ("ok", c2))
check("R4d confirme=autre : confirmation", refus(p4, confirme="autre").code == "confirmation" and verdict(p4, "autre")[0] == "confirmation")
check("R4e verdict sans confirmation", verdict(p4)[0] == "confirmation")
p4.confirme_client = c2
check("R4f confirme_client du post = client : passe", verdict(p4) == ("ok", c2))
check("R4g statut_initial draft garde (publie_en_son_nom)", R.statut_initial(c2, "draft") == "draft")

print("[R5] produit d'un client : regles du parent")
pr = E.creer({"nom": "Pain du matin", "type": "produit", "parent": c})["id"]
cp = C.creer({"espace_id": pr, "plateforme": "x", "libelle": "X Pain"})["id"]
C.noter_verification(cp, {"etat": "vert", "id_distant": "333"})
F.ajouter_consentement(c, "x:333", ["publier"], "ecrit")
e5 = refus(post(pr, [cp]))
check("R5a produit non valide : a_valider, client = parent, nom = societe du parent",
      e5 is not None and e5.code == "a_valider" and e5.client == c and e5.nom == "Lune SARL", repr(e5 and vars(e5)))
check("R5b verdict a_valider puis ok une fois valide", verdict(post(pr, [cp]))[0] == "a_valider"
      and verdict(post(pr, [cp], valide=MAINTENANT)) == ("ok", c))
cp2 = C.creer({"espace_id": pr, "plateforme": "telegram", "libelle": "TG Pain"})["id"]
e5c = refus(post(pr, [cp, cp2], valide=MAINTENANT))
check("R5c canal du produit non couvert : consentement du parent", e5c is not None and e5c.code == "consentement"
      and e5c.client == c and e5c.canaux == ["TG Pain"] and verdict(post(pr, [cp, cp2], valide=MAINTENANT))[0] == "consentement")
check("R5d statut_initial du produit = celui du parent", R.statut_initial(pr, "draft") == "a_valider")
pr2 = E.creer({"nom": "Affiche Nord", "type": "produit", "parent": c2})["id"]
cq = C.creer({"espace_id": pr2, "plateforme": "x", "libelle": "X Affiche"})["id"]
C.noter_verification(cq, {"etat": "vert", "id_distant": "444"})
F.ajouter_consentement(c2, "x:444", ["publier"], "ecrit")
e5e = refus(post(pr2, [cq]))
check("R5e produit d'un client publie_en_son_nom : confirmation au nom du parent", e5e is not None and e5e.code == "confirmation"
      and e5e.client == c2 and e5e.nom == "Studio Nord" and verdict(post(pr2, [cq]), c2) == ("ok", c2))
pm = E.creer({"nom": "Produit Soleil", "type": "produit", "parent": m})["id"]
check("R5f produit d'une marque : aucune regle", R.exigences(pm, []) is None and verdict(post(pm, [])) == ("ok", None))

print("[R6] revocation : en pause")
p6 = post(c, [ca], valide=MAINTENANT)
check("R6a couvert et valide : pas en pause", R.en_pause(p6) is False and verdict(p6) == ("ok", c))
F.revoquer(c, "x:111")
check("R6b revoque : en pause", R.en_pause(p6) is True and verdict(p6)[0] == "consentement")
F.ajouter_consentement(c, "x:111", ["publier"], "whatsapp")
check("R6c nouveau consentement : repart", R.en_pause(p6) is False and verdict(p6) == ("ok", c))
check("R6d non valide : en pause", R.en_pause(post(c, [ca])) is True)
check("R6e publie_en_son_nom non confirme : PAS en pause (confirmation deja donnee)", R.en_pause(post(c2, [cc])) is False)
check("R6f marque, Deepotus : jamais en pause", R.en_pause(post(m, [cm])) is False and R.en_pause(post(None, [])) is False)
check("R6g en_pause accepte un dict", R.en_pause({"espace_id": c, "comptes": json.dumps([ca]), "valide_client_le": None,
                                                 "confirme_client": None}) is True)

print("[R7] lecture brute : memes verdicts, aucune ecriture")
check("R7a memes verdicts brut / non brut sur R1-R6", not ECARTS and len(POSTS) >= 20, repr(ECARTS))


def instantane():
    d = E.dossier()
    return {str(f.relative_to(d)): f.read_bytes() for f in sorted(d.rglob("*")) if f.is_file()}


avant = instantane()
attendus = []
for p, conf in POSTS:
    try:
        R.controler(p, confirme=conf, brut=True); attendus.append("ok")
    except R.RefusClient as x:
        attendus.append(x.code)
# les lecteurs qui migrent ou ecrivent sont INTERDITS en lecture brute : ils levent s'ils sont appeles
_interdits = [(E, "lire"), (E, "client_responsable"), (E, "dossier"), (E, "chemin"), (F, "lire"), (F, "_client"),
              (F, "_charger"), (C, "_lire"), (C, "obtenir"), (C, "_fichier")]
_orig = {(mod, n): getattr(mod, n) for mod, n in _interdits}
def _interdit(*a, **k):
    raise AssertionError("lecteur interdit en lecture brute")
for mod, n in _interdits:
    setattr(mod, n, _interdit)
obtenus, err7 = [], None
try:
    for p, conf in POSTS:
        try:
            R.controler(p, confirme=conf, brut=True); obtenus.append("ok")
        except R.RefusClient as x:
            obtenus.append(x.code)
        R.en_pause(p)
        R.exigences(p.espace_id, json.loads(p.comptes), brut=True)
except AssertionError as x:
    err7 = x
finally:
    for (mod, n), f in _orig.items():
        setattr(mod, n, f)
check("R7b' brut n'appelle ni espaces.lire / fiche_client.lire / comptes._lire ni rien qui ecrit",
      err7 is None and obtenus == attendus, repr(err7))
check("R7b brut n'ecrit aucun fichier (espaces.json, client.json, comptes.json)", instantane() == avant,
      repr(set(instantane()) ^ set(avant)))
check("R7c fichiers suivis presents", "espaces.json" in avant and "comptes.json" in avant
      and str(pathlib.Path(c) / "client.json") in avant)
fch = E.dossier() / c / "client.json"
fch.write_bytes(bytes([0xFF, 0xFE]) + b"{pas du json ###")
avant = instantane()
try:
    pause, ex7, err = R.en_pause(p6), R.exigences(c, [ca], brut=True), None
except Exception as x:  # noqa: BLE001
    pause, ex7, err = None, None, x
check("R7d client.json corrompu : en_pause True, aucune exception", err is None and pause is True, repr(err))
check("R7e exigences brut : illisible, non couvert", isinstance(ex7, dict) and ex7.get("illisible") is True and ex7["client"] == c
      and ex7["non_couverts"] == ["X Lune"], repr(ex7))
check("R7f client.json corrompu laisse tel quel (rien mis de cote)", instantane() == avant)
check("R7g produit du client corrompu : en pause aussi", R.en_pause(post(pr, [cp], valide=MAINTENANT)) is True)
check("R7h marque : toujours libre malgre la fiche corrompue", R.en_pause(post(m, [cm])) is False)
fch.unlink()
(E.dossier() / "comptes.json").write_text("{casse", encoding="utf-8")
avant = instantane()
check("R7i comptes.json illisible : client en pause, marque libre, rien ecrit",
      R.en_pause(post(c2, [cc], confirme=c2)) is True and R.en_pause(post(m, [cm])) is False and instantane() == avant)

# t309 revue (26/10/2026) : espaces.json corrompu -> Deepotus part (espace vide OU « deepotus », valeur posee depuis t204),
# un post de client reste en pause, rien n'est ecrit.
fes = E.dossier() / "espaces.json"
octets_es = fes.read_bytes()
fes.write_text("{espaces casses", encoding="utf-8")
avant = instantane()
try:
    r7j = (R.en_pause(post("", [])), R.en_pause(post(None, [])), R.en_pause(post("deepotus", [])),
           R.exigences("deepotus", [cm], brut=True), R.controler(post("deepotus", []), brut=True), R.en_pause(post(c, [ca], valide=MAINTENANT)))
    err = None
except Exception as x:  # noqa: BLE001
    r7j, err = None, x
check("R7j espaces.json corrompu : Deepotus (vide, None, « deepotus ») pas en pause, client en pause",
      err is None and r7j == (False, False, False, None, None, True), repr((r7j, err)))
check("R7k espaces.json corrompu : rien ecrit, rien mis de cote", instantane() == avant)
fes.write_bytes(octets_es)
check("R7l « deepotus » sans regle aussi en lecture normale", R.exigences("deepotus", []) is None
      and R.controler(post("deepotus", [])) is None and R.statut_initial("deepotus", "draft") == "draft")

print("[R8] colonnes valide_client_le / confirme_client")
from app.services import storage as S                              # noqa: E402
nom_cols = [n for n, _t in S.SCHEDULED_POSTS_COLUMNS]
check("R8a SCHEDULED_POSTS_COLUMNS porte les deux colonnes", ("valide_client_le", "DATETIME") in S.SCHEDULED_POSTS_COLUMNS
      and ("confirme_client", "VARCHAR(40)") in S.SCHEDULED_POSTS_COLUMNS)
neuf = S.ScheduledPost(id="p-neuf", title="t", run_at=MAINTENANT)
check("R8b ScheduledPost neuf : None, None", getattr(neuf, "valide_client_le", "absent") is None
      and getattr(neuf, "confirme_client", "absent") is None)
# une base d'AVANT t309 : la table existe sans les deux colonnes ; init_db les ajoute (auto-ALTER) sans perdre la ligne
anciennes = [(n, t) for n, t in S.SCHEDULED_POSTS_COLUMNS if n not in ("valide_client_le", "confirme_client")]
cx = sqlite3.connect(_DB)
cx.execute("CREATE TABLE scheduled_posts (id VARCHAR(36) PRIMARY KEY, " + ", ".join(f"{n} {t}" for n, t in anciennes) + ")")
cx.execute("INSERT INTO scheduled_posts (id, title, channels, run_at, status, mode) VALUES "
           "('p-vieux', 'vieux', 'x', '2026-10-01 10:00:00', 'scheduled', 'auto')")
cx.commit(); cx.close()
asyncio.run(S.init_db())
cx = sqlite3.connect(_DB)
cols = {r[1] for r in cx.execute("PRAGMA table_info(scheduled_posts)")}
ligne = cx.execute("SELECT title, valide_client_le, confirme_client FROM scheduled_posts WHERE id='p-vieux'").fetchone() \
    if {"valide_client_le", "confirme_client"} <= cols else None
cx.close()
check("R8c base existante : auto-ALTER ajoute les colonnes, la ligne reste", ligne == ("vieux", None, None), repr((cols, ligne)))


async def _aller_retour():
    async with S.async_session_factory() as s:
        s.add(S.ScheduledPost(id="p-db", title="db", run_at=MAINTENANT, espace_id=c2, comptes=json.dumps([cc]),
                              confirme_client=c2))
        await s.commit()
    async with S.async_session_factory() as s:
        return await s.get(S.ScheduledPost, "p-db")
lu = asyncio.run(_aller_retour())
check("R8d aller-retour en base : confirme_client garde, valide_client_le None", lu.confirme_client == c2 and lu.valide_client_le is None)

print("[R9] L10 : messages traduits")
racine = _ICI.parent.parent
r = subprocess.run([sys.executable, str(racine / "scripts" / "i18n_l10_erreurs.py"), "--check"], cwd=str(racine),
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
check("R9a i18n_l10_erreurs.py --check code 0", r.returncode == 0, (r.stdout + r.stderr)[-600:])
from app.i18n import erreurs as L10                                  # noqa: E402
check("R9b consentement FR -> EN", L10.texte(str(e3), "en") == "no current consent from client “Lune SARL” for: TG Lune",
      L10.texte(str(e3), "en"))
check("R9c a_valider FR -> EN", L10.texte(str(e), "en") == "post awaiting approval by client “Lune SARL” before it can be scheduled",
      L10.texte(str(e), "en"))
check("R9d confirmation FR -> EN", L10.texte(str(e4), "en") == "confirm publishing on behalf of client “Studio Nord” on: x:222",
      L10.texte(str(e4), "en"))
check("R9e FR rendu tel quel", L10.texte(str(e3), "fr") == str(e3))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
