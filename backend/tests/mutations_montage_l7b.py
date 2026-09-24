# -*- coding: utf-8 -*-
"""Banc de mutations du lot L7-B du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l7b.py            # toutes
    python tests/mutations_montage_l7b.py 0 7 14     # celles-la

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_l7.py` (5-uplets, mutation en OCTETS avec fin de
ligne MESUREE, `ecrire()` avec retentatives, sha256 restaure dans `finally`
par application inverse, etat MORT distinct de ROUGE).

CE QU'IL MUTE. Le lot L7-B (D-37 export EDL/FCPXML, D-42 decouper aux
changements de plan, D-40 recadrage par energie de mouvement, D-41
auto-clips, D-34 note etoile des rendus) vit dans :
  . les services PURS `edl_export.py`, `scenes.py`, `autoclips.py` et
    `montage_service.py` (`_reframe_of`, `_rf_lerp_expr`, la chaine cover
    V1, la route /autoclips) -> banc `l7b` ;
  . `pipeline.py` (`list_jobs(min_rating)`) -> banc `l7b_notes` ;
  . `frontend/patches/montage.js` : LA COUCHE jouee sous node par le shim
    de `test_montage_edition.py` (`dzmCutAt`, `dzmAcPayload`, le tiroir
    Medias) -> banc `edition` ;
  . `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour la
    garde d'obsolescence de « Decouper aux changements de plan » qui vit
    dans le corps reecrit par le patcher (muter le PATCHER puis rejouer la
    chaine prouverait seulement que le patcher est coherent avec lui-meme)
    -> banc `bundle`.
Le banc `bundle` n'est jamais choisi pour une mutation de la COUCHE : il
compare le bloc injecte a `montage.js` octet pour octet, toute mutation de
la couche l'y ferait rougir et le bruit noierait le signal.

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF), les motifs sont ecrits en LF et remis
dans la fin de ligne du fichier ; c'est le sha256 d'APRES qui prouve la
restauration, pas cette phrase. Mesure du 24/09/2026 (sommet 393b7b1) :
`montage_service.py`, `pipeline.py` et le bundle en CRLF ; `edl_export.py`,
`scenes.py`, `autoclips.py` et la couche en LF. La restauration est une
application INVERSE (les octets d'avant reecrits), JAMAIS un `git
checkout` : le worktree peut porter d'autres changements non commis.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
La restauration est verifiee par sha256 APRES CHAQUE mutation, dans un
`finally`. Un banc qui ne rend pas `=== N passed, M failed ===` ou un code
autre que 0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

LES BANCS `l7b` ET `l7b_notes` JOUENT FFMPEG ET SQLITE REELS (sources
testsrc2 generees en TMP, rendus 9:16, base TMP) : une mutation de service
est donc jugee sur le COMPORTEMENT mesure, pas seulement sur la forme ;
AUCUN reseau (LLM factice, transcription espionnee).

RESULTAT MESURE le 24/09/2026 (worktree epic-fermi-f6adf5, sommet 393b7b1
+ bancs de cloture, python embarque, un processus par execution de banc,
campagne ENTIERE jouee deux fois : la premiere pour MESURER, la seconde
pour PROUVER) : LES DIX-NEUF SONT ROUGES, AUCUN SURVIVANT, AUCUN MORT,
chacune sur les lignes declarees et au compte declare ; code de sortie 0 ;
sha256 des fichiers identiques avant / apres chaque mutation.
Comptes des bancs au repos : l7b 158/0, l7b_notes 48/0, edition 459/0,
bundle 2271/0.

    #   fonction visee                                    banc       rouges
    0   EDL sans M2 (coupe franche)                       l7b        1
    1   EDL FROM CLIP NAME = libelle                      l7b        1
    2   FCPXML sans timeMap                               l7b        1
    3   commentaire XML non neutralise                    l7b        2
    4   scdet sans setpts=PTS-STARTPTS                    l7b        1
    5   dzmCutAt sans ecart minimal                       edition    3
    6   _reframe_of t non borne                           l7b        3
    7   crop place apres setpts=PTS/vitesse               l7b        2
    8   _rf_lerp_expr en chaine                           l7b        2
    9   windows replafonnee a 400                         l7b        2
   10   glouton retire des choix du LLM                   l7b        1
   11   confirm accepte sans max_usd (chemin payant)      l7b        3
   12   cache des mots transcrits retire                  l7b        4
   13   verrou de transcription en cours retire           l7b        1
   14   min_rating applique apres le limit                l7b_notes  6
   15   dzmAcPayload accepte une coche booleenne          edition    3
   16   offset du tiroir fige                             edition    1
   17   memoires videes malgre un PUT encore en vol       edition    1
   18   bundle : garde d'obsolescence sans la source      bundle     4

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  . la n°0 etait SURVIVANTE a la premiere passe : la fixture de [1]
    n'avait de vitesse que sur un plan en FONDU, la ligne M2 de la branche
    COUPE FRANCHE n'etait lue par aucune ligne -- trou comble par la ligne
    `l7b_cloture_edl_coupe_franche_a_vitesse_M2_…` (section [9]) ;
  . la n°8 etait MORTE a la premiere passe : `_eval_ff` du banc (qui evalue
    l'expression ffmpeg en python) levait SyntaxError « too many nested
    parentheses » sur la chaine de 240 niveaux et TUAIT le banc (faute
    n°6) ; elle rend desormais NaN et la ligne rougit, avec le rendu reel
    (ffmpeg refuse la chaine au-dela de 93 niveaux : -22) ;
  . la n°4 ne rougit QUE la ligne de FORME de la commande : avec -ss avant
    -i, ffmpeg 8.1.1 rend deja des temps relatifs au debut lu (srcIn 0,5 ->
    coupe a 1,5 reste vert sans setpts) -- `setpts=PTS-STARTPTS` est une
    ceinture, ECART CONTESTE PAR LA MESURE, date dans la conception ;
  . les n°16 et 17 ne rougissent que des pins de FORME du banc edition (le
    tiroir est un composant React que le shim ne monte pas) ; le
    comportement de 16 est joue sous node par le banc bundle (84814da) ;
  . la n°7 rougit le RENDU REEL (le carre sort du cadre a x2) ET la forme ;
  . la n°12 rougit quatre lignes : sans cache, chaque relance repaie et les
    compteurs d'espion des lignes suivantes (duree nulle, chapitre) derivent ;
  . la n°18 rougit la ligne sous node (source remplacee pendant l'analyse)
    et trois pins de forme du patcher (section EC1, remplacement, queue).
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
EDL = "backend/app/services/edl_export.py"
SCN = "backend/app/services/scenes.py"
ACL = "backend/app/services/autoclips.py"
PIP = "backend/app/services/pipeline.py"
JS = "frontend/patches/montage.js"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
B_L7B = "tests/test_montage_l7b.py"
B_NOTES = "tests/test_montage_l7b_notes.py"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, rouges attendues)
M = [
    # -- D-37 : edl_export.py, joue par `l7b` [1] -------------------------------
    # 0 -- l'EDL sans la ligne `M2` d'un plan a vitesse != 1 (branche coupe
    #      franche) : Resolve relit le plan a x1 et la duree source ment.
    (B_L7B, EDL,
     '            bloc.append(_ev(n, "AX", "V", "C", "", si, so, ri, ro, fps))\n'
     '            if sp != 1.0:\n'
     '                bloc.append("M2   %-8s %05.1f                %s" % ("AX", fps * sp, _tc(si, fps)))\n',
     '            bloc.append(_ev(n, "AX", "V", "C", "", si, so, ri, ro, fps))\n',
     ['l7b_cloture_edl_coupe_franche_a_vitesse_M2_juste_apres_l_evenement']),
    # 1 -- `* FROM CLIP NAME:` = le LIBELLE du plan au lieu du nom de FICHIER :
    #      la reconnexion de Resolve par nom de fichier echoue.
    (B_L7B, EDL,
     '            bloc.append("* FROM CLIP NAME: " + _nom_fichier(info))\n',
     '            bloc.append("* FROM CLIP NAME: " + _libelle(c, "plan"))\n',
     ['d37_edl_lignes_exactes_timecodes_calcules_a_la_main']),
    # 2 -- le FCPXML sans `timeMap` : un plan x2 est relu a x1.
    (B_L7B, EDL,
     '        if sp != 1.0:\n'
     '            tm = ET.SubElement(el, "timeMap")\n',
     '        if False:\n'
     '            tm = ET.SubElement(el, "timeMap")\n',
     ['d37_fcpxml_vitesse_x2_par_timeMap_0_0_puis_45_90']),
    # 3 -- le commentaire XML non neutralise : un libelle `x--y-` rend le
    #      FCPXML illisible (`--` interdit dans un commentaire).
    (B_L7B, EDL,
     '    while "--" in t:\n'
     '        t = t.replace("--", "- -")\n',
     '',
     ['d37_revue_libelle_x__y_tiret_final_le_FCPXML_reste_lisible_commentaires_neutralises',
      'd37_revue_chevauchement_V1_start_avance_avec_le_debut_36_30s']),
    # -- D-42 : scenes.py, joue par `l7b` [2] ----------------------------------
    # 4 -- `scdet` sans `setpts=PTS-STARTPTS` (forme seule : voir la table) ; avec
    #      srcIn != 0, les coupes seraient decalees de srcIn.
    (B_L7B, SCN,
     '                 "setpts=PTS-STARTPTS,scdet=threshold=%g,"\n',
     '                 "scdet=threshold=%g,"\n',
     ['d42_detect_commande_ss_t_avant_i_scdet_seuil_et_impression_par_cle']),
    # -- D-42 : la couche, jouee par `edition` [32] ---------------------------
    # 5 -- `dzmCutAt` sans ecart minimal entre deux coupes : deux coupes a
    #      moins de 0,05 s font un morceau d'une image.
    (B_EDIT, JS,
     'cand.forEach(function(p){if(prev===null||p-prev>=DZM_CUT_BORD-1e-9)ps.push(p);prev=p});',
     'cand.forEach(function(p){ps.push(p);prev=p});',
     ['ca_ecart_minimal_0_05_entre_candidates_une_rafale_fait_une_coupe']),
    # -- D-40 : montage_service.py, joue par `l7b` [3] -------------------------
    # 6 -- `_reframe_of` : t non borne a la duree de SOURCE du plan.
    (B_L7B, SVC,
     '        t = max(0.0, t)\n'
     '        if dur > 0:\n'
     '            t = min(t, dur)\n',
     '        t = max(0.0, t)\n',
     ['d40_reframe_of_suivi_a_vitesse_2_borne_t_a_la_duree_de_SOURCE_consommee',
      'd40_reframe_of_suivi_trie_t_borne_0_duree_du_clip_x_borne']),
    # 7 -- le crop place APRES setpts=PTS/vitesse (chaine a vitesse) : `t`
    #      de l'expression n'est plus le temps de SOURCE depuis srcIn.
    (B_L7B, SVC,
     '                       f"{crp},setsar=1,"\n'
     '                       f"setpts=PTS/{sfx_service.fnum(spd)}{rtp if rt == \'flow\' else \'\'},"\n',
     '                       f"setsar=1,"\n'
     '                       f"setpts=PTS/{sfx_service.fnum(spd)},{crp}{rtp if rt == \'flow\' else \'\'},"\n',
     ['d40_revue_rendu_reel_vitesse_2_le_carre_reste_dans_le_cadre_temoin_centre_en_sort']),
    # 8 -- `_rf_lerp_expr` en CHAINE (`_mp_lerp_expr`) : ffmpeg refuse (-22)
    #      au-dela de 93 points dans le crop.
    (B_L7B, SVC,
     '    return (f"if(lt({var},{n(pts[0][0])}),{n(pts[0][1])},"\n'
     '            f"if(lt({var},{n(pts[-1][0])}),{arbre(0, len(pts) - 1)},{n(pts[-1][1])}))")\n',
     '    return _mp_lerp_expr(pts, var)\n',
     ['d40_revue_rf_lerp_expr_arbre_equilibre_memes_valeurs_que_le_lineaire',
      'd40_revue_commande_longue_graphe_par_fichier_rendu_reel_ok']),
    # -- D-41 : autoclips.py, joue par `l7b` [4] -------------------------------
    # 9 -- `windows` replafonnee a 400 fenetres : la fin d'une longue source
    #      n'est jamais examinee.
    (B_L7B, ACL,
     '        if emis:\n'
     '            last_start = s0\n'
     '    return out\n',
     '        if emis:\n'
     '            last_start = s0\n'
     '    return out[:400]\n',
     ['d41_revue_source_1800_s_fenetres_jusqu_a_la_fin',
      'd41_revue_heuristique_voit_toute_la_source_huit_clips_disjoints']),
    # 10 -- le filtre glouton retire des choix du LLM : deux extraits qui se
    #       chevauchent sont rendus tous les deux.
    (B_L7B, ACL,
     '    retenus = _glouton(choix, n, pris, False)\n',
     '    retenus = choix[:n]\n'
     '    pris.extend(c[1] for c in retenus)\n',
     ['d41_revue_llm_choix_chevauchants_filtres_le_mieux_note_garde']),
    # -- D-41 : la route /autoclips (montage_service.py), jouee par `l7b` ------
    # 11 -- `confirm` accepte SANS `max_usd` sur le chemin payant : le plafond
    #       de cout confirme n'est plus exige.
    (B_L7B, SVC,
     '            if (isinstance(max_usd, bool) or not isinstance(max_usd, (int, float))\n',
     '            if max_usd is None:\n'
     '                max_usd = 1e9\n'
     '            elif (isinstance(max_usd, bool) or not isinstance(max_usd, (int, float))\n',
     ['d41_revue_T6_confirm_sans_plafond_lisible_400_sur_le_chemin_payant',
      'l7b_cloture_confirm_sans_max_usd_accepte_sur_texte_connu_et_cache_400_sur_le_chemin_payant']),
    # 12 -- le cache des mots transcrits retire : une relance repaie.
    (B_L7B, SVC,
     '        res = await asyncio.to_thread(_autoclips_stt_lire, cle) if cle else None\n',
     '        res = None\n',
     ['d41_revue_transcription_en_cache_relance_sans_transcribe_ni_confirm']),
    # 13 -- le verrou de transcription en cours retire (cloture T8) : deux
    #       « Lancer » payants concurrents paient deux fois.
    (B_L7B, SVC,
     '            if verrou in _AUTOCLIPS_STT_EN_COURS:\n',
     '            if False:\n',
     ['l7b_cloture_verrou_deux_transcriptions_concurrentes_meme_cle_une_seule_payee']),
    # -- D-34 : pipeline.py, joue par `l7b_notes` ------------------------------
    # 14 -- `min_rating` applique APRES le `limit` : une page filtree est
    #       vide alors que des rendus notes existent plus loin.
    (B_NOTES, PIP,
     '        if min_rating > 0:\n'
     '            stmt = stmt.where(func.coalesce(JobRecord.rating, 0) >= min_rating)\n'
     '        async with async_session_factory() as session:\n'
     '            res = await session.execute(\n'
     '                stmt.order_by(JobRecord.created_at.desc()).offset(offset).limit(limit)\n'
     '            )\n'
     '            return list(res.scalars().all())\n',
     '        async with async_session_factory() as session:\n'
     '            res = await session.execute(\n'
     '                stmt.order_by(JobRecord.created_at.desc()).offset(offset).limit(limit)\n'
     '            )\n'
     '            return [j for j in res.scalars().all() if (j.rating or 0) >= min_rating]\n',
     ['n4_min_rating_3_pagine_juste_sur_deux_pages',
      'n4_min_rating_5_good_take_seul_j05']),
    # -- D-41 / D-34 : la couche, jouee par `edition` --------------------------
    # 15 -- `dzmAcPayload` qui accepte une coche BOOLEENNE : une coche restee
    #       vraie couvre une estimation neuve (revue T6).
    (B_EDIT, JS,
     'if(!t&&v&&typeof v==="object"&&e.payer===v&&v.ok===!0',
     'if(!t&&v&&typeof v==="object"&&(e.payer===v||e.payer===!0)&&v.ok===!0',
     ['ac_confirm_seulement_coche_de_l_estimation_affichee']),
    # 16 -- l'offset du tiroir FIGE : sous filtre, une note qui passe sous le
    #       seuil fait sauter un rendu a « Plus ».
    (B_EDIT, JS,
     'if(dl)setOffset(function(o2){return Math.max(0,o2+dl)})',
     'if(dl)void 0',
     ['l7b_tiroir_offset_suit_le_seuil_au_succes']),
    # 17 -- (cloture T8) les memoires d'un rendu dont le PUT est ENCORE en
    #       cours apres le plafond de 15 s sont videes.
    (B_EDIT, JS,
     'if(noteFile.current[k2]!==att[k2]||(att[k2]&&!fini[k2]))return;',
     'if(noteFile.current[k2]!==att[k2])return;',
     ['l7b_tiroir_recharge_page0_attend_les_notes_en_vol_puis_vide_les_memoires']),
    # -- D-42 : le bundle livre, lu par `bundle` --------------------------------
    # 18 -- la garde d'obsolescence de « Decouper aux changements de plan »
    #       SANS la source : « Remplacer la source » pendant l'analyse ecrit
    #       les coupes de l'ANCIENNE source.
    (B_BUND, BUN,
     'Number(k.start)||0,Number(k.end)||0,svmSrcKey(k.src)].join("|")}\n'
     '    var sg=dzSg(c);\n',
     'Number(k.start)||0,Number(k.end)||0].join("|")}\n'
     '    var sg=dzSg(c);\n',
     ['L7Bb_sous_node_revue_D40_source_remplacee_pendant_l_analyse']),
]

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (1, 1, 1, 2, 1, 3, 3, 2, 2, 2, 1, 3, 4, 1, 6, 3, 1, 1, 4)
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
        print(f"[{i:2d}] {verdict:16s} {banc.split('_', 2)[-1][:-3]:11s} "
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
