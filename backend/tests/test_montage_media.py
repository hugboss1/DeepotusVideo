# -*- coding: utf-8 -*-
"""P7 — LE SOCLE DE LA LECTURE FLUIDE : pics d'onde, filmstrip, proxy 480p.

Run : & $PY tests/test_montage_media.py   (depuis backend/)

CE QUE FERME CE BANC — la moitie BACKEND de la tache 8 (etapes 1 a 4). Le
balayage de la timeline decodait la source a chaque mouvement de la tete de
lecture ; on precalcule desormais trois choses, on les met en cache, et on
les sert. L'ECRAN n'est PAS touche ici (sections M17-M19, lot separe) : ces
quatre routes n'ont a ce jour AUCUN lecteur, et c'est une DETTE assumee,
ecrite ici plutot que sous-entendue — exactement comme `v1_non_video` l'a
ete en P8.

  [1] `_cache_path` : une extension par FAMILLE de genre, et un genre inconnu
      qui LEVE. Le code du plan la tirait d'un `kind.rstrip("0123456789")` —
      MESURE (scratchpad/mesure_plan.py, section [1]) : `"strip12x78x44"
      .rstrip("0123456789")` rend `"strip12x78x"` (le `x` final arrete le
      rstrip), donc `.jpg` sortait du REPLI du `.get`, par accident, et un
      genre mal orthographie serait devenu un `.jpg` silencieux.
  [2] `peaks` : TROIS ECARTS AU PLAN, chacun mesure.
      2a NORMALISATION. Le plan : `mx = max(pk) or 1` puis `round(v/mx, 3)
         if mx > 1 else 0.0`. MESURE (scratchpad/mesure2.py, balayage du
         seuil, ffmpeg 8.1.1-essentials_build) : la crete `s8` vaut 2 a −40
         et −42 dBFS, et 1 a −44, −46, −50 et −60 dBFS (plancher de dither,
         jamais 0). Un signal sous ≈ −44 dBFS donnait donc `mx == 1`, donc
         DES ZEROS PARTOUT — le meme dessin, au bit pres, que du silence
         numerique. Ici seule une crete NULLE rend des zeros ; `anullsrc`
         decode bien tout a zero (MESURE : 4 000 octets, une seule valeur
         distincte, 0), donc `silence_a_zero` reste tenue.
      2b REPARTITION DES CASES. Le plan : `step = max(1, n // bins)`, qui
         laisse les cases de queue VIDES quand la source est plus courte que
         `bins` echantillons. MESURE sur 0,05 s (100 echantillons a 2 000 Hz,
         300 cases) : 97 cases porteuses, 203 a 0,0 — deux tiers de silence
         INVENTE. Bornes proportionnelles ici, borne haute forcee d'au moins
         un echantillon : la meme mesure rend 300 cases sur 300.
      2c AUCUN FLUX AUDIO ≠ SILENCE. Le plan : `n = max(1, len(a))`, donc une
         source muette rendait `dur = 0.001` et une onde plate. MESURE : un
         PNG comme un `.mp4` sans piste audio rendent 0 octet et `rc = -22`.
         On LEVE ; la route repond 415 en nommant le fichier.
      2d L'ONDE PARTIELLE ETAIT INATTEIGNABLE. Quand ffmpeg se plaint mais a
         produit des octets, `peaks` rend l'onde SANS la mettre en cache. La
         route, elle, passait par `peaks_path` : celui-ci APPELAIT `peaks`,
         JETAIT son dict, reconstruisait un chemin — absent — et la route
         levait un 502. Le client ne pouvait JAMAIS recevoir cette onde, et
         aucune ligne ne couvrait ce chemin. La route rend desormais le DICT ;
         `peaks_path` est retire (il ne servait qu'a cela).
  [3] `strip` et `proxy` : bornes des parametres CLIENTS, cache, et ecriture
      ATOMIQUE (temporaire + `os.replace`) — `ffmpeg -y` TRONQUE sa sortie
      avant de la reecrire, et un `FileResponse` deja en vol servirait des
      octets vides. Meme raisonnement que `forge3d.py` l. 3842 pour un
      `copyfile`. ET LE BALAYAGE : `fps = n / duree` est TOUT l'interet de
      `strip`, et rien ne le mesurait — `_dur` force a 0 laissait le banc
      entierement vert, les six vignettes tirees des 0,1 premieres secondes.
      `filmstrip_balaie_la_source` compare les teintes de six vignettes
      prises sur une source qui change de couleur chaque seconde.
  [4] LA GARDE VIDEO DES ROUTES `strip` / `proxy`, par `_is_video_artifact` —
      la MEME autorite que la construction de timeline et que
      `GET /media-rules`, jamais une seconde liste. Ce n'est PAS une garde
      contre un plantage : MESURE (scratchpad/mesure2.py), ffmpeg REUSSIT le
      filmstrip d'un PNG (rc=0, image de 468x44 faite de six copies du meme
      carton) et l'apercu d'un `.wav` (un mp4 SANS image) ; il n'echoue que
      sur le `.glb`. Sans garde, la moitie des non-videos rendrait un
      resultat silencieusement faux plutot qu'une erreur.
  [7] P11 — `GET /duration`, ajoutee a cette famille de routes le 05/09/2026 :
      la duree d'une source, pour qu'un clip entre a SA longueur au lieu du
      chiffre par defaut du bundle. Elle n'est PAS gardee par `_is_video_
      artifact` (`video=False`), et c'est la ligne `route_duration_accepte_un_
      son_la_ou_strip_et_proxy_refusent` qui le mesure : un clip audio doit
      lui aussi entrer a sa longueur. Le piege de [4] ne la concerne pas —
      elle lit `format=duration`, pas `codec_type`, et un PNG y rend « N/A »,
      donc 0.0 : « je ne sais pas », jamais une duree inventee.
  [5] LE PIEGE PRINCIPAL DE LA TACHE — LE JOB DE PROXY N'EST PAS UN PLAN.
      `POST /proxy` cree un `JobRecord provider="montage_proxy"` ; or
      `montage_project` n'excluait que `provider == "montage"` porteur de
      `_preview`, et `montage_newer` que `provider != "montage"`. « montage_
      proxy » n'est ni l'un ni l'autre : un cache 480p serait devenu un plan
      V1 et une « version plus recente ». DEUX VERROUS, et chacun a SA ligne
      de banc, dans SON fichier :
        verrou 1, MESURE ICI — le job ne porte AUCUN chemin d'artefact
          (`final_video_path` et `video_path` restent NULS). Il est donc
          invisible de TOUT ce qui interroge un artefact, y compris le
          selecteur d'assets du bundle (`status==="done" && (video_path ||
          final_video_path)`, P9) — pas seulement des deux routes nommees.
          Le chemin du cache se DEDUIT de la source, l'ecran n'a donc jamais
          besoin de le lire sur le job.
        verrou 2, mesure AILLEURS — les deux requetes ecartent ce `provider`
          NOMMEMENT (`test_montage_sources.py` [2-sexies],
          `test_montage_remplacer.py` [1]). C'est la garde de REGRESSION du
          verrou 1 ; ses fixtures posent donc la forme REGRESSEE (un vrai
          `.mp4` en `final_video_path`), sans quoi elles seraient vertes a
          vide.
  [5-bis] LE BUDGET DE LA FENETRE, ET LE COUT. Le verrou 1 rend le job
      invisible du FILTRE des ecrans ; il ne l'empeche pas d'OCCUPER une
      place dans les fenetres qui n'en filtrent aucun. Deux etaient ouvertes
      et le sont maintenant fermees, chacune dans SA requete, avant le
      `limit` :
        * `GET /api/jobs` (`Pipeline.list_jobs`, 50 lignes) — le selecteur
          d'assets du Montage les lit, filtre, puis coupe a 12 : cinquante
          proxys et la liste « Rendus video » est VIDE, base pleine de
          rendus. Meme lecon que P8-bis, appliquee a `provider`.
        * `GET /api/cost/usage` — `_job_to_cost` retombait sur sa branche
          « campaign » par defaut et facturait 0,403 USD PAR PROXY (mesure
          aux tarifs par defaut : 0,400 « Seedance video » + 0,003 « FLUX
          image x1 », imputes a `fal`), soit 4,84 USD affiches pour une
          timeline de douze clips — pour un transcodage ffmpeg local et
          GRATUIT. De l'argent montre pour une depense qui n'existe pas.
      Les deux exclusions passent par `coalesce(provider, '')` : `NULL != …`
      vaut NULL en SQL et ECARTERAIT les 13 jobs `done` a provider nul de la
      base reelle. Une ligne par piege, N-P18 / N-P19 / N-P20.
  [6] OU VIT LE CACHE. `outputs/montage_cache/`, un dossier NEUF. MESURE
      (`grep -rn "outputs_path" backend/app --include=*.py`, 05/09/2026) :
      aucune route n'enumere `outputs/` recursivement, et les deux seuls
      parcours (routes.py l. 257 et 274) cherchent un fichier PAR NOM a la
      RACINE d'`outputs/` — jamais dans un sous-dossier. La ligne
      `cache_introuvable_par_nom_a_la_racine_d_outputs` mesure exactement
      cela.
  [7] QUI A LE DROIT D'APPELER. Ces routes rendent du CONTENU DERIVE (un
      JPEG, un mp4, un JSON) d'une source dont le vocabulaire accepte
      `{file_path}`, un chemin absolu LIBRE. Mesures qui ont porte la
      decision (05/09/2026) : `settings.HOST` vaut « 127.0.0.1 » et ni un
      `.env` ni `scripts/launch.ps1` ne le surchargent ; CORS n'est monte que
      sous `DEEPOTUS_DEV=1`, donc une page etrangere peut DECLENCHER un GET
      mais pas en LIRE la reponse ; et `{file_path}` est un usage LEGITIME et
      vivant (les incrustations d'emoji, frontend/patches/montage.js l. 331,
      chemin produit par `POST /api/subtitles/emoji-hints`). On ne restreint
      donc pas le vocabulaire — on restreint l'APPELANT, en REUTILISANT la
      seule definition de « boucle locale » du depot
      (`routes._require_localhost`).

VINGT ET UNE MUTATIONS, TOUTES REJOUEES le 05/09/2026 sur la version
COURANTE des trois bancs. Les quatorze d'abord declarees l'avaient ete sur
une version a 60 assertions et n'avaient PAS ete re-mesurees : ONZE de leurs
quatorze totaux sommaient a 60 quand la ligne verte de reference declaree
deux paragraphes plus haut valait 61 (seules N-P1, N-P8 et N-P14 sommaient
juste). C'est la FAUTE N°1 de ce chantier — un chiffre mesure sur une version
d'avant, recopie sur une version d'apres — et elle a ete payee sept fois
ailleurs. Tout est donc re-mesure ci-dessous, avec les ensembles de rouges
complets.

Protocole : le fichier vise est reecrit sur DISQUE, les trois bancs sont
relances en processus NEUFS, le fichier restaure quoi qu'il arrive
(try/finally + verification du sha256) ; script scratchpad/mut_p7.py, qui
refuse de partir si un motif ne se trouve pas EXACTEMENT une fois. Lignes
vertes de reference : media 67/0, sources 67/0, remplacer 99/0.

  LES TROIS DU PIEGE PRINCIPAL — chaque verrou rougit SEUL, et c'est le point.
  N-P1  la route de proxy REND son chemin au job (`final_video_path` et
        `video_path` poses sur le mp4 480p — la forme naive du plan)
          media 64/3 : job_proxy_sans_final_video_path,
                       job_proxy_sans_video_path,
                       job_proxy_hors_du_filtre_du_selecteur_d_assets
          sources 67/0 et remplacer 99/0 : AUCUNE rouge — le verrou 2 tient
          seul. C'est ce qui rend les deux verrous mesurables separement.
  N-P2  `where` de provider retire de `montage_project`
          sources 64/3 : proxy_de_scrub_n_entre_pas_en_v1 (la SORTIE),
                         proxy_de_scrub_ne_mange_pas_la_fenetre_de_60 (le
                         BUDGET) et proxy_de_scrub_hors_de_la_fenetre_sql
                         (la FENETRE, interrogee au-dela du cap de sortie)
          media 67/0 et remplacer 99/0 : aucune rouge.
  N-P3  `montage_newer` revient a `coalesce(provider,'') != "montage"`
          remplacer 97/2 : newer_n_offre_pas_un_proxy_de_scrub ET le litteral
                         d'ordre newer_rend_les_homonymes_… (le proxy, plus
                         recent que I(2), arrive EN TETE)
          media 67/0 et sources 67/0 : aucune rouge.
          DECLARE : la mutation garde le `coalesce`. Jouee avec un `!=` NU
          elle rend 95/4 — elle emporte en plus newer_accepte_un_provider_nul
          et newer_rend_une_duree_nulle_telle_quelle, qui tiennent la
          decision 4 de `montage_newer` et non le proxy. Deux mutations en
          une ne mesurent ni l'une ni l'autre.
  N-P14 valeur de `_PROXY_PROVIDER` renommee (« montage_cache_job »)
          media 65/2 : job_proxy_provider_nomme,
                       job_proxy_le_litteral_du_provider_est_celui_du_service
          sources 63/4, remplacer 96/3 — dont les TROIS lignes
          « le_litteral_du_provider… ». C'est ce qui empeche les fixtures des
          deux autres bancs, qui posent la valeur EN DUR, de devenir vertes a
          vide le jour ou la constante bouge.
          DECLARE : job_proxy_hors_de_la_fenetre_de_api_jobs et
          cout_un_proxy_ne_coute_rien restent VERTES — elles lisent la MEME
          constante que le code exclut, donc un renommage COHERENT ne casse
          rien ; c'est le litteral, ci-dessus, qui tient ce cas-la.

  LES QUATRE ECARTS AU CODE DU PLAN
  N-P4  normalisation du plan (`mx = max(pk) or 1` puis `if mx > 1 else 0.0`)
          media 65/2 : pics_signal_faible_pas_confondu_avec_le_silence,
                       pics_signal_faible_a_bien_une_crete_de_1_en_s8
  N-P5  repartition du plan (`step = max(1, n // bins)`)
          media 65/2 : pics_source_courte_la_seconde_moitie_porte_du_signal,
                       pics_source_courte_depasse_le_plafond_de_100_cases_du_plan
  N-P6  `n = max(1, len(a))` du plan au lieu de lever
          media 64/3 : pics_sans_flux_audio_leve,
                       route_peaks_415_sans_flux_audio,
                       route_peaks_415_nomme_le_fichier
  N-P7  `_cache_path` par `rstrip("0123456789")`, comme le plan
          media 66/1 : cache_genre_inconnu_leve SEULE. DECLARE : les trois
          familles recoivent la MEME extension sous les deux formes (mesure
          en tete) — ce que la forme du plan perd, c'est le refus d'un genre
          inconnu, et c'est la seule ligne qui puisse les separer.

  LES SEPT AUTRES
  N-P8  garde video retiree de `strip` / `proxy`
          media 64/3 : route_strip_415_sur_une_image,
                       route_proxy_post_415_sur_une_image,
                       route_proxy_post_415_sur_un_son.
          DECLARE : route_strip_415_sur_un_son_par_refus_ffmpeg reste VERTE —
          ffmpeg refuse deja le filmstrip d'un `.wav`. Cette ligne tient le
          CODE (415 nomme, pas 500), pas la garde ; la ligne discriminante
          pour le son est celle du proxy, que ffmpeg accepterait.
  N-P9  garde de boucle locale retiree
          media 63/4 : les quatre lignes route_hors_boucle_locale_403_*
  N-P10 temporaire finissant par « .tmp » (sans extension utile)
          media 51/16 — c'est le defaut REEL trouve par ce banc a sa premiere
          execution : sans extension, ffmpeg n'a pas de muxer a deduire et
          rend « Error opening output files: Invalid argument ». Filmstrip et
          apercu echouaient a 100 %. Les seize : filmstrip_6x,
          filmstrip_en_cache, filmstrip_borne_appliquee_a_l_image,
          filmstrip_balaie_la_source, proxy_duree_source, proxy_hauteur_480,
          proxy_gop_court, proxy_en_cache, route_strip_200_jpeg,
          route_strip_sert_bien_468x44, route_proxy_get_200_apres_fabrication,
          route_proxy_post_ne_refabrique_pas, job_proxy_termine,
          job_proxy_hors_du_filtre_du_selecteur_d_assets,
          cout_un_proxy_ne_coute_rien, et aucun_appel_n_a_plante.
  N-P11 bornes de `bins` retirees        media 65/2 (les deux ecretages)
  N-P12 bornes de `strip` retirees       media 64/3 (les deux bornes +
                                         aucun_appel_n_a_plante)
  N-P13 `mtime` retire de la cle de cache media 66/1 :
                                         cache_change_avec_le_mtime SEULE

  LES SEPT NOUVELLES — une par ligne ajoutee ou reparee le 05/09/2026, et
  CHACUNE ne rend qu'UNE SEULE ligne rouge, dans ce banc et pas dans les
  deux autres (sources 67/0, remplacer 99/0 pour les sept).
  N-P15 la route `peaks` revient a `peaks_path` (elle appelle `peaks`, JETTE
        son dict et reconstruit un chemin de cache)
          media 66/1 : route_peaks_sert_l_onde_partielle_au_lieu_de_lever
  N-P16 `peaks` MET EN CACHE l'onde partielle
          media 66/1 : pics_onde_partielle_rendue_mais_jamais_mise_en_cache
  N-P17 `_dur` force a 0 dans `strip` (donc `fps = n / 0,1` : les six
        vignettes viennent des 0,1 PREMIERES secondes au lieu de la duree)
          media 66/1 : filmstrip_balaie_la_source
  N-P18 `where` de provider retire de `Pipeline.list_jobs`
          media 66/1 : job_proxy_hors_de_la_fenetre_de_api_jobs
  N-P19 `!=` NU (sans `coalesce`) dans `Pipeline.list_jobs`
          media 66/1 : api_jobs_garde_les_jobs_a_provider_nul
  N-P20 `where` de provider retire de `GET /api/cost/usage`
          media 66/1 : cout_un_proxy_ne_coute_rien
  N-P21 la route `strip` sert une planche d'une AUTRE TAILLE (`n + 1`)
          media 66/1 : route_strip_sert_bien_468x44. C'est la mutation que
          l'ancienne forme de cette ligne (`content[:2] == JPEG`) laissait
          passer : elle ne regardait pas les dimensions qu'elle nomme.

LA LECON GENERALE DE CE BANC, ET ELLE VAUT POUR TOUT LE CHANTIER : UN TEMOIN
DISTINGUABLE SE RETOURNE CONTRE TOUTE ASSERTION D'INEGALITE. Les gardes
`CH` / `PK` / `SH` rendent un temoin NUMEROTE (« ·ECHEC#n ») justement pour
que deux echecs ne se confondent pas — c'est ce qui ferme la faute n°6. Mais
`a != b`, `not (…)`, `x not in y` sont alors VRAIS PAR CONSTRUCTION entre
deux temoins, et la ligne verdit sans avoir rien mesure. MESURE le
05/09/2026 : CINQ lignes de ce banc etaient dans ce cas
(cache_un_fichier_par_reglage, cache_change_avec_le_mtime,
job_proxy_hors_du_filtre_du_selecteur_d_assets, cache_hors_d_outputs_videos,
cache_introuvable_par_nom_a_la_racine_d_outputs) — plus une sixieme, ajoutee
le meme jour, qui l'aurait ete (job_proxy_hors_de_la_fenetre_de_api_jobs).
LA REGLE : toute assertion NEGATIVE doit d'abord exiger que ses operandes
SOIENT ce qu'ils pretendent etre (un chemin de cache, un job `done`, un
identifiant non vide), et seulement ensuite les comparer. Le temoin dit ce
qui a echoue ; il ne doit jamais servir a repondre a la question posee.

LA GARDE DE LA FAUTE N°6, MESUREE PLUTOT QUE PROMISE. Le banc a ete relance
le 05/09/2026 avec ffmpeg et ffprobe HORS DU PATH (`PATH=C:/Windows/System32;
C:/Windows`, meme python), c'est-a-dire dans l'etat ou les sept fixtures
n'existent pas et ou tout sous-processus leve `FileNotFoundError` :
  AVANT les gardes de fixture — MORT sur `os.utime(COURT, …)`, traceback,
    AUCUNE ligne de compte imprimee, sections [3] a [6] jamais jouees.
  APRES — 15/67, la ligne de compte EST imprimee, `fixtures_ffmpeg_fabriquees`
    arrive EN TETE des rouges en nommant les fichiers absents, et
    `aucun_appel_n_a_plante` compte les appels gardes qui ont leve.
  LES QUINZE VERTES, UNE A UNE, parce que « elles le sont a bon droit » est
  precisement le genre d'affirmation qui se verifie mal : cache_genre_inconnu
  _leve et cache_source_illisible_leve (aucun media) ; pics_sans_flux_audio
  _leve et filmstrip_source_illisible_leve_une_MediaError (elles exigent une
  `MediaError` — DECLARE : sans ffmpeg elles restent vertes pour une RAISON
  DIFFERENTE, « ffmpeg introuvable » et non « pas de flux audio » ; c'est le
  TYPE qui est mesure, pas le motif) ; pics_onde_partielle_rendue_mais_jamais
  _mise_en_cache et route_peaks_sert_l_onde_partielle_au_lieu_de_lever (elles
  FORCENT le sous-processus, par construction — voir `_RunPartiel`) ; les
  trois 404 et les quatre 403 (la route refuse avant tout media) ;
  api_jobs_garde_les_jobs_a_provider_nul (base seule) ; et
  job_proxy_le_litteral_du_provider_est_celui_du_service (une constante).
  Le compte precedent, « 17 vertes a bon droit », etait FAUX de trois : les
  trois assertions d'inegalite ci-dessus verdissaient a vide. Deux autres
  (cache_hors_d_outputs_videos, cache_introuvable_par_nom_a_la_racine
  _d_outputs) ont ete trouvees en appliquant la meme regle et fermees.

LA FAUTE N°6 DU CHANTIER (« un banc qui MEURT au lieu de rougir ») est ici
sur son terrain le plus favorable : ce fichier manipule des SOUS-PROCESSUS et
des FICHIERS BINAIRES. Toute lecture nue — `subprocess` dont on lit
`stdout`, `Image.open`, `json.loads`, `asyncio.run`, un appel a `MM.*` qui
peut lever `MediaError` — passe donc par une garde qui rend un TEMOIN
NUMEROTE ET DISTINGUABLE (`temoin`, `SH`, `S8`, `PK`, `PKS`, `MX`, `MN`,
`CH`, `IM`, `IMB`, `TEINTES`, `api`, `JOB`), jamais un `None` ni un `-1` nu
qui remplacerait la mort par une assertion creuse.

CE QUE CE BANC N'AFFIRME PAS
  * Il ne mesure AUCUN gain de fluidite. La cible du plan — p95 des
    intervalles rAF < 33 ms, premier `seeked` < 150 ms — se mesure DANS LE
    NAVIGATEUR, par `scripts/qa/qa-montage-scrub.js`, que l'utilisateur lance
    avec le backend demarre. Aucune ligne ici ne dit que le balayage est plus
    fluide ; elles disent que les precalculs existent, sont justes et sont
    caches.
  * Il ne mesure aucun COUT. Le decodage `s8` est un boucle Python sur des
    tranches d'`array` ; on n'a pas chronometre `peaks` sur une source
    longue, et aucun chiffre de duree n'est cite nulle part dans ce lot.
  * LIMITE ASSUMEE du `s8` (« sans numpy », contrainte du plan) : 8 bits par
    echantillon, donc une crete sous ≈ −44 dBFS est indiscernable de la
    suivante. C'est mesure (voir 2a), pas suppose. Un vumetre demanderait
    autre chose ; une forme d'onde de montage, non.
  * La NORMALISATION est RELATIVE (par la crete du morceau) : un extrait
    discret remplit sa bande autant qu'un extrait fort. C'est un choix, pas
    un defaut — mais aucune ligne ici ne dit qu'une hauteur de pic vaut un
    niveau absolu.
  * Le cache NE SE PURGE PAS tout seul : la cle porte le `st_mtime_ns` de la
    source, donc une source modifiee obtient une NOUVELLE cle et l'ancienne
    entree reste sur le disque a jamais. Rien n'est perdu par une purge
    manuelle (tout se recalcule), rien n'est reclame non plus.
  * Les deux fenetres de [5-bis] sont mesurees sur la base du BANC (trois
    jobs), pas sur la base reelle. Elles disent que la requete filtre et que
    le `coalesce` tient ; elles ne disent rien du nombre de proxys qu'un
    usage reel produirait — `POST /proxy` n'a a ce jour aucun appelant.
  * Aucune ligne ici ne dit que la facture GLOBALE soit juste. Ce lot n'a
    ferme que le cas qu'il ouvrait lui-meme ; la branche « campaign » par
    defaut de `_job_to_cost`, qui facturait TOUT provider qu'elle ne nommait
    pas (`asset3d` y tombait aussi), a ete fermee ENSUITE, par la tache 8b —
    c'est `tests/test_cost_usage.py` qui la tient, et lui seul.
  * Aucune ligne ne mesure la CONCURRENCE. L'ecriture est atomique par
    construction (temporaire a nom unique + `os.replace`) et la ligne
    `filmstrip_en_cache` verifie qu'un second appel ne REECRIT pas ; deux
    appels SIMULTANES ne sont pas joues.

PROTOCOLE DE TOUT CHIFFRE CITE ICI ET DANS `montage_media.py` : ffmpeg /
ffprobe `8.1.1-essentials_build-www.gyan.dev` (celui du PATH de la machine de
developpement — l'installation embarquee, elle, porte un 9.0 ; aucune des
mesures ci-dessus ne depend de la version, elles portent sur des formats de
fichier et une quantification), Windows 11 26200, AMD64 Family 23 ;
fixtures fabriquees par `lavfi` dans le temporaire du banc ; scripts
scratchpad/mesure_plan.py, mesure_ampl.py, mesure2.py, mesure3.py.

LA GARDE DE LA FAUTE N°6, MESUREE PLUTOT QUE PROMISE. Le banc a ete relance
le 05/09/2026 avec ffmpeg et ffprobe HORS DU PATH (`PATH=/c/Windows/System32:
/c/Windows`, meme python), c'est-a-dire dans l'etat ou les six fixtures
n'existent pas et ou tout sous-processus leve `FileNotFoundError` :
  AVANT les gardes de fixture — MORT sur `os.utime(COURT, …)`, traceback,
    AUCUNE ligne de compte imprimee, sections [3] a [6] jamais jouees.
  APRES — 17/44, la ligne de compte EST imprimee, `fixtures_ffmpeg_fabriquees`
    arrive EN TETE des rouges en nommant les six fichiers absents, et
    `aucun_appel_n_a_plante` compte 39 appels gardes qui ont leve. Les 17
    vertes le sont a bon droit : ce sont les lignes qui n'ont besoin d'aucun
    media (le refus d'un genre inconnu, le refus d'une source illisible, les
    403 de boucle locale, les 404 de source introuvable, l'emplacement du
    cache).

LA FAUTE N°6 DU CHANTIER (« un banc qui MEURT au lieu de rougir ») est ici
sur son terrain le plus favorable : ce fichier manipule des SOUS-PROCESSUS et
des FICHIERS BINAIRES. Toute lecture nue — `subprocess` dont on lit
`stdout`, `Image.open`, `json.loads`, `asyncio.run`, un appel a `MM.*` qui
peut lever `MediaError` — passe donc par une garde qui rend un TEMOIN
NUMEROTE ET DISTINGUABLE (`temoin`, `SH`, `PK`, `PKS`, `MX`, `MN`, `CH`,
`IM`, `api`, `JOB`), jamais un `None` ni un `-1` nu qui remplacerait la mort
par une assertion creuse."""
import array
import asyncio
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp7_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from httpx import AsyncClient, ASGITransport                # noqa: E402
from PIL import Image                                       # noqa: E402
from app.config import settings                             # noqa: E402
from app.main import app                                    # noqa: E402
from app.services import montage_media as MM                # noqa: E402
from app.services import montage_service as M               # noqa: E402
from app.services.storage import (JobRecord,                # noqa: E402
                                  async_session_factory, init_db)

