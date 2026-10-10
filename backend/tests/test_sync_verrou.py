# -*- coding: utf-8 -*-
"""Plan mobile T14 + T21 (tache #59 du suivi, 02/10/2026) — un chapitre EMPORTE par le telephone, ecrit hors ligne,
RENDU au retour. DECISIONS DE L'UTILISATEUR (02/10) :
  - deux ecritures ouvertes au Wi-Fi, PRENDRE et RENDRE (POST /api/sync/chapitre/prendre|rendre, l'id dans le corps :
    la liste des ecritures ouvertes est EXACTE) ; l'appareil est celui du JETON ;
  - un chapitre emporte est protege PARTOUT sur le PC : modification (PUT), suppression (DELETE) et re-import du
    manuscrit (le chapitre est laisse tel quel, le texte du manuscrit va au journal) — 423 ;
  - « Reprendre sur le PC » force la liberation (boucle locale seulement) ; revoquer l'appareil libere ses chapitres ;
  - un conflit est JOURNALISE avec le texte du telephone : rien n'est ecrase en silence, rien n'est perdu.
Corrections du plan (03/09) : appareil pris du corps, ecritures non ouvertes, seul le PUT garde, revocation qui ne
liberait rien, aucune liberation forcee, `int(offset)` -> 500, JSON non atomique, aucune borne, plusieurs boucles async.
Banc-miroir : vraies requetes depuis des IP du reseau local avec de vrais jetons ; re-import par le VRAI job du PC
(seules les trois fonctions LLM de l'agent sont remplacees) ; lignes relues dans la base.
Temoin positif : la base (6e64be6d) n'a pas sync_verrou.
Run (depuis backend/) : & $PY tests/test_sync_verrou.py"""
import asyncio, json, os, pathlib, sqlite3, subprocess, sys, tempfile
import sys as _s8, pathlib as _p8; _s8.path.insert(0, str(_p8.Path(__file__).resolve().parent)); import _labs_avant_l8  # noqa: E402,F401  (t148 : Atelier, Material Forge, Établi d'avant la traduction L8)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzverrou_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "6e64be6d"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/sync_verrou.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas sync_verrou", r0.returncode != 0)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import app.api.routes as RT                                         # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
IP1, IP2 = "192.168.1.42", "192.168.1.43"


def js(r) -> dict:
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def ligne(sql, *a):
    cx = sqlite3.connect(str(_DB))
    try:
        return cx.execute(sql, a).fetchall()
    except sqlite3.OperationalError:          # table absente (base temoin) : le banc ECHOUE, il ne plante pas
        return []
    finally:
        cx.close()


def texte(cid):
    r = ligne("SELECT script_text, spans FROM chapters WHERE id=?", cid)
    return r[0] if r else (None, None)                 # chapitre absent : le banc ECHOUE, il ne plante pas


