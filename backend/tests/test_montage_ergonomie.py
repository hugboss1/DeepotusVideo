"""E-12 (lot E-C, tache 6, 23/09/2026) — AUDIT BANCABLE DES BOUTONS DU MONTAGE.

Deux regles, verrouillees par SCAN DES SOURCES (precedent :
test_subs_regle_des_gestes.py ; l'audit DOM du Vectorlab,
frontend/vectorlab/qa/ergonomie.test.mjs, est l'autre precedent) :

  REGLE 1 — INFOBULLE OBLIGATOIRE. Tout `r.jsx("button",{className:"…"` dont
  les classes portent svm-tbtn | dzm-tbb | svm-secbtn | svm-goldbtn |
  svm-minibtn | svm-viewbtn | svm-menuitem | svm-menubtn porte `title:` dans
  les 400 caracteres qui suivent (avant le prochain `r.jsx` / `r.jsxs`). La fabrique
  `.dzm-tbb` (DzmToolBtn, couche) est reconnue : le `title:o.title||lbl` est
  dans la fabrique, aucun `className:"dzm-tbb` litteral n'existe.

  REGLE 2 — UN BOUTON D'OUTIL SE GRISE, IL NE DISPARAIT PAS. Aucun bouton
  svm-tbtn / svm-secbtn / svm-goldbtn n'est rendu selon l'etat par
  `x?null:r.jsx("button"…` ou `x?r.jsx("button"…):null` ou `x&&r.jsx("button"`.
  Les BASCULES (les deux branches rendent un bouton : ok/renommer, Reessayer/
  Rendre) et les CONTROLES CONTEXTUELS TOLERES (chips, M/S de piste sans bus,
  minibtn de l'overlay et de l'inspecteur, kbreset, projets, medplus,
  composants de la couche rendant null) sont PINNES par leur forme exacte et
  DATES : si l'un bouge (ajoute, retire, reecrit), le banc rougit et on redate.

ZONES SCANNEES (bornes mesurees 1/1 chacune) : DzMontage (`function
DzMontage(` -> en-tete de la couche SFX Studio) et la couche montage (`/* ──
Montage, couche window.DzTracks` -> `window.DzTracks=DzTracks;`). ENTRE les
deux vivent les couches SFX Studio (sfxstudio.js), rack VFX et sous-titres
d'autres chantiers, avec leurs propres patchers : HORS AUDIT, ecart date
(23/09/2026) — leurs boutons `svm-secbtn` sans titre (Reessayer, Effacer la
recherche, Importer un son, Generer un SFX, svx-measure conditionnel) restent
a ces chantiers.

ETAT VIDE (regle des assertions negatives) : le meme scanner, passe sur
`.bak_montage` (l'entree du patcher, zone DzMontage seule : la couche n'y est
pas), DOIT trouver des manquants et les deux `proj.demo?null:` — sinon
« manquants == [] » ne prouverait rien. Faute n°6 : aucune lecture nue avant un
check ; un fichier absent est un FAIL compte, pas une trace.

Un processus, `check`, `=== N passed, M failed ===`, code de sortie.
"""
import pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
LAYER = ROOT / "frontend" / "patches" / "montage.js"

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


for p in (BUNDLE, BAK, LAYER):
    if not p.is_file():
        print(f"  FAIL  fichier_absent {p}")
        print("\n=== 0 passed, 1 failed ===")
        sys.exit(1)

# OCTETS, utf-8-sig, fins de ligne CONSERVEES (le bundle mele LF et CRLF).
s = BUNDLE.read_bytes().decode("utf-8-sig")
bak = BAK.read_bytes().decode("utf-8-sig")
lay = LAYER.read_bytes().decode("utf-8-sig")

Z1_DEB = "function DzMontage("
Z1_FIN = "/* ── SFX Studio — couche window.DzSfx"
Z2_DEB = "/* ── Montage, couche window.DzTracks"
Z2_FIN = "window.DzTracks=DzTracks;"

CLASSES = re.compile(r"svm-tbtn|dzm-tbb|svm-secbtn|svm-goldbtn|svm-minibtn|svm-viewbtn|svm-menuitem|svm-menubtn")
OUTIL = re.compile(r"svm-tbtn|svm-secbtn|svm-goldbtn")
# REVUE (23/09/2026) : `r.jsx` ET `r.jsxs` (le seul svm-menuitem est un jsxs,
# couche :6737) ; `type:"button",` peut PRECEDER className (dzm-tbtab,
# dzm-tbgrip, dzm-tbwb x2 : quatre boutons de la barre d'outils, hors classes
# auditees mais vus par le scanner desormais).
_PROPS = r'\{(?:[^}\n]{0,60}?,)?className:"([^"]*)"'
RX_BTN = re.compile(r'r\.jsxs?\("button",' + _PROPS)
# un bouton conditionnel : `?r.jsx("button"`, `&&r.jsx("button"` (espaces et
# sauts de ligne admis) ou `?null:r.jsx("button"`
RX_COND = re.compile(r'(\?null:|\?|&&)\s*r\.jsxs?\("button",' + _PROPS)
# ECART DATE (23/09/2026) : le « Oui » de la narration et de la generation SFX
# (`svm-nbgold`, .bak x3) est HORS classes auditees — sans title, non corrige.


