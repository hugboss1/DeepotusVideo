# -*- coding: utf-8 -*-
"""t240 (lot « Studio : Animation », 18/10/2026) — personnaliser une direction côté chorégraphe.

Spec docs/superpowers/specs/2026-10-18-studio-animation-personnalisation.md § P1-P6 et P8, plan t240. Le corps de
`POST /api/motion/choregraphier` gagne `direction.champs`, `direction.precisions`, `direction.curseurs` et `tempo_bpm` ;
`effort` (t239) reste tel quel.

Zéro dépense : un FAUX OLLAMA (127.0.0.1, port tiré au hasard, jamais 8765) rend les réponses de sa file et note chaque
corps reçu (le prompt système compris). Le skill vient d'un faux miroir GitHub en mémoire. Ce que ce banc garde :
  [C] les 11 fiches maison déclarent leurs `champs` (id, libellé et aide FR/EN, défaut, type texte / nombre / liste,
      bornes) et leur consigne FR et EN cite chacun par `{{id}}`, rien d'autre ; GET /api/motion/biblio/{id} les rend ;
  [U] substitution : vide ou absent → défaut (dans la langue), texte nettoyé et tronqué, nombre borné, liste hors
      options → défaut, id inconnu ignoré, une valeur qui contient `{{…}}` n'est jamais substituée à son tour ;
  [P] bloc de précisions (prompt importé, skill) : APRÈS la consigne, avec la règle de priorité, texte importé intact
      (dans le prompt système ET dans la bibliothèque) ; sans source → ignoré ; champs vides → pas de bloc ;
  [T] tempo : 40-220 BPM, donné au prompt système ; les `start` du modèle et du repli tombent sur les temps (bornes
      respectées) ; sans tempo, rien ne bouge ;
  [K] curseurs : 0-4, 2 = neutre ; Créativité et Rythme ajoutent NOTRE phrase (FR / EN) en fin de direction, aucune au
      neutre ; Finition 0-1 → une tentative avant le repli, 2 → deux, 3-4 → passe de vérification (bornes, deux textes
      au même endroit au même instant, tenue minimale) ; route de lecture GET /api/motion/personnalisation ;
  [Q] P6 : le modèle ne pose aucune question ; P4 : `marque` remplace le kit ; `effort` / `effort_applique` intacts ;
  [G] garde G3 sur nos textes neufs (fiches, phrases) : aucune empreinte du catalogue tiers.
Run (depuis backend/) : & $PY tests/test_motion_personnalisation.py"""
import asyncio, hashlib, json, os, pathlib, re, sys, tempfile, threading, unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzperso_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.pop("DZ_MOTION_MIROIR_GITHUB", None)
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
           "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\n", encoding="utf-8")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import motion_biblio as MB                        # noqa: E402
from app.services import motion_choregraphe as CH                   # noqa: E402

