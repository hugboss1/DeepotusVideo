# -*- coding: utf-8 -*-
"""t317 (28/10/2026) (D3, tâche 5) — l'éditeur de montage côté écran, joué sous node (aucun navigateur).
Plan docs/superpowers/plans/2026-10-28-t317-montage-capture.md, spec boîte à outils §8.4.
[L] dz-montage-capture-logique.js = les formules du RENDU (app/services/capture_montage.py) : zoomA = zoom_a sur 200
    instants, segments, versSortie, cadreFormat ; fenêtre de l'aperçu (plein cadre sans zoom, centrée, bornée) ;
    lecture (saut d'une coupe, vitesse) ; zoom ajouté sans chevauchement ; brouillon du Planificateur (draft, sans
    canaux, demain 10 h) ;
[P] livraison : copies shared == dist ; index.html charge le module une fois, après dz-capture.js ; dz-capture.js et
    dz-capture-scene.js NON modifiés depuis t316 ; ni alert/confirm/prompt ni emoji ni écoute clavier hors du piège ;
    la transcription payante n'est lancée qu'avec confirme_cout venu du bouton de devis ; le Planificateur reçoit un
    brouillon sans canaux ; clés montagecap.* FR/EN à 3 segments, mêmes variables, toutes employées, assemblées.
Le comportement à l'écran (entrées posées dans les boîtes de dz-capture.js, éditeur, rendu) est prouvé dans Chrome sur
le backend de preuve (docs/superpowers/specs/captures/t317/).
Run (depuis backend/) : & $PY tests/test_capture_montage_ecran.py"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
NODE = shutil.which("node")
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
FICHIERS = ["dz-montage-capture.js", "dz-montage-capture-logique.js"]
DICO = json.loads((SH / "i18n" / "montagecap.json").read_text("utf-8"))
TXT = (SH / "dz-montage-capture.js").read_text("utf-8")
LOG = (SH / "dz-montage-capture-logique.js").read_text("utf-8")


def node(script: str):
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzmontjs_"))
    f = d / "banc.mjs"
    f.write_text(script, "utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = r.stdout.strip().splitlines()
    if r.returncode or not out:
        raise RuntimeError((r.stderr or r.stdout)[-1500:])
    return json.loads(out[-1])


from app.services import capture_montage as M                      # noqa: E402

MONT = {"zooms": [{"id": "a", "t0": 1000, "t1": 4000, "k": 2.2, "x": 0.2, "y": 0.8},
                  {"id": "b", "t0": 5000, "t1": 5600, "k": 1.5, "x": 0.9, "y": 0.1}],
        "coupes": [{"id": "c", "t0": 6000, "t1": 9000, "mode": "accelerer", "vitesse": 8},
                   {"id": "d", "t0": 9500, "t1": 11000, "mode": "couper", "vitesse": 8}],
        "chapitres": [], "format": "9:16"}
INSTANTS = [i * 61 for i in range(200)]

print("[L] logique")
L = node(r"""
const L = await import(%s);
const m = %s, ts = %s;
const z = ts.map((t) => { const r = L.zoomA(m, t); return [r.z, r.cx, r.cy]; });
const segs = L.segments(m, 12000);
const vs = [0, 3000, 7000, 9600, 12000].map((t) => L.versSortie(t, segs));
const plein = L.fenetre({zooms: []}, 0, 1440, 900, "16:9");
const vert = L.fenetre({zooms: []}, 0, 1440, 900, "9:16");
const bord = L.fenetre({zooms: [{t0: 0, t1: 4000, k: 2.5, x: 0.99, y: 0.01}]}, 2000, 1440, 900, "16:9");
const cf = [["16:9", 1440, 900], ["9:16", 1440, 900], ["1:1", 1440, 900], ["9:16", 1080, 1920]].map(([f, l, h]) => L.cadreFormat(f, l, h));
const lec = [L.lecture(m, 7000), L.lecture(m, 10000), L.lecture(m, 500)];
let n = {zooms: [{id: "x", t0: 0, t1: 3000, k: 2, x: .5, y: .5}, {id: "y", t0: 3500, t1: 6000, k: 2, x: .5, y: .5}]};
n = L.ajouterZoom(n, 3200, 0.3, 0.3, 9, 12000);
const br = L.brouillon({job_id: "J", chapitres_texte: "00:00 A"}, "Tuto", "9:16", Date.UTC(2026, 9, 28, 8, 0, 0));
console.log(JSON.stringify({z, segs, vs, plein, vert, bord, cf, lec, n: n.zooms, br,
  proche: L.clicProche([{type:"clic", t: 100, x: .1, y: .2}, {type:"clic", t: 200, x: .7, y: .7, secret: true}], 900),
  ecran: L.ecranA([{type:"ecran", t:0, ecran:"quick"}, {type:"ecran", t:500, ecran:"studio"}], 400),
  lib: [L.libelleChapitre({titre:"", ecran:"sonvfx_hub"}, 0), L.libelleChapitre({titre:"", ecran:""}, 2),
        L.libelleChapitre({titre:"", ecran:"library"}, 1, (k) => "<" + k + ">")],
  remplis: L.titresRemplis({chapitres: [{id:"a", t:0, titre:"", ecran:"library"}, {id:"b", t:9, titre:"Mon titre", ecran:"quick"}]},
    (k) => "Bibliothèque").chapitres.map((h) => h.titre)}));
