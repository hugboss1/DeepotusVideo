# -*- coding: utf-8 -*-
"""t155 (Photolab parité L5) — peinture et retouche : le pont et le VRAI moteur.
[1] liste blanche (PM.commande_autorisee) : les 17 commandes paint.* de l'écran passent avec les paramètres qu'il
    envoie ; tools.setBrush admet les champs de la pointe (CHAMPS_POINTE, A1) dans leurs bornes et refuse le reste.
[2] VRAI moteur photocraft-cli 0.3.0 : chaque commande change le rendu (empreinte sha256, maxSide 64) et ajoute
    EXACTEMENT l'état d'historique attendu ; le tampon sans source est refusé, accepté après cloneSource.set.
[3] chaque nom d'état de [2] est traduit par ETATS_MOTEUR (frontend/photolab/js/mod-historique.js) vers une clé qui
    existe en fr ET en en dans frontend/shared/i18n/photolab.json.
Section VRAI moteur rouge si le binaire manque — jamais de saut silencieux (PHOTOCRAFT_CLI dans un worktree).
Run : & $PY -X utf8 tests/test_photolab_peinture.py   (depuis backend/)"""
import hashlib, json, os, pathlib, re, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt155_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.setdefault("FAL_KEY", "test-key")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
from app.services import photolab_registre as PR              # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


def admise(reg, cid, params):
    try:
        PM.commande_autorisee(cid, params, reg)
        return True, ""
    except ValueError as e:
        return False, str(e)


P = [[8, 8, 0.5], [20, 30, 0.7], [40, 24, 0.9], [56, 50, 0.6]]
# (commande, paramètres tels que l'écran les envoie, nom d'historique attendu). L'ordre compte en [2] : la Forme
# d'historique repeint l'état « Open » (le document BLANC d'avant les nuages) ; placée avant Densité/Éponge, elle
# laisserait du blanc sous leurs traits, où elles ne changent rien. Un trait `erase` s'appelle « Eraser ».
GESTES = (
    ("paint.stroke", {"points": P, "size": 9, "hardness": 0.8, "opacity": 1, "flow": 1, "color": "#ff0000",
                      "mode": "multiply", "smoothing": 0.1}, "Brush Tool"),
    ("paint.stroke", {"points": P, "size": 5, "hardness": 1, "opacity": 1, "flow": 1, "erase": True}, "Eraser"),
    ("paint.pencil", {"points": P, "size": 3, "opacity": 1, "mode": "normal", "autoErase": False, "color": "#0000ff"},
     "Pencil"),
    ("paint.mixerBrush", {"points": P, "size": 7, "wet": 60, "load": 40, "mix": 50, "flow": 100,
                          "sampleAllLayers": False, "color": "#00ff00"}, "Mixer Brush"),
    ("paint.dodge", {"points": P, "size": 11, "hardness": 50, "range": "midtones", "exposure": 80, "protectTones": True},
     "Dodge Tool"),
    ("paint.burn", {"points": P, "size": 11, "hardness": 50, "range": "shadows", "exposure": 80, "protectTones": False},
     "Burn Tool"),
    ("paint.sponge", {"points": P, "size": 11, "hardness": 50, "mode": "desaturate", "vibrance": False, "flow": 100},
     "Sponge Tool"),
    ("paint.blur", {"points": P, "size": 11, "hardness": 50, "strength": 100, "sampleAllLayers": False}, "Blur Tool"),
    ("paint.sharpen", {"points": P, "size": 11, "hardness": 50, "strength": 100, "protectDetail": False,
                       "sampleAllLayers": False}, "Sharpen Tool"),
    ("paint.smudge", {"points": P, "size": 11, "hardness": 50, "strength": 90, "fingerPainting": False,
                      "sampleAllLayers": False}, "Smudge Tool"),
    ("paint.spotHealing", {"points": P[:2], "size": 9, "hardness": 50, "type": "contentAware"}, "Spot Healing Brush"),
    ("paint.historyBrush", {"points": P, "size": 11, "hardness": 100, "opacity": 100, "flow": 100}, "History Brush"),
    ("paint.backgroundEraser", {"points": P, "size": 9, "hardness": 0.5, "sampling": "continuous", "limits": "contiguous",
                                "tolerance": 50, "protectForegroundColor": False}, "Background Eraser"),
    ("paint.bucket", {"x": 2, "y": 60, "tolerance": 32, "contiguous": True, "antiAlias": True, "contents": "foreground",
                      "opacity": 100, "color": "#ffff00"}, "Paint Bucket"),
    ("paint.gradient", {"from": [0, 0], "to": [63, 0], "style": "linear", "reverse": False, "dither": True,
                        "opacity": 50, "mode": "normal"}, "Gradient"),
    ("paint.magicEraser", {"x": 62, "y": 2, "tolerance": 32, "antiAlias": True, "contiguous": True,
                           "sampleAllLayers": False, "opacity": 100}, "Magic Eraser"),
)
SOURCES = (   # après cloneSource.set : l'écran n'envoie jamais de source dans le trait
    ("paint.cloneStamp", {"points": [[40, 40], [50, 50]], "size": 9, "hardness": 50, "opacity": 100, "flow": 100,
                          "aligned": True, "sampleLayer": "current", "mode": "normal"}, "Clone Stamp"),
    ("paint.healingBrush", {"points": [[30, 50], [36, 56]], "size": 9, "hardness": 50, "aligned": True,
                            "sampleLayer": "all", "mode": "normal"}, "Healing Brush"),
)
POINTE = {"size": 20, "hardness": 0.3, "spacing": 0.25, "spacingEnabled": True, "angle": -30, "roundness": 0.5,
          "flipX": True, "flipY": False, "opacity": 0.9, "flow": 0.8}