CAC.appliquer({"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "", "OLLAMA_MODEL": "",
               "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})
c = TestClient(app)
cd = TestClient(app, client=("192.168.1.50", 5000))

# ── faux Ollama ───────────────────────────────────────────────────────────────────────────────────────────────────
OLL, FILE = [], []


class _Ollama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _rendre(self, code, obj):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._rendre(200, {"models": [{"name": "llama3"}]})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/api/show":
            return self._rendre(200, {"capabilities": ["completion"]})
        OLL.append(corps)
        txt = FILE.pop(0) if len(FILE) > 1 else (FILE[0] if FILE else "{}")
        self._rendre(200, {"response": txt, "done": True})


_srv = ThreadingHTTPServer(("127.0.0.1", 0), _Ollama)
assert _srv.server_address[1] != 8765
threading.Thread(target=_srv.serve_forever, daemon=True).start()
settings.OLLAMA_URL = f"http://127.0.0.1:{_srv.server_address[1]}"
CAC.appliquer({"OLLAMA_MODEL": "llama3"})


def el(text, start, x=50, y=50, dur=0.4, hold=1.0):
    return {"type": "text", "text": text, "start": start, "dur": dur, "hold": hold,
            "keyframes": [{"t": 0, "x": x, "y": y, "opacity": 0}, {"t": 1, "x": x, "y": y, "opacity": 1}]}


def rep(*elements):
    return json.dumps({"elements": list(elements)})


def chor(corps, langue="fr"):
    OLL.clear()
    return asyncio.run(CH.choregraphier(corps, langue))


def sy():
    return OLL[-1].get("system", "") if OLL else ""


PERSO = CH.personnalisation() if callable(getattr(CH, "personnalisation", None)) else {}

# ── [C] fiches à champs ───────────────────────────────────────────────────────────────────────────────────────────
print("[C] fiches maison à champs")
_PH = re.compile(r"\{\{([a-z0-9_]+)\}\}")
fiches = {f["theme"]: f for f in MB.lister("style")}
check("C1 11 fiches", len(fiches) == 11, sorted(fiches))
for th, f in sorted(fiches.items()):
    champs = f.get("champs")
    defauts = []
    if not isinstance(champs, list) or len(champs) < 2:
        check(f"C2 {th} : au moins deux champs", False, champs)
        continue
    ids = [ch.get("id") for ch in champs]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and re.fullmatch(r"[a-z][a-z0-9_]{1,30}", i)
                                            for i in ids):
        defauts.append(f"ids {ids}")
    for ch in champs:
        for k in ("libelle", "aide"):
            v = ch.get(k) or {}
            if not (isinstance(v, dict) and str(v.get("fr", "")).strip() and str(v.get("en", "")).strip()):
                defauts.append(f"{ch.get('id')}.{k}")
        t = ch.get("type")
        if t == "texte":
            d = ch.get("defaut") or {}
            if not (isinstance(d, dict) and d.get("fr") and d.get("en") and isinstance(ch.get("max"), int)
                    and max(len(d["fr"]), len(d["en"])) <= ch["max"] <= 400):
                defauts.append(f"{ch['id']} texte {d} {ch.get('max')}")
        elif t == "nombre":
            if not (isinstance(ch.get("min"), (int, float)) and isinstance(ch.get("max"), (int, float))
                    and ch["min"] <= ch.get("defaut", ch["min"] - 1) <= ch["max"]):
                defauts.append(f"{ch['id']} nombre")
        elif t == "liste":
            op = ch.get("options") or []
            vals = [o.get("valeur") for o in op]
            if len(op) < 2 or ch.get("defaut") not in vals or not all(
                    o.get("libelle", {}).get("fr") and o.get("libelle", {}).get("en") for o in op):
                defauts.append(f"{ch['id']} liste")
        else:
            defauts.append(f"{ch.get('id')} type {t}")
    for lg in ("fr", "en"):
        cites = set(_PH.findall(f["consigne"][lg]))
        if cites != set(ids):
            defauts.append(f"{lg} cite {sorted(cites)} ≠ {sorted(ids)}")
        if f["consigne"][lg].count("{{") != len(_PH.findall(f["consigne"][lg])):
            defauts.append(f"{lg} accolade orpheline")
    check(f"C2 {th} : {len(champs)} champs complets, tous cités FR et EN, rien d'autre", not defauts, defauts)
r = c.get("/api/motion/biblio/style-kinetic-type")
check("C3 GET /api/motion/biblio/{id} rend les champs", r.status_code == 200
      and [x["id"] for x in r.json().get("champs", [])] == [x["id"] for x in fiches.get("kinetic-type", {})
                                                             .get("champs", [])] and r.json().get("champs"),
      r.text[:200])
# Défauts substitués = consigne sans aucune accolade, et pour kinetic-type le texte d'origine (t233) à l'identique.
_ok_def = True
for th, f in fiches.items():
    for lg in ("fr", "en"):
        d = CH.direction({"style": f"style-{th}"}, lg) if f.get("champs") else {}
        if "{{" in (d.get("consigne_style") or "{{"):
            _ok_def = False
check("C4 aucun {{…}} ne reste une fois les défauts posés (11 fiches, FR et EN)", _ok_def)
d = CH.direction({"style": "style-kinetic-type"}, "fr")
check("C5 défauts : la consigne d'origine revient (polices, fond, marque)",
      "(Anton, Bebas Neue, Archivo Black) sur un fond uni très contrasté" in d.get("consigne_style", "")
      and "se termine sur la marque" in d.get("consigne_style", ""), d.get("consigne_style", "")[:300])

# ── [U] substitution ──────────────────────────────────────────────────────────────────────────────────────────────
print("[U] substitution des champs")
d = CH.direction({"style": "style-kinetic-type", "champs": {"fond": "un ciel violet", "mots_max": 99,
                                                             "inconnu": "ZETA-INCONNU", "fin": "  "}}, "fr")
cs = d.get("consigne_style", "")
check("U1 texte rempli → remplace la partie", "sur un ciel violet" in cs and "fond uni" not in cs, cs[:400])
check("U2 nombre hors borne → borné (99 → 6)", "6 mots à l'écran au plus" in cs, cs[:300])
check("U3 texte vide (espaces) → défaut", "se termine sur la marque" in cs)
check("U4 champ absent → défaut", "(Anton, Bebas Neue, Archivo Black)" in cs)
check("U5 id inconnu ignoré (ni dans la consigne ni dans les valeurs)", "ZETA" not in cs
      and "inconnu" not in (d.get("champs") or {}), d.get("champs"))
check("U6 valeurs appliquées rendues (défaut compris)", (d.get("champs") or {}).get("mots_max") == 6
      and d["champs"].get("fond") == "un ciel violet" and d["champs"].get("fin") == "la marque", d.get("champs"))
d = CH.direction({"style": "style-kinetic-type", "champs": {"fond": "X" * 500 + "\x07", "mots_max": "abc"}}, "fr")
cs = d.get("consigne_style", "")
_mx = next(x["max"] for x in fiches["kinetic-type"]["champs"] if x["id"] == "fond")
check("U7 texte tronqué au max du champ, nettoyé", ("sur " + "X" * _mx + ".") in cs and "X" * (_mx + 1) not in cs
      and "\x07" not in cs, cs[:200])
check("U8 nombre illisible → défaut (3)", "3 mots à l'écran au plus" in cs)
d = CH.direction({"style": "style-kinetic-type", "champs": {"mots_max": 1.5, "polices": True}}, "fr")
check("U9 nombre décimal borné, non-texte → défaut", "1.5 mots" in d.get("consigne_style", "")
      and "(Anton, Bebas Neue, Archivo Black)" in d.get("consigne_style", ""), d.get("consigne_style", "")[:200])
d = CH.direction({"style": "style-kinetic-type", "champs": {"fond": "{{fin}} {{mots_max}}"}}, "fr")
check("U10 une valeur contenant {{…}} n'est pas substituée à son tour",
      "sur {{fin}} {{mots_max}}" in d.get("consigne_style", ""), d.get("consigne_style", "")[:300])
d = CH.direction({"style": "style-diagrams", "champs": {"sens": "vertical"}}, "en")
d2 = CH.direction({"style": "style-diagrams", "champs": {"sens": "diagonale"}}, "fr")
check("U11 liste : option → son libellé dans la langue ; hors options → défaut",
      "top to bottom" in d.get("consigne_style", "") and "left to right" not in d.get("consigne_style", "")
      and "de gauche à droite ou de haut en bas" in d2.get("consigne_style", "")
      and d2.get("champs", {}).get("sens") == "libre", (d.get("champs"), d2.get("champs")))
d = CH.direction({"style": "style-kinetic-type"}, "en")
check("U12 défauts EN en anglais", "on a flat, high-contrast background" in d.get("consigne_style", "")
      and "lands on the brand" in d.get("consigne_style", ""))
d = CH.direction({"style": "style-kinetic-type", "champs": "pas un objet"}, "fr")
check("U13 champs non-objet → défauts, sans erreur", "se termine sur la marque" in d.get("consigne_style", ""))
FILE[:] = [rep(el("Bonjour", 0))]
r = c.post("/api/motion/choregraphier", json={"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
                                              "direction": {"style": "style-kinetic-type",
                                                            "champs": {"fond": "un dégradé ZETA-FOND"}}})
check("U14 par la route : la valeur part au modèle, la réponse rend les champs appliqués",
      r.status_code == 200 and "sur un dégradé ZETA-FOND" in sy() and "fond uni" not in sy()
      and r.json().get("champs", {}).get("fond") == "un dégradé ZETA-FOND", (r.status_code, r.text[:300]))
d = CH.direction({"source": None, "champs": {"fond": "x"}}, "fr")
check("U15 sans fiche, des champs sont ignorés", not d.get("champs") and not d.get("consigne_style"))

# ── [P] bloc de précisions ────────────────────────────────────────────────────────────────────────────────────────
print("[P] bloc de précisions")
TEXTE = "Ligne une du prompt ZETA-IMPORT.\n  Ligne deux, indentée, avec des « guillemets ».\nLigne trois."
r = c.post("/api/motion/biblio", json={"titre": "Import banc", "texte": TEXTE, "url": "https://exemple.test/f/1"})
PID = r.json().get("id")
PREC = {"usage": "une annonce de lancement", "duree": "12 s", "couleurs": "noir et or", "police": "Bebas Neue",
        "autre": "finir sur le logo ZETA-AUTRE"}
FILE[:] = [rep(el("Bonjour", 0))]
r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
          "direction": {"style": "style-kinetic-type", "source": PID, "precisions": PREC}})
