# -*- coding: utf-8 -*-
"""t191 (G9, plan « Génération IA ») — Photolab : calque IA et détourage NON destructif, le pont.

  [0] refus GRATUITS : sans document ouvert -> 409 ; calque inconnu -> 404 ; sans FAL_KEY pour un modèle fal -> 503
      (AVANT tout appel payant, message traduit par Accept-Language) ; prompt vide, format, modèle vectoriel -> 400 ;
      refus du DÉTOURAGE (modèle inconnu, clé absente, sujet exigé) AVANT la génération ; zéro ligne de dépense, zéro
      appel d'espion sur chaque refus
  [1] espions : IP.generate (façade) appelé avec model/size, FLUX par la route ; detourage.detourer_image appelé
      seulement si detourer=True ; une ligne `depenses` par tir réussi, montant == devis == `usd` rendu
  [2] séquence moteur EXACTE : layer.select(auDessusDe) -> placer(objet_dynamique=False) -> layer.renameLayer("IA — …") ;
      calque de PIXELS juste au-dessus ; Annuler en DEUX étapes (Renommer, Coller) ; détourage échoué après la
      génération payée : image posée telle quelle, `detourEchec` le dit ; pose impossible : le message garde le nom
  [3] /calque/detourer : exporter -> détourer -> placer -> setProps(visible=False) sur l'original ; l'original N'EST PAS
      supprimé ; la copie détourée retombe pile à sa place ; échec du fournisseur : document intact
  [4] plafond : 402 sans X-DZ-Plafond quand le budget est dépassé (rien de tiré, rien d'inscrit), confirmé -> 200 ;
      PAYANTES (test_plafonds_garde) liste les deux routes, le recensement AST les voit gardées
  [5] test_photolab_textes : aucune chaîne française hors dictionnaire (mod-iacalque.js compris)
Le VRAI moteur photocraft-cli 0.3.0 (vendor/) ; les fournisseurs sont des espions — aucun httpx sortant.
Run : & $PY tests/test_photolab_iacalque.py   (depuis backend/)"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt191_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
from loguru import logger                                       # noqa: E402
logger.remove()
import httpx                                                    # noqa: E402
from PIL import Image                                           # noqa: E402
from app.services import photolab_moteur as PM                  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


# ── le vrai moteur ──
PM.fermer()
PM.FABRIQUE = None
try:
    PM.chemin_cli()
except PM.MoteurAbsent as e:
    check("le binaire photocraft-cli 0.3.0 est présent (vendor/)", False, e)
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

from app.main import app                                        # noqa: E402
from app.api import routes as R                                 # noqa: E402
from app.config import settings                                 # noqa: E402
from app.services import detourage as DT, image_providers as IP, plafonds as P, pricing as PR  # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db   # noqa: E402
from sqlalchemy import select                                   # noqa: E402

# ── espions ──
journal = []                                    # (méthode, params) de chaque échange avec le moteur, dans l'ordre
_echange0 = PM.SessionMoteur._echange


def _echange(self, proc, lignes, methode, params, delai):
    journal.append((methode, json.loads(json.dumps(params or {}))))
    return _echange0(self, proc, lignes, methode, params, delai)


PM.SessionMoteur._echange = _echange
appels = {"flux": [], "facade": [], "detour": [], "placer": []}
pannes = {"detour": None, "placer": None}
compteur = [0]


def _png(taille, couleur):
    compteur[0] += 1
    nom = f"gen_banc{compteur[0]:04d}.png"
    Image.new("RGBA", taille, couleur).save(settings.images_path / nom)
    return nom


async def _faux_flux(prompt, size, n, seed=None, **k):
    appels["flux"].append((prompt, size, n))
    return {"images": [_png((400, 200), (0, 160, 0, 255))], "seed": 1}


async def _faux_generate(provider, prompt, size, n=1, **k):
    appels["facade"].append((provider, prompt, size, n))
    return {"images": [_png((400, 200), (0, 0, 200, 255))], "seed": None}


async def _faux_detour(mid, chemin, prompt=None, dossier=None):
    appels["detour"].append((mid, pathlib.Path(chemin).name, prompt))
    if pannes["detour"]:
        raise pannes["detour"]
    with Image.open(chemin) as im:
        w, h = im.size
    return _png((w, h), (255, 255, 0, 128))


_placer0 = PM.placer


def _placer(s, chemin, nom, objet_dynamique=True, reduire=True, centre=None):
    appels["placer"].append({"chemin": chemin, "nom": nom, "objet_dynamique": objet_dynamique, "reduire": reduire,
                             "centre": centre})
    if pannes["placer"]:
        raise pannes["placer"]
    return _placer0(s, chemin, nom, objet_dynamique, reduire, centre)


R._flux_generate = _faux_flux
IP.generate = _faux_generate
DT.detourer_image = _faux_detour
PM.placer = _placer
sortants = []
_send0 = httpx.AsyncClient.send


async def _send(self, request, *a, **k):
    if request.url.host != "t":
        sortants.append(str(request.url))
        raise RuntimeError("httpx sortant interdit au banc")
    return await _send0(self, request, *a, **k)


httpx.AsyncClient.send = _send
settings.FAL_KEY = "cle-de-banc"
settings.OPENAI_API_KEY = "cle-openai-de-banc"
asyncio.run(init_db())


def nb_appels():
    return sum(len(v) for k, v in appels.items() if k != "placer")


def devis(ops):
    return round(PR.estimate({"kind": "campaign", "ops": ops})["total_usd"], 6)


def a_plat(layers):
    for c in layers or []:
        yield c
        yield from a_plat(c.get("children"))


def commandes(depuis):
    return [(m, p) for m, p in journal[depuis:]]


async def scenario():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        async def lire_lignes():
            async with async_session_factory() as s:
                return (await s.execute(select(Depense).order_by(Depense.id))).scalars().all()

        IA = "/api/photolab/calque/ia"
        DET = "/api/photolab/calque/detourer"
        base = {"prompt": "un phare sous la pluie battante", "modele": "flux", "taille": "landscape_16_9", "auDessusDe": 3}

        print("\n[0] refus gratuits")
        r = await c.post(IA, json=base)
        check("0.1 sans document ouvert -> 409, aucun appel", r.status_code == 409 and nb_appels() == 0, (r.status_code, r.text))
        r = await c.post(DET, json={"layer": 3, "modele": "bria-rmbg"})
        check("0.2 /calque/detourer sans document -> 409", r.status_code == 409 and nb_appels() == 0, (r.status_code, r.text))
        # le document : fond blanc 200×100, « Layer 1 » (id 3) = rectangle rouge (10, 20, 50×40), « Layer 2 » (id 4) vide
        s = PM.session()
        s.appeler("doc.new", {"width": 200, "height": 100, "background": "white"})
        ex = lambda cmd, **p: s.appeler("engine.execute", {"command": cmd, "params": p})
        ex("layer.new.layer"); ex("layer.new.layer")
        ex("layer.select", layer=3)
        ex("select.rect", x=10, y=20, width=50, height=40)
        ex("edit.fill", contents="color", color="#ff0000")
        ex("select.deselect")
        i0 = s.appeler("doc.inspect")
        check("0.3 document de banc : Layer 1 (3) au rectangle [10, 20, 50, 40]",
              next(x for x in i0["layers"] if x["id"] == 3).get("bounds") == [10, 20, 50, 40], i0["layers"])
        r = await c.post(IA, json={**base, "auDessusDe": 999})
        check("0.4 calque inconnu -> 404, aucun appel", r.status_code == 404 and "999" in r.text and nb_appels() == 0,
              (r.status_code, r.text))
        for corps, motif in (({**base, "prompt": "   "}, "prompt"), ({**base, "taille": "a4"}, "a4"),
                             ({**base, "modele": "recraft-4.1-vecteur"}, "SVG"), ({**base, "modele": "zorg"}, "zorg"),
                             ({**base, "auDessusDe": "3"}, "3"), ({**base, "zorglub": 1}, "zorglub"),
                             ({**base, "detourer": "oui"}, "detourer")):
            r = await c.post(IA, json=corps)
            check(f"0.5 400 « {motif} » sans appel ({list(set(corps) ^ set(base)) or 'prompt'})",
                  r.status_code == 400 and motif in r.text and nb_appels() == 0, (r.status_code, r.text))
        settings.FAL_KEY = ""
        r = await c.post(IA, json=base)
        check("0.6 sans FAL_KEY, modèle fal -> 503 qui nomme la clé, AVANT tout appel", r.status_code == 503
              and "FAL_KEY" in r.text and nb_appels() == 0, (r.status_code, r.text))
        r = await c.post(IA, json=base, headers={"Accept-Language": "en-US,en;q=0.9"})
        check("0.7 le même refus en anglais (Accept-Language)", r.status_code == 503 and "not configured" in r.text,
              (r.status_code, r.text))
        # le DÉTOURAGE refusé AVANT la génération payée : l'image (OpenAI) a sa clé, le détourage fal ne l'a pas
        r = await c.post(IA, json={**base, "modele": "gpt-image-1", "detourer": True, "modeleDetour": "bria-rmbg"})
        check("0.8 clé du détourage absente -> 503 (FAL_KEY), la génération (clé présente) n'est PAS tirée",
              r.status_code == 503 and "FAL_KEY" in r.text and nb_appels() == 0, (r.status_code, r.text))
        r = await c.post(DET, json={"layer": 3, "modele": "bria-rmbg"})
        check("0.9 /calque/detourer sans FAL_KEY -> 503, rien d'exporté", r.status_code == 503 and nb_appels() == 0
              and not any(m == "doc.save" for m, _ in journal), (r.status_code, r.text))
        settings.FAL_KEY = "cle-de-banc"
        for corps, motif in (({**base, "detourer": True, "modeleDetour": "zorg"}, "zorg"),
                             ({**base, "detourer": True}, "inconnu"),
                             ({**base, "detourer": True, "modeleDetour": "birefnet-v2-video"}, "BiRefNet"),
                             ({**base, "detourer": True, "modeleDetour": "sam3-sujet"}, "sujet")):
            r = await c.post(IA, json=corps)
            check(f"0.10 détourage refusé AVANT la génération (« {motif} ») -> 400, zéro appel",
                  r.status_code == 400 and motif in r.text and nb_appels() == 0, (r.status_code, r.text))
        for corps, code in (({"layer": 999, "modele": "bria-rmbg"}, 404), ({"layer": 4, "modele": "bria-rmbg"}, 400),
                            ({"layer": 3, "modele": "sam3-sujet"}, 400), ({"layer": 3, "modele": "zorg"}, 400)):
            r = await c.post(DET, json=corps)
            check(f"0.11 /calque/detourer {corps} -> {code} sans appel", r.status_code == code and nb_appels() == 0,
                  (r.status_code, r.text))
        check("0.12 aucune ligne de dépense après tous ces refus", await lire_lignes() == [], len(await lire_lignes()))

        print("\n[1] espions et dépense")
        n0 = len(journal)
        hist0 = len(s.appeler("doc.inspect")["history"])
        r = await c.post(IA, json=base)
        j = r.json() if r.status_code == 200 else {}
        d1 = devis([{"kind": "image", "n": 1, "model": "flux"}])
        L = await lire_lignes()
        check("1.1 tir FLUX : 200, FLUX tiré par la route (prompt, format, n=1), façade et détourage NON appelés",
              r.status_code == 200 and appels["flux"] == [(base["prompt"], "landscape_16_9", 1)]
              and appels["facade"] == [] and appels["detour"] == [], (r.status_code, r.text, appels))
        check("1.2 une ligne de dépense : photolab, montant == devis == usd rendu", len(L) == 1 and L[0].categorie == "photolab"
              and abs(L[0].estime_usd - d1) < 1e-9 and abs(j.get("usd", -1) - d1) < 1e-9,
              ([(l.categorie, l.estime_usd) for l in L], d1, j))
        check("1.3 la réponse : layer, bounds [x, y, w, h], image de la Bibliothèque", isinstance(j.get("layer"), int)
              and isinstance(j.get("bounds"), list) and len(j["bounds"]) == 4 and (settings.images_path / j.get("image", "-")).is_file(), j)

        print("\n[2] séquence moteur")
        cmds = [(p.get("command"), p.get("params")) for m, p in commandes(n0) if m == "engine.execute"]
        noms = [x[0] for x in cmds]
        k_sel = next((k for k, (cm, pa) in enumerate(cmds) if cm == "layer.select" and pa.get("layer") == 3), -1)
        k_col = noms.index("edit.paste") if "edit.paste" in noms else -1
        k_ren = noms.index("layer.renameLayer") if "layer.renameLayer" in noms else -1
        check("2.1 layer.select(auDessusDe=3) -> edit.paste -> layer.renameLayer, dans cet ordre",
              0 <= k_sel < k_col < k_ren, noms)
        check("2.2 nom « IA — <15 premiers caractères du prompt> »", k_ren >= 0
              and cmds[k_ren][1].get("name") == "IA — " + base["prompt"][:15] == j.get("nom"), cmds[k_ren] if k_ren >= 0 else noms)
        check("2.3 placer(objet_dynamique=False) : un calque de PIXELS, jamais d'objet dynamique",
              [a["objet_dynamique"] for a in appels["placer"]] == [False]
              and "layer.smartObjects.convertToSmartObject" not in noms, (appels["placer"], noms))
        i1 = s.appeler("doc.inspect")
        ids = [x["id"] for x in i1["layers"]]
        neuf = next((x for x in i1["layers"] if x["id"] == j.get("layer")), {})
        check("2.4 le nouveau calque est JUSTE au-dessus de Layer 1 (3), en pixels, à la taille de la toile (réduit)",
              j.get("layer") in ids and ids.index(j["layer"]) + 1 == ids.index(3) and neuf.get("kind") == "Pixel"
              and neuf.get("bounds") == [0, 0, 200, 100] and i1["activeLayer"] == j["layer"], (ids, neuf))
        check("2.5 Annuler en DEUX étapes : l'historique gagne exactement « Paste », « Rename Layer »",
              i1["history"][hist0:] == ["Paste", "Rename Layer"], i1["history"][hist0:])
        r = await c.post("/api/photolab/historique", json={"annuler": 2})
        i2 = r.json().get("inspect", {}) if r.status_code == 200 else {}
        check("2.6 deux annulations retirent le calque IA, le document revient tel qu'avant",
              j.get("layer") not in [x["id"] for x in i2.get("layers", [])] and len(i2.get("history", [])) == hist0, i2.get("history"))
        # détourage demandé, via la façade : les deux espions, la campagne entière au devis
        n_l = len(await lire_lignes())
        r = await c.post(IA, json={**base, "modele": "nano-banana-2.1", "taille": "square_hd", "detourer": True,
                                   "modeleDetour": "bria-rmbg", "nom": "Mon calque"})
        j = r.json() if r.status_code == 200 else {}
        d2 = devis([{"kind": "image", "n": 1, "model": "nano-banana-2.1"}, DT.op_cout("bria-rmbg", images=1)])
        L = (await lire_lignes())[n_l:]
        check("2.7 façade appelée avec model/size, détourage appelé UNE fois (bria-rmbg), image détourée posée",
              r.status_code == 200 and [a[0] for a in appels["facade"]] == ["nano-banana-2.1"]
              and appels["facade"][0][2] == "square_hd" and [a[0] for a in appels["detour"]] == ["bria-rmbg"]
              and "detourEchec" not in j, (r.status_code, r.text, appels))
        check("2.8 dépense image + détourage : somme des lignes == devis de la campagne == usd", r.status_code == 200
              and abs(sum(l.estime_usd for l in L) - d2) < 1e-9 and abs(j.get("usd", -1) - d2) < 1e-9 and len(L) == 2,
              ([l.estime_usd for l in L], d2, j.get("usd")))
        check("2.9 « nom » donné : le calque le porte", any(x.get("name") == "Mon calque" for x in s.appeler("doc.inspect")["layers"]))
        # le détourage échoue APRÈS la génération payée : l'image est posée telle quelle, et c'est dit
        pannes["detour"] = RuntimeError("fal.ai : 502 Bad Gateway")
        nf = len(appels["flux"])
        r = await c.post(IA, json={**base, "detourer": True, "modeleDetour": "bria-rmbg"})
        pannes["detour"] = None
        j = r.json() if r.status_code == 200 else {}
        check("2.10 détourage en échec après la génération : 200, image NON détourée posée, detourEchec le dit",
              r.status_code == 200 and len(appels["flux"]) == nf + 1 and "502" in j.get("detourEchec", "")
              and j.get("image") == f"gen_banc{compteur[0]:04d}.png" and isinstance(j.get("layer"), int), (r.status_code, r.text))
        # le moteur refuse la pose : le message dit que l'image est gardée, avec son nom
        pannes["placer"] = PM.MoteurErreur("no such layer")
        r = await c.post(IA, json=base)
        pannes["placer"] = None
        garde = f"gen_banc{compteur[0]:04d}.png"
        check("2.11 pose impossible : 422 dont le message garde le nom de l'image (Bibliothèque)", r.status_code == 422
              and garde in r.text and (settings.images_path / garde).is_file(), (r.status_code, r.text))

        print("\n[3] /calque/detourer : non destructif")
        i_av = s.appeler("doc.inspect")
        hist0 = len(i_av["history"])
        n0, nd = len(journal), len(appels["detour"])
        r = await c.post(DET, json={"layer": 3, "modele": "bria-rmbg"})
        j = r.json() if r.status_code == 200 else {}
        seq = []
        for m, p in commandes(n0):
            if m == "doc.save" and str(p.get("path", "")).startswith("exports/"):
                seq.append("exporter")
            elif m == "engine.execute" and p.get("command") == "edit.paste":
                seq.append("placer")
            elif m == "engine.execute" and p.get("command") == "layer.setProps" and p["params"].get("layer") == 3:
                seq.append("masquer" if p["params"].get("visible") is False else "setProps?")
            elif m == "engine.execute" and p.get("command") in ("layer.delete", "layer.mergeDown", "layer.mergeLayers"):
                seq.append("SUPPRIMER")
        check("3.1 exporter -> détourer -> placer -> masquer l'original, rien de supprimé",
              r.status_code == 200 and seq == ["exporter", "placer", "masquer"] and len(appels["detour"]) == nd + 1,
              (r.status_code, r.text, seq))
        i3 = s.appeler("doc.inspect")
        orig = next((x for x in i3["layers"] if x["id"] == 3), None)
        neuf = next((x for x in i3["layers"] if x["id"] == j.get("layer")), {})
        ids = [x["id"] for x in i3["layers"]]
        check("3.2 l'original EXISTE toujours, masqué, juste sous la copie détourée",
              orig is not None and orig.get("visible") is False and j.get("layer") in ids
              and ids.index(j["layer"]) + 1 == ids.index(3), (ids, orig))
        check("3.3 la copie détourée retombe pile à la place de l'original ([10, 20, 50, 40]), en pixels",
              neuf.get("bounds") == [10, 20, 50, 40] and neuf.get("kind") == "Pixel" and j.get("original") == 3, neuf)
        check("3.4 Annuler en TROIS étapes (Paste, Rename Layer, puis le masquage)", len(i3["history"]) - hist0 == 3
              and i3["history"][hist0:hist0 + 2] == ["Paste", "Rename Layer"], i3["history"][hist0:])
        check("3.5 aucun export ne traîne sous exports/", not any((PM.dossier_travail() / "exports").iterdir()),
              list((PM.dossier_travail() / "exports").iterdir()))
        L = await lire_lignes()
        check("3.6 une ligne de dépense au devis du détourage", bool(L) and r.status_code == 200 and abs(L[-1].estime_usd - devis([DT.op_cout("bria-rmbg", images=1)])) < 1e-9
              and abs(j.get("usd", -1) - L[-1].estime_usd) < 1e-9, ([l.estime_usd for l in L[-1:]], j.get("usd")))
        hist1, n0 = len(i3["history"]), len(journal)
        pannes["detour"] = RuntimeError("fal.ai : 502")
        r = await c.post(DET, json={"layer": 3, "modele": "bria-rmbg"})
        pannes["detour"] = None
        i4 = s.appeler("doc.inspect")
        check("3.7 fournisseur en échec : 502 qui le nomme, document intact (aucun collage, aucun masquage)",
              r.status_code == 502 and "Bria" in r.text and len(i4["history"]) == hist1
              and not any(p.get("command") in ("edit.paste", "layer.setProps") for m, p in commandes(n0) if m == "engine.execute"),
              (r.status_code, r.text, i4["history"][hist1:]))

        print("\n[4] plafond")
        nb, nl = nb_appels(), len(await lire_lignes())
        P.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
        try:
            r = await c.post(IA, json=base)
            d = (r.json().get("detail") or {}) if r.status_code == 402 else {}
            check("4.1 budget dépassé : 402 dz_plafond, catégorie photolab, rien de tiré ni d'inscrit", r.status_code == 402
                  and isinstance(d, dict) and d.get("dz_plafond", {}).get("categorie") == "photolab"
                  and nb_appels() == nb and len(await lire_lignes()) == nl, (r.status_code, r.text))
            r = await c.post(DET, json={"layer": 3, "modele": "bria-rmbg"})
            check("4.2 /calque/detourer : 402 aussi, rien d'exporté ni de détouré", r.status_code == 402 and nb_appels() == nb,
                  (r.status_code, r.text))
            r = await c.post(IA, json=base, headers={"X-DZ-Plafond": "confirme"})
            check("4.3 confirmé (X-DZ-Plafond: confirme) : 200 et UN tir", r.status_code == 200 and nb_appels() == nb + 1,
                  (r.status_code, r.text))
        finally:
            P.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
        import _recensement_payant as RP
        rec = RP.recenser()
        cles = [("photolab", "POST", "/calque/ia"), ("photolab", "POST", "/calque/detourer")]
        check("4.4 le recensement AST voit les deux routes : un puits payant atteint, la garde appelée",
              all(k in rec and rec[k]["puits"] and rec[k]["garde"] for k in cles), {k: rec.get(k) for k in cles})
        src = (BACKEND / "tests" / "test_plafonds_garde.py").read_text("utf-8")
        check("4.5 PAYANTES (test_plafonds_garde) liste les deux routes", all("(" + ", ".join(f'"{x}"' for x in k) + ")" in src for k in cles), cles)
        r = await c.post(IA, json=base)
        check("4.6 hors plafond : la route reste ouverte à la boucle locale", r.status_code == 200, r.status_code)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("192.168.1.20", 5000)), base_url="http://t") as c2:
        nb = nb_appels()
        r = await c2.post("/api/photolab/calque/ia", json={"prompt": "x", "auDessusDe": 3})
        check("4.7 hors boucle locale : refusé (403/401) sans aucun appel", r.status_code in (401, 403) and nb_appels() == nb,
              (r.status_code, r.text[:120]))
    check("4.8 aucun httpx sortant pendant tout le banc", sortants == [], sortants)


try:
    asyncio.run(scenario())
finally:
    PM.fermer()
    PM.SessionMoteur._echange = _echange0

print("\n[5] textes")
r = subprocess.run([sys.executable, "-X", "utf8", str(BACKEND / "tests" / "test_photolab_textes.py")], capture_output=True,
                   text=True, encoding="utf-8", cwd=str(BACKEND))
check("5.1 mod-iacalque.js existe et test_photolab_textes passe (aucune chaîne française hors dictionnaire)",
      (BACKEND.parent / "frontend" / "photolab" / "js" / "mod-iacalque.js").is_file() and r.returncode == 0,
      (r.stdout or "")[-600:])
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
