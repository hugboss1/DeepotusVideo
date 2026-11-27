# -*- coding: utf-8 -*-
"""t498 (lot G8 « boucle de croissance », 26/11/2026) — recycler un GAGNANT : carrousel, accroches, fil X, branche.

[A] pur         le gabarit d'une diapo (4:5, texte posé, échantillon), l'espacement de 7 jours entre deux pièces
[B] proposer    refus sous le seuil, post inconnu ; quatre CARTES de devis, gratuites (aucun appel), raisons codées
[C] rédiger     accord, coût changé AVANT l'appel, garde « campagnes », mots interdits relevés, payé une fois
[D] brouillons  canaux du projet, brief.recycle_de, recycled_from, 7 jours d'écart, carrousel Instagram, fil X,
                branche jamais en brouillon, client « validé par le client » -> a_valider, JAMAIS de mode auto
[E] routes      /api/recyclage : codes, boucle locale
[F] source      aucun appel nu au modèle ; l'accord précède l'appel
Data-dir temporaire, faux Claude (httpx.post remplacé), rendu des diapos remplacé, aucun réseau.
Run : & $PY tests/test_croissance_recyclage.py   (depuis backend/)"""
import asyncio, io, json, os, pathlib, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrecy_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image                                               # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import plafonds as PL                             # noqa: E402
from app.services import espaces, comptes, fiche_client, storage    # noqa: E402
from app.services import library_projects as LP                     # noqa: E402
from app.services import template_layout as TL                      # noqa: E402
from app.services.storage import ScheduledPost, PostMetric, async_session_factory  # noqa: E402
from app.services import recyclage as RC                            # noqa: E402

settings.ANTHROPIC_API_KEY = "cle-de-banc"
settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
_loop = asyncio.new_event_loop()
def run(c):
    return _loop.run_until_complete(c)


def erreur(coro):
    try:
        run(coro); return None
    except Exception as e:  # noqa: BLE001
        return e


# ---- [A] pur ---------------------------------------------------------------------------------------------------------
print("[A] pur")
TPL = {"id": "tpl_t", "name": "T", "canvas": {"width": 1080, "height": 1920, "fps": 30, "duration_s": 8},
       "regions": [{"id": "r1", "type": "video_slot", "x": 0, "y": 0, "width": 1080, "height": 1920, "slot_name": "fond"},
                   {"id": "r2", "type": "text_slot", "x": 64, "y": 1650, "width": 952, "height": 120,
                    "slot_name": "legende", "default_text": "x", "max_chars": 40}],
       "metadata": {}}
g = RC._gabarit_diapo(TPL, "Un point par volet", "fond.png")
check("A1 la diapo est au format du carrousel (4:5), le gabarit d'origine intact",
      TL.format_de(g) == RC.FORMAT_CARROUSEL == "4:5" and TL.format_de(TPL) == "9:16", str(g.get("canvas")))
txt = [r for r in g["regions"] if r["type"] == "text_slot"]
check("A2 le texte de la diapo est posé dans la PREMIÈRE case de texte, sa borne relevée",
      txt[0]["default_text"] == "Un point par volet" and txt[0]["max_chars"] >= len("Un point par volet"), str(txt))
check("A3 l'image du post gagnant devient l'échantillon de la case image", g["metadata"]["samples"] == {"fond": "fond.png"})
check("A4 sans image : aucun échantillon (la mire du gabarit)", "samples" not in (RC._gabarit_diapo(TPL, "a", None).get("metadata") or {}))
D0 = datetime(2026, 12, 1, 9, 0)
check("A5 deux pièces tirées du même gagnant : 7 jours d'écart au moins",
      [RC._quand(D0, k) for k in range(3)] == [D0, D0 + timedelta(days=7), D0 + timedelta(days=14)])
check("A6 cinq éléments, dans l'ordre de la spec (t500 : + x_video)", RC.ELEMENTS == ("carrousel", "accroches", "fil_x", "branche", "x_video"))

