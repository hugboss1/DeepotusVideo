# -*- coding: utf-8 -*-
"""P8 — SEULE DE LA VIDEO SUR V1, ET UNE ERREUR DE RENDU LISIBLE.

Run : & $PY tests/test_montage_sources.py   (depuis backend/)

LE DEFAUT, MESURE AVANT D'ETRE CORRIGE (journal du 04/09/2026, job de
montage a32009c4 a 15:57:44, base deepotus.db interrogee sur une COPIE) :
les quatre « plans » de la piste V1 de l'utilisateur n'etaient pas des
videos. `sprite2d` range sa planche PNG et `asset3d` son maillage GLB dans
la MEME colonne `final_video_path` qu'un rendu `seedance` ; GET
/api/montage/project retenait les jobs `done` les plus RECENTS dont ce
chemin existe, sans jamais regarder ce que le fichier est. Les 35 rendus
seedance de la base, plus anciens, n'ont jamais ete atteints. Le rendu
mourait ensuite sur `model.glb` — « Invalid data found when processing
input » — et l'utilisateur lisait une tranche de 1200 CARACTERES de
stderr, coupee au milieu de la banniere de compilation de ffmpeg.

LE SECOND DEFAUT, TROUVE PAR LA REVUE DE QUALITE ET FERME ICI (P8-bis) : le
correctif ci-dessus filtrait les non-video DANS LA BOUCLE, APRES une requete
qui prenait les 60 derniers jobs `done`. Les lignes ecartees CONSOMMAIENT
donc le budget. Si les 60 lignes les plus recentes sont des planches et des
maillages, zero video est trouvee, `has_assets` passe a FAUX et l'ecran
retombe sur sa DEMO — alors que les rendus seedance sont toujours en base.
P8 avait donc remplace un etat faux BRUYANT (quatre cartons de 4 s) par un
etat faux SILENCIEUX, et ne le disait nulle part. Le seuil est exactement 60,
par construction ; sur une COPIE de la base REELLE les 60 lignes les plus
recentes en portent DEJA 15, dont 10 consecutives en tete. Voir [2-bis].

CE QUI EST FERME ICI
  [1] CONSTRUCTION AUTOMATIQUE : la boucle de `montage_project` n'accepte en
      V1 qu'une extension de `_VIDEO_EXTS`. Le banc pose en base les QUATRE
      cas reels — un seedance `.mp4`, un sprite2d `.png`, un asset3d `.glb`,
      un quatrieme dont le fichier a disparu — le mp4 etant le PLUS ANCIEN
      des quatre, comme dans la base de l'utilisateur. La liste des job_id
      retenus en V1 est comparee a un LITTERAL d'un seul element.
  [2] la base ne portant QUE des planches et un maillage : `has_assets` est
      FAUX et `clips` est vide — l'ecran garde sa demo au lieu d'ouvrir sur
      quatre cartons de 4 s.
  [2-bis] LE SEUIL DE LA FENETRE SQL (P8-bis). Soixante planches plus
      recentes qu'une seule vraie video : la video doit QUAND MEME atterrir
      en V1. C'est la ligne de la regression du second defaut, et la
      construction (60 planches posees APRES les sections [1] et [2]) est
      faite pour qu'elle rougisse SEULE — mesure N1.
  [2-ter] CASSE MIXTE. Un rush `Rush_Camera.MOV` : l'upload UGC teste en
      minuscules mais ECRIT la casse d'origine. Les DEUX `.lower()` porteurs
      sont mesures, sur leurs deux chemins distincts — la construction ici,
      le pre-vol en [4]. Aucun des deux n'etait tenu par quoi que ce soit
      avant (mutations N2 et N3, 35/0 chacune sur la version d'avant).
  [2-quater] LE `where` ET LE TEST PYTHON DISENT LA MEME CHOSE. La liste
      blanche est desormais ecrite DEUX FOIS — dans la requete et dans la
      boucle — et cet invariant est le vrai contrat du correctif : le `where`
      ne doit ni ECARTER ce que la boucle accepterait (timeline vide,
      silencieuse) ni ADMETTRE ce qu'elle rejetterait (le gaspillage de
      fenetre qu'on vient de retirer). Cinq lignes, une par propriete, et
      chacune tient une forme de `where` DIFFERENTE : N14 (la forme proposee
      par la revue, sur `final_video_path` seul) fait rougir les deux lignes
      de repli ; N16 (sans `nullif`) la ligne de la chaine vide ; N15 (le
      surensemble sur les deux colonnes) la ligne de budget ; M3 (test Python
      retire) la ligne du fichier NOMME « .mp4 ».
  [3] NON-REGRESSION, l'autre cote de la frontiere : une image POSEE A LA
      MAIN reste valide. `_resolve_src({image})` la resout, et le pre-vol
      l'accepte AUSSI BIEN sur V1 (carton fixe) que sur V2 (incrustation).
      MESURE (04/09/2026) qui fonde ce choix : `ovPicker()` du bundle
      (frontend/patches/son-vfx-montage.js, ~l.3630) propose la rubrique
      « Images (Bibliotheque) » sur TOUTE piste video — le filtre y est
      `trackKind(tr)==="audio"`, pas `tr==="v2"`. Refuser une image sur V1
      casserait un geste que l'interface offre. La regle « seule de la
      video » ne vaut donc QUE pour la construction automatique.
      Les deux appels DIRECTS a `_resolve_src` de cette section passent par
      `CO()` : nus, ils TUAIENT le banc — voir MB dans le tableau des
      mutations.
  [4] PRE-VOL de POST /render : les sources sont resolues AVANT la creation
      du JobRecord, et celles qu'aucun demultiplexeur n'ouvrira sont
      refusees en 400 en nommant le libelle du clip ET le fichier. Le banc
      verifie qu'AUCUN job `montage` n'a ete cree par un refus.
      UNE REQUETE PAR CAS accepte : image sur V1, image sur V2, son sur A1
      — une requete unique portant les trois ne pouvait pas dire lequel
      avait casse (M8 le prouve : elle fait rougir les deux lignes image et
      laisse VERTE la ligne son).
      La frontiere du pre-vol est une UNION PLATE, la MEME pour toute piste
      media : un `.wav` sur V1 passe, un `.mp4` sur A1 passe (MESURE : 200
      dans les deux sens). C'est un choix, pas un oubli — une video sur une
      piste audio est un geste SUPPORTE (le son d'un plan V1, garde
      `_has_audio_stream`), et differencier dans l'autre sens seul ne se
      decide pas a l'extension (un `.mkv` peut ne porter aucun flux video :
      il faudrait la sonde que la mesure ci-dessous ecarte). Les deux cas
      croises sont mesures — M9 et M10 les font rougir chacun SEUL.
      Les DEUX BORNES du 400 y sont aussi mesurees, et aucune ne l'etait :
      le NOMBRE de fautifs cites (`refus[:8]`, borne qui existait deja mais
      que rien ne tenait — mutation `refus[:1]` : 35/0) et la LONGUEUR de
      chaque libelle, qui n'etait pas bornee du tout alors que `label` est
      une chaine CLIENTE arbitraire.
  [5] `_run_ffmpeg` : la ligne qui DECIDE passe en tete du message, la
      tranche brute de 1200 caracteres restant derriere. Sans motif trouve,
      le message est identique CARACTERE POUR CARACTERE a l'historique —
      c'est une assertion a part entiere (`erreur_sans_motif_inchangee`),
      sans quoi la mise en tete serait verte a vide.
  [5-bis] LA CLASSE « GRAPHE DE FILTRES » (P8-bis). Les cinq motifs
      d'origine ne couvraient QUE l'ouverture d'une entree et le choix d'un
      encodeur : quatre cas mesures au VRAI ffmpeg rendaient ZERO motif,
      donc la tranche brute. Le plus grave est celui que le pre-vol laisse
      passer EXPRES — un `.wav` sur V1 — dont la docstring de
      `_ffmpeg_ouvrira` AFFIRMAIT qu'il « tombe sur le message lisible de
      `_run_ffmpeg` ». Mesure : il n'y tombait pas. Quatre motifs ajoutes,
      une ligne de banc chacun.
  [5-ter] TROIS COMPORTEMENTS de `_ffmpeg_lignes_utiles` que rien ne tenait
      — dedoublonnage, troncature a 200 caracteres, ORDRE (que la docstring
      promet noir sur blanc). Les trois mutations donnaient 35/0. Le plafond
      `limite`, lui, etait deja tenu (MLIM).
  [6] la SAUVEGARDE n'est pas elaguee, elle est SIGNALEE — et le CONTRAT du
      champ `v1_non_video` est arrete : ce sont des IDENTIFIANTS, joignables
      aux `clips` de la meme reponse, parce que la tache 16 les lira pour
      marquer les clips a l'ecran. Le repli d'origine
      (`id or label or p.name`) pouvait rendre un libelle ou un nom de
      fichier — une liste heterogene que rien ne peut rejoindre. La forme
      NOMINALE etait deja tenue (M7) ; c'est le REPLI qui ne l'etait pas.

VINGT-DEUX MUTATIONS, TOUTES REJOUEES le 04/09/2026 sur la version courante
du banc — les onze + une de P8 COMPRISES, dont les comptes d'alors (mesures
sur une version a 35 assertions) ne valent plus. Protocole : le fichier vise
est reecrit sur DISQUE, le banc relance en processus NEUF, le fichier
restaure quoi qu'il arrive (try/finally + verification du sha256) ; script
scratchpad/mut.py. Ligne verte de reference : 60/0.
LES QUINZE DE P8-bis (le second defaut et ce que la revue a ouvert autour) :
  N1 `where` retire de la requete => 57/3 : les deux lignes du seuil et
     `le_where_n_est_pas_un_surensemble`. C'EST LA MUTATION DU SECOND
     DEFAUT — celle qui reproduit la timeline vide et silencieuse. Aucune
     ligne d'une autre section ne bouge : les 60 planches sont posees APRES
     [1] et [2] exactement pour cela.
  N14 `where` sur `final_video_path` SEUL — la forme ecrite de tete par la
     revue => 58/2, les deux lignes de repli
     `where_suit_le_repli_video_path_quand_fvp_est_{nul,vide}`. La revue
     avait raison de prevenir : cette forme ECARTE des jobs legitimes.
  N15 `where` en SURENSEMBLE (OR sur les deux colonnes) => 59/1,
     `le_where_n_est_pas_un_surensemble` SEULE. Le surensemble ne change pas
     la SORTIE (la boucle rejette ensuite) — il rend le GASPILLAGE de
     fenetre, donc le defaut, en plus etroit.
  N16 `nullif` retire du `where` => 59/1, la ligne de la chaine VIDE seule
     (`coalesce` seul ne voit pas `""`, la ou le `or` de Python le traverse).
  N17 `ilike` -> `like` => 60/0, AUCUNE rouge, et c'est declare : le LIKE de
     SQLite est deja insensible a la casse pour l'ASCII par defaut. Les deux
     formes ne se separent que sous `PRAGMA case_sensitive_like = 1`, ou le
     LIKE nu ne garde plus que `a.mp4` quand la forme `lower()/lower()` que
     compile `ilike` garde aussi `Rush_Camera.MOV` et `b.Mp4` (mesure
     sqlite3 stdlib). Le choix est porte par CETTE mesure, pas par une ligne
     de banc — aucune ne peut les separer sur ce backend-ci.
  N2 `_is_video_artifact` sans `.lower()` => 58/2, les deux lignes
     `casse_mixte_*` de la construction.
  N3 `_ffmpeg_ouvrira` sans `.lower()` => 59/1,
     `casse_mixte_acceptee_au_prevol` SEULE.
  N4 motif « matches no streams » retire => 58/2, `motif_flux_absent` et
     `motif_flux_absent_en_tete_du_message` — les deux mesurent ce motif-la,
     l'une dans la table, l'autre de bout en bout.
  N5 « Error parsing filterchain » retire => 59/1, `motif_filterchain` SEULE.
  N6 « Error initializing filters » retire => 59/1, `motif_init_filtres`
     SEULE. (Une premiere version faisait rougir AUSSI
     `lignes_utiles_tronque_a_200`, dont le litteral empruntait ce motif ;
     le porteur de la troncature a ete change pour un motif d'origine.)
  N7 « Error opening output » retire => 59/1, `motif_sortie` SEULE.
  N8 borne `[:60]` du libelle retiree => 59/1,
     `prevol_borne_la_longueur_du_libelle` SEULE.
  N9 `refus[:8]` -> `refus[:1]` => 59/1,
     `prevol_borne_le_nombre_de_fautifs_cites` SEULE.
  N10 dedoublonnage retire => 59/1, `lignes_utiles_dedoublonne` SEULE.
  N11 troncature a 200 retiree => 59/1, `lignes_utiles_tronque_a_200` SEULE.
  N12 `return out[::-1]` => 59/1, `lignes_utiles_garde_l_ordre` SEULE.
  N13 `v1_non_video` revenu au repli heterogene => 57/3, les trois lignes du
     champ.
  F1 `raise` en tete de la fixture `pose()` => 32/28, et LE BANC IMPRIME SON
     COMPTE. C'est la garde de la faute n°6 etendue aux fixtures : sans elle
     la premiere `pose` en erreur tuait le processus avant toute ligne.

LES DOUZE DE P8, REJOUEES sur cette version (leurs comptes d'alors, mesures
a 35 assertions, ne valent plus) :
  M1 `_VIDEO_EXTS` + ".png"  => 48/12, dont `sprite_exclu` ROUGE et
     `glb_exclu` VERTE — les deux discriminent bien.
  M2 `_VIDEO_EXTS` + ".glb"  => 41/19, dont `glb_exclu` ROUGE et
     `sprite_exclu` VERTE. (Les `prevol_*` du refus rougissent aussi : le
     pre-vol lit la meme table.)
  M3 filtre `_is_video_artifact` retire de `montage_project` => 59/1,
     `nom_de_fichier_sans_extension_arrete_par_la_boucle` SEULE.
     CE CHIFFRE A CHANGE DE NATURE, et il faut le dire : avant P8-bis cette
     mutation donnait 28/7. Depuis que le `where` porte la meme liste
     blanche, la requete ne rend plus AUCUNE ligne que la boucle rejetterait
     — le test Python est devenu, pour presque tout, une seconde serrure sur
     la meme porte. La seule divergence qui subsiste est reelle et mesuree :
     le `where` filtre la CHAINE (`LIKE '%.mp4'`), la boucle filtre
     l'EXTENSION ANALYSEE (`Path(fp).suffix`), et `PurePath("C:/a/.mp4")
     .suffix` vaut `''`. C'est cette divergence-la, et elle seule, qui tient
     encore le test Python — sans la ligne ajoutee pour elle, M3 donnait
     55/0, AUCUNE rouge.
  M4 pre-vol retire de `montage_render` => 49/11, EXACTEMENT les lignes du
     refus et des deux bornes ; les cinq lignes d'acceptation, les deux cas
     croises, `casse_mixte_acceptee_au_prevol` et
     `prevol_laisse_passer_une_source_disparue` restent vertes.
  M5 `_ffmpeg_lignes_utiles` rendant toujours [] => 48/12, les quatre lignes
     de position, les cinq de [5-bis] et les trois de [5-ter] ;
     `erreur_sans_motif_inchangee` VERTE (autre branche).
  M6 mise en tete INCONDITIONNELLE (motif ou pas) => 34/1 A L'EPOQUE,
     `erreur_sans_motif_inchangee` SEULE rouge. NON REJOUEE sur cette
     version : la mutation portait sur une forme du code que P8-bis n'a pas
     touchee, et son chiffre est donc CELUI DE LA VERSION A 35 — il est cite
     ici pour memoire, pas comme une mesure courante.
  M7 `v1_non_video` jamais rempli => 58/2,
     `sauvegarde_signale_le_clip_non_video` et
     `v1_non_video_ne_rend_que_des_identifiants_joignables`.
  M8 pre-vol REFUSANT aussi les images (le zele que la decision 3 interdit)
     => 57/3 : `prevol_accepte_une_image_sur_v1`,
     `prevol_accepte_une_image_sur_v2` et `prevol_accepte_a_bien_mis_en_file`
     rouges — et `prevol_accepte_un_son_sur_a1` VERTE. C'est ce que la
     SEPARATION des trois cas achete : la ligne agregee d'avant rougissait
     en bloc sans dire lequel des trois cotes avait cede.
  M9 pre-vol DIFFERENCIANT (refus d'un son sur une piste video) => 59/1,
     `prevol_laisse_passer_un_son_sur_v1` SEULE rouge.
  M10 pre-vol DIFFERENCIANT dans l'autre sens (refus d'une video sur une
     piste audio) => 59/1, `prevol_laisse_passer_une_video_sur_a1` SEULE
     rouge. M9 et M10 mesurent que l'union est PLATE, et dans quel sens.
  MLIM `limite` ramene de 5 a 1 => 56/4 : `erreur_motif_en_tete`,
     `erreur_deux_motifs`, `erreur_banniere_pas_en_tete` et
     `lignes_utiles_garde_l_ordre`. Le plafond, lui, EST tenu — c'est le
     contre-exemple qui rend lisibles les trois trous de [5-ter].
  MB `raise` a l'appel de `_resolve_src` (la definition est renommee, donc
     AttributeError au moment de l'appel — ce que le thunk de `CO()` est
     fait pour rattraper).
     AVANT la garde (version a 30 assertions) : traceback sur la ligne alors
     NUE `asyncio.run(M._resolve_src(...))` de la section [3], exit 1,
     AUCUNE ligne de compte imprimee, sections [4] [5] [6] JAMAIS jouees —
     21 des 30 assertions emportees EN SILENCE. C'est la faute n°6 du
     chantier dans sa forme la plus couteuse : un banc qui meurt ne dit pas
     ce qui manque.
     APRES, sur cette version : 35/25, le banc va jusqu'au bout et IMPRIME
     SON COMPTE. Les temoins sont numerotes et lisibles dans le detail de
     chaque ligne rouge ; le dernier se pose PAR-DESSUS l'avant-dernier (la
     reponse-temoin releve a son tour dans `J()`), ce qui montre les deux
     gardes empilees sans jamais rendre `None`.
     Restent VERTES a bon droit : les sections [1], [2], [2-bis], [2-ter] et
     [2-quater] (sans sauvegarde, la construction depuis la Bibliotheque ne
     passe pas par `_resolve_src`), `prevol_aucun_job_cree` (une route qui
     meurt ne cree effectivement aucun job), `save_acceptee` (POST /save ne
     resout rien) et tout [5] / [5-bis] / [5-ter] (le message d'erreur ne
     resout aucune source).

CE QUE CE BANC N'AFFIRME PAS
  * Aucun octet n'est encode : `_run_ffmpeg` est REMPLACE par un talon pour
    les deux rendus acceptes. Ce banc mesure le PRE-VOL et le MESSAGE, pas
    la sortie video — c'est test_montage_pistes_rendu.py et
    test_montage_pistes_dyn.py qui rendent pour de vrai, et ils restent la
    garde contre un pre-vol trop zele.
  * La liste blanche est une liste d'EXTENSIONS. Un `.mp4` de zero octet ou
    un `.webm` tronque la passent. La sonde ffprobe n'est PAS ajoutee, et
    voici le protocole COMPLET qui le fonde — un chiffre dont le protocole
    ment n'est pas verifiable, et le precedent mentait deux fois.
      PROTOCOLE : binaire %LOCALAPPDATA%\\DeepotusVideoGen\\bin\\ffprobe.exe,
      version `ffprobe version 9.0-essentials_build-www.gyan.dev` (et NON
      « 7.x », comme l'affirmait la version precedente de cet en-tete) ;
      commande exacte `ffprobe -v error -select_streams v -show_entries
      stream=codec_type -of csv=p=0 <fichier>` ; 3 appels de chauffe puis 12
      appels chronometres, mediane ; machine Windows 11 26200, AMD64
      Family 23 Model 8 ; scratchpad/mesure_ffprobe2.py.
      RESULTAT, PAR CLASSE D'ASSET — c'est le second mensonge du chiffre
      unique de « 52 ms » : il avait ete mesure sur la FIXTURE du banc, un
      faux mp4 de NEUF octets (52,8 ms re-mesures, le plancher du lancement
      de processus), et non sur les assets dont la decision parle.
        planche PNG REELLE (1,9 a 2,7 Mo) : 73,9 / 81,8 / 83,8 ms
        maillage GLB REEL (9,4 et 42,5 Mo) : 99,1 / 102,3 ms
        faux mp4 de 9 octets (fixture)     : 52,8 ms
      VERDICT, la ou tout se joue : rc=0 et « video » sur les TROIS planches
      PNG reelles, rc=1 sur les DEUX maillages. La sonde n'aurait donc
      ecarte aucune des trois planches de sprites, seulement le GLB — que
      l'extension ecarte pour 0 ms. La conclusion est inchangee, et meme
      renforcee : sur les vrais assets la sonde coute 1,4 a 2 fois plus que
      ce qui avait ete annonce.
    Le trou restant (fichier video corrompu) tombe sur le message lisible de
    [5], ou « Invalid data found » est l'un des NEUF motifs remontes en tete
    — et cette phrase-la, au moins, est MESUREE : un mp4 de zero octet passe
    au vrai ffmpeg rend 3 motifs, en tete. C'est la meme phrase, appliquee au
    `.wav` sur V1, qui etait FAUSSE dans la docstring de `_ffmpeg_ouvrira`
    jusqu'a P8-bis (0 motif, diagnostic a l'offset 999 sur 1200). Une phrase
    de cette forme ne vaut que mesuree cas par cas.
  * COUT du pre-vol, RE-MESURE le 04/09/2026 (scratchpad/cout_prevol.py, base
    sqlite neuve de 24 JobRecord, 3 tours de chauffe puis 15 chronometres,
    mediane) : 58,7 ms pour 24 clips, soit 2,45 ms par clip — une session
    sqlite par `job_id`. Les MEMES 24 assets sondes par ffprobe : 1264 ms
    (5 tours), soit 21,5 fois plus — et ces 24-la sont les faux mp4 de 9
    octets, le cas le PLUS FAVORABLE a la sonde ; sur les assets reels
    mesures ci-dessus le rapport monte a 30–42x. Le pre-vol n'est pas
    gratuit : sur une timeline de cent clips il ajoute ~0,25 s au clic. Ce
    n'est PAS optimise (pas de resolution groupee).
  * VERIFICATION sur la base REELLE (une COPIE de deepotus.db + -wal + -shm,
    04/09/2026 18:10, l'application tournant ; DEEPOTUS_DATA_DIR temporaire
    donc sans sauvegarde) : 13 jobs `sprite2d`/`asset3d` sont desormais
    ecartes au journal, et la construction automatique rend QUATRE VRAIES
    videos — 10,04 + 15,97 + 21,63 + 21,23 s, total 68,881 s — la ou elle
    rendait quatre cartons de 4 s (16,0 s exactes de la capture).
    CE QUE CETTE VERIFICATION NE COUVRAIT PAS, et c'est la revue qui l'a vu :
    a 13 ecartes sur 60, elle n'approchait pas le seuil du second defaut.
    RE-MESURE le 04/09/2026 sur une COPIE fraiche
    (scratchpad/mesure_base_reelle.py, lecture seule, sqlite3 stdlib) : 116
    jobs `done`, 101 videos ; dans les 60 lignes les plus recentes, 15
    non-video (8 `sprite2d` .png, 7 `asset3d` .glb) ; et la liste COMMENCE
    par 10 non-video CONSECUTIVES. Marge avant le seuil : 50. Les trois
    derniers commits de la branche principale sont tous du pipeline 3D.
    Toujours zero job a `final_video_path` NULL ou vide dont `video_path`
    soit une video, zero job mixte (planche + video), zero extension en casse
    non minuscule : les cas de [2-quater] et [2-ter] sont ATTEIGNABLES par
    des gestes de l'application, pas encore PRESENTS. C'est dit pour que
    personne ne relise ces lignes comme une observation de terrain.
  * La SAUVEGARDE de l'utilisateur n'est PAS elaguee de ses clips V1
    non-video ; elle est seulement SIGNALEE (cle `v1_non_video` + warning au
    journal). MESURE sur le fichier reel
    (%LOCALAPPDATA%\\DeepotusVideoGenData\\assets\\montage_saved.json,
    5980 o, RELU le 04/09/2026) : il porte 17 clips — 4 V1 fautifs (tous a
    `src` {job_id}), 9 segments de sous-titres mot a mot a `src` NULL, 1
    voix A1 {audio}, 1 musique A2 {audio}, 2 incrustations V2 {job_id} ;
    plus un `subs_style` qui n'est pas un clip. Elaguer les 4 viderait la
    piste V1, et la garde deja en place (`any(c["tr"] == "v1")`) ferait
    alors repartir la construction depuis la Bibliotheque : 13 clips de
    travail detruits pour en retirer 4, sans retour.
    A UNE CONDITION, qu'il faut dire : sur ces 13, seuls les 9 sous-titres
    survivent INCONDITIONNELLEMENT (pas de `src`, donc rien a resoudre). Les
    4 autres — la voix, la musique et les DEUX incrustations — ne tiennent
    que tant que leurs fichiers existent : l'elagage deja en place juste
    au-dessus les retire sinon, en levant `saved_pruned`. L'argument porte
    donc sur 9 clips garantis et 4 conditionnels, pas sur 13 garantis — il
    tient, mais pas au chiffre brut.
  * DETTE DECLAREE — `v1_non_video` est un champ d'API SANS CONSOMMATEUR.
    GET /project le rend et le banc le mesure
    (`sauvegarde_signale_le_clip_non_video`, M7 la fait rougir), mais AUCUNE
    interface ne le lit encore : la sauvegarde de l'utilisateur rouvre sur
    ses clips fautifs sans marque visuelle, et c'est le 400 du pre-vol qui
    les nomme au moment du rendu. Sa lecture a l'ecran est inscrite au plan,
    tache 16 (celle qui touche le bundle) — cette tache-ci est backend pure.
    Tant que la 16 n'a pas atterri, ce champ est une DETTE assumee, pas une
    fonctionnalite. Son CONTRAT, lui, est desormais arrete et tenu : ce sont
    des IDENTIFIANTS joignables aux `clips` servis, et un clip V1 non-video
    sans `id` exploitable en est EXCLU (le journal le nomme encore par son
    libelle). C'est ce que la tache 16 doit pouvoir supposer ; sans quoi
    elle recevrait une liste ou un libelle et un id se ressemblent.
  * CE QU'AUCUNE LIGNE DE CE BANC NE SEPARE — declare pour que personne ne
    croie le contraire en lisant le vert : `ilike` et `like` dans le `where`
    de la requete. Le LIKE de SQLite est deja insensible a la casse pour
    l'ASCII par defaut ; la mutation N17 laisse le banc a 60/0. Le choix
    d'`ilike` est porte par une mesure hors banc (sous `PRAGMA
    case_sensitive_like = 1`, le LIKE nu perd `.MOV` et `.Mp4` la ou la
    forme `lower()/lower()` les garde), pas par une assertion.
  * NI le SEUIL LUI-MEME, au-dela de sa valeur actuelle. La ligne
    `seuil_60_*` pose exactement 60 planches parce que c'est la valeur
    MESUREE de `.limit(60)` ; changer cette constante DEPLACERAIT le seuil
    sans le rouvrir, et la ligne resterait verte. Ce qui ferme le defaut,
    c'est le `where` — et c'est la mutation N1, pas le nombre 60, qui le
    verifie.
  * DETTE NAVIGATEUR, non corrigee ici (cette tache est backend pure) : le
    selecteur d'assets du bundle (`openPicker`, son-vfx-montage.js ~l.3168)
    filtre `/api/jobs` sur `status==="done" && (video_path ||
    final_video_path)` — la MEME faute. Les planches de sprites et le
    maillage restent donc proposes sous « Rendus video » tant que le bundle
    n'est pas patche."""
