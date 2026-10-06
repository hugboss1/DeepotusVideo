# -*- coding: utf-8 -*-
"""Plafonds mensuels : la garde est posée sur TOUTES les routes payantes (tâche #16, plan Settings T5, 29/09/2026).
Décision de l'utilisateur : « toutes les payantes » — un recensement AST (tests/_recensement_payant.py) rougit si une
route qui atteint un fournisseur payant n'appelle pas la garde, ou si une route de la liste disparaît/perd sa garde.
Puis l'essai RÉEL : /api/images/generate (faux FLUX, zéro réseau) → 402 `dz_plafond` sans dépense ; rejoué avec
`X-DZ-Plafond: confirme` → passe et s'inscrit au registre ; la confirmation ne fuit pas vers la requête suivante.
Et les routes /api/reglages/plafonds (lecture, fusion, état) réservées à la boucle locale.
Run : & $PY tests/test_plafonds_garde.py   (depuis backend/)"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzplafg_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()
import _recensement_payant as RP                                    # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


# Les routes qui DÉPENSENT, relevées le 29/09 (rapport de classement + lecture du code). Une route neuve qui atteint
# un puits sans être ici rougit A2 ; une route d'ici qui perd sa garde rougit A1.
PAYANTES = {
    ("routes", "POST", "/chapters/{chapter_id}/reecrire"),     # tâche #66 : la réécriture dans le ton de la bible (LLM)
    ("routes", "POST", "/chapters/{chapter_id}/animatique"),   # tâche #63 : la voix témoin de l'animatique (sur demande)
    ("routes", "POST", "/shots/{shot_id}/image"),        # tâche #62 : l'image de production d'un plan (Nano Banana)
    ("routes", "POST", "/layout-templates/{template_id}/render"), ("routes", "POST", "/assets/3d"),
    ("routes", "POST", "/assets/3d/{job}/refine"), ("routes", "POST", "/assets/3d/{job}/texturer"),
    ("routes", "POST", "/assets/3d/{job}/qc"), ("routes", "ROUTE", "/meshy/{meshy_path:path}"),
    ("routes", "POST", "/assets/sprite"), ("routes", "POST", "/news/script"), ("routes", "POST", "/audio/sfx"),
    ("routes", "POST", "/audio/music"), ("routes", "POST", "/audio/voiceover"), ("routes", "POST", "/episodes/scenes"),
    ("routes", "POST", "/episodes/render"), ("routes", "POST", "/episodes/{ep_id}/narrate"),
    ("routes", "POST", "/generate"), ("routes", "POST", "/generate/batch"), ("routes", "POST", "/generate/heygen"),
    ("routes", "POST", "/generate/heygen-image"), ("routes", "POST", "/generate/heygen-cinematic"),
    ("routes", "POST", "/generate/composition"), ("routes", "POST", "/heygen/photo-avatar/create"),
    ("routes", "POST", "/prompt/build-script"), ("routes", "POST", "/prompt/refine"),
    ("routes", "POST", "/prompt/build-composition"), ("routes", "POST", "/marketing/plan"),
    ("routes", "POST", "/marketing/plan/import"), ("routes", "POST", "/images/generate"),
    ("routes", "POST", "/images/process"), ("routes", "POST", "/finition/upscale-measure"),
    ("routes", "POST", "/atelier/style/propose"), ("routes", "POST", "/bible/entities/{entity_id}/model3d"),
    ("routes", "POST", "/bible/entities/{entity_id}/generate"),
    ("routes", "POST", "/bible/entities/{entity_id}/suggest-voice"),
    ("routes", "POST", "/chapters/{chapter_id}/storyboard/decoupe"), ("routes", "POST", "/shots/{shot_id}/sketch"),
    ("routes", "POST", "/vector/illustration"), ("routes", "POST", "/atelier/manuscript"),
    ("routes", "POST", "/scenes/{scene_id}/voiceover"), ("routes", "POST", "/chapters/{chapter_id}/voiceover"),
    ("routes", "POST", "/chapters/{chapter_id}/screenplay/adapt"), ("routes", "POST", "/materials/generate"),
    ("routes", "POST", "/subtitles/translate"), ("routes", "POST", "/subtitles/transcribe"),
    ("dictation", "POST", "/dictation"), ("montage", "POST", "/autoclips"), ("capture", "POST", "/rembg"),
    ("face", "POST", "/serie/generer"), ("forge3d", "POST", "/mesh3d/{nid}"),
    ("data", "POST", "/traduire"),   # tâche #86 : la traduction des cartes (LLM des Réglages ou Ollama)
    ("data", "POST", "/lot/generer"),   # tâche #87 : l'art du deck en lot (façade image, mur par lot)
    ("routes", "POST", "/news/rank"),   # tâche #33 : le score LLM sur demande
    ("routes", "POST", "/news/chain/polish"),   # tâche #35 : le polissage LLM d'un script du lot
    ("routes", "POST", "/generate/extend"),   # tâche #51 : l'extension Veo 3.1 (fal)
    ("routes", "POST", "/studio-graphs/{graph_id}/recette/lancer"),   # tâche #71 : une recette du Studio (gardée PAR la route de rendu)
    # T098 (oubliée là, rattrapée en T099) : la photo du téléphone passe par generate_material — branche library,
    # gratuite en pratique, mais le chemin atteint le puits FLUX et la garde de generate_material est sur sa route
    ("routes", "POST", "/materials/from-photo"),
    ("routes", "POST", "/assets/3d/{job}/rig"),
    ("routes", "POST", "/assets/3d/{job}/convert"),   # T105 : fbx/usdz/blend par Meshy convert   # T104 : rig + animations Meshy d'un job fal (crédits)
    ("routes", "POST", "/audio/stems"), ("routes", "POST", "/audio/isolate"),   # T100 : Demucs (fal), isolation ElevenLabs
}


def _git_show(chemin):
    r = subprocess.run(["git", "show", f"bfec23e:backend/app/{chemin}"], capture_output=True, cwd=str(_ICI.parent))
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


print("\n[A] recensement AST")
rec = RP.recenser()
manquent = sorted(k for k in PAYANTES if k not in rec)
check("A0 chaque route de la liste existe encore", not manquent, str(manquent))
sans = sorted(" ".join(k) for k in PAYANTES if k in rec and not rec[k]["garde"])
check(f"A1 les {len(PAYANTES)} routes payantes appellent la garde (corps ou fonctions du module)", not sans, str(sans))
oubliees = sorted(" ".join(k) + " " + str(sorted(v["puits"])) for k, v in rec.items() if v["puits"] and k not in PAYANTES)
check("A2 aucune route qui atteint un fournisseur payant n'est hors liste", not oubliees, "\n    " + "\n    ".join(oubliees))
check("A3 la liste couvre au moins 48 routes (recensement du 29/09)", len(PAYANTES) >= 48, str(len(PAYANTES)))

# témoin positif : l'ANCIEN code (avant la tâche) doit faire rougir A1 sur presque toutes les routes
anciens = {"routes": _git_show("api/routes.py"), "dictation": _git_show("services/dictation_service.py"),
           "montage": _git_show("services/montage_service.py"), "face": _git_show("services/cards/face.py"),
           "capture": _git_show("services/cards/capture.py"), "forge3d": _git_show("services/cards/forge3d.py"),
           "data": _git_show("services/cards/data.py")}   # tâche #86 : le module de la traduction des cartes
if all(anciens.values()):
    rec0 = RP.recenser(anciens)
    gardees0 = [k for k in PAYANTES if k in rec0 and rec0[k]["garde"]]
    check("A4 témoin : sur l'ancien code (bfec23e), aucune route payante n'est gardée", gardees0 == [], str(gardees0))
else:
    check("A4 témoin : ancien code lisible par git show bfec23e", False, "git show a échoué")
# témoin ciblé : retirer UNE garde d'un source fait rougir CETTE route
src = RP.MODULES["routes"].read_text(encoding="utf-8")
cible = '    await _plafond(_PLAF.op_llm(len(prompt) / 4 + 200, 800), "studio")\n'
check("A5 la garde de /prompt/refine est une ligne unique du source", src.count(cible) == 1, str(src.count(cible)))
rec1 = RP.recenser({"routes": src.replace(cible, "")})
check("A6 témoin : sans cette ligne, /prompt/refine n'est plus gardée", not rec1[("routes", "POST", "/prompt/refine")]["garde"], "")
# T6 : les trois rendus HeyGen tournent DANS `suivi_heygen` (le delta du solde est leur seul coût réel)
import ast as _ast                                                  # noqa: E402
_arbre = _ast.parse(src)
_hg = {"/generate/heygen", "/generate/heygen-image", "/generate/heygen-cinematic"}
_suivis = set()
for _f in _arbre.body:
    if isinstance(_f, _ast.AsyncFunctionDef):
        _ch = next((d.args[0].value for d in _f.decorator_list if isinstance(d, _ast.Call) and d.args
                    and isinstance(d.args[0], _ast.Constant)), None)
        if _ch in _hg and any(isinstance(w, _ast.AsyncWith) and any(isinstance(i.context_expr, _ast.Call)
                              and RP._nom_appel(i.context_expr) == "suivi_heygen" for i in w.items)
                              for w in _ast.walk(_f)):
            _suivis.add(_ch)
check("A7 les trois rendus HeyGen tournent dans `async with suivi_heygen(ref)`", _suivis == _hg, str(sorted(_hg - _suivis)))

print("\n[B] essai réel : /api/images/generate, faux FLUX")
from fastapi.testclient import TestClient                          # noqa: E402
from sqlalchemy import select                                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.api import routes as R                                     # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import plafonds as P                              # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

asyncio.run(init_db())
tirs = []


async def _faux_flux(prompt, size, n, seed=None, **k):
    tirs.append((prompt, n))
    return {"images": [f"faux_{len(tirs)}.png"], "seed": 7}

R._flux_generate = _faux_flux
settings.FAL_KEY = "cle-de-banc"


def _lignes():
    async def f():
        async with async_session_factory() as s:
            return (await s.execute(select(Depense).order_by(Depense.id))).scalars().all()
    return asyncio.run(f())


corps = {"prompt": "un phare", "model": "flux", "n": 2, "source": "cartes"}
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    P.enregistrer({"global_usd": 0.001, "par_moteur": {}, "alerte_pct": 80})
    r = c.post("/api/images/generate", json=corps)
    d = (r.json().get("detail") or {}) if r.headers.get("content-type", "").startswith("application/json") else {}
    dp = d.get("dz_plafond", {}) if isinstance(d, dict) else {}
    check("B1 au-dessus du plafond global : 402 dz_plafond", r.status_code == 402 and dp.get("motif") == "global",
          f"{r.status_code} {r.text[:200]}")
    check("B2 le détail dit l'écran appelant (source) et le devis de 2 images FLUX", dp.get("categorie") in (None, "cartes")
          and "cartes" in dp.get("message", "") and abs(dp.get("devis_usd", 0) - 0.006) < 1e-9, json.dumps(dp, ensure_ascii=False))
    check("B3 rien n'est parti chez le fournisseur, rien n'est inscrit", tirs == [] and _lignes() == [], f"{tirs}")
    r = c.post("/api/images/generate", json=corps, headers={"X-DZ-Plafond": "confirme"})
    L = _lignes()
    check("B4 rejoué avec X-DZ-Plafond: confirme : 200 et UN tir", r.status_code == 200 and len(tirs) == 1, f"{r.status_code} {r.text[:200]}")
    check("B5 la dépense est inscrite : fal, cartes, image, 0,006 $", len(L) == 1 and L[0].moteur == "fal"
          and L[0].categorie == "cartes" and L[0].op == "image" and abs(L[0].estime_usd - 0.006) < 1e-9,
          str([(l.moteur, l.categorie, l.op, l.estime_usd) for l in L]))
    r = c.post("/api/images/generate", json=corps)
    check("B6 la confirmation ne fuit pas : la requête suivante sans en-tête est refusée", r.status_code == 402 and len(tirs) == 1, str(r.status_code))
    P.enregistrer({"global_usd": 0, "par_moteur": {"fal": 1.0}})
    r = c.post("/api/images/generate", json=corps)
    check("B7 sous le plafond par moteur : passe sans en-tête", r.status_code == 200 and len(tirs) == 2, f"{r.status_code} {r.text[:160]}")

    print("\n[C] /api/reglages/plafonds")
    g = c.get("/api/reglages/plafonds").json()
    check("C1 lecture : global 0, fal 1, alerte 80 (conservée par la fusion)", g == {"global_usd": 0.0, "par_moteur": {"fal": 1.0}, "alerte_pct": 80}, json.dumps(g))
    e = c.post("/api/reglages/plafonds", json={"alerte_pct": 50}).json()
    check("C2 un POST partiel FUSIONNE (le plafond fal survit)", e["par_moteur"] == {"fal": 1.0} and e["alerte_pct"] == 50, json.dumps(e))
    e = c.post("/api/reglages/plafonds", json={"global_usd": 20}).json()
    check("C3 le global écrit dans la grille (monthly_budget_usd) est relu par /cost/pricing", e["global_usd"] == 20.0
          and c.get("/api/cost/pricing").json().get("monthly_budget_usd") == 20.0, json.dumps(e))
    et = c.get("/api/reglages/plafonds/etat").json()
    check("C4 état : 0,012 $ fal au mois, 1,2 % de 1 $", abs(et["par_moteur"]["fal"]["estime_usd"] - 0.012) < 1e-9
          and et["par_moteur"]["fal"]["pct"] == 1.2, json.dumps(et["par_moteur"]))
    check("C5 mois illisible : 400", c.get("/api/reglages/plafonds/etat?mois=2026-9").status_code == 400, "")
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E401,E702
import _jeton_appareil as _JA  # noqa: E402 — tache #56 : le reseau local exige un jeton d'appareil (garde exterieure)
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    check("C6 hors boucle locale : lecture refusée", c2.get("/api/reglages/plafonds").status_code == 403, "")
    check("C7 hors boucle locale : écriture refusée", c2.post("/api/reglages/plafonds", json={"global_usd": 0}).status_code == 403, "")
check("C8 le refus distant n'a rien écrit", P.charger()["global_usd"] == 20.0, "")


async def _middleware_isole():
    """Le middleware appelé dans UN SEUL contexte : TestClient isole chaque requête et masquerait un oubli de remise
    à zéro ; ici, la ContextVar doit valoir vrai PENDANT la requête confirmée et redevenir fausse APRÈS."""
    from app.main import _dz_plafond_confirme

    class _Rq:
        def __init__(self, h): self.headers = h
    vu = []

    async def suite(_r):
        vu.append(P.CONFIRME.get())
        return "réponse"
    rep = await _dz_plafond_confirme(_Rq({"x-dz-plafond": "confirme"}), suite)
    apres = P.CONFIRME.get()
    await _dz_plafond_confirme(_Rq({}), suite)
    return rep, vu, apres

_rep, _vu, _apres = asyncio.run(_middleware_isole())
check("C9 middleware : vrai pendant la requête confirmée, faux après, faux sans en-tête",
      _rep == "réponse" and _vu == [True, False] and _apres is False, str((_rep, _vu, _apres)))

print("\n[D] la voix off chiffrée par les gardes vidéo")
from app.services import voice_providers as VP                      # noqa: E402
_resolve0, _script0 = VP.resolve_provider, R.pipeline.engine.build_voiceover_script
try:
    VP.resolve_provider = lambda *a, **k: "elevenlabs"
    check("D1 ElevenLabs : un op au nombre de caractères", R._op_tts("  bonjour  ") == [{"kind": "elevenlabs", "chars": 7}], str(R._op_tts("  bonjour  ")))
    check("D2 texte vide : rien", R._op_tts("   ") == [], "")
    VP.resolve_provider = lambda *a, **k: "voicebox"
    check("D3 Voicebox (local) : rien", R._op_tts("bonjour") == [], "")
    VP.resolve_provider = lambda *a, **k: "elevenlabs"
    R.pipeline.engine.build_voiceover_script = lambda req: "douze lettres"

    class _Req:
        voiceover_enabled, voiceover = True, None
    check("D4 voix off par défaut d'une génération : chiffrée", R._op_voix_off(_Req()) == [{"kind": "elevenlabs", "chars": 13}], str(R._op_voix_off(_Req())))
    _Req.voiceover = "fichier.mp3"
    check("D5 voix off FOURNIE : rien à synthétiser", R._op_voix_off(_Req()) == [], "")
    _Req.voiceover, _Req.voiceover_enabled = None, False
    check("D6 voix off désactivée : rien", R._op_voix_off(_Req()) == [], "")
finally:
    VP.resolve_provider, R.pipeline.engine.build_voiceover_script = _resolve0, _script0

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
