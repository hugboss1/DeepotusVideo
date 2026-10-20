# -*- coding: utf-8 -*-
"""t256 (Photolab M7, photocraft 0.10) — calques : le pont et le VRAI moteur.
[1] liste blanche (PM.commande_autorisee) : les 17 commandes de calques ouvertes passent avec les paramètres que
    l'écran envoie ; formes et bornes refusées (couleur d'étiquette inconnue, cadre de taille nulle, document négatif,
    liste de calques illisible, défaut de style aux clés inconnues, masque sans densité ni contour progressif…) ;
    restent fermées : layerStyle.replace (le dialogue Style de calque applique déjà effet par effet), et les commandes
    à CHEMIN des objets dynamiques — le moteur les désactive en automation (« uses ambient filesystem paths »).
[2] VRAI moteur : chaque commande agit et nomme EXACTEMENT son état d'historique (ou n'en fait aucun).
[3] chaque nom d'état de [2] est traduit par ETATS_MOTEUR (mod-historique.js) en fr ET en en.
[4] enregistrées dans une action, ces commandes restent des étapes rejouables (photolab_registre.verifier_etape).
PR 2 (historique, nuancier) :
[5] instantanés et document d'après un état : liste blanche (history.newSnapshot / deleteSnapshot / renameSnapshot /
    selectSnapshot / newDocument ; nom vide, trop long, sur deux lignes, id négatif refusés ; undo / redo / selectState /
    deleteState et swatches.* restent fermées à /executer) puis VRAI moteur (aucun état, sauf « choisir » = un état
    au nom de l'instantané ; le nouveau document devient actif).
[6] nuancier .aco / .ase : conversion pure (groupes_depuis_moteur, fusionner), refus du pont, puis VRAI moteur : export
    de NOS groupes, réimport (append, replace), fichier illisible -> erreur, et la bibliothèque du moteur remise aux
    défauts d'usine après chaque échange.
PR 3 (Déformer) :
[7] Ctrl+T › Déformer : edit.transform.warpGrid ouverte (taille Par défaut / 3 / 4 / 5, style « none » + rect, ou le
    maillage en cours `warp`) ; edit.transform.warp admise en aperçu ; VRAI moteur : maillage neutre (16 points, 100 en
    3 × 3), découpe qui GARDE la surface (un point déplacé reste à sa place), aucun état pour la grille, « Warp » à la
    validation, rien pour un maillage neutre.
Section VRAI moteur rouge si le binaire manque — jamais de saut silencieux.
Run : & $PY -X utf8 tests/test_photolab_m7.py   (depuis backend/)"""
import json, os, pathlib, re, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt256_"))
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
sys.path.insert(0, str(BACKEND / "tests"))
from app.services import photolab_moteur as PM                # noqa: E402
from app.services import photolab_registre as PR              # noqa: E402
from app.services import photolab_neuves as PN                # noqa: E402
import photocraft_version as _PV                                # noqa: E402

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


OUVERTES_CALQUES = ("layer.removeBackground", "filter.render.relight", "filter.other.colorToAlpha", "layer.showOnly",
                    "layer.toggleLockTransparency", "layer.setLabelColor", "layer.mergeGroup", "layer.copyToDocument",
                    "layer.new.frame", "layer.artboard.addBeside", "layer.layerStyle.transferEffects",
                    "layer.layerStyle.makeDefault", "layer.layerStyle.defaultFor", "layer.layerMask.edit",
                    "layer.smartObjects.convertToLayers", "layer.new.backgroundFromLayer", "layer.rasterize.layerStyle")
