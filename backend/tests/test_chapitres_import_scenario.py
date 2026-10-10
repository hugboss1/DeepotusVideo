# -*- coding: utf-8 -*-
"""Plan chapitres T12-T13 (tache #64 du suivi, 02/10/2026) — IMPORTER un scenario Fountain / Final Draft dans les
scenes d'un chapitre. Aucune depense (ni IA ni reseau).
Ce que le plan faisait faux, et que ce banc garde :
  - des versions PAR SCENE puis la suppression des scenes = des versions invisibles -> UNE version du scenario entier ;
  - DAY/NIGHT/I-E gardes tels quels -> reecrits par PUT /scenes a la premiere edition : TRADUITS ici ;
  - FDX : page de titre melee aux scenes, dialogue double lu deux fois, scene fantome « . », action en capitales prise
    pour une en-tete ;
  - un texte sans en-tete efface le scenario (le 422 ne partait jamais) ; « FADE IN: » perdu ou avale ;
  - la voix-off lisait « CUT TO: ».
DECISIONS DE L'UTILISATEUR (02/10) : chapitre ouvert ; remplacer (confirme, sauvegarde) ou ajouter ; verrou du
telephone respecte (423) ; vocabulaire traduit, original note ; transitions gardees mais non lues.
Temoin positif : la base (05e5eb36) n'a ni le module ni la route.
Run (depuis backend/) : & $PY tests/test_chapitres_import_scenario.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
from datetime import datetime
import sys as _s8, pathlib as _p8; _s8.path.insert(0, str(_p8.Path(__file__).resolve().parent)); import _labs_avant_l8  # noqa: E402,F401  (t148 : Atelier, Material Forge, Établi d'avant la traduction L8)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzimpsc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY",
          "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "05e5eb36"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/screenplay_import.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni le module ni la route d'import", r0.returncode != 0 and r1.returncode == 0
      and b'"/chapters/{chapter_id}/screenplay/import"' not in r1.stdout)


def leve(f):
    try:
        f()
    except ValueError as e:
        return str(e)
    return None


try:
    from app.services import screenplay_import as SI                # noqa: E402
except ImportError as e:
    SI = None
    check("T2 le module existe", False, str(e))

FOUNTAIN = """Title: Le Phare
Author: Moi
    et une autrice
INT. CUISINE - NIGHT

Vane entre, trempe.

VANE (V.O.)
Il pleut.

YSOLDE ^
(bas)
Encore.

BOB (V.O.) ^
Aussi.

CUT TO:

ext. falaise - later that night #12#

[[une note]]
/* coupe
   longtemps */
@McCLANE
Yippee.

# Acte deux
= un synopsis

===

I/E. VOITURE - CONTINUOUS

!EXT. DANS LE TEXTE, PAS UNE SCENE

.SALLE BLANCHE