import asyncio
import os
import pathlib
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp8_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from httpx import AsyncClient, ASGITransport                # noqa: E402
from app.main import app                                    # noqa: E402
from app.services import montage_service as M               # noqa: E402
from app.services.storage import (JobRecord, async_session_factory,  # noqa: E402
                                  init_db)
from app.models.schemas import JobStatus                    # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


_plantages = 0


def temoin(e):
    """TEMOIN d'un appel qui a LEVE. Ce banc doit ROUGIR, pas mourir (faute
    n°6 du chantier) — une mort n'imprime aucune ligne de compte et emporte en
    silence tout ce qui suit.

    Deux exigences, et le temoin les tient toutes les deux :
      * NUMEROTE — deux echecs ne se valent jamais, donc un `a == b` entre
        deux temoins reste rouge ;
      * DISTINGUABLE — jamais `None`, qui ferait passer au VERT toute
        assertion comparant a None ; on aurait remplace une mort par une
        assertion creuse. C'est une CHAINE finissant par « ·ECHEC#n », un
        marqueur sans point ni separateur de chemin : `Path(temoin).name` ne
        peut donc egaler aucun vrai nom de fichier, et `Path(temoin).suffix`
        aucune vraie extension (le marqueur reste colle a la fin)."""
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


def J(resp):
    """Corps JSON, ou un temoin (voir `temoin`)."""
    try:
        v = resp.json()
    except Exception as e:
        return {"_illisible": temoin(e)}
    return v if isinstance(v, dict) else {"_liste": v}