FF, FP = "ffmpeg", "ffprobe"

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
    """TEMOIN d'un appel qui a LEVE — NUMEROTE (deux echecs ne se valent
    jamais) et DISTINGUABLE (jamais `None`, jamais `""`). Voir l'en-tete."""
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


class _ShEchec:
    """Sous-processus qui n'a pas pu s'executer. `returncode` NEGATIF (jamais
    0), `stdout`/`stderr` porteurs du temoin — donc `r.stdout.strip() ==
    "480"` reste FAUX, et `len(r.stdout.splitlines())` ne peut pas atteindre
    un seuil par hasard (une seule ligne)."""

    def __init__(self, t):
        self.returncode = -1
        self.stdout = t
        self.stderr = t


def SH(args):
    """`subprocess.run` garde. `ffmpeg`/`ffprobe` absent leve
    `FileNotFoundError` : sans cette garde, la premiere fixture tuerait le
    banc avant la moindre ligne de compte."""
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300)
    except Exception as e:
        t = temoin(e)
        print(f"  ----  {args[0]} {' '.join(str(a) for a in args[1:4])}… a leve : {t}")
        return _ShEchec(t)


def PK(fabrique, quoi=""):
    """Resultat d'un appel a `montage_media`, ou un dict-temoin. JAMAIS `{}` :
    un dict vide verdirait une comparaison a une cle absente."""
    try:
        return fabrique()
    except Exception as e:
        t = temoin(e)
        print(f"  ----  {quoi} a leve : {t}")
        return {"_echec": t}