def zones(t, avec_couche):
    """Bornes des zones — mesurees (1/1), None si un marqueur manque ou double."""
    out = []
    for d, f in ((Z1_DEB, Z1_FIN),) + (((Z2_DEB, Z2_FIN),) if avec_couche else ()):
        if t.count(d) != 1 or t.count(f) != 1 or t.index(d) >= t.index(f):
            return None
        out.append((t.index(d), t.index(f)))
    return out


def ligne(t, i):
    return t[:i].count("\n") + 1


def scan_titres(t, zs):
    """(nb de boutons des classes auditees, [(ligne, classes, extrait) sans title])."""
    n, manq = 0, []
    for a, b in zs:
        z = t[a:b]
        for m in RX_BTN.finditer(z):
            if not CLASSES.search(m.group(1)):
                continue
            n += 1
            fen = z[m.end():m.end() + 400]
            # REVUE (23/09/2026) : `r.jsx` sans parenthese — couvre jsx ET jsxs ;
            # avec `r.jsx(`, un frere `r.jsxs(` titre juste apres masquait un
            # manquant (mutation B : title retire + leurre r.jsxs("span",{title:…})
            # -> faux vert).
            k = fen.find("r.jsx")
            if k >= 0:
                fen = fen[:k]
            if "title:" not in fen:
                manq.append((ligne(t, a + m.start()), m.group(1), z[m.start():m.start() + 130].replace("\r", "").replace("\n", "⏎")))
    return n, manq


def scan_cond(t, zs):
    """Tous les boutons conditionnels des zones : (ligne, forme, classes, contexte
    de 80 caracteres avant, blancs replies)."""
    out = []
    for a, b in zs:
        z = t[a:b]
        for m in RX_COND.finditer(z):
            ctx = re.sub(r"\s+", " ", z[max(0, m.start() - 80):m.end()].replace("\r", ""))
            out.append((ligne(t, a + m.start()), m.group(1), m.group(2), ctx))
    return out


ZS = zones(s, True)
ZB = zones(bak, False)
check("zones_du_bundle_mesurees_1_1_DzMontage_puis_couche",
      ZS is not None and len(ZS) == 2 and ZS[0][1] < ZS[1][0]
      and s.count(Z1_DEB) == 1 and s.count(Z1_FIN) == 1 and s.count(Z2_DEB) == 1 and s.count(Z2_FIN) == 1,
      f"{[s.count(k) for k in (Z1_DEB, Z1_FIN, Z2_DEB, Z2_FIN)]}")
check("zone_DzMontage_du_bak_mesuree_et_la_couche_ABSENTE_du_bak",
      ZB is not None and len(ZB) == 1 and bak.count(Z1_DEB) == 1 and bak.count(Z2_DEB) == 0 and bak.count(Z2_FIN) == 0,
      f"{[bak.count(k) for k in (Z1_DEB, Z1_FIN, Z2_DEB, Z2_FIN)]}")
if ZS is None or ZB is None:
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

# ── REGLE 1 ─────────────────────────────────────────────────────────────────
n_b, manq_b = scan_titres(s, ZS)
n_l, manq_l = scan_titres(lay, [(0, len(lay))])
n_k, manq_k = scan_titres(bak, ZB)
check("R1_bundle_tout_bouton_audite_porte_title_temoin_40_boutons",
      manq_b == [] and n_b >= 40, f"scannes={n_b} manquants={manq_b}")
check("R1_couche_tout_bouton_audite_porte_title_temoin_20_boutons_et_le_menuitem_jsxs",
      manq_l == [] and n_l >= 21 and lay.count('r.jsxs("button",{className:"svm-menuitem"') == 1
      and RX_BTN.search('r.jsxs("button",{className:"svm-menuitem",') is not None
      and RX_BTN.search('r.jsx("button",{type:"button",className:"dzm-tbtab",') is not None,
      f"scannes={n_l} manquants={manq_l}")
# ETAT VIDE : le scanner VOIT — l'entree du patcher a des boutons sans titre
# (Fermer x4, Reessayer, le bouton or busy, retirer, oui/non x2, Non : 13 le
# 23/09/2026) que ce lot a titres. Un scanner aveugle donnerait 0 ici aussi.
check("R1_etat_vide_le_scanner_trouve_les_manquants_du_bak_temoin",
      n_k >= 30 and len(manq_k) >= 10
      and any("Fermer" in m[2] for m in manq_k) and any("Réessayer" in m[2] for m in manq_k),
      f"bak scannes={n_k} manquants={len(manq_k)}")
# la fabrique .dzm-tbb : UN site, `title:o.title||lbl` a moins de 600 caracteres,
# aucun className litteral dzm-tbb (bundle et couche)
_i = lay.find('var cls="dzm-tbb";')
check("R1_fabrique_dzm_tbb_unique_porte_title_o_title_ou_lbl",
      lay.count('var cls="dzm-tbb";') == 1 and _i > 0 and 'title:o.title||lbl,' in lay[_i:_i + 600]
      and lay.count('title:o.title||lbl,') == 1 and s.count('title:o.title||lbl,') == 1
      and lay.count('className:"dzm-tbb') == 0 and s.count('className:"dzm-tbb') == 0)
