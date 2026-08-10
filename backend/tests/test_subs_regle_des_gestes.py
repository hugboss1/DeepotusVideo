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
    assert src.count("function subsConflictsFrom(") == 1
    assert src.count("function subsGoalConflicts(") == 1
    assert src.count("function subsTraits(") == 1
    tr = src.split("function subsTraits(", 1)[1].split("\nfunction ", 1)[0]
    for trait in ("fond:", "contour:", "karaoke:"):
        assert trait in tr, "trait observable manquant : %s" % trait
    gc = src.split("function subsConflictsFrom(", 1)[1].split("\nfunction ", 1)[0]
    # un conflit = les DEUX changent le meme trait, vers deux valeurs
    assert "a.tr[k]!==base[k]&&b.tr[k]!==base[k]&&a.tr[k]!==b.tr[k]" in gc
    assert "a.but===b.but" in gc, "deux gestes du meme objectif ne s'opposent pas"
    # et l'ecran le dit, entre les deux boutons
    sty = src.split("const SubsStyle=", 1)[1].split("\nconst ", 1)[0]
    assert "var arb=subsConflictsFrom(st,gestesVus)" in sty
    assert '"sub-arb"' in sty
    assert "en sens inverse" in sty
    # ancre EXPLICITE : depuis le tour 7 l'arbitrage contient une fonction
    # interne qui commence elle aussi par « return r.jsxs( ».
    body = sty.split('return r.jsxs("div",{className:"sub-style"', 1)[1]
    i_quick = body.index('className:"sub-quick"')
    i_arb = body.index("arbitrage,")
    i_ec = body.index("\n    ecarts,")
    # L'INVARIANT est « ENTRE », pas un sens de lecture : « Couper le fond »
    # vit dans le bloc « Reglages », « Fond opaque » dans la carte des ecarts,
    # et l'arbitrage se pose entre les deux — quel que soit celui des deux qui
    # passe en premier. Au tour 6, la carte des ecarts est montee TOUT EN HAUT
    # (sa preuve etait coupee par le bord du tiroir) : l'ordre s'est inverse,
    # la regle n'a pas bouge.
    assert min(i_quick, i_ec) < i_arb < max(i_quick, i_ec), \
        "l'arbitrage se pose ENTRE les deux gestes qui s'opposent"


# ---------------------------------------------------------------------------
# 7. TOUR 7 — un arbitrage ne designe que des boutons PRESENTS
# ---------------------------------------------------------------------------

def test_l_arbitrage_ne_travaille_que_sur_les_gestes_rendus():
    """« Le bloc dit de choisir entre "Couper le fond" et "Fond opaque", mais
    "Couper le fond" n'est pas l'un des deux boutons a l'ecran. »

    Le libelle etait deja lu a la source ; le defaut etait l'ENSEMBLE. La
    detection enumerait tous les gestes du MODELE (`subsGestes`), y compris
    ceux qu'aucun pixel ne montrait — un ecart replie, ou un bouton rendu
    300 px sous le bord du tiroir.

    Deux verrous ici, le troisieme (la visibilite en PIXELS) etant mesure par
    `scripts/qa/qa-subs-consistency.js`, garde F :
      a. l'ecran passe a la detection la liste des gestes qu'il rend VRAIMENT,
         construite depuis `ecVus` (les ecarts AFFICHES, pas `issues`) et les
         reglages eteints ;
      b. il ne recopie plus un seul libelle : il RE-REND les deux boutons.
    """
    src = _strip_comments(_layer())
    sty = src.split("const SubsStyle=", 1)[1].split("\nconst ", 1)[0]
    # a. la liste des gestes RENDUS, et rien d'autre
    assert "var gestesVus=[]" in sty
    assert "ecVus.forEach(" in sty, \
        "les gestes viennent des ecarts AFFICHES, pas de tous les ecarts"
    assert "if(!p.ok)return" in sty, "un plan bloque n'a pas de bouton"
    assert "var arb=subsConflictsFrom(st,gestesVus)" in sty
    assert "subsGoalConflicts(st)" not in sty, \
        "l'ecran ne doit plus arbitrer sur le modele entier"
    # b. le bloc PORTE ses boutons — via le helper commun, donc avec famille,
    #    objectif et apres — et ne cite plus aucun libelle en dur
    arb = sty.split('className:"sub-arb"', 1)[1].split('"arb")', 1)[0]
    assert "subsActBtn({" in arb, "l'arbitrage doit rendre les vrais boutons"
    assert "label:g.label" in arb
    assert "c.a.label" not in arb and "c.b.label" not in arb, \
        "un arbitrage ne recopie pas le libelle d'un bouton"
    # c. la place d'origine porte un RENVOI, qui ne nomme pas le bouton
    assert "var arbPris={}" in sty
    assert 'className:"sub-arbptr"' in sty
    ptr = sty.split('className:"sub-arbptr"', 1)[1].split("},", 1)[0]
    assert "children:" in ptr
    assert ".sub-arbptr{" in _css()
    # d. et le geste happe n'est pas rendu deux fois
    assert 'arbPris["ec:"+k+":"+j]' in sty
    assert 'arbPris["mort:outW"]' in sty


