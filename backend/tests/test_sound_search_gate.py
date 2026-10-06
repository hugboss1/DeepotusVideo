# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T11, D3a) — la porte de la recherche de sons : détection du service d'embeddings (patron
Voicebox : local d'abord, distant ensuite, rien = repli PROPRE avec la raison), index compact (array 'f' + base64,
stdlib), cosinus en Python pur MESURÉ sur 606 vecteurs de 512 (la taille du catalogue livré — le dossier audio de
l'utilisateur n'en compte que 15 le 06/10/2026, la borne reste celle du pire cas), et la table de décision DATÉE
dans le module.
Run: python tests/test_sound_search_gate.py (depuis backend/)"""
import os, random, sys, tempfile, time
_tmp = tempfile.mkdtemp(prefix="dzclap_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["IMAGES_FOLDER"] = os.path.join(_tmp, "images"); os.makedirs(os.environ["IMAGES_FOLDER"])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from loguru import logger
logger.remove()
random.seed(4)
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
from app.config import settings
from app.services import sound_search as SS

print("\n[1] la porte fermée : personne, et rien ne casse")
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False)
settings.CLAP_REMOTE_URL = ""
check("aucun service : resolve_embedder rend '' et ne lève pas", SS.resolve_embedder() == "")
st = SS.status()
check("statut fermé : ready False, raison nommant les DEUX voies",
      st["ready"] is False and "Clapbox" in st["hint"] and "CLAP_REMOTE_URL" in st["hint"], str(st))
check("available() : deux voies, aucune prête", [(a["id"], a["ready"]) for a in SS.available()] == [("clapbox", False), ("remote", False)])

print("\n[2] la porte ouverte par le service local")
SS._reach = lambda url, timeout=2.0: url == SS.clapbox_url()
SS._reach_cache.update(t=0.0, ok=False)
check("clapbox joignable : voie locale préférée", SS.resolve_embedder() == "clapbox")
check("URL par défaut : 127.0.0.1:17494", SS.clapbox_url() == "http://127.0.0.1:17494")
settings.CLAPBOX_URL = "http://127.0.0.1:9999/"
check("CLAPBOX_URL réglée : prise, sans la barre finale", SS.clapbox_url() == "http://127.0.0.1:9999")
settings.CLAPBOX_URL = ""
APPELS = []
SS._reach = lambda url, timeout=2.0: APPELS.append(url) or True
SS._reach_cache.update(t=0.0, ok=False)
SS.clapbox_reachable(); SS.clapbox_reachable(); SS.clapbox_reachable()
check("détection CACHÉE : un ping pour trois questions rapprochées (ttl)", len(APPELS) == 1, str(APPELS))

print("\n[3] la porte ouverte par l'endpoint distant seul")
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False)
settings.CLAP_REMOTE_URL = "https://clap.test/v1/"
check("distant seul : voie remote, URL sans barre finale", SS.resolve_embedder() == "remote" and SS.embedder_url() == "https://clap.test/v1")
SS._reach = lambda url, timeout=2.0: True
SS._reach_cache.update(t=0.0, ok=False)
check("les DEUX voies prêtes : le local passe d'abord (gratuit)", SS.resolve_embedder() == "clapbox")
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False)
check("statut ouvert : ready True, provider dit, aucune raison", SS.status()["ready"] is True and SS.status()["provider"] == "remote"
      and SS.status()["hint"] == "")
settings.CLAP_REMOTE_URL = ""

print("\n[4] l'index : aller-retour exact, dimension gardée")
v = [random.uniform(-1, 1) for _ in range(512)]
ix = SS.Index(dim=512, model="laion/clap-htsat-unfused", provider="clapbox")
ix.put("boom.wav", v, sig="1:2")
check("normalisé à l'écriture (norme 1)", abs(SS.norm(ix.get("boom.wav")) - 1.0) < 1e-5, str(SS.norm(ix.get("boom.wav"))))
ix.save()
ix2 = SS.Index.load()
check("relu à l'identique (array 'f' + base64)",
      max(abs(a - b) for a, b in zip(ix.get("boom.wav"), ix2.get("boom.wav"))) < 1e-6)
check("métadonnées relues : dim, modèle, provider, signature",
      (ix2.dim, ix2.model, ix2.provider, ix2.sig("boom.wav")) == (512, "laion/clap-htsat-unfused", "clapbox", "1:2"))
for label, vec in (("dimension étrangère", v[:256]), ("vecteur nul", [0.0] * 512), ("NaN", [float("nan")] * 512)):
    try: ix.put("x.wav", vec, sig=""); check(f"{label} refusé", False)
    except ValueError: check(f"{label} refusé (ValueError)", True)
SS.Index.path().write_text("{pas du json", encoding="utf-8")
check("index illisible : index VIDE, pas d'exception", SS.Index.load().count() == 0)

print("\n[5] LA MESURE : 606 vecteurs, un chargement, une requête")
big = SS.Index(dim=512, model="m", provider="clapbox")
for i in range(606):
    big.put(f"s{i}.wav", [random.uniform(-1, 1) for _ in range(512)], sig="0:0")
big.save()
t0 = time.perf_counter(); big2 = SS.Index.load(); t_load = time.perf_counter() - t0
q = [random.uniform(-1, 1) for _ in range(512)]
t0 = time.perf_counter(); top = big2.nearest(q, 8); t_q = time.perf_counter() - t0
check(f"MESURÉ : index de 606 vecteurs relu en {t_load * 1000:.0f} ms (budget 1500)", t_load < 1.5)
check(f"MESURÉ : une requête en {t_q * 1000:.1f} ms (budget 60) SANS numpy", t_q < 0.06)
check("8 voisins, score décroissant", len(top) == 8 and all(top[i][1] >= top[i + 1][1] for i in range(7)))
check("un vecteur est son propre plus proche voisin", big2.nearest(big2.get("s42.wav"), 1)[0][0] == "s42.wav")
check("exclude retire le demandeur", big2.nearest(big2.get("s42.wav"), 1, exclude="s42.wav")[0][0] != "s42.wav")
check("index d'une autre dimension : rejeté au chargement, pas planté", SS.Index.load(dim=384).count() == 0)

print("\n[6] la décision est DANS le module, datée")
check("table de décision datée du 06/10/2026, voie « dans le backend » IMPOSSIBLE",
      "06/10/2026" in SS.__doc__ and "IMPOSSIBLE" in SS.__doc__ and "RETENUE" in SS.__doc__, SS.__doc__[:200])
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
