# -*- coding: utf-8 -*-
"""Plan-templates T8 / D1 (tache #76 du suivi, PR E, 03/10/2026) — COMPOSANTS (groupes de regions reutilisables),
cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : une instance garde la forme du composant, on n'y change que les TEXTES et les
COULEURS ; « Enregistrer comme composant » depuis l'editeur ; pas de composant dans un composant.
Ce que le plan faisait faux : un composant livre au schema invalide (contraintes anglaises, effets plats, jetons de
marque inexistants) ; un resoudre() qui perdait le kit et le raccourci « sans jeton » ; des sous-regions qui
pouvaient deborder d'un pixel ; un enregistrement possible dans le dossier des livres.
Preuve d'identite : un gabarit SANS composant est resolu tel quel (meme objet) et rendu par la meme commande.
Temoin positif : la base (ba3ee1fa) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_templates_composants.py"""
import importlib.util, io, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcomp_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "ba3ee1fa"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_components.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a pas le module des composants", r0.returncode != 0)
from PIL import Image                                               # noqa: E402
from app.services import template_components as TC                  # noqa: E402
from app.services import template_service as TSV                    # noqa: E402
from app.services import template_layout as TL                      # noqa: E402
from app.services import template_still as TS                       # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
E = TemplateEngine()
D = _tmp / "outputs" / "_tmp_still"


def reg(i, t, x, y, w, h, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, w=1000, h=1000, **kw):
    return dict({"id": "tpl_k", "name": "k", "canvas": {"width": w, "height": h, "fps": 10, "duration_s": 2, "background_color": "#101010"}, "regions": regions}, **kw)


def erreur(f):
    try:
        f(); return None
    except (ValueError, RuntimeError) as e:
        return str(e)


print("[I] l'identite")
SANS = tpl([reg("t", "text", 20, 20, 500, 100, text="Titre"), reg("s", "separator", 0, 200, 1000, 10)])
check("I1 sans composant, resoudre rend le MEME objet (aucune copie, aucun changement)", E.resoudre(SANS) is SANS)
(_tmp / "ts_base.py").write_bytes(subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_service.py"], capture_output=True, cwd=str(RACINE)).stdout)
_sp = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
TSB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TSB)
(_tmp / "wa").mkdir(); (_tmp / "wb").mkdir()
ca = [str(x) for x in TSV.build_ffmpeg_command(E, SANS, {}, _tmp / "o.mp4", _tmp / "wa")]
cb = [str(x).replace(str(_tmp / "wb"), str(_tmp / "wa")) for x in TSB.build_ffmpeg_command(E, SANS, {}, _tmp / "o.mp4", _tmp / "wb")]
check("I2 la commande ffmpeg d'un gabarit sans composant est celle de la base", ca == cb)

print("\n[K] le composant livre et le depliage")
L = TC.lister()
liv = next((c for c in L if c["id"] == "cmp_bandeau_titre"), None)
check("K1 le composant livre « Bandeau titre » est liste (livre) et VALIDE pour le moteur", liv is not None and liv["builtin"]
      and erreur(lambda: TC.verifier_composant(liv, E)) is None, str(L))
INST = reg("b1", "component", 100, 600, 500, 110, component="cmp_bandeau_titre", z_index=5,
           overrides={"titre": {"text": "LE POULPE"}, "sous_titre": {"color": "#ffd400"}}, animation={"in": {"type": "fade"}})
R = E.resoudre(tpl([INST]))
sub = {r["id"]: r for r in R["regions"]}
check("K2 l'instance se DEPLIE en ses sous-regions, ids prefixes, a l'echelle de sa boite (x0,5 par axe), dans l'ordre du composant",
      list(sub) == ["b1__fond", "b1__barre", "b1__titre", "b1__sous_titre"] and (sub["b1__fond"]["x"], sub["b1__fond"]["y"], sub["b1__fond"]["width"], sub["b1__fond"]["height"]) == (100, 600, 500, 110)
      and (sub["b1__titre"]["x"], sub["b1__titre"]["y"]) == (122, 614) and sub["b1__barre"]["width"] == 7, str(sub.get("b1__titre")))