def test_les_seuils_sont_affiches_et_reglables():
    """« On affiche les COMPTES sans jamais afficher les REGLES. J'ai du
    retro-concevoir les seuils. »

    Une seule copie des quatre seuils, ecrite a l'ecran, reglable, et qui
    voyage jusqu'au moteur — sinon le panneau afficherait « 17 c/s » pendant
    que le backend continuerait de marquer a 20.
    """
    src = _strip_comments(_layer())
    # une seule definition, et les variables de lecture en descendent
    assert src.count("var SUBS_NORM_DEF=") == 1
    assert src.count("function subsNormApply(") == 1
    ap = src.split("function subsNormApply(", 1)[1].split("\nfunction ", 1)[0]
    for var in ("SUBS_CPS_MAX=", "SUBS_MIN_S=", "SUBS_MAX_S=", "SUBS_MIN_GAP="):
        assert var in ap, "seuil non derive de la norme : %s" % var
    # personne d'autre ne les reecrit
    ns = _strip_comments(_layer())
    for var in ("SUBS_CPS_MAX", "SUBS_MIN_S", "SUBS_MAX_S", "SUBS_MIN_GAP"):
        ecritures = re.findall(r"(?<![A-Za-z_])%s\s*=" % var, ns)
        assert len(ecritures) == 2, \
            "%s doit etre ecrit deux fois seulement (declaration + " \
            "subsNormApply), trouve %d" % (var, len(ecritures))
    # ils entrent dans la CLE du verdict : un seuil change relance le controle
    key = ns.split("function subsKeyOf(", 1)[1].split("\nfunction ", 1)[0]
    assert "subsNormSig()" in key
    # ... et ils PARTENT avec la requete au moteur
    chk = ns.split("function subsUseCheck(", 1)[1].split("\nfunction ", 1)[0]
    assert "normes:subsNormBody()" in chk
    body = ns.split("function subsNormBody(", 1)[1].split("\nfunction ", 1)[0]
    for k in ("cps_warn", "cps_error", "min_duration", "max_duration", "min_gap"):
        assert k in body, "parametre moteur manquant : %s" % k
    # l'ecran les ECRIT, avec l'ecart aussi compte EN IMAGES
    segs = ns.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    assert 'className:"sub-nrm"' in segs
    assert '"data-cps":String(nrm.cps)' in segs, \
        "le seuil doit etre lisible par le controle DOM, pas seulement par l'oeil"
    assert "subsNormImgs()" in segs, "l'ecart doit aussi se lire en images"
    assert 'children:"régler ▸"' in segs or "régler ▸" in segs
    # trois normes nommees, et « personnalise » n'est pas une norme
    assert ns.count("var SUBS_NORM_SETS=") == 1
    sets = ns.split("var SUBS_NORM_SETS=", 1)[1].split("];", 1)[0]
    for nom in ("ebu", "netflix", "reseaux"):
        assert '"%s"' % nom in sets
    assert ".sub-nrm{" in _css()