> FIN <
"""

if SI:
    print("[F] Fountain")
    r = SI.lire(FOUNTAIN.encode("utf-8"), "x.fountain")
    sc = r["scenes"]
    check("F1 quatre scenes, sluglines dans le VOCABULAIRE de l'atelier (NIGHT -> NUIT, I/E -> INT/EXT, en-tete minuscule lue)",
          [s["slugline"] for s in sc] == ["INT. CUISINE - NUIT", "EXT. FALAISE - NUIT", "INT/EXT. VOITURE - NUIT", "INT. SALLE BLANCHE - JOUR"],
          str([s["slugline"] for s in sc]))
    check("F2 tout moment et tout INT/EXT est un de ceux de l'atelier", all(s["moment"] in SI.MOMENTS and s["int_ext"] in SI.INT_EXT for s in sc))
    check("F3 l'original non traduit EXACTEMENT est rendu (later that night ; CONTINUOUS herite du precedent) ; rien sinon",
          [s["moment_original"] for s in sc] == [None, "later that night", "CONTINUOUS", None], str([s["moment_original"] for s in sc]))
    check("F4 numero de scene #12# ote du lieu ; en-tete forcee « .SALLE » marquee (INT par defaut), « ! » reste une action",
          sc[1]["lieu"] == "FALAISE" and sc[3]["ie_force"] and not sc[2]["ie_force"] and "!EXT. DANS LE TEXTE" in sc[2]["texte"])
    check("F5 repliques : extension et « ^ » otes du nom, « @McCLANE » garde sa casse dans la distribution, CAPITALES dans le texte",
          sc[0]["personnages"] == ["VANE", "YSOLDE", "BOB"] and sc[1]["personnages"] == ["McCLANE"] and "YSOLDE\n(bas)" in sc[0]["texte"]
          and "^" not in sc[0]["texte"] and "VANE (V.O.)" in sc[0]["texte"] and sc[1]["texte"].startswith("MCCLANE\nYippee."), str(sc[:2]))
    check("F6 page de titre SANS ligne vide : la 1re en-tete n'est pas avalee ; valeur indentee jointe",
          r["titre"] == "Le Phare" and r["meta"].get("author") == "Moi et une autrice", str(r["meta"]))
    check("F7 notes, boneyard, sections, synopsis, sauts de page : ECARTES et COMPTES",
          r["ignores"] == {"boneyard": 1, "notes": 1, "sections": 1, "synopsis": 1, "sauts_de_page": 1}
          and "une note" not in sc[1]["texte"] and "coupe" not in sc[1]["texte"], str(r["ignores"]))
    check("F8 transitions GARDEES dans le texte (CUT TO:, > FIN <)", sc[0]["texte"].endswith("CUT TO:") and "> FIN <" in sc[3]["texte"])
    r = SI.lire("FADE IN:\r\rINT. A - DAY\r\rIl dit l’ami.\r".encode("cp1252"), "y.txt")
    check("F9 cp1252 (’), fins de ligne CR seules ; « FADE IN: » n'est pas une cle de titre : rattache a la 1re scene, et dit",
          r["prologue"] and r["scenes"][0]["texte"] == "FADE IN:\n\nIl dit l’ami." and r["meta"] == {}, str(r))
    r = SI.lire(b"\xef\xbb\xbfEXT. PLAGE - LE LENDEMAIN\n\nLa mer.", "b.fountain")
    check("F10 BOM ote ; moment inconnu -> JOUR, l'original rendu", r["scenes"][0]["slugline"] == "EXT. PLAGE - JOUR"
          and r["scenes"][0]["moment_original"] == "LE LENDEMAIN", str(r["scenes"]))
    check("F11 un texte SANS en-tete n'est pas un scenario : refus (rien n'est remplace)",
          "Aucune en-tête" in (leve(lambda: SI.lire("Un roman.\n\nSans scene.\n\n...Et des points.".encode(), "z.txt")) or ""))

    print("\n[X] Final Draft")
    FDX = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<FinalDraft DocumentType="Script" Template="No" Version="5">
<Content>
<Paragraph Type="Scene Heading"><Text>INT. BUREAU - DAY</Text></Paragraph>
<Paragraph Type="Action"><Text>Elias </Text><Text Style="Bold">regarde</Text><Text> dehors.</Text></Paragraph>
<Paragraph Type="Action"><Text>EXT. CE N'EST PAS UNE SCENE</Text></Paragraph>
<Paragraph Type="Character"><Text>ELIAS</Text></Paragraph>
<Paragraph Type="Parenthetical"><Text>(las)</Text></Paragraph>
<Paragraph Type="Dialogue"><Text>Assez.</Text></Paragraph>
<Paragraph><DualDialogue>
<Paragraph Type="Character"><Text>BRICK</Text></Paragraph><Paragraph Type="Dialogue"><Text>Screw it.</Text></Paragraph>
<Paragraph Type="Character"><Text>STEEL</Text></Paragraph><Paragraph Type="Dialogue"><Text>Screw it too.</Text></Paragraph>
</DualDialogue></Paragraph>
<Paragraph Type="Transition"><Text>Cut to:</Text></Paragraph>
<Paragraph Type="Scene Heading"><Text>.</Text></Paragraph>
<Paragraph Type="Scene Heading"><Text>PLAGE - DUSK</Text></Paragraph>
<Paragraph Type="Cast List"><Text>ELIAS</Text></Paragraph>
<Paragraph Type="Action"><Text>La mer.</Text></Paragraph>
</Content>
<TitlePage><Content><Paragraph><Text>Mon Film</Text></Paragraph><Paragraph><Text>\t</Text><DynamicLabel/><Text>.</Text></Paragraph></Content></TitlePage>
</FinalDraft>"""
    r = SI.lire(FDX.encode("utf-8"), "f.fdx")
    sc = r["scenes"]
    check("X1 deux scenes (le « . » n'en est pas une), page de titre HORS des scenes, titre lu",
          r["format"] == "fdx" and [s["slugline"] for s in sc] == ["INT. BUREAU - JOUR", "INT. PLAGE - CRÉPUSCULE"]
          and r["titre"] == "Mon Film" and "Mon Film" not in sc[0]["texte"] + sc[1]["texte"], str([s["slugline"] for s in sc]))
    t0 = sc[0]["texte"]
    check("X2 dialogue double lu UNE fois, les styles fondus, la parenthese attachee a la replique",
          t0.count("Screw it.") == 1 and t0.count("Screw it too.") == 1 and "BRICKScrew" not in t0 and "Elias regarde dehors." in t0
          and "ELIAS\n(las)\nAssez." in t0 and sc[0]["personnages"] == ["ELIAS", "BRICK", "STEEL"], repr(t0))
    check("X3 une action en capitales est FORCEE en action (pas une scene) ; la transition en capitales",
          "!EXT. CE N'EST PAS UNE SCENE" in t0 and t0.endswith("CUT TO:"), repr(t0))
    check("X4 ce qui n'a pas d'equivalent est compte (Cast List, en-tete vide) ; une en-tete sans INT/EXT est marquee",
          r["ignores"] == {"en_tetes_vides": 1, "Cast List": 1} and sc[1]["ie_force"], str(r["ignores"]))
    check("X5 DOCTYPE / ENTITY refuses (aucune entite resolue)",
          "DOCTYPE" in (leve(lambda: SI.lire(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><FinalDraft/>', "e.fdx")) or ""))
    check("X6 un XML qui n'est pas Final Draft : refus", "Final Draft" in (leve(lambda: SI.lire(b"<?xml version='1.0'?><svg/>", "e.fdx")) or ""))
    check("X7 un FDX renomme .xml est reconnu a sa signature", SI.lire(FDX.encode("utf-8"), "f.xml")["format"] == "fdx")

    print("\n[V] la voix-off ne lit pas ce qui n'est pas dit")
    from app.services import manuscript_agent as MA
    segs = MA.parse_fountain_segments("Vane entre. [[note]]\n\nCUT TO:\n\n!LA PORTE CLAQUE.\n\nVANE\nIl pleut.\n\n> FIN <\n\nFADE OUT.")
    lus = " ".join(s["text"] for s in segs)
    check("V1 ni « CUT TO: », ni « > FIN < », ni « FADE OUT. », ni la note, ni le « ! » ; la replique et l'action restent",
          "CUT TO" not in lus and "FIN" not in lus and "FADE" not in lus and "note" not in lus and "!" not in lus
          and "LA PORTE CLAQUE." in lus and ("dialogue", "VANE", "Il pleut.") in [(s["kind"], s["character"], s["text"]) for s in segs], str(segs))

# ── la route ──────────────────────────────────────────────────────────────────────────────────────────────────────
sys.modules["fal_client"] = types.ModuleType("fal_client")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def envoyer(c, cid, nom, data, mode=None):
    return c.post(f"/api/chapters/{cid}/screenplay/import", files={"file": (nom, data)}, data=({"mode": mode} if mode else {}))


def scenes(c, cid):
    return js(c.get(f"/api/chapters/{cid}/scenes")).get("scenes", [])


print("\n[R] la route")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    check("R1 chapitre inconnu : 404", envoyer(c, "inconnu", "a.fountain", b"INT. A - DAY\n\nx").status_code == 404)
    ch = js(c.post("/api/chapters", json={"title": "C", "script_text": "Il etait une fois."}))
    cid = ch.get("id")
    vane = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Vane Ardel", "description": "x"}))
    sqlite3.connect(str(_DB)).execute("UPDATE bible_entities SET aliases=? WHERE id=?", (json.dumps(["Vane"]), vane.get("id"))).connection.commit()
    falaise = js(c.post("/api/bible/entities", json={"kind": "place", "name": "Falaise", "description": "x"}))
    r = envoyer(c, cid, "x.fountain", FOUNTAIN.encode("utf-8"))
    j = js(r)
    sc = scenes(c, cid)
    check("R2 import dans un chapitre vide : 200, 4 scenes, dans l'ordre, sluglines traduites",
          r.status_code == 200 and j.get("scenes") == 4 and [s["slugline"] for s in sc] == ["INT. CUISINE - NUIT", "EXT. FALAISE - NUIT",
          "INT/EXT. VOITURE - NUIT", "INT. SALLE BLANCHE - JOUR"] and [s["idx"] for s in sc] == [0, 1, 2, 3], f"{r.status_code} {r.text[:200]}")
    check("R3 les lieux : FALAISE retrouve (pas de doublon), les autres crees ; Vane lie PAR SON ALIAS",
          sc[1]["location_entity_id"] == falaise.get("id") and j.get("lieux_crees") == 3 and vane.get("id") in sc[0]["entities"]
          and j.get("personnages_lies") == 1, f"{j} {sc[0]['entities']}")
    check("R4 l'original du moment et l'INT/EXT par defaut sont NOTES dans les notes camera ; les ecartes rendus",
          sc[1]["camera_notes"] == "Moment d'origine : later that night" and "INT/EXT non précisé" in sc[3]["camera_notes"]
          and j.get("ignores", {}).get("notes") == 1, str([s["camera_notes"] for s in sc]))
    s1 = sc[1]
    c.put(f"/api/scenes/{s1['id']}", json={"fountain_text": s1["fountain_text"] + "\nUne ligne."})
    c.put(f"/api/scenes/{sc[2]['id']}", json={"mood": "tendu"})
    sc2 = scenes(c, cid)
    check("R5 LE BUG DU PLAN : editer une scene importee ne reecrit PAS sa slugline", [s["slugline"] for s in sc2] == [s["slugline"] for s in sc],
          str([s["slugline"] for s in sc2]))
    with sqlite3.connect(str(_DB)) as db:
        db.execute("UPDATE scenes SET vo_audio='vo.mp3' WHERE id=?", (sc[0]["id"],))
    avant = [s["fountain_text"] for s in scenes(c, cid)]
    r = envoyer(c, cid, "roman.txt", "Un roman.\n\nSans scene.".encode())
    check("R6 un texte qui n'est pas un scenario : 422, et le scenario existant est INTACT",
          r.status_code == 422 and [s["fountain_text"] for s in scenes(c, cid)] == avant, f"{r.status_code} {r.text[:120]}")
    check("R7 mode inconnu : 400", envoyer(c, cid, "x.fountain", b"INT. A - DAY\n\nx", mode="fusionner").status_code == 400)
    r = envoyer(c, cid, "f.fdx", FDX.encode("utf-8") if SI else b"")
    j = js(r)
    sc3 = scenes(c, cid)
    vers = js(c.get(f"/api/chapters/{cid}/versions")).get("versions", [])
    sauve = [v for v in vers if v.get("kind") == "scenario" and v.get("passe") == "import_scenario"]
    lu = js(c.get(f"/api/versions/{sauve[0]['id']}")) if sauve else {}
    check("R8 REMPLACER : les 4 scenes cedent la place aux 2 du FDX ; la reponse dit combien ont ete remplacees",
          r.status_code == 200 and j.get("remplacees") == 4 and [s["slugline"] for s in sc3] == ["INT. BUREAU - JOUR", "INT. PLAGE - CRÉPUSCULE"],
          f"{r.status_code} {j}")
    check("R9 ... et le scenario ENTIER d'avant est sauvegarde : UNE version « import_scenario », VISIBLE dans le tiroir, lisible",
          len(sauve) == 1 and "Une ligne." in lu.get("text", "") and "CUISINE" in lu.get("text", ""), f"{[ (v.get('kind'), v.get('passe')) for v in vers]}")
    r = envoyer(c, cid, "b.fountain", b"EXT. JARDIN - MORNING\n\nDes oiseaux.", mode="ajouter")
    sc4 = scenes(c, cid)
    vers2 = js(c.get(f"/api/chapters/{cid}/versions")).get("versions", [])
    check("R10 AJOUTER : a la suite (idx 2), rien de supprime, aucune sauvegarde de plus",
          r.status_code == 200 and js(r).get("remplacees") == 0 and [s["slugline"] for s in sc4][-1] == "EXT. JARDIN - MATIN"
          and [s["idx"] for s in sc4] == [0, 1, 2] and len(vers2) == len(vers), f"{[ (s['idx'], s['slugline']) for s in sc4]}")
    exp = c.get(f"/api/chapters/{cid}/screenplay", params={"format": "fountain"}).text
    ch2 = js(c.post("/api/chapters", json={"title": "D", "script_text": "x"}))
    envoyer(c, ch2.get("id"), "aller-retour.fountain", exp.encode("utf-8"))
    sc5 = scenes(c, ch2.get("id"))
    check("R11 aller-retour export -> import : memes sluglines, memes textes",
          [(s["slugline"], s["fountain_text"]) for s in sc5] == [(s["slugline"], s["fountain_text"]) for s in sc4],
          f"{[s['slugline'] for s in sc5]}")
    with sqlite3.connect(str(_DB)) as db:
        db.execute("INSERT INTO chapter_locks (chapter_id, device_id, device_nom, base_sha256, pris_le) VALUES (?,?,?,?,?)",
                   (cid, "dev1", "Pixel", "", datetime.utcnow().isoformat(sep=" ")))
    avant = [s["id"] for s in scenes(c, cid)]
    r = envoyer(c, cid, "x.fountain", FOUNTAIN.encode("utf-8"))
    check("R12 chapitre EMPORTE par le telephone : 423, rien ne bouge", r.status_code == 423 and [s["id"] for s in scenes(c, cid)] == avant,
          f"{r.status_code}")
    with sqlite3.connect(str(_DB)) as db:
        db.execute("DELETE FROM chapter_locks")
    r = envoyer(c, cid, "gros.fountain", b"INT. A - DAY\n\n" + b"x" * (8 * 1024 * 1024 + 1))
    check("R13 plus de 8 Mo : 413", r.status_code == 413)

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
import re as _re                                                     # noqa: E402
_at = _ICI.parent.parent / "frontend" / "atelier"
_js = (_at / "atelier.js").read_text(encoding="utf-8")
_html = (_at / "index.html").read_text(encoding="utf-8")
_fn = _js.split("async function importerScenario(")[1].split("\n}\n")[0] if "async function importerScenario(" in _js else ""
check("U1 le bouton d'import (label avec title) et son champ fichier .fountain/.fdx",
      _re.search(r'<label class="btn" for="spImportFile" title="[^"]+">', _html) is not None
      and 'id="spImportFile" accept=".fountain,.spmd,.txt,.fdx"' in _html)
_garde = _fn.find("const remplacer = await window.__dzDialogue.confirmer(")
_post = _fn.find("method: \"POST\"")
check("U2 REMPLACER est confirme AVANT l'envoi, en nommant les scenes et les voix-off perdues ; refuser deux fois = rien",
      0 <= _garde < _post and "${scenes.length} scène(s)" in _fn and "voix-off" in _fn
      and 'if (!await window.__dzDialogue.confirmer(`Ajouter' in _fn and '{ ok: "Ajouter à la suite" })) return;' in _fn
      and not _re.search(r"(?<![.\w])confirm\(", _fn), f"garde={_garde} post={_post}")
check("U3 le mode part avec le fichier ; le tiroir nomme la sauvegarde", 'fd.append("mode", mode)' in _fn
      and 'import_scenario: "scénario importé"' in _js)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
