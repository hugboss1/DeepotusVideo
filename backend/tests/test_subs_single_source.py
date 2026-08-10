# -*- coding: utf-8 -*-
"""Un seul endroit decide de la severite et des comptes des sous-titres.

Le defaut ferme ici avait quatre visages dans la MEME image :

  * la piste S1 peignait 9 pastilles « critiques » pendant que la liste juste
    a cote en peignait 8 en ambre et une seule en rouge ;
  * le badge d'onglet et la chip de la barre d'outils affichaient tous les deux
    « 9 » sans compter la meme chose (des avertissements d'un cote, des
    repliques de l'autre), alors que 11 lignes portaient une marque ;
  * l'onglet actif annoncait des defauts que rien a l'ecran ne designait ;
  * l'apercu tracait une zone sure a 10 % et posait le texte d'usine a 9 %.

Cause unique : la severite et les comptes etaient calcules a QUATRE endroits.
La correction est structurelle — une seule fonction, `subsVerdict`, decide ;
toutes les surfaces lisent son resultat. Ce fichier verrouille cette structure
sur les SOURCES (le bundle de prod est un fichier minifie patche : c'est la
source du patch qui fait foi), pour qu'aucune passe future ne rouvre un second
lieu de calcul sans le voir.

L'egalite VUE A L'ECRAN, replique par replique (timeline / liste / badges /
chip / inspecteur), est mesuree dans le DOM reel par
`scripts/qa/subs-consistency.js`.

Lance seul (un processus par fichier, cf. scripts/run-tests.ps1) :
    python -m pytest backend/tests/test_subs_single_source.py -q
"""
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]
LAYER = REPO / "frontend" / "patches" / "subs.js"
PATCHER = REPO / "scripts" / "patch_bundle_subs.py"
CSS = REPO / "frontend" / "dist" / "shared" / "subs.css"


def _layer() -> str:
    return LAYER.read_text(encoding="utf-8")


def _patcher() -> str:
    return PATCHER.read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    """Retire les commentaires /* */ et // — un exemple cite dans un commentaire
    ne doit pas compter comme un second lieu de calcul."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


# ---------------------------------------------------------------------------
# 1. une seule fonction decide
# ---------------------------------------------------------------------------

def test_une_seule_definition_du_verdict():
    src = _strip_comments(_layer())
    assert src.count("function subsVerdict(") == 1
    assert src.count("function subsWarnings(") == 1


def test_le_calcul_de_severite_ne_vit_que_dans_le_verdict():
    """`subsWarnings` (le calcul brut) n'est appele QUE par `subsVerdict`.

    Toute autre surface qui l'appellerait se fabriquerait un second verdict :
    c'est exactement ce que faisaient la timeline, le badge d'onglet et
    l'inspecteur.
    """
    src = _strip_comments(_layer())
    # appels = occurrences suivies de '(' moins la definition et l'export
    calls = re.findall(r"subsWarnings\(", src)
    assert len(calls) == 2, f"appels a subsWarnings : {len(calls)} (definition + verdict attendus)"
    body = src.split("function subsVerdict(", 1)[1]
    assert "subsWarnings(list,st,dur)" in body[:2000], \
        "subsVerdict doit etre le seul appelant de subsWarnings"


def test_les_surfaces_du_tiroir_lisent_le_verdict():
    src = _strip_comments(_layer())
    # la liste des repliques
    segs = src.split("const SubsSegments=", 1)[1].split("const ", 1)[0]
    assert "props.verdict" in segs
    assert "subsWarnings(" not in segs
    assert "subsSegState(vd," in segs
    # les comptes affiches ne sont pas recalcules : ils sortent de vd.counts
    assert "vd.counts.masquees" in segs
    assert "vd.counts.signalees" in segs
    assert "vd.counts.bloquantes" in segs
    # l'onglet Style
    sty = src.split("const SubsStyle=", 1)[1].split("const ", 1)[0]
    assert "props.verdict" in sty
    assert "subsStyleIssues(" not in sty
    # le tiroir : un seul appel, descendu dans les deux onglets
    drw = src.split("const SubsDrawer=", 1)[1]
    assert drw.count("subsUseVerdict(") == 1
    assert "verdict:vd" in drw
    assert "subsWarnings(" not in drw


def test_les_surfaces_de_l_hote_lisent_le_verdict():
    """Timeline, chip de la barre d'outils et inspecteur passent par DzSubs."""
    src = _patcher()
    assert "d.verdict(subsSegsOf(clips)" in src, "l'hote doit appeler DzSubs.verdict"
    assert src.count("function subsVd()") == 1
    # plus aucun calcul local cote hote
    assert "d.warnings(" not in src, "l'hote ne doit plus calculer ses avertissements"
    assert "subsWarnMap" not in src
    # la pastille de la timeline porte la SEVERITE decidee, pas un booleen
    assert 'subsSev(c.id).sev' in src
    # la chip lit les comptes du verdict
    assert "subsVd().counts" in src
    # l'inspecteur lit les memes avertissements
    assert "subsSev(sel.id).warns" in src


