# -*- coding: utf-8 -*-
"""t206 (Espaces de marque E6, 13/10/2026) — l'IDENTITÉ VISUELLE d'un persona.
Ce que ce banc garde :
  - DEEPOTUS À L'OCTET : generate_from_intent rend, pour 160 cas (10 intentions × persona oui/non × 4 graines × 2
    styles), exactement ce que rendait le « DNA » codé en dur (figé avant t206 : tests/identite_adn_deepotus.json),
    sans identite.json puis APRÈS une écriture de sa palette ; le DNA n'est plus dans prompt_engine ;
  - un autre persona n'hérite RIEN de Deepotus : sans identité, aucune touche (« neutral environment », explication
    dite) ; avec un style écrit et une palette, ses descripteurs ; ses repères empêchent le doublon ; un ADN saisi
    l'emporte sur le dérivé ;
  - la doctrine : un nom d'artiste ou un « à la manière de » dans le style écrit ou l'ADN -> 400, RIEN d'écrit ;
    couleur, plafonds, champ inconnu -> 400 ;
  - les images : PNG normalisés par Pillow (un faux -> 400), plafonds (6 mascottes), le logo REMPLACE, copie de
    Bibliothèque refaite si elle disparaît, retrait, import depuis la Bibliothèque, aucun chemin hors liste servi ;
  - la planche : composée gratuitement (aucune dépense), à valider, validée, PÉRIMÉE quand l'identité change (valider
    une planche périmée -> 400) ;
  - les références passées aux modèles : retouche (`identite`) -> 400 pour un modèle à image unique AVANT la garde ;
    Nano Banana reçoit l'image + les références (faux tir, une ligne de dépense) ; avatar cinématique : les références
    de l'identité complètent celles choisies (3 au plus) ;
  - écritures réservées à la machine locale. Data-dir isolé, rien de payé.
Témoin : la base (24ffc42a) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_espaces_identite.py"""
import asyncio, contextlib, io, json, os, pathlib, random, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzidv_"))
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


