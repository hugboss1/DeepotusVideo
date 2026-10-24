# -*- coding: utf-8 -*-
"""t286 (24/10/2026, T11) : l'agent Campagnes OUVERT au compagnon mobile appairé (spec §7) et le PAQUET agent.

- hors boucle locale : un jeton d'appareil valide (401 sinon, garde extérieure de main.py) ; les écritures de l'agent
  rejoignent `_ECRITURES_OUVERTES` en GABARITS (`{cid}`, `{n}`), lus par `main._ecriture_ouverte` : aucune autre
  écriture ne s'ouvre (préfixe, segment vide, « .. ») ;
- une conversation créée depuis l'appareil a `origine == "telephone"` ; le message `utilisateur` envoyé depuis
  l'appareil porte `origine == "telephone"` et `appareil == <id de l'appareil du JETON>` (jamais un champ du corps) ;
- `GET /api/agent/campagnes/paquet?espace_id=` : docs/agent/campagnes/* + persona.json filtrée, version = sha256.
Vraies requêtes depuis une IP du réseau local avec un VRAI jeton (base jetable, `_jeton_appareil`). Le modèle est
SIMULÉ (`moteurs_texte._POSTER`), la clé est factice : aucun appel payant, aucun réseau.
Run : & $PY tests/test_agent_campagnes_appareil.py   (depuis backend/, PYTHONUTF8=1)."""
import asyncio, json, os, re, shutil, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# Parent PRIVÉ : le contrôle 7b regarde aussi au-dessus de DATA_ROOT (« ../x »), jamais dans le %TEMP% partagé où
# d'autres outils laissent leurs propres fichiers (un « x » y rendait le banc rouge sans aucune écriture de la route).
PARENT = tempfile.mkdtemp(prefix="dzt286_appareil_")
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
from sqlalchemy import func, select                                  # noqa: E402
from app.config import settings                                      # noqa: E402
import app.main as MAIN                                              # noqa: E402
from app.main import app                                             # noqa: E402
from app.api import agent_campagnes_routes as ACR                    # noqa: E402
from app.services import agent_campagnes as AC, espaces, moteurs_texte as MT, pricing   # noqa: E402
from app.services.storage import AgentConversation, async_session_factory, init_db       # noqa: E402
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


MODELE = "claude-banc"
CLE = "sk-ant-FACTICE-appareil"
BASE = "/api/agent/campagnes"
LAN = ("192.168.1.50", 5000)


class Rep:
    def __init__(self, d): self.status_code, self._d, self.text = 200, d, ""
    def json(self): return self._d


class Script:
    def __init__(self, reponses):
        self.reponses, self.corps = list(reponses), []

    def __call__(self, url, **kw):
        self.corps.append(json.loads(json.dumps(kw.get("json"))))
        if self.reponses:
            return Rep(self.reponses.pop(0))
        raise AssertionError("appel du modèle en trop")


def outil(nom, args, i=1000, o=200):
    return {"content": [{"type": "tool_use", "id": f"toolu_{nom}", "name": nom, "input": args}],
            "stop_reason": "tool_use", "usage": {"input_tokens": i, "output_tokens": o}}


def texte(t, i=1000, o=100):
    return {"content": [{"type": "text", "text": t}], "stop_reason": "end_turn",
            "usage": {"input_tokens": i, "output_tokens": o}}


def evenements(r):
    return [json.loads(x[5:].strip()) for x in r.text.splitlines() if x.startswith("data:")]


async def _nb_conversations():
    async with async_session_factory() as s:
        return (await s.execute(select(func.count()).select_from(AgentConversation))).scalar_one()


_CTX: dict = {}