s = sy()
i_txt, i_bloc = s.find(TEXTE), s.find("ZETA-AUTRE")
check("P1 le texte importé est dans le prompt système, intact", i_txt >= 0, s[-600:])
check("P2 le bloc vient APRÈS la consigne importée", 0 <= i_txt < i_bloc, (i_txt, i_bloc))
regle_fr = (PERSO.get("precisions") or {}).get("regle", {}).get("fr", "§§")
check("P3 la règle « en cas de conflit, ces précisions priment » est posée avant les lignes", regle_fr in s
      and "priment" in regle_fr and i_txt < s.find(regle_fr) < i_bloc, regle_fr)
check("P4 les cinq précisions, avec leur libellé", all(v in s for v in PREC.values())
      and all(x["libelle"]["fr"] in s for x in (PERSO.get("precisions") or {}).get("champs", [])), s[-500:])
check("P5 la réponse dit que les précisions sont appliquées", r.get("precisions") is True, r.get("precisions"))
check("P6 l'entrée de la bibliothèque n'est pas modifiée", MB.lire(PID).get("texte") == TEXTE)
FILE[:] = [rep(el("Bonjour", 0))]
r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
          "direction": {"source": PID, "precisions": PREC}}, "en")
regle_en = (PERSO.get("precisions") or {}).get("regle", {}).get("en", "§§")
check("P7 en anglais : la règle anglaise", regle_en in sy() and regle_fr not in sy() and "ZETA-AUTRE" in sy())
FILE[:] = [rep(el("Bonjour", 0))]
r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
          "direction": {"style": "style-kinetic-type", "precisions": PREC}})