def liste_blanche(reg):
    print("\n[1] liste blanche du pont")
    for cid, p, _ in GESTES + SOURCES:
        a, m = admise(reg, cid, p)
        check(f"1a {cid} {sorted(p)} admis", a, m)
    for cid, p in (("cloneSource.set", {"source": [3, 4]}), ("tools.setBrush", {"preset": "Soft Round"}),
                   ("tool.presets.select", {"preset": "Soft Round 100 px"}), ("tool.presets.new", {"name": "x", "tool": "brush"}),
                   ("brush.get", {}), ("brush.presets.list", {}), ("tool.presets.list", {}), ("cloneSource.list", {}),
                   ("cloneSource.select", {"index": 2}),
                   ("cloneSource.set", {"index": 1, "offset": [2, 3], "width": 120, "rotation": 15, "flipH": True})):
        a, m = admise(reg, cid, p)
        check(f"1b {cid} {sorted(p)} admis", a, m)
    a, m = admise(reg, "tools.setBrush", POINTE)
    check("1c tools.setBrush : les 10 champs de la pointe (A1) admis", a, m)
    for k, v in (("size", 0), ("size", 5001), ("hardness", 1.5), ("spacing", 0), ("spacing", 11), ("angle", 181),
                 ("roundness", 0), ("opacity", -0.1), ("flow", 2), ("flipX", 1), ("size", "20"), ("spacingEnabled", "oui")):
        a, _ = admise(reg, "tools.setBrush", {k: v})
        check(f"1d tools.setBrush {k}={v!r} refusé", not a)
    for p in ({"tip": "round"}, {"shapeDynamics": {"enabled": True}}, {"texture": {"pattern": "x"}}, {"path": "a.abr"}):
        a, _ = admise(reg, "tools.setBrush", p)
        check(f"1e tools.setBrush {sorted(p)} hors de la pointe refusé", not a)
    a, _ = admise(reg, "paint.stroke", {"points": [[1, 2]] * 50_001})
    check("1f paint.stroke : plus de 100 000 valeurs de points refusé", not a)
    a, _ = admise(reg, "paint.stroke", {"points": [[1, 2]], "size": 5, "zorg": 1})
    check("1g paint.stroke : clé inconnue refusée", not a)


D = PM.dossier_travail()
_N = [0]