def test_l_acquittement_retire_du_calcul_jamais_du_constat():
    """« "Acquitter — sans parole" rend l'alarme verte alors que le plan sort
    toujours muet. »

    Le constat ne se replie pas avec l'atelier, il additionne les plans a
    traiter ET les plans acquittes, et le bloc ne redevient jamais neutre.
    """
    src = _strip_comments(_layer())
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    # le CONSTAT compte les deux
    assert "var covMuets=covBad.length+cov.ignores.length" in segs
    assert "sortiront muets" in segs
    assert "hors du calcul, muet" in segs, \
        "un plan acquitte reste un plan muet, et la phrase doit le dire"
    # ... et il vit HORS de l'atelier repliable
    assert "covOpen?covBad.map(planRow):null" in segs, \
        "les lignes de plan (l'atelier) se replient"
    # le CONSTAT est conditionne par le constat lui-meme, jamais par le pli
    assert 'covSay?r.jsx("div",{className:"sub-covsay"' in segs
    say = segs.split('className:"sub-covsay"', 1)[1].split('},"s")', 1)[0]
    assert "covOpen" not in say, "le constat ne se replie pas"
    assert 'cov.ignores.length?r.jsxs("div",{className:"sub-covign"' in segs
    ign = segs.split('className:"sub-covign"', 1)[1].split('},"ig")', 1)[0]
    assert "covOpen" not in ign, "la trace des acquittements ne se replie pas"
    assert "muet" in ign
    # le bloc garde une marque tant qu'un plan sortira muet
    assert '"data-ack":cov.ignores.length?"":void 0' in segs
    assert ".sub-cov[data-ack]{" in _css()
    # et la timeline dit la CONSEQUENCE, pas la propriete
    assert 'content:"muet (acquitté)"' in _css(), \
        "« sans parole » se lisait comme un reglage satisfait"


def test_le_diagnostic_se_resume_le_contenu_reste():
    """« Le panneau consacre la TOTALITE de ses ~470 px au resume d'audit et au
    bloc couverture : PAS UNE SEULE ligne de replique n'est visible. »

    Un ecran d'edition montre ce qu'on edite. La regle en pixels est mesuree
    par `qa-subs-consistency.js` (garde G) ; ici on verrouille la MECANIQUE qui
    la rend possible.
    """
    src = _strip_comments(_layer())
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    # l'atelier est replie par defaut (l'etat part de faux)
    assert "var s7=x.useState(!1),covAll=s7[0]" in src
    assert "var covOpen=covAll" in segs
    # la legende des familles fait partie de l'atelier, pas du constat
    assert "covBad.length&&covOpen?" in segs
    # le bouton dit ce qu'il ouvre, et porte le nombre de plans qu'il traite
    assert 'children:covOpen?"replier les gestes ▾"' in segs
    assert '"traiter "+subsPl(covBad.length,"plan")' in segs
    # ordre dans l'onglet : le diagnostic, puis les outils, puis LA LISTE
    body = segs.split("return r.jsxs(", 1)[-1]
    i_cov = body.index("\n    couverture,")
    i_nrm = body.index("\n    normes,")
    i_rows = body.index("shown.length")
    assert i_cov < i_nrm < i_rows, \
        "la regle se lit juste au-dessus des pastilles qu'elle produit"


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
    # ecrire ici : ce qu'il cree ne couvre RIEN tant qu'il est vide, et il
    # l'annonce DANS LA MEME CASE que les autres (« 20 % -> 20 % »), au meme
    # format — « vide . 0 $ » se lisait comme un prix et ne disait rien de
    # l'apres d'un geste offert sous « ils sortiront muets ».
    assert "Une réplique SANS TEXTE ne couvre rien" in row
    assert "cost:cov.pct+\" % → \"+cov.pct+\" %\"" in row
    # acquitter : le chiffre qu'il deplace, calcule
    assert "pctAp=subsPctOf(cvt,att)" in row
    assert "cost:cov.pct+\" % → \"+pctAp+\" %\"" in row


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


# ---------------------------------------------------------------------------
# 6. TOUR 6 — un nombre qu'on ne peut pas refaire se lit comme un nombre faux
# ---------------------------------------------------------------------------

