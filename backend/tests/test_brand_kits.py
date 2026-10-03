# -*- coding: utf-8 -*-
"""Plan-templates T1 (tache #72 du suivi, PR A, 03/10/2026) — PLUSIEURS kits de marque, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : Reglages -> Branding modifie le kit ACTIF (les quatre routes /branding deviennent
sa vue, un logo par kit) ; un rendu FIGE le kit actif a l'envoi ; on ne supprime ni le kit actif ni le dernier.
Ce que le plan faisait faux, et que ce banc garde : il ne reecrivait que la LECTURE de /branding — l'ecran Branding
aurait ecrit dans un fichier que plus personne ne lit ; pas de logo par kit ; un jeton inconnu passait a ffmpeg ; un
kits.json illisible etait ecrase au premier enregistrement (kits perdus) ; le kit etait lu au rendu, pas a l'envoi.
Banc-miroir pour la couleur : deux kits, deux MP4, deux pixels LUS. Data-dir isole, cles de banc, rien de paye.
Temoin positif : la base (3203828a) n'a ni le module ni les routes.
Run (depuis backend/) : & $PY tests/test_brand_kits.py"""
import asyncio, io, json, os, pathlib, shutil, subprocess, sys, tempfile, time, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzkits_"))
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


BASE = "3203828a"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/brand_kits.py"], capture_output=True, cwd=str(RACINE))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a ni le module ni les routes de kits", r0.returncode != 0 and r1.returncode == 0 and b'"/brand-kits"' not in r1.stdout)

from PIL import Image                                               # noqa: E402
BR = _tmp / "assets" / "branding"
BR.mkdir(parents=True, exist_ok=True)
(BR / "branding.json").write_text(json.dumps({"app_name": "ACME", "brand_color": "#112233", "intrus": "x"}), encoding="utf-8")
Image.new("RGBA", (40, 40), (200, 10, 10, 255)).save(BR / "logo.png")
AVANT = ((BR / "branding.json").read_bytes(), (BR / "logo.png").read_bytes())

try:
    from app.services import brand_kits as BK                       # noqa: E402
except ImportError as e:
    BK = None
    check("T2 le module existe", False, str(e))

print("[M] la migration")
if BK:
    doc = BK.lire()
    k0 = doc["kits"].get("deepotus", {})
    check("M1 le kit d'avant devient « deepotus » (ses champs, pas l'intrus), ACTIF ; son logo est COPIE ; les originaux restent",
          doc["actif"] == "deepotus" and k0.get("app_name") == "ACME" and k0.get("brand_color") == "#112233" and "intrus" not in k0
          and (BR / "logos" / "deepotus.png").read_bytes() == AVANT[1]
          and ((BR / "branding.json").read_bytes(), (BR / "logo.png").read_bytes()) == AVANT, str(doc))
    b1 = (BR / "kits.json").read_bytes(); BK.lire(); BK.actif()
    check("M2 idempotente : relire ne reecrit rien", (BR / "kits.json").read_bytes() == b1)
    BK.enregistrer({"name": "Client"})
    (BR / "kits.json").write_text("{pas du json", encoding="utf-8")
    doc2 = BK.lire()
    cote = sorted(BR.glob("kits.json.illisible-*"))
    check("M3 kits.json ILLISIBLE : mis de cote (contenu intact), jamais ecrase ; les kits repartent de la migration",
          len(cote) == 1 and cote[0].read_text(encoding="utf-8") == "{pas du json" and list(doc2["kits"]) == ["deepotus"], str([c.name for c in cote]))
    time.sleep(1.1)
    (BR / "kits.json").write_text(json.dumps({"actif": "x", "kits": {"mauvais id": {}}}), encoding="utf-8")
    BK.lire()
    check("M4 structure invalide (id interdit) : mise de cote aussi", len(sorted(BR.glob("kits.json.illisible-*"))) == 2)

