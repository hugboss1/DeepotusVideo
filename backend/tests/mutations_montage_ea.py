# -*- coding: utf-8 -*-
"""Banc de mutations du lot E-A du Montage (E-1, E-3, E-4) : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_montage_ea.py            # les dix-huit
    python tests/mutations_montage_ea.py 0 9 14     # celles-la

CE QU'IL MUTE, ET POURQUOI CES TROIS FICHIERS-LA. Le lot E-A vit des deux
cotes du reseau et dans DEUX artefacts livres :
  · `backend/app/services/montage_service.py` : le drapeau `vide` (E-1 :
    `_save_record`, la garde 400 de POST /projects, GET /project, `open`, le
    plafond 2 Mo), `montage_publish` (E-4 : liste blanche, run_at, brief,
    fichier present, fuseau) et `_CLIENT_DEFAULT_TRACKS` ;
  · `frontend/patches/montage.js` : LA COUCHE (E-1 `dzmProjetNeuf`,
    `dzmInstantaneNom` ; E-4 `dzmChannelsNorm`, `dzmPublishLocal`) -- c'est
    elle que le shim de `test_montage_edition.py` execute ;
  · `frontend/dist/assets/index-BEOJX8L5.js` : LE BUNDLE LIVRE, pour les
    trois sections qui ne sont PAS dans la couche (EA1 la porte sur V1, EA4
    le poll qui ne poste plus, EA6 le bandeau qui se ferme) -- le fichier que
    l'application charge, celui que `test_montage_bundle.py` lit.

UN BANC PAR MUTATION, CELUI QUI COUVRE LA FONCTION. Backend -> `ea` (par la
route, TestClient) ; couche -> `edition` (sections [12] et [13], executees
sous node) ; bundle -> `bundle` (le MIROIR). Jamais `bundle` pour une
mutation de la couche : il compare le bloc injecte a `montage.js` octet pour
octet et TOUTE mutation de la couche l'y ferait rougir (bruit, pas signal).

TRAVAIL EN OCTETS. Mesure du 22/09/2026 dans CE worktree (epic-fermi) :
`montage_service.py` 195 825 o CRLF (3 594), `montage.js` 374 803 o CRLF
(6 170) -- EN CRLF ICI, la ou le worktree de L2 le tenait en LF : c'est la
fin de ligne DU FICHIER qui commande, pas une phrase --, le bundle
1 860 366 o CRLF homogene (19 437 = 19 437). Les motifs sont ecrits en LF et
remis dans la fin de ligne du fichier ; le sha256 d'APRES le prouve.

CHAQUE `ancien` DOIT EXISTER EXACTEMENT UNE FOIS (assert avant l'ecriture).
Restauration verifiee par sha256 APRES CHAQUE mutation, dans un `finally`.
Faute n°6 : un banc rend 0 ou 1 ; tout autre code, ou une sortie sans
`=== N passed`, est un etat MORT distinct de « rien casse ».

RESULTAT MESURE le 22/09/2026 (worktree epic-fermi-f6adf5, sommet 6bf0244 +
la section [3] du banc ea, python embarque, un processus par banc) : LES
DIX-HUIT SONT ROUGES, AUCUN SURVIVANT, AUCUN MORT, chacune rougit la ligne
NOMMEE ci-dessous (`ROUGE`, jamais `ROUGE(autres)`), et le compte est celui
que le script a IMPRIME (journal de la cloture). Comptes au repos : ea 31/0,
edition 169/0, bundle 1685/0.

    #   fonction visee                                   banc     rouges
    0   _save_record ne garde plus `vide`                ea       8
    1   garde 400 de POST /projects sans l'exception     ea       7
    2   GET /project sans `vide` (repli Bibliotheque)    ea       4
    3   `open` sans l'exemption (409 sur un vide)        ea       2
    4   plafond 2 Mo retire de _save_record              ea       1
    5   /publish : _CHANNELS ignore                      ea       1
    6   /publish : run_at par defaut a +1 j              ea       1
    7   /publish : brief sans project_id                 ea       1
    8   /publish : fichier disparu accepte (is_file)     ea       2
    9   /publish : fuseau jete (astimezone retire)       ea       1
   10   dzmChannelsNorm sans liste blanche               edition  2
   11   dzmPublishLocal sans arrondi au quart d'heure    edition  3
   12   dzmInstantaneNom garde « montage » comme nom     edition  1
   13   dzmProjetNeuf sans `vide`                        edition  1
   14   EA1 remis sur "v2" (bundle)                      bundle   6
   15   EA4 refait fetch("/api/schedule" (bundle)        bundle   3
   16   EA6 sans setDzFin(null) (bundle)                 bundle   3
   17   _CLIENT_DEFAULT_TRACKS sans le `loop` de a2      ea       1

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  · la n°0 rougit HUIT lignes et non une (quatre etaient prevues) : POST
    /projects {vide:true} passe par `_save_record`, qui perd le drapeau, et
    la garde 400 qui suit (`cur.get("vide") is not True`) refuse alors le
    projet neuf -- creation, meta, liste, GET /project, pistes, `open`, le
    second projet et l'autosave tombent ensemble ; la n°1 (la garde seule)
    en emporte SEPT, tout ce qui nomme `pid` ;
  · la n°2 (GET /project) emporte aussi `e1_vide_sans_tracks...` et
    `e1_les_pistes...` : sans le drapeau resservi, le projet vide retombe sur
    le repli Bibliotheque (`saved:false`, pas de `tracks`) ;
  · la n°5 (liste blanche ignoree) ne rougit QU'UNE ligne : le Scheduler
    (`create_scheduled_post`) accepte « zzz » sans broncher -- c'est notre
    route, et elle seule, qui filtre ; sans elle un canal inconnu est stocke ;
  · la n°8 rougit DEUX lignes : le 409 attendu ET « n'a rien cree » -- sans
    `is_file()` un brouillon EST cree sur un .mp4 disparu ;
  · la n°11 (arrondi) fait tomber `pb_defaults_plus_deux_heures...` avec les
    deux lignes de `dzmPublishLocal` : la valeur par defaut EST l'arrondi ;
  · la n°14 rougit SIX lignes, dont `EA1-porte-bibliotheque-v1_ancre_consommee`
    -- EA1 ne REPREND PAS son ancre (`"v2"` -> `"v1"`), la boucle exige donc
    qu'elle ait disparu, et la remettre la fait revenir -- plus `P14_la_demo_
    la_table_et_le_greffon_gardent_leur_v2` (le greffon compte 1 v2 de trop)
    et `E3_le_patcher_porte_EA1_EA2_EA3_apres_TT11` ; les n°15 et n°16 rougissent
    de meme leur ligne generique `_remplace` ET `E4_le_patcher_porte_les_huit_
    sections_en_queue_apres_EA3` (qui compte chaque remplacement dans le
    bundle) en plus de leur pin ;
  · la n°17 prouve le banc croise : retirer `loop: True` de a2 cote service
    laisse VERTE `e1_vide_sans_tracks_prend_les_sept_pistes...` (elle ne
    compare que les ids) et ne rougit QUE le croisement -- sans lui, a2
    cesserait de boucler au rendu d'un montage neuf sans que rien ne le dise.

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
B_EA = "tests/test_montage_ea.py"
B_EDIT = "tests/test_montage_edition.py"
B_BUND = "tests/test_montage_bundle.py"

# (banc, fichier, ancien | [(ancien, nouveau)...], nouveau, lignes attendues rouges)
M = [
    # ── E-1, le drapeau `vide` (backend) ─────────────────────────────────
    # 0 — `_save_record` ne recopie plus `vide` : l'autosave le perd, et
    #     POST /projects {vide:true}, qui passe par lui, retombe sur le 400.
    (B_EA, SVC,
     '    if body.get("vide") is True:    # E-1 (voir le bloc au-dessus de _CLIENT_DEFAULT_TRACKS)\n'
     '        data["vide"] = True\n',
     "",
     ["e1_autosave_garde_vide_quand_le_client_le_renvoie",
      "e1_vide_true_cree_un_projet_200"]),
    # 1 — la garde 400 de POST /projects sans l'exception : un montage neuf
    #     (zero clip) est « Aucune timeline a enregistrer » comme avant E-1.
    (B_EA, SVC,
     '    if cur is None or (not cur.get("clips") and cur.get("vide") is not True):\n',
     '    if cur is None or not cur.get("clips"):\n',
     ["e1_vide_true_cree_un_projet_200"]),
    # 2 — GET /project sans `vide` : un projet vide (aucun clip V1) retombe
    #     sur le repli Bibliotheque et se remplit des 4 derniers rendus.
    (B_EA, SVC,
     '        if saved.get("vide") is True or any(c.get("tr") == "v1" for c in kept):\n',
     '        if any(c.get("tr") == "v1" for c in kept):\n',
     ["e1_get_project_rend_le_vide_sans_le_remplir"]),
    # 3 — `open` sans l'exemption : un projet vide n'a « plus un seul plan »
    #     et rend 409 -- il ne s'ouvre plus jamais.
    (B_EA, SVC,
     "    if not ouvrable and d.get(\"vide\") is not True:   # E-1 : un vide s'ouvre\n",
     "    if not ouvrable:\n",
     ["e1_ouvrir_un_projet_vide_200_pas_409"]),
    # 4 — le plafond 2 Mo retire de `_save_record` : la branche `vide` de
    #     POST /projects ecrit de nouveau 10 Mo (mesure de la revue E-1).
    (B_EA, SVC,
     '    if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > _SAVE_MAX_BYTES:\n'
     '        raise HTTPException(400, "Sauvegarde refusée — plus de 2 Mo.")\n',
     "",
     ["e1_vide_de_dix_mo_est_refuse_400_deux_mo"]),
    # ── E-4, POST /publish (backend) ─────────────────────────────────────
    # 5 — la liste blanche ignoree : un canal inconnu (« zzz ») est stocke
    #     tel quel dans le brouillon.
    (B_EA, SVC,
     '    ch = [c for c in chs if isinstance(c, str) and c in _CHANNELS] or ["x"]\n',
     '    ch = [c for c in chs if isinstance(c, str)] or ["x"]\n',
     ["e4_les_canaux_sont_filtres_par_la_liste_blanche"]),
    # 6 — run_at par defaut a +1 j : la convention partagee avec la
    #     Bibliotheque (+2 h) est rompue.
    (B_EA, SVC,
     "        run_at = (_dt.utcnow() + _td(hours=2)).replace(microsecond=0)\n",
     "        run_at = (_dt.utcnow() + _td(days=1)).replace(microsecond=0)\n",
     ["e4_run_at_par_defaut_est_a_deux_heures"]),
    # 7 — `brief` sans project_id : le post ne sait plus de quel montage il
    #     vient.
    (B_EA, SVC,
     '        post["brief"] = {"project_id": pid}\n',
     '        post["brief"] = {}\n',
     ["e4_project_id_voyage_dans_brief"]),
    # 8 — `is_file()` retire : un job `done` dont le .mp4 a disparu est
    #     publiable, un brouillon est cree sur du vent.
    (B_EA, SVC,
     "            or not _is_video_artifact(Path(fp)) or not Path(fp).is_file()):\n",
     "            or not _is_video_artifact(Path(fp))):\n",
     ["e4_fichier_disparu_409"]),
    # 9 — le fuseau JETE au lieu d'etre ramene en UTC : « 09:00+02:00 » est
    #     stocke 09:00 naif, le post part 2 h en retard (mesure de la revue).
    (B_EA, SVC,
     "        if run_at.tzinfo is not None:\n"
     "            run_at = run_at.astimezone(_tz.utc).replace(tzinfo=None)\n",
     "        run_at = run_at.replace(tzinfo=None)\n",
     ["e4_run_at_avec_fuseau_est_ramene_en_utc"]),
    # ── E-4 et E-1, la couche ────────────────────────────────────────────
    # 10 — `dzmChannelsNorm` sans liste blanche : un canal memorise perime
    #      (ou forge) est coche et envoye.
    (B_EDIT, JS,
     "if(ok.indexOf(c)>=0&&out.indexOf(c)<0)out.push(c)",
     "if(out.indexOf(c)<0)out.push(c)",
     ["pb_norm_liste_blanche_sans_doublon_x_a_defaut"]),
    # 11 — `dzmPublishLocal` sans l'arrondi au quart d'heure suivant.
    (B_EDIT, JS,
     "d=new Date(Math.ceil(d.getTime()/q)*q);",
     "",
     ["pb_local_est_la_forme_datetime_local",
      "pb_local_pile_ne_monte_pas_une_seconde_monte"]),
    # 12 — `dzmInstantaneNom` rend « montage » comme un vrai nom : la copie de
    #      surete d'un montage non nomme s'appelle « montage » et ECRASE la
    #      precedente au lieu d'etre datee.
    (B_EDIT, JS,
     '  if(n&&n!=="montage")return n;\n',
     "  if(n)return n;\n",
     ["pn_instantane_nomme_le_non_nomme_et_garde_un_vrai_nom"]),
    # 13 — `dzmProjetNeuf` sans `vide` : le corps envoye est un « enregistrer
    #      sous » a zero clip, le backend le refuse (400).
    (B_EDIT, JS,
     "  return {name:n,vide:!0,tracks:",
     "  return {name:n,tracks:",
     ["pn_neuf_porte_nom_vide_et_les_pistes_par_defaut"]),
    # ── E-3 et E-4, le bundle livre ──────────────────────────────────────
    # 14 — EA1 remis sur "v2" : la porte « Envoyer vers -> Montage » repose la
    #      video en incrustation muette. Mutation DANS LE BUNDLE (le fichier
    #      charge), pas dans le patcher.
    (B_BUND, BUN,
     '"video",p.dur||0,"v1")}catch(_e2)',
     '"video",p.dur||0,"v2")}catch(_e2)',
     ["E3_la_porte_de_la_bibliotheque_pose_la_video_sur_v1_et_l_image_sur_v2",
      "M16a_le_greffon_amont_n_a_pas_ete_touche"]),
    # 15 — EA4 qui refait `fetch("/api/schedule"` : le rendu final recree un
    #      brouillon en effet de bord, ce que E-4 interdit.
    (B_BUND, BUN,
     "setDzFin({job_id:job.id",
     'fetch("/api/schedule");setDzFin({job_id:job.id',
     ["E4_le_rendu_final_ne_poste_plus_sur_schedule_et_ne_navigue_plus"]),
    # 16 — EA6 sans `setDzFin(null)` : le second rendu reutilise l'instance
    #      du bandeau (bouton desarme, « Brouillon ajouté » perime).
    (B_BUND, BUN,
     'if(proj.demo||(job&&job.status!=="failed"))return;setDzFin(null);',
     'if(proj.demo||(job&&job.status!=="failed"))return;',
     ["E4_le_bandeau_se_ferme_au_lancement_d_un_rendu"]),
    # ── le banc croise ───────────────────────────────────────────────────
    # 17 — `_CLIENT_DEFAULT_TRACKS` sans le `loop` de a2 : le miroir du
    #      service diverge de la table du client ; seul le croisement le voit.
    (B_EA, SVC,
     '                          {"id": "a2", "kind": "audio", "bus": "musique", "loop": True},\n',
     '                          {"id": "a2", "kind": "audio", "bus": "musique"},\n',
     ["ea_croise_les_sept_pistes_par_defaut_du_client_sont_celles_du_service"]),
]


def rouges(banc):
    """Les noms des lignes ROUGES du banc, sa sortie, et un drapeau d'ERREUR
    (banc MORT : code hors {0, 1} ou pas de ligne de compte)."""
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
        # LE MOTIF EST ECRIT EN LF ET REMIS DANS LA FIN DE LIGNE DU FICHIER.
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
        # Les lignes attendues sont des SOUS-CHAINES du nom imprime.
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
