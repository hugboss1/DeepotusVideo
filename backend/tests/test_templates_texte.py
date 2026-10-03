# -*- coding: utf-8 -*-
"""Plan-templates T4 (tache #74 du suivi, PR C, 03/10/2026) — TEXTE ADAPTATIF et EFFETS (textes, sous-titres, badges,
tickers), cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : couper en lignes PUIS reduire (taille mini reglable, « … » en dernier recours) ;
contour reglable, ombre nette ou floue, fond (coins arrondis), degrade ; SANS reglage, rendu IDENTIQUE au pixel.
Ce que le plan faisait faux, et que ce banc garde : il passait tout texte regle par une image — perdant le contour par
defaut, la pulsation et la position ; ici drawtext natif tant que possible (image seulement pour flou, degrade, fond
arrondi) ; il ne mesurait que la largeur (le texte debordait en hauteur) ; il ne coupait pas un mot trop long.
Preuve d'identite : SANS reglage, la commande ffmpeg (texte, badge pulse, ticker) est celle de la base a l'octet.
Banc-miroir : un long texte qui DEBORDE sans ajustement et TIENT avec ; fond, degrade, contour lus au pixel.
Temoin positif : la base (8fe5ab1e) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_templates_texte.py"""
import importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dztxt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
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


BASE = "8fe5ab1e"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_text.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a pas le module du texte adaptatif", r0.returncode != 0)
from PIL import Image                                               # noqa: E402
try:
    from app.services import template_text as TT                    # noqa: E402
except ImportError as e:
    TT = None
    check("T2 le module existe", False, str(e))
from app.services import template_service as TS                     # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
from app.services import template_layout as TL                      # noqa: E402
E = TemplateEngine()
POLICE = E.font_path(None)


def reg(i, t, x, y, w, h, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, w=400, h=400, bg="#101010"):
    return {"id": "tpl_t", "name": "t", "canvas": {"width": w, "height": h, "fps": 10, "duration_s": 1, "background_color": bg}, "regions": regions}


def erreur(r):
    try:
        E._validate(tpl([r])); return None
    except ValueError as e:
        return str(e)


print("[V] la validation")
if TT:
    tx = reg("t1", "text", 0, 0, 100, 50, text="x")
    cas = [reg("v1", "video_slot", 0, 0, 100, 100, slot_name="v", text_fit=True), dict(tx, text_fit="oui"), dict(tx, text_min_size=2),
           dict(tx, text_effects={"lueur": {}}), dict(tx, text_effects={"stroke": {"px": 99}}), dict(tx, text_effects={"shadow": {"opacity": 2}}),
           dict(tx, text_effects={"box": {"color": "rouge"}}), dict(tx, text_effects={"gradient": {"direction": "diagonale"}})]
    es = [erreur(c) for c in cas]
    check("V1 refus qui NOMMENT region et champ : type hors texte, text_fit non booleen, taille mini, effet inconnu, contour trop epais, opacite, couleur, sens du degrade",
          all(isinstance(e, str) for e in es) and "video_slot" not in es[0] and "text, text_slot, badge, ticker" in es[0] and "vrai ou faux" in es[1]
          and "6 et 400" in es[2] and "stroke, shadow, box, gradient" in es[3] and "stroke.px" in es[4] and "opacity" in es[5] and "#RRGGBB" in es[6]
          and "vertical ou horizontal" in es[7] and all("t1" in e for e in es[1:]), str(es))
    check("V2 un texte bien regle passe ; un texte SANS reglage aussi (rien a valider)", erreur(dict(tx, text_fit=True, text_min_size=14, text_effects={
        "stroke": {"px": 4, "color": "#00ff00"}, "shadow": {"dx": 3, "dy": 3, "blur": 6, "color": "#000000", "opacity": 0.7},
        "box": {"color": "#ff0000", "opacity": 0.8, "radius": 12, "pad": 10}, "gradient": {"c0": "#ffffff", "c1": "#00e5ff"}})) is None and erreur(tx) is None)