# ---- données ---------------------------------------------------------------------------------------------------------
APPELS = []
REP = {}


class _Rep:
    status_code = 200
    text = ""
    def __init__(self, txt): self._t = txt
    def json(self): return {"content": [{"type": "text", "text": self._t}], "usage": {"input_tokens": 10, "output_tokens": 10}}


def faux_post(url, headers=None, json=None, timeout=None, verify=None):
    APPELS.append(json)
    s = str(json.get("system"))
    for el in RC.ELEMENTS:
        if RC.MARQUES[el] in s:
            return _Rep(REP[el])
    return _Rep("{}")


REP["accroches"] = json.dumps({"accroches": ["Avant 7 h, tout se joue", "Le geste gratuit du matin", "Ce que le four sait"]},
                              ensure_ascii=False)
REP["fil_x"] = json.dumps({"fil": ["1/ Le pain se fait la veille.", "2/ Le levain dort 12 h.", "3/ Le four chauffe à 4 h."]},
                          ensure_ascii=False)
REP["carrousel"] = json.dumps({"diapos": ["Le levain", "La pâte", "Le façonnage", "La cuisson", "Le partage"],
                               "legende": "Cinq étapes, un pain."}, ensure_ascii=False)
REP["branche"] = json.dumps({"accroche": "Et si on refaisait tout ?", "voix": "Chaque nuit, la même patience.",
                             "textes": ["La nuit", "Le levain", "Le matin"]}, ensure_ascii=False)

run(storage.init_db())
espaces.lire()
EA = espaces.creer({"nom": "Atelier Soleil"})["id"]
EB = espaces.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
fiche_client.ecrire(EB, {"societe": "Lune SARL"})
p = espaces.persona(EA)
p["ecran"] = {"banned": ["gratuit"]}
espaces.ecrire_persona(EA, p)
ig_a = comptes.creer({"espace_id": EA, "plateforme": "instagram", "libelle": "IG Soleil"})["id"]
x_a = comptes.creer({"espace_id": EA, "plateforme": "x", "libelle": "X Soleil"})["id"]
ig_b = comptes.creer({"espace_id": EB, "plateforme": "instagram", "libelle": "IG Lune"})["id"]
with espaces.sous_espace(EA):
    pa = run(LP.creer("Projet Soleil"))
    run(LP.poser_actif(pa["id"]))
run(LP.poser_canaux(pa["id"], [ig_a, x_a]))
with espaces.sous_espace(EB):
    pb = run(LP.creer("Projet Lune"))
    run(LP.poser_actif(pb["id"]))
run(LP.poser_canaux(pb["id"], [ig_b]))

NOW = datetime.utcnow().replace(microsecond=0)
Image.new("RGB", (64, 80), (200, 120, 40)).save(_tmp / "images" / "visuel_gagnant.png")


def _m(pid, at, views):
    return PostMetric(id=f"{pid}-{at.isoformat()}", post_id=pid, channel="instagram", remote_id="r" + pid, fetched_at=at,
                      views=views, likes=0, comments=0, shares=0, saves=0)