with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as loc:
    H1 = JA.entetes(app, IP1)
    H2 = JA.entetes(app, IP2)
    lan1 = TestClient(app, client=(IP1, 50000), raise_server_exceptions=False)
    lan2 = TestClient(app, client=(IP2, 50000), raise_server_exceptions=False)
    devs = {a["nom"]: a for a in loc.get("/api/devices").json()["appareils"]}
    ids = [a["id"] for a in loc.get("/api/devices").json()["appareils"]]
    c1 = js(loc.post("/api/chapters", json={"title": "Chapitre du train", "series": "Saga", "script_text": "Il etait une fois Oli."}))
    c2 = js(loc.post("/api/chapters", json={"title": "Autre chapitre", "series": "Saga", "script_text": "Rien."}))
    C1, C2 = c1.get("id"), c2.get("id")
    loc.post("/api/bible/entities", json={"kind": "character", "name": "Oli", "description": "le heros"})
    prendre = lambda c, h, cid: c.post("/api/sync/chapitre/prendre", headers=h, json={"chapitre": cid})
    rendre = lambda c, h, corps: c.post("/api/sync/chapitre/rendre", headers=h, json=corps)

    print("\n[P] prendre")
    check("P1 sans jeton depuis le Wi-Fi : 401", prendre(lan1, {}, C1).status_code == 401)
    r = prendre(lan1, H1, C1)
    p = js(r)
    verrous = ligne("SELECT chapter_id, device_id FROM chapter_locks")
    check("P2 prendre : 200, le chapitre (titre, texte), son empreinte, l'heure UTC Z ; verrou au nom de l'appareil du JETON",
          r.status_code == 200 and p.get("chapitre", {}).get("script_text") == "Il etait une fois Oli." and len(p.get("sha256", "")) == 64
          and str(p.get("pris_le", "")).endswith("Z") and len(verrous) == 1 and verrous[0][0] == C1 and verrous[0][1] in ids, f"{r.status_code} {r.text[:200]} {verrous}")
    moi = verrous[0][1] if verrous else ""
    check("P3 un chapitre inexistant : 404, aucun verrou", prendre(lan1, H1, "nexiste-pas").status_code == 404
          and len(ligne("SELECT * FROM chapter_locks")) == 1)
    r2 = prendre(lan1, H1, C1)
    check("P4 le MEME appareil reprend : 200, meme verrou (idempotent)", r2.status_code == 200 and js(r2).get("pris_le") == p.get("pris_le"), r2.text[:200])
    r3 = prendre(lan2, H2, C1)
    check("P5 un AUTRE appareil : 409 qui nomme le detenteur", r3.status_code == 409 and "banc" in r3.text, f"{r3.status_code} {r3.text[:200]}")
    check("P6 corps sans chapitre : 400", lan1.post("/api/sync/chapitre/prendre", headers=H1, json={}).status_code == 400)

    print("\n[G] le PC ne l'ecrase pas")
    r = loc.put(f"/api/chapters/{C1}", json={"script_text": "ECRASE"})
    check("G1 PUT sur le chapitre emporte : 423 qui dit qui l'a, texte intact", r.status_code == 423 and "banc" in r.text
          and texte(C1)[0] == "Il etait une fois Oli.", f"{r.status_code} {r.text[:200]}")
    r = loc.delete(f"/api/chapters/{C1}")
    check("G2 DELETE : 423, le chapitre est toujours la", r.status_code == 423 and texte(C1)[0] is not None, f"{r.status_code}")
    check("G3 un AUTRE chapitre reste modifiable (200)", loc.put(f"/api/chapters/{C2}", json={"script_text": "Libre."}).status_code == 200
          and texte(C2)[0] == "Libre.")
    import app.services.manuscript_agent as MA
    MA.segment_chapters = lambda t: [{"title": "Chapitre du train", "text": "TEXTE DU MANUSCRIT REIMPORTE"},
                                     {"title": "Autre chapitre", "text": "Autre texte reimporte"}]
    MA.extract_chapter = lambda titre, txt, roster: [{"kind": "character", "name": "Oli", "aliases": [], "quotes": [], "description": "x"}]
    MA.consolidate = lambda raw, comp: raw[:1]
    RT._ms_register("job-ms", {"job_id": "job-ms", "phase": "segmentation", "chapter_i": 0, "chapter_n": 0, "message": "",
                               "done": False, "error": None, "stats": {}, "series": "Saga"})
    asyncio.run(RT._run_manuscript_job("job-ms", "x" * 300, "", "Saga"))
    check("G4 re-import du manuscrit : le chapitre EMPORTE est laisse tel quel ; l'autre est mis a jour",
          texte(C1)[0] == "Il etait une fois Oli." and texte(C2)[0] == "Autre texte reimporte", f"{texte(C1)} {texte(C2)}")
    conf = js(loc.get("/api/sync/conflits")).get("conflits", [])
    check("G5 ... et le texte du manuscrit est au JOURNAL (rien n'est perdu)", any(c.get("chapitre") == C1 and c.get("motif") == "reimport"
          and c.get("texte") == "TEXTE DU MANUSCRIT REIMPORTE" for c in conf), str(conf)[:300])

    print("\n[R] rendre")
    base = p.get("sha256")
    r = rendre(lan2, H2, {"chapitre": C1, "base_sha256": base, "texte": "Texte de l'autre."})
    check("R1 un appareil qui n'a PAS le verrou : 409, son texte au journal, rien d'ecrit", r.status_code == 409
          and texte(C1)[0] == "Il etait une fois Oli." and any(c.get("texte") == "Texte de l'autre." for c in
          js(loc.get("/api/sync/conflits")).get("conflits", [])), f"{r.status_code}")
    r = rendre(lan1, H1, {"chapitre": C1, "base_sha256": "0" * 64, "texte": "Copie perimee."})
    check("R2 empreinte de base differente : 409, texte au journal, verrou garde", r.status_code == 409 and texte(C1)[0] == "Il etait une fois Oli."
          and len(ligne("SELECT * FROM chapter_locks WHERE chapter_id=?", C1)) == 1, f"{r.status_code}")
    for mauvais in ({"chapitre": C1, "base_sha256": base, "texte": 12},
                    {"chapitre": C1, "base_sha256": base, "texte": "x" * (2 * 1024 * 1024 + 1)},
                    {"chapitre": C1, "base_sha256": base, "texte": "ok", "annotations": [{"offset": "dix", "texte": "n"}]},
                    {"chapitre": C1, "base_sha256": base, "texte": "ok", "annotations": [{"offset": 1, "texte": "n"}] * 501},
                    {"chapitre": C1, "base_sha256": base, "texte": "ok", "annotations": ["pas un objet"]}):
        rr = rendre(lan1, H1, mauvais)
        if rr.status_code != 400 or texte(C1)[0] != "Il etait une fois Oli.":
            break
    check("R3 corps malforme (texte non chaine, trop long, annotation illisible, trop d'annotations) : 400, rien d'ecrit",
          rr.status_code == 400 and texte(C1)[0] == "Il etait une fois Oli.", f"{rr.status_code} {rr.text[:150]}")
    r = rendre(lan1, H1, {"chapitre": C1, "base_sha256": base, "texte": "Ecrit dans le train par Oli.", "garder": True,
                          "annotations": [{"offset": 3, "texte": "verifier ce passage"}]})
    check("R4 rendre en GARDANT le verrou : texte ecrit, verrou garde", r.status_code == 200 and texte(C1)[0] == "Ecrit dans le train par Oli."
          and len(ligne("SELECT * FROM chapter_locks WHERE chapter_id=?", C1)) == 1, f"{r.status_code} {r.text[:200]}")
    spans = json.loads(texte(C1)[1] or "[]")
    check("R5 le surlignage des entites est RECALCULE sur le nouveau texte (Oli)", any("Oli" == "Ecrit dans le train par Oli."[s.get("start", 0):s.get("end", 0)]
          for s in spans if isinstance(s, dict)), str(spans)[:200])
    an = js(lan1.get(f"/api/sync/chapitre/{C1}/annotations", headers=H1)).get("annotations")
    check("R6 les annotations sont gardees (lecture)", an == [{"offset": 3, "texte": "verifier ce passage"}], str(an))
    nb = js(rendre(lan1, H1, {"chapitre": C1, "base_sha256": js(r).get("sha256"), "texte": "Version finale du train."}))
    check("R7 rendre (sans garder) : texte ecrit, verrou LIBERE, nouvelle empreinte rendue", texte(C1)[0] == "Version finale du train."
          and ligne("SELECT * FROM chapter_locks WHERE chapter_id=?", C1) == [] and len(nb.get("sha256", "")) == 64, str(nb)[:200])
    check("R8 libere : le PC peut de nouveau le modifier (200)", loc.put(f"/api/chapters/{C1}", json={"title": "Chapitre du train (relu)"}).status_code == 200)

    print("\n[F] reprendre sur le PC, revocation")
    p2 = js(prendre(lan1, H1, C1))
    check("F1 reprendre DEPUIS le Wi-Fi : 403 (boucle locale seulement)", lan1.post(f"/api/chapters/{C1}/reprendre", headers=H1).status_code == 403)
    r = loc.post(f"/api/chapters/{C1}/reprendre")
    check("F2 reprendre sur le PC : 200, verrou libere, journal « repris sur le PC »", r.status_code == 200
          and ligne("SELECT * FROM chapter_locks") == [] and any(c.get("motif") == "repris_pc" and c.get("chapitre") == C1
          for c in js(loc.get("/api/sync/conflits")).get("conflits", [])), f"{r.status_code} {r.text[:150]}")
    r = rendre(lan1, H1, {"chapitre": C1, "base_sha256": p2.get("sha256"), "texte": "Travail du train apres reprise."})
    check("F3 le telephone rend APRES la reprise : 409, son texte au journal (jamais perdu), PC intact",
          r.status_code == 409 and texte(C1)[0] == "Version finale du train." and any(c.get("texte") == "Travail du train apres reprise."
          for c in js(loc.get("/api/sync/conflits")).get("conflits", [])), f"{r.status_code}")
    check("F4 reprendre un chapitre non emporte : 404", loc.post(f"/api/chapters/{C2}/reprendre").status_code == 404)
    prendre(lan1, H1, C2)
    vs = js(loc.get("/api/sync/verrous")).get("verrous", [])
    check("F5 la liste des chapitres emportes dit le titre et l'appareil", len(vs) == 1 and vs[0].get("chapitre") == C2
          and vs[0].get("titre") == "Autre chapitre" and vs[0].get("appareil", {}).get("nom") == "banc", str(vs))
    loc.post(f"/api/devices/{moi}/revoke")
    check("F6 revoquer l'appareil LIBERE ses chapitres, journal « appareil revoque »", ligne("SELECT * FROM chapter_locks") == []
          and any(c.get("motif") == "revoque" and c.get("chapitre") == C2 for c in js(loc.get("/api/sync/conflits")).get("conflits", [])))
    check("F7 les ecritures ouvertes au Wi-Fi : exactement les six", _MAIN._ECRITURES_OUVERTES == frozenset({
          ("POST", "/api/pair/claim"), ("POST", "/api/sync/lot/etat"), ("POST", "/api/sync/depot"), ("POST", "/api/sync/depenses"),
          ("POST", "/api/sync/chapitre/prendre"), ("POST", "/api/sync/chapitre/rendre")}), str(sorted(_MAIN._ECRITURES_OUVERTES)))