# titres POSES par ce lot (bundle) — le libelle dit ce que fait le bouton
_TITRES = [
    'title:proj.demo?"Rendu indisponible sur la démo — ouvre un projet réel":"Relancer le rendu qui a échoué"',
    'title:proj.demo?"Rendu indisponible sur la démo — ouvre un projet réel":(isR?"Lancer le rendu final (master 1080, local)":"Lancer l\'aperçu 480p (gratuit, local)")',
    'title:"Fermer ce panneau (Échap)",onClick:function(){setPop("");if(failed)setJob(null)},children:"Fermer"',
    'title:"Fermer le sélecteur d\'effets",onClick:function(){setFxPick(!1)},children:"Fermer"',
    'title:"Fermer le sélecteur d\'overlay",onClick:function(){setOvPick("")},children:"Fermer"',
    'title:"Fermer le panneau des raccourcis (Échap)",onClick:function(){setKbOn(!1)},children:"Fermer"',
    'title:"Retirer cet effet du plan",onClick:function(){',
    'title:"Confirmer : tous les raccourcis reviennent au défaut",',
    'title:"Garder les raccourcis personnalisés",',
    'title:"Annuler — aucune voix générée, aucun crédit consommé",',
    'title:"Confirmer : la sauvegarde est écrasée par la Bibliothèque",onClick:svmLibReset,children:"oui"',
    'title:"Garder la sauvegarde",',
    'title:proj.demo?"Réinitialisation indisponible sur la démo":"Réinitialiser depuis la Bibliothèque — écrase la sauvegarde"',
    'title:"Aperçu 480p — gratuit, local, aucun crédit",onClick:function(){setPop(pop==="preview"?"":"preview")},children:"Preview"',
    'title:"Rendu final (master 1080, local) — ouvre le panneau de rendu",onClick:function(){setPop(pop==="render"?"":"render")},children:"Rendre →"',
    # L7 D-10 (24/09/2026, tache 1) : les trois boutons du panneau « ? »
    'title:"Preset Resolve : pose O (sortie), Ctrl+B (lame), Alt+O (barre d\'outils) — Ctrl+T reste au navigateur, la transition est sur Alt+T",',
    'title:"Exporter les raccourcis personnalisés (deepotus-raccourcis.json)",',
    'title:"Importer un fichier de raccourcis JSON — les actions inconnues et les touches réservées sont ignorées",',
    # L7 D-8 (24/09/2026, tache 3) : le popover « Plans trop longs / jump cuts » -- la case, les deux champs, « Fermer »
    'title:"Marquer sur la timeline les plans trop longs et les jump cuts de V1",',
    'title:"Un plan de V1 plus long que ce seuil (2 à 60 s) est marqué « long »",',
    'title:"Deux plans V1 de la même source, en contact, dont la reprise est à moins de n images (1 à 60, à 30 i/s) : jump cut",',
    'title:"Fermer ce panneau (Échap)",onClick:function(){setPop("")},children:"Fermer"',
    # L7 D-3b (24/09/2026, tache 4-bis) : la rangee A/B du popover de jonction -- deux vignettes, deux boutons de roll
    'title:"A — dernière image du plan de gauche"',
    'title:"Reculer la jonction d\'une image (Maj : dix) — A raccourcit, B s\'allonge",',
    'title:"Avancer la jonction d\'une image (Maj : dix) — A s\'allonge, B raccourcit",',
    'title:"B — première image du plan de droite"',
    # L7 D-19 (24/09/2026, tache 5, client) : le champ « Coins » et la case « Ombre portée » de l'inspecteur d'overlay
    'title:"Rayon des coins de l\'overlay en px du canvas (0 = coins droits, 200 au plus) — statique, les keyframes ne l\'animent pas",',
    'title:"Ombre portée sous l\'overlay (noir à 55 %, décalée de 6 px au rendu) — statique, retirée par « plein cadre »",',
    # L7 D-22 (24/09/2026, tache 6) : la case « nouvelle piste » du tiroir de traduction (les cinq entrees du menu de
    # piste portent title:it.lbl par DzmCtxMenu, deja audite)
    'title:"Coché : la traduction naît dans une nouvelle piste de sous-titres S2, S3… (S1 reste intacte ; la piste gravée au rendu se choisit par clic droit sur sa tête). Décoché : S1 est réécrite.",',
]
for t in _TITRES:
    check("R1_titre_pose_x1_" + re.sub(r"\W+", "_", t[6:40]).strip("_"),
          s.count(t) == 1 and bak.count(t) == 0, f"bundle={s.count(t)} bak={bak.count(t)}")
