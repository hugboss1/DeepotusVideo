# -*- coding: utf-8 -*-
"""Card Forge — tâche #87 PR A à l'écran (plan-cartes T14-T15, 04/10/2026) : l'ART DU DECK EN LOT dans la pièce 04.
DÉCISIONS DE L'UTILISATEUR (04/10) : devis AVANT, dialogue maison qui annonce le coût, le plafond « cartes » et le MUR
du lot ; la colonne remplie est celle mappée sur l'illustration, en UNE modification annulable ; variantes au choix.
Écart au plan corrigé : le panneau vit dans Données (qui possède la table et le mappage), pas dans Face — aucun
événement inter-pièces, aucun patch de `data` depuis une autre pièce.
Les fonctions LIVRÉES sont extraites de mod-data.js et EXÉCUTÉES sous node (aucun appel réel).
Témoin positif : la base (5234b286) n'a pas d'art en lot.
Run (depuis backend/) : & $PY tests/test_cards_lot_art_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
DATA = (RACINE / "frontend/cardforge/js/mod-data.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cflote_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "5234b286"
b = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-data.js"], capture_output=True, cwd=str(RACINE)).stdout
check("E1 témoin : la base n'a pas d'art en lot", b and b"lotGenerer" not in b)
check("E2 chaque bouton du lot est TITRÉ ; clics, réglages et ouverture câblés ; la clé « lot » est au schéma",
      DATA.count('data-lot-devis="1" title="') == 1 and DATA.count('data-lot-go="1" title="') == 1
      and DATA.count("data-lot-var=\"' + i + \":\" + k\n          + '\" title=\"") == 1
      and 'if (ev.target.closest("[data-lot-go]")) { lotGenerer(); return; }' in DATA
      and 'if (s) lotRegler(String(s.dataset.lotK), s.value);' in DATA
      and 'on(lot, "toggle", () => { if (lot.open) lotModeles(); });' in DATA
      and "      lot: {},          /* tache #87" in DATA and DATA.count("LOTDEV = null; paintLot();") == 2)


def fonction(src, nom):
    k = src.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = src.find("{", src.find(")", k)), 0, None, False
    while i < len(src):
        c_ = src[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif src.startswith("/*", i):
            i = src.find("*/", i) + 2; continue
        elif src.startswith("//", i) and src[i - 1] != ":":
            i = src.find("\n", i); continue
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return src[k - 6 if src[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


NOMS = ("artCol", "lotGabarit", "lotCorps", "usd", "lotHTML", "paintLot", "lotModeles", "lotRegler", "lotDevis",
        "lotGenerer", "lotVariante")
COUCHE = "\n".join(fonction(DATA, n) for n in NOMS)
k0 = DATA.find("  const LOTDEF = ")
COUCHE = DATA[k0:DATA.find("\n", k0)] + "\n" + COUCHE
check("E3 la couche livrée est extraite", COUCHE.count("function ") >= len(NOMS), str([n for n in NOMS if not fonction(DATA, n)]))

HARNAIS = r"""
var LOT = Object.assign({}, LOTDEF), LOTMODS = null, LOTDEV = null, LOTRES = [], LOTV = false;
var T = {columns: ["nom", "prompt", "illus", "qty"], rows: [["Colosse", "golem", "", "3"], ["Oracle", "pieuvre", "deja.png", "2"],
         ["Echo", "echo", "", "1"]], off: [], map: {nom: "title", illus: "art"}, qty_col: "qty"};
