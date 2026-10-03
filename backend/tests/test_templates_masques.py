# -*- coding: utf-8 -*-
"""Plan-templates T3 (tache #74 du suivi, PR A, 03/10/2026) — MASQUES de region (cases video et image), cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : arrondi, ellipse, fenetres ajourees, polygone ; video et image seulement ;
adoucissement reglable + liseré colore ; sans masque, rendu IDENTIQUE.
Ce que le plan faisait faux, et que ce banc garde : fenetres et points en PIXELS (le reagencement etire une case axe
par axe : ils deriveraient) — ici en fractions ; epaisseurs non reagencees ; aucune validation (une forme inconnue
devenait « rounded » en silence) ; un id de region non filtre dans un nom de fichier.
Banc-miroir : une image BLEUE masquee sur une toile ROUGE, rendue, pixels lus dans le MP4 (cinq rendus).
Preuve d'identite : SANS masque, la commande ffmpeg est la meme, a l'octet, que celle de la base (module charge de git).
Temoin positif : la base (7a89302a) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_templates_masques.py"""
import importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmask_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
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


BASE = "7a89302a"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_mask.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a pas le module des masques", r0.returncode != 0)

from PIL import Image                                               # noqa: E402
try:
    from app.services import template_mask as TM                    # noqa: E402
except ImportError as e:
    TM = None
    check("T2 le module existe", False, str(e))
from app.services import template_service as TS                     # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
from app.services import template_layout as TL                      # noqa: E402
E = TemplateEngine()


def reg(i, t, x, y, w, h, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, w=400, h=400, bg="#ff0000"):
    return {"id": "tpl_m", "name": "m", "canvas": {"width": w, "height": h, "fps": 10, "duration_s": 1, "background_color": bg}, "regions": regions}


def erreur(r):
    try:
        E._validate(tpl([r])); return None
    except ValueError as e:
        return str(e)


