# -*- coding: utf-8 -*-
"""L4.1 T1 (25/10/2026) : le PAQUET AGENT du téléphone, versionné — GET /api/agent/campagnes/paquet?avec=telephone.

Le téléphone fait tourner la même boucle que le PC hors ligne : il reçoit le catalogue (fiches allégées), les poids et
mots vides de la recherche, le texte exact du système par rôle, les cinq outils qu'il sait exécuter, le modèle et les
constantes. Aucune écriture : seulement un GET (la liste figée des écritures ouvertes ne bouge pas).
- p1 sans `avec`, la réponse est celle d'avant ; p2 catalogue = fiches non retirées, champs du PC retirés ;
- p3 le système est celui de la boucle ; p4 les cinq outils ; p5 ETag/304 ; p6 jeton d'appareil / 401 ; p7 persona.
Vraies requêtes (base jetable, `_jeton_appareil`). Aucun appel du modèle, aucun réseau.
Run : & $PY tests/test_agent_paquet_telephone.py   (depuis backend/, PYTHONUTF8=1)."""
import asyncio, json, os, re, shutil, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PARENT = tempfile.mkdtemp(prefix="dzl41_paquet_")
TMP = os.path.join(PARENT, "data")
os.makedirs(TMP)
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
for _k in ("ANTHROPIC_MODEL", "AGENT_MODEL", "ANTHROPIC_API_KEY"):
    os.environ.pop(_k, None)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

from fastapi.testclient import TestClient                           # noqa: E402
from app.config import settings                                      # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import agent_aide, agent_campagnes as AC, agent_outils as AO, espaces, moteurs_texte as MT  # noqa: E402
from app.services.storage import init_db                             # noqa: E402
import _jeton_appareil as JA                                         # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


BASE = "/api/agent/campagnes"
LAN = ("192.168.1.50", 5000)
OUTILS_TEL = ["chercher_app", "lire_espace", "lire_document", "proposer_porte", "deviser_generation"]
CHAMPS_PC = ("localisateur", "sources", "cadre", "icone", "empreinte", "etat", "ecran_fixe")
_CTX: dict = {}


def _contexte() -> dict:
    if _CTX:
        return _CTX
    asyncio.run(init_db())
    settings.AGENT_MODEL = "claude-banc"
    a = espaces.creer({"nom": "Alpha"})["id"]
    b = espaces.creer({"nom": "Bravo"})["id"]
    espaces.activer(a)
    loc = TestClient(app, client=("127.0.0.1", 50000))
    loc.__enter__()
    h = JA.entetes(app, LAN[0])
    _CTX.update(A=a, B=b, loc=loc, lan=TestClient(app, client=LAN), H=h)
    return _CTX


def _fiches_attendues() -> list:
    out = []
    for f in sorted(agent_aide.CATALOGUE.glob("*.json")):
        if f.name.startswith("_"):
            continue
        out += [x for x in json.loads(f.read_text(encoding="utf-8"))["fiches"] if x.get("etat") != "retire"]
    return out


def _tel(c, **q):
    q = dict({"avec": "telephone", "espace_id": c["B"], "langue": "fr"}, **q)
    return c["loc"].get(BASE + "/paquet", params=q)


# ---- p1 --------------------------------------------------------------------------------------------------------------
def test_p1_sans_avec_inchange():
    avant = fail
    c = _contexte()
    print("\n[p1] sans « avec » : la réponse d'avant")
    r = c["loc"].get(BASE + "/paquet", params={"espace_id": c["B"]})
    p = r.json()
    check("p1a clés : version et fichiers, rien d'autre", r.status_code == 200 and sorted(p) == ["fichiers", "version"],
          str(sorted(p)))
    check("p1b version : 16 hex", re.fullmatch(r"[0-9a-f]{16}", p.get("version", "")) is not None)
    check("p1c pas d'ETag sans « avec »", "etag" not in r.headers)
    t = _tel(c).json()
    check("p1d « avec » : les fichiers d'avant s'y trouvent toujours, la version diffère",
          t.get("fichiers") == p["fichiers"] and t.get("version") != p["version"])
    check("p1e « avec » inconnu : réponse d'avant",
          sorted(c["loc"].get(BASE + "/paquet", params={"avec": "x"}).json()) == ["fichiers", "version"])
    assert fail == avant


