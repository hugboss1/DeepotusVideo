# -*- coding: utf-8 -*-
"""Card Forge — pièce 11 « Édition » à l'écran (tâche #84, plan-cartes T6-T7, 04/10/2026).
Les fonctions du panneau sont extraites du `mod-edition.js` LIVRÉ et EXÉCUTÉES sous node (CF, M, DOM simulés).
DÉCISION DE L'UTILISATEUR (04/10) : Tabletop Simulator = ZIP (planches + objet à chemins locaux) ET « Poser dans
Tabletop Simulator » (copie dans Saved Objects), sur demande.
Témoin positif : la pièce de la base (b6e81497) n'exporte rien.
Run (depuis backend/) : & $PY tests/test_cards_edition_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
SRC = (RACINE / "frontend" / "cardforge" / "js" / "mod-edition.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cfedie_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "b6e81497"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-edition.js"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la pièce de la base n'exporte rien", r0.returncode == 0 and b"exporterTts" not in r0.stdout and b'data-act="tts"' not in r0.stdout)
check("T2 trois boutons TITRÉS (TTS exporter / poser, Tabletopia), câblés", SRC.count('data-act="tts" title="') == 1
      and SRC.count('data-act="tts-poser" title="') == 1 and SRC.count('data-act="tabletopia" title="') == 1
      and 'else if (t.dataset.act === "tts") exporterTts();' in SRC and 'else if (t.dataset.act === "tts-poser") poserTts();' in SRC
      and 'else if (t.dataset.act === "tabletopia") exporterTabletopia();' in SRC)


def fonction(nom):
    k = SRC.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = SRC.find("{", SRC.find(")", k)), 0, None, False
    while i < len(SRC):
        c_ = SRC[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif SRC.startswith("/*", i):
            i = SRC.find("*/", i) + 2; continue
        elif SRC.startswith("//", i) and SRC[i - 1] != ":":
            i = SRC.find("\n", i); continue
        elif c_ == "/" and SRC[i - 1] == "(":            # littéral d'expression régulière après « ( »
            j = i + 1
            while SRC[j] != "/" or SRC[j - 1] == "\\": j += 1
            i = j + 1; continue
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return SRC[k - 6 if SRC[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


NOMS = ("cardName", "slugJeu", "etat", "paintTts", "exporterTts", "poserTts", "exporterTabletopia")
COUCHE = "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livrée a ses fonctions (une fois chacune)", all(SRC.count("function " + n + "(") == 1 for n in NOMS)
      and all(fonction(n) for n in NOMS))

HARNAIS = r"""
var DEFAULTS = {cible: "tts"}, DERNIER = null, VERROU = false;
var DOC = {name: "Éclair d'été !", edition: {cible: "tts"}};
var CARDS = [{i: 0, id: "c1", fields: {title: "Gobelin"}}, {i: 1, id: "c2", fields: {nom: "Elfe"}}, {i: 2, fields: {}}];
var BLOBS = [], APPELS = [], DL = [], TOASTS = [], REP = {}, ECHEC = null;
function el() { return {textContent: "", disabled: false, cls: {}, classList: {toggle: function (c, v) { this._o.cls[c] = !!v; }}}; }
var DOMS = {};
var HOST = {querySelector: function (s) { if (!DOMS[s]) { DOMS[s] = el(); DOMS[s].classList._o = DOMS[s]; } return DOMS[s]; }};
function FormData() { this.parts = []; } FormData.prototype.append = function (k, v, n) { this.parts.push([k, v, n || null]); };
var CF = {doc: function () { return DOC; }, cards: function () { return CARDS; }, busy: function () {}, toast: function (t, e) { TOASTS.push([t, !!e]); },
          cardBlob: async function (i, o) { BLOBS.push([i, o.face]); return "blob" + i + o.face; }, download: function (b, n) { DL.push(n); }};
var M = {api: {blob: async function (m, u, fd) { APPELS.push([m, u, fd]); if (ECHEC) throw new Error(ECHEC); await new Promise(function (s) { setTimeout(s, 5); }); return "zip"; },
               post: async function (u, b) { APPELS.push(["POST", u, b]); if (REP[u] && REP[u].err) throw new Error(REP[u].err); return REP[u]; }}};
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R));process.exit(0)})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-800:])
        return None


