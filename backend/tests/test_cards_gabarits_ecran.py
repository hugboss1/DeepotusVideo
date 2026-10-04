# -*- coding: utf-8 -*-
"""Card Forge — tâche #83 PR B (plan-cartes T4, 04/10/2026) : le GABARIT se choisit dans la pièce 07.
Les fonctions du panneau sont extraites du `mod-print.js` LIVRÉ et EXÉCUTÉES sous node (CF, M, DOM simulés).
DÉCISIONS DE L'UTILISATEUR (04/10) : choisir un imprimeur règle le format du jeu et l'impression qu'il impose ;
revenir à « maison » RESTAURE ce qu'il y avait avant ; un format non vérifié est grisé ; DTC sans profil de presse
dit que PDF/X-1a n'est pas revendiqué.
Témoin positif : la pièce 07 de la base (87ac0d2f) n'a pas de gabarit.
Run (depuis backend/) : & $PY tests/test_cards_gabarits_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
JSF = RACINE / "frontend" / "cardforge" / "js" / "mod-print.js"
SRC = JSF.read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cfgabe_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "87ac0d2f"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-print.js"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base a la pièce 07 mais pas de gabarit", r0.returncode == 0 and b"exportSheet" in r0.stdout
      and b"choisirGabarit" not in r0.stdout and b'data-act="pack"' not in r0.stdout)
check("T2 le panneau porte le bloc Gabarit EN TÊTE (avant le contrôle avant vol), le bouton paquet titré, et l'état "
      "déclare profile / profile_avant (seules clés patchables)",
      0 < SRC.find('data-role="gabs"') < SRC.find("Contrôle avant vol — cartes ET fichier")
      and SRC.count('data-act="pack" title="') == 1 and 'profile: "maison", profile_avant: "",' in SRC
      and 'else if (a === "profile") choisirGabarit(String(act.dataset.v));' in SRC and 'else if (a === "pack") exportPack();' in SRC
      and "loadGabarits();" in SRC.split('CF.on("core:geom"')[1].split("\n")[0])


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
        elif SRC.startswith("/*", i):          # un commentaire peut porter une apostrophe : on le saute
            i = SRC.find("*/", i) + 2; continue
        elif SRC.startswith("//", i) and SRC[i - 1] != ":":
            i = SRC.find("\n", i); continue
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return SRC[k - 6 if SRC[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


def bloc(debut, fin):
    k = SRC.find(debut)
    return SRC[k:SRC.find(fin, k) + len(fin)] if k >= 0 else ""


NOMS = ("gabCourant", "gabRow", "ecartPdfx", "paintGabarits", "loadGabarits", "choisirGabarit", "exportPack")
COUCHE = "\n".join([bloc("let GAB = [], GABFMT", ";"), bloc("const GAB_NOTE = {", "};"), bloc("const GAB_CLES = [", "];")]
                   + [fonction(n) for n in NOMS])
check("T3 la couche livrée a ses fonctions (une fois chacune)", all(SRC.count("function " + n + "(") == 1 for n in NOMS)
      and "GAB_NOTE" in COUCHE and "GAB_CLES" in COUCHE)

CATALOGUE = {
    "poker_us": [
        {"id": "maison", "label": "Imposition maison", "delivery": "pdf", "pdfx": "PDF/X-3:2003", "color": "rgb", "sheet": "a4",
         "marks": "crop", "fmts": ["poker_us", "mini"], "verifie": "", "note": "",
         "geom": {"canvas_px": [825, 1125], "bleed_off_px": [37.5, 37.5], "safe_off_px": [75, 75], "bleed_mm": 3.175, "safe_mm": 3.175, "dpi": 300}},
        {"id": "mpc", "label": "MakePlayingCards — fond perdu 36 px", "delivery": "png_zip", "pdfx": None, "color": "rgb", "sheet": "card",
         "marks": "none", "fmts": ["poker_us"], "verifie": "04/10/2026 — makeplayingcards.com", "note": "",
         "geom": {"canvas_px": [822, 1122], "bleed_off_px": [36, 36], "safe_off_px": [72, 72], "bleed_mm": 3.048, "safe_mm": 3.048, "dpi": 300}},
        {"id": "tgc", "label": "The Game Crafter", "delivery": "png_zip", "pdfx": None, "color": "rgb", "sheet": "card",
         "marks": "none", "fmts": ["poker_us"], "verifie": "04/10/2026", "note": "",
         "geom": {"canvas_px": [825, 1125], "bleed_off_px": [37.5, 37.5], "safe_off_px": [75, 75], "bleed_mm": 3.175, "safe_mm": 3.175, "dpi": 300}},
        {"id": "dtc", "label": "DriveThruCards — PDF 2,75 x 3,75 in", "delivery": "pdf", "pdfx": "PDF/X-1a:2001", "color": "cmyk_device",
         "sheet": "card", "marks": "none", "fmts": ["poker_us"], "verifie": "04/10/2026", "note": "",
         "geom": {"canvas_px": [825, 1125], "bleed_off_px": [37.5, 37.5], "safe_off_px": [75, 75], "bleed_mm": 3.175, "safe_mm": 3.175, "dpi": 300}},
    ],
}
CATALOGUE["mini"] = [dict(r, geom=(r["geom"] if r["id"] == "maison" else None)) for r in CATALOGUE["poker_us"]]

HARNAIS = r"""
var CAT = %s;
var DOC = {format: {fmt: "poker_us", dpi: 300, bleed_mm: 3.0, safe_mm: 3.0, corner_mm: 3}, print: {}};
var DEF = {sheet: "a4", marks: "crop", slug: true, color: "rgb", layers: true, intent: "srgb", profile: "maison", profile_avant: ""};
function st() { var o = {}; Object.keys(DEF).forEach(function (k) { o[k] = (k in DOC.print) ? DOC.print[k] : DEF[k]; }); return o; }
var SETS = [], FMTS = [], TOASTS = [], APPELS = [], DL = [], ICC = null, FORCE = false, GATE = true, REFRESH = 0;
function set(o) { SETS.push(JSON.parse(JSON.stringify(o))); Object.keys(o).forEach(function (k) { DOC.print[k] = o[k]; }); }
function el(sel) { return {sel: sel, innerHTML: "", textContent: "", cls: {}, classList: {toggle: function (c, v) { this._o.cls[c] = !!v; }}}; }
var DOMS = {};
function q(sel) { if (!DOMS[sel]) { DOMS[sel] = el(sel); DOMS[sel].classList._o = DOMS[sel]; } return DOMS[sel]; }
function qa(sel) { return sel.split(", ").map(q); }
var esc = function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); };
var fx = function (v, n) { return Number(v).toFixed(n); };
function refresh() { REFRESH++; } function schedulePreflight() {}
var M = {api: {get: async function (u) { APPELS.push(u); var f = decodeURIComponent(u.split("fmt=")[1]); return {fmt: f, gabarits: CAT[f]}; },
               blob: async function (m, u, fd) { APPELS.push(m + " " + u); return {size: 1234}; }},
         setFormat: function (o) { FMTS.push(JSON.parse(JSON.stringify(o))); Object.keys(o).forEach(function (k) { DOC.format[k] = o[k]; }); }};