# ---- p2 --------------------------------------------------------------------------------------------------------------
def test_p2_catalogue():
    avant = fail
    c = _contexte()
    print("\n[p2] le catalogue allégé")
    p = _tel(c).json()
    cat = p.get("catalogue") or []
    att = _fiches_attendues()
    check("p2a autant de fiches que de fiches non retirées des fichiers non « _ »",
          len(cat) == len(att) and len(att) > 100, f"{len(cat)} != {len(att)}")
    check("p2b mêmes ids", sorted(x["id"] for x in cat) == sorted(x["id"] for x in att))
    check("p2c aucun champ du PC (localisateur, sources, cadre, icone, empreinte)",
          not any(k in x for x in cat for k in CHAMPS_PC))
    cles = {"id", "ecran", "type", "libelle", "infobulle", "role", "synonymes", "guide"}
    check("p2d chaque fiche a exactement les huit clés", all(set(x) == cles for x in cat))
    f0 = next(x for x in cat if x["role"]["fr"])
    check("p2e libellé/infobulle/rôle {fr,en}, synonymes {fr:[],en:[]}",
          all(set(f0[k]) == {"fr", "en"} for k in ("libelle", "infobulle", "role", "synonymes"))
          and isinstance(f0["synonymes"]["fr"], list))
    check("p2f mots_vides = ceux d'agent_aide", sorted(p.get("mots_vides") or []) == sorted(agent_aide.MOTS_VIDES))
    check("p2g poids = ceux d'agent_aide", p.get("poids") == {k: v for k, v in agent_aide.POIDS}, str(p.get("poids")))
    # le catalogue réel n'a aucune fiche retirée : un dossier jetable en porte une (et un fichier « _ » à ignorer)
    cat0, jetable = agent_aide.CATALOGUE, pathlib.Path(TMP) / "catalogue_copie"
    shutil.copytree(cat0, jetable)
    base = {"ecran": "quick", "type": "bouton", "libelle": {"fr": "x", "en": "x"}, "infobulle": {"fr": "", "en": ""},
            "role": {"fr": "x", "en": "x"}, "synonymes": {"fr": [], "en": []}, "guide": None, "etat": "redige"}
    (jetable / "zz_banc.json").write_text(json.dumps({"ecran": "quick", "fiches": [
        dict(base, id="banc.retiree", etat="retire"), dict(base, id="banc.vivante")]}), encoding="utf-8")
    (jetable / "_banc.json").write_text(json.dumps({"ecran": "quick", "fiches": [dict(base, id="banc.cachee")]}),
                                        encoding="utf-8")
    try:
        agent_aide.CATALOGUE = jetable
        agent_aide.catalogue.cache_clear(); agent_aide._index.cache_clear()
        ids = {x["id"] for x in _tel(c).json()["catalogue"]}
        check("p2h une fiche retirée n'est pas servie, une vivante l'est, un fichier « _ » est ignoré",
              "banc.vivante" in ids and "banc.retiree" not in ids and "banc.cachee" not in ids, str(sorted(
                  i for i in ids if i.startswith("banc."))))
    finally:
        agent_aide.CATALOGUE = cat0
        agent_aide.catalogue.cache_clear(); agent_aide._index.cache_clear()
    assert fail == avant


