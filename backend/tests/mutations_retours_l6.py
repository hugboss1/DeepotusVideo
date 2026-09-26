# -*- coding: utf-8 -*-
"""Banc de mutations des RETOURS D'USAGE apres L6 (26/09/2026) : casser ->
rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_retours_l6.py            # toutes
    python tests/mutations_retours_l6.py 0 7 14     # celles-la
    python tests/mutations_retours_l6.py --pre-vol  # le pre-vol seul

PRE-VOL (modele L5, 24/09/2026) : avant toute mutation, `repatch_all.py
--list` doit rendre `montage` PUIS `dzcout` (ordre = mtime des `.bak_*`) ;
sinon sortie code 2, rien n'est mute.

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_l6.py` (5-uplets, mutation en OCTETS avec fin de
ligne MESUREE, `ecrire()` avec retentatives, sha256 restaure dans `finally`
par application inverse, etat MORT distinct de ROUGE).

CE QU'IL MUTE. Les retours du 26/09 vivent dans :
  . `sfx_service.py` (T1 : `_aecho`, le « mix » dose la part d'effet) ->
    banc `retours_sfx` ;
  . `montage_service.py` (T2 : musique bornee a son clip -> banc
    `retours_musique` ; T3 : `_cadre_of`, sémaphore de /grade-frame -> banc
    `retours_grade`) ;
  . `grading.py` (T3 : `_au_temps`, cle du cache) -> banc `retours_grade` ;
  . `frontend/patches/montage.js` : LA COUCHE jouee sous node (T4
    `DzmGradeLive` / `dzmGlBody`, T5 `DzmScopes` flottant) -> banc
    `edition` ; les bornes partagees (`dzmGlSec` / `dzmGlActif`, ratios,
    tailles) -> banc croise `retours_croise` ;
  . `scripts/patch_bundle_montage.py` (revue T2, I-2 : les textes de la
    musique bornee, sections R6mu*) : muter le patcher PUIS rejouer la chaine
    (`scripts/repatch_all.py --from montage`, cwd = racine), jouer le banc,
    RESTAURER le patcher puis rejouer la chaine ; le sha256 du patcher, du
    bundle ET du `.bak_dzcout` d'apres est compare a celui d'avant. Une
    chaine qui ne se rejoue pas (assert du patcher) = MORT, pas ROUGE ; quand
    un assert du patcher epingle le texte mute, la mutation porte AUSSI
    l'assert (liste de paires).
Le banc `bundle` n'est jamais choisi pour une mutation de la COUCHE (il
compare le bloc injecte a `montage.js` : le bruit noierait le signal).

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF), les motifs sont ecrits en LF et remis
dans la fin de ligne du fichier ; c'est le sha256 d'APRES qui prouve la
restauration. La restauration est une application INVERSE (les octets
d'avant reecrits), JAMAIS un `git checkout`. CHAQUE `ancien` DOIT EXISTER
EXACTEMENT UNE FOIS (assert avant l'ecriture). Un banc qui ne rend pas
`=== N passed, M failed ===` ou un code autre que 0/1 est MORT (faute n°6).

AUCUN reseau, AUCUNE depense : `retours_sfx`, `retours_musique` et
`retours_grade` jouent ffmpeg reel sur des sources lavfi generees en TMP ;
`retours_croise` et `edition` ne lancent ni ffmpeg ni serveur.

RESULTAT MESURE le 26/09/2026 (worktree epic-fermi-f6adf5, sommet 15d1ba7 +
bancs de cloture, python embarque, un processus par execution de banc,
campagne ENTIERE jouee deux fois : la premiere pour MESURER, la seconde pour
PROUVER) : LES VINGT-CINQ SONT ROUGES, AUCUN SURVIVANT, AUCUN MORT, chacune
sur les lignes declarees et au compte declare ; code de sortie 0 ; sha256 des
fichiers identiques avant / apres chaque mutation (patcher, bundle et
.bak_dzcout compris). 85 lignes rouges au total. Comptes des bancs au repos :
retours_sfx 26/0, retours_musique 31/0, retours_grade 47/0, edition 644/0,
bundle 2371/0, retours_croise 21/0.

    #   fonction visee                                    banc        rouges
    0   _AECHO_MARGE 0,5 au lieu de 0,25                  retours_sfx  4
    1   volume=4 retire (sec a -12 dB)                    retours_sfx  8
    2   mix ignore dans les decays                        retours_sfx  9
    3   adelay retire                                     musique      8
    4   apad retire                                       musique      8
    5   fondu de sortie sur la fin du RENDU               musique      3
    6   D non plafonne au total                           musique      2
    7   automation AVANT adelay                           musique      2
    8   bornes des effets ignorees (_au_temps)            grade        7
    9   cle du cache sans le cadre                        grade        7
   10   ratio sans garde de type (500)                    grade        2
   11   semaphore de /grade-frame retire                  grade        2
   12   t1 NaN « tout le plan » (cloture)                 grade        1
   13   DzmGradeLive : garde de lecture retiree           edition      2
   14   DzmGradeLive : rafale sans clearTimeout           edition      1
   15   dzmGlBody : image fixe acceptee                   edition      2
   16   DzmGradeLive : empreinte perimee affichee         edition      2
   17   DzmScopes : taille fixee suit le geste            edition      3
   18   DzmScopes : bascule sans finGeste                 edition      3
   19   DzmScopes : recadrage en plein geste              edition      1
   20   patcher : ancien texte de la musique restaure     bundle       1
   21   dzmGlActif : t1 NaN tout le plan                  croise       2
   22   dzmGlSec : « nan »/« inf » illisibles             croise       1
   23   DZM_GL_RATIOS + « 3:4 »                           croise       2
   24   dzmScwSize bornee a 2048                          croise       2

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  . la n°20 etait MORTE a la premiere passe : le motif restaurait le texte
    ENTIER de l'ancre A_R6MU5, que l'assert `a not in r` du patcher refuse
    (chaine interrompue, pas un rouge) ; le motif ne restaure plus que la
    moitie « sur toute la duree » (l'assert qui l'interdit est mute avec) ;
  . la n°0 ne rougit PAS `m8_aucun_ecretage_interne…` : avec une marge 0,5 le
    coin extreme (mix 100, fb 90, 20 ms) sur un bruit rose a -6 dBFS
    n'ecrete toujours pas EN INTERNE (mesure) — c'est la somme coherente
    (f5, 1 + 1 + 0,9 + 0,81 > 2) et la forme exacte (f1/f2) qui tiennent la
    marge 0,25, pas une mesure d'ecretage ;
  . la n°12 (lecture NaN du rendu, mesuree a la cloture) ne rougit QUE le
    check r2 rendu discriminant a la cloture (t_local < t0, t0 0, t0 NaN
    hors de [0, 1[) : avant la cloture, elle SURVIVAIT (w {t0 1, t1 NaN} a
    t_local 2 etait present des deux lectures) ;
  . la n°21 et la n°22 ne rougissent QUE le banc croise : `edition` ne
    joue aucune borne NaN — c'est la table partagee qui les tient.
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
SFX = "backend/app/services/sfx_service.py"
SVC = "backend/app/services/montage_service.py"
GRD = "backend/app/services/grading.py"
JS = "frontend/patches/montage.js"
PAT = "scripts/patch_bundle_montage.py"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
BAK = "frontend/dist/assets/index-BEOJX8L5.js.bak_dzcout"
B_SFX = "tests/test_retours_sfx.py"
B_MUS = "tests/test_retours_musique.py"
B_GRD = "tests/test_retours_grade.py"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"
B_CROI = "tests/test_retours_croise.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, lignes rouges attendues)
M = [
    # -- T1 : sfx_service.py, joue par `retours_sfx` ------------------------------
    # 0 -- marge 0,5 au lieu de 0,25 : `aecho` ecrete EN INTERNE au coin extreme
    #      (1 + 1 + 0,9 + 0,81 > 2) ; le sec reste a 1 (0,5 x 2).
    (B_SFX, SFX,
     '_AECHO_MARGE = 0.25\n',
     '_AECHO_MARGE = 0.5\n',
     ['f5_marge_interne_somme_coherente_sous_1',
      'f1_echo_du_projet_forme_exacte']),
    # 1 -- `volume=4` retire : le sec retombe a 0,25 (-12 dB).
    (B_SFX, SFX,
     '            f",volume={_g(1.0 / h)}")\n',
     '            "")\n',
     ['f3_sec_exactement_1_pour_tout_mix',
      'm1_sec_preserve_0_5_db_mix_22_55_100_echo_et_reverbe']),
    # 2 -- le mix ignore : la part d'effet ne suit plus le reglage.
    (B_SFX, SFX,
     'h * mix * r)) for r in taps]',
     'h * r)) for r in taps]',
     ['f6_part_d_effet_strictement_croissante_avec_mix',
      'm3_part_d_effet_mesuree_strictement_croissante']),
    # -- T2 : montage_service.py, joue par `retours_musique` ----------------------
    # 3 -- `adelay` retire : la musique d'un clip 5-15 s demarre a 0.
    (B_MUS, SVC,
     'f"adelay={mdly}|{mdly},{mautom}"',
     'f"{mautom}"',
     ['b_bornes_degenerees_historique_temoin_bornees',
      'b_chaine_bornee_exacte']),
    # 4 -- `apad` retire : le flux musique s'arrete a la fin du clip (la chaine
    #      laterale du ducking et amix voient un flux court).
    (B_MUS, SVC,
     'f"apad=whole_dur={round(total, 3)}[mtrk]")',
     'f"anull[mtrk]")',
     ['rA_flux_aussi_long_que_le_rendu',
      'rG_flux_aussi_long_que_le_rendu_avec_ducking']),
    # 5 -- fondu de sortie cale sur la fin du RENDU (l'ancien texte).
    (B_MUS, SVC,
     'mref = max(0.0, total) if mdur is None else mdur',
     'mref = max(0.0, total)',
     ['b_chaine_bornee_exacte',
      'b_fondus_bornes_a_la_duree_du_clip']),
    # 6 -- D non plafonne au total : `end` 1e20 -> `atrim=0.0:1e+20`, refuse par ffmpeg.
    (B_MUS, SVC,
     '                b_d = min(b_d, max(0.1, total - b_st))\n',
     '                b_d = b_d\n',
     ['rI_end_1e20_plafonne_au_total_rc0',
      'rK_end_infini_start_respecte_plafonne_au_total_src_in_infini_absent']),
    # 7 -- automation posee AVANT adelay (horloge locale au lieu de globale).
    (B_MUS, SVC,
     [('f"[{idx}:a]{mtrim}{mproc}{mf}"', 'f"[{idx}:a]{mtrim}{mproc}{mf}{mautom}"'),
      ('f"adelay={mdly}|{mdly},{mautom}"', 'f"adelay={mdly}|{mdly},"')],
     None,
     ['b_chaine_bornee_exacte',
      'rF_automation_en_temps_global']),
    # -- T3 : grading.py / montage_service.py, joue par `retours_grade` -----------
    # 8 -- bornes des effets ignorees en mode cadre : un effet borne [5,6] montre partout.
    (B_GRD, GRD,
     'if t1 - t0 < 0.05 or t0 <= t_local < t1:',
     'if True:',
     ['r2_au_temps_t0_inf_tout_le_plan_nan_comme_le_rendu_mesure',
      'r2_bornes_comme_le_rendu_t1_borne_a_dur_intervalle_court_plein_sans_borne_plein_off_eteint']),
    # 9 -- cle du cache SANS le cadre : deux cadres differents servent la meme image.
    (B_GRD, GRD,
     '        cle.append({"cadre": cadre})\n',
     '        pass\n',
     ['r2_cache_cle_porte_le_cadre_second_appel_sans_sous_processus',
      'r2_cadre_quatre_ratios_dimensions_du_canvas']),
    # 10 -- ratio sans garde de type : une liste n'est pas hachable -> 500.
    (B_GRD, SVC,
     'ratio = r if isinstance(r, str) and r in _CANVAS else "9:16"',
     'ratio = r if r in _CANVAS else "9:16"',
     ['r2_cadre_ratio_liste_objet_booleen_nul_nombre_200_en_9_16',
      'r2_cadre_types_inattendus_jamais_500_sur_les_deux_routes_88_cas']),
    # 11 -- semaphore de /grade-frame retire : cinq calculs a la fois.
    (B_GRD, SVC,
     '        async with _grade_sem():\n',
     '        if True:\n',
     ['r4_grade_frame_deux_au_plus_sur_deux_boucles_temoin_nu_cinq',
      'r4_troisieme_part_des_la_premiere_place_libre_client_parti_499_sans_calcul']),
    # 12 -- (cloture) t1 NaN « tout le plan » (l'ancienne lecture) : l'apercu montre
    #       un effet que le rendu n'allume qu'a t0 (ou jamais).
    (B_GRD, GRD,
     '            if t0 > 0 and t_local >= t0:\n                res.append(e)\n',
     '            res.append(e)\n',
     ['r2_au_temps_t0_inf_tout_le_plan_nan_comme_le_rendu_mesure']),
    # -- T4 : la couche, DzmGradeLive / dzmGlBody, jouee par `edition` -------------
    # 13 -- garde de lecture retiree : une requete part pendant la lecture.
    (B_EDIT, JS,
     'var c=o.playing?null:dzmScopesAt(o.clips,o.head),body=c?dzmGlBody(',
     'var c=dzmScopesAt(o.clips,o.head),body=c?dzmGlBody(',
     ['r6_en_lecture_aucun_minuteur_aucune_requete_aucune_image_aucun_bouton',
      'r6_la_lecture_repart_requete_abandonnee_minuteur_annule_reponse_tardive_jetee']),
    # 14 -- rafale : le minuteur de l'etat precedent n'est plus annule.
    (B_EDIT, JS,
     'function(){})},DZM_GL_MS);\n    return function(){seq.current++;clearTimeout(h);',
     'function(){})},DZM_GL_MS);\n    return function(){seq.current++;',
     ['r6_rafale_de_positions_un_seul_minuteur_vivant_une_seule_requete_a_la_derniere_position']),
    # 15 -- image fixe : un V1 en image demande grade-frame (415 a chaque arret).
    (B_EDIT, JS,
     '||c.src.image)return null;',
     ')return null;',
     ['r6_m3_actif_comme_effects_engine_timed_intervalle_t1_exclu_t1_borne_a_dur_moins_de_5_centiemes_tout_le_plan_bornes_illisibles_tout_le_plan',
      'r6_m3_effet_borne_hors_de_son_intervalle_ni_requete_ni_pastille_m4_image_fixe_rien_dedans_une_requete']),
    # 16 -- empreinte perimee : l'image d'un autre instant reste affichee.
    (B_EDIT, JS,
     'var voit=!!(sig&&img&&img.sig===sig),z=',
     'var voit=!!(sig&&img),z=',
     ['r6_refus_415_et_panne_reseau_silence_rien_d_affiche_aucune_ligne_d_etat',
      'r6_tete_deplacee_image_perimee_masquee_aussitot_nouvelle_requete_au_nouvel_instant']),
    # -- T5 : la couche, DzmScopes flottant, jouee par `edition` -------------------
    # 17 -- la taille FIXEE suit le geste : une requete par mouvement du pointeur.
    (B_EDIT, JS,
     'setGeo({x:n.x,y:n.y,s:n.s,f:f0})',
     'setGeo({x:n.x,y:n.y,s:n.s,f:n.s})',
     ['r6s_redimensionner_au_relacher_memorise_puis_une_requete_a_la_nouvelle_taille_image_remplacee',
      'r6s_redimensionner_carre_borne_racine_pendant_le_geste_image_gardee_aucun_minuteur_aucune_requete']),
    # 18 -- la bascule (« × » ou la puce) ne finit plus le geste en cours.
    (B_EDIT, JS,
     'if(!n){finGeste();seq.current++;',
     'if(!n){seq.current++;',
     ['r6s_revue_m1a_croix_en_plein_geste_abandonne_le_geste_rien_memorise_meme_au_relacher_ecouteurs_otes',
      'r6s_revue_m1b_second_pointerdown_abandonne_le_premier_ecouteurs_non_doubles_seul_le_second_memorise']),
    # 19 -- recadrage au redimensionnement du navigateur EN PLEIN geste.
    (B_EDIT, JS,
     'function(){if(gesteR.current)return;var W=',
     'function(){var W=',
     ['r6s_revue_m3_navigateur_retreci_en_plein_geste_aucun_recadrage_ni_minuteur_recadre_dans_la_racine_courante_au_relacher']),
    # -- revue T2 (I-2) : le patcher, joue par `bundle` apres la chaine --------------
    # 20 -- un ANCIEN texte restaure (la note de l'inspecteur redit « sur toute la duree »)
    #       + l'assert du patcher qui l'interdisait.
    (B_BUND, PAT,
     [("R_R6MU5 = 'children:\"musique bouclée dans les bornes de son clip — fondu de sortie calé sur la fin du clip\"'",
       "R_R6MU5 = 'children:\"musique bouclée sur toute la durée — fondu de sortie calé sur la fin du clip\"'"),
      ('"fin de rendu" not in r and "sur toute la durée" not in r', '"fin de rendu" not in r')],
     None,
     ['R6mu_anciens_textes_a_0_nouveaux_a_1_temoin_le_bak_porte_les_anciens']),
    # -- cloture : les bornes partagees, jouees par `retours_croise` ---------------------
    # 21 -- dzmGlActif : t1 NaN « tout le plan » cote client (le serveur dit [t0, inf)).
    (B_CROI, JS,
     'if(b!==b)return a>0&&tl>=a;',
     'if(b!==b)return !0;',
     ['x1_service_couche_et_attendu_egaux_sur_toute_la_table_aucune_divergence',
      'x1_temoin_jeton_nan_decode_en_natif_des_deux_cotes']),
    # 22 -- dzmGlSec ne lit plus « nan » / « inf » comme float() (chaine -> illisible).
    (B_CROI, JS,
     'if(m)return m[2].toLowerCase()==="nan"?NaN:',
     'if(m)return null;if(0)return m[2].toLowerCase()==="nan"?NaN:',
     ['x1_service_couche_et_attendu_egaux_sur_toute_la_table_aucune_divergence']),
    # 23 -- un ratio que le rendu ne connait pas dans la liste du client.
    (B_CROI, JS,
     'DZM_GL_RATIOS=["9:16","16:9","1:1","4:5"]',
     'DZM_GL_RATIOS=["9:16","16:9","1:1","4:5","3:4"]',
     ['x4_les_ratios_du_client_sont_ceux_du_canvas_du_rendu',
      'x4_repli_du_client_egal_au_repli_de_cadre_of']),
    # 24 -- taille des scopes du client bornee a 2048 (le serveur a 1024).
    (B_CROI, JS,
     'return Math.max(256,Math.min(1024,Math.round(s*d/2)*2))}',
     'return Math.max(256,Math.min(2048,Math.round(s*d/2)*2))}',
     ['x3_taille_des_scopes_min_max_du_client_egaux_au_serveur_defaut_du_client_dit',
      'x3_toute_largeur_et_toute_taille_du_client_est_un_point_fixe_du_serveur']),
]

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (4, 8, 9, 8, 8, 3, 2, 2, 7, 7, 2, 2, 1, 2, 1, 2, 2, 3, 3, 1, 1, 2, 1, 2, 2)
assert len(N_ROUGES) == len(M), (len(N_ROUGES), len(M))

# Les fichiers dont le sha256 doit revenir a l'identique apres une mutation du
# PATCHER : le patcher lui-meme, le bundle et le point de chaine aval.
CHAINE = (PAT, BUN, BAK)


def ecrire(p, data):
    """Ecrit les OCTETS, avec retentatives : MESURE le 23/09/2026 (banc E-C),
    une restauration a leve `OSError: [Errno 22] Invalid argument` a
    l'ouverture du bundle (Windows, ouverture concurrente transitoire) et a
    laisse le bundle MUTE dans l'arbre. Cinq essais a 0,5 s ; au-dela,
    l'erreur remonte et le sha256 du `finally` accuse. Jamais un `git
    checkout`."""
    for essai in range(5):
        try:
            p.write_bytes(data)
            return
        except OSError:
            if essai == 4:
                raise
            time.sleep(0.5)


def sha(rel):
    """sha256 des octets, avec retentatives de lecture (meme piege qu'`ecrire`)."""
    for essai in range(5):
        try:
            return hashlib.sha256((R / rel).read_bytes()).hexdigest()
        except OSError:
            if essai == 4:
                raise
            time.sleep(0.5)


def chaine():
    """Rejoue la chaine des patchers depuis `montage` (cwd = racine). (ok, sortie)."""
    r = subprocess.run([PY, "scripts/repatch_all.py", "--from", "montage"], capture_output=True,
                       cwd=R, timeout=600)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r.returncode == 0 and "OK" in txt, txt


def rouges(banc):
    """Les noms des lignes ROUGES du banc, sa sortie, et un drapeau d'ERREUR.

    Le banc rend 0 (tout vert) ou 1 (des rouges) ; tout autre code veut dire
    qu'il est MORT au lieu de rougir -- la faute n°6 du chantier -- et l'on
    rend un troisieme etat plutot que de lire une liste vide comme « rien
    casse ».
    """
    try:
        r = subprocess.run([PY, banc], capture_output=True,
                           cwd=R / "backend", timeout=1800)
    except subprocess.TimeoutExpired as e:
        return set(), "TIMEOUT du banc : %r" % e, True
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    erreur = r.returncode not in (0, 1) or "=== " not in txt
    return set(re.findall(r"^  FAIL  (\S+)", txt, re.M)), txt, erreur


def pre_vol():
    """PRE-VOL DE LA CHAINE : `repatch_all.py --list` doit rendre `montage`
    PUIS `dzcout`, chacun avec son script.

    L'ordre de la chaine est celui du MTIME des `.bak_*` (repatch_all.chain) :
    des `.bak` copies sans leur date (copie simple, worktree neuf) peuvent
    l'inverser ; alors `--from montage` ne rejoue plus `dzcout`, et la
    restauration d'une mutation du PATCHER laisse le bundle MODIFIE (le
    sha256 du `finally` accuse, mais apres coup). On refuse donc AVANT toute
    mutation. Rend (ok, message)."""
    r = subprocess.run([PY, "scripts/repatch_all.py", "--list"], capture_output=True,
                       cwd=R, timeout=120)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    if r.returncode != 0:
        return False, "repatch_all.py --list a rendu le code %d :\n%s" % (r.returncode, txt)
    lignes = [l.split() for l in txt.splitlines() if l.strip()]
    tags = [l[0] for l in lignes]
    sans = [l[0] for l in lignes if len(l) < 2 or l[1] != "OK"]
    if "montage" not in tags or "dzcout" not in tags:
        return False, "chaine sans `montage` ou sans `dzcout` : %s" % tags
    if tags.index("montage") > tags.index("dzcout"):
        return False, ("chaine INVERSEE (mtime des .bak_*) : %s -- `dzcout` passe "
                       "avant `montage` ; retablir le mtime des .bak avant toute "
                       "mutation" % tags)
    if sans:
        return False, "maillon(s) sans script : %s" % sans
    return True, "chaine %s : montage puis dzcout, OK" % " -> ".join(tags)


def main():
    seuls = [a for a in sys.argv[1:] if not a.startswith("--")]
    bilan = []
    for i, (banc, rel, old, new, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        est_patcher = rel == PAT
        src = p.read_bytes()                      # OCTETS, jamais read_text
        avant = {f: sha(f) for f in ((rel,) + (CHAINE if est_patcher else ()))}
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
        mort_chaine = ""
        try:
            if est_patcher:
                ok_c, sortie_c = chaine()
                if not ok_c:
                    mort_chaine = sortie_c[-1500:]
            if mort_chaine:
                rg, sortie, erreur = set(), mort_chaine, True
            else:
                rg, sortie, erreur = rouges(banc)
        finally:
            ecrire(p, src)                        # application INVERSE, jamais git
            if est_patcher:
                ok_r, sortie_r = chaine()         # le bundle et le .bak_dzcout d'avant
                assert ok_r, (i, "la chaine ne se rejoue pas a la restauration", sortie_r[-800:])
            apres = {f: sha(f) for f in avant}
            assert apres == avant, (i, rel, avant, apres)
        manquants = sorted(a for a in attendus
                           if not any(a in x for x in rg))
        if erreur:
            verdict = "MORT(pas rouge)"
            print(sortie[-1500:], file=sys.stderr)
        elif not rg:
            verdict = "SURVIVANT"
        elif manquants:
            verdict = "ROUGE(autres)"
        elif len(rg) not in (N_ROUGES[i] if isinstance(N_ROUGES[i], tuple) else (N_ROUGES[i],)):
            verdict = "ROUGE(compte)"
        else:
            verdict = "ROUGE"
        bilan.append((i, verdict, sorted(rg), manquants))
        print(f"[{i:2d}] {verdict:16s} {banc.split('_', 2)[-1][:-3]:11s} "
              f"{pathlib.Path(rel).name:24s} {paires[0][0].strip()[:40]!r}")
        print(f"     rouges({len(rg)}/{N_ROUGES[i]})={sorted(rg)}")
        if manquants:
            print(f"     MANQUANTS={manquants}")
        print("     sha " + " ".join(f"{pathlib.Path(f).name}:{avant[f][:10]}={apres[f][:10]}" for f in avant))
        sys.stdout.flush()
    print(json.dumps([b[:2] for b in bilan], ensure_ascii=False))
    # LU PAR CODE DE SORTIE, jamais par grep : 1 des qu'une mutation survit,
    # meurt, rougit ailleurs que la ligne nommee ou plus/moins que N_ROUGES.
    sys.exit(0 if bilan and all(v == "ROUGE" for _, v, _, _ in bilan) else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ok_pv, msg_pv = pre_vol()
    print("PRE-VOL : " + msg_pv)
    if not ok_pv:
        sys.exit(2)                               # AVANT toute mutation
    if "--pre-vol" in sys.argv:                   # s'arreter apres le pre-vol
        sys.exit(0)
    main()