var APPELS = [], DIAL = [], DREP = true, TOASTS = [], REP = {}, ERR = {}, UNDO = 0, COMMIT = 0, RENDER = 0, SCHED = 0, PATCH = [], BUSY = [];
var esc = function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); };
var BOX = {className: "", innerHTML: ""};
var REFS = {lot: BOX};
var CF = {images: {url: function (f) { return "/api/images/file/" + encodeURIComponent(f); }}};
var window = {__dzDialogue: {confirmer: async function (m, o) { DIAL.push([m, o]); return DREP; }}};
var M = {busy: function (on) { BUSY.push(!!on); }, toast: function (t, e) { TOASTS.push([t, !!e]); },
         patch: function (o) { PATCH.push(JSON.parse(JSON.stringify(o))); },
         api: {post: async function (u, b) { APPELS.push([u, JSON.parse(JSON.stringify(b))]); await new Promise(function (s) { setTimeout(s, 5); });
                                            if (ERR[u]) throw new Error(ERR[u]); return JSON.parse(JSON.stringify(REP[u])); },
               get: async function (u) { APPELS.push([u, null]); if (ERR[u]) throw new Error(ERR[u]); return JSON.parse(JSON.stringify(REP[u])); }}};
function pushUndo() { UNDO++; } function commit() { COMMIT++; } function render() { RENDER++; } function schedule() { SCHED++; }
REP["lot/modeles"] = {models: [{id: "nano-banana", label: "Nano Banana", provider: "fal", usd_par_image: 0.039, cle: true},
                               {id: "gpt-image-2", label: "GPT Image 2", provider: "openai", usd_par_image: 0.05, cle: false}],
                      tailles: ["portrait_4_3", "square_hd"], mur_usd: 10};
var DEV = {lignes_a_generer: 3, incomplets: 1, deja_illustrees: 1, cartes_couvertes: 4, lignes_de_ce_lot: 2, restants: 0,
           n_par_ligne: 1, images: 2, model: "nano-banana", usd_par_image: 0.039, total_usd: 0.078, mur_usd: 10, sous_le_mur: true,
           sans_prompt: [5]};
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
var t0 = T; T = {columns: ["nom", "illus"], rows: [["a", ""]], off: [], map: {nom: "title"}}; R.sansart = lotHTML(); T = t0;
await lotModeles(); R.barre = BOX.innerHTML; R.cls = BOX.className;
LOTDEV = DEV; R.devis = lotHTML();
LOTRES = [{ligne: 1, entite: "Colosse", fichiers: ["a<1>.png", "b.png"], choisi: "a<1>.png"}]; R.res = lotHTML();
var t1 = T; T = {columns: ["nom", "texte", "illus"], rows: [], off: [], map: {nom: "title", illus: "art"}}; R.gabtitre = lotGabarit(); T = t1;
LOT.gabarit = "{nom}, {prompt}"; R.gabsaisi = lotGabarit(); LOT.gabarit = "";
""")
check("H0 sous node : le panneau s'exécute", R is not None)
if R:
    check("H1 sans colonne mappée sur l'illustration : le panneau le dit, AUCUN bouton de tir",
          "Mappez d’abord une colonne" in R["sansart"] and "data-lot-go" not in R["sansart"], R["sansart"])
    bar = R["barre"]
    check("H2 la barre : modèles avec leur tarif, un modèle SANS CLÉ grisé, variantes, cadre, gabarit par défaut {prompt}, mur 10 $",
          '<option value="nano-banana" selected>Nano Banana · 0.039 $/image</option>' in bar
          and '<option value="gpt-image-2" disabled>GPT Image 2 · 0.050 $/image · sans clé</option>' in bar
          and 'value="4">4 variante(s)' in bar and '<option value="square_hd">square_hd</option>' in bar
          and 'data-lot-k="gabarit" value="{prompt}"' in bar and 'data-lot-k="mur_usd" type="number"' in bar and 'value="10"' in bar
          and "colonne « illus »" in bar and "jamais un nom d’artiste" in bar and R["cls"] == "cf-data-lot", bar)
    dv = R["devis"]
    check("H3 le devis : lignes, images, cartes couvertes, dollars, mur, lignes sans texte, Bibliothèque",
          "<b>3 ligne(s) à générer</b>" in dv and "2 image(s) pour ce lot" in dv and "4 cartes couvertes" in dv
          and "<b>0.078 $</b> (nano-banana, mur 10.00 $)" in dv and "1 ligne(s) sans texte (5) ne seront pas tirées" in dv
          and "<b>Bibliothèque</b>" in dv, dv)
    check("H4 les variantes : une vignette par fichier, ÉCHAPPÉE, la choisie marquée, chaque bouton titré",
          R["res"].count('class="cf-data-lotvar') == 2 and 'class="cf-data-lotvar on" data-lot-var="0:0"' in R["res"]
          and "a%3C1%3E.png" in R["res"] and "<1>" not in R["res"] and R["res"].count('title="Poser cette variante sur la ligne 1') == 2, R["res"])
    check("H5 gabarit par défaut : la colonne « prompt », sinon la colonne du titre ; une saisie l'emporte",
          R["gabtitre"] == "{nom}" and R["gabsaisi"] == "{nom}, {prompt}", str(R))

R = node("""
REP["lot/modeles"] && (LOTMODS = REP["lot/modeles"]);
REP["lot/devis"] = DEV;
REP["lot/generer"] = {generees: 2, echecs: 1, resultats: [{ligne: 1, fichiers: ["g1.png", "g1b.png"], entite: ""}, {ligne: 2, fichiers: ["g2.png"], entite: ""}],
                      erreurs: [{ligne: 3, message: "le fournisseur a répondu 500"}], arret: "Plafond mensuel atteint"};