class _RepIllisible:
    """Reponse-temoin : un appel d'API qui LEVE ne doit pas tuer le banc.
    `status_code` negatif — jamais 200, jamais 400 ; `.json()` releve, donc
    `J()` posera son propre temoin par-dessus."""

    def __init__(self, t):
        self.status_code = -1
        self.text = t

    def json(self):
        raise ValueError(self.text)


def api(method, path, **kw):
    """Appel HTTP contre l'app ASGI. Une exception que FastAPI ne rattrape pas
    (NameError, TypeError… dans la route) TRAVERSE ASGITransport : sans cette
    garde elle tuerait le banc au milieu d'une section. Elle rend ici une
    reponse-temoin, et tout ce qui la lit rougit."""
    async def go():
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=180.0) as c:
            return await c.request(method, path, **kw)
    try:
        return asyncio.run(go())
    except Exception as e:
        t = temoin(e)
        print(f"  ----  {method} {path} a leve : {t}")
        return _RepIllisible(t)


def CO(fabrique, quoi=""):
    """Resultat d'une coroutine appelee DIRECTEMENT, ou un temoin.

    Meme parade que `J()`, pour l'AUTRE forme d'appel a l'unite sous test.
    MESURE le 04/09/2026 : `raise RuntimeError("boom resolve")` en tete de
    `_resolve_src` faisait mourir le banc sur la ligne alors NUE
    `asyncio.run(M._resolve_src(...))` de la section [3] — traceback, exit 1,
    AUCUNE ligne de compte imprimee, sections [4] [5] [6] jamais jouees : 21
    des 30 assertions de l'epoque emportees en silence.
    `fabrique` est un THUNK, pas une coroutine deja construite : ainsi meme la
    disparition de l'attribut `M._resolve_src` (AttributeError au moment de
    l'appel) est rattrapee."""
    try:
        return asyncio.run(fabrique())
    except Exception as e:
        t = temoin(e)
        print(f"  ----  {quoi} a leve : {t}")
        return t