""" % (json.dumps((SH / "dz-montage-capture-logique.js").resolve().as_uri()), json.dumps(MONT), json.dumps(INSTANTS)))
py = [list(M.zoom_a(MONT, t)) for t in INSTANTS]
check("L1 zoomA (JS) = zoom_a (Python) sur 200 instants",
      all(abs(a - b) < 1e-9 for p, j in zip(py, L["z"]) for a, b in zip(p, j)))
check("L2 segments = Python", [list(s) for s in M.segments(MONT, 12000)] == L["segs"], L["segs"])
check("L3 versSortie = Python", L["vs"] == [M.vers_sortie(t, M.segments(MONT, 12000)) for t in (0, 3000, 7000, 9600, 12000)],
      L["vs"])
check("L4 cadreFormat = cadre_format", L["cf"] == [list(M.cadre_format(f, l, h)) for f, l, h in
                                                  [("16:9", 1440, 900), ("9:16", 1440, 900), ("1:1", 1440, 900),
                                                   ("9:16", 1080, 1920)]], L["cf"])
check("L5 sans zoom : 16:9 pleine largeur centré, 9:16 centré", L["plein"] == {"sx": 0, "sy": 45, "sl": 1440, "sh": 810}
      and L["vert"] == {"sx": 467, "sy": 0, "sl": 506, "sh": 900}, (L["plein"], L["vert"]))
b = L["bord"]
check("L6 zoom collé au bord : fenêtre dans l'image", b["sx"] >= 0 and b["sy"] >= 0 and b["sx"] + b["sl"] <= 1440.001
      and b["sy"] + b["sh"] <= 900.001 and abs(b["sl"] - 1440 / 2.5) < 1e-6, b)
check("L7 lecture : accéléré ×8, coupe sautée, normal", L["lec"] == [{"saut": None, "vitesse": 8},
      {"saut": 11000, "vitesse": 1}, {"saut": None, "vitesse": 1}], L["lec"])
zs = sorted(L["n"], key=lambda z: z["t0"])
check("L8 zoom ajouté : borné (k 2,5), voisins rognés, jamais de chevauchement", len(zs) == 3
      and all(a["t1"] <= b["t0"] for a, b in zip(zs, zs[1:])) and any(z["k"] == 2.5 and z["t0"] == 2700 for z in zs), zs)
check("L9 brouillon : draft, sans canaux, demain 10 h, job et chapitres", L["br"]["status"] == "draft"
      and "channels" not in L["br"] and "comptes" not in L["br"] and L["br"]["job_id"] == "J"
      and L["br"]["caption"] == "00:00 A" and L["br"]["run_at"].startswith("2026-10-29T") and L["br"]["format"] == "9:16",
      L["br"])
check("L10 clic proche (jamais un clic masqué), écran à l'instant, libellés", L["proche"] == {"x": 0.1, "y": 0.2}
      and L["ecran"] == "quick" and L["lib"] == ["Sonvfx hub", "3", "<coque.rail.bibliotheque>"]
      and L["remplis"] == ["Bibliothèque", "Mon titre"], (L["proche"], L["ecran"], L["lib"], L["remplis"]))

print("[P] livraison")
check("P1 copies shared == dist", all((SH / f).read_bytes() == (DI / f).read_bytes() for f in FICHIERS))
idx = (REPO / "frontend" / "dist" / "index.html").read_text("utf-8")
check("P2 index.html : une balise, après dz-capture.js", idx.count('src="/shared/dz-montage-capture.js"') == 1
      and idx.index("/shared/dz-capture.js") < idx.index("/shared/dz-montage-capture.js"))
base = subprocess.run(["git", "diff", "--quiet", "f1cf9bd9", "--", "frontend/shared/dz-capture.js",
                       "frontend/shared/dz-capture-scene.js", "frontend/shared/dz-capture-logique.js"], cwd=REPO)
check("P3 dz-capture*.js non modifiés depuis la base t316", base.returncode == 0)
tout = TXT + LOG
check("P4 ni alert/confirm/prompt, ni emoji, ni écoute clavier hors du piège Escape/Tab",
      not re.search(r"\b(alert|confirm|prompt)\s*\(", tout) and not re.search(r"[\U0001F300-\U0001FAFF☀-➿]", tout)
      and tout.count('addEventListener("keydown"') == 1 and "keypress" not in tout and "keyup" not in tout)
check("P5 transcription payante : confirme_cout seulement depuis le bouton du devis",
      TXT.count("confirme_cout") == 1 and re.search(r"confirmer\.addEventListener\(\"click\", \(\) => lancerRendu\(\{ confirme_cout: true",
                                                    TXT) is not None)
check("P6 Planificateur : POST /api/schedule avec brouillon(), aucun canal posé par l'écran",
      '"/api/schedule"' in TXT and "brouillon(j," in TXT and "channels" not in tout and "comptes" not in tout)
cles = set(DICO)
check("P7 clés à 3 segments montagecap.*", all(re.fullmatch(r"montagecap\.[a-z_]+\.[a-z0-9_]+", k) for k in cles))
var = lambda s: sorted(re.findall(r"\{(\w+)\}", s))                  # noqa: E731
check("P8 FR/EN mêmes variables, non vides", all(v["fr"].strip() and v["en"].strip() and var(v["fr"]) == var(v["en"])
                                                 for v in DICO.values()))
emploi = set(re.findall(r'"(montagecap\.[a-z_]+\.[a-z0-9_]+)"(?!\s*\+)', TXT))
dyn = {"montagecap.coupe." + x for x in ("accelerer", "couper")} | {"montagecap.st." + x for x in
       ("aucun", "texte", "transcrire")} | {"montagecap.st_etat." + x for x in ("graves", "echec", "sans_voix",
                                                                                    "sans_texte")} \
    | {"montagecap.format.f" + x for x in ("16x9", "9x16", "1x1")}
check("P9 toutes les clés employées, aucune clé employée absente", (emploi | dyn) == cles,
      (sorted((emploi | dyn) - cles), sorted(cles - (emploi | dyn))))
dico_js = (SH / "dz-i18n-dico.js").read_text("utf-8")
check("P10 clés assemblées (dz-i18n-dico.js, deux copies identiques)", all(f'"{k}"' in dico_js for k in cles)
      and (SH / "dz-i18n-dico.js").read_bytes() == (DI / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