var CF = {doc: function () { return DOC; }, toast: function (t, e) { TOASTS.push([t, !!e]); }, cards: function () { return [1, 2]; },
          busy: function () {}, download: function (b, n) { DL.push(n); }};
async function gate() { return GATE; }
async function renderAll(b) { return {fronts: ["f1", "f2"], backs: b ? ["b1", "b2"] : [], ms: 1}; }
var FDS = []; function formData(s, f, b) { var o = {spec: s, f: f.length, b: b.length}; FDS.push(o); return o; }
function exportSpec(e) { return Object.assign({}, st(), e || {}); }
function deckSlug() { return "mon-jeu"; } function logLine() {}
function boutons() { return (q('[data-role="gabs"]').innerHTML.match(/<button[^>]*>/g) || []); }
""" % json.dumps(CATALOGUE)


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
await loadGabarits();
R.appel = APPELS[0]; R.html = q('[data-role="gabs"]').innerHTML; R.b = boutons();
R.packCache = q('[data-act="pack"]').cls.hidden; R.pdfCache = q('[data-act="pdf"]').cls.hidden;
choisirGabarit("mpc");
R.sets1 = SETS.slice(); R.fmts1 = FMTS.slice(); R.doc1 = JSON.parse(JSON.stringify(DOC));
R.packCache2 = q('[data-act="pack"]').cls.hidden; R.pdfCache2 = q('[data-act="pdf"]').cls.hidden; R.pngCache2 = q('[data-act="png"]').cls.hidden;
R.on = (q('[data-role="gabs"]').innerHTML.match(/class="cf-print-gab on"[^>]*data-v="(\\w+)"/) || [])[1];
SETS = []; FMTS = []; choisirGabarit("tgc"); R.avantGarde = JSON.parse(DOC.print.profile_avant || "null"); R.fmts2 = FMTS.slice();
SETS = []; FMTS = []; choisirGabarit("maison"); R.sets3 = SETS.slice(); R.fmts3 = FMTS.slice(); R.doc3 = JSON.parse(JSON.stringify(DOC));
R.toasts = TOASTS.map(function (t) { return t[0]; });
SETS = []; choisirGabarit("maison"); R.rienDeuxFois = SETS.length;
""")
check("E0 sous node : le panneau s'exécute", R is not None)
if R:
    check("E1 le catalogue vient du backend pour le format du jeu ; une carte par gabarit, chacune TITRÉE, avec ses pixels",
          R["appel"] == "gabarits?fmt=poker_us" and len(R["b"]) == 4 and all(' title="' in b for b in R["b"])
          and "822 x 1122 px · fond perdu 36,0 px · zone sûre à 72,0 px du bord" in R["html"]
          and "le portail contrôle les pixels" in R["html"]
          and 'title="Régler le jeu pour MakePlayingCards — fond perdu 36 px — pixels vérifiés le 04/10/2026' in R["html"] and "PDF/X-1a:2001" in R["html"], R["html"][:300])
    check("E2 « maison » au départ : paquet caché, PDF visible", R["packCache"] is True and R["pdfCache"] is False)
    check("E3 MPC : le jeu passe à 3,048 mm / 300 DPI, l'impression à « 1 carte, sans traits ni cartouche » ; l'AVANT est retenu",
          R["fmts1"] == [{"bleed_mm": 3.048, "safe_mm": 3.048, "dpi": 300}]
          and R["sets1"][0]["profile"] == "mpc" and R["sets1"][0]["sheet"] == "card" and R["sets1"][0]["marks"] == "none"
          and R["sets1"][0]["slug"] is False
          and json.loads(R["sets1"][0]["profile_avant"]) == {"format": {"bleed_mm": 3.0, "safe_mm": 3.0, "dpi": 300},
                                                            "print": {"sheet": "a4", "marks": "crop", "slug": True, "color": "rgb", "layers": True, "intent": "srgb"}},
          str(R["sets1"]) + str(R["fmts1"]))
    check("E4 MPC : le bouton paquet paraît, PDF / planche PNG disparaissent (MPC ne prend pas de PDF) ; MPC est marqué choisi",
          R["packCache2"] is False and R["pdfCache2"] is True and R["pngCache2"] is True and R["on"] == "mpc", str(R))
    check("E5 MPC -> TGC : l'avant N'EST PAS écrasé (il reste celui de « maison ») ; le fond perdu passe à 3,175",
          R["avantGarde"]["format"]["bleed_mm"] == 3.0 and R["fmts2"] == [{"bleed_mm": 3.175, "safe_mm": 3.175, "dpi": 300}], str(R["avantGarde"]))
    check("E6 retour à « maison » : format ET réglages d'avant RESTAURÉS, l'avant effacé, et c'est dit",
          R["fmts3"] == [{"bleed_mm": 3.0, "safe_mm": 3.0, "dpi": 300}] and R["doc3"]["print"]["sheet"] == "a4"
          and R["doc3"]["print"]["marks"] == "crop" and R["doc3"]["print"]["slug"] is True and R["doc3"]["print"]["profile"] == "maison"
          and R["doc3"]["print"]["profile_avant"] == "" and any("rétablis" in t for t in R["toasts"]), str(R["doc3"]))
    check("E7 re-choisir le gabarit courant ne fait rien", R["rienDeuxFois"] == 0)

