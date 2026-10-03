# -*- coding: utf-8 -*-
"""Plan-templates T9 / D2 (tache #76 du suivi, PR A, 03/10/2026) — ANIMATIONS d'entree et de sortie des regions,
cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : fondu, glissement, pop + courbes (lineaire, douce, rebond) ; TOUTES les regions
visibles (cases, textes, badges, stickers, separateurs, bandeaux, tickers ; le liseré d'un masque suit sa case) ;
SANS animation, rendu identique a l'octet.
Ce que le plan faisait faux, et que ce banc garde : « pop impossible » (scale lit t en eval=frame) ; overlay anime
pose sur TOUTE commande (la garantie au pixel tombait) ; textes et badges non animes ; liseré laisse sur place.
Mesure qui fonde la technique (ffmpeg 9.0.1) : une source color=black@0 DONNEE EN ENTREE sort en yuv420p, opaque ;
creee dans le graphe en rgba elle reste transparente ; drawbox y exige replace=1.
Temoin positif : la base (9dcf4d3d) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_templates_anim.py"""
import importlib.util, io, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzanim_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "FAL_KEY", "HEYGEN_API_KEY"):
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


BASE = "9dcf4d3d"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_anim.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a pas le module des animations", r0.returncode != 0)
from PIL import Image                                               # noqa: E402
try:
    from app.services import template_anim as TA                    # noqa: E402
except ImportError as e:
    TA = None
    check("T2 le module existe", False, str(e))
from app.services import template_service as TSV                    # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
from app.config import settings                                     # noqa: E402
E = TemplateEngine()
FF = shutil.which("ffmpeg")
IMG = pathlib.Path(settings.images_path)
Image.new("RGB", (64, 64), (255, 0, 0)).save(IMG / "rouge.png")
Image.new("RGBA", (64, 64), (0, 0, 255, 255)).save(IMG / "bleu.png")
FOND = (16, 16, 16)


def reg(i, t, x, y, w, h, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, w=400, h=400, d=4, **kw):
    return dict({"id": "tpl_a", "name": "a", "canvas": {"width": w, "height": h, "fps": 10, "duration_s": d, "background_color": "#101010"}, "regions": regions}, **kw)


SV = {"pic": {"path": IMG / "rouge.png"}}


def images(t, instants):
    mp4 = E.render("a", SV, _tmp / "outputs" / f"r{abs(hash(json.dumps(t, sort_keys=True))) % 10**8}.mp4", template=t)
    out = {}
    for s in instants:
        png = _tmp / f"f{s}.png"
        subprocess.run([FF, "-v", "error", "-y", "-ss", str(s), "-i", str(mp4), "-frames:v", "1", str(png)], check=True)
        out[s] = Image.open(png).convert("RGB")
    return out


def proche(p, q, tol=12):
    return all(abs(a - b) <= tol for a, b in zip(p, q))


print("[I] l'identite : sans animation, rien ne change")
_sp = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
(_tmp / "ts_base.py").write_bytes(subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_service.py"], capture_output=True, cwd=str(RACINE)).stdout)
TSB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TSB)
TOUT = tpl([reg("im", "image_slot", 0, 0, 200, 200, slot_name="pic", mask={"shape": "ellipse", "border_px": 3}),
            reg("tx", "text", 10, 210, 380, 60, text="Titre", size=40, effect="pulse", text_effects={"stroke": {"px": 3}}),
            reg("bd", "badge", 210, 10, 180, 60, text="LIVE", effect="pulse"), reg("sp", "separator", 0, 280, 400, 6, color="#00ff00"),
            reg("st", "sticker", 300, 300, 80, 80, image_src="bleu.png"), reg("tk", "ticker", 0, 330, 400, 40, text="defile", background_color="#000000"),
            reg("bs", "brand_strip", 0, 370, 400, 30, background_color="#0000ff", items=[{"type": "text", "text": "$DZ", "x": 10, "y": 2, "size": 20}])])
for d in ("wa", "wb", "wc", "wd"):
    (_tmp / d).mkdir(exist_ok=True)
ca = [str(x) for x in TSV.build_ffmpeg_command(E, TOUT, SV, _tmp / "o.mp4", _tmp / "wa")]
cb = [str(x).replace(str(_tmp / "wb"), str(_tmp / "wa")) for x in TSB.build_ffmpeg_command(E, TOUT, SV, _tmp / "o.mp4", _tmp / "wb")]
check("I1 commande video (case masquee, texte a effets pulse, badge, separateur, sticker, ticker, bandeau) identique a la base", ca == cb,
      next((f"{x} != {y}" for x, y in zip(ca, cb) if x != y), "longueurs"))
