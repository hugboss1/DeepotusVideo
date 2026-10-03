# -*- coding: utf-8 -*-
"""Plan-templates T11 / D4 (tache #76 du suivi, PR C, 03/10/2026) — TEXTE SUR ARC, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : un arc dessine par le serveur, lettre par lettre (le texte reste modifiable et
remplissable) ; un trace libre passe par le Vectorlab (texte sur chemin) pose en sticker — le serveur n'a pas de moteur
SVG. Champ : text_curve = {"radius": px, "dir": "haut" (arche) | "bas" (sourire)} sur text et text_slot.
Ce que le plan faisait faux : des noms qui n'existent pas (rendre_texte_png, _fonte, hauteur_ligne(chemin, taille)),
une route /layout-templates/fonts masquee par /{template_id}.
Preuve d'identite : un texte DROIT a effets donne une image identique au pixel a celle de la base.
Temoin positif : la base (9a515858) ne connait pas text_curve.
Run (depuis backend/) : & $PY tests/test_templates_courbe.py"""
import importlib.util, io, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcourbe_"))
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


BASE = "9a515858"
src0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_text.py"], capture_output=True, cwd=str(RACINE)).stdout
check("T1 temoin : la base ne connait pas le texte sur arc", b"text_curve" not in src0 and len(src0) > 1000)
from PIL import Image                                               # noqa: E402
from app.services import template_text as TT                        # noqa: E402
from app.services import template_service as TSV                    # noqa: E402
from app.services import template_layout as TL                      # noqa: E402
from app.services import template_still as TS                       # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
E = TemplateEngine()
POLICE = E.font_path(None)
D = _tmp / "outputs" / "_tmp_still"


def reg(i, t, x, y, w, h, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, w=600, h=600):
    return {"id": "tpl_c", "name": "c", "canvas": {"width": w, "height": h, "fps": 10, "duration_s": 2, "background_color": "#000000"}, "regions": regions}


def image(regions, w=600, h=600):
    return Image.open(io.BytesIO(TS.rendre(E, tpl(regions, w, h), 1.0, "png", D))).convert("RGB")


print("[I] l'identite : le texte droit ne change pas")
(_tmp / "tt_base.py").write_bytes(src0)
_sp = importlib.util.spec_from_file_location("tt_base", str(_tmp / "tt_base.py"))
TTB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TTB)
EFF = {"stroke": {"px": 4, "color": "#00ff00"}, "shadow": {"dx": 3, "dy": 5, "blur": 4, "opacity": 0.7}, "box": {"color": "#ff0000", "radius": 12, "pad": 8},
       "gradient": {"c0": "#ffffff", "c1": "#0000ff"}}
TT.rendre_png(["Deux lignes", "de texte"], POLICE, 40, "ffffff", EFF, 400, 200, "center", "middle", _tmp / "n.png")
TTB.rendre_png(["Deux lignes", "de texte"], POLICE, 40, "ffffff", EFF, 400, 200, "center", "middle", _tmp / "b.png")
check("I1 un texte DROIT a quatre effets donne une image identique au pixel a celle de la base",
      Image.open(_tmp / "n.png").tobytes() == Image.open(_tmp / "b.png").tobytes())