R = node("""
await loadGabarits(); choisirGabarit("dtc");
R.set = SETS[0]; R.ecart = q('[data-role="gab-ecart"]').textContent; R.ecartCache = q('[data-role="gab-ecart"]').cls.hidden;
R.packCache = q('[data-act="pack"]').cls.hidden; R.pdfCache = q('[data-act="pdf"]').cls.hidden;
DOC.print = {}; DOC.format.bleed_mm = 3.0; SETS = []; ICC = {space: "CMYK", cls: "prtr", desc: "Coated GRACoL 2006"};
choisirGabarit("dtc"); R.setIcc = SETS[0]; R.ecartIcc = q('[data-role="gab-ecart"]').textContent;
DOC.print = {}; SETS = []; ICC = {space: "RGB", cls: "mntr"}; choisirGabarit("dtc"); R.setEcran = SETS[0];
""")
check("D0 sous node : DriveThruCards s'exécute", R is not None)
if R:
    check("D1 DTC sans profil de presse : CMJN d'appareil, sans calques ; l'ÉCART est écrit à l'écran",
          R["set"]["color"] == "cmyk_device" and R["set"]["layers"] is False and "intent" not in R["set"]
          and "conformité PDF/X-1a non revendiquée" in R["ecart"] and "sans retrait des sous-couleurs" in R["ecart"]
          and "profil ICC de l’imprimeur" in R["ecart"] and R["ecartCache"] is False, str(R["set"]) + R["ecart"])
    check("D2 DTC se livre en PDF : paquet caché, PDF visible", R["packCache"] is True and R["pdfCache"] is False)
    check("D3 avec un profil de PRESSE (CMYK, prtr) : séparation par le profil + intention ICC, et l'écran dit la revendication",
          R["setIcc"]["color"] == "cmyk_icc" and R["setIcc"]["intent"] == "icc" and "revendiquée et relue" in R["ecartIcc"]
          and "Coated GRACoL 2006" in R["ecartIcc"], str(R["setIcc"]) + R["ecartIcc"])
    check("D4 un profil d'ÉCRAN (RGB, mntr) ne vaut pas profil de presse", R["setEcran"]["color"] == "cmyk_device")