def CH(fabrique, quoi=""):
    """Comme `PK`, pour un appel qui rend un CHEMIN. Le temoin est une chaine
    finissant par « ·ECHEC#n » — un marqueur sans point ni separateur, donc
    `pathlib.Path(temoin).suffix` ne peut egaler aucune vraie extension."""
    try:
        return fabrique()
    except Exception as e:
        t = temoin(e)
        print(f"  ----  {quoi} a leve : {t}")
        return t


def LEVE(fabrique, quoi=""):
    """Le NOM de l'exception levee, ou la chaine « AUCUNE ». Sert aux lignes
    qui exigent qu'un appel LEVE : sans cette forme, un `try/except: pass`
    rendrait la ligne verte a vide."""
    try:
        fabrique()
        return "AUCUNE"
    except Exception as e:
        return type(e).__name__


def PKS(d):
    """La liste des pics, ou un TEMOIN qui n'est pas une liste."""
    if not isinstance(d, dict) or "peaks" not in d:
        return "SANS_CLE_peaks: %r" % (d,)
    v = d["peaks"]
    if not isinstance(v, list) or not v:
        return "peaks_n_est_pas_une_liste_non_vide: %r" % (v,)
    return v


def MX(v):
    """Crete d'une liste de pics, ou −1.0. Le temoin est HORS du domaine
    0..1 : il ne peut donc egaler ni 1.0 (`pics_normalises_sinus`) ni 0.0
    (`silence_a_zero`), et ces deux lignes rougissent au lieu de verdir."""
    return max(v) if isinstance(v, list) and v else -1.0