(_tmp / "wa").mkdir(); (_tmp / "wb").mkdir()
(_tmp / "ts_base.py").write_bytes(subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_service.py"], capture_output=True, cwd=str(RACINE)).stdout)
_sp2 = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
TSB = importlib.util.module_from_spec(_sp2); _sp2.loader.exec_module(TSB)
DROIT = tpl([reg("t", "text", 20, 20, 500, 100, text="Titre", size=40, text_effects={"stroke": {"px": 3}}), reg("u", "text_slot", 20, 200, 500, 200, slot_name="s",
             default_text="Long texte ajuste", text_fit=True)])
ca = [str(x) for x in TSV.build_ffmpeg_command(E, DROIT, {}, _tmp / "o.mp4", _tmp / "wa")]
cb = [str(x).replace(str(_tmp / "wb"), str(_tmp / "wa")) for x in TSB.build_ffmpeg_command(E, DROIT, {}, _tmp / "o.mp4", _tmp / "wb")]
check("I2 commande ffmpeg d'un gabarit SANS arc identique a la base", ca == cb, next((f"{x} != {y}" for x, y in zip(ca, cb) if x != y), "longueurs"))

print("\n[V] la validation")
def erreur(rg):
    try:
        E._validate(tpl([rg])); return None
    except ValueError as e:
        return str(e)
cas = [reg("r1", "badge", 0, 0, 100, 50, text="x", text_curve={"radius": 100}), reg("r1", "text", 0, 0, 100, 50, text="x", text_curve={"radius": 5}),
       reg("r1", "text", 0, 0, 100, 50, text="x", text_curve={"radius": 100, "dir": "gauche"}), reg("r1", "text", 0, 0, 100, 50, text="x", text_curve={"radius": 100, "angle": 3}),
       reg("r1", "text", 0, 0, 100, 50, text="x", text_curve={"radius": 100}, text_fit=True), reg("r1", "text", 0, 0, 100, 50, text="x", text_curve="arc")]
es = [erreur(c) for c in cas]
check("V1 refus qui NOMMENT la region et le champ : type (badge), rayon hors 20..20000, sens inconnu, cle inconnue, avec l'ajustement, pas un objet",
      all(es) and all("r1" in e for e in es) and "text et text_slot" in es[0] and "20 et 20000" in es[1] and "haut ou bas" in es[2]
      and "radius" in es[3] and "s'excluent" in es[4] and "radius" in es[5], str(es))
check("V2 un arc bien forme passe (sur text et text_slot)", erreur(reg("r1", "text", 0, 0, 100, 50, text="x", text_curve={"radius": 300, "dir": "bas"})) is None
      and erreur(reg("r1", "text_slot", 0, 0, 100, 50, slot_name="s", text_curve={"radius": 300})) is None)
check("V3 l'arc rend la region « active » et force l'image (lettre par lettre) ; sans arc, rien ne change",
      TT.actif({"text_curve": {"radius": 100}}) and TT.besoin_image({}, {"text_curve": {"radius": 100}}) and not TT.besoin_image({}, {})
      and not TT.actif({}) and TT.courbe({"text_curve": {"radius": 100}}) == (100.0, "haut") and TT.courbe({}) is None)

print("\n[C] les rendus, pixels lus")
blanc = lambda p: sum(p) > 500


def encre(im, x0, x1, y0=0, y1=None):
    y1 = y1 or im.height
    return [(x, y) for x in range(x0, x1, 2) for y in range(y0, y1, 2) if blanc(im.getpixel((x, y)))]


H = image([reg("t", "text", 50, 50, 500, 500, text="ARCHE EN HAUT DU CERCLE", size=48, color="#ffffff", text_curve={"radius": 250, "dir": "haut"})])
milieu, bords = encre(H, 280, 320), encre(H, 50, 130) + encre(H, 470, 550)
check("C1 « haut » : une ARCHE — au milieu l'encre est en haut, sur les bords elle descend",
      milieu and bords and max(y for _, y in milieu) < min(y for _, y in bords) + 40 and sum(y for _, y in milieu) / len(milieu) < sum(y for _, y in bords) / len(bords) - 60,
      f"{sum(y for _, y in milieu) / max(1, len(milieu)):.0f} vs {sum(y for _, y in bords) / max(1, len(bords)):.0f}")
B = image([reg("t", "text", 50, 50, 500, 500, text="SOURIRE EN BAS DU CERCLE", size=48, color="#ffffff", text_curve={"radius": 250, "dir": "bas"})])
milieu, bords = encre(B, 280, 320), encre(B, 50, 130) + encre(B, 470, 550)
check("C2 « bas » : un SOURIRE — au milieu l'encre est en bas, sur les bords elle remonte",
      milieu and bords and sum(y for _, y in milieu) / len(milieu) > sum(y for _, y in bords) / len(bords) + 60,
      f"{sum(y for _, y in milieu) / max(1, len(milieu)):.0f} vs {sum(y for _, y in bords) / max(1, len(bords)):.0f}")
tout = encre(H, 0, 600)
cx, cy = (min(x for x, _ in tout) + max(x for x, _ in tout)) / 2, (min(y for _, y in tout) + max(y for _, y in tout)) / 2
check("C3 l'arc est CENTRE dans sa case (a quelques px) et n'en sort pas", abs(cx - 300) <= 6 and abs(cy - 300) <= 12
      and min(x for x, _ in tout) >= 50 and max(x for x, _ in tout) <= 550, f"{cx:.0f},{cy:.0f}")
I = image([reg("t", "text", 50, 50, 500, 500, text="I            I", size=80, color="#ffffff", text_curve={"radius": 140, "dir": "haut"})])
def penche(x0, x1):   # x moyen de l'encre en haut de la lettre moins x moyen en bas
    pts = encre(I, x0, x1)
    if not pts:
        return None
    ya, yb = min(y for _, y in pts), max(y for _, y in pts)
    h_ = [x for x, y in pts if y < ya + (yb - ya) * 0.3]; b_ = [x for x, y in pts if y > yb - (yb - ya) * 0.3]
    return sum(h_) / max(1, len(h_)) - sum(b_) / max(1, len(b_))
pg, pd = penche(0, 300), penche(300, 600)
check("C6 chaque lettre PENCHE selon la tangente de l'arche : le I de gauche penche vers la gauche (haut a gauche), celui de droite vers la droite",
      pg is not None and pd is not None and pg < -8 and pd > 8, f"{pg} {pd}")
S_ = image([reg("t", "text", 50, 50, 500, 500, text="MMMMMMMMMMMM", size=48, color="#ffffff", text_curve={"radius": 200, "dir": "haut"})])
pts = encre(S_, 0, 600)
xg, xd = min(x for x, _ in pts), max(x for x, _ in pts)
yg = [y for x, y in pts if x < xg + 30]; yd = [y for x, y in pts if x > xd - 30]
check("C7 un texte regulier est SYMETRIQUE sur l'arc (chaque lettre prise en son milieu) : ses deux pieds a la meme hauteur, a 4 px pres",
      abs(sum(yg) / len(yg) - sum(yd) / len(yd)) <= 4 and abs((xg + xd) / 2 - 300) <= 4, f"{sum(yg) / len(yg):.1f} {sum(yd) / len(yd):.1f} {(xg + xd) / 2}")
G = image([reg("t", "text", 50, 50, 500, 500, text="DEGRADE ET CONTOUR", size=56, text_curve={"radius": 220},
               text_effects={"gradient": {"c0": "#ff0000", "c1": "#0000ff"}, "stroke": {"px": 4, "color": "#00ff00"}})])
vert = [1 for x in range(50, 550, 2) for y in range(50, 550, 2) if G.getpixel((x, y))[1] > 200 and G.getpixel((x, y))[0] < 80 and G.getpixel((x, y))[2] < 80]
haut_ = [G.getpixel((x, y)) for x in range(250, 350, 2) for y in range(50, 300, 2) if G.getpixel((x, y))[0] + G.getpixel((x, y))[2] > 200 and G.getpixel((x, y))[1] < 120]
bas_ = [G.getpixel((x, y)) for x in list(range(50, 150, 2)) + list(range(450, 550, 2)) for y in range(50, 550, 2) if G.getpixel((x, y))[0] + G.getpixel((x, y))[2] > 200 and G.getpixel((x, y))[1] < 120]
mr = lambda ps, i: sum(p[i] for p in ps) / max(1, len(ps))
check("C4 les EFFETS suivent la courbe : contour vert autour des lettres, degrade vertical (le sommet de l'arche plus rouge, les pieds plus bleus)",
      len(vert) > 30 and haut_ and bas_ and mr(haut_, 0) > mr(bas_, 0) + 20 and mr(bas_, 2) > mr(haut_, 2) + 20, f"{len(vert)} {mr(haut_, 0):.0f}/{mr(bas_, 0):.0f}")
cmd = " ".join(map(str, TSV.build_ffmpeg_command(E, tpl([reg("t", "text", 50, 50, 500, 500, text="ARC", size=48, text_curve={"radius": 250})]), {}, _tmp / "x.mp4", _tmp / "wa")))
check("C5 un texte sur arc passe par une IMAGE posee (pas par drawtext)", "drawtext" not in cmd and __import__("re").search(r"ta\d+\.png", cmd) is not None, cmd[-200:])

GR = image([reg("t", "text", 100, 200, 400, 150, text="UN TITRE BEAUCOUP TROP LONG POUR SA CASE", size=96, color="#ffffff", text_curve={"radius": 260})])
gp = encre(GR, 0, 600)
t_r = TT.taille_arc("UN TITRE BEAUCOUP TROP LONG POUR SA CASE", POLICE, 96, 400, 150, (260.0, "haut"), {})
check("C8 un arc TROP GRAND est REDUIT jusqu'a tenir dans sa case (decision 03/10) : l'encre reste dans la case, la taille baisse",
      gp and min(x for x, _ in gp) >= 103 and max(x for x, _ in gp) <= 497 and min(y for _, y in gp) >= 203 and max(y for _, y in gp) <= 347 and t_r < 96,
      f"{t_r} {min(x for x, _ in gp) if gp else None}-{max(x for x, _ in gp) if gp else None} / {min(y for _, y in gp) if gp else None}-{max(y for _, y in gp) if gp else None}")
BH = image([reg("t", "text", 0, 250, 600, 90, text="ARCHE SERREE", size=60, color="#ffffff", text_curve={"radius": 90})])
bh_ = encre(BH, 0, 600)
check("C8b la HAUTEUR compte aussi : une arche serree dans une case basse est reduite jusqu'a y tenir (l'encre ne TOUCHE pas les bords : rognee, elle les toucherait)",
      bh_ and min(y for _, y in bh_) >= 253 and max(y for _, y in bh_) <= 337, f"{min(y for _, y in bh_) if bh_ else None}-{max(y for _, y in bh_) if bh_ else None}")
ML = image([reg("t", "text", 100, 200, 400, 150, text="A\nSECONDE LIGNE BIEN PLUS LONGUE SUR L'ARC", size=80, color="#ffffff", text_curve={"radius": 400})])
ml = encre(ML, 0, 600)
check("C8c un texte sur PLUSIEURS lignes se pose en une seule ligne sur l'arc, et c'est TOUT le texte qui doit tenir",
      ml and min(x for x, _ in ml) >= 103 and max(x for x, _ in ml) <= 497, f"{min(x for x, _ in ml) if ml else None}-{max(x for x, _ in ml) if ml else None}")
check("C9 un arc qui TIENT garde sa taille ; la reduction s'arrete a la taille minimale", TT.taille_arc("OK", POLICE, 40, 500, 300, (300.0, "haut"), {}) == 40
      and TT.taille_arc("UN TITRE BEAUCOUP TROP LONG", POLICE, 96, 60, 30, (100.0, "haut"), {}, 30) == 30)

print("\n[L] le reagencement")
o, _ = TL.reflow(tpl([reg("t", "text", 100, 100, 800, 300, text="ARC", text_curve={"radius": 400, "dir": "bas"})], 1080, 1920), "16:9")
s = min(1920 / 1080, 1080 / 1920)
check("L1 le rayon de l'arc suit l'echelle du reagencement (le sens ne change pas)", o["regions"][0]["text_curve"] == {"radius": round(400 * s, 2), "dir": "bas"},
      str(o["regions"][0]["text_curve"]))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
