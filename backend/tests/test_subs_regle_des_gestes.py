# -*- coding: utf-8 -*-
"""LA REGLE DES GESTES — un bouton fait ce que son avertissement laisse croire.

Quatre tours de suite, un critique a retrouve le MEME defaut sous un visage
neuf, chaque fois dans le panneau de sous-titres :

  tour 2  « Etirer » fabriquait le chevauchement denonce juste en dessous ;
  tour 3  « Passer le fond en opaque » fabriquait la condition de l'ecart
          voisin ;
  tour 4  « Sans parole » eteignait l'alerte « 3 plans sortiront muets » SANS
          RIEN CHANGER au fichier livre, et rien a l'ecran ne disait que
          c'etait un acquittement ; et « Couper le fond » / « Fond opaque »,
          a 60 px l'un de l'autre, poussaient en sens inverse.

Ce n'etaient pas trois rattrapages qui manquaient : c'etait UNE regle. Ce
fichier la verrouille sur les SOURCES (le bundle de prod est un fichier
minifie patche : la source du patch fait foi), en trois articles.

  1. DEUX FAMILLES, JAMAIS CONFONDUES. Un geste attache a un avertissement
     change le fichier livre (`fam:"fix"`), ou il dit explicitement qu'il ne
     fait que taire l'alerte (`fam:"ack"`). Les deux se distinguent PAR LA
     FORME — bordure, rayon, fond — pas par le seul libelle.
  2. DEUX GESTES VISIBLES EN MEME TEMPS NE POUSSENT PAS EN SENS INVERSE sans
     que chacun nomme son OBJECTIF.
  3. TOUT BOUTON DE REMEDE ANNONCE SON APRES AVANT LE CLIC : ce qu'il eteint,
     ce qu'il cree, ce qui reste.

Et la convention maison, tenue ici comme ailleurs : un bouton qui DEPENSE
annonce sa langue, son moteur, son prix et sa duree — y compris les quatre
boutons « transcrire ce plan ».

Ce que ces tests ne peuvent pas voir (l'ecran reel : formes calculees,
egalite des chiffres, densite) est mesure par
`scripts/qa/qa-subs-consistency.js`.

Lance seul (un processus par fichier, cf. scripts/run-tests.ps1) :
    python -m pytest backend/tests/test_subs_regle_des_gestes.py -q
"""
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]
LAYER = REPO / "frontend" / "patches" / "subs.js"
CSS = REPO / "frontend" / "dist" / "shared" / "subs.css"


def _layer() -> str:
    return LAYER.read_text(encoding="utf-8")


def _css() -> str:
    return CSS.read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


def _calls(src: str, fn: str):
    """Tous les appels `fn({...})`, rendus par equilibrage d'accolades."""
    out, needle = [], fn + "({"
    i = src.find(needle)
    while i >= 0:
        j, depth = i + len(fn) + 1, 0
        while j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(src[i:j + 1])
        i = src.find(needle, j)
    return out


# ---------------------------------------------------------------------------
# 1. deux familles, jamais confondues
# ---------------------------------------------------------------------------

def test_les_deux_familles_sont_declarees_une_fois():
    src = _strip_comments(_layer())
    assert src.count("var SUBS_FAM=") == 1
    fam = src.split("var SUBS_FAM=", 1)[1].split(";", 1)[0]
    assert "fix:" in fam and "ack:" in fam
    # chaque famille porte un GLYPHE (la forme) et une phrase qui la DIT
    assert fam.count("glyph:") == 2
    assert "ÉCRIT dans le fichier livré" in fam
    assert "n'écrit RIEN dans le fichier livré" in fam


