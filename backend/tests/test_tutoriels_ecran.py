# -*- coding: utf-8 -*-
"""t319 (28/10/2026) (D5, tâche 6) — les tutoriels et parcours côté écran, joués sous node (aucun navigateur).
Plan docs/superpowers/plans/2026-10-28-t319-tutoriels.md, spec boîte à outils §8.7.
[L] dz-tutoriels-logique.js : mots, bornes, étape à l'instant t, langue, ACTION SÛRE (seconde garde du rejeu : type
    « point » seulement, champs inconnus retirés, cadre / écran / section au gabarit), fenêtre de lecture, horloge ;
[P] livraison : copies shared == dist ; index.html charge le module une fois, après dz-montage-capture.js ;
    dz-capture*.js, dz-montage-capture*.js, dz-skins*.js et dz-agent*.js NON modifiés depuis la base t317 ; le
    pointeur est IMPORTÉ de dz-agent-pointeur.js ; aucun clic simulé (.click(), MouseEvent, PointerEvent), aucun
    eval, ni alert/confirm/prompt, ni emoji ; innerHTML réservé au glyphe de l'app ; le téléchargement est un lien que
    l'utilisateur clique ; clés tuto.* FR/EN à 3 segments, mêmes variables, toutes employées, assemblées.
Le comportement à l'écran est prouvé dans Chrome sur deux backends de preuve (docs/superpowers/specs/captures/t319/).
Run (depuis backend/) : & $PY tests/test_tutoriels_ecran.py"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
NODE = shutil.which("node")
BASE_T317 = "ae7e13a8"
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:700]}")


SH = REPO / "frontend" / "shared"
DI = REPO / "frontend" / "dist" / "shared"
FICHIERS = ["dz-tutoriels.js", "dz-tutoriels-logique.js"]
DICO = json.loads((SH / "i18n" / "tutoriels.json").read_text("utf-8"))
TXT = (SH / "dz-tutoriels.js").read_text("utf-8")
LOG = (SH / "dz-tutoriels-logique.js").read_text("utf-8")


def node(script: str):
    d = pathlib.Path(tempfile.mkdtemp(prefix="dztutojs_"))
    f = d / "banc.mjs"
    f.write_text(script, "utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = r.stdout.strip().splitlines()
    if r.returncode or not out:
        raise RuntimeError((r.stderr or r.stdout)[-1500:])
    return json.loads(out[-1])


print("[L] logique")
URL = (SH / "dz-tutoriels-logique.js").as_uri()
R = node(f"""
import * as L from {json.dumps(URL)};
const r = {{}};
r.mots = [L.compterMots("un  deux\\ntrois "), L.compterMots(""), L.compterMots(null)];
r.borner = L.borner("a\\n\\n b" + "x".repeat(300), 10);
const E = [{{t0: 1000}}, {{t0: 3000}}, {{t0: 6000}}];
r.etape = [L.etapeA(E, 0), L.etapeA(E, 1000), L.etapeA(E, 4500), L.etapeA(E, 99999), L.etapeA([], 5)];
r.langue = [L.dansLangue({{fr: "a", en: "b"}}, "en"), L.dansLangue({{fr: "a", en: ""}}, "en"), L.dansLangue(null, "fr")];
const bon = {{type: "point", cible: "quick.galerie.bouton", selecteur: "button", texte: {{fr: "Galerie", en: "Gallery"}},
  ecran: "quick", cadre: null, reglages: null, partout: false, libelle: null, fr: "Galerie", en: "Gallery",
  onclick: "x", script: "<img>", html: "<b>"}};
r.sure = L.actionSure(bon);
r.refus = [L.actionSure({{...bon, type: "point_xy"}}), L.actionSure({{...bon, type: "aller"}}), L.actionSure(null),
  L.actionSure({{...bon, selecteur: ""}}), L.actionSure({{...bon, selecteur: "a".repeat(201)}}), L.actionSure("point")];