# ECART DATE (23/09/2026) : le titre du bandeau de fin fait 76 caracteres —
# a raccourcir au prochain passage sur la couche.
_TITRES_COUCHE = [
    'title:"Fermer l\'index des marqueurs",onClick:o&&o.onClose,',
    'title:"Envoyer ce rendu au Scheduler (brouillon, rien n\'est publié sans validation)",',
    'title:"Ouvrir la Bibliothèque sur ce rendu",onClick:function(){o.onLib&&o.onLib()},children:"Voir dans la Bibliothèque"',
    'title:"Fermer le bandeau (Échap)",onClick:function(){o.onClose&&o.onClose()},children:"Fermer"',
    'title:"Fermer le tiroir Médias",onClick:function(){if(o.onClose)o.onClose()},children:"Fermer"',
    'title:"Charger les rendus suivants",',
    # L7 D-39 (24/09/2026, tache 4) : « ⇄ » de la ligne Projets (branche « comparer » du titre, une ligne) et le
    # « Fermer » de la vue diff -- dans la COUCHE, donc ici et non dans _TITRES (ecart au plan, qui disait _TITRES +2)
    ':"Comparer « "+(p.name||"")+" » à la timeline courante (rien n\'est modifié)",',
    'title:"Fermer la comparaison (Échap)",onClick:function(){if(o.onClose)o.onClose()},children:"Fermer"',
    # L7-B D-34 (24/09/2026, tache 7) : les cinq etoiles d'une ligne du tiroir Medias (l'etoile courante dit « retirer »)
    # et les deux chips de note (la chip active dit « retirer le filtre ») -- classes hors audit R1, titrees quand meme
    # revue 24/09 : l'infobulle est calculee une fois (ti) et sert aussi d'aria-label
    'var ti=i===cur?"Retirer la note ("+i+" ★)":"Noter "+i+" ★"+(i===5?" — Good Take":"");',
    'title:ti,"aria-label":ti,',
    'title:minNote===n[0]?"Retirer le filtre de note — tous les rendus":n[2],',
    # L7-B D-41 (24/09/2026, tache 6) : « ✂ auto-clips » d'une ligne du tiroir Medias (classe hors audit R1, titree quand
    # meme), puis le popover : « Fermer », le bouton or (titre calcule, goTi) et « Creer le projet » (branche non armee)
    'title:"Auto-clips — proposer des extraits de 15 à 60 s de ce rendu (texte connu gratuit ; transcription payante seulement après confirmation)",',
    'title:"Fermer les auto-clips (rien n\'est lancé)",',
    'className:"svm-goldbtn dzm-acgo",disabled:!!busy,title:goTi,onClick:lancer,children:goTxt',
    ':"Créer un projet neuf avec cet extrait (V1, son du plan, sous-titres) — un second clic confirme",',
]
for t in _TITRES_COUCHE:
    check("R1_titre_couche_x1_" + re.sub(r"\W+", "_", t[6:40]).strip("_"),
          lay.count(t) == 1 and s.count(t) == 1 and bak.count(t) == 0,
          f"couche={lay.count(t)} bundle={s.count(t)} bak={bak.count(t)}")

# ── REGLE 2 ─────────────────────────────────────────────────────────────────
# Le bouton or du popover de rendu et « bibliothèque » : RENDUS TOUJOURS,
# grises sur la demo (handlers deja gardes : launchRender `if(proj.demo||…)return`,
# setLibArm inatteignable sous disabled). Temoin : les deux `proj.demo?null:`
# du .bak, zero dans le livre. ECART DATE (23/09/2026) : `.svm-libbtn:hover`
# s'applique encore au bouton grise (aucune regle :disabled:hover pour lui).
_z1 = s[ZS[0][0]:ZS[0][1]]
_zk = bak[ZB[0][0]:ZB[0][1]]
check("R2_proj_demo_null_devant_un_bouton_0_dans_le_livre_2_dans_le_bak",
      _z1.count("proj.demo?null:") == 0 and _zk.count("proj.demo?null:") == 2
      and re.search(r"proj\.demo\?null:\s*failed\?r\.jsx\(\"button\"", _zk) is not None
      and re.search(r"proj\.demo\?null:libArm\?", _zk) is not None,
      f"livre={_z1.count('proj.demo?null:')} bak={_zk.count('proj.demo?null:')}")
check("R2_bouton_or_du_popover_disabled_busy_ou_demo_et_libbtn_disabled_demo",
      s.count('r.jsx("button",{className:"svm-goldbtn",disabled:busy||proj.demo,style:(busy||proj.demo)?{opacity:.55,cursor:"default"}:null,') == 1
      and s.count('r.jsx("button",{className:"svm-goldbtn",disabled:proj.demo,') == 1
      and s.count('r.jsx("button",{className:"svm-secbtn svm-libbtn",disabled:proj.demo,') == 1
      and _z1.count("libArm?") == 1 and _z1.count("failed?r.jsx(\"button\"") == 1
      and bak.count("disabled:busy||proj.demo") == 0 and bak.count("svm-libbtn\",disabled:proj.demo") == 0
      and s.count("if(proj.demo||(job&&job.status!==\"failed\"))return;") == 1)

