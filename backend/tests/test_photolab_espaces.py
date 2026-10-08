# -*- coding: utf-8 -*-
"""t151 (Photolab parité L1) — espaces de travail : le service photolab_espaces et les routes /api/photolab/espaces.
[1] service : état par défaut, validation STRICTE (liste blanche des groupes, onglets, espaces, bornes des noms),
    lecture tolérante (fichier absent ou corrompu -> défaut), écriture atomique (aucun fichier temporaire laissé).
[2] routes GET / PUT : aller-retour, 400 sur un corps refusé (le fichier n'est pas touché), garde des écritures hors
    de la boucle locale (403).
[3] la copie JavaScript (frontend/photolab/js/mod-espaces.js) a les MÊMES groupes, onglets et espaces fournis.
Run : & $PY -X utf8 tests/test_photolab_espaces.py   (depuis backend/)"""
import asyncio, copy, json, os, pathlib, re, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt151_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
sys.path.insert(0, str(BACKEND))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:400]}")


from app.services import photolab_espaces as E      # noqa: E402

DISP = {"colonnes": 1, "outils": "base", "options": True, "barreOutils": True,
        "groupes": [{"id": "calques", "etat": "ouvert", "onglet": "historique"},
                    {"id": "couleur", "etat": "replie", "onglet": "couleur"},
                    {"id": "proprietes", "etat": "masque", "onglet": "ajustements"}]}
ETAT = {"version": 1, "actif": "perso-a1", "verrouille": True,
        "modifs": {"peinture": DISP}, "perso": [{"id": "perso-a1", "nom": "Mon atelier", "disposition": DISP}]}


def refuse(obj):
    try:
        E.valider(obj)
        return False
    except ValueError:
        return True


def service():
    print("\n[1] service")
    d = E.etat_defaut()
    check("1a défaut : Essentiel actif, non verrouillé, aucun changement ni espace personnel",
          d == {"version": 1, "actif": "essentiel", "verrouille": False, "modifs": {}, "perso": []}, d)
    check("1b sept espaces fournis, dans l'ordre de la décision Q1",
          E.FOURNIS == ("essentiel", "base", "graphisme", "mouvement", "peinture", "photo", "pixel"), E.FOURNIS)
    check("1c groupes et onglets", E.GROUPES == {"couleur": ("couleur",), "proprietes": ("proprietes", "ajustements"),
          "pinceaux": ("pinceaux", "parametres", "source", "predefinis"), "calques": ("calques", "historique", "navigateur")}, E.GROUPES)
    check("1d un état complet est admis tel quel", E.valider(copy.deepcopy(ETAT)) == ETAT)
    mauvais = []
    def m(chemin, f):
        o = copy.deepcopy(ETAT); f(o); mauvais.append((chemin, o))
    m("clé inconnue", lambda o: o.update(zorg=1))
    m("version", lambda o: o.update(version=2))
    m("actif inconnu", lambda o: o.update(actif="atelier"))
    m("actif perso absent", lambda o: o.update(actif="perso-zz"))
    m("verrouille non booléen", lambda o: o.update(verrouille=1))
    m("modifs : espace inconnu", lambda o: o["modifs"].update({"zorg": DISP}))
    m("modifs : perso absent", lambda o: o["modifs"].update({"perso-zz": DISP}))
    m("groupe inconnu", lambda o: o["perso"][0]["disposition"]["groupes"].append({"id": "nuancier", "etat": "ouvert", "onglet": "nuancier"}))
    m("groupe en double", lambda o: o["perso"][0]["disposition"]["groupes"].append({"id": "calques", "etat": "ouvert", "onglet": "calques"}))
    m("onglet d'un autre groupe", lambda o: o["perso"][0]["disposition"]["groupes"][0].update(onglet="couleur"))
    m("état de groupe inconnu", lambda o: o["perso"][0]["disposition"]["groupes"][0].update(etat="flottant"))
    m("clé de groupe inconnue", lambda o: o["perso"][0]["disposition"]["groupes"][0].update(largeur=300))
    m("colonnes 3", lambda o: o["perso"][0]["disposition"].update(colonnes=3))
    m("outils inconnu", lambda o: o["perso"][0]["disposition"].update(outils="tout"))
    m("options non booléen", lambda o: o["perso"][0]["disposition"].update(options="oui"))
    m("disposition : clé inconnue", lambda o: o["perso"][0]["disposition"].update(css="body{}"))
    m("nom vide", lambda o: o["perso"][0].update(nom="   "))
    m("nom de 65 caractères", lambda o: o["perso"][0].update(nom="x" * 65))
    m("nom avec saut de ligne", lambda o: o["perso"][0].update(nom="a\nb"))
    m("id perso mal formé", lambda o: o["perso"][0].update(id="perso-A/1"))
    m("id perso en double", lambda o: o["perso"].append(copy.deepcopy(o["perso"][0])))
    m("nom en double (sans casse)", lambda o: o["perso"].append({"id": "perso-b2", "nom": "MON ATELIER", "disposition": DISP}))
    m("nom d'un espace fourni", lambda o: o["perso"].append({"id": "perso-b2", "nom": "Peinture", "disposition": DISP}))
    m("21 espaces personnels", lambda o: o.update(perso=[{"id": f"perso-{i}", "nom": f"E{i}", "disposition": DISP} for i in range(21)], actif="essentiel", modifs={}))
    m("perso : clé inconnue", lambda o: o["perso"][0].update(chemin="C:/x"))
    m("pas un objet", lambda o: o.clear() or o.update(version=1))
    for nom, o in mauvais:
        check(f"1e refusé : {nom}", refuse(o))
    check("1f refusé : une liste, une chaîne", refuse([]) and refuse("x"))
    o = copy.deepcopy(ETAT); o["perso"][0]["nom"] = "  Mon atelier  "
    check("1g le nom est rendu sans espaces autour", E.valider(o)["perso"][0]["nom"] == "Mon atelier")
    o = copy.deepcopy(ETAT); o["perso"][0]["disposition"]["groupes"] = []
    check("1h une disposition peut omettre des groupes (ceux d'un lot futur s'ajoutent à la lecture)", not refuse(o))
    f = E.chemin()
    check("1i fichier dans <données>/photolab/espaces.json", f == pathlib.Path(os.environ["DEEPOTUS_DATA_DIR"]) / "photolab" / "espaces.json", f)
    if f.exists():
        f.unlink()
    check("1j lire sans fichier -> défaut", E.lire() == E.etat_defaut())
    E.ecrire(copy.deepcopy(ETAT))
    check("1k écrire puis lire -> même état", E.lire() == ETAT)
    check("1l aucun fichier temporaire laissé", sorted(p.name for p in f.parent.iterdir() if p.name.startswith("espaces")) == ["espaces.json"],
          [p.name for p in f.parent.iterdir()])
    f.write_text("{ pas du json", encoding="utf-8")
    check("1m fichier corrompu -> défaut (jamais d'exception)", E.lire() == E.etat_defaut())
    f.write_text(json.dumps({**ETAT, "zorg": 1}), encoding="utf-8")
    check("1n fichier refusé par la validation -> défaut", E.lire() == E.etat_defaut())
    try:
        E.ecrire({"version": 1, "actif": "zorg"})
        check("1o écrire un état refusé lève ValueError", False)
    except ValueError:
        check("1o écrire un état refusé lève ValueError (fichier inchangé)", json.loads(f.read_text(encoding="utf-8")).get("zorg") == 1)


