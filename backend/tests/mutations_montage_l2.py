# -*- coding: utf-8 -*-
"""Banc de mutations du lot L2 du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l2.py            # les dix-sept
    python tests/mutations_montage_l2.py 0 9 16     # celles-la

CE QU'IL MUTE, ET POURQUOI CES CINQ FICHIERS-LA. Le lot L2 vit des deux
cotes du reseau et dans TROIS artefacts livres, pas un :
  · `backend/app/services/montage_service.py` : les 58 `xfade`, leurs six
    familles, `transitions_catalog`, le chainage `titles_ass`, `_prev_w` ;
  · `backend/app/services/titles.py` : `title_spec` et `_ass_text` ;
  · `frontend/patches/montage.js` : LA COUCHE, pas le bundle -- c'est elle
    que le shim de `test_montage_edition.py` execute (son `SRC_PATH` la
    nomme) et c'est elle que le patcher injecte ;
  · `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour les
    deux mutations qui ne sont PAS dans la couche mais dans le corps du
    bundle reecrit par une section (`trackKind`, le filtre du payload) --
    meme raison que `mutations_cout_pastille.py` : c'est le fichier que
    l'application charge, et c'est lui que `test_montage_bundle.py` lit ;
  · `frontend/dist/shared/montage.css` : la feuille neuve du lot, lue elle
    aussi par le banc bundle (`_MC`).

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. Backend -> `l2` ;
couche JS de D-20/D-12/D-21 -> `edition` (il joue la couche sous node) ;
bundle livre et `montage.css` -> `bundle` (le MIROIR). Le banc `bundle` n'est
jamais choisi pour une mutation de la COUCHE : il compare le bloc injecte a
`montage.js` octet pour octet, donc TOUTE mutation de la couche l'y ferait
rougir et le bruit noierait le signal (meme raison qu'en L0/L1).

TRAVAIL EN OCTETS, AVEC UNE PRECAUTION DE PLUS QU'EN L0/L1. Mesure du
22/09/2026, python embarque : `montage.js` 360 548 octets et `montage.css`
82 049 octets sont en LF DANS L'ARBRE (zero `\\r\\n`), `montage_service.py`
190 917 o et `titles.py` 25 240 o sont en CRLF (3 515 et 543), et le bundle
1 851 202 o est en CRLF homogene (19 320 `\\r\\n` pour 19 320 `\\n`). Les
motifs sont donc ecrits en LF et remis dans la fin de ligne du fichier, comme
dans `mutations_cout_pastille.py` -- et c'est le sha256 d'APRES qui le
prouve, pas cette phrase.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture) :
une chaine trouvee deux fois muterait deux sites et le verdict ne dirait plus
lequel des deux la ligne rouge accuse. C'EST UNE MESURE QUI A SERVI : la
mutation n°11 (`trackKind` sans le genre « title ») ne peut PAS s'ecrire sur
sa seule ligne de retour -- `dzmKindOf`, de la couche injectee, porte le
MEME texte a l'octet pres dans le bundle (2 occurrences). Elle est donc
ancree sur la declaration complete. La restauration est verifiee par sha256
APRES CHAQUE mutation, dans un `finally`.

FAUTE N°6, DANS CE SCRIPT LUI-MEME. Un banc rend 0 (tout vert) ou 1 (des
rouges) ; tout autre code, ou une sortie sans `=== N passed`, veut dire qu'il
est MORT au lieu de rougir. On rend alors un troisieme etat (`MORT`) plutot
que de lire une liste de rouges vide comme « rien n'est casse ».

RESULTAT MESURE le 22/09/2026 (worktree sweet-euclid-d6d915, sommet 9078055,
python embarque, un processus par execution de banc) : LES DIX-SEPT SONT
ROUGES, AUCUN SURVIVANT, et chacune rougit EXACTEMENT les lignes declarees
ci-dessous. Les fichiers sont restaures a l'octet apres chacune (sha256
verifie). Comptes des bancs au repos : bundle 1636/0, edition 158/0,
historique 51/0, projets 159/0, l2 77/0.

    #   fonction visee                        banc     rouges
    0   _XFADE_FAMILIES sans « zooms »        l2       5
    1   _XFADE_LIVE elargi a dissolve         l2       1
    2   transitions_catalog sans `live`       l2       2
    3   dzmTransList sans « coupe » en tete   edition  5
    4   dzmTransLabel ignore le catalogue     edition  1
    5   dzmVeil sans la garde du voisin       edition  2
    6   dzmVeil alpha constant                edition  5
    7   title_spec accepte le texte vide      l2       5
    8   _ass_text ecrit un BOM                l2       1
    9   titles_ass chaine APRES S1            l2       2
   10   dzmTitleNew pose `src:{}`             edition  1
   11   trackKind sans k==="t"                bundle   59
   12   dzmTitleTrack en queue                edition  2
   13   _prev_w sans OverflowError            l2       1
   14   dzmTitleUpdate sans borne 24..200     edition  1
   15   payload rendu filtre `c.src` seul     bundle   6
   16   pause CSS [data-fam] retiree          bundle   1

CINQ CHOSES QUE CETTE TABLE A MESUREES, ET QUI NE SE DEVINAIENT PAS :
  · la n°0 rougit CINQ lignes et non deux : amputer une famille retire aussi
    `zoomin/squeezeh/squeezev` des CLES de `_XFADE` (elles n'y entrent que
    par `_XFADE.update` sur les familles), donc la table des 58, la route et
    les libelles parlent eux aussi ;
  · la n°4 laisse VERTE la ligne qui dit « le catalogue prime sur
    l'historique » : sa fixture donne le MEME libelle des deux cotes pour
    `fade`. La ligne est CREUSE, et c'est ce script qui le montre (detail
    et correctif d'un mot en commentaire de la n°4) ;
  · la n°6 (alpha constant) ne touche PAS `vl_au_raccord_le_voile_noir_est
    _plein` : au raccord exact la formule rend deja 1, et un alpha constant
    de 1 y est JUSTE. Ce sont la montee, le bord de fenetre, le choix entre
    deux jonctions proches et le croise des bornes qui voient la pente --
    une ligne qui ne mesure qu'UN POINT ne peut pas voir une pente ;
  · la n°7 laisse VERTE `d21_sans_texte_pas_de_titre`, qui n'eprouve que la
    cle `text` ABSENTE, jamais le texte PRESENT MAIS VIDE (commentaire de la
    n°7). Quatre autres lignes attrapent la panne par ricochet ;
  · la n°11 rougit CINQUANTE-NEUF lignes, et ce n'est pas du bruit gratuit :
    `trackKind` est l'une des tranches de cablage que le banc bundle EXTRAIT
    du bundle livre et EXECUTE sous node (`_KIND`), si bien que la casser
    fait tomber tout le shim `js_*` avec elle. La ligne qui la NOMME
    (`D21_TT1_trackKind_connait_un_quatrieme_genre`) est bien dans le lot ;
    aucun autre banc ne lit le bundle livre, donc il n'y a pas de cible plus
    etroite a lui donner.

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
TI = "backend/app/services/titles.py"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
CSS = "frontend/dist/shared/montage.css"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"
B_L2 = "tests/test_montage_l2.py"

# (banc, fichier, ancien, nouveau, lignes attendues rouges)
# `ancien` peut etre une LISTE de couples (ancien, nouveau) appliques dans
# l'ordre quand une seule panne demande deux retouches -- voir la n°9.
M = [
    # ── D-20, le catalogue des transitions ───────────────────────────────
    # 0 — une famille AMPUTEE. Les six familles sont la SEULE autorite : les
    #     58 noms n'entrent dans `_XFADE` que par `_XFADE.update` sur elles,
    #     et le catalogue servi les recopie. Retirer « zooms » fait donc
    #     disparaitre `zoomin/squeezeh/squeezev` de partout d'un coup, et
    #     c'est ce qui rend la mutation interessante : une famille perdue
    #     n'est pas une case vide dans une grille, c'est trois transitions
    #     qui retombent EN SILENCE sur la coupe franche a 0,04 s.
    (B_L2, SVC,
     '    "zooms":       {"label": "zooms",       "noms": ["zoomin", "squeezeh", "squeezev"]},\n',
     "",
     ["d20_six_familles_nommees", "d20_chaque_xfade_a_une_famille_et_une_seule",
      "d20_les_58_xfade_sont_des_cles_de_la_table"]),
    # 1 — `_XFADE_LIVE` elargi a `dissolve` : le catalogue marque « live »
    #     une transition que `DZM_VEIL` ne sait pas voiler. La tuile perd son
    #     « visible apres Preview » et ne joue pourtant rien.
    (B_L2, SVC,
     '_XFADE_LIVE = ("fade", "fadeblack", "fadewhite")',
     '_XFADE_LIVE = ("fade", "fadeblack", "fadewhite", "dissolve")',
     ["d20_le_direct_ne_couvre_que_les_fondus_simples"]),
    # 2 — le catalogue servi SANS le drapeau `live` : le client ne peut plus
    #     dire lesquelles se jouent en direct, et `dzmTransLive` replie sur
    #     « seule `cut` est directe ».
    (B_L2, SVC,
     ', "live": n in _XFADE_LIVE}',
     "}",
     ["d20_la_route_rend_les_familles_et_le_direct"]),
    # 3 — la galerie SANS la famille « coupe » en tete : la coupe franche,
    #     qui est le defaut de tout raccord, n'a plus de tuile du tout (elle
    #     est aussi exclue des « historiques » par le filtre qui suit).
    (B_EDIT, JS,
     'var inCat={},out=[{id:"coupe",label:"coupe",items:[{id:"cut",label:dzmTransLabel("cut",lg,cat),live:!0}]}];',
     "var inCat={},out=[];",
     ["tl_la_liste_commence_par_les_coupes_puis_les_familles",
      "tl_cut_reste_en_tete"]),
    # 4 — `dzmTransLabel` ignore le catalogue et ne lit plus que les sept
    #     paires historiques : les 51 noms neufs s'affichent en anglais nu
    #     (« wipetl »), et un nom commun aux deux sources prend le vieux
    #     libelle au lieu du francais du service.
    (B_EDIT, JS,
     "if(it.id===id&&it.label)return String(it.label)}",
     "if(!1)return String(it.label)}",
     ["tl_le_libelle_vient_du_catalogue_puis_de_l_historique_puis_du_nom"]),
    # `tl_le_catalogue_prime_sur_l_historique_pour_un_nom_commun` N'EST PAS
    # DECLAREE ICI, ET C'EST UNE MESURE : elle reste VERTE sous cette
    # mutation. Son montage dit `transLabel("fade",LEG,CAT)` doit rendre
    # « fondu » -- mais `LEG` porte `["fade","fondu"]` et `CAT` porte
    # `{id:"fade",label:"fondu"}` : les DEUX sources donnent le MEME mot,
    # donc la ligne ne peut pas separer « le catalogue prime » de « c'est
    # l'historique qui a parle », ce que son commentaire affirme pourtant
    # etre sa raison d'etre. Elle est CREUSE. Le correctif tient en un mot
    # dans la fixture du banc (l. 280 de test_montage_edition.py) :
    # `["fade","fondu simple"]` cote LEG -- non applique ici, ce script ne
    # touche pas aux bancs.
    # ── D-12, le voile du lecteur vivant ─────────────────────────────────
    # 5 — le voile SANS la garde du voisin gauche : le tout premier clip de
    #     V1, qui n'a aucune jonction a fondre, se met a noircir au temps 0,
    #     et un trou de plus d'un dixieme devient une jonction.
    (B_EDIT, JS,
     "var g=dzmVoisins(cs,c).g;if(!g)continue;",
     "",
     ["vl_le_premier_clip_n_a_aucune_jonction_a_fondre",
      "vl_un_trou_de_plus_d_un_dixieme_n_est_pas_une_jonction"]),
    # 6 — l'alpha CONSTANT au lieu de triangulaire : le voile ne monte ni ne
    #     descend, il s'allume plein sur toute la fenetre et s'eteint net.
    #     `vl_au_raccord_le_voile_noir_est_plein` reste VERTE a bon droit --
    #     au raccord exact, la formule rend deja 1.
    (B_EDIT, JS,
     "var a=dzmR3(1-Math.abs(v-t0)/(s/2));",
     "var a=1;",
     ["vl_la_montee_et_la_descente_valent_une_moitie_chacune",
      "vl_au_bord_exact_de_la_fenetre_il_n_y_a_plus_de_voile"]),
    # ── D-21, les cartons de titre ───────────────────────────────────────
    # 7 — `title_spec` accepte le texte VIDE : un carton sans un mot est
    #     grave quand meme (un `.ass` de plus, un maillon ffmpeg de plus,
    #     rien a l'ecran), et la route d'apercu rend 200 au lieu de 400.
    (B_L2, TI,
     "    if not text:\n        return None\n",
     "",
     ["d21_l_apercu_sans_texte_est_un_400",
      "d21_le_clip_titre_sans_texte_est_compte_comme_ignore"]),
    # `d21_sans_texte_pas_de_titre` N'EST PAS DECLAREE, ET C'EST UNE MESURE :
    # elle reste VERTE sous cette mutation. Elle passe `{"template":"cta"}`,
    # une entree SANS LA CLE `text` -- et c'est la garde d'AVANT
    # (`isinstance(t.get("text"), str)`) qui la refuse, pas celle-ci. Le cas
    # qui manque au banc est le texte PRESENT MAIS VIDE (`""` ou `"   "`),
    # que quatre autres lignes attrapent par ricochet (la collecte, le rendu,
    # la route d'apercu) mais qu'aucune ne NOMME. Ligne manquante :
    # `title_spec({"title":{"template":"cta","text":"   "},...}) is None`.
    # 8 — le `.ass` ecrit AVEC un BOM : libass decale la premiere ligne et
    #     rien dans ffmpeg ne le signale. Meme regle que `_subs_ass`.
    (B_L2, TI,
     '    tmp.write_bytes(_ass_text(spec, canvas).encode("utf-8"))',
     '    tmp.write_bytes(_ass_text(spec, canvas).encode("utf-8-sig"))',
     ["d21_le_fichier_ass_existe_sans_bom"]),
    # 9 — les titres graves APRES S1. DEUX remplacements, et il en faut deux :
    #     la boucle est RETIREE de sa place (avant S1) et REPOSEE apres, avec
    #     le maillon `[s1]` qu'il faut alors nommer. La commande reste valide
    #     -- c'est tout le probleme : rien ne plante, les sous-titres passent
    #     simplement SOUS les cartons de titre au lieu d'etre au-dessus.
    (B_L2, SVC,
     [('    for j, tpath in enumerate(titles_ass or []):\n'
       '        parts.append(f"[{cur}]{subtitles_filter(tpath)}[tt{j}]")\n'
       '        cur = f"tt{j}"\n', ""),
      ('    if subs_ass:\n'
       '        parts.append(f"[{cur}]{subtitles_filter(subs_ass)},"\n'
       '                     f"format=yuv420p[outv]")\n'
       '    else:\n'
       '        parts.append(f"[{cur}]format=yuv420p[outv]")\n',
       '    if subs_ass:\n'
       '        parts.append(f"[{cur}]{subtitles_filter(subs_ass)}[s1]")\n'
       '        cur = "s1"\n'
       '    for j, tpath in enumerate(titles_ass or []):\n'
       '        parts.append(f"[{cur}]{subtitles_filter(tpath)}[tt{j}]")\n'
       '        cur = f"tt{j}"\n'
       '    parts.append(f"[{cur}]format=yuv420p[outv]")\n')],
     None,
     ["d21_le_titre_est_grave_avant_les_sous_titres"]),
    # 10 — le carton neuf pose un `src` (vide) : il cesse d'etre un clip SANS
    #      source, la timeline lui cherche une vignette et le backend le
    #      compte comme un plan video.
    (B_EDIT, JS,
     'return {tr:piste,kind:"title",id:dzmUniqueId(clips,piste+"u"+n),',
     'return {tr:piste,kind:"title",src:{},id:dzmUniqueId(clips,piste+"u"+n),',
     ["tt_le_carton_neuf_est_un_clip_sans_source"]),
    # 11 — `trackKind` du BUNDLE oublie le quatrieme genre : `t1` redevient
    #      une piste VIDEO pour les seize sites du bloc sonvfx, qui lui
    #      rendent alors le depot d'asset, la pile d'effets et le mixage.
    #      ANCREE SUR LA DECLARATION ENTIERE : la ligne de retour seule
    #      existe DEUX fois dans le bundle (`dzmKindOf`, de la couche).
    (B_BUND, BUN,
     '  function trackKind(trId){var k=String(trId||"").charAt(0);\n'
     '    return k==="a"?"audio":k==="s"?"subs":k==="t"?"title":"video"}',
     '  function trackKind(trId){var k=String(trId||"").charAt(0);\n'
     '    return k==="a"?"audio":k==="s"?"subs":"video"}',
     ["D21_TT1_trackKind_connait_un_quatrieme_genre"]),
    # 12 — la piste des titres posee EN QUEUE : `t1` arrive sous les pistes
    #      audio au lieu d'etre en tete de la timeline.
    (B_EDIT, JS,
     'var out=list.slice();out.unshift(dzmSkin("t1","title"));return out}',
     'var out=list.slice();out.push(dzmSkin("t1","title"));return out}',
     ["tt_la_piste_manquante_est_posee_en_tete"]),
    # 13 — `_prev_w` n'attrape plus `OverflowError` : `w=inf` donne un 500
    #      la ou la promesse de la route est le repli sur 270.
    (B_L2, SVC,
     "    except (TypeError, ValueError, OverflowError):",
     "    except (TypeError, ValueError):",
     ["d21_une_largeur_infinie_retombe_sur_le_defaut"]),
    # 14 — `dzmTitleUpdate` sans la borne 24..200 : un appel exterieur ecrit
    #      un `size:5000` que la sauvegarde garde et que seul le rendu ramene
    #      a 200, sans le dire.
    (B_EDIT, JS,
     "nz=Math.max(24,Math.min(200,nz));",
     "",
     ["tu_la_taille_est_bornee_vingt_quatre_deux_cents"]),
    # 15 — le filtre du payload de rendu ramene a `c.src` : les cartons de
    #      titre, qui n'ont pas de source, ne partent plus au backend du
    #      tout. La mutation est faite DANS LE BUNDLE (le fichier charge),
    #      pas dans le patcher -- muter le patcher prouverait seulement que
    #      le patcher est coherent avec lui-meme.
    (B_BUND, BUN,
     'clips.filter(function(c){return c.src||c.kind==="title"})',
     "clips.filter(function(c){return c.src})",
     ["TT2_le_carton_passe_le_filtre_du_payload"]),
    # 16 — la PAUSE au repos retiree de montage.css : les six regles de
    #      famille ecrivent le raccourci `animation:`, qui remet
    #      `animation-play-state` a `running` -- sans cette ligne, les 58
    #      micro-scenes tournent toutes en meme temps, en permanence.
    (B_BUND, CSS,
     ".dzsvm .svm-tprev[data-fam] .svm-tb{animation-play-state:paused}",
     "",
     ["D20_la_pause_le_survol_et_le_figement_sont_reposes_sur_la_famille"]),
]


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
        # deux des cinq fichiers sont en CRLF (montage_service.py, titles.py)
        # et le bundle aussi. Le sha256 d'apres verifie l'aller-retour.
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
        # leurs noms par la section (`d20_`, `tl_`, `D21_TT1_`), et l'on veut
        # nommer la panne, pas recopier un prefixe qui bougera.
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


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