def _contexte() -> dict:
    """Monté une fois : base jetable, espaces, clé factice, un appareil appairé (vrai jeton), deux clients."""
    if _CTX:
        return _CTX
    asyncio.run(init_db())
    pricing._PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
    pricing._PRICING_FILE.write_text(json.dumps({"llm_claude_usd_per_mtok": {MODELE: {"in": 0.5, "out": 2.5}}}),
                                     encoding="utf-8")
    settings.ANTHROPIC_API_KEY = CLE
    settings.AGENT_MODEL = MODELE
    a = espaces.creer({"nom": "Alpha"})["id"]
    b = espaces.creer({"nom": "Bravo"})["id"]
    z = espaces.creer({"nom": "Zulu archivé"})["id"]
    espaces.archiver(z)
    espaces.activer(a)                                   # l'espace ACTIF n'est jamais celui du paquet d'office
    loc = TestClient(app, client=("127.0.0.1", 50000))
    loc.__enter__()
    h = JA.entetes(app, LAN[0])
    moi = [x for x in loc.get("/api/devices").json()["appareils"] if not x["revoque"]][0]
    _CTX.update(A=a, B=b, Z=z, loc=loc, lan=TestClient(app, client=LAN), H=h, appareil=moi["id"])
    return _CTX


def _creer_pc(espace=None):
    c = _contexte()
    r = c["loc"].post(BASE + "/", json={"role": "campagnes", "espace_id": espace or c["B"], "titre": "PC"})
    assert r.status_code == 200, (r.status_code, r.text[:200])
    return r.json()["id"]


# ---- test_sans_jeton_hors_local_401 ----------------------------------------------------------------------------------
def test_sans_jeton_hors_local_401():
    avant = fail
    c = _contexte()
    print("\n[1] réseau local SANS jeton : 401, rien d'écrit")
    cid = _creer_pc()
    n0 = asyncio.run(_nb_conversations())
    s = Script([texte("jamais")]); MT._POSTER = s
    lan, faux = c["lan"], {"Authorization": "Bearer " + "0" * 64}
    rep = {
        "GET /{cid}": lan.get(f"{BASE}/{cid}").status_code,
        "GET /paquet": lan.get(f"{BASE}/paquet").status_code,
        "POST /": lan.post(BASE + "/", json={"role": "campagnes"}).status_code,
        "POST /{cid}/message": lan.post(f"{BASE}/{cid}/message", json={"texte": "x", "plafond_usd": 1}).status_code,
        "POST /{cid}/devis": lan.post(f"{BASE}/{cid}/devis", json={"texte": "x"}).status_code,
        "POST /{cid}/depot": lan.post(f"{BASE}/{cid}/depot", json={"texte": "x"}).status_code,
        "POST /importer": lan.post(f"{BASE}/importer", json={"conversation": {}}).status_code,
        "POST / (jeton faux)": lan.post(BASE + "/", json={"role": "campagnes"}, headers=faux).status_code,
    }
    check("1a toutes les routes de l'agent : 401 sans jeton valide", set(rep.values()) == {401}, str(rep))
    check("1b aucune conversation créée, aucun message, aucun appel du modèle",
          asyncio.run(_nb_conversations()) == n0 and c["loc"].get(f"{BASE}/{cid}").json()["messages"] == []
          and s.corps == [])
    assert fail == avant