FERMEES_CALQUES = ("layer.layerStyle.replace", "layer.smartObjects.updateChanged")
# (commande, paramètres tels que l'écran les envoie)
ADMIS = (
    ("layer.removeBackground", {}), ("layer.removeBackground", {"refine": False, "sampleAllLayers": True}),
    ("filter.render.relight", {"angle": -30, "elevation": 60, "intensity": 70, "ambient": 40, "warmth": 20, "softness": 10}),
    ("filter.other.colorToAlpha", {"color": "#ffffff", "transparencyThreshold": 0.1, "opacityThreshold": 0.9}),
    ("layer.showOnly", {"layer": 3}), ("layer.toggleLockTransparency", {}), ("layer.toggleLockTransparency", {"layer": 4}),
    ("layer.setLabelColor", {"color": "red", "layer": 3}), ("layer.setLabelColor", {"color": "none"}),
    ("layer.mergeGroup", {}), ("layer.mergeGroup", {"layer": 5}),
    ("layer.copyToDocument", {"document": 0}),
    ("layer.copyToDocument", {"document": 2, "center": True, "layers": [3, 4], "offset": [10, -5], "name": "Copie"}),
    ("layer.copyToDocument", {"document": 1, "at": [100.5, 40]}),
    ("layer.new.frame", {"x": 10, "y": 20, "width": 50, "height": 40}),
    ("layer.new.frame", {"x": -10, "y": 0, "width": 1, "height": 300000, "shape": "ellipse", "layer": 3, "name": "Cadre"}),
    ("layer.artboard.addBeside", {"side": "left", "duplicate": True}), ("layer.artboard.addBeside", {}),
    ("layer.layerStyle.transferEffects", {"from": 3, "to": 4}),
    ("layer.layerStyle.transferEffects", {"from": 3, "to": 4, "copy": True, "effect": 0}),
    ("layer.layerStyle.makeDefault", {"kind": "dropShadow", "params": {"distance": 12, "color": "#102030", "opacity": 60}}),
    ("layer.layerStyle.makeDefault", {"kind": "stroke", "params": {"size": 3}}),
    ("layer.layerStyle.defaultFor", {"kind": "satin"}),
    ("layer.layerMask.edit", {"layer": 3, "density": 50}), ("layer.layerMask.edit", {"feather": 12.5}),
    ("layer.layerMask.edit", {"density": 0, "feather": 1000}),
    ("layer.smartObjects.convertToLayers", {}), ("layer.new.backgroundFromLayer", {"layer": 3}),
    ("layer.rasterize.layerStyle", {}),
)
REFUS = (
    ("layer.setLabelColor", {"color": "pink"}), ("layer.setLabelColor", {}),
    ("layer.removeBackground", {"refine": "oui"}),
    ("filter.render.relight", {"angle": 200}), ("filter.other.colorToAlpha", {"color": "blanc"}),
    ("filter.other.colorToAlpha", {"opacityThreshold": 2}),
    ("layer.copyToDocument", {}), ("layer.copyToDocument", {"document": -1}),
    ("layer.copyToDocument", {"document": 1, "layers": "3"}), ("layer.copyToDocument", {"document": 1, "layers": [3, -2]}),
    ("layer.copyToDocument", {"document": 1, "layers": []}), ("layer.copyToDocument", {"document": 1, "at": [1]}),
    ("layer.copyToDocument", {"document": 1, "offset": [1, "2"]}), ("layer.copyToDocument", {"document": 1, "offset": [1e9, 0]}),
    ("layer.copyToDocument", {"document": 1, "name": "C:/x.png"}),
    ("layer.new.frame", {"x": 0, "y": 0, "width": 0, "height": 10}), ("layer.new.frame", {"x": 0, "y": 0, "width": 10}),
    ("layer.new.frame", {"x": 0, "y": 0, "width": 10, "height": 400000}), ("layer.new.frame", {"x": 0.5, "y": 0, "width": 10, "height": 10}),
    ("layer.new.frame", {"x": 0, "y": 0, "width": 10, "height": 10, "shape": "star"}),
    ("layer.artboard.addBeside", {"side": "dessus"}),
    ("layer.layerStyle.transferEffects", {"from": 3}), ("layer.layerStyle.transferEffects", {"from": 3, "to": 4, "effect": -1}),
    ("layer.layerStyle.makeDefault", {"kind": "dropShadow"}), ("layer.layerStyle.makeDefault", {"kind": "ombre", "params": {}}),
    ("layer.layerStyle.makeDefault", {"kind": "stroke", "params": {"taille": 9}}),
    ("layer.layerStyle.makeDefault", {"kind": "stroke", "params": {"size": "x"}}),
    ("layer.layerStyle.makeDefault", {"kind": "stroke", "params": {"size": 3, "layer": 4}}),
    ("layer.layerStyle.makeDefault", {"kind": "stroke", "params": [3]}),
    ("layer.layerStyle.defaultFor", {}), ("layer.layerStyle.defaultFor", {"kind": "../prefs"}),
    ("layer.layerMask.edit", {}), ("layer.layerMask.edit", {"layer": 3}), ("layer.layerMask.edit", {"density": 101}),
    ("layer.layerMask.edit", {"feather": -1}),
    ("layer.layerStyle.replace", {"layer": 3, "effects": []}),
    ("layer.smartObjects.updateChanged", {}),
    ("layer.smartObjects.exportContents", {"path": "so.png"}), ("layer.smartObjects.replaceContents", {"path": "entrees/a.png"}),
)


def liste_blanche(reg):
    print("\n[1] liste blanche du pont")
    check("1.0 les 17 commandes de calques ne sont plus dans COMMANDES_NEUVES_FERMEES ; replace et updateChanged y restent",
          not (set(OUVERTES_CALQUES) & PN.COMMANDES_NEUVES_FERMEES) and set(FERMEES_CALQUES) <= PN.COMMANDES_NEUVES_FERMEES)
    for cid, p in ADMIS:
        a, m = admise(reg, cid, p)
        check(f"1a {cid} {sorted(p)} admis", a, m)
    for cid, p in REFUS:
        a, _ = admise(reg, cid, p)
        check(f"1b {cid} {json.dumps(p, ensure_ascii=False)[:90]} refusé", not a)


def historique(s):
    h = s.appeler("doc.inspect").get("history")
    return list(h) if isinstance(h, list) else []