r0 = subprocess.run(["git", "show", "24ffc42a:backend/app/services/identite.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a pas le module", r0.returncode != 0)

from PIL import Image                                               # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import espaces as ES, identite as IDV            # noqa: E402
from app.services import prompt_engine as PE                        # noqa: E402
from app.models.schemas import BuildPromptRequest                   # noqa: E402
from app.api import routes as RT                                    # noqa: E402
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
c.__enter__()
ES.lire()
rip = ES.creer({"nom": "Rippled"})["id"]
B = f"/api/espaces/{rip}/identite"


def png(couleur="#ff0000", taille=(64, 48)):
    b = io.BytesIO()
    Image.new("RGB", taille, couleur).save(b, format="PNG")
    return b.getvalue()


def rejouer(cas, eid="deepotus"):
    with ES.sous_espace(eid):
        random.seed(cas["seed"])
        return PE.PromptEngine().generate_from_intent(BuildPromptRequest(
            intent=cas["intent"], inject_persona=cas["inject"], style=cas["style"])).model_dump()


print("[A] Deepotus à l'octet")
GOLD = json.loads((_ICI / "identite_adn_deepotus.json").read_text(encoding="utf-8"))
ecarts = [g["intent"] for g in GOLD if rejouer(g) != g["r"]]
check(f"A1 les {len(GOLD)} cas figés avant t206 sont identiques (sans identite.json)", not ecarts and len(GOLD) == 160, ecarts[:3])
src_pe = (RACINE / "backend/app/services/prompt_engine.py").read_text(encoding="utf-8")
check("A2 le DNA n'est plus codé en dur dans prompt_engine", "DEEPOTUS_DNA" not in src_pe and "bioluminescent cyan accents" not in src_pe
      and "persona_words" not in src_pe)
r = c.put("/api/espaces/deepotus/identite", json={"palette": [{"hex": "#00e0ff", "role": "primaire"}]})
ecarts = [g["intent"] for g in GOLD if rejouer(g) != g["r"]]
check("A3 ... toujours identiques après une écriture de la palette de Deepotus (l'ADN de la graine reste)",
      r.status_code == 200 and not ecarts and r.json()["palette"] == [{"hex": "#00E0FF", "role": "primaire"}], (r.text[:200], ecarts[:2]))
# l'aller-retour de l'écran (DzIdentite) : listes jointes par ligne (repères par virgules), puis redécoupées
_v = c.get("/api/espaces/deepotus/identite").json()
_adn = {}
for _k, _g in (("touches_sujet", "l"), ("touches_decor", "l"), ("decor_defaut", "t"), ("reperes", "v"), ("eclairages", "l"),
               ("explication", "t")):
    _x = _v["adn"].get(_k)
    _t = "\n".join(_x) if _g == "l" else ", ".join(_x) if _g == "v" else _x
    _adn[_k] = _t.strip() if _g == "t" else [y.strip() for y in _t.split("\n" if _g == "l" else ",") if y.strip()]
r = c.put("/api/espaces/deepotus/identite", json={"palette": _v["palette"], "typographies": [], "style_ecrit": _v["style_ecrit"], "adn": _adn})
ecarts = [g["intent"] for g in GOLD if rejouer(g) != g["r"]]
check("A4 ... et après un enregistrement depuis l'écran (aller-retour des champs de l'ADN)", r.status_code == 200 and not ecarts,
      (r.text[:200], ecarts[:2]))

print("\n[P] un autre persona")
cas = {"intent": "a trader staring at charts at night", "inject": True, "seed": 1, "style": "hybrid"}
x = rejouer(cas, rip)
low = x["prompt"].lower()
check("P1 sans identité : rien de Deepotus, décor neutre, explication dite",
      not any(w in low for w in ("deepotus", "bioluminescent", "underwater", "deep blue", "cyan")) and "Setting: charts at night." in x["prompt"]
      and "no identity descriptors" in x["explanation"], x["prompt"] + " | " + x["explanation"])
x2 = rejouer({"intent": "product reveal with soft focus", "inject": True, "seed": 0, "style": "hybrid"}, rip)
check("P2 ... et sans lieu détecté : « neutral environment »", "Setting: neutral environment." in x2["prompt"], x2["prompt"])
r = c.put(B, json={"style_ecrit": "warm terracotta tones, matte ceramic textures; soft side light",
                   "palette": [{"hex": "#c2410c", "role": "primaire"}, {"hex": "#fef3c7", "role": "fond"}]})
x3 = rejouer(cas, rip)
check("P3 avec un style écrit : une de ses touches s'ajoute au sujet, la palette au décor",
      r.status_code == 200 and any(t in x3["prompt"] for t in ("warm terracotta tones", "matte ceramic textures", "soft side light"))
      and "with brand colors #C2410C and #FEF3C7" in x3["prompt"] and "Rippled identity injected" in x3["explanation"], x3["prompt"])
x4 = rejouer({"intent": "the rippled logo on a hoodie", "inject": True, "seed": 2, "style": "hybrid"}, rip)
check("P4 ses repères (le nom du persona) évitent le doublon", x4["prompt"].startswith("Subject: the rippled logo on a hoodie. "), x4["prompt"])
c.put(B, json={"adn": {"decor_defaut": "sunlit pottery studio", "touches_sujet": ["with a glazed ceramic sheen"]}})
x5 = rejouer({"intent": "product reveal with soft focus", "inject": True, "seed": 0, "style": "hybrid"}, rip)
check("P5 un ADN saisi l'emporte sur le dérivé", "Setting: sunlit pottery studio." in x5["prompt"]
      and "with a glazed ceramic sheen" in x5["prompt"], x5["prompt"])
x6 = rejouer({"intent": "product reveal with soft focus", "inject": False, "seed": 0, "style": "hybrid"}, rip)
check("P6 inject_persona=false : rien d'injecté", "glazed" not in x6["prompt"] and "neutral environment" in x6["prompt"])
x7 = PE.PromptEngine(rip).generate_from_intent(BuildPromptRequest(intent="product reveal with soft focus"))
check("P7 PromptEngine(id) lit l'identité de CET espace (l'actif reste Deepotus)", "sunlit pottery studio" in x7.prompt
      and ES.lire()["actif"] == "deepotus")

print("\n[D] la doctrine et la validation")
avant = (IDV.dossier(rip) / "identite.json").read_bytes()
for i, (corps, attendu) in enumerate([
        ({"style_ecrit": "dreamy, in the style of Van Gogh"}, "in the style of"),
        ({"style_ecrit": "à la manière de Mucha, ornements"}, "manière"),
        ({"style_ecrit": "soft ghibli vibes"}, "ghibli"),
        ({"adn": {"touches_sujet": ["painted like Picasso"]}}, "picasso"),
        ({"palette": [{"hex": "rouge", "role": "x"}]}, "#RRGGBB"),
        ({"palette": [{"hex": "#000000", "role": "x"}] * 13}, "12"),
        ({"typographies": [{"nom": "", "usage": "titres"}]}, "nom manquant"),
        ({"logo": "x.png"}, "champ inconnu"),
        ({"adn": {"inconnu": "x"}}, "champ inconnu")], 1):
    rr = c.put(B, json=corps)
    check(f"D{i} {list(corps)[0]} refusé -> 400 « {attendu} », rien d'écrit", rr.status_code == 400 and attendu.lower() in rr.text.lower()
          and (IDV.dossier(rip) / "identite.json").read_bytes() == avant, rr.text[:200])
check("D10 des descripteurs sans nom passent", c.put(B, json={"style_ecrit": "warm terracotta tones, matte ceramic textures; soft side light",
                                                              "typographies": [{"nom": "Inter", "usage": "titres"}]}).status_code == 200)
dist = TestClient(app, client=("192.168.1.20", 50000))
check("D11 écrire depuis le réseau local sans jeton -> refusé", dist.put(B, json={"style_ecrit": "x"}).status_code in (401, 403)
      and dist.post(f"{B}/planche").status_code in (401, 403))

print("\n[I] les images")
up = lambda g, data, nom="a.png": c.post(f"{B}/images/{g}", files={"file": (nom, data, "image/png")})
m1 = up("mascotte", png("#00ff00", (3000, 1000)))
nom1 = m1.json().get("nom", "")
f1 = IDV.dossier(rip) / nom1
check("I1 une mascotte rangée : PNG, 2048 px au plus, copie de Bibliothèque", m1.status_code == 200 and f1.is_file()
      and max(Image.open(f1).size) == 2048 and (_tmp / "images" / f"identite_{rip}_{nom1}").is_file()
      and m1.json()["identite"]["bibliotheque"][nom1] == f"identite_{rip}_{nom1}", m1.text[:200])
check("I2 un faux PNG -> 400, rien de rangé", up("mascotte", b"pas une image").status_code == 400 and len(IDV.lire(rip)["mascotte"]) == 1)
check("I3 genre inconnu -> 400", up("fond", png()).status_code == 400)
for _ in range(5):
    up("mascotte", png())
check("I4 une 7e mascotte -> 400", up("mascotte", png()).status_code == 400 and len(IDV.lire(rip)["mascotte"]) == 6)
l1 = up("logo", png("#111111")).json()["nom"]
l2 = up("logo", png("#222222")).json()["nom"]
check("I5 le logo REMPLACE le précédent (fichier effacé)", IDV.lire(rip)["logo"] == l2 and not (IDV.dossier(rip) / l1).exists())
g = c.get(f"{B}/fichier/{nom1}")
check("I6 une image de l'identité est servie", g.status_code == 200 and g.headers["content-type"] == "image/png")
_tr = c.get(f"{B}/fichier/..%2Fpersona.json")
check("I7 un nom hors liste n'est jamais servi (« ..%2F » tombe sur la page de l'app, jamais sur le fichier)",
      c.get(f"{B}/fichier/identite.json").status_code == 404 and c.get(f"{B}/fichier/persona.json").status_code == 404
      and _tr.headers.get("content-type", "") != "image/png" and "display_name" not in _tr.text, (_tr.status_code, _tr.text[:80]))
(_tmp / "images" / f"identite_{rip}_{nom1}").unlink()
refs = IDV.references_bibliotheque(rip, n=3)
check("I8 une copie de Bibliothèque disparue est refaite", len(refs) == 3 and (_tmp / "images" / f"identite_{rip}_{nom1}").is_file(), refs)
(_tmp / "images" / "photo_banc.png").write_bytes(png("#0000ff"))
im = c.post(f"{B}/importer", json={"genre": "produits", "fichiers": ["photo_banc.png"]})
check("I9 importer une image de la Bibliothèque comme photo produit", im.status_code == 200 and len(IDV.lire(rip)["produits"]) == 1, im.text[:200])
check("I10 importer un chemin -> 400", c.post(f"{B}/importer", json={"genre": "produits", "fichiers": ["../t.db"]}).status_code == 400)
der = IDV.lire(rip)["mascotte"][-1]
dl = c.delete(f"{B}/images/{der}")
check("I11 retirer une image (fichier et copie effacés)", dl.status_code == 200 and der not in IDV.lire(rip)["mascotte"]
      and not (IDV.dossier(rip) / der).exists() and not (_tmp / "images" / f"identite_{rip}_{der}").exists())
check("I12 retirer une image inconnue -> 404", c.delete(f"{B}/images/inconnue.png").status_code == 404)

print("\n[L] la planche d'identité")
from app.services.storage import Depense, async_session_factory     # noqa: E402
from sqlalchemy import select                                       # noqa: E402
async def depenses():
    async with async_session_factory() as s:
        return list((await s.execute(select(Depense))).scalars().all())
check("L0 sans planche : « absente », valider -> 400", c.get(B).json()["etat_planche"] == "absente"
      and c.post(f"{B}/planche/valider").status_code == 400)
pl = c.post(f"{B}/planche")
fpl = IDV.dossier(rip) / (pl.json().get("planche") or {}).get("fichier", "x")
check("L1 composée (1600×1000), à valider, gratuite", pl.status_code == 200 and pl.json()["etat_planche"] == "a_valider"
      and Image.open(fpl).size == (1600, 1000) and asyncio.run(depenses()) == [], pl.text[:200])
check("L2 servie", c.get(f"{B}/fichier/{fpl.name}").status_code == 200)
from PIL import ImageFont                                            # noqa: E402
check("L2b police TrueType livrée (les accents de « Identité visuelle » s'affichent), typographie nommée si livrée",
      isinstance(IDV._police(20), ImageFont.FreeTypeFont) and IDV._police(20, "Space Grotesk").path.endswith("SpaceGrotesk.ttf")
      and IDV._police(20, "Police Inconnue").path.endswith("Inter.ttf"))
v = c.post(f"{B}/planche/valider")
check("L3 validée", v.status_code == 200 and v.json()["etat_planche"] == "validee" and v.json()["planche"]["validee_le"])
c.put(B, json={"palette": [{"hex": "#000000", "role": "texte"}]})
check("L4 la palette change : planche PÉRIMÉE, valider -> 400", c.get(B).json()["etat_planche"] == "perimee"
      and c.post(f"{B}/planche/valider").status_code == 400)
pl2 = c.post(f"{B}/planche").json()
check("L5 recomposée : l'ancienne effacée, à valider de nouveau", pl2["etat_planche"] == "a_valider" and not fpl.exists())
c.post(f"{B}/planche/valider")
_lg = IDV.lire(rip)["logo"]
(IDV.dossier(rip) / _lg).write_bytes(png("#abcdef"))          # même nom, autre CONTENU
check("L6 une image qui change (même nom) rend la planche périmée", c.get(B).json()["etat_planche"] == "perimee")

print("\n[K] le kit des contenus de l'espace (D4)")
from app.services import brand_kits as BK                           # noqa: E402
KITS_AVANT = BK._fichier().read_bytes()
ACTIF_APP = BK.actif()["id"]
check("K0 rien de ce qui précède n'a touché aux kits de marque (Deepotus et l'application intacts)",
      ACTIF_APP == "deepotus" and BK.lire()["kits"].keys() == {"deepotus"} and ES.kit_de_l_espace(rip)["id"] == "deepotus"
      and c.get(B).json()["kit"]["branding"] is True)
c.put(B, json={"palette": [{"hex": "#fef3c7", "role": "fond"}, {"hex": "#EA580C", "role": "accent"}, {"hex": "#0ea5e9", "role": "primaire"}]})
ES.ecrire_persona(rip, dict(ES.persona(rip), ecran={"id": rip, "handle": "@rippled", "catchphrase": "Make waves."}))
k1 = c.post(f"{B}/kit")
kv = BK.lire()["kits"].get(IDV.kit_id(rip), {})
logo_id = IDV.dossier(rip) / IDV.lire(rip)["logo"]
check("K1 le kit idv_<espace> : couleurs par rôle (primaire, accent), nom et accroches du PERSONA, logo de l'identité",
      k1.status_code == 200 and kv.get("brand_color") == "#0EA5E9" and kv.get("accent_color") == "#EA580C"
      and kv.get("app_name") == "Rippled" and kv.get("tagline_1") == "Make waves." and kv.get("tagline_2") == "@rippled"
      and BK.logo_path(IDV.kit_id(rip)).read_bytes() == logo_id.read_bytes(), (k1.text[:200], kv))
check("K2 rien de Deepotus dans ce kit", not any("deep" in str(v).lower() for v in kv.values()), kv)
check("K3 associé aux CONTENUS de l'espace, JAMAIS activé (l'application garde son kit)",
      ES.kit_de_l_espace(rip)["id"] == IDV.kit_id(rip) and BK.actif()["id"] == ACTIF_APP
      and k1.json()["kit"]["depuis_identite"] is True and ES.kit_de_l_espace("deepotus")["id"] == "deepotus")
from app.services.template_service import TemplateEngine           # noqa: E402
with ES.sous_espace(rip):
    _tpl = TemplateEngine().resoudre({"layers": [{"type": "text", "text": "{{brand.app_name}}", "color": "{{brand.brand_color}}"}]})
check("K4 un gabarit rendu dans l'espace prend ses couleurs et son nom", "#0EA5E9" in str(_tpl) and "Rippled" in str(_tpl), str(_tpl)[:200])
c.put(B, json={"palette": [{"hex": "#16a34a", "role": "primaire"}]})
kv2 = BK.lire()["kits"][IDV.kit_id(rip)]
check("K5 la palette change : le kit SUIT (accent = marque faute d'autre couleur)", kv2["brand_color"] == "#16A34A"
      and kv2["accent_color"] == "#16A34A", kv2)
_nl = up("logo", png("#facc15")).json()["nom"]
check("K6 un nouveau logo : le kit suit", BK.logo_path(IDV.kit_id(rip)).read_bytes() == (IDV.dossier(rip) / _nl).read_bytes())
c.delete(f"{B}/images/{_nl}")
check("K7 le logo retiré : le kit n'a plus de logo", BK.logo_path(IDV.kit_id(rip)) is None)
up("logo", png("#facc15"))
BK.activer(IDV.kit_id(rip))
_kb = BK._fichier().read_bytes()
k8 = c.post(f"{B}/kit")
c.put(B, json={"palette": [{"hex": "#000000", "role": "primaire"}]})
check("K8 si ce kit habille l'application (activé à la main) : synchroniser -> 400, et l'identité n'y touche plus",
      k8.status_code == 400 and "application" in k8.text and BK._fichier().read_bytes() == _kb, k8.text[:200])
BK.activer(ACTIF_APP)
ES.modifier(rip, {"kit_id": "deepotus"})
_kb = BK._fichier().read_bytes()
c.put(B, json={"palette": [{"hex": "#123456", "role": "primaire"}]})
check("K9 l'espace a choisi un autre kit : l'identité ne touche à aucun kit", BK._fichier().read_bytes() == _kb
      and c.get(B).json()["kit"]["depuis_identite"] is False)
check("K10 depuis le réseau local sans jeton -> refusé", dist.post(f"{B}/kit").status_code in (401, 403))
ES.modifier(rip, {"kit_id": ""})

print("\n[R] les références passées aux modèles")
src = _tmp / "images" / "a_retoucher.png"
src.write_bytes(png("#888888"))
with ES.sous_espace(rip):
    pass
ES.activer(rip)
r1 = c.post("/api/images/process", json={"op": "edit", "filename": src.name, "prompt": "on a beach", "model": "flux", "identite": True})
check("R1 retouche + identité avec un modèle à image unique -> 400 AVANT la garde (aucune dépense)",
      r1.status_code == 400 and asyncio.run(depenses()) == [], r1.text[:200])
r2 = c.post("/api/images/process", json={"op": "edit", "filename": src.name, "prompt": "on a beach", "model": "nano-banana", "identite": True})
check("R2 Nano Banana sans clé fal -> 503, aucune dépense", r2.status_code == 503 and asyncio.run(depenses()) == [], r2.text[:200])
settings.FAL_KEY = "cle-de-banc"
from app.services import image_providers as IP                      # noqa: E402
tirs = []
async def faux_generate(model, prompt, size, n=1, **kw):
    tirs.append({"model": model, "prompt": prompt, **kw})
    return {"images": ["gen_banc.png"], "seed": None}
_og = IP.generate
IP.generate = faux_generate
try:
    r3 = c.post("/api/images/process", json={"op": "edit", "filename": src.name, "prompt": "on a beach", "model": "nano-banana",
                                              "identite": True})
    r4 = c.post("/api/images/process", json={"op": "edit", "filename": src.name, "prompt": "on a beach", "model": "nano-banana"})
finally:
    IP.generate = _og
attendu = [src] + IDV.references(rip, n=IP.REF_MAX - 1)
check("R3 Nano Banana reçoit l'image PUIS les références de l'identité (mascotte, produits), consigne ajoutée",
      r3.status_code == 200 and tirs and [pathlib.Path(p) for p in tirs[0].get("image_paths", [])] == attendu
      and len(attendu) == 7 and "exactly as in the reference images" in tirs[0]["prompt"], (r3.text[:200], tirs[:1]))
check("R4 sans `identite` : l'image seule (comportement d'avant)", r4.status_code == 200 and len(tirs) == 2
      and tirs[1].get("image_path") == src and "image_paths" not in tirs[1] and tirs[1]["prompt"] == "on a beach")
check("R5 deux tirs = deux lignes de dépense", len(asyncio.run(depenses())) == 2)

settings.HEYGEN_API_KEY = "cle-de-banc"
from app.services import plafonds as PLAF                           # noqa: E402
vus = []
async def faux_cine(req):
    vus.append(list(req.reference_images))
@contextlib.asynccontextmanager
async def faux_suivi(ref):
    yield
_oc, _os, _op = RT.pipeline.run_heygen_cinematic, PLAF.suivi_heygen, RT._plafond
async def faux_plafond(*a, **k):
    return None
RT.pipeline.run_heygen_cinematic, PLAF.suivi_heygen, RT._plafond = faux_cine, faux_suivi, faux_plafond
try:
    k1 = c.post("/api/generate/heygen-cinematic", json={"prompt": "p", "look_ids": ["l1"], "reference_images": ["photo_banc.png"],
                                                         "identite": True})
    k2 = c.post("/api/generate/heygen-cinematic", json={"prompt": "p", "look_ids": ["l1"], "reference_images": ["photo_banc.png"]})
finally:
    RT.pipeline.run_heygen_cinematic, PLAF.suivi_heygen, RT._plafond = _oc, _os, _op
m = IDV.lire(rip)["mascotte"]
check("R6 avatar cinématique + identité : la référence choisie, puis 2 de l'identité (3 au plus), copiées en Bibliothèque",
      k1.status_code == 200 and vus and vus[0] == ["photo_banc.png", f"identite_{rip}_{m[0]}", f"identite_{rip}_{m[1]}"]
      and all((_tmp / "images" / f).is_file() for f in vus[0]), (k1.text[:200], vus))
check("R7 ... sans `identite` : inchangé", k2.status_code == 200 and len(vus) == 2 and vus[1] == ["photo_banc.png"])
ES.activer("deepotus")
check("R8 l'espace Deepotus n'a aucune référence : identite -> 400 (rien inventé)",
      c.post("/api/images/process", json={"op": "edit", "filename": src.name, "prompt": "x", "model": "nano-banana",
                                           "identite": True}).status_code == 400)

c.__exit__(None, None, None)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