# ---- test_avec_jeton_ok ----------------------------------------------------------------------------------------------
def test_avec_jeton_ok():
    avant = fail
    c = _contexte()
    lan, H = c["lan"], c["H"]
    print("\n[2] réseau local AVEC jeton : l'agent répond, rien d'autre ne s'ouvre")
    r = lan.post(BASE + "/", json={"role": "campagnes", "espace_id": c["B"], "titre": "Wi-Fi"}, headers=H)
    cid = r.json().get("id") if r.status_code == 200 else None
    check("2a POST / : 200, la conversation dans l'espace demandé", r.status_code == 200 and r.json().get("espace_id")
          == c["B"], f"{r.status_code} {r.text[:200]}")
    g = lan.get(f"{BASE}/{cid}", headers=H)
    check("2b GET /{cid} : 200", g.status_code == 200 and g.json().get("id") == cid, f"{g.status_code} {g.text[:200]}")
    d = lan.post(f"{BASE}/{cid}/devis", json={"texte": "Prépare la campagne."}, headers=H)
    check("2c POST /{cid}/devis : 200, un plafond", d.status_code == 200 and d.json().get("plafond_usd", 0) > 0,
          f"{d.status_code} {d.text[:200]}")
    MT._POSTER = Script([texte("Voici le plan.")])
    m = lan.post(f"{BASE}/{cid}/message", json={"texte": "Que faire ?", "plafond_usd": 1.0}, headers=H)
    check("2d POST /{cid}/message : 200 SSE jusqu'à fin (le tour tourne sur le PC)", m.status_code == 200
          and [e.get("type") for e in evenements(m)] == ["texte", "fin"], f"{m.status_code} {m.text[:200]}")
    p = lan.post(f"{BASE}/{cid}/depot", json={"texte": "Notes du téléphone", "nom": "notes"}, headers=H)
    check("2e POST /{cid}/depot : 200", p.status_code == 200 and p.json().get("caracteres") == 18,
          f"{p.status_code} {p.text[:200]}")
    i = lan.post(f"{BASE}/importer", json={"conversation": {"pas": "valide"}}, headers=H)
    check("2f POST /importer : atteint la route (400 de validation, pas 403)", i.status_code == 400,
          f"{i.status_code} {i.text[:200]}")
    hors = lan.post("/api/assets/3d", json={"engine": "tripo", "image_filename": "a.png"}, headers=H)
    check("2g une écriture HORS agent avec le même jeton : 403", hors.status_code == 403, f"{hors.status_code}")
    s = Script([texte("jamais")]); MT._POSTER = s
    n_av = len(c["loc"].get(f"{BASE}/{cid}").json()["messages"])
    pieges = {
        "suffixe": lan.post(f"{BASE}/{cid}/message/plus", json={"texte": "x", "plafond_usd": 1}, headers=H).status_code,
        "segment vide": lan.post(f"{BASE}//message", json={"texte": "x", "plafond_usd": 1}, headers=H).status_code,
        "carte sans n": lan.post(f"{BASE}/{cid}/carte/", json={"decision": "acceptee"}, headers=H).status_code,
        "devis/": lan.post(f"{BASE}/{cid}/devis/", json={"texte": "x"}, headers=H).status_code,
    }
    check("2h chemins piégés : 403 ou 404, jamais exécutés", all(v in (403, 404) for v in pieges.values())
          and s.corps == [] and len(c["loc"].get(f"{BASE}/{cid}").json()["messages"]) == n_av, str(pieges))
    check("2i le premier piège est refusé par la garde des écritures (403), pas seulement par le routage",
          pieges["suffixe"] == 403 and pieges["segment vide"] == 403, str(pieges))
    assert fail == avant


# ---- test_ecritures_listees_dans_mutations_appairage -----------------------------------------------------------------
def _exemple(gabarit: str) -> str:
    """Un chemin concret pour un gabarit : chaque `{x}` (ou `{x:int}`) devient un segment plausible."""
    return re.sub(r"\{[^}]+\}", "c1d2", gabarit)


