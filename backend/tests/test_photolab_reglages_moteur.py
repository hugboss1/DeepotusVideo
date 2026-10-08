# -*- coding: utf-8 -*-
"""t138 (Photolab P3, Task A4) — table de conversion doc.inspect -> paramètres de commande, sur le VRAI moteur.
Pour chacun des 16 kinds de calque de réglage : des paramètres NON par défaut écrits en clair ci-dessous passent par la
liste blanche du pont (PM.commande_autorisee + registre), créent le calque (`layer.newAdjustmentLayer.<kind>`),
`doc.inspect` donne la structure INTERNE (`adjustment`, élaguée du LUT par PM.elaguer_inspect), puis
`layer.setAdjustment` avec les mêmes paramètres ne change NI le rendu (empreinte sha256, maxSide 128) NI `adjustment`
— preuve que les paramètres décrivent bien l'état. Le tout est figé dans frontend/photolab/qa/fixtures/reglages-inspect.json,
que le banc JS de l'écran (B5, `depuisInspect`) relit : sans `--ecrire` on COMPARE (le moteur épinglé ne doit pas
bouger), avec `--ecrire` on réécrit.
Section VRAI moteur rouge si le binaire manque — jamais de saut silencieux.
Run : & $PY -X utf8 tests/test_photolab_reglages_moteur.py [--ecrire]   (depuis backend/)"""
import hashlib, json, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt138a4_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.setdefault("FAL_KEY", "test-key")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402

FIXTURE = BACKEND.parent / "frontend" / "photolab" / "qa" / "fixtures" / "reglages-inspect.json"
ECRIRE = "--ecrire" in sys.argv[1:]
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


# Paramètres NON par défaut, écrits en clair (jamais calculés à partir du résultat qu'on veut obtenir).
# Formes `json` vérifiées sur le moteur (sonde A4) : `reds` & co de selectiveColor = TABLEAU [c,m,y,k] (un objet
# {cyan,…} est accepté puis ignoré en silence) ; `stops` de gradientMap = [[position 0..1, "#rrggbb"], …] (des
# triplets [r,g,b] sont acceptés puis rendent du blanc) ; hueSaturation `reds` = objet {hue,saturation,lightness,range?}.
PARAMETRES = {
    "brightnessContrast": {"brightness": 20, "contrast": -15, "legacy": True},
    "levels": {"inBlack": 20, "gamma": 1.3, "inWhite": 230, "outBlack": 5, "outWhite": 250, "red": {"inBlack": 10}},
    "curves": {"points": [[0, 0], [64, 40], [192, 220], [255, 255]], "blue": [[0, 0], [128, 150], [255, 255]]},
    "exposure": {"exposure": 0.5, "offset": -0.02, "gamma": 1.2},
    "vibrance": {"vibrance": 30, "saturation": -10},
    "hueSaturation": {"hue": 25, "saturation": -10, "lightness": 5,
                      "reds": {"hue": 10, "saturation": 5, "lightness": 0},
                      "blues": {"hue": 3, "saturation": 4, "lightness": 5, "range": [190, 210, 250, 270]}},
    "colorBalance": {"shadows": [10, -5, 0], "midtones": [0, 0, 20], "highlights": [-10, 0, 0],
                     "preserveLuminosity": False},
    "blackWhite": {"reds": 50, "yellows": 70, "greens": 30, "cyans": 55, "blues": 10, "magentas": 90,
                   "tint": True, "tintColor": "#c08040"},
    "photoFilter": {"filter": "cooling80", "density": 40, "preserveLuminosity": False},
    "channelMixer": {"red": [80, 20, 0, 0], "green": [5, 90, 5, 10], "blue": [0, 10, 90, -5]},
    "invert": {},
    "posterize": {"levels": 6},
    "threshold": {"level": 100},
    "gradientMap": {"stops": [[0, "#101030"], [0.4, "#c04020"], [1, "#fff0b0"]], "reverse": True, "dither": True},
    # `reds` (tableau) + une seconde gamme par la forme plate {colors, cyan, …} : seules clés que le registre décrit
    # (les autres gammes en tableau — blues, neutrals… — sont vues en [2], le registre ne les liste que dans sa note).
    "selectiveColor": {"method": "absolute", "reds": [10, 0, -5, 0], "colors": "neutrals", "cyan": 1, "magenta": 2,
                       "yellow": 3, "black": 4},
    "colorLookup": {"lut": "warm", "interpolation": "tetrahedral", "dither": True},
}
KINDS = tuple(PARAMETRES)        # l'ordre du plan ; le fichier, lui, est trié
# Cas pièges de la conversion inverse (B5), même aller-retour que la base : (kind, cas, paramètres).
VARIANTES = (
    ("channelMixer", "monochrome", {"monochrome": True, "gray": [30, 60, 10, 5]}),
    ("hueSaturation", "colorize", {"colorize": True, "hue": 200, "saturation": 40, "lightness": -5}),
    ("blackWhite", "sans-teinte", {"reds": 50}),
    ("colorLookup", "none", {"lut": "none"}),
    # canal rouge à l'identité : l'état garde [{0,0},{1,1}] pour lui (jamais une liste vide), la conversion l'OMET
    ("curves", "canal-identite", {"points": [[0, 0], [64, 40], [255, 255]], "red": [[0, 0], [255, 255]],
                                   "blue": [[0, 0], [128, 150], [255, 255]]}),
)
CAS = tuple((k, "base", PARAMETRES[k]) for k in KINDS) + VARIANTES
D = PM.dossier_travail()
_N = [0]