def MN(v):
    """Creux d'une liste de pics, ou −1.0 — sous TOUT seuil que les lignes
    comparent (`min > 0.8`), donc rouge et jamais vert a vide."""
    return min(v) if isinstance(v, list) and v else -1.0


def IM(p):
    """Taille d'une image, ou un temoin. `Image.open` sur un JPEG tronque
    leve : nue, elle emporterait tout ce qui suit."""
    try:
        with Image.open(str(p)) as im:
            return im.size
    except Exception as e:
        t = temoin(e)
        print(f"  ----  Image.open({p}) a leve : {t}")
        return t


def IMB(b):
    """Taille d'une image recue en OCTETS (le corps d'une reponse), ou un
    temoin. Sans elle, une ligne qui veut juger des DIMENSIONS ne peut que
    regarder les deux premiers octets — et « n'importe quel JPEG passe »."""
    try:
        with Image.open(io.BytesIO(b or b"")) as im:
            return im.size
    except Exception as e:
        t = temoin(e)
        print(f"  ----  Image.open(<{len(b or b'')} octets>) a leve : {t}")
        return t


def S8(p):
    """Crete ABSOLUE du decodage `s8` BRUT de `p`, ou −1.

    C'est la grandeur sur laquelle repose le seuil mesure en tete (2a) : sous
    ≈ −44 dBFS la crete `s8` vaut 1, et la forme du plan la rendait nulle.
    `SH` ne convient pas ici — il decode en texte UTF-8 et detruirait les
    octets. Le temoin −1 est HORS du domaine (une crete est >= 0), donc une
    ligne qui exige `== 1` rougit quand la fixture manque au lieu de verdir."""
    try:
        r = subprocess.run([FF, "-v", "error", "-i", str(p), "-vn", "-ac", "1",
                            "-ar", "2000", "-f", "s8", "-"],
                           capture_output=True, timeout=300)
    except Exception as e:
        t = temoin(e)
        print(f"  ----  decodage s8 de {p} a leve : {t}")
        return -1
    a8 = array.array("b")
    try:
        a8.frombytes(r.stdout or b"")
    except Exception as e:
        print(f"  ----  s8 illisible : {temoin(e)}")
        return -1
    if not len(a8):
        return -1
    return max(max(a8), -min(a8))