sa = [str(x) for x in TSV.build_ffmpeg_command(E, TOUT, SV, _tmp / "o.png", _tmp / "wc", still_at=1)]
sb = [str(x).replace(str(_tmp / "wd"), str(_tmp / "wc")) for x in TSB.build_ffmpeg_command(E, TOUT, SV, _tmp / "o.png", _tmp / "wd", still_at=1)]
check("I2 commande d'IMAGE FIXE identique a la base aussi", sa == sb, next((f"{x} != {y}" for x, y in zip(sa, sb) if x != y), "longueurs"))

print("\n[V] la validation")
if TA:
    def erreur(t):
        try:
            E._validate(t); return None
        except ValueError as e:
            return str(e)
    bon = {"in": {"type": "pop", "duration": 0.8, "delay": 0.2, "easing": "back"}, "out": {"type": "fade"}}
    cas = [tpl([reg("r1", "text", 0, 0, 100, 50, text="x", animation={"in": {"type": "spin"}})]),
           tpl([reg("r1", "text", 0, 0, 100, 50, text="x", animation={"in": {"type": "fade", "duration": 30}})]),
           tpl([reg("r1", "text", 0, 0, 100, 50, text="x", animation={"in": {"type": "fade", "delay": -1}})]),
           tpl([reg("r1", "text", 0, 0, 100, 50, text="x", animation={"in": {"type": "fade", "easing": "elastique"}})]),
           tpl([reg("r1", "text", 0, 0, 100, 50, text="x", animation={"pendant": {}})]),
           tpl([reg("a1", "video_slot", 0, 0, 400, 400, slot_name="a1", animation=bon)], render_mode="sequential"),
           tpl([reg("r0", "text", 0, 0, 10, 10, text="x"), {"id": "r1", "type": "audio_slot", "slot_name": "son", "animation": bon}])]
    es = [erreur(c) for c in cas]
    check("V1 refus qui NOMMENT region et champ : type, duree, delai, courbe, cle inconnue, gabarit sequentiel, piste son",
          all(es) and all(("r1" in e) for e in es[:5]) and "pop" in es[0] and "0.05 et 10" in es[1] and "0 et 600" in es[2]
          and "back" in es[3] and "in" in es[4] and "spatiaux" in es[5] and "audio_slot" in es[6] and "r1" in es[6], str(es))
    check("V2 une animation bien formee passe ; une animation vide (null) aussi", erreur(tpl([reg("r1", "text", 0, 0, 100, 50, text="x", animation=bon)])) is None
          and erreur(tpl([reg("r1", "text", 0, 0, 100, 50, text="x", animation=None)])) is None)
    n = TA.normaliser({"animation": {"in": {"type": "fade"}}})
    check("V3 valeurs par defaut : 0,6 s, sans delai, courbe douce ; pas d'animation -> None",
          n == {"in": {"type": "fade", "d": 0.6, "delai": 0.0, "e": "ease_out"}, "out": None} and TA.normaliser({}) is None
          and TA.normaliser({"animation": {"in": None}}) is None, str(n))

