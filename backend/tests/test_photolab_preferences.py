# t159 (Photolab parité L9) : préférences de l'écran, raccourcis, menus, préréglages — le pont.
# [1] schéma et défauts (copie JavaScript comparée) ; [2] liste blanche des préférences (refus) ; [3] fichier (lire,
# écrire, réinitialiser) ; [4] préréglages : gestionnaire et échange sous liste blanche ; [5] vrai moteur (gestionnaire,
# export / import, Placer sans objet dynamique ni réduction) ; [6] routes.
# Lancement : python embarqué, `python tests/test_photolab_preferences.py` (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt159_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
from app.services import photolab_preferences as PF           # noqa: E402
from app.services import photolab_registre as PR              # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


def refuse(f, *a):
    try:
        f(*a)
        return False
    except ValueError:
        return True


def node_json(expr):
    mod = (RACINE / "frontend" / "photolab" / "js" / "mod-preferences.js").as_uri()
    r = subprocess.run(["node", "--input-type=module", "-e",
                        f"import * as M from '{mod}'; console.log(JSON.stringify({expr}))"],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"erreur": r.stderr[:400]}


def avec(**modifs):
    """L'état par défaut avec des préférences changées : avec(general={"zoomWithScrollWheel": 1})."""
    e = PF.etat_defaut()
    for s, kv in modifs.items():
        e["prefs"][s] = {**e["prefs"][s], **kv}
    return e


def schema():
    print("\n[1] schéma et défauts")
    d = PF.etat_defaut()
    check("1a 11 sections réglables, 7 explicatives, 18 au total (les 18 entrées du menu)",
          len(PF.SCHEMA) == 11 and len(PF.SECTIONS_EXPLICATIVES) == 7 and len(set(PF.SCHEMA) | set(PF.SECTIONS_EXPLICATIVES)) == 18)
    check("1b défauts de photocraft : grille d'un pouce en 4, repères #4affff, qualité JPG 85, curseur pointe normale",
          d["prefs"]["guidesGridAndSlices"]["gridlineEvery"] == 1.0 and d["prefs"]["guidesGridAndSlices"]["subdivisions"] == 4
          and d["prefs"]["guidesGridAndSlices"]["guideColor"] == "#4affff" and d["prefs"]["export"]["jpegQuality"] == 85
          and d["prefs"]["cursors"]["painting"] == "normalTip")
    check("1c damier « thème » par défaut (l'écran garde son aspect d'avant t159)",
          d["prefs"]["transparencyAndGamut"]["gridColors"] == "theme")
    check("1d le défaut se valide lui-même", PF.valider(d) == d)
    js = node_json("M.SCHEMA")
    py = json.loads(json.dumps({s: {k: list(v) for k, v in c.items()} for s, c in PF.SCHEMA.items()}))
    check("1e mod-preferences.SCHEMA == photolab_preferences.SCHEMA (types, défauts, valeurs, bornes)", js == py, js)
    check("1f mod-preferences.etatDefaut() == photolab_preferences.etat_defaut()", node_json("M.etatDefaut()") == d)
    js_sec = node_json("M.SECTIONS.map(s => s[1])")
    check("1g les 18 sections de l'écran = sections réglables + explicatives",
          isinstance(js_sec, list) and len(js_sec) == 18 and set(js_sec) == set(PF.SCHEMA) | set(PF.SECTIONS_EXPLICATIVES), js_sec)