def TEINTES(p, n=6, w=78, h=44):
    """Une teinte GROSSIERE par vignette d'une planche, ou une liste-temoin
    d'un seul element.

    Moyenne du TIERS CENTRAL de chaque tuile (les bords portent le fondu JPEG
    d'une tuile sur l'autre), quantifiee au quart de canal. Sert a mesurer
    qu'une planche BALAIE la source : six vignettes tirees de six instants
    d'une video qui change de couleur chaque seconde ne peuvent pas rendre la
    meme teinte. Le temoin est une liste d'UN element : `len(set(...)) >= 3`
    y est faux, donc rouge et jamais vert a vide."""
    try:
        with Image.open(str(p)) as im:
            rgb = im.convert("RGB")
            out = []
            for k in range(n):
                box = (k * w + w // 3, h // 3, k * w + 2 * w // 3, 2 * h // 3)
                px = rgb.crop(box).resize((1, 1), Image.BOX).getpixel((0, 0))
                out.append(tuple(c // 64 for c in px))
            return out
    except Exception as e:
        t = temoin(e)
        print(f"  ----  teintes de {p} ont leve : {t}")
        return [t]


class _RunPartiel:
    """Sous-processus qui a PRODUIT des octets ET s'est plaint (rc != 0).

    C'est la seule facon d'atteindre l'onde PARTIELLE de `peaks` : mesure le
    05/09/2026, douze cas de troncature et de corruption (wav, mp3, m4a, mp4 —
    moitie, quart, 90 %, milieu ecrase de 0xFF) rendent TOUS soit rc = 0 avec
    des octets (chemin normal, mis en cache), soit rc != 0 avec ZERO octet
    (chemin du 415). Pas un seul rc != 0 AVEC des octets. Forcer le
    sous-processus a un second merite : cette ligne-la ne depend pas de
    ffmpeg, donc elle rougit pour ce qu'elle mesure et pour rien d'autre."""

    def __init__(self, data):
        self.returncode = 1
        self.stdout = data
        self.stderr = b"[wav @ 0] Invalid data found when processing input"


class _RepIllisible:
    """Reponse-temoin d'une route qui a leve hors de FastAPI. `status_code`
    negatif : jamais 200, jamais 404, jamais 415."""

    def __init__(self, t):
        self.status_code = -1
        self.text = t
        self.content = b""
        self.headers = {}

    def json(self):
        raise ValueError(self.text)


def api(method, path, *, client=("127.0.0.1", 123), **kw):
    """Appel HTTP contre l'app ASGI, garde. `client` porte l'adresse vue par
    `request.client.host` — c'est ce qui permet de mesurer la garde de boucle
    locale sans lancer de serveur."""
    async def go():
        async with AsyncClient(transport=ASGITransport(app=app, client=client),
                               base_url="http://t", timeout=300.0) as c:
            return await c.request(method, path, **kw)
    try:
        return asyncio.run(go())
    except Exception as e:
        t = temoin(e)
        print(f"  ----  {method} {path} a leve : {t}")
        return _RepIllisible(t)


def J(resp):
    """Corps JSON, ou un dict-temoin. JAMAIS `{}`."""
    try:
        v = resp.json()
    except Exception as e:
        return {"_illisible": temoin(e)}
    return v if isinstance(v, dict) else {"_liste": v}


def _job_temoin(t):
    """Un job-temoin dont TOUTES les cles portent une chaine NON VIDE.

    C'est la forme exacte de la faute n°2 que ce banc a failli commettre :
    la section [5] teste `not j.get("final_video_path")`, qui serait VERTE
    sur un dict vide ou sur un job absent — on aurait mesure « le job n'a pas
    d'artefact » en ne mesurant rien du tout. MESURE le 05/09/2026 : avec un
    repli `{"_absent": …}`, trois des six lignes de [5] restaient vertes
    alors que la route levait avant meme de creer le job."""
    return {"provider": t, "status": t, "final_video_path": t,
            "video_path": t, "error": t}


def JOB(jid):
    """Le JobRecord `jid` reduit a ce que ce banc juge, ou un job-temoin.
    Les chemins sont rendus TELS QUELS (None compris) : le point de la
    section [5] est justement qu'ils soient absents."""
    async def go():
        async with async_session_factory() as s:
            j = await s.get(JobRecord, str(jid))
            if j is None:
                return _job_temoin("JOB_ABSENT:%s ·ECHEC" % (jid,))
            return {"provider": j.provider, "status": j.status,
                    "final_video_path": j.final_video_path,
                    "video_path": j.video_path, "error": j.error}
    try:
        return asyncio.run(go())
    except Exception as e:
        return _job_temoin(temoin(e))


def GARDE(fn, quoi=""):
    """Un geste de FIXTURE (`os.utime`, `write_bytes`) qui LEVE ne doit pas
    tuer le banc. Ce ne sont pas des unites sous test, mais l'invariant
    « rougir plutot que mourir » vaut de BOUT EN BOUT, sans quoi il ne vaut
    nulle part. MESURE le 05/09/2026 : lance avec ffmpeg HORS du PATH, ce
    banc MOURAIT sur `os.utime(COURT, …)` — les fixtures n'existent pas,
    `FileNotFoundError`, traceback, AUCUNE ligne de compte imprimee et les
    sections [3] a [6] jamais jouees. Avec cette garde il va jusqu'au bout et
    imprime son compte, `fixtures_ffmpeg_fabriquees` en tete des rouges."""
    try:
        fn()
        return True
    except Exception as e:
        print(f"  ----  {quoi} a leve : {temoin(e)}")
        return False


def Q(src: dict) -> str:
    """Un `src` en chaine de requete."""
    from urllib.parse import quote
    return quote(json.dumps(src, ensure_ascii=False))


# ───────────────────────────────────────────────────────────── fixtures ────
ROOT = pathlib.Path(TMP)
LIB = ROOT / "lib"
LIB.mkdir(parents=True, exist_ok=True)

MUS = str(LIB / "mus.wav")          # sinus 440 Hz, 6,000 s
SIL = str(LIB / "sil.wav")          # silence numerique, 2 s
FAIBLE = str(LIB / "faible.wav")    # sinus a −52 dB : crete `s8` = 1
COURT = str(LIB / "court.wav")      # 0,05 s = 100 echantillons a 2 000 Hz
V1 = str(LIB / "plan.mp4")          # 4,000 s, 25 i/s, 320x240, AVEC audio
PNG = str(LIB / "carton.png")
GLB = str(LIB / "model.glb")

SH([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=6",
    "-ac", "1", "-ar", "44100", MUS])
SH([FF, "-y", "-v", "error", "-f", "lavfi",
    "-i", "anullsrc=r=44100:cl=mono:d=2", SIL])
SH([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=2",
    "-af", "volume=-52dB", "-ac", "1", "-ar", "44100", FAIBLE])
SH([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=0.05",
    "-ac", "1", "-ar", "44100", COURT])
SH([FF, "-y", "-v", "error", "-f", "lavfi",
    "-i", "testsrc=size=320x240:rate=25:d=4", "-f", "lavfi",
    "-i", "sine=f=330:d=4", "-pix_fmt", "yuv420p", "-shortest", V1])
SH([FF, "-y", "-v", "error", "-f", "lavfi",
    "-i", "color=c=red:s=320x240:d=0.04", "-frames:v", "1", PNG])
GARDE(lambda: pathlib.Path(GLB).write_bytes(b"glTF\x02\x00\x00\x00faux"),
      "ecriture du faux .glb")

# 4 s de video qui CHANGE de couleur chaque seconde — rouge, vert, bleu,
# blanc. C'est la seule fixture dont on puisse dire, en regardant la planche,
# de QUEL instant vient chaque vignette : `plan.mp4` (testsrc) change a
# chaque image et ne distingue donc pas « six instants repartis sur 4 s » de
# « six images consecutives du debut ».
V4C = str(LIB / "quatre_couleurs.mp4")
SH([FF, "-y", "-v", "error",
    "-f", "lavfi", "-i", "color=c=red:s=320x240:r=25:d=1",
    "-f", "lavfi", "-i", "color=c=lime:s=320x240:r=25:d=1",
    "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=25:d=1",
    "-f", "lavfi", "-i", "color=c=white:s=320x240:r=25:d=1",
    "-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]",
    "-map", "[v]", "-pix_fmt", "yuv420p", V4C])

# LA GARDE DES FIXTURES, et il en faut une : tout ce banc repose sur cinq
# fichiers fabriques par ffmpeg. S'ils manquent, les quarante lignes qui
# suivent rougissent une a une sans jamais dire POURQUOI. Cette ligne-ci le
# dit en un mot, et elle rougit d'abord.
_manquants = [os.path.basename(f)
              for f in (MUS, SIL, FAIBLE, COURT, V1, PNG, V4C)
              if not os.path.exists(f) or os.path.getsize(f) == 0]
check("fixtures_ffmpeg_fabriquees", _manquants == [],
      f"absents ou vides : {_manquants}")

asyncio.run(init_db())


print("\n[1] _cache_path — une extension par FAMILLE, un genre inconnu qui LEVE.")
# Le `kind.rstrip(\"0123456789\")` du plan rendait `strip12x78x` et non
# `strip` : l'extension `.jpg` sortait du REPLI du `.get`. Les trois familles
# recevaient bien la bonne extension, mais une seule des trois par le chemin
# prevu — et un genre mal orthographie serait devenu un `.jpg` silencieux.
c_pk = CH(lambda: MM._cache_path(MUS, "peaks120"), "_cache_path(peaks120)")
c_st = CH(lambda: MM._cache_path(V1, "strip12x78x44"), "_cache_path(strip…)")
c_px = CH(lambda: MM._cache_path(V1, "proxy"), "_cache_path(proxy)")
check("cache_ext_peaks_json", pathlib.Path(str(c_pk)).suffix == ".json", str(c_pk))
check("cache_ext_strip_jpg", pathlib.Path(str(c_st)).suffix == ".jpg", str(c_st))
check("cache_ext_proxy_mp4", pathlib.Path(str(c_px)).suffix == ".mp4", str(c_px))
check("cache_genre_inconnu_leve",
      LEVE(lambda: MM._cache_path(MUS, "vignette"), "genre inconnu") == "MediaError",
      LEVE(lambda: MM._cache_path(MUS, "vignette")))
check("cache_source_illisible_leve",
      LEVE(lambda: MM._cache_path(str(LIB / "jamais_cree.wav"), "proxy"))
      == "MediaError")
# Le nom porte le GENRE COMPLET : deux reglages ne peuvent pas se marcher
# dessus dans le cache. Sans cette ligne, `strip6x78x44` et `strip12x78x44`
# pourraient partager un fichier et le premier appel deciderait pour l'autre.
c_st6 = CH(lambda: MM._cache_path(V1, "strip6x78x44"), "_cache_path(strip6…)")
# `!=` ENTRE DEUX APPELS GARDES SE PASSE DE SON UNITE : le temoin de `CH`
# est NUMEROTE (« ·ECHEC#n »), donc deux echecs different TOUJOURS et cette
# ligne verdissait sans rien mesurer. MESURE le 05/09/2026 (banc relance avec
# `PATH=C:/Windows/System32;C:/Windows`) : verte alors que `_cache_path`
# n'avait jamais rendu de chemin. On exige donc d'abord DEUX VRAIS chemins
# (parent = le dossier de cache), et seulement ensuite qu'ils different.
check("cache_un_fichier_par_reglage",
      pathlib.Path(str(c_st6)).parent.name == "montage_cache"
      and pathlib.Path(str(c_st)).parent.name == "montage_cache"
      and str(c_st6) != str(c_st),
      f"{c_st6} vs {c_st}")
# ... et la cle suit le `st_mtime_ns` de la source : une source modifiee
# n'est jamais servie depuis l'entree d'avant.
_av = str(CH(lambda: MM._cache_path(COURT, "proxy")))
GARDE(lambda: os.utime(COURT, ns=(1_700_000_000_000_000_000,
                                  1_700_000_000_000_000_000)),
      "os.utime(COURT)")
_ap = str(CH(lambda: MM._cache_path(COURT, "proxy")))
# meme piege que ci-dessus, meme remede : deux temoins numerotes different
# toujours. Les deux cotes doivent d'abord ETRE des chemins de cache.
check("cache_change_avec_le_mtime",
      pathlib.Path(_av).parent.name == "montage_cache"
      and pathlib.Path(_ap).parent.name == "montage_cache"
      and _av != _ap, f"{_av}\n      vs {_ap}")


print("\n[2] peaks — les huit lignes du plan, plus les trois ecarts mesures.")
pk = PK(lambda: MM.peaks(MUS, bins=120), "peaks(MUS, 120)")
check("pics_120", len(PKS(pk)) == 120 and abs(pk.get("dur", -1) - 6.0) < 0.1,
      f"{len(PKS(pk)) if isinstance(PKS(pk), list) else PKS(pk)} / {pk.get('dur')}")
check("pics_normalises_sinus", MX(PKS(pk)) == 1.0 and MN(PKS(pk)) > 0.8,
      f"max={MX(PKS(pk))} min={MN(PKS(pk))}")
sil = PK(lambda: MM.peaks(SIL, bins=20), "peaks(SIL, 20)")
check("silence_a_zero", MX(PKS(sil)) == 0.0, f"max={MX(PKS(sil))}")
check("cache_par_mtime",
      PK(lambda: MM.peaks(MUS, bins=120), "peaks(MUS, 120) bis").get("bins") == 120
      and pathlib.Path(str(CH(lambda: MM._cache_path(MUS, "peaks120")))).exists(),
      str(CH(lambda: MM._cache_path(MUS, "peaks120"))))

# 2a — L'ECART SUR LA NORMALISATION. `mx > 1 else 0.0` rendait DES ZEROS pour
# tout signal dont la crete `s8` vaut 1, c'est-a-dire tout ce qui est sous
# ≈ −44 dBFS (mesure du seuil en tete de fichier). Le silence et le tres
# faible etaient alors le MEME dessin. Les deux lignes sont SEPAREES : une
# seule ligne agregee resterait verte si l'un des deux cotes repassait.
faible = PK(lambda: MM.peaks(FAIBLE, bins=20), "peaks(FAIBLE, 20)")
check("pics_signal_faible_pas_confondu_avec_le_silence",
      MX(PKS(faible)) == 1.0, f"max={MX(PKS(faible))} (silence = 0.0)")
# Cette ligne NOMME une crete de 1 : elle la MESURE desormais, sur le
# decodage `s8` BRUT, en plus de tenir la distinction d'avec le silence.
# Sans cette premiere moitie, son nom promettait ce que son corps ne
# regardait pas — et c'est ce `1` qui fonde tout le seuil mesure en tete (2a).
_s8_faible, _s8_sil = S8(FAIBLE), S8(SIL)
check("pics_signal_faible_a_bien_une_crete_de_1_en_s8",
      _s8_faible == 1 and MX(PKS(faible)) != MX(PKS(sil)),
      f"crete s8 brute = {_s8_faible} (attendu 1, silence = {_s8_sil}) · "
      f"faible={MX(PKS(faible))} silence={MX(PKS(sil))}")

# 2b — L'ECART SUR LA REPARTITION. La source fait 0,05 s, soit n = 100
# echantillons a 2 000 Hz, pour 300 cases. Sous `step = max(1, n // bins)`,
# `step` vaut 1 et le test `i * step < n` ferme TOUTE case d'indice >= n :
# les cases 100 a 299 sont vides PAR CONSTRUCTION, quel que soit le signal —
# 200 cases de silence invente, et les 100 premieres seules porteuses (97
# mesurees, trois echantillons tombant sur un passage par zero du sinus).
# Les DEUX lignes ci-dessous tiennent chacune un cote de cette borne.
court = PK(lambda: MM.peaks(COURT, bins=300), "peaks(COURT, 300)")
_pc = PKS(court)
_nz = sum(1 for v in _pc if v > 0) if isinstance(_pc, list) else -1
# a) la SECONDE MOITIE de l'onde porte du signal. Sous la forme du plan elle
#    en porte exactement ZERO — c'est la queue muette, celle qu'on voit.
check("pics_source_courte_la_seconde_moitie_porte_du_signal",
      isinstance(_pc, list) and len(_pc) == 300 and any(v > 0 for v in _pc[150:]),
      f"{sum(1 for v in _pc[150:] if v > 0) if isinstance(_pc, list) else _pc}"
      f"/150 cases porteuses dans la seconde moitie")
# b) et le COMPTE depasse le plafond STRUCTUREL de la forme du plan : au plus
#    n = 100 cases porteuses, puisque seules les n premieres recoivent un
#    echantillon. Mesure : 97 pour la forme du plan, 291 pour celle-ci.
check("pics_source_courte_depasse_le_plafond_de_100_cases_du_plan",
      isinstance(_pc, list) and len(_pc) == 300 and _nz > 100,
      f"{_nz}/300 cases porteuses (plafond de la forme du plan : n = 100)")

# 2c — AUCUN FLUX AUDIO N'EST PAS UN SILENCE. Le plan rendait une onde plate
# et `dur = 0.001` ; on LEVE, et la route repond 415 (section [4]).
check("pics_sans_flux_audio_leve", LEVE(lambda: MM.peaks(PNG, bins=20))
      == "MediaError", LEVE(lambda: MM.peaks(PNG, bins=20)))

# Les BORNES de `bins` — parametre CLIENT, meme lecon que le `[:60]` du
# libelle au pre-vol de P8-bis.
gros = PK(lambda: MM.peaks(MUS, bins=999999), "peaks(MUS, 999999)")
petit = PK(lambda: MM.peaks(MUS, bins=1), "peaks(MUS, 1)")
check("pics_bins_ecrete_en_haut", len(PKS(gros)) == 2000,
      str(len(PKS(gros)) if isinstance(PKS(gros), list) else PKS(gros)))
check("pics_bins_ecrete_en_bas", len(PKS(petit)) == 8,
      str(len(PKS(petit)) if isinstance(PKS(petit), list) else PKS(petit)))

# LE CACHE EST BIEN RELU, et ce n'est pas une deduction : on remplace le
# contenu du fichier de cache par un TEMOIN reconnaissable, puis on rappelle
# `peaks`. S'il recalculait, il rendrait le sinus.
_cpk = pathlib.Path(str(CH(lambda: MM._cache_path(MUS, "peaks120"))))
try:
    _cpk.write_text(json.dumps({"peaks": [0.5] * 120, "dur": 42.0, "bins": 120}),
                    encoding="utf-8")
    _ecrit_ok = True
except OSError as e:
    print(f"  ----  ecriture du temoin de cache a leve : {temoin(e)}")
    _ecrit_ok = False
relu = PK(lambda: MM.peaks(MUS, bins=120), "peaks(MUS, 120) relu")
check("pics_relus_du_cache_sans_recalcul",
      _ecrit_ok and relu.get("dur") == 42.0, f"dur={relu.get('dur')}")
# ... et un cache ILLISIBLE ne fait pas tomber la route : on recalcule.
try:
    _cpk.write_text("{ ceci n'est pas du json", encoding="utf-8")
    _casse_ok = True
except OSError:
    _casse_ok = False
recalc = PK(lambda: MM.peaks(MUS, bins=120), "peaks(MUS, 120) cache casse")
check("pics_cache_illisible_recalcule_au_lieu_de_lever",
      _casse_ok and abs(recalc.get("dur", -1) - 6.0) < 0.1
      and MX(PKS(recalc)) == 1.0, f"dur={recalc.get('dur')}")


# 2d — L'ONDE PARTIELLE, ET LA ROUTE QUI LA SERT. Quand ffmpeg se plaint mais
# a tout de meme produit des octets, `peaks` rend l'onde SANS la mettre en
# cache (« une onde partielle vaut mieux qu'une bande vide », et la cle ne
# porte que le mtime : une entree ecrite la resterait servie apres reparation
# du decodeur). Jusqu'au 05/09/2026 la route passait par `peaks_path`, qui
# APPELAIT `peaks`, JETAIT son dict et reconstruisait un chemin : le fichier
# n'existait pas, la route levait un 502, et le client ne recevait JAMAIS
# cette onde-la. AUCUNE ligne ne couvrait ce chemin. Voir `_RunPartiel` pour
# la raison de forcer le sous-processus (douze cas reels mesures, aucun ne
# produit rc != 0 AVEC des octets).
PARTIEL = str(LIB / "partiel.wav")
GARDE(lambda: pathlib.Path(PARTIEL).write_bytes(b"RIFFfaux"),
      "ecriture de partiel.wav")
_ech = bytes(bytearray(i % 101 for i in range(400)))   # 0,2 s a 2 000 Hz
_vrai_run = MM._run
MM._run = lambda cmd, *, timeout, quoi: _RunPartiel(_ech)
try:
    part = PK(lambda: MM.peaks(PARTIEL, bins=20), "peaks(PARTIEL, 20)")
    _c_part = pathlib.Path(str(CH(lambda: MM._cache_path(PARTIEL, "peaks20"),
                                  "_cache_path(partiel)")))
    r_part = api("GET", "/api/montage/peaks?bins=20&src="
                 + Q({"file_path": PARTIEL}))
finally:
    MM._run = _vrai_run
check("pics_onde_partielle_rendue_mais_jamais_mise_en_cache",
      len(PKS(part)) == 20 and MX(PKS(part)) == 1.0
      and abs(part.get("dur", -1) - 0.2) < 0.001
      and not _c_part.exists(),
      f"bins={len(PKS(part)) if isinstance(PKS(part), list) else PKS(part)} "
      f"max={MX(PKS(part))} dur={part.get('dur')} "
      f"cache_ecrit={_c_part.exists()}")
_d_part = J(r_part)
check("route_peaks_sert_l_onde_partielle_au_lieu_de_lever",
      r_part.status_code == 200 and len(PKS(_d_part)) == 20
      and MX(PKS(_d_part)) == 1.0,
      f"{r_part.status_code} {str(_d_part)[:160]}")


print("\n[3] strip et proxy — la sortie, le cache, les bornes.")
st = CH(lambda: MM.strip(V1, n=6, w=78, h=44), "strip(V1, 6, 78, 44)")
check("filmstrip_6x", IM(st) == (468, 44), str(IM(st)))
# LE CACHE : un second appel ne REECRIT pas le fichier. C'est aussi ce qui
# rend l'ecriture atomique observable — un `-y` sur place changerait le
# `mtime` et, pendant un `FileResponse`, tronquerait le fichier servi.
_m1 = os.path.getmtime(str(st)) if os.path.exists(str(st)) else -1.0
st2 = CH(lambda: MM.strip(V1, n=6, w=78, h=44), "strip(V1, 6, 78, 44) bis")
_m2 = os.path.getmtime(str(st2)) if os.path.exists(str(st2)) else -2.0
check("filmstrip_en_cache", str(st2) == str(st) and _m1 == _m2 and _m1 > 0,
      f"{_m1} vs {_m2}")
# BORNES des parametres clients : n ≤ 60, w/h ∈ 8..320. Mesurees sur le NOM
# du fichier de cache, qui porte le genre APRES ecretage — donc sur ce que le
# calcul a reellement fait, pas sur ce qui a ete demande.
st3 = CH(lambda: MM.strip(V1, n=999, w=9999, h=9999), "strip(V1, 999, 9999, 9999)")
check("filmstrip_bornes_les_parametres_clients",
      "strip60x320x320" in pathlib.Path(str(st3)).name, str(st3))
check("filmstrip_borne_appliquee_a_l_image", IM(st3) == (60 * 320, 320),
      str(IM(st3)))
# Une source qu'aucun demultiplexeur n'ouvre LEVE une MediaError NOMMEE (et
# non un CalledProcessError nu, qui sortirait en 500 sans message).
check("filmstrip_source_illisible_leve_une_MediaError",
      LEVE(lambda: MM.strip(GLB, n=6)) == "MediaError",
      LEVE(lambda: MM.strip(GLB, n=6)))
# LA PLANCHE BALAIE-T-ELLE LA SOURCE ? Rien ne le mesurait, et c'est TOUT
# l'interet de la fonction : `fps = n / duree` est la seule ligne qui repartit
# les six vignettes sur la duree. MESURE le 05/09/2026 — `_dur` force a 0
# (donc `fps = n / 0,1`, les six vignettes tirees des 0,1 PREMIERES secondes)
# laissait le banc a 61/0, AUCUNE rouge : l'image restait 468x44 et
# `filmstrip_6x` passait. Sur `quatre_couleurs.mp4` (rouge, vert, bleu, blanc,
# 1 s chacun) les six vignettes rendent QUATRE teintes distinctes ; sous la
# mutation elles n'en rendent qu'UNE (tout rouge).
_st4 = CH(lambda: MM.strip(V4C, n=6, w=78, h=44), "strip(V4C, 6, 78, 44)")
_t4 = TEINTES(_st4)
check("filmstrip_balaie_la_source", len(set(_t4)) >= 3,
      f"{len(set(_t4))} teintes distinctes sur six vignettes : {_t4}")

px = CH(lambda: MM.proxy(V1), "proxy(V1)")
r_dur = SH([FP, "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(px)])
try:
    _pxdur = float(r_dur.stdout.strip())
except (TypeError, ValueError):
    _pxdur = -1.0
check("proxy_duree_source", abs(_pxdur - 4.0) < 0.15, str(_pxdur))
r_h = SH([FP, "-v", "error", "-select_streams", "v", "-show_entries",
          "stream=height", "-of", "csv=p=0", str(px)])
check("proxy_hauteur_480", r_h.stdout.strip() == "480", r_h.stdout)
r_k = SH([FP, "-v", "error", "-skip_frame", "nokey", "-select_streams", "v",
          "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(px)])
_kf = [l for l in r_k.stdout.splitlines() if l.strip()]
# `-g 15` est un GOP de QUINZE IMAGES, pas « une image cle toutes les
# 0,5 s » comme l'ecrivait le plan : MESURE sur cette source a 25 i/s, sept
# cles a 0,000 / 0,600 / 1,200 / 1,800 / 2,400 / 3,000 / 3,600 s — 0,6 s
# d'intervalle. L'intervalle en SECONDES suit la cadence de la source ; ce
# qui est constant, c'est le nombre d'images a decoder depuis la cle
# precedente.
check("proxy_gop_court", len(_kf) >= 7, f"{len(_kf)} cles — {r_k.stdout[:80]!r}")
_pm1 = os.path.getmtime(str(px)) if os.path.exists(str(px)) else -1.0
px2 = CH(lambda: MM.proxy(V1), "proxy(V1) bis")
_pm2 = os.path.getmtime(str(px2)) if os.path.exists(str(px2)) else -2.0
check("proxy_en_cache", str(px2) == str(px) and _pm1 == _pm2 and _pm1 > 0,
      f"{_pm1} vs {_pm2}")


print("\n[4] les quatre routes — la garde video, les codes, la boucle locale.")
r = api("GET", "/api/montage/peaks?bins=120&src=" + Q({"file_path": MUS}))
d = J(r)
check("route_peaks_200", r.status_code == 200, f"{r.status_code} {r.text[:160]}")
check("route_peaks_sert_le_json_du_cache",
      len(PKS(d)) == 120 and abs(d.get("dur", -1) - 6.0) < 0.1, str(d)[:160])
r = api("GET", "/api/montage/peaks?src=" + Q({"job_id": "inexistant"}))
check("route_peaks_404_source_inconnue", r.status_code == 404,
      f"{r.status_code} {r.text[:160]}")
r = api("GET", "/api/montage/peaks?src=pas-du-json")
check("route_peaks_404_src_illisible", r.status_code == 404,
      f"{r.status_code} {r.text[:160]}")
# LA LIGNE DE L'ECART 2c, de bout en bout : un PNG n'a pas d'onde plate, il
# n'a PAS D'ONDE. 415 qui le nomme.
r = api("GET", "/api/montage/peaks?src=" + Q({"file_path": PNG}))
check("route_peaks_415_sans_flux_audio", r.status_code == 415,
      f"{r.status_code} {r.text[:160]}")
check("route_peaks_415_nomme_le_fichier", "carton.png" in (r.text or ""),
      r.text[:200])
# ... et un SON reste accepte : la route `peaks` n'a PAS de garde video, et
# c'est voulu (l'onde d'un plan V1, « le son du plan »).
r = api("GET", "/api/montage/peaks?bins=64&src=" + Q({"file_path": V1}))
check("route_peaks_accepte_une_video_avec_son", r.status_code == 200,
      f"{r.status_code} {r.text[:160]}")

r = api("GET", "/api/montage/strip?n=6&w=78&h=44&src=" + Q({"file_path": V1}))
check("route_strip_200_jpeg",
      r.status_code == 200 and r.headers.get("content-type") == "image/jpeg",
      f"{r.status_code} {r.headers.get('content-type')}")
# LES DIMENSIONS, et non la signature : tester les deux premiers octets
# laissait passer N'IMPORTE QUEL JPEG de n'importe quelle taille. Les 468x44
# etaient tenus ailleurs (`filmstrip_6x`), jamais par la ligne qui les nomme.
_st_srv = IMB(r.content)
check("route_strip_sert_bien_468x44", _st_srv == (468, 44),
      f"{_st_srv} — {len(r.content)} octets, tete={r.content[:4]!r}")
# LA GARDE VIDEO. MESURE : ffmpeg REUSSIT le filmstrip d'un PNG (six copies
# du meme carton) — sans cette garde, la route rendrait 200 et une planche
# vide de sens.
r = api("GET", "/api/montage/strip?src=" + Q({"file_path": PNG}))
check("route_strip_415_sur_une_image", r.status_code == 415,
      f"{r.status_code} {r.text[:160]}")
# CETTE LIGNE-CI N'EST PAS TENUE PAR LA GARDE, et il faut le dire : MESURE,
# ffmpeg REFUSE deja le filmstrip d'un `.wav` (« Output file does not contain
# any stream »), donc la mutation « garde video retiree » la laisse VERTE
# (415 par la `MediaError`, pas par la garde). Ce qu'elle tient reellement,
# c'est que ce refus sorte en 415 NOMME et non en 500 : c'est la frontiere de
# `_media_http`. La ligne DISCRIMINANTE pour le son est celle du proxy, plus
# bas — ffmpeg, lui, accepte de « proxifier » un `.wav`.
r = api("GET", "/api/montage/strip?src=" + Q({"file_path": MUS}))
check("route_strip_415_sur_un_son_par_refus_ffmpeg", r.status_code == 415,
      f"{r.status_code} {r.text[:160]}")

# `GET /proxy` avant toute fabrication : 404, jamais un encodage a la volee.
# Il faut une source NEUVE pour que le cache soit vide — `V1` a deja son
# proxy depuis la section [3].
V2 = str(LIB / "plan2.mp4")
SH([FF, "-y", "-v", "error", "-f", "lavfi",
    "-i", "testsrc=size=320x240:rate=25:d=2", "-pix_fmt", "yuv420p", V2])
r = api("GET", "/api/montage/proxy?src=" + Q({"file_path": V2}))
check("route_proxy_get_404_avant_fabrication", r.status_code == 404,
      f"{r.status_code} {r.text[:160]}")
r = api("POST", "/api/montage/proxy", json={"src": {"file_path": V2}})
d_post = J(r)
check("route_proxy_post_met_en_file",
      r.status_code == 200 and d_post.get("ready") is False
      and isinstance(d_post.get("job_id"), str) and d_post["job_id"],
      f"{r.status_code} {d_post}")
r = api("GET", "/api/montage/proxy?src=" + Q({"file_path": V2}))
check("route_proxy_get_200_apres_fabrication",
      r.status_code == 200 and r.headers.get("content-type") == "video/mp4",
      f"{r.status_code} {r.headers.get('content-type')} {r.text[:120]}")
r2 = api("POST", "/api/montage/proxy", json={"src": {"file_path": V2}})
d_post2 = J(r2)
check("route_proxy_post_ne_refabrique_pas",
      d_post2.get("ready") is True and d_post2.get("job_id") is None,
      str(d_post2))
r = api("POST", "/api/montage/proxy", json={"src": {"file_path": PNG}})
check("route_proxy_post_415_sur_une_image", r.status_code == 415,
      f"{r.status_code} {r.text[:160]}")
# LA LIGNE LA PLUS DISCRIMINANTE DE LA GARDE VIDEO : sur un `.wav`, ffmpeg
# REUSSIT (MESURE : rc=0, un mp4 sans image, `-vf scale` simplement ignore).
# Sans la garde, cette route rendrait donc 200 et un « apercu » muet et
# aveugle — un echec DISCRET, pas une erreur.
r = api("POST", "/api/montage/proxy", json={"src": {"file_path": MUS}})
check("route_proxy_post_415_sur_un_son", r.status_code == 415,
      f"{r.status_code} {r.text[:160]}")

# LA BOUCLE LOCALE. Les quatre routes, pas une seule : un appelant distant
# ne doit obtenir NI contenu NI travail de fond.
for _m, _p in (("GET", "/api/montage/peaks?src=" + Q({"file_path": MUS})),
               ("GET", "/api/montage/strip?src=" + Q({"file_path": V1})),
               ("GET", "/api/montage/proxy?src=" + Q({"file_path": V1}))):
    _r = api(_m, _p, client=("10.0.0.5", 4242))
    check("route_hors_boucle_locale_403_" + _p.split("?")[0].rsplit("/", 1)[-1]
          + "_" + _m.lower(), _r.status_code == 403,
          f"{_r.status_code} {_r.text[:120]}")
_r = api("POST", "/api/montage/proxy", json={"src": {"file_path": V1}},
         client=("10.0.0.5", 4242))
check("route_hors_boucle_locale_403_proxy_post", _r.status_code == 403,
      f"{_r.status_code} {_r.text[:120]}")


print("\n[5] LE PIEGE PRINCIPAL — le job de proxy ne porte AUCUN artefact.")
# VERROU 1. `montage_project` construit V1 depuis les jobs `done` dont
# l'artefact est une video, et `montage_newer` propose les jobs `done` plus
# recents de meme titre : les deux lisent `final_video_path or video_path`.
# Un job de proxy qui porterait son mp4 480p deviendrait donc un PLAN et une
# « version plus recente ». Il n'en porte pas — et c'est ce qui le rend aussi
# invisible du selecteur d'assets du bundle, qui filtre exactement
# `status==="done" && (video_path || final_video_path)` (P9).
_jid = d_post.get("job_id")
j = (JOB(_jid) if isinstance(_jid, str) and _jid
     else _job_temoin("PAS_DE_job_id:%r ·ECHEC" % (_jid,)))
check("job_proxy_provider_nomme", j.get("provider") == "montage_proxy",
      f'provider={j.get("provider")!r}')
check("job_proxy_termine", j.get("status") == "done",
      f'status={j.get("status")!r} error={str(j.get("error"))[:120]!r}')
check("job_proxy_sans_final_video_path", not j.get("final_video_path"),
      repr(j.get("final_video_path")))
check("job_proxy_sans_video_path", not j.get("video_path"),
      repr(j.get("video_path")))
# ... et la conclusion, ecrite comme le selecteur d'assets l'ecrit. LA
# PREMIERE MOITIE N'EST PAS DECORATIVE : `not (status == "done" and …)` est
# un ET, donc VRAI des que le statut n'est pas « done » — verte sur le
# job-temoin, verte sur un job en echec, verte sans avoir rien mesure
# (MESURE le 05/09/2026, banc relance sans ffmpeg : verte). Le filtre ne dit
# quelque chose QUE d'un job termine ; on exige donc qu'il le soit.
check("job_proxy_hors_du_filtre_du_selecteur_d_assets",
      j.get("status") == "done"
      and not (j.get("video_path") or j.get("final_video_path")),
      str(j))
# LE BUDGET DE LA FENETRE, l'autre moitie du verrou 1 — et celle que le
# commentaire du service promettait a tort. Un job de proxy est invisible du
# FILTRE, mais il OCCUPAIT une place dans les 50 lignes de `GET /api/jobs`,
# que le selecteur d'assets du Montage lit AVANT de filtrer puis de couper a
# 12 : cinquante proxys et la liste « Rendus video » est vide, base pleine de
# rendus. La fenetre est donc filtree DANS LA REQUETE (`Pipeline.list_jobs`),
# avant le `limit` — meme lecon que P8-bis.
_ID_RENDU = "beefbeef-0000-0000-0000-000000000001"
_ID_NUL = "beefbeef-0000-0000-0000-000000000002"


def _pose(jid, prov):
    async def go():
        async with async_session_factory() as sess:
            sess.add(JobRecord(id=jid, status="done", progress=100,
                               title="rendu temoin " + str(prov),
                               provider=prov,
                               image_filename="temoin_" + jid[:8],
                               final_video_path=V1))
            await sess.commit()
    return asyncio.run(go())


# LE COUT, MESURE AVANT DE POSER LE MOINDRE VRAI RENDU : a cet instant le
# SEUL job `done` de la base est le proxy ci-dessus. `GET /api/cost/usage`
# doit donc rendre ZERO. Sans l'exclusion, `_job_to_cost` retombe sur sa
# branche « campaign » par defaut (le proxy ne porte ni `duration_s` ni
# `video_model`) et facture `duration_s or 10` secondes de Seedance plus une
# image FLUX — MESURE aux tarifs par defaut : 0,403 USD par job, imputes a
# `fal`, soit 4,84 USD pour une timeline de douze clips. Un transcodage
# ffmpeg LOCAL et GRATUIT presente comme une depense. La ligne compare a 0.0
# et non a un tarif : elle ne bougera pas le jour ou les prix bougeront.
# DEPUIS LA TACHE 8b, CE QUE MESURE CETTE LIGNE A CHANGE et il faut le dire :
# `_job_to_cost` facture par LISTE BLANCHE, `montage_proxy` y figure, donc
# sans l'exclusion le proxy ne couterait plus 0,403 USD mais 0,00 — sous une
# ligne `local` qui, elle, REMPLIT `by_provider`. C'est la seconde moitie de
# l'assertion (« et une carte VIDE ») qui tient desormais ce cas. REJOUE le
# 05/09/2026 : N-P20 rend toujours ce banc 66/1, cette ligne rouge SEULE, sur
# {'total_usd': 0.0, 'by_provider': {'local': 0.0}}.
_cu = J(api("GET", "/api/cost/usage"))
check("cout_un_proxy_ne_coute_rien",
      j.get("status") == "done"
      and _cu.get("total_usd") == 0.0
      and not (_cu.get("by_provider") or {}),
      f"{_cu} (le proxy est bien termine : {j.get('status')!r})")
GARDE(lambda: _pose(_ID_RENDU, "seedance"), "pose du rendu temoin")
GARDE(lambda: _pose(_ID_NUL, None), "pose du rendu a provider NUL")
_lj = J(api("GET", "/api/jobs"))
# la cle est `job_id`, pas `id` — c'est le vocabulaire de `_job_to_dict`,
# celui que le selecteur d'assets du bundle lit lui aussi.
_ids_jobs = [x.get("job_id") for x in (_lj.get("_liste") or [])
             if isinstance(x, dict)]
# `_ID_RENDU in …` interdit la version vacante : une fenetre VIDE rendrait
# « le proxy n'y est pas » vrai sans rien mesurer.
# `isinstance(_jid, str)` : sans job de proxy, « il n'est pas dans la
# fenetre » serait vrai sans rien mesurer — meme regle que ci-dessus.
check("job_proxy_hors_de_la_fenetre_de_api_jobs",
      isinstance(_jid, str) and bool(_jid)
      and _ID_RENDU in _ids_jobs and _jid not in _ids_jobs,
      f"{len(_ids_jobs)} job(s) : {_ids_jobs}")
# ... et le `coalesce` de cette exclusion, qui n'est pas un detail : en SQL
# `NULL != 'montage_proxy'` vaut NULL et la ligne serait ECARTEE. MESURE sur
# la base reelle : 13 jobs `done` portent `provider IS NULL` — un `!=` nu les
# perdrait tous, SANS ERREUR ET SANS TRACE.
check("api_jobs_garde_les_jobs_a_provider_nul", _ID_NUL in _ids_jobs,
      f"{_ID_NUL} absent de {_ids_jobs}")
# Le NOM du provider est un LITTERAL ici, et il doit l'etre : c'est la valeur
# que les deux autres bancs posent dans leurs fixtures de regression. Si la
# constante changeait sans qu'ils changent, ils deviendraient verts a vide.
check("job_proxy_le_litteral_du_provider_est_celui_du_service",
      M._PROXY_PROVIDER == "montage_proxy", repr(M._PROXY_PROVIDER))


print("\n[6] ou vit le cache — hors de tout dossier que le depot enumere.")
_c = pathlib.Path(str(CH(lambda: MM.proxy_path(V1)), ))
check("cache_dans_son_propre_dossier", _c.parent.name == "montage_cache",
      str(_c.parent))
# MEME PIEGE QUE [1], TROUVE EN APPLIQUANT LA MEME REGLE : cette ligne-ci et
# la suivante sont des NEGATIONS portant sur `_c`, qui peut etre un temoin.
# MESURE (banc relance sans ffmpeg) : toutes deux VERTES alors que
# `proxy_path` n'avait jamais rendu de chemin. On exige donc d'abord que `_c`
# SOIT un chemin de cache — c'est exactement ce que mesure la ligne
# ci-dessus, et elle est reprise ici plutot que supposee.
_c_ok = _c.parent.name == "montage_cache"
check("cache_hors_d_outputs_videos",
      _c_ok and _c.parent != settings.outputs_path / "videos", str(_c.parent))
# La seule facon dont le depot atteint un fichier d'`outputs/` par une chaine
# est `outputs_path / <nom>` (routes.py l. 257 et 274) — a la RACINE. Un
# fichier de cache n'y est donc pas joignable, et cette ligne le mesure au
# lieu de le promettre.
check("cache_introuvable_par_nom_a_la_racine_d_outputs",
      _c_ok and not (settings.outputs_path / _c.name).exists(), str(_c.name))


print("\n[7] P11 — GET /duration : la duree d'une source, pour qu'un clip "
      "entre a SA longueur.")
# POURQUOI CETTE ROUTE EXISTE, MESURE PLUTOT QUE SUPPOSE : sur un instantane
# COHERENT de la base de l'utilisateur (`sqlite3 … .backup()`, qui fusionne le
# WAL : 120 jobs contre 106 pour une copie d'octets du seul `.db`),
# `duration_s` est NULL pour DEUX de ses trois videos et pour toute la famille
# `template`. Lever le plafond du bundle ne leur rendait donc RIEN : il fallait
# aller mesurer. Le champ `duration_real_s` ne comble pas ce trou — il n'est
# calcule que par `GET /jobs/{id}`, un job a la fois, jamais par la LISTE que
# le selecteur d'assets charge.
r = api("GET", "/api/montage/duration?src=" + Q({"file_path": V1}))
d7 = J(r)
check("route_duration_200_sur_une_video",
      r.status_code == 200 and abs(d7.get("dur", -1) - 4.0) < 0.1
      and d7.get("name") == "plan.mp4",
      f"{r.status_code} {d7}")
# LA MESURE EST CELLE DU RENDU, PAS UNE SECONDE. La route rend EXACTEMENT ce
# que `_probe_duration` rend — la fonction que la construction de timeline et
# le rendu appellent deja, et dont `montage_media._dur` n'est qu'une vue.
_direct = round(float(M._probe_duration(pathlib.Path(V1))), 3)
check("route_duration_rend_la_meme_sonde_que_le_rendu",
      _direct > 0 and d7.get("dur") == _direct,
      f'route={d7.get("dur")} sonde={_direct}')
# LA LIGNE DISCRIMINANTE DE `video=False` : `strip` et `proxy` REFUSENT un
# son (415), celle-ci l'accepte — un clip audio doit lui aussi entrer a sa
# longueur. Sans ce choix, la moitie audio de la tache serait morte.
r = api("GET", "/api/montage/duration?src=" + Q({"file_path": MUS}))
d7b = J(r)
check("route_duration_accepte_un_son_la_ou_strip_et_proxy_refusent",
      r.status_code == 200 and abs(d7b.get("dur", -1) - 6.0) < 0.1,
      f"{r.status_code} {d7b}")
# LE PIEGE DE P7 NE MORD PAS ICI, et c'est mesure : ffprobe rend « video » sur
# un PNG quand on lui demande `codec_type`, mais cette route lit
# `format=duration`, ou le meme PNG rend « N/A » — donc 0.0. Une image repond
# « je ne sais pas », ce qui est VRAI, au lieu d'une duree inventee. Le nom
# servi est le conjoint : un 404 ou un 415 ne peut pas verdir cette ligne.
r = api("GET", "/api/montage/duration?src=" + Q({"file_path": PNG}))
d7c = J(r)
check("route_duration_une_image_repond_zero_et_non_une_duree_inventee",
      r.status_code == 200 and d7c.get("dur") == 0
      and d7c.get("name") == "carton.png",
      f"{r.status_code} {d7c}")
# UNE SOURCE RESOLUE MAIS NON MESURABLE (un maillage 3D) rend 200 et « 0 » :
# elle EXISTE, c'est sa duree qu'on ignore. L'ecran pose alors le clip sur son
# repli — en le disant (js_cliplen_le_repli_video_est_DIT).
r = api("GET", "/api/montage/duration?src=" + Q({"file_path": GLB}))
d7d = J(r)
check("route_duration_un_maillage_repond_zero_sans_echouer",
      r.status_code == 200 and d7d.get("dur") == 0
      and d7d.get("name") == "model.glb",
      f"{r.status_code} {d7d}")
r = api("GET", "/api/montage/duration?src=" + Q({"job_id": "inexistant"}))
check("route_duration_404_source_inconnue", r.status_code == 404,
      f"{r.status_code} {r.text[:160]}")
r = api("GET", "/api/montage/duration?src=pas-du-json")
check("route_duration_404_src_illisible", r.status_code == 404,
      f"{r.status_code} {r.text[:160]}")
r = api("GET", "/api/montage/duration")
check("route_duration_404_sans_src", r.status_code == 404,
      f"{r.status_code} {r.text[:160]}")
# LA BOUCLE LOCALE, comme les quatre autres : la garde vient de
# `_media_source`, jamais d'une seconde liste d'hotes.
r = api("GET", "/api/montage/duration?src=" + Q({"file_path": V1}),
        client=("10.0.0.5", 4242))
check("route_duration_403_hors_boucle_locale", r.status_code == 403,
      f"{r.status_code} {r.text[:120]}")


# La ligne qui dit que le banc a ROUGI plutot que MEURE : aucun des appels
# gardes n'a pose de temoin. Une mutation qui fait lever l'unite sous test
# fait rougir CETTE ligne EN PLUS de celles qu'elle casse — et le banc va
# jusqu'a imprimer son compte.
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
