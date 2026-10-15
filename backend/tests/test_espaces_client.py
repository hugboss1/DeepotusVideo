# -*- coding: utf-8 -*-
"""t210 (Espaces de marque E10, 15/10/2026) — le CLIENT et l'ISOLATION des espaces (spec D9).
Ce que ce banc garde :
  - EXPORT d'un espace (GET /api/espaces/{id}/export) : un .zip à liste blanche (espace.json, persona, contenus,
    onboarding, identité et ses images, kit et son logo, comptes) ; AUCUN secret — ni ceux d'un compte (.env/coffre,
    DZC_<ID>_<CHAMP>), ni les clés plates des comptes historiques de Deepotus ; les champs secrets y sont seulement
    NOMMÉS (à ressaisir), les champs publics y sont ;
  - IMPORT (POST /api/espaces/importer) : toujours un espace NEUF et non actif, nom libre (« (2) »), persona,
    contenus, onboarding, identité (images recopiées), kit (logo) et comptes (publics posés, secrets jamais) ; un
    secret glissé dans le paquet n'est JAMAIS écrit ; paquet illisible, d'un autre format, trop récent, persona
    invalide, image fausse : 400 et RIEN d'écrit (ni espace, ni compte, ni kit) ; entrées hors liste blanche (../)
    ignorées et dites, rien écrit hors du dossier ; zip trop lourd décompressé : 400 ;
  - ARCHIVAGE : la réponse dit combien de posts sont mis en pause ; la boucle du Planificateur ne publie plus les posts
    d'un espace archivé (ils restent « scheduled ») et les reprend au désarchivage ;
  - en-tête X-Dz-Espace : un client (skill deepotus-comms) travaille DANS un espace sans changer l'actif ; inconnu
    404, archivé 409 (jamais un repli silencieux sur l'actif) ;
  - ISOLATION : avec deux espaces remplis (Deepotus, Rippled), aucune donnée d'un espace n'apparaît dans les lectures
    de l'autre (persona, contenus, identité et ses fichiers, onboarding, comptes, Planificateur, Bibliothèque, jobs,
    sons, projets, dépenses, relevé, export).
Data-dir isolé, aucune clé, rien de payé. Témoin : la base (cdb34331) n'a ni export ni import d'espace.
Run (depuis backend/) : & $PY tests/test_espaces_client.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile, zipfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcli_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs", "audio"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "FAL_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
          "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
          "YOUTUBE_CHANNEL_ID", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET",
          "TIKTOK_REFRESH_TOKEN"):
    os.environ[k] = ""
# les clés PLATES d'avant (compte historique X de Deepotus) : jamais dans un paquet
os.environ.update({"X_API_KEY": "plat-ak-SECRET", "X_API_SECRET": "plat-as-SECRET", "X_ACCESS_TOKEN": "plat-at-SECRET",
                   "X_ACCESS_SECRET": "plat-ax-SECRET"})
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


r0 = subprocess.run(["git", "show", "cdb34331:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a ni export ni import d'espace",
      r0.returncode == 0 and b"/espaces/importer" not in r0.stdout and b'"/espaces/{espace_id}/export"' not in r0.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
c.__enter__()
from app.services import (brand_kits as BK, comptes as CP, espaces as ES, identite as IDV, library_index as LI,  # noqa: E402
                          marketing as MK)
from app.services.storage import JobRecord, async_session_factory  # noqa: E402
from app.config import ENV_FILE                                     # noqa: E402

DEEP, RIPM = "MARQ-DEEP-QQ", "MARQ-RIP-ZZ"          # un repère par espace : jamais lu chez l'autre


def png_octets(couleur=(10, 20, 30), cote=8):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (cote, cote), couleur).save(b, format="PNG")
    return b.getvalue()


# ---- deux espaces remplis -------------------------------------------------------------------------------------------
ES.lire()
rip = ES.creer({"nom": "Rippled", "couleur": "#3b82f6"})["id"]
pd = ES.persona("deepotus")
pd["vibe_keywords"] = list(pd.get("vibe_keywords") or []) + [DEEP]
c.put("/api/espaces/deepotus/persona", json=pd).raise_for_status()
c.put(f"/api/espaces/{rip}/persona", json={"display_name": "Rippled", "vibe_keywords": [RIPM, "ledger"],
                                           "voice_ids": {"default": "v-rip"}, "audience": {"qui": "builders"}}).raise_for_status()
ct = {"version": 1, "prompt_templates": [{"id": "rip1", "title": "Lancement " + RIPM, "cat": "rip", "emoji": "",
                                          "body": "a calm ledger " + RIPM}],
      "prompt_cats": [{"id": "rip", "label": "Rippled"}], "ingredients": {"lieu": ["quai " + RIPM]},
      "vibes": [{"id": "v1", "preset": "cinematic", "tags": "calm"}],
      "hashtags": ["#rippled"]}
rct = c.put(f"/api/espaces/{rip}/contenus", json=ct)
check("0.1 contenus de Rippled écrits", rct.status_code == 200, rct.text[:200])
c.put(f"/api/espaces/{rip}/identite", json={"palette": [{"hex": "#112233", "role": "fond"}], "style_ecrit": "flat calm " + RIPM,
                                            "typographies": [{"nom": "Inter", "role": "titre"}]}).raise_for_status()
B = f"/api/espaces/{rip}/identite"
up = lambda g, data: c.post(f"{B}/images/{g}", files={"file": ("a.png", data, "image/png")})
check("0.2 logo et mascotte de Rippled posés",
      up("logo", png_octets((200, 0, 0))).status_code == 200 and up("mascotte", png_octets((0, 200, 0))).status_code == 200)
c.put(f"/api/espaces/{rip}/onboarding/produit", json={"nom": "un registre " + RIPM, "pitch": "p"}).raise_for_status()
c.put("/api/espaces/deepotus/onboarding/produit", json={"nom": "le jeu " + DEEP}).raise_for_status()
# un kit pour les contenus de Rippled, avec un logo
kid = BK.enregistrer({"name": "Kit Rippled", "brand_color": "#123456"})
(BK.dossier() / "logos").mkdir(parents=True, exist_ok=True)
(BK.dossier() / "logos" / f"{kid}.png").write_bytes(png_octets((1, 2, 3)))
ES.modifier(rip, {"kit_id": kid})
# des comptes : secrets dans le .env (pas de coffre), publics dans comptes.json
cx = CP.creer({"espace_id": rip, "plateforme": "x", "libelle": "Rippled X", "handle": "@" + RIPM,
               "valeurs": {"X_API_KEY": "rip-ak-SECRET", "X_API_SECRET": "rip-as-SECRET", "X_ACCESS_TOKEN": "rip-at-SECRET",
                           "X_ACCESS_SECRET": "rip-ax-SECRET"}})["id"]
ctg = CP.creer({"espace_id": rip, "plateforme": "telegram", "libelle": "Canal Rippled",
                "valeurs": {"TELEGRAM_BOT_TOKEN": "999:RIP-SECRET", "TELEGRAM_CHAT_ID": "-100rip"}})["id"]
cdx = CP.creer({"espace_id": "deepotus", "plateforme": "telegram", "libelle": "Canal " + DEEP,
                "valeurs": {"TELEGRAM_BOT_TOKEN": "111:DEEP-SECRET", "TELEGRAM_CHAT_ID": "-100deep"}})["id"]
SECRETS = ["rip-ak-SECRET", "rip-as-SECRET", "rip-at-SECRET", "rip-ax-SECRET", "999:RIP-SECRET", "111:DEEP-SECRET",
           "plat-ak-SECRET", "plat-as-SECRET", "plat-at-SECRET", "plat-ax-SECRET"]
env0 = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
check("0.3 les secrets des comptes sont au .env (pas dans comptes.json)",
      "rip-at-SECRET" in env0 and "SECRET" not in (ES.dossier() / "comptes.json").read_text(encoding="utf-8"))


async def remplir():
    (_tmp / "images" / f"deep_{DEEP}.png").write_bytes(png_octets())
    (_tmp / "images" / f"rip_{RIPM}.png").write_bytes(png_octets())
    (_tmp / "audio" / f"deep_{DEEP}.mp3").write_bytes(b"ID3")
    (_tmp / "audio" / f"rip_{RIPM}.mp3").write_bytes(b"ID3")
    await LI.noter([f"deep_{DEEP}.png"], "quick")
    await LI.noter([f"deep_{DEEP}.mp3"], "son", kind="audio")
    async with async_session_factory() as s:
        s.add(JobRecord(id="job_deep", status="done", title="job " + DEEP, image_filename="x.png"))
        await s.commit()
    with ES.sous_espace(rip):
        await LI.noter([f"rip_{RIPM}.png"], "quick")
        await LI.noter([f"rip_{RIPM}.mp3"], "son", kind="audio")
        async with async_session_factory() as s:
            s.add(JobRecord(id="job_rip", status="done", title="job " + RIPM, image_filename="x.png"))
            await s.commit()
asyncio.run(remplir())
QUAND = (datetime.utcnow() - timedelta(minutes=5)).isoformat()   # DÛ : la boucle le prendrait
p_deep = c.post("/api/schedule", json={"title": "post " + DEEP, "caption": "c", "channels": ["telegram"], "run_at": QUAND,
                                       "status": "scheduled", "mode": "assisted"}).json()
p_rip = c.post("/api/schedule", json={"title": "post " + RIPM, "caption": "c", "channels": ["x"], "run_at": QUAND,
                                      "espace_id": rip, "comptes": [cx], "status": "scheduled", "mode": "assisted"}).json()
check("0.4 un post par espace", p_deep.get("espace_id") == "deepotus" and p_rip.get("espace_id") == rip, str((p_deep, p_rip))[:300])
c.post("/api/library/projets", json={"nom": "Projet " + DEEP}).raise_for_status()
with ES.sous_espace(rip):
    pass
c.post("/api/library/projets", json={"nom": "Projet " + RIPM}, headers={"X-Dz-Espace": rip}).raise_for_status()
con = sqlite3.connect(_tmp / "t.db")
mois = datetime.now().strftime("%Y-%m")
con.execute("INSERT INTO depenses (quand, mois, moteur, categorie, op, estime_usd, ref, espace_id) VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(sep=" "), mois, "fal", "quick", "image", 0.25, "ref-" + DEEP, "deepotus"))
con.execute("INSERT INTO depenses (quand, mois, moteur, categorie, op, estime_usd, ref, espace_id) VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(sep=" "), mois, "fal", "quick", "image", 0.5, "ref-" + RIPM, rip))
con.commit(); con.close()

# ---- [H] l'en-tête X-Dz-Espace ----------------------------------------------------------------------------------------
print("[H] en-tête X-Dz-Espace")
check("H1 l'espace actif reste Deepotus", c.get("/api/espaces/actif").json()["id"] == "deepotus")
ph = c.post("/api/schedule", json={"title": "h", "channels": ["x"], "run_at": QUAND}, headers={"X-Dz-Espace": rip}).json()
check("H2 un post créé sous l'en-tête va dans l'espace nommé", ph.get("espace_id") == rip, str(ph)[:200])
lp = [p["title"] for p in c.get("/api/schedule", headers={"X-Dz-Espace": rip}).json()]
check("H3 la liste sous l'en-tête est celle de l'espace nommé", "post " + RIPM in lp and "post " + DEEP not in lp, str(lp))
check("H4 l'actif n'a pas bougé", c.get("/api/espaces/actif").json()["id"] == "deepotus")
r = c.get("/api/schedule", headers={"X-Dz-Espace": "esp_inconnu"})
check("H5 espace inconnu : 404, aucun repli", r.status_code == 404 and "inconnu" in r.text, f"{r.status_code} {r.text[:120]}")
r = c.get("/api/schedule", headers={"X-Dz-Espace": "../x"})
check("H6 id hostile : 404", r.status_code == 404)
r = c.get("/api/schedule", headers={"X-Dz-Espace": rip, "Accept-Language": "en"})
check("H7 sans faute, l'en-tête passe (200)", r.status_code == 200)
c.delete(f"/api/schedule/{ph['id']}")

# ---- [I] isolation ---------------------------------------------------------------------------------------------------
print("[I] isolation : rien de Deepotus chez Rippled, rien de Rippled chez Deepotus")
def lectures(eid, autre_marq, hdr=None):
    q = f"espace={eid}"
    h = {"X-Dz-Espace": eid}
    return {
        "persona": c.get(f"/api/espaces/{eid}/persona"),
        "contenus": c.get(f"/api/espaces/{eid}/contenus"),
        "identite": c.get(f"/api/espaces/{eid}/identite"),
        "onboarding": c.get(f"/api/espaces/{eid}/onboarding"),
        "comptes": c.get(f"/api/comptes?{q}"),
        "schedule": c.get(f"/api/schedule?{q}"),
        "images": c.get(f"/api/images?{q}"),
        "jobs": c.get(f"/api/jobs?limit=50&{q}"),
        "audio": c.get(f"/api/audio?{q}"),
        "projets": c.get(f"/api/library/projets?{q}"),
        "projets_entete": c.get("/api/library/projets", headers=h),
        "depenses": c.get(f"/api/reglages/depenses?{q}"),
        "releve": c.get(f"/api/reglages/depenses/releve?{q}&mois={mois}"),
        "export": c.get(f"/api/espaces/{eid}/export"),
    }
for eid, mien, autre in (("deepotus", DEEP, RIPM), (rip, RIPM, DEEP)):
    L = lectures(eid, autre)
    nom = "Deepotus" if eid == "deepotus" else "Rippled"
    for k, r in L.items():
        corps = r.content if k == "export" else r.text.encode("utf-8")
        if k == "export" and r.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            corps = b"".join(z.read(n) for n in z.namelist())
        check(f"I {nom} · {k} : 200 et rien de l'autre espace", r.status_code == 200 and autre.encode() not in corps,
              f"{r.status_code} {r.text[:160] if k != 'export' else ''}")
    for k in ("persona", "comptes", "schedule", "images", "jobs", "audio", "projets") + (("contenus",) if eid == rip else ()):
        check(f"I {nom} · {k} : sa propre donnée y est (le filtre ne vide pas tout)", mien in L[k].text, L[k].text[:160])
idr = c.get(f"/api/espaces/{rip}/identite").json()
r = c.get(f"/api/espaces/deepotus/identite/fichier/{idr['logo']}")
check("I.f le logo de Rippled n'est pas lisible par l'adresse de Deepotus (404)", r.status_code == 404, str(r.status_code))
r = c.get(f"/api/espaces/{rip}/identite/fichier/{idr['logo']}")
check("I.g … et l'est par la sienne", r.status_code == 200)

# ---- [E] export -------------------------------------------------------------------------------------------------------
print("[E] export")
r = c.get(f"/api/espaces/{rip}/export")
check("E1 200 application/zip, en pièce jointe nommée d'après l'espace",
      r.status_code == 200 and r.headers["content-type"] == "application/zip"
      and 'filename="espace-rippled-' in r.headers.get("content-disposition", ""), str(r.headers)[:200])
z = zipfile.ZipFile(io.BytesIO(r.content))
noms = sorted(z.namelist())
attendus = {"espace.json", "persona.json", "contenus.json", "onboarding.json", "comptes.json", "identite/identite.json",
            "kit/kit.json", "kit/logo.png"}
check("E2 entrées : la liste blanche (+ les images de l'identité)",
      attendus <= set(noms) and all(n in attendus or n.startswith("identite/") and n.endswith(".png") for n in noms)
      and sum(1 for n in noms if n.startswith("identite/") and n.endswith(".png")) == 2, str(noms))
tout = b"".join(z.read(n) for n in noms)
check("E3 AUCUN secret (ni ceux de Rippled, ni ceux de Deepotus, ni les clés plates)", not any(s.encode() in tout for s in SECRETS),
      str([s for s in SECRETS if s.encode() in tout]))
tete = json.loads(z.read("espace.json"))
check("E4 espace.json : format, version, nom, couleur", tete["format"] == "deepotus-espace" and tete["version"] == 1
      and tete["espace"]["nom"] == "Rippled" and tete["espace"]["couleur"] == "#3b82f6", str(tete))
cps = json.loads(z.read("comptes.json"))
tg = [x for x in cps if x["plateforme"] == "telegram"][0]
xx = [x for x in cps if x["plateforme"] == "x"][0]
check("E5 comptes : publics présents, secrets NOMMÉS seulement",
      tg["publics"] == {"TELEGRAM_CHAT_ID": "-100rip"} and tg["a_ressaisir"] == ["TELEGRAM_BOT_TOKEN"]
      and xx["handle"] == "@" + RIPM and set(xx["a_ressaisir"]) == {"X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"}
      and xx["publics"] == {}, str(cps))
check("E6 le persona et les contenus sont ceux de l'espace", RIPM in json.loads(z.read("persona.json"))["vibe_keywords"]
      and json.loads(z.read("contenus.json"))["prompt_templates"][0]["id"] == "rip1")
rd = c.get("/api/espaces/deepotus/export")
zd = zipfile.ZipFile(io.BytesIO(rd.content))
toutd = b"".join(zd.read(n) for n in zd.namelist())
cpd = json.loads(zd.read("comptes.json"))
check("E7 Deepotus : le compte historique X est exporté SANS ses clés plates",
      rd.status_code == 200 and any(x["plateforme"] == "x" and x["a_ressaisir"] for x in cpd)
      and not any(s.encode() in toutd for s in SECRETS) and "kit/kit.json" not in zd.namelist(), str(cpd)[:300])
check("E8 espace inconnu : 404", c.get("/api/espaces/esp_nope/export").status_code == 404)

# ---- [M] import -------------------------------------------------------------------------------------------------------
print("[M] import")
def importer(data, nom="p.zip"):
    return c.post("/api/espaces/importer", files={"file": (nom, data, "application/zip")})
def etat():
    return (sorted(ES.lire()["espaces"]), sorted(CP._lire()["comptes"]), sorted(BK.lire()["kits"]),
            sorted(p.name for p in ES.dossier().iterdir()), sorted(p.name for p in (_tmp / "images").iterdir()), ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else "")
avant = etat()
ri = importer(r.content)
check("M1 import : 200", ri.status_code == 200, ri.text[:300])
J = ri.json()
nid = J["espace"]["id"]
check("M2 un espace NEUF, non actif, nom libre « Rippled (2) »", nid not in avant[0] and nid != rip and not J["espace"]["actif"]
      and J["espace"]["nom"] == "Rippled (2)" and J["espace"]["couleur"] == "#3b82f6", str(J["espace"]))
check("M3 l'actif n'a pas bougé", ES.lire()["actif"] == "deepotus")
pn = ES.persona(nid)
check("M4 persona repris (id réécrit)", pn["persona_id"] == nid and RIPM in pn["vibe_keywords"] and pn["voice_ids"] == {"default": "v-rip"})
check("M5 contenus repris à l'identique", ES.contenus(nid) == ES.contenus(rip))
from app.services import onboarding_persona as OB                    # noqa: E402
check("M6 brouillon d'onboarding repris", OB.brouillon(nid)["etapes"].get("produit", {}).get("nom") == "un registre " + RIPM)
idn = IDV.lire(nid)
check("M7 identité reprise (palette, style, logo et mascotte recopiés, NOMS neufs)",
      idn["palette"] == IDV.lire(rip)["palette"] and RIPM in idn["style_ecrit"] and idn["logo"] and len(idn["mascotte"]) == 1
      and idn["logo"] != IDV.lire(rip)["logo"] and (IDV.dossier(nid) / idn["logo"]).is_file(), str(idn)[:300])
kn = ES.lire()["espaces"][nid]["kit_id"]
check("M8 un kit NEUF pour l'espace importé, logo compris", kn and kn != kid and BK.lire()["kits"][kn]["brand_color"] == "#123456"
      and BK.logo_path(kn) is not None, str(kn))
cn = CP.lister(nid)
tgn = [x for x in cn if x["plateforme"] == "telegram"][0]
check("M9 comptes recréés : publics posés, AUCUN secret posé",
      len(cn) == 2 and tgn["libelle"] == "Canal Rippled" and [ch for ch in tgn["champs"] if ch["nom"] == "TELEGRAM_CHAT_ID"][0]["valeur"] == "-100rip"
      and not any(ch["pose"] for x in cn for ch in x["champs"] if ch["secret"]), str(cn)[:400])
check("M10 la réponse dit les secrets à ressaisir", sorted(a["plateforme"] for a in J["a_ressaisir"]) == ["telegram", "x"]
      and all(a["champs"] for a in J["a_ressaisir"]) and J["ignores"] == [], str(J["a_ressaisir"]))
check("M11 le .env n'a reçu aucune ligne", (ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else "") == avant[5])
check("M12 un second import : « Rippled (3) »", importer(r.content).json()["espace"]["nom"] == "Rippled (3)")


def zipper(entrees: dict) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as zz:
        for n, v in entrees.items():
            zz.writestr(n, v if isinstance(v, bytes) else json.dumps(v))
    return b.getvalue()
BASE = {"espace.json": {"format": "deepotus-espace", "version": 1, "espace": {"nom": "Client X"}},
        "persona.json": {"display_name": "Client X"}}
avant = etat()
cas = [
    ("M13 pas un zip", b"bonjour"),
    ("M14 autre format", zipper({**BASE, "espace.json": {"format": "autre", "version": 1, "espace": {"nom": "a"}}})),
    ("M15 version plus récente", zipper({**BASE, "espace.json": {"format": "deepotus-espace", "version": 9, "espace": {"nom": "a"}}})),
    ("M16 persona invalide", zipper({**BASE, "persona.json": {"display_name": ""}})),
    ("M17 persona manquant", zipper({"espace.json": BASE["espace.json"]})),
    ("M18 contenus invalides", zipper({**BASE, "contenus.json": {"prompt_templates": "x"}})),
    ("M19 image fausse dans l'identité", zipper({**BASE, "identite/identite.json": {"logo": "logo-0123abcd.png"},
                                                 "identite/logo-0123abcd.png": b"pas une image"})),
    ("M20 style avec un nom d'artiste", zipper({**BASE, "identite/identite.json": {"style_ecrit": "in the style of Monet"}})),
    ("M21 compte d'une plateforme inconnue", zipper({**BASE, "comptes.json": [{"plateforme": "myspace"}]})),
    ("M22 couleur fausse", zipper({**BASE, "espace.json": {"format": "deepotus-espace", "version": 1, "espace": {"nom": "a", "couleur": "rouge"}}})),
]
for label, data in cas:
    rr = importer(data)
    check(f"{label} : 400 et rien d'écrit", rr.status_code == 400 and etat() == avant, f"{rr.status_code} {rr.text[:160]}")
# un échec PENDANT l'écriture (le plafond de comptes atteint au 2e compte) : tout est défait
_max = CP.MAX_COMPTES
CP.MAX_COMPTES = len(CP._lire()["comptes"]) + 1
rr = importer(zipper({**BASE, "comptes.json": [{"plateforme": "x"}, {"plateforme": "telegram"}],
                      "identite/identite.json": {"logo": "logo-0123abcd.png"}, "identite/logo-0123abcd.png": png_octets()}))
CP.MAX_COMPTES = _max
check("M23 échec pendant l'écriture : 400 et tout défait (espace, dossier, comptes, copie du logo en Bibliothèque)", rr.status_code == 400 and etat() == avant,
      f"{rr.status_code} {rr.text[:160]}")
# un secret glissé dans le paquet n'est jamais écrit
rr = importer(zipper({**BASE, "comptes.json": [{"plateforme": "telegram", "publics": {"TELEGRAM_BOT_TOKEN": "glisse-SECRET",
                                                                                   "TELEGRAM_CHAT_ID": {"x": "objet-glisse"}}}]}))
env = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
cg = CP.lister(rr.json()["espace"]["id"])[0] if rr.status_code == 200 else {}
check("M24 un secret glissé dans le paquet : jamais écrit, à ressaisir ; une valeur publique non texte ignorée",
      rr.status_code == 200 and "glisse-SECRET" not in env and "glisse-SECRET" not in (ES.dossier() / "comptes.json").read_text(encoding="utf-8")
      and not [ch for ch in cg["champs"] if ch["nom"] == "TELEGRAM_BOT_TOKEN"][0]["pose"]
      and "objet-glisse" not in (ES.dossier() / "comptes.json").read_text(encoding="utf-8"), rr.text[:200])
# entrées hors liste blanche : ignorées, dites, rien écrit dehors
rr = importer(zipper({**BASE, "../evil.json": {"x": 1}, "identite/../../evil.png": b"x", "notes.txt": b"x"}))
check("M25 entrées hors liste blanche ignorées et dites ; rien écrit hors du dossier",
      rr.status_code == 200 and sorted(rr.json()["ignores"]) == sorted(["../evil.json", "identite/../../evil.png", "notes.txt"])
      and not (_tmp / "evil.json").exists() and not (ES.dossier() / "evil.json").exists(), rr.text[:200])
# zip qui gonfle
gros = io.BytesIO()
with zipfile.ZipFile(gros, "w", zipfile.ZIP_DEFLATED) as zz:
    for n, v in BASE.items():
        zz.writestr(n, json.dumps(v))
    zz.writestr("contenus.json", b"{}" + b" " * (130 * 1024 * 1024))     # un JSON VALIDE : seule la borne le refuse
avant = etat()
rr = importer(gros.getvalue())
check("M26 zip qui gonfle au-delà de la borne : 400, rien d'écrit", rr.status_code == 400 and etat() == avant, f"{rr.status_code} {rr.text[:120]}")
# aller-retour de Deepotus
rr = importer(rd.content)
dn = rr.json()["espace"]["id"] if rr.status_code == 200 else ""
check("M27 aller-retour de Deepotus : persona et contenus identiques (hors id), nom « Deepotus (2) »",
      rr.status_code == 200 and rr.json()["espace"]["nom"] == "Deepotus (2)"
      and {k: v for k, v in ES.persona(dn).items() if k != "persona_id"} == {k: v for k, v in ES.persona("deepotus").items() if k != "persona_id"}
      and ES.contenus(dn) == ES.contenus("deepotus"), rr.text[:200])
check("M28 l'espace importé est isolé : ses comptes sont les siens, aucun de Deepotus",
      all(x["espace_id"] == dn for x in CP.lister(dn)) and not any(x["historique"] for x in CP.lister(dn)))

# ---- [A] archivage ----------------------------------------------------------------------------------------------------
print("[A] archivage")
ra = c.post(f"/api/espaces/{rip}/archive", json={"archive": True})
check("A1 archiver dit combien de posts sont mis en pause", ra.status_code == 200 and ra.json().get("en_pause") == 1, ra.text[:200])
asyncio.run(MK.tick([datetime.utcnow().strftime("%Y-%m-%d")]))
st = {p["id"]: p["status"] for p in c.get("/api/schedule?espace=*").json()}
check("A2 la boucle ne touche pas au post de l'espace archivé ; celui de Deepotus part (ready)",
      st.get(p_rip["id"]) == "scheduled" and st.get(p_deep["id"]) == "ready", str(st))
r = c.get("/api/schedule", headers={"X-Dz-Espace": rip})
check("A3 X-Dz-Espace d'un espace archivé : 409", r.status_code == 409 and "archiv" in r.text, f"{r.status_code} {r.text[:120]}")
check("A4 un espace archivé ne s'active pas", c.post(f"/api/espaces/{rip}/activate").status_code == 400)
check("A5 un espace archivé s'exporte encore (remise au client)", c.get(f"/api/espaces/{rip}/export").status_code == 200)
rd2 = c.post(f"/api/espaces/{rip}/archive", json={"archive": False})
asyncio.run(MK.tick([datetime.utcnow().strftime("%Y-%m-%d")]))
st = {p["id"]: p["status"] for p in c.get("/api/schedule?espace=*").json()}
check("A6 désarchivé : le post reprend (ready)", rd2.status_code == 200 and st.get(p_rip["id"]) == "ready", str(st))
check("A7 Deepotus intact : actif, persona livré + repère", ES.lire()["actif"] == "deepotus" and DEEP in ES.persona("deepotus")["vibe_keywords"])

# ---- [U] l'écran (maillon dzespace) -----------------------------------------------------------------------------------
print("[U] écran : Réglages › Espaces")
import re                                                              # noqa: E402
BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(encoding="utf-8-sig")
SITES = {
    "U1 « Exporter » : un lien de téléchargement par espace": 'r.jsx("a",{href:base(e.id)+"/export",download:"","data-dz-espace-exporter":e.id,',
    "U2 « Importer un espace… » : un fichier .zip": '"data-dz-espace-importer":"1"',
    "U3 l'import poste le fichier en FormData": 'fetch("/api/espaces/importer",{method:"POST",body:fd})',
    "U4 l'import dit l'espace, les secrets à ressaisir, les entrées ignorées":
        'maj({msg:dzT("espaces.import.fait",{nom:(j.espace||{}).nom||""})+(n?" "+dzT("espaces.import.ressaisir",{n:n}):"")'
        '+(ig?" "+dzT("espaces.import.ignores",{n:ig}):"")})',
    "U5 l'archivage dit les posts mis en pause": 'ar&&j&&j.en_pause&&maj({msg:dzT("espaces.archive.en_pause",{n:j.en_pause,nom:e.nom})})',
    "U6 le message est annoncé (role=status)": 'st.msg&&r.jsx("div",{role:"status","data-dz-espace-msg":"1"',
    "U11 la dépense d'un espace neuf ou importé recharge le mois (plafond repris visible)": 'dzDepCharger(!dzDepD||!(dzDepD.par_espace||{})[esp])',
}
for nom, motif in SITES.items():
    check(nom, BUNDLE.count(motif) == 1, str(BUNDLE.count(motif)))
check("U7 aucun useState ajouté, v2.8.0 intact", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4)
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "espaces.json").read_text(encoding="utf-8"))
cles = sorted(set(re.findall(r'dzT\("(espaces\.[a-z_.0-9]+)"', BUNDLE)))
manquent = [k for k in cles if not k.endswith(".") and not (DICO.get(k, {}).get("fr") and DICO.get(k, {}).get("en"))]
manquent += [k for k in cles if k.endswith(".") and not any(d.startswith(k) for d in DICO)]   # préfixes composés
check("U8 toutes les clés « espaces.* » du bundle sont traduites FR et EN", not manquent and len(cles) > 100, str(manquent))
neuves = ["espaces.action.exporter", "espaces.export.aide", "espaces.import.bouton", "espaces.import.aide",
          "espaces.import.fait", "espaces.import.ressaisir", "espaces.import.ignores", "espaces.archive.en_pause"]
check("U9 les clés neuves gardent leurs variables dans les deux langues",
      all(all(v in DICO[k]["en"] for v in re.findall(r"\{\w+\}", DICO[k]["fr"])) for k in neuves))
sys.path.insert(0, str(RACINE / "scripts"))
import patch_bundle_dzespace as DZE                                     # noqa: E402
try:
    avant = DZE.defaire(BUNDLE)
except AssertionError as e:
    avant = str(e)
check("U10 l'inverse du maillon retire tout l'écran t210, aller-retour exact",
      "data-dz-espace-exporter" not in avant and "espaces.import." not in avant and DZE.appliquer(avant) == BUNDLE, avant[:120])

c.__exit__(None, None, None)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
