# -*- coding: utf-8 -*-
"""Banc de mutations des lots L0/L1 du Montage : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_l0l1.py          # les vingt
    python tests/mutations_montage_l0l1.py 0 3 17   # celles-la

CE QU'IL MUTE, ET POURQUOI CE FICHIER-LA. Dix-sept mutations visent
`frontend/patches/montage.js` — LA COUCHE, pas le bundle : c'est elle que le
shim de `test_montage_historique.py` et de `test_montage_edition.py` execute
(leur `SRC_PATH` la nomme), et c'est elle que le patcher injecte. Trois visent
`backend/app/services/montage_service.py`, le seul endroit ou vit la
normalisation de `POST /save` (banc `test_montage_projets.py`, par la ROUTE).

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. La n°6 fait exception et
c'est une MESURE, pas un choix : jouee contre `test_montage_edition.py` elle
est SURVIVANTE (0 rouge). Le banc edition ne connait du verrou que le REPLI de
« dessus » (sa sonde C1 : aucune piste libre, donc `tr` reste la piste visee
et juger l'une ou l'autre revient au meme). Le cas qui SEPARE les deux —
« dessus » REUSSIT sur V2 pendant que V1 est verrouillee — n'est joue que par
`test_montage_bundle.py` (`js_D2_E4_au_dessus_pose_sur_V2_quand_V1_est
_verrouillee`, la conformite 7 / « E4 » de D-2). Elle est donc dirigee vers ce
banc-la, ou elle rougit TROIS lignes. La troisieme, `bloc_EST_la_couche_octet
_pour_octet`, est STRUCTURELLE : ce banc compare le bloc injecte dans le
bundle a `montage.js` octet pour octet, donc TOUTE mutation de la couche la
fait rougir. C'est pour cela que les seize autres mutations de la couche ne
passent pas par lui — le bruit noierait le signal.

TRAVAIL EN OCTETS. `read_bytes` / `write_bytes`, jamais `read_text` : une
traduction de fin de ligne changerait le fichier sous les pieds du banc.
MESURE DU 21/09/2026, python embarque : `montage.js` fait 318 630 octets,
5 400 `\\n` et ZERO `\\r\\n` — il est en LF DANS L'ARBRE DE TRAVAIL, contrairement
a ce qu'affirme le commentaire de `test_montage_bundle.py` l.1261 (« montage.js
est en CRLF »), qui parle du fichier tel que git le rend sur disque avec
autocrlf, pas de celui-ci. `montage_service.py` : 172 513 octets, LF aussi.
Ce script n'en depend d'ailleurs pas : il remplace des octets par des octets
et ne touche a aucun saut de ligne.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture) :
une chaine trouvee deux fois muterait deux sites et le verdict ne dirait plus
lequel des deux la ligne rouge accuse. La restauration est verifiee par
sha256 APRES CHAQUE mutation, dans un `finally`.

FAUTE N°6, DANS CE SCRIPT LUI-MEME. Un banc rend 0 (tout vert) ou 1 (des
rouges) ; tout autre code, ou une sortie sans `=== N passed`, veut dire qu'il
est MORT au lieu de rougir. On rend alors un troisieme etat (`MORT`) plutot
que de lire une liste de rouges vide comme « rien n'est casse ».

RESULTAT MESURE le 21/09/2026 (worktree sweet-euclid-d6d915, sommet a456aae,
python embarque, un processus par execution de banc) : LES VINGT SONT ROUGES,
AUCUN SURVIVANT, et chacune rougit EXACTEMENT les lignes declarees ci-dessous.
Les fichiers sont restaures a l'octet apres chacune (sha256 verifie) :
`montage.js` 2cce37a6b4…, `montage_service.py` 685a697695….

    #   fonction visee                   banc        rouges
    0   histApply ignore `dur`           historique  3
    1   histSnap `if(k in p)`            historique  2
    2   rangeSet ne pousse pas `out`     historique  1
    3   rangeFrom accepte in == out      historique  1
    4   cutOpts ignore le verrou         historique  1
    5   inserer ne pousse pas la suite   edition     3
    6   le verrou juge la piste VISEE    bundle      3  (voir ci-dessus)
    7   carve invente un srcIn           edition     1
    8   slip ne suit pas la vitesse      edition     1
    9   slide bouge sans voisin droit    edition     1
   10   roll sans borne 0,3 s            edition     2
   11   roll sans garde de contiguite    edition     2
   12   markerAdd doublonne              edition     2
   13   markerNext seuil 1e-6            edition     2
   14   markersFrom filtre strict        edition     1
   15   swap ancre sur `a.start` seul    historique  1
   16   swap echange aussi `srcIn`       historique  4
   17   backend range accepte in == out  projets     1
   18   backend markers sans plafond     projets     1
   19   backend markers filtre strict    projets     1

DEUX CHOSES QUE CETTE TABLE A MESUREES, ET QUI NE SE DEVINAIENT PAS :
  · la n°6 est un TROU DU BANC EDITION, pas un trou du depot (ci-dessus) ;
  · la n°16 (`swap` qui echangerait aussi `srcIn`) rougit les QUATRE lignes
    de bornes de D-4 et AUCUNE autre : ce sont des comparaisons de clip
    ENTIER (`{tr,id,start,end,srcIn,src}`), pas de bornes seules, et c'est
    ce qui tient les champs que `dzmSwap` ne doit PAS toucher. Elle ne
    touche en revanche pas `swap_clip_de_titre_sans_src_pas_de_srcIn
    _invente`, et c'est juste : un titre n'a pas de `srcIn`, donc la
    mutation y ecrit `srcIn: undefined`, que `JSON.stringify` OMET — la cle
    ne ressort pas du shim. Cette ligne-la garde un autre mode de panne
    (`srcIn: null` ECRIT), pas celui-ci.

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
B_HIST = "tests/test_montage_historique.py"
B_EDIT = "tests/test_montage_edition.py"
B_PROJ = "tests/test_montage_projets.py"
B_BUND = "tests/test_montage_bundle.py"

# (banc, fichier, ancien, nouveau, lignes attendues rouges)
# `ancien` peut etre une LISTE de couples (ancien, nouveau) appliques dans
# l'ordre quand une seule panne demande deux retouches — voir 13 et 16.
M = [
    # ── D-0, l'historique complet ────────────────────────────────────────
    # 0 — `histApply` saute `dur` : les six autres cles reviennent, la duree
    #     reste celle d'avant l'annulation. C'est le mode de panne EXACT que
    #     D-0 a corrige, une cle a la fois.
    (B_HIST, JS,
     "{k=DZM_HIST_CLES[i];if(k in s)n[k]=s[k]}",
     '{k=DZM_HIST_CLES[i];if(k in s&&k!=="dur")n[k]=s[k]}',
     ["hist_apply_restaure_duree_pistes_style_plage_marqueurs",
      "hist_apply_restaure_l_absence", "hist_apply_projet_nul_ne_meurt_pas"]),
    # 1 — `histSnap` redevient conditionnel : une cle ABSENTE du projet n'est
    #     plus portee par l'instantane, donc « Annuler » ne peut plus
    #     RESTAURER cette absence. Bug vu a l'ecran le 21/09 (projet de
    #     demonstration sans `proj.tracks`, la piste ajoutee survivait).
    (B_HIST, JS,
     "k=DZM_HIST_CLES[i];s[k]=p[k]}",
     "k=DZM_HIST_CLES[i];if(k in p)s[k]=p[k]}",
     ["hist_snap_porte_une_cle_absente_comme_absente",
      "hist_apply_restaure_l_absence"]),
    # ── D-11, la plage I/O ───────────────────────────────────────────────
    # 2 — poser « I » apres « O » n'ecarte plus la sortie : la plage devient
    #     INVERSEE (in > out) et tout ce qui la lit la rejette en silence.
    (B_HIST, JS,
     'if(which==="in"){r.in=v;if(r.out!=null&&r.out<=v)r.out=dzmRangeNum(dur,dur)}',
     'if(which==="in"){r.in=v}',
     ["range_entree_apres_la_sortie_pousse_la_sortie"]),
    # 3 — `rangeFrom` accepte une plage de longueur NULLE (in == out) : la
    #     chip « remplir » s'allume sur une plage vide et `dzmInsereUn`
    #     divise par zero pour la vitesse.
    (B_HIST, JS,
     "if(!isFinite(a)||!isFinite(b)||a<0||b<=a)return null;",
     "if(!isFinite(a)||!isFinite(b)||a<0||b<a)return null;",
     ["range_degeneree_n_est_pas_une_plage"]),
    # 4 — `cutOpts` ne lit plus le verrou : une piste verrouillee RIPPE avec
    #     les autres a « Maj+X ». Une seule condition, deux lectrices (R2 et
    #     le tiroir Texte) — c'est pour cela qu'elle vit a un seul endroit.
    (B_HIST, JS,
     "Object.keys(st).forEach(function(k){if(st[k]&&st[k].l)lk[k]=!0});",
     "Object.keys(st).forEach(function(k){if(!1)lk[k]=!0});",
     ["cut_opts_separe_le_verrou_de_la_boucle"]),
    # ── D-2, les six modes d'edition ─────────────────────────────────────
    # 5 — « inserer » pose sans POUSSER : le clip ecrase la suite au lieu de
    #     la decaler. Le ripple est toute la difference entre « inserer » et
    #     « ecraser » — sans lui les deux modes rendent la meme chose.
    (B_EDIT, JS,
     "cut=cut.map(function(c){return (c&&c.tr===tr&&Number(c.start)>=st-1e-6)?",
     "cut=cut.map(function(c){return (c&&c.tr===tr&&!1)?",
     ["inserer_fend_et_pousse", "fend_avec_vitesse",
      "jumeau_suit_sur_sa_piste"]),
    # 6 — le verrou est juge sur la piste VISEE et non sur la piste REELLE :
    #     « au-dessus » refuse de poser sur V2 (libre) parce que V1 (la
    #     visee) est verrouillee. C'est la conformite 7 / « E4 » de D-2,
    #     jouee a l'envers — la garde etait AVANT la resolution du mode.
    (B_BUND, JS,
     'if(lk[tr])return {clips:cs.slice(),track:tr,mode:m,refus:"verrou",note:"",id:null};',
     'if(lk[clip.tr])return {clips:cs.slice(),track:tr,mode:m,refus:"verrou",note:"",id:null};',
     ["js_D2_E4_au_dessus_pose_sur_V2_quand_V1_est_verrouillee",
      "js_D2_dessus_sur_une_piste_verrouillee_ne_pose_RIEN_et_le_dit",
      "bloc_EST_la_couche_octet_pour_octet"]),
    # 7 — `dzmCarve` INVENTE une fenetre de source sur un clip qui n'en a
    #     pas (un titre) : le morceau de droite ressort avec un `srcIn`, il
    #     entre dans la sauvegarde et dans le payload de rendu.
    (B_EDIT, JS,
     "if(c.srcIn!=null||c.src)q.srcIn=dzmR3(si+(b-s)*sp);",
     "q.srcIn=dzmR3(si+(b-s)*sp);",
     ["titre_sans_source_ne_gagne_pas_de_srcIn"]),
    # ── D-3, slip / slide / roll ─────────────────────────────────────────
    # 8 — le slip ne multiplie plus par la VITESSE : sur un clip a x2, faire
    #     glisser la fenetre d'une seconde de timeline consomme une seconde
    #     de source au lieu de deux — l'image ne suit pas le curseur.
    (B_EDIT, JS,
     "var sp=dzmSpeedNum(k),len=dzmSrcLen(k)*sp,si=(Number(k.srcIn)||0)-d*sp;",
     "var sp=dzmSpeedNum(k),len=dzmSrcLen(k)*sp,si=(Number(k.srcIn)||0)-d;",
     ["slip_suit_la_vitesse"]),
    # 9 — le slide devient un simple DEPLACEMENT quand il n'y a pas de
    #     voisin droit : le clip part en laissant un trou, alors qu'un slide
    #     est par definition un echange de matiere avec ses deux voisins.
    (B_EDIT, JS,
     "if(!v.d)return cs.slice();                     "
     "/* sans voisin droit : pas un slide */",
     "if(!v.d)return cs.map(function(k){return (k&&k.id===c.id)?"
     "Object.assign({},k,{start:dzmR3(Number(k.start)+d),"
     "end:dzmR3(Number(k.end)+d)}):k});",
     ["slide_sans_voisin_droit_ne_bouge_pas"]),
    # 10 — le roll n'a plus de plancher de 0,3 s : la jonction peut etre
    #      poussee jusqu'a ANNULER l'un des deux plans (duree nulle, voire
    #      negative), et rien a l'ecran ne le rattrape.
    (B_EDIT, JS,
     "var dmin=-((Number(L.end)-Number(L.start))-.3),"
     "dmax=(Number(R.end)-Number(R.start))-.3;",
     "var dmin=-((Number(L.end)-Number(L.start))-0),"
     "dmax=(Number(R.end)-Number(R.start))-0;",
     ["roll_borne_a_0_3_s", "roll_borne_haut_a_0_3_s"]),
    # 11 — le roll accepte DEUX CLIPS ETRANGERS (pistes differentes, aucune
    #      borne en contact) : il rallonge l'un et deplace l'autre chacun
    #      dans son coin. Deux clips mutiles, aucune jonction deplacee.
    (B_EDIT, JS,
     "if(L.tr!==R.tr||Math.abs(Number(R.start)-Number(L.end))>.1+1e-9)return cs.slice();",
     "if(!1)return cs.slice();",
     ["roll_refuse_deux_clips_non_contigus",
      "roll_refuse_deux_pistes_differentes"]),
    # ── D-5, les marqueurs ───────────────────────────────────────────────
    # 12 — la BASCULE disparait : reposer un marqueur sous la tete ne le
    #      retire plus, il se DOUBLE. C'est le geste de Resolve (la meme
    #      touche pose et depose) et il n'a aucun autre porteur.
    (B_EDIT, JS,
     "if(near&&!(o&&o.force))return l.filter(function(m){return m!==near});",
     "if(!1)return l.filter(function(m){return m!==near});",
     ["mk_reposer_sous_l_eps_retire_au_lieu_de_doubler",
      "mk_la_bascule_retire_le_marqueur_le_plus_proche"]),
    # 13 — `markerNext` revient au seuil de 1e-6 : « aller au suivant »
    #      depuis un marqueur rend 2,004 pour une tete a 2,000, c'est-a-dire
    #      qu'il RESTE SUR PLACE. Les deux sens, une seule panne.
    (B_EDIT, JS,
     [("if(dir>=0){for(i=0;i<l.length;i++)if(l[i].t>v+DZM_MARKER_EPS)return l[i].t}",
       "if(dir>=0){for(i=0;i<l.length;i++)if(l[i].t>v+1e-6)return l[i].t}"),
      ("else{for(i=l.length-1;i>=0;i--)if(l[i].t<v-DZM_MARKER_EPS)return l[i].t}",
       "else{for(i=l.length-1;i>=0;i--)if(l[i].t<v-1e-6)return l[i].t}")],
     None,
     ["mk_suivant_ignore_le_marqueur_sous_la_tete",
      "mk_un_ecart_d_exactement_un_eps_serait_injoignable"]),
    # 14 — le filtre d'espacement de la RESTAURATION redevient STRICT : un
    #      couple a EXACTEMENT 0,15 s passe, et le second est injoignable
    #      dans les deux sens (R-1 de la seconde revue de D-5).
    (B_EDIT, JS,
     "if(out.length&&m.t-out[out.length-1].t<=DZM_MARKER_EPS+1e-9)return;",
     "if(out.length&&m.t-out[out.length-1].t<DZM_MARKER_EPS)return;",
     ["mk_un_ecart_d_exactement_un_eps_est_trop_proche"]),
    # ── D-4, l'echange de deux plans voisins ─────────────────────────────
    # 15 — une SEULE borne ancree (`a.start`), comme la premiere version :
    #      l'ecart tolere par `dzmVoisins` (jusqu'a 0,1 s) est ABSORBE et le
    #      second clip TELEPORTE au raccord suivant.
    (B_HIST, JS,
     "if(k===a)return Object.assign({},k,{start:dzmR3(e-la),end:dzmR3(e)});",
     "if(k===a)return Object.assign({},k,{start:dzmR3(s+lb),end:dzmR3(s+lb+la)});",
     ["swap_un_trou_tolere_reste_au_raccord_interieur"]),
    # 16 — l'echange emporte aussi `srcIn` : les deux plans echangent leurs
    #      places ET leurs fenetres de source, donc chacun montre l'image de
    #      l'autre. `dzmSwap` ne doit toucher qu'a `start`/`end`.
    (B_HIST, JS,
     [("if(k===b)return Object.assign({},k,{start:dzmR3(s),end:dzmR3(s+lb)});",
       "if(k===b)return Object.assign({},k,{start:dzmR3(s),end:dzmR3(s+lb),srcIn:a.srcIn});"),
      ("if(k===a)return Object.assign({},k,{start:dzmR3(e-la),end:dzmR3(e)});",
       "if(k===a)return Object.assign({},k,{start:dzmR3(e-la),end:dzmR3(e),srcIn:b.srcIn});")],
     None,
     ["swap_p2_gauche_p1_prend_la_place_de_p2",
      "swap_p2_gauche_p2_prend_la_place_de_p1",
      "swap_p2_droite_p2_prend_la_place_de_p3",
      "swap_p2_droite_p3_prend_la_place_de_p2"]),
    # ── le backend, par la ROUTE ─────────────────────────────────────────
    # 17 — `_save_record` accepte une plage de longueur NULLE : `in == out`
    #      est stocke, puis resservi, et la chip « remplir » s'allume dessus.
    #      Le serveur doit dire la meme chose que `dzmRangeFrom`.
    (B_PROJ, SVC,
     "if math.isfinite(a) and math.isfinite(b) and 0 <= a < b:",
     "if math.isfinite(a) and math.isfinite(b) and 0 <= a <= b:",
     ["d11_une_plage_de_longueur_nulle_n_est_pas_stockee"]),
    # 18 — le plafond de 200 marqueurs saute cote serveur : un fichier edite
    #      a la main, ou un autre client, peut faire gonfler la sauvegarde
    #      sans borne. Le client, lui, borne toujours — d'ou l'interet de le
    #      mesurer PAR LA ROUTE.
    (B_PROJ, SVC,
     "if len(out_mk) >= 200:",
     "if len(out_mk) >= 100000:",
     ["d5_deux_cent_cinquante_marqueurs_sont_tronques_a_deux_cents"]),
    # 19 — le filtre d'espacement du serveur redevient STRICT : c'est le
    #      jumeau exact de la mutation 14, de l'autre cote du fil. Les deux
    #      bornes doivent dire la meme chose, sinon un couple a 0,15 s
    #      survit au disque et disparait au chargement (ou l'inverse).
    (B_PROJ, SVC,
     "<= _MONTAGE_MARKER_EPS + 1e-9):",
     "< _MONTAGE_MARKER_EPS):",
     ["d5_un_ecart_d_exactement_un_eps_est_trop_proche"]),
]


def rouges(banc):
    """Les noms des lignes ROUGES du banc, sa sortie, et un drapeau d'ERREUR.

    Le banc rend 0 (tout vert) ou 1 (des rouges) ; tout autre code veut dire
    qu'il est MORT au lieu de rougir — la faute n°6 du chantier — et l'on rend
    un troisieme etat plutot que de lire une liste vide comme « rien casse ».
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
        mute = src
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            ob, nb = o.encode("utf-8"), n_.encode("utf-8")
            # EXACTEMENT UNE FOIS : deux sites mutes rendraient le verdict
            # illisible (quelle ligne rouge accuse lequel ?).
            assert mute.count(ob) == 1, (i, rel, mute.count(ob), o[:60])
            mute = mute.replace(ob, nb)
        p.write_bytes(mute)
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        # Les lignes attendues sont des SOUS-CHAINES : les bancs prefixent
        # leurs noms par la section (`js_D2_...`, `d5_...`), et l'on veut
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
              f"{pathlib.Path(rel).name:20s} {paires[0][0].strip()[:44]!r}")
        print(f"     rouges({len(rg)})={sorted(rg)}")
        if manquants:
            print(f"     MANQUANTS={manquants}")
        print(f"     sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:2] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