def test_le_verdict_se_rafraichit_quand_le_moteur_repond():
    """Sans abonnement, la timeline garderait le calcul local pendant que le
    tiroir affiche celui du moteur : la divergence par le retard."""
    assert "d.onVerdict(" in _patcher()
    src = _strip_comments(_layer())
    assert "onVerdict:subsChkSub" in src
    assert "function subsUseVerdict(" in src


# ---------------------------------------------------------------------------
# 2. le resultat du moteur ne s'applique qu'a la piste qu'il a mesuree
# ---------------------------------------------------------------------------

def test_le_controle_moteur_est_cle_sur_la_piste():
    """Un resultat serveur calcule pour une version precedente de la piste ne
    doit jamais teinter le verdict de la version courante — c'est ainsi que la
    liste affichait un verdict et la timeline un autre."""
    src = _strip_comments(_layer())
    assert "function subsKeyOf(" in src
    assert "SUBS_CHK.key===key" in src, \
        "le verdict ne doit lire le moteur que si la cle correspond"
    assert "subsChkPut(key,d)" in src


# ---------------------------------------------------------------------------
# 3. chaque nombre affiche dit ce qu'il compte
# ---------------------------------------------------------------------------

def test_les_comptes_sont_nommes_et_distincts():
    src = _strip_comments(_layer())
    body = src.split("function subsVerdict(", 1)[1]
    for k in ("repliques", "masquees", "signalees", "bloquantes", "defauts",
              "ecarts"):
        assert k + ":" in body, f"compte manquant dans le verdict : {k}"
    # bloquantes est un SOUS-ENSEMBLE de signalees : compte de repliques dans
    # les deux cas, jamais un compte d'avertissements
    assert "if(e.n)nSig++" in body
    assert "if(e.nErr)nBlk++" in body
    # la ligne qui ecrit l'unite a cote de chaque nombre existe
    assert '"sub-tally"' in src
    for mot in ("répliques", "signalées", "bloquantes", "défauts"):
        assert mot in src


def test_un_badge_ne_peut_pas_annoncer_ce_que_rien_ne_montre():
    """Filtre ou recherche peuvent cacher des repliques signalees : l'ecart
    entre le badge (toute la piste) et la liste (filtree) doit etre dit."""
    src = _layer()
    assert "sub-hidbad" in src
    assert "hiddenBad" in src
    assert "tout afficher" in src


# ---------------------------------------------------------------------------
# 4. la zone sure et la marge d'usine disent la meme chose
# ---------------------------------------------------------------------------

def _const(src: str, name: str) -> str:
    m = re.search(r"var %s=([^;]+);" % re.escape(name), src)
    assert m, f"constante introuvable : {name}"
    return m.group(1).strip()