# TOUS les boutons conditionnels des deux zones, pinnes par leur forme —
# BASCULES (les deux branches sont un bouton) et TOLERES (contextuels), DATES
# 23/09/2026. Chaque site doit trouver SA forme, et chaque forme son compte.
BASCULES = [
    ("failed?r.jsx(\"button\",{className:\"svm-goldbtn\"", "Réessayer / Rendre : le popover de rendu (echoue ou non)", 1),
    ("edit ?r.jsx(\"button\",{className:\"svm-tbtn dzm-projbtn\"", "ok / renommer : la ligne d'un projet en edition", 1),
]
TOLERES = [  # dates 23/09/2026 — contextuels : ils n'ont de sens que dans l'etat qui les montre
    ("tf||mp?r.jsx(\"button\",{className:\"svm-minibtn\"", "overlay : « revenir au plein cadre » n'existe que s'il y a un cadrage", 1),
    ("isOv&&!editing?r.jsx(\"button\",{className:\"svm-minibtn svm-kbreset\"", "raccourcis : « revenir au defaut » d'une ligne surchargee", 1),
    ("svmSfx()?r.jsx(\"button\",{className:\"svm-themechip svm-sfxchip\"", "chip Sons : absente sans la couche DzSfx (feature-detect)", 1),
    ("sel?r.jsx(\"button\",{className:\"svm-minibtn\"", "inspecteur : la corbeille du clip selectionne", 1),
    ("proj.ducking?r.jsx(\"button\",{className:\"svm-minibtn svm-duckbtn\"", "ducking : « revenir aux reglages » d'un ducking personnalise", 1),
    ("var thM=bus?r.jsx(\"button\",{className:\"svm-minibtn svm-tkbtn\"", "M de piste : seulement sur un bus", 1),
    ("var thS=bus?r.jsx(\"button\",{className:\"svm-minibtn svm-tkbtn svm-tksolo\"", "S de piste : seulement sur un bus", 1),
    ("nu?null:r.jsx(\"button\",{className:\"svm-tbtn dzm-projb\"", "projets : le bouton n'existe pas tant que le montage n'est pas nomme", 1),
    ("!fin?r.jsx(\"button\",{className:\"svm-secbtn svm-medplus\"", "tiroir Medias : « Plus » disparait a la derniere page", 1),
]
conds = scan_cond(s, ZS)
_attendu = {f: (d, n) for f, d, n in BASCULES + TOLERES}
_vus = {f: 0 for f in _attendu}
_orphelins = []
for c in conds:
    hit = [f for f in _attendu if f in c[3]]
    if len(hit) == 1:
        _vus[hit[0]] += 1
    else:
        _orphelins.append(c)
check("R2_chaque_bouton_conditionnel_a_sa_forme_datee_et_chaque_forme_son_compte",
      _orphelins == [] and all(_vus[f] == n for f, (d, n) in _attendu.items())
      and len(conds) == sum(n for _, (_, n) in _attendu.items()) == 11,
      f"orphelins={_orphelins} vus={_vus} total={len(conds)}")
# regle 2 stricte sur les classes d'outil : parmi les conditionnels, seules les
# deux BASCULES et les deux TOLERES DATES (projb, medplus) portent svm-tbtn /
# svm-secbtn / svm-goldbtn — temoin : un `svm-secbtn` non conditionnel existe
_outils_cond = [c for c in conds if OUTIL.search(c[2])]
check("R2_aucun_bouton_d_outil_ne_disparait_hors_bascules_et_toleres_dates_temoin",
      len(_outils_cond) == 4 and all(any(f in c[3] for f, _, _ in BASCULES + TOLERES[7:9]) for c in _outils_cond)
      and s.count('r.jsx("button",{className:"svm-secbtn"') >= 5,
      f"{_outils_cond}")
# le scanner des conditionnels VOIT (etat vide) : le .bak porte proj.demo?null:
# devant le bouton or, que le livre ne porte plus
_ck = scan_cond(bak, ZB)
check("R2_etat_vide_le_bak_porte_le_conditionnel_demo_du_bouton_or",
      any("proj.demo?null:" in c[3] and "svm-goldbtn" in c[2] for c in _ck)
      and not any("proj.demo?null:" in c[3] and "svm-goldbtn" in c[2] for c in conds)
      and len(_ck) >= 7, f"bak={len(_ck)} livre={len(conds)}")
# composants de la couche qui RENDENT null (contextuels, dates 23/09/2026) :
# replaceBtn, revertBtn, gradeAllBtn, extractBtn — chacun UNE fois, garde en tete
_NULLS = [
    ("function dzmReplaceBtn(sel,onArm){", "if(!sel||!sel.src)return null;"),
    ("function dzmRevertBtn(", "if(!h)return null;"),
    ("function dzmGradeAllBtn(", "if(!dzmGradeOf(sel))return null;"),
    ("function dzmExtractBtn(sel,o){", 'if(!sel||!sel.src||sel.src.image||dzmKindOf(sel.tr)!=="video")return null;'),
    # L5 (24/09/2026, tache 5) : le panneau Etalonnage (sans clip -- l'hote R_DZ1 ne le monte qu'avec un clip V1 rendu)
    # et le contour du masque au lecteur (sans masque lisible ou sans effet actif : rien a dessiner) -- ni l'un ni
    # l'autre n'est un bouton ; dates ici parce qu'ils rendent null
    ("function DzmGradePanel(o){", "if(!c)return null;"),
    ("function DzmMaskBox(o){", "return null;"),
    # L5 (24/09/2026, tache 6) : les scopes et la lightbox rendent null SANS props (l'hote les monte toujours avec) --
    # garde en tete, avant les hooks ; ni l'un ni l'autre n'est un bouton
    ("function DzmScopes(o){", "if(!o)return null;"),
    ("function DzmLightbox(o){", "if(!o)return null;"),
]
for f, g in _NULLS:
    i = lay.find(f)
    check("R2_tolere_composant_null_" + f[len("function "):].split("(")[0],
          lay.count(f) == 1 and i >= 0 and g in lay[i:i + 400] and s.count(f) == 1)