r.gabarits = L.actionSure({{...bon, ecran: "../x", cadre: "https://ailleurs/", reglages: "a b", partout: "oui", libelle: "x".repeat(81)}});
r.cadre = L.actionSure({{...bon, cadre: "/vectorlab/"}}).cadre;
r.fen = [L.fenetreEtape({{t0: 1000, t1: 3000}}), L.fenetreEtape({{t0: 5000, t1: 4000}}), L.fenetreEtape(null)];
r.horloge = [L.horloge(65000), L.horloge(0), L.horloge(-5)];
console.log(JSON.stringify(r));
""")
check("L1 mots", R["mots"] == [3, 0, 0], R["mots"])
check("L2 borné, sans retour à la ligne", R["borner"] == "a b" + "x" * 7, R["borner"])
check("L3 étape à l'instant t", R["etape"] == [0, 0, 1, 2, 0], R["etape"])
check("L4 langue avec repli", R["langue"] == ["b", "a", ""], R["langue"])
S = R["sure"]
check("L5 action sûre : champs inconnus retirés", S and set(S) == {"type", "cible", "selecteur", "texte", "libelle", "ecran",
      "cadre", "reglages", "partout", "fr", "en"} and S["selecteur"] == "button" and S["texte"]["en"] == "Gallery", S)
check("L6 seul le type « point » passe (ni point_xy, ni aller, ni vide)", R["refus"] == [None] * 6, R["refus"])
G = R["gabarits"]
check("L7 écran, cadre, section, partout, libellé hors gabarit neutralisés", G["ecran"] is None and G["cadre"] is None
      and G["reglages"] is None and G["partout"] is False and G["libelle"] is None, G)
check("L8 cadre d'un lab accepté", R["cadre"] == "/vectorlab/")
check("L9 fenêtre de lecture jamais vide", R["fen"][0] == {"debut": 1, "fin": 3.3} and R["fen"][1]["fin"] >= R["fen"][1]["debut"] + 0.5
      and R["fen"][2] == {"debut": 0, "fin": 0.5}, R["fen"])
check("L10 horloge", R["horloge"] == ["1:05", "0:00", "0:00"], R["horloge"])

print("[P] livraison")
check("P1 copies shared == dist", all((SH / f).read_bytes() == (DI / f).read_bytes() for f in FICHIERS))
IDX = (REPO / "frontend" / "dist" / "index.html").read_text("utf-8")
check("P2 index.html : chargé une fois, après dz-montage-capture.js", IDX.count('src="/shared/dz-tutoriels.js"') == 1
      and IDX.index("/shared/dz-montage-capture.js") < IDX.index("/shared/dz-tutoriels.js"))
INTACTS = ["dz-capture.js", "dz-capture-scene.js", "dz-capture-logique.js", "dz-montage-capture.js",
           "dz-montage-capture-logique.js", "dz-skins.js", "dz-agent.js", "dz-agent-pointeur.js", "dz-agent-logique.js",
           "dz-agent-cadre.js"]
diff = subprocess.run(["git", "diff", "--name-only", BASE_T317, "--"] + [f"frontend/shared/{f}" for f in INTACTS]
                      + [f"frontend/dist/shared/{f}" for f in INTACTS], cwd=REPO, capture_output=True, text=True)
check("P3 capture, montage, skins et « Demander » non modifiés", diff.returncode == 0 and diff.stdout.strip() == "", diff.stdout)
check("P4 pointeur IMPORTÉ de « Demander »", 'import { creerPointeur } from "./dz-agent-pointeur.js"' in TXT
      and "dz-agent-logique.js" in TXT and "function creerPointeur" not in TXT)
check("P5 aucun clic simulé", not re.search(r"\.click\(\)|new (Mouse|Pointer)Event|dispatchEvent\(new (Mouse|Pointer)", TXT + LOG))
check("P6 ni eval, ni Function, ni alert/confirm/prompt", not re.search(r"\beval\(|new Function|\balert\(|\bconfirm\(|\bprompt\(", TXT + LOG))
check("P7 innerHTML réservé au glyphe de l'app", TXT.count("innerHTML") == 1 and "s.innerHTML = typeof window.dzIcone" in TXT)
check("P8 aucun emoji", not re.search("[\U0001F300-\U0001FAFF☀-➿]", TXT + LOG))
check("P9 téléchargement : un lien download, pas de clic", 'el("a", { href: lien, download: nom' in TXT)
check("P10 l'action du parcours passe par actionSure avant le pointeur", "const a = actionSure(e && e.action)" in TXT)
check("P11 navigation seulement depuis montrerEtape (geste « Montrer »)", TXT.count('new CustomEvent("deepotus:navigate"') == 1
      and TXT.index('new CustomEvent("deepotus:navigate"') > TXT.index("async function montrerEtape"))

print("[I] textes")
cles_js = set(re.findall(r'"(tuto\.[a-z_]+\.[a-z_]+)"', TXT))
check("I1 clés à 3 segments", all(re.fullmatch(r"tuto\.[a-z_]+\.[a-z_]+", k) for k in DICO), [k for k in DICO if k.count(".") != 2])
check("I2 toute clé employée existe", cles_js <= set(DICO), sorted(cles_js - set(DICO)))
check("I3 toute clé du dictionnaire est employée", set(DICO) <= cles_js, sorted(set(DICO) - cles_js))
var = lambda s: sorted(re.findall(r"\{(\w+)\}", s))                  # noqa: E731
check("I4 FR/EN mêmes variables, non vides", all(var(v["fr"]) == var(v["en"]) and v["fr"] and v["en"] for v in DICO.values()),
      [k for k, v in DICO.items() if var(v["fr"]) != var(v["en"])])
DZ = (SH / "dz-i18n-dico.js").read_text("utf-8")
check("I5 assemblées (dz-i18n-dico.js)", all(json.dumps(k, ensure_ascii=False) + ":" in DZ for k in DICO)
      and (SH / "dz-i18n-dico.js").read_bytes() == (DI / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