print("\n[K] le service")
if BK:
    kc = BK.enregistrer({"name": "Client", "accent_color": "#ff8800", "app_name": "  " + "Y" * 80})
    vc = {k["id"]: k for k in BK.lister()}[kc]
    check("K1 creer : id kit_xxxxxxxx, defauts deepotus + ce qui est donne, nettoye et tronque a 60 (comme v1.11)",
          kc.startswith("kit_") and len(kc) == 12 and vc["accent_color"] == "#ff8800" and vc["brand_color"] == "#ef4444"
          and vc["app_name"] == "Y" * 60 and vc["name"] == "Client" and vc["actif"] is False and vc["logo"] is False, str(vc))
    errs = []
    for champs in ({"id": kc, "accent_color": "bleu"}, {"id": "mon kit"}):
        try:
            BK.enregistrer(champs); errs.append(None)
        except ValueError as e:
            errs.append(str(e))
    check("K2 refus qui le DISENT : couleur hors #RRGGBB, identifiant interdit", errs[0] and "#RRGGBB" in errs[0] and errs[1] and "identifiant" in errs[1], str(errs))
    Image.new("RGBA", (8, 8), (0, 0, 255, 255)).save(BR / "logos" / f"{kc}.png")
    kd = BK.dupliquer(kc)
    vd = {k["id"]: k for k in BK.lister()}[kd]
    check("K3 dupliquer : champs et logo copies, nom « (copie) »", vd["accent_color"] == "#ff8800" and vd["name"] == "Client (copie)"
          and (BR / "logos" / f"{kd}.png").read_bytes() == (BR / "logos" / f"{kc}.png").read_bytes())
    BK.activer(kc)
    rs = [BK.supprimer("absent"), BK.supprimer(kc), BK.supprimer(kd)]
    check("K4 supprimer : inconnu « absent », le kit ACTIF refuse, un autre part AVEC son logo", rs == ["absent", "actif", "supprime"]
          and not (BR / "logos" / f"{kd}.png").exists(), str(rs))
    BK.activer("deepotus"); BK.supprimer(kc)
    check("K5 le DERNIER kit ne se supprime pas", BK.supprimer("deepotus") == "seul" and list(BK.lire()["kits"]) == ["deepotus"])
    try:
        BK.activer("fantome"); e5 = None
    except ValueError as e:
        e5 = str(e)
    check("K6 activer un kit inconnu : refus qui le nomme", e5 and "fantome" in e5, str(e5))
    kr = BK.enregistrer({"name": "Remis", "accent_color": "#123456"})
    Image.new("RGBA", (8, 8), (0, 255, 0, 255)).save(BR / "logos" / f"{kr}.png")
    BK.reinitialiser(kr)
    vr = {k["id"]: k for k in BK.lister()}[kr]
    check("K7 reinitialiser : les six champs aux defauts, le logo retire, le NOM garde", vr["accent_color"] == "#00e5ff" and vr["name"] == "Remis"
          and vr["logo"] is False, str(vr))
    tpl = {"canvas": {"background_color": "{{brand.brand_color}}"}, "regions": [{"text": "{{ brand.app_name }} — {{brand.tagline_1}}"}]}
    a = BK.appliquer(tpl, BK.actif())
    try:
        BK.appliquer({"x": "{{brand.police}} {{brand.ombre}}"}); e8 = None
    except ValueError as e:
        e8 = str(e)
    from app.services.template_service import TemplateEngine        # noqa: E402
    sans = {"regions": [{"color": "#000000"}]}
    check("K8 jetons remplaces (espaces toleres) ; jeton INCONNU refuse en le nommant ; sans jeton, le gabarit est rendu TEL QUEL (meme objet)",
          a == {"canvas": {"background_color": "#112233"}, "regions": [{"text": "ACME — From the deep,"}]} and tpl["canvas"]["background_color"] == "{{brand.brand_color}}"
          and e8 and "{{brand.ombre}}" in e8 and "{{brand.police}}" in e8 and TemplateEngine().resoudre(sans) is sans, f"{a} {e8}")

print("\n[R] les routes")
from fastapi.testclient import TestClient                           # noqa: E402
from fastapi import HTTPException                                   # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import app.api.routes as RT                                         # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
VUS = []


async def _faux_rendu(**kw):
    VUS.append(kw)
RT.pipeline.render_template = _faux_rendu


def png(coul):
    b = io.BytesIO(); Image.new("RGB", (16, 16), coul).save(b, format="PNG"); return b.getvalue()