def test_ecritures_listees_dans_mutations_appairage():
    avant = fail
    print("\n[3] chaque écriture de l'agent est listée, et rien de plus")
    ecritures = sorted({(m, "/api/agent/campagnes" + r.path) for r in ACR.router.routes
                        for m in (getattr(r, "methods", None) or ()) if m not in ("GET", "HEAD", "OPTIONS")})
    check("3a le routeur a ses six écritures", len(ecritures) == 6, str(ecritures))
    pas_ouvertes = [e for e in ecritures if not MAIN._ecriture_ouverte(e[0], _exemple(e[1]))]
    check("3b chacune est ouverte par main._ecriture_ouverte (sur un chemin concret)", not pas_ouvertes,
          str(pas_ouvertes))
    agent = {e for e in MAIN._ECRITURES_OUVERTES if e[1].startswith("/api/agent/")}
    check("3c aucune entrée orpheline : chaque gabarit agent de la liste est une vraie route",
          agent == set(ecritures), f"{sorted(agent)} != {ecritures}")
    ferme = MAIN._ecriture_ouverte
    refus = {
        "GET sur un gabarit POST": ferme("GET", "/api/agent/campagnes/c1/message"),
        "suffixe": ferme("POST", "/api/agent/campagnes/c1/message/plus"),
        "préfixe": ferme("POST", "/api/agent/campagnes/c1"),
        "segment vide": ferme("POST", "/api/agent/campagnes//message"),
        "barre finale": ferme("POST", "/api/agent/campagnes/c1/devis/"),
        "..": ferme("POST", "/api/agent/campagnes/../message"),
        ".": ferme("POST", "/api/agent/campagnes/./message"),
        "carte vide": ferme("POST", "/api/agent/campagnes/c1/carte/"),
        "autre arbre": ferme("POST", "/api/assets/c1/message"),
        "sans barre": ferme("POST", "/api/agent/campagnes"),
        "hors agent": ferme("POST", "/api/assets/3d"),
    }
    check("3d aucun autre chemin ne s'ouvre", not any(refus.values()), str({k: v for k, v in refus.items() if v}))
    check("3e les entrées exactes d'avant restent ouvertes, à l'identique",
          ferme("POST", "/api/pair/claim") and ferme("POST", "/api/avatar-live/recast/finaliser")
          and not ferme("POST", "/api/pair/claim/x"))
    assert fail == avant