R = node("""
DOC.format.fmt = "mini"; await loadGabarits();
R.b = boutons(); R.html = q('[data-role="gabs"]').innerHTML; SETS = []; choisirGabarit("mpc"); R.refuse = SETS.length;
DOC.format.fmt = "poker_us"; await loadGabarits(); choisirGabarit("mpc");
/* le CORE ramene le fond perdu natif quand le format change : le gabarit le remet */
DOC.format.bleed_mm = 3.175; FMTS = []; await loadGabarits(); R.reapplique = FMTS.slice();
FMTS = []; await loadGabarits(); R.stable = FMTS.length;
DOC.format.fmt = "mini"; await loadGabarits(); R.ecartMini = q('[data-role="gab-ecart"]').textContent;
""")
check("F0 sous node : les formats s'exécutent", R is not None)
if R:
    check("F1 un format non vérifié : les imprimeurs sont GRISÉS (disabled, title qui dit pourquoi), le clic ne fait rien",
          sum(1 for b in R["b"] if " disabled" in b) == 3 and "ne sert pas ce format (mini)" in R["html"]
          and "vérifié le 04/10/2026" in R["html"] and R["refuse"] == 0, R["html"][:400])
    check("F2 sous MPC, un fond perdu ramené au natif est REMIS à 3,048 ; une fois aligné, plus rien (pas de boucle)",
          R["reapplique"] == [{"bleed_mm": 3.048, "safe_mm": 3.048, "dpi": 300}] and R["stable"] == 0, str(R["reapplique"]))
    check("F3 passer à un format que le gabarit choisi ne sert pas : c'est DIT", "ne sert pas le format mini" in R["ecartMini"], R["ecartMini"])

R = node("""
await loadGabarits(); choisirGabarit("mpc"); APPELS = []; await exportPack();
R.appels = APPELS; R.dl = DL; R.fd = FDS[FDS.length - 1]; R.toast = TOASTS[TOASTS.length - 1][0];
DL = []; APPELS = []; GATE = false; await exportPack(); R.porte = [APPELS.length, DL.length];
GATE = true; choisirGabarit("maison"); APPELS = []; await exportPack(); R.maison = APPELS.length;
""")
check("P0 sous node : le paquet s'exécute", R is not None)
if R:
    check("P1 le paquet : recto ET verso rendus, POST pack, fichier nommé par le jeu et le gabarit, chiffres dits",
          R["appels"] == ["POST pack"] and R["fd"]["f"] == 2 and R["fd"]["b"] == 2 and R["fd"]["spec"]["profile"] == "mpc" and R["dl"] == ["mon-jeu_paquet_mpc.zip"] and "822 x 1122 px" in R["toast"], str(R))
    check("P2 le contrôle avant vol refuse : rien ne part ; en « maison », pas de paquet", R["porte"] == [0, 0] and R["maison"] == 0)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