check("P8 sans prompt ni skill : précisions ignorées", "ZETA-AUTRE" not in sy() and regle_fr not in sy()
      and r.get("precisions") is False, r.get("precisions"))
FILE[:] = [rep(el("Bonjour", 0))]
r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
          "direction": {"source": PID, "precisions": {"usage": "  ", "autre": ""}}})
check("P9 précisions vides : pas de bloc", regle_fr not in sy() and r.get("precisions") is False)
FILE[:] = [rep(el("Bonjour", 0))]
r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
          "direction": {"source": PID, "precisions": {"autre": "Y" * 2000, "pirate": "ZETA-PIRATE"}}})
check("P10 précision tronquée, clé inconnue ignorée", "Y" * 300 in sy() and "Y" * 301 not in sy()
      and "ZETA-PIRATE" not in sy())
FILE[:] = [rep(el("Bonjour", 0))]
r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
          "direction": {"source": PID, "precisions": {"pirate": "ZETA-PIRATE"}}})
check("P10b seulement des clés inconnues : rien de retenu, pas de bloc", CH.precisions({"pirate": "x", "usage": "u"})
      == {"usage": "u"} and r.get("precisions") is False and regle_fr not in sy(), r.get("precisions"))
# un skill (faux miroir GitHub) : consigne éditée + précisions
MIT = ("MIT License\n\nCopyright (c) 2026 Banc\n\nPermission is hereby granted, free of charge, to any person obtaining "
       "a copy of this software, to deal in the Software without restriction. THE SOFTWARE IS PROVIDED \"AS IS\", "
       "WITHOUT WARRANTY OF ANY KIND.\n")