# ---- test_paquet_versionne -------------------------------------------------------------------------------------------
def test_paquet_versionne():
    avant = fail
    c = _contexte()
    lan, H = c["lan"], c["H"]
    print("\n[4] le paquet agent")
    r = lan.get(f"{BASE}/paquet", headers=H)
    p = r.json() if r.status_code == 200 else {}
    f = p.get("fichiers") or {}
    check("4a GET /paquet (appareil) : 200, CAMPAGNES.md et format.md, en texte", r.status_code == 200
          and isinstance(f.get("CAMPAGNES.md"), str) and isinstance(f.get("format.md"), str)
          and "Campagnes" in f.get("CAMPAGNES.md", ""), f"{r.status_code} {r.text[:200]}")
    attendus = sorted(x.name for x in AC.DOCS.iterdir() if x.is_file() and not x.name.startswith("."))
    check("4b tous les fichiers de docs/agent/campagnes, noms simples, triés", list(f) == attendus,
          f"{list(f)} != {attendus}")
    check("4c sans espace_id : pas de persona (aucun repli sur l'espace actif)", "persona.json" not in f)
    check("4d version : 16 hex", isinstance(p.get("version"), str)
          and re.fullmatch(r"[0-9a-f]{16}", p["version"] or ""), str(p.get("version")))
    v0 = p.get("version")
    check("4e la même demande rend la même version",
          v0 and lan.get(f"{BASE}/paquet", headers=H).json().get("version") == v0)
    check("4f le PC lit aussi le paquet", v0 and c["loc"].get(f"{BASE}/paquet").json().get("version") == v0)
    brut = espaces.persona(c["B"])
    check("4g témoin : la persona de l'espace porte voice_ids et templates",
          "voice_ids" in brut and "templates" in brut, str(sorted(brut)))
    r = lan.get(f"{BASE}/paquet", params={"espace_id": c["B"]}, headers=H)
    fb = (r.json().get("fichiers") or {}) if r.status_code == 200 else {}
    try:
        pj = json.loads(fb.get("persona.json") or "null")
    except ValueError:
        pj = None
    check("4h avec espace_id : persona.json sans voice_ids ni templates, le reste à l'identique",
          isinstance(pj, dict) and "voice_ids" not in pj and "templates" not in pj
          and pj == {k: v for k, v in brut.items() if k not in ("templates", "voice_ids")},
          f"{r.status_code} {r.text[:300]}")
    check("4i persona.json : JSON trié, indenté, non échappé",
          fb.get("persona.json") == json.dumps(pj, ensure_ascii=False, indent=2, sort_keys=True))
    vb = r.json().get("version") if r.status_code == 200 else None
    check("4j la persona entre dans la version", vb and vb != v0)
    check("4k espace inconnu : 400", lan.get(f"{BASE}/paquet", params={"espace_id": "nulle-part"}, headers=H
                                             ).status_code == 400)
    check("4l espace archivé : 400", lan.get(f"{BASE}/paquet", params={"espace_id": c["Z"]}, headers=H
                                             ).status_code == 400)
    # la version suit les fichiers : une COPIE jetable du dossier, jamais docs/ du dépôt
    copie = pathlib.Path(TMP) / "paquet_copie"
    shutil.copytree(AC.DOCS, copie)
    docs0 = AC.DOCS
    try:
        AC.DOCS = copie
        va = lan.get(f"{BASE}/paquet", headers=H).json().get("version")
        check("4m même contenu dans un autre dossier : même version", v0 and va == v0, f"{va} {v0}")
        (copie / "format.md").write_text((copie / "format.md").read_text(encoding="utf-8") + "\nune ligne\n",
                                         encoding="utf-8")
        vm = lan.get(f"{BASE}/paquet", headers=H).json()
        check("4n un fichier change : la version change, le texte suit", vm.get("version") != v0
              and vm["fichiers"]["format.md"].endswith("une ligne\n"), str(vm.get("version")))
        (copie / "nouveau.md").write_text("x", encoding="utf-8")
        vn = lan.get(f"{BASE}/paquet", headers=H).json()
        check("4o un fichier ajouté : il est servi, la version change encore", vn["fichiers"].get("nouveau.md") == "x"
              and vn.get("version") not in (v0, vm.get("version")))
        (copie / ".format.md.swp").write_text("brouillon d'éditeur", encoding="utf-8")
        (copie / ".DS_Store").write_bytes(b"\x00\x01")
        vh = lan.get(f"{BASE}/paquet", headers=H).json()
        check("4q les fichiers cachés (« . ») ne sont pas servis et ne changent pas la version",
              not any(k.startswith(".") for k in vh.get("fichiers", {})) and vh.get("version") == vn.get("version"),
              str(sorted(vh.get("fichiers", {}))))
    finally:
        AC.DOCS = docs0
    pers = dict(espaces.persona(c["B"]))
    pers["nom"] = "Bravo renommée"
    espaces.ecrire_persona(c["B"], pers)
    vp = lan.get(f"{BASE}/paquet", params={"espace_id": c["B"]}, headers=H).json().get("version")
    check("4p la persona change : la version change", vp and vp != vb, f"{vp} {vb}")
    assert fail == avant


