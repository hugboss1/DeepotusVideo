# -*- coding: utf-8 -*-
"""Banc de mutations du lot L7-A du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l7.py            # toutes
    python tests/mutations_montage_l7.py 0 7 14     # celles-la

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_l4.py` (5-uplets, mutation en OCTETS avec fin de
ligne MESUREE, `ecrire()` avec retentatives, sha256 restaure dans `finally`
par application inverse, etat MORT distinct de ROUGE).

CE QU'IL MUTE, ET POURQUOI CES TROIS FICHIERS-LA. Le lot L7-A (D-10 preset
Resolve + export/import du mappage, D-6 presse-papiers, D-8 boring
detector, D-39 comparaison de projets, D-3b vignettes A/B et roll d'une
image, D-19 coins et ombre d'un overlay, D-22 pistes de sous-titres par
langue) vit des deux cotes du reseau :
  . `frontend/patches/montage.js` : LA COUCHE, celle que le shim de
    `test_montage_edition.py` execute sous node (`dzmKmImport`,
    `DZM_KM_PRESETS`, `dzmClipCopy`, `dzmClipPaste`, `dzmBoring`,
    `dzmDiff`, `dzmAbSecs`, `dzmAbRollDit`, `dzmSubsBurn`) ;
  . `backend/app/services/montage_service.py` : `_ov_transform` (bornes de
    `radius`), la chaine `geq` et les cinq maillons d'ombre de
    `_build_montage_command` ;
  . `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour les
    quatre mutations qui ne sont PAS dans la couche mais dans le corps du
    bundle reecrit par les sections / replis du patcher (`data-boring` de
    L7c1, la garde `getSelection` de L7b3, `subsPayload` de L7f1,
    `subsOverlay` de L7f5) -- muter le PATCHER puis rejouer la chaine
    prouverait seulement que le patcher est coherent avec lui-meme ; c'est
    le fichier que l'application charge et que `test_montage_bundle.py` lit.

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. Couche JS -> `edition` ;
service -> `l7` ; bundle livre -> `bundle`. Le banc `bundle` n'est jamais
choisi pour une mutation de la COUCHE : il compare le bloc injecte a
`montage.js` octet pour octet, TOUTE mutation de la couche l'y ferait
rougir et le bruit noierait le signal.

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF ; mesure du 24/09/2026, sommet 5e0006f :
couche 0 `\\r\\n` pour 7 316 `\\n` -- LF, ce n'est PLUS le CRLF du 23/09
(le lot L7-A l'a reecrite en LF, `git ls-files --eol` : i/lf w/lf) ;
service 4 790 / 4 790 et bundle 20 973 / 20 973 -- CRLF), les motifs sont
ecrits en LF et remis dans la fin de ligne du fichier ; c'est le sha256
d'APRES qui prouve la restauration, pas cette phrase. La restauration est
une application INVERSE (les octets d'avant reecrits), JAMAIS un `git
checkout` : le worktree peut porter d'autres changements non commis.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
La restauration est verifiee par sha256 APRES CHAQUE mutation, dans un
`finally`. Un banc qui ne rend pas `=== N passed, M failed ===` ou un code
autre que 0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

LE BANC `l7` REND PAR FFMPEG (section [M] : rendu reel de 2 s, coins et
ombre sur testsrc2). Une mutation du service est donc jouee CONTRE ffmpeg
aussi : un `geq` sans `min(...)` et une ombre floutee AVANT le pad sont des
commandes que ffmpeg ACCEPTE (un rendu moins bon, pas un rendu mort) --
c'est la ligne qui pinne la forme, ET la mesure de pixels du rendu reel
quand elle voit la difference, qui rougissent ; c'est dit mutation par
mutation.

RESULTAT MESURE le 24/09/2026 (worktree epic-fermi-f6adf5, sommet 5e0006f,
python embarque, un processus par execution de banc, campagne ENTIERE
jouee deux fois : la premiere pour MESURER les comptes, la seconde pour
les prouver) : LES DIX-HUIT SONT ROUGES, AUCUN SURVIVANT, AUCUN MORT,
chacune sur les lignes declarees ; code de sortie 0 ; sha256 des trois
fichiers identiques avant / apres chaque mutation (arbre `git status`
propre a la fin).
Comptes des bancs au repos : edition 400/0, bundle 2191/0, l7 33/0.

    #   fonction visee                                    banc     rouges
    0   dzmKmImport acceptant version 2                   edition  1
    1   preset Resolve sans blade                         edition  4
    2   dzmKmImport sans detection de collision           edition  2
    3   dzmClipCopy gardant id                            edition  3
    4   dzmClipPaste sans refus « source »                edition  1
    5   dzmBoring jump sans test de source                edition  2
    6   dzmBoring long avec >=                            edition  2
    7   dzmDiff moved incluant trimmed                    edition  1
    8   dzmAbSecs sans x vitesse                          edition  2
    9   dzmAbRollDit partiel jamais dit                   edition  1
   10   dzmSubsBurn laissant deux gravees                 edition  1
   11   _ov_transform radius non borne                    l7       1
   12   geq sans min(...,min(...))                        l7       5
   13   ombre boxblur AVANT pad                           l7       6
   14   bundle : data-boring retire                       bundle   4
   15   bundle : garde getSelection retiree               bundle   4
   16   bundle : subsPayload lisant "s1" en dur           bundle   5
   17   bundle : subsOverlay sans subsBurnId              bundle   7

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  . la n°1 (preset sans blade) rougit QUATRE lignes : la table du preset,
    la copie neuve (`kp_rend_une_copie_neuve_a_chaque_appel` compare a la
    table attendue), la ligne « le preset passe svmKmMerge sans collision »
    ET la ligne de coeur pur `l7a_coeur_pur_x3_…` qui compte les combos
    ecrites dans la couche -- un pin de FORME rougit avec le comportement ;
  . les n°2, 5, 6 et 8 rougissent aussi leur ligne `l7x_coeur_pur_…` : ces
    lignes comptent des sous-chaines de la couche (`raison:"collision"`,
    `dzmBoringKey(g)`, `len>o.maxS`, `dzmSpeedNum(g)`) -- c'est pourquoi le
    compte est 2 et non 1 ; la ligne de comportement est celle qui est
    DECLAREE, la ligne de forme est comptee ;
  . la n°3 (`id` copie) rougit TROIS lignes : la copie, `cp_pur_ni_les_
    clips_ni_le_presse_papiers_ne_sont_mutes` (le collage ecrit l'id sur la
    copie ; avec `id` copie, la comparaison JSON du presse-papiers bouge) et
    `l7b_coeur_pur_…` qui compte la table NOCOPY ecrite une fois ;
  . la n°7 (moved incluant trimmed) ne rougit qu'UNE ligne : la ligne
    `df_rogne_et_bouge_…` est la seule dont un clip est rogne ET deplace ;
    la fixture principale `df` du plan n'a pas ce cas (id "2" ne bouge pas) ;
  . la n°12 (`geq` sans `min`) est jouee CONTRE ffmpeg : le rendu reel
    ACCEPTE `min(...)` absent (rc 0) mais la ligne `d19_rendu_reel_rc_0_…`
    rougit quand meme, car elle pinne la FORME de la commande (`min(`), pas
    seulement son rc ; la mesure des pixels du coin reste VERTE (mesure :
    rayon 60 a l'echelle du rendu 480x270, k = 0,25, = 15 px, plus petit que
    la demi-taille de l'overlay : `min` n'a pas a agir) -- la borne `min` ne
    se verrait qu'avec un rayon plus grand que la demi-taille de l'overlay,
    cas que [M] ne rend pas ;
  . la n°13 (boxblur AVANT pad) rougit SIX lignes, dont `d19_rendu_reel_
    rc_0_…` (forme de la commande) mais PAS `d19_rendu_reel_le_dernier_
    rang_du_canvas_d_ombre_est_le_fond_…` : le flou avant le pad laisse le
    dernier rang a 0 lui aussi (le canvas est vide au-dela du cadre floute)
    -- ce que la revue du 24/09 avait mesure au BORD (alpha 0 -> 140 sur
    1 px), pas au dernier rang ; c'est la ligne de forme
    `d19_l_ombre_est_paddee_PUIS_floutee_…` qui accuse, declaree ;
  . les mutations du bundle rougissent 4, 4, 5 et 7 lignes : la ligne
    nommee, la ligne GENERIQUE `<section>_remplace` (L7b3, L7f1, L7f5 --
    pas L7c1, repliee dans R_AJ6A dont c'est `AJ6a-…_remplace` qui rougit),
    la ligne de queue du patcher (`DZ_le_patcher_porte…_la_sonde_dit_132`) ;
    la n°14 rougit en plus la ligne CSS `L7c_css_liseres_…` (elle tient le
    temoin `data-boring` du bundle) ; la n°15 rougit en plus `L7b3-…_ancre_
    consommee` (la garde retiree rend a l'ancre sa liberte) ; les n°16 et 17
    rougissent `L7f_deux_sections_en_queue_…` (les remplacements L7f ne sont
    plus x1) ; la n°16 rougit en plus `L7f_sous_node_…` (le comportement
    joue sous node : s2 marquee, s1 part) ; la n°17 rougit en plus LES DEUX
    sondes dzcout (`DzTracks` x159 -> 158 : `subsBurnId(` retire) et la
    ligne `L7f4_hote_onNewTrack_…` qui compte `subsBurnId` x4 ;
  . AUCUNE mutation ne rougit sur un seul pin sans comportement.

ECARTS AU PLAN, DATES 24/09/2026 : le plan (tache 7) nommait quinze
candidates ; « preset Resolve sans trans_add » est devenu « sans blade »
(le preset MESURE ne porte pas trans_add : Ctrl+T est reservee au
navigateur, l'action a pour defaut Alt+T) ; « dzmClipPaste sans repli de
piste » est devenu « sans refus source » (le repli de piste est joue par
dzmClipPisteCible, deja bance par ses propres lignes, et le refus « source »
est la revue I-2 qui n'existait pas au plan) ; « ombre sans boxblur » est
devenu « boxblur AVANT pad » (la revue du 24/09 a inverse l'ordre, c'est
l'ordre qui est la regle) ; « dzmRemove supprimant s1 » et « trans_add
retire de SVM_ACTIONS » ne sont PAS dans la table (dzmRemove est inchange
par le lot, et trans_add vit dans le repli R_R1 du patcher, deja pinne par
`L7a1_…` ; dix-huit mutations couvrent les sept decisions) ; AJOUTEES :
dzmKmImport sans collision, dzmAbSecs sans vitesse, dzmAbRollDit partiel,
la garde getSelection, subsOverlay sans subsBurnId.
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
SVC = "backend/app/services/montage_service.py"
JS = "frontend/patches/montage.js"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
B_L7 = "tests/test_montage_l7.py"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, rouges attendues)
M = [
    # -- la couche (montage.js), jouee sous node par `edition` ---------------
    # 0 -- `dzmKmImport` acceptant un fichier version 2 : un format inconnu
    #      passerait pour le notre.
    (B_EDIT, JS,
     'd.version!==1||!d.keymap',
     '(d.version!==1&&d.version!==2)||!d.keymap',
     ["ki_v2_version_2_absente_keymap_absent_tableau_null_chaine_refus_version"]),
    # 1 -- le preset Resolve sans `blade` : Ctrl+B n'est plus la lame.
    (B_EDIT, JS,
     'var DZM_KM_PRESETS={resolve:{range_out:"O",toolbar:"Alt+O",blade:"Ctrl+B"}};\n',
     'var DZM_KM_PRESETS={resolve:{range_out:"O",toolbar:"Alt+O"}};\n',
     ["kp_resolve_exactement_range_out_O_toolbar_Alt_O_blade_Ctrl_B",
      "ki_vol_le_preset_resolve_passe_sans_collision_toolbar_deplacee"]),
    # 2 -- l'import sans detection de collision : une ligne qui vole la touche
    #      d'une action non remappee est retenue en silence (svmKmMerge la
    #      jettera au chargement, sans un mot).
    (B_EDIT, JS,
     'if(used[c])ign.push({id:a.id,raison:"collision",avec:used[c]});else{km[a.id]=c;used[c]=a.id}',
     'km[a.id]=c;used[c]=a.id',
     ["ki_vol_vol_du_defaut_et_doublon_dits_collision_avec_l_id_qui_garde_la_touche_temoin_blade_passe"]),
    # 3 -- `dzmClipCopy` gardant `id` : le clip colle porterait l'id du clip
    #      d'origine (collision d'ids dans le meme projet).
    (B_EDIT, JS,
     'var DZM_CLIP_NOCOPY=["id","transition","transition_s","src_history"];\n',
     'var DZM_CLIP_NOCOPY=["transition","transition_s","src_history"];\n',
     ["cc_copie_sans_id_transition_transition_s_src_history_avec_srcOut_et_gain_undefined_ignore",
      "cp_pur_ni_les_clips_ni_le_presse_papiers_ne_sont_mutes"]),
    # 4 -- `dzmClipPaste` sans le refus « source » : un clip de demo (sans src)
    #      serait colle et jamais rendu.
    (B_EDIT, JS,
     '  if(!c.src&&c.kind!=="title"&&c.kind!=="adjust")\n',
     '  if(!1)\n',
     ["cp_revue_I2_clip_sans_source_refus_source_note_dite_temoins_title_et_adjust_sans_src_passent"]),
    # 5 -- `dzmBoring` jump sans le test de source : deux plans DIFFERENTS en
    #      contact dont les srcIn se suivent seraient dits jump cut.
    (B_EDIT, JS,
     'if(!g||!k||k!==dzmBoringKey(g))return;',
     'if(!g||!k)return;',
     ["bo_sources_job_vs_image_differents_deux_images_identiques_jump_differentes_non_sans_source_rien_src_vide_rien"]),
    # 6 -- `long` avec `>=` : un plan de exactement maxS est dit trop long.
    (B_EDIT, JS,
     'if(len>o.maxS)out[c.id]="long";',
     'if(len>=o.maxS)out[c.id]="long";',
     ["bo_egal_8_s_exactement_n_est_pas_long_8_001_l_est"]),
    # 7 -- `dzmDiff` : moved n'exclut plus trimmed -- un clip rogne dont le
    #      start a bouge est aussi dit deplace.
    (B_EDIT, JS,
     '    else if(Math.abs(sa-sb)>1e-6)out.moved.push({id:id,de:sa,en:sb});\n',
     '    if(Math.abs(sa-sb)>1e-6)out.moved.push({id:id,de:sa,en:sb});\n',
     ["df_rogne_et_bouge_tete_coupee_duree_et_srcIn_changes_rogne_seulement_jamais_deplace"]),
    # 8 -- `dzmAbSecs` sans la vitesse du plan gauche : a x2 la vignette A
    #      montre le milieu du plan, pas sa derniere image.
    (B_EDIT, JS,
     'len*dzmSpeedNum(g)-DZM_AB_IMG',
     'len-DZM_AB_IMG',
     ["ab_vitesse_du_gauche_etire_la_fenetre_x2_illisible_ou_nulle_vaut_1_celle_du_droit_ne_compte_pas"]),
    # 9 -- `dzmAbRollDit` : un roll borne (4 images sur 10 demandees) n'est
    #      jamais dit partiel.
    (B_EDIT, JS,
     'return {k:Math.round(d/DZM_AB_IMG),partiel:!0}}',
     'return {k:Math.round(d/DZM_AB_IMG),partiel:!1}}',
     ["abd_total_partiel_nul_signe_entrees_molles_demi_ms_rien_millieme_arrondi_total"]),
    # 10 -- `dzmSubsBurn` laissant deux gravees : l'ancienne marque survit.
    (B_EDIT, JS,
     'return Object.assign({},t,{burn:String(t.id)===want})})}',
     'return Object.assign({},t,{burn:String(t.id)===want||!!t.burn})})}',
     ["sb_bascule_retour_une_seule_gravee"]),
    # -- le service, joue par `l7` ---------------------------------------------
    # 11 -- `_ov_transform` : `radius` non borne (999 passe, -1 passe).
    (B_L7, SVC,
     '            out[key] = int(max(lo, min(hi, int(round(f)))))\n',
     '            out[key] = int(round(f))\n',
     ["d19_radius_999_borne_a_200_et_moins_1_a_0"]),
    # 12 -- `geq` sans `min(rayon, min(W/2,H/2))` : un rayon plus grand que la
    #       demi-hauteur de l'overlay inverse le masque ; ffmpeg accepte.
    (B_L7, SVC,
     '                rm = f"min({rrad},min(W/2,H/2))"\n',
     '                rm = f"{rrad}"\n',
     ["d19_radius_40_pose_geq_une_fois_avec_min_imbrique_apres_format_rgba_et_avant_setpts",
      "d19_rendu_reel_rc_0_fichier_non_vide_geq_et_ombre_dans_la_commande"]),
    # 13 -- l'ombre floutee AVANT le pad : le flou travaille un alpha constant
    #       dans son propre cadre, bord net (revue 24/09) ; ffmpeg accepte.
    (B_L7, SVC,
     '            parts.append(f"[os{j}]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.55,"\n'
     '                         f"pad=iw+{6 * u}:ih+{6 * u}:{4 * u}:{4 * u}:color=black@0,"\n'
     '                         f"boxblur={u}[osp{j}]")\n',
     '            parts.append(f"[os{j}]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.55,"\n'
     '                         f"boxblur={u},"\n'
     '                         f"pad=iw+{6 * u}:ih+{6 * u}:{4 * u}:{4 * u}:color=black@0[osp{j}]")\n',
     ["d19_l_ombre_est_paddee_PUIS_floutee_et_l_overlay_interne_garde_rgba",
      "d19_shadow_1_split_en_cinq_maillons_et_le_label_ov0_reste_final"]),
    # -- le bundle livre, lu par `bundle` ----------------------------------------
    # 14 -- `data-boring` retire de .svm-clip : le detecteur calcule, rien ne
    #       se voit.
    (B_BUND, BUN,
     '                    "data-boring":boMap[c.id]||void 0,\n',
     '',
     ["L7c1_data_boring_x1_sur_svm_clip_juste_apres_data_kind_replie_dans_R_AJ6A_undefined_ailleurs_que_V1"]),
    # 15 -- la garde `getSelection` retiree : Ctrl+C sur un texte selectionne
    #       hors champ copie le clip au lieu du texte.
    (B_BUND, BUN,
     '      if(id==="copy"&&window.getSelection&&String(window.getSelection())!=="")return;\n',
     '',
     ["L7b3_garde_getSelection_x1_avant_le_preventDefault_d_onKey_ancre_libre_1_0_1_bak_x0_temoin"]),
    # 16 -- `subsPayload` lisant "s1" en dur : la piste marquee gravee n'est
    #       jamais celle du rendu.
    (B_BUND, BUN,
     'return c.tr===bid}',
     'return c.tr==="s1"}',
     ["L7f1_subsPayload_bid_par_subsBurnId_filtre_c_tr_bid_subsSegsOf_intact_ailleurs_temoin_s1_x1",
      "L7f_sous_node_sans_marque_s1_part_s2_marquee_s2_part_s1_video_la_premiere_subs_sans_subs_s1"]),
    # 17 -- `subsOverlay` sans `subsBurnId` : le lecteur montre S1 alors que
    #       le rendu grave S2.
    (B_BUND, BUN,
     '    var dzBid=DzTracks.subsBurnId(svmTracksOf(proj));\n',
     '    var dzBid="s1";\n',
     ["L7f5_subsOverlay_filtre_par_subsBurnId_comme_subsPayload_temoin_subsSegsOf_x7_ailleurs",
      "EC_la_sonde_dzcout_compte_DzTracks_159"]),
]

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (1, 4, 2, 3, 1, 2, 2, 1, 2, 1, 1, 1, 5, 6, 4, 4, 5, 7)
assert len(N_ROUGES) == len(M), (len(N_ROUGES), len(M))


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