def test_les_pourcentages_se_calculent_sur_les_valeurs_affichees():
    """« "21 % -> 30 %" n'est reconstructible par aucune autre surface. »

    Le chiffre etait JUSTE (acquitter retire le plan du total : 14,1 / (68,8 -
    21,6) = 30 %) mais rien a l'ecran ne disait laquelle des deux conventions
    s'applique, et le pourcentage etait calcule sur les secondes EXACTES puis
    affiche a cote de secondes ARRONDIES — 14,1 / 68,8 rendait 20 % au lecteur
    et 21 % au panneau.

    Deux regles, verrouillees ici :
      a. on arrondit AU DIXIEME d'abord — la precision que l'ecran montre —
         et tout pourcentage se calcule SUR CES VALEURS-LA ;
      b. les sommes sont des sommes de valeurs AFFICHEES.
    """
    src = _strip_comments(_layer())
    assert src.count("function subsSec(") == 1
    assert src.count("function subsPctOf(") == 1
    pct = src.split("function subsPctOf(", 1)[1].split("\nfunction ", 1)[0]
    assert "subsSec(couvert)" in pct and "subsSec(attendu)" in pct, \
        "le pourcentage doit se calculer sur les secondes ARRONDIES"
    cov = src.split("function subsCoverage(", 1)[1].split("\nfunction ", 1)[0]
    assert "p.couvert=subsSec(" in cov
    assert "p.pct=subsPctOf(p.couvert,p.dur)" in cov
    assert "var attendu=subsSec(retenus.reduce(" in cov, \
        "le total est la somme des durees AFFICHEES"
    assert "var couvert=subsSec(retenus.reduce(" in cov
    assert "var pct=subsPctOf(couvert,attendu)" in cov
    # la duree d'un plan est arrondie UNE fois, a la source
    pl = src.split("function subsPlans(", 1)[1].split("\nfunction ", 1)[0]
    assert "dur:subsSec(Math.max(0,b-a))" in pl
    # ... et plus aucune surface ne re-arrondit un pourcentage deja entier
    assert "Math.round(cov.pct)" not in src
    assert "Math.round(vd.cov.pct)" not in src


def test_la_convention_de_l_acquittement_est_ecrite_ou_le_nombre_apparait():
    """« Ecris la convention la ou le nombre apparait, et fais que le calcul
    soit reconstructible depuis ce que l'ecran montre deja. »"""
    src = _strip_comments(_layer())
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    row = segs.split("function planRow(", 1)[1].split("\n  function ", 1)[0]
    # la convention, en toutes lettres, avec l'operation
    assert "RETIRE le plan des deux termes" in row
    assert "jamais ajouté au couvert" in row
    assert '" − "+subsFr(p.couvert,1)+") ÷ ("' in row
    assert '" − "+subsFr(p.dur,1)+") = "+pctAp' in row
    # ... et elle est A L'ECRAN, pas seulement dans une infobulle
    assert 'className:"sub-planmath"' in row
    assert ".sub-planmath{" in _css()
    # les DEUX termes de la division vivent aussi sur la ligne du plan
    assert 'subsFr(p.couvert,1)+" / "+subsFr(p.dur,1)' in row
    # et l'en-tete du bloc porte la division, pas seulement son resultat
    head = segs.split('children:"Couverture du montage"', 1)[1][:1400]
    assert 'subsFr(cov.couvert,1)+" ÷ "+subsFr(cov.attendu,1)+" s = "' in head
    assert "RETIRÉS du total" in segs, \
        "la trace des acquittements doit nommer la meme convention"


def test_une_replique_vide_ne_couvre_rien():
    """« Decide et dis-le. » Une replique sans texte ne couvre rien : le
    verdict la saute (comme une masquee), et le geste qui en pose une annonce
    que le pourcentage NE BOUGE PAS."""
    src = _strip_comments(_layer())
    # 1. le calcul : l'union des repliques saute le vide ET le masque
    u = src.split("function subsUnion(", 1)[1].split("\nfunction ", 1)[0]
    assert 'if(s.hidden||!String(s.text||"").trim())return' in u
    # 2. le geste le DIT, dans la case ou les autres disent leur apres
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    row = segs.split("function planRow(", 1)[1].split("\n  function ", 1)[0]
    assert 'label:"Écrire ici"' in row
    assert 'cost:cov.pct+" % → "+cov.pct+" %"' in row, \
        "le geste doit afficher qu'il ne deplace RIEN"
    assert "vide · 0 $" not in row, "un prix n'est pas un apres"
    assert "une réplique VIDE ne couvre rien" in row
    # 3. et le compte des repliques ne se confond pas avec la couverture :
    #    une replique vide EXISTE dans la liste, elle ne couvre simplement pas
    vd = src.split("function subsVerdict(", 1)[1].split("\nfunction ", 1)[0]
    assert "repliques:list.length" in vd