def empreinte(s):
    _N[0] += 1
    nom = f"t155-{_N[0]}.png"
    s.appeler("doc.render", {"path": PM.relatif(f"rendus/{nom}"), "maxSide": 64})
    p = D / "rendus" / nom
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    p.unlink()
    return h


def historique(s):
    h = s.appeler("doc.inspect").get("history")
    return list(h) if isinstance(h, list) else []


def peindre(s):
    s.appeler("doc.new", {"width": 64, "height": 64, "background": "white"})
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})
    ex("filter.render.clouds", seed=11)
    for (x, y, w, h), col in (((0, 0, 32, 32), "#cc2222"), ((32, 32, 32, 32), "#2244cc")):
        ex("select.rect", x=x, y=y, width=w, height=h, mode="replace")
        ex("edit.fill", color=col)
    ex("select.deselect")


def moteur(reg):
    print("\n[2] VRAI moteur photocraft-cli : chaque geste change le rendu et nomme son état")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("2a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("2a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return []
    s = PM.session()
    peindre(s)
    ex = lambda c, p: s.appeler("engine.execute", {"command": c, "params": p})
    noms = []
    for cid, p, attendu in GESTES:
        avant, h0 = empreinte(s), historique(s)
        try:
            ex(cid, p)
        except PM.MoteurErreur as e:
            check(f"2b {cid} exécuté", False, e)
            continue
        apres, h1 = empreinte(s), historique(s)
        check(f"2b {cid} : le rendu change", avant != apres)
        check(f"2c {cid} : un état « {attendu} » de plus", h1[:-1] == h0 and h1[-1:] == [attendu], h1[-3:])
        noms.append(attendu)
    try:
        ex("paint.cloneStamp", dict(SOURCES[0][1]))
        check("2d tampon sans source : refusé par le moteur", False, "accepté")
    except PM.MoteurErreur as e:
        check("2d tampon sans source : refusé par le moteur (source/offset ou cloneSource.set)", "source" in str(e), e)
    ex("cloneSource.set", {"source": [10, 10]})
    for cid, p, attendu in SOURCES:
        avant, h0 = empreinte(s), historique(s)
        r = ex(cid, p)
        apres, h1 = empreinte(s), historique(s)
        check(f"2e {cid} après cloneSource.set : le rendu change", avant != apres, r)
        check(f"2f {cid} : un état « {attendu} » de plus", h1[:-1] == h0 and h1[-1:] == [attendu], h1[-3:])
        noms.append(attendu)
    b = ex("tools.setBrush", POINTE)
    lu = ex("brush.get", {})
    check("2g tools.setBrush puis brush.get : la pointe relue = celle envoyée",
          all(abs(lu[k] - v) < 1e-6 if isinstance(v, float) else lu[k] == v for k, v in POINTE.items()),
          {k: lu.get(k) for k in POINTE})
    return noms


def traductions(noms):
    print("\n[3] noms d'historique traduits (ETATS_MOTEUR -> photolab.json fr/en)")
    src = (RACINE / "frontend/photolab/js/mod-historique.js").read_text(encoding="utf-8")
    bloc = src[src.index("export const ETATS_MOTEUR"):]
    bloc = bloc[:bloc.index("};")]
    table = dict(re.findall(r'"([^"]+)":\s*"(photolab\.[a-z0-9_.]+)"', bloc))
    dico = json.loads((RACINE / "frontend/shared/i18n/photolab.json").read_text(encoding="utf-8"))
    for n in sorted(set(noms) | {g[2] for g in GESTES + SOURCES}):
        cle = table.get(n)
        check(f"3a « {n} » -> {cle}", cle is not None and bool((dico.get(cle) or {}).get("fr"))
              and bool((dico.get(cle) or {}).get("en")), cle)


reg = PR.structurer(json.loads((BACKEND / "tests/photocraft_commandes_0.3.0.json").read_text(encoding="utf-8")))
try:
    liste_blanche(reg)
    noms = moteur(reg)
    traductions(noms)
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
