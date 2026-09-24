# -*- coding: utf-8 -*-
"""Banc de mutations du lot L5 du Montage (couleur) : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l5.py            # toutes
    python tests/mutations_montage_l5.py 0 7 14     # celles-la
    python tests/mutations_montage_l5.py --pre-vol  # le pre-vol seul

PRE-VOL (revue finale, 24/09/2026) : avant toute mutation, `repatch_all.py
--list` doit rendre `montage` PUIS `dzcout` (ordre = mtime des `.bak_*`) ;
sinon sortie code 2, rien n'est mute.

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_l7b.py` (5-uplets, mutation en OCTETS avec fin de
ligne MESUREE, `ecrire()` avec retentatives, sha256 restaure dans `finally`
par application inverse, etat MORT distinct de ROUGE).

CE QU'IL MUTE. Le lot L5 (D-27 roues, D-28 accord, D-29 courbes et
teinte/saturation, D-30 masque, D-31 scopes, D-32 copier/coller du grade et
lightbox, D-33 effets) vit dans :
  . `effects_engine.py` (constructeurs, `curves_clean`, `_c`, l'enveloppe
    `_timed`) -> banc `l5` [1] ; l'enveloppe au format de l'overlay V2 ->
    banc `l5_masque` ;
  . `mask_region.py` et la chaine V1 / l'overlay V2 de `montage_service.py`
    -> banc `l5_masque` (rendus REELS : 90 s au plus par rendu, borne de
    temps du banc lui-meme -- un graphe qui ne finit pas ROUGIT au lieu de
    bloquer) ;
  . `grading.py` et les trois routes de `montage_service.py` -> banc `l5`
    [4] [7] ;
  . `frontend/patches/montage.js` : LA COUCHE jouee sous node par le shim
    de `test_montage_edition.py` (coeur pur, panneau Etalonnage) -> banc
    `edition` ;
  . `scripts/patch_bundle_montage.py` : LE PATCHER, pour ce qui vit dans le
    corps reecrit du bundle (payload V1 `mask`, garde modale de la
    lightbox, combo de `grade_copy`). DEMANDE DU CONTROLEUR (24/09/2026) :
    muter le patcher PUIS rejouer la chaine (`scripts/repatch_all.py --from
    montage`, cwd = racine), jouer le banc, RESTAURER le patcher puis
    rejouer la chaine ; le sha256 du patcher, du bundle ET du
    `.bak_dzcout` d'apres est compare a celui d'avant. Une chaine qui ne se
    rejoue pas (assert du patcher) = MORT, pas ROUGE. Quand un assert du
    patcher epingle le texte mute, la mutation porte AUSSI l'assert (liste
    de paires) : sinon la chaine meurt et rien n'est juge ;
  . `frontend/dist/shared/montage.css` (encart des scopes) -> banc `bundle`
    qui la lit telle quelle (aucune chaine a rejouer).
Le banc `bundle` n'est jamais choisi pour une mutation de la COUCHE : il
compare le bloc injecte a `montage.js`, toute mutation de la couche l'y
ferait rougir et le bruit noierait le signal.

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF), les motifs sont ecrits en LF et remis
dans la fin de ligne du fichier ; c'est le sha256 d'APRES qui prouve la
restauration, pas cette phrase. Mesure du 24/09/2026 (sommet 76987ad,
worktree charming-nash-c82726, autocrlf) : `effects_engine.py`,
`montage_service.py`, la couche, le patcher, `montage.css` et le bundle en
CRLF (homogenes) ; `mask_region.py` et `grading.py` en LF. La restauration
est une application INVERSE (les octets d'avant reecrits), JAMAIS un `git
checkout`.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
Un banc qui ne rend pas `=== N passed, M failed ===` ou un code autre que
0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

AUCUN reseau, AUCUNE depense : les bancs `l5` et `l5_masque` jouent ffmpeg
et PIL reels sur des sources lavfi generees en TMP.

RESULTAT MESURE le 24/09/2026 (worktree charming-nash-c82726, sommet
76987ad + bancs de cloture, python embarque, un processus par execution de
banc, campagne ENTIERE jouee deux fois : la premiere pour MESURER, la
seconde pour PROUVER) : voir la table -- LES VINGT SONT ROUGES, AUCUN
SURVIVANT, AUCUN MORT, chacune sur les lignes declarees et au compte
declare ; code de sortie 0 ; sha256 des fichiers identiques avant / apres
chaque mutation (patcher, bundle et .bak_dzcout compris).
Comptes des bancs au repos : l5 109/0, l5_masque 60/0, edition 557/0,
bundle 2294/0, l5_croise 36/0. 51 lignes rouges au total.

    #   fonction visee                                    banc       rouges
    0   colormatch non pivote (val*G+O)                   l5         7
    1   curves_clean : le PREMIER x duplique gagne        l5         2
    2   _c sans controle hexa (longueur seule)            l5         3
    3   V2 : copie opaque lutrgb=a=255 retiree            l5_masque  5
    4   _timed en yuv420p pour V2 (fmt ignore)            l5_masque  3
    5   V1 masque sans shortest=1 (ceinture, voir dessous) l5_masque 1
    6   mask_graph : min() a trois arguments              l5_masque  5
    7   _probe sans le tag DURATION (mkv/webm)            l5         1
    8   recul fixe 0,1 s sans second essai                l5         2
    9   os.replace non protege (cible ouverte)            l5         1
   10   dzmGradeTake emporte un effet off                 edition    5
   11   dzmCurveClean : jeton invalide => tout invalide   edition    2
   12   pchip : moyenne arithmetique des pentes           edition    2
   13   geste du panneau sans garde d'id du plan          edition    1
   14   patcher : payload V1 sans mask                    bundle     2
   15   patcher : garde modale de la lightbox retiree     bundle     2
   16   css : .dzm-scimg en pointer-events:auto           bundle     1
   17   /scopes sans semaphore                            l5         1
   18   patcher : grade_copy sur Ctrl+Maj+C (reservee)    l5_croise  3
   19   /grade-frame lit `width` au lieu de `w`           l5_croise  2

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  . la n°5 ne rougit QUE la ligne de FORME : EQUIVALENCE PROUVEE PAR LA
    MESURE (24/09/2026, ffmpeg 9.0.1 de l'app, graphe du service rejoue a la
    main) -- la commande du Montage porte TOUJOURS `-t total` en sortie
    (`montage_service`, « coupée par `-t total` comme tout le reste ») :
    sans `shortest=1`, un plan masque seul rend 50 images en 0,22 s, deux
    plans (masque puis rouge, xfade) 99 images, le rouge a 3 s, comme avec ;
    SANS `-t` ET sans `shortest=1`, le graphe ne finit pas (TIMEOUT 25 s),
    avec `shortest=1` seul il finit. `shortest=1` est donc une CEINTURE
    sous le `-t` du rendu -- la mesure de T2 (« sans lui le graphe ne finit
    jamais ») valait pour un graphe SANS `-t`. Ecart date dans la
    conception ; la mutation reste au banc (elle garde la forme) ;
  . les n°18 et 19 etaient ROUGE(autres) a la premiere passe : deux TROUS du
    banc croise, combles avant son premier commit (voir son en-tete) --
    la ligne « absentes de SVM_COMBO_RESERVED » ne lisait que le LITTERAL
    Ctrl+Alt+C (ligne des combos EFFECTIVES ajoutee) ; la sonde envoyait
    w=240, le DEFAUT de la route, et l'espion ne voyait pas `width` (320) ;
  . la n°0 rougit sept lignes : la forme, deux rendus reels du moteur et
    quatre lignes de l'ACCORD (color_match compte sur la forme pivotee) ;
  . la n°3 rougit les lignes « alpha d'origine 128/0/255 » sans masque de
    trois effets (grade_basic neutre, curves, invert) : c'est l'alpha AU
    CARRE, mesure en rendu reel ;
  . la n°14 (patcher) rougit la ligne JOUEE sous node du banc bundle
    (masque joint au payload V1) et le pin de R_DZ4 : l'assert du patcher,
    qui ne voit que le sous-texte `maskOf(c.mask);if(mkD)o.mask=mkD;`, ne
    l'arrete pas -- c'est le banc qui juge.
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
EE = "backend/app/services/effects_engine.py"
MRG = "backend/app/services/mask_region.py"
GRD = "backend/app/services/grading.py"
SVC = "backend/app/services/montage_service.py"
JS = "frontend/patches/montage.js"
CSS = "frontend/dist/shared/montage.css"
PAT = "scripts/patch_bundle_montage.py"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
BAK = "frontend/dist/assets/index-BEOJX8L5.js.bak_dzcout"
B_L5 = "tests/test_montage_l5.py"
B_MSK = "tests/test_montage_l5_masque.py"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"
B_CROI = "tests/test_montage_l5_croise.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, lignes rouges attendues)
M = [
    # -- T1 : effects_engine.py, joue par `l5` [1] -----------------------------
    # 0 -- colormatch NON pivote : `val*G+O` agit autour de 0 sur U/V et teinte
    #      un gris neutre des que G != 1 (le defaut corrige en revue T1).
    (B_L5, EE,
     '        parts.append(f"{p}=\'clip((val-128)*{g:.3f}+128{off:+.3f},0,255)\'")\n',
     '        parts.append(f"{p}=\'clip(val*{g:.3f}{off:+.3f},0,255)\'")\n',
     ['t1_colormatch_pivote_128']),
    # 1 -- curves_clean : le PREMIER x duplique gagne (la regle dit le dernier).
    (B_L5, EE,
     '        pts[x] = y\n',
     '        pts.setdefault(x, y)\n',
     ['t1_cc_x_duplique_dernier_gagne']),
    # 2 -- `_c` sans controle hexa : « ;[x]ab » (6 caracteres) part tel quel
    #      dans le -filter_complex (injection).
    (B_L5, EE,
     '    if len(s) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in s):\n',
     '    if len(s) != 6:\n',
     ['t1_couleur_hexa_stricte']),
    # -- T2 : l'overlay V2 et le masque, joues par `l5_masque` -----------------
    # 3 -- la pile V2 recoit l'alpha d'origine (copie OPAQUE retiree) : alpha
    #      AU CARRE pour ~28 effets.
    (B_MSK, SVC,
     '                parts.append(f"[ofs{j}]lutrgb=a=255[ofa{j}]")\n',
     '                parts.append(f"[ofs{j}]null[ofa{j}]")\n',
     ['v2_pile_recoit_une_copie_opaque_lutrgb_a_255']),
    # 4 -- `_timed` en yuv420p quel que soit l'appelant : l'overlay V2 perd
    #      alpha et chroma HORS de la fenetre t0/t1.
    (B_MSK, EE,
     '    fmt = (ctx or {}).get("fmt") or "yuv420p"\n',
     '    fmt = "yuv420p"\n',
     ['i2_fmt_gbrap_enveloppe_sans_yuv420p']),
    # 5 -- V1 masque SANS `shortest=1` : sans `-t` le graphe ne finirait pas
    #      (masque boucle) ; le banc borne chaque rendu a 90 s (TIMEOUT rouge,
    #      jamais bloque). Sous le `-t total` du rendu : CEINTURE (en-tete).
    (B_MSK, SVC,
     '                parts.append(f"[mo{k}][mm{k}]overlay=0:0:shortest=1,"\n',
     '                parts.append(f"[mo{k}][mm{k}]overlay=0:0,"\n',
     ['v1_effets_et_masque_split_alphamerge_overlay_shortest']),
    # 6 -- mask_graph : `min()` a TROIS arguments (ffmpeg n'en accepte que deux :
    #      « Error initializing filters »).
    (B_MSK, MRG,
     '        e = (f"255*clip(min(min(X-{_n(x0)},{_n(x1)}-X),min(Y-{_n(y0)},{_n(y1)}-Y))"\n',
     '        e = (f"255*clip(min(X-{_n(x0)},{_n(x1)}-X,min(Y-{_n(y0)},{_n(y1)}-Y))"\n',
     ['v1_rectangle_net_centre_assombri_coin_intact']),
    # -- T3 : grading.py, joue par `l5` [4] ------------------------------------
    # 7 -- `_probe` sans le tag DURATION : en .mkv/.webm la duree retombe sur
    #      celle du CONTENEUR (audio plus long) et `-ss` tombe hors video.
    (B_L5, GRD,
     '        dur = (_num(s.get("duration")) or _tag_duree(s)\n',
     '        dur = (_num(s.get("duration"))\n',
     ['t4_mkv_webm_duree_du_flux_par_tag_temoins_nus_vides']),
    # 8 -- recul FIXE de 0,1 s et pas de second essai : a 5 i/s, 1,85 s ne rend
    #      rien (mesure) et l'echec muet devient une MediaError.
    (B_L5, GRD,
     [('    return max(_RECUL, 1.0 / fps) if fps > 0 else _RECUL\n',
       '    return _RECUL\n'),
      ('    essais = [t] + ([max(0.0, t - pas)] if pas > 0 and t > 0 else [])\n',
       '    essais = [t]\n')],
     None,
     ['t4_fin_lisible_5ips_et_audio_plus_long_temoins_nus_vides',
      't4_second_essai_seul_rend_quand_le_premier_est_muet']),
    # 9 -- `os.replace` non protege : sous Windows une cible ouverte en lecture
    #      (FileResponse) leve WinError 5 et l'apercu echoue.
    (B_L5, GRD,
     '    except OSError as e:\n'
     '        _efface(tmp)\n'
     '        if not out.exists():\n',
     '    except ZeroDivisionError as e:\n'
     '        _efface(tmp)\n'
     '        if not out.exists():\n',
     ['t4_cible_ouverte_en_lecture_rerendu_sans_erreur_ni_tmp']),
    # -- T4 : la couche, jouee par `edition` [36] -------------------------------
    # 10 -- dzmGradeTake emporte un effet `off` (et le RALLUME : la copie
    #       retire la cle off).
    (B_EDIT, JS,
     'var es=(Array.isArray(clip.effects)?clip.effects:[]).filter(dzmIsGradeEff).map(dzmGradeEffCopy),mk=dzmMaskOf(clip.mask);',
     'var es=(Array.isArray(clip.effects)?clip.effects:[]).filter(dzmIsColorEff).map(dzmGradeEffCopy),mk=dzmMaskOf(clip.mask);',
     ['co_take_sans_t0_ni_off_ni_grain', 'co_paste_off_effet_eteint_ni_emporte']),
    # 11 -- dzmCurveClean : un jeton invalide rend TOUTE la courbe invalide
    #       (curves_clean le saute et garde les autres).
    (B_EDIT, JS,
     '    if(!q)continue;\n',
     '    if(!q)return DZM_CURVE_ID;\n',
     ['co_clean_regles_de_curves_clean', 'co_vec_regle_unique_des_courbes']),
    # 12 -- pchip : moyenne ARITHMETIQUE des pentes (Fritsch-Carlson dit
    #       harmonique ponderee) : depassement entre deux points.
    (B_EDIT, JS,
     'm[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])',
     'm[i]=(d[i-1]+d[i])/2',
     ['co_eval_exact_pchip_epinglee_au_1e_6']),
    # -- T5 : le panneau, joue par `edition` [37] -------------------------------
    # 13 -- le geste d'une roue / d'une courbe ecrit sur le plan SELECTIONNE
    #       au lieu du plan SAISI (garde d'id retiree).
    (B_EDIT, JS,
     'if(!vivant.current||cur.current.id!==id)return;ecrire(cx,cy)',
     'if(!vivant.current)return;ecrire(cx,cy)',
     ['l5x_gp_I2_geste_ecrit_dans_le_plan_saisi']),
    # -- T5 : le patcher (payload V1), joue par `bundle` apres la chaine --------
    # 14 -- le payload de rendu V1 ne porte plus `mask` : le masque ne sort
    #       jamais du client (l'assert du patcher garde son sous-texte).
    (B_BUND, PAT,
     "         '        var mkD=o.effects&&c.src&&trackKind(c.tr)===\"video\"&&DzTracks.maskOf(c.mask);if(mkD)o.mask=mkD;')\n",
     "         '        var mkD=!1&&o.effects&&c.src&&trackKind(c.tr)===\"video\"&&DzTracks.maskOf(c.mask);if(mkD)o.mask=mkD;')\n",
     ['L5gp_masque_au_payload_dans_R_DZ4', 'L5gp_sous_node_masque_joint_sur_V1']),
    # -- T6 : le patcher (clavier) et la css, joues par `bundle` ----------------
    # 15 -- la lightbox n'est plus MODALE au clavier : seul Echap est pris,
    #       Espace / Suppr / Ctrl+Z passent sous le voile (+ l'assert).
    (B_BUND, PAT,
     [("R_K7 = ('if(dzLbRef.current){if(e.key===\"Escape\"){e.preventDefault();setDzLb(!1)}return}'",
       "R_K7 = ('if(dzLbRef.current&&e.key===\"Escape\"){e.preventDefault();setDzLb(!1);return}'"),
      ("R_K7.count('if(dzLbRef.current){if(e.key===\"Escape\"){e.preventDefault();setDzLb(!1)}return}') == 1"
       " and R_K7.startswith(\"if(dzLbRef.current){\")",
       "R_K7.startswith(\"if(dzLbRef.current&&\")")],
     None,
     ['L5_T6_I1_lightbox_modale_au_clavier']),
    # 16 -- l'image des scopes capte le pointeur : poignees d'overlay et
    #       rectangles du coin haut droit inatteignables (re-revue 4bda880).
    (B_BUND, CSS,
     'border:1px solid #ffffff33;background:#000;pointer-events:none}',
     'border:1px solid #ffffff33;background:#000;pointer-events:auto}',
     ['L5_css_scopes_puce_dans_la_barre']),
    # -- restes backend : /scopes, joue par `l5` [7] ----------------------------
    # 17 -- /scopes sans semaphore : cinq arrets de tete = cinq ffmpeg a la fois.
    (B_L5, SVC,
     '        async with _scopes_sem():\n',
     '        if True:\n',
     ['r3_scopes_semaphore_deux_au_plus']),
    # -- banc croise ------------------------------------------------------------
    # 18 -- grade_copy remappee sur Ctrl+Maj+C (RESERVEE : l'inspecteur des
    #       DevTools la prend) -- patcher + son assert ; le banc croise la voit.
    (B_CROI, PAT,
     [('lbl:"grade : copier (effets couleur et masque du plan sélectionné)",combo:"Ctrl+Alt+C"},\'',
       'lbl:"grade : copier (effets couleur et masque du plan sélectionné)",combo:"Ctrl+Maj+C"},\''),
      ("assert R_R1.count('combo:\"Ctrl+Alt+C\"') == 1 and",
       "assert R_R1.count('combo:\"Ctrl+Maj+C\"') == 1 and")],
     None,
     ['x4_grade_copy_Ctrl_Alt_C', 'x4_les_combos_effectives_de_grade_copy']),
    # 19 -- /grade-frame lit `width` : la largeur envoyee par dzmFrameBody (`w`)
    #       n'est plus lue (le champ du client et celui de la route divergent).
    (B_CROI, SVC,
     '    w = _grade_w(body.get("w"))\n',
     '    w = _grade_w(body.get("width"))\n',
     ['x6_grade_frame_champs_envoyes', 'x6_grade_frame_appelee_avec_le_corps']),
]

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (7, 2, 3, 5, 3, 1, 5, 1, 2, 1, 5, 2, 2, 1, 2, 2, 1, 1, 3, 2)
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
    """PRE-VOL DE LA CHAINE (revue finale, 24/09/2026) : `repatch_all.py
    --list` doit rendre `montage` PUIS `dzcout`, chacun avec son script.

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
        elif len(rg) != N_ROUGES[i]:
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
