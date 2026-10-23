# -*- coding: utf-8 -*-
"""t220 (Menus : Réglages, 16/10/2026) — Fournisseurs par défaut branchés sur le serveur, modèles de texte réglables,
garde anti-clé. Banc SERVEUR (l'écran a son banc à part : test_reglages_fournisseurs_ecran.py).

Défauts relevés sur 7a104ba2 : les rôles « Résumé News » / « Planificateur » restaient dans le localStorage
(« Enregistré localement ») et le Diagnostic disait PLANNER/SUMMARIZER_PROVIDER « missing » ; ANTHROPIC_MODEL et
OPENAI_MODEL ne se réglaient nulle part ; GEMINI_MODEL était un champ de clé, et sur la machine de l'utilisateur il
CONTIENT sa clé AIza… (chaque appel Gemini part vers models/AIza…:generateContent).

Ce que ce banc garde (zéro réseau : httpx des listes de modèles remplacé) :
  [G] `moteurs_texte.ressemble_a_une_cle` : AIza / sk- / msy_ / > 30 caractères sans - . : ; les vrais noms passent ;
  [P] POST /settings/provider-defaults, rôles : moteur connu écrit au .env et appliqué à chaud, "" = automatique,
      moteur inconnu → 400 sans rien écrire, rôle inconnu ignoré, ancienne forme « Ollama » toujours comprise ;
  [M] le même POST, `modeles` : *_MODEL écrit, cache `_CATALOGUE` vidé, valeur qui ressemble à une clé → 400 et RIEN
      d'écrit (ni le rôle voisin), moteur inconnu → 400 ;
  [K] POST /settings/keys : même garde sur les *_MODEL (lot entier refusé), cache vidé à l'écriture ;
  [L] GET /settings/provider-defaults : `moteurs` (configuré, modèle sain, alerte) ; une valeur fautive est SIGNALÉE,
      jamais renvoyée (ni en clair, ni masquée), jamais effacée du .env ;
  [D] Diagnostic : la ligne GEMINI_MODEL porte l'alerte, sans aperçu ;
  [V] la clé n'atteint plus aucun appel : `modele_defaut`, `modeles_de`, l'URL de gemini_llm ;
  [R] GET /settings/provider-defaults/modeles : la liste du fournisseur, filtrée ; moteur inconnu → 400 ;
  [T] POST /settings/provider-defaults/tester : connu / inconnu / non vérifiable, sans dépense ; clé → 400 ;
  [E] chaque message d'erreur neuf est traduit (scripts/i18n_l10_traductions.json).
Run (depuis backend/) : & $PY tests/test_reglages_fournisseurs.py"""
import json, os, pathlib, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzfourn_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
           "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\nOPENAI_API_KEY=sk-test-openai\nGEMINI_API_KEY=AIzaFAUSSECLEDEBANC000000000000000\n",
                           encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import vector_illustration as VI                  # noqa: E402