# ---- p3 --------------------------------------------------------------------------------------------------------------
def test_p3_systeme():
    avant = fail
    c = _contexte()
    print("\n[p3] le système : celui de la boucle")
    for lg in ("fr", "en"):
        s = _tel(c, langue=lg).json().get("systeme") or {}
        check(f"p3a ({lg}) trois rôles", sorted(s) == ["campagnes", "demonstrateur", "orienteur"], str(sorted(s)))
        check(f"p3b ({lg}) systeme[campagnes] == systeme_pour",
              s.get("campagnes") == AC.systeme_pour("campagnes", c["B"], lg))
        check(f"p3c ({lg}) les deux autres rôles aussi", s.get("orienteur") == AC.systeme_pour("orienteur", c["B"], lg)
              and s.get("demonstrateur") == AC.systeme_pour("demonstrateur", c["B"], lg))
    conv = {"role": "campagnes", "espace_id": c["B"]}
    check("p3d la boucle garde le même texte (systeme == systeme_pour)",
          AC.systeme(conv, "fr") == AC.systeme_pour("campagnes", c["B"], "fr")
          and AC.systeme(conv, "en") == AC.systeme_pour("campagnes", c["B"], "en"))
    fr = _tel(c, langue="fr").json()["systeme"]["campagnes"]
    en = _tel(c, langue="en").json()["systeme"]["campagnes"]
    check("p3e la langue change le texte", "Réponds en français." in fr and "Answer in English." in en)
    check("p3f un autre espace change le texte",
          _tel(c, espace_id=c["A"]).json()["systeme"]["campagnes"] != AC.systeme_pour("campagnes", c["B"], "fr"))
    assert fail == avant


# ---- p4 --------------------------------------------------------------------------------------------------------------
def test_p4_outils():
    avant = fail
    c = _contexte()
    print("\n[p4] les cinq outils du téléphone")
    p = _tel(c).json()
    o = p.get("outils") or []
    check("p4a les cinq noms, dans l'ordre", [x["name"] for x in o] == OUTILS_TEL, str([x.get("name") for x in o]))
    check("p4b chacun : description et input_schema objet", all(isinstance(x["description"], str) and x["description"]
          and x["input_schema"].get("type") == "object" for x in o))
    ref = {d["name"]: d for d in AO.definitions()}
    check("p4c schémas identiques à la table d'agent_outils (rien de recopié)", all(x == ref[x["name"]] for x in o))
    check("p4d modèle = celui du PC", p.get("modele") == MT.modele_agent() == "claude-banc", str(p.get("modele")))
    check("p4e constantes", p.get("constantes") == {"MAX_TOURS": AC.MAX_TOURS, "SORTIE_MAX": AC.SORTIE_MAX,
          "CARS_PAR_JETON": AC.CARS_PAR_JETON, "SURCOUT_OUTILS": AC.SURCOUT_OUTILS}, str(p.get("constantes")))
    check("p4f genere_a : ISO", re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+(Z|\+00:00)", p.get("genere_a", "")) is not None,
          str(p.get("genere_a")))
    assert fail == avant


# ---- p5 --------------------------------------------------------------------------------------------------------------
def test_p5_etag_304():
    avant = fail
    c = _contexte()
    print("\n[p5] ETag et 304")
    q = {"avec": "telephone", "espace_id": c["B"], "langue": "fr"}
    r = _tel(c)
    v = r.json()["version"]
    check("p5a ETag = version", r.headers.get("etag") == v, str(r.headers.get("etag")))
    r2 = c["loc"].get(BASE + "/paquet", params=q, headers={"If-None-Match": v})
    check("p5b If-None-Match égal : 304 sans corps", r2.status_code == 304 and r2.content == b"",
          f"{r2.status_code} {r2.content[:50]}")
    r3 = c["loc"].get(BASE + "/paquet", params=q, headers={"If-None-Match": '"' + v + '"'})
    check("p5c la forme entre guillemets est reconnue aussi", r3.status_code == 304)
    r4 = c["loc"].get(BASE + "/paquet", params=q, headers={"If-None-Match": "0" * 16})
    check("p5d autre version : 200 avec corps", r4.status_code == 200 and r4.json()["version"] == v)
    check("p5e la version ne dépend pas de genere_a (deux appels, même version)", _tel(c).json()["version"] == v)
    check("p5f la langue change la version", _tel(c, langue="en").json()["version"] != v)
    check("p5g l'espace change la version", _tel(c, espace_id=c["A"]).json()["version"] != v)
    docs0 = AC.DOCS
    copie = pathlib.Path(TMP) / "docs_copie"
    shutil.copytree(AC.DOCS, copie)
    try:
        AC.DOCS = copie
        (copie / "format.md").write_text((copie / "format.md").read_text(encoding="utf-8") + "\nune ligne\n",
                                         encoding="utf-8")
        check("p5h le texte du système entre dans la version", _tel(c).json()["version"] != v)
    finally:
        AC.DOCS = docs0
    assert fail == avant