def refus():
    print("\n[2] liste blanche")
    v = PF.valider
    for e, pourquoi in ((avec(general={"zoomWithScrollWheel": 1}), "booléen = 1"),
                        (avec(interface={"canvasColor": "pink"}), "énumération"),
                        (avec(interface={"canvasCustomColor": "red"}), "couleur nommée"),
                        (avec(interface={"canvasCustomColor": "#12345"}), "couleur courte"),
                        (avec(export={"jpegQuality": 0}), "qualité 0"),
                        (avec(export={"jpegQuality": 85.5}), "qualité non entière"),
                        (avec(export={"quickExportFormat": "gif"}), "gif (le pont ne l'exporte pas)"),
                        (avec(guidesGridAndSlices={"subdivisions": 101}), "subdivisions 101"),
                        (avec(guidesGridAndSlices={"gridlineEvery": 0}), "pas 0"),
                        (avec(guidesGridAndSlices={"gridlineEvery": True}), "pas booléen"),
                        (avec(type={"fontPreview": "off"}), "aperçu off"),
                        ):
        check(f"2a refusé : {pourquoi}", refuse(v, e))
    e = PF.etat_defaut(); e["prefs"]["performance"] = {"historyStates": 50}
    check("2b section inconnue (performance : réglage du moteur) refusée", refuse(v, e))
    e = PF.etat_defaut(); e["prefs"]["general"]["beepWhenDone"] = True
    check("2c clé inconnue refusée", refuse(v, e))
    e = PF.etat_defaut(); e["chemin"] = "C:/x"
    check("2d clé d'état inconnue refusée", refuse(v, e))
    e = PF.etat_defaut(); del e["prefs"]["cursors"]; e["prefs"]["general"] = {}
    r = v(e)
    check("2e clés et sections absentes -> défauts", r["prefs"]["cursors"]["painting"] == "normalTip" and r["prefs"]["general"]["resizeImageDuringPlace"] is True)
    check("2f couleur en majuscules -> minuscules", v(avec(interface={"canvasCustomColor": "#ABCDEF"}))["prefs"]["interface"]["canvasCustomColor"] == "#abcdef")
    ok_r = PF.etat_defaut(); ok_r["raccourcis"] = {"commandes": {"image.adjustments.levels": "ctrl+l", "edit.fill": "shift+f5",
                                                                "layer.new.layer": "", "filter.lastFilter": "ctrl+alt+shift+f"},
                                                   "outils": {"brush": "b", "pencil": "b", "eraser": ""}}
    check("2g raccourcis admis (Ctrl, Alt, Maj+F5, retrait, deux outils sur la même lettre)", v(ok_r)["raccourcis"] == ok_r["raccourcis"])
    for cmd, pourquoi in (({"edit.fill": "f"}, "lettre seule pour une commande"), ({"edit.fill": "shift+f"}, "Maj+lettre"),
                          ({"edit.fill": "ctrl+shift+alt+f"}, "ordre des modificateurs"), ({"edit.fill": "ctrl+ff"}, "touche inconnue"),
                          ({"Edit.fill": "ctrl+k"}, "id mal formé"), ({"edit.fill": "ctrl+k", "edit.clear": "ctrl+k"}, "doublon"),
                          ({"edit.fill": None}, "valeur nulle"), ({"edit.fill": "ctrl+f13"}, "F13")):
        e = PF.etat_defaut(); e["raccourcis"]["commandes"] = cmd
        check(f"2h raccourci refusé : {pourquoi}", refuse(v, e))
    for out, pourquoi in (({"brush": "ctrl+b"}, "combinaison pour un outil"), ({"brush": "1"}, "chiffre"), ({"../x": "b"}, "outil mal formé")):
        e = PF.etat_defaut(); e["raccourcis"]["outils"] = out
        check(f"2i lettre d'outil refusée : {pourquoi}", refuse(v, e))
    e = PF.etat_defaut(); e["menus"] = {"masques": ["filter.blur.gaussianBlur", "filter.blur.gaussianBlur"], "couleurs": {"layer.new.layer": "violet"}}
    check("2j menus admis (doublon replié)", v(e)["menus"] == {"masques": ["filter.blur.gaussianBlur"], "couleurs": {"layer.new.layer": "violet"}})
    for m, pourquoi in (({"masques": ["edit.menus"]}, "Menus… masqué"), ({"masques": ["edit.preferences.general"]}, "Préférences masquées"),
                        ({"couleurs": {"edit.fill": "pink"}}, "couleur inconnue"), ({"masques": "edit.fill"}, "masques en texte"),
                        ({"masques": ["x/y"]}, "id chemin")):
        e = PF.etat_defaut(); e["menus"] = {**e["menus"], **m}
        check(f"2k menus refusés : {pourquoi}", refuse(v, e))
    e = PF.etat_defaut(); e["affichage"] = {"grille": True, "ecran": "plein", "afficher": {"apercuPinceau": False}}
    check("2l affichage repris admis", v(e)["affichage"] == e["affichage"])
    for a, pourquoi in (({"grille": 1}, "booléen = 1"), ({"ecran": "x"}, "écran"), ({"inconnu": True}, "clé"),
                        ({"afficher": {"x": True}}, "sous-clé")):
        e = PF.etat_defaut(); e["affichage"] = a
        check(f"2m affichage refusé : {pourquoi}", refuse(v, e))
    e = PF.etat_defaut(); e["texte"] = {"langue": "type.languageOptions.eastAsianFeatures", "composeur": True}
    check("2n texte admis", v(e)["texte"] == e["texte"])
    e = PF.etat_defaut(); e["texte"] = {"langue": "fr"}
    check("2o texte refusé (langue inconnue)", refuse(v, e))