ROOT = pathlib.Path(TMP)
LIB = ROOT / "lib"
LIB.mkdir(parents=True, exist_ok=True)
(ROOT / "images").mkdir(parents=True, exist_ok=True)
(ROOT / "audio").mkdir(parents=True, exist_ok=True)

# Les fixtures ne sont PAS des medias valides : rien ici n'est decode. Ce que
# le code sous test lit, c'est l'EXTENSION du chemin range en base.
F_MP4 = LIB / "plan_seedance.mp4"
F_PNG = LIB / "sheet.png"
F_GLB = LIB / "model.glb"
F_ABSENT = LIB / "efface.mp4"          # jamais cree : la source disparue
# CASSE MIXTE, et ce n'est pas une curiosite : l'upload UGC (routes.py, POST
# d'un rush) teste `safe.lower().endswith((".mp4", ".mov", ...))` mais ECRIT
# le fichier avec la casse d'ORIGINE (`safe` ne garde que les alphanumeriques
# et `._- `, sans jamais abaisser la casse), puis pose `final_video_path` ET
# `video_path` sur ce chemin-la, `provider="ugc"`, `status=DONE`. Un
# `Rush_Camera.MOV` importe par l'utilisateur porte donc `.MOV` en base —
# exactement les lignes que `montage_project` balaie et que le pre-vol juge.
# MESURE sur une COPIE de la base REELLE (04/09/2026) : zero extension en
# casse non minuscule AUJOURD'HUI. Le cas est donc ATTEIGNABLE par un geste
# de l'application, pas encore present — et c'est bien pour cela qu'il se
# tient ici et nulle part ailleurs.
F_MOV = LIB / "Rush_Camera.MOV"
F_MP4.write_bytes(b"\x00faux mp4")
F_MOV.write_bytes(b"\x00faux mov")
F_PNG.write_bytes(b"\x89PNG\r\n\x1a\nfaux")
F_GLB.write_bytes(b"glTF\x02\x00\x00\x00faux")
CARTON = ROOT / "images" / "carton.png"
CARTON.write_bytes(b"\x89PNG\r\n\x1a\ncarton")
VOIX = ROOT / "audio" / "voix.wav"
VOIX.write_bytes(b"RIFFfauxWAVE")

ID_MP4 = "aaaaaaaa-0000-0000-0000-000000000001"
ID_PNG = "bbbbbbbb-0000-0000-0000-000000000002"
ID_GLB = "cccccccc-0000-0000-0000-000000000003"
ID_GONE = "dddddddd-0000-0000-0000-000000000004"
ID_MOV = "eeeeeeee-0000-0000-0000-000000000005"

asyncio.run(init_db())


def pose(jid, provider, path, dur, quand):
    """FIXTURE gardee. Ce ne sont pas des unites sous test, et la faute n°6 ne
    s'y applique donc pas au sens strict — mais l'invariant « rougir plutot
    que mourir » doit valoir de BOUT EN BOUT, sans quoi il ne vaut nulle part.
    Le cas concret : `pose(ID_MP4, ...)` est REJOUE en fin de section [2],
    apres que `retire` a efface la ligne. Si cet effacement n'avait pas eu
    lieu, l'insertion leverait sur la contrainte de cle primaire — et une
    fixture nue emporterait EN SILENCE les sections [3] a [7], donc tout le
    pre-vol, tout le message d'erreur et toute la sauvegarde, AVANT le moindre
    compte. Le temoin fait rougir `aucun_appel_n_a_plante` et laisse le banc
    aller jusqu'a imprimer son compte."""
    async def go():
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, provider=provider,
                            status=JobStatus.DONE.value, progress=100,
                            title=provider + " " + jid[:4],
                            image_filename=jid[:8] + ".png",
                            final_video_path=str(path), video_path=str(path),
                            duration_s=dur, completed_at=quand))
            await s.commit()
    try:
        asyncio.run(go())
    except Exception as e:
        print(f"  ----  pose({jid[:8]}, {provider}) a leve : {temoin(e)}")


def pose_colonnes(jid, provider, fvp, vp, dur, quand):
    """Comme `pose`, mais les DEUX colonnes sont donnees separement : c'est la
    ou le `where` de la requete et le test Python peuvent diverger, donc la
    seule facon de mesurer qu'ils ne divergent pas. Meme garde que `pose`."""
    async def go():
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, provider=provider,
                            status=JobStatus.DONE.value, progress=100,
                            title=provider + " " + jid[:4],
                            image_filename=jid[:8] + ".png",
                            final_video_path=fvp, video_path=vp,
                            duration_s=dur, completed_at=quand))
            await s.commit()
    try:
        asyncio.run(go())
    except Exception as e:
        print(f"  ----  pose_colonnes({jid[:8]}) a leve : {temoin(e)}")


def retire(*jids):
    async def go():
        async with async_session_factory() as s:
            for jid in jids:
                v = await s.get(JobRecord, jid)
                if v is not None:
                    await s.delete(v)
            await s.commit()
    try:
        asyncio.run(go())
    except Exception as e:
        print(f"  ----  retire{jids} a leve : {temoin(e)}")


def n_montage():
    """Combien de JobRecord `montage` la base porte — la file d'attente."""
    async def go():
        from sqlalchemy import select, func
        async with async_session_factory() as s:
            r = await s.execute(select(func.count()).select_from(JobRecord)
                                .where(JobRecord.provider == "montage"))
            return int(r.scalar() or 0)
    try:
        return asyncio.run(go())
    except Exception as e:
        print(f"  ----  n_montage a leve : {temoin(e)}")
        # TEMOIN NUMERIQUE, et il le faut : `n_montage()` est lu dans des
        # ARITHMETIQUES (`avant = n_montage()` puis `n_montage() == avant + 3`).
        # La CHAINE que rend `temoin()` y leverait un TypeError — on aurait
        # remplace une mort par une autre, deux lignes plus bas. Un entier
        # NEGATIF, lui, se calcule et ne peut egaler aucun compte reel (>= 0),
        # et `_plantages` le NUMEROTE : deux temoins ne se valent jamais, donc
        # un `n_montage() == avant + k` entre deux appels plantes reste ROUGE.
        return -1000 - _plantages


T0 = datetime(2026, 9, 4, 12, 0, 0)
# L'ORDRE EST LE POINT : le seul vrai plan video est le PLUS ANCIEN des
# quatre, exactement comme dans la base de l'utilisateur (35 seedance jamais
# atteints, les quatre plus recents etant trois planches et un maillage).
pose(ID_MP4, "seedance", F_MP4, 5, T0 - timedelta(hours=3))
pose(ID_PNG, "sprite2d", F_PNG, None, T0 - timedelta(hours=2))
pose(ID_GLB, "asset3d", F_GLB, None, T0 - timedelta(hours=1))
pose(ID_GONE, "template", F_ABSENT, 6, T0)


print("\n[1] construction AUTOMATIQUE — GET /project sans sauvegarde :")
print("    seule de la video atterrit sur V1.")
d = J(api("GET", "/api/montage/project"))
v1_ids = [c.get("src", {}).get("job_id")
          for c in (d.get("clips") or []) if c.get("tr") == "v1"]
check("project_repond", d.get("ok") is True and d.get("saved") is False,
      str(d)[:200])