# L7-B D-37 (24/09/2026, tache 1) : les deux entrees « Exporter EDL… » / « Exporter FCPXML… » de la
# rubrique Projet du menu ☰ -- TOUJOURS rendues (jamais conditionnelles, jamais `off` : le refus de la
# demo est DIT par une note), leur title est leur libelle (DzmCtxMenu pose title:it.lbl, temoin x1 dans
# la couche et dans le bundle) ; absentes du .bak
check("R1_menu_Projet_Exporter_EDL_FCPXML_x1_sans_off_title_par_it_lbl_bak_x0",
      s.count('{lbl:"Exporter EDL…",run:function(){dzExportTl("edl")}}') == 1
      and s.count('{lbl:"Exporter FCPXML…",run:function(){dzExportTl("fcpxml")}}') == 1
      and s.count('lbl:"Exporter EDL…",off:') == 0 and s.count('lbl:"Exporter FCPXML…",off:') == 0
      and lay.count('role:"menuitem",disabled:!!it.off,title:it.lbl') == 1 and s.count('role:"menuitem",disabled:!!it.off,title:it.lbl') == 1
      and bak.count("Exporter EDL") == 0 and bak.count("Exporter FCPXML") == 0,
      f"edl={s.count('Exporter EDL…')} fcpxml={s.count('Exporter FCPXML…')} bak={bak.count('Exporter EDL')}")

# L7-B D-42 (24/09/2026, tache 2) : « Découper aux changements de plan » du menu contextuel de clip -- TOUJOURS
# rendue (jamais conditionnelle), GRISEE (off) hors d'un clip video rendu, jamais cachee ; son title est son libelle
# (DzmCtxMenu pose title:it.lbl) ; le refus d'un clic sur une entree grisee n'existe pas (disabled), celui d'une
# analyse est DIT par une note (le geste) ; absente du .bak
check("R1_menu_clip_Decouper_aux_changements_de_plan_x1_grisee_hors_video_rendu_title_par_it_lbl_bak_x0",
      s.count('{lbl:"Découper aux changements de plan",off:!(c.src&&c.src.job_id)||trackKind(c.tr)!=="video",run:function(){dzSceneCut(id)}}') == 1
      and s.count("Découper aux changements de plan") == 1
      and lay.count('role:"menuitem",disabled:!!it.off,title:it.lbl') == 1
      and bak.count("Découper aux changements") == 0,
      f"n={s.count('Découper aux changements de plan')} bak={bak.count('Découper aux changements')}")

# L7-B D-40 (24/09/2026, tache 4) : la section « Cadrage » de l'inspecteur de plan (couche, DzmPlanProps) -- les
# quatre boutons (Centré / Suivre / Manuel par la fabrique rfBtn, « Analyser le mouvement ») sont TOUJOURS rendus,
# svm-minibtn avec title ; « sans effet » (source pas plus large que le cadre) les GRISE (disabled) et le DIT par le
# title (rfNon), jamais par un `?null:` ; « Centré » n'est jamais grisé. Le curseur du mode manuel est un <input
# range> (hors classes auditees) : grise et titre lui aussi. Temoin : la regle 1 compte la fabrique (UN
# r.jsx("button" pour trois boutons) ; absent du .bak.
_PPE = lay[lay.find("function DzmPlanProps(o){"):lay.find("function DzmDzRects(o){")]
_RFB = 'var rfBtn=function(m,lbl,title,dis,cb){return r.jsx("button",{className:"svm-minibtn dzm-rf-mode","data-on":rfMode===m?"1":"",'
check("R1_R2_cadrage_quatre_boutons_toujours_rendus_titres_grises_sans_effet_centre_grise_seulement_pendant_l_analyse_bak_x0",
      len(_PPE) > 3000 and _PPE.count(_RFB) == 1 and _PPE.count('"aria-pressed":rfMode===m,disabled:dis,title:title,onClick:cb') == 1
      and _PPE.count('rfBtn("centre","Centré",rfBusy?rfGel:"Cadrage centré') == 1 and _PPE.count("rfSans?rfNon:") == 4
      and _PPE.count('rfBtn("') == 3 and _PPE.count("?null:rfBtn(") == 0 and _PPE.count("&&rfBtn(") == 0
      and _PPE.count("pas plus large que le cadre du projet") == 1
      # « Centré » : dis = !1 ; Suivre : rfSans||rfBusy ; Manuel : rfSans ; Analyser : disabled:rfSans||rfBusy
      # revue 24/09 : « Centré » n est grise QUE pendant l analyse de ce plan (modes geles), titre « en cours »
      and _PPE.count('les points d\'une analyse restent gardés pour « Suivre »",rfBusy,') == 1
      and _PPE.count("rfBusy?rfGel:") == 5 and _PPE.count('disabled:rfSans||rfBusy,"aria-label"') == 1
      and _PPE.count('r.jsx("button",{className:"svm-minibtn",disabled:rfSans||rfBusy,') == 1
      and _PPE.count('children:"Analyser le mouvement"') == 1
      and _PPE.count('r.jsx("input",{type:"range",min:0,max:100,step:1,value:rfV,disabled:rfSans||rfBusy,') == 1
      and s.count('children:"Analyser le mouvement"') == 1 and bak.count("Analyser le mouvement") == 0,
      f"hote={len(_PPE)} rfBtn={_PPE.count('rfBtn(')} non={_PPE.count('rfSans?rfNon:')}")