print("\n[U] l'ecran Chapitres (frontend/atelier) — cablage ; le comportement est prouve dans le navigateur (8799)")
_js = (_ICI.parent.parent / "frontend" / "atelier" / "atelier.js").read_text(encoding="utf-8")
_html = (_ICI.parent.parent / "frontend" / "atelier" / "index.html").read_text(encoding="utf-8")
check("U1 le bandeau existe et l'ecran lit les verrous ET le journal", 'id="emporte"' in _html
      and 'api.get("/sync/verrous")' in _js and 'api.get("/sync/conflits")' in _js)
check("U2 « Reprendre sur le PC » appelle la route locale, apres le dialogue maison (jamais window.confirm)",
      "/reprendre`" in _js and "window.__dzDialogue.confirmer(`Reprendre" in _js and "window.confirm(" not in _js)
check("U3 lecture seule et sauvegarde suspendue tant que le chapitre est emporte",
      '$("#script").readOnly = !!emporte;' in _js and 'if (emporte) { $("#saveState").textContent = "emporté"' in _js)
check("U4 chaque bouton neuf a un title (E-12)", all(f'id="{i}" title=' in _js for i in ("btnReprendre",))
      and _js.count('data-copier="${c.id}" title=') == 1 and _js.count('data-remplacer="${c.id}" ${emporte ? "disabled" : ""}\n         title=') == 1)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