SKILL = "---\nname: banc-perso\ndescription: skill du banc t240\n---\n\n# Banc\n\nSKILL-ZETA-ORIGINE\n"
_MIR = {"/banc/skill-perso/HEAD/SKILL.md": SKILL, "/banc/skill-perso/HEAD/LICENSE": MIT}
MB._transport = httpx.MockTransport(lambda q: httpx.Response(200, text=_MIR[q.url.path]) if q.url.path in _MIR
                                    else httpx.Response(404))
r = c.post("/api/motion/skills/installer", json={"source": "banc/skill-perso"})
SID = r.json().get("id")
FILE[:] = [rep(el("Bonjour", 0))]
chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
      "direction": {"source": SID, "consigne": "CONSIGNE-EDITEE-ZETA", "precisions": {"couleurs": "rouge ZETA-C"}}})
s = sy()
check("P11 skill : consigne éditée puis bloc de précisions", 0 <= s.find("CONSIGNE-EDITEE-ZETA") < s.find("ZETA-C")
      and regle_fr in s, s[-400:])
check("P12 skill : l'original reste à l'octet", r.status_code == 200 and MB.lire(SID).get("original") == SKILL)

# ── [T] tempo ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[T] tempo")
check("T1 tempo borné 40-220, absent / illisible → None",
      [CH.tempo(v) for v in (None, 30, 300, 120, "abc", True, 0, float("nan"))]
      == [None, 40, 220, 120, None, None, None, None], [CH.tempo(v) for v in (None, 30, 300, 120, "abc", True, 0)])


def sur_les_temps(els, bpm):
    b = 60 / bpm
    return all(abs(e["start"] / b - round(e["start"] / b)) < 1e-3 for e in els)


FILE[:] = [rep(el("Un", 0.13), el("Deux", 1.37), el("Trois", 2.9), el("Quatre", 7.99))]
r = chor({"script": "Un\nDeux\nTrois\nQuatre", "moteur": "ollama", "modele": "llama3", "duree_s": 8,
          "tempo_bpm": 120})
st = [e["start"] for e in r.get("elements", [])]
check("T2 modèle : starts calés au temps le plus proche (120 BPM = 0,5 s), la fin bornée", st == [0, 1.5, 3.0, 7.5]
      and r.get("tempo_bpm") == 120, st)
check("T3 bornes tenues : start + dur + hold ≤ durée", all(e["start"] + e["dur"] + e["hold"] <= 8 + 1e-6
                                                          for e in r.get("elements", [])))