def test_tout_bouton_de_remede_passe_par_le_helper():
    """Un seul point de fabrication : impossible d'ajouter un bouton de remede
    sans sa famille et sans son apres. Les anciens boutons crus
    (`sub-minibtn sub-fix`, `sub-fixalt`) ne doivent plus exister."""
    src = _strip_comments(_layer())
    assert src.count("function subsActBtn(") == 1
    assert "sub-minibtn sub-fix" not in src
    assert "sub-fixalt" not in src
    # le helper ecrit la famille dans le DOM et le glyphe dans le bouton
    body = src.split("function subsActBtn(", 1)[1].split("\nfunction ", 1)[0]
    assert '"data-fam":fam' in body
    assert "SUBS_FAM[fam].glyph" in body
    assert 'className:"sub-act"' in body
    # un acquittement le DIT dans son libelle, sans qu'on ait a le taper
    assert '"Acquitter — "' in body


def test_les_deux_familles_se_distinguent_par_la_forme():
    """« Par la forme, pas par le libelle seul » : trois proprietes
    differentes au moins, pour qu'on tranche sans lire."""
    css = _css()
    fix = css.split('.sub-act[data-fam="fix"]{', 1)[1].split("}", 1)[0]
    ack = css.split('.sub-act[data-fam="ack"]{', 1)[1].split("}", 1)[0]
    assert "border-radius:5px" in fix and "border-radius:999px" in ack, \
        "le rayon doit separer les deux familles"
    assert "border-style:dashed" in ack, "l'acquittement est en pointille"
    assert "background:transparent" in ack and "background:color-mix" in fix, \
        "le fond doit separer les deux familles"


def test_l_acquittement_laisse_une_trace_visible_et_revocable():
    """« Pas un silence. » Il se compte dans le verdict, il se nomme dans la
    ligne des comptes, et il se revoque d'un bouton."""
    src = _layer()
    ns = _strip_comments(src)
    # compte dans le verdict, et forme vide identique
    vd = ns.split("function subsVerdict(", 1)[1].split("\nfunction ", 1)[0]
    assert "acquittes:cov.ignores.length" in vd
    assert "acquittes:0" in ns.split("function subsVerdictNil(", 1)[1][:400]
    # domicile du nombre : la ligne des comptes, avec son mot
    drw = ns.split("const SubsDrawer=", 1)[1]
    tally = drw.split('className:"sub-tally"', 1)[1].split('className:"sub-tabs"', 1)[0]
    assert '"data-k":"acquittes"' in tally
    assert '"data-fam":"ack"' in tally, "meme forme que le geste qui l'a produit"
    assert "plans acquittés" in tally
    # le geste lui-meme : famille ack, et la revocation
    segs = ns.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    assert 'fam:"ack",label:"sans parole"' in segs
    assert "révoquer" in segs
    # ... et il dit ce qu'il ne fait PAS
    assert "N'écrit RIEN dans la vidéo" in segs


# ---------------------------------------------------------------------------
# 2. deux gestes opposes nomment leur objectif
# ---------------------------------------------------------------------------

def test_chaque_correctif_de_style_nomme_son_objectif():
    """Sans `but`, deux gestes contraires ne peuvent pas s'expliquer."""
    src = _strip_comments(_layer())
    # les correctifs offerts par les regles de style et par la neutralisation
    for bloc in ("function subsSafeIssues(", "function subsStyleRules(",
                 "function subsNeutralized("):
        body = src.split(bloc, 1)[1].split("\nfunction ", 1)[0]
        n_lab = body.count("label:")
        n_but = body.count("but:")
        assert n_lab == n_but, \
            "%s : %d libelles pour %d objectifs" % (bloc, n_lab, n_but)
        assert n_lab > 0