# ---- test_message_depuis_appareil_trace_l_appareil -------------------------------------------------------------------
def test_message_depuis_appareil_trace_l_appareil():
    avant = fail
    c = _contexte()
    lan, H, moi = c["lan"], c["H"], c["appareil"]
    print("\n[5] l'origine et l'appareil du JETON")
    r = lan.post(BASE + "/", json={"role": "campagnes", "espace_id": c["B"], "origine": "pc"}, headers=H)
    cid = r.json().get("id") if r.status_code == 200 else None
    check("5a conversation créée depuis l'appareil : origine telephone (le corps n'y peut rien)",
          r.status_code == 200 and r.json().get("origine") == "telephone"
          and c["loc"].get(f"{BASE}/{cid}").json().get("origine") == "telephone", r.text[:200])
    MT._POSTER = Script([texte("Bien reçu.")])
    m = lan.post(f"{BASE}/{cid}/message", json={"texte": "Depuis le canapé", "plafond_usd": 1.0,
                                                "appareil": "usurpe", "origine": "pc"}, headers=H)
    msgs = c["loc"].get(f"{BASE}/{cid}").json()["messages"]
    u = next((x for x in msgs if x["role"] == "utilisateur"), {})
    check("5b le message utilisateur : origine telephone, appareil = celui du JETON (usurpation ignorée)",
          m.status_code == 200 and u.get("origine") == "telephone" and u.get("appareil") == moi,
          f"{m.status_code} {json.dumps(u)[:200]} {moi}")
    check("5c la réponse de l'agent est calculée sur le PC (origine pc)",
          [x.get("origine") for x in msgs if x["role"] == "agent"] == ["pc"], str([x.get("origine") for x in msgs]))
    # une décision de carte prise sur le téléphone porte la même trace
    MT._POSTER = Script([outil("proposer_porte", {"resume": "Trois posts X.", "calendrier": ["J1"]})])
    lan.post(f"{BASE}/{cid}/message", json={"texte": "Lance", "plafond_usd": 1.0}, headers=H)
    d = lan.post(f"{BASE}/{cid}/carte/0", json={"decision": "acceptee", "appareil": "usurpe"}, headers=H)
    fait = c["loc"].get(f"{BASE}/{cid}").json()["messages"][-1]
    check("5d décision de carte depuis l'appareil : 200, le fait porte origine telephone et l'appareil du jeton",
          d.status_code == 200 and fait.get("role") == "fait" and fait.get("origine") == "telephone"
          and fait.get("appareil") == moi, f"{d.status_code} {json.dumps(fait)[:200]}")
    # témoin : le même chemin depuis le PC reste « pc », sans appareil
    cpc = _creer_pc()
    MT._POSTER = Script([texte("ok")])
    c["loc"].post(f"{BASE}/{cpc}/message", json={"texte": "Du bureau", "plafond_usd": 1.0, "appareil": "usurpe"})
    l = c["loc"].get(f"{BASE}/{cpc}").json()
    up = next((x for x in l["messages"] if x["role"] == "utilisateur"), {})
    check("5e témoin PC : conversation et message origine pc, appareil None", l.get("origine") == "pc"
          and up.get("origine") == "pc" and up.get("appareil") is None, json.dumps(up)[:200])
    assert fail == avant


# ---- test_import_depuis_appareil_trace_l_appareil --------------------------------------------------------------------
def test_import_depuis_appareil_trace_l_appareil():
    """Relecture t286 : un import venu d'un appareil ne choisit ni l'origine ni l'appareil. Toute entorse → 400, RIEN
    d'écrit (refus, jamais de réécriture : les empreintes restent idempotentes)."""
    import uuid
    from app.services import agent_format as fmt
    avant = fail
    c = _contexte()
    lan, H, moi, loc = c["lan"], c["H"], c["appareil"], c["loc"]
    print("\n[6] import depuis l'appareil : origine et appareil du JETON seulement")

    def msg(origine="telephone", appareil=None, t="Écrit dans le métro"):
        return fmt.nouveau_message("utilisateur", [{"type": "texte", "texte": t}], origine=origine,
                                   appareil=moi if appareil is None else appareil)

    def conv(messages, **k):
        return {"id": str(uuid.uuid4()), "role": "campagnes", "titre": "Hors ligne", "messages": messages, **k}

    cpc = _creer_pc()
    n0 = asyncio.run(_nb_conversations())
    cas = {
        "conversation origine pc": conv([msg()], origine="pc"),
        "message d'un autre appareil": conv([msg(appareil="autre-appareil")]),
        "message origine pc": conv([msg(origine="pc", appareil="")]),
        "message pc sans appareil": dict(conv([msg(), msg(origine="pc", appareil="")]), id=cpc),
    }
    for nom, cv in cas.items():
        r = lan.post(f"{BASE}/importer", json={"conversation": cv}, headers=H)
        check(f"6a {nom} : 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")
    check("6b rien d'écrit : aucune conversation créée, la conversation du PC intacte",
          asyncio.run(_nb_conversations()) == n0 and loc.get(f"{BASE}/{cpc}").json()["messages"] == [])
    bon = conv([msg(), msg(t="Deuxième")])
    r = lan.post(f"{BASE}/importer", json={"conversation": bon}, headers=H)
    l = loc.get(f"{BASE}/{bon['id']}").json()
    check("6c import valide (sans origine de conversation) : 2 ajoutés, conversation telephone",
          r.status_code == 200 and r.json().get("ajoutes") == 2 and l.get("origine") == "telephone"
          and [m.get("appareil") for m in l.get("messages", [])] == [moi, moi], f"{r.status_code} {r.text[:200]}")
    r = lan.post(f"{BASE}/importer", json={"conversation": bon}, headers=H)
    check("6d ré-import : idempotent (0 ajouté, 2 ignorés)", r.status_code == 200 and r.json().get("ajoutes") == 0
          and r.json().get("ignores") == 2 and len(loc.get(f"{BASE}/{bon['id']}").json()["messages"]) == 2,
          r.text[:200])
    r = lan.post(f"{BASE}/importer", json={"conversation": dict(conv([msg()], origine="telephone"), id=cpc)},
                 headers=H)
    check("6e des messages valides du téléphone rejoignent une conversation créée sur le PC",
          r.status_code == 200 and r.json().get("ajoutes") == 1
          and len(loc.get(f"{BASE}/{cpc}").json()["messages"]) == 1, f"{r.status_code} {r.text[:200]}")
    r = loc.post(f"{BASE}/importer", json={"conversation": conv([msg(origine="pc", appareil="")], origine="pc")})
    check("6f témoin PC : l'import du PC reste libre (origine pc acceptée)", r.status_code == 200
          and r.json().get("ajoutes") == 1, f"{r.status_code} {r.text[:200]}")
    assert fail == avant