check("T4 le prompt système donne le tempo et la durée d'un temps", "120 BPM" in sy() and "0.5 s" in sy(), sy()[-300:])
FILE[:] = [rep(el("Un", 0.13), el("Deux", 1.37))]
r = chor({"script": "Un\nDeux", "moteur": "ollama", "modele": "llama3", "duree_s": 8})
check("T5 sans tempo : starts du modèle inchangés, rien dans le prompt", [e["start"] for e in r["elements"]]
      == [0.13, 1.37] and "BPM" not in sy() and r.get("tempo_bpm") is None, [e["start"] for e in r["elements"]])
r = chor({"script": "Le fond marin\nDeepotus plonge dans le grand bleu\nfin", "duree_s": 7, "tempo_bpm": 90,
          "direction": {"style": "style-kinetic-type"}})
els = r["elements"]
check("T6 repli : starts sur les temps (90 BPM), croissants, tenue jusqu'au suivant", r["repli"] and
      sur_les_temps(els, 90) and [e["start"] for e in els] == sorted({e["start"] for e in els})
      and all(abs(a["start"] + a["dur"] + a["hold"] - b["start"]) < 2e-3 for a, b in zip(els, els[1:]))
      and abs(els[-1]["start"] + els[-1]["dur"] + els[-1]["hold"] - 7) < 2e-3, [(e["start"], e["dur"], e["hold"])
                                                                                for e in els])
r = c.post("/api/motion/choregraphier", json={"script": "Un\nDeux", "tempo_bpm": 128, "duree_s": 6, "aspect": "4:5"})
check("T7 par la route : tempo, format et durée de la requête", r.status_code == 200 and r.json()["tempo_bpm"] == 128
      and r.json()["aspect"] == "4:5" and r.json()["duree_s"] == 6 and sur_les_temps(r.json()["elements"], 128),
      r.text[:300])
r = c.post("/api/motion/choregraphier", json={"script": "Un", "direction": {"tempo_bpm": 100}})
check("T8 le tempo est aussi lu dans direction", r.json().get("tempo_bpm") == 100, r.json().get("tempo_bpm"))

# ── [K] curseurs ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] curseurs")
check("K1 normalisation : 0-4, 2 par défaut", CH.curseurs({"creativite": 9, "rythme": -3, "finition": "x"})
      == {"creativite": 4, "rythme": 0, "finition": 2} and CH.curseurs(None) == {"creativite": 2, "rythme": 2,
                                                                                  "finition": 2}
      and CH.curseurs({"creativite": True, "rythme": 3.0})["creativite"] == 2, CH.curseurs({"creativite": 9}))
cur = PERSO.get("curseurs") or {}
crans = {k: v.get("crans") or [] for k, v in cur.items()}
check("K2 trois curseurs à cinq crans, libellés FR/EN", sorted(cur) == ["creativite", "finition", "rythme"]
      and all(len(v) == 5 and all(x.get("etat", {}).get("fr") and x.get("etat", {}).get("en") for x in v)
              for v in crans.values()), {k: len(v) for k, v in crans.items()})
PH = {(k, i, lg): (crans.get(k) or [{}] * 5)[i].get("phrase") and crans[k][i]["phrase"][lg]
      for k in ("creativite", "rythme") for i in range(5) for lg in ("fr", "en")}
check("K3 une phrase FR/EN par cran hors neutre, aucune au neutre",
      all(PH[(k, i, lg)] for k in ("creativite", "rythme") for i in (0, 1, 3, 4) for lg in ("fr", "en"))
      and not any(PH[(k, 2, lg)] for k in ("creativite", "rythme") for lg in ("fr", "en")))
toutes = [v for v in PH.values() if v]
FILE[:] = [rep(el("Bonjour", 0))]
chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
      "direction": {"style": "style-kinetic-type", "curseurs": {"creativite": 2, "rythme": 2, "finition": 2}}})
check("K4 au neutre : aucune phrase ajoutée", not any(p in sy() for p in toutes))
FILE[:] = [rep(el("Bonjour", 0))]
chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
      "direction": {"style": "style-kinetic-type", "source": PID, "precisions": PREC,
                    "curseurs": {"creativite": 0, "rythme": 4}}})