def test_les_gestes_opposes_sont_detectes_et_nommes():
    """La detection ne compare pas les CLES ecrites (« Couper le fond » ecrit
    bgOn, « Fond opaque » ecrit bgOpacity) mais ce que le style DEVIENT."""
    src = _strip_comments(_layer())
    assert src.count("function subsGoalConflicts(") == 1
    assert src.count("function subsTraits(") == 1
    tr = src.split("function subsTraits(", 1)[1].split("\nfunction ", 1)[0]
    for trait in ("fond:", "contour:", "karaoke:"):
        assert trait in tr, "trait observable manquant : %s" % trait
    gc = src.split("function subsGoalConflicts(", 1)[1].split("\nfunction ", 1)[0]
    # un conflit = les DEUX changent le meme trait, vers deux valeurs
    assert "a.tr[k]!==base[k]&&b.tr[k]!==base[k]&&a.tr[k]!==b.tr[k]" in gc
    assert "a.but===b.but" in gc, "deux gestes du meme objectif ne s'opposent pas"
    # et l'ecran le dit, entre les deux boutons
    sty = src.split("const SubsStyle=", 1)[1].split("\nconst ", 1)[0]
    assert "var arb=subsGoalConflicts(st)" in sty
    assert '"sub-arb"' in sty
    assert "en sens inverse" in sty
    body = sty.split("return r.jsxs(", 1)[1]
    i_quick = body.index('className:"sub-quick"')
    i_arb = body.index("arbitrage,")
    i_ec = body.index("\n    ecarts,")
    assert i_quick < i_arb < i_ec, \
        "l'arbitrage se pose ENTRE les deux gestes qui s'opposent"


# ---------------------------------------------------------------------------
# 3. aucun bouton de remede sans son plan
# ---------------------------------------------------------------------------

def test_aucun_bouton_de_remede_sans_son_apres():
    """LE test que le tour 5 devait ecrire : un bouton de remede existe avec
    son plan, ou il n'existe pas."""
    src = _strip_comments(_layer())
    appels = _calls(src, "subsActBtn")
    assert len(appels) >= 6, "trop peu de gestes trouves : %d" % len(appels)
    for a in appels:
        assert "fam:" in a, "geste sans famille : %s" % a[:90]
        assert "apres:" in a, "geste sans APRES : %s" % a[:90]
        assert "onClick:" in a, "geste sans action : %s" % a[:90]
    # les deux familles sont effectivement utilisees
    assert any('fam:"ack"' in a for a in appels)
    assert any('fam:"fix"' in a for a in appels)


def test_un_correctif_de_temps_simule_son_apres():
    """Le mecanisme existait pour le style ; il couvre desormais le TEMPS.
    On applique le plan a une copie de la piste et on recompte : un chiffre,
    pas une promesse."""
    src = _strip_comments(_layer())
    assert src.count("function subsPlanAfter(") == 1
    body = src.split("function subsPlanAfter(", 1)[1].split("\nfunction ", 1)[0]
    assert "subsApplyPlan(list,plan)" in body, "il APPLIQUE le plan pour compter"
    assert "Éteint :" in body and "CRÉE :" in body and "Reste :" in body
    assert "plan.eteint=eteint" in body
    assert "plan.apres=bits.join" in body
    # et le verdict l'appelle pour CHAQUE plan affiche, y compris les alternatives
    vd = src.split("function subsVerdict(", 1)[1].split("\nfunction ", 1)[0]
    assert "subsPlanAfter(list,w.plan,st,dur)" in vd
    assert "subsPlanAfter(list,w.plan.alt,st,dur)" in vd
    # le correctif de STYLE porte le meme champ, pour que l'ecran ne fasse
    # qu'une seule lecture
    sp = src.split("function subsStylePlan(", 1)[1].split("\nfunction ", 1)[0]
    assert "plan.apres=plan.effect" in sp


def test_les_gestes_de_couverture_annoncent_aussi_leur_apres():
    """« Y compris ceux du temps et ceux de la couverture. »"""
    src = _strip_comments(_layer())
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    row = segs.split("function planRow(", 1)[1].split("\n  function ", 1)[0]
    assert row.count("subsActBtn({") == 3, "trois gestes, pas un de plus"
    # transcrire : ce qu'il ecrit et ce qu'il ne touche pas
    assert "les \"+\n            \"autres plans ne bougent pas" in row \
        or "autres plans ne bougent pas" in row
    # ecrire ici : ce qu'il cree ne couvre RIEN tant qu'il est vide
    assert "elle ne couvre rien" in row
    # acquitter : le chiffre qu'il deplace, calcule
    assert "pctAp=att>0" in row
    assert "cost:Math.round(cov.pct)+\" % → \"+pctAp+\" %\"" in row