# ---- test_import_id_hostile_400 --------------------------------------------------------------------------------------
def test_import_id_hostile_400():
    """Relecture finale t286 : l'id d'une conversation importée devient un DOSSIER (_conversations/<id>/). Seul un UUID
    canonique en minuscules passe ; « ../x », un chemin absolu, « paquet » (masqué par GET /paquet) → 400, rien
    d'écrit."""
    import uuid
    from app import config
    from app.services import agent_format as fmt
    avant = fail
    c = _contexte()
    lan, H, moi, loc = c["lan"], c["H"], c["appareil"], c["loc"]
    print("\n[7] import : l'id de conversation est un UUID canonique, jamais un chemin")
    dehors = pathlib.Path(TMP).parent / ("dzt286_evasion_" + uuid.uuid4().hex[:8])
    absolu = str(dehors / "abs")
    ids = {"../x": "../x", "../../../x": "../../../" + dehors.name, "absolu": absolu, "paquet": "paquet",
           "majuscules": str(uuid.uuid4()).upper(), "sans tirets": uuid.uuid4().hex,
           "accolades": "{" + str(uuid.uuid4()) + "}", "vide": "", "nombre": 42}
    n0 = asyncio.run(_nb_conversations())
    racine = config.DATA_ROOT / "campagnes" / "_conversations"
    avant_dossiers = sorted(p.name for p in racine.iterdir()) if racine.is_dir() else []
    m = fmt.nouveau_message("utilisateur", [{"type": "texte", "texte": "x"}], origine="telephone", appareil=moi)
    rep = {}
    for nom, cid in ids.items():
        cv = {"id": cid, "role": "campagnes", "messages": [m]}
        rep[nom] = (lan.post(f"{BASE}/importer", json={"conversation": cv}, headers=H).status_code,
                    loc.post(f"{BASE}/importer", json={"conversation": cv}).status_code)
    check("7a appareil ET PC : 400 pour chaque id hostile ou non canonique", all(v == (400, 400) for v in rep.values()),
          str(rep))
    apres_dossiers = sorted(p.name for p in racine.iterdir()) if racine.is_dir() else []
    check("7b rien d'écrit : aucune ligne en base, aucun dossier sous _conversations, rien hors de DATA_ROOT",
          asyncio.run(_nb_conversations()) == n0 and apres_dossiers == avant_dossiers and not dehors.exists()
          and not (pathlib.Path(TMP).parent / "x").exists() and not (config.DATA_ROOT / "campagnes" / "x").exists(),
          f"{apres_dossiers} {dehors.exists()}")
    bon = str(uuid.uuid4())
    r = lan.post(f"{BASE}/importer", json={"conversation": {"id": bon, "role": "campagnes", "messages": [m]}},
                 headers=H)
    check("7c témoin : un UUID canonique passe", r.status_code == 200 and r.json().get("ajoutes") == 1
          and (racine / bon / "conversation.json").is_file(), f"{r.status_code} {r.text[:200]}")
    assert fail == avant


