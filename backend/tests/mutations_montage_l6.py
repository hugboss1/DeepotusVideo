# -*- coding: utf-8 -*-
"""Banc de mutations du lot L6 du Montage (audio) : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l6.py            # toutes
    python tests/mutations_montage_l6.py 0 7 14     # celles-la
    python tests/mutations_montage_l6.py --pre-vol  # le pre-vol seul

PRE-VOL (modele L5, 24/09/2026) : avant toute mutation, `repatch_all.py
--list` doit rendre `montage` PUIS `dzcout` (ordre = mtime des `.bak_*`) ;
sinon sortie code 2, rien n'est mute.

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_l5.py` (5-uplets, mutation en OCTETS avec fin de
ligne MESUREE, `ecrire()` avec retentatives, sha256 restaure dans `finally`
par application inverse, etat MORT distinct de ROUGE).

CE QU'IL MUTE. Le lot L6 (D-23 egaliseur 6 bandes et pan, D-25
anti-ronflement et bruit appris, D-26 voix off) vit dans :
  . `sfx_service.py` (T1 : vocabulaire `_FX_ORDER` / `_FX_PARAMS`,
    `_fx_dehum`, `_fx_denoise`, `learn_of`, `nf_of`) -> banc `l6` [1] ;
  . `montage_service.py` (T2 : prefixe de bruit de la chaine par clip, route
    `noise-profile`) -> bancs `l6` [2] et `l6_croise` [3] ;
  . `routes.py` (T3 : `POST /api/audio/recording`) -> banc `l6_voix` ;
  . `frontend/patches/montage.js` : LA COUCHE jouee sous node (T4 coeur pur,
    T6 `DzmVoiceRec`) -> banc `edition` [39] [41] ;
  . `scripts/patch_bundle_montage.py` : LE PATCHER (T5 sections L6fx*/L6au1
    du bloc SFXSTUDIO, T6 section L6vo1 et action `vo_record`) : muter le
    patcher PUIS rejouer la chaine (`scripts/repatch_all.py --from montage`,
    cwd = racine), jouer le banc, RESTAURER le patcher puis rejouer la
    chaine ; le sha256 du patcher, du bundle ET du `.bak_dzcout` d'apres est
    compare a celui d'avant. Une chaine qui ne se rejoue pas (assert du
    patcher) = MORT, pas ROUGE. Quand un assert du patcher epingle le texte
    mute, la mutation porte AUSSI l'assert (liste de paires) : sinon la
    chaine meurt et rien n'est juge.
Le banc `bundle` n'est jamais choisi pour une mutation de la COUCHE : il
compare le bloc injecte a `montage.js`, toute mutation de la couche l'y
ferait rougir et le bruit noierait le signal.

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF), les motifs sont ecrits en LF et remis
dans la fin de ligne du fichier ; c'est le sha256 d'APRES qui prouve la
restauration, pas cette phrase. Mesure du 25/09/2026 (worktree
epic-fermi-f6adf5, autocrlf) : les cinq fichiers mutes ET le bundle en CRLF
(homogenes). La restauration est une application INVERSE (les octets d'avant
reecrits), JAMAIS un `git checkout`.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
Un banc qui ne rend pas `=== N passed, M failed ===` ou un code autre que
0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

AUCUN reseau, AUCUNE depense : les bancs `l6` et `l6_voix` jouent ffmpeg reel
sur des sources lavfi generees en TMP ; jamais /api/audio/voiceover ni
/api/audio/sfx.

RESULTAT MESURE le 25/09/2026 (worktree epic-fermi-f6adf5, sommet a669092 +
bancs de cloture, python embarque, un processus par execution de banc,
campagne ENTIERE jouee deux fois : la premiere pour MESURER, la seconde pour
PROUVER) : LES VINGT-QUATRE SONT ROUGES, AUCUN SURVIVANT, AUCUN MORT, chacune
sur les lignes declarees et au compte declare ; code de sortie 0 ; sha256 des
fichiers identiques avant / apres chaque mutation (patcher, bundle et
.bak_dzcout compris). Comptes des bancs au repos : l6 110/0, l6_voix 36/0,
edition 598/0, bundle 2340/0, l6_croise 29/0. 106 lignes rouges au total.

    #   fonction visee                                    banc       rouges
    0   _FX_ORDER : dehum apres eq6                       l6         3
    1   eq6 : borne ls_g +/-24                            l6         1
    2   dehum : cran w=30                                 l6         2
    3   dehum : dosage m= ignore                          l6         1
    4   DN_DELAY 1100 au lieu de 1200                     l6         23
    5   asetnsamples sans p=0                             l6         15
    6   afftdn non nomme (asendcmd de tous)               l6         15
    7   tn=1 pose                                         l6         10
    8   nf_of : RMS + 5                                   l6         5
    9   learn_of sans tolerance 1e-9                      l6         1
   10   prefixe sans apad=whole_len                       l6         2
   11   src_dur_sonde ignore (repli 9999)                 l6         3
   12   noise-profile sans tolerance 1e-9                 l6_croise  1
   13   /audio/recording sans -ac 1                       l6_voix    1
   14   nom reserve en wb (ecrase)                        l6_voix    6
   15   dzmLearnRange sans tolerance                      edition    1
   16   dzmNfEffectif sans borne -20                      edition    2
   17   DzmVoiceRec : M.pj="P1" en dur                    edition    1
   18   DzmVoiceRec : garde demo retiree                  edition    5
   19   patcher : refus job_id retabli (sfxAudition)      bundle     1
   20   patcher : hide:1 retire de learn_out              bundle     1
   21   patcher : mode ecraser non restaure               bundle     3
   22   patcher : onDone sans comparaison du projet       bundle     1
   23   patcher : vo_record sur Ctrl+R (reservee)         l6_croise  2

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  . la n°9 etait SURVIVANTE a la premiere passe : TROU du banc `l6` -- la
    seule ligne de la garde (5 -> 5,2) vaut 0,2000…02 en flottant et passe
    sans la tolerance ; 1,0 -> 1,2 vaut 0,1999…96. Ligne
    `t1_learn_of_tolerance_1_0_1_2_acceptee_temoin_1_19_refusee` ajoutee ;
  . la n°17 (revue T6) SURVIVAIT au cas 13 de la section [41] du banc
    edition : onStart y rendait `pj:"P1"`, la valeur mutee elle-meme ; le cas
    rend desormais `P9`, et la mutation rougit ;
  . la n°12 ne rougit QUE le banc croise : le banc `l6` interroge la route
    sur 0,1 / 31 s et jamais sur 1,0-1,2 -- c'est la table du croise qui la
    tient (l'aller-retour couche -> route) ;
  . la n°4 rougit 23 lignes : le retard entre dans TOUTES les commandes du
    debruiteur (defaut preexistant corrige par T1 pour tous les clips) ;
  . la n°21 rougit aussi `chaque_armement_a_son_extinction` : un mode force
    jamais remis est un armement sans extinction.
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
RTS = "backend/app/api/routes.py"
JS = "frontend/patches/montage.js"
PAT = "scripts/patch_bundle_montage.py"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
BAK = "frontend/dist/assets/index-BEOJX8L5.js.bak_dzcout"
B_L6 = "tests/test_montage_l6.py"
B_VOIX = "tests/test_montage_l6_voix.py"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"
B_CROI = "tests/test_montage_l6_croise.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, lignes rouges attendues)
M = [
    # -- T1 : sfx_service.py, joue par `l6` [1] ---------------------------------
    # 0 -- ordre de chaine : l'anti-ronflement APRES l'egaliseur 6 bandes (le
    #      bruit serait appris sur une source encore ronflante).
    (B_L6, SFX,
     '_FX_ORDER = ("filter", "dehum", "eq3", "denoise", "eq6", "deesser", "compressor",\n',
     '_FX_ORDER = ("filter", "eq3", "denoise", "eq6", "dehum", "deesser", "compressor",\n',
     ['t1_ordre_contrat_douze_types',
      't1_ordre_fragments_contrat']),
    # 1 -- borne de `eq6` : un gain de +/-24 dB passe (ffmpeg refuse au-dela
    #      de ses bornes : le rendu echouerait).
    (B_L6, SFX,
     '            "ls_f": (30.0, 500.0, 100.0), "ls_g": (-12.0, 12.0, 0.0),\n',
     '            "ls_f": (30.0, 500.0, 100.0), "ls_g": (-24.0, 24.0, 0.0),\n',
     ['t1_sanitize_eq6_bornes']),
    # 2 -- cran du de-hum a Q=30 : ne tient plus la derive du secteur (mesure).
    (B_L6, SFX,
     'bandreject=f={base * k}:width_type=q:w=10:m={m}',
     'bandreject=f={base * k}:width_type=q:w=30:m={m}',
     ['t1_dehum_defauts_quatre_crans_50',
      't1_dehum_60_trois_crans_dose']),
    # 3 -- dosage `m=` ignore : le de-hum coupe toujours a 100 %.
    (B_L6, SFX,
     '    m = _g(p["amount"] / 100.0)\n',
     '    m = "1"\n',
     ['t1_dehum_60_trois_crans_dose']),
    # 4 -- retard d'afftdn 1100 au lieu de 1200 : le son sort decale de 100
    #      echantillons (le clic n'est plus a sa place).
    (B_L6, SFX,
     'DN_DELAY = 1200 ',
     'DN_DELAY = 1100 ',
     ['t1_denoise_defaut_retard_compense',
      't1_reel_denoise_decalage_nul_longueur_exacte']),
    # 5 -- `asetnsamples` sans `p=0` : la derniere trame est remplie de
    #      silence, la duree s'allonge.
    (B_L6, SFX,
     '"asetnsamples=n=4096:p=0"]',
     '"asetnsamples=n=4096"]',
     ['t1_denoise_defaut_retard_compense',
      't1_reel_chaine_complete_longueur_et_decalage']),
    # 6 -- instance non nommee : l'asendcmd d'un clip pilote l'apprentissage
    #      de TOUS les afftdn du graphe.
    (B_L6, SFX,
     '        name = f"afftdn@dn{uid}"\n',
     '        name = "afftdn"\n',
     ['t1_denoise_appris_asendcmd_nomme',
      't2_deux_clips_appris_deux_uid_distincts']),
    # 7 -- `tn=1` pose : il ecrase le profil appris (mesure).
    (B_L6, SFX,
     "    opts = f\"nr={_g(p['amount'])}\"\n",
     "    opts = f\"nr={_g(p['amount'])}:tn=1\"\n",
     ['t1_denoise_appris_jamais_tn_temoin_sn']),
    # 8 -- regle du plancher RMS + 5 au lieu de RMS + 10.
    (B_L6, SFX,
     'round(v + 10.0)',
     'round(v + 5.0)',
     ['t1_nf_of_regle',
      't2_route_200_rms_du_bruit_et_nf_de_la_regle']),
    # 9 -- garde de learn_of sans sa tolerance : 1,2 - 1,0 = 0,19999… refuse
    #      alors que la couche et la route l'acceptent. SURVIVANTE a la
    #      premiere passe (5 -> 5,2 vaut 0,2000…02 : aucune ligne ne tenait la
    #      tolerance) -> TROU du banc `l6` ferme par
    #      `t1_learn_of_tolerance_1_0_1_2_…` ; le banc croise [3] la voit aussi.
    (B_L6, SFX,
     '        if b - a < LEARN_MIN - 1e-9:\n',
     '        if b - a < LEARN_MIN:\n',
     ['t1_learn_of_tolerance_1_0_1_2_acceptee_temoin_1_19_refusee']),
    # -- T2 : montage_service.py ------------------------------------------------
    # 10 -- prefixe sans `apad=whole_len` : une plage en partie hors source
    #       rend un prefixe COURT et le retrait mange le debut du clip.
    (B_L6, SVC,
     'f"apad=whole_len={P}[l6p{n}]")',
     'f"anull[l6p{n}]")',
     ['t2_reel_plage_partie_hors_source_duree_exacte_clic_a_sa_place']),
    # 11 -- `src_dur_sonde` ignore : le repli 9999 de `src_dur` redevient une
    #       duree (une source longue perd son apprentissage, une inconnue le garde).
    (B_L6, SVC,
     '        sd = c["src_dur_sonde"] if "src_dur_sonde" in c else c.get("src_dur")\n',
     '        sd = c.get("src_dur")\n',
     ['r4_source_longue_sondee_9999_et_10000_s_gardent_le_prefixe',
      't2_duree_inconnue_pas_de_prefixe_temoin_duree_connue']),
    # 12 -- route noise-profile sans sa tolerance : 1,0-1,2 refusee (400)
    #       alors que la couche l'envoie.
    (B_CROI, SVC,
     '    if not (_NP_MIN - 1e-9 <= t1 - t0 <= _NP_MAX + 1e-9):\n',
     '    if not (_NP_MIN <= t1 - t0 <= _NP_MAX + 1e-9):\n',
     ['x3_dzmLearnRange_accepte_refuse_comme_la_route_noise_profile_bornes_0_2_et_30']),
    # -- T3 : routes.py, joue par `l6_voix` ---------------------------------------
    # 13 -- prise transcodee sans `-ac 1` : le WAV garde les canaux recus.
    (B_VOIX, RTS,
     '"-i", str(src), "-vn", "-map", "0:a:0", "-ac", "1",',
     '"-i", str(src), "-vn", "-map", "0:a:0",',
     ['v1_wav_200_nom_voix_off_wav_48k_mono_16_bits_duree_fabriquee']),
    # 14 -- nom reserve en `wb` : deux prises dans la meme seconde s'ecrasent.
    (B_VOIX, RTS,
     '            with open(dest, "xb"):\n',
     '            with open(dest, "wb"):\n',
     ['v2_meme_seconde_trois_noms_distincts_base_puis_2_puis_3',
      'v2_la_premiere_prise_reste_intacte']),
    # -- T4 / T5 / T6 : la couche, jouee par `edition` -----------------------------
    # 15 -- dzmLearnRange sans la tolerance de learn_of : 1,0-1,2 refusee.
    (B_EDIT, JS,
     'if(b-a<.2-1e-9)return {refus:"courte"',
     'if(b-a<.2)return {refus:"courte"',
     ['au_lr_plage_de_source_vitesse_hors_clip_hors_source']),
    # 16 -- dzmNfEffectif sans la borne -20 : « -5 dB » affiche, -20 rendu.
    (B_EDIT, JS,
     '  return Math.max(-80,Math.min(-20,n))}',
     '  return Math.max(-80,n)}',
     ['l6v_nfEffectif_regle_du_rendu',
      'l6v_statut_et_title_d_oublier_montrent_le_plancher_du_rendu']),
    # 17 -- identite de projet EN DUR (revue T6) : la prise d'un projet se pose
    #       dans le suivant.
    (B_EDIT, JS,
     'M.pj=ob?r0.pj:void 0;',
     'M.pj="P1";',
     ['l6v_arret_spontane_onDone_recoit_l_identite_du_projet_rendue_par_onStart']),
    # 18 -- garde demo de l'enregistreur retiree : la bascule du clavier ouvre
    #       le micro sur la maquette.
    (B_EDIT, JS,
     'if(demo){note("Voix off : disponible sur un projet réel',
     'if(!1){note("Voix off : disponible sur un projet réel',
     ['l6v_demo_un_bouton_grise_titre_la_bascule_clavier_dit_le_refus_sans_ouvrir_le_micro']),
    # -- T5 / T6 : le patcher, joue par `bundle` apres la chaine ----------------------
    # 19 -- refus `job_id` retabli dans sfxAudition : le son d'un plan ne
    #       s'ecoute plus rendu.
    (B_BUND, PAT,
     "R_L6AU1 = ('    if(!c||!c.src||!(c.src.audio||c.src.job_id)){\\n'",
     "R_L6AU1 = ('    if(!c||!c.src||!c.src.audio){\\n'",
     ['L6_ecoute_rendue_accepte_le_son_d_un_plan_job_id']),
    # 20 -- `hide:1` retire de la rangee `learn_out` : elle s'affiche en
    #       curseur (+ l'assert du compte).
    (B_BUND, PAT,
     [('R_L6FX2.count("hide:1") == 2', 'R_L6FX2.count("hide:1") == 1'),
      ('dec:3,unit:"s",hide:1}]},\\n\'', 'dec:3,unit:"s"}]},\\n\'')],
     None,
     ['L6_catalogue_eq6_dehum_en_rendu_seul_libelles_plancher_dit_auto_plage_apprise_cachee']),
    # 21 -- mode « ecraser » NON restaure apres la pose d'une prise (+ l'assert).
    (B_BUND, PAT,
     [('R_L6VO1.find("finally{dzModeRef.current=m0;dzmReplaceRef.current=rp}")',
       'R_L6VO1.find("finally{dzmReplaceRef.current=rp}")'),
      ("'            finally{dzModeRef.current=m0;dzmReplaceRef.current=rp}\\n'",
       "'            finally{dzmReplaceRef.current=rp}\\n'")],
     None,
     ['L6vo_la_pose_force_ecraser_suspend_le_remplacement',
      'L6vo_un_refus_d_addAsset_restaure_quand_meme_le_mode']),
    # 22 -- onDone ne compare plus le projet : une prise commencee dans un
    #       projet se pose dans le suivant.
    (B_BUND, PAT,
     'if(pj!==String(pc&&(pc.project_id||pc.name)||"")){fireNote(',
     'if(!1){fireNote(',
     ['L6vo_projet_change_pendant_la_prise_rien_de_pose']),
    # -- banc croise -----------------------------------------------------------------
    # 23 -- vo_record sur Ctrl+R (RESERVEE : le navigateur recharge la page).
    (B_CROI, PAT,
     'combo:"Alt+R"},',
     'combo:"Ctrl+R"},',
     ['x6_la_combo_effective_de_vo_record_n_est_pas_reservee',
      'x6_vo_record_une_fois_au_bundle_avec_Alt_R']),
]

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (3, 1, 2, 1, 23, 15, 15, 10, 5, 1, 2, 3, 1, 1, 6, 1, 2, 1, 5, 1, 1, 3, 1, 2)
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