check("v1_ne_prend_que_la_video", v1_ids == [ID_MP4], str(v1_ids))
# Trois lignes SEPAREES et DISCRIMINANTES : une seule ligne agregee resterait
# verte si l'un des trois repassait. `ID_MP4 in v1_ids` interdit la version
# vacante (un filtre qui jetterait TOUT rendrait ces lignes vertes a vide) ;
# `len(v1_ids) == 1` n'est PAS utilise ici, sinon rouvrir la porte au sprite
# ferait aussi rougir `glb_exclu` et les deux cesseraient de discriminer
# (MESURE : c'etait le cas d'une premiere version, mutations M1/M2 du
# 04/09/2026).
check("sprite_exclu", ID_MP4 in v1_ids and ID_PNG not in v1_ids, str(v1_ids))
check("glb_exclu", ID_MP4 in v1_ids and ID_GLB not in v1_ids, str(v1_ids))
check("chemin_disparu_exclu", ID_MP4 in v1_ids and ID_GONE not in v1_ids,
      str(v1_ids))
# La duree du clip retenu vient du plan video (duration_s=5), pas du repli
# `or 4.0` qui donnait les quatre cartons de 4 s (16,0 s exactes) de la
# capture de l'utilisateur.
v1c = [c for c in (d.get("clips") or []) if c.get("tr") == "v1"]
check("duree_du_plan_video",
      len(v1c) == 1 and round(v1c[0]["end"] - v1c[0]["start"], 3) == 5.0,
      str(v1c)[:200])
check("duree_totale_du_seul_plan", d.get("duration") == 5.0,
      str(d.get("duration")))


print("\n[2] la base ne porte QUE des planches et un maillage :")
print("    has_assets FAUX — l'ecran garde sa demo.")
retire(ID_MP4, ID_GONE)
d2 = J(api("GET", "/api/montage/project"))
check("aucune_video_has_assets_faux",
      d2.get("ok") is True and d2.get("has_assets") is False
      and d2.get("clips") == [], str(d2)[:200])
# Et la Bibliotheque a bien ete LUE : deux jobs `done` y sont, tous deux
# ecartes. Sans cette ligne, un GET qui echouerait avant la boucle rendrait
# la meme chose.
check("sources_comptees_a_zero",
      (d2.get("sources") or {}).get("videos") == 0,
      str(d2.get("sources")))
pose(ID_MP4, "seedance", F_MP4, 5, T0 - timedelta(hours=3))


print("\n[2-bis] LE SEUIL DE LA FENETRE SQL — soixante planches plus recentes")
print("        qu'une seule vraie video, qui doit QUAND MEME atterrir en V1.")
# LE DEFAUT, mesure avant d'etre corrige : la requete prenait les 60 derniers
# jobs `done` PUIS la boucle ecartait les non-video. Les lignes ecartees
# CONSOMMAIENT le budget. Si les 60 lignes les plus recentes sont des planches
# et des maillages, zero video est trouvee, `has_assets` passe a faux, et
# l'ecran retombe sur sa DEMO — alors que les rendus seedance sont toujours en
# base. Deux etats faux, pas un : avant P8 la meme situation donnait quatre
# cartons de 4 s ; apres P8 elle donnait la demo, en silence.
# MESURE, protocole nomme (scratchpad/mesure_seuil.py) : base sqlite NEUVE
# par valeur de N, N jobs `sprite2d` a `final_video_path = sheet.png` tous
# plus recents qu'un unique `seedance` .mp4 valide, un GET
# /api/montage/project par base, via ASGITransport.
#   N = 3 / 55 / 56 / 57 / 58 / 59  -> has_assets True,  1 clip V1 (le seedance)
#   N = 60 / 61 / 80                -> has_assets FALSE, 0 clip V1
# Le seuil est exactement 60, par CONSTRUCTION (`.limit(60)`). Apres le
# correctif, les neuf valeurs rendent has_assets True et le seedance en V1.
# CE QUE CETTE LIGNE NE DIT PAS : elle est calee sur le seuil MESURE, donc
# sur la valeur actuelle de `.limit(60)`. Un changement de cette constante
# DEPLACERAIT le seuil sans le fermer ; ce qui le ferme, c'est la liste
# blanche DANS la requete, et c'est cela que la mutation « retirer le
# `where` » verifie. La ligne est le temoin de la regression, pas la preuve
# du mecanisme.
# VERIFICATION sur la base REELLE (COPIE de deepotus.db + -wal + -shm,
# 04/09/2026, lecture seule, scratchpad/mesure_base_reelle.py) : 116 jobs
# `done`, dont 101 videos ; les 60 lignes les plus recentes portent DEJA 15
# non-video (8 `sprite2d` .png, 7 `asset3d` .glb) et la liste COMMENCE par 10
# non-video consecutives. Marge avant le seuil : 50. La verification « la
# construction rend quatre vraies videos » citee plus haut a franchi ce seuil
# a 15/60 : elle ne le couvre pas.
# Ces 60 planches sont posees APRES les sections [1] et [2], pour que la
# mutation « retirer le `where` » fasse rougir la ligne ci-dessous SEULE.
for _i in range(60):
    pose("planche%02d-0000-0000-0000-000000000000" % _i, "sprite2d", F_PNG,
         None, T0 + timedelta(minutes=_i + 1))
d_seuil = J(api("GET", "/api/montage/project"))
v1_seuil = [c.get("src", {}).get("job_id")
            for c in (d_seuil.get("clips") or []) if c.get("tr") == "v1"]
check("seuil_60_la_video_ancienne_reste_en_v1",
      d_seuil.get("has_assets") is True and v1_seuil == [ID_MP4],
      f"has_assets={d_seuil.get('has_assets')} v1={v1_seuil}")
# ... et la FENETRE elle-meme a bien ete filtree, pas seulement la sortie :
# `sources.videos` est `len(vids)`, le compte des lignes RETENUES. Sans le
# `where`, la fenetre de 60 est faite des 60 planches et ce compte tombe a 0.
check("seuil_60_la_fenetre_ne_rend_que_des_candidats",
      (d_seuil.get("sources") or {}).get("videos") == 1,
      str(d_seuil.get("sources")))


print("\n[2-ter] CASSE MIXTE — un rush `.MOV` importe par l'utilisateur.")
# Voir le commentaire de la fixture F_MOV : l'upload UGC ecrit la casse
# d'origine. Les deux `.lower()` porteurs (`_is_video_artifact` et
# `_ffmpeg_ouvrira`) n'etaient tenus par RIEN — mutation mesuree le
# 04/09/2026 : les retirer laissait le banc a 35/0, aucune ligne rouge.
# Les DEUX cotes sont mesures, parce que ce sont deux `.lower()` differents
# sur deux chemins differents : la CONSTRUCTION ici, le PRE-VOL en [4].
pose(ID_MOV, "ugc", F_MOV, 7, T0 + timedelta(hours=2))
d_mov = J(api("GET", "/api/montage/project"))
v1_mov = [c.get("src", {}).get("job_id")
          for c in (d_mov.get("clips") or []) if c.get("tr") == "v1"]
check("casse_mixte_acceptee_a_la_construction", ID_MOV in v1_mov, str(v1_mov))
# Et sa duree vient bien du job (7 s), pas du repli `or 4.0` : la ligne
# ci-dessus resterait verte si le .MOV entrait comme un carton vide.
c_mov = [c for c in (d_mov.get("clips") or [])
         if c.get("tr") == "v1" and c.get("src", {}).get("job_id") == ID_MOV]
check("casse_mixte_duree_du_rush",
      len(c_mov) == 1 and round(c_mov[0]["end"] - c_mov[0]["start"], 3) == 7.0,
      str(c_mov)[:200])


print("\n[2-quater] LE `where` ET LE TEST PYTHON DOIVENT DIRE LA MEME CHOSE.")
# La liste blanche est desormais ECRITE DEUX FOIS : dans la requete (`where`,
# pour que les 60 lignes de la fenetre soient 60 CANDIDATS) et dans la boucle
# (`_is_video_artifact`, qui juge le chemin retenu). C'est un INVARIANT, et
# c'est le seul endroit du banc qui puisse le mesurer : le `where` ne doit ni
# ECARTER ce que la boucle accepterait — ce serait la timeline vide, en pire,
# parce que silencieuse — ni ADMETTRE ce qu'elle rejetterait, ce qui rendrait
# a la fenetre le gaspillage qu'on vient de lui retirer.
# La FORME du `where` a ete choisie SUR MESURE (scratchpad/mesure_ilike.py,
# base neuve, huit jobs couvrant les cas). Le filtre Python lit
# `fp = j.final_video_path or j.video_path` :
#   * un `where` sur la SEULE colonne `final_video_path` — la forme proposee
#     par la revue — manque 2 des 5 jobs que le filtre Python accepte (celui
#     dont `final_video_path` est NULL, celui dont il est vide) ;
#   * un OR sur les DEUX colonnes n'en manque aucun mais en admet un de TROP,
#     et ce n'est pas gratuit : soixante lignes de ce genre plus recentes que
#     la derniere vraie video RENDRAIENT le defaut, la boucle les rejetant une
#     a une apres qu'elles ont mange la fenetre ;
#   * `coalesce(nullif(final_video_path, ''), video_path)` est le MIROIR
#     EXACT du `or` de Python — 0 manquant, 0 en trop. C'est cette forme-la.
# Les quatre lignes ci-dessous tiennent ces trois constats.
NUL = "f0000000-0000-0000-0000-000000000010"   # final_video_path NULL
VID = "f0000000-0000-0000-0000-000000000011"   # final_video_path ""
MIX = "f0000000-0000-0000-0000-000000000012"   # planche + video
PNT = "f0000000-0000-0000-0000-000000000013"   # fichier NOMME « .mp4 »
F_POINT = LIB / ".mp4"
F_POINT.write_bytes(b"\x00nomme point mp4")
pose_colonnes(NUL, "seedance", None, str(F_MP4), 3, T0 + timedelta(hours=3))
pose_colonnes(VID, "seedance", "", str(F_MP4), 3, T0 + timedelta(hours=3, minutes=1))
pose_colonnes(MIX, "sprite2d", str(F_PNG), str(F_MP4), 3, T0 + timedelta(hours=3, minutes=2))
pose_colonnes(PNT, "seedance", str(F_POINT), str(F_POINT), 3, T0 + timedelta(hours=3, minutes=3))
d_inv = J(api("GET", "/api/montage/project?limit=20"))
v1_inv = [c.get("src", {}).get("job_id")
          for c in (d_inv.get("clips") or []) if c.get("tr") == "v1"]