print("\n[A] l'ajustement")
if TT:
    t0, l0, tr0 = TT.ajuster("Court", POLICE, 40, 400, 200)
    long = "Le grand poulpe des profondeurs se leve lentement sur la ville endormie et regarde les toits"
    t1, l1, tr1 = TT.ajuster(long, POLICE, 40, 300, 600)
    pol1 = TT._police(POLICE, t1)
    check("A1 un texte court garde sa taille et tient sur une ligne ; un long passe A LA LIGNE (mots entiers) sans reduire s'il tient",
          (t0, l0, tr0) == (40, ["Court"], False) and t1 == 40 and len(l1) > 1 and not tr1 and all(pol1.getlength(l) <= 300 for l in l1)
          and " ".join(l1) == long, str(l1))
    t2, l2, tr2 = TT.ajuster(long, POLICE, 60, 300, 120, 12)
    pol2 = TT._police(POLICE, t2)
    def _tient(tt):
        pp = TT._police(POLICE, tt); ll = TT.couper(long, pp, 300)
        return len(ll) * TT.hauteur_ligne(pp) <= 120 and all(pp.getlength(l) <= 300 for l in ll)
    meilleure = max(tt for tt in range(12, 61) if _tient(tt))
    check("A2 trop haut : la taille BAISSE jusqu'a tenir en largeur ET en hauteur, sans reduire plus que necessaire (au moins 90 % de la plus grande taille qui tient)",
          t2 < 60 and len(l2) * TT.hauteur_ligne(pol2) <= 120 and not tr2 and all(pol2.getlength(l) <= 300 for l in l2) and t2 >= 0.9 * meilleure, f"{t2} / {meilleure} {l2}")
    t3, l3, tr3 = TT.ajuster(long * 4, POLICE, 40, 200, 60, 20)
    pol3 = TT._police(POLICE, t3)
    check("A3 a la taille MINIMALE, les lignes en trop partent et la derniere finit par « … » (dans la largeur)",
          t3 == 20 and tr3 and l3[-1].endswith("…") and len(l3) * TT.hauteur_ligne(pol3) <= 60 and pol3.getlength(l3[-1]) <= 200, f"{t3} {l3}")
    t4, l4, _ = TT.ajuster("Anticonstitutionnellement", POLICE, 40, 120, 400)
    t5, l5, _ = TT.ajuster("ligne un\nligne deux", POLICE, 30, 400, 400)
    check("A4 un mot plus large qu'une ligne est coupe a la lettre ; les sauts de ligne de l'auteur sont gardes",
          len(l4) > 1 and "".join(l4) == "Anticonstitutionnellement" and l5 == ["ligne un", "ligne deux"], f"{l4} {l5}")

print("\n[O] natif ou image")
if TT:
    o = TT.drawtext_options({"stroke": {"px": 5, "color": "#00ff00"}, "shadow": {"dx": 3, "dy": 4, "color": "#112233", "opacity": 0.5},
                             "box": {"color": "#ff0000", "opacity": 0.8, "pad": 9}})
    check("O1 contour, ombre NETTE et fond CARRE en drawtext natif", o == "borderw=5:bordercolor=0x00ff00:shadowx=3:shadowy=4:shadowcolor=0x112233@0.50:"
          "box=1:boxcolor=0xff0000@0.80:boxborderw=9", o)
    check("O2 image SEULEMENT pour l'ombre floue, le degrade et le fond arrondi", [TT.besoin_image(e) for e in (
        {}, {"stroke": {"px": 4}}, {"shadow": {"blur": 0}}, {"box": {"radius": 0}}, {"shadow": {"blur": 4}}, {"gradient": {}}, {"box": {"radius": 8}})]
          == [False, False, False, False, True, True, True])

print("\n[G] le graphe ffmpeg")
_sp = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
(_tmp / "ts_base.py").write_bytes(subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_service.py"], capture_output=True, cwd=str(RACINE)).stdout)
TSB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TSB)
SANS = tpl([reg("tx", "text_slot", 20, 20, 360, 80, slot_name="titre", default_text="Bonjour le monde", align="center", effect="pulse", size=40),
            reg("bd", "badge", 20, 120, 200, 60, text="LIVE", effect="pulse"), reg("tk", "ticker", 0, 300, 400, 60, text="Le ticker defile", speed=80)])
for _d in ("wa", "wb", "wc", "wd", "we", "wf"):
    (_tmp / _d).mkdir(exist_ok=True)   # le rendu cree son dossier de travail avant de construire la commande
