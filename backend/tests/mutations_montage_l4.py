# -*- coding: utf-8 -*-
"""Banc de mutations du lot L4 du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l4.py            # toutes
    python tests/mutations_montage_l4.py 0 7 14     # celles-la

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET sur le COMPTE declare (`N_ROUGES`, compare
par main() : verdict `ROUGE(compte)` sinon), 1 des qu'une survit, meurt,
rougit ailleurs ou rougit plus ou moins que la table ne le dit. Modele
EXACT : `mutations_montage_ec.py` (5-uplets, mutation en OCTETS, `ecrire()`
avec retentatives, sha256 restaure dans `finally` par application inverse,
etat MORT distinct de ROUGE) ; `mutations_montage_l3.py` pour les
mutations du service.

CE QU'IL MUTE, ET POURQUOI CES TROIS FICHIERS-LA. Le lot L4 (D-35 presets
de sortie, D-24 loudness deux passes, D-36 file de rendus, D-38 rendu
partiel de la plage) vit des deux cotes du reseau :
  . `backend/app/services/montage_service.py` : `_deliver_dims`,
    `_deliver_resolve`, `_deliver_tail` (sonde `_encoder_ok`, palette GIF,
    `-vn` de l'audio seul), `_loudnorm_chain`, la passe 1 dans `_run`,
    `_range_args`, la file (`q.put_nowait`, statut `queued`), la course de
    threads stab + flow ;
  . `frontend/patches/montage.js` : LA COUCHE, celle que le shim de
    `test_montage_edition.py` execute (`dzmLoudPastille`,
    `dzmDeliverPayload`) ;
  . `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour les
    deux mutations qui ne sont PAS dans la couche mais dans le corps du
    bundle reecrit par la section L4c2 du patcher (`renderPayload`) --
    muter le PATCHER puis rejouer la chaine prouverait seulement que le
    patcher est coherent avec lui-meme ; c'est le fichier que l'application
    charge et que `test_montage_bundle.py` lit.

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. Service -> `l4` ; couche
JS -> `edition` ; bundle livre -> `bundle`. Le banc `bundle` n'est jamais
choisi pour une mutation de la COUCHE : il compare le bloc injecte a
`montage.js` octet pour octet, TOUTE mutation de la couche l'y ferait
rougir et le bruit noierait le signal.

TRAVAIL EN OCTETS. La fin de ligne de chaque fichier est MESUREE a chaque
mutation (`\\r\\n` present -> CRLF ; mesure du 23/09/2026, sommet 00e1b8a :
service 4 707 `\\r\\n` pour 4 707 `\\n`, couche 6 941 / 6 941, bundle
20 447 / 20 447 -- CRLF homogene les trois), les motifs sont ecrits en LF
et remis dans la fin de ligne du fichier ; c'est le sha256 d'APRES qui
prouve la restauration, pas cette phrase. La restauration est une
application INVERSE (les octets d'avant reecrits), JAMAIS un `git
checkout` : le worktree peut porter d'autres changements non commis.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
La restauration est verifiee par sha256 APRES CHAQUE mutation, dans un
`finally`. Un banc qui ne rend pas `=== N passed, M failed ===` ou un code
autre que 0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

LE BANC `l4` REND PAR FFMPEG (sections [M], [5] et [7] : rendus reels, 29 s
au repos). Une mutation du service est donc jouee CONTRE ffmpeg aussi : le
GIF sans palette, l'audio seul sans `-vn`, la loudnorm sans `linear=true`
sont des commandes que ffmpeg ACCEPTE (un rendu moins bon, pas un rendu
mort) -- c'est la ligne qui pinne la forme de la commande qui rougit, et
c'est dit mutation par mutation.

RESULTAT MESURE le 23/09/2026 (worktree epic-fermi-f6adf5, sommet 00e1b8a,
python embarque, un processus par execution de banc) : LES SEIZE SONT
ROUGES, AUCUN SURVIVANT, AUCUN MORT, chacune sur les lignes declarees ;
code de sortie 0.
Comptes des bancs au repos : l4 120/0, edition 294/0, bundle 2092/0.

    #   fonction visee                                    banc     rouges
    0   _deliver_dims sans arrondi pair                   l4       1
    1   preset inconnu -> social_720 et non master        l4       4
    2   hevc sans sonde _encoder_ok (nvenc d'office)      l4       1
    3   GIF sans palettegen/paletteuse                    l4       4
    4   audio seul sans -vn                               l4       6
    5   loudnorm sans linear=true                         l4       6
    6   passe 1 non exigee (echec avale, rendu « sans »)  l4       1
    7   _range_args sans -ss                              l4       9
    8   -t non recalcule sur la plage                     l4       10
    9   file : create_task par item (worker parallele)    l4       5
   10   statut queued non pose (nait generating_video)    l4       2
   11   -threads 1 retire sous la paire stab + flow       l4       3
   12   dzmLoudPastille bornes strictes (< au lieu de <=) edition  1
   13   deliverPayload posant fps hors liste              edition  2
   14   bundle : queue:queue===!0 retire du payload       bundle   4
   15   bundle : renderPayload sans deliverPayload        bundle   7

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  . la n°0 (arrondi pair) ne rougit PAS la ligne `d35_dims_petit_cote_et_pair`
    que le plan visait : ses cas tombent tous PAIRS sans l'arrondi -- seule
    `d35_dims_master_reproduit_le_canvas_et_l_arrondi_est_pair` (un ratio a
    cote impair) le voit ; c'est elle qui est declaree ;
  . la n°2 (sonde hevc) ne rougit qu'UNE ligne : sur CETTE machine (RTX,
    hevc_nvenc repond) `if True:` choisit le meme candidat que la sonde --
    `d35_hevc_prend_nvenc_si_sonde_ok_sinon_libx265` reste verte ; c'est
    `d35_la_sonde_hevc_decide_la_branche` (espion qui force la sonde a False)
    qui accuse. Sur une machine sans NVENC les deux rougiraient ;
  . les n°3, 4, 5 sont jouees CONTRE ffmpeg (rendus reels de [M] et [6]) et
    ffmpeg ACCEPTE les trois commandes mutees : ce sont les pins de FORME
    (palette, `-vn`, `linear=true`) et les espions de /render qui rougissent,
    4 / 6 / 6 lignes -- pas un rendu mort ;
  . la n°7 (sans `-ss`) rougit 9 lignes et la n°8 (`-t` non recalcule) 10 :
    toute la section [4] plus l'espion /render, et pour la n°8 le RENDU REEL
    de la plage [1,2] (`…dure_environ_1_s`) qui dure alors 30 s ;
  . la n°9 (worker parallele) rougit 5 lignes : la serie, mais aussi
    `queued` jamais observe (les trois partent tout de suite), les positions
    qui ne repartent plus a 1 (`_RENDER_PENDING` jamais decremente) et
    l'ordre apres un echec ;
  . la n°11 (`-threads 1`) rougit aussi le rendu reel stab + flow de [7] :
    le pin compte `-threads 1` devant CHAQUE `-i` (revue finale du 23/09 :
    option PAR FICHIER), et le rendu sous charge n'a pas plante cette fois
    (course ALEATOIRE, 3/6 mesures) -- c'est le pin qui parle, jamais le
    plantage ;
  . la n°13 rougit aussi `l4_coeur_pur_…_listes_uniques` : elle compte
    `DZM_DEL_FPS` x5 dans la couche (4 apres la mutation) ;
  . les mutations du bundle rougissent 4 et 7 lignes : la ligne nommee, la
    ligne GENERIQUE `<section>_remplace`, l'ancre `_ancre_libre_1_0_1`
    (la forme mutee n'est plus le remplacement) et la ligne de queue du
    patcher (`DZ_le_patcher_porte…_la_sonde_dit_132`) ; la n°15 rougit en
    plus les DEUX sondes dzcout (`DzTracks` x135 -> 134 : `deliverPayload(`
    retire) et la ligne L4a qui compte `dzDelRef` ;
  . AUCUNE mutation ne rougit sur un seul pin sans comportement, sauf la
    n°2 sur cette machine (dit ci-dessus).

ECARTS AU PLAN, DATES 23/09/2026 : le plan nommait seize candidates ; les
seize sont dans la table, chacune adaptee au code REEL (« preset inconnu ne
retombe pas sur master » = le repli envoye sur social_720 ; « passe 1 non
exigee » = son echec avale par un try/except ; « hevc sans sonde » = `if
True:` ; « queue:!0 retire » = `queue:queue===!0` retire de l'objet passe a
deliverPayload). AUCUNE candidate ecartee.
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
B_L4 = "tests/test_montage_l4.py"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, rouges attendues)
M = [
    # -- le service, joue par `l4` -------------------------------------------
    # 0 -- `_deliver_dims` sans l'arrondi pair : 9:16 a 720 donne 405x720,
    #      yuv420p refuserait la largeur impaire.
    (B_L4, SVC,
     '    return w - w % 2, h - h % 2\n',
     '    return w, h\n',
     ["d35_dims_master_reproduit_le_canvas_et_l_arrondi_est_pair"]),
    # 1 -- preset inconnu qui ne retombe PAS sur master (social_720 a sa
    #      place) : `spec["id"]` dit toujours master, le rendu est a 720.
    (B_L4, SVC,
     '    src = _DELIVER.get(base_id) or _DELIVER[_DELIVER_DEFAUT]\n',
     '    src = _DELIVER.get(base_id) or _DELIVER["social_720"]\n',
     ["d35_preset_inconnu_retombe_sur_master"]),
    # 2 -- `hevc` sans la sonde : le premier candidat (hevc_nvenc) est pris
    #      d'office, une machine sans NVENC rend un job failed.
    (B_L4, SVC,
     '            if _encoder_ok(cand[1]):\n',
     '            if True:\n',
     ["d35_la_sonde_hevc_decide_la_branche"]),
    # 3 -- GIF sans palette : ffmpeg accepte (palette generique 256 couleurs,
    #      tramage grossier) -- c'est le pin de la forme qui rougit.
    (B_L4, SVC,
     '        parts.append(f"[{cur}]{gravure}fps={gfps},split[g0][g1];"\n'
     '                     f"[g0]palettegen[pal];[g1][pal]paletteuse[outv]")\n',
     '        parts.append(f"[{cur}]{gravure}fps={gfps}[outv]")\n',
     ["d35_gif_palettegen_paletteuse_12fps_sans_audio"]),
    # 4 -- audio seul sans `-vn` : la video composee part dans nullsink, ffmpeg
    #      n'a rien a mapper en video -- accepte ; la forme est pinnee.
    (B_L4, SVC,
     '                "-vn", "-map", amap, *ss, "-t", str(round(total, 3)),\n',
     '                "-map", amap, *ss, "-t", str(round(total, 3)),\n',
     ["d35_audio_seul_vn_sans_map_outv_mp3"]),
    # 5 -- `loudnorm` sans `linear=true` : la passe 2 travaille en DYNAMIQUE
    #      (compression), la voix est modelee ; ffmpeg accepte.
    (B_L4, SVC,
     '            f"linear=true:print_format=summary,aresample=48000")\n',
     '            f"print_format=summary,aresample=48000")\n',
     ["d24_chaine_passe_2_exacte_apres_outa_forme_aresample_seule_et_outn_mappe_a_la_place_de_outa"]),
    # 6 -- la passe 1 non exigee : son echec est AVALE, le job rend « sans »
    #      loudness au lieu de passer failed avec le message nomme.
    (B_L4, SVC,
     '                loud_measured = await asyncio.to_thread(\n'
     '                    _loudnorm_pass1, v1, v2, a_clips, music, loudness=loudness,\n'
     '                    w=w, h=h, fps=fps, mix_db=mix, ducking=ducking,\n'
     '                    duration_master=duration_master, adjust_clips=adjust,\n'
     '                    range_out=range_out)\n',
     '                try:\n'
     '                    loud_measured = await asyncio.to_thread(\n'
     '                        _loudnorm_pass1, v1, v2, a_clips, music, loudness=loudness,\n'
     '                        w=w, h=h, fps=fps, mix_db=mix, ducking=ducking,\n'
     '                        duration_master=duration_master, adjust_clips=adjust,\n'
     '                        range_out=range_out)\n'
     '                except Exception:\n'
     '                    loud_measured = None\n',
     ["d24_render_passe_1_en_echec_met_le_job_en_failed_avec_le_message_sans_commande_finale"]),
    # 7 -- `_range_args` sans `-ss` : la plage [2,5] rend les 3 PREMIERES
    #      secondes du montage.
    (B_L4, SVC,
     '    return ["-ss", str(a)], round(min(b, float(total)) - a, 3)\n',
     '    return [], round(min(b, float(total)) - a, 3)\n',
     ["d38_range_2_5_ecrit_ss_2_0_juste_avant_t_3_0_a_la_place_de_t_8"]),
    # 8 -- `-t` non recalcule : `-ss 2` puis `-t 8` (le total) -- la sortie
    #      court jusqu'a la fin du montage, la borne de fin est ignoree.
    (B_L4, SVC,
     '    return ["-ss", str(a)], round(min(b, float(total)) - a, 3)\n',
     '    return ["-ss", str(a)], total\n',
     ["d38_range_2_5_ecrit_ss_2_0_juste_avant_t_3_0_a_la_place_de_t_8",
      "d38_la_fin_est_bornee_au_total"]),
    # 9 -- la file : un `create_task` par item au lieu du worker unique --
    #      trois POST queue:true = trois ffmpeg en parallele, `_RENDER_PENDING`
    #      n'est jamais decremente.
    (B_L4, SVC,
     '        q.put_nowait(_run)\n',
     '        asyncio.get_running_loop().create_task(_run())\n',
     ["d36_les_trois_jobs_en_file_s_executent_en_serie_start_k1_superieur_ou_egal_a_end_k"]),
    # 10 -- `queued` non pose : le job en file nait `generating_video` a 0 %,
    #       la vue Livraison ne sait plus qu'il attend.
    (B_L4, SVC,
     '            status=(JobStatus.QUEUED.value if queue\n'
     '                    else JobStatus.GENERATING_VIDEO.value),\n',
     '            status=JobStatus.GENERATING_VIDEO.value,\n',
     ["d36_le_troisieme_job_nait_queued_progress_0_en_file_lu_par_get_jobs_id"]),
    # 11 -- `-threads 1` retire sous la paire stab + flow : la course des
    #       decodeurs h264 (3/6 sous charge) revient.
    (B_L4, SVC,
     '            for k in [i for i, t in enumerate(cmd) if t == "-i"][::-1]:\n'
     '                cmd[k:k] = ["-threads", "1"]\n',
     '',
     ["t2_stab_et_flow_ensemble_posent_filter_complex_threads_1_juste_avant_le_graphe"]),
    # -- la couche (montage.js), jouee sous node par `edition` ---------------
    # 12 -- `dzmLoudPastille` a bornes strictes : |d| = 1 dB tombe en jaune,
    #       3 dB en rouge.
    (B_EDIT, JS,
     '  return d<=1?"vert":d<=3?"jaune":"rouge"}\n',
     '  return d<1?"vert":d<3?"jaune":"rouge"}\n',
     ["lp_bornes_exactes_1_et_3_dB_vert_jaune_rouge_gris_sans_cible_nan_null_cible_non_numerique"]),
    # 13 -- `dzmDeliverPayload` posant un `fps` hors liste (48) : le backend
    #       repond 400 « Cadence 48 refusee ».
    (B_EDIT, JS,
     'var f=Number(o.fps);if(DZM_DEL_FPS.indexOf(f)>=0)out.fps=f;\n',
     'var f=Number(o.fps);if(isFinite(f)&&f>0)out.fps=f;\n',
     ["pl_bornes_fps_48_omis_60_chaine_pris_loudness_chaine_omise_hors_liste_omise_plage_inversee_ou_decochee_omise_preset_vide_queue_false_base_null_fps_null_vide"]),
    # -- le bundle livre (section L4c2 du patcher), lu par `bundle` ----------
    # 14 -- `queue:queue===!0` retire du payload : « Ajouter a la file » rend
    #       tout de suite (le backend lit `queue` absent = faux).
    (B_BUND, BUN,
     '{range:proj.range,queue:queue===!0}',
     '{range:proj.range}',
     ["L4c_renderPayload_var_b_return_preview_b_sinon_deliverPayload_dzDelRef_range_queue_x1_return_name_x0_measure_intact"]),
    # 15 -- `renderPayload` sans `deliverPayload` : le rendu final part avec le
    #       payload historique, preset / cadence / loudness / plage ignores.
    (B_BUND, BUN,
     '    return preview?_b:DzTracks.deliverPayload(_b,Object.assign({},dzDelRef.current,{range:proj.range,queue:queue===!0}))}\n',
     '    return _b}\n',
     ["L4c_renderPayload_var_b_return_preview_b_sinon_deliverPayload_dzDelRef_range_queue_x1_return_name_x0_measure_intact"]),
]

# LE COMPTE MESURE, compare par main() -- une ligne par mutation de M.
N_ROUGES = (1, 4, 1, 4, 6, 6, 1, 9, 10, 5, 2, 3, 1, 2, 4, 7)
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