# ---------------------------------------------------------------------------
# 4. la convention du cout, tenue ici
# ---------------------------------------------------------------------------

def test_chaque_bouton_qui_depense_annonce_langue_moteur_prix_duree():
    src = _strip_comments(_layer())
    assert src.count("function subsCostOf(") == 1
    body = src.split("function subsCostOf(", 1)[1].split("\nfunction ", 1)[0]
    assert "subsLangLab(lang)" in body, "la langue"
    assert "subsMoteurNom(court)" in body, "le moteur, nomme"
    assert "subsUsd(usd)" in body, "le prix"
    assert "subsEta(eta)" in body, "la duree"
    # l'estimation vient du moteur, pas d'un chiffre code en dur
    assert "/api/subtitles/estimate?duration_s=60" in src
    assert "/api/subtitles/estimate?duration_s=0" in src
    # ... et le chemin GRATUIT est dit la ou il est vrai
    assert "calage local · gratuit" in body
    assert "Aucun appel " in body
    # les CINQ boutons qui declenchent une depense portent la pastille
    drw = src.split("const SubsDrawer=", 1)[1]
    assert "trAll=subsCostOf(trFree" in drw
    assert "cost:trJob&&trJob.busy?\"en cours…\":trAll.txt" in drw
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    assert "ct=subsCostOf(!!p.texte,p.dur,props.lang||\"fr\",!0)" in segs
    assert "cost:ct.txt" in segs
    # la langue est CHOISIE et voyage jusqu'au moteur
    assert "var SUBS_LANGS=" in src
    assert "lang:lang,cps:" in drw, "la langue choisie part avec la requete"
    assert 'localStorage.setItem("dz_subs_lang"' in drw


def test_le_bouton_annonce_le_chemin_reel_pas_le_plus_flatteur():
    """Le backend prend le calage GRATUIT des qu'un clip de voix porte son
    texte (`use_align`). Le bouton doit annoncer CE chemin."""
    src = _strip_comments(_layer())
    drw = src.split("const SubsDrawer=", 1)[1]
    assert 'c.tr==="a1"||c.tr==="a3"' in drw
    assert 'trAll.free?"Caler la narration écrite":"Transcrire l\'audio"' in drw


# ---------------------------------------------------------------------------
# 5. une ligne repliee doit pouvoir se juger
# ---------------------------------------------------------------------------

def test_la_ligne_repliee_porte_debut_duree_et_mesure():
    """« Les lignes ne montrent qu'un temps de debut. » Elle porte desormais
    le debut, la DUREE, et la MESURE qui a motive sa pastille."""
    src = _strip_comments(_layer())
    # la mesure voyage avec l'avertissement
    w = src.split("function subsWarnings(", 1)[1].split("\nfunction ", 1)[0]
    assert "mes:String(mes||\"\")" in w
    for mes in ('"−"+subsFrMs(-gap)', 'Math.round(cps)+" c/s"',
                'ln.length+" lignes"'):
        assert mes in w, "mesure manquante : %s" % mes
    # ... et elle survit au verdict du MOTEUR (qui ne la renvoie pas)
    vd = src.split("function subsVerdict(", 1)[1].split("\nfunction ", 1)[0]
    assert "mesBy[w.id" in vd and "mes:String(w.mes||mesBy[" in vd
    # la ligne repliee l'affiche, a cote de sa pastille
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    head = segs.split('className:"sub-r1"', 1)[1].split('"r1")', 1)[0]
    assert '"sub-rdur"' in head, "la duree"
    assert '"sub-rmes"' in head, "la mesure"
    assert '"sub-rbadge"' in head
    # la mesure est celle du defaut le PLUS GRAVE, pas du premier venu
    assert "SUBS_SEVN[pire.sev]" in segs
    css = _css()
    assert ".sub-rdur{" in css and ".sub-rmes{" in css
    assert '.sub-rmes[data-sev="err"]' in css
