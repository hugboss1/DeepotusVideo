# -*- coding: utf-8 -*-
"""Banc de mutations du lot E-B du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_eb.py            # toutes
    python tests/mutations_montage_eb.py 0 7 16     # celles-la

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_l3.py` (5-uplets, mutation en OCTETS, sha256
restaure dans `finally`, etat MORT distinct de ROUGE).

CE QU'IL MUTE, ET POURQUOI CES QUATRE FICHIERS-LA. Le lot E-B (E-2 tiroir
Medias, E-5 Preview/Rendre/Publier, E-11 voile, E-8 inspecteur, E-9
separateur et durees, D-7 mini-carte) vit des deux cotes du reseau :
  · `backend/app/services/pipeline.py` : `Pipeline.list_jobs` (offset,
    providers avec `NULL` lu seedance, `q` echappe) ;
  · `backend/app/api/routes.py` : la route `GET /jobs` (`video=1` ->
    `media_rules()`) ;
  · `frontend/patches/montage.js` : LA COUCHE, celle que le shim de
    `test_montage_edition.py` execute (`dzmProvGroupe`, `dzmProvChips`,
    `dzmMediaFiltre`, la ligne `vus=` de `DzmMediaDrawer`, `dzmFinStore`,
    `dzmInspW`, `dzmTlH`, `dzmDurLbl`, `dzmMinimap`) ;
  · `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour les
    mutations qui ne sont PAS dans la couche mais dans le corps du bundle
    reecrit par une section du patcher (EB5a, R_TT11, R_EB2, EB6a, EB7b,
    EB8a) -- muter le PATCHER puis rejouer la chaine prouverait seulement
    que le patcher est coherent avec lui-meme et couterait la chaine
    entiere a chaque essai ; c'est le fichier que l'application charge et
    que `test_montage_bundle.py` lit.

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. Backend -> `eb` ; couche
JS -> `edition` ; bundle livre -> `bundle`. Le banc `bundle` n'est jamais
choisi pour une mutation de la COUCHE : il compare le bloc injecte a
`montage.js` octet pour octet, TOUTE mutation de la couche l'y ferait rougir
et le bruit noierait le signal.

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF), les motifs sont ecrits en LF et remis
dans la fin de ligne du fichier ; c'est le sha256 d'APRES qui prouve la
restauration, pas cette phrase. Les motifs qui portent un antislash (la n°4,
`\\\\%`) se verifient par CE script, jamais par un heredoc Bash.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
La restauration est verifiee par sha256 APRES CHAQUE mutation, dans un
`finally`. Un banc qui ne rend pas `=== N passed, M failed ===` ou un code
autre que 0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

RESULTAT MESURE le 23/09/2026 (worktree epic-fermi-f6adf5, sommet 7b584f6 +
la cloture, python embarque, un processus par execution de banc) : LES
VINGT-TROIS SONT ROUGES, AUCUN SURVIVANT, AUCUN MORT, chacune sur les
lignes declarees ; code de sortie 0. Deux candidates de plus (les deux
formes de « q sensible a la casse », ci-dessous) ont SURVECU et ont ete
ecartees. Comptes des bancs au repos :
eb 24/0, edition 245/0, bundle 1892/0.

    #   fonction visee                                    banc     rouges
    0   list_jobs sans .offset(                           eb       4
    1   providers ignore (where retire)                   eb       2
    2   provider NULL non lu seedance                     eb       1
    3   video=1 sans regle (exts=None)                    eb       4
    4   jokers LIKE non echappes                          eb       2
    5   dzmProvGroupe sans repli seedance                 edition  2
    6   dzmProvChips sans « Tout »                        edition  2
    7   dzmMediaFiltre sans groupe                        edition  1
    8   le tiroir sans le juge de statut (vus=jobs)       edition  1
    9   dzmFinStore qui ne retire pas sur null            edition  2
   10   dzmInspW sans borne haute                         edition  2
   11   dzmTlH sans borne basse                           edition  2
   12   dzmDurLbl qui ignore `on`                         edition  1
   13   dzmMinimap qui garde les clips hors duree         edition  1
   14   EB5a voile sans setDzFin(null)                    bundle   7
   15   R_TT11 « + » video sans garde demo                bundle   4
   16   R_EB2 chip medias sans garde demo                 bundle   6
   17   EB6a aside sans `inspOn?`                         bundle   5
   18   EB7b .svm-tl sans data-h                          bundle   3
   19   EB8a onSeek sans la gouttiere -88                 bundle   5
   20   EB5a voile sans setPop("")                        bundle   5
   21   EB5b racine .svm-pop sans stopPropagation         bundle   4
   22   R_TT11 « + » video rappelle openPicker            bundle   4

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  · DEUX candidates du plan, « `q` sensible a la casse » (le `func.lower`
    de la colonne, puis le `.lower()` de `q`), sont des SURVIVANTES (0
    rouge chacune) et ne sont PAS dans la table : le LIKE de SQLite est
    insensible a la casse pour l'ASCII par construction — voir le bloc
    ECARTEES sous la table ;
  · la n°11 (`dzmTlH` sans borne basse) ne rougit PAS la ligne « les bornes
    elles-memes » : elle donne .3*t et .7*t en ENTREE, valeurs qu'une borne
    basse a 0 laisse passer telles quelles — c'est la ligne du coeur pur,
    qui pinne le literal `.3*t`, et la ligne des valeurs (100 -> 300) qui
    parlent. La ligne des bornes n'est pas fausse, elle mesure autre chose
    (les entrees non numeriques) ;
  · les mutations du bundle rougissent de 3 a 7 lignes : la ligne nommee de
    la section, la ligne GENERIQUE `<section>_remplace` que la boucle sur
    `P.PATCHES` emet, la ligne de la queue du patcher (`DZ_le_patcher_porte…`)
    qui compte chaque remplacement — et, pour la n°14, `E4_le_bandeau_se_
    ferme_au_lancement` et `EB_fermer_et_lancer_ne_touchent_pas_le_store`
    qui comptent les `setDzFin(null)` du bundle (quatre formes, une par
    site) ; pour la n°15, `D21_TT11` qui pinne le bloc TT11 entier ; pour la
    n°16, `EB6c`/`EB7c` dont les replis sont DANS R_EB2 ; pour la n°21,
    `EB5b…_ancre_consommee` — la forme mutee EST l'ancre d'avant patch, le
    banc la voit renaitre ; pour la n°22, `M16lib_openPicker_a_exactement_
    trois_appelants` — le « + » video rappelant openPicker en fait quatre ;
    c'est le miroir qui parle, pas un doublon ;
  · la n°0 rougit aussi « offset au-dela rend une liste vide » : sans
    `.offset(`, la premiere page revient au lieu de rien — l'etat vide que
    le banc etablit d'abord est bien celui-la ;
  · la n°5 rougit la ligne des CHIPS : elles sont derivees par
    `dzmProvGroupe`, la chip « null » y apparait aussi.
(Le detail exact des noms de lignes est celui que le script IMPRIME ; la
colonne « rouges » ci-dessus est `N_ROUGES`, le COMPTE mesure que main()
compare a chaque execution, pas un resume.)

ECARTS AU PLAN, DATES 23/09/2026 : le plan nommait quinze candidates ; la
table en porte vingt-trois — quatorze du plan (dont « EB5 sans
stopPropagation » = n°21 sur la racine `.svm-pop` d'EB5b, et « R_TT11 ou le
+ video rappelle openPicker » = n°22 ; la quinzieme, « q sensible a la
casse », est ecartee comme survivante sous ses deux formes, bloc ECARTEES)
plus neuf tirees de la lecture du code (n°2 NULL/seedance, n°4 jokers, n°8
`vus=`, n°14 voile sans setDzFin, n°15 et n°16 gardes demo du « + » et de
la chip, n°18 data-h, n°19 gouttiere, n°20 voile sans setPop).
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
JS = "frontend/patches/montage.js"
PIPE = "backend/app/services/pipeline.py"
ROUTES = "backend/app/api/routes.py"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"
B_EB = "tests/test_montage_eb.py"

_DEMO = ('if(proj.demo){fireNote("Ajout d\'assets : disponible sur un projet '
         'réel — la démo reste une maquette.");return}')

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, rouges attendues)
M = [
    # ── E-2 backend : GET /jobs ──────────────────────────────────────────
    # 0 — `list_jobs` sans `.offset(` : la page 2 rend la page 1 (l'ETAT
    #     VIDE que le banc etablit d'abord).
    (B_EB, PIPE,
     '                stmt.order_by(JobRecord.created_at.desc()).offset(offset).limit(limit)\n',
     '                stmt.order_by(JobRecord.created_at.desc()).limit(limit)\n',
     # MESURE : quatre lignes, dont « offset au-dela rend une liste vide » —
     # sans .offset(, la premiere page revient au lieu de rien.
     ["eb_jobs_offset_rend_la_page_suivante_sans_recouvrement",
      "eb_jobs_offset_pres_de_la_fin_rend_le_reste",
      "eb_jobs_les_filtres_se_combinent_avec_la_pagination",
      "eb_jobs_offset_au_dela_rend_une_liste_vide_200"]),
    # 1 — `providers` ignore : le `where` retire, la liste rend tout.
    (B_EB, PIPE,
     '        if provs:\n            stmt = stmt.where(func.coalesce(JobRecord.provider, "seedance").in_(provs))\n',
     '',
     ["eb_jobs_providers_ne_rend_que_ces_providers",
      "eb_jobs_providers_espaces_et_vides_tolere_et_provider_nul_lu_seedance"]),
    # 2 — `NULL` non lu « seedance » : `providers=seedance` perd les 13 jobs
    #     a provider NULL de la base reelle (mesure du docstring du service).
    (B_EB, PIPE,
     '            stmt = stmt.where(func.coalesce(JobRecord.provider, "seedance").in_(provs))\n',
     '            stmt = stmt.where(JobRecord.provider.in_(provs))\n',
     ["eb_jobs_providers_espaces_et_vides_tolere_et_provider_nul_lu_seedance"]),
    # 3 — `video=1` sans regle : la route n'appelle plus `media_rules()` et
    #     ne passe aucune extension ; le png et le sans-artefact entrent.
    (B_EB, ROUTES,
     '        exts = tuple(_ms.media_rules().get("video_exts") or ())\n',
     '        exts = None\n',
     ["eb_jobs_video_1_ne_rend_que_des_jobs_video_selon_media_rules",
      "eb_jobs_video_1_ecarte_le_png_et_le_sans_artefact_et_garde_l_extension_en_capitales",
      "eb_video_1_passe_par_media_rules_et_limit_seul_non",
      "eb_la_regle_servie_est_celle_appliquee_par_video_1"]),
    # 4 — jokers LIKE non echappes : `q=100%` rend aussi « 100 pour cent »,
    #     `q=snake_case` rend aussi « snakeXcase ». Motif avec `\\%` : verifie
    #     par CE script, jamais par un heredoc.
    (B_EB, PIPE,
     '             .replace("%", "\\\\%").replace("_", "\\\\_"))\n',
     '             )\n',
     ["eb_jobs_q_echappe_le_pour_cent_temoin_sans_joker_en_rend_deux",
      "eb_jobs_q_echappe_le_souligne_temoin_sans_joker_en_rend_deux"]),
    # ── la couche (montage.js), jouee sous node par `edition` ────────────
    # 5 — `dzmProvGroupe` sans le repli seedance : un provider NULL devient
    #     la chip « null » au lieu de « Studio ».
    (B_EDIT, JS,
     'function dzmProvGroupe(p){var k=(p==null||p==="")?"seedance":String(p);return DZM_PROV_LBL[k]||k}',
     'function dzmProvGroupe(p){var k=String(p);return DZM_PROV_LBL[k]||k}',
     # MESURE : deux lignes — les chips sont DERIVEES par dzmProvGroupe, la
     # chip « null » apparait donc aussi dans la ligne des chips.
     ["prov_groupe_derive_du_provider_null_vaut_seedance_inconnu_tel_quel",
      "prov_chips_derivees_uniques_tout_en_tete_ordre_d_apparition"]),
    # 6 — `dzmProvChips` sans « Tout » en tete : plus de retour au tout.
    (B_EDIT, JS,
     'function dzmProvChips(jobs){var out=["Tout"],seen={};',
     'function dzmProvChips(jobs){var out=[],seen={};',
     ["prov_chips_derivees_uniques_tout_en_tete_ordre_d_apparition"]),
    # 7 — `dzmMediaFiltre` sans `groupe` : la chip ne filtre plus rien.
    (B_EDIT, JS,
     'if(g!=="Tout"&&dzmProvGroupe(j.provider)!==g)return !1;\n',
     '\n',
     ["media_filtre_par_groupe"]),
    # 8 — le tiroir sans le juge de statut (`vus=jobs`) : un job en cours
    #     dont `video_path` est deja pose entre dans le tiroir (revue
    #     dfc1239).
    (B_EDIT, JS,
     '  var vus=jobs.filter(function(j){return dzmIsVideoJob(j,o.exts)});\n',
     '  var vus=jobs;\n',
     ["media_drawer_applique_toujours_le_juge_de_statut_exts_facultatif"]),
    # 9 — `dzmFinStore` qui ne retire pas sur null : la cle reste, Publier
    #     rouvre un rendu qui n'existe plus.
    (B_EDIT, JS,
     '  if(fin==null)delete out[k];\n  else out[k]=',
     '  if(fin!=null)out[k]=',
     # MESURE : deux lignes — la ligne des bornes retire aussi sur null
     # (retrait d'une cle absente = store inchange, objet neuf).
     ["fin_store_null_retire_la_cle",
      "fin_store_bornes_pid_vide_store_non_objet_objet_neuf_et_voisines"]),
    # 10 — `dzmInspW` sans borne haute : l'inspecteur peut manger l'ecran.
    (B_EDIT, JS,
     'function dzmInspW(raw){return Math.round(dzmClamp(raw,260,480,300))}',
     'function dzmInspW(raw){return Math.round(dzmClamp(raw,260,1e9,300))}',
     ["insp_w_borne_260_480_defaut_300_sur_null_vide_et_non_numerique",
      "insp_coeur_pur_et_inspW_passe_par_clamp_avec_260_480_300"]),
    # 11 — `dzmTlH` sans borne basse : la timeline peut tomber a 0.
    (B_EDIT, JS,
     '  var n=dzmClamp(raw,.3*t,.7*t,NaN);\n',
     '  var n=dzmClamp(raw,0,.7*t,NaN);\n',
     # MESURE : la ligne « bornes elles-memes » NE rougit PAS (elle donne
     # .3*t et .7*t en ENTREE, qu'une borne basse a 0 laisse passer) ; c'est
     # la ligne du coeur pur, qui pinne le literal `.3*t`, qui rougit avec
     # la ligne des valeurs (tlH(100,1000) rend 100 au lieu de 300).
     ["tlh_borne_30_70_pour_cent_du_total_arrondi_null_sans_choix_ou_sans_total",
      "tlh_durlbl_coeur_pur_tlH_passe_par_clamp_durLbl_par_dzmDurTxt_aucun_second_formateur"]),
    # 12 — `dzmDurLbl` qui ignore `on` : la duree s'affiche chip eteinte.
    (B_EDIT, JS,
     '  if(!on||!(d>0))return l;\n',
     '  if(!(d>0))return l;\n',
     ["durlbl_ajoute_la_duree_m_ss_quand_la_chip_est_allumee_label_seul_sinon_ou_sans_duree"]),
    # 13 — `dzmMinimap` qui garde les clips hors duree : un rect au-dela de
    #      100 % (x0 > 1) ou avant 0.
    (B_EDIT, JS,
     '    var s=Number(c.start),e=Number(c.end);if(!(e>s)||e<=0||s>=d)return;\n',
     '    var s=Number(c.start),e=Number(c.end);if(!(e>s))return;\n',
     ["mm_"]),
    # ── le bundle livre (sections du patcher), lu par `bundle` ───────────
    # 14 — EB5a : le voile ne ferme plus le bandeau de fin (`setDzFin(null)`
    #      retire) : cliquer a cote du bandeau ne le ferme pas.
    (B_BUND, BUN,
     'onClick:function(){setPop("");setDzFin(null)}}):null,',
     'onClick:function(){setPop("")}}):null,',
     ["EB5a_le_voile_est_monte_entre_transPopover_et_kbPanel_sur_le_predicat_pop_ou_dzFin",
      "EB5_les_quatre_setDzFin_null_ont_chacun_leur_forme"]),
    # 15 — R_TT11 : le « + » video ouvre le tiroir SANS la garde demo (la
    #      revue 3e9a878 : addAsset n'a pas de garde, ses appelants l'ont).
    (B_BUND, BUN,
     '!(e&&e.shiftKey)){' + _DEMO + 'setMedTr(tr.id);',
     '!(e&&e.shiftKey)){setMedTr(tr.id);',
     ["EB_revue_la_chip_et_le_plus_video_refusent_la_demo_comme_openPicker"]),
    # 16 — R_EB2 : la chip « medias » sans la garde demo.
    (B_BUND, BUN,
     'onClick:function(){' + _DEMO + 'setMedTr("");setMedOn(!medOn);',
     'onClick:function(){setMedTr("");setMedOn(!medOn);',
     ["EB_revue_la_chip_et_le_plus_video_refusent_la_demo_comme_openPicker"]),
    # 17 — EB6a : l'aside n'est plus conditionne par `inspOn` (`!0?` garde
    #      la syntaxe : le repli `]}):null` de M13 reste) — la bascule ne
    #      ferme plus rien.
    (B_BUND, BUN,
     'inspOn?r.jsxs("aside",{className:"svm-insp",style:{width:inspW},"data-w":inspW,',
     '!0?r.jsxs("aside",{className:"svm-insp",style:{width:inspW},"data-w":inspW,',
     ["EB6a_l_aside_est_conditionne_par_inspOn_porte_sa_largeur_data_w_et_sa_poignee_en_tete"]),
    # 18 — EB7b : `.svm-tl` sans `data-h` : la feuille ne leve plus le
    #      plafond 48vh, la hauteur choisie est ecrasee par max-height.
    (B_BUND, BUN,
     'r.jsxs("div",{className:"svm-tl","data-h":tlH||void 0,style:tlH?{height:tlH}:void 0,children:[',
     'r.jsxs("div",{className:"svm-tl",style:tlH?{height:tlH}:void 0,children:[',
     ["EB7b_la_poignee_precede_svm_tl_qui_porte_data_h_et_sa_hauteur_inline_ancre_a_quatre_espaces"]),
    # 19 — EB8a : onSeek sans la gouttiere de 88 px (deux fois) : le clic
    #      centre a cote, d'autant plus que la timeline est courte.
    (B_BUND, BUN,
     'var w=el.scrollWidth-88;el.scrollLeft=Math.max(0,f*w-(el.clientWidth-88)/2)',
     'var w=el.scrollWidth;el.scrollLeft=Math.max(0,f*w-(el.clientWidth)/2)',
     ["EB8a_onSeek_centre_scrollLeft_sur_la_fraction_gouttiere_deduite_deux_fois_jamais_sous_zero"]),
    # 20 — EB5a : le voile ne ferme plus le popover (`setPop("")` retire) :
    #      le mode reste arme sous le voile.
    (B_BUND, BUN,
     'onClick:function(){setPop("");setDzFin(null)}}):null,',
     'onClick:function(){setDzFin(null)}}):null,',
     ["EB5a_le_voile_est_monte_entre_transPopover_et_kbPanel_sur_le_predicat_pop_ou_dzFin"]),
    # 21 — EB5b : la racine du popover sans `stopPropagation` : un clic DANS
    #      le popover remonte au voile ? Non — le voile est un FRERE, pas un
    #      parent (mesure) ; la garde est defensive, et le banc la pinne.
    (B_BUND, BUN,
     '    return r.jsxs("div",{className:"svm-pop",onClick:function(e){e.stopPropagation()},children:[',
     '    return r.jsxs("div",{className:"svm-pop",children:[',
     ["EB5b_la_racine_de_popover_arrete_le_clic_et_ovPicker_reste_sans_voile_ni_stopPropagation"]),
    # 22 — R_TT11 : le « + » video rappelle `openPicker` au lieu d'ouvrir le
    #      tiroir (l'etat d'avant E-2) : `openPicker(tr.id)` passe a deux.
    (B_BUND, BUN,
     'setMedTr(tr.id);setMedOn(!0);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1);return}',
     'openPicker(tr.id);return}',
     ["EB_R_TT11_le_plus_d_une_piste_video_ouvre_le_tiroir_et_Maj_clic_garde_le_selecteur"]),
]

# ECARTEES, MESUREES le 23/09/2026 (SURVIVANTES, 0 rouge chacune) : « `q`
# sensible a la casse », sous ses DEUX formes — `func.lower(` retire de la
# colonne titre, et `.lower()` retire de `q` — survit au banc eb : le LIKE de
# SQLite est insensible a la casse pour l'ASCII par construction (sans ICU,
# `lower()` ne plie d'ailleurs que l'ASCII aussi), le titre « PREUVE-EB » est
# ASCII et la requete `preuve-eb` le trouve sans les deux `lower`. Le
# `lower` du service est une CEINTURE pour un autre moteur, pas un
# comportement observable sur SQLite ; une ligne de banc ne peut pas le
# voir, elle ne le promet donc pas. Une mutation qui survit n'entre pas dans
# une table qui promet 0.

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (4, 2, 1, 4, 2, 2, 2, 1, 1, 2, 2, 2, 1, 1, 7, 4, 6, 5, 3, 5, 5, 4, 4)
assert len(N_ROUGES) == len(M), (len(N_ROUGES), len(M))


def rouges(banc):
    """Les noms des lignes ROUGES du banc, sa sortie, et un drapeau d'ERREUR.

    Le banc rend 0 (tout vert) ou 1 (des rouges) ; tout autre code veut dire
    qu'il est MORT au lieu de rougir -- la faute n°6 du chantier -- et l'on
    rend un troisieme etat plutot que de lire une liste vide comme « rien
    casse ».
    """
    r = subprocess.run([PY, banc], capture_output=True,
                       cwd=R / "backend", timeout=1800)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    erreur = r.returncode not in (0, 1) or "=== " not in txt
    return set(re.findall(r"^  FAIL  (\S+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (banc, rel, old, new, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()                      # OCTETS, jamais read_text
        sha_avant = hashlib.sha256(src).hexdigest()
        brut = src.decode("utf-8")
        # LE MOTIF EST ECRIT EN LF ET REMIS DANS LA FIN DE LIGNE DU FICHIER,
        # mesuree ici et non supposee. Le sha256 d'apres verifie l'aller-retour.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            # EXACTEMENT UNE FOIS : deux sites mutes rendraient le verdict
            # illisible (quelle ligne rouge accuse lequel ?).
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:60])
            txt = txt.replace(o, n_)
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        # Les lignes attendues sont des SOUS-CHAINES : les bancs prefixent
        # leurs noms par la section, et l'on veut nommer la panne, pas
        # recopier un prefixe qui bougera.
        manquants = sorted(a for a in attendus
                           if not any(a in x for x in rg))
        if erreur:
            verdict = "MORT(pas rouge)"
            print(sortie[-1500:], file=sys.stderr)
        elif not rg:
            verdict = "SURVIVANT"
        elif manquants:
            verdict = "ROUGE(autres)"
        elif len(rg) != N_ROUGES[i]:
            verdict = "ROUGE(compte)"
        else:
            verdict = "ROUGE"
        bilan.append((i, verdict, sorted(rg), manquants))
        print(f"[{i:2d}] {verdict:16s} {banc.split('_')[-1][:-3]:11s} "
              f"{pathlib.Path(rel).name:24s} {paires[0][0].strip()[:40]!r}")
        print(f"     rouges({len(rg)}/{N_ROUGES[i]})={sorted(rg)}")
        if manquants:
            print(f"     MANQUANTS={manquants}")
        print(f"     sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:2] for b in bilan], ensure_ascii=False))
    # LU PAR CODE DE SORTIE, jamais par grep : 1 des qu'une mutation survit,
    # meurt, rougit ailleurs que la ligne nommee ou plus/moins que N_ROUGES.
    sys.exit(0 if bilan and all(v == "ROUGE" for _, v, _, _ in bilan) else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