var p1 = lotGenerer(), p2 = lotGenerer(); await p1; await p2;
R.appels = APPELS.map(function (a) { return a[0]; }); R.corps = APPELS[1] && APPELS[1][1]; R.dial = DIAL.slice(); R.rows = T.rows.map(function (r) { return r.slice(); });
R.c = [UNDO, COMMIT, RENDER, SCHED]; R.toast = TOASTS[TOASTS.length - 1]; R.res = LOTRES.map(function (x) { return x.choisi || null; }); R.verrou = LOTV; R.busy = BUSY.slice();
lotVariante(0, 1); R.var = [T.rows[0][2], UNDO, LOTRES[0].choisi];
APPELS = []; DIAL = []; DREP = false; await lotGenerer(); R.annule = [APPELS.map(function (a) { return a[0]; }), DIAL.length];
""")
check("G0 sous node : le tir s'exécute", R is not None)
if R:
    check("G1 UN devis au double clic, puis le dialogue ANNONCE images, modèle, coût, PAYANT, plafond, mur, lignes sans texte, colonne, Bibliothèque",
          R["appels"] == ["lot/devis", "lot/generer"] and len(R["dial"]) == 1
          and "2 image(s) avec nano-banana pour 2 ligne(s) : ≈ 0.078 $ — PAYANT, plafond « cartes » et mur du lot (10.00 $) appliqués." in R["dial"][0][0]
          and "1 ligne(s) sans texte ne seront pas tirées" in R["dial"][0][0] and "La colonne « illus » sera remplie (Ctrl+Z annule)" in R["dial"][0][0]
          and "Bibliothèque" in R["dial"][0][0] and R["dial"][0][1]["ok"] == "Générer (≈ 0.078 $)", str(R["dial"]))
    check("G2 la demande part CONFIRMÉE avec la table, le mappage, les écartées, la quantité et les réglages",
          R["corps"]["confirmer"] is True and R["corps"]["map"] == {"nom": "title", "illus": "art"} and R["corps"]["qty_col"] == "qty"
          and R["corps"]["gabarit"] == "{prompt}" and R["corps"]["model"] == "nano-banana" and R["corps"]["mur_usd"] == 10
          and R["corps"]["rows"][1][2] == "deja.png", str(R["corps"]))
    check("G3 la colonne d'art est remplie en UNE modification annulable, sans écraser une image déjà posée",
          R["rows"][0][2] == "g1.png" and R["rows"][1][2] == "deja.png" and R["rows"][2][2] == "" and R["c"] == [1, 1, 1, 1]
          and R["res"] == ["g1.png", None], str(R))
    check("G4 le bilan dit les échecs (ligne et message) et l'arrêt au plafond ; le verrou est rendu",
          "2 ligne(s) illustrée(s)" in R["toast"][0] and "ligne 3 — le fournisseur a répondu 500" in R["toast"][0]
          and "lot arrêté : Plafond mensuel atteint" in R["toast"][0] and R["toast"][1] is True and R["verrou"] is False
          and R["busy"][-1] is False, str(R["toast"]))
    check("G5 choisir une variante : la cellule change, annulable", R["var"] == ["g1b.png", 2, "g1b.png"], str(R["var"]))
    check("G6 annuler le dialogue : le devis seul est parti", R["annule"] == [["lot/devis"], 1], str(R["annule"]))

R = node("""
LOTMODS = REP["lot/modeles"];
REP["lot/devis"] = Object.assign({}, DEV, {model: "gpt-image-2"}); await lotGenerer(); R.cle = [APPELS.length, DIAL.length, TOASTS[0], LOTV];
APPELS = []; TOASTS = []; REP["lot/devis"] = Object.assign({}, DEV, {total_usd: 12.5, sous_le_mur: false}); await lotGenerer();
R.mur = [APPELS.length, DIAL.length, TOASTS[0]];
APPELS = []; TOASTS = []; REP["lot/devis"] = Object.assign({}, DEV, {lignes_de_ce_lot: 0, images: 0, incomplets: 2}); await lotGenerer();
R.rien = [APPELS.length, DIAL.length, TOASTS[0]];
APPELS = []; TOASTS = []; REP["lot/devis"] = DEV; ERR["lot/generer"] = "402 Plafond mensuel atteint"; await lotGenerer();
R.err = [TOASTS[0], LOTV, T.rows[0][2], UNDO];
APPELS = []; TOASTS = []; ERR["lot/devis"] = "400 Modèle non servi"; R.dv = await lotDevis(); R.dvt = TOASTS[0];
""")
check("O0 sous node : les cas limites s'exécutent", R is not None)
if R:
    check("O1 modèle sans clé : dit AVANT tout dialogue (Réglages), seul le devis est parti, verrou rendu",
          R["cle"][0] == 1 and R["cle"][1] == 0 and "Réglages" in R["cle"][2][0] and R["cle"][2][1] is True and R["cle"][3] is False, str(R["cle"]))
    check("O2 au-dessus du mur : dit avant tout dialogue", R["mur"][0] == 1 and R["mur"][1] == 0 and "au-dessus du mur de 10.00 $" in R["mur"][2][0], str(R["mur"]))
    check("O3 aucune ligne prête : dit (lignes sans texte), aucun dialogue",
          R["rien"][0] == 1 and R["rien"][1] == 0 and "2 ligne(s) sans texte" in R["rien"][2][0], str(R["rien"]))
    check("O4 un refus du serveur est dit, la table intacte, le verrou rendu",
          "402" in R["err"][0][0] and R["err"][0][1] is True and R["err"][1] is False and R["err"][2] == "" and R["err"][3] == 0, str(R["err"]))
    check("O5 un devis refusé est dit et rend null", R["dv"] is None and "Modèle non servi" in R["dvt"][0], str(R))

R = node("""
lotRegler("n", "9"); R.n = LOT.n; lotRegler("n", "x"); R.n2 = LOT.n; lotRegler("mur_usd", "25"); R.mur = LOT.mur_usd;
lotRegler("mur_usd", ""); R.mur2 = LOT.mur_usd; LOTDEV = DEV; lotRegler("style", "vitrail"); R.dev = LOTDEV; R.patch = PATCH[PATCH.length - 1];
R.corps = lotCorps(); T.map = {nom: "title"}; R.sans = artCol();
""")
check("R0 sous node : les réglages s'exécutent", R is not None)
if R:
    check("R1 réglages bornés (variantes 1-4, mur numérique), enregistrés dans « lot », le devis d'avant ne vaut plus",
          R["n"] == 4 and R["n2"] == 1 and R["mur"] == 25 and R["mur2"] == 10 and R["dev"] is None
          and R["patch"]["lot"]["style"] == "vitrail" and R["patch"]["lot"]["mur_usd"] == 10 and list(R["patch"]) == ["lot"], str(R))
    check("R2 la colonne d'art est celle du MAPPAGE ; sans elle, aucune", R["corps"]["style"] == "vitrail" and R["sans"] == "", str(R))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