check("K3 textes a l'echelle (plus petit rapport), SURCHARGES appliquees (texte, couleur), reste du composant garde ; animation et rang passent a chacune",
      sub["b1__titre"]["size"] == 32 and sub["b1__titre"]["text"] == "LE POULPE" and sub["b1__sous_titre"]["color"] == "#ffd400"
      and sub["b1__sous_titre"]["text"] == "Sous-titre" and all(s.get("animation") == {"in": {"type": "fade"}} for s in sub.values())
      and all(5 <= s["z_index"] < 6 for s in sub.values()) and sub["b1__titre"]["z_index"] > sub["b1__fond"]["z_index"], str(sub["b1__titre"]))
check("K3b une instance ANIMEE (et surchargee) passe la validation du gabarit tel qu'enregistre", erreur(lambda: E._validate(tpl([INST]))) is None,
      str(erreur(lambda: E._validate(tpl([INST])))))
BORD = TC.deplier(tpl([reg("b2", "component", 3, 3, 997, 333, component="cmp_bandeau_titre")]))
check("K4 l'arrondi ne deborde jamais : chaque sous-region tient dans la boite de l'instance (et la toile) ; le gabarit deplie est VALIDE",
      all(s["x"] + s["width"] <= 1000 and s["y"] + s["height"] <= 336 for s in BORD["regions"]) and erreur(lambda: E._validate(BORD)) is None)

print("\n[V] la validation")
cas = [lambda: E._validate(tpl([reg("x", "component", 0, 0, 100, 100, component="cmp_absent")])),
       lambda: E._validate(tpl([reg("x", "component", 0, 0, 100, 100, component="cmp_bandeau_titre", overrides={"inconnu": {"text": "a"}})])),
       lambda: E._validate(tpl([reg("x", "component", 0, 0, 100, 100, component="cmp_bandeau_titre", overrides={"titre": {"x": 5}})])),
       lambda: E._validate(tpl([reg("x", "component", 0, 0, 100, 100, component="cmp_bandeau_titre", overrides={"titre": {"color": "rouge"}})])),
       lambda: TC.verifier_composant({"name": "a", "width": 100, "height": 100, "regions": [reg("c", "component", 0, 0, 10, 10, component="cmp_bandeau_titre")]}, E),
       lambda: TC.verifier_composant({"name": "a", "width": 100, "height": 100, "regions": [reg("v", "video_slot", 0, 0, 10, 10, slot_name="v")]}, E),
       lambda: TC.verifier_composant({"name": " ", "width": 100, "height": 100, "regions": [reg("t", "text", 0, 0, 10, 10, text="x")]}, E),
       lambda: TC.verifier_composant({"name": "a", "width": 100, "height": 100, "regions": [reg("t", "text", 0, 0, 200, 10, text="x")]}, E),
       lambda: TC.lire("../secret"), lambda: TC.lire("../tpl_news_reel")]
es = [erreur(f) for f in cas]
check("V1 refus parlants : composant inconnu, surcharge d'une sous-region absente, d'un champ de FORME, couleur illisible ; composant dans un composant ; case video ; sans nom ; sous-region hors de la boite ; id qui sort du dossier (meme vers un GABARIT voisin)",
      all(es) and "cmp_absent" in es[0] and "inconnu" in es[1] and "forme" in es[2] and "#RRGGBB" in es[3] and "composant dans un composant" in es[4]
      and "video_slot" in es[5] and "nom" in es[6] and "exceeds" in es[7] and "inconnu" in es[8].lower() and "inconnu" in es[9].lower(), str(es))

(TC.dossier_utilisateur() / "cmp_bandeau_titre.json").write_text('{"id": "cmp_bandeau_titre", "name": "Imposteur", "width": 10, "height": 10, "regions": []}', encoding="utf-8")
lst = [c for c in TC.lister() if c["id"] == "cmp_bandeau_titre"]
check("V2 un fichier utilisateur au nom d'un LIVRE ne le masque pas (liste et lecture rendent le livre)",
      len(lst) == 1 and lst[0]["name"] == "Bandeau titre" and TC.lire("cmp_bandeau_titre")["name"] == "Bandeau titre", str(lst))
(TC.dossier_utilisateur() / "cmp_bandeau_titre.json").unlink()

print("\n[S] slots, marque, reagencement, rendu")
cmp_slot = {"name": "Slot", "width": 400, "height": 100, "regions": [reg("t", "text_slot", 0, 0, 400, 100, slot_name="titre", default_text="{{brand.app_name}}")]}
cid = TC.enregistrer(cmp_slot, E)
T2 = tpl([reg("k1", "component", 0, 0, 800, 200, component=cid)])
slots = E.slots_from(T2)
check("S1 les SLOTS d'un composant sont proposes, prefixes par l'instance (deux instances ne se melangent pas)",
      [s["slot_name"] for s in slots] == ["k1_titre"], str(slots))