print("[V] la validation")
if TM:
    base = reg("v1", "video_slot", 0, 0, 100, 100, slot_name="v")
    cas = [dict(base, mask={"shape": "etoile"}), dict(base, mask={"shape": "polygon", "points": [[0, 0], [1, 1]]}),
           dict(base, mask={"shape": "polygon", "points": [[0, 0], [2, 0], [1, 1]]}), dict(base, mask={"holes": [{"x": 0.1, "y": 0.1, "width": 0, "height": 0.2}]}),
           dict(base, mask={"border_color": "vert"}), dict(base, mask={"feather_px": -2}), dict(base, mask="rond"),
           reg("b1", "badge", 0, 0, 100, 40, mask={"shape": "ellipse"})]
    es = [erreur(c) for c in cas]
    check("V1 refus qui NOMMENT region et champ : forme inconnue, polygone de 2 points, point hors 0..1, fenetre vide, couleur, adoucissement negatif, masque non objet, masque sur un badge",
          all(isinstance(e, str) for e in es) and "etoile" in es[0] and "3 à 64" in es[1] and "fractions" in es[2] and "fenêtre 1" in es[3]
          and "#RRGGBB" in es[4] and "feather_px" in es[5] and "objet" in es[6] and "vidéo et image" in es[7] and all("v1" in e for e in es[:7]), str(es))
    bons = [dict(base, mask={"shape": "rounded", "radius": 20, "feather_px": 4, "border_px": 3, "border_color": "#00ff00"}),
            dict(base, mask={"shape": "ellipse", "holes": [{"shape": "ellipse", "x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2}]}),
            dict(base, mask={"shape": "polygon", "points": [[0.5, 0], [1, 1], [0, 1]]}), reg("i1", "image_slot", 0, 0, 100, 100, slot_name="i", mask={"shape": "ellipse"})]
    check("V2 les masques bien formes passent (video et image)", all(erreur(b) is None for b in bons), str([erreur(b) for b in bons]))

print("\n[D] le dessin")
if TM:
    m1 = TM.dessiner_masque({"shape": "rounded", "radius": 30}, 100, 80)
    m2 = TM.dessiner_masque({"shape": "ellipse"}, 100, 80)
    m3 = TM.dessiner_masque({"shape": "polygon", "points": [[0.5, 0], [1, 1], [0, 1]]}, 100, 100)
    m4 = TM.dessiner_masque({"shape": "rounded", "radius": 0, "holes": [{"x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2}]}, 100, 100)
    m5 = TM.dessiner_masque({"shape": "rounded", "radius": 0, "feather_px": 20}, 100, 100)
    check("D1 arrondi : coin vide, centre plein ; ellipse : coin vide ; polygone (triangle) : coin haut vide, bas plein",
          m1.getpixel((1, 1)) == 0 and m1.getpixel((50, 40)) == 255 and m1.getpixel((99, 79)) == 0 and m2.getpixel((3, 3)) == 0
          and m2.getpixel((50, 40)) == 255 and m3.getpixel((5, 5)) == 0 and m3.getpixel((50, 95)) == 255 and m3.getpixel((50, 3)) > 0)
    check("D2 une fenetre est VIDE en son centre, la case pleine autour ; l'adoucissement donne un degrade au bord",
          m4.getpixel((50, 50)) == 0 and m4.getpixel((20, 20)) == 255 and 0 < m5.getpixel((1, 50)) < 255 and m5.getpixel((50, 50)) == 255,
          f"{m5.getpixel((1, 50))}")
    c1 = TM.dessiner_cadre({"shape": "rounded", "radius": 10, "border_px": 4, "border_color": "#00ff00",
                            "holes": [{"shape": "ellipse", "x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2}]}, 100, 100)
    check("D3 le liseré suit la forme (bord gauche vert) ET les fenetres ; le centre de la case est transparent ; sans epaisseur : pas de liseré",
          c1.getpixel((1, 50))[:3] == (0, 255, 0) and c1.getpixel((1, 50))[3] > 200 and c1.getpixel((25, 25))[3] == 0
          and c1.getpixel((40, 50))[3] > 100 and TM.dessiner_cadre({"shape": "rounded"}, 10, 10) is None, str(c1.getpixel((40, 50))))
    w = _tmp / "w"
    mp, fp = TM.ecrire({"id": "../../evil", "mask": {"shape": "ellipse", "border_px": 2}}, 20, 20, w)
    mp2, fp2 = TM.ecrire({"id": "r_ok", "mask": {"shape": "ellipse"}}, 20, 20, w)
    check("D4 un id de region douteux ne sort pas du dossier de travail (nom par empreinte) ; un id sur garde son nom",
          mp.parent == w and fp.parent == w and ".." not in mp.name and mp2.name == "mask_r_ok.png" and fp2 is None, f"{mp} {fp}")

print("\n[G] le graphe ffmpeg")
_sp = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
(_tmp / "ts_base.py").write_bytes(subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_service.py"], capture_output=True, cwd=str(RACINE)).stdout)
TSB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TSB)
BLEU = _tmp / "images" / "bleu.png"
Image.new("RGB", (300, 300), (0, 0, 255)).save(BLEU)
SLOTS = {"i": {"path": BLEU}}
sans = tpl([reg("img", "image_slot", 50, 50, 300, 300, slot_name="i", fit="cover")])
ca = TS.build_ffmpeg_command(E, sans, SLOTS, _tmp / "outputs" / "a.mp4", _tmp / "wa")
cb = TSB.build_ffmpeg_command(TSB.TemplateEngine(), sans, SLOTS, _tmp / "outputs" / "a.mp4", _tmp / "wa")
check("G1 SANS masque, la commande ffmpeg est IDENTIQUE a celle de la base (a l'octet)", ca == cb and "alphamerge" not in " ".join(map(str, ca)))
avec = json.loads(json.dumps(sans)); avec["regions"][0]["mask"] = {"shape": "ellipse", "border_px": 4, "border_color": "#00ff00"}
cc = " ".join(map(str, TS.build_ffmpeg_command(E, avec, SLOTS, _tmp / "outputs" / "b.mp4", _tmp / "wb")))
check("G2 AVEC masque : alphamerge sur la case, puis le liseré pose APRES la case", "alphamerge" in cc and cc.index("alphamerge") < cc.index("[fr1i]overlay")
      and (_tmp / "wb" / "mask_img.png").is_file() and (_tmp / "wb" / "frame_img.png").is_file(), cc[-400:])

print("\n[R] banc-miroir : rendus, pixels lus")
FF = shutil.which("ffmpeg")


def rendre(nom, mask):
    t = json.loads(json.dumps(sans))
    if mask is not None:
        t["regions"][0]["mask"] = mask
    mp4 = E.render("tpl_m", SLOTS, _tmp / "outputs" / f"{nom}.mp4", template=t)
    png = _tmp / "outputs" / f"{nom}.png"
    subprocess.run([FF, "-y", "-v", "error", "-i", str(mp4), "-frames:v", "1", str(png)], check=True)
    return Image.open(png).convert("RGB")


rouge = lambda p: p[0] > 170 and p[1] < 90 and p[2] < 90
bleu = lambda p: p[2] > 170 and p[0] < 90 and p[1] < 90
vert = lambda p: p[1] > 150 and p[0] < 110 and p[2] < 110
if TM and FF:
    a = rendre("arrondi", {"shape": "rounded", "radius": 70, "border_px": 8, "border_color": "#00ff00"})
    check("R1 arrondi + liseré : le coin de la case montre la TOILE (rouge), le centre l'image (bleu), le bord gauche le liseré (vert)",
          rouge(a.getpixel((53, 53))) and bleu(a.getpixel((200, 200))) and vert(a.getpixel((53, 200))), f"{a.getpixel((53, 53))} {a.getpixel((53, 200))}")
    b = rendre("ellipse", {"shape": "ellipse"})
    c = rendre("fenetre", {"shape": "rounded", "radius": 0, "holes": [{"shape": "rect", "x": 0.35, "y": 0.35, "width": 0.3, "height": 0.3}]})
    d = rendre("triangle", {"shape": "polygon", "points": [[0.5, 0], [1, 1], [0, 1]]})
    check("R2 ellipse : coin rouge, centre bleu ; fenetre : centre ROUGE (la toile au travers), bleu autour ; triangle : coin haut-gauche rouge, bas bleu",
          rouge(b.getpixel((60, 60))) and bleu(b.getpixel((200, 200))) and rouge(c.getpixel((200, 200))) and bleu(c.getpixel((80, 200)))
          and rouge(d.getpixel((70, 70))) and bleu(d.getpixel((200, 330))), f"{b.getpixel((60, 60))} {c.getpixel((200, 200))} {d.getpixel((70, 70))}")
    e = rendre("adouci", {"shape": "rounded", "radius": 0, "feather_px": 40})
    pe = e.getpixel((52, 200))
    check("R3 bord adouci : au bord, un MELANGE rouge/bleu (ni l'un ni l'autre) ; au centre, bleu pur", pe[0] > 40 and pe[2] > 40 and bleu(e.getpixel((200, 200))), str(pe))
    z = rendre("sans", None)
    check("R4 sans masque : la case entiere est bleue (coin compris)", bleu(z.getpixel((53, 53))) and bleu(z.getpixel((200, 200))) and rouge(z.getpixel((20, 20))))
else:
    check("R0 ffmpeg disponible pour le banc-miroir", False, "ffmpeg introuvable")

print("\n[L] le reagencement")
if TM:
    tl = tpl([reg("v", "video_slot", 790, 1590, 250, 250, slot_name="v", mask={"shape": "rounded", "radius": 40, "feather_px": 10, "border_px": 6,
              "holes": [{"shape": "rect", "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4, "radius": 8}], "points": [[0.5, 0], [1, 1], [0, 1]]})], 1080, 1920)
    o, _ = TL.reflow(tl, "16:9")
    mo = o["regions"][0]["mask"]
    s = min(1920 / 1080, 1080 / 1920)
    check("L1 reagence : rayon, adoucissement, liseré et rayon des fenetres suivent l'echelle ; fenetres et points (fractions) ne bougent pas",
          mo["radius"] == round(40 * s, 2) and mo["feather_px"] == round(10 * s, 2) and mo["border_px"] == round(6 * s, 2)
          and mo["holes"][0] == {"shape": "rect", "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4, "radius": round(8 * s, 2)}
          and mo["points"] == [[0.5, 0], [1, 1], [0, 1]] and tl["regions"][0]["mask"]["radius"] == 40, str(mo))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