def moteur():
    print("\n[2] VRAI moteur : chaque commande agit et nomme son état")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check(f"2a le binaire photocraft-cli {PM.VERSION} est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check(f"2a le binaire photocraft-cli {PM.VERSION} est présent (sinon cette section est rouge)", False, e)
        return []
    s = PM.session()
    ex = lambda c, p=None: s.appeler("engine.execute", {"command": c, "params": p or {}})
    ins = lambda: s.appeler("doc.inspect")
    calque = lambda i: next(c for c in PM._a_plat(ins()["layers"]) if c["id"] == i)
    noms = []

    def etat(label, attendu, h0, n=1):
        h1 = historique(s)
        check(f"{label} : {n} état(s) « {attendu} » de plus", h1[:-n] == h0 and h1[-n:] == [attendu] * n, h1[-3:])
        noms.append(attendu)

    def erreur(c, p):
        try:
            ex(c, p); return None
        except PM.MoteurErreur as e:
            return str(e)

    # Retirer l'arrière-plan (local) : sur une vraie image (sujet sur fond uni), masque posé, l'arrière-plan devient calque
    entrees = _tmp / "photolab" / "entrees"
    entrees.mkdir(parents=True, exist_ok=True)
    shutil.copy(BACKEND / "app/assets/emoji/1f30a.png", entrees / "vague.png")
    s.appeler("doc.open", {"path": "entrees/vague.png"})
    h0 = historique(s); r = ex("layer.removeBackground", {})
    c = calque(r["layer"])
    check("2b Retirer l'arrière-plan (local) : un masque de fusion, l'arrière-plan devenu calque ordinaire",
          c["hasMask"] is True and c["name"] != "Background" and len(r.get("bounds") or []) == 4, (r, c["name"]))
    etat("2b retirer l'arrière-plan", "Remove Background", h0)
    s.appeler("doc.close", {})

    s.appeler("doc.new", {"width": 200, "height": 120, "background": "white"})
    fond = ins()["activeLayer"]
    ex("layer.new.layer", {}); ex("select.all"); ex("edit.fill", {"color": "#ff0000"}); ex("select.deselect")
    a = ins()["activeLayer"]
    h0 = historique(s); r = ex("filter.render.relight", {"angle": -30, "intensity": 70})
    check("2c Rééclairer : le filtre et ses réglages", (r.get("filter") or {}).get("filter") == "relight" and r["filter"]["angle"] == -30, r)
    etat("2c Rééclairer", "Relight", h0)
    h0 = historique(s); r = ex("filter.other.colorToAlpha", {"color": "#ff0000"})
    check("2d Couleur en alpha : le rouge devient transparent", (r.get("filter") or {}).get("filter") == "colorToAlpha", r)
    etat("2d Couleur en alpha", "Color to Alpha", h0)
    ex("edit.undo")
    # Verrou de transparence : bascule, l'état est celui de layer.setProps locks (le même dans le moteur)
    h0 = historique(s); r1 = ex("layer.toggleLockTransparency", {}); r2 = ex("layer.toggleLockTransparency", {})
    check("2e verrou de transparence : verrouille puis déverrouille", r1 == {"locked": True} and r2 == {"locked": False}, (r1, r2))
    h1 = historique(s)
    check("2e deux états « Lock / Unlock Transparent Pixels »", h1[:-2] == h0 and h1[-2:] == ["Lock Transparent Pixels", "Unlock Transparent Pixels"], h1[-2:])
    noms += ["Lock Transparent Pixels", "Unlock Transparent Pixels"]
    ex("layer.setProps", {"layer": a, "locks": {"transparency": True, "pixels": False, "position": False, "artboard": False, "all": False}})
    check("2e verrou posé par setProps : la bascule le relit (déverrouille)", ex("layer.toggleLockTransparency", {}) == {"locked": False})
    m = erreur("filter.other.colorToAlpha", {"color": "#ffffff"}) if ex("layer.toggleLockTransparency", {}) == {"locked": True} else "?"
    check("2e transparence verrouillée : Couleur en alpha refusée par le moteur", m is not None and "locked" in m, m)
    ex("layer.toggleLockTransparency", {})
    m = erreur("layer.toggleLockTransparency", {"layer": fond})
    check("2e l'arrière-plan ne se verrouille pas (erreur du moteur)", m is not None and "Background" in m, m)
    # Couleur d'étiquette : doc.inspect la relit
    h0 = historique(s); r = ex("layer.setLabelColor", {"color": "seafoam", "layer": a})
    check("2f couleur du calque : doc.inspect rend labelColor", r.get("layers") == [a] and calque(a)["labelColor"] == "seafoam", (r, calque(a).get("labelColor")))
    etat("2f couleur du calque", "Layer Color", h0)
    # Afficher seulement ce calque (Alt-clic sur l'œil), puis de nouveau : les autres reviennent
    h0 = historique(s); r1 = ex("layer.showOnly", {"layer": a}); seul = calque(fond)["visible"]
    r2 = ex("layer.showOnly", {"layer": a})
    check("2g Alt-clic sur l'œil : seul ce calque, puis tous de nouveau", r1 == {"shownAlone": True} and seul is False
          and r2 == {"shownAlone": False} and calque(fond)["visible"] is True, (r1, seul, r2))
    h1 = historique(s)
    check("2g états « Show Only This Layer » puis « Show Layers »", h1[:-2] == h0 and h1[-2:] == ["Show Only This Layer", "Show Layers"], h1[-2:])
    noms += ["Show Only This Layer", "Show Layers"]
    # Masque : densité et contour progressif
    ex("layer.layerMask.revealAll", {})
    h0 = historique(s); r = ex("layer.layerMask.edit", {"layer": a, "density": 50, "feather": 4})
    check("2h masque : densité et contour progressif rendus", r == {"layer": a, "density": 50.0, "feather": 4.0}, r)
    etat("2h modifier le masque", "Edit Layer Mask", h0)
    m = erreur("layer.layerMask.edit", {"layer": fond, "density": 10})
    check("2h calque sans masque : erreur du moteur (no pixel mask)", m is not None and "no pixel mask" in m, m)
    # Styles : défaut de l'utilisateur (aucun état), transfert d'effets, pixellisation du style
    r = ex("layer.layerStyle.defaultFor", {"kind": "dropShadow"})
    check("2i défaut d'usine de l'ombre portée (user: false)", r.get("user") is False and r["params"].get("distance") == 5, r)
    h0 = historique(s); ex("layer.layerStyle.makeDefault", {"kind": "dropShadow", "params": {"distance": 12}})
    r = ex("layer.layerStyle.defaultFor", {"kind": "dropShadow"})
    check("2i Définir par défaut puis Rétablir : le défaut de l'utilisateur", r == {"params": {"distance": 12}, "user": True}, r)
    check("2i défauts de style : aucun état d'historique", historique(s) == h0, historique(s)[-2:])
    ex("layer.layerStyle.stroke", {"layer": a, "size": 3})
    ex("layer.new.layer", {}); b = ins()["activeLayer"]
    h0 = historique(s); ex("layer.layerStyle.transferEffects", {"from": a, "to": b, "copy": True})
    check("2j Alt-glisser fx : effets copiés (les deux calques en ont)", bool((calque(a).get("effects") or {}).get("items"))
          and bool((calque(b).get("effects") or {}).get("items")))
    etat("2j copier les effets", "Copy Layer Effects", h0)
    ex("layer.layerStyle.clear", {"layer": b})
    h0 = historique(s); ex("layer.layerStyle.transferEffects", {"from": a, "to": b})
    check("2j glisser fx : effets déplacés", not (calque(a).get("effects") or {}).get("items") and bool((calque(b).get("effects") or {}).get("items")))
    etat("2j déplacer les effets", "Move Layer Effects", h0)
    h0 = historique(s); r = ex("layer.rasterize.layerStyle", {"layer": b})
    check("2k pixelliser le style : plus d'effet", r.get("layers") == [b] and not (calque(b).get("effects") or {}).get("items"), r)
    etat("2k pixelliser le style", "Rasterize Layer Style", h0)
    # Fusionner le groupe
    ex("layer.select", {"layer": a, "mode": "replace"}); ex("layer.groupLayers", {})
    g = ins()["activeLayer"]
    h0 = historique(s); r = ex("layer.mergeGroup", {})
    check("2l Fusionner le groupe : un calque de pixels à la place du groupe", r == {"layer": g} and calque(g)["kind"] == "Pixel", (r, calque(g)["kind"]))
    etat("2l fusionner le groupe", "Merge Group", h0)
    # Cadre : un groupe découpé par la forme
    h0 = historique(s); r = ex("layer.new.frame", {"x": 10, "y": 10, "width": 50, "height": 40, "shape": "ellipse"})
    check("2m Nouveau cadre : un groupe masqué par l'ellipse", r.get("frame") == [10, 10, 50, 40] and r.get("shape") == "ellipse"
          and calque(r["layer"])["kind"] == "Group" and calque(r["layer"])["hasMask"] is True, r)
    etat("2m nouveau cadre", "New Frame", h0)
    m = erreur("layer.new.frame", {"x": 0, "y": 0, "width": 0, "height": 10})
    check("2m cadre de largeur nulle : erreur du moteur", m is not None and "1..=300000" in m, m)
    # Objet dynamique -> calques
    ex("layer.select", {"layer": g, "mode": "replace"}); ex("layer.smartObjects.convertToSmartObject", {})
    h0 = historique(s); r = ex("layer.smartObjects.convertToLayers", {})
    check("2n Convertir en calques : l'objet dynamique redevient un calque de pixels",
          r.get("group") is False and calque(r["layer"])["kind"] == "Pixel", r)
    etat("2n convertir en calques", "Convert to Layers", h0)
    m = erreur("layer.smartObjects.convertToLayers", {})
    check("2n sur un calque de pixels : « not available right now »", m is not None and "not available" in m, m)
    for c, p in (("layer.smartObjects.updateChanged", {}), ("layer.smartObjects.exportContents", {"path": "so.png"})):
        m = erreur(c, p)
        check(f"2o {c} : désactivée par le moteur en automation (restée fermée au pont)", m is not None and "ambient filesystem paths" in m, m)
    # Arrière-plan d'après un calque
    m = erreur("layer.new.backgroundFromLayer", {})
    check("2p un arrière-plan existe déjà : « not available right now »", m is not None and "already has a Background" in m, m)
    # Plans de travail : voisin vide, puis copie
    ex("layer.new.artboard", {"x": 0, "y": 0, "width": 100, "height": 80})
    h0 = historique(s); r = ex("layer.artboard.addBeside", {})
    check("2q plan de travail voisin à droite, 100 px plus loin", r.get("rect") == [200, 0, 100, 80], r)
    etat("2q plan de travail voisin", "New Artboard", h0)
    h0 = historique(s); r = ex("layer.artboard.addBeside", {"side": "bottom", "duplicate": True})
    check("2q copie du plan de travail en dessous", r.get("rect") == [200, 180, 100, 80], r)
    etat("2q copie du plan de travail", "Duplicate Artboard", h0)
    # Copier vers un document : le DESTINATAIRE devient actif et reçoit « Duplicate Layer » ; la source ne change pas
    s.appeler("doc.new", {"width": 100, "height": 80, "background": "transparent"})
    h0 = historique(s); r = ex("layer.new.backgroundFromLayer", {})
    check("2p Arrière-plan d'après un calque : le calque devient « Background »", ins()["layers"][-1]["name"] == "Background", r)
    etat("2p arrière-plan d'après un calque", "Background From Layer", h0)
    src = s.appeler("session.list")["active"]
    h_src = historique(s)
    s.appeler("doc.select", {"index": 0}); h_dst = historique(s); s.appeler("doc.select", {"index": src})
    r = ex("layer.copyToDocument", {"document": 0, "center": True})
    actif = s.appeler("session.list")["active"]
    h_dst1 = historique(s)
    s.appeler("doc.select", {"index": src})
    check("2r Dupliquer vers un document : le destinataire devient actif, la copie y est centrée",
          actif == 0 and r.get("document") == 0 and isinstance(r.get("offset"), list) and len(r["offset"]) == 2, (actif, r))
    check("2r le destinataire gagne « Duplicate Layer », la source rien", h_dst1 == h_dst + ["Duplicate Layer"] and historique(s) == h_src,
          (h_dst1[-2:], historique(s)[-2:]))
    noms.append("Duplicate Layer")
    m = erreur("layer.copyToDocument", {"document": src})
    check("2r vers soi-même : erreur du moteur", m is not None and "the destination is the source" in m, m)
    return noms


def traductions(noms):
    print("\n[3] noms d'historique traduits (ETATS_MOTEUR -> photolab.json fr/en)")
    src = (RACINE / "frontend/photolab/js/mod-historique.js").read_text(encoding="utf-8")
    bloc = src[src.index("export const ETATS_MOTEUR"):]
    bloc = bloc[:bloc.index("};")]
    table = dict(re.findall(r'"([^"]+)":\s*"(photolab\.[a-z0-9_.]+)"', bloc))
    dico = json.loads((RACINE / "frontend/shared/i18n/photolab.json").read_text(encoding="utf-8"))
    for n in sorted(set(noms)):
        cle = table.get(n)
        check(f"3a « {n} » -> {cle}", cle is not None and bool((dico.get(cle) or {}).get("fr"))
              and bool((dico.get(cle) or {}).get("en")), cle)


def etapes(reg):
    print("\n[4] étapes d'action rejouables")
    for cid, p in ADMIS:
        try:
            PR.verifier_etape(reg, cid, p)
            check(f"4a {cid} rejouable dans une action", True)
        except ValueError as e:
            check(f"4a {cid} rejouable dans une action", False, e)
    for cid, p in (("layer.setLabelColor", {"color": "pink"}), ("layer.layerStyle.makeDefault", {"kind": "stroke", "params": {"x": 1}})):
        try:
            PR.verifier_etape(reg, cid, p); check(f"4b {cid} mal formée refusée à la lecture", False)
        except ValueError:
            check(f"4b {cid} mal formée refusée à la lecture", True)


OUVERTES_HISTO = ("history.newSnapshot", "history.deleteSnapshot", "history.renameSnapshot", "history.selectSnapshot",
                  "history.newDocument")
FERMEES_HISTO = ("history.undo", "history.redo", "history.selectState", "history.deleteState", "swatches.import",
                 "swatches.export", "swatches.list", "swatches.reset", "swatches.add")


def instantanes(reg):
    print("\n[5] instantanés : liste blanche puis VRAI moteur")
    check("5.0 les 5 commandes d'instantané ouvertes ; undo/redo/selectState/deleteState et swatches.* fermées",
          not (set(OUVERTES_HISTO) & PN.COMMANDES_NEUVES_FERMEES) and set(FERMEES_HISTO) <= PN.COMMANDES_NEUVES_FERMEES)
    for cid, p in (("history.newSnapshot", {}), ("history.newSnapshot", {"name": "Avant retouche", "from": "mergedLayers"}),
                   ("history.newSnapshot", {"from": "currentLayer"}), ("history.renameSnapshot", {"snapshot": 2, "name": "Après"}),
                   ("history.selectSnapshot", {"snapshot": 1}), ("history.deleteSnapshot", {"snapshot": 1}),
                   ("history.newDocument", {}), ("history.newDocument", {"state": 3, "name": "Copie"})):
        a, m = admise(reg, cid, p)
        check(f"5a {cid} {sorted(p)} admis", a, m)
    for cid, p in (("history.newSnapshot", {"name": ""}), ("history.newSnapshot", {"name": "x" * 65}),
                   ("history.newSnapshot", {"name": "a\nb"}), ("history.newSnapshot", {"from": "tout"}),
                   ("history.renameSnapshot", {"snapshot": 1}), ("history.renameSnapshot", {"name": "x"}),
                   ("history.selectSnapshot", {}), ("history.selectSnapshot", {"snapshot": -1}),
                   ("history.deleteSnapshot", {"snapshot": "1"}), ("history.newDocument", {"state": -1}),
                   ("history.undo", {}), ("history.selectState", {"state": 0}), ("swatches.list", {})):
        a, _ = admise(reg, cid, p)
        check(f"5b {cid} {json.dumps(p, ensure_ascii=False)[:60]} refusé", not a)
    for cid, p in (("history.newSnapshot", {"name": "Avant"}), ("history.selectSnapshot", {"snapshot": 1})):
        try:
            PR.verifier_etape(reg, cid, p); check(f"5c {cid} rejouable dans une action", True)
        except ValueError as e:
            check(f"5c {cid} rejouable dans une action", False, e)
    try:
        PM.chemin_cli()
    except PM.MoteurAbsent as e:
        check("5d le binaire du moteur est présent", False, e)
        return
    s = PM.session()
    ex = lambda c, p=None: s.appeler("engine.execute", {"command": c, "params": p or {}})
    ins = lambda: s.appeler("doc.inspect")
    s.appeler("doc.new", {"width": 100, "height": 80, "background": "white"})
    ex("layer.new.layer", {})
    h0 = historique(s)
    r1 = ex("history.newSnapshot", {"name": "Avant"}); r2 = ex("history.newSnapshot", {})
    check("5d deux instantanés, aucun état d'historique, relus par doc.inspect.snapshots",
          historique(s) == h0 and ins().get("snapshots") == [{"id": r1["snapshot"], "name": "Avant"}, {"id": r2["snapshot"], "name": r2["name"]}],
          ins().get("snapshots"))
    ex("history.renameSnapshot", {"snapshot": r2["snapshot"], "name": "Fond"})
    check("5e renommer : le nouveau nom, aucun état", ins()["snapshots"][1]["name"] == "Fond" and historique(s) == h0)
    ex("select.all"); ex("edit.fill", {"color": "#ff0000"})
    h1 = historique(s); ex("history.selectSnapshot", {"snapshot": r1["snapshot"]})
    check("5f choisir l'instantané : UN état nommé comme lui (le document y revient)", historique(s) == h1 + ["Avant"], historique(s)[-2:])
    ex("history.deleteSnapshot", {"snapshot": r1["snapshot"]})
    check("5g supprimer : il reste « Fond », le document ne change pas", [x["name"] for x in ins()["snapshots"]] == ["Fond"]
          and historique(s)[-1] == "Avant")
    try:
        ex("history.selectSnapshot", {"snapshot": 99}); m = None
    except PM.MoteurErreur as e:
        m = str(e)
    check("5h instantané inconnu : erreur du moteur (no snapshot)", m is not None and "no snapshot" in m, m)
    avant = s.appeler("session.list")["active"]
    r = ex("history.newDocument", {"state": 0, "name": "Origine"})
    sl = s.appeler("session.list")
    check("5i Nouveau document d'après l'état : un document de plus, ACTIF, qui ne porte qu'« Open »",
          sl["active"] == r["document"] != avant and ins()["name"] == "Origine" and historique(s) == ["Open"], (sl["active"], r, historique(s)))


def nuancier(reg):
    print("\n[6] nuancier .aco / .ase")
    from app.services import photolab_nuancier as NUA
    liste = {"groups": [{"name": "  Mes   couleurs ", "swatches": [{"hex": "#FF0000", "name": "Rouge"}, {"hex": "rouge"},
                                                                  {"hex": "#00ff00", "name": "x" * 90}]},
                        {"name": "Vide", "swatches": []}, {"name": "", "swatches": [{"hex": "#0000ff"}]}]}
    g = NUA.groupes_depuis_moteur(liste, ["g-1"])
    check("6a conversion : hex en minuscules, nuance illisible écartée, nom tronqué à 64, groupe vide écarté, ids libres",
          g == [{"id": "g-2", "nom": "Mes couleurs", "couleurs": [{"hex": "#ff0000", "nom": "Rouge"}, {"hex": "#00ff00", "nom": "x" * 64}]},
                {"id": "g-3", "nom": "g-3", "couleurs": [{"hex": "#0000ff", "nom": ""}]}], g)
    e0 = NUA.etat_defaut()
    check("6b fusionner : append à la suite, replace remplace (récentes gardées)",
          len(NUA.fusionner(e0, g, "append")["groupes"]) == 6 and NUA.fusionner({**e0, "recentes": ["#123456"]}, g, "replace")
          == {**e0, "recentes": ["#123456"], "groupes": g})
    for corps in ({}, {"data": "!!!"}, {"data": "QUFB", "mode": "tout"}, {"data": "QUFB", "format": "gpl"},
                  {"data": "QUFB", "chemin": "x.aco"}, {"data": "A" * 3_000_000}):
        try:
            NUA.importer(None, corps); m = None
        except ValueError as e:
            m = str(e)
        check(f"6c import refusé AVANT le moteur : {json.dumps(corps)[:50]}", m is not None, m)
    for corps in ({"format": "gpl", "groupes": [{"nom": "a", "couleurs": [{"hex": "#000000", "nom": ""}]}]},
                  {"format": "ase", "groupes": []}, {"format": "ase", "groupes": [{"nom": "", "couleurs": []}]},
                  {"format": "ase", "groupes": [{"nom": "a", "couleurs": [{"hex": "#GG0000", "nom": ""}]}]},
                  {"format": "ase", "groupes": [{"nom": "a", "couleurs": []}]}):
        try:
            NUA.exporter(None, corps); m = None
        except ValueError as e:
            m = str(e)
        check(f"6d export refusé AVANT le moteur : {json.dumps(corps)[:60]}", m is not None, m)
    try:
        PM.chemin_cli()
    except PM.MoteurAbsent as e:
        check("6e le binaire du moteur est présent", False, e)
        return
    s = PM.session()
    usine = s.appeler("engine.execute", {"command": "swatches.list", "params": {}})
    nos = [{"nom": "Marque", "couleurs": [{"hex": "#e35d4a", "nom": "Corail"}, {"hex": "#5ec8a0", "nom": ""}]},
           {"nom": "Gris", "couleurs": [{"hex": "#808080", "nom": "Moyen"}]}]
    fichiers = {}
    for fmt in ("ase", "aco"):
        r = NUA.exporter(s, {"format": fmt, "groupes": nos})
        fichiers[fmt] = r["data"]
        check(f"6e export {fmt} : 3 couleurs, la bibliothèque du moteur revient aux défauts d'usine",
              r["count"] == 3 and r["format"] == fmt and s.appeler("engine.execute", {"command": "swatches.list", "params": {}}) == usine, r["count"])
    NUA.ecrire(NUA.etat_defaut())
    r = NUA.importer(s, {"data": fichiers["ase"], "mode": "append"})
    noms = [x["nom"] for x in r["groupes"]]
    check("6f import .ase en append : les 4 groupes fournis + Marque et Gris, couleurs et noms gardés",
          r["importees"] == 3 and noms[-2:] == ["Marque", "Gris"] and len(noms) == 6
          and r["groupes"][4]["couleurs"][0] == {"hex": "#e35d4a", "nom": "Corail"} and NUA.lire()["groupes"] == r["groupes"], noms)
    r = NUA.importer(s, {"data": fichiers["aco"], "mode": "replace"})
    check("6g import .aco en replace : un seul groupe (.aco n'a pas de groupes), les 3 couleurs",
          len(r["groupes"]) == 1 and [c["hex"] for c in r["groupes"][0]["couleurs"]] == ["#e35d4a", "#5ec8a0", "#808080"], r["groupes"])
    try:
        NUA.importer(s, {"data": "QUFBQUFBQUE=", "format": "aco"}); m = None
    except (ValueError, PM.MoteurErreur) as e:
        m = str(e)
    check("6h fichier illisible : erreur du moteur, le nuancier et la bibliothèque inchangés",
          m is not None and NUA.lire() == {k: v for k, v in r.items() if k != "importees"}
          and s.appeler("engine.execute", {"command": "swatches.list", "params": {}}) == usine, m)



def deformer(reg):
    print("\n[7] Ctrl+T › Déformer")
    check("7.0 edit.transform.warpGrid ouverte ; edit.transform.warp admise en aperçu",
          "edit.transform.warpGrid" not in PN.COMMANDES_NEUVES_FERMEES and PM._admise_en_apercu("edit.transform.warp"))
    W = {"style": "custom", "bend": 0, "hDistort": 0, "vDistort": 0, "vertical": False, "bounds": [0, 0, 200, 120],
         "mesh": {"us": [0, 1], "vs": [0, 1], "points": [[x, y] for y in (0, 40, 80, 120) for x in (0, 66.7, 133.3, 200)]}}
    for p in ({"style": "none", "rect": [0, 0, 200, 120], "size": "default"}, {"style": "none", "rect": [10, 5, 90, 60], "size": "5"},
              {"warp": W, "size": "3"}):
        a, m = admise(reg, "edit.transform.warpGrid", p)
        check(f"7a warpGrid {sorted(p)} admis", a, m)
    a, m = admise(reg, "edit.transform.warp", {"layer": 3, "warp": W, "interpolation": "bicubic"})
    check("7a edit.transform.warp {layer, warp, interpolation} admis", a, m)
    for p in ({"size": "3"}, {"style": "none", "size": "3"}, {"style": "arc", "rect": [0, 0, 1, 1], "size": "3"},
              {"style": "none", "rect": [0, 0, 1, 1], "size": "64"}, {"style": "none", "rect": [0, 0, 1, 1], "size": 3},
              {"warp": {**W, "fichier": "C:/x.png"}, "size": "3"}):
        a, _ = admise(reg, "edit.transform.warpGrid", p)
        check(f"7b warpGrid {json.dumps(p)[:70]} refusé", not a)
    try:
        PM.chemin_cli()
    except PM.MoteurAbsent as e:
        check("7c le binaire du moteur est présent", False, e)
        return
    s = PM.session()
    ex = lambda c, p=None: s.appeler("engine.execute", {"command": c, "params": p or {}})
    s.appeler("doc.new", {"width": 200, "height": 120, "background": "white"})
    ex("layer.new.layer", {}); ex("select.all"); ex("edit.fill", {"color": "#ff0000"}); ex("select.deselect")
    calque = s.appeler("doc.inspect")["activeLayer"]
    h0 = historique(s)
    w1 = ex("edit.transform.warpGrid", {"style": "none", "rect": [0, 0, 200, 120], "size": "default"})["warp"]
    w3 = ex("edit.transform.warpGrid", {"style": "none", "rect": [0, 0, 200, 120], "size": "3"})["warp"]
    pts = w1["mesh"]["points"]
    check("7c maillage neutre : 4 × 4 points (Par défaut), 10 × 10 en 3 × 3, bords sur le cadre, aucun état",
          len(pts) == 16 and len(w3["mesh"]["points"]) == 100 and pts[0] == [0, 0] and pts[15] == [200, 120]
          and w3["mesh"]["us"][1] == 1 / 3 and historique(s) == h0, (len(pts), len(w3["mesh"]["points"])))
    w = json.loads(json.dumps(w1)); w["mesh"]["points"][5] = [w["mesh"]["points"][5][0] + 20, w["mesh"]["points"][5][1] + 15]
    ws = ex("edit.transform.warpGrid", {"warp": w, "size": "3"})["warp"]
    check("7d découpe 3 × 3 d'un maillage modifié : 100 points, les coins restent, la surface aussi (point (1/3,1/3) déplacé)",
          len(ws["mesh"]["points"]) == 100 and ws["mesh"]["points"][0] == [0, 0]
          and ws["mesh"]["points"][33] != w3["mesh"]["points"][33], ws["mesh"]["points"][33])
    r = ex("edit.transform.warp", {"layer": calque, "warp": w1})
    check("7e maillage neutre : rien ne change, aucun état", r.get("changed") is False and historique(s) == h0, r)
    r = ex("edit.transform.warp", {"layer": calque, "warp": ws, "interpolation": "bicubic"})
    check("7f valider : le calque change, UN état « Warp »", r.get("changed") is True and historique(s) == h0 + ["Warp"], (r, historique(s)[-2:]))
    import asyncio

    async def routes():
        import httpx
        from app.main import app
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
            h1 = historique(s)
            r = await c.post("/api/photolab/deformer/grille", json={"style": "none", "rect": [0, 0, 200, 120], "size": "4"})
            j = r.json() if r.status_code == 200 else {}
            check("7g POST /deformer/grille : le maillage 4 × 4 (169 points), aucun état", r.status_code == 200
                  and len(((j.get("warp") or {}).get("mesh") or {}).get("points") or []) == 169 and historique(s) == h1, (r.status_code, r.text[:200]))
            r = await c.post("/api/photolab/deformer/grille", json={"style": "none", "rect": [0, 0, 200, 120], "size": "64"})
            check("7g grille hors liste : 400", r.status_code == 400, (r.status_code, r.text[:200]))
            r = await c.post("/api/photolab/deformer/grille", json={"size": "3"})
            check("7g sans maillage ni cadre : 400 (le moteur viserait l'objet dynamique)", r.status_code == 400, (r.status_code, r.text[:200]))
            r = await c.post("/api/photolab/apercu", json={"etapes": [{"command": "edit.transform.warp", "params": {"layer": calque, "warp": ws}}], "maxSide": 64})
            check("7h /apercu joue edit.transform.warp sur une copie : une image, le document ne change pas",
                  r.status_code == 200 and bool(r.json().get("url")) and historique(s) == h1, (r.status_code, r.text[:200]))
    asyncio.run(routes())

reg = PR.structurer(_PV.commandes())
try:
    liste_blanche(reg)
    etapes(reg)
    traductions(moteur())
    instantanes(reg)
    nuancier(reg)
    deformer(reg)
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
