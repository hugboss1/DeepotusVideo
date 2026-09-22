# -*- coding: utf-8 -*-
"""Banc de mutations du lot L3 du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l3.py            # toutes
    python tests/mutations_montage_l3.py 0 9 16     # celles-la

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees, 1 des qu'une survit, meurt ou rougit ailleurs
(la faute que le harnais E-A avait d'abord oubliee, revue du 22/09/2026).

CE QU'IL MUTE, ET POURQUOI CES TROIS FICHIERS-LA. Le lot L3 (D-13 zoom
dynamique, D-15 retime, D-16 stabilisation, D-14 keyframes d'echelle et
d'opacite, D-9 piste d'ajustement) vit des deux cotes du reseau :
  · `backend/app/services/montage_service.py` : `_dz_spec`/`_dz_filter`,
    `_v1_retime`/`_RETIME`, `_v1_stab` et l'entree entiere, `_motion_points`
    et `_mp_cmds`, la toile bornee des overlays, le post-pass `adjust_clips` ;
  · `frontend/patches/montage.js` : LA COUCHE, celle que le shim de
    `test_montage_edition.py` execute (`SRC_PATH`) et que le patcher injecte
    (`dzmDzNorm`, `dzmDzCss`, `dzmRampe`, `dzmKindOf`, `dzmAdjustTrack`,
    `dzmStabNorm`, `dzmMpKeep`) ;
  · `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour les trois
    mutations qui ne sont PAS dans la couche mais dans le corps du bundle
    reecrit par une section du patcher (R_AJ2A, R_AJ7, R_DZ4) -- muter le
    PATCHER prouverait seulement que le patcher est coherent avec lui-meme ;
    c'est le fichier que l'application charge et que `test_montage_bundle.py`
    lit.

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. Backend -> `l3` ; couche
JS -> `edition` (elle joue la couche sous node) ; bundle livre -> `bundle`
(le MIROIR). Le banc `bundle` n'est jamais choisi pour une mutation de la
COUCHE : il compare le bloc injecte a `montage.js` octet pour octet, donc
TOUTE mutation de la couche l'y ferait rougir et le bruit noierait le signal.

TRAVAIL EN OCTETS. Mesure du 23/09/2026, python embarque, sommet 07af074 :
`montage_service.py` 219 712 o en CRLF homogene (4 000 `\\r\\n` pour 4 000
`\\n`), `montage.js` 394 211 o en CRLF (6 442 -- il etait en LF dans l'arbre
le 22/09, mesure du docstring de mutations_montage_l2.py : la fin de ligne
d'un fichier N'EST PAS une constante du depot, on la mesure a chaque
mutation), le bundle 1 885 906 o en CRLF (19 777). Les motifs sont ecrits en
LF et remis dans la fin de ligne du fichier ; c'est le sha256 d'APRES qui le
prouve, pas cette phrase. PIEGE d'ecriture : un motif qui porte un `\\`
(la n°9, `"\\\\;"`) ne se verifie PAS par un heredoc Bash -- le heredoc
desescape les antislashs et compte 0 la ou le fichier en porte un.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
La restauration est verifiee par sha256 APRES CHAQUE mutation, dans un
`finally`. Un banc qui ne rend pas `=== N passed, M failed ===` ou un code
autre que 0/1 est MORT, troisieme etat distinct de ROUGE (faute n°6).

RESULTAT MESURE le 23/09/2026 (worktree epic-fermi-f6adf5, sommet 07af074 +
la cloture, python embarque, un processus par execution de banc) : LES
VINGT-TROIS SONT ROUGES, AUCUN SURVIVANT, chacune sur les lignes declarees ;
code de sortie 0. Une vingt-quatrieme candidate (ci-dessous) a SURVECU et a
ete ecartee. Comptes des bancs au repos : l3 86/0, edition 207/0, bundle
1776/0.

    #   fonction visee                                    banc     rouges
    0   _dz_spec sans clamp de w                          l3       1
    1   _dz_filter avec `t` au lieu de `it`               l3       7
    2   zoompan pose AVANT fps                            l3       1
    3   _v1_retime accepte « nearest »                    l3       2
    4   tblend pose AVANT fps (comme flow)                l3       2
    5   _v1_stab sans borne de zoom                       l3       1
    6   entree stab qui garde -ss                         l3       1
    7   _ff_escape_path retire de input=                  l3       2
    8   _motion_points qui perd `opacity`                 l3       13
    9   _mp_cmds sans la commande plate finale            l3       4
   10   toile non bornee (fh = 2*fw)                      l3       2
   11   adjust_clips pose APRES les titres                l3       1
   12   garde des bornes locales hors clip retiree        l3       2
   13   dzmDzNorm sans borne de w                         edition  1
   14   dzmDzCss sans le signe moins                      edition  1
   15   dzmRampe oublie srcIn                             edition  2
   16   dzmKindOf sans « j »                              edition  2
   17   dzmAdjustTrack en queue                           edition  1
   18   dzmStabNorm sans borne de zoom                    edition  1
   19   dzmMpKeep sans borne                              edition  1
   20   R_AJ2A sans `||sel.kind==="adjust"`               bundle   3
   21   AJ7 sans `c.kind!=="adjust"&&`                    bundle   3
   22   DZ4 sans `o.dz`                                   bundle   4

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  · une candidate du plan, `not effs` retire de la garde du post-pass D-9,
    est un SURVIVANT (0 rouge) et n'est PAS dans la table : depuis la revue
    du 23/09 (0c34b06), `if not bounded: continue` filtre un clip sans effet
    AVANT `build_chain` -- la garde `not effs` est devenue REDONDANTE, et le
    commentaire du service qui la disait « indispensable » a ete corrige
    dans le meme commit que ce harnais. Une mutation qui survit n'entre pas
    dans une table qui promet 0 ;
  · DEUX mutations ont d'abord TUE le banc l3 au lieu de le faire rougir
    (verdict MORT) : la n°3 (`_RETIME["nearest"]` -> KeyError) et la n°8
    (5-uplets -> IndexError sur `q[5]`, dans OVBUILD PUIS dans l'appel
    direct du rendu reel, l. 744). Les gardes du banc n'attrapaient que
    (TypeError, ValueError) -- la faute n°6 dans le banc lui-meme. Elles
    attrapent desormais toute exception et rendent un temoin nomme ; les
    deux mutations rougissent 2 et 13 lignes. C'est ce harnais qui l'a vu,
    pas la relecture ;
  · la n°1 (`t` au lieu de `it`) rougit SEPT lignes dont les quatre du
    rendu reel : zoompan ne connait pas `t`, ffmpeg refuse l'expression --
    seule la mesure sur ffmpeg voit qu'un mauvais nom de variable n'est pas
    qu'une faute de chaine ;
  · la n°6 (entree stab qui garde `-ss`) ne rougit QU'UNE ligne : la ligne
    du gap pinne les index `[0:v]`/`[1:v]`, que `-ss` ne deplace pas ;
  · la n°7 (chemin non echappe) rougit aussi le rendu reel : le `:` du
    lecteur Windows est lu comme separateur d'option, ffmpeg refuse ;
  · la n°20/21/22 rougissent TROIS ou QUATRE lignes : la ligne nommee de la
    section [D-9]/[D-13], la ligne GENERIQUE que la boucle sur `P.PATCHES`
    emet pour chaque section (`<section>_remplace`), la ligne de la queue du
    patcher (`DZ_le_patcher_porte_…`) qui compte chaque remplacement dans le
    bundle -- et, pour la n°22, RT2 qui pinne le bloc DZ4 entier (`o.dz`
    et `o.retime` sont dans le MEME remplacement) ; c'est le miroir qui
    parle, pas un doublon.

(Le detail exact des noms de lignes est celui que le script IMPRIME ; la
colonne « rouges » ci-dessus en donne le COMPTE mesure, pas un resume.)
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
SVC = "backend/app/services/montage_service.py"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"
B_L3 = "tests/test_montage_l3.py"

# Le post-pass D-9, ENTIER, tel qu'il est dans le service (0c34b06) : la
# n°11 le RETIRE de sa place (avant les titres) et le REPOSE apres la boucle
# des titres. Recopie a l'octet -- l'assert d'unicite le verifie.
_AJ_BLOC = '''    for j, aj in enumerate(adjust_clips or []):
        if not isinstance(aj, dict):
            continue
        try:
            a0 = max(0.0, float(aj.get("start") or 0))
            a1 = min(float(total), float(aj.get("end") or 0))
        except (TypeError, ValueError):
            continue
        effs = [e for e in (aj.get("effects") or [])
                if isinstance(e, dict) and e.get("type") in _fx.EFFECTS]
        if a1 - a0 < 0.05 or not effs:
            continue
        bounded = []
        for e in effs:
            e2 = dict(e)
            try:
                lt0 = max(0.0, float(e.get("t0") or 0))
                lt1 = (float(e.get("t1")) if e.get("t1") is not None
                       else (a1 - a0))
            except (TypeError, ValueError):
                lt0, lt1 = 0.0, a1 - a0
            e2["t0"] = round(a0 + lt0, 3)
            e2["t1"] = round(min(a1, a0 + lt1), 3)
            # Revue (23/09/2026) : bornes locales HORS du clip ou < 0,05 s
            # → _timed rendrait la chaîne NUE (effet plein cadre, 0..total,
            # mesuré : `[n0]vignette=angle=0.600[aj0]` sans sendcmd). Rien.
            if e2["t1"] - e2["t0"] < 0.05:
                continue
            bounded.append(e2)
        if not bounded:
            continue
        parts += _fx.build_chain(bounded, cur, f"aj{j}", f"ajfx{j}",
                                 {"w": w, "h": h, "dur": total, "fps": fps})
        cur = f"aj{j}"
'''
_TT_BOUCLE = ('    for j, tpath in enumerate(titles_ass or []):\n'
              '        parts.append(f"[{cur}]{subtitles_filter(tpath)}[tt{j}]")\n'
              '        cur = f"tt{j}"\n')

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, rouges attendues)
M = [
    # ── D-13, le zoom dynamique ──────────────────────────────────────────
    # 0 — `_dz_spec` sans le clamp de w : une fenetre de 0,02 ou de 3 entre
    #     dans le filtergraph (z = 50, ou z < 1 que zoompan refuse en silence).
    (B_L3, SVC,
     '        out["w" + i] = max(0.1, min(1.0, out["w" + i]))\n',
     '        out["w" + i] = out["w" + i]\n',
     ["d13_les_bornes_sont_tenues_w_min_0_1_et_x_dans_le_cadre"]),
    # 1 — `_dz_filter` avec `t` : zoompan ne connait pas `t` (son horloge est
    #     `it`) ; l'expression est refusee par ffmpeg -- le rendu reel le voit.
    (B_L3, SVC,
     '    u = f"clip(it/{n(d)},0,1)"\n',
     '    u = f"clip(t/{n(d)},0,1)"\n',
     ["d13_le_temps_est_it_sur_la_duree_jamais_t",
      "d13_la_duree_du_zoom_est_celle_du_segment",
      "d13_avec_vitesse_la_duree_du_zoom_est_la_duree_timeline_pas_source"]),
    # 2 — le zoompan pose AVANT `fps=` (branche sans vitesse) : sur un flux
    #     retime il dupliquerait chaque image ; ici l'ordre pinne rougit.
    (B_L3, SVC,
     'f"crop={w}:{h},setsar=1,fps={fps}{dzp},format=yuv420p")\n',
     'f"crop={w}:{h},setsar=1{dzp},fps={fps},format=yuv420p")\n',
     ["d13_avec_dz_le_zoompan_est_pose_apres_fps_et_avant_format"]),
    # ── D-15, le retime ──────────────────────────────────────────────────
    # 3 — `_v1_retime` accepte « nearest » : `_RETIME["nearest"]` n'existe
    #     pas, la commande avec vitesse MEURT (KeyError) au lieu de rester
    #     l'historique.
    (B_L3, SVC,
     '    return v if isinstance(v, str) and v in _RETIME else None\n',
     '    return v if isinstance(v, str) and (v in _RETIME or v == "nearest") else None\n',
     # MESURE : cette mutation TUAIT le banc l3 (KeyError non attrape par
     # BUILD) -- MORT au lieu de ROUGE. BUILD attrape desormais toute
     # exception et rend un temoin `KeyError: 'nearest'` ; deux lignes.
     ["d15_nearest_absent_ou_inconnu_rend_none",
      "d15_un_retime_inconnu_avec_vitesse_reste_l_historique"]),
    # 4 — tblend pose AVANT `fps=`, comme flow : (A+B)/2,(A+B)/2,… tout flou
    #     (mesure de la revue du 22/09). DEUX retouches : le retime part du
    #     setpts quel qu'il soit, et fps= ne le porte plus.
    (B_L3, SVC,
     [("{rtp if rt == 'flow' else ''},\"\n", "{rtp},\"\n"),
      ("f\"fps={fps}{rtp if rt == 'blend' else ''}{dzp},format=yuv420p\")\n",
       "f\"fps={fps}{dzp},format=yuv420p\")\n")],
     None,
     ["d15_blend_pose_tblend_average_apres_fps_avant_format",
      "d15_avec_dz_l_ordre_est_setpts_fps_tblend_zoompan_format"]),
    # ── D-16, la stabilisation ───────────────────────────────────────────
    # 5 — `_v1_stab` sans la borne de zoom : `zoom=-80` part a vidstabtransform.
    (B_L3, SVC,
     '            "zoom": num("zoom", -30, 30, 0)}\n',
     '            "zoom": num("zoom", -1e9, 1e9, 0)}\n',
     ["d16_stab_est_clampe_smooth_1_100_zoom_m30_30_crop_black_ou_keep"]),
    # 6 — l'entree stabilisee GARDE `-ss` : le .trf est indexe par image
    #     d'entree, un `-ss` decale toutes les transformations (mesure du
    #     22/09) -- et le trim de la chaine coupe une seconde fois.
    (B_L3, SVC,
     '                else:\n                    inputs.extend(["-i", str(s["path"])])\n',
     '                else:\n                    if s["src_in"] > 0:\n'
     '                        inputs.extend(["-ss", str(s["src_in"])])\n'
     '                    inputs.extend(["-i", str(s["path"])])\n',
     ["d16_avec_stab_l_entree_n_est_plus_tronquee_par_ss_t"]),
    # 7 — `_ff_escape_path` retire de `input=` : `C:\\…` nu dans un
    #     filtergraph, le `:` est lu comme separateur d'option.
    (B_L3, SVC,
     "                pre = (f\"vidstabtransform=input='{_ff_escape_path(trf)}':\"\n",
     "                pre = (f\"vidstabtransform=input='{trf}':\"\n",
     ["d16_le_chemin_trf_est_echappe_comme_un_ass"]),
    # ── D-14, les keyframes d'echelle et d'opacite ───────────────────────
    # 8 — `_motion_points` qui perd `opacity` : 5-uplets, l'opacite animee
    #     disparait de tout le chemin (sendcmd, colorchannelmixer@mpo).
    (B_L3, SVC,
     '                            ("opacity", 0.0, 1.0)):\n',
     '                            ):\n',
     # MESURE : TUAIT le banc DEUX fois (IndexError `q[5]` dans OVBUILD, puis
     # dans l'appel direct du rendu reel, l. 744) -- les deux gardes du banc
     # n'attrapaient que (TypeError, ValueError). Elargies ; treize lignes.
     ["d14_les_points_portent_scale_et_opacity_ou_none",
      "d14_scale_clampe_0_05_3_opacity_0_1_absent_none",
      "d14_scale_ou_opacity_invalide_retombe_a_none_sans_tuer_le_point"]),
    # 9 — `_mp_cmds` sans la commande plate finale : apres la derniere cle,
    #     `aa` retombe sur la valeur INITIALE (sendcmd ne cloue rien). Motif
    #     avec `\\\\;` : verifie par CE script, jamais par un heredoc.
    (B_L3, SVC,
     '    return "\\\\;".join(segs + [f"{n(pairs[-1][0])} {target} {opt} {fmt(pairs[-1][1])}"])\n',
     '    return "\\\\;".join(segs)\n',
     ["d14_mp_cmds_une_commande_expr_par_segment_plus_une_plate_finale",
      "d14_mp_cmds_une_seule_cle_est_une_commande_plate_sans_segment",
      "d14_mp_cmds_8_points_sur_56_s_tiennent_en_moins_de_420_caracteres"]),
    # 10 — la toile NON bornee (fh = 2·fw) : en 1080p a smax 3, 5760×11520
    #      au lieu de 5760×3240 -- quatre fois la memoire pour des lignes que
    #      le cadre ne montre jamais (y clampe −0,5..1,5).
    (B_L3, SVC,
     '                fh = max(2, min(2 * fw, 3 * h) // 2 * 2)\n',
     '                fh = max(2, 2 * fw)\n',
     ["d14_la_toile_est_rognee_a_3h_en_hauteur_1080p_smax_3_donne_5760x3240"]),
    # ── D-9, la piste d'ajustement ───────────────────────────────────────
    # 11 — le post-pass pose APRES les titres : un carton passe SOUS la
    #      vignette au lieu d'etre au-dessus. DEUX retouches : le bloc est
    #      retire de sa place puis repose apres la boucle `[tt{j}]`.
    (B_L3, SVC,
     [(_AJ_BLOC, ""), (_TT_BOUCLE, _TT_BOUCLE + _AJ_BLOC)],
     None,
     ["d9_l_ajustement_precede_les_titres_et_s1"]),
    # 12 — la garde des bornes locales HORS du clip retiree : `_timed` rend la
    #      chaine NUE et l'effet couvre TOUT le film (mesure avant 0c34b06).
    (B_L3, SVC,
     '            if e2["t1"] - e2["t0"] < 0.05:\n                continue\n',
     '',
     ["d9_des_bornes_locales_hors_du_clip_ignorent_l_effet_jamais_plein_cadre",
      "d9_des_bornes_locales_trop_courtes_ignorent_l_effet_jamais_plein_cadre"]),
    # ── la couche (montage.js), jouee sous node par `edition` ────────────
    # 13 — `dzmDzNorm` sans la borne de w : le client envoie ce que le
    #      backend clampe, et la <video> en direct le montre tel quel.
    (B_EDIT, JS,
     '    o["w"+s]=Math.max(.1,Math.min(1,o["w"+s]));\n',
     '    o["w"+s]=o["w"+s];\n',
     ["dz_norm_tient_les_memes_bornes_que_le_backend"]),
    # 14 — `dzmDzCss` sans le signe moins : la <video> glisse a l'OPPOSE de la
    #      fenetre (translate +33 % au lieu de −33 %).
    (B_EDIT, JS,
     'return "translate("+f(-r.x*s*100)+"%, "+f(-r.y*s*100)+"%) scale("+f(s)+")"}',
     'return "translate("+f(r.x*s*100)+"%, "+f(r.y*s*100)+"%) scale("+f(s)+")"}',
     ["dz_css_est_une_translation_puis_une_echelle_origine_0_0"]),
    # 15 — `dzmRampe` oublie srcIn : la partie droite rejoue la source depuis
    #      le DEBUT du plan au lieu de continuer a t.
    (B_EDIT, JS,
     '  if(c.srcIn!=null||c.src)R.srcIn=dzmR3((Number(c.srcIn)||0)+(t-s)*sp);\n',
     '',
     ["rt_rampe_fend_a_t_et_pose_les_deux_vitesses_srcin_propage_a_l_ancienne_vitesse",
      "rt_rampe_ne_rond_pas_la_vitesse_et_srcin_suit_la_vitesse_fine"]),
    # 16 — `dzmKindOf` sans « j » : `j1` redevient une piste VIDEO -- la
    #      timeline lui cherche une vignette et une seconde j1 se pose.
    (B_EDIT, JS,
     'k==="t"?"title":k==="j"?"adjust":"video"}',
     'k==="t"?"title":"video"}',
     ["aj_kind_j_est_le_cinquieme_genre",
      "aj_track_pose_j1_sous_t1_au_dessus_de_v2_idempotent"]),
    # 17 — `dzmAdjustTrack` en queue : j1 arrive sous les pistes audio au
    #      lieu d'etre sous T1, au-dessus de V2.
    (B_EDIT, JS,
     'out.splice(dzmTitresAt(list),0,dzmSkin("j1","adjust"));',
     'out.push(dzmSkin("j1","adjust"));',
     ["aj_track_pose_j1_sous_t1_au_dessus_de_v2_idempotent"]),
    # 18 — `dzmStabNorm` sans la borne de zoom (le miroir de la n°5).
    (B_EDIT, JS,
     'zoom:n(raw.zoom,-30,30,0)}}',
     'zoom:n(raw.zoom,-1e9,1e9,0)}}',
     ["sb_norm_tient_les_bornes_du_backend_et_rend_null_hors_on"]),
    # 19 — `dzmMpKeep` sans borne : un `scale:9` est garde par le point, le
    #      backend le ramene a 3 sans le dire.
    (B_EDIT, JS,
     'np[k]=Math.min(b[1],Math.max(b[0],Math.round(v*b[2])/b[2]))',
     'np[k]=Math.round(v*b[2])/b[2]',
     ["kf_keep_reporte_le_patch_sinon_le_point_ecrase_avec_les_bornes_du_backend"]),
    # ── le bundle livre (sections du patcher), lu par `bundle` ───────────
    # 20 — R_AJ2A sans `||sel.kind==="adjust"` : le rack VFX ne s'ouvre plus
    #      sur un clip d'ajustement (sans src), l'inspecteur reste muet.
    (B_BUND, BUN,
     'if(d&&d.Stack&&sel&&((sel.src&&trackKind(sel.tr)==="video")||sel.kind==="adjust"))',
     'if(d&&d.Stack&&sel&&((sel.src&&trackKind(sel.tr)==="video")))',
     ["D9_AJ2_le_rack_VFX_accepte_un_clip_d_ajustement_et_dit_l_apercu"]),
    # 21 — AJ7 sans `c.kind!=="adjust"&&` : la garde amont de vfxAddTo refuse
    #      tout clip sans src -- « Vignette » sur j1u1 laisse `effects []`
    #      (la preuve ecran de la revue du 23/09).
    (B_BUND, BUN,
     'if(c.kind!=="adjust"&&!c.src){fireNote(',
     'if(!c.src){fireNote(',
     ["D9_AJ7_la_pose_d_un_effet_atteint_le_clip_d_ajustement_et_garde_V1"]),
    # 22 — DZ4 sans `o.dz` : le payload de rendu ne porte plus le zoom, le
    #      480p rend le plan sans zoom pendant que le lecteur le montre.
    (B_BUND, BUN,
     'var dzD=c.tr==="v1"&&DzTracks.dzOf(c);if(dzD)o.dz=dzD;',
     'var dzD=c.tr==="v1"&&DzTracks.dzOf(c);',
     ["DZ4_le_payload_joint_dz_seulement_s_il_existe"]),
]
# ECARTEE, MESUREE le 23/09/2026 (SURVIVANT, 0 rouge) : `not effs` retire de
# `if a1 - a0 < 0.05 or not effs:` -- `if not bounded: continue` (0c34b06)
# filtre deja un clip sans effet AVANT build_chain. Le commentaire du service
# qui disait la garde « indispensable » a ete corrige dans le meme commit.


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
        # LE MOTIF EST ECRIT EN LF ET REMIS DANS LA FIN DE LIGNE DU FICHIER :
        # les trois fichiers sont en CRLF le 23/09 (montage.js ne l'etait pas
        # le 22/09). Le sha256 d'apres verifie l'aller-retour.
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
        else:
            verdict = "ROUGE"
        bilan.append((i, verdict, sorted(rg), manquants))
        print(f"[{i:2d}] {verdict:16s} {banc.split('_')[-1][:-3]:11s} "
              f"{pathlib.Path(rel).name:24s} {paires[0][0].strip()[:40]!r}")
        print(f"     rouges({len(rg)})={sorted(rg)}")
        if manquants:
            print(f"     MANQUANTS={manquants}")
        print(f"     sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:2] for b in bilan], ensure_ascii=False))
    # LU PAR CODE DE SORTIE, jamais par grep : 1 des qu'une mutation survit,
    # meurt ou rougit ailleurs que la ligne nommee.
    sys.exit(0 if bilan and all(v == "ROUGE" for _, v, _, _ in bilan) else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