# 1 & 2 — le REPLI `video_path`. Un `where` sur `final_video_path` seul
# ecarterait ces deux jobs-la : la ligne rougirait sur la forme proposee par
# la revue, et c'est precisement ce qu'elle est faite pour dire.
check("where_suit_le_repli_video_path_quand_fvp_est_nul", NUL in v1_inv,
      str(v1_inv))
check("where_suit_le_repli_video_path_quand_fvp_est_vide", VID in v1_inv,
      str(v1_inv))
# 3 — et `final_video_path` FAIT FOI quand il est renseigne : une planche en
# `final_video_path` n'entre pas en V1 sous pretexte que `video_path` porte
# un mp4. C'est la PRECEDENCE des deux colonnes, et rien de plus : MESURE du
# 04/09/2026, la mutation « `where` en surensemble sur les deux colonnes »
# laisse cette ligne VERTE — le surensemble admet bien MIX dans la fenetre,
# mais la boucle le rejette ensuite, et la SORTIE est identique. Ce que le
# surensemble change n'est pas le resultat, c'est le BUDGET ; il faut donc
# une autre ligne pour le voir, et c'est la derniere de cette section.
check("final_video_path_fait_foi_sur_le_repli", MIX not in v1_inv, str(v1_inv))
# 4 — LA LIGNE QUI TIENT LE TEST PYTHON, et il en fallait une : le `where`
# filtre la CHAINE stockee (`LIKE '%.mp4'`), la boucle filtre l'EXTENSION
# ANALYSEE (`Path(fp).suffix`). Les deux ne coincident pas partout — MESURE :
# `PurePath("C:/a/.mp4").suffix` vaut `''` (le nom commence par un point, il
# est donc un STEM entier et non une extension), alors que la chaine, elle,
# se termine bien par « .mp4 ». Un fichier NOMME « .mp4 » traverse donc le
# `where` et doit etre arrete par la boucle. Sans cette ligne, le test Python
# n'etait plus tenu par rien depuis que le `where` existe — mutation mesuree
# le 04/09/2026 : le retirer laissait le banc a 55/0, AUCUNE rouge.
check("nom_de_fichier_sans_extension_arrete_par_la_boucle",
      PNT not in v1_inv, str(v1_inv))

# 5 — LE SURENSEMBLE RENDRAIT LE DEFAUT, en plus etroit. C'est l'argument qui
# fait preferer le miroir exact a un OR sur les deux colonnes, et il ne
# valait rien tant qu'aucune ligne ne le portait : soixante lignes « planche
# en `final_video_path`, video en `video_path` » plus recentes que la
# derniere vraie video remplissent la fenetre sous un `where` en surensemble,
# la boucle les rejette une a une — et l'ecran retombe sur sa demo, exactement
# comme avant le correctif. Sous le miroir exact elles n'entrent jamais dans
# la fenetre. MESURE : sans cette ligne, la mutation « surensemble » laissait
# le banc a 59/0, aucune rouge — le choix de forme n'etait tenu par rien.
for _i in range(60):
    pose_colonnes("mixte%02d-0000-0000-0000-000000000000" % _i, "sprite2d",
                  str(F_PNG), str(F_MP4), 3, T0 + timedelta(hours=4, minutes=_i))
d_sur = J(api("GET", "/api/montage/project?limit=20"))
v1_sur = [c.get("src", {}).get("job_id")
          for c in (d_sur.get("clips") or []) if c.get("tr") == "v1"]
check("le_where_n_est_pas_un_surensemble",
      d_sur.get("has_assets") is True and ID_MP4 in v1_sur,
      f"has_assets={d_sur.get('has_assets')} v1={v1_sur}")


print("\n[3] NON-REGRESSION — une image posee A LA MAIN reste valide.")
p_img = CO(lambda: M._resolve_src({"image": "carton.png"}),
           "_resolve_src({image})")
check("image_posee_a_la_main_reste_valide",
      p_img is not None and pathlib.Path(p_img).name == "carton.png",
      str(p_img))
p_glb = CO(lambda: M._resolve_src({"job_id": ID_GLB}),
           "_resolve_src({job_id du glb})")
check("resolve_src_resout_aussi_le_glb",
      p_glb is not None and pathlib.Path(p_glb).suffix == ".glb", str(p_glb))
# `_resolve_src` ne juge PAS : c'est le pre-vol qui juge. Les deux cotes de
# la frontiere sont donc mesures separement.


# Le talon : ce banc mesure le PRE-VOL, pas l'encodage. Sans lui, chaque
# rendu accepte lancerait un vrai ffmpeg.
_vrai_run_ffmpeg = M._run_ffmpeg


def _talon(cmd, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"talon")
    return out


M._run_ffmpeg = _talon

print("\n[4] PRE-VOL de POST /render.")
BASE = {"name": "p8", "ratio": "9:16", "preview": True,
        "mix": {"dialogue": -6, "musique": -18, "sfx": -12}}
PLAN = {"tr": "v1", "id": "c1", "label": "plan", "start": 0, "end": 4,
        "src": {"job_id": ID_MP4}, "srcIn": 0, "transition": "cut"}

# UNE REQUETE PAR CAS. Une seule requete portant les trois cotes (image V1 +
# image V2 + son A1) ne pouvait pas dire LEQUEL avait casse. Ce n'est pas de
# la vacuite, c'est de la granularite — et c'est elle qui rend une mutation
# lisible : M8 (pre-vol refusant aussi les images) doit faire rougir les deux
# lignes image et LAISSER VERTE la ligne son.
# Le porteur V1 des cas 2 et 3 est le mp4 : POST /render refuse d'emblee, et
# pour une autre raison, une timeline sans clip V1 (« Timeline sans clip
# video »). L'acceptation de ce mp4-la est deja temoignee separement par
# `prevol_ne_nomme_pas_le_clip_valide` plus bas.
avant = n_montage()
r_i1 = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c2", "label": "carton fixe", "start": 0, "end": 2,
     "src": {"image": "carton.png"}, "srcIn": 0, "transition": "cut"}]))
check("prevol_accepte_une_image_sur_v1",
      r_i1.status_code == 200 and bool(J(r_i1).get("job_id")),
      f"{r_i1.status_code} {r_i1.text[:200]}")

r_i2 = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    PLAN,
    {"tr": "v2", "id": "c3", "label": "incrustation", "start": 0, "end": 3,
     "src": {"image": "carton.png"}}]))
check("prevol_accepte_une_image_sur_v2",
      r_i2.status_code == 200 and bool(J(r_i2).get("job_id")),
      f"{r_i2.status_code} {r_i2.text[:200]}")

r_a1 = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    PLAN,
    {"tr": "a1", "id": "c4", "label": "voix", "start": 0, "end": 3,
     "src": {"audio": "voix.wav"}}]))
check("prevol_accepte_un_son_sur_a1",
      r_a1.status_code == 200 and bool(J(r_a1).get("job_id")),
      f"{r_a1.status_code} {r_a1.text[:200]}")

# Les trois lignes ci-dessus localisent DEJA le cas fautif ; celle-ci mesure
# une AUTRE propriete — « accepte » veut dire « entre en file d'attente », et
# rien d'autre ne le dit. Son detail nomme les trois codes, pour qu'un compte
# faux se lise sans relancer.
check("prevol_accepte_a_bien_mis_en_file", n_montage() == avant + 3,
      f"{avant} -> {n_montage()} (codes {r_i1.status_code}/"
      f"{r_i2.status_code}/{r_a1.status_code})")

# LES DEUX CAS CROISES. La frontiere du pre-vol est une UNION PLATE, la MEME
# pour toute piste media — un `.wav` sur V1 et un `.mp4` sur A1 passent tous
# deux. C'est un CHOIX (cf. la docstring de `_ffmpeg_ouvrira`), et il est
# PERMISSIF dans les deux sens : une video sur une piste audio est un geste
# SUPPORTE (le son d'un plan V1, garde `_has_audio_stream` de `_run`), et
# differencier dans l'autre sens seul ne se decide pas a l'extension — un
# `.mkv` ou un `.mp4` peuvent ne porter aucun flux video, il faudrait la
# sonde que la decision 1 ecarte sur mesure. Ni l'un ni l'autre de ces deux
# cas n'etait couvert jusqu'ici, dans aucun sens.
r_wav_v1 = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c5", "label": "un son sur la piste video",
     "start": 0, "end": 3, "src": {"audio": "voix.wav"}, "srcIn": 0,
     "transition": "cut"}]))
check("prevol_laisse_passer_un_son_sur_v1", r_wav_v1.status_code == 200,
      f"{r_wav_v1.status_code} {r_wav_v1.text[:200]}")

r_mp4_a1 = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    PLAN,
    {"tr": "a1", "id": "c6", "label": "une video sur la piste audio",
     "start": 0, "end": 3, "src": {"job_id": ID_MP4}}]))
check("prevol_laisse_passer_une_video_sur_a1", r_mp4_a1.status_code == 200,
      f"{r_mp4_a1.status_code} {r_mp4_a1.text[:200]}")

# CASSE MIXTE, cote PRE-VOL. C'est un `.lower()` DIFFERENT de celui de la
# construction (`_ffmpeg_ouvrira` et non `_is_video_artifact`), sur un chemin
# different — et il n'etait pas tenu davantage : mutation mesuree, le retirer
# laissait 35/0. Un rush `Rush_Camera.MOV` refuse ici serait un 400 sur un
# fichier parfaitement lisible.
r_mov = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c7", "label": "rush camera", "start": 0, "end": 4,
     "src": {"job_id": ID_MOV}, "srcIn": 0, "transition": "cut"}]))