# ---- test_depot_multipart_sans_longueur_413 --------------------------------------------------------------------------
def test_depot_multipart_sans_longueur_413():
    """Relecture finale t286 : un multipart SANS Content-Length (chunked) est borné en LISANT le flux : 413 dès la
    limite franchie, quelle que soit la part (même une part qui n'est pas « fichier »)."""
    avant = fail
    c = _contexte()
    lan, H = c["lan"], c["H"]
    print("\n[8] dépôt multipart en flux (chunked) : borné à la lecture")
    cid = _creer_pc()
    b = "dzborne286"

    def corps(champ, taille, nom="gros.txt"):
        yield (f"--{b}\r\nContent-Disposition: form-data; name=\"{champ}\"; filename=\"{nom}\"\r\n"
               f"Content-Type: text/plain\r\n\r\n").encode()
        reste = taille
        while reste > 0:
            n = min(reste, 16 * 1024)
            yield b"a" * n
            reste -= n
        yield f"\r\n--{b}--\r\n".encode()

    entetes = dict(H, **{"Content-Type": f"multipart/form-data; boundary={b}"})
    max0 = ACR.MAX_DEPOT_OCTETS
    try:
        ACR.MAX_DEPOT_OCTETS = 4 * 1024                  # la limite réelle est 15 Mo : on la réduit pour le banc
        r = lan.post(f"{BASE}/{cid}/depot", content=corps("autre", 200 * 1024), headers=entetes)
        check("8a part hors « fichier », trop lourde, sans Content-Length : 413 (pas lue jusqu'au bout)",
              r.status_code == 413 and "15 Mo" in r.text, f"{r.status_code} {r.text[:200]}")
        r = lan.post(f"{BASE}/{cid}/depot", content=corps("fichier", 200 * 1024), headers=entetes)
        check("8b fichier trop lourd sans Content-Length : 413", r.status_code == 413,
              f"{r.status_code} {r.text[:200]}")
        r = lan.post(f"{BASE}/{cid}/depot", content=corps("fichier", 1000), headers=entetes)
        check("8c témoin : un petit fichier en flux passe (200)", r.status_code == 200
              and r.json().get("caracteres") == 1000, f"{r.status_code} {r.text[:200]}")
        r = lan.post(f"{BASE}/{cid}/depot", content=iter([b"--pas-un-multipart"]), headers=entetes)
        check("8d multipart illisible : 400, jamais 500", r.status_code == 400, f"{r.status_code} {r.text[:200]}")
    finally:
        ACR.MAX_DEPOT_OCTETS = max0
    assert fail == avant


def _lanceur() -> int:
    global fail
    tests = [test_sans_jeton_hors_local_401, test_avec_jeton_ok, test_ecritures_listees_dans_mutations_appairage,
             test_paquet_versionne, test_message_depuis_appareil_trace_l_appareil,
             test_import_depuis_appareil_trace_l_appareil, test_import_id_hostile_400,
             test_depot_multipart_sans_longueur_413]
    for t in tests:
        try:
            t()
        except AssertionError:
            pass                                          # déjà compté par check
        except Exception as e:                            # noqa: BLE001 — un banc qui plante est un échec
            fail += 1
            print(f"  FAIL  {t.__name__} a levé {e!r}")
    if _CTX:
        _CTX["loc"].__exit__(None, None, None)
    shutil.rmtree(PARENT, ignore_errors=True)
    print(f"\n{ok} ok, {fail} fail")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_lanceur())