def test_le_defaut_d_usine_est_dans_la_zone_sure():
    """L'apercu tracait « zone sure 10 % » et posait le texte a 9 % de marge :
    le bas du sous-titre livre par defaut passait SOUS la ligne, sans un mot.
    Le defaut d'usine doit desormais se tenir au-dessus des DEUX reperes que
    l'apercu dessine (zone sure 10 %, bande d'UI des reseaux 13 %), et la
    largeur d'usine doit tomber exactement sur la zone sure laterale."""
    src = _layer()
    assert _const(src, "SUBS_SAFE_TITLE") == "10"
    assert _const(src, "SUBS_SOCIAL_BOT") == "13"
    assert _const(src, "SUBS_MARGIN_DEF") == "SUBS_SOCIAL_BOT"
    assert _const(src, "SUBS_WIDTH_DEF") == "100-2*SUBS_SAFE_TITLE"
    # le style par defaut lit CES constantes, il ne reecrit pas un chiffre
    dft = src.split("function subsDefaultStyle(", 1)[1].split("}", 1)[0]
    assert "width:SUBS_WIDTH_DEF" in dft
    assert "marginV:SUBS_MARGIN_DEF" in dft
    # ... et les valeurs d'usine ne declenchent donc pas le controle de zone
    # sure : marge 13 >= 10, marges laterales (100-80)/2 = 10 >= 10.
    assert 13 >= 10 and (100 - (100 - 2 * 10)) / 2 >= 10


def test_sortir_de_la_zone_sure_est_dit_a_l_ecran():
    """Un reglage qui franchit le repere doit s'annoncer la ou il est franchi
    (bandeau de placement) ET la ou il se repare (onglet Style), comme les
    autres defauts — avec le geste qui le ferme."""
    src = _strip_comments(_layer())
    assert "function subsSafeIssues(" in src
    # dans les ecarts apercu/gravure, donc dans le badge de l'onglet Style
    assert "safe:subsSafeIssues(st)" in src
    # dans le bandeau du lecteur, pendant le geste
    assert "var safeBad=subsSafeIssues(style)" in src
    assert "hors zone sûre" in _layer()
    # et les deux correctifs ramenent exactement sur la ligne
    assert 'champ:"width",valeur:wSafe' in src
    assert 'champ:"marginV",valeur:SUBS_SAFE_TITLE' in src
    assert '.sub-hud[data-out]' in CSS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 5. les reglages qui servent le plus sont AU-DESSUS de la galerie
# ---------------------------------------------------------------------------

def test_les_reglages_precedent_la_galerie():
    """Tout ce qui etait au-dessus de la ligne de flottaison etait une galerie
    de prereglages : ni taille, ni couleur, ni epaisseur de contour, ni marge.
    Le bloc « Reglages » doit venir AVANT la grille de prereglages."""
    src = _layer()
    sty = src.split("const SubsStyle=", 1)[1]
    body = sty.split("return r.jsxs(", 1)[1]
    i_quick = body.index('className:"sub-quick"')
    i_grid = body.index('className:"sub-pgrid"')
    assert i_quick < i_grid, "les reglages doivent preceder la galerie"
    quick = body[i_quick:i_grid]
    for ctrl in ('rng("size"', 'col("color"', '"Contour"', '"marginV"'):
        assert ctrl in quick, f"reglage absent du bloc du haut : {ctrl}"


def test_aucun_reglage_en_double():
    """Un reglage remonte dans « Reglages » ne doit pas rester dans son module :
    deux curseurs pour la meme valeur, c'est un autre visage du meme bug."""
    src = _strip_comments(_layer())
    sty = src.split("const SubsStyle=", 1)[1]
    body = sty.split("return r.jsxs(", 1)[1]
    quick = body[body.index('className:"sub-quick"'):body.index('className:"sub-pgrid"')]
    folds = body[body.index('className:"sub-pgrid"'):]
    for ctrl in ('rng("size"', 'col("color"', 'rng("marginV"'):
        assert ctrl in quick
        assert ctrl not in folds, f"reglage present deux fois : {ctrl}"
    # l'epaisseur de contour vit dans le bloc du haut, l'interrupteur a disparu
    assert 'sw("outOn"' not in body
    assert '"aria-label":"Épaisseur du contour"' in quick