s = sy()
check("K5 Créativité 0 et Rythme 4 : leurs phrases, en fin de direction (après la consigne, avant les précisions)",
      PH[("creativite", 0, "fr")] in s and PH[("rythme", 4, "fr")] in s
      and s.find(TEXTE) < s.find(PH[("creativite", 0, "fr")]) < s.find(regle_fr)
      and sum(p in s for p in toutes) == 2, s[-700:])
FILE[:] = [rep(el("Bonjour", 0))]
chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
      "direction": {"style": "style-kinetic-type", "curseurs": {"creativite": 3, "rythme": 1}}}, "en")
check("K6 en anglais : les phrases anglaises", PH[("creativite", 3, "en")] in sy() and PH[("rythme", 1, "en")] in sy()
      and PH[("creativite", 3, "fr")] not in sy())
for fin, attendu in ((0, 1), (1, 1), (2, 2), (4, 2)):
    FILE[:] = ["pas du JSON"]
    r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3", "direction": {"curseurs": {"finition": fin}}})
    check(f"K7 finition {fin} → {attendu} tentative(s) avant le repli", r["tentatives"] == attendu and len(OLL)
          == attendu and r["repli"] and r["raison"] == "sortie_invalide", (r["tentatives"], len(OLL)))
# deux textes au même endroit au même instant, un texte qui ne tient pas
PIEGE = rep(el("Premier", 0, x=50, y=50, dur=0.4, hold=3), el("Second", 1, x=52, y=51, dur=0.4, hold=2),
            el("Éclair", 5, x=20, y=80, dur=0.05, hold=0))


def chevauchent(els):
    for i, a in enumerate(els):
        for b in els[i + 1:]:
            ka, kb = a["keyframes"][-1], b["keyframes"][-1]
            if abs(ka["x"] - kb["x"]) < 10 and abs(ka["y"] - kb["y"]) < 8 and \
                    a["start"] < b["start"] + b["dur"] + b["hold"] and b["start"] < a["start"] + a["dur"] + a["hold"]:
                return True
    return False


FILE[:] = [PIEGE]
r2 = chor({"script": "x", "moteur": "ollama", "modele": "llama3", "duree_s": 8,
           "direction": {"curseurs": {"finition": 2}}})
FILE[:] = [PIEGE]
r3 = chor({"script": "x", "moteur": "ollama", "modele": "llama3", "duree_s": 8,
           "direction": {"curseurs": {"finition": 3}}})
check("K8 finition 2 : pas de vérification (le piège reste)", chevauchent(r2["elements"])
      and not r2.get("verification", {}).get("faite"), r2.get("verification"))
check("K9 finition 3 : plus deux textes au même endroit au même instant", not chevauchent(r3["elements"])
      and r3["verification"]["faite"] and r3["verification"]["corrections"] >= 2, r3.get("verification"))
tmin = {e["text"]: e["dur"] + e["hold"] for e in r3["elements"]}
check("K10 finition 3 : tenue minimale (0,5 s) et bornes", tmin.get("Éclair", 0) >= 0.5 - 1e-6
      and all(0 <= e["start"] and e["start"] + e["dur"] + e["hold"] <= 8 + 1e-6 for e in r3["elements"])
      and len(r3["elements"]) == 3, tmin)
FILE[:] = [PIEGE]
r4 = chor({"script": "x", "moteur": "ollama", "modele": "llama3", "duree_s": 8, "tempo_bpm": 120,
           "direction": {"curseurs": {"finition": 4}}})
check("K11 finition 4 : tenue plus longue (0,8 s), tempo gardé après correction",
      min(e["dur"] + e["hold"] for e in r4["elements"]) >= 0.8 - 1e-6 and not chevauchent(r4["elements"])
      and sur_les_temps(r4["elements"], 120), [(e["start"], e["dur"], e["hold"]) for e in r4["elements"]])