ca = TS.build_ffmpeg_command(E, SANS, {}, _tmp / "outputs" / "a.mp4", _tmp / "wa")
cb = TSB.build_ffmpeg_command(E, SANS, {}, _tmp / "outputs" / "a.mp4", _tmp / "wb")   # le moteur (et ses polices) est le meme
cb = [str(x).replace(str(_tmp / "wb"), str(_tmp / "wa")) for x in cb]
check("G1 SANS reglage, la commande ffmpeg (texte centre pulse, badge pulse, ticker) est IDENTIQUE a celle de la base", [str(x) for x in ca] == cb,
      next((f"{x} != {y}" for x, y in zip(map(str, ca), cb) if x != y), "longueurs"))
if TT:
    AVEC = json.loads(json.dumps(SANS))
    AVEC["regions"][0].update(text_fit=True, default_text="Le grand poulpe des profondeurs se leve lentement sur la ville endormie")
    AVEC["regions"][1]["text_effects"] = {"stroke": {"px": 4, "color": "#00ff00"}}
    AVEC["regions"][2]["text_effects"] = {"gradient": {"c0": "#ff0000", "c1": "#0000ff"}}
    cc = " ".join(map(str, TS.build_ffmpeg_command(E, AVEC, {}, _tmp / "outputs" / "c.mp4", _tmp / "wc")))
    txts = sorted((_tmp / "wc").glob("*.txt"))
    contenus = [p.read_text(encoding="utf-8") for p in txts]
    import re as _re
    lignes_ta = _re.findall(r"drawtext=[^\[]*?x='20\+\(\(360\)-tw\)/2':y='(\d+)'[^\[]*\[ta\d+l(\d+)\]", cc)
    taille_ta = TT.ajuster(AVEC["regions"][0]["default_text"], POLICE, 40, 360, 80)[0]
    lh = TT.hauteur_ligne(TT._police(POLICE, taille_ta))
    check("G2 ajuste : PLUSIEURS lignes, UN drawtext centre par ligne, espacees de l'interligne de l'ajustement (drawtext espace a ~2,5x) ; "
          "contour et pulsation gardes ; le badge prend SON contour",
          len(lignes_ta) > 1 and [int(y) for y, _ in lignes_ta] == [20 + i * lh for i in range(len(lignes_ta))]
          and all(chr(10) not in c for c in contenus) and cc.count("alpha='0.5+0.5*sin(2*PI*t*1.0)'") == len(lignes_ta)
          and "borderw=4:bordercolor=0x00ff00" in cc and cc.count("borderw=3:bordercolor=0x02060d@0.65") == len(lignes_ta) and "text_align" not in cc,
          f"{lignes_ta} lh={lh} " + cc[-600:])
    EF = json.loads(json.dumps(SANS)); EF["regions"][0].update(default_text="Le grand poulpe des profondeurs se leve lentement sur la ville endormie",
                                                               text_effects={"stroke": {"px": 4, "color": "#00ff00"}})
    TS.build_ffmpeg_command(E, EF, {}, _tmp / "outputs" / "e.mp4", _tmp / "we")
    _ef = [p.read_text(encoding="utf-8") for p in (_tmp / "we").glob("*.txt")]
    check("G2b des EFFETS seuls (sans text_fit) n'ajustent rien : le long texte entier reste dans UN seul drawtext, sur UNE ligne",
          EF["regions"][0]["default_text"] in _ef, str(_ef))
    check("G3 le ticker a degrade passe par une IMAGE qui DEFILE (overlay a x anime), pas par drawtext", "tk" in cc and "mod(t*80.0," in cc
          and "overlay=x=" in cc and any(p.name.startswith("tk") for p in (_tmp / "wc").glob("*.png")), cc[-300:])
    PU = json.loads(json.dumps(SANS)); PU["regions"][1]["text_effects"] = {"box": {"color": "#ff0000", "radius": 10}}
    cp = " ".join(map(str, TS.build_ffmpeg_command(E, PU, {}, _tmp / "outputs" / "d.mp4", _tmp / "wd")))
    BL = json.loads(json.dumps(SANS)); BL["regions"][1].update(text="Edition speciale ce soir", text_fit=True, height=120, text_min_size=20, text_effects={"stroke": {"px": 2}})
    cl = " ".join(map(str, TS.build_ffmpeg_command(E, BL, {}, _tmp / "outputs" / "f.mp4", _tmp / "wf")))
    tb, lb, _ = TT.ajuster("Edition speciale ce soir", POLICE, 34, 200 - 60, 120 - 24, 20)   # case du badge : (rw - rh/2) x (rh - rh/5)
    lhb = TT.hauteur_ligne(TT._police(POLICE, tb))
    yb = [int(y) for y in _re.findall(r"y='(\d+)'[^\[]*\[bt\d+l\d+\]", cl)]
    check("G5 un badge ajuste sur plusieurs lignes : le BLOC est centre verticalement dans le badge (une ligne par drawtext)",
          len(lb) > 1 and yb == [132 + (96 - lhb * len(lb)) // 2 + i * lhb for i in range(len(lb))], f"{yb} {lb} lh={lhb}")
    check("G4 un badge PULSE en image garde sa pulsation (alpha anime par geq, en T)", "geq=r='r(X,Y)'" in cp and "sin(2*PI*T*1.2)" in cp, cp[-300:])

print("\n[R] banc-miroir : rendus, pixels lus")
FF = shutil.which("ffmpeg")


def rendre(nom, regions, bg="#101010"):
    mp4 = E.render("tpl_t", {}, _tmp / "outputs" / f"{nom}.mp4", template=tpl(regions, bg=bg))
    png = _tmp / "outputs" / f"{nom}.png"
    subprocess.run([FF, "-y", "-v", "error", "-i", str(mp4), "-frames:v", "1", str(png)], check=True)
    return Image.open(png).convert("RGB")


def boite(im, f):
    W, H = im.size
    pts = [(x, y) for y in range(H) for x in range(W) if f(im.getpixel((x, y)))]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else None


blanc = lambda p: p[0] > 200 and p[1] > 200 and p[2] > 200
if TT and FF:
    LONG = "Le grand poulpe des profondeurs se leve lentement sur la ville"
    sans = rendre("deborde", [reg("t", "text", 50, 100, 300, 200, text=LONG, size=40, color="#ffffff")])
    avec = rendre("tient", [reg("t", "text", 50, 100, 300, 200, text=LONG, size=40, color="#ffffff", text_fit=True)])
    b0, b1 = boite(sans, blanc), boite(avec, blanc)
    check("R1 SANS ajustement le texte DEBORDE de sa case (300 px) ; AVEC, toute son encre reste DANS la case (x 50..350, y 100..300)",
          b0 and b0[2] > 360 and b1 and b1[0] >= 46 and b1[2] <= 354 and b1[1] >= 96 and b1[3] <= 304, f"{b0} {b1}")
    fond = rendre("fond", [reg("t", "text", 50, 150, 300, 100, text="TEXTE", size=40, color="#ffffff", align="center",
                               text_effects={"box": {"color": "#ff0000", "opacity": 1, "radius": 16, "pad": 14}})])
    rouge = boite(fond, lambda p: p[0] > 180 and p[1] < 70 and p[2] < 70)
    check("R2 fond arrondi : une boite ROUGE derriere le texte, dans la case", rouge and rouge[0] >= 50 and rouge[2] <= 350 and rouge[3] - rouge[1] > 30, str(rouge))
    deg = rendre("degrade", [reg("t", "text", 20, 100, 360, 200, text="HAUT\nBAS", size=70, align="center",
                                 text_effects={"gradient": {"c0": "#ff0000", "c1": "#0000ff", "direction": "vertical"}})])
    hautes = [deg.getpixel((x, y)) for y in range(100, 170) for x in range(20, 380) if sum(deg.getpixel((x, y))) > 150]
    basses = [deg.getpixel((x, y)) for y in range(180, 260) for x in range(20, 380) if sum(deg.getpixel((x, y))) > 150]
    mr = lambda ps, i: sum(p[i] for p in ps) / max(1, len(ps))
    check("R3 degrade vertical : le haut du texte est plus ROUGE, le bas plus BLEU", hautes and basses and mr(hautes, 0) > mr(basses, 0) + 30
          and mr(basses, 2) > mr(hautes, 2) + 30, f"{mr(hautes, 0):.0f}/{mr(basses, 0):.0f} {mr(hautes, 2):.0f}/{mr(basses, 2):.0f}")
    _enc = [y for y in range(400) if any(sum(deg.getpixel((x, y))) > 150 for x in range(20, 380))]
    _rg = lambda y: [deg.getpixel((x, y)) for x in range(20, 380) if sum(deg.getpixel((x, y))) > 150]
    _part = lambda ps: sum(p[0] for p in ps) / max(1, sum(p[0] + p[2] for p in ps))
    _h, _b = _rg(_enc[0] + 1) if _enc else [], _rg(_enc[-1] - 1) if _enc else []
    check("R3b le degrade court de l'ENCRE du haut (pur c0) a celle du bas (pur c1)", _h and _b and _part(_h) > 0.9 and _part(_b) < 0.1,
          f"{_part(_h):.2f} {_part(_b):.2f}")
    ct = rendre("contour", [reg("t", "text", 50, 150, 300, 100, text="MOT", size=60, color="#ffffff", text_effects={"stroke": {"px": 6, "color": "#00ff00"}})])
    vert = boite(ct, lambda p: p[1] > 180 and p[0] < 90 and p[2] < 90)
    check("R4 contour natif de 6 px VERT autour des lettres", vert is not None and vert[2] - vert[0] > 40, str(vert))
    # R5 : trois lignes (sauts de l'auteur) ajustees, en drawtext natif — l'ecart entre les hauts des lettres = l'interligne
    trois = rendre("interligne", [reg("t", "text", 50, 40, 300, 330, text="HAUT\nHAUT\nHAUT", size=60, color="#ffffff", text_fit=True)])
    rangs = [y for y in range(400) if any(blanc(trois.getpixel((x, y))) for x in range(400))]
    hauts = [rangs[0]] + [rangs[i] for i in range(1, len(rangs)) if rangs[i] - rangs[i - 1] > 1] if rangs else []
    lh60 = TT.hauteur_ligne(TT._police(POLICE, 60))
    check("R5 lignes ajustees : l'ecart RENDU entre deux lignes est l'interligne calcule (pas les ~2,5x de drawtext), et tout tient dans la case",
          len(hauts) == 3 and all(abs((b - a) - lh60) <= 2 for a, b in zip(hauts, hauts[1:])) and rangs[-1] <= 372, f"{hauts} lh={lh60}")
    # R6 : badge a fond arrondi — le texte est CENTRE verticalement dans son fond (a 3 px pres)
    bdg = rendre("badge", [reg("b", "badge", 50, 100, 300, 160, text="EN DIRECT", size=40,   # assez haut : le fond n'est pas rogne
                               text_effects={"box": {"color": "#ff0000", "opacity": 1, "radius": 20, "pad": 16}})])
    fr = boite(bdg, lambda p: p[0] > 180 and p[1] < 70 and p[2] < 70)
    lettres = boite(bdg, lambda p: p[0] > 200 and p[1] > 200 and p[2] > 200)
    check("R6 badge a fond arrondi : le texte est au MILIEU de son fond ET du badge (encre centree a 2 px pres)", fr and lettres
          and abs((fr[1] + fr[3]) / 2 - (lettres[1] + lettres[3]) / 2) <= 2 and abs((lettres[1] + lettres[3]) / 2 - 180) <= 2, f"{fr} {lettres}")
else:
    check("R0 ffmpeg disponible pour le banc-miroir", False, "ffmpeg introuvable")

print("\n[L] le reagencement")
if TT:
    tl = tpl([reg("t", "text_slot", 100, 100, 600, 200, slot_name="s", text_min_size=20, text_effects={"stroke": {"px": 6}, "shadow": {"dx": 4, "dy": 8, "blur": 10},
              "box": {"radius": 12, "pad": 20}, "gradient": {"c0": "#ffffff", "c1": "#000000"}}), reg("u", "text", 100, 400, 400, 100, text="x")], 1080, 1920)
    o, _ = TL.reflow(tl, "16:9")
    s = min(1920 / 1080, 1080 / 1920)
    fx = o["regions"][0]["text_effects"]
    check("L1 reagence : taille mini, contour, ombre (decalage et flou) et fond (rayon, marge) suivent l'echelle ; le degrade ne bouge pas ; un « text » sans taille prend 48 a l'echelle",
          o["regions"][0]["text_min_size"] == round(20 * s) and fx["stroke"]["px"] == round(6 * s, 2) and fx["shadow"] == {"dx": round(4 * s, 2), "dy": round(8 * s, 2), "blur": round(10 * s, 2)}
          and fx["box"] == {"radius": round(12 * s, 2), "pad": round(20 * s, 2)} and fx["gradient"] == {"c0": "#ffffff", "c1": "#000000"}
          and o["regions"][1]["size"] == round(48 * s), str(o["regions"]))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