with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    if BK:
        for k in list(BK.lire()["kits"]):
            if k != "deepotus":
                BK.activer("deepotus"); BK.supprimer(k)
    g = c.get("/api/branding").json()
    check("R1 GET /branding = le kit ACTIF sous la forme de v1.11 (six champs, has_custom_logo, is_default) + kit_id/kit_name",
          g.get("app_name") == "ACME" and g.get("kit_id") == "deepotus" and g.get("kit_name") == "Deepotus" and g.get("has_custom_logo") is True
          and g.get("is_default") is False and set(g) == set(RT.BRAND_DEFAULTS) | {"has_custom_logo", "is_default", "kit_id", "kit_name"}, str(g))
    kc = c.post("/api/brand-kits", json={"name": "Client", "accent_color": "#ff8800"}).json().get("kit_id")
    r = c.post("/api/branding", json={"app_name": "  Studio Nord  ", "brand_color": "#0a0b0c", "intrus": "x"})
    kits = {k["id"]: k for k in c.get("/api/brand-kits").json()["kits"]}
    check("R2 « Enregistrer » de Reglages -> Branding modifie le kit ACTIF (et lui seul) ; l'ancien branding.json n'est plus ecrit",
          r.status_code == 200 and r.json().get("app_name") == "Studio Nord" and kits["deepotus"]["brand_color"] == "#0a0b0c"
          and kits[kc]["app_name"] == "DEEPOTUS" and (BR / "branding.json").read_bytes() == AVANT[0], r.text[:200])
    r3 = c.post("/api/branding", json={"accent_color": "cyan"})
    check("R3 couleur invalide : 400 qui le dit", r3.status_code == 400 and "#RRGGBB" in r3.json().get("detail", ""), r3.text[:150])
    up = c.post(f"/api/brand-kits/{kc}/logo", files={"file": ("l.png", png((1, 2, 3)), "image/png")})
    lg = c.get("/api/branding/logo")
    c.post("/api/brand-kits/" + kc + "/activate")
    lg2 = c.get("/api/branding/logo")
    lk = c.get(f"/api/brand-kits/{kc}/logo")
    check("R4 un logo PAR kit : /branding/logo sert celui du kit ACTIF ; changer de kit change le logo servi",
          up.status_code == 200 and lg.content == (BR / "logos" / "deepotus.png").read_bytes()
          and lg2.content == (BR / "logos" / f"{kc}.png").read_bytes() == lk.content and lg.content != lg2.content, f"{up.status_code}")
    c.post("/api/branding/logo", files={"file": ("n.webp", png((9, 9, 9)), "image/webp")})
    br = c.get("/api/branding").json()
    check("R5 activer change /branding (le shell suit) ; le logo envoye par Reglages va au kit ACTIF",
          br.get("kit_id") == kc and br.get("accent_color") == "#ff8800" and br.get("has_custom_logo") is True
          and Image.open(BR / "logos" / f"{kc}.png").getpixel((0, 0))[:3] == (9, 9, 9), str(br))
    rr = c.post("/api/branding", json={"reset": True})
    check("R6 « Reinitialiser » : le kit ACTIF seul revient aux defauts, logo retire ; l'autre kit garde tout",
          rr.json().get("kit_id") == kc and rr.json().get("accent_color") == "#00e5ff" and rr.json().get("has_custom_logo") is False
          and rr.json().get("is_default") is True and not (BR / "logos" / f"{kc}.png").exists()
          and (BR / "logos" / "deepotus.png").exists() and {k["id"]: k for k in c.get("/api/brand-kits").json()["kits"]}["deepotus"]["app_name"] == "Studio Nord")
    dup = c.post("/api/brand-kits/deepotus/dupliquer").json().get("kit_id")
    ren = c.post("/api/brand-kits", json={"id": dup, "name": "Variante"})
    errs = [c.delete(f"/api/brand-kits/{kc}"), c.delete("/api/brand-kits/fantome"), c.post("/api/brand-kits/fantome/activate"),
            c.post("/api/brand-kits", json={"id": "fantome", "name": "x"}), c.get("/api/brand-kits/fantome/logo"),
            c.post("/api/brand-kits", json={"name": "x", "brand_color": "rouge"})]
    check("R7 dupliquer, renommer ; refus : supprimer l'actif (400 qui dit quoi faire), kit inconnu (404 partout), couleur (400)",
          dup and ren.status_code == 200 and {k["id"]: k for k in ren.json()["kits"]}[dup]["name"] == "Variante"
          and [e.status_code for e in errs] == [400, 404, 404, 404, 404, 400] and "activez-en un autre" in errs[0].json()["detail"],
          str([e.status_code for e in errs]))
    c.post("/api/brand-kits/deepotus/activate")
    d1 = c.delete(f"/api/brand-kits/{dup}"); d2 = c.delete(f"/api/brand-kits/{kc}")
    d3 = c.delete("/api/brand-kits/deepotus")
    check("R8 les autres se suppriment ; le DERNIER est refuse (400 qui le dit)", d1.status_code == 200 and d2.status_code == 200
          and d3.status_code == 400 and "dernier" in d3.json()["detail"], f"{d1.status_code} {d2.status_code} {d3.text[:120]}")
    kc = c.post("/api/brand-kits", json={"name": "Client", "accent_color": "#ff8800"}).json()["kit_id"]
    c.post(f"/api/brand-kits/{kc}/activate")
    TPLJ = {"id": "tpl_kit", "name": "kit", "canvas": {"width": 240, "height": 320, "background_color": "#101010", "fps": 10, "duration_s": 1},
            "regions": [{"id": "sep", "type": "separator", "x": 0, "y": 100, "width": 240, "height": 120, "z_index": 1, "color": "{{brand.accent_color}}"}]}
    VUS.clear()
    rf = c.post("/api/layout-templates/tpl_kit/render", json={"template_id": "tpl_kit", "slot_values": {}, "template": TPLJ})
    c.post("/api/brand-kits/deepotus/activate")
    fige = VUS[0]["template"] if VUS else {}
    check("R9 FIGE A L'ENVOI : le pipeline recoit le gabarit DEJA resolu avec le kit actif au moment de l'envoi (#ff8800)",
          rf.status_code == 200 and fige.get("regions", [{}])[0].get("color") == "#ff8800" and TPLJ["regions"][0]["color"] == "{{brand.accent_color}}",
          f"{rf.status_code} {rf.text[:150]} {fige}")
    VUS.clear()
    rb = c.post("/api/layout-templates/tpl_kit/render", json={"template_id": "tpl_kit", "slot_values": {}, "template": {**TPLJ, "name": "{{brand.police}}"}})
    sans = dict(TPLJ); sans["regions"] = [dict(TPLJ["regions"][0], color="#00ff00")]
    rs = c.post("/api/layout-templates/tpl_kit/render", json={"template_id": "tpl_kit", "slot_values": {}, "template": sans})
    check("R10 jeton inconnu : 400 qui le nomme, rien ne part ; gabarit SANS jeton : transmis tel quel",
          rb.status_code == 400 and "{{brand.police}}" in rb.json().get("detail", "") and len(VUS) == 1 and VUS[0]["template"] == sans, f"{rb.text[:150]} {len(VUS)}")