r5 = chor({"script": "Un\nDeux", "direction": {"curseurs": {"finition": 3}}})
check("K12 le repli passe aussi la vérification à finition 3", r5["repli"] and r5["verification"]["faite"])
r = c.get("/api/motion/personnalisation")
j = r.json() if r.status_code == 200 else {}
check("K13 GET /api/motion/personnalisation : curseurs, neutre, précisions, tempo", r.status_code == 200
      and j.get("neutre") == 2 and sorted(j.get("curseurs", {})) == ["creativite", "finition", "rythme"]
      and [x["id"] for x in j.get("precisions", {}).get("champs", [])] == ["usage", "duree", "couleurs", "police",
                                                                          "autre"]
      and j.get("tempo") == {"min": 40, "max": 220} and j.get("precisions", {}).get("regle", {}).get("en"),
      r.text[:300])
check("K14 la finition dit son effet à chaque cran", all(x.get("effet", {}).get("fr") and x["effet"].get("en")
                                                          for x in crans.get("finition", [])))
r = cd.get("/api/motion/personnalisation")
check("K15 la route refuse un autre appareil", r.status_code in (401, 403), r.status_code)

# ── [Q] P4, P6, effort ────────────────────────────────────────────────────────────────────────────────────────────
print("[Q] marque, aucune question, effort")
FILE[:] = [rep(el("Bonjour", 0))]
r = chor({"script": "Bonjour", "moteur": "ollama", "modele": "llama3",
          "marque": {"couleur": "#aa00ff", "marque": "#ffcc00", "police": "Bebas Neue"}})
check("Q1 P4 : la marque du nœud remplace le kit (éléments et réponse)", r["elements"][0]["style"]["color"] == "#aa00ff"
      and r["elements"][0]["style"]["font"] == "Bebas Neue" and r.get("marque", {}).get("marque") == "#ffcc00",
      r.get("marque"))
check("Q2 P6 : le prompt système interdit de poser des questions", "Ne pose aucune question" in sy())
check("Q3 effort de t239 intact", r.get("effort") == "auto" and "effort_applique" in r)
r = c.post("/api/motion/choregraphier", json={"script": "Bonjour", "effort": "high"})
check("Q4 effort demandé rendu tel quel", r.json().get("effort") == "high" and r.json().get("effort_applique") == "")
check("Q5 la réponse rend les curseurs normalisés", r.json().get("curseurs") == {"creativite": 2, "rythme": 2,
                                                                                 "finition": 2})

# ── [G] garde G3 sur nos textes ───────────────────────────────────────────────────────────────────────────────────
print("[G] garde G3 sur nos textes neufs")


def _jetons(t):
    t = unicodedata.normalize("NFKD", t)
    return re.findall(r"[a-z0-9_]+", "".join(ch for ch in t if not unicodedata.combining(ch)).lower())


emp = json.loads((ICI / "motion_garde_empreintes.json").read_text(encoding="utf-8"))["empreintes"]
TETES = {}
for n, t, h in emp:
    TETES.setdefault(t, []).append((n, h))
nos = [RACINE / "backend" / "app" / "motion" / "personnalisation.json", RACINE / "backend" / "app" / "services" /
       "motion_choregraphe.py"] + sorted((RACINE / "backend" / "app" / "motion" / "styles").glob("*.json"))
trouves = []
for p in nos:
    jj = _jetons(p.read_text(encoding="utf-8")) if p.is_file() else []
    for i, j in enumerate(jj):
        for n, h in TETES.get(hashlib.sha256(("dzmotion1|" + j).encode()).hexdigest()[:12], ()):
            if hashlib.sha256(("dzmotion|" + " ".join(jj[i:i + n])).encode()).hexdigest()[:20] == h:
                trouves.append((p.name, h))
check(f"G1 {len(nos)} fichiers (phrases, fiches, module) : aucune empreinte du catalogue tiers",
      all(p.is_file() for p in nos) and not trouves, trouves[:10])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