def fichier():
    print("\n[3] fichier")
    f = PF.chemin()
    check("3a dans le dossier de données : <données>/photolab/preferences.json", f == _tmp / "photolab" / "preferences.json", f)
    r = PF.lire()
    check("3b fichier absent -> défaut, enregistre: false", r == {"etat": PF.etat_defaut(), "enregistre": False}, r)
    e = avec(tools={"overscroll": False})
    PF.ecrire(e)
    r = PF.lire()
    check("3c écrit puis relu, enregistre: true", r["enregistre"] is True and r["etat"]["prefs"]["tools"]["overscroll"] is False)
    check("3d aucun fichier temporaire laissé", [p.name for p in f.parent.glob("preferences-*.tmp")] == [])
    f.write_text('{"version": 1, "prefs": {"general": {"x": 1}}}', encoding="utf-8")
    check("3e fichier refusé -> défaut, enregistre: false", PF.lire() == {"etat": PF.etat_defaut(), "enregistre": False})
    f.write_text("{pas du json", encoding="utf-8")
    check("3f fichier illisible -> défaut", PF.lire()["etat"] == PF.etat_defaut())
    PF.ecrire(e)
    check("3g réinitialiser -> défaut enregistré", PF.reinitialiser() == PF.etat_defaut() and PF.lire()["enregistre"] is True
          and PF.lire()["etat"] == PF.etat_defaut())
    check("3h une écriture refusée ne touche pas au fichier", refuse(PF.ecrire, avec(tools={"overscroll": "non"})) and PF.lire()["etat"] == PF.etat_defaut())


