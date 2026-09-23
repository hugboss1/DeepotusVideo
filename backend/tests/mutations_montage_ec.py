# -*- coding: utf-8 -*-
"""Banc de mutations du lot E-C du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_ec.py            # toutes
    python tests/mutations_montage_ec.py 0 7 16     # celles-la

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_eb.py` (5-uplets, mutation en OCTETS, sha256
restaure dans `finally`, etat MORT distinct de ROUGE).

CE QU'IL MUTE, ET POURQUOI CES TROIS FICHIERS-LA. Le lot E-C (E-6 menu ☰ et
menus contextuels, E-7 trois vues, E-10 barre ancree, E-12 audit des
boutons, E-13 tete dans l'inspecteur, E-14 trou selectionne) ne touche PAS
le backend : tout vit dans le client.
  · `frontend/patches/montage.js` : LA COUCHE, celle que le shim de
    `test_montage_edition.py` execute (`dzmComboToKey`, `dzmMenuRub`,
    `dzmMenuModel`, `DzmCtxMenu`, `dzmJobsTri`, `dzmTeteTxt`, `dzmTrou`,
    `dzmTrouRipple`, `DzmToolBar`, `saisir` de `DzmToolDock`) ;
  · `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour les
    mutations qui ne sont PAS dans la couche mais dans le corps du bundle
    reecrit par une section du patcher (EC1, EC4, EC7, EC13, R_EB5A,
    R_M16REF, EC15b, EC15d) -- muter le PATCHER puis rejouer la chaine
    prouverait seulement que le patcher est coherent avec lui-meme et
    couterait la chaine entiere a chaque essai ; c'est le fichier que
    l'application charge, que `test_montage_bundle.py` et
    `test_montage_ergonomie.py` lisent ;
  · `frontend/dist/shared/montage.css` : LA FEUILLE, pour la seule regle
    d'E-10 qui fait tout (`position:static` : sans elle la barre « ancree »
    flotte encore), lue par `test_montage_bundle.py` (section [EC] E-10).

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. Couche JS -> `edition` ;
bundle livre / feuille -> `bundle` ; les deux regles d'E-12 (infobulle
obligatoire, un bouton se grise) -> `ergonomie`. Le banc `bundle` n'est
jamais choisi pour une mutation de la COUCHE : il compare le bloc injecte a
`montage.js` octet pour octet, TOUTE mutation de la couche l'y ferait rougir
et le bruit noierait le signal. Et `ergonomie` n'est pas choisi pour une
mutation que `bundle` couvre aussi (les deux d'E-12 rougissent `bundle` par
la ligne `_remplace` de leur section : c'est la REGLE d'audit que l'on veut
voir parler, pas le pin de section).

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF ; les trois fichiers sont en CRLF, mesure
du 23/09/2026), les motifs sont ecrits en LF et remis dans la fin de ligne
du fichier ; c'est le sha256 d'APRES qui prouve la restauration, pas cette
phrase. La restauration est une application INVERSE (les octets d'avant
reecrits), JAMAIS un `git checkout` : le worktree peut porter d'autres
changements non commis.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
La restauration est verifiee par sha256 APRES CHAQUE mutation, dans un
`finally`. Un banc qui ne rend pas `=== N passed, M failed ===` ou un code
autre que 0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

RESULTAT MESURE le 23/09/2026 (worktree epic-fermi-f6adf5, sommet 072741c +
la cloture, python embarque, un processus par execution de banc) : LES
VINGT ET UNE SONT ROUGES, AUCUN SURVIVANT, AUCUN MORT, chacune sur les
lignes declarees ; code de sortie 0. Comptes des bancs au repos :
ergonomie 36/0, edition 278/0 (277 + la sonde `rip_autre` de la cloture),
bundle 2055/0.

    #   fonction visee                                    banc       rouges
    0   dzmComboToKey sans Maj -> shiftKey                edition    3
    1   dzmMenuModel sans ordre fixe (Object.keys)        edition    3
    2   dzmMenuRub : repli Audio -> Timeline              edition    1
    3   DzmCtxMenu sans disabled:!!it.off                 edition    1
    4   DzmCtxMenu : onClose hors du finally              edition    2
    5   dzmJobsTri gardant les apercus dans finals        edition    5
    6   dzmTeteTxt sans « hors du plan »                  edition    2
    7   dzmTrou acceptant la queue de piste               edition    2
    8   dzmTrouRipple decalant les autres pistes          edition    2
    9   DzmToolBar sans data-docked                       edition    2
   10   saisir sans la garde docked                       edition    1
   11   EC1 dzFire sans bubbles/cancelable                bundle     4
   12   R_EB5A voile sans dzMenu                          bundle     6
   13   EC4 clic droit clip sans preventDefault           bundle     4
   14   EC7 data-view retire                              bundle     5
   15   [data-docked] sans position:static (feuille)      bundle     1
   16   R_M16REF effet [view,proj.name] -> [view]         bundle     2
   17   R_M16REF useEffect(...,[clips]) retire            bundle     3
   18   EC13 Suppr sans pushHistory                       bundle     4
   19   EC15b disabled:proj.demo retire du bouton or      ergonomie  1
   20   EC15d un title retire (Fermer le selecteur)       ergonomie  2

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  · la n°8 (`dzmTrouRipple` decalant les autres pistes) SURVIVAIT sur le
    comportement avant la cloture : dans le jeu `_g` du banc edition, aucun
    clip d'une autre piste ne commence APRES la borne b du trou (n [0,10[ sur
    a1, o [5,9[ sur v2, b = 6), le ripple « toutes pistes » y rendait le
    meme tableau ; seul le pin textuel `c.tr!==tr` rougissait. La cloture a
    AJOUTE la sonde `rip_autre` (v2 [7,9[ reste en place) : la ligne
    `ripple_revue_t7_…` est celle du comportement, edition 277 -> 278 ;
  · la n°10 (`saisir` sans la garde docked) et la n°11 (`dzFire` sans
    `bubbles`) ne rougissent QUE par un pin de forme : la poignee n'est pas
    jouee par le shim (aucun geste pointeur), et `bubbles` est INERTE pour un
    ecouteur pose SUR window, la cible meme du dispatch (ecart date
    23/09/2026 : le plan disait « si ca rougit — sinon ecarter » ; ca rougit,
    par le pin, et c'est dit) ;
  · les mutations du bundle rougissent de 1 a 6 lignes : la ligne nommee de
    la section, la ligne GENERIQUE `<section>_remplace` que la boucle sur
    `P.PATCHES` emet, la ligne de la queue du patcher (`DZ_le_patcher_porte…
    _la_sonde_dit_132`) qui compte chaque remplacement -- et, pour la n°14
    (data-view), `EC7…_ancre_consommee` : la forme mutee EST l'ancre d'avant
    patch, le banc la voit renaitre ; pour la n°12 (voile), les DEUX lignes
    d'EB5a du lot E-B (`_sur_le_predicat_pop_ou_dzFin`, `_z_index_est_la_seule
    _parade`) : E-6 a reecrit R_EB5A, ces pins lisent la forme livree ; pour
    les n°16 et n°17 (replis de R_M16REF), `M16ref-tracks-ref_remplace` sans
    ligne de queue (l'ancre A_M16REF est conservee, le compte des
    remplacements ne bouge pas) ; la n°15 (feuille) ne rougit qu'UNE ligne :
    la feuille n'a pas de patcher, aucune ligne generique ;
  · la n°17 rougit aussi `E14_Echap…` : elle compte `setGapSel` x6, l'effet
    retire en fait cinq -- un compte est un temoin, pas un doublon ;
  · la n°5 rougit CINQ lignes : les trois du tri, le rendu du panneau (les
    rangees sortent toutes « final ») et le pin `DZM_DEL_APERCU` x1 dans le
    corps de `dzmJobsTri` (0 apres la mutation) ;
  · les deux d'E-12 (n°19, n°20) sont jouees sur le banc `ergonomie` SEUL
    (le banc `bundle` pinne aussi ces sections par leur ligne `_remplace`,
    non mesure ici) -- c'est la REGLE d'audit que l'on prouve, pas un pin.
(Le detail exact des noms de lignes est celui que le script IMPRIME ; la
colonne « rouges » ci-dessus est `N_ROUGES`, le COMPTE mesure que main()
compare a chaque execution, pas un resume.)

ECARTS AU PLAN, DATES 23/09/2026 : le plan nommait quinze candidates ; la
table en porte vingt et une -- quatorze du plan (« dzFire sans bubbles »
gardee, voir ci-dessus ; « rubrique par defaut fausse » = n°2 sur le repli
Audio ; « data-view retire » = n°14 ; « Suppr sans pushHistory » = n°18 ;
« un title retire » = n°20) plus sept tirees de la lecture du code (n°4
onClose hors du finally, n°10 la garde docked de `saisir`, n°13 le
preventDefault du clic droit, n°16 l'effet `[view,proj.name]` de la revue
T3, n°17 l'effet `[clips]` de la revue T5, n°19 `disabled:proj.demo` du
bouton or, n°7 la queue de piste). AUCUNE candidate ecartee : les vingt et
une rougissent.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
JS = "frontend/patches/montage.js"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
CSS = "frontend/dist/shared/montage.css"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"
B_ERGO = "tests/test_montage_ergonomie.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, rouges attendues)
M = [
    # ── la couche (montage.js), jouee sous node par `edition` ────────────
    # 0 — `dzmComboToKey` sans « Maj » : « Maj+X », « Ctrl+Maj+X », « Maj+M »
    #     rendent null (le jeton n'est ni modificateur ni dernier) ; les
    #     combos du bundle qui portent Maj ne se rejouent plus.
    (B_EDIT, JS,
     'else if(l==="maj"||l==="shift")k.shiftKey=!0;',
     'else if(l==="shift")k.shiftKey=!0;',
     ["combo_six_cas_lettre_minuscule_maj_shift",
      "combo_bornes_null_nombre_echap",
      "combo_toutes_les_combos_du_bundle_patche_sont_parsables"]),
    # 1 — `dzmMenuModel` sans l'ordre fixe : les rubriques sortent dans
    #     l'ordre d'apparition des actions (Timeline avant Edition).
    (B_EDIT, JS,
     'return DZM_MENU_ORDRE.filter(function(n){return par[n]&&par[n].length})',
     'return Object.keys(par)',
     ["menu_cinq_actions_quatre_rubriques_dans_l_ordre_fixe",
      "menu_sec_inconnue_timeline_ids_inconnus_audio_edition",
      "ec_coeur_pur_les_trois_fonctions"]),
    # 2 — `dzmMenuRub` : le repli Audio -> Edition retire ; un id inconnu
    #     de sec Audio tombe en Timeline.
    (B_EDIT, JS,
     'return a.sec==="Audio"?"Édition":a.sec==="Affichage"?"Affichage":"Timeline"}',
     'return a.sec==="Affichage"?"Affichage":"Timeline"}',
     ["menu_sec_inconnue_timeline_ids_inconnus_audio_edition"]),
    # 3 — `DzmCtxMenu` sans `disabled:!!it.off` : « Publier » sans rendu,
    #     « Transition… » sans voisin restent cliquables.
    (B_EDIT, JS,
     'role:"menuitem",disabled:!!it.off,title:it.lbl,',
     'role:"menuitem",title:it.lbl,',
     ["ctx_porte_svm_pop_svm_menu_role_menu"]),
    # 4 — `onClose` hors du `finally` : un run qui leve laisse le menu ouvert
    #     sous le voile.
    (B_EDIT, JS,
     'onClick:function(){try{it.run&&it.run()}finally{o.onClose&&o.onClose()}},',
     'onClick:function(){it.run&&it.run();o.onClose&&o.onClose()},',
     ["ctx_le_clic_appelle_onClose_meme_quand_run_leve",
      "ctx_porte_svm_pop_svm_menu_role_menu"]),
    # 5 — `dzmJobsTri` qui garde les apercus dans `finals` : la vue Livraison
    #     compte un 480p comme un master.
    (B_EDIT, JS,
     '(t.indexOf(DZM_DEL_APERCU)>=0?prev:fin).push(j)});',
     'fin.push(j)});',
     ["jt_deux_finals_un_apercu",
      "jt_nom_vide_prend_tous_les_jobs_montage",
      "jt_bornes_null_chaine_non_objets",
      "del_rendu_racine_titre_trois_boutons",
      "e7_jobsTri_pur_Deliver_sans_hook_suffixe_unique"]),
    # 6 — `dzmTeteTxt` sans « hors du plan » : a ph == end, l'en-tete se
    #     tait au lieu de le dire.
    (B_EDIT, JS,
     ':" · hors du plan";',
     ':"";',
     ["tete_dans_le_plan_hors_a_la_borne_end",
      "e13_e14_coeur_pur_formateur_passe"]),
    # 7 — `dzmTrou` acceptant la queue de piste : sans clip suivant, un
    #     « trou » {a, b:null} est rendu (decision 8 : la queue n'est pas un trou).
    (B_EDIT, JS,
     '  if(b===null||b-a<.05)return null;\n',
     '  if(b!==null&&b-a<.05)return null;\n',
     ["trou_entre_deux_clips_a_la_borne_en_tete_dans_un_clip_en_queue",
      "trou_bornes_clips_null_chaine_t_nan_piste_null_inconnue"]),
    # 8 — `dzmTrouRipple` decalant les autres pistes : le clip v2 [7,9[
    #     recule aussi (la sonde `rip_autre` de la cloture : dans `_g`, aucun
    #     clip d'une autre piste ne commence apres b -- sans elle, cette
    #     mutation SURVIVAIT sur le comportement).
    (B_EDIT, JS,
     'if(!c||typeof c!=="object"||c.tr!==tr||!(Number(c.start)>=Number(b)-1e-6))return c;',
     'if(!c||typeof c!=="object"||!(Number(c.start)>=Number(b)-1e-6))return c;',
     ["ripple_revue_t7_une_autre_piste_dont_le_clip_commence_apres_le_trou_ne_bouge_pas",
      "e13_e14_coeur_pur_formateur_passe"]),
    # 9 — `DzmToolBar` sans `data-docked` : la feuille ne voit jamais l'ancrage.
    (B_EDIT, JS,
     '    "data-docked":o.docked===!0?"":void 0,\n',
     '',
     ["tbd_docked_true_pose_data_docked_vide",
      "e10_data_docked_ecrit_une_fois_dans_la_barre"]),
    # 10 — `saisir` sans la garde docked : ancree, la poignee enregistre un
    #      deport invisible qui reparait au desancrage (revue T4).
    (B_EDIT, JS,
     '    if(o.docked===!0)return;\n    if(e&&e.button!=null&&e.button!==0)return;\n',
     '    if(e&&e.button!=null&&e.button!==0)return;\n',
     ["e10_data_docked_ecrit_une_fois_dans_la_barre"]),
    # ── le bundle livre (sections du patcher), lu par `bundle` ───────────
    # 11 — EC1 : `dzFire` sans `bubbles`/`cancelable`. Le plan disait « si ca
    #      rougit » : ca rougit par le pin de la forme, PAS par un comportement
    #      (l'ecouteur est SUR window, la cible du dispatch : `bubbles` n'y
    #      change rien -- ecart date 23/09/2026).
    (B_BUND, BUN,
     'Object.assign({bubbles:!0,cancelable:!0},k)',
     'k',
     ["EC1_dzFire_rejoue_la_combo_vivante"]),
    # 12 — R_EB5A : le voile sans `dzMenu` : le menu ouvert n'a plus de voile,
    #      un clic a cote ne le ferme pas.
    (B_BUND, BUN,
     '(pop||dzFin||dzMenu)?r.jsx("div",{className:"svm-modescrim",onClick:function(){setPop("");setDzFin(null);setDzMenu(null)}}):null,',
     '(pop||dzFin)?r.jsx("div",{className:"svm-modescrim",onClick:function(){setPop("");setDzFin(null);setDzMenu(null)}}):null,',
     ["EC_l_etat_dzMenu_nait_dans_R_M16REF"]),
    # 13 — EC4 : le clic droit sur un clip sans `preventDefault` : le menu
    #      natif du navigateur s'ouvre par-dessus le notre.
    (B_BUND, BUN,
     'onContextMenu:function(e){e.preventDefault();e.stopPropagation();setSelId(c.id);',
     'onContextMenu:function(e){e.stopPropagation();setSelId(c.id);',
     ["EC4_EC5_clic_droit_clip_et_piste"]),
    # 14 — EC7 : `data-view` retire de la racine : la feuille ne masque plus
    #      la timeline en Medias / Livraison.
    (B_BUND, BUN,
     'ref:rootRef,"data-view":view,"data-svm-theme"',
     'ref:rootRef,"data-svm-theme"',
     ["EC7_la_racine_dzsvm_porte_data_view"]),
    # 15 — la feuille : `[data-docked]` sans `position:static` : la barre
    #      « ancree » flotte toujours au-dessus du bandeau.
    (B_BUND, CSS,
     '.dzsvm .dzm-tbar[data-docked]{position:static; bottom:auto;',
     '.dzsvm .dzm-tbar[data-docked]{bottom:auto;',
     ["E10_feuille_regles_separees_premiere_regle_intacte_docked_statique"]),
    # 16 — R_M16REF : l'effet de fetch sur `[view]` seul : renommer le projet
    #      en place laisse la vue Livraison sur l'ancien titre (revue T3).
    (B_BUND, BUN,
     '    return function(){alive=!1}}},[view,proj.name]);\n',
     '    return function(){alive=!1}}},[view]);\n',
     ["EC6_view_etat_de_session_sans_localStorage"]),
    # 17 — R_M16REF : `useEffect(...,[clips])` retire : le trou selectionne
    #      survit aux 55 `setClips(` (revue T5 : bornes perimees).
    (B_BUND, BUN,
     '  x.useEffect(function(){setGapSel(null)},[clips]);\n',
     '',
     ["E14_revue_le_trou_s_efface_quand_les_clips_changent"]),
    # 18 — EC13 : Suppr referme le trou SANS `pushHistory` : Ctrl+Z ne le
    #      rouvre pas.
    (B_BUND, BUN,
     '          pushHistory();setClips(DzTracks.trouRipple(clipsRef.current,gs.tr,gs.a,gs.b));',
     '          setClips(DzTracks.trouRipple(clipsRef.current,gs.tr,gs.a,gs.b));',
     ["E14_Suppr_referme_le_trou_avant_vpDel"]),
    # ── E-12, la regle d'audit (banc `ergonomie`, fichier = le bundle) ───
    # 19 — EC15b : `disabled:proj.demo` retire du bouton or « Reessayer » :
    #      sur la demo il redevient cliquable (regle 2).
    (B_ERGO, BUN,
     'r.jsx("button",{className:"svm-goldbtn",disabled:proj.demo,title:proj.demo?',
     'r.jsx("button",{className:"svm-goldbtn",title:proj.demo?',
     ["R2_bouton_or_du_popover_disabled_busy_ou_demo"]),
    # 20 — EC15d : un `title` retire (« Fermer le selecteur d'effets ») :
    #      le scanner de la regle 1 le trouve.
    (B_ERGO, BUN,
     'title:"Fermer le sélecteur d\'effets",onClick:function(){setFxPick(!1)},children:"Fermer"',
     'onClick:function(){setFxPick(!1)},children:"Fermer"',
     ["R1_bundle_tout_bouton_audite_porte_title",
      "R1_titre_pose_x1_Fermer_le_s"]),
]

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (3, 3, 1, 1, 2, 5, 2, 2, 2, 2, 1, 4, 6, 4, 5, 1, 2, 3, 4, 1, 2)
assert len(N_ROUGES) == len(M), (len(N_ROUGES), len(M))


def ecrire(p, data):
    """Ecrit les OCTETS, avec retentatives : MESURE le 23/09/2026, la
    RESTAURATION de la n°11 a leve `OSError: [Errno 22] Invalid argument` a
    l'ouverture du bundle (Windows, ouverture concurrente transitoire) et a
    laisse le bundle MUTE dans l'arbre -- le tour de bancs qui suivait a lu
    un faux bundle (2051/4). Cinq essais a 0,5 s ; au-dela, l'erreur remonte
    et le sha256 du `finally` accuse. Jamais un `git checkout`."""
    for essai in range(5):
        try:
            p.write_bytes(data)
            return
        except OSError:
            if essai == 4:
                raise
            time.sleep(0.5)


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
        ecrire(p, txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            ecrire(p, src)                        # application INVERSE, jamais git
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