def test_la_langue_est_detectee_sur_le_contenu_et_jamais_affirmee_contre_lui():
    """« Le bouton dit "francais . ElevenLabs Scribe v1" au-dessus de treize
    sous-titres manifestement anglais. » On detecte sur le texte present, on
    propose, et si l'on doute on le DIT au lieu de choisir en silence."""
    src = _strip_comments(_layer())
    assert src.count("function subsGuessLang(") == 1
    assert src.count("function subsDetectLang(") == 1
    g = src.split("function subsGuessLang(", 1)[1].split("\nfunction ", 1)[0]
    # deux seuils ECRITS, pas un flair
    assert "SUBS_LG_MIN" in g and "SUBS_LG_LEAD" in g
    assert "out.sur=score[p]>=SUBS_LG_MIN" in g
    # la source du jugement est nommee (les repliques, sinon la narration)
    ls = src.split("function subsLangSource(", 1)[1].split("\nfunction ", 1)[0]
    assert "les répliques de la piste" in ls
    assert 'c.tr==="a1"||c.tr==="a3"' in ls
    drw = src.split("const SubsDrawer=", 1)[1]
    assert "var det=x.useMemo(function(){" in drw
    assert "subsDetectLang(segs,props.srcClips)" in drw
    # on n'ecrase JAMAIS un choix explicite
    assert "if(langPris||!det.sur||det.code===lang)return" in drw
    assert 'localStorage.getItem("dz_subs_lang_pris")' in drw
    assert 'localStorage.setItem("dz_subs_lang_pris","1")' in drw
    # les quatre etats sont dits a l'ecran, avec le compte des mots reconnus
    assert 'className:"sub-lgnote"' in drw
    assert '"data-etat":etat' in drw
    for etat in ('"vide"', '"flou"', '"ok"', '"contre"'):
        assert etat in drw, "etat de detection manquant : %s" % etat
    assert 'det.hits+" mots reconnus sur "+det.total' in drw
    assert "Langue indécise" in drw, "le doute se DIT"
    assert 'children:"passer en "+subsLangLab(det.code)' in drw
    assert ".sub-lgnote{" in _css()


def test_la_piece_a_conviction_tient_dans_le_premier_ecran():
    """« La carte "LES ECARTS" est tronquee par le bord du panneau. » Ce qui
    justifie un avertissement ne peut pas etre hors champ : la carte passe en
    tete de l'onglet, et elle ne montre qu'un ecart a la fois."""
    src = _strip_comments(_layer())
    sty = src.split("const SubsStyle=", 1)[1].split("\nconst ", 1)[0]
    body = sty.split("return r.jsxs(", 1)[1]
    i_ec = body.index("\n    ecarts,")
    i_quick = body.index('className:"sub-quick"')
    i_grid = body.index('className:"sub-pgrid"')
    assert i_ec < i_quick < i_grid, \
        "la preuve passe devant les reglages, qui passent devant la galerie"
    # un seul ecart deplie par defaut, les autres a un clic, avec leur nombre
    assert "var ecVus=ecAll?issues:issues.slice(0,1)" in sty
    assert 'subsPl(issues.length-1,"autre écart","autres écarts")' in sty
    # et dans l'autre onglet, la mesure reste dans le premier ecran de la
    # piste vide : l'invitation d'abord, compacte, la mesure juste dessous
    segs = src.split("const SubsSegments=", 1)[1].split("\nconst ", 1)[0]
    vide = segs.split("if(empty)", 1)[1][:1200]
    assert vide.index('className:"sub-empty"') < vide.index("couverture]")
    assert ".sub-empty{padding:13px" in _css(), \
        "le bloc d'invitation a ete resserre pour que les deux tiennent"