def presets(reg):
    print("\n[4] préréglages sous liste blanche")
    def admis(cid, p):
        try:
            PM.commande_autorisee(cid, p, reg)
            return True
        except ValueError as e:
            return str(e)
    for p in ({"action": "list", "kind": "brushes"}, {"action": "rename", "kind": "patterns", "index": 0, "newName": "Lignes fines"},
              {"action": "delete", "kind": "customShapes", "index": 3}, {"action": "move", "kind": "brushes", "index": 2, "to": 0}):
        check(f"4a gestionnaire admis : {p['action']} {p['kind']}", admis("edit.presets.presetManager", p) is True, admis("edit.presets.presetManager", p))
    for p, pourquoi in (({"action": "list", "kind": "gradients"}, "genre"), ({"action": "erase", "kind": "brushes"}, "action"),
                        ({"action": "rename", "kind": "brushes", "index": 0}, "newName manquant"),
                        ({"action": "rename", "kind": "brushes", "index": 0, "newName": ""}, "nom vide"),
                        ({"action": "rename", "kind": "brushes", "index": 0, "newName": "a\nb"}, "nom sur deux lignes"),
                        ({"action": "rename", "kind": "brushes", "index": 0, "newName": "x" * 65}, "nom trop long"),
                        ({"action": "delete", "kind": "brushes", "index": -1}, "index négatif"),
                        ({"action": "delete", "kind": "brushes", "index": True}, "index booléen"),
                        ({"action": "delete", "kind": "brushes", "name": "Hard Round"}, "par nom"),
                        ({"action": "list", "kind": "brushes", "path": "C:/x"}, "path")):
        check(f"4b gestionnaire refusé : {pourquoi}", admis("edit.presets.presetManager", p) is not True)
    pinceau = {"name": "Mien", "brush": {"size": 20.0, "tip": "round", "mode": "Normal",
                                         "texture": {"pattern": {"procedural": {"seed": 1, "size": 128, "style": "paper"}}}}}
    donnees = {"format": "photocraft-presets", "version": 1, "brushes": [pinceau], "customShapes": []}
    for p in ({"action": "export"}, {"action": "export", "kinds": ["brushes"], "includeBuiltins": True},
              {"action": "import", "data": donnees}, {"action": "import", "data": donnees, "kinds": ["customShapes"]},
              {"action": "import", "data": {**donnees, "brushes": [{"brush": {"tip": {"sampled": {"w": 2, "data": "AAECAw=="}}}}]}}):
        check(f"4c échange admis : {p['action']}", admis("edit.presets.exportImportPresets", p) is True, admis("edit.presets.exportImportPresets", p))
    profond = {"a": 1}
    for _ in range(13):
        profond = {"b": profond}
    for p, pourquoi in (({"action": "import"}, "sans data"), ({"action": "import", "data": {**donnees, "format": "abr"}}, "format"),
                        ({"action": "import", "data": {**donnees, "version": 2}}, "version"),
                        ({"action": "import", "data": {**donnees, "gradients": []}}, "genre inconnu"),
                        ({"action": "import", "data": {**donnees, "brushes": [{"brush": {"texture": {"path": "C:/p.pat"}}}]}}, "clé path"),
                        ({"action": "import", "data": {**donnees, "brushes": [{"brush": {"texture": {"path": "papier"}}}]}}, "clé path, valeur anodine"),
                        ({"action": "import", "data": {**donnees, "brushes": [{"brush": {"File": 3}}]}}, "clé File (casse)"),
                        ({"action": "import", "data": {**donnees, "brushes": [{"brush": {"tip": "C:\\pointes\\a.png"}}]}}, "valeur fichier"),
                        ({"action": "import", "data": {**donnees, "brushes": [{"brush": {"tip": {"data": "../../x"}}}]}}, "data non base64"),
                        ({"action": "import", "data": {**donnees, "brushes": [{"n": "x" * 300}]}}, "texte trop long"),
                        ({"action": "import", "data": {**donnees, "brushes": [{}] * 501}}, "501 préréglages"),
                        ({"action": "import", "data": {**donnees, "brushes": [{"t": "A" * 200} for _ in range(12000)]}}, "plus de 2 Mo"),
                        ({"action": "import", "data": {**donnees, "brushes": [profond]}}, "profondeur 14"),
                        ({"action": "export", "kinds": ["patterns"]}, "kinds patterns"), ({"action": "export", "kinds": []}, "kinds vide"),
                        ({"action": "export", "data": donnees}, "data à l'export"), ({"action": "export", "includeBuiltins": "oui"}, "includeBuiltins texte")):
        check(f"4d échange refusé : {pourquoi}", admis("edit.presets.exportImportPresets", p) is not True)
    check("4e Migrer les préréglages (chemin) reste refusée", admis("edit.presets.migratePresets", {"path": "x.json"}) is not True)
    r = admis("edit.presets.migratePresets", {})
    check("4e2 … par son PRÉFIXE, même sans chemin (pas seulement par la clé path)", isinstance(r, str) and "réservée aux routes" in r, r)
    check("4f prefs.set reste refusée (les préférences ne vont jamais au moteur)",
          admis("prefs.set", {"path": "performance.historyStates", "value": 10}) is not True)