R = node("""
paintTts(); R.poserInactif = HOST.querySelector('[data-act="tts-poser"]').disabled;
var p1 = exporterTts(), p2 = exporterTts(); await p1; await p2;
var a = APPELS[0]; R.nAppels = APPELS.length; R.url = [a[0], a[1]];
R.spec = JSON.parse(a[2].parts[0][1]); R.parts = a[2].parts.slice(1).map(function (p) { return [p[0], p[1], p[2]]; });
R.blobs = BLOBS; R.dl = DL; R.etat = HOST.querySelector('[data-role="tts-etat"]').textContent;
R.poserActif = !HOST.querySelector('[data-act="tts-poser"]').disabled;
REP["tts/poser"] = {chemin: "C:\\\\Docs\\\\My Games\\\\Tabletop Simulator\\\\Saves\\\\Saved Objects\\\\Deepotus\\\\eclair-d-ete.json"};
APPELS = []; await poserTts(); R.pose = APPELS.slice(); R.etatPose = HOST.querySelector('[data-role="tts-etat"]').textContent;
REP["tts/poser"] = {err: "Tabletop Simulator introuvable sur ce PC"}; await poserTts(); R.etatKo = HOST.querySelector('[data-role="tts-etat"]').textContent;
R.toastKo = TOASTS[TOASTS.length - 1];
DOC.edition.cible = "tabletopia"; paintTts(); R.cacheTabletopia = HOST.querySelector('[data-role="tts"]').cls.hidden;
R.ttVisible = HOST.querySelector('[data-role="tabletopia"]').cls.hidden;
DOC.edition.cible = "tts"; paintTts(); R.visibleTts = HOST.querySelector('[data-role="tts"]').cls.hidden;
R.ttCache = HOST.querySelector('[data-role="tabletopia"]').cls.hidden;
""")
check("E0 sous node : le panneau s'exécute", R is not None)
if R:
    check("E1 avant tout export, « Poser » est inactif", R["poserInactif"] is True)
    check("E2 UN export au double clic : POST tts, recto ET verso de chaque carte rendus et envoyés dans l'ordre",
          R["nAppels"] == 1 and R["url"] == ["POST", "tts"]
          and R["blobs"] == [[0, "front"], [0, "back"], [1, "front"], [1, "back"], [2, "front"], [2, "back"]]
          and [p[0] for p in R["parts"]] == ["fronts", "backs"] * 3 and R["parts"][2] == ["fronts", "blob1front", "f2.png"], str(R["parts"]))
    check("E3 les noms des cartes partent (title, nom, puis l'id ou « carte N ») ; le ZIP porte le nom du jeu ASCII",
          R["spec"] == {"noms": ["Gobelin", "Elfe", "carte 3"]} and R["dl"] == ["eclair-d-ete_tts.zip"], str(R["spec"]) + str(R["dl"]))
    check("E4 après l'export : l'état dit ce qui est écrit et propose de poser ; « Poser » devient actif",
          "3 carte(s) exportée(s)" in R["etat"] and "Poser dans Tabletop Simulator" in R["etat"] and R["poserActif"] is True, R["etat"])
    check("E5 poser : POST tts/poser, et l'état dit OÙ (Objects > Saved Objects > Deepotus) ; un refus est DIT",
          R["pose"] == [["POST", "tts/poser", {}]] and "Saved Objects" in R["etatPose"] and "Deepotus" in R["etatPose"]
          and "introuvable" in R["etatKo"] and R["toastKo"][1] is True, R["etatPose"] + " | " + R["etatKo"])
    check("E6 chaque cible montre SES boutons et cache ceux de l'autre", R["cacheTabletopia"] is True and R["visibleTts"] is False
          and R["ttVisible"] is False and R["ttCache"] is True, str(R))

R = node("""
BLOBS = []; APPELS = []; DL = [];
var p1 = exporterTabletopia(), p2 = exporterTabletopia(); await p1; await p2;
R.n = APPELS.length; R.url = [APPELS[0][0], APPELS[0][1]]; R.spec = JSON.parse(APPELS[0][2].parts[0][1]);
R.kinds = APPELS[0][2].parts.slice(1).map(function (p) { return p[0]; }); R.blobs = BLOBS.slice(); R.dl = DL.slice();
R.etat = HOST.querySelector('[data-role="tts-etat"]').textContent; R.verrou = VERROU;
R.derniereTts = DERNIER;
ECHEC = "400 Bad Request"; TOASTS = []; await exporterTabletopia(); R.echec = TOASTS[0]; R.verrou2 = VERROU;
""")
check("TT0 sous node : Tabletopia s'exécute", R is not None)
if R:
    check("TT1 UN export au double clic : POST tabletopia, recto + verso de chaque carte, noms, ZIP au nom du jeu",
          R["n"] == 1 and R["url"] == ["POST", "tabletopia"] and R["kinds"] == ["fronts", "backs"] * 3
          and R["blobs"] == [[0, "front"], [0, "back"], [1, "front"], [1, "back"], [2, "front"], [2, "back"]]
          and R["spec"] == {"noms": ["Gobelin", "Elfe", "carte 3"]} and R["dl"] == ["eclair-d-ete_tabletopia.zip"], str(R))
    check("TT2 l'état dit quoi faire (éditeur de Tabletopia, recto et verso séparés) ; « Poser » TTS n'est pas armé par Tabletopia ; "
          "un échec est dit et le verrou rendu",
          "éditeur de Tabletopia" in R["etat"] and R["verrou"] is False and R["derniereTts"] is None
          and "Tabletopia impossible : 400" in R["echec"][0] and R["echec"][1] is True and R["verrou2"] is False, str(R))

R = node("""
CARDS = []; await exporterTts(); R.vide = [APPELS.length, TOASTS[0]];
DOC.type = {slots: [{id: "cost", text: "5"}, {id: "title", text: "Veilleur, Grand Oracle"}]};
R.nomSlot = [cardName({i: 0, id: "c1", fields: {}}), cardName({i: 1, id: "c2", fields: {title: "Elfe"}})];
DOC.type = null;
CARDS = [{i: 0, fields: {}}]; ECHEC = "400 Bad Request"; TOASTS = []; await exporterTts(); R.echec = TOASTS[0]; R.dernier = DERNIER;
R.verrouLibre = VERROU === false;
ECHEC = null; DERNIER = null; APPELS = []; await poserTts(); R.poserSans = APPELS.length;
""")
check("V0 sous node : les cas limites s'exécutent", R is not None)
if R:
    check("V1 sans carte : rien ne part, c'est dit ; un échec est dit, le verrou est rendu, rien n'est retenu comme exporté",
          R["vide"][0] == 0 and R["vide"][1][1] is True and "Aucune carte" in R["vide"][1][0]
          and "impossible : 400" in R["echec"][0] and R["dernier"] is None and R["verrouLibre"] is True, str(R))
    check("V2 « Poser » sans export ne fait rien", R["poserSans"] == 0)
    check("V3 une carte sans donnée prend le texte que montre son bloc « title » (pas son id) ; une donnée l'emporte",
          R["nomSlot"] == ["Veilleur, Grand Oracle", "Elfe"], str(R["nomSlot"]))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