print("\n[A] les rendus, pixels lus")
if TA and FF:
    A = lambda t, **k: {"in": dict({"type": t, "duration": 1, "delay": 1}, **k)}
    F = images(tpl([reg("sp", "separator", 0, 20, 400, 20, color="#00ff00", animation={"in": {"type": "fade", "duration": 1, "delay": 1, "easing": "linear"},
                                                                                       "out": {"type": "fade", "duration": 0.5, "delay": 0.5}})]), (0.5, 1.5, 2.5, 3.8))
    v = {s: F[s].getpixel((200, 30)) for s in F}
    check("A1 FONDU : rien avant le delai, a moitie au milieu, plein ensuite, puis il s'efface en fin de rendu ; le reste de l'image ne bouge pas",
          proche(v[0.5], FOND, 3) and 90 < v[1.5][1] < 170 and proche(v[2.5], (0, 255, 0), 4) and proche(v[3.8], FOND, 6)
          and all(proche(F[s].getpixel((200, 300)), FOND, 2) for s in F), str(v))
    F = images(tpl([reg("im", "image_slot", 150, 150, 100, 100, slot_name="pic", animation={"in": {"type": "slide_left", "duration": 1, "delay": 0.5, "easing": "linear"},
                                                                                           "out": {"type": "slide_down", "duration": 1, "delay": 0, "easing": "linear"}})]), (0.2, 1.0, 2.0, 3.5))
    rouge = lambda im: [x for x in range(0, 400, 2) for y in range(150, 250, 4) if im.getpixel((x, y))[0] > 200 and im.getpixel((x, y))[1] < 60]
    rouge_y = lambda im: [y for y in range(0, 400, 2) for x in range(150, 250, 4) if im.getpixel((x, y))[0] > 200 and im.getpixel((x, y))[1] < 60]
    g = {s: rouge(F[s]) for s in F}
    check("A2 GLISSEMENT : « slide_left » entre par la DROITE (hors toile au depart, a mi-chemin a droite de sa place), puis sa place ; « slide_down » sort par le BAS",
          not g[0.2] and min(g[1.0]) > 190 and min(g[2.0]) in range(146, 156) and min(rouge_y(F[3.5])) > 270,
          f"{min(g[1.0]) if g[1.0] else None} {min(g[2.0]) if g[2.0] else None} {min(rouge_y(F[3.5])) if rouge_y(F[3.5]) else None}")
    F2 = images(tpl([reg("im", "image_slot", 150, 150, 100, 100, slot_name="pic", animation={"in": {"type": "slide_left", "duration": 1, "delay": 0.5}})]), (1.0,))
    gd = rouge(F2[1.0])
    check("A2b la courbe DOUCE par defaut (ease_out) avance vite au debut : a mi-temps, la case est bien plus pres de sa place qu'en lineaire",
          gd and min(gd) < 200 and min(gd) < min(g[1.0]) - 60, f"{min(gd) if gd else None} vs lineaire {min(g[1.0]) if g[1.0] else None}")
    F = images(tpl([reg("st", "sticker", 40, 40, 160, 160, image_src="bleu.png", animation={"in": {"type": "pop", "duration": 1, "delay": 0.5, "easing": "linear"},
                                                                                      "out": {"type": "pop", "duration": 1, "delay": 0, "easing": "linear"}})], d=5), (0.4, 1.0, 2.0, 4.6))
    bleu = lambda im: [(x, y) for x in range(0, 400, 2) for y in range(0, 400, 2) if im.getpixel((x, y))[2] > 200 and im.getpixel((x, y))[0] < 60]
    def larg(pts):
        return (max(p[0] for p in pts) - min(p[0] for p in pts), (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2) if pts else (0, 0)
    w1, c1 = larg(bleu(F[1.0])); w2, c2 = larg(bleu(F[2.0])); w3, c3 = larg(bleu(F[4.6]))
    check("A3 POP : invisible avant, a mi-course a peu pres a la moitie de sa taille et CENTRE sur sa case (hors du centre de la toile), puis a sa taille ; en SORTIE il retrecit vers son centre",
          not bleu(F[0.4]) and 55 < w1 < 105 and abs(c1 - 120) <= 4 and 150 <= w2 <= 162 and abs(c2 - 120) <= 3 and 20 < w3 < 90 and abs(c3 - 120) <= 4,
          f"{w1} {c1} {w2} {c2} {w3} {c3}")
    F = images(tpl([reg("st", "sticker", 100, 100, 200, 200, image_src="bleu.png", animation={"in": {"type": "pop", "duration": 1, "delay": 0.5, "easing": "back"}})]), (1.1, 2.0))
    wb, _ = larg(bleu(F[1.1])); wf, _ = larg(bleu(F[2.0]))
    check("A4 la courbe « back » DEPASSE la taille finale avant de revenir (rebond)", wb > wf + 6, f"{wb} > {wf}")
    F = images(tpl([reg("bd", "badge", 100, 300, 200, 70, text="X", background_color="#e0004d", bg_opacity=1,
                        animation={"in": {"type": "slide_up", "duration": 0.6, "delay": 1.2, "easing": "back"}})], h=400), (0.0,))
    roses = [y for y in range(300, 400) if any(F[0.0].getpixel((x, y))[0] > 120 for x in range(0, 400, 2))]
    check("A8 AVANT son entree, une region qui glisse est ENTIEREMENT hors champ, meme avec la courbe « back » (position arrondie, pas tronquee)",
          not roses, str(roses))
    TT = tpl([reg("tx", "text", 20, 20, 360, 60, text="TITRE", size=40, color="#ffffff", animation=A("fade")),
              reg("tf", "text", 20, 90, 360, 60, text="EFFETS", size=40, color="#ffffff", text_effects={"box": {"color": "#ff00ff", "opacity": 1, "radius": 10}}, animation=A("fade")),
              reg("bd", "badge", 20, 160, 200, 60, text="LIVE", background_color="#00ffff", bg_opacity=1, animation=A("fade")),
              reg("bs", "brand_strip", 0, 240, 400, 40, background_color="#0000ff", animation=A("fade")),
              reg("tk", "ticker", 0, 290, 400, 40, text="DEFILE", speed=60, background_color="#ffff00", animation=A("fade")),
              reg("im", "image_slot", 240, 160, 100, 100, slot_name="pic", mask={"shape": "rounded", "radius": 20, "border_px": 6, "border_color": "#00ff00"}, animation=A("fade"))])
    F = images(TT, (0.5, 2.5))
    pts = {"texte": (lambda im: sum(1 for x in range(20, 380, 2) for y in range(20, 80, 2) if sum(im.getpixel((x, y))) > 600)),
           "texte a effets (image)": (lambda im: sum(1 for x in range(20, 380, 2) for y in range(90, 150, 2) if im.getpixel((x, y))[0] > 200 and im.getpixel((x, y))[2] > 200 and im.getpixel((x, y))[1] < 80)),
           "badge": (lambda im: sum(1 for x in range(20, 220, 4) for y in range(160, 220, 4) if im.getpixel((x, y))[1] > 200 and im.getpixel((x, y))[2] > 200 and im.getpixel((x, y))[0] < 80)),
           "bandeau": (lambda im: sum(1 for x in range(0, 400, 8) if im.getpixel((x, 260))[2] > 200 and im.getpixel((x, 260))[0] < 60)),
           "ticker": (lambda im: sum(1 for x in range(0, 400, 8) if im.getpixel((x, 295))[0] > 200 and im.getpixel((x, 295))[1] > 200 and im.getpixel((x, 295))[2] < 80)),
           "case": (lambda im: sum(1 for x in range(260, 320, 4) for y in range(180, 240, 4) if im.getpixel((x, y))[0] > 200 and im.getpixel((x, y))[1] < 60)),
           "lisere": (lambda im: sum(1 for x in range(236, 344, 2) for y in range(156, 264, 2) if im.getpixel((x, y))[1] > 200 and im.getpixel((x, y))[0] < 80 and im.getpixel((x, y))[2] < 80))}
    av = {k: f(F[0.5]) for k, f in pts.items()}; ap = {k: f(F[2.5]) for k, f in pts.items()}
    check("A5 TOUTES les regions visibles s'animent : texte, texte a effets (image), badge, bandeau, ticker, case video/image ET son liseré — absents avant, presents apres",
          all(v == 0 for v in av.values()) and all(v > 3 for v in ap.values()), f"avant={av} apres={ap}")
    check("A6 la couche est TRANSPARENTE hors de ce qu'elle dessine (le fond reste au pixel), avant comme apres",
          all(proche(F[s].getpixel((390, 390)), FOND, 2) and proche(F[s].getpixel((385, 230)), FOND, 2) for s in F), str([F[s].getpixel((390, 390)) for s in F]))
    from app.services import template_still as TS
    D = _tmp / "outputs" / "_tmp_still"
    a1 = Image.open(io.BytesIO(TS.rendre(E, tpl([reg("sp", "separator", 0, 20, 400, 20, color="#00ff00", animation=A("slide_right"))]), 3.0, "png", D))).convert("RGB")
    a0 = Image.open(io.BytesIO(TS.rendre(E, tpl([reg("sp", "separator", 0, 20, 400, 20, color="#00ff00", animation=A("slide_right"))]), 0.2, "png", D))).convert("RGB")
    a2 = Image.open(io.BytesIO(TS.rendre(E, tpl([reg("st", "sticker", 100, 100, 200, 200, image_src="bleu.png", animation=A("fade"))]), 3.0, "png", D))).convert("RGB")
    check("A7b en image fixe, ce qui est SUPERPOSE sur la couche (sticker) garde sa couleur exacte (couche en RGBA, pas en yuva sous-echantillonne)",
          a2.getpixel((200, 200)) == (0, 0, 255), str(a2.getpixel((200, 200))))
    check("A7 l'IMAGE FIXE (composee en RGB) suit l'animation : absente avant, couleur EXACTE apres",
          a1.getpixel((200, 30)) == (0, 255, 0) and a0.getpixel((200, 30)) == FOND and a1.getpixel((200, 300)) == FOND, f"{a0.getpixel((200, 30))} {a1.getpixel((200, 30))}")
else:
    check("A0 module et ffmpeg presents", False)

print("\n[C] la chaine de filtres")
if TA:
    fl, x, y = TA.chaine(TA.normaliser({"animation": {"in": {"type": "slide_up", "duration": 1}, "out": {"type": "slide_left", "duration": 1, "delay": 1}}}),
                         "ly1", "la1", (100, 200, 50, 50), (400, 400), 5)
    check("C1 un glissement sans fondu ni pop ne filtre pas la couche (null) ; x et y sont des fonctions de t ; entree par le bas, sortie vers la gauche",
          fl == ["[ly1]null[la1]"] and y.startswith("round(0+(200*") and x.startswith("round(0+(-150*") and "clip((t-0)/1,0,1)" in y and "clip((t-3)/1,0,1)" in x, f"{fl} {x} {y}")

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