def moteur():
    print("\n[5] VRAI moteur")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("5 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("5 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return None
    s = PM.session()
    reg = PM.registre(s)
    presets(reg)
    ex = lambda c, p=None: s.appeler("engine.execute", {"command": c, "params": p or {}})
    l0 = ex("edit.presets.presetManager", {"action": "list", "kind": "patterns"})["patterns"]
    ex("edit.presets.presetManager", {"action": "rename", "kind": "patterns", "index": 1, "newName": "Lignes"})
    ex("edit.presets.presetManager", {"action": "move", "kind": "patterns", "index": 1, "to": 0})
    l1 = ex("edit.presets.presetManager", {"action": "list", "kind": "patterns"})["patterns"]
    check("5a renommer puis monter un motif", l1[0] == "Lignes" and len(l1) == len(l0), (l0, l1))
    ex("edit.presets.presetManager", {"action": "delete", "kind": "patterns", "index": 0})
    l2 = ex("edit.presets.presetManager", {"action": "list", "kind": "patterns"})["patterns"]
    check("5b supprimer un motif", len(l2) == len(l0) - 1 and "Lignes" not in l2, l2)
    ex("brush.presets.save", {"name": "Sonde t159"})
    exp = ex("edit.presets.exportImportPresets", {"action": "export"})
    data = exp.get("data", {})
    check("5c export : le pinceau de l'utilisateur, format photocraft-presets", exp.get("brushes") == 1 and data.get("format") == "photocraft-presets"
          and data["brushes"][0].get("name") == "Sonde t159", {k: exp[k] for k in exp if k != "data"})
    check("5d l'export du moteur passe la liste blanche de l'import", PR.verifier(reg, "edit.presets.exportImportPresets", {"action": "import", "data": data}) is not None)
    liste = lambda: ex("edit.presets.presetManager", {"action": "list", "kind": "brushes"})["brushes"]
    n = len(liste())
    imp = ex("edit.presets.exportImportPresets", {"action": "import", "data": data})
    check("5e import d'un pinceau du même nom : il REMPLACE (aucun doublon)", imp.get("brushes") == 1 and len(liste()) == n, (imp, n, len(liste())))
    ex("edit.presets.presetManager", {"action": "delete", "kind": "brushes", "index": liste().index("Sonde t159")})
    ex("edit.presets.exportImportPresets", {"action": "import", "data": data})
    check("5e2 supprimé puis importé : il revient", "Sonde t159" in liste() and len(liste()) == n, liste()[-3:])

    from PIL import Image
    W = PM.dossier_travail()
    Image.new("RGB", (200, 50), (255, 200, 0)).save(W / "entrees" / "grand.png")
    s.appeler("doc.new", {"width": 64, "height": 48})
    r, _ = PM.placer(s, "entrees/grand.png", "grand", False, False)
    c = next(x for x in s.appeler("doc.inspect")["layers"] if x["id"] == r["layer"])
    check("5f Placer sans objet dynamique ni réduction : calque de pixels nommé, pleine taille (200 de large)",
          c["kind"] != "Smart Object" and c["name"] == "grand" and c["bounds"][2] >= 64, c)
    r, _ = PM.placer(s, "entrees/grand.png", "grand2")
    c = next(x for x in s.appeler("doc.inspect")["layers"] if x["id"] == r["layer"])
    check("5g Placer par défaut inchangé : objet dynamique réduit à la toile", c["kind"] == "Smart Object" and c["bounds"] == [0, 16, 64, 16], c)
    return s


async def routes():
    print("\n[6] routes")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    PF.chemin().unlink(missing_ok=True)
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/preferences")
        check("6a GET sans fichier -> défaut, enregistre: false", r.status_code == 200 and r.json() == {"etat": PF.etat_defaut(), "enregistre": False}, r.text[:200])
        e = avec(cursors={"painting": "precise"})
        e["raccourcis"]["commandes"] = {"image.adjustments.levels": "ctrl+alt+l"}
        r = await c.put("/api/photolab/preferences", json=e)
        check("6b PUT -> l'état validé", r.status_code == 200 and r.json()["prefs"]["cursors"]["painting"] == "precise", r.text[:200])
        r = await c.get("/api/photolab/preferences")
        check("6c relu : enregistre: true", r.json()["enregistre"] is True and r.json()["etat"]["raccourcis"]["commandes"] == {"image.adjustments.levels": "ctrl+alt+l"})
        r = await c.put("/api/photolab/preferences", json=avec(cursors={"painting": "C:/x.cur"}))
        check("6d PUT refusé -> 400 qui dit pourquoi", r.status_code == 400 and "cursors.painting" in r.text, r.text[:200])
        r = await c.post("/api/photolab/preferences/reinitialiser")
        check("6e réinitialiser -> défaut", r.status_code == 200 and r.json() == PF.etat_defaut())
        for corps, pourquoi in (({"filename": "x.png", "objetDynamique": "non"}, "objetDynamique texte"),
                                ({"filename": "x.png", "chemin": "C:/x"}, "clé inconnue")):
            r = await c.post("/api/photolab/placer", json=corps)
            check(f"6f /placer refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "edit.presets.presetManager", "params": {"action": "list", "kind": "customShapes"}})
        check("6g /executer gestionnaire -> 200", r.status_code == 200 and "customShapes" in r.json(), (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "edit.presets.migratePresets", "params": {"path": "x.json"}})
        check("6h /executer migratePresets -> 400", r.status_code == 400, (r.status_code, r.text[:200]))


try:
    schema()
    refus()
    fichier()
    if moteur():
        asyncio.run(routes())
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
