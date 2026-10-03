# -*- coding: utf-8 -*-
"""Plan-templates T2 (tache #73 du suivi, PR A, 03/10/2026) — REAGENCER un gabarit dans un autre format, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : les grandes CASES suivent la toile en proportion (video recadree, jamais
deformee), les petits ELEMENTS gardent proportions et ancrage ; contrainte possible par region et par axe ; les TEXTES
suivent l'echelle de leur region ; une COPIE est enregistree apres un APERCU qui avertit (avatar HeyGen qui change de
format -> rendus epingles repayes).
Ce que le plan faisait faux, et que ce banc garde : il etirait chaque axe a part (un avatar 250x250 devenait 444x141),
ne touchait ni polices ni bandeau, et ajoutait une quatrieme copie de la table des formats sans garde.
Banc-miroir : un bandeau et un carre en coin, reagences en 16:9 puis RENDUS ; leurs pixels sont lus dans le MP4.
Temoin positif : la base (06438ed3) n'a ni le module ni les routes.
Run (depuis backend/) : & $PY tests/test_templates_reflow.py"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzreflow_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
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


BASE = "06438ed3"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_layout.py"], capture_output=True, cwd=str(RACINE))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a ni le module ni les routes de reagencement", r0.returncode != 0 and r1.returncode == 0
      and b'"/layout-templates/{template_id}/reflow"' not in r1.stdout)

try:
    from app.services import template_layout as TL                  # noqa: E402
except ImportError as e:
    TL = None
    check("T2 le module existe", False, str(e))
from app.services.template_service import TemplateEngine            # noqa: E402
E = TemplateEngine()
from app.services.quick_finish import CANVAS as QC                  # noqa: E402
from app.services.montage_service import _CANVAS as MC              # noqa: E402


def reg(i, t, x, y, w, h, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, w=1080, h=1920, **kw):
    return dict({"id": "tpl_banc", "name": "banc", "canvas": {"width": w, "height": h, "fps": 10, "duration_s": 1, "background_color": "#101010"},
                 "regions": regions}, **kw)


print("[F] les formats")
if TL:
    check("F1 la table des formats est la MEME que celles de Quick et du Montage (aucune derive)", TL.FORMATS == QC and all(MC.get(k) == v for k, v in TL.FORMATS.items()), str(TL.FORMATS))

print("\n[R] la regle")
if TL:
    s = min(1920 / 1080, 1080 / 1920)
    pip = E.get_template("tpl_pip_corner_avatar")
    src = {r["id"]: r for r in pip["regions"]}["r_pip"]
    out, av = TL.reflow(pip, "16:9")
    o = {r["id"]: r for r in out["regions"]}
    w1 = round(src["width"] * s)
    check("R1 une CASE plein ecran suit la toile (1920x1080)", (o["r_main"]["x"], o["r_main"]["y"], o["r_main"]["width"], o["r_main"]["height"]) == (0, 0, 1920, 1080), str(o["r_main"]))
    check("R2 un INSERT garde ses PROPORTIONS (carre -> carre) et son ancrage au coin, marges a l'echelle",
          o["r_pip"]["width"] == o["r_pip"]["height"] == w1 and o["r_pip"]["x"] == 1920 - round((1080 - src["x"] - src["width"]) * s) - w1
          and o["r_pip"]["y"] == 1080 - round((1920 - src["y"] - src["height"]) * s) - w1, f"{src} -> {o['r_pip']}")
    vs, _ = TL.reflow(E.get_template("tpl_classic_vstack_50_50"), "16:9")
    hs, _ = TL.reflow(E.get_template("tpl_hstack_left_right_dialogue"), "16:9")
    check("R3 des cases qui PAVENT l'ecran le pavent toujours (deux bandes, deux colonnes : ni trou ni chevauchement)",
          [(r["x"], r["y"], r["width"], r["height"]) for r in vs["regions"] if r["type"] != "audio_slot"] == [(0, 0, 1920, 540), (0, 540, 1920, 540)]
          and [(r["x"], r["y"], r["width"], r["height"]) for r in hs["regions"] if r["type"] != "audio_slot"] == [(0, 0, 960, 1080), (960, 0, 960, 1080)])
    t = tpl([reg("fond", "separator", 0, 0, 1080, 1920, color="#000000"), reg("mil", "text_slot", 300, 900, 480, 120, slot_name="t", size=40),
             reg("haut", "separator", 400, 10, 100, 100, color="#ffffff"),
             reg("f1", "separator", 100, 100, 200, 200, color="#ff0000", constraints={"h": "fin", "v": "debut"}),
             reg("f2", "separator", 100, 1500, 200, 100, color="#00ff00", constraints={"h": "etirer"})])
    tt, _ = TL.reflow(t, "16:9")
    q = {r["id"]: r for r in tt["regions"]}
    check("R4 un insert au milieu reste CENTRE (centre relatif garde) ; collé en haut reste en haut", abs(q["mil"]["x"] + q["mil"]["width"] / 2 - 960) <= 1
          and abs(q["mil"]["y"] + q["mil"]["height"] / 2 - 540 * 960 / 1920 * 2) <= 1 and q["haut"]["y"] == round(10 * s), f"{q['mil']} {q['haut']}")
    check("R5 les CONTRAINTES gagnent : h=fin (marge droite a l'echelle) / v=debut ; h=etirer (proportion de la toile)",
          q["f1"]["x"] == 1920 - round((1080 - 100 - 200) * s) - round(200 * s) and q["f1"]["y"] == round(100 * s)
          and (q["f2"]["x"], q["f2"]["width"]) == (round(100 * 1920 / 1080), round(200 * 1920 / 1080)) and q["f2"]["height"] == round(100 * s), f"{q['f1']} {q['f2']}")
    k_mil = min(q["mil"]["width"] / 480, q["mil"]["height"] / 120)
    t2 = tpl([reg("tx", "text_slot", 300, 900, 480, 120, slot_name="t"), reg("bd", "badge", 400, 400, 200, 80, radius=20),
              reg("bs", "brand_strip", 0, 1700, 1080, 160, items=[{"type": "mark", "x": 20, "y": 30, "scale": 0.5}, {"type": "text", "text": "X", "x": 180, "y": 60, "size": 36}])])
    t2o, _ = TL.reflow(t2, "16:9")
    z = {r["id"]: r for r in t2o["regions"]}
    kb = min(z["bs"]["width"] / 1080, z["bs"]["height"] / 160)
    check("R6 les TEXTES suivent l'echelle : taille explicite et implicite (48 du text_slot), rayon du badge, elements du bandeau (x, y, taille, echelle de la marque)",
          q["mil"]["size"] == max(8, round(40 * k_mil)) and z["tx"]["size"] == round(48 * s) and z["bd"]["radius"] == round(20 * s) and z["bd"]["size"] == round(34 * s)
          and z["bs"]["items"][1] == {"type": "text", "text": "X", "x": round(180 * kb), "y": round(60 * kb), "size": round(36 * kb)}
          and z["bs"]["items"][0]["scale"] == round(0.5 * kb, 4) and z["bs"]["items"][1]["y"] + z["bs"]["items"][1]["size"] <= z["bs"]["height"], str(z["bs"]))
    sq = E.get_template("tpl_three_act_sequential")
    sqo, sav = TL.reflow(sq, "1:1")
    check("R7 gabarit SEQUENTIEL : seule la toile change (ses actes se recadrent deja), et c'est DIT",
          sqo["regions"] == sq["regions"] and sqo["canvas"]["width"] == 1080 == sqo["canvas"]["height"] and sav and "séquentiel" in sav[0], str(sav))
    au = tpl([reg("v", "video_slot", 0, 0, 1080, 1920, slot_name="v"), {"id": "a", "type": "audio_slot", "slot_name": "a", "volume": 0.5}])
    check("R8 une piste audio n'est pas placee : intacte", TL.reflow(au, "1:1")[0]["regions"][1] == {"id": "a", "type": "audio_slot", "slot_name": "a", "volume": 0.5})
    tous, mauvais = 0, []
    for tid in ("tpl_alpha_reel_60_30_10", "tpl_classic_vstack_50_50", "tpl_hstack_left_right_dialogue", "tpl_news_reel",
                "tpl_oracle_full_with_lower_third", "tpl_pip_corner_avatar"):
        s0 = E.get_template(tid); avant = json.dumps(s0, sort_keys=True)
        for f in ("16:9", "1:1", "4:5"):
            oo, _ = TL.reflow(s0, f)
            try:
                E._validate(oo); tous += 1
            except ValueError as e:
                mauvais.append((tid, f, str(e)))
            W1, H1 = TL.FORMATS[f]
            if any(r.get("type") != "audio_slot" and (r["x"] + r["width"] > W1 or r["y"] + r["height"] > H1) for r in oo["regions"]):
                mauvais.append((tid, f, "hors toile"))
        if json.dumps(s0, sort_keys=True) != avant:
            mauvais.append((tid, "source modifiee"))
    check("R9 les SIX gabarits composes livres, dans les trois autres formats : valides, dans la toile, source intacte (18 sur 18)", tous == 18 and not mauvais, str(mauvais))
    try:
        E._validate(tpl([reg("r1", "separator", 0, 0, 10, 10, constraints={"h": "gauche"})])); e10 = None
    except ValueError as e:
        e10 = str(e)
    check("R10 une contrainte INVENTEE est refusee en nommant la region et le mode (par la validation de tout gabarit)", e10 and "r1" in e10 and "gauche" in e10, str(e10))
    hso, _ = TL.reflow(E.get_template("tpl_hstack_left_right_dialogue"), "16:9")
    w_hs = TL.avertissements_heygen(E.get_template("tpl_hstack_left_right_dialogue"), hso)
    w_pip = TL.avertissements_heygen(pip, out)
    check("R11 AVERTIT quand un avatar HeyGen change de format (colonnes 9:16 -> 1:1 : rendus epingles repayes) ; pas quand il le garde (coin carre)",
          len(w_hs) == 2 and all("9:16 à 1:1" in w and "payants" in w for w in w_hs) and w_pip == [], f"{w_hs} {w_pip}")

print("\n[W] les routes")
from fastapi.testclient import TestClient                           # noqa: E402
from fastapi import HTTPException                                   # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import app.api.routes as RT                                         # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    n0 = len(c.get("/api/layout-templates").json()["templates"])
    g = c.get("/api/layout-templates/tpl_hstack_left_right_dialogue/reflow", params={"format": "16:9"})
    gd = g.json() if g.status_code == 200 else {}
    check("W1 APERCU : le gabarit reagence et ses avertissements, RIEN d'enregistre", g.status_code == 200 and gd.get("template", {}).get("canvas", {}).get("width") == 1920
          and len(gd.get("warnings", [])) == 2 and len(c.get("/api/layout-templates").json()["templates"]) == n0, g.text[:200])
    rs = [c.get("/api/layout-templates/inconnu/reflow", params={"format": "1:1"}).status_code,
          c.get("/api/layout-templates/tpl_news_reel/reflow", params={"format": "21:9"}),
          c.get("/api/layout-templates/tpl_news_reel/reflow", params={"format": "9:16"})]
    check("W2 gabarit inconnu 404 ; format inconnu 400 (les formats dits) ; meme format 400 (« deja »)",
          rs[0] == 404 and rs[1].status_code == 400 and "4:5" in rs[1].json()["detail"] and rs[2].status_code == 400 and "déjà" in rs[2].json()["detail"], str(rs[0]))
    p = c.post("/api/layout-templates/tpl_pip_corner_avatar/reflow", json={"format": "1:1"})
    pd = p.json() if p.status_code == 200 else {}
    neuf = c.get(f"/api/layout-templates/{pd.get('template_id')}").json() if pd.get("template_id") else {}
    check("W3 ENREGISTRER : un NOUVEAU gabarit utilisateur « nom (1:1) », trace de son origine ; le livre est intact",
          p.status_code == 200 and str(pd.get("template_id", "")).startswith("tpl_user_") and neuf.get("name", "").endswith("(1:1)")
          and neuf.get("metadata", {}).get("reflow_de") == "tpl_pip_corner_avatar" and neuf.get("metadata", {}).get("format") == "1:1"
          and neuf.get("canvas", {}).get("height") == 1080
          and c.get("/api/layout-templates/tpl_pip_corner_avatar").json()["canvas"]["height"] == 1920
          and len(c.get("/api/layout-templates").json()["templates"]) == n0 + 1, p.text[:200])
    p2 = c.post("/api/layout-templates/tpl_news_reel/reflow", json={"format": "4:5", "name": "  Reel carre  "})
    check("W4 un nom donne est garde (nettoye) ; sans format : 400", p2.status_code == 200 and p2.json().get("name") == "Reel carre"
          and c.post("/api/layout-templates/tpl_news_reel/reflow", json={}).status_code == 400, p2.text[:150])
try:
    asyncio.run(RT.save_layout_reflow("tpl_news_reel", {"format": "1:1"}, types.SimpleNamespace(client=types.SimpleNamespace(host="10.0.0.7"))))
    _st = 200
except HTTPException as e:
    _st = e.status_code
check("W5 l'enregistrement refuse lui-meme un client distant (403)", _st == 403, str(_st))

print("\n[V] banc-miroir : reagence en 16:9 puis RENDU, pixels lus")
if TL and shutil.which("ffmpeg"):
    from PIL import Image                                           # noqa: E402
    tm = tpl([reg("bande", "separator", 0, 1720, 1080, 200, color="#ff0000"), reg("carre", "separator", 830, 1470, 200, 200, color="#00ff00")])
    tm["canvas"]["fps"] = 10
    om, _ = TL.reflow(tm, "16:9")
    mp4 = E.render("tpl_banc", {}, _tmp / "outputs" / "reflow.mp4", template=om)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-frames:v", "1", str(_tmp / "outputs" / "reflow.png")], check=True)
    im = Image.open(_tmp / "outputs" / "reflow.png").convert("RGB")
    W, H = im.size
    vert = [(x, y) for y in range(0, H, 2) for x in range(0, W, 2) if (lambda p: p[1] > 180 and p[0] < 80 and p[2] < 80)(im.getpixel((x, y)))]
    xs, ys = [v[0] for v in vert], [v[1] for v in vert]
    lw, lh = (max(xs) - min(xs) + 2, max(ys) - min(ys) + 2) if vert else (0, 0)
    rouge = lambda x, y: (lambda p: p[0] > 180 and p[1] < 80)(im.getpixel((x, y)))
    check("V1 le MP4 est en 16:9 ; le bandeau bord a bord en BAS couvre TOUTE la largeur ; le carre en coin reste CARRE et dans son coin",
          (W, H) == (1920, 1080) and rouge(5, H - 20) and rouge(W - 5, H - 20) and rouge(W // 2, H - 20) and not rouge(W // 2, H // 2)
          and vert and abs(lw - lh) <= 4 and min(xs) > W // 2 and min(ys) > H // 2, f"{(W, H)} carre {lw}x{lh} a {min(xs) if xs else None},{min(ys) if ys else None}")
else:
    check("V1 ffmpeg disponible pour le banc-miroir", False, "ffmpeg introuvable")

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