check("casse_mixte_acceptee_au_prevol", r_mov.status_code == 200,
      f"{r_mov.status_code} {r_mov.text[:200]}")

avant = n_montage()
r_ko = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c1", "label": "plan", "start": 0, "end": 4,
     "src": {"job_id": ID_MP4}, "srcIn": 0, "transition": "cut"},
    {"tr": "v1", "id": "c2", "label": "3D · tripo", "start": 4, "end": 8,
     "src": {"job_id": ID_GLB}, "srcIn": 0, "transition": "cut"}]))
det = str(J(r_ko).get("detail") or "")
check("prevol_refuse_le_maillage", r_ko.status_code == 400,
      f"{r_ko.status_code} {r_ko.text[:200]}")
check("prevol_nomme_le_clip", "3D · tripo" in det, det[:250])
check("prevol_nomme_le_fichier", "model.glb" in det, det[:250])
# TEMOIN : le message ne deballe pas la timeline entiere — le clip VALIDE
# n'a rien a faire dans un refus. Sans cette ligne, un `detail` qui listerait
# tout passerait les deux precedentes.
check("prevol_ne_nomme_pas_le_clip_valide",
      bool(det) and "plan_seedance.mp4" not in det, det[:250])
check("prevol_aucun_job_cree", n_montage() == avant, f"{avant} -> {n_montage()}")

# Le pre-vol vaut pour TOUTE piste media, pas seulement V1 : un maillage en
# incrustation etait jusqu'ici jete en silence (warning au journal), donc
# invisible pour l'utilisateur.
r_ov = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c1", "label": "plan", "start": 0, "end": 4,
     "src": {"job_id": ID_MP4}, "srcIn": 0, "transition": "cut"},
    {"tr": "v2", "id": "c9", "label": "maillage en overlay", "start": 0,
     "end": 3, "src": {"job_id": ID_GLB}}]))
check("prevol_refuse_le_maillage_en_overlay", r_ov.status_code == 400,
      f"{r_ov.status_code} {r_ov.text[:200]}")

# LES DEUX BORNES DU 400, et aucune des deux n'etait mesuree. Le message de
# refus est construit a partir de chaines CLIENTES (`label`, `id`, `tr`) : il
# faut borner le NOMBRE de fautifs cites ET la LONGUEUR de chacun. Le nombre
# l'etait deja dans le code (`refus[:8]`) mais rien ne le tenait — mutation
# `refus[:8]` -> `refus[:1]` : 35/0, aucune rouge. La longueur ne l'etait pas
# du tout : huit libelles de dix mille caracteres faisaient un `detail` de
# 80 ko traverse jusqu'au navigateur.
LONG = "L" * 5000
r_long = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c8", "label": LONG, "start": 0, "end": 4,
     "src": {"job_id": ID_GLB}, "srcIn": 0, "transition": "cut"}]))
det_l = str(J(r_long).get("detail") or "")
check("prevol_refuse_bien_le_libelle_geant", r_long.status_code == 400,
      f"{r_long.status_code} {r_long.text[:120]}")
# La borne EXACTE, des deux cotes : 60 caracteres presents, 61 absents. Une
# assertion de seule longueur totale passerait au vert sur `[:4000]`.
check("prevol_borne_la_longueur_du_libelle",
      ("L" * 60) in det_l and ("L" * 61) not in det_l,
      f"detail de {len(det_l)} o ; 60 ={('L' * 60) in det_l} ; "
      f"61 ={('L' * 61) in det_l}")
# ... et le fichier reste nomme MALGRE la troncature : borner ne doit pas
# effacer le diagnostic.
check("prevol_borne_sans_perdre_le_fichier", "model.glb" in det_l, det_l[:200])

# LA BORNE DU NOMBRE : douze fautifs, huit cites. Les libelles sont DISTINCTS
# pour que le compte se lise sans ambiguite.
r_12 = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "d%02d" % i, "label": "fautif%02d" % i,
     "start": i * 4, "end": i * 4 + 4, "src": {"job_id": ID_GLB}, "srcIn": 0,
     "transition": "cut"} for i in range(12)]))
det_12 = str(J(r_12).get("detail") or "")
cites = [i for i in range(12) if ("fautif%02d" % i) in det_12]
check("prevol_borne_le_nombre_de_fautifs_cites",
      r_12.status_code == 400 and len(cites) == 8,
      f"{r_12.status_code} ; cites = {cites}")
# Le COMPTE annonce, lui, reste le vrai : borner l'affichage ne doit pas
# mentir sur le nombre. Sans cette ligne, `refus[:8]` applique AVANT le
# `len()` passerait au vert.
check("prevol_annonce_le_vrai_nombre", "12 source(s)" in det_12, det_12[:160])

# Une source DISPARUE n'est PAS l'affaire du pre-vol : ce chemin reste celui
# d'avant (echec nomme dans _run), sinon le pre-vol changerait deux choses a
# la fois.
avant = n_montage()
r_gone = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c1", "label": "efface", "start": 0, "end": 4,
     "src": {"job_id": ID_GONE}, "srcIn": 0, "transition": "cut"}]))
check("prevol_laisse_passer_une_source_disparue",
      r_gone.status_code == 200 and n_montage() == avant + 1,
      f"{r_gone.status_code} {avant} -> {n_montage()}")

M._run_ffmpeg = _vrai_run_ffmpeg


print("\n[5] _run_ffmpeg — la ligne qui DECIDE passe devant la tranche brute.")
BANNIERE = ("  configuration: --prefix=/ffbuild/prefix --enable-libtheora "
            "--enable-libvo-amrwbenc --enable-libvorbis --enable-libvpx "
            "--enable-libwebp --enable-libx264 --enable-libx265 "
            "--enable-libxml2 --enable-libxvid --enable-libzimg "
            "--enable-libzvbi --enable-lv2 --enable-libmysofa "
            "--enable-openal --enable-opencl --enable-opengl\n") * 6
STDERR_ERR = (
    "ffmpeg version 7.1 Copyright (c) 2000-2024 the FFmpeg developers\n"
    + BANNIERE
    + "[in#2 @ 000001d0] Error opening input: Invalid data found when "
      "processing input\n"
      "Error opening input file C:\\\\assets3d\\\\b6cec0f5\\\\model.glb.\n"
      "Error opening input files: Invalid data found when processing input\n"
      "MARQUEUR_DE_QUEUE_UNIQUE\n")
STDERR_MUET = ("ffmpeg version 7.1\n" + BANNIERE
               + "frame=  120 fps=0.0 q=-1.0 Lsize=  512kB\n")
SEP = "--- journal ffmpeg (fin) ---"


def _faux_subprocess(rc, err):
    def run(cmd, **kw):
        return types.SimpleNamespace(returncode=rc, stdout="", stderr=err)
    return types.SimpleNamespace(run=run,
                                 TimeoutExpired=subprocess.TimeoutExpired)


def _msg(rc, err):
    vrai = M.subprocess
    M.subprocess = _faux_subprocess(rc, err)
    try:
        M._run_ffmpeg(["ffmpeg"], pathlib.Path(TMP) / "jamais_ecrit.mp4")
        return "<AUCUNE EXCEPTION>"
    except RuntimeError as e:
        return str(e)          # le CONTRAT : c'est ce message-la qu'on mesure
    except Exception as e:     # tout autre type est un BUG, jamais une mort
        return temoin(e)
    finally:
        M.subprocess = vrai


msg = _msg(1, STDERR_ERR)
# Assertions de POSITION, pas de sous-chaine : avant le correctif la ligne
# « Error opening input file » ETAIT dans le message — a l'offset 960, apres
# neuf cents caracteres de drapeaux de compilation. Une simple recherche de
# sous-chaine passait donc au VERT sur le defaut lui-meme (constate en
# jouant ce banc AVANT l'implementation : `erreur_motif_en_tete` et
# `erreur_deux_motifs` etaient vertes). Ce qui se mesure ici, c'est OU.
i_motif = msg.find("Error opening input file")
check("erreur_motif_en_tete", 0 <= i_motif < 200, f"offset {i_motif}")
i_ban = msg.find("--enable-libtheora")
check("erreur_deux_motifs",
      0 <= msg.find("Invalid data found") < i_ban
      and 0 <= msg.find("model.glb") < i_ban,
      f"invalid {msg.find('Invalid data found')}, glb "
      f"{msg.find('model.glb')}, banniere {i_ban}")
# La banniere de compilation n'a rien a faire DEVANT le diagnostic : c'est
# elle qui occupait les neuf cents premiers caracteres de l'ancien message.
check("erreur_banniere_pas_en_tete", i_ban > i_motif >= 0,
      f"banniere {i_ban}, motif {i_motif}")
# ... et la tranche brute est TOUJOURS la, DERRIERE le diagnostic.
i_queue = msg.find("MARQUEUR_DE_QUEUE_UNIQUE")
check("erreur_tranche_conservee_apres_motif",
      i_queue > i_motif >= 0 and "--enable-libtheora" in msg
      and SEP in msg, f"motif {i_motif}, queue {i_queue}")
check("erreur_code_de_retour_cite", msg.startswith("ffmpeg a échoué (1) :"),
      msg[:80])

# L'AUTRE BRANCHE, litteralement : sans motif, le message est celui d'avant,
# caractere pour caractere. Sans cette ligne, une mise en tete
# INCONDITIONNELLE serait verte.
msg2 = _msg(7, STDERR_MUET)
check("erreur_sans_motif_inchangee",
      msg2 == "ffmpeg a échoué (7) : " + STDERR_MUET[-1200:],
      msg2[:120] + " … len=" + str(len(msg2)))