async def seed():
    async with async_session_factory() as s:
        for eid, pre in ((EA, "a"), (EB, "b")):
            for i in range(6):                                       # six reels anciens : J1 = 100 vues
                d = NOW - timedelta(days=20 + i)
                s.add(ScheduledPost(id=f"{pre}{i}", title=f"Ancien {i}", channels="instagram", run_at=d, status="posted",
                                    posted_at=d, format="reel", espace_id=eid))
                s.add(_m(f"{pre}{i}", d + timedelta(days=1, hours=1), 100))
            d = NOW - timedelta(days=8)                              # le gagnant : J1 = 600, 6× l'habituel
            s.add(ScheduledPost(id=f"{pre}g", title="Le pain de la nuit", caption="Notre pain dort toute la nuit.",
                                hook="Le secret, c'est la nuit", script_idea="La nuit, le levain travaille.",
                                channels="instagram", run_at=d, status="posted", posted_at=d, format="reel",
                                job_id=f"job-{pre}", source_image="visuel_gagnant.png", espace_id=eid,
                                brief=json.dumps({"hashtags": ["#pain"]})))
            s.add(_m(f"{pre}g", d + timedelta(days=1, hours=2), 600))
        d = NOW - timedelta(days=9)                                  # un moyen : J1 = 150, 1,5×
        s.add(ScheduledPost(id="moyen", title="Moyen", channels="instagram", run_at=d, status="posted", posted_at=d,
                            format="reel", espace_id=EA))
        s.add(_m("moyen", d + timedelta(days=1, hours=3), 150))
        await s.commit()
run(seed())

_post0 = MT.httpx.post
MT.httpx.post = faux_post
_verif0 = PL.verifier
GARDES = []
async def verif_trace(op, categorie="", ref=None, *a, **k):
    GARDES.append(categorie)
    return await _verif0(op, categorie, ref, *a, **k)
PL.verifier = verif_trace
RENDUS = []
def faux_rendu(tpl, texte, fond):
    nom = f"recy_banc_{len(RENDUS)}.jpg"
    Image.new("RGB", (1080, 1350), (20, 20, 20)).save(_tmp / "images" / nom, "JPEG")
    RENDUS.append((tpl.get("id"), texte, fond))
    return nom