res = E.resoudre(T2)
check("S2 les jetons de MARQUE dans un composant sont resolus (depliage AVANT les jetons)", "{{" not in json.dumps(res) and res["regions"][0]["default_text"], str(res["regions"][0]))
o, _ = TL.reflow(tpl([INST], 1080, 1920), "16:9")
d = TC.deplier(o)
check("S3 le reagencement deplace et met a l'echelle l'INSTANCE ; son depliage suit (tout dans la nouvelle toile)",
      o["regions"][0]["type"] == "component" and all(s["x"] + s["width"] <= 1920 and s["y"] + s["height"] <= 1080 for s in d["regions"]) and erreur(lambda: E._validate(d)) is None)
im = Image.open(io.BytesIO(TS.rendre(E, tpl([INST]), 1.0, "png", D))).convert("RGB")
jaune = sum(1 for x in range(100, 600, 2) for y in range(660, 710, 2) if im.getpixel((x, y))[0] > 200 and im.getpixel((x, y))[1] > 180 and im.getpixel((x, y))[2] < 80)
check("S4 RENDU : le fond du composant dans la boite, le titre surcharge en blanc, le sous-titre en JAUNE (surcharge de couleur)",
      im.getpixel((300, 605)) == (2, 6, 13) and im.getpixel((50, 650)) == (16, 16, 16) and jaune > 10
      and sum(1 for x in range(120, 600, 2) for y in range(612, 660, 2) if sum(im.getpixel((x, y))) > 600) > 20, f"{im.getpixel((300, 605))} jaune={jaune}")
k1 = TS.cle_vignette(E, T2)
p = TC.dossier_utilisateur() / f"{cid}.json"
c = json.loads(p.read_text(encoding="utf-8")); c["regions"][0]["default_text"] = "Autre"; p.write_text(json.dumps(c), encoding="utf-8")
check("S5 modifier un COMPOSANT change la vignette des gabarits qui le posent (cle sur le gabarit deplie)", TS.cle_vignette(E, T2) != k1)

print("\n[W] les routes")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
NOUV = {"name": "Bandeau titre", "width": 600, "height": 120, "regions": [reg("t", "text", 0, 0, 600, 120, text="Coucou")]}
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as cl:
    w1 = cl.get("/api/template-components").json()
    w2 = cl.post("/api/template-components", json=NOUV)
    w3 = cl.post("/api/template-components", json={"name": "x", "width": 100, "height": 100, "regions": []})
    nid = w2.json().get("id") if w2.status_code == 200 else None
    E.save_template(tpl([reg("i1", "component", 0, 0, 600, 120, component=nid)], **{"id": "", "name": "Gabarit qui pose"})) if nid else None
    w4 = cl.delete(f"/api/template-components/{nid}")
    w5 = cl.delete("/api/template-components/cmp_bandeau_titre")
    w6 = cl.post("/api/template-components", json=dict(NOUV, name="Jetable"))
    w7 = cl.delete(f"/api/template-components/{w6.json().get('id')}")
    w8 = cl.get("/api/template-components").json()
with TestClient(app, client=("192.168.1.20", 50000), raise_server_exceptions=False) as c2:
    w9 = c2.post("/api/template-components", json=NOUV).status_code
check("W1 la liste : le livre d'abord, puis ceux de l'utilisateur",
      [c["id"] for c in w1["components"]][0] == "cmp_bandeau_titre" and w1["components"][0]["builtin"] is True, str([c["id"] for c in w1["components"]]))
check("W2 creer : un id tire du nom, qui ne MASQUE jamais un livre de meme nom (_2) ; refus parlant (400) d'un composant vide",
      w2.status_code == 200 and nid == "cmp_bandeau_titre_2" and w3.status_code == 400 and "au moins une région" in w3.json()["detail"], f"{w2.text[:200]} {w3.text[:120]}")
check("W3 supprimer : refuse (409) tant qu'un gabarit le pose, en le NOMMANT ; un livre ne se supprime pas (400) ; un composant libre part",
      w4.status_code == 409 and "Gabarit qui pose" in w4.json()["detail"] and w5.status_code == 400 and w7.status_code == 200
      and w6.json()["id"] not in [c["id"] for c in w8["components"]], f"{w4.status_code} {w5.status_code} {w7.status_code}")
check("W4 hors de la machine : refuse", w9 in (401, 403), str(w9))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