def empreinte(s):
    """sha256 du PNG rendu (maxSide 128) du document actif."""
    _N[0] += 1
    nom = f"a4-{_N[0]}.png"
    s.appeler("doc.render", {"path": PM.relatif(f"rendus/{nom}"), "maxSide": 128})
    p = D / "rendus" / nom
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    p.unlink()
    return h


def calque(s, lid):
    insp = PM.elaguer_inspect(s.appeler("doc.inspect"))
    return next(c for c in PM._a_plat(insp["layers"]) if c.get("id") == lid)


def admise(reg, cid, params, kind=None, etat=None):
    """(vrai, message) — la liste blanche du pont accepte-t-elle cette commande ? `etat` : `adjustment` du calque visé."""
    try:
        PM.commande_autorisee(cid, params, reg, kind, etat)
        return True, ""
    except ValueError as e:
        return False, str(e)


def peindre(s):
    """Un document 64×64 non uniforme et COLORÉ (nuages + quatre aplats) : chaque réglage y a un effet visible."""
    s.appeler("doc.new", {"width": 64, "height": 64, "background": "white"})
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})
    ex("filter.render.clouds", seed=7)
    for (x, y, w, h), col in (((0, 0, 32, 32), "#cc2222"), ((32, 0, 32, 32), "#22aa33"),
                              ((0, 32, 32, 32), "#2244cc"), ((32, 32, 32, 32), "#ddcc22")):
        ex("select.rect", x=x, y=y, width=w, height=h, mode="replace")
        ex("edit.fill", color=col)
    ex("select.deselect")