RC._rendre_diapo = faux_rendu
try:
    # ---- [B] proposer --------------------------------------------------------------------------------------------
    print("[B] proposer")
    e = erreur(RC.proposer_recyclage("nulle-part"))
    check("B1 post inconnu -> Inconnu", isinstance(e, RC.Inconnu), repr(e))
    e = erreur(RC.proposer_recyclage("moyen"))
    check("B2 sous le seuil (1,5× < 3×) -> Refus sous_seuil, avec le seuil et la mesure",
          isinstance(e, RC.Refus) and e.code == "sous_seuil" and e.details.get("seuil") == 3.0
          and e.details.get("multiplicateur") == 1.5, repr(e) + str(getattr(e, "details", "")))
    APPELS.clear()
    pr = run(RC.proposer_recyclage("ag"))
    check("B3 gratuit : aucun appel au modèle", APPELS == [])
    check("B4 la mesure du gagnant : 6× sur Instagram, au seuil 3×",
          pr["mesure"]["multiplicateur"] == 6.0 and pr["mesure"]["canal"] == "instagram" and pr["seuil"] == 3.0, str(pr["mesure"]))
    cartes = {c["arguments"]["element"]: c for c in pr["cartes"]}
    check("B5 quatre cartes de devis, une par élément", list(cartes) == list(RC.ELEMENTS)
          and all(c["type"] == "carte" and c["genre"] == "devis" and c["etat"] == "proposee" for c in pr["cartes"]), str(list(cartes)))
    check("B6 chaque carte chiffre son texte (> 0 $) et porte la route payante",
          all(c["arguments"]["texte"]["usd"] > 0 and c["arguments"]["texte"]["route"] == "/api/recyclage/ag/redaction"
              and c["devis"] >= c["arguments"]["texte"]["usd"] for c in pr["cartes"]), str([c["devis"] for c in pr["cartes"]]))
    cc = cartes["carrousel"]["arguments"]
    check("B7 carrousel : un gabarit Templates, en 4:5, rendu local gratuit",
          cc["rendu"]["gabarit"]["id"] and cc["rendu"]["format"] == "4:5" and cc["rendu"]["usd"] == 0
          and cc["rendu"]["diapos"] == RC.DIAPOS, str(cc["rendu"]))
    cbr = cartes["branche"]["arguments"]
    check("B8 branche : plans gardés (le job du gagnant), voix chiffrée à part, montage non automatisé",
          cbr["montage"]["plans"] == "job-a" and cbr["montage"]["automatise"] is False and "usd" in cbr["voix"], str(cbr))
    check("B9 le projet de l'espace et ses canaux", pr["post"]["espace_id"] == EA
          and sorted(c["id"] for c in pr["canaux"]) == sorted([ig_a, x_a]), str(pr["canaux"]))
    settings.ANTHROPIC_API_KEY = ""
    pr0 = run(RC.proposer_recyclage("ag"))
    settings.ANTHROPIC_API_KEY = "cle-de-banc"
    check("B10 sans clé : cartes indisponibles, raison codée, 0 $",
          all(c["arguments"]["texte"]["disponible"] is False and c["arguments"]["texte"]["raison"] == "cle"
              and c["arguments"]["texte"]["usd"] == 0 for c in pr0["cartes"]), str(pr0["cartes"][0]["arguments"]["texte"]))
    async def sans_job():
        async with async_session_factory() as s:
            (await s.get(ScheduledPost, "bg")).job_id = None
            await s.commit()
    run(sans_job())
    prb = run(RC.proposer_recyclage("bg"))
    check("B11 un gagnant sans vidéo : branche indisponible (sans_plans)",
          [c for c in prb["cartes"] if c["arguments"]["element"] == "branche"][0]["arguments"]["texte"]["raison"] == "sans_plans")

    # ---- [C] rédiger ---------------------------------------------------------------------------------------------
    print("[C] rédiger")
    usd = cartes["accroches"]["arguments"]["texte"]["usd"]
    e = erreur(RC.rediger("ag", "accroches", max_usd="1"))
    check("C1 accord invalide -> ValueError", isinstance(e, ValueError) and not isinstance(e, RC.Refus), repr(e))
    e = erreur(RC.rediger("ag", "accroches", max_usd=usd / 10))
    check("C2 coût > accord -> CoutChange, aucun appel", isinstance(e, RC.CoutChange) and APPELS == [], repr(e))
    e = erreur(RC.rediger("ag", "tiktok", max_usd=1))
    check("C3 élément inconnu -> Refus element", isinstance(e, RC.Refus) and e.code == "element", repr(e))
    e = erreur(RC.rediger("moyen", "accroches", max_usd=1))
    check("C4 sous le seuil : la rédaction est refusée aussi", isinstance(e, RC.Refus) and e.code == "sous_seuil", repr(e))
    GARDES.clear()
    r = run(RC.rediger("ag", "accroches", max_usd=usd))
    check("C5 un appel, sous la garde « campagnes »", len(APPELS) == 1 and GARDES == ["campagnes"], str(GARDES))
    prompt = json.dumps(APPELS[0], ensure_ascii=False)
    check("C6 le prompt porte le post gagnant (accroche, légende) et les mots interdits",
          "Le secret, c'est la nuit" in prompt and "Notre pain dort toute la nuit." in prompt and "gratuit" in prompt)
    check("C7 trois accroches, le mot interdit relevé", len(r["accroches"]) == 3 and r["interdits"] == ["gratuit"], str(r))
    r2 = run(RC.rediger("ag", "accroches", max_usd=usd))
    check("C8 déjà payée : rendue sans nouvel appel", r2.get("deja_payee") is True and len(APPELS) == 1)

    # ---- [D] brouillons ------------------------------------------------------------------------------------------
    print("[D] brouillons")
    e = erreur(RC.creer_brouillons("ag", ["fil_x"]))
    check("D1 élément non rédigé -> Refus a_rediger", isinstance(e, RC.Refus) and e.code == "a_rediger", repr(e))
    e = erreur(RC.creer_brouillons("ag", ["accroches"]))
    check("D2 mot interdit -> Refus interdits, rien d'écrit", isinstance(e, RC.Refus) and e.code == "interdits", repr(e))
    REP["accroches"] = json.dumps({"accroches": ["Avant 7 h, tout se joue", "Le geste du matin", "Ce que le four sait"]},
                                  ensure_ascii=False)
    r3 = run(RC.rediger("ag", "accroches", max_usd=usd, nouvelle=True))
    check("D3 « nouvelle » : un appel de plus, plus de mot interdit", len(APPELS) == 2 and r3["interdits"] == [], str(r3))
    for el in ("fil_x", "carrousel", "branche"):
        run(RC.rediger("ag", el, max_usd=cartes[el]["devis"]))
    res = run(RC.creer_brouillons("ag"))
    posts = res["brouillons"]
    par = {}
    for b in posts:
        par.setdefault(b["element"], []).append(b["post"])
    check("D4 trois accroches + un fil X + un carrousel ; la branche non créée (montage)",
          len(par.get("accroches", [])) == 3 and len(par.get("fil_x", [])) == 1 and len(par.get("carrousel", [])) == 1
          and "branche" not in par and [n["element"] for n in res["non_crees"]] == ["branche"]
          and res["non_crees"][0]["raison"] == "montage", str({k: len(v) for k, v in par.items()}) + str(res["non_crees"]))
    tous = [b["post"] for b in posts]
    check("D5 JAMAIS de mode auto : brouillons assistés", all(p["status"] == "draft" and p["mode"] == "assisted" for p in tous),
          str([(p["status"], p["mode"]) for p in tous]))
    check("D6 brief.recycle_de : le post d'origine, l'élément, le multiplicateur",
          all(p["brief"]["recycle_de"]["post_id"] == "ag" and p["brief"]["recycle_de"]["multiplicateur"] == 6.0 for p in tous))
    a = par["accroches"]
    check("D7 accroches : mêmes plans, nouvelle accroche, canaux du projet",
          [p["hook"] for p in a] == ["Avant 7 h, tout se joue", "Le geste du matin", "Ce que le four sait"]
          and all(p["job_id"] == "job-a" and sorted(p["comptes"]) == sorted([ig_a, x_a]) for p in a), str(a[0]))
    quand = sorted(datetime.fromisoformat(p["run_at"].replace("Z", "")) for p in tous)
    check("D8 au moins 7 jours entre deux pièces du même gagnant",
          all((b - a_).days >= 7 for a_, b in zip(quand, quand[1:])), str(quand))
    fx = par["fil_x"][0]
    check("D9 fil X : sur le compte X du projet, le fil entier dans le brief",
          fx["comptes"] == [x_a] and fx["brief"]["x_fil"] == json.loads(REP["fil_x"])["fil"]
          and fx["caption"] == "1/ Le pain se fait la veille.", str(fx))
    ca = par["carrousel"][0]
    ig = ca["brief"]["instagram"]
    check("D10 carrousel : forme Instagram, cinq diapos rendues du gabarit, sur le compte Instagram du projet",
          ig["forme"] == "carrousel" and len(ig["images"]) == 5 and ca["comptes"] == [ig_a]
          and [t for _i, t, _f in RENDUS] == json.loads(REP["carrousel"])["diapos"]
          and all(f == "visuel_gagnant.png" for _i, _t, f in RENDUS) and ca["caption"] == "Cinq étapes, un pain.", str(ig))
    from app.services import instagram_publisher as IGP
    check("D11 le format du carrousel passe la normalisation du publieur (t494)",
          IGP.format_post(ig)["images"] == ig["images"] and IGP.format_post(ig)["forme"] == "carrousel")
    async def lus():
        async with async_session_factory() as s:
            return [await s.get(ScheduledPost, p["id"]) for p in tous]
    check("D12 recycled_from = le gagnant (la suggestion du Planificateur ne le repropose plus)",
          all(x.recycled_from == "ag" for x in run(lus())))
    check("D13 registre : brouillons notés", len(RC.lire("ag")["brouillons"]) == 5)
    res_b = run(RC.creer_brouillons("ag", ["accroches"]))
    q2 = min(datetime.fromisoformat(b["post"]["run_at"].replace("Z", "")) for b in res_b["brouillons"])
    check("D14 une deuxième série continue l'espacement (après la dernière pièce)", q2 >= quand[-1] + timedelta(days=7), str(q2))
    # client « validé par le client »
    REP["accroches"] = json.dumps({"accroches": ["Un", "Deux", "Trois"]})
    cb = [c for c in prb["cartes"] if c["arguments"]["element"] == "accroches"][0]
    run(RC.rediger("bg", "accroches", max_usd=cb["devis"]))
    rb = run(RC.creer_brouillons("bg", ["accroches"]))
    check("D15 client valide_par_client -> a_valider, canaux du projet du client",
          all(b["post"]["status"] == "a_valider" and b["post"]["comptes"] == [ig_b] and b["post"]["mode"] == "assisted"
              for b in rb["brouillons"]), str([b["post"]["status"] for b in rb["brouillons"]]))

    # ---- [E] routes ----------------------------------------------------------------------------------------------
    print("[E] routes")
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes as R
    c = TestClient(app, client=("127.0.0.1", 50000))
    rr = c.get("/api/recyclage/ag/proposition")
    check("E1 GET proposition : 200, cinq cartes (t500 : + x_video)", rr.status_code == 200 and len(rr.json()["cartes"]) == 5, rr.text[:300])
    check("E2 post inconnu : 404", c.get("/api/recyclage/nulle-part/proposition").status_code == 404)
    rr = c.get("/api/recyclage/moyen/proposition")
    check("E3 sous le seuil : 409 code sous_seuil", rr.status_code == 409 and rr.json()["detail"]["code"] == "sous_seuil", rr.text[:300])
    rr = c.post("/api/recyclage/ag/redaction", json={"element": "fil_x", "max_usd": 0.0000001, "nouvelle": True})
    check("E4 rédaction hors accord : 409 cout + usd", rr.status_code == 409 and rr.json()["detail"]["code"] == "cout"
          and rr.json()["detail"]["usd"] > 0, rr.text[:300])
    rr = c.post("/api/recyclage/ag/redaction", json={"element": "fil_x", "max_usd": 1})
    check("E5 rédaction déjà payée : 200 deja_payee", rr.status_code == 200 and rr.json().get("deja_payee") is True, rr.text[:300])
    rr = c.post("/api/recyclage/ag/brouillons", json={"elements": ["fil_x"]})
    check("E6 brouillons : 200", rr.status_code == 200 and len(rr.json()["brouillons"]) == 1, rr.text[:300])
    loin = TestClient(app, client=("192.168.1.20", 50000))
    check("E7 hors boucle locale : refusé", loin.get("/api/recyclage/ag/proposition").status_code in (401, 403))
    rr = c.post("/api/recyclage/ag/brouillons", json={"elements": ["tiktok"]})
    check("E8 élément inconnu : 400", rr.status_code == 400, rr.text[:300])
finally:
    MT.httpx.post = _post0
    PL.verifier = _verif0

# ---- [F] source ------------------------------------------------------------------------------------------------------
print("[F] source")
SRC = (_ICI.parent / "app" / "services" / "recyclage.py").read_text(encoding="utf-8")
_rd = SRC[SRC.find("async def rediger("):SRC.find("# ---- brouillons")]
check("F1 aucun appel nu au modèle ; _appel passe par MT.tirer_garde", "MT.tirer(" not in SRC and "MT.tirer_garde(" in SRC)
check("F2 l'accord (CoutChange) précède l'appel", 0 < _rd.find("raise CoutChange(") < _rd.find("await _appel("))
check("F3 jamais de mode auto ni de statut programmé dans le service",
      '"auto"' not in SRC and '"scheduled"' not in SRC and '"mode": "assisted"' in SRC)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