try:
    asyncio.run(RT.activate_brand_kit("deepotus", types.SimpleNamespace(client=types.SimpleNamespace(host="10.0.0.7"))))
    _st = 200
except HTTPException as e:
    _st = e.status_code
check("R11 les routes d'ecriture refusent elles-memes un client distant (403)", _st == 403, str(_st))

print("\n[V] banc-miroir : deux kits, deux MP4, deux couleurs LUES")
if BK and shutil.which("ffmpeg"):
    from app.services.template_service import TemplateEngine        # noqa: E402
    eng, out, pix = TemplateEngine(), _tmp / "outputs", []
    for kid, nom in (("deepotus", "a"), (kc, "b")):
        BK.activer(kid)
        tpl = json.loads(json.dumps(TPLJ))
        mp4 = eng.render("tpl_kit", {}, out / f"kit_{nom}.mp4", template=tpl)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-frames:v", "1", str(out / f"kit_{nom}.png")], check=True)
        pix.append(Image.open(out / f"kit_{nom}.png").convert("RGB").getpixel((120, 160)))
    proche = lambda p, h: all(abs(p[i] - int(h[1 + 2 * i:3 + 2 * i], 16)) <= 14 for i in range(3))
    check("V1 le MEME gabarit rendu sous deux kits : #00e5ff puis #ff8800, lus au pixel du MP4", proche(pix[0], "#00e5ff") and proche(pix[1], "#ff8800"), str(pix))
else:
    check("V1 ffmpeg disponible pour le banc-miroir", False, "ffmpeg introuvable")

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