# L5 (24/09/2026, tache 5) : le panneau « Étalonnage » (couche, DzmGradePanel) -- HUIT sites r.jsx("button" (les
# onglets M/R/G/B et les trois formes du masque par fabrique, « + Point », « À plat », les deux boutons d'accord,
# copier / coller le grade), TOUS titres ; AUCUN bouton conditionnel (on grise : disabled + title qui dit pourquoi) ;
# le « sans effet » du masque est DIT par son title. Temoin : le meme scanner voit les boutons de DzmPlanProps.
_GPE = lay[lay.find("function DzmGradePanel(o){"):lay.find("function DzmMaskBox(o){")]
_gp_n, _gp_manq = scan_titres(_GPE, [(0, len(_GPE))]) if len(_GPE) > 3000 else (0, ["zone introuvable"])
_gp_cond = scan_cond(_GPE, [(0, len(_GPE))]) if len(_GPE) > 3000 else ["zone introuvable"]
_pp_n, _pp_manq = scan_titres(_PPE, [(0, len(_PPE))])
check("R1_R2_etalonnage_huit_sites_de_bouton_tous_titres_aucun_conditionnel_masque_grise_et_dit_temoin_PlanProps",
      len(_GPE) > 3000 and _gp_n == 8 and _gp_manq == [] and _gp_cond == []
      and _GPE.count('"Le masque limite les effets du plan : ajoutez-en un"') == 1
      and _GPE.count("disabled:") >= 8 and _pp_n >= 3 and _pp_manq == []
      and s.count("function DzmGradePanel(o){") == 1 and bak.count("DzmGradePanel") == 0,
      f"sites={_gp_n} manquants={_gp_manq} conditionnels={_gp_cond} temoin={_pp_n}")

# L5 (24/09/2026, tache 6) : les scopes (DzmScopes) et la lightbox (DzmLightbox) -- TROIS sites de bouton, TOUTES classes
# confondues (la bascule « Scopes » est une svm-pchip et la tuile une dzm-lbtile, hors CLASSES auditees : le scanner
# ci-dessous ne filtre PAS par classe), chacun TITRE (props lues jusqu'a children:) ; AUCUN conditionnel (la bascule reste
# rendue eteinte, une tuile sans source reste rendue et dit « sans source »). Les entrees de menu (☰ Lightbox, Copier /
# Coller le grade) passent par DzmCtxMenu (title:it.lbl, pin EXPORT ci-dessus). Temoin : le meme scanner voit 8 sites
# dans le panneau Etalonnage.
_L5Z = lay[lay.find("function DzmScopes(o){"):lay.find("var DzTracks={")]
def _l5_sites(z):
    b = [m.start() for m in re.finditer(r'r\.jsxs?\("button",\{', z)]
    return b, [z[i:i + 60] for i in b if "title:" not in z[i:z.find("children:", i)]]
_l5_b, _l5_sans = _l5_sites(_L5Z)
_l5_tb, _l5_tsans = _l5_sites(_GPE)
_l5_cond = [m.group(0) for m in RX_COND.finditer(_L5Z)]
check("R1_R2_L5_scopes_et_lightbox_trois_sites_de_bouton_tous_titres_toutes_classes_aucun_conditionnel_temoin_Etalonnage",
      len(_L5Z) > 3000 and len(_l5_b) == 3 and _l5_sans == [] and _l5_cond == []
      and len(_l5_tb) == 8 and _l5_tsans == []
      and _L5Z.count('children:"Scopes"') == 1 and _L5Z.count('"sans source"') == 1
      and s.count("function DzmScopes(o){") == 1 and s.count("function DzmLightbox(o){") == 1 and bak.count("DzmScopes") == 0,
      f"sites={len(_l5_b)} sans_title={_l5_sans} conditionnels={_l5_cond} temoin={len(_l5_tb)}")

# L6 D-25 (25/09/2026, tache 5) : « Apprendre le bruit » (couche, DzmNoiseLearn, monte sous le rack de l'inspecteur audio)
# -- DEUX sites de bouton, TOUS titres, AUCUN conditionnel : « Apprendre le bruit » est UN bouton a deux etats (son
# `children` et son `title` changent pendant la mesure, jamais un ternaire de deux boutons), grise sans plage I/O / sur la
# demo / pendant la mesure ; « Oublier » grise sans plage apprise. Le composant vit HORS de la zone _L5Z (avant
# DzmScopes). Temoin : le meme scanner voit trois sites dans _L5Z ; absent du .bak.
# L6 (25/09/2026, tache 6) : la zone s'arrete desormais a DzmVoiceRec (pose APRES DzmNoiseLearn, avant DzmScopes) --
# sinon le bouton de la voix off serait compte ici comme un troisieme site ; il a sa propre ligne ci-dessous.
_L6N = lay[lay.find("function DzmNoiseLearn(o){"):lay.find("function DzmVoiceRec(")]
_l6_b, _l6_sans = _l5_sites(_L6N) if len(_L6N) > 1500 else ([], ["zone introuvable"])
_l6_cond = [m.group(0) for m in RX_COND.finditer(_L6N)]
_l6_n, _l6_manq = scan_titres(_L6N, [(0, len(_L6N))])
check("R1_R2_L6_apprendre_le_bruit_deux_sites_de_bouton_titres_grises_aucun_conditionnel_un_bouton_a_deux_etats_hors_zone_L5",
      len(_L6N) > 1500 and len(_l6_b) == 2 and _l6_sans == [] and _l6_cond == [] and _l6_n == 2 and _l6_manq == []
      and _L6N.count("disabled:dis,") == 1 and _L6N.count("disabled:!ap,") == 1
      and _L6N.count('children:busy?"Mesure…":"Apprendre le bruit"') == 1 and _L6N.count('children:"Oublier"') == 1
      and 0 < lay.find("function DzmNoiseLearn(o){") < lay.find("function DzmScopes(o){") and _L5Z.count("NoiseLearn") == 0
      and len(_l5_b) == 3 and s.count("function DzmNoiseLearn(o){") == 1 and bak.count("NoiseLearn") == 0,
      f"sites={len(_l6_b)} sans_title={_l6_sans} conditionnels={_l6_cond} audites={_l6_n} manquants={_l6_manq}")