# ---- p6 --------------------------------------------------------------------------------------------------------------
def test_p6_jeton():
    avant = fail
    c = _contexte()
    print("\n[p6] jeton d'appareil")
    q = {"avec": "telephone", "espace_id": c["B"], "langue": "fr"}
    r = c["lan"].get(BASE + "/paquet", params=q, headers=c["H"])
    check("p6a appareil avec jeton : 200, catalogue présent",
          r.status_code == 200 and len(r.json().get("catalogue", [])) > 100, str(r.status_code))
    check("p6b LAN sans jeton : 401", c["lan"].get(BASE + "/paquet", params=q).status_code == 401)
    check("p6c espace inconnu : 400",
          c["loc"].get(BASE + "/paquet", params=dict(q, espace_id="nulle-part")).status_code == 400)
    assert fail == avant


# ---- p7 --------------------------------------------------------------------------------------------------------------
def test_p7_persona():
    avant = fail
    c = _contexte()
    print("\n[p7] persona filtrée")
    p = _tel(c).json()
    pj = json.loads(p["fichiers"]["persona.json"])
    check("p7a persona.json : ni templates ni voice_ids", "templates" not in pj and "voice_ids" not in pj)
    brut = espaces.persona(c["B"])
    check("p7b témoin : la persona brute les porte", "templates" in brut and "voice_ids" in brut)
    check("p7c le système n'en dit rien non plus", '"templates"' not in p["systeme"]["campagnes"]
          and '"voice_ids"' not in p["systeme"]["campagnes"])
    assert fail == avant


# ---- p8 --------------------------------------------------------------------------------------------------------------
def test_p8_espace_actif():
    avant = fail
    c = _contexte()
    print("\n[p8] sans espace_id : l'espace ACTIF du PC")
    r = c["loc"].get(BASE + "/paquet", params={"avec": "telephone", "langue": "fr"})
    p = r.json()
    check("p8a 200 et espace_id = l'espace actif", r.status_code == 200 and p.get("espace_id") == c["A"] == espaces.actif()["id"],
          str(p.get("espace_id")))
    ref = _tel(c, espace_id=c["A"]).json()
    pj = json.loads(p["fichiers"]["persona.json"])
    check("p8b persona.json = celle de l'espace actif, filtrée",
          p["fichiers"]["persona.json"] == ref["fichiers"]["persona.json"] and "templates" not in pj and "voice_ids" not in pj)
    check("p8c systeme = celui de l'espace actif", p["systeme"]["campagnes"] == AC.systeme_pour("campagnes", c["A"], "fr")
          and p["systeme"] == ref["systeme"])
    check("p8d espace_id explicite : renvoyé tel quel", ref.get("espace_id") == c["A"] and _tel(c).json().get("espace_id") == c["B"])
    check("p8e le bouton du LAN avec jeton aussi", c["lan"].get(BASE + "/paquet", params={"avec": "telephone"},
          headers=c["H"]).json().get("espace_id") == c["A"])
    sans = c["loc"].get(BASE + "/paquet").json()
    check("p8f sans « avec » : toujours pas de persona d'office", "persona.json" not in sans["fichiers"] and "espace_id" not in sans)
    assert fail == avant


def _lanceur() -> int:
    global fail
    tests = [test_p1_sans_avec_inchange, test_p2_catalogue, test_p3_systeme, test_p4_outils, test_p5_etag_304,
             test_p6_jeton, test_p7_persona, test_p8_espace_actif]
    for t in tests:
        try:
            t()
        except AssertionError:
            pass
        except Exception as e:                            # noqa: BLE001 — un banc qui plante est un échec
            global_fail = 1
            fail += global_fail
            print(f"  FAIL  {t.__name__} a levé {e!r}")
    if _CTX:
        _CTX["loc"].__exit__(None, None, None)
    shutil.rmtree(PARENT, ignore_errors=True)
    print(f"\n{ok} ok, {fail} fail")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_lanceur())