print("\n[5-bis] LA CLASSE « GRAPHE DE FILTRES » — quatre motifs de plus.")
# LE TROU, mesure : les cinq motifs de P8 ne couvraient que l'ouverture d'une
# ENTREE et le choix d'un encodeur. Toute la classe « graphe de filtres »
# rendait ZERO motif, donc la tranche brute — et c'est la faute la PLUS
# PROBABLE d'un service qui construit un `filter_complex` de cette taille
# (xfade, overlay, volume='expr', adelay, subtitles).
# PROTOCOLE (scratchpad/mesure_ffmpeg.py et mesure_ffmpeg_wav.py) : le VRAI
# ffmpeg.exe 9.0-essentials_build-www.gyan.dev de
# %LOCALAPPDATA%\DeepotusVideoGen\bin\, entrees fabriquees par lavfi, stderr
# capture en UTF-8, passe a la VRAIE `_ffmpeg_lignes_utiles` importee du
# service. Les quatre cas ci-dessous rendaient 0 motif ; les trois du bas du
# tableau (dossier absent 2, mp4 de zero octet 3, encodeur inconnu 1)
# tombaient deja en tete, et les cinq motifs d'origine RESTENT pour eux.
# Les lignes ci-dessous sont des LITTERAUX recopies de cette mesure.
def _lignes(ligne):
    """Ce que `_ffmpeg_lignes_utiles` retient d'un stderr fait de la banniere
    de compilation, de cette ligne-la, et d'une queue muette."""
    return M._ffmpeg_lignes_utiles(
        "ffmpeg version 9.0\n" + BANNIERE + ligne + "\nqueue muette\n")


# LE CAS LE PLUS GRAVE, et le seul dont une DOCSTRING parlait : le pre-vol
# laisse EXPRES passer un `.wav` sur V1 (ligne `prevol_laisse_passer_un_son_
# sur_v1` plus haut, 200), et la docstring de `_ffmpeg_ouvrira` JUSTIFIAIT ce
# laissez-passer en disant que « ce qui reste tombe sur le message lisible de
# `_run_ffmpeg` ». Mesure : il n'y tombait pas. `_ffmpeg_lignes_utiles`
# rendait [], le message redevenait la tranche brute, et le diagnostic
# atterrissait a l'offset 999 sur 1200 — la reproduction exacte du defaut que
# P8 corrige ailleurs. Une docstring affirmait quelque chose de faux.
L_FLUX = ("[fc#0 @ 000001749f5cf2c0] Stream specifier ':v' in filtergraph "
          "description [0:v]setsar=1,format=yuv420p,scale=540:960[n0] "
          "matches no streams.")
check("motif_flux_absent", _lignes(L_FLUX) == [L_FLUX], str(_lignes(L_FLUX))[:200])
L_CHAINE = ("[AVFilterGraph @ 000001db0af10700] Error parsing filterchain "
            "'[0:v]nexistepas=1[v]' around: [v]")
check("motif_filterchain", _lignes(L_CHAINE) == [L_CHAINE],
      str(_lignes(L_CHAINE))[:200])
L_INIT = "[AVFilterGraph @ 00000232ec906cc0] Error initializing filters"
check("motif_init_filtres", _lignes(L_INIT) == [L_INIT],
      str(_lignes(L_INIT))[:200])
# « Error opening output » et non « … output file » : ffmpeg emet les trois
# formes (« Error opening output <chemin>: … », « Error opening output file
# <chemin>. », « Error opening output files: … ») et le prefixe court les
# prend toutes. Le litteral choisi ici ne porte AUCUN des cinq motifs
# d'origine — sinon la ligne serait verte a vide.
L_SORTIE = "Error opening output files: Invalid argument"
check("motif_sortie", _lignes(L_SORTIE) == [L_SORTIE], str(_lignes(L_SORTIE))[:200])

# ... et de bout en bout : le cas du `.wav` sur V1 passe MAINTENANT en tete du
# message rendu. Les quatre lignes ci-dessus mesurent la table de motifs ;
# celle-ci mesure que la chaine complete en profite.
msg_flux = _msg(1, "ffmpeg version 9.0\n" + BANNIERE + L_FLUX
                + "\nMARQUEUR_DE_QUEUE_UNIQUE\n")
i_flux = msg_flux.find("matches no streams")
check("motif_flux_absent_en_tete_du_message", 0 <= i_flux < 250,
      f"offset {i_flux} sur {len(msg_flux)}")


print("\n[5-ter] TROIS COMPORTEMENTS de _ffmpeg_lignes_utiles que rien ne")
print("        tenait — mutations mesurees le 04/09/2026 : 35/0 chacune.")
# Le plafond `limite`, lui, EST tenu (le ramener a 1 => 32/3). Ces trois-la ne
# l'etaient pas : la docstring promet « dans l'ordre, sans doublon,
# plafonnees », et deux tiers de cette phrase ne coutaient rien a violer.
DBL = "Unknown encoder 'pasuncodec'"
check("lignes_utiles_dedoublonne",
      M._ffmpeg_lignes_utiles(DBL + "\n" + DBL + "\n" + DBL) == [DBL],
      str(M._ffmpeg_lignes_utiles(DBL + "\n" + DBL + "\n" + DBL)))
# La TRONCATURE a 200 caracteres + « … ». Une ligne de filtergraph reelle
# depasse largement : celle du `.wav` ci-dessus fait deja 160 caracteres, et
# un `filter_complex` de vingt clips en fait des milliers.
# Le motif PORTEUR est ici l'un des CINQ d'origine, a dessein : mesure du
# 04/09/2026, avec « Error initializing filters » comme porteur, la mutation
# « retirer ce motif-la » faisait rougir CETTE ligne EN PLUS de
# `motif_init_filtres` — la ligne de troncature cessait de ne mesurer que la
# troncature. Un porteur deja tenu ailleurs les redecouple.
L300 = "Conversion failed " + "Z" * (300 - len("Conversion failed "))
out300 = M._ffmpeg_lignes_utiles(L300)
check("lignes_utiles_tronque_a_200",
      out300 == [L300[:200] + "…"],
      f"len(ligne)={len(L300)} -> len(sortie)="
      f"{len(out300[0]) if out300 else 'RIEN'}")
# L'ORDRE, que la docstring promet noir sur blanc. Deux motifs DIFFERENTS,
# pour qu'un `return out[::-1]` se voie.
ORD_A = "Error opening input file C:\\a\\premier.mp4."
ORD_B = "Unknown encoder 'second'"
check("lignes_utiles_garde_l_ordre",
      M._ffmpeg_lignes_utiles(ORD_A + "\nbruit\n" + ORD_B) == [ORD_A, ORD_B],
      str(M._ffmpeg_lignes_utiles(ORD_A + "\nbruit\n" + ORD_B)))


print("\n[6] la SAUVEGARDE n'est pas elaguee — elle est SIGNALEE.")
r_save = api("POST", "/api/montage/save", json={
    "name": "sauvegarde de l'utilisateur", "ratio": "9:16", "duration": 16.0,
    "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
    "clips": [
        {"tr": "v1", "id": "v1_plan", "label": "plan", "start": 0, "end": 4,
         "src": {"job_id": ID_MP4}, "srcIn": 0},
        {"tr": "v1", "id": "v1_sheet", "label": "Particules · Aura magique",
         "start": 4, "end": 8, "src": {"job_id": ID_PNG}, "srcIn": 0},
        {"tr": "a1", "id": "a1_vo", "label": "voix", "start": 0, "end": 3,
         "src": {"audio": "voix.wav"}},
        # LE CLIP SANS `id` — le repli que rien ne tenait. Voir plus bas.
        {"tr": "v1", "label": "planche anonyme", "start": 8, "end": 12,
         "src": {"job_id": ID_PNG}, "srcIn": 0}]})
check("save_acceptee", r_save.status_code == 200 and J(r_save).get("ok") is True,
      r_save.text[:200])
d3 = J(api("GET", "/api/montage/project"))
ids3 = [c.get("id") for c in (d3.get("clips") or [])]
check("sauvegarde_servie", d3.get("saved") is True, str(d3)[:200])
# Le clip sans id est SERVI comme les autres — signale, jamais elague. Le
# `None` final le dit : c'est bien QUATRE clips qui reviennent.
check("sauvegarde_pas_elaguee",
      ids3 == ["v1_plan", "v1_sheet", "a1_vo", None], str(ids3))
check("sauvegarde_signale_le_clip_non_video",
      d3.get("v1_non_video") == ["v1_sheet"], str(d3.get("v1_non_video")))

# LE CONTRAT DU CHAMP, arrete ici. `v1_non_video` rendait
# `c.get("id") or c.get("label") or p.name` : un clip sans id y deposait un
# LIBELLE ou un NOM DE FICHIER, que rien ne peut rejoindre aux `clips` de la
# meme reponse. La tache 16 lit ce champ pour marquer les clips fautifs a
# l'ecran : il lui faut des IDENTIFIANTS. La forme nominale etait deja tenue
# (mutation M7) ; c'est le REPLI qui ne l'etait pas, et c'est lui que ces
# deux lignes tiennent.
nv = d3.get("v1_non_video") or []
check("v1_non_video_ne_rend_que_des_identifiants_joignables",
      bool(nv) and set(nv) <= set(i for i in ids3 if i),
      f"{nv} vs {ids3}")
# ... et le clip sans id est EXCLU du champ plutot que designe autrement.
# Le journal, lui, le nomme encore par son libelle — c'est un humain qui le
# lit. Sans cette ligne, rendre `["v1_sheet", "planche anonyme"]` passerait
# la precedente au vert des que « planche anonyme » ne serait plus un id.
check("v1_non_video_exclut_le_clip_sans_id",
      "planche anonyme" not in nv and ID_PNG not in nv
      and "sheet.png" not in nv, str(nv))


# La ligne qui dit que le banc a ROUGI plutot que MEURE : aucun des appels
# gardes (api, CO, _msg, J) n'a pose de temoin. Une mutation qui fait lever
# l'unite sous test fait rougir CETTE ligne EN PLUS de celles qu'elle casse —
# et le banc va jusqu'a imprimer son compte.
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