# L6 D-26 (25/09/2026, tache 6) : l'enregistreur de voix off (couche, DzmVoiceRec, puce montee par l'hote apres
# « narration », section L6vo1) -- UN SEUL site de bouton (toutes classes : svm-themechip hors CLASSES auditees, le scanner
# _l5_sites ne filtre pas), TITRE, AUCUN conditionnel : c'est UN bouton a deux etats (repos « ● voix off » / prise
# « ■ m:ss », plus « micro… » et « envoi… » grises) dont `children` ET `title` changent -- jamais un ternaire de deux
# boutons ; grise sur la demo (disabled + title qui le dit). Le composant vit HORS de la zone _L5Z (avant DzmScopes).
# Temoins : le meme scanner voit deux sites dans _L6N et trois dans _L5Z ; absent du .bak.
_L6V = lay[lay.find("function DzmVoiceRec(o){"):lay.find("function DzmScopes(o){")]
_l6v_b, _l6v_sans = _l5_sites(_L6V) if len(_L6V) > 2500 else ([], ["zone introuvable"])
_l6v_cond = [m.group(0) for m in RX_COND.finditer(_L6V)]
check("R1_R2_L6_voix_off_un_seul_bouton_a_deux_etats_titre_dans_les_deux_etats_grise_sur_la_demo_hors_zone_L5",
      len(_L6V) > 2500 and len(_l6v_b) == 1 and _l6v_sans == [] and _l6v_cond == []
      and _L6V.count("disabled:dis,") == 1 and _L6V.count("var dis=demo||") == 1 and _L6V.count("title:tt,") == 1
      and _L6V.count('children:st==="prise"?"■ "+el:st==="micro"?"micro…":st==="envoi"?"envoi…":"● voix off"') == 1
      and _L6V.count('var tt=demo?"Projet de démonstration') == 1 and _L6V.count(':st==="prise"?"Arrêter la prise (') == 1
      and _L6V.count(':"Enregistrer une voix off au micro"') == 1
      and 0 < lay.find("function DzmNoiseLearn(o){") < lay.find("function DzmVoiceRec(o){") < lay.find("function DzmScopes(o){")
      and _L5Z.count("VoiceRec") == 0 and len(_l6_b) == 2 and len(_l5_b) == 3
      and s.count("function DzmVoiceRec(o){") == 1 and bak.count("VoiceRec") == 0,
      f"sites={len(_l6v_b)} sans_title={_l6v_sans} conditionnels={_l6v_cond} zone={len(_L6V)}")

# Retours L6 (26/09/2026, tache 4) : l'image etalonnee dans la fenetre principale (couche, DzmGradeLive, montee par l'hote
# dans le cadre du lecteur, section R6gl1) -- AUCUN bouton (toutes classes, le scanner _l5_sites ne filtre pas) : c'est
# une image et une pastille de TEXTE, sans pointeur ; tolere null ; posee APRES DzmMaskBox et AVANT DzmNoiseLearn, donc
# hors des zones _GPE, _L5Z, _L6N et _L6V (leurs comptes de boutons restent 8 / 3 / 2 / 1). Absente du .bak.
_R6Z = lay[lay.find("function DzmGradeLive(o){"):lay.find("/* L6 D-25 D-26 (25/09/2026, tâche 4)")]
_r6_b, _r6_sans = _l5_sites(_R6Z) if len(_R6Z) > 800 else (["zone introuvable"], [])
check("R1_R2_retours_L6_image_etalonnee_aucun_bouton_tolere_null_hors_des_zones_L5_L6_bak_x0",
      len(_R6Z) > 800 and _r6_b == [] and _R6Z.count("if(!o)return null;") == 1 and _R6Z.count("<button") == 0
      and 0 < lay.find("function DzmMaskBox(o){") < lay.find("function DzmGradeLive(o){") < lay.find("function DzmNoiseLearn(o){")
      and _GPE.count("GradeLive") == 0 and _L5Z.count("GradeLive") == 0 and _L6N.count("GradeLive") == 0 and _L6V.count("GradeLive") == 0
      and len(_l5_tb) == 8 and len(_l5_b) == 3 and len(_l6_b) == 2 and len(_l6v_b) == 1
      and s.count("function DzmGradeLive(o){") == 1 and bak.count("GradeLive") == 0,
      f"zone={len(_R6Z)} sites={_r6_b}")
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