async def routes():
    print("\n[2] routes")
    import httpx
    from app.main import app
    E.chemin().unlink(missing_ok=True)
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/espaces")
        check("2a GET sans fichier -> 200, défaut", r.status_code == 200 and r.json() == E.etat_defaut(), (r.status_code, r.text[:200]))
        r = await c.put("/api/photolab/espaces", json=ETAT)
        check("2b PUT d'un état valide -> 200, l'état rendu", r.status_code == 200 and r.json() == ETAT, (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/espaces")
        check("2c GET relit ce qui a été écrit", r.json() == ETAT)
        avant = E.chemin().read_bytes()
        r = await c.put("/api/photolab/espaces", json={**ETAT, "actif": "zorg"})
        check("2d PUT refusé -> 400 qui dit pourquoi", r.status_code == 400 and "actif" in r.text, (r.status_code, r.text[:200]))
        check("2e … et le fichier n'est pas touché", E.chemin().read_bytes() == avant)
        r = await c.put("/api/photolab/espaces", content=b"[1,2]", headers={"content-type": "application/json"})
        check("2f PUT d'une liste -> 400 ou 422", r.status_code in (400, 422), r.status_code)
    t2 = httpx.ASGITransport(app=app, client=("192.168.1.20", 50000))
    async with httpx.AsyncClient(transport=t2, base_url="http://t") as c:
        r = await c.put("/api/photolab/espaces", json=E.etat_defaut())
        check("2g PUT depuis le réseau local -> refusé (401 jeton d appairage, ou 403 garde des écritures)", r.status_code in (401, 403), r.status_code)
        check("2h … fichier inchangé", E.chemin().read_bytes() == avant)


def copie_js():
    print("\n[3] copie JavaScript")
    src = (RACINE / "frontend/photolab/js/mod-espaces.js").read_text(encoding="utf-8")
    m = re.search(r"export const GROUPES = (\{[^;]*\});", src)
    js = json.loads(re.sub(r"(\w+):", r'"\1":', m.group(1))) if m else None
    check("3a GROUPES identiques", js == {k: list(v) for k, v in E.GROUPES.items()}, js)
    m = re.search(r"export const FOURNIS = (\[[^\]]*\]);", src)
    check("3b FOURNIS identiques", m and json.loads(m.group(1)) == list(E.FOURNIS), m and m.group(1))
    m = re.search(r"export const MAX_PERSO = (\d+);", src)
    check("3c MAX_PERSO identique", m and int(m.group(1)) == E.MAX_PERSO)


try:
    service()
    asyncio.run(routes())
    copie_js()
finally:
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