def scenario():
    print("\n[1] VRAI moteur photocraft-cli : paramètres envoyés <-> doc.inspect, aller-retour par setAdjustment")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("1a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("1a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return None
    s = PM.session()
    peindre(s)
    reg = PM.registre(s)
    liste = s.appeler("engine.execute", {"command": "image.adjustments.colorLookup.list", "params": {}})
    check("1b colorLookup.list : 8 LUT {id, label}", isinstance(liste, list) and len(liste) == 8
          and all(set(x) == {"id", "label"} for x in liste), liste)
    nu = empreinte(s)
    fixtures = {}
    for kind, cas, p in CAS:
        nom = kind if cas == "base" else f"{kind}/{cas}"
        cid = f"layer.newAdjustmentLayer.{kind}"
        a, msg = admise(reg, cid, p)
        check(f"{nom} : la liste blanche du pont admet {cid}", a, msg)
        r = s.appeler("engine.execute", {"command": cid, "params": p})       # envoyé même si refusé : on veut savoir si le moteur accepte
        lid = r.get("layer")
        check(f"{nom} : calque créé {{layer: id}}", isinstance(lid, int), r)
        if not isinstance(lid, int):
            continue
        c = calque(s, lid)
        adj = c.get("adjustment")
        check(f"{nom} : doc.inspect rend `adjustment` (kind reconnu par PR.kind_de = {kind})",
              c.get("kind") == "Adjustment" and PM.PR.kind_de(c) == kind, (c.get("kind"), str(adj)[:200]))
        avec = empreinte(s)
        if cas == "none":
            check(f"{nom} : sans LUT le calque ne change pas le rendu (état muet par construction)", avec == nu)
        else:
            check(f"{nom} : le calque de réglage change le rendu (l'état n'est pas muet)", avec != nu)
        a2, msg2 = admise(reg, "layer.setAdjustment", {"layer": lid, **p}, kind, adj)
        check(f"{nom} : la liste blanche du pont admet layer.setAdjustment {{layer, …envoyé}}", a2, msg2)
        s.appeler("engine.execute", {"command": "layer.setAdjustment", "params": {"layer": lid, **p}})
        apres = empreinte(s)
        check(f"{nom} : setAdjustment avec les paramètres envoyés NE change PAS le rendu (empreinte identique)",
              apres == avec, (avec[:12], apres[:12]))
        adj2 = calque(s, lid).get("adjustment")
        check(f"{nom} : ni `adjustment` (même structure interne après setAdjustment)", adj2 == adj,
              (str(adj)[:200], str(adj2)[:200]))
        fixtures[f"{kind}/{cas}"] = {"kind": kind, "cas": cas, "envoye": p, "adjustment": adj, "lut_list": liste}
        s.appeler("engine.execute", {"command": "layer.delete", "params": {"layer": lid}})
    check("1c les 16 kinds sont couverts en `base`, plus les cas pièges",
          sorted(k for k in fixtures if k.endswith("/base")) == sorted(f"{k}/base" for k in PM.PR.KINDS.values())
          and len(fixtures) == 16 + len(VARIANTES), sorted(fixtures))
    cl = fixtures.get("colorLookup/base", {}).get("adjustment", {}).get("ColorLookup", {})
    check("1d colorLookup : `adjustment.ColorLookup.lut` élagué (None, lutElague), nom lisible 'Warm Filter'",
          cl.get("lut", 1) is None and cl.get("lutElague") is True and cl.get("name") == "Warm Filter", cl)
    cn = fixtures.get("colorLookup/none", {}).get("adjustment", {}).get("ColorLookup", {})
    check("1d2 colorLookup none : nom vide, taille 0, pas de LUT", cn.get("name") == "" and cn.get("size") == 0
          and cn.get("lut") is None, cn)
    pc = fixtures.get("curves/canal-identite", {}).get("adjustment", {}).get("Curves", {}).get("per_channel", [[]])
    check("1d3 curves canal identité : l'état garde [{0,0},{1,1}] pour le rouge (jamais une liste vide)",
          pc[0] == [{"input": 0.0, "output": 0.0}, {"input": 1.0, "output": 1.0}], pc)
    bn = fixtures.get("blackWhite/sans-teinte", {}).get("adjustment", {}).get("BlackWhite", {})
    check("1d4 blackWhite sans teinte : tint null", bn.get("tint", 1) is None, bn)
    hc = fixtures.get("hueSaturation/colorize", {}).get("adjustment", {}).get("HueSaturation", {})
    check("1d5 hueSaturation colorize : colorize vrai, hue 200 saturation 40 conservés", hc.get("colorize") is True
          and hc.get("hue") == 200.0 and hc.get("saturation") == 40.0, hc)
    cm = fixtures.get("channelMixer/monochrome", {}).get("adjustment", {}).get("ChannelMixer", {})
    check("1d6 channelMixer monochrome : monochrome vrai, ligne 0 = gray", cm.get("monochrome") is True
          and [round(v * 100) for v in cm.get("matrix", [[]])[0]] == [30, 60, 10, 5], cm)
    variantes(s, reg)
    return fixtures


def variantes(s, reg):
    """Formes qui piègent la conversion (B5) : on FIGE ce que le moteur fait réellement, pour qu'un changement du
    moteur épinglé soit vu ici et pas à l'écran."""
    print("\n[2] VRAI moteur : formes qui piègent la conversion")

    def cree(kind, p):
        lid = s.appeler("engine.execute", {"command": f"layer.newAdjustmentLayer.{kind}", "params": p})["layer"]
        a = calque(s, lid)["adjustment"]
        s.appeler("engine.execute", {"command": "layer.delete", "params": {"layer": lid}})
        return a
    a = cree("selectiveColor", {"method": "absolute", "reds": {"cyan": 10, "magenta": 0, "yellow": -5, "black": 0}})
    check("2a selectiveColor `reds` en OBJET : accepté puis ignoré en silence (tout à zéro) — il faut un tableau [c,m,y,k]",
          a["SelectiveColor"]["adjustments"][0] == [0.0, 0.0, 0.0, 0.0], a)
    a = cree("selectiveColor", {"colors": "blues", "cyan": 10, "yellow": -5, "black": 3})
    check("2b selectiveColor forme plate {colors, cyan, …} : écrit la gamme visée (blues = index 4), relative reste vrai",
          a["SelectiveColor"]["adjustments"][4] == [10.0, 0.0, -5.0, 3.0] and a["SelectiveColor"]["relative"] is True, a)
    # Le registre ne décrit que `reds` en clé (les huit autres gammes sont dans sa note) : la liste blanche du pont les
    # ajoute (photolab_registre.GAMMES_SELECTIVE) puisque le moteur les accepte.
    p9 = {"method": "absolute", "reds": [1, 0, 0, 0], "blues": [0, 5, 0, -8], "neutrals": [1, 2, 3, 4]}
    adm, msg = admise(reg, "layer.newAdjustmentLayer.selectiveColor", p9)
    a = cree("selectiveColor", p9)
    check("2b2 selectiveColor : le MOTEUR accepte les gammes en tableau (blues index 4, neutrals index 7)",
          a["SelectiveColor"]["adjustments"][4] == [0.0, 5.0, 0.0, -8.0]
          and a["SelectiveColor"]["adjustments"][7] == [1.0, 2.0, 3.0, 4.0], a)
    check("2b3 et la liste blanche du pont les admet aussi (schémas du registre complétés)", adm, msg)
    adm, msg = admise(reg, "layer.newAdjustmentLayer.selectiveColor", {"reds": {"cyan": 10}})
    check("2b4 …mais refuse `reds` en objet, que le moteur ignorerait en silence", not adm, msg)
    a = cree("gradientMap", {"stops": [[0, [16, 16, 48]], [1, [255, 240, 176]]]})
    check("2c gradientMap stops en triplets [r,g,b] : accepté puis BLANC (couleurs fausses) — il faut \"#rrggbb\"",
          all(st[1] == [1.0, 1.0, 1.0] for st in a["GradientMap"]["stops"]), a)
    a = cree("blackWhite", {"reds": 50})
    check("2d blackWhite sans teinte : tint null, poids par défaut 60/40/60/20/80 pour les autres",
          a["BlackWhite"]["tint"] is None and a["BlackWhite"]["weights"] == [50.0, 60.0, 40.0, 60.0, 20.0, 80.0], a)
    a = cree("channelMixer", {"monochrome": True, "gray": [30, 60, 10, 5]})
    m = a["ChannelMixer"]
    check("2e channelMixer monochrome : `gray` est la ligne matrix[0] (÷100), les deux autres lignes restent l'identité",
          m["monochrome"] is True and [round(v * 100) for v in m["matrix"][0]] == [30, 60, 10, 5]
          and m["matrix"][1] == [0.0, 1.0, 0.0, 0.0] and m["matrix"][2] == [0.0, 0.0, 1.0, 0.0], a)
    a = cree("hueSaturation", {"colorize": True, "hue": 200, "saturation": 40, "lightness": -5})
    h = a["HueSaturation"]
    check("2f hueSaturation colorize : hue 0..360 et saturation 0..100 tels quels dans l'état",
          h["colorize"] is True and h["hue"] == 200.0 and h["saturation"] == 40.0 and h["lightness"] == -5.0, a)
    a = cree("photoFilter", {"color": "#aa5522", "density": 33})
    pf = a["PhotoFilter"]
    check("2g photoFilter avec `color` : couleur/255 (f32) et densité/100 ; preserve_luminosity vrai par défaut",
          [round(v * 255) for v in pf["color"]] == [0xaa, 0x55, 0x22] and abs(pf["density"] - 0.33) < 1e-6
          and pf["preserve_luminosity"] is True, a)


def ecrire_ou_comparer(fixtures):
    print("\n[3] fixture frontend/photolab/qa/fixtures/reglages-inspect.json")
    texte = json.dumps(fixtures, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
    if ECRIRE and fail:
        # jamais figer un état dont une preuve a échoué : la fixture ne doit décrire que des paramètres vérifiés
        check("3a --ecrire : fixture NON écrite parce qu'une vérification précédente a échoué", False, f"{fail} échec(s)")
        return
    if ECRIRE:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        with open(FIXTURE, "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
        print(f"  écrit : {FIXTURE} ({len(texte)} octets)")
        check("3a fichier écrit", len(fixtures) == 16 + len(VARIANTES))
        return
    if not FIXTURE.is_file():
        check("3a la fixture existe (lancer une fois avec --ecrire)", False, FIXTURE)
        return
    brut = FIXTURE.read_bytes()
    check("3a la fixture existe", True)
    check("3b UTF-8 sans BOM, fins de ligne LF", not brut.startswith(b"\xef\xbb\xbf") and b"\r" not in brut)
    try:
        lu = json.loads(brut.decode("utf-8"))
    except ValueError as e:
        check("3c la fixture est du JSON", False, e)
        return
    for kind in sorted(set(lu) | set(fixtures)):
        check(f"3d {kind} : identique à la fixture (le moteur épinglé n'a pas bougé)", lu.get(kind) == fixtures.get(kind),
              f"fixture={str(lu.get(kind))[:200]} moteur={str(fixtures.get(kind))[:200]}")
    check("3e fichier octet pour octet égal à la sérialisation (JSON trié, indenté 1, UTF-8, LF)",
          brut.decode("utf-8") == texte)


try:
    fx = scenario()
    if fx:
        ecrire_ou_comparer(fx)
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