import app.services.gemini_llm as GL                                # noqa: E402
import app.api.settings_routes as SR                                # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
CLE_G = "AIzaFAUSSECLEDEBANC000000000000000"
CAC.appliquer({"OPENAI_API_KEY": "sk-test-openai", "GEMINI_API_KEY": CLE_G, "ANTHROPIC_API_KEY": "",
               "GEMINI_MODEL": "", "OPENAI_MODEL": "", "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def env():
    return (_tmp / ".env").read_text(encoding="utf-8")


class _R:
    def __init__(self, code, j):
        self.status_code, self._j = code, j

    def json(self):
        return self._j


APPELS = []
LISTES = {"openai": ["gpt-4o-mini", "gpt-4.1", "text-embedding-3-small", "dall-e-3"],
          "gemini": ["gemini-flash-latest", "gemini-2.5-pro"]}


def _faux_get(url, headers=None, timeout=None, verify=None):
    APPELS.append(url)
    if "openai.com" in url:
        return _R(200, {"data": [{"id": i} for i in LISTES["openai"]]})
    if "generativelanguage" in url or "/models" in url and "anthropic" not in url:
        return _R(200, {"models": [{"name": "models/" + i, "supportedGenerationMethods": ["generateContent"]}
                                   for i in LISTES["gemini"]]})
    return _R(500, {})


VI.httpx = types.SimpleNamespace(get=_faux_get, post=None)


async def _soldes():
    return {}
SR._soldes = _soldes

print("[G] la garde")
for v in ("AIzaSyD-abc_def", "sk-proj-123", "sk-ant-api03-xyz", "msy_abcdef", "A" * 31, "abc123DEF456ghi789JKL012mno345pq"):
    check(f"G1 clé reconnue : {v[:12]}…", MT.ressemble_a_une_cle(v))
for v in ("claude-haiku-4-5-20251001", "gpt-4o-mini", "gemini-flash-latest", "qwen2.5:14b-instruct", "llama3",
          "", "o3", "gemini-2.5-pro-preview-05-06-thinking-experimental-long"):
    check(f"G2 nom de modèle accepté : {v or '(vide)'}", not MT.ressemble_a_une_cle(v))

with TestClient(app) as c:
    print("[P] rôles")
    r = c.post("/api/settings/provider-defaults", json={"summarizer": "openai", "planner": "gemini"})
    check("P1 rôles écrits (200)", r.status_code == 200, r.text[:200])
    check("P2 .env : SUMMARIZER_PROVIDER / PLANNER_PROVIDER, le reste du fichier gardé",
          "SUMMARIZER_PROVIDER=openai" in env() and "PLANNER_PROVIDER=gemini" in env()
          and "# fichier de l'utilisateur" in env() and "OPENAI_API_KEY=sk-test-openai" in env(), env())
    check("P3 appliqués à chaud", settings.SUMMARIZER_PROVIDER == "openai" and settings.PLANNER_PROVIDER == "gemini")
    r = c.post("/api/settings/provider-defaults", json={"planner": ""})
    check("P4 \"\" = automatique", r.status_code == 200 and settings.PLANNER_PROVIDER == "" and "PLANNER_PROVIDER=\n" in env())
    avant = env()
    r = c.post("/api/settings/provider-defaults", json={"summarizer": "mistral", "planner": "openai"})
    check("P5 moteur inconnu → 400, RIEN d'écrit (ni le rôle voisin)", r.status_code == 400 and env() == avant
          and settings.PLANNER_PROVIDER == "", r.text[:200])
    r = c.post("/api/settings/provider-defaults", json={"summarizer": "Ollama"})
    check("P6 l'ancienne forme « Ollama » reste comprise", r.status_code == 200 and settings.SUMMARIZER_PROVIDER == "ollama")
    r = c.post("/api/settings/provider-defaults", json={"video": "FAL_KEY"})
    check("P7 rôle inconnu seul → 400 (rien à écrire)", r.status_code == 400)
    j = c.get("/api/settings/provider-defaults").json()
    check("P8 relu au chargement : preference du résumé", j["roles"]["summarizer"]["preference"] == "ollama", json.dumps(j)[:300])

    print("[M] modèles")
    VI._CATALOGUE["openai"] = ["vieux"]
    VI._CATALOGUE["gemini"] = ["vieux"]
    r = c.post("/api/settings/provider-defaults", json={"modeles": {"openai": "gpt-4.1"}})
    check("M1 OPENAI_MODEL écrit et appliqué", r.status_code == 200 and "OPENAI_MODEL=gpt-4.1" in env()
          and settings.OPENAI_MODEL == "gpt-4.1", r.text[:200])
    check("M2 cache _CATALOGUE vidé à l'écriture", VI._CATALOGUE == {}, repr(VI._CATALOGUE))
    check("M3 la réponse porte l'état des moteurs", any(m["moteur"] == "openai" and m["modele"] == "gpt-4.1"
                                                         for m in r.json().get("moteurs", [])))
    avant = env()
    r = c.post("/api/settings/provider-defaults", json={"summarizer": "openai", "modeles": {"gemini": "AIzaSyCOLLEE"}})
    check("M4 clé dans un *_MODEL → 400, rien d'écrit (ni le rôle)", r.status_code == 400 and env() == avant
          and settings.SUMMARIZER_PROVIDER == "ollama", r.text[:200])
    check("M5 le message ne recopie pas la valeur", "AIzaSyCOLLEE" not in r.text, r.text[:200])
    for v in ("sk-proj-abc", "msy_123", "x" * 40):
        r = c.post("/api/settings/provider-defaults", json={"modeles": {"anthropic": v}})
        check(f"M6 refus 400 : {v[:10]}…", r.status_code == 400 and env() == avant)
    r = c.post("/api/settings/provider-defaults", json={"modeles": {"mistral": "m"}})
    check("M7 moteur inconnu → 400", r.status_code == 400 and env() == avant)
    r = c.post("/api/settings/provider-defaults", json={"modeles": {"ollama": "qwen2.5:14b-instruct"}})
    check("M8 nom Ollama avec « : » accepté", r.status_code == 200 and settings.OLLAMA_MODEL == "qwen2.5:14b-instruct")
    r = c.post("/api/settings/provider-defaults", json={"modeles": {"ollama": ""}})
    check("M9 valeur vide : retour au défaut", r.status_code == 200 and settings.OLLAMA_MODEL == "")
    r = c.post("/api/settings/provider-defaults", json={"modeles": "gpt"})
    check("M10 `modeles` non objet → 400", r.status_code == 400)

    print("[K] /settings/keys")
    avant = env()
    r = c.post("/api/settings/keys", json={"entries": [{"name": "FIGMA_TOKEN", "value": "figd_x"},
                                                       {"name": "GEMINI_MODEL", "value": CLE_G}]})
    check("K1 clé dans GEMINI_MODEL → 400, lot entier refusé", r.status_code == 400 and env() == avant
          and settings.FIGMA_TOKEN != "figd_x", r.text[:200])
    check("K2 le message ne recopie pas la clé", CLE_G not in r.text)
    VI._CATALOGUE["openai"] = ["vieux"]
    r = c.post("/api/settings/keys", json={"name": "OPENAI_MODEL", "value": "gpt-4o-mini"})
    check("K3 nom valide écrit, cache vidé", r.status_code == 200 and settings.OPENAI_MODEL == "gpt-4o-mini"
          and VI._CATALOGUE == {})

    print("[L] valeur déjà fautive : signalée, jamais renvoyée, jamais effacée")
    with open(_tmp / ".env", "a", encoding="utf-8") as f:            # l'état de la machine de l'utilisateur
        f.write(f"GEMINI_MODEL={CLE_G}\n")
    CAC.appliquer({"GEMINI_MODEL": CLE_G})
    r = c.get("/api/settings/provider-defaults")
    j = r.json()
    g = next((m for m in j.get("moteurs", []) if m["moteur"] == "gemini"), {})
    check("L1 gemini signalé : fautif, alerte « contient une clé »", g.get("fautif") is True
          and g.get("alerte") == "contient une clé, pas un nom de modèle", json.dumps(g, ensure_ascii=False))
    check("L2 modèle rendu vide", g.get("modele") == "")
    check("L3 la clé n'apparaît nulle part dans la réponse (ni entière ni son début)", CLE_G not in r.text
          and CLE_G[:8] not in r.text, r.text[:300])
    check("L4 jamais effacée du .env", f"GEMINI_MODEL={CLE_G}" in env())
    check("L5 chaque moteur a sa ligne (configuré ou non) et le réglage de son modèle",
          [m["moteur"] for m in j["moteurs"]] == ["anthropic", "openai", "gemini", "ollama", "agent"]   # t285a : + ligne agent
          and {m["moteur"]: m["cle_modele"] for m in j["moteurs"]}["openai"] == "OPENAI_MODEL"
          and {m["moteur"]: m["configure"] for m in j["moteurs"]} == {"anthropic": False, "openai": True,
                                                                      "gemini": True, "ollama": False, "agent": False})

    print("[D] Diagnostic")
    r = c.get("/api/reglages/diagnostic")
    lig = next((x for x in r.json().get("cles", []) if x["cle"] == "GEMINI_MODEL"), {})
    check("D1 GEMINI_MODEL : alerte, sans aperçu", lig.get("alerte") == "contient une clé, pas un nom de modèle"
          and lig.get("apercu") == "" and lig.get("definie") is True, json.dumps(lig, ensure_ascii=False))
    check("D2 la clé, même masquée, n'est pas dans la ligne", CLE_G[-4:] not in json.dumps(lig))
    lo = next((x for x in r.json().get("cles", []) if x["cle"] == "OPENAI_MODEL"), {})
    check("D3 un modèle sain n'a pas d'alerte", not lo.get("alerte") and lo.get("apercu"))

    print("[V] la clé n'atteint plus aucun appel")
    VI._CATALOGUE.clear()
    check("V1 modele_defaut(gemini) vide", VI.modele_defaut("gemini") == "")
    mods = VI.modeles_de("gemini")
    check("V2 modeles_de(gemini) : la liste du fournisseur, sans la clé", mods == ["gemini-2.5-pro", "gemini-flash-latest"]
          and CLE_G not in mods, repr(mods))
    check("V3 gemini_llm : l'URL retombe sur le défaut du code, sans la clé",
          CLE_G not in GL._url() and GL._url().endswith("/models/gemini-flash-latest:generateContent"), GL._url())

    print("[R] liste des modèles d'un moteur")
    VI._CATALOGUE.clear()
    r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "openai"})
    check("R1 liste du fournisseur, filtrée (texte seulement), modèle courant en tête",
          r.status_code == 200 and r.json().get("modeles") == ["gpt-4o-mini", "gpt-4.1"] and r.json().get("lisible") is True, r.text[:200])
    r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "zz"})
    check("R2 moteur inconnu → 400", r.status_code == 400)
    r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "anthropic"})
    check("R3 moteur non configuré : liste vide, aucun appel", r.status_code == 200 and r.json().get("modeles") == []
          and r.json().get("configure") is False)

    LISTES_SAUVE = LISTES["openai"]; LISTES["openai"] = []; VI._CATALOGUE.clear()
    r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "openai"})
    check("R4 fournisseur muet : liste réduite au modèle des Réglages, lisible False", r.json().get("modeles") == ["gpt-4o-mini"]
          and r.json().get("lisible") is False, r.text[:200])
    LISTES["openai"] = LISTES_SAUVE; VI._CATALOGUE.clear()

    print("[T] Tester")
    r = c.post("/api/settings/provider-defaults/tester", json={"moteur": "openai", "modele": "gpt-4.1"})
    check("T1 modèle publié → connu", r.status_code == 200 and r.json().get("etat") == "connu" and r.json().get("ok") is True,
          r.text[:200])
    r = c.post("/api/settings/provider-defaults/tester", json={"moteur": "openai", "modele": "gpt-9"})
    check("T2 modèle absent → inconnu", r.json().get("etat") == "inconnu" and r.json().get("ok") is False)
    r = c.post("/api/settings/provider-defaults/tester", json={"moteur": "openai", "modele": "sk-proj-zz"})
    check("T3 clé → 400", r.status_code == 400)
    LISTES["openai"] = []
    VI._CATALOGUE.clear()
    r = c.post("/api/settings/provider-defaults/tester", json={"moteur": "openai", "modele": "gpt-4.1"})
    check("T4 liste illisible → non vérifiable (ok null)", r.json().get("etat") == "non_verifiable" and r.json().get("ok") is None,
          r.text[:200])
    check("T5 aucun appel de génération (POST) : un test ne dépense rien", all("chat/completions" not in u for u in APPELS))

print("[E] messages traduits (L10)")
trad = json.loads((RACINE / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
for g in ("Moteur inconnu : {moteur}", "{nom_cle} : cette valeur ressemble à une clé d'API, pas à un nom de modèle",
          "`modeles` doit être un objet (moteur → modèle)"):
    e = trad.get(g) or {}
    check(f"E1 traduit : {g[:40]}", e.get("fr") and e.get("en") and e["fr"] != e["en"], repr(e))
b = (RACINE / "scripts" / "i18n_l10_traductions.json").read_bytes()
check("E2 traductions : CRLF, indentation d'un espace", b.count(b"\r\n") > 1000 and b"\n \"Moteur inconnu" in b.replace(b"\r\n", b"\n"))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
