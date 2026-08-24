# -*- coding: utf-8 -*-
"""Card Forge — P10 « Import » (id de module `capture`). Les seuils, mesurés.

CE QUE CE FICHIER TIENT : l'ADMISSION d'une image de carte, le SERVICE des
fichiers du dossier `capture/` (T1), et L'ANALYSE LOCALE — bordure, zones,
fond, palette — mesurée sur des CARTES DE SYNTHÈSE À VÉRITÉ CONNUE (T2,
spec §9.1). Le test POSE une bordure de x mm, trois cartouches, un fond ; il
exige que l'analyse les retrouve à une tolérance CHIFFRÉE ET ÉCRITE DANS
L'ASSERTION — une tolérance qui ne se lit nulle part est une tolérance qu'on
élargit en silence le jour où le test rougit.

Ce qui est verrouillé, seuil par seuil :

  1. L'ADMISSION EST CELLE DE `texture.py:post_paper`, à la lettre : corps vide
     -> 400 ; corps > 64 Mo -> 400 ; dimensions lues dans L'EN-TÊTE avant tout
     décodage -> 413 au-delà de 32 Mpx ; `load()` gardé ; RGB ; réduction
     LANCZOS au-delà de 4096 px ; écriture atomique (tmp + replace).
     Le contrôle AVANT décodage est épinglé SUR LA SOURCE : après `img.load()`
     le demi-gigaoctet est déjà alloué, et aucun test dynamique ne distingue
     les deux ordres.
  2. `?side` est une LISTE BLANCHE À DEUX ENTRÉES, refusée en français et
     nommée. Pas un 422 FastAPI en anglais : le paramètre se prend en `str` et
     se valide à la main, sinon l'utilisateur lit « value is not a valid
     enumeration member » pour une faute de frappe.
  3. Le GET du dossier sert par LISTE BLANCHE DE NOMS FINAUX. Ni traversée, ni
     fichier temporaire : `source_recto.png.tmp` existe pendant la fenêtre
     d'écriture, il ne doit être servi à personne — un nom de fichier est un
     identifiant, jamais un chemin.
  4. RÉ-IMPORT = REMPLACEMENT. Une capture est un point de départ, pas une
     pile : le second envoi écrase le premier, et les octets servis sont ceux
     du second.
  5. JAMAIS 500 (spec §8) : corps illisible, JSON à la place d'un PNG, deck
     inconnu, nom inconnu, image pathologique — chacun a son refus nommé ou
     son relevé DÉGRADÉ AVOUÉ.
  6. L'ANALYSE COURT SUR LE RECTO STOCKÉ, GRATUITEMENT. Pas de corps, pas de
     réseau, pas de fournisseur : la source est balayée pour qu'aucun appel
     payant ne s'y glisse à T3. Elle est REJOUABLE, et déposer un verso ne
     l'efface pas (D3 amendé).
  7. CHAQUE CONFIANCE A UN CAS CONNU OÙ ELLE S'EFFONDRE, et il est joué :
     bordure irrégulière -> régularité en berne ; recto flou -> netteté en
     berne ; fond dégradé -> refus motivé portant sa mesure. Un chiffre de
     confiance qui ne peut pas être bas est un chiffre qui ment (clôture T1).
  8. LE DÉTOURAGE IA EST OPT-IN, ET IL NE DÉPENSE RIEN ICI (T3, spec
     §7.1.3, plan D5). Disponibilité honnête AVANT le clic, prix LU dans
     `pricing.py` (jamais recopié — le contrôle déplace la table et exige
     que la réponse suive) et SANS TARIF TABULÉ LA VOIE PAYANTE N'EST PAS
     OFFERTE, 503 littéral français quand aucune voie n'existe (§8, et pas
     le 400 de `routes.py`), erreur de fournisseur PRÉFIXÉE et sans chemin
     absolu, réponse du fournisseur PLAFONNÉE en octets et sa destination
     contrôlée, couche refusée si elle garde tout OU rien, DEUX CLICS NE
     PAIENT PAS DEUX FOIS (coalescence par jeu). Les portes du dehors —
     `fal_client` (ses seize noms), `FalSeedanceClient.upload_image`,
     `urlopen` — sont refermées sur un COMPTEUR D'APPELS RÉELS asserté à
     ZÉRO dans chaque chemin.
     ET LA VRAIE CLÉ N'ENTRE PAS DANS CE PROCESSUS : `os.environ.setdefault`
     ne tient pas contre le `_load_dotenv(override=True)` de `app/config.py`
     (mesuré : la clé réelle, 69 signes, vivait ici) — l'objet `settings` est
     forcé après l'import, une fixture le refait à chaque test, et un
     contrôle l'épingle.
     LA VÉRITÉ SUR `rembg`, mesurée le 24/08 : il n'est installé NI dans le
     python de développement NI dans le runtime embarqué, et il n'est pas
     dans `requirements.txt`. La voie locale ne s'exécute donc jamais en
     production aujourd'hui ; elle est jouée ici avec un faux module injecté
     dans `sys.modules`, faute de quoi la moitié du basculement serait
     écrite et jamais éprouvée.
 11. UNE COPIE SE PÉRIME, ET LE MANIFESTE LA DATE (ronde T5, B1). Chaque
     ligne porte le nom de sa source, son empreinte AU MOMENT de la
     publication et ses pixels ; P9 confronte les trois au disque avant de
     construire, et refuse NOMMÉ (« republie ») plutôt que de livrer une
     carte périmée. Le format et la toile sont datés de la même façon : la
     face est rendue à la toile d'UN format, un autre format la rend fausse.
     Une source EFFACÉE, elle, ne périme rien — c'est un aveu au bordereau,
     pas un refus.

 10. LE MANIFESTE DES COUCHES IMPORTÉES (T5, plan D7 amendé, spec §7.1.6).
     Il est écrit par une ROUTE et pas au fil de l'eau, et le test dit
     pourquoi : il DÉPEND du format du jeu (toile, millimètres, densité), donc
     il se REJOUE — un manifeste écrit en douce à l'analyse serait périmé au
     premier changement de format. Il ne liste QUE ce qui existe (la face
     entière, et le sujet détouré s'il a été produit) : jamais un `cadre` ni
     un `fond-matiere` qu'aucun fichier ne porte. Sa preuve n'est PAS celle
     des peintres — il n'y a pas eu d'empilement : c'est l'empreinte de chaque
     fichier (que P9 recalcule avant de construire) et la couverture mesurée
     du sujet. Le test de bout §7.1.6 (« une carte importée part en 3D sans
     être reconstruite ») roule ici, de l'import au GLB SERVI, avec la voie
     locale de détourage jouée par le faux module — ZÉRO dépense, prouvée par
     la sentinelle comme partout ailleurs dans ce fichier.

  9. LES ADOPTIONS VIVENT CHEZ L'ADOPTANT (plan D6), et leur contrat se
     garde ICI — c'est le schéma de P10 qu'elles consomment. P1 (mod-face)
     et P3 (mod-type) sont donc lus depuis ce fichier : `test_cards_face.py`
     n'appartient pas à cette tâche, et la moitié qui est vraiment de P3 (ce
     que le SERVEUR fait des slots nés) vit, elle, dans
     `test_cards_type.py`.

────────────────────────────────────────────────────────────────────────────
LES DEUX RONDES DE MUTATION. Le principe ne bouge pas : on REMET le défaut,
on joue le contrôle qui doit le voir, on restaure. Un contrôle qui reste vert
sur le défaut restauré ne garde rien.

Ronde 1 (livraison) — 5 gardes cassées, 5 vues : `_side_or_400` sans son test
d'appartenance ; `FILE_RE` privée de son ancre finale ; écriture directe au
lieu de tmp + replace ; plafond de trame élargi ; `capture` retiré de
`MODULE_IDS` (4 contrôles d'un coup).

Ronde 2 (corrections) — 19 défauts remis, 18 vus :
  · brouillon PARTAGÉ + replace nu (le 500 en concurrence) ......... ROUGE
  · brouillon partagé seul ......................................... ROUGE
  · `except DecompressionBombError` retiré (413 -> 400) ............ ROUGE
  · `$` + `.match` remis ENSEMBLE (le $-newline) ................... ROUGE
  · service remis à la racine (`GET /{nom}`) ....................... ROUGE
  · mébipixels réétiquetés « millions » ............................ ROUGE
  · LANCZOS -> NEAREST (le témoin de la ronde 1, FERMÉ) ............ ROUGE
  · horodatage en secondes ......................................... ROUGE
  · `HTTPException` à message anglais ajoutée ...................... ROUGE
  · tout 404 traduit en « backend absent » (JS) .................... ROUGE
  · `effacements()` : garde neutralisée, puis INVERSÉE (JS) ........ ROUGE
  · `accept="image/*"` remis (JS) .................................. ROUGE
  · `img.onerror` renommé d'une lettre (JS) ........................ ROUGE
  · plafond réécrit en toutes lettres dans une phrase (JS) ......... ROUGE
  · `capture` retiré du lint ; `<script>` retiré d'index.html ...... ROUGE
  · le test du meta.json abîmé qui ne nettoie plus son épave ....... ROUGE

Ronde 6 (T5, corrections de ronde) — 8 défauts remis, 8 vus :
  · le manifeste ne date plus ses copies (format/toile/source) ...... ROUGE
  · l'index de carte redevient sans borne ........................... ROUGE
  · les orphelins de la publication précédente restent .............. ROUGE
  · le manifeste s'écrit sans brouillon sous la concurrence ......... ROUGE
  · le recto réaffiche sa constante de format en « couverture » ..... ROUGE
  · le chiffre du sujet ne nomme plus son cadre ..................... ROUGE
  (+ les deux gardes de P9 que ce fichier alimente : format confronté,
   empreinte de source confrontée — jouées côté forge3d.)

Ronde 5 (T5, le manifeste importé) — 5 défauts remis, 5 vus :
  · la face importée n'est plus posée dans la toile (recopie brute) . ROUGE
  · la densité devient celle de la bibliothèque (39,3701 tronqué) ... ROUGE
  · le manifeste invente un `cadre` qu'aucun fichier ne porte ....... ROUGE
  · le manifeste écrit sans brouillon (pas d'atomicité) ............. ROUGE
  · le manifeste ne dit plus son côté (le nom seul le porterait) .... ROUGE

Ronde 3 (T2, l'analyse) — 20 défauts remis, 20 vus :
  · seuil de refus du fond mis à zéro .............................. ROUGE
  · `_clamp01` qui rend toujours 1 (la confiance ne bouge plus) .... ROUGE
  · clamp retiré, confiance libre de dépasser 1 .................... ROUGE
  · échelle prise sur la HAUTEUR au lieu de la largeur ............. ROUGE
  · échelle en dur (0,1 mm/px) au lieu du format ................... ROUGE
  · front = la PLUS HAUTE marche au lieu de la PREMIÈRE ............ ROUGE
  · plancher de front abaissé à 1 (tout dégradé devient bordure) ... ROUGE
  · rayon de coin sondé à MI-BANDE (les huit sondes) ............... ROUGE
  · fusion des boîtes désactivée ................................... ROUGE
  · retrait de bordure supprimé (l'anneau redevient une zone) ...... ROUGE
  · plancher d'étendue supprimé (le grain devient du dessin) ....... ROUGE
  · 404 sans recto remplacé par un relevé vide ..................... ROUGE
  · le prix recopié dans la phrase d'option IA ..................... ROUGE
  · les pixels retraversent la frontière (`border.px` revient) ..... ROUGE
  · une clé de mesure disparaît du schéma de l'écran (JS) .......... ROUGE
  · `effacements` oublie une clé de mesure (JS) .................... ROUGE
  · `estNombre` relâché : `Number(null)` redevient zéro (JS) ....... ROUGE
  · `analyser()` relit la réponse à la main (JS) ................... ROUGE
  · le verrou BUSY saute sur `analyser()` (JS) ..................... ROUGE
  · les boîtes placées au jugé, sans l'échelle (JS) ................ ROUGE

Ronde 4 (T2, corrections de revue) — 19 défauts remis, 19 vus :
  · la bande exclue n'est plus nommée dans les notes .............. ROUGE
  · plus aucune boîte n'est marquée `tronquee` .................... ROUGE
  · TOUTES les boîtes sont marquées `tronquee` (le drapeau qui
    ne discrimine plus) ............................................ ROUGE
  · la bande n'est plus publiée en mm ............................. ROUGE
  · le relevé n'initialise plus `zones_bande_mm` (la clé manque
    quand une détection LÈVE) ...................................... ROUGE
  · `epaisseurs_mm` redevient une liste triée par taille .......... ROUGE
  · la note « profil texturé » disparaît .......................... ROUGE
  · `_front` ne distingue plus texture et aplat ................... ROUGE
  · le rayon n'est plus corrigé du biais de rangée ................ ROUGE
  · l'option IA proposée même sans sujet à détourer ............... ROUGE
  · le seuil de silence du ratio revient à zéro ................... ROUGE
  · le 503 de dépendance absente redevient un 500 ................. ROUGE
  · les lignes du fond reprennent l'ordre fixe (JS) ............... ROUGE
  · les bornes de couverture ne sont plus écrites (JS) ............ ROUGE
  · `divergence` ne compare plus rien (JS) ........................ ROUGE
  · `core:geom` MIS EN COMMENTAIRE (JS) ........................... ROUGE
  · `peutIncruster` oublie l'échelle (JS) ......................... ROUGE
  · `panne()` ne voit plus le rejet réseau (JS) ................... ROUGE
  · `effacements` oublie `zones_bande_mm` (JS) .................... ROUGE

Ronde 5 (T3, le détourage IA et les adoptions) — 30 défauts remis, 30 vus :
  · le basculement INVERSÉ : fal avant local ..................... ROUGE
  · le 503 redevenu le 400 de `routes.py` ........................ ROUGE
  · « aucune voie » transformé en ERREUR au lieu d'une réponse ... ROUGE
  · le prix RECOPIÉ au lieu d'être lu dans `pricing` ............. ROUGE
  · le préfixe de fournisseur retiré du refus .................... ROUGE
  · `_sans_chemin` neutralisé (la fuite de nom rejouée) .......... ROUGE
  · la couche ENTIÈREMENT transparente acceptée .................. ROUGE
  · un nouveau recto ne tue plus le sujet d'avant ................ ROUGE
  · la liste blanche non étendue (le sujet n'est pas servi) ...... ROUGE
  · le 404 qui nomme le fichier par DÉCOUPE (le « cto ») ......... ROUGE
  · la couche rangée en RGB : l'alpha meurt ...................... ROUGE
  · le brouillon PARTAGÉ (le défaut grave de T1, rejoué) ......... ROUGE
  · L'ESPION CONTOURNÉ : la route appelle un alias figé à
    l'import — la sentinelle compte 1 et le dit .................. ROUGE
  · le dépliage fal privé de la forme `images[]` ................. ROUGE
  · la relève acceptant n'importe quel schéma d'adresse .......... ROUGE
  · un rembg CASSÉ qui fait tomber la route au lieu de se dire ... ROUGE
  · l'écran propose l'option même sans voie (JS) ................. ROUGE
  · l'écran écrit un montant même sans tarif tabulé (JS) ......... ROUGE
  · le verrou BUSY qui saute sur le détourage (JS) ............... ROUGE
  · les options relues à CHAQUE peinture (JS) .................... ROUGE
  · P1 préfère le recto entier au sujet détouré (JS) ............. ROUGE
  · P1 pose l'illustration DEUX fois (deux annulations, JS) ...... ROUGE
  · P1 construit l'URL SANS la liste blanche (JS) ................ ROUGE
  · P3 accepte une boîte SANS taille (JS) ........................ ROUGE
  · P3 tait les boîtes tronquées (JS) ............................ ROUGE
  · P3 fait naître les zones DANS UNE BOUCLE (JS) ................ ROUGE
  · P3 renomme les zones (le serveur les répare en silence, JS) .. ROUGE
  · P3 CONVERTIT les mm au lieu de les reprendre (JS) ............ ROUGE
  · le plafond de blocs n'est plus compté avant (JS) ............. ROUGE
  · les zones REMPLACENT les blocs au lieu de s'y ajouter (JS) ... ROUGE

TROIS DE CES TRENTE ONT OUVERT UN TROU AVANT DE LE FERMER, et ce sont les
trois plus instructifs :
  · « naître dans une boucle » restait VERT côté P3 : un `naitre(` dans un
    `forEach` est toujours UNE occurrence de texte et fait N naissances. Le
    contrôle de `test_cards_type.py` comptait les occurrences ; il refuse
    maintenant toute boucle sur ce chemin.
  · « l'URL sans liste blanche » restait VERT : le contrôle cherchait un
    `…test(…)` dans le corps de `captureURL`, et celui de l'identifiant de
    jeu le satisfaisait. La garde est désormais EXÉCUTÉE dans node, sur six
    noms dont la traversée et le `%0A`.
  · le corps de `_fal_rembg` n'était joué NULLE PART — espionné en entier
    partout ailleurs. C'est le seul code payant du fichier : un bug de
    dépliage y coûte un appel PAYÉ dont le résultat n'est pas lu. Il a
    maintenant son contrôle, `fal_client` ouvert pour lui seul (les trois
    autres portes restent fermées sur le compteur).

Ronde 6 (T3, corrections de revue) — 22 défauts remis, 22 vus :
  · LA VRAIE CLÉ FAL remise dans le processus de test .............. ROUGE
  · le plafond de couverture retiré (une couche intacte passe) ..... ROUGE
  · ... et mis SI BAS qu'un vrai détourage est refusé .............. ROUGE
  · le repeint qui attend à nouveau le réseau (JS) ................. ROUGE
  · la coalescence supprimée : chacun paie ......................... ROUGE
  · ... et la coalescence qui ne distingue plus les jeux ........... ROUGE
  · la lecture du résultat redevenue sans borne .................... ROUGE
  · la destination du résultat plus jugée (127.0.0.1 passe) ........ ROUGE
  · ... et jugée dans le MAUVAIS ORDRE (le mot juste se perd) ...... ROUGE
  · le sujet qui n'hérite plus de la réduction d'admission ......... ROUGE
  · le plafond de trame x10000 dans `_store_layer` ................. ROUGE
  · le 409 d'écriture devenu 418 .................................. ROUGE
  · `imageBlob` peignant un fond blanc avant le sujet (JS) ......... ROUGE
  · P1 réimportant en silence au lieu de reposer (JS) .............. ROUGE
  · P3 taisant les zones déjà posées (JS) .......................... ROUGE
  · le prix qui n'est plus relu avant de payer (JS) ................ ROUGE
  · la voie payante offerte sans tarif tabulé (route) .............. ROUGE
  · ... et la même, côté écran (JS) ................................ ROUGE
  · la copie d'écran de la liste blanche qui DÉRIVE (JS) ........... ROUGE
  · le nettoyage de chemin reperdant UNC et le tilde ............... ROUGE
  · le refus « sans recto » qui part quand même chez fal ........... ROUGE
  · l'écran fabriquant l'URL sans filtrer le nom (JS) .............. ROUGE

DEUX DE CES VINGT-DEUX ONT D'ABORD SURVÉCU, et les deux enseignent :
  · retirer la branche « boucle locale » de `_destination_sure` ne changeait
    RIEN au verdict — `ipaddress` range 127.0.0.0/8, ::1, 169.254/16 et
    0.0.0.0/8 DANS les réseaux privés, donc le refus tombait quand même,
    sous un autre nom. Ce n'était donc pas un trou de garde mais un trou de
    DIAGNOSTIC : le contrôle exige maintenant le MOT JUSTE, cas par cas, et
    l'ordre des branches est devenu porteur.
  · la mutation prévue pour `s.zero()` portait sur le TEST et non sur le
    code : retirer une assertion ne peut pas faire rougir la suite. Elle a
    été remplacée par un vrai défaut — le refus « sans recto » qui part
    quand même chez le fournisseur — que la sentinelle voit.

TROIS TÉMOINS FERMÉS PAR CETTE RONDE (la revue les avait mesurés survivants) :
`IMG_MAX_PIXELS` dans `_store_layer`, le code 409 de l'échec d'écriture, et
`imageBlob` — la fonction dont tout le métier est « garder l'alpha qu'on
vient de payer », et qui n'était jouée nulle part.

LES TÉMOINS SURVIVANTS DE T3, AVOUÉS (deux, plus une limite dite) :
  · `FAL_TIMEOUT_S` (120 s) n'est gardé par AUCUN contrôle — le ramener à
    1 s survivrait à toute la suite. Le mesurer demanderait de tenir une
    socket ouverte plus longtemps que le délai, c'est-à-dire un test qui
    dure ce qu'il mesure. Un chiffre de confort, dit plutôt que gardé.
  · le témoin de T1 sur `_replace_avec_patience` vaut ici tel quel : retirer
    la reprise patiente SEULE, en gardant le brouillon unique, n'est vu
    qu'environ une fois sur deux. Le défaut GRAVE — le brouillon partagé —
    est vu, lui, à tous les coups (mutation 12 de la ronde 5).
  · LIMITE DITE, ET PAS UN TÉMOIN : `_destination_sure` ne RÉSOUT aucun nom
    (une résolution DNS est un appel réseau, dans une fonction dont l'objet
    est de décider s'il faut en faire un). Un nom public qui pointerait vers
    127.0.0.1 passerait donc. Ce qui est attrapé est le cas réel : une IP
    littérale de la machine ou du réseau local dans une réponse.

DEUX DES DIX-NEUF DE LA RONDE 4 SONT DES TROUS QUE LA RONDE A OUVERTS, PAS
FERMÉS, et c'est ce qui les rend intéressants :
  · `core:geom` entouré de `/* */` laissait le contrôle VERT — il cherchait
    du code par son TEXTE, et un texte en commentaire est encore du texte.
    Les recherches de code passent désormais par `_code_js`, qui dépouille.
  · retirer `zones_bande_mm` de l'initialisation du relevé ne se voyait sur
    aucun chemin heureux : la clé est réécrite juste après. Elle ne manque
    que si la détection LÈVE — un chemin gardé que rien n'exécutait. Il l'est
    maintenant (`test_une_DETECTION_QUI_LEVE…`), en faisant mourir `_grille`.

ET LES TÉMOINS QUI SURVIVENT À LA RONDE 3, AVOUÉS ET MESURÉS. Six réglages
peuvent bouger sans qu'aucun contrôle ne rougisse, et ce n'est pas un oubli
(le septième, `BORD_FRONT_RATIO`, a été RETOURNÉ par la ronde — voir plus
bas) :

  · `ZONE_SOUS` (8 pixels de travail par bloc) de 4 à 24 — les trois boîtes
    restent trouvées et appariées dans tout cet intervalle. C'est le témoin
    de classe LANCZOS de la ronde 1 : un réglage de COÛT et de finesse, dont
    la dégradation est graduelle et n'a pas de seuil honnête à épingler.
  · `ZONE_MIN_BLOCS` (2) et `ZONE_MAX_BOITES` (12) — des réglages de LISIBILITÉ
    du relevé. Les fabriquer en test demanderait une carte à quarante taches
    d'un bloc, qui ne ressemble à aucun import réel.
  · `BORD_MIN_BORDS` (2) abaissé à 1 — le facteur n/4 de la confiance plafonne
    déjà une « bordure » d'un seul bord à 0,25, donc l'écran la donne pour ce
    qu'elle vaut. Le garde-fou est une ceinture, pas la bretelle.
  · `BORD_MARGE` (20 % de chaque extrémité) ramenée à 2 % — mesuré sur des
    coins de 40, 90 et 140 px : l'épaisseur, la confiance et le rayon sont
    IDENTIQUES. La marge protège d'un cas plus dur que tout ce qu'on sait
    fabriquer sans deviner ; elle reste, avouée comme non gardée.
  · `asyncio.to_thread` retiré de la route — l'analyse bloquerait la boucle
    d'événements. Aucun test en-processus ne peut le voir : le transport ASGI
    du banc joue tout dans la même boucle de toute façon.

LE TÉMOIN QUI N'EN ÉTAIT PAS UN — `BORD_FRONT_RATIO`, retourné par la ronde 4.
L'aveu de la ronde 3 disait que ce rapport ne peut pas mordre sur une carte
(un fondu monotone ne cumule que ~5 de marche médiane) et qu'il ne mord que
sur une image minuscule. Re-mesuré, C'EST L'INVERSE : sur un profil OSCILLANT
— des rayures de 2 px — la marche médiane vaut 455 et le plancher passe de 40
à 1824, donc le rapport décide seul ; sur une image de 40 x 56, la marche
médiane vaut ZÉRO et il ne joue aucun rôle. Ce qu'il attrape est une bordure à
filets fins ou un scan tramé, et ce refus-là a maintenant SA note et SON
contrôle (`test_une_bordure_TEXTUREE…`). Leçon : un aveu qui explique pourquoi
un garde-fou ne peut pas servir mérite la même mesure qu'une affirmation de
succès — celui-ci était une hypothèse écrite au présent.

ET LE TÉMOIN DE LA RONDE 2, AVOUÉ — c'en est un NOUVEAU : celui de la ronde 1
(LANCZOS) est fermé par `test_la_reduction_FILTRE_vraiment…`. Retirer
`_replace_avec_patience` SEUL, en gardant le brouillon unique, n'est vu
qu'environ une fois sur deux : sans la reprise, la course rend
{200: 33, 409: 7} sur ce poste, mais parfois 37 ou 38 succès — au-dessus du
plancher de 90 % du contrôle. Le seuil qui l'attraperait à coup sûr (exiger
40/40) serait FAUX DANS L'AUTRE SENS : une machine chargée rendrait un 409
légitime et le contrôle rougirait sans faute. Entre un trou connu et une
intermittence rouge, on garde le trou et on l'écrit. Le défaut GRAVE — le
brouillon partagé, celui qui rendait des 500 et ne laissait AUCUN fichier —
est vu, lui, à tous les coups.

Run : .\\scripts\\run-tests.ps1 -Filter cards_capture
"""
import asyncio
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                   # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

from app.config import settings as _settings                     # noqa: E402
from app.services.cards import capture as CP                     # noqa: E402
from app.services.cards import contract as CT                    # noqa: E402
from app.services.cards import core as CC                        # noqa: E402

# ── LA VRAIE CLÉ FAL N'ENTRE PAS DANS CE PROCESSUS ──────────────────────────
#
# `os.environ.setdefault("FAL_KEY", …)` vingt lignes plus haut NE SUFFIT PAS,
# et c'est mesuré : `app/config.py` fait `_load_dotenv(ENV_FILE, override=True)`
# À L'IMPORT — délibérément, pour qu'un lanceur qui exporte une variable vide
# ne masque pas les clés enregistrées de l'utilisateur. Conséquence pour un
# banc : le `.env` du dossier de données GAGNE, et `settings.FAL_KEY` valait la
# VRAIE clé (69 signes, mesuré le 24/08). Le `setdefault`, lui, n'avait même
# pas d'effet — la variable n'était pas absente, elle était réécrite après.
#
# CE QUE ÇA CHANGE : la voie par défaut du basculement devenait la voie
# PAYANTE, et la seule chose entre ce banc et une facture était UNE couche de
# monkeypatch là où l'en-tête en revendiquait deux. Rien n'a fui (chaque test
# pose son espion, et la sentinelle compte), mais un banc dont la sûreté tient
# à ce que personne n'oublie une ligne n'est pas un banc sûr — et T5 écrira
# contre celui-ci.
#
# ON FORCE DONC L'OBJET, PAS L'ENVIRONNEMENT, et APRÈS l'import de config :
# c'est le seul point où l'on gagne contre un `override=True` déjà joué.
_settings.FAL_KEY = "test-key"

REPO = pathlib.Path(__file__).resolve().parents[2]
JS = REPO / "frontend" / "cardforge" / "js" / "mod-capture.js"
CSS = REPO / "frontend" / "cardforge" / "css" / "mod-capture.css"


# ═══════════════════════ outillage ══════════════════════════════════════════

@pytest.fixture(autouse=True)
def _clef_de_banc(monkeypatch):
    """LA SECONDE COUCHE, celle que l'en-tête revendiquait sans l'avoir.

    Le forçage au niveau module tient au chargement ; celui-ci tient à CHAQUE
    test, y compris ceux qui rendent la main après avoir posé leur propre
    valeur. Un test qui remettrait une vraie clé — par mégarde, par un import
    tardif, par un `settings.reload()` d'une autre pièce — repartirait de la
    valeur de banc au test suivant."""
    monkeypatch.setattr(_settings, "FAL_KEY", "test-key", raising=False)
    yield


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=600.0) as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _deck() -> str:
    return CC.create_deck("import")["id"]


def _carte(w: int = 630, h: int = 880, teinte: int = 40) -> bytes:
    """Une carte plausible : bordure claire, intérieur sombre, un aplat.
    Une image PLATE ne dirait rien des mesures de T2 ; celle-ci porte déjà
    une bordure franche, pour que le fichier d'aujourd'hui serve demain."""
    im = Image.new("RGB", (w, h), (216, 183, 106))
    b = max(2, min(w, h) // 24)
    # DESSINÉ PAR PRIMITIVE, pas pixel par pixel : la boucle Python coûtait
    # 2,7 millions d'itérations pour une carte de scan réaliste, et le test de
    # concurrence en fabrique quarante.
    ImageDraw.Draw(im).rectangle(
        [b, b, w - b - 1, h - b - 1],
        fill=(teinte, teinte - 4 if teinte > 4 else 0, teinte // 2))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _bombe_png(w: int, h: int) -> bytes:
    """Un PNG VALIDE et minuscule qui DÉCLARE `w` x `h`.

    Construit à la main, une ligne à la fois : la charge est faite de zéros,
    donc zlib la réduit à quelques kilo-octets et le tampon de construction ne
    dépasse jamais une ligne. C'est exactement l'asymétrie qu'une bombe de
    pixels exploite — quelques centaines de kilo-octets sur le fil, des
    centaines de mégaoctets chez celui qui décode."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)   # 8 bits, gris
    co = zlib.compressobj(1)
    ligne = b"\x00" * (w + 1)                              # filtre 0 + w octets
    morceaux = [co.compress(ligne) for _ in range(h)]
    morceaux.append(co.flush())
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", b"".join(morceaux)) + chunk(b"IEND", b""))


def _post(did: str, corps: bytes, side: str | None = None):
    q = "" if side is None else f"?side={side}"
    return _api("POST", f"/api/cards/{did}/capture/card{q}",
                content=corps, headers={"Content-Type": "image/png"})


def _get(did: str, nom: str):
    """Le service passe sous /file/ — voir `capture.get_file` : à la racine du
    préfixe, le joker avalait toutes les routes GET des tâches suivantes."""
    return _api("GET", f"/api/cards/{did}/capture/file/{nom}")


# ── les cartes de SYNTHÈSE, et la vérité qu'on y pose (spec §9.1) ───────────
#
# Le poste de mesure de toute cette section : un poker_eu (63 x 88 mm) rendu à
# 630 x 880 px, soit EXACTEMENT 0,1 mm par pixel. Ce chiffre rond n'est pas de
# la coquetterie — il rend la vérité posée lisible en millimètres sans
# arrondi intermédiaire : une bordure de 26 px EST une bordure de 2,6 mm.
SYNTH_W, SYNTH_H = 630, 880
SYNTH_MM_PX = 63.0 / SYNTH_W          # 0,1 mm/px
OR = (216, 183, 106)                  # la bande
NOIR = (20, 18, 12)                   # l'intérieur


def _synth(bord_px: int = 26, boites=(), bord=OR, fond=NOIR,
           w: int = SYNTH_W, h: int = SYNTH_H, rayon: int = 0,
           dehors=(255, 255, 255)):
    """Une carte à VÉRITÉ CONNUE : bande de `bord_px`, intérieur uni, et les
    cartouches qu'on veut, posés au pixel."""
    im = Image.new("RGB", (w, h), dehors)
    d = ImageDraw.Draw(im)
    if rayon:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=rayon, fill=bord)
    else:
        d.rectangle([0, 0, w - 1, h - 1], fill=bord)
    if bord_px:
        d.rectangle([bord_px, bord_px, w - bord_px - 1, h - bord_px - 1],
                    fill=fond)
    for (x, y, bw, bh, col) in boites:
        d.rectangle([x, y, x + bw - 1, y + bh - 1], fill=col)
    return im


def _pngs(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# Trois cartouches POSÉS, aux places d'une vraie carte : un bandeau de titre,
# une boîte de capacité, un badge de camp. Leurs coordonnées en px sont la
# vérité ; leurs millimètres s'en déduisent par SYNTH_MM_PX et rien d'autre.
TROIS_BOITES_PX = ((80, 60, 470, 70), (80, 620, 470, 150), (60, 200, 90, 90))
TROIS_COULEURS = ((230, 210, 150), (200, 190, 170), (240, 230, 120))
TROIS = tuple((x, y, w, h, c) for (x, y, w, h), c
              in zip(TROIS_BOITES_PX, TROIS_COULEURS))


def _analyse(did: str):
    return _api("POST", f"/api/cards/{did}/capture/analyse")


def _pose_et_analyse(im, fmt: str | None = None):
    """Le geste réel, de bout en bout : on dépose, puis on demande la mesure.
    Le relevé est rendu avec le `did` pour que l'appelant range son deck."""
    did = (CC.create_deck("import", {"fmt": fmt})["id"] if fmt else _deck())
    r = _post(did, _pngs(im), "recto")
    assert r.status_code == 200, r.text[:300]
    a = _analyse(did)
    assert a.status_code == 200, (a.status_code, a.text[:400])
    return did, a.json()


def _iou(a, b) -> float:
    """Intersection sur union de deux boîtes [x, y, w, h]."""
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if not inter:
        return 0.0
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def _scan_js(src: str):
    """(littéraux de chaîne, source SANS ses commentaires).

    Un automate de vingt lignes, et il en faut un pour DEUX raisons :

      · les commentaires de ce chantier sont en français, donc pleins
        d'apostrophes, et toute recherche de `'…'` par expression régulière
        prend un commentaire pour une chaîne ;
      · un contrôle qui cherche du CODE par son texte est satisfait par ce
        même code MIS EN COMMENTAIRE. Mesuré : l'écoute de `core:geom`
        neutralisée en l'entourant de `/* */` laissait le contrôle vert. Un
        garde-fou qu'on peut désactiver sans faire rougir un test n'est pas
        gardé — on cherche donc dans le code dépouillé.
    """
    chaines, code, i, n = [], [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j + 1
        elif c in "\"'`":
            j, buf = i + 1, []
            while j < n and src[j] != c:
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1])
                    j += 2
                    continue
                buf.append(src[j])
                j += 1
            chaines.append("".join(buf))
            code.append(src[i:min(j + 1, n)])
            i = j + 1
        else:
            code.append(c)
            i += 1
    return chaines, "".join(code)


def _chaines_js(src: str) -> list:
    return _scan_js(src)[0]


def _code_js(src: str) -> str:
    return _scan_js(src)[1]


def _cles_du_schema() -> set:
    """Les clés du bloc `state:` de mod-capture.js — le SCHÉMA que `patchAs`
    fait respecter. Lues sur le fichier : le JS n'est importable d'aucune
    façon depuis Python, et c'est cette frontière-là qui casse en silence."""
    js = JS.read_text(encoding="utf-8")
    i = js.index("state: {")
    bloc = js[i:js.index("\n    },", i)]
    return set(re.findall(r"^\s{6}([a-z_]+):", bloc, re.M))


def _en_parallele(appels):
    """DE LA VRAIE CONCURRENCE, pas une boucle. `asyncio.gather` sur le même
    transport lance les requêtes ensemble, et l'écriture disque de la route
    part en `asyncio.to_thread` — donc dans de VRAIS threads, exactement là où
    la course se joue. Une boucle séquentielle ne l'aurait jamais reproduite."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=600.0) as c:
            return await asyncio.gather(
                *[c.request(m, p, **kw) for (m, p, kw) in appels])
    return asyncio.run(go())


# ═══════════════════════ la pièce existe ════════════════════════════════════

def test_la_piece_existe_et_respecte_la_regle_1():
    """Règle 1 : 1 JS + 1 CSS + 1 py + 1 test. Le test, c'est ce fichier ;
    les trois autres se vérifient sur le disque, pas sur une intention."""
    assert JS.is_file(), JS
    assert CSS.is_file(), CSS
    assert pathlib.Path(CP.__file__).is_file()
    from fastapi import APIRouter
    assert isinstance(CP.router, APIRouter)


def test_capture_est_dans_les_dix_ids_du_contrat():
    """Un sous-arbre que le contrat ignore est un sous-arbre effacé à chaque
    autosave (F2 : `doc.forge3d`, deux phases durant). P10 ne recommence pas."""
    assert "capture" in CT.MODULE_IDS
    assert CT.MODULE_IDS[-1] == "capture", "P10 est la dixième du rail"
    assert len(CT.MODULE_IDS) == 10


def test_la_route_est_montee_sous_capture():
    from app.main import app
    chemins = list(app.openapi().get("paths", {}))
    assert "/api/cards/{did}/capture/card" in chemins, chemins[-8:]
    assert "/api/cards/{did}/capture/file/{nom}" in chemins, chemins[-8:]
    # AVANT le filet attrape-tout : Starlette apparie dans l'ordre. Sans cela
    # POST /capture/card répondrait « Route inconnue ».
    filet = [p for p in chemins if p.endswith("/{rest:path}")]
    if filet:
        assert chemins.index("/api/cards/{did}/capture/card") \
            < chemins.index(filet[0])


def test_le_service_ne_squatte_pas_les_routes_a_venir():
    """LE JOKER `GET /{nom}` À LA RACINE DU PRÉFIXE ÉTAIT UN PIÈGE DE CLASSE :
    Starlette apparie dans l'ordre, donc il aurait avalé `/ai-options` (T3),
    `/rembg` et `/analyse` — et répondu « Fichier inconnu dans le dossier de
    capture » à qui interroge une route qui n'existe pas encore. Le
    diagnostic aurait coûté une demi-tâche à quelqu'un. Sous `/file/`, une
    route absente redevient une route absente.

    AMENDEMENT T3 : deux des quatre noms de la liste d'origine ont pris
    corps — `ai-options` répond maintenant 200 et `rembg` est un POST. Les
    remplacer par les noms QUI RESTENT à venir (T5 : le manifeste de couches)
    garde la CLASSE de piège, qui est ce que ce contrôle protège ; la liste,
    elle, n'a jamais été le sujet."""
    did = _deck()
    for futur in ("layers", "manifeste", "state"):
        r = _api("GET", f"/api/cards/{did}/capture/{futur}")
        assert r.status_code == 404, (futur, r.status_code)
        detail = (r.json() or {}).get("detail", "")
        assert "dossier de capture" not in detail, \
            f"/{futur} est avalé par le service de fichiers : {detail!r}"
        assert "Route inconnue" in detail, (futur, detail)
    CC.delete_deck(did)


# ═══════════════════════ l'admission ════════════════════════════════════════

def test_admission_aller_retour_recto_et_verso():
    """Le geste complet : on dépose, le serveur RÉPOND ses mesures, et le
    fichier se relit à l'octet par la route de service."""
    did = _deck()
    for side, nom in (("recto", "source_recto.png"),
                      ("verso", "source_verso.png")):
        r = _post(did, _carte(300, 420), side)
        assert r.status_code == 200, (side, r.text[:300])
        d = r.json()
        assert d["side"] == side
        assert (d["w"], d["h"]) == (300, 420), d
        assert d["bytes"] > 0
        # L'HORODATAGE EST EN MILLISECONDES : en secondes, deux imports de la
        # même seconde rendaient la même URL d'aperçu et le navigateur
        # resservait l'ancienne image. 1e12 ms = 2001 ; un horodatage en
        # secondes (1,7e9) tomberait ici.
        assert d["stamp"] > 1_000_000_000_000, d["stamp"]
        g = _get(did, nom)
        assert g.status_code == 200, (nom, g.status_code)
        assert g.headers["content-type"] == "image/png"
        assert len(g.content) == d["bytes"], "les octets servis ne sont pas ceux pesés"
        with Image.open(io.BytesIO(g.content)) as im:
            assert im.size == (300, 420)
    CC.delete_deck(did)


def test_le_recto_est_le_defaut():
    """`?side` absent = recto. Un défaut implicite doit s'écrire quelque part :
    ici, et le verso reste vierge."""
    did = _deck()
    r = _post(did, _carte(120, 168))
    assert r.status_code == 200, r.text
    assert r.json()["side"] == "recto"
    assert _get(did, "source_recto.png").status_code == 200
    assert _get(did, "source_verso.png").status_code == 404
    CC.delete_deck(did)


def test_un_side_inconnu_est_refuse_EN_FRANCAIS_et_nomme():
    """Un `Literal["recto","verso"]` de FastAPI aurait rendu un 422 anglais
    (« value is not a valid enumeration member ») sur une faute de frappe. Le
    paramètre se prend en `str` et se valide ici : 400, en français, avec les
    deux valeurs possibles ÉCRITES dans le message."""
    did = _deck()
    for mauvais in ("front", "RECTO_", "dos", "1", " ", "recto,verso"):
        r = _post(did, _carte(60, 84), mauvais)
        assert r.status_code == 400, (mauvais, r.status_code, r.text[:200])
        detail = r.json()["detail"]
        assert "recto" in detail and "verso" in detail, detail
        assert re.search(r"[éèêàç]", detail), \
            f"le refus n'est pas en français : {detail!r}"
    # aucun fichier n'a été écrit au passage
    d = CT.deck_dir(did) / "capture"
    assert not d.exists() or not list(d.iterdir()), list(d.iterdir())
    CC.delete_deck(did)


def test_un_corps_vide_ou_trop_lourd_est_refuse_avant_tout_decodage():
    """Deux garde-fous DISTINCTS et le premier est le poids : `SRC_MAX_BYTES`
    pèse ce qui arrive sur le fil, et il se lit sur `len(raw)` — pas après une
    tentative d'ouverture."""
    did = _deck()
    r = _post(did, b"", "recto")
    assert r.status_code == 400 and "vide" in r.json()["detail"].lower(), r.text
    assert CP.SRC_MAX_BYTES == 64 * 1024 * 1024
    gros = b"\x89PNG\r\n\x1a\n" + b"\x00" * (CP.SRC_MAX_BYTES + 1)
    r = _post(did, gros, "recto")
    assert r.status_code == 400, r.status_code
    assert "64" in r.json()["detail"], r.json()["detail"]
    CC.delete_deck(did)


def test_une_BOMBE_DE_PIXELS_est_refusee_sur_ses_DIMENSIONS():
    """Le poids du corps ne dit RIEN du coût du décodage : un PNG de zéros de
    quelques centaines de kilo-octets déclare 12000 x 12000, soit 144 Mpx et un
    demi-gigaoctet de tampon — par requête, et la bibliothèque se contente
    d'AVERTIR jusqu'à 179 Mpx avant de décoder quand même."""
    did = _deck()
    bombe = _bombe_png(12000, 12000)
    assert len(bombe) < 1_000_000, len(bombe)
    with Image.open(io.BytesIO(bombe)) as im:
        assert im.size == (12000, 12000)      # l'en-tête suffit, sans décoder
    assert CP.IMG_MAX_PIXELS == 32 * 1024 * 1024
    r = _post(did, bombe, "recto")
    assert r.status_code == 413, (r.status_code, r.text[:200])
    detail = r.json()["detail"]
    assert "12000" in detail and "pixel" in detail.lower(), detail
    # LE CHIFFRE ANNONCÉ EST JUSTE. `// 1048576` écrivait « 137 millions »
    # pour 144 000 000 pixels — un mébipixel sous le nom d'un million, et un
    # nombre que personne ne pouvait retrouver (le commentaire de la source,
    # vingt lignes plus haut, dit 144). Leçon Mo/Mio de P8, même piège.
    assert "144" in detail, detail
    assert "137" not in detail, detail
    # et rien n'a été écrit
    assert not (CT.deck_dir(did) / "capture" / "source_recto.png").exists()
    CC.delete_deck(did)


def test_une_bombe_QUE_PIL_REFUSE_D_OUVRIR_est_refusee_pour_LA_BONNE_RAISON():
    """AU-DELÀ DE ~179 Mpx (2 x `MAX_IMAGE_PIXELS`), la bibliothèque lève
    `DecompressionBombError` AVANT de rendre la taille — donc avant notre
    contrôle. Écrasé par un `except Exception` générique, ce refus ressortait
    en 400 « Corps illisible : une image PNG/JPEG/WebP est attendue » : le
    message envoie chercher un fichier corrompu là où il n'y a qu'une image
    valide et démesurée. Mesuré sur 20000² (400 Mpx) et 60000² (3,6 Gpx).

    LE MONTAGE EST UN EN-TÊTE, ET C'EST EXACT : `Image.open` tranche sur la
    TAILLE DÉCLARÉE seule, sans lire un octet d'IDAT — la preuve est que le
    même montage à 12000² passe l'ouverture (test voisin) et sort en 413 par
    notre contrôle à nous. Fabriquer 3,6 milliards de pixels réels pour dire
    la même chose coûterait des minutes et des gigaoctets."""
    did = _deck()
    for cote in (20000, 60000):
        bombe = _png_entete_saine_corps_pourri(cote, cote)
        r = _post(did, bombe, "recto")
        assert r.status_code == 413, (cote, r.status_code, r.text[:200])
        detail = r.json()["detail"]
        assert "trop grande" in detail, (cote, detail)
        assert "illisible" not in detail, (cote, detail)
        assert "pixel" in detail.lower(), (cote, detail)
    assert not (CT.deck_dir(did) / "capture" / "source_recto.png").exists()
    CC.delete_deck(did)


def _png_entete_saine_corps_pourri(w: int, h: int) -> bytes:
    """UN PNG QUI MENT À DEUX NIVEAUX : son IHDR déclare w x h honnêtement,
    son IDAT ne se décode pas. C'est le discriminateur DYNAMIQUE de l'ordre
    des gardes — si la taille est contrôlée sur l'en-tête, il sort en 413 ;
    si elle l'est après `load()`, le décodage meurt d'abord et il sort en
    400. Aucun autre montage ne sépare les deux."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    pourri = b"\x78\x9c" + b"\xff" * 64          # en-tête zlib, suite invalide
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", pourri) + chunk(b"IEND", b""))


def test_le_controle_de_trame_est_AVANT_le_decodage_ET_CA_SE_MESURE():
    """La preuve était au TEXTE (l'ordre de deux mots dans la source). Elle
    est maintenant au COMPORTEMENT : l'image ci-dessous est indécodable, donc
    un contrôle placé après `load()` répondrait 400 « corps illisible ». Elle
    répond 413 : les dimensions ont été lues et refusées sans qu'un octet de
    trame soit décodé — c'est le seul endroit où ce refus coûte zéro."""
    did = _deck()
    menteur = _png_entete_saine_corps_pourri(12000, 12000)
    assert len(menteur) < 500, "le montage doit rester minuscule"
    from PIL import Image as _I
    with _I.open(io.BytesIO(menteur)) as im:
        assert im.size == (12000, 12000)          # l'en-tête suffit...
        try:
            im.load()
            leve = False
        except Exception:
            leve = True
    assert leve, "le corps devait être indécodable — le montage ne prouve rien"
    r = _post(did, menteur, "recto")
    assert r.status_code == 413, \
        f"413 attendu (en-tête AVANT décodage), reçu {r.status_code} : {r.text[:200]}"
    assert "12000" in r.json()["detail"]
    # ... et le même corps SANS trame démesurée sort bien en 400 : c'est ce
    # qui prouve que le 413 ci-dessus vient de la TAILLE et non du hasard.
    petit = _png_entete_saine_corps_pourri(40, 56)
    r = _post(did, petit, "recto")
    assert r.status_code == 400 and "illisible" in r.json()["detail"], r.text[:200]
    CC.delete_deck(did)


def test_les_HUIT_copies_de_MAX_IMPORT_PX_disent_le_meme_chiffre():
    """La règle 8 interdit à une pièce d'importer le module d'une voisine :
    le plafond d'import est donc RECOPIÉ, et la seule chose qui empêche les
    copies de diverger est ce test. Il en confrontait TROIS sur sept, et son
    commentaire annonçait le contraire — un test qui ment sur sa couverture
    est pire qu'absent. Les huit sont lues SUR LES FICHIERS (les quatre JS ne
    sont importables d'aucune façon depuis Python) ; la ronde en a d'ailleurs
    trouvé une huitième, écrite en prose dans `mod-capture.js`."""
    front = REPO / "frontend" / "cardforge" / "js"
    back = pathlib.Path(CP.__file__).parent
    porteurs = [back / "face.py", back / "frame.py", back / "type.py",
                back / "capture.py", front / "mod-face.js",
                front / "mod-frame.js", front / "mod-type.js",
                front / "mod-capture.js"]
    vus = {}
    for p in porteurs:
        assert p.is_file(), p
        m = re.search(r"MAX_IMPORT_PX\s*=\s*(\d+)",
                      p.read_text(encoding="utf-8"))
        assert m, f"{p.name} ne déclare plus MAX_IMPORT_PX"
        vus[p.name] = int(m.group(1))
    assert len(vus) == 8, vus
    assert set(vus.values()) == {4096}, vus
    assert CP.MAX_IMPORT_PX == 4096
    # ... ET AUCUN 4096 ORPHELIN dans les fichiers de la pièce : un plafond
    # écrit en clair dans une phrase est une copie de plus, que rien ne
    # confronte (c'est exactement ce que la ronde a trouvé).
    for p in (back / "capture.py", front / "mod-capture.js"):
        txt = p.read_text(encoding="utf-8")
        for m in re.finditer(r"4096", txt):
            ligne = txt[txt.rfind("\n", 0, m.start()) + 1:
                        txt.find("\n", m.start())]
            assert "MAX_IMPORT_PX" in ligne, \
                f"{p.name} écrit 4096 hors de sa constante : {ligne.strip()!r}"


def test_une_image_trop_grande_est_REDUITE_a_MAX_IMPORT_PX():
    """4096 px de côté long, mesurés sur le fichier SERVI."""
    did = _deck()
    r = _post(did, _carte(5000, 2000), "recto")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert max(d["w"], d["h"]) == CP.MAX_IMPORT_PX, d
    assert d["h"] == round(2000 * 4096 / 5000), d       # le ratio est tenu
    with Image.open(io.BytesIO(_get(did, "source_recto.png").content)) as im:
        assert im.size == (d["w"], d["h"]), "le fichier ment sur la réponse"
    CC.delete_deck(did)


def _damier(w: int, h: int) -> bytes:
    """Un damier de 1 pixel — le pire cas d'un rééchantillonnage, et le seul
    motif où plus-proche-voisin et filtre séparable donnent des images
    OPPOSÉES au lieu de proches."""
    a = bytes([0, 255] * (w // 2)) + (b"\x00" if w % 2 else b"")
    b = bytes([255, 0] * (w // 2)) + (b"\xff" if w % 2 else b"")
    im = Image.frombytes("L", (w, h),
                         b"".join(a if y % 2 == 0 else b for y in range(h)))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def test_la_reduction_FILTRE_vraiment_elle_ne_prend_pas_un_pixel_sur_deux():
    """LE TÉMOIN SURVIVANT DE LA PREMIÈRE RONDE, FERMÉ. `Image.LANCZOS`
    remplacé par `Image.NEAREST` ne faisait tomber aucun des 19 contrôles :
    les dimensions et le poids sont identiques, seule la QUALITÉ change — et
    rien ne la mesurait. Il n'a pas fallu l'outillage de T2 pour la mesurer,
    juste le bon sujet : sur un damier de 1 px réduit de 5000 à 4096, un
    filtre séparable MOYENNE (écart-type mesuré 6,0 sur 255) là où le
    plus-proche-voisin REPIQUE le damier (127,5). Le seuil est posé à 40 —
    vingt fois la marge d'un côté, trois fois de l'autre : il attrape la
    substitution sans se briser sur un changement de filtre honnête."""
    did = _deck()
    r = _post(did, _damier(5000, 2000), "recto")
    assert r.status_code == 200, r.text[:200]
    assert r.json()["w"] == CP.MAX_IMPORT_PX, r.json()
    from PIL import ImageStat
    with Image.open(io.BytesIO(_get(did, "source_recto.png").content)) as im:
        ecart = ImageStat.Stat(im.convert("L")).stddev[0]
    assert ecart < 40, \
        (f"écart-type {ecart:.1f} sur le fichier servi : le damier a survécu "
         f"à la réduction, donc aucun filtrage n'a eu lieu")
    CC.delete_deck(did)


def test_le_reimport_REMPLACE_et_ne_laisse_aucun_tmp():
    """Une capture est un point de départ, pas une pile : le second envoi
    écrase le premier. Et l'écriture est ATOMIQUE — le `.tmp` de la fenêtre
    d'écriture ne survit pas à la requête."""
    did = _deck()
    _post(did, _carte(200, 280), "recto")
    r = _post(did, _carte(300, 200), "recto")
    assert r.status_code == 200, r.text
    assert (r.json()["w"], r.json()["h"]) == (300, 200)
    d = CT.deck_dir(did) / "capture"
    restes = [p.name for p in d.iterdir()]
    assert restes == ["source_recto.png"], restes
    with Image.open(d / "source_recto.png") as im:
        assert im.size == (300, 200), "l'ancien fichier a survécu"
    CC.delete_deck(did)


def test_une_ecriture_qui_ECHOUE_ne_laisse_NI_final_NI_brouillon():
    """L'ATOMICITÉ, MESURÉE PLUTÔT QUE LUE. La preuve était au texte (l'ordre
    de `.tmp` et de `replace(` dans la source) : elle ne disait rien de ce qui
    arrive VRAIMENT quand l'écriture meurt. Ici `Image.save` écrit puis lève,
    exactement comme un disque plein ou un verrou : le nom final ne doit pas
    exister (personne ne servira une image tronquée), le brouillon ne doit pas
    rester (il s'accumulerait à chaque incident), et la réponse doit être un
    refus NOMMÉ — pas une trace de pile."""
    from PIL import Image as _I
    did = _deck()
    # LES OCTETS SONT FABRIQUÉS AVANT LE PIÈGE : `_carte` passe elle aussi par
    # `Image.save`, et la poser après le remplacement ferait mourir le test au
    # lieu de la route.
    corps = _carte(60, 84)
    vrai = _I.Image.save

    def _save_qui_meurt(self, fp, *a, **k):
        vrai(self, fp, *a, **k)                  # le brouillon est écrit...
        raise OSError(13, "verrou simule par le test")   # ... puis tout casse

    _I.Image.save = _save_qui_meurt
    try:
        r = _post(did, corps, "recto")
    finally:
        _I.Image.save = vrai
    assert r.status_code != 500, r.text[:300]
    assert r.status_code == 409, (r.status_code, r.text[:300])
    detail = r.json()["detail"]
    assert "verrou simule" in detail, detail
    # LE CHEMIN ABSOLU NE SORT PAS. `str(OSError)` porte le nom du fichier,
    # donc le nom de compte de l'utilisateur — la fuite du gauntlet, à ne pas
    # rejouer dans une réponse HTTP.
    assert "\\" not in detail and "/" not in detail, detail
    assert "olivi" not in detail.lower(), detail
    d = CT.deck_dir(did) / "capture"
    restes = sorted(p.name for p in d.iterdir()) if d.is_dir() else []
    assert restes == [], f"des restes après l'échec : {restes}"
    # et la pièce fonctionne toujours après l'incident
    assert _post(did, _carte(60, 84), "recto").status_code == 200
    CC.delete_deck(did)


def test_VINGT_PAIRES_D_ENVOIS_SIMULTANES_ne_font_AUCUN_500():
    """LE DÉFAUT LE PLUS CHER DE LA PREMIÈRE LIVRAISON, et il ne demandait
    qu'un double-clic : le brouillon s'appelait `source_recto.png.tmp`, LE
    MÊME pour tout le monde. Deux envois simultanés sur le même côté
    écrivaient dans le même fichier et se disputaient le `replace` —
    WinError 32, « le processus ne peut pas accéder au fichier », remonté en
    500. Mesuré avant correction sur 40 requêtes : {200: 36, 500: 4}, soit
    10 %.

    Le test envoie VINGT PAIRES sur le même côté, en vraie concurrence, avec
    des tailles distinctes pour que le gagnant soit identifiable. Ce qui est
    exigé : aucun 500, aucun brouillon abandonné, un fichier final ENTIER —
    celui de l'un des envois, pas un mélange des deux — et la très grande
    majorité des envois SERVIS.

    CE DERNIER POINT EST LE VRAI SEUIL, et il a fallu le mesurer pour
    l'écrire. « Aucun 500 » ne suffisait pas : le brouillon partagé remis en
    place rendait 40 refus 409 sur 40 et NE LAISSAIT AUCUN FICHIER — un
    contrôle qui ne regarde que le code de panne aurait vu là un système
    poli. Mesures sur ce poste, 40 envois simultanés de 1400x1900 :
      · brouillon partagé ............... {409: 40}, dossier VIDE
      · brouillon unique ................ {200: 33, 409: 7}
      · brouillon unique + patience ..... {200: 40} (trois passages)
    Le plancher est posé à 90 % (36/40) : trois fois la marge du pire cas
    mesuré, et infiniment loin du zéro du défaut."""
    did = _deck()
    # DES CARTES DE LA TAILLE D'UN VRAI SCAN. Sur des vignettes de 200 px,
    # l'encodage PNG dure moins d'une milliseconde et la fenêtre de course est
    # trop étroite pour se reproduire : le test restait VERT sur le défaut
    # remis (mesuré). À ~2,6 Mpx, l'écriture dure assez pour que deux threads
    # se croisent — c'est aussi la taille des images que la pièce recevra.
    tailles = [(1400 + 2 * i, 1900 + 2 * i) for i in range(40)]
    appels = [("POST", f"/api/cards/{did}/capture/card?side=recto",
               {"content": _carte(w, h),
                "headers": {"Content-Type": "image/png"}})
              for (w, h) in tailles]
    reps = _en_parallele(appels)
    codes = {}
    for r in reps:
        codes[r.status_code] = codes.get(r.status_code, 0) + 1
    assert 500 not in codes, (codes, [r.text[:160] for r in reps
                                      if r.status_code == 500][:2])
    assert set(codes) <= {200, 409}, codes
    assert codes.get(200, 0) >= 0.9 * len(tailles), \
        f"{codes} : la course mange les envois au lieu de les servir"
    # AUCUN BROUILLON ABANDONNÉ : un `.tmp` par requête, tous consommés.
    d = CT.deck_dir(did) / "capture"
    restes = sorted(p.name for p in d.iterdir())
    assert restes == ["source_recto.png"], restes
    # LE DERNIER GAGNE PROPREMENT : le fichier est une image ENTIÈRE, et sa
    # taille est celle d'un des envois — jamais deux moitiés cousues.
    servi = _get(did, "source_recto.png")
    assert servi.status_code == 200
    with Image.open(io.BytesIO(servi.content)) as im:
        im.load()
        assert im.size in tailles, (im.size, tailles[:3])
    CC.delete_deck(did)


# ═══════════════════════ le service, par liste blanche ══════════════════════

def test_le_GET_sert_par_LISTE_BLANCHE_et_refuse_la_traversee():
    """Un nom de fichier est un IDENTIFIANT, jamais un chemin. Le double
    garde-fou de `deck_dir` protège le `did` ; le nom, lui, n'a que cette
    liste — et elle est close."""
    did = _deck()
    _post(did, _carte(80, 112), "recto")
    for mauvais in ("../meta.json", "..%2fmeta.json", "source_recto.png.tmp",
                    "source_RECTO.png", "meta.json", "source_dos.png",
                    "source_recto.jpg", "", "source_recto",
                    # LE $-NEWLINE, QUATRIÈME OCCURRENCE DE LA LEÇON DU
                    # CHANTIER : en Python, `$` apparie AUSSI juste avant un
                    # saut de ligne final. `source_recto.png%0A` passait donc
                    # la liste blanche d'un motif ancré par `$` + `.match`.
                    # `\\Z` + `fullmatch` ne connaissent que la fin de chaîne.
                    "source_recto.png%0A", "source_recto.png%0D%0A",
                    "source_recto.png%20"):
        chemin = f"/api/cards/{did}/capture/file/{mauvais}"
        r = _api("GET", chemin)
        assert r.status_code in (400, 404), (mauvais, r.status_code)
        assert "json" in r.headers.get("content-type", ""), \
            f"{mauvais} rend {r.headers.get('content-type')} — le catch-all SPA"
        assert not r.text.lstrip().startswith("<")
    CC.delete_deck(did)


def test_la_liste_blanche_REFUSE_le_saut_de_ligne_final():
    """LE $-NEWLINE, QUATRIÈME FOIS SUR CE CHANTIER. En Python, `$` apparie
    aussi JUSTE AVANT un saut de ligne final : `re.match(r"^x\\.png$",
    "x.png\\n")` réussit. Un nom venu d'une URL (`…%0A`) traversait donc la
    liste blanche d'un motif ancré par `$`.

    LE CONTRÔLE EST PRIS SUR LA FONCTION, PAS SUR LA ROUTE, et c'est le point :
    par HTTP le défaut ne se voyait pas — le fichier « source_recto.png\\n »
    n'existe pas sur le disque, donc la route rendait 404 de toute façon et le
    test restait vert sur le motif fautif (mesuré). Le jour où un nom à
    espace-fin ou à point-fin (que Windows, lui, RABOTE en ouvrant le fichier)
    passerait la liste, le 404 deviendrait un 200. La garde se prouve où elle
    est écrite."""
    for mauvais in ("source_recto.png\n", "source_recto.png\r\n",
                    "source_verso.png\n", "source_recto.png ",
                    "source_recto.png.", "source_recto.png\t"):
        assert not CP.FILE_RE.fullmatch(mauvais), repr(mauvais)
        with pytest.raises(Exception) as e:
            CP._name_or_404(mauvais)
        assert getattr(e.value, "status_code", None) == 404, repr(mauvais)
    for bon in ("source_recto.png", "source_verso.png"):
        assert CP._name_or_404(bon) == bon


def test_un_tmp_de_la_fenetre_d_ecriture_n_est_jamais_servi():
    """LE CAS SE FABRIQUE : on POSE un `.tmp` à la main, comme la fenêtre
    d'écriture en laisse un, et on demande la porte. Sans liste blanche de
    noms FINAUX, un `?nom=source_recto.png.tmp` servirait un fichier en cours
    d'écriture — c'est-à-dire une image tronquée présentée comme la capture."""
    did = _deck()
    d = CT.deck_dir(did, create=True) / "capture"
    d.mkdir(parents=True, exist_ok=True)
    (d / "source_recto.png.tmp").write_bytes(_carte(40, 56)[:200])
    # ... et le brouillon RÉEL, qui porte un suffixe unique depuis la ronde.
    (d / f"source_recto.png.{'a' * 32}.tmp").write_bytes(_carte(40, 56)[:200])
    for nom in ("source_recto.png.tmp",
                f"source_recto.png.{'a' * 32}.tmp"):
        r = _api("GET", f"/api/cards/{did}/capture/file/{nom}")
        assert r.status_code in (400, 404), (nom, r.status_code)
    assert (d / "source_recto.png.tmp").is_file(), "le test n'a rien prouvé"
    CC.delete_deck(did)


def test_un_fichier_absent_ou_un_deck_inconnu_sont_NOMMES():
    did = _deck()
    r = _get(did, "source_recto.png")
    assert r.status_code == 404
    assert "capture" in r.json()["detail"].lower(), r.json()["detail"]
    for faux in ("deck_00000000", "pas_un_did"):
        r = _get(faux, "source_recto.png")
        assert r.status_code in (400, 404), (faux, r.status_code)
        assert "json" in r.headers.get("content-type", "")
    r = _post("deck_00000000", _carte(40, 56), "recto")
    assert r.status_code == 404, r.status_code
    CC.delete_deck(did)


# ═══════════════════════ jamais 500 ═════════════════════════════════════════

def test_jamais_500_quoi_qu_on_envoie():
    """Spec §8. Le corps est BRUT : tout ce qui n'est pas une image doit
    ressortir en refus nommé, jamais en trace de pile."""
    did = _deck()
    corps = [b"{\"pas\": \"une image\"}", b"\x00\x01\x02\x03",
             b"GIF89a" + b"\x00" * 40, _carte(20, 28)[:60],
             "des accents é à".encode("utf-8"),
             b"\x89PNG\r\n\x1a\n" + b"\xff" * 300]
    for c in corps:
        for side in (None, "recto", "verso", "milieu"):
            r = _post(did, c, side)
            assert r.status_code != 500, (c[:12], side, r.text[:200])
            assert r.status_code in (400, 413), (c[:12], side, r.status_code)
            assert "json" in r.headers.get("content-type", "")
    CC.delete_deck(did)


def test_les_refus_sont_TOUS_en_francais():
    """La doctrine des refus nommés vaut pour la pièce entière : on balaie les
    `HTTPException` de la source et on exige un message, en français, qui ne
    soit pas un mot-clé technique nu.

    LE PLANCHER ÉTAIT `>= 5` POUR DOUZE REFUS : un `HTTPException` ajouté
    demain avec un message anglais, ou sans message du tout, ne serait pas
    même compté. Le contrôle est une ÉGALITÉ au nombre de `HTTPException` du
    fichier : tout refus non apparié par la regex fait tomber le test."""
    src = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    messages = re.findall(r'HTTPException\(\s*\d{3},\s*(?:f?")([^"]{6,})',
                          src)
    combien = len(re.findall(r"\bHTTPException\(", src))
    assert combien >= 8, combien
    assert len(messages) == combien, \
        (f"{combien} refus dans la source, {len(messages)} portent une phrase "
         f"française d'au moins 6 signes")
    # LA MARQUE D'UNE PHRASE ANGLAISE, en liste noire. Le contrôle d'avant
    # exigeait « deux groupes de lettres séparés par une espace » : « Empty
    # body » le satisfaisait sans broncher (mesuré en remettant le défaut).
    # Prouver qu'un texte EST français demanderait un dictionnaire ; refuser
    # les mots qui trahissent l'anglais tient en une ligne et attrape le cas
    # réel — un message écrit à la va-vite dans la langue du framework.
    ANGLAIS = {"the", "is", "are", "not", "must", "empty", "body", "invalid",
               "unknown", "missing", "failed", "error", "request", "required",
               "allowed", "found", "file", "too", "large", "please"}
    for m in messages:
        # `[^\W\d_]` = « une lettre », accents compris — un `[a-z]` couperait
        # « Côté » en deux et ferait échouer le test sur du français correct.
        assert re.search(r"[^\W\d_]{3,}\s+[^\W\d_]{2,}", m), m
        mots = {w.lower() for w in re.findall(r"[A-Za-z]+", m)}
        assert not (mots & ANGLAIS), (sorted(mots & ANGLAIS), m)


# ═══════════════════════ l'écran, ce qu'on peut lire d'ici ══════════════════

def test_l_ecran_n_a_AUCUN_painter_et_ne_sort_pas_de_chez_lui():
    """§9.4 : P10 ne dessine pas la carte. Et son panneau ne s'adresse qu'au
    sous-arbre `capture` — un `M.patch` d'une autre pièce serait une écriture
    hors jeton (le CORE la refuserait, mais elle ne doit pas être écrite)."""
    js = JS.read_text(encoding="utf-8")
    assert js.lstrip().startswith("/*") or js.lstrip().startswith('"use strict"')
    assert 'painters: []' in js.replace('painters:[', 'painters: [')
    assert re.search(r'id:\s*"capture"', js)
    for interdit in ("CF.patch(", "CF.api", "CF.setCards", "CF.setFormat"):
        assert interdit not in js, interdit
    css = CSS.read_text(encoding="utf-8")
    assert ".cf-capture" in css


def _corps_js(nom: str) -> str:
    """Le corps d'une fonction de mod-capture.js, du `function nom(` à
    l'accolade de fin de colonne 2 (l'indentation du module est stable)."""
    js = JS.read_text(encoding="utf-8")
    i = js.index("function " + nom + "(")
    j = js.index("\n  }", i)
    return js[i:j]


def _fonction_js(nom: str) -> str:
    """La fonction ENTIÈRE, accolade fermante comprise — prête à être
    exécutée. `_corps_js` s'arrête juste avant, pour l'inspection."""
    return _corps_js(nom) + "\n  }\n"


def _node(source: str) -> str:
    """Exécute du JS dans node et rend sa sortie. Le harnais QA du lab exige
    déjà node (`qa/test_core_contract.mjs`) ; ici il est OPTIONNEL — sur une
    machine sans node le contrôle se saute plutôt que de rougir pour une
    raison qui n'est pas la sienne."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la règle ne peut pas être EXÉCUTÉE ici")
    r = subprocess.run([node, "-e", source], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:400]
    return r.stdout.decode("utf-8", "replace")


def test_deposer_un_VERSO_n_efface_pas_l_analyse_du_RECTO():
    """DÉCISION DE PLAN (D3 amendé) : l'analyse est une propriété du RECTO.
    Les adoptions (§7.1.5 : illustration, bordure, zones) sont des gestes de
    recto ; le verso est stocké pour l'objet 3D et le dos (§6.2ter). La
    première livraison remettait l'analyse à zéro à CHAQUE dépôt : importer
    son verso effaçait donc les mesures du recto, sans un mot.

    LA RÈGLE EST EXÉCUTÉE, PAS LUE. La première écriture de ce contrôle
    lisait la forme du code (« la garde est là, l'effacement vient après ») :
    un `|| true` glissé dans la garde la laissait verte — mesuré. La décision
    vit donc dans une fonction PURE, que ce test extrait de la vraie source
    et fait tourner dans node.

    ET LA LISTE DES CLÉS N'EST PAS RECOPIÉE ICI (renfort T2) : elle se DÉRIVE
    du schéma déclaré par le module. Le contrôle nommait cinq clés en dur, et
    T2 en a ajouté trois (`echelle`, `ecart_ratio`, `notes`) — une mesure
    oubliée dans `effacements` aurait survécu à un nouveau recto, c'est-à-dire
    aurait décrit une image qui n'est plus sur le disque, et le test serait
    resté vert. Toute clé de mesure ajoutée demain tombe désormais ici."""
    fn = _fonction_js("effacements")
    sortie = _node(fn + """
      const dump = (s) => JSON.stringify(effacements(s));
      console.log(dump("recto") + "|" + dump("verso") + "|" + dump("milieu"));
    """)
    recto, verso, autre = sortie.strip().split("|")
    recto = json.loads(recto)
    assert json.loads(verso) == {}, f"un verso efface : {verso}"
    assert json.loads(autre) == {}, autre
    assert recto.get("analyzed", "absent") is None, recto
    # `sources` est le SEUL sous-arbre qu'un dépôt ne doit pas effacer (c'est
    # lui qu'il vient d'écrire) ; tout le reste décrit la mesure.
    mesure = _cles_du_schema() - {"sources"}
    manquantes = mesure - set(recto)
    assert not manquantes, \
        (f"un nouveau recto laisserait {sorted(manquantes)} en place : ces "
         f"mesures décriraient une image qui n'est plus sur le disque")
    # ... et l'écran le DIT : une asymétrie muette serait une surprise.
    js = JS.read_text(encoding="utf-8")
    assert re.search(r"analyse[^\n]{0,80}recto", js, re.I), \
        "aucune phrase d'écran n'explique que l'analyse porte sur le recto"


def test_l_ecran_distingue_UNE_ROUTE_ABSENTE_d_un_REFUS_NOMME():
    """Le CORE a déjà nommé ce bug et payé son remède (`core.js:jsonNamed`,
    §9bis) : traduire TOUT 404 en « backend absent » fait déclarer le domaine
    éteint parce qu'un JEU a été supprimé. `capture.py` rend précisément un
    404 « Deck introuvable » AVANT de lire le corps — un jeu effacé dans un
    autre onglet aurait donc affiché « backend absent : l'import exige
    /api/cards ». La question se tranche sur le TYPE DE RÉPONSE, pas sur le
    code : du HTML = pas de route, du JSON = le backend parle.

    LA RÈGLE VIT À UN SEUL ENDROIT (renfort T2). Elle était écrite dans
    `upload()` ; `analyser()` est arrivé avec le même besoin, et une règle
    recopiée est une règle qui dérive — le second appel aurait pu perdre la
    nuance sans que rien ne rougisse. Le contrôle exige donc la règle dans
    `lireJson` ET son usage par les DEUX appels."""
    corps = _corps_js("lireJson")
    assert "content-type" in corps.lower(), corps[-700:]
    assert "json" in corps, corps[-700:]
    assert "resp.status === 404" not in corps, \
        "le 404 est encore traduit en aveugle en « route absente »"
    for appel in ("upload", "analyser"):
        c = _corps_js(appel)
        assert "lireJson(" in c, \
            f"{appel}() lit la réponse à la main : la règle va diverger"
    # ... et l'échec de route reste NOMMÉ, pas silencieux.
    assert "missing" in _corps_js("panne")


def test_l_ecran_ne_promet_que_les_formats_que_PIL_sait_ouvrir():
    """`accept="image/*"` ouvrait le sélecteur sur HEIC, SVG, AVIF, TIFF —
    que la route refuse en 400 « corps illisible ». Un filtre de fichiers est
    une PROMESSE : il ne doit proposer que ce qui passe."""
    js = JS.read_text(encoding="utf-8")
    m = re.search(r'accept="([^"]+)"', js)
    assert m, "le champ de dépôt ne filtre plus rien"
    assert m.group(1) == "image/png,image/jpeg,image/webp", m.group(1)


def test_l_apercu_ne_peut_pas_echouer_en_silence():
    """Gotcha connu du projet (vignettes du dock, 2026-08) : une `<img>` sans
    `onerror` qui perd son fichier laisse la DERNIÈRE image affichée, ou un
    cadre vide, et l'écran continue d'annoncer « capture déposée ». Le PNG
    peut disparaître (dossier nettoyé, jeu dupliqué à moitié) : l'échec doit
    se voir."""
    js = JS.read_text(encoding="utf-8")
    # `"onerror" in js` était vrai d'un `img.onerrorX` — un contrôle qui se
    # contente d'un mot ne voit pas une faute de frappe. L'AFFECTATION est ce
    # qui branche le garde-fou : c'est elle qu'on exige.
    assert re.search(r"\bimg\.onerror\s*=\s*(\(|function)", js), \
        "aucun garde-fou branché sur le chargement de l'aperçu"


def test_le_bouton_de_la_galerie_ne_promet_plus_la_phase_4():
    """Le placeholder honnête (`core.js:galImport`) devait mourir le jour où
    la pièce existe : un bouton qui explique qu'il ne fait rien alors que le
    panneau est là serait devenu un mensonge à l'envers."""
    core = (REPO / "frontend" / "cardforge" / "js" / "core.js") \
        .read_text(encoding="utf-8")
    i = core.index("function galImport(")
    corps = core[i:core.index("\n  }", i)]
    assert "phase 4" not in corps, corps
    assert 'show("capture")' in corps, corps


# ═══════════════════════ T2 — l'analyse, à vérité connue ════════════════════

def test_l_analyse_SANS_RECTO_est_un_404_qui_dit_quoi_faire():
    """L'analyse court sur le recto STOCKÉ : sans recto, il n'y a rien à
    mesurer, et le refus doit envoyer déposer — pas annoncer une panne."""
    did = _deck()
    r = _analyse(did)
    assert r.status_code == 404, (r.status_code, r.text[:300])
    detail = r.json()["detail"]
    assert "recto" in detail.lower(), detail
    assert re.search(r"dépos", detail, re.I), detail
    # ... et un verso SEUL ne suffit pas non plus : la mesure est du recto.
    _post(did, _pngs(_synth()), "verso")
    r = _analyse(did)
    assert r.status_code == 404, (r.status_code, r.text[:200])
    CC.delete_deck(did)


def _imports_par_fonction() -> dict:
    """{nom de fonction (ou "<module>") : {modules importés dedans}}.

    LE BALAYAGE EST SUR L'ARBRE SYNTAXIQUE, PAS SUR LE TEXTE. La première
    écriture cherchait des sous-chaînes et rougissait sur un COMMENTAIRE de
    T1 qui nomme les routes futures — un test qui interdit de PARLER d'une
    chose n'est pas un test qui interdit de la FAIRE. Une dépendance payante
    ne peut entrer que par un import, et un import a une fonction hôte."""
    import ast
    arbre = ast.parse(pathlib.Path(CP.__file__).read_text(encoding="utf-8"))
    out: dict = {}

    def _pose(hote, n):
        s = out.setdefault(hote, set())
        if isinstance(n, ast.Import):
            s.update(a.name for a in n.names)
        else:
            s.add(n.module or "")
            s.update(f"{n.module or ''}.{a.name}" for a in n.names)

    def _marche(noeud, hote):
        for enfant in ast.iter_child_nodes(noeud):
            if isinstance(enfant, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _marche(enfant, enfant.name)
            else:
                if isinstance(enfant, (ast.Import, ast.ImportFrom)):
                    _pose(hote, enfant)
                _marche(enfant, hote)

    _marche(arbre, "<module>")
    return out


# Les fonctions qui composent le RELEVÉ. Une dépendance payante importée dans
# l'une d'elles serait un appel sur le chemin gratuit.
ANALYSE_FNS = (
    "analyse_recto", "_analyse_du_disque", "post_analyse", "_analyse_bordure",
    "_analyse_zones", "_analyse_fond", "_analyse_palette", "_grille",
    "_profils", "_front", "_mesure_fond", "_dominantes", "_couleur_bande",
    "_rayon_coin", "_composants", "_fusionne", "_store_image", "post_card",
)
# ... et les SEULES fonctions autorisées à toucher un fournisseur. La liste
# est courte EXPRÈS : elle est le périmètre de la dépense.
PAYANTES_FNS = ("_fal_upload", "_fal_rembg", "_fal_lire", "_rembg_local",
                "_rembg_local_dispo", "_prix_rembg", "_destination_sure")
INTERDITS = ("httpx", "requests", "urllib", "aiohttp", "fal_client", "openai",
             "rembg", "replicate", "socket", "http")


def test_l_analyse_ne_DEPENSE_rien_et_ne_sort_pas_de_la_machine(monkeypatch):
    """« GRATUIT, PIL pur, AUCUN appel réseau/fournisseur » (plan T2).

    AMENDEMENT T3, ET C'EST LA VÉRITÉ NEUVE : la pièce SAIT maintenant
    dépenser (`/rembg`), donc « aucun import payant dans le fichier » est
    devenu faux par construction. Ce qui reste vrai, et ce qui compte, c'est
    que la DÉPENSE A UN PÉRIMÈTRE : les modules payants n'entrent que par une
    poignée de fonctions nommées, jamais au niveau du module, et jamais sur
    le chemin de l'analyse. Le contrôle porte donc sur le périmètre — et il
    est doublé d'une preuve DYNAMIQUE : l'analyse jouée pour de vrai, les
    quatre portes du dehors fermées sur un compteur, qui reste à zéro."""
    par_fn = _imports_par_fonction()
    racines_module = {m.split(".")[0] for m in par_fn.get("<module>", set())}
    for interdit in INTERDITS:
        assert interdit not in racines_module, \
            (f"« {interdit} » est importé AU NIVEAU DU MODULE : il partirait "
             f"au chargement, pour toutes les routes")
    for fn in ANALYSE_FNS + PAYANTES_FNS:
        # LA LISTE DOIT RESTER VIVANTE : un renommage la viderait de son
        # sens sans faire rougir personne (le périmètre deviendrait « aucune
        # fonction », donc toujours respecté).
        assert hasattr(CP, fn), \
            f"{fn} a disparu : la liste du périmètre est périmée"
    for fn in ANALYSE_FNS:
        racines = {m.split(".")[0] for m in par_fn.get(fn, set())}
        for interdit in INTERDITS:
            assert interdit not in racines, \
                f"« {interdit} » entre par {fn}(), qui est sur le chemin gratuit"
    debordent = sorted(
        fn for fn, mods in par_fn.items()
        if fn not in PAYANTES_FNS
        and ({m.split(".")[0] for m in mods} & set(INTERDITS)))
    assert not debordent, \
        (f"des fonctions hors périmètre touchent un fournisseur : {debordent} "
         f"— la dépense doit rester dans {sorted(PAYANTES_FNS)}")
    # Les seules dépendances de calcul, et elles sont locales.
    tous = set().union(*par_fn.values()) if par_fn else set()
    assert "app.services.pbr_service" in tous, sorted(tous)
    assert "app.services.pixel_ops.chroma_key" in tous, sorted(tous)
    # LA PREUVE DYNAMIQUE : l'analyse RÉELLE, portes fermées, compteur à zéro.
    s = _sentinelle(monkeypatch)
    did, _ = _pose_et_analyse(_synth(boites=TROIS))
    s.zero()
    CC.delete_deck(did)


def test_les_PRIMITIVES_reutilisees_existent_encore_chez_elles():
    """L'analyse emprunte `_micro_contrast` (PRIVÉE), `stats` et `chroma_key`
    à deux services voisins. Un renommage là-bas ferait tomber la route en
    production avec une trace de pile ; ici il fait rougir un test qui NOMME
    le contrat emprunté."""
    from app.services.pbr_service import _micro_contrast, stats
    from app.services.pixel_ops import chroma_key
    im = Image.new("L", (32, 32), 128)
    assert _micro_contrast(im, 1.5).size == (32, 32)
    s = stats(im)
    assert {"mean", "median", "p5", "p95", "span"} <= set(s)
    out, ok = chroma_key(Image.new("RGB", (40, 40), (10, 20, 30)))
    assert out.mode == "RGBA" and isinstance(ok, bool)


def test_une_BORDURE_POSEE_en_mm_est_RETROUVEE_a_tolerance_chiffree():
    """LE CŒUR DE §9.1 : le test pose x mm de bordure, l'analyse rend x.

    TOLÉRANCE : 1,5 pixel, soit 0,15 mm sur ce poste (630 px pour 63 mm). Ce
    n'est pas un chiffre de confort — c'est la RÉSOLUTION de la mesure : le
    front est localisé à la rangée près, et une rangée d'hésitation (le côté
    d'un bord anticrénelé) est le pire cas physique. Une tolérance plus large
    laisserait passer une erreur d'échelle ; plus étroite, elle rougirait sur
    une image ré-encodée."""
    tol = 1.5 * SYNTH_MM_PX
    for bord_px in (13, 26, 40):
        did, a = _pose_et_analyse(_synth(bord_px))
        b = a["border"]
        attendu = bord_px * SYNTH_MM_PX
        assert b, f"bordure de {bord_px} px non vue : {a['notes']}"
        assert abs(b["mm"] - attendu) <= tol, \
            (f"bordure posée {attendu:.3f} mm, mesurée {b['mm']} mm "
             f"(tolérance {tol:.3f} mm)")
        # ... et la COULEUR de la bande est celle qu'on a peinte, à l'octet.
        assert b["color"] == "#d8b76a", (b["color"], bord_px)
        assert 0.0 <= b["confidence"] <= 1.0, b
        CC.delete_deck(did)


def test_une_bordure_IRREGULIERE_a_une_confiance_PLUS_BASSE():
    """Le chiffre doit BOUGER DANS LE BON SENS. Bandes posées de 1,0 / 2,6 /
    4,0 / 6,0 mm : la régularité tombe à 1 - (6-1)/6 = 0,167, et la confiance
    la suit. Sans cette exigence, une « confiance » constante à 1 passerait
    tous les autres contrôles de ce fichier."""
    did, reg = _pose_et_analyse(_synth(26))
    CC.delete_deck(did)
    irr = Image.new("RGB", (SYNTH_W, SYNTH_H), OR)
    # gauche 10, haut 40, droite 26, bas 60 px
    ImageDraw.Draw(irr).rectangle(
        [10, 40, SYNTH_W - 27, SYNTH_H - 61], fill=NOIR)
    did, a = _pose_et_analyse(irr)
    a, b = a["border"], reg["border"]
    assert a and b
    assert a["confidence"] < b["confidence"], (a["confidence"], b["confidence"])
    assert a["confidence"] < 0.5, a
    # et les quatre épaisseurs mesurées SONT les quatre posées, CHACUNE À SON
    # BORD (gauche 10, haut 40, droite 26, bas 60 px).
    assert a["epaisseurs_mm"] == {"gauche": 1.0, "haut": 4.0,
                                 "droite": 2.6, "bas": 6.0}, a["epaisseurs_mm"]
    CC.delete_deck(did)


def test_un_recto_FLOU_fait_tomber_la_confiance_puis_la_bordure():
    """LA SECONDE PART DE LA CONFIANCE, et son cas connu. Le profil de bord
    est une MOYENNE sur 60 % du bord : elle écrase le grain (un bruit uniforme
    de ±28 par canal laisse la netteté à 0,993 — mesuré). Ce qu'elle n'écrase
    pas, c'est un front ÉTALÉ — la photo floue d'une carte. Mesuré à sigma
    0 / 1 / 3 px : confiance 1,00 -> 0,50 -> 0,167, puis plus de bordure du
    tout à sigma 6 (le front ne domine plus le plancher)."""
    from PIL import ImageFilter
    vues = []
    for sigma in (0, 1, 3):
        im = _synth(26)
        if sigma:
            im = im.filter(ImageFilter.GaussianBlur(sigma))
        did, a = _pose_et_analyse(im)
        assert a["border"], (sigma, a["notes"])
        vues.append(a["border"]["confidence"])
        CC.delete_deck(did)
    assert vues[0] > vues[1] > vues[2], vues
    assert vues[2] < 0.3, vues
    did, a = _pose_et_analyse(_synth(26).filter(ImageFilter.GaussianBlur(6)))
    assert a["border"] is None, a["border"]
    CC.delete_deck(did)


def test_une_carte_SANS_bordure_n_en_publie_AUCUNE_et_le_DIT():
    """« Aucun front trouvé » = bordure ABSENTE du résultat, jamais « 0 mm,
    confiance 1 » (plan D4). Une carte pleine illustration, un dégradé doux :
    la bonne réponse est de se taire et d'expliquer."""
    grad = Image.new("RGB", (SYNTH_W, SYNTH_H))
    d = ImageDraw.Draw(grad)
    for y in range(SYNTH_H):
        d.line([(0, y), (SYNTH_W, y)],
               fill=(int(20 + y * 0.25), 40, int(200 - y * 0.2)))
    did, a = _pose_et_analyse(grad)
    assert a["border"] is None, a["border"]
    assert any("ordure" in n for n in a["notes"]), a["notes"]
    # LE PIÈGE NOMMÉ PAR LE PLAN, épinglé : pas de zéro rassurant.
    assert not isinstance(a["border"], dict), a["border"]
    CC.delete_deck(did)
    # ... et un contraste sous le plancher (L1 = 24 pour un plancher de 40)
    # se tait aussi, alors que L1 = 45 se voit : le plancher est un seuil,
    # pas une opinion.
    for delta, attendu in ((15, True), (8, False)):
        im = Image.new("RGB", (SYNTH_W, SYNTH_H),
                       (120 + delta, 120 + delta, 120 + delta))
        ImageDraw.Draw(im).rectangle(
            [26, 26, SYNTH_W - 27, SYNTH_H - 27], fill=(120, 120, 120))
        did, a = _pose_et_analyse(im)
        assert bool(a["border"]) is attendu, (delta, a["border"], a["notes"])
        CC.delete_deck(did)


def test_les_TROIS_BOITES_POSEES_sont_retrouvees_ET_COMPTEES():
    """La seconde vérité connue de §9.1. Trois cartouches posés au pixel :
    l'analyse doit en rendre TROIS — le compte exact, pas « au moins » — et
    chacun doit recouvrir le sien.

    SEUIL D'APPARIEMENT : IoU >= 0,60. Le plafond n'est pas libre — les
    boîtes sont quantifiées sur une grille de 1,5 mm, donc un cartouche de
    9 x 9 mm mesuré à un bloc près ne PEUT pas dépasser ~0,74 d'IoU. Mesuré
    sur les trois : 0,914 / 0,890 / 0,735. Le seuil est posé sous le pire des
    trois, et loin au-dessus du 0,05 que rendait une grille de 2,5 mm."""
    did, a = _pose_et_analyse(_synth(26, TROIS))
    boites = a["boxes"]
    assert len(boites) == 3, [(b["x"], b["y"], b["w"], b["h"]) for b in boites]
    trouvees = [[b["x"], b["y"], b["w"], b["h"]] for b in boites]
    for (x, y, w, h) in TROIS_BOITES_PX:
        posee = [v * SYNTH_MM_PX for v in (x, y, w, h)]
        meilleur = max(_iou(posee, t) for t in trouvees)
        assert meilleur >= 0.60, \
            (f"cartouche posé {[round(v, 1) for v in posee]} mm : meilleur "
             f"recouvrement {meilleur:.3f} sur {trouvees}")
    for b in boites:
        assert 0.0 < b["densite"] <= 1.0, b
        assert 0.0 < b["nettete"] <= 1.0, b
        assert b["x"] >= 0 and b["y"] >= 0, b
    CC.delete_deck(did)


def test_la_bordure_ne_DEVORE_pas_les_boites():
    """LE DÉFAUT MESURÉ PENDANT L'ÉCRITURE, épinglé pour de bon. La bande de
    bordure est le plus fort contraste de la carte : sans retrait, son anneau
    relie les trois cartouches en UN SEUL composant faisant le tour de
    l'image — mesuré, une boîte de 570 x 825 px au lieu de trois. Une boîte
    qui couvre plus des trois quarts de la carte est cet anneau-là."""
    did, a = _pose_et_analyse(_synth(26, TROIS))
    carte = a["echelle"]["carte_mm"]
    for b in a["boxes"]:
        part = (b["w"] * b["h"]) / float(carte[0] * carte[1])
        assert part < 0.75, (part, b, "l'anneau de bordure est passé en zone")
    CC.delete_deck(did)


def test_deux_boites_EMBOITEES_n_en_font_qu_UNE():
    """LA FUSION, ET LE CAS QU'ELLE EXISTE POUR RÉGLER. Les composants connexes
    sont disjoints par construction — mais leurs RECTANGLES peuvent
    s'emboîter : un cartouche CREUX (un cadre à filet) est un seul composant
    dont la boîte englobe tout ce qui est posé dedans, et un pictogramme au
    centre en est un second, sans contact.

    Deux boîtes pour une seule zone donneraient deux slots superposés à P3.
    Mesuré sur le montage ci-dessous : 2 composants, 1 boîte après fusion —
    et 2 si l'on remonte le seuil de fusion au-dessus de 1."""
    im = _synth(26)
    d = ImageDraw.Draw(im)
    d.rectangle([100, 200, 520, 620], outline=(235, 220, 160), width=6)
    d.rectangle([270, 380, 350, 460], fill=(240, 230, 120))
    did, a = _pose_et_analyse(im)
    assert len(a["boxes"]) == 1, \
        [(b["x"], b["y"], b["w"], b["h"]) for b in a["boxes"]]
    b = a["boxes"][0]
    # ... et la boîte fusionnée est bien celle du cadre POSÉ (10 x 20 mm,
    # 42 x 42 mm), à un bloc près.
    assert _iou([b["x"], b["y"], b["w"], b["h"]], [10.0, 20.0, 42.0, 42.0]) \
        >= 0.85, b
    CC.delete_deck(did)


def test_un_FOND_NON_UNI_est_refuse_AVEC_LA_MESURE_QUI_A_REFUSE():
    """Spec §8 :589 — « fond non uni à l'import -> refus mesuré du détourage
    local + proposition de l'option IA ». Le refus doit porter le CHIFFRE et
    le SEUIL, et proposer la suite sans en donner le prix (le prix vient de
    `pricing.py` par la route d'options, jamais d'une copie)."""
    grad = Image.new("RGB", (SYNTH_W, SYNTH_H))
    d = ImageDraw.Draw(grad)
    for y in range(SYNTH_H):
        d.line([(0, y), (SYNTH_W, y)],
               fill=(int(20 + y * 0.25), 40, int(200 - y * 0.2)))
    did, a = _pose_et_analyse(grad)
    bg = a["bg"]
    assert bg.get("bg_failed") is True, bg
    assert bg["seuil"] == CP.FOND_SEUIL_UNI == 0.60, bg
    assert 0.0 <= bg["uniformite"] < bg["seuil"], \
        f"le refus n'est pas motivé par sa mesure : {bg}"
    assert bg["motif"] == "pourtour non uni", bg
    phrase = bg["option_ia"]
    assert "IA" in phrase and "payante" in phrase, phrase
    # LE PRIX N'EST PAS RECOPIÉ (doctrine D5) : aucun chiffre monétaire ici.
    assert not re.search(r"\d[\d ,.]*\s*(\$|€|USD|EUR)", phrase), phrase
    # LA NOTE PORTE LE MÊME CHIFFRE, ÉCRIT EN FRANÇAIS. Les notes sont de la
    # prose (l'écran les affiche telles quelles) : « 0.246 » au milieu de
    # trois lignes à virgule décimale se voit — mesuré à l'écran, corrigé.
    fr = str(bg["uniformite"]).replace(".", ",")
    assert any("ond" in n and fr in n for n in a["notes"]), (fr, a["notes"])
    assert not any(re.search(r"\d\.\d", n) for n in a["notes"]), \
        [n for n in a["notes"] if re.search(r"\d\.\d", n)]
    CC.delete_deck(did)


def test_un_FOND_UNI_rend_sa_couleur_POSEE_et_sa_confiance():
    """L'autre côté de la porte : pourtour uni, sujet assez grand pour que la
    couverture tienne dans [5 %, 95 %]. La couleur rendue est celle POSÉE.

    TOLÉRANCE : 6 niveaux par canal. La clé est la MÉDIANE des échantillons
    de pourtour — sur un aplat elle est exacte, et les 6 niveaux couvrent un
    ré-encodage qui ne serait pas sans perte. Mesuré ici : écart 0."""
    fond = (30, 60, 120)
    uni = Image.new("RGB", (SYNTH_W, SYNTH_H), fond)
    ImageDraw.Draw(uni).rectangle([120, 180, 500, 700], fill=(230, 200, 90))
    did, a = _pose_et_analyse(uni)
    bg = a["bg"]
    assert not bg.get("bg_failed"), bg
    vu = tuple(int(bg["color"][i:i + 2], 16) for i in (1, 3, 5))
    assert max(abs(v - p) for v, p in zip(vu, fond)) <= 6, (bg["color"], fond)
    assert bg["confidence"] == bg["uniformite"] >= CP.FOND_SEUIL_UNI, bg
    assert CP.FOND_COUV_MIN <= bg["couverture"] <= CP.FOND_COUV_MAX, bg
    CC.delete_deck(did)


def test_la_MESURE_du_fond_et_le_VERDICT_de_chroma_key_ne_divergent_pas():
    """LA MESURE PUBLIÉE VIENT D'ICI, LE VERDICT VIENT DE `pixel_ops`. Deux
    formules pour un seul refus : si elles dérivaient, le message dirait
    « pourtour non uni à 0,82 » sur un refus causé par autre chose — un
    utilisateur chercherait un fond que rien ne condamne. Le contrôle exige
    l'accord sur les deux cas, dans les deux sens."""
    from app.services.pixel_ops import chroma_key
    grad = Image.new("RGB", (300, 420))
    d = ImageDraw.Draw(grad)
    for y in range(420):
        d.line([(0, y), (300, y)], fill=(int(20 + y * 0.5), 40, int(200 - y * 0.4)))
    uni = Image.new("RGB", (300, 420), (30, 60, 120))
    ImageDraw.Draw(uni).rectangle([60, 90, 240, 330], fill=(230, 200, 90))
    for im, attendu in ((grad, False), (uni, True)):
        m = CP._mesure_fond(im)
        _, ok = chroma_key(im, tolerance=CP.FOND_TOLERANCE,
                           feather=CP.FOND_FEATHER)
        assert ok is attendu, (attendu, ok)
        porte = (m["uniformite"] >= CP.FOND_SEUIL_UNI
                 and CP.FOND_COUV_MIN <= m["couverture"] <= CP.FOND_COUV_MAX)
        assert porte is ok, \
            (f"la mesure d'ici dit {porte} là où chroma_key dit {ok} : "
             f"uniformité {m['uniformite']:.3f}, couverture {m['couverture']:.3f}")


def test_la_PALETTE_rend_les_teintes_POSEES():
    """Quantification adaptative sur une carte peinte de cinq aplats connus :
    les deux dominants doivent sortir À L'OCTET (une médiane de coupe sur une
    zone uniforme rend la couleur elle-même), et les parts doivent faire 1."""
    did, a = _pose_et_analyse(_synth(26, TROIS))
    hexs = [c["hex"] for c in a["palette"]]
    assert len(hexs) == CP.PALETTE_N == 6, hexs
    assert "#d8b76a" in hexs, hexs        # la bande
    assert "#14120c" in hexs, hexs        # l'intérieur (20,18,12)
    parts = [c["part"] for c in a["palette"]]
    assert abs(sum(parts) - 1.0) < 0.02, parts
    assert parts == sorted(parts, reverse=True), parts
    CC.delete_deck(did)


def test_L_ECHELLE_VIENT_DU_FORMAT_DU_DECK_et_pas_de_l_image():
    """La MÊME image, trois formats : les millimètres changent, et chacun est
    exactement `trim_mm[0] * px / largeur`. C'est la preuve que l'échelle
    n'est pas un hasard de l'image — elle vient du document."""
    octets = _synth(26)
    for fmt, trim in (("poker_eu", 63.0), ("tarot_eu", 70.0), ("mini", 44.0)):
        did, a = _pose_et_analyse(octets, fmt)
        attendu = trim * 26 / SYNTH_W
        assert a["echelle"]["fmt"] == fmt, a["echelle"]
        assert abs(a["border"]["mm"] - attendu) < 1e-3, \
            (fmt, a["border"]["mm"], attendu)
        assert abs(a["echelle"]["carte_mm"][0] - trim) < 0.01, a["echelle"]
        CC.delete_deck(did)


def test_la_BANDE_EXCLUE_du_retrait_est_NOMMEE_et_les_boites_coupees_AVOUEES():
    """LA TROUVAILLE BLOQUANTE DE LA RONDE. Le retrait qui empêche l'anneau de
    bordure d'avaler les zones (contrôle voisin) blanchit AUSSI une bande de
    plusieurs millimètres le long des quatre bords — 6,00 mm mesurés pour une
    bordure de 2,6 mm. Un cartouche posé dedans ressortait COUPÉ à la
    frontière du masque, avec une densité et une netteté parfaitement
    saines : rien, dans le relevé, ne distinguait la coupe d'une mesure.
    Mesuré, cartouche de 30 x 9 mm : collé au coin -> IoU 0,459 ; à 3 mm du
    bord -> 0,503 — SOUS le seuil d'appariement de 0,60 de cette suite ; et
    `notes` était VIDE dans les cinq cas.

    C'est le cas du Patriarche (bandeau de titre collé au cadre), et T3 fera
    naître des slots de ces millimètres-là. Trois exigences : la bande est
    publiée EN MILLIMÈTRES, la note la nomme avec ses deux termes, et toute
    boîte qui la touche porte `tronquee`."""
    did, a = _pose_et_analyse(_synth(26, [(27, 27, 300, 90, (235, 220, 160))]))
    assert a["zones_bande_mm"] and a["zones_bande_mm"] > 0, a["zones_bande_mm"]
    note = [n for n in a["notes"] if "bande" in n and "exclue" in n]
    assert note, a["notes"]
    assert _fr_py(a["zones_bande_mm"]) in note[0], (a["zones_bande_mm"], note)
    assert a["boxes"], a["notes"]
    assert all(b.get("tronquee") is True for b in a["boxes"]), a["boxes"]
    CC.delete_deck(did)
    # ... et une boîte LOIN du bord ne porte pas le drapeau : sinon il ne
    # dirait rien, il décorerait.
    did, a = _pose_et_analyse(_synth(26, [(200, 200, 300, 90, (235, 220, 160))]))
    assert a["boxes"], a["notes"]
    assert all(b.get("tronquee") is False for b in a["boxes"]), a["boxes"]
    CC.delete_deck(did)


def _fr_py(v, n=2):
    """Le MÊME écrivain de nombres que la source (`capture._fr`) — pas une
    seconde recette. Deux façons d'écrire un nombre dans un test et dans le
    code, c'est un faux-rouge qui attend son zéro final : `str(rnd(0.250,3))`
    donne « 0.25 » quand `_fr` donne « 0,250 »."""
    return CP._fr(v, n)


def test_les_QUATRE_EPAISSEURS_sont_APPARIEES_a_leur_bord():
    """DEUX TRIS, DEUX CLÉS. `bords` sortait de `sorted(vus)` — l'ordre
    ALPHABÉTIQUE des noms — et `epaisseurs_mm` de `sorted(eps)` — l'ordre
    NUMÉRIQUE des épaisseurs. Les apparier par indice était donc faux dès que
    l'ordre des mesures n'était pas l'ordre de l'alphabet. Mesuré sur des
    bandes posées gauche 1,0 / haut 2,0 / droite 3,0 / bas 4,0 mm :
    l'appariement par indice donnait {bas: 1,0, droite: 2,0, gauche: 3,0,
    haut: 4,0} — les QUATRE fausses. `epaisseurs_mm` est un DICTIONNAIRE."""
    im = Image.new("RGB", (SYNTH_W, SYNTH_H), OR)
    # gauche 10 px, haut 20 px, droite 30 px, bas 40 px
    ImageDraw.Draw(im).rectangle(
        [10, 20, SYNTH_W - 31, SYNTH_H - 41], fill=NOIR)
    did, a = _pose_et_analyse(im)
    b = a["border"]
    assert b["epaisseurs_mm"] == {"gauche": 1.0, "haut": 2.0,
                                 "droite": 3.0, "bas": 4.0}, b["epaisseurs_mm"]
    # `bords` et le dictionnaire disent la MÊME chose — une seule vérité.
    assert b["bords"] == sorted(b["epaisseurs_mm"]), b
    CC.delete_deck(did)
    # ... et quand un bord seulement est vu, il n'y en a QU'UN dans le
    # dictionnaire : on ne publie pas trois trous pour faire quatre.
    im = Image.new("RGB", (SYNTH_W, SYNTH_H), OR)
    ImageDraw.Draw(im).rectangle([0, 20, SYNTH_W - 1, SYNTH_H - 1], fill=NOIR)
    did, a = _pose_et_analyse(im)
    if a["border"]:
        assert set(a["border"]["epaisseurs_mm"]) == set(a["border"]["bords"])
        assert len(a["border"]["bords"]) < 4, a["border"]
    CC.delete_deck(did)


def test_une_bordure_TEXTUREE_est_refusee_pour_SA_VRAIE_RAISON():
    """LE TÉMOIN `BORD_FRONT_RATIO`, RETOURNÉ PAR LA RONDE. L'aveu de la
    livraison disait deux choses, toutes deux fausses : que le rapport ne mord
    jamais sur une carte, et qu'il ne mord que sur une image minuscule.

    Mesuré : sur un profil OSCILLANT (rayures de 2 px), la marche médiane vaut
    455 et le plancher passe de 40 à 1824 — le rapport décide, et il décide
    seul. Sur une image de 40 x 56, la marche médiane vaut 0 : le rapport ne
    joue AUCUN rôle. C'est l'inverse exact de ce qui était écrit.

    Conséquence réelle, et c'est elle qu'on garde : un scan tramé ou une
    bordure à filets fins rend `border: null` avec une note qui disait
    « aucun front franc » — un refus qui ne nomme pas sa cause. La note doit
    dire le PROFIL TEXTURÉ et ses deux chiffres."""
    ray = Image.new("RGB", (SYNTH_W, SYNTH_H), NOIR)
    d = ImageDraw.Draw(ray)
    for y in range(0, SYNTH_H, 4):
        d.rectangle([0, y, SYNTH_W - 1, y + 1], fill=OR)
    did, a = _pose_et_analyse(ray)
    assert a["border"] is None, a["border"]
    tex = [n for n in a["notes"] if "textur" in n.lower()]
    assert tex, a["notes"]
    assert "455" in tex[0] and "1824" in tex[0], tex[0]
    # ... et le refus ORDINAIRE (dégradé doux, marche médiane nulle) garde sa
    # note à lui : les deux causes ne se confondent pas.
    grad = Image.new("RGB", (SYNTH_W, SYNTH_H))
    dg = ImageDraw.Draw(grad)
    for y in range(SYNTH_H):
        dg.line([(0, y), (SYNTH_W, y)],
                fill=(int(20 + y * 0.25), 40, int(200 - y * 0.2)))
    CC.delete_deck(did)
    did, a = _pose_et_analyse(grad)
    assert a["border"] is None
    assert not any("textur" in n.lower() for n in a["notes"]), a["notes"]
    assert any("front franc" in n for n in a["notes"]), a["notes"]
    CC.delete_deck(did)


def test_l_option_IA_n_est_PAS_proposee_quand_il_n_y_a_RIEN_a_detourer():
    """Un aplat total refuse par la porte de COUVERTURE : 0,0 % de l'image
    survivrait au détourage, c'est-à-dire qu'il n'y a pas de sujet. Proposer
    là une option PAYANTE, c'est vendre un service sans objet."""
    did, a = _pose_et_analyse(Image.new("RGB", (SYNTH_W, SYNTH_H), (90, 90, 90)))
    bg = a["bg"]
    assert bg["bg_failed"] is True and bg["couverture"] == 0.0, bg
    assert "option_ia" not in bg, bg.get("option_ia")
    assert "rien" in bg["motif"] or "rien" in " ".join(a["notes"]).lower(), \
        (bg["motif"], a["notes"])
    CC.delete_deck(did)


def test_le_RAYON_est_CORRIGE_du_biais_de_la_rangee_exterieure():
    """LE BIAIS ÉTAIT CONNU, ÉCRIT, EXACT — ET ABSORBÉ PAR UNE TOLÉRANCE DIX
    FOIS TROP LARGE. La ronde a eu raison : un biais qu'on sait calculer se
    corrige, il ne se tolère pas.

    D'OÙ IL VIENT : la rangée extérieure d'un coin arrondi a une HAUTEUR. Le
    premier pixel plein de cette rangée n'est pas à `r` du coin mais à
    `r - sqrt(r)` environ — le pixel dont le centre entre le premier dans le
    disque. Ce n'est PAS un artefact de la bibliothèque de dessin du test :
    c'est vrai de tout arc rastérisé, donc du scan d'une vraie carte. La
    correction appartient à la MESURE, pas au montage.

    Mesuré avant correction, rayons posés 10/20/40/60/90 px : 7/16/34/53/81 px
    lus, soit 3 à 9 px de moins — 12 à 30 % du rayon. Après inversion, l'écart
    tombe sous 0,10 mm, et la tolérance passe de 1,00 mm à 0,15 mm : la même
    que l'épaisseur de bande, parce que c'est la même résolution — 1,5 px."""
    tol = 1.5 * SYNTH_MM_PX
    for r_px in (10, 20, 40, 60, 90):
        im = Image.new("RGB", (SYNTH_W, SYNTH_H), (255, 255, 255))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, SYNTH_W - 1, SYNTH_H - 1], radius=r_px,
                            fill=OR)
        d.rectangle([26, 26, SYNTH_W - 27, SYNTH_H - 27], fill=NOIR)
        did, a = _pose_et_analyse(im)
        vu = a["border"]["radius_mm"]
        attendu = r_px * SYNTH_MM_PX
        assert abs(vu - attendu) <= tol, \
            (f"rayon posé {attendu:.2f} mm, mesuré {vu} mm "
             f"(tolérance {tol:.2f} mm)")
        CC.delete_deck(did)
    # ... et un coin CARRÉ rend toujours zéro : la correction ne fabrique pas
    # un rayon là où la course vaut zéro pixel.
    did, a = _pose_et_analyse(_synth(26))
    assert a["border"]["radius_mm"] == 0.0, a["border"]
    CC.delete_deck(did)


def test_le_SEUIL_DE_SILENCE_de_l_ecart_de_ratio_est_NOMME_et_tenu():
    """Le 0,005 nu de la livraison : sous un demi-pour-cent d'écart, l'image
    est au format à l'arrondi d'un pixel près (un poker_eu de 630 px de large
    fait 880 px de haut ; 879 ou 881 donnent déjà ±0,11 %), et une note à
    chaque analyse serait du bruit. Il porte maintenant un nom et sa raison.
    Mesuré aux deux bords : +0,0045 se tait, +0,0057 parle."""
    assert 0.0 < CP.ECART_RATIO_MUET < 0.05, CP.ECART_RATIO_MUET
    for cible, parle in ((0.004, False), (0.006, True)):
        hh = int(round(SYNTH_W * (88.0 / 63.0) * (1 + cible)))
        did, a = _pose_et_analyse(_synth(26).resize((SYNTH_W, hh)))
        assert abs(a["ecart_ratio"]) > 0, a["ecart_ratio"]
        vu = any("ratio" in n for n in a["notes"])
        assert vu is parle, (cible, a["ecart_ratio"], a["notes"])
        CC.delete_deck(did)


def test_une_dependance_ABSENTE_rend_503_avec_l_erreur_LITTERALE():
    """La doctrine §8 était REVENDIQUÉE et jamais jouée. On la joue : la
    bibliothèque d'images est retirée du chargeur le temps d'une requête, et
    le refus doit être un 503 qui PORTE l'erreur, pas un 500.

    (Ce que la prose de la source dit maintenant : PIL n'est pas une
    dépendance optionnelle de ce laboratoire — ce garde-fou couvre une
    installation cassée, pas une option absente. La doctrine 503 vise les
    dépendances vraiment facultatives, et T3 en aura une.)"""
    import types
    did = _deck()
    _post(did, _pngs(_synth(26)), "recto")
    # `PIL.Image` AUSSI, et c'est le piège du montage : `from PIL import Image`
    # ne s'arrête pas à l'attribut manquant, il retombe sur le SOUS-MODULE —
    # qui est encore dans le chargeur. Une première écriture ne retirait que
    # `PIL` et la route répondait 200, la bibliothèque toujours là.
    vrais = {k: v for k, v in sys.modules.items()
             if k == "PIL" or k.startswith("PIL.")}
    for k in vrais:
        del sys.modules[k]
    sys.modules["PIL"] = types.ModuleType("PIL")     # un PIL sans `Image`
    try:
        r = _analyse(did)
    finally:
        sys.modules.pop("PIL", None)
        sys.modules.update(vrais)
    assert r.status_code == 503, (r.status_code, r.text[:300])
    detail = r.json()["detail"]
    assert "Image" in detail or "PIL" in detail, detail
    assert re.search(r"[éèêàç]", detail), detail
    # la pièce remarche une fois la bibliothèque revenue
    assert _analyse(did).status_code == 200
    CC.delete_deck(did)


def test_les_MESURES_franchissent_la_frontiere_en_MILLIMETRES():
    """Plan D3 : « une unité par frontière, convertie au bord de l'API ». Le
    relevé ne parle qu'en millimètres — la seule exception est `echelle`, dont
    le rôle EST de dire dans quel cadre ces millimètres se lisent (la trame de
    l'image en pixels, et le facteur qui l'y ramène).

    LE PIÈGE ÉTAIT ÉCRIT : la bordure publiait son épaisseur en pixels À CÔTÉ
    de ses millimètres, « pour le confort ». Deux unités pour une mesure, et
    la première pièce qui adopte (T3, T4) doit choisir laquelle croire.

    ET LE BALAYAGE SE DÉRIVE DE LA RÉPONSE, il ne récite pas quatre noms. La
    première écriture nommait `border`, `boxes`, `bg`, `palette` EN DUR : la
    ronde a ajouté un `retrait_px` au sommet du relevé, proprement déclaré
    partout, et les 56 contrôles sont restés verts. C'est la leçon des miroirs
    de T1 appliquée à un balayage — ce qu'on énumère à la main, on cesse de
    l'énumérer le jour où l'on ajoute une clé."""
    did, a = _pose_et_analyse(_synth(26, TROIS))

    def balaie(v, chemin):
        if isinstance(v, dict):
            for k, x in v.items():
                assert "px" not in k.split("_") and not k.endswith("_px"), \
                    f"{chemin}.{k} traverse l'API en pixels"
                balaie(x, f"{chemin}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                balaie(x, f"{chemin}[{i}]")

    balayees = set(a) - {"echelle"}
    assert len(balayees) >= 6, balayees
    for cle in sorted(balayees):
        assert "px" not in cle.split("_"), f"{cle} traverse l'API en pixels"
        balaie(a[cle], cle)
    # ... et `echelle` porte l'exception, EXPLICITEMENT nommée.
    assert a["echelle"]["image_px"] == [SYNTH_W, SYNTH_H], a["echelle"]
    assert abs(a["echelle"]["mm_par_px"] - SYNTH_MM_PX) < 1e-6, a["echelle"]
    CC.delete_deck(did)


def test_l_ECART_DE_RATIO_est_MESURE_et_publie_au_lieu_d_etre_un_echec():
    """Une image carrée sur un poker_eu : les mm sont calés sur la LARGEUR, et
    l'écart de ratio dit de combien la hauteur les dément. Publier l'écart
    plutôt que refuser, c'est le laisser servir — mais il doit être JUSTE :
    1,0000 / 1,3968 - 1 = -0,2841, au signe près."""
    did, a = _pose_et_analyse(_synth(24, w=600, h=600))
    attendu = 1.0 / (88.0 / 63.0) - 1.0
    assert abs(a["ecart_ratio"] - attendu) < 1e-3, (a["ecart_ratio"], attendu)
    assert a["ecart_ratio"] < 0, "une image plus large que le format"
    assert any("ratio" in n for n in a["notes"]), a["notes"]
    assert not any(re.search(r"\d\.\d", n) for n in a["notes"]), \
        ["une note écrit un nombre à l'anglaise", a["notes"]]
    CC.delete_deck(did)
    # ... et un ratio JUSTE ne fait pas de bruit.
    did, a = _pose_et_analyse(_synth(26))
    assert abs(a["ecart_ratio"]) < 1e-6, a["ecart_ratio"]
    assert not any("ratio" in n for n in a["notes"]), a["notes"]
    CC.delete_deck(did)


def test_une_image_PATHOLOGIQUE_degrade_l_analyse_SANS_500():
    """Spec §8 : jamais 500. Un pixel, trois pixels, un aplat total — chacun
    rend un relevé DÉGRADÉ ET AVOUÉ (les détections absentes, les notes qui
    disent pourquoi), pas une trace de pile."""
    # LA RÉFÉRENCE : les clés d'un relevé SAIN. Un relevé dégradé doit être
    # aussi COMPLET — vide, pas amputé. Une clé qui n'apparaît que sur le
    # chemin heureux force chaque lecteur à un `if` de plus, et l'écran, lui,
    # lèverait sur une valeur `undefined` (c'est la leçon `patchAs` de T1).
    did, sain = _pose_et_analyse(_synth(26, TROIS))
    cles = set(sain)
    CC.delete_deck(did)
    for (w, h) in ((1, 1), (2, 3), (SYNTH_W, SYNTH_H)):
        im = Image.new("RGB", (w, h), (90, 90, 90))
        did, a = _pose_et_analyse(im)
        assert set(a) == cles, (w, h, sorted(cles - set(a)), sorted(set(a) - cles))
        assert a["border"] is None, (w, h, a["border"])
        assert a["boxes"] == [], (w, h, a["boxes"])
        assert a["bg"].get("bg_failed") is True, (w, h, a["bg"])
        assert a["notes"], (w, h, "un relevé vide qui ne dit pas pourquoi")
        assert a["palette"], (w, h, a["palette"])
        assert a["analyzed"] > 1_000_000_000_000, a["analyzed"]
        CC.delete_deck(did)


def test_une_DETECTION_QUI_LEVE_laisse_le_releve_COMPLET_et_l_AVOUE():
    """LE CHEMIN GARDÉ, ENFIN JOUÉ. Chaque détection de `analyse_recto` est
    entourée d'un `try` qui écrit une note et continue — c'est ce qui tient la
    promesse « jamais 500 » sur une image pathologique. Mais rien ne
    l'exécutait : les images dégénérées passent par le chemin NORMAL (elles
    rendent zéro boîte, sans lever).

    Ce que le contrôle exige, et que la ronde a mis en lumière : sur ce
    chemin-là aussi, le relevé reste COMPLET. Une clé qui n'existe que si la
    détection réussit oblige chaque lecteur à un `if` de plus — et côté écran,
    `patchAs` reçoit un `undefined` que `sanitize` refuse (leçon T1)."""
    did = _deck()
    _post(did, _pngs(_synth(26, TROIS)), "recto")
    complet = set(_analyse(did).json())
    vrai = CP._grille

    def _grille_qui_meurt(*a, **k):
        raise RuntimeError("panne simulée par le test")

    CP._grille = _grille_qui_meurt
    try:
        r = _analyse(did)
    finally:
        CP._grille = vrai
    assert r.status_code == 200, (r.status_code, r.text[:300])
    a = r.json()
    assert set(a) == complet, sorted(complet - set(a))
    assert a["boxes"] == [] and a["zones_bande_mm"] is None, a["zones_bande_mm"]
    assert any("panne simulée" in n for n in a["notes"]), a["notes"]
    # ... et les AUTRES détections ont quand même travaillé : une panne de
    # zones n'emporte pas la bordure.
    assert a["border"] and a["border"]["mm"] == 2.6, a["border"]
    CC.delete_deck(did)


def test_un_aplat_GRENU_ne_fabrique_pas_de_zones():
    """LE PLANCHER D'ÉTENDUE, ET SON CAS QUI COMPTE. Un aplat PARFAIT ne prouve
    rien : son énergie est nulle partout, donc le seuil relatif ne découpe
    rien même sans plancher. Le vrai piège est le GRAIN — le scan d'une zone
    vide de la carte. Mesuré sur un aplat gris bruité de ±8 niveaux : sans le
    plancher, 12 « zones » sortent de nulle part ; avec, zéro. À ±4 : une
    contre zéro. Le plancher de 10 est ce qui sépare le grain du dessin (la
    carte de synthèse, elle, mesure une étendue de 89)."""
    import random
    random.seed(3)
    im = Image.new("RGB", (SYNTH_W, SYNTH_H))
    px = im.load()
    for y in range(SYNTH_H):
        for x in range(SYNTH_W):
            n = 120 + random.randint(-8, 8)
            px[x, y] = (n, n, n)
    did, a = _pose_et_analyse(im)
    assert a["boxes"] == [], \
        f"{len(a['boxes'])} zones inventées sur du grain : {a['boxes'][:2]}"
    assert any("tendue" in n for n in a["notes"]), a["notes"]
    CC.delete_deck(did)


def test_l_analyse_est_REJOUABLE_et_ne_touche_a_aucun_fichier():
    """« Relançable sans re-dépôt » (plan D3 précisé T2). Deux analyses de
    suite rendent les mêmes mesures, et le dossier ne bouge pas : la route
    RÉPOND, elle n'écrit rien — c'est la pièce qui publie."""
    did = _deck()
    _post(did, _pngs(_synth(26, TROIS)), "recto")
    a = _analyse(did).json()
    b = _analyse(did).json()
    for k in ("border", "boxes", "bg", "palette", "echelle", "ecart_ratio"):
        assert a[k] == b[k], k
    assert b["analyzed"] >= a["analyzed"]
    d = CT.deck_dir(did) / "capture"
    assert sorted(p.name for p in d.iterdir()) == ["source_recto.png"]
    CC.delete_deck(did)


def test_deposer_un_VERSO_ne_change_RIEN_a_la_mesure_du_recto():
    """L'asymétrie de D3 amendé, vue côté ROUTE cette fois (le contrôle
    voisin la prouve côté écran, dans node)."""
    did = _deck()
    _post(did, _pngs(_synth(26, TROIS)), "recto")
    avant = _analyse(did).json()
    _post(did, _pngs(_synth(13)), "verso")
    apres = _analyse(did).json()
    assert avant["border"] == apres["border"], (avant["border"], apres["border"])
    assert avant["boxes"] == apres["boxes"]
    CC.delete_deck(did)


def test_l_analyse_ne_rend_JAMAIS_500_meme_sur_un_recto_abime():
    """Un PNG tronqué posé À LA MAIN dans le dossier — l'accident réel d'un
    disque plein ou d'un dossier copié à moitié. La route doit le NOMMER."""
    did = _deck()
    d = CT.deck_dir(did, create=True) / "capture"
    d.mkdir(parents=True, exist_ok=True)
    (d / "source_recto.png").write_bytes(_pngs(_synth(26))[:400])
    r = _analyse(did)
    assert r.status_code != 500, r.text[:300]
    assert r.status_code in (400, 409), (r.status_code, r.text[:200])
    assert "json" in r.headers.get("content-type", "")
    assert re.search(r"[éèêàç]", r.json()["detail"]), r.json()["detail"]
    CC.delete_deck(did)


# ═══════════════════════ l'écran, côté mesures ══════════════════════════════

def test_le_SCHEMA_de_l_ecran_couvre_TOUTES_les_cles_du_releve():
    """LA FRONTIÈRE QUI CASSE EN SILENCE. `patchAs` LÈVE sur une clé hors
    schéma : une clé publiée par `analyse_recto` et absente du bloc `state:`
    de mod-capture.js ne « manquerait » pas à l'écran — elle ferait échouer le
    geste « Analyser » en entier, avec pour tout diagnostic « capture ne
    possède pas ecart_ratio » dans un toast. Rien d'autre que ce contrôle ne
    tient les deux bouts : le JS n'est importable d'aucune façon depuis
    Python, et le Python n'est lu par aucun test JS."""
    from app.services.cards.contract import geom
    releve = CP.analyse_recto(_synth(26, TROIS), geom("poker_eu", 300))
    schema = _cles_du_schema()
    hors = set(releve) - schema
    assert not hors, \
        (f"le backend publie {sorted(hors)} — `M.patch` lèvera : ajoutez-les "
         f"au bloc `state:` de mod-capture.js")
    # ... et dans l'autre sens : `releve()` ne doit pas inventer de clés.
    js = _corps_js("releve")
    for cle in sorted(set(releve)):
        assert cle + ":" in js, \
            f"releve() ne recopie pas « {cle} » : la mesure se perdrait"


def test_l_ecran_ecrit_TOUJOURS_un_CHIFFRE_de_confiance():
    """Spec §7.1.2 : « l'écran affiche le chiffre, jamais une certitude ». La
    règle est EXÉCUTÉE : on extrait `conf` et `num` de la vraie source et on
    les fait tourner dans node. Une version qui rendrait « bonne » ou
    « fiable » sur un nombre tomberait ici, et une virgule anglaise aussi."""
    src = (_fonction_js("estNombre") + _fonction_js("num")
           + _fonction_js("conf"))
    sortie = _node(src + """
      console.log([conf(0.84), conf(1), conf(0), conf(null), conf("x"),
                   num(2.6, 2), num(0.1665, 2)].join("|"));
    """)
    vus = sortie.strip().split("|")
    assert vus[0] == "confiance 0,84", vus
    assert vus[1] == "confiance 1,00", vus
    assert vus[2] == "confiance 0,00", "une confiance NULLE s'écrit aussi"
    assert vus[3] == "confiance inconnue" and vus[4] == "confiance inconnue", vus
    assert vus[5] == "2,60" and vus[6] == "0,17", vus
    # AUCUN ADJECTIF DE CERTITUDE dans les phrases d'ÉCRAN.
    #
    # LES COMMENTAIRES NE SONT PAS DES PHRASES D'ÉCRAN, et la première
    # écriture les confondait : un `'` d'apostrophe française dans un
    # commentaire (« qu'on n'a pas ») ferme un faux littéral, et tout le
    # commentaire entrait dans le balayage — le contrôle rougissait sur la
    # DOCTRINE qui interdit le mot. On dépouille donc pour de bon.
    plat = " ".join(_chaines_js(JS.read_text(encoding="utf-8"))).lower()
    assert "confiance " in plat, "le dépouillage a mangé les phrases d'écran"
    assert "deux decimales" not in plat, "un commentaire a survécu au dépouillage"
    for mot in ("fiable", "certaine", "sûre", "excellente", "parfaite",
                "bonne détection", "détection correcte"):
        assert mot not in plat, f"« {mot} » remplace un chiffre à l'écran"
    # ET LA CLASSE DE DÉFAUT EST FERMÉE, pas seulement l'occurrence trouvée.
    # `isFinite(Number(x))` est VRAI pour `null` : partout où l'écran s'en
    # servait pour décider s'il a une mesure, une mesure absente devenait un
    # zéro affiché (le rayon de coin non suivi, l'écart de ratio jamais
    # calculé). Le seul test d'existence autorisé est `estNombre`.
    js = JS.read_text(encoding="utf-8")
    assert "isFinite(Number(" not in js, \
        ("`isFinite(Number(x))` est de retour : il accepte null et le peint "
         "en zéro — utiliser `estNombre`")


def test_l_incrustation_des_boites_n_est_PAS_un_painter():
    """§9.4 : P10 n'a aucun z et ne dessine pas la carte. L'aperçu des boîtes
    est de l'HTML posé PAR-DESSUS l'<img>, en pourcentages de la carte —
    donc dans la même unité que `boxes`, sans mesurer une seule fois la mise
    en page. Un canvas ici serait un painter clandestin."""
    corps = _corps_js("dessineBoites")
    for interdit in ("getContext", "canvas", "CanvasRenderingContext"):
        assert interdit not in corps, interdit
    assert "carte_mm" in corps, "les boîtes ne sont pas placées par l'échelle"
    assert corps.count('+ "%"') >= 4, \
        "les quatre côtés doivent être posés en pourcentages"
    js = JS.read_text(encoding="utf-8")
    assert 'painters: []' in js.replace('painters:[', 'painters: [')


def test_le_refus_du_fond_nomme_a_l_ecran_la_PORTE_QUI_A_REFUSE():
    """Le JSON disait juste (`motif` nomme la porte), l'écran non : il posait
    TOUJOURS la ligne d'uniformité en tête. Sur un refus par COUVERTURE on
    lisait donc « uniformité 1,00 pour un plancher de 0,60 » — un chiffre qui
    PASSE, présenté comme la cause d'un refus — puis la couverture sans ses
    bornes, alors que `couverture_bornes` était publié et lu par personne.

    La règle est EXÉCUTÉE : on extrait `lignesFond` de la vraie source et on
    lui donne les deux refus."""
    src = (_fonction_js("isPlain") + _fonction_js("estNombre")
           + _fonction_js("num") + _fonction_js("lignesFond"))
    sortie = _node(src + """
      const uni = {bg_failed:true, motif:"pourtour non uni", uniformite:0.246,
                   seuil:0.6, couverture:0.15, couverture_bornes:[0.05,0.95],
                   option_ia:"IA"};
      const cou = {bg_failed:true, motif:"couverture hors bornes",
                   uniformite:1, seuil:0.6, couverture:0.0,
                   couverture_bornes:[0.05,0.95]};
      const ok = {color:"#1e3c78", confidence:1, couverture:0.358, seuil:0.6};
      console.log(JSON.stringify([lignesFond(uni), lignesFond(cou),
                                  lignesFond(ok)]));
    """)
    par_uni, par_couv, sain = json.loads(sortie)
    par_uni = " | ".join(x for x in par_uni if x)
    par_couv = " | ".join(x for x in par_couv if x)
    sain = " | ".join(x for x in sain if x)
    # le refus par uniformité mène avec l'uniformité...
    assert "uniformit" in par_uni.split("|")[1], par_uni
    assert "0,25" in par_uni and "0,60" in par_uni, par_uni
    # ... et le refus par COUVERTURE mène avec la couverture ET ses bornes,
    # sans jamais donner l'uniformité pour cause.
    assert "couverture" in par_couv.split("|")[1].lower(), par_couv
    assert "5" in par_couv and "95" in par_couv, \
        f"les bornes ne sont pas écrites : {par_couv}"
    tete = par_couv.split("|")[1].lower()
    assert "uniformit" not in tete, \
        f"la mauvaise porte est nommée en tête : {par_couv}"
    assert "refus" not in sain.lower(), sain


def test_l_ecran_DIT_quand_le_FORMAT_a_bouge_sous_les_mesures():
    """Le piège était nommé dans un commentaire, pas fermé. Le CORE émet
    `core:geom` quand le format change (core.js:424) ; P10 ne l'écoutait pas.
    Après un passage poker -> tarot, l'écran gardait sa pastille verte et
    affichait « 63,0 x 88,0 mm (poker_eu) » sur un jeu tarot : des
    millimètres faux de 11 %, présentés comme mesurés.

    La décision vit dans une fonction PURE, exécutée ici."""
    fn = _fonction_js("isPlain") + _fonction_js("divergence")
    sortie = _node(fn + """
      const d = (e, f) => JSON.stringify(divergence(e, {format: {fmt: f}}));
      console.log([d({fmt:"poker_eu"}, "poker_eu"), d({fmt:"poker_eu"}, "tarot_eu"),
                   d(null, "poker_eu"), d({fmt:"poker_eu"}, null),
                   d({}, "tarot_eu")].join("|"));
    """)
    memes, autres, sans_e, sans_f, vide = sortie.strip().split("|")
    assert json.loads(memes) is None, memes
    assert json.loads(autres) == {"avant": "poker_eu", "apres": "tarot_eu"}, autres
    for muet in (sans_e, sans_f, vide):
        assert json.loads(muet) is None, muet
    # ... et l'écran se REPEINT sur l'événement, sinon la divergence attend
    # un clic pour se voir. LA RECHERCHE PORTE SUR LE CODE DÉPOUILLÉ : la
    # ligne mise en commentaire satisfaisait le contrôle précédent (mesuré en
    # l'entourant de `/* */` — vert), ce qui en faisait un garde-fou qu'on
    # pouvait débrancher sans rien casser.
    code = _code_js(JS.read_text(encoding="utf-8"))
    assert re.search(r'CF\.on\(\s*"core:geom"', code), \
        "P10 n'écoute pas core:geom : le format peut bouger sans qu'elle le sache"
    assert "divergence(" in _code_js(_corps_js("mesures")), \
        "la divergence est calculée mais jamais affichée"


def test_le_bouton_des_ZONES_ne_promet_que_ce_qu_il_peut_faire():
    """Sa visibilité tenait au seul `boxes.length` ; l'incrustation, elle,
    exige AUSSI `echelle.carte_mm` — sans quoi elle n'a pas d'unité où poser
    ses pourcentages. Un document venu d'une version antérieure (des boîtes,
    pas d'échelle) affichait donc un bouton qui ne faisait rien. Les deux
    conditions sont la MÊME : `peutIncruster`."""
    src = (_fonction_js("isPlain") + _fonction_js("estNombre")
           + _fonction_js("peutIncruster"))
    sortie = _node(src + """
      const p = (s) => peutIncruster(s) ? 1 : 0;
      console.log([p({boxes:[{x:1}], echelle:{carte_mm:[63,88]}}),
                   p({boxes:[], echelle:{carte_mm:[63,88]}}),
                   p({boxes:[{x:1}], echelle:null}),
                   p({boxes:[{x:1}], echelle:{carte_mm:[0,88]}}),
                   p({})].join(""));
    """)
    assert sortie.strip() == "10000", sortie
    # ... et c'est ELLE que les deux endroits interrogent.
    for f in ("paint", "dessineBoites"):
        assert "peutIncruster(" in _corps_js(f), f


def test_une_PANNE_DE_RESEAU_ne_se_dit_pas_dans_la_langue_du_navigateur():
    """`panne()` ne traduisait que `e.missing` : un `fetch` rejeté (backend
    éteint, câble débranché) ressortait en « Failed to fetch », en anglais et
    sans dire ce qu'il faut faire. Le CORE a déjà écrit le remède
    (`core.js:1244`, « backend injoignable ») ; on l'applique."""
    src = _fonction_js("panne")
    sortie = _node(src + """
      const e1 = new Error("route absente"); e1.missing = true;
      const e2 = new TypeError("Failed to fetch");
      const e3 = new Error("Côté inconnu : « dos »");
      console.log([panne(e1, "l'analyse"), panne(e2, "l'analyse"),
                   panne(e3, "l'analyse")].join("|"));
    """)
    absente, reseau, nomme = sortie.strip().split("|")
    assert "backend absent" in absente, absente
    # LA PHRASE DU NAVIGATEUR RESTE, EN PARENTHÈSES, ET C'EST VOULU : la
    # doctrine du lab est « l'erreur LITTÉRALE, préfixée » — celui qui
    # diagnostique veut le mot exact, celui qui lit veut la phrase française.
    # Ce qui est interdit, c'est que la phrase anglaise soit TOUT le message.
    assert reseau.startswith("backend injoignable"), reseau
    assert "service local" in reseau, reseau
    assert reseau != "Failed to fetch", reseau
    # ... et un refus NOMMÉ par le backend traverse intact : le remède ne doit
    # pas avaler la phrase que la route a pris la peine d'écrire.
    assert nomme == "Côté inconnu : « dos »", nomme


def test_le_geste_ANALYSER_est_garde_contre_le_double_clic():
    """Patron BUSY de T1, étendu au second geste : le MÊME verrou que
    l'import — mesurer pendant qu'un fichier monte mesurerait l'image d'avant.
    Et le bouton n'existe pas sans recto : l'analyse porte sur lui."""
    corps = _corps_js("analyser")
    assert re.search(r"if\s*\(\s*BUSY\s*\)", corps), corps[:400]
    assert "BUSY = true" in corps and "BUSY = false" in corps, corps[:400]
    assert 'info("recto")' in corps, corps[:400]
    assert "M.patch(" in corps, "la PIÈCE publie (D3) — pas la route"
    peint = _corps_js("paint")
    assert "cf-capture-analyse" in peint, \
        "le bouton n'est pas piloté par l'état de l'écran"


# ═══════════════════════ T3 — le détourage IA opt-in ════════════════════════
#
# CE QUE CETTE SECTION VERROUILLE, et pourquoi chaque contrôle existe.
#
# §7.1.3 donne à P10 UNE capacité payante : rembg, « fal 0,003 $/image OU
# local si présent — MÊME basculement que le pipeline sprite », prix affiché.
# D5 en fait une doctrine en quatre points, et chacun a son contrôle :
#
#   1. LA DISPONIBILITÉ EST HONNÊTE. `GET /ai-options` dit ce qui est vraiment
#      là (import réussi ? clé posée ?) AVANT le clic. Rien de disponible n'est
#      PAS une erreur : la réponse le dit, et l'écran ne propose pas l'option.
#   2. LE PRIX VIENT DE LA TABLE. `pricing.load()["rembg_api_usd"]`, jamais une
#      copie — le contrôle bouge la table et exige que la réponse suive.
#   3. LE REFUS EST UN 503 LITTÉRAL FRANÇAIS. `routes.py` répond 400 sur
#      dépendance absente ; chez `cards`, §8 fait loi et l'écart ne fait pas
#      jurisprudence.
#   4. ZÉRO DOLLAR. L'espion est posé au POINT DE CONSOMMATION — la fonction
#      que LA ROUTE appelle — et un COMPTEUR D'APPELS RÉELS garde les quatre
#      portes par lesquelles de l'argent peut sortir (`fal_client`,
#      `FalSeedanceClient.upload_image`, `urlopen`). Il est asserté à ZÉRO
#      dans chacun des quatre chemins.
#
# LA VÉRITÉ SUR `rembg` DANS CE RUNTIME, mesurée le 24/08 : il n'est installé
# NI dans le python de développement NI dans le runtime embarqué de
# l'application, et il n'est pas dans `requirements.txt`. La voie locale est
# donc du code qui ne s'exécute JAMAIS ici — c'est pourquoi le test l'exerce
# avec un faux module `rembg` injecté dans `sys.modules` : sans lui, la moitié
# du basculement serait écrite et jamais jouée.


def _png_rgba(w: int = 60, h: int = 80, opaque: bool = True) -> bytes:
    """Un PNG RGBA plausible en retour de détourage : un disque opaque au
    milieu, le reste transparent. `opaque=False` rend une couche ENTIÈREMENT
    transparente — le « détourage » qui n'a rien gardé."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if opaque:
        ImageDraw.Draw(im).ellipse([w // 5, h // 5, w - w // 5, h - h // 5],
                                   fill=(210, 180, 100, 255))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


class _Sentinelle:
    """LE COMPTEUR D'APPELS RÉELS. Il ne simule rien : il compte, puis il
    LÈVE. Toute porte par laquelle un dollar peut sortir est refermée sur lui,
    et chaque test de cette section finit par `sentinelle.zero()`.

    Pourquoi un compteur ET une levée : la levée seule ferait rougir le test
    au bon endroit, mais un appel avalé par un `except Exception:` quelque
    part sur le chemin passerait inaperçu. Le compteur, lui, survit à tous les
    filets."""

    def __init__(self):
        self.n = 0
        self.portes: list = []

    def _porte(self, nom):
        def _refus(*a, **k):
            self.n += 1
            self.portes.append(nom)
            raise AssertionError(
                f"UN APPEL PAYANT RÉEL EST PARTI D'UN TEST : {nom}")
        return _refus

    def _porte_async(self, nom):
        async def _refus(*a, **k):
            self.n += 1
            self.portes.append(nom)
            raise AssertionError(
                f"UN APPEL PAYANT RÉEL EST PARTI D'UN TEST : {nom}")
        return _refus

    def zero(self):
        assert self.n == 0, f"{self.n} appel(s) réel(s) : {self.portes}"


def _sentinelle(monkeypatch, sauf=()) -> _Sentinelle:
    """Les portes du dehors, refermées sur le compteur.

    L'ESPION DE LA ROUTE EST AILLEURS (chaque test pose le sien sur la
    fonction que la route appelle) ; celui-ci est la CEINTURE : si un chemin
    oublié atteignait quand même le fournisseur, il compterait.

    `sauf` laisse UNE porte ouverte pour le test qui veut exercer le code qui
    la franchit — les autres restent fermées, et le compteur reste la preuve
    pour elles. Deux tests s'en servent, et chacun le dit. La porte ouverte
    n'est JAMAIS ouverte sur le réseau : le test qui la demande y pose son
    propre faux, qui rend des octets sans sortir de la machine.

    LE MODULE `fal_client` PORTE NEUF NOMS EXPORTÉS QUI PARTENT AU DEHORS, et
    la liste ci-dessous les couvre tous — pas seulement `subscribe_async`. La
    première rédaction en fermait cinq : un chemin qui aurait appelé `run`,
    `submit` ou `upload` (les variantes SYNCHRONES) serait passé au travers,
    et l'écart ne se voyait qu'en lisant `dir(fal_client)`."""
    s = _Sentinelle()
    try:
        import fal_client
    except Exception:                                    # pragma: no cover
        fal_client = None
    if "fal_client" in sauf:
        fal_client = None
    if fal_client is not None:
        for nom in ("subscribe_async", "submit_async", "run_async",
                    "stream_async", "upload_async", "upload_file_async",
                    "result_async", "status_async"):
            if hasattr(fal_client, nom):
                monkeypatch.setattr(fal_client, nom, s._porte_async(
                    "fal_client." + nom))
        for nom in ("subscribe", "submit", "run", "stream", "upload",
                    "upload_file", "result", "status"):
            if hasattr(fal_client, nom):
                monkeypatch.setattr(fal_client, nom,
                                    s._porte("fal_client." + nom))
    try:
        from app.services.fal_service import FalSeedanceClient
        monkeypatch.setattr(FalSeedanceClient, "upload_image",
                            staticmethod(s._porte_async(
                                "FalSeedanceClient.upload_image")))
    except Exception:                                    # pragma: no cover
        pass
    if "urlopen" not in sauf:
        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen",
                            s._porte("urllib.request.urlopen"))
    return s


def test_la_VRAIE_CLE_FAL_n_entre_PAS_dans_ce_processus():
    """LE BLOQUANT DE LA RONDE, ÉPINGLÉ. `os.environ.setdefault("FAL_KEY", …)`
    en tête de fichier ne tient PAS : `app/config.py` fait
    `_load_dotenv(ENV_FILE, override=True)` À L'IMPORT, et le `.env` du
    dossier de données gagne. Mesuré le 24/08 : `settings.FAL_KEY` valait la
    VRAIE clé (69 signes) dans le processus de test, donc la voie par défaut
    du basculement était la voie PAYANTE.

    Rien n'a fui — chaque test pose son espion et la sentinelle compte — mais
    la sûreté du banc tenait à ce que personne n'oublie une ligne. Ce contrôle
    la rend structurelle : si un jour l'ordre des imports change, ou si une
    pièce recharge les réglages, il rougit AVANT que quiconque écrive un
    nouveau test contre ce banc."""
    from app.config import settings
    assert settings.FAL_KEY == "test-key", \
        (f"la clé fal du processus de test n'est pas neutralisée "
         f"({len(settings.FAL_KEY or '')} signes) — un appel oublié partirait "
         f"pour de bon")
    # ... et l'objet `settings` du test est bien CELUI que la pièce lit.
    from app.config import settings as autre
    assert autre is settings
    assert CP._fal_dispo()[0] is True, "la clé de banc doit rester CRÉDIBLE"


class _FauxRembg:
    """Le module `rembg` que ce runtime n'a pas. Injecté dans `sys.modules`,
    il rend la voie locale JOUABLE — `_rembg_local_dispo` le voit, et
    `from rembg import remove` tombe sur `remove` d'ici.

    `pause` ouvre une VRAIE fenêtre de recouvrement : la route appelle
    `remove` dans un fil (`to_thread`), donc douze requêtes simultanées ne se
    chevauchent que si le travail dure. Sans elle, la coalescence se
    mesurerait sur une course qui n'a pas lieu."""

    def __init__(self, sortie=None, casse=None, pause=0.0):
        self.appels = 0
        self._sortie = sortie
        self._casse = casse
        self._pause = pause

    def remove(self, data, *a, **k):
        self.appels += 1
        if self._pause:
            time.sleep(self._pause)
        if self._casse:
            raise self._casse
        return self._sortie if self._sortie is not None else _png_rgba()


def _pose_rembg(monkeypatch, faux: _FauxRembg):
    monkeypatch.setitem(sys.modules, "rembg", faux)
    return faux


def _sans_rembg(monkeypatch):
    monkeypatch.delitem(sys.modules, "rembg", raising=False)


def _options(did: str):
    return _api("GET", f"/api/cards/{did}/capture/ai-options")


def _rembg(did: str):
    return _api("POST", f"/api/cards/{did}/capture/rembg")


def _deck_avec_recto(im=None) -> str:
    did = _deck()
    r = _post(did, _pngs(im if im is not None else _synth(boites=TROIS)),
              "recto")
    assert r.status_code == 200, r.text[:300]
    return did


# ── A. la disponibilité, dite avant le clic ─────────────────────────────────

def test_les_OPTIONS_IA_disent_la_VERITE_sur_les_deux_voies(monkeypatch):
    """« Disponibilité rapportée HONNÊTEMENT » (D5). Les quatre combinaisons
    de (rembg importable, clé fal posée) sont jouées, et la voie annoncée est
    celle que la route PRENDRAIT — locale d'abord, patron sprite."""
    from app.config import settings
    s = _sentinelle(monkeypatch)
    did = _deck()

    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "")
    j = _options(did).json()
    assert j["local"] is False and j["fal"] is False, j
    assert j["voie"] is None, j
    assert j["motif"], "rien de disponible et rien à dire : l'écran ne peut " \
                       "pas expliquer l'absence de l'option"

    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
    j = _options(did).json()
    assert j["local"] is False and j["fal"] is True and j["voie"] == "fal", j
    assert j["gratuit"] is False, j

    _pose_rembg(monkeypatch, _FauxRembg())
    j = _options(did).json()
    assert j["local"] is True and j["voie"] == "local", \
        "le local passe AVANT la voie payante (patron sprite)"
    assert j["gratuit"] is True, j

    monkeypatch.setattr(settings, "FAL_KEY", "")
    j = _options(did).json()
    assert j["local"] is True and j["fal"] is False and j["voie"] == "local", j

    # SANS PRIX TABULÉ, LA VOIE PAYANTE N'EST PAS OFFERTE (§8 « prix AVANT »).
    # Un bouton payant sans chiffre n'est pas un libellé honnête, c'est un
    # écart de spec : on ne peut pas dire le prix avant, donc on ne propose
    # pas. La voie GRATUITE, elle, ne dépend d'aucun tarif.
    from app.services import pricing
    vraie = pricing.load
    monkeypatch.setattr(pricing, "load",
                        lambda: {k: v for k, v in vraie().items()
                                 if k != CP.PRIX_CLE})
    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
    j = _options(did).json()
    assert j["fal"] is True and j["prix_usd"] is None, j
    assert j["voie"] is None, "une voie payante sans prix reste offerte"
    assert "tarif" in (j["fal_motif"] + j["motif"]).lower(), j
    _pose_rembg(monkeypatch, _FauxRembg())
    j = _options(did).json()
    assert j["voie"] == "local", "le gratuit ne dépend pas d'un tarif"
    s.zero()
    CC.delete_deck(did)


def test_SANS_PRIX_TABULE_le_detourage_PAYANT_ne_part_pas(monkeypatch):
    """L'autre bout de la même règle : la route refuse aussi. Un écran d'une
    version antérieure — ou un client hors CF — ne doit pas pouvoir déclencher
    une dépense dont personne n'a pu annoncer le montant."""
    from app.config import settings
    from app.services import pricing
    s = _sentinelle(monkeypatch)
    vraie = pricing.load
    monkeypatch.setattr(pricing, "load",
                        lambda: {k: v for k, v in vraie().items()
                                 if k != CP.PRIX_CLE})
    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 503, (r.status_code, r.text[:300])
    assert "tarif" in r.json()["detail"].lower(), r.json()["detail"]
    s.zero()
    CC.delete_deck(did)


# Les 22 noms sur lesquels les DEUX listes blanches sont jugées : celle du
# backend (`capture.FILE_RE`) et sa copie d'écran (`mod-face.CAPTURE_FILE_RE`).
# UN SEUL corpus, et c'est le point : deux demi-tests sur deux corpus
# différents ne prouvent aucune parité (leçon T4, « la parité compte TOUS les
# miroirs »).
NOMS_JUGES = (
    "source_recto.png", "source_verso.png", "sujet_recto.png",
    "sujet_verso.png", "sujet.png", "source.png", "source_recto.PNG",
    "Source_recto.png", "source_recto.png.tmp", "source_recto.png\n",
    "source_recto.png ", " source_recto.png", "source_recto.png\r",
    "../meta.json", "..%2fmeta.json", "capture/source_recto.png",
    "source_recto.jpg", "source_rectoXpng", "", "sujet_recto.png.bak",
    "sujet_recto", "sujet_recto.png?x=1",
)


def test_les_DEUX_listes_blanches_rendent_LE_MEME_VERDICT():
    """PARITÉ MESURÉE PAR EXÉCUTION, sur un corpus PARTAGÉ. `mod-face.js`
    porte une copie de `FILE_RE` (règle 8 : on recopie, on ne partage pas) —
    et une copie qui dériverait laisserait P1 fabriquer une URL que le backend
    refuse, ou l'inverse. Les deux motifs sont joués sur les 22 mêmes noms,
    l'un en Python, l'autre dans node."""
    js = FACE_JS.read_text(encoding="utf-8")
    m = re.search(r"^\s*const CAPTURE_FILE_RE = (.*);\s*$", js, re.M)
    assert m, "la copie de la liste blanche a disparu de mod-face.js"
    sortie = _node(
        "const RE = " + m.group(1) + ";\n"
        "const noms = " + json.dumps(list(NOMS_JUGES)) + ";\n"
        "console.log(JSON.stringify(noms.map((n) => RE.test(n))));")
    cote_js = json.loads(sortie)
    cote_py = [bool(CP.FILE_RE.fullmatch(n)) for n in NOMS_JUGES]
    ecarts = [(n, a, b) for n, a, b in zip(NOMS_JUGES, cote_py, cote_js)
              if a != b]
    assert not ecarts, f"les deux listes blanches divergent : {ecarts}"
    # ... et elles disent OUI aux trois noms servis, NON à tout le reste.
    assert [n for n, ok in zip(NOMS_JUGES, cote_py) if ok] == \
        ["source_recto.png", "source_verso.png", "sujet_recto.png"], \
        [n for n, ok in zip(NOMS_JUGES, cote_py) if ok]


def test_AUCUNE_voie_disponible_n_est_PAS_une_erreur(monkeypatch):
    """D5, mot pour mot : « option absente = pas proposée (AUCUNE erreur) ».
    Une route d'options qui répondrait 503 quand rien n'est là forcerait
    l'écran à traiter une absence comme une panne."""
    from app.config import settings
    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "")
    did = _deck()
    r = _options(did)
    assert r.status_code == 200, (r.status_code, r.text[:200])
    CC.delete_deck(did)


def test_les_OPTIONS_se_servent_meme_sans_recto_et_meme_sans_deck():
    """Précédent `frame.py:ai_models` : « un menu qui s'éteint parce qu'un
    deck a été supprimé est pire qu'inutile ». La question posée ici est
    « cette machine sait-elle détourer ? » — elle n'a pas de deck pour
    réponse. Un identifiant MAL FORMÉ reste refusé : c'est la garde de
    domaine, pas celle du dossier."""
    did = _deck()
    CC.delete_deck(did)
    assert _options(did).status_code == 200, "un deck supprimé éteint le menu"
    r = _api("GET", "/api/cards/pas-un-did/capture/ai-options")
    assert r.status_code in (400, 404), r.status_code


def test_le_PRIX_vient_de_pricing_et_n_est_JAMAIS_recopie(monkeypatch):
    """§8 :583 — « prix AVANT, depuis `pricing.py`, jamais recopié ». Deux
    preuves, et la seconde est la seule qui vaille : l'ÉGALITÉ à la table, ET
    le fait que déplacer la table déplace la réponse. Une constante recopiée
    passe la première et tombe sur la seconde."""
    from app.services import pricing
    did = _deck()
    j = _options(did).json()
    assert j["prix_usd"] == pricing.load()["rembg_api_usd"], \
        (j.get("prix_usd"), pricing.load().get("rembg_api_usd"))
    assert j["devise"] == "USD", j

    vraie = pricing.load
    monkeypatch.setattr(pricing, "load",
                        lambda: dict(vraie(), rembg_api_usd=0.0177))
    j2 = _options(did).json()
    assert j2["prix_usd"] == 0.0177, \
        f"le prix ne suit pas la table : {j2.get('prix_usd')}"
    CC.delete_deck(did)


def test_le_prix_n_est_ecrit_EN_DUR_ni_dans_la_piece_ni_dans_l_ecran():
    """Le tarif ne s'écrit qu'à UN endroit du produit : `pricing.DEFAULTS`.
    Une copie dans la pièce ou dans une phrase d'écran survivrait à une
    baisse de tarif et afficherait un prix faux — le pire des cas, parce
    qu'il est crédible.

    LE CHIFFRE CHERCHÉ VIENT DE LA TABLE, LUI AUSSI : l'écrire ici en aurait
    fait la copie de plus. Et il est cherché EN CONTEXTE — la première
    rédaction interdisait la suite « 0,003 » n'importe où, et rougissait sur
    un commentaire d'arrondi qui parle de 0,0025 et 0,003 à propos d'autre
    chose. Un contrôle qui rougit pour une raison qui n'est pas la sienne
    finit désarmé."""
    from app.services import pricing
    brut = repr(float(pricing.DEFAULTS["rembg_api_usd"]))
    motif = re.compile(re.escape(brut) + "|"
                       + re.escape(brut.replace(".", ",")))
    argent = re.compile(r"usd|\$|prix|tarif|rembg|price", re.I)
    py = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    for n, ligne in enumerate(py.splitlines(), 1):
        if motif.search(ligne):
            assert not argent.search(ligne), \
                f"capture.py:{n} recopie le tarif : {ligne.strip()}"
    # côté écran, les commentaires sont ÔTÉS : ce qui reste est du code, et un
    # tarif dans du code est une copie, sans discussion possible.
    code = _code_js(JS.read_text(encoding="utf-8"))
    assert not motif.search(code), \
        "le tarif est écrit en dur dans mod-capture.js"
    assert "rembg_api_usd" not in code, \
        "l'écran lit la table lui-même : le prix vient de la route"


def test_la_route_d_options_ne_DEPENSE_rien(monkeypatch):
    """Une route qui dit le prix ne doit pas le payer pour le savoir."""
    s = _sentinelle(monkeypatch)
    did = _deck()
    for _ in range(3):
        assert _options(did).status_code == 200
    s.zero()
    CC.delete_deck(did)


# ── B. le détourage lui-même : quatre chemins, zéro dollar ──────────────────

def test_le_detourage_SANS_RECTO_est_un_404_qui_dit_quoi_faire(monkeypatch):
    s = _sentinelle(monkeypatch)
    did = _deck()
    r = _rembg(did)
    assert r.status_code == 404, (r.status_code, r.text[:200])
    d = r.json()["detail"]
    assert "recto" in d and ("déposez" in d.lower() or "importez" in d.lower()), d
    s.zero()                       # le patron vaut aussi pour les refus
    CC.delete_deck(did)


def test_AUCUNE_voie_disponible_rend_503_LITTERAL_et_FRANCAIS(monkeypatch):
    """D5 : « invoquée quand même = 503 littéral (§8) ». `routes.py` répond
    400 sur dépendance absente (:710-720, :3835-3845) — l'écart est CONNU et
    ne fait pas jurisprudence chez `cards`, où §8 :581 dit 503. Le message
    doit nommer LES DEUX voies : sans cela, celui qui le lit ne sait pas s'il
    doit installer quelque chose ou poser une clé."""
    from app.config import settings
    s = _sentinelle(monkeypatch)
    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "")
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 503, (r.status_code, r.text[:300])
    d = r.json()["detail"]
    assert not re.search(r"[a-z]{4,} (is|not|the) ", d), f"anglais : {d}"
    assert "rembg" in d and "fal" in d.lower(), d
    s.zero()
    CC.delete_deck(did)


def test_LA_VOIE_LOCALE_produit_la_couche_SUJET_sans_un_centime(monkeypatch):
    """Le basculement du patron sprite, moitié gratuite. Le faux `rembg` est
    injecté dans `sys.modules` : c'est la SEULE façon de jouer ce chemin ici
    (rembg n'est installé dans aucun des deux runtimes, mesuré le 24/08)."""
    from app.config import settings
    s = _sentinelle(monkeypatch)
    faux = _pose_rembg(monkeypatch, _FauxRembg())
    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
    espion_fal = []
    monkeypatch.setattr(CP, "_rembg_fal",
                        lambda *a, **k: espion_fal.append(a) or b"")
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 200, (r.status_code, r.text[:400])
    j = r.json()
    assert j["voie"] == "local", "la clé fal était posée : le local passe avant"
    assert j["layer"] == "sujet_recto.png", j
    assert j["w"] > 0 and j["h"] > 0 and j["bytes"] > 0, j
    assert j["stamp"] > 1_600_000_000_000, "un horodatage en MILLISECONDES"
    assert faux.appels == 1, f"{faux.appels} appel(s) à rembg local"
    assert espion_fal == [], "la voie payante a été touchée"
    # la couche est SERVIE par le GET de la pièce, et c'est de la RGBA
    g = _get(did, "sujet_recto.png")
    assert g.status_code == 200, (g.status_code, g.text[:200])
    with Image.open(io.BytesIO(g.content)) as im:
        assert im.mode == "RGBA", im.mode
        assert im.getchannel("A").getextrema()[0] == 0, \
            "aucune transparence : ce n'est pas une couche de sujet"
    s.zero()
    CC.delete_deck(did)


def test_LA_VOIE_FAL_est_JOUEE_ENTIEREMENT_sous_espion(monkeypatch):
    """La moitié payante, exercée pour de vrai — le corps de `_rembg_fal`
    tourne. L'espion est posé sur ses TROIS primitives réseau, c'est-à-dire
    au POINT DE CONSOMMATION (leçon spy 3c) et non sur un alias importé
    ailleurs ; le compteur de la sentinelle prouve que rien n'a fui à côté."""
    from app.config import settings
    s = _sentinelle(monkeypatch)
    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
    vu = {"envois": 0, "appels": [], "tel": []}

    async def faux_upload(chemin):
        vu["envois"] += 1
        return "https://fal.example/entree.png"

    async def faux_rembg(url):
        vu["appels"].append(url)
        return "https://fal.example/sortie.png"

    async def faux_download(url):
        vu["tel"].append(url)
        return _png_rgba()

    monkeypatch.setattr(CP, "_fal_upload", faux_upload)
    monkeypatch.setattr(CP, "_fal_rembg", faux_rembg)
    monkeypatch.setattr(CP, "_fal_download", faux_download)
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 200, (r.status_code, r.text[:400])
    j = r.json()
    assert j["voie"] == "fal" and j["layer"] == "sujet_recto.png", j
    assert vu["envois"] == 1, f"{vu['envois']} envois : une image, un envoi"
    assert vu["appels"] == ["https://fal.example/entree.png"], vu
    assert vu["tel"] == ["https://fal.example/sortie.png"], vu
    assert (CP.cap_dir(did) / "sujet_recto.png").is_file()
    s.zero()
    CC.delete_deck(did)


def test_un_ECHEC_FOURNISSEUR_rend_l_erreur_LITTERALE_avec_son_PREFIXE(
        monkeypatch):
    """§8 :584 — « échec fournisseur -> erreur littérale + préfixe
    fournisseur ». Les deux voies échouent tour à tour, et chacune porte le
    NOM de qui a refusé : « fal.ai » pour l'une, « rembg » pour l'autre. Sans
    le préfixe, l'utilisateur ne sait pas où aller regarder son compte."""
    from app.config import settings
    s = _sentinelle(monkeypatch)
    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")

    async def casse(*a, **k):
        raise RuntimeError("crédit épuisé")

    monkeypatch.setattr(CP, "_fal_upload", casse)
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 502, (r.status_code, r.text[:300])
    d = r.json()["detail"]
    assert "fal" in d.lower() and "crédit épuisé" in d, d
    assert not (CP.cap_dir(did) / "sujet_recto.png").exists(), \
        "un échec a quand même écrit une couche"

    _pose_rembg(monkeypatch, _FauxRembg(casse=RuntimeError("modèle absent")))
    r = _rembg(did)
    assert r.status_code == 502, (r.status_code, r.text[:300])
    d = r.json()["detail"]
    assert "rembg" in d.lower() and "modèle absent" in d, d
    s.zero()
    CC.delete_deck(did)


def test_une_erreur_de_fournisseur_ne_FUIT_PAS_le_chemin_absolu(monkeypatch):
    """La jurisprudence de la fuite de nom (T1, incident du gauntlet) : une
    erreur littérale n'est pas une raison d'expédier `C:\\Users\\<compte>\\…`
    dans une réponse HTTP. `FalSeedanceClient.upload_image` lève précisément
    `FileNotFoundError(f"Image not found: {image_path}")`."""
    from app.config import settings
    s = _sentinelle(monkeypatch)
    _sans_rembg(monkeypatch)
    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
    did = _deck_avec_recto()
    chemin = str(CP.cap_dir(did) / "source_recto.png")

    async def casse(*a, **k):
        raise FileNotFoundError(f"Image not found: {chemin}")

    monkeypatch.setattr(CP, "_fal_upload", casse)
    d = _rembg(did).json()["detail"]
    assert chemin not in d, d
    assert "Users" not in d and ":\\" not in d, d
    assert "Image not found" in d, f"l'erreur littérale a disparu : {d}"
    s.zero()
    CC.delete_deck(did)


def test_une_couche_QUI_NE_RETIRE_RIEN_est_REFUSEE_AVEC_SON_CHIFFRE(
        monkeypatch):
    """LA DOCTRINE VAUT DE SES DEUX MOITIÉS. « Un détourage qui garde TOUT, ou
    rien, n'est pas un détourage » : la moitié « rien » était implémentée, la
    moitié « tout » ne l'était pas — et c'est pourtant le mode d'échec le plus
    ORDINAIRE de rembg (aucun sujet trouvé -> l'image ressort quasi intacte).
    L'utilisateur PAIE, et P1 adopte sa carte entière comme « sujet détouré ».

    LE SEUIL EST MESURÉ, sur une carte de 630 x 880 :
      · rien retiré ................................. couverture 1,00000
      · un cadre d'UN pixel retiré .................. couverture 0,99456
      · un sujet posé à 4 px du bord ................ couverture 0,97833
      · un sujet ovale ordinaire .................... couverture 0,52181
    Le plancher se pose donc à 0,995 : en dessous, il reste au moins le
    liséré d'un pixel de vrai retrait ; au-dessus, RIEN n'a été retiré nulle
    part. (Le chiffre est une PART, donc il dépend de la résolution : sur une
    trame au plafond d'import, un cadre d'un pixel ne pèse plus que 0,0008 —
    dit ici, parce qu'aucun détourage réel ne retire un seul pixel de bord.)"""
    s = _sentinelle(monkeypatch)
    assert CP.COUCHE_COUV_MAX == 0.995, CP.COUCHE_COUV_MAX
    intacte = Image.new("RGBA", (60, 80), (30, 30, 30, 255))
    buf = io.BytesIO()
    intacte.save(buf, format="PNG")
    _pose_rembg(monkeypatch, _FauxRembg(sortie=buf.getvalue()))
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 502, (r.status_code, r.text[:300])
    d = r.json()["detail"]
    assert "100" in d and "%" in d, f"le chiffre du refus manque : {d}"
    assert "99" in d or "0,995" in d or "99,5" in d, d
    assert not (CP.cap_dir(did) / "sujet_recto.png").exists()
    # ... et un détourage ORDINAIRE passe : le plancher ne mord pas sur lui.
    _pose_rembg(monkeypatch, _FauxRembg())
    assert _rembg(did).status_code == 200
    s.zero()
    CC.delete_deck(did)


def test_une_couche_ENTIEREMENT_TRANSPARENTE_est_REFUSEE(monkeypatch):
    """« Un détourage qui garde tout, ou rien, n'est pas un détourage » — la
    phrase est déjà celle du refus local (`_analyse_fond`). Une couche vide
    rangée en silence deviendrait l'illustration adoptée par P1 : une carte
    invisible, sans un mot."""
    s = _sentinelle(monkeypatch)
    _pose_rembg(monkeypatch, _FauxRembg(sortie=_png_rgba(opaque=False)))
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 502, (r.status_code, r.text[:300])
    assert "transparent" in r.json()["detail"].lower(), r.json()["detail"]
    assert not (CP.cap_dir(did) / "sujet_recto.png").exists()
    s.zero()
    CC.delete_deck(did)


def test_une_REPONSE_QUI_N_EST_PAS_UNE_IMAGE_est_refusee_SANS_500(monkeypatch):
    """Le fournisseur peut rendre du HTML, du JSON d'erreur, ou rien. Jamais
    500 (§8)."""
    s = _sentinelle(monkeypatch)
    _pose_rembg(monkeypatch, _FauxRembg(sortie=b"<html>oops</html>"))
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code != 500, r.text[:300]
    assert r.status_code == 502, (r.status_code, r.text[:300])
    s.zero()
    CC.delete_deck(did)


def test_la_COUCHE_SUJET_est_ECRITE_ATOMIQUEMENT_et_ne_laisse_pas_de_tmp(
        monkeypatch):
    """Le patron T1 : brouillon UNIQUE + `replace` patient. Deux détourages
    concurrents sur le même jeu ne doivent ni se disputer le fichier ni
    laisser un brouillon lisible par le GET."""
    s = _sentinelle(monkeypatch)
    _pose_rembg(monkeypatch, _FauxRembg())
    did = _deck_avec_recto()
    assert _rembg(did).status_code == 200
    assert _rembg(did).status_code == 200
    restes = [p.name for p in CP.cap_dir(did).iterdir()
              if p.name.endswith(".tmp")]
    assert restes == [], restes
    src = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    i = src.index("def _store_layer")
    corps = src[i:src.index("\ndef ", i + 10)]
    assert "_replace_avec_patience" in corps, corps[:600]
    assert "uuid" in corps, "le brouillon n'est pas nominatif (leçon T1)"
    s.zero()
    CC.delete_deck(did)


def test_un_NOUVEAU_RECTO_efface_la_couche_SUJET_du_DISQUE(monkeypatch):
    """`effacements("recto")` remet `layers` à vide DANS LE DOCUMENT — mais le
    PNG, lui, reste sur le disque et `GET /file/sujet_recto.png` continuerait
    de servir le sujet de la carte PRÉCÉDENTE. P1 l'adopterait sans que rien
    ne l'annonce."""
    s = _sentinelle(monkeypatch)
    _pose_rembg(monkeypatch, _FauxRembg())
    did = _deck_avec_recto()
    assert _rembg(did).status_code == 200
    assert (CP.cap_dir(did) / "sujet_recto.png").is_file()
    assert _post(did, _pngs(_synth(bord_px=10)), "recto").status_code == 200
    assert not (CP.cap_dir(did) / "sujet_recto.png").exists(), \
        "le sujet de la carte d'avant survit au remplacement du recto"
    # ... et un VERSO ne touche à rien (D3 amendé : l'analyse est du recto)
    assert _rembg(did).status_code == 200
    assert _post(did, _pngs(_synth()), "verso").status_code == 200
    assert (CP.cap_dir(did) / "sujet_recto.png").is_file()
    s.zero()
    CC.delete_deck(did)


def test_la_LISTE_BLANCHE_admet_le_sujet_et_RIEN_de_plus():
    """La liste blanche du service s'étend d'UN nom, pas d'un motif. Et le
    404 « fichier absent » doit nommer LE BON fichier : la première rédaction
    découpait `n[len("source_"):-4]`, ce qui rendait « cto » pour
    « sujet_recto.png »."""
    for bon in ("source_recto.png", "source_verso.png", "sujet_recto.png"):
        assert CP.FILE_RE.fullmatch(bon), bon
    for mauvais in ("sujet_verso.png", "sujet_recto.png.tmp", "sujet.png",
                    "sujet_recto.png\n", "../meta.json", "sujet_recto.PNG"):
        assert not CP.FILE_RE.fullmatch(mauvais), repr(mauvais)
    did = _deck()
    r = _get(did, "sujet_recto.png")
    assert r.status_code == 404, r.status_code
    d = r.json()["detail"]
    assert "cto" not in d.replace("recto", "").replace("Recto", ""), d
    assert "sujet" in d.lower(), d
    CC.delete_deck(did)


def test_le_detourage_ne_touche_a_AUCUN_document(monkeypatch):
    """D3 tenu jusqu'ici : la route range un PNG et RÉPOND. C'est la PIÈCE
    qui publie `doc.capture.layers.sujet` par la voie d'autosave unique."""
    s = _sentinelle(monkeypatch)
    _pose_rembg(monkeypatch, _FauxRembg())
    did = _deck_avec_recto()
    avant = json.dumps(CC.read_deck(did), sort_keys=True)
    assert _rembg(did).status_code == 200
    assert json.dumps(CC.read_deck(did), sort_keys=True) == avant, \
        "la route a écrit dans le document"
    s.zero()
    CC.delete_deck(did)


def test_le_DEPLIAGE_de_la_reponse_fal_lit_LES_DEUX_FORMES(monkeypatch):
    """LE SEUL MORCEAU DE CODE PAYANT QUE LES AUTRES CONTRÔLES N'EXÉCUTENT
    PAS : le corps de `_fal_rembg`. Ailleurs il est espionné en entier, donc
    son dépliage de réponse n'était joué nulle part — et c'est précisément
    l'endroit où un bug coûte un appel PAYÉ pour rien : la facture part, le
    résultat n'est pas lu.

    Ce fournisseur rend deux formes (`image.url` et `images[].url`), comme
    `sprite_service._rembg_api` le documente. Les deux sont jouées, plus le
    cas « aucune image ».

    LA PORTE `fal_client` EST OUVERTE ICI, ET C'EST LE SEUL TEST OÙ ELLE
    L'EST : `subscribe_async` est remplacé par un faux qui REND une réponse
    au lieu de lever. Les trois autres portes restent fermées sur le
    compteur — aucun octet ne part, aucun dollar non plus."""
    import fal_client
    s = _sentinelle(monkeypatch, sauf=("fal_client",))
    vu: list = []

    def canne(payload):
        async def _f(modele, arguments=None, **k):
            vu.append((modele, dict(arguments or {})))
            return payload
        return _f

    monkeypatch.setattr(fal_client, "subscribe_async",
                        canne({"image": {"url": "https://f/a.png"}}))
    assert asyncio.run(CP._fal_rembg("https://f/in.png")) == "https://f/a.png"
    assert vu == [(CP.REMBG_FAL_MODELE, {"image_url": "https://f/in.png"})], vu

    monkeypatch.setattr(fal_client, "subscribe_async",
                        canne({"images": [{}, {"url": "https://f/b.png"}]}))
    assert asyncio.run(CP._fal_rembg("https://f/in.png")) == "https://f/b.png"

    for creux in ({}, {"images": []}, {"image": {}}, None):
        with pytest.raises(Exception) as boom:
            monkeypatch.setattr(fal_client, "subscribe_async", canne(creux))
            asyncio.run(CP._fal_rembg("https://f/in.png"))
        assert "aucune image" in str(boom.value), (creux, boom.value)
    assert len(vu) == 6, vu
    s.zero()


def test_la_RELEVE_du_resultat_REFUSE_une_adresse_qui_n_est_pas_du_WEB(
        monkeypatch):
    """L'URL de sortie vient DU FOURNISSEUR, donc du dehors. `urlopen` sait
    ouvrir `file://` : sans garde, une réponse mal formée — ou hostile —
    ferait lire un fichier de cette machine et le rangerait comme « sujet »."""
    s = _sentinelle(monkeypatch)
    for mauvaise in ("file:///C:/Windows/win.ini", "ftp://x/y.png", "",
                     "/etc/passwd", "javascript:1"):
        with pytest.raises(Exception) as boom:
            asyncio.run(CP._fal_download(mauvaise))
        assert "adresse" in str(boom.value), (mauvaise, boom.value)
    s.zero()


def test_un_rembg_PRESENT_MAIS_CASSE_se_dit_AUTREMENT_qu_un_rembg_ABSENT(
        monkeypatch):
    """Les TROIS portes de `_rembg_local_dispo`, et la troisième est celle
    qu'aucune machine de ce chantier ne peut franchir toute seule (rembg y
    est absent). Elle se joue donc au point de CONSOMMATION : `find_spec`
    dit oui, l'import échoue. C'est la situation réelle d'un rembg installé
    sans son moteur ONNX — et « pas installé » serait alors un mauvais
    conseil : le paquet EST là, c'est sa dépendance qui manque."""
    import importlib
    import importlib.util
    _sans_rembg(monkeypatch)
    absent, motif = CP._rembg_local_dispo()
    assert absent is False and "pas installé" in motif, motif

    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda n, *a, **k: object() if n == "rembg" else None)
    monkeypatch.setattr(importlib, "import_module",
                        lambda n, *a, **k: (_ for _ in ()).throw(
                            ImportError("DLL load failed: onnxruntime")))
    casse, motif2 = CP._rembg_local_dispo()
    assert casse is False, "un rembg qui ne se charge pas est annoncé présent"
    assert "ne se charge pas" in motif2 and "onnxruntime" in motif2, motif2
    assert motif2 != motif, "les deux absences se disent de la même façon"


# ── C. l'écran P10 : le bloc « Détourage IA » ───────────────────────────────

def test_l_ecran_ne_PROPOSE_l_option_que_si_elle_EXISTE():
    """La règle de l'offre vit dans une fonction PURE, exécutée dans node —
    la leçon T1 : un contrôle qui lit du texte ne voit pas un `|| true`."""
    fn = (_fonction_js("isPlain") + _fonction_js("estNombre")
          + _fonction_js("num") + _fonction_js("offreIA"))
    cas = json.dumps([
        {"o": None, "recto": True},
        {"o": {"local": False, "fal": False, "voie": None,
               "motif": "ni l'un ni l'autre"}, "recto": True},
        {"o": {"local": False, "fal": True, "voie": "fal",
               "prix_usd": 0.003}, "recto": True},
        {"o": {"local": False, "fal": True, "voie": "fal",
               "prix_usd": 0.003}, "recto": False},
        {"o": {"local": True, "fal": False, "voie": "local",
               "gratuit": True}, "recto": True},
        {"o": {"local": False, "fal": True, "voie": "fal",
               "prix_usd": None}, "recto": True},
    ], ensure_ascii=False)
    sortie = _node(fn + f"""
      const cas = {cas};
      console.log(JSON.stringify(cas.map((c) => offreIA(c.o, c.recto))));
    """)
    rien, aucune, fal, sans_recto, local, sans_tarif = json.loads(sortie)
    assert rien["on"] is False, rien
    assert aucune["on"] is False and aucune["motif"], aucune
    assert fal["on"] is True and fal["voie"] == "fal", fal
    assert "0,003" in fal["libelle"] and "$" in fal["libelle"], fal["libelle"]
    assert "fal" in fal["libelle"], fal["libelle"]
    assert sans_recto["on"] is False, "pas de recto, pas de sujet à détourer"
    assert local["on"] is True and "gratuit" in local["libelle"], local
    assert "$" not in local["libelle"], local["libelle"]
    # SANS PRIX TABULÉ, LA VOIE PAYANTE N'EST PAS OFFERTE (§8 « prix AVANT »).
    # L'écran tient la même règle que la route — défense en profondeur : un
    # backend d'une version antérieure ne doit pas pouvoir faire naître un
    # bouton payant sans chiffre.
    assert sans_tarif["on"] is False, sans_tarif
    assert "tarif" in sans_tarif["motif"].lower(), sans_tarif
    assert "$" not in sans_tarif["libelle"], sans_tarif["libelle"]


def test_l_ecran_lit_les_OPTIONS_UNE_FOIS_et_pas_a_chaque_PEINTURE():
    """« lu d'ai-options au montage du panneau, pas à chaque frame » (T3-C).
    Une requête par repeinture ferait une rafale à chaque événement du
    document — et le prix clignoterait."""
    js = JS.read_text(encoding="utf-8")
    code = _code_js(js)
    assert code.count('"ai-options"') + code.count("'ai-options'") == 1, \
        "l'appel d'options est écrit à plusieurs endroits"
    for muet in ("paint", "mesures", "dessineBoites"):
        assert "ai-options" not in _corps_js(muet), \
            f"{muet}() interroge le backend à chaque peinture"
    assert "ai-options" in _corps_js("chargeOptions"), \
        "l'appel n'est pas isolé dans son chargeur"
    # `init` est une MÉTHODE du bloc `register` (« init(host) { »), pas une
    # `function` : on lit son bloc, pas une déclaration qui n'existe pas.
    i = js.index("init(host) {")
    assert "chargeOptions" in js[i:js.index("\n    },", i)], \
        "les options ne sont pas lues au montage du panneau"


def test_le_bloc_de_DETOURAGE_publie_la_couche_DANS_LE_DOCUMENT():
    """D3 : la route répond, la PIÈCE publie. Et le verrou BUSY est PARTAGÉ
    avec l'import et l'analyse — détourer pendant qu'un fichier monte
    détourerait l'image d'avant."""
    corps = _corps_js("detourer")
    assert re.search(r"if\s*\(\s*BUSY\s*\)", corps), corps[:400]
    assert "BUSY = true" in corps and "BUSY = false" in corps, corps[:400]
    assert "M.patch(" in corps, "la pièce ne publie pas"
    assert "layers" in corps, "la couche n'entre pas dans `layers`"
    assert "layers" in _cles_du_schema(), \
        "`layers` n'est pas dans le schéma : `patchAs` lèverait"


def test_le_REPEINT_d_un_changement_de_jeu_n_ATTEND_PAS_LE_RESEAU():
    """RÉGRESSION DE LA LIVRAISON, ÉPINGLÉE. `core:deck` passait de `paint()`
    à `chargeOptions()`, qui ATTEND un `fetch` nu (le `rawFetch` du CORE n'a
    pas de délai d'attente) AVANT de repeindre. Backend lent ou processus
    orphelin — le scénario documenté de ce dépôt — et le panneau montrait
    l'aperçu, les mesures ET LE SUJET du jeu PRÉCÉDENT, sans fin : exactement
    le défaut que `_oublie_sujet` venait de tuer côté serveur.

    L'ordre est donc : repeindre D'ABORD (ce qui est local et instantané),
    relire les options ENSUITE. Le contrôle porte sur l'ORDRE dans le code
    dépouillé — un `await` glissé entre les deux le ferait rougir."""
    code = _code_js(JS.read_text(encoding="utf-8"))
    i = code.index('CF.on("core:deck"')
    ligne = code[i:code.index("\n", i + 20)]
    assert "paint()" in ligne, \
        f"le changement de jeu ne repeint plus tout de suite : {ligne.strip()}"
    assert ligne.index("paint()") < ligne.index("chargeOptions"), \
        f"le repeint attend le réseau : {ligne.strip()}"
    assert "await" not in ligne, ligne.strip()


def test_le_PRIX_est_RELU_juste_avant_de_PAYER():
    """Le prix affiché pouvait ne plus être le prix rendu : les options sont
    lues au montage, et une table déplacée entre-temps (Réglages -> Tarifs)
    laissait le bouton sur l'ancien chiffre jusqu'à réouverture du panneau.
    Mesuré : table multipliée par 83, bouton inchangé.

    La relecture est GRATUITE et LOCALE (`/ai-options` ne parle à personne) :
    on la refait juste avant le POST, et si le chiffre a bougé, le POST NE
    PART PAS — le bouton se re-libelle et l'utilisateur re-consent d'un clic.
    Consentir à 0,003 $ et payer 0,25 $ est le genre de chose qui ne se
    rattrape pas après coup."""
    corps = _corps_js("detourer")
    assert "chargeOptions" in corps, \
        "le prix n'est pas relu avant l'appel payant"
    assert corps.index("chargeOptions") < corps.index('"rembg"'), \
        "la relecture arrive APRÈS le POST : elle ne protège rien"
    assert "return" in corps[corps.index("chargeOptions"):
                             corps.index('"rembg"')], \
        "un prix qui a bougé n'arrête pas le geste"


def test_le_NOM_de_la_couche_est_une_COPIE_AVOUEE_et_FILTREE():
    """Deux mineurs de la ronde, et ils tiennent ensemble. (1) Le nom
    `sujet_recto.png` est une TROISIÈME copie du même identifiant (capture.py
    et mod-face.js portent les deux autres) : la règle 8 veut qu'une copie
    soit AVOUÉE là où elle est écrite. (2) L'écran fabrique une URL avec le
    nom que le DOCUMENT lui donne — il doit le filtrer comme P1 le fait, et
    non lui faire confiance parce qu'il vient « de chez nous »."""
    js = JS.read_text(encoding="utf-8")
    i = js.index('"sujet_recto.png"')
    autour = js[max(0, i - 900):i]
    assert re.search(r"recopi|copie|règle 8|regle 8|miroir", autour, re.I), \
        "la copie du nom de couche n'est pas avouée"
    m = re.search(r"^\s*const CAPTURE_FILE_RE = (.*);\s*$", js, re.M)
    assert m, "l'écran n'a pas de liste blanche pour les noms du document"
    corps = _corps_js("blocIA")
    assert "CAPTURE_FILE_RE" in corps or "fichierSujet" in corps, \
        "blocIA fabrique une URL sans filtrer le nom venu du document"
    # LA GARDE EST EXÉCUTÉE, pas cherchée : même standard que P1.
    sortie = _node(
        m.group(0) + "\n"
        + _fonction_js("isPlain") + _fonction_js("fichierSujet") + """
        console.log(JSON.stringify([
          fichierSujet({file: "sujet_recto.png"}),
          fichierSujet({file: "../meta.json"}),
          fichierSujet({file: "sujet_recto.png\\n"}),
          fichierSujet({}), fichierSujet(null), fichierSujet("x"),
        ]));
        """)
    bon, trav, saut, vide, nul, pas_objet = json.loads(sortie)
    assert bon == "sujet_recto.png", bon
    for mauvais in (trav, saut, vide, nul, pas_objet):
        assert mauvais == "", mauvais


def test_le_refus_du_fond_POINTE_vers_le_bloc_de_detourage():
    """Clôture T2 : « la phrase option_ia promet le prix que T3 apporte ». La
    promesse doit maintenant AVOIR une suite visible à l'écran — sinon elle
    envoie chercher une option qui n'est nulle part."""
    js = JS.read_text(encoding="utf-8")
    assert "cf-capture-ia" in js, "aucun bloc d'écran pour le détourage IA"
    assert "option_ia" in _corps_js("lignesFond"), \
        "la phrase de refus n'est plus reliée au bloc"


# ── D. P1 « adopter l'illustration » (mod-face.js) ──────────────────────────

FACE_JS = REPO / "frontend" / "cardforge" / "js" / "mod-face.js"
TYPE_JS = REPO / "frontend" / "cardforge" / "js" / "mod-type.js"


def _fonction_de(chemin: pathlib.Path, nom: str) -> str:
    """La même extraction que `_fonction_js`, mais sur le fichier d'une
    pièce VOISINE. Les adoptions vivent chez l'adoptant (D6) : leurs règles
    ne sont pas dans mod-capture.js, et c'est le contrat de P10 qu'elles
    consomment — d'où leur contrôle ICI."""
    js = chemin.read_text(encoding="utf-8")
    i = js.index("function " + nom + "(")
    j = js.index("\n  }", i)
    return js[i:j] + "\n  }\n"


def test_P1_ADOPTER_est_DERIVE_de_doc_capture_et_dit_SA_SOURCE():
    """§7.1.5 : « le sujet (ou le recadrage art) devient la pose ». La règle
    est PURE et exécutée : un bouton d'adoption sans matière à adopter
    n'existe pas (patron sectionsBasses, D6), et celui qui existe DIT ce
    qu'il va prendre — le sujet détouré, ou le recto entier."""
    fn = _fonction_de(FACE_JS, "adoptionCapture")
    cas = json.dumps([
        {},
        {"capture": {}},
        {"capture": {"sources": {"verso": {"stamp": 3}}}},
        {"capture": {"sources": {"recto": {"stamp": 7}}}},
        {"capture": {"sources": {"recto": {"stamp": 7}},
                     "layers": {"sujet": {"file": "sujet_recto.png",
                                          "stamp": 9}}}},
        {"capture": {"layers": {"sujet": "pas un objet"},
                     "sources": {"recto": {"stamp": 7}}}},
        {"capture": {"layers": {"sujet": {"file": "../meta.json"}},
                     "sources": {"recto": {"stamp": 7}}}},
    ], ensure_ascii=False)
    sortie = _node(fn + f"""
      const cas = {cas};
      console.log(JSON.stringify(cas.map((d) => adoptionCapture(d))));
    """)
    (vide, sans, verso, recto, sujet, sale, traversee) = json.loads(sortie)
    assert vide is None and sans is None, (vide, sans)
    assert verso is None, "le verso n'est pas une illustration de recto"
    assert recto and recto["nom"] == "source_recto.png", recto
    assert recto["sujet"] is False, recto
    assert "recto entier" in recto["libelle"], recto["libelle"]
    assert sujet and sujet["nom"] == "sujet_recto.png", sujet
    assert sujet["sujet"] is True and sujet["stamp"] == 9, sujet
    assert "sujet" in sujet["libelle"] and "détour" in sujet["libelle"], sujet
    assert sale and sale["nom"] == "source_recto.png", \
        "une couche mal formée doit retomber sur le recto, pas casser"
    assert traversee and traversee["nom"] == "source_recto.png", \
        "un nom de fichier venu du document n'est pas un chemin"


def test_P1_ADOPTER_passe_par_l_import_EXISTANT_et_ne_cree_PAS_de_4e_schema():
    """D6 : « adopter = importer les octets du sujet dans la pile P1 puis
    `setArt("local:"+clé)` ». Un quatrième schéma (`capture:…`) aurait doublé
    `artSource`, le cache d'images, la vignette et la suppression."""
    js = FACE_JS.read_text(encoding="utf-8")
    corps = _fonction_de(FACE_JS, "adopterCapture")
    assert "importFiles(" in corps, "l'import ne passe pas par le mécanisme " \
                                    "existant"
    assert "afterImport(" in corps, "la pose ne passe pas par afterImport"
    assert "setArt(" not in corps, \
        "setArt est appelé DEUX fois (afterImport le fait déjà) : deux pas " \
        "d'annulation pour un geste"
    code = _code_js(js)
    assert 'indexOf("capture:")' not in code and "capture:" not in code, \
        "un quatrième schéma de source est né"
    # LE BOUTON EST DÉRIVÉ DANS LA PEINTURE, ET CÂBLÉ SOUS GARDE. Un
    # `q("#cf-face-adopt").addEventListener(...)` sans garde — le style de
    # tous ses voisins, qui eux existent toujours — ferait tomber TOUT le
    # panneau de P1 dès qu'il n'y a rien à adopter, c'est-à-dire dans le cas
    # ordinaire. C'est la classe de défaut la plus chère de cette adoption.
    assert 'id="cf-face-adopt"' in js, "le bouton n'est pas dans le panneau"
    assert re.search(r'const adopt = adoptionCapture\(CF\.doc\(\)\);', code), \
        "la dérivation ne se refait pas à chaque peinture"
    assert re.search(r'const adopt = q\("#cf-face-adopt"\);\s*\n\s*if \(adopt\)',
                     code), "le câblage du bouton n'est pas gardé"


BANC_ALPHA = r"""
/* Une toile de paille A QUATRE CANAUX. Ce banc ne juge pas une mise en page :
   il juge des OCTETS D'ALPHA. `drawImage` compose en `source-over`, comme un
   vrai contexte 2D — c'est ce qui rend la mutation visible : un `fillRect`
   opaque posé AVANT le dessin donne un fond alpha 255, et le sujet composé
   par-dessus ne redevient jamais transparent. */
function toile(w, h) {
  const px = new Uint8ClampedArray(w * h * 4);          /* tout à zéro */
  const ctx = {
    fillStyle: "#000000", globalAlpha: 1, imageSmoothingEnabled: true,
    save() { }, restore() { }, translate() { }, rotate() { }, setTransform() { },
    clearRect(x, y, cw, ch) { for (let i = 0; i < px.length; i++) px[i] = 0; },
    fillRect(x, y, cw, ch) {
      const c = coul(ctx.fillStyle);
      for (let j = y; j < y + ch; j++) {
        for (let i = x; i < x + cw; i++) melange(px, (j * w + i) * 4, c);
      }
    },
    drawImage(im) {
      for (let j = 0; j < Math.min(h, im.h); j++) {
        for (let i = 0; i < Math.min(w, im.w); i++) {
          const s = (j * im.w + i) * 4;
          melange(px, (j * w + i) * 4,
            [im.px[s], im.px[s + 1], im.px[s + 2], im.px[s + 3] / 255]);
        }
      }
    },
  };
  return { width: w, height: h, getContext: () => ctx, _px: px,
    toBlob(cb) { cb({ type: "image/png", size: px.length, _px: px }); } };
}
function coul(s) {
  const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(String(s));
  return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16), 1]
    : [255, 255, 255, 1];
}
/* source-over : a_out = a_src + a_dst * (1 - a_src) */
function melange(px, o, c) {
  const as = c[3], ad = px[o + 3] / 255, ao = as + ad * (1 - as);
  if (ao <= 0) { px[o] = px[o + 1] = px[o + 2] = px[o + 3] = 0; return; }
  px[o] = (c[0] * as + px[o] * ad * (1 - as)) / ao;
  px[o + 1] = (c[1] * as + px[o + 1] * ad * (1 - as)) / ao;
  px[o + 2] = (c[2] * as + px[o + 2] * ad * (1 - as)) / ao;
  px[o + 3] = Math.round(ao * 255);
}
globalThis.document = { createElement: () => toile(1, 1) };
function newCanvas(w, h) { return toile(w, h); }
"""


def test_P1_le_TRANSFERT_DES_OCTETS_garde_l_ALPHA_qu_on_vient_de_payer():
    """TÉMOIN FERMÉ (ronde) : `imageBlob` n'était jouée NULLE PART. C'est
    pourtant la fonction dont TOUT le métier tient en une phrase — garder
    l'alpha qu'on vient de payer — et un `fillRect` blanc posé avant le
    dessin la rendrait opaque sans faire bouger un seul contrôle. Une couche
    « sujet » recomposée sur du blanc, adoptée par P1, redonne exactement la
    carte de départ : la dépense pour rien, en silence.

    La fonction est donc EXÉCUTÉE, sur une toile de paille à quatre canaux
    qui compose en `source-over` comme un vrai contexte 2D."""
    src = BANC_ALPHA + _fonction_de(FACE_JS, "imageBlob")
    sortie = _node(src + """
      /* 4 x 3 : deux colonnes opaques, deux transparentes. */
      const w = 4, h = 3, px = new Uint8ClampedArray(w * h * 4);
      for (let j = 0; j < h; j++) {
        for (let i = 0; i < w; i++) {
          const o = (j * w + i) * 4;
          px[o] = 200; px[o + 1] = 180; px[o + 2] = 120;
          px[o + 3] = (i < 2) ? 255 : 0;
        }
      }
      imageBlob({ naturalWidth: w, naturalHeight: h, w: w, h: h, px: px })
        .then((b) => {
          const a = [];
          for (let k = 3; k < b._px.length; k += 4) a.push(b._px[k]);
          console.log(JSON.stringify({ type: b.type, alpha: a }));
        })
        .catch((e) => { console.log(JSON.stringify({ err: String(e) })); });
    """)
    d = json.loads(sortie)
    assert "err" not in d, d
    assert d["type"] == "image/png", d
    # DEUX COLONNES SUR QUATRE RESTENT PARFAITEMENT TRANSPARENTES.
    assert d["alpha"] == [255, 255, 0, 0, 255, 255, 0, 0, 255, 255, 0, 0], \
        f"l'alpha n'a pas survécu au transfert : {d['alpha']}"
    assert 0 in d["alpha"], "plus aucun pixel transparent : le sujet est un carré"
    # ... et une image sans taille est refusée plutôt que rendue vide.
    vide = _node(src + """
      imageBlob({ naturalWidth: 0, naturalHeight: 0 })
        .then(() => console.log('"passe"'))
        .catch((e) => console.log(JSON.stringify(String(e.message || e))));
    """)
    assert "illisible" in json.loads(vide), vide


def test_P1_ADOPTER_DEUX_FOIS_ne_pollue_pas_la_pile_EN_SILENCE():
    """Adopter deux fois de suite posait DEUX entrées identiques dans la pile
    (mesuré). Le remède est le plus petit qui soit honnête : si la pile porte
    déjà cette adoption — même nom, mêmes pixels, mêmes octets — on ne
    ré-importe pas, on RE-POSE celle qui est là, et on le DIT.

    L'IDENTITÉ EST JUGÉE SUR (nom, largeur, hauteur, octets) et pas sur les
    octets eux-mêmes : c'est avoué ici. Le blob sort du même encodeur pour la
    même source, donc la taille est stable ; deux sujets réellement
    différents qui tomberaient sur les mêmes quatre nombres sont un cas que
    ce contrôle ne couvre pas, et il ne prétend pas le couvrir."""
    corps = _fonction_de(FACE_JS, "adopterCapture")
    assert "dejaDansLaPile" in corps, "aucune détection de doublon"
    fn = _fonction_de(FACE_JS, "dejaDansLaPile")
    sortie = _node(fn + """
      const pile = [
        { key: "a1", name: "sujet_detoure.png", w: 630, h: 880, bytes: 4242 },
        { key: "b2", name: "carte_importee.png", w: 630, h: 880, bytes: 9000 },
      ];
      const t = (rec) => { const r = dejaDansLaPile(pile, rec); return r ? r.key : null; };
      console.log(JSON.stringify([
        t({ name: "sujet_detoure.png", w: 630, h: 880, bytes: 4242 }),
        t({ name: "carte_importee.png", w: 630, h: 880, bytes: 9000 }),
        t({ name: "sujet_detoure.png", w: 630, h: 880, bytes: 4243 }),
        t({ name: "sujet_detoure.png", w: 629, h: 880, bytes: 4242 }),
        t({ name: "autre.png", w: 630, h: 880, bytes: 4242 }),
      ]));
    """)
    memes, autre, octets, taille, nom = json.loads(sortie)
    assert memes == "a1" and autre == "b2", (memes, autre)
    assert octets is None and taille is None and nom is None, \
        (octets, taille, nom)
    # ... et l'écran le dit au lieu de faire comme si de rien n'était.
    chaines = " ".join(_chaines_js(FACE_JS.read_text(encoding="utf-8")))
    assert "déjà dans la pile" in chaines, \
        "le doublon est sauté en silence — le pire des deux"


def test_P1_ADOPTER_ne_pese_QU_UN_pas_d_annulation():
    """« UN pas d'undo » (T3-D). `afterImport` -> `setArt` -> `pushUndo` :
    exactement un. Un `pushUndo` de plus sur le chemin d'adoption obligerait
    à annuler deux fois un geste unique."""
    corps = _fonction_de(FACE_JS, "adopterCapture")
    assert "pushUndo" not in corps, corps


def test_P1_ADOPTER_ne_sort_pas_du_domaine_de_la_piece():
    """Règle 8 côté écran : `M.api` d'une pièce est CONFINÉ à son préfixe —
    P1 ne peut donc pas s'en servir pour lire un fichier de P10. L'URL est
    donc construite à la main, et les deux morceaux qui viennent du DOCUMENT
    sont gardés : le nom par la liste blanche de P10 (recopiée, règle 8),
    l'identifiant de jeu par sa forme.

    LA GARDE EST EXÉCUTÉE, pas cherchée dans le texte : la première écriture
    de ce contrôle acceptait n'importe quel `…test(…)` du corps — donc aussi
    celui de l'identifiant — et une liste blanche retirée l'aurait laissé
    vert (mesuré)."""
    js = FACE_JS.read_text(encoding="utf-8")
    m = re.search(r"^\s*const CAPTURE_FILE_RE = .*$", js, re.M)
    assert m, "la liste blanche recopiée de P10 a disparu de mod-face.js"
    src = (m.group(0) + "\n" + _fonction_de(FACE_JS, "captureURL"))
    sortie = _node(
        "const CF = { doc: () => ({ id: 'deck_12345678' }) };\n" + src + """
        console.log(JSON.stringify([
          captureURL("source_recto.png"), captureURL("sujet_recto.png"),
          captureURL("../meta.json"), captureURL("source_recto.png\\n"),
          captureURL("sujet_recto.png.tmp"), captureURL(""), captureURL(null),
        ]));
        """)
    recto, sujet, trav, saut, tmp, vide, nul = json.loads(sortie)
    assert recto == "/api/cards/deck_12345678/capture/file/source_recto.png", recto
    assert sujet == "/api/cards/deck_12345678/capture/file/sujet_recto.png", sujet
    for mauvais, quoi in ((trav, "traversée"), (saut, "saut de ligne final"),
                          (tmp, "brouillon d'écriture"), (vide, "nom vide"),
                          (nul, "nom absent")):
        assert mauvais == "", f"{quoi} : {mauvais!r} devient une URL"
    # ... et le jeu lui-même est une FORME, pas une chaîne quelconque.
    sale = _node(
        "const CF = { doc: () => ({ id: '../../etc' }) };\n" + src
        + 'console.log(JSON.stringify(captureURL("source_recto.png")));')
    assert json.loads(sale) == "", sale


def test_DOUZE_DETOURAGES_SIMULTANES_ne_paient_QU_UNE_FOIS(monkeypatch):
    """LE CONTRAT A CHANGÉ, ET C'EST UNE CORRECTION DE FOND. La première
    rédaction gravait l'inverse : « au moins n-1 réponses 200 », c'est-à-dire
    DOUZE FACTURES pour un double-clic ou deux onglets — mesuré, 12 requêtes
    simultanées donnaient 12 invocations du fournisseur et 11 résultats jetés.
    Un plancher de service qui compte les paiements n'est pas un plancher de
    service.

    Les POST concurrents sur un MÊME jeu se COALESCENT : un seul appel part,
    tous les demandeurs sont servis du même résultat. Ce qui reste de T1 est
    intact — jamais 500, fichier final entier, aucun brouillon abandonné.

    CE QUI N'EST PAS COALESCÉ, ET POURQUOI : deux clics SÉPARÉS dans le temps.
    Un « Redétourer » est une demande explicite ; mettre le résultat en cache
    empêcherait de relancer après un changement de recto, et rendrait le
    bouton menteur. La coalescence protège de l'accident (le double-clic, les
    deux onglets), pas de l'intention."""
    s = _sentinelle(monkeypatch)
    faux = _pose_rembg(monkeypatch, _FauxRembg(pause=0.20))
    did = _deck_avec_recto()
    n = 12
    reps = _en_parallele([("POST", f"/api/cards/{did}/capture/rembg", {})] * n)
    codes: dict = {}
    for r in reps:
        codes[r.status_code] = codes.get(r.status_code, 0) + 1
    assert codes == {200: n}, codes
    assert faux.appels == 1, \
        (f"{faux.appels} invocations du fournisseur pour {n} clics : "
         f"{faux.appels - 1} facture(s) de trop")
    # TOUS SERVIS DU MÊME RÉSULTAT — même couche, même horodatage.
    corps = [r.json() for r in reps]
    assert len({c["stamp"] for c in corps}) == 1, [c["stamp"] for c in corps]
    assert len({c["bytes"] for c in corps}) == 1, corps[0]
    # ... et UN SEUL a réellement payé : les autres le disent.
    payeurs = [c for c in corps if c.get("coalesce") is False]
    assert len(payeurs) == 1, [c.get("coalesce") for c in corps]
    # LE FICHIER FINAL EST ENTIER — un brouillon partagé le laisserait tronqué.
    with Image.open(CP.cap_dir(did) / "sujet_recto.png") as im:
        im.load()
        assert im.mode == "RGBA", im.mode
    assert [p.name for p in CP.cap_dir(did).iterdir()
            if p.name.endswith(".tmp")] == []
    # DEUX JEUX NE SE COALESCENT PAS ENSEMBLE : la clé est le jeu.
    did2 = _deck_avec_recto()
    reps2 = _en_parallele(
        [("POST", f"/api/cards/{d}/capture/rembg", {}) for d in (did, did2)])
    assert [r.status_code for r in reps2] == [200, 200], reps2
    assert faux.appels == 3, faux.appels
    # ... ET UN ÉCHEC SE PARTAGE AUSSI : personne ne repart avec un faux succès.
    faux2 = _pose_rembg(monkeypatch,
                        _FauxRembg(casse=RuntimeError("modèle absent"),
                                   pause=0.20))
    mauvais = _en_parallele(
        [("POST", f"/api/cards/{did}/capture/rembg", {})] * 4)
    assert {r.status_code for r in mauvais} == {502}, \
        [r.status_code for r in mauvais]
    assert faux2.appels == 1, faux2.appels
    s.zero()
    CC.delete_deck(did)
    CC.delete_deck(did2)


def test_UN_CLIC_APRES_L_AUTRE_paie_bien_DEUX_FOIS_et_c_est_voulu(monkeypatch):
    """Le revers de la coalescence, épinglé pour qu'il reste un CHOIX. Deux
    demandes séparées sont deux demandes : la seconde relance le fournisseur.
    Si un jour quelqu'un veut un cache, ce contrôle le lui dira en face."""
    s = _sentinelle(monkeypatch)
    faux = _pose_rembg(monkeypatch, _FauxRembg())
    did = _deck_avec_recto()
    assert _rembg(did).status_code == 200
    assert _rembg(did).status_code == 200
    assert faux.appels == 2, faux.appels
    s.zero()
    CC.delete_deck(did)


def test_la_REPONSE_du_fournisseur_est_PLAFONNEE_EN_OCTETS(monkeypatch):
    """« 502 trop grande » ne parlait que des PIXELS, et il était contrôlé
    APRÈS que tout soit en mémoire : `urlopen().read()` sans borne ramenait
    d'abord l'intégralité de ce que le fournisseur voulait bien envoyer. Le
    plafond est le MÊME que celui de l'admission (`SRC_MAX_BYTES`) : ce qui
    entre par une route ou par l'autre pèse pareil.

    LA PORTE `urlopen` EST OUVERTE ICI, ET SUR UN FAUX QUI NE SORT PAS DE LA
    MACHINE : il rend des octets depuis la mémoire. Les autres portes restent
    fermées sur le compteur."""
    import urllib.request
    s = _sentinelle(monkeypatch, sauf=("urlopen",))
    monkeypatch.setattr(CP, "SRC_MAX_BYTES", 2048)
    lus: list = []

    class _Faux:
        def __init__(self, taille):
            self._d = b"x" * taille
        def read(self, n=None):
            lus.append(n)
            return self._d if n is None else self._d[:n]
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda u, timeout=None: _Faux(4096))
    with pytest.raises(Exception) as boom:
        asyncio.run(CP._fal_download("https://f/x.png"))
    assert "lourde" in str(boom.value) or "octets" in str(boom.value), boom.value
    # LA BORNE EST DEMANDÉE À LA LECTURE, pas mesurée après coup.
    assert lus and lus[0] is not None and lus[0] <= CP.SRC_MAX_BYTES + 1, lus
    # ... et une réponse de taille normale passe.
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda u, timeout=None: _Faux(100))
    assert asyncio.run(CP._fal_download("https://f/x.png")) == b"x" * 100
    s.zero()


def test_la_RELEVE_refuse_une_destination_LOCALE_ou_PRIVEE(monkeypatch):
    """LA GARDE CONTRÔLAIT LE SCHÉMA, PAS LA DESTINATION — et son propre
    docstring valait mot pour mot contre elle : `http://127.0.0.1:8765/api/…`
    passait, alors que l'API locale de cette application n'a AUCUNE
    authentification. Une réponse de fournisseur mal formée, ou hostile,
    désignait donc le backend de l'utilisateur.

    Les IP LITTÉRALES sont jugées (loopback, privées, lien-local, réservées) ;
    `localhost` aussi, par son nom. Ce qui n'est PAS fait, et c'est dit : on
    ne RÉSOUT aucun nom — une résolution DNS est un appel réseau, et ce banc
    n'en fait aucun. Un nom public qui pointerait vers 127.0.0.1 passerait
    donc ; c'est une limite connue, pas un oubli."""
    LE_MOT_JUSTE = (
        ("http://127.0.0.1:8765/api/settings", "boucle locale"),
        ("http://localhost:8765/api/settings", "localhost"),
        ("https://LOCALHOST/x.png", "localhost"),
        ("http://[::1]/x.png", "boucle locale"),
        ("http://192.168.1.10/x.png", "réseau privé"),
        ("http://10.0.0.5/x.png", "réseau privé"),
        ("http://172.16.4.4/x.png", "réseau privé"),
        ("http://169.254.169.254/latest/meta-data", "lien-local"),
        ("http://0.0.0.0/x.png", "réservée"),
    )
    s = _sentinelle(monkeypatch)
    for mauvaise, attendu in LE_MOT_JUSTE:
        with pytest.raises(Exception) as boom:
            asyncio.run(CP._fal_download(mauvaise))
        dit = str(boom.value).lower()
        assert "destination" in dit, (mauvaise, boom.value)
        # LE MOT JUSTE, ET PAS SEULEMENT LE REFUS. `ipaddress` range la boucle
        # locale, le lien-local et 0.0.0.0 DANS les réseaux privés : un ordre
        # de branches inversé refuserait pareil mais dirait « un réseau privé
        # (127.0.0.1) » — et c'est le diagnostic qui apprend à l'utilisateur
        # où sa réponse voulait aller. Sans ce contrôle, retirer la branche
        # « boucle locale » ne faisait rougir personne (mesuré).
        assert attendu in dit, (mauvaise, attendu, boom.value)
    s.zero()


def test_la_couche_SUJET_herite_de_la_REDUCTION_d_admission(monkeypatch):
    """Le recto est ramené à `MAX_IMPORT_PX` à l'admission ; le sujet, lui,
    ressortait à la taille que le fournisseur voulait bien rendre. Un scan de
    6000 px donnait donc un recto de 4096 et un sujet de 6000 — deux tailles
    pour la même carte, et P1 adoptant la plus lourde des deux.

    Le plafond est monkeypatché bas pour que le contrôle coûte des pixels et
    pas des mégaoctets : ce qu'il prouve est que la constante EST consultée
    au moment de ranger."""
    s = _sentinelle(monkeypatch)
    monkeypatch.setattr(CP, "MAX_IMPORT_PX", 64)
    _pose_rembg(monkeypatch, _FauxRembg(sortie=_png_rgba(200, 160)))
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 200, r.text[:300]
    j = r.json()
    assert max(j["w"], j["h"]) == 64, (j["w"], j["h"])
    assert (j["w"], j["h"]) == (64, 51), (j["w"], j["h"])
    # L'ALPHA SURVIT À LA RÉDUCTION — c'est tout l'objet de la couche.
    with Image.open(CP.cap_dir(did) / "sujet_recto.png") as im:
        assert im.mode == "RGBA" and im.getchannel("A").getextrema()[0] == 0
    src = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    i = src.index("def _store_layer")
    assert "MAX_IMPORT_PX" in src[i:src.index("\ndef ", i + 10)]
    s.zero()
    CC.delete_deck(did)


def test_une_couche_TROP_GRANDE_EN_PIXELS_est_refusee_AVEC_SON_COMPTE(
        monkeypatch):
    """TÉMOIN FERMÉ (ronde) : `IMG_MAX_PIXELS` multiplié par dix mille dans
    `_store_layer` SURVIVAIT à toute la suite. Le plafond de trame vaut pour
    ce qui entre par le fournisseur exactement comme pour ce qui entre par
    l'admission — c'est le même demi-gigaoctet de tampon."""
    s = _sentinelle(monkeypatch)
    bombe = _bombe_png(8000, 5000)              # 40 Mpx : au-delà des 33,5
    assert 8000 * 5000 > CP.IMG_MAX_PIXELS
    _pose_rembg(monkeypatch, _FauxRembg(sortie=bombe))
    did = _deck_avec_recto()
    r = _rembg(did)
    assert r.status_code == 502, (r.status_code, r.text[:300])
    d = r.json()["detail"]
    assert "40" in d and "pixel" in d.lower(), d
    assert "rembg" in d.lower(), "le préfixe de fournisseur a disparu"
    assert not (CP.cap_dir(did) / "sujet_recto.png").exists()
    s.zero()
    CC.delete_deck(did)


def test_une_ECRITURE_DE_COUCHE_REFUSEE_rend_409_NOMME(monkeypatch):
    """TÉMOIN FERMÉ (ronde) : le code 409 de l'échec d'écriture pouvait
    devenir 418 sans faire rougir personne. Le disque plein, le fichier tenu
    par un antivirus, le dossier en lecture seule : un refus nommé, pas une
    trace de pile — et pas de brouillon laissé derrière."""
    s = _sentinelle(monkeypatch)
    _pose_rembg(monkeypatch, _FauxRembg())
    # LE RECTO D'ABORD : `_store_image` passe par le même remplacement, et le
    # casser avant le dépôt ferait échouer l'admission au lieu de la couche.
    did = _deck_avec_recto()

    def _plein(tmp, final):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(CP, "_replace_avec_patience", _plein)
    r = _rembg(did)
    assert r.status_code == 409, (r.status_code, r.text[:300])
    d = r.json()["detail"]
    assert "couche" in d.lower() and "No space left" in d, d
    assert ":\\" not in d and "Users" not in d, d
    assert [p.name for p in CP.cap_dir(did).iterdir()
            if p.name.endswith(".tmp")] == [], "un brouillon est resté"
    s.zero()
    CC.delete_deck(did)


def test_le_NETTOYAGE_de_chemin_couvre_AUSSI_UNC_et_le_tilde():
    """`_sans_chemin` connaissait `C:\\…` et `/home/…`. Deux formes
    manquaient, et ce sont celles d'un poste d'entreprise : le chemin UNC
    (`\\\\serveur\\partage\\…`, qui porte un nom de machine ET un nom de
    partage) et le raccourci `~/` (qui se développe en nom de compte dès
    qu'un outil l'affiche)."""
    assert "olivi" not in CP._sans_chemin(
        FileNotFoundError(r"Image not found: C:\Users\olivi\jeu\x.png"))
    for brut, interdit in (
            (r"cannot open \\SRV-PAIE\partage\cartes\recto.png", "SRV-PAIE"),
            (r"open ~/Documents/DeepotusVideoGen/decks/x.png", "Documents"),
            ("no such file: /home/olivi/decks/x.png", "olivi"),
            ("no such file: /Users/olivi/decks/x.png", "olivi")):
        net = CP._sans_chemin(RuntimeError(brut))
        assert interdit not in net, (brut, net)
        assert "…" in net, (brut, net)
    # ... et ce qui APPREND quelque chose survit au nettoyage.
    assert "Image not found" in CP._sans_chemin(
        FileNotFoundError(r"Image not found: C:\Users\olivi\x.png"))


# ── C. l'écran P10 : le bloc « Détourage IA » ───────────────────────────────


# ── E. P3 « adopter les zones » (mod-type.js) ───────────────────────────────

def test_P3_les_ZONES_deviennent_des_SLOTS_avec_les_MM_de_P10():
    """§7.1.5 : « boîtes -> slots de gabarit (éditables ensuite, §6.1) ». Les
    millimètres de T2 sont DÉJÀ dans le repère de la carte (une unité par
    frontière) : ils se reprennent tels quels, sans conversion."""
    fn = _fonction_de(TYPE_JS, "specsZones")
    doc = json.dumps({"capture": {"boxes": [
        {"x": 8.0, "y": 6.0, "w": 47.0, "h": 7.0, "tronquee": False},
        {"x": 8.0, "y": 62.0, "w": 47.0, "h": 15.0, "tronquee": True},
        {"x": 6.0, "y": 20.0, "w": 9.0, "h": 9.0},
    ]}}, ensure_ascii=False)
    sortie = _node(fn + f"""
      console.log(JSON.stringify(specsZones({doc}, 1)));
    """)
    specs = json.loads(sortie)
    assert len(specs) == 3, specs
    assert [s["id"] for s in specs] == ["zone1", "zone2", "zone3"], specs
    assert specs[0]["label"] == "zone importée n°1", specs[0]
    assert specs[0]["box"] == [8.0, 6.0, 47.0, 7.0], specs[0]
    assert specs[1]["box"] == [8.0, 62.0, 47.0, 15.0], specs[1]
    for s in specs:
        assert s.get("kind", "text") == "text", s
        assert s.get("text", "") == "", "un texte inventé se peindrait"


def test_P3_les_ZONES_sont_LUES_avec_TOLERANCE():
    """Dérivation PURE de `doc.capture.boxes` (D6). Un document sans P10, une
    liste absente, une boîte qui n'est pas un objet, une mesure qui n'est pas
    un nombre : rien de tout cela ne doit faire naître un slot faux."""
    fn = _fonction_de(TYPE_JS, "specsZones")
    cas = json.dumps([
        {},
        {"capture": {}},
        {"capture": {"boxes": "trois"}},
        {"capture": {"boxes": []}},
        {"capture": {"boxes": [None, 3, {"x": 1}, {"x": 1, "y": 2, "w": 0,
                                                   "h": 5}]}},
        {"capture": {"boxes": [{"x": 1, "y": 2, "w": 3, "h": 4}]}},
    ], ensure_ascii=False)
    sortie = _node(fn + f"""
      const cas = {cas};
      console.log(JSON.stringify(cas.map((d) => specsZones(d, 1).length)));
    """)
    assert json.loads(sortie) == [0, 0, 0, 0, 0, 1], sortie


def test_P3_l_AVEU_des_TRONQUEES_suit_l_adoption():
    """Clôture T2, leçon (a) : « une coupe qui ne se dit pas devient une
    fausse mesure chez l'adoptant ». Les boîtes `tronquee` sont ADOPTÉES —
    elles sont éditables — mais le compte se dit."""
    fn = _fonction_de(TYPE_JS, "phraseZones")
    sortie = _node(fn + """
      console.log(JSON.stringify([phraseZones(3, 0, 0), phraseZones(3, 2, 0),
                                  phraseZones(1, 1, 0), phraseZones(3, 0, 3),
                                  phraseZones(3, 2, 1)]));
    """)
    sans, avec, une, redite, tout = json.loads(sortie)
    assert "3" in sans and "tronqu" not in sans, sans
    assert "3" in avec and "2" in avec and "tronqu" in avec, avec
    assert "tronqu" in une, une
    # ADOPTER DEUX FOIS EMPILE DES SLOTS SUPERPOSÉS. Le remède minimal, et le
    # seul qui ne décide pas à la place de l'utilisateur : le DIRE.
    assert "déjà" in redite and "3" in redite, redite
    assert "déjà" not in sans, sans
    assert "tronqu" in tout and "déjà" in tout, tout


def test_P3_ADOPTER_naît_EN_UN_SEUL_APPEL_donc_UN_pas_d_annulation():
    """`naitre(specs, quoi)` est la naissance ATOMIQUE multi-slots de P3 : un
    `mpatch`, un `pushUndo`. Une boucle d'appels rendrait N pas d'annulation
    pour un geste, et ferait sauter le plafond bloc par bloc au lieu de
    refuser l'élément ENTIER."""
    corps = _fonction_de(TYPE_JS, "adopterZones")
    assert corps.count("naitre(") == 1, corps
    assert "forEach" not in corps or "naitre(" not in corps.split("forEach")[1], \
        "la naissance est dans une boucle"
    assert "pushUndo" not in corps, "un second pas d'annulation"
    assert "specsZones(" in corps and "phraseZones(" in corps, corps


def test_P3_les_ZONES_S_AJOUTENT_et_RESPECTENT_le_plafond():
    """« si le gabarit a déjà des slots, les zones S'AJOUTENT » — `naitre`
    concatène, il ne remplace pas. Et le plafond de `type.py` (SLOTS_MAX) est
    celui de la pièce, pas un second chiffre : il est LU sur les deux
    sources."""
    from app.services.cards import type as TY
    js = TYPE_JS.read_text(encoding="utf-8")
    m = re.search(r"const SLOTS_MAX = (\d+)", js)
    assert m and int(m.group(1)) == TY.SLOTS_MAX, (m, TY.SLOTS_MAX)
    naitre = _fonction_de(TYPE_JS, "naitre")
    assert "slots().concat(" in naitre, naitre
    assert "placeOu(" in naitre, "le plafond n'est plus dit avant"


def test_P3_le_bouton_d_ADOPTION_n_existe_pas_sans_matiere():
    """Patron sectionsBasses (D6) : la visibilité DÉRIVE du document. Un
    bouton qui s'affiche sans pouvoir agir fait douter du clic — c'est la
    leçon déjà payée par le bouton des zones de P10."""
    js = TYPE_JS.read_text(encoding="utf-8")
    code = _code_js(js)
    assert "specsZones(" in code, "la dérivation n'existe pas"
    assert re.search(r"specsZones\([^;]{0,60}\)\s*\.length", code), \
        "la visibilité n'est pas dérivée du compte de zones"
    # ... et la dérivation COMMANDE bien la visibilité, dans la peinture.
    i = code.index("function renderAll(")
    bloc = code[i:code.index("\n  }", i)]
    assert "specsZones(" in bloc and 'toggle("hidden"' in bloc, \
        "le bouton n'est pas caché/montré par la peinture"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ═══════════════════════════════════════════════════════════════════════════
# T5 — LE MANIFESTE DES COUCHES IMPORTÉES (plan D7 amendé, spec §7.1.6)
#
# LA PROMESSE À TENIR, en une phrase : « une carte importée peut partir en 3D
# sans être reconstruite ». Ce bloc la rend MESURABLE.
#
# Ce que le manifeste importé n'a pas, et qu'il ne feint pas d'avoir : la
# preuve d'empilement des peintres. Ces couches n'ont jamais été empilées.
# Ce qu'il a À LA PLACE, et qui se vérifie : l'EMPREINTE de chaque fichier
# (P9 la recalcule avant de construire — un manifeste qui ment est refusé
# nommé, et ce refus se mesure là-bas) et la COUVERTURE du sujet (T3).
#
# Ce qu'il ne liste PAS, et c'est l'amendement du 24/08 : un `cadre` ou un
# `fond-matiere` qu'aucun fichier ne porte. Aucune tâche n'a découpé de
# bordure ni de fond isolés ; le manifeste ne nomme que `recto` (la face
# entière) et `illustration` (le sujet détouré, s'il existe).
# ═══════════════════════════════════════════════════════════════════════════

def _manifeste(did: str, card=None):
    q = "" if card is None else f"?card={card}"
    return _api("POST", f"/api/cards/{did}/capture/manifeste{q}")


def _p9_dir(did: str):
    from app.services.cards.contract import deck_dir
    from app.services.cards import capture as CP
    return deck_dir(did) / CP.P9_DIR


def _lit_manifeste(did: str, label: str = "c01") -> dict:
    return json.loads((_p9_dir(did) / f"layers_{label}_capture.json")
                      .read_text(encoding="utf-8"))


def test_le_manifeste_importe_est_au_SCHEMA_de_P9(monkeypatch):
    """Le contrat structurel : MÊME schéma, MÊME forme de lignes,
    MÊMES conventions de repère que le manifeste des peintres — sinon P9 ne
    saurait pas le lire, et « sans être reconstruite » serait un vœu.

    Les chiffres ne sont pas postulés : `sha256` est RECALCULÉ sur les octets
    servis, `bytes` confronté à la taille du fichier, `canvas_px` à la
    géométrie du jeu, `bbox_mm` bornée par la TOILE (fond perdu compris — le
    repère de P9, pas celui de la coupe)."""
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()
    r = _manifeste(did)
    assert r.status_code == 200, r.text[:400]
    m = r.json()["layers"]
    assert r.json()["manifeste"] == "layers_c01_capture.json"
    from app.services.cards import forge3d as F9
    from app.services.cards import capture as CP
    assert m["schema"] == F9.MANIFEST_SCHEMA == CP.MANIFEST_SCHEMA
    # LE NOM ET LE CONTENU DISENT LA MÊME CHOSE (la porte de `_lire_manifeste`)
    assert m["side"] == "capture" and m["source"] == "capture"
    assert m["card"] == {"index": 0, "label": "c01"}
    assert m["deck"]["id"] == did
    g = CC.geom_of(CC.read_deck(did))
    assert m["canvas_px"] == list(g.canvas_px)
    assert m["size_mm"] == [g.trim_mm[0], g.trim_mm[1]]
    assert m["bleed_mm"] == g.bleed_mm
    assert m["format"] == g.fmt
    toile = [g.trim_mm[0] + 2 * g.bleed_mm, g.trim_mm[1] + 2 * g.bleed_mm]
    assert m["canvas_mm"] == toile
    # LA DENSITÉ PHYSIQUE EST CELLE DE P9, à l'entier (copie avouée, parité
    # testée — un pHYs qui diffère d'une couche peinte du même jeu ferait deux
    # densités pour une même toile).
    assert m["phys_ppm"] == F9._dpi_to_ppm(g.dpi)
    assert CP._ppm(g.dpi) == F9._dpi_to_ppm(g.dpi)
    for dpi in (150, 300, 600, 1200):
        assert CP._ppm(dpi) == F9._dpi_to_ppm(dpi), dpi
    # ... et le chunk pHYs est bel et bien DANS les octets
    data = (_p9_dir(did) / m["layers"][0]["file"]).read_bytes()
    i = data.index(b"pHYs")
    assert struct.unpack(">IIB", data[i + 4:i + 13]) == (m["phys_ppm"],
                                                         m["phys_ppm"], 1)
    # ── LES LIGNES : la forme de `post_layers`, chiffres RECALCULÉS ──────
    for l in m["layers"]:
        assert set(l) == {"role", "z", "module", "file", "mode", "sha256",
                          "bytes", "bbox_px", "bbox_mm", "coverage_pct",
                          "source_file", "source_sha256", "source_px"}, l
        # ── LA COPIE EST DATÉE (ronde T5, B1) : le nom de sa source, son
        #    empreinte AU MOMENT de la publication, et ses pixels. Les trois
        #    se vérifient sur le disque, ici comme chez P9.
        src = CP.cap_dir(did) / l["source_file"]
        assert src.is_file(), l["source_file"]
        assert hashlib.sha256(src.read_bytes()).hexdigest() == l["source_sha256"]
        assert l["source_px"] == list(Image.open(src).size), l
        p = _p9_dir(did) / l["file"]
        octets = p.read_bytes()
        assert hashlib.sha256(octets).hexdigest() == l["sha256"], l["role"]
        assert len(octets) == l["bytes"], l["role"]
        im = Image.open(io.BytesIO(octets))
        assert im.size == tuple(g.canvas_px), (l["role"], im.size)
        assert im.mode == "RGBA"
        # une couche importée n'a PAS de rang dans la Z_TABLE gelée : rien ne
        # l'a empilée. Le dire vaut mieux que lui prêter le z d'une homonyme.
        assert l["z"] == [] and l["module"] == "capture", l
        assert 0.0 < l["coverage_pct"] <= 100.0, l
        x0, y0, x1, y1 = l["bbox_mm"]
        assert 0 <= x0 < x1 <= toile[0] + 0.01, l["bbox_mm"]
        assert 0 <= y0 < y1 <= toile[1] + 0.01, l["bbox_mm"]
    # ── LA PREUVE, ET SA DETTE, ÉCRITES ENSEMBLE ────────────────────────
    pr = m["proof"]
    assert set(pr) == {"capture"}, pr
    assert "client" not in pr and "backend" not in pr, \
        "un manifeste importé n'emprunte PAS la preuve d'empilement"
    c = pr["capture"]
    assert "aucune preuve d'empilement" in c["note"]
    assert "couverture_sujet_pct" not in c, \
        "un chiffre de couverture qui ne nomme pas son cadre : il en existe " \
        "deux (celui du détourage, celui de la toile)"
    assert "couverture_sujet_pct_toile" in c, c
    assert c["recomposition"] is None and c["recomposition_why"]
    assert "fond" in c["recomposition_why"]
    assert c["source_px"] == [SYNTH_W, SYNTH_H]
    assert isinstance(c["ecart_ratio"], float)
    s.zero()


def test_le_manifeste_ne_liste_QUE_ce_qui_existe(monkeypatch):
    """L'amendement D7 du 24/08, mesuré. Sans sujet détouré : UNE ligne, la
    face entière. Avec : deux. JAMAIS un `cadre` ni un `fond-matiere` —
    aucune tâche n'a produit ces fichiers-là, et un manifeste qui les nommerait
    enverrait P9 lire un fichier qui n'existe pas.

    La couverture du sujet ENTRE dans la preuve quand il est là, et vaut
    `null` quand il n'y est pas : un chiffre inventé serait pire que rien."""
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()
    m = _manifeste(did).json()["layers"]
    assert [l["role"] for l in m["layers"]] == ["recto"]
    assert m["proof"]["capture"]["couverture_sujet_pct_toile"] is None
    # le sujet arrive (posé comme le poserait un détourage)
    from app.services.cards import capture as CP
    (CP.cap_dir(did) / CP.SUJET_NAME).write_bytes(_png_rgba(300, 400))
    m2 = _manifeste(did).json()["layers"]
    roles = [l["role"] for l in m2["layers"]]
    assert roles == ["recto", "illustration"], roles
    ligne = [l for l in m2["layers"] if l["role"] == "illustration"][0]
    assert m2["proof"]["capture"]["couverture_sujet_pct_toile"] == \
        ligne["coverage_pct"]
    # LE SUJET EST DÉTOURÉ : il couvre MOINS que la face entière (sinon la
    # « couche » publiée serait la carte de départ — la doctrine T3).
    face = [l for l in m2["layers"] if l["role"] == "recto"][0]
    assert ligne["coverage_pct"] < face["coverage_pct"], (ligne, face)
    # ── LES RÔLES INVENTÉS N'EXISTENT NULLE PART ────────────────────────
    from app.services.cards import forge3d as F9
    assert set(F9.CAPTURE_ROLES) == {"recto", "illustration"}
    assert "cadre" not in roles and "fond-matiere" not in roles
    for role in ("cadre", "fond-matiere", "typographie", "ornements",
                 "voile-matiere"):
        assert not (_p9_dir(did) / f"{role}_c01_capture.png").exists(), role
    s.zero()


def test_le_manifeste_importe_ne_touche_PAS_celui_des_peintres(monkeypatch):
    """« Les cartes du manifeste des PEINTRES ne bougent pas d'un octet »
    (D7). Les deux familles cohabitent dans le même dossier et ne se
    rencontrent jamais : le suffixe de côté les sépare, et l'export de couches
    reste octet pour octet ce qu'il était."""
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()
    # un manifeste de peintres, écrit à la main au nom que P9 lui donne
    from app.services.cards.contract import deck_dir
    out = _p9_dir(did)
    out.mkdir(parents=True, exist_ok=True)
    faux = out / "layers_c01_front.json"
    faux.write_text(json.dumps({"side": "front", "layers": [{"role": "cadre"}]}),
                    encoding="utf-8")
    avant = faux.read_bytes()
    peint = out / "cadre_c01_front.png"
    peint.write_bytes(_png_rgba(10, 10))
    avant_png = peint.read_bytes()
    _manifeste(did)
    assert faux.read_bytes() == avant
    assert peint.read_bytes() == avant_png
    assert (out / "layers_c01_capture.json").is_file()
    assert (out / "recto_c01_capture.png").is_file()
    s.zero()


def test_le_manifeste_suit_la_CARTE_et_refuse_sans_recto(monkeypatch):
    """L'étiquette de carte nomme les fichiers de P9 : le manifeste la prend
    en paramètre, avec la MÊME garde que P9 (une entrée non numérique retombe
    sur la première carte, jamais une exception). Et sans face importée, il
    n'y a rien à décrire : 404 nommé, pas un manifeste vide."""
    s = _sentinelle(monkeypatch)
    from app.services.cards import capture as CP
    from app.services.cards import forge3d as F9
    for brut in (0, 1, 7, "3", "abc", -4, None, [1], 1.9):
        attendu = f"c{F9._card_idx(brut) + 1:02d}"
        assert CP._card_label(brut) == attendu, (brut, attendu)
    did = _deck_avec_recto()
    assert _manifeste(did, 2).json()["manifeste"] == "layers_c03_capture.json"
    assert (_p9_dir(did) / "recto_c03_capture.png").is_file()
    assert _manifeste(did, "abc").json()["manifeste"] == \
        "layers_c01_capture.json"
    vide = _deck()
    r = _manifeste(vide)
    assert r.status_code == 404, r.status_code
    assert "déposez" in r.json()["detail"] or "recto" in r.json()["detail"]
    # deck inconnu / identifiant sale : refus du domaine, jamais 500
    assert _manifeste("deck_00000000").status_code == 404
    assert _manifeste("nimportequoi").status_code == 400
    s.zero()


def test_la_face_importee_est_POSEE_dans_la_toile_du_jeu(monkeypatch):
    """La convention de P9 : une couche est une TOILE (`canvas_px`, fond perdu
    compris), et c'est sur elle que reposent la fenêtre UV du quad, la boîte
    en millimètres et le recadrage à la coupe d'un relief.

    La face importée est donc posée dans le rectangle de COUPE de cette
    toile ; le fond perdu reste TRANSPARENT — une capture n'en a pas, et en
    inventer un serait peindre. Mesuré au pixel : opaque au centre, alpha nul
    dans la marge, et la boîte publiée EST le rectangle de coupe."""
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()
    m = _manifeste(did).json()["layers"]
    g = CC.geom_of(CC.read_deck(did))
    im = Image.open(io.BytesIO(
        (_p9_dir(did) / "recto_c01_capture.png").read_bytes())).convert("RGBA")
    ox, oy = int(round(g.bleed_off_px[0])), int(round(g.bleed_off_px[1]))
    assert im.getpixel((ox + 2, oy + 2))[3] == 255           # dans la coupe
    assert im.getpixel((im.size[0] // 2, im.size[1] // 2))[3] == 255
    assert im.getpixel((1, 1))[3] == 0                        # le fond perdu
    assert im.getpixel((im.size[0] - 2, im.size[1] - 2))[3] == 0
    ligne = m["layers"][0]
    assert ligne["bbox_px"] == [ox, oy, ox + g.trim_px[0], oy + g.trim_px[1]]
    # la couverture EST le rapport des aires coupe/toile, au centième
    attendu = (g.trim_px[0] * g.trim_px[1]
               / float(g.canvas_px[0] * g.canvas_px[1]) * 100.0)
    assert abs(ligne["coverage_pct"] - attendu) < 0.01, (ligne, attendu)
    # ... et la boîte MM tombe sur le fond perdu, aux deux bords
    x0, y0, x1, y1 = ligne["bbox_mm"]
    assert abs(x0 - g.bleed_mm) < 0.1 and abs(y0 - g.bleed_mm) < 0.1
    assert abs(x1 - (g.bleed_mm + g.trim_mm[0])) < 0.1
    assert abs(y1 - (g.bleed_mm + g.trim_mm[1])) < 0.1
    s.zero()


def test_le_manifeste_se_REJOUE_et_suit_le_format(monkeypatch):
    """POURQUOI UNE ROUTE PLUTÔT QU'UN EFFET DE BORD DE L'ANALYSE OU DU
    DÉTOURAGE, mesuré : le manifeste DÉPEND du format du jeu. Toile,
    millimètres, densité — tout en vient. Un manifeste écrit en douce à
    l'analyse serait périmé au premier changement de format ; le geste
    explicite se rejoue, et le second relevé décrit le format COURANT.

    Rejouable veut aussi dire IDEMPOTENT à format constant : deux
    publications de suite rendent les mêmes octets (à l'horodatage près)."""
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()
    un = _manifeste(did).json()["layers"]
    deux = _manifeste(did).json()["layers"]
    for a, b in zip(un["layers"], deux["layers"]):
        assert a["sha256"] == b["sha256"] and a["bytes"] == b["bytes"]
    assert un["canvas_px"] == deux["canvas_px"]
    # ── LE FORMAT CHANGE : le relevé suivant le suit ────────────────────
    CC.patch_deck(did, {"format": {"fmt": "tarot_eu"}})
    trois = _manifeste(did).json()["layers"]
    assert trois["format"] == "tarot_eu"
    assert trois["size_mm"] == [70.0, 120.0]
    assert trois["canvas_px"] != un["canvas_px"]
    im = Image.open(io.BytesIO(
        (_p9_dir(did) / "recto_c01_capture.png").read_bytes()))
    assert im.size == tuple(CC.geom_of(CC.read_deck(did)).canvas_px)
    # l'écart de ratio est PUBLIÉ, jamais absorbé : la face est étirée au
    # format, et le chiffre dit de combien.
    assert abs(trois["proof"]["capture"]["ecart_ratio"]) > 0.1, \
        trois["proof"]["capture"]
    s.zero()


def test_le_manifeste_ne_laisse_JAMAIS_de_brouillon_et_ne_leve_pas(monkeypatch):
    """Le patron d'écriture de T1, appliqué chez la voisine : brouillon
    nominatif + `replace` patient, aucun `.tmp` survivant, et un disque qui
    refuse rend un 409 NOMMÉ — jamais 500 (§8)."""
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()
    _manifeste(did)
    restes = [p.name for p in _p9_dir(did).iterdir() if p.suffix == ".tmp"]
    assert not restes, restes
    # ── LE DISQUE REFUSE AU MOMENT DU REMPLACEMENT ──────────────────────
    # Le refus est intercepté SUR CHACUNE des deux écritures, et le message le
    # dit : la COUCHE nommée d'abord (c'est elle qui passe la première), le
    # manifeste ensuite. Épingler « Relancez » seul laisserait passer une
    # écriture directe du PNG — les deux phrases le portent.
    from app.services.cards import capture as CP

    def _refuse(tmp, final):
        raise OSError(32, "fichier utilise par un autre processus")
    monkeypatch.setattr(CP, "_replace_avec_patience", _refuse)
    r = _manifeste(did)
    assert r.status_code == 409, r.status_code
    detail = r.json()["detail"]
    assert "La couche « recto »" in detail, detail
    assert "Relancez" in detail, detail
    # ... et rien n'a été laissé derrière : ni brouillon, ni demi-fichier
    assert not [q.name for q in _p9_dir(did).iterdir() if q.suffix == ".tmp"]
    monkeypatch.undo()
    # LE MANIFESTE LUI-MÊME a la même garde : on ne laisse passer QUE la
    # couche, et c'est alors lui qui refuse — la seconde moitié du contrat.
    vrai = CP._replace_avec_patience

    def _refuse_json(tmp, final):
        if final.suffix == ".json":
            raise OSError(32, "fichier utilise par un autre processus")
        return vrai(tmp, final)
    monkeypatch.setattr(CP, "_replace_avec_patience", _refuse_json)
    r2 = _manifeste(did)
    assert r2.status_code == 409, r2.status_code
    assert "Le manifeste n'a pas pu être écrit" in r2.json()["detail"],         r2.json()["detail"]
    monkeypatch.undo()
    s.zero()


def test_UNE_CARTE_IMPORTEE_PART_EN_3D_SANS_ETRE_RECONSTRUITE(monkeypatch):
    """§7.1.6, LE TEST DE BOUT — et c'est le geste complet, pas une pièce de
    puzzle : on dépose une carte, on la MESURE, on en isole le sujet par la
    voie locale (faux module, ZÉRO dépense), on PUBLIE le manifeste, puis on
    construit un graphe de HUIT nœuds chez P9. Il en sort un GLB SERVI.

    Ce que la construction n'a PAS fait, et c'est tout l'objet : reconstruire
    la carte. Aucun painter n'a tourné, aucune couche n'a été exportée — la
    face importée texture un plan au format carte, le sujet détouré en
    texture un second, et la couronne du Sceau les ceint.

    Ce qui est vérifié à l'arrivée : le GLB est servi, le bordereau AVOUE la
    provenance des deux couches AVEC leur couverture, l'artefact ne porte
    AUCUN nom d'outil (`scrub_identity`) et ses dimensions physiques sont
    celles du format."""
    s = _sentinelle(monkeypatch)
    _sans_rembg(monkeypatch)
    did = _deck()

    # ── 1. IMPORTER ─────────────────────────────────────────────────────
    r = _post(did, _pngs(_synth(bord_px=26, boites=TROIS)), "recto")
    assert r.status_code == 200, r.text[:300]

    # ── 2. MESURER (gratuit, local) ─────────────────────────────────────
    a = _analyse(did)
    assert a.status_code == 200, a.text[:300]
    rel = a.json()
    assert rel["border"] and rel["border"]["mm"] > 0
    assert rel["boxes"], "la carte de synthèse porte trois cartouches"

    # ── 3. ISOLER LE SUJET (voie LOCALE, faux module, zéro dépense) ─────
    faux = _pose_rembg(monkeypatch, _FauxRembg(sortie=_png_rgba(630, 880)))
    rr = _rembg(did)
    assert rr.status_code == 200, rr.text[:300]
    assert rr.json()["voie"] == "local" and rr.json()["gratuit"] is True
    assert faux.appels == 1

    # ── 4. PUBLIER LE MANIFESTE ─────────────────────────────────────────
    pub = _manifeste(did)
    assert pub.status_code == 200, pub.text[:400]
    man = pub.json()["layers"]
    assert [l["role"] for l in man["layers"]] == ["recto", "illustration"]

    # ── 5. PARTIR EN 3D — huit nœuds, aucune couche exportée ────────────
    g = {"nodes": [
        {"id": "face", "kind": "layer", "role": "recto", "side": "capture"},
        {"id": "plan", "kind": "plane", "depth_mm": 0.0},
        {"id": "sujet", "kind": "layer", "role": "illustration",
         "side": "capture"},
        {"id": "relief", "kind": "plane", "depth_mm": 0.4},
        {"id": "anneau", "kind": "extrude", "contour": "sceau",
         "depth_mm": 0.5},
        {"id": "sceau", "kind": "material", "finish": "argent",
         "aniso": False},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "fragment"}],
        "edges": [{"from": "face", "to": "plan"}, {"from": "plan", "to": "asm"},
                  {"from": "sujet", "to": "relief"},
                  {"from": "relief", "to": "asm"},
                  {"from": "anneau", "to": "sceau"},
                  {"from": "sceau", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    b = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert b.status_code == 200, b.text[:600]
    art = b.json()["artifact"]
    assert art["ignored"] == [], art["ignored"]
    assert art["elements"] == 3, art["elements"]

    # ── LE BORDEREAU AVOUE LA PROVENANCE, AVEC SON CHIFFRE ──────────────
    par_nom = {d["name"]: d for d in art["elements_detail"]}
    assert set(par_nom) == {"recto_capture", "illustration_capture",
                            "extrude_sceau"}, sorted(par_nom)
    # LE RECTO NE MAQUILLE PAS UNE CONSTANTE DE FORMAT EN MESURE (R4) : sa
    # part opaque de toile vaut le rapport coupe/toile, la MÊME sur toute
    # carte du format. Il dit donc ce qu'il EST et ce qu'il pèse en pixels.
    face = par_nom["recto_capture"]
    assert face["side"] == "capture", face
    assert "face entiere importee" in face["import"], face
    assert "%" not in face["import"], face
    src = [l for l in man["layers"] if l["role"] == "recto"][0]["source_px"]
    assert f"{src[0]}x{src[1]} px" in face["import"], (src, face)
    # LE SUJET, LUI, MESURE VRAIMENT SON CONTENU — et il NOMME SON CADRE.
    suj = par_nom["illustration_capture"]
    ligne = [l for l in man["layers"] if l["role"] == "illustration"][0]
    chiffre = f"{ligne['coverage_pct']:.1f}".replace(".", ",")
    assert suj["side"] == "capture" and "couche importee" in suj["import"], suj
    assert f"{chiffre} % de la toile" in suj["import"], suj
    assert par_nom["extrude_sceau"]["contour"] == "sceau"

    # ── LE GLB EST SERVI, ET IL EST PROPRE ──────────────────────────────
    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{art['glb']['name']}")
    assert glb.status_code == 200
    assert glb.content[:4] == b"glTF"
    assert len(glb.content) == art["glb"]["bytes"]
    doc = _glb_doc(glb.content)
    ex = doc["asset"].get("extras") or {}
    assert ex["size_mm"] == [63.0, 88.0] and ex["unit"] == "metre"
    assert ex["card"] == "c01" and ex["schema"] == "card-3d/artifact@1"
    # SCRUB_IDENTITY : aucun nom d'outil, nulle part dans les octets du JSON
    for cle in ("generator", "producer", "author", "software", "application",
                "copyright"):
        assert cle not in doc["asset"], (cle, doc["asset"])
        assert cle not in ex, (cle, ex)
    assert [m2["name"] for m2 in doc["materials"]] == [
        "recto_capture", "illustration_capture", "extrude_sceau"]
    # la couronne porte bien la recette du Sceau (le matériau par référence)
    anneau = [m2 for m2 in doc["materials"]
              if m2["name"] == "extrude_sceau"][0]
    assert "KHR_materials_iridescence" in anneau.get("extensions", {}), anneau
    assert "KHR_materials_iridescence" in doc["extensionsUsed"]
    assert "KHR_materials_iridescence" not in doc.get("extensionsRequired", [])
    # le metadata ERC-721 est écrit à côté, et il compte les trois éléments
    meta = json.loads(_api(
        "GET",
        f"/api/cards/{did}/forge3d/file/{art['metadata']['name']}").content)
    attrs = {a2["trait_type"]: a2["value"] for a2 in meta["attributes"]}
    assert attrs["elements_3d"] == 3 and attrs["carte"] == "c01"

    # ── ZÉRO DÉPENSE, PROUVÉE ───────────────────────────────────────────
    assert faux.appels == 1
    s.zero()


def _glb_doc(data: bytes) -> dict:
    """Le chunk JSON d'un GLB — juste ce qu'il faut pour relire un artefact
    depuis ce fichier-ci (P9 a son propre lecteur ; le recopier en entier
    ferait deux lecteurs qui dérivent, celui-ci n'en lit que l'en-tête)."""
    assert data[:4] == b"glTF"
    n = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + n].decode("utf-8").rstrip("\x00 "))


# ═══════════════════════════════════════════════════════════════════════════
# RONDE T5 — CE QUE LA REVUE A MESURÉ, CÔTÉ IMPORT
# ═══════════════════════════════════════════════════════════════════════════

def test_vingt_quatre_publications_simultanees_rendent_UN_manifeste(monkeypatch):
    """R6 (ronde T5) — LA CONCURRENCE PASSAIT, ET RIEN NE L'ÉPINGLAIT. C'est
    exactement la leçon T1 : le patron d'écriture (brouillon nominatif +
    `replace` patient) a été recopié de l'admission, il TIENT (24 sur 24
    mesurés par la revue), mais un patron recopié sans son test se perd à la
    première réécriture.

    Ce qui est exigé : tous servis (aucun 500, aucun 409 de course), UN seul
    manifeste sur le disque, et des empreintes COHÉRENTES — le sha publié doit
    décrire les octets réellement posés, pas ceux d'un autre tour."""
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()

    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=600.0) as c:
            return await asyncio.gather(*[
                c.post(f"/api/cards/{did}/capture/manifeste")
                for _ in range(24)], return_exceptions=True)

    reps = asyncio.run(go())
    codes = [getattr(r, "status_code", r) for r in reps]
    assert all(c == 200 for c in codes), codes
    # UN SEUL manifeste, et AUCUN brouillon oublié
    fichiers = sorted(p.name for p in _p9_dir(did).iterdir())
    assert fichiers.count("layers_c01_capture.json") == 1, fichiers
    assert not [n for n in fichiers if n.endswith(".tmp")], fichiers
    # L'EMPREINTE PUBLIÉE DÉCRIT LES OCTETS POSÉS — c'est le seul contrôle qui
    # verrait un `replace` qui laisse deux tours se mélanger.
    m = _lit_manifeste(did)
    for l in m["layers"]:
        octets = (_p9_dir(did) / l["file"]).read_bytes()
        assert hashlib.sha256(octets).hexdigest() == l["sha256"], l["file"]
        assert len(octets) == l["bytes"], l["file"]
    # ... et TOUTES les réponses décrivent le même fichier (le manifeste rendu
    # par chaque appel est celui qu'on relit sur le disque).
    shas = {tuple(sorted(x["sha256"] for x in r.json()["layers"]["layers"]))
            for r in reps}
    assert len(shas) == 1, shas
    s.zero()


def test_le_chiffre_du_recto_ne_DEGUISE_PAS_une_constante_de_format(monkeypatch):
    """R4 (ronde T5) — `coverage_pct` de la face entière vaut le rapport
    coupe/toile : 85,45 % sur TOUT poker, quel que soit ce qu'il y a dessus.
    Le bordereau l'affichait comme une « couverture », c'est-à-dire comme un
    relevé. C'est la leçon T4-a mot pour mot : une constante de format
    maquillée en mesure.

    LA PREUVE QUE C'EN EST UNE : un aplat noir et une photographie donnent la
    MÊME phrase de bordereau à la taille près — parce qu'il n'y a rien à
    mesurer là. Le sujet, lui, mesure vraiment, et il NOMME son cadre."""
    from app.services.cards import forge3d as F9
    s = _sentinelle(monkeypatch)
    phrases = []
    couvertures = []
    for im in (Image.new("RGB", (630, 880), (0, 0, 0)),
               _synth(bord_px=26, boites=TROIS)):
        did = _deck()
        assert _post(did, _pngs(im), "recto").status_code == 200
        m = _manifeste(did).json()["layers"]
        ligne = [l for l in m["layers"] if l["role"] == "recto"][0]
        couvertures.append(ligne["coverage_pct"])
        phrases.append(F9._dit_provenance(ligne))
    assert couvertures[0] == couvertures[1], couvertures
    assert phrases[0] == phrases[1], phrases
    assert "face entiere importee" in phrases[0], phrases[0]
    assert "%" not in phrases[0], phrases[0]
    assert "630x880 px" in phrases[0], phrases[0]
    # ── LE SUJET, LUI, MESURE — ET IL DIT DANS QUEL CADRE ────────────────
    from app.services.cards import capture as CP
    did = _deck_avec_recto()
    (CP.cap_dir(did) / CP.SUJET_NAME).write_bytes(_png_rgba(300, 400))
    m = _manifeste(did).json()["layers"]
    suj = [l for l in m["layers"] if l["role"] == "illustration"][0]
    phrase = F9._dit_provenance(suj)
    assert "% de la toile" in phrase, phrase
    assert f"{suj['coverage_pct']:.1f}".replace(".", ",") in phrase, phrase
    # DEUX CADRES, DEUX NOMBRES : celui de `/rembg` décrit l'image rendue par
    # le détourage, celui du manifeste décrit la TOILE. Ils diffèrent, et
    # c'est normal — ce qui ne l'était pas, c'est qu'ils partageaient un nom.
    assert suj["coverage_pct"] != couvertures[0]
    s.zero()


def test_l_index_de_carte_est_BORNE_et_les_orphelins_sont_ramasses(monkeypatch):
    """M11 (ronde T5), les deux moitiés.

    LA BORNE. Mesuré : `?card=99999999` écrivait `layers_c100000000_capture`
    — un nom de fichier que rien ne bornait — et brûlait 691 ms de
    rééchantillonnage pour une carte qui n'existe dans aucun jeu. Refus 404
    NOMMÉ, et la carte juste en dessous du plafond, elle, passe.

    LES ORPHELINS. Le publieur POSSÈDE ses noms canoniques : republier après
    avoir effacé le sujet laissait `illustration_c01_capture.png` sur le
    disque, plus nommée par aucun manifeste et pourtant servie par le GET de
    P9 — une couche fantôme qu'un graphe pouvait encore viser."""
    from app.services.cards import capture as CP
    s = _sentinelle(monkeypatch)
    did = _deck_avec_recto()
    r = _manifeste(did, 99999999)
    assert r.status_code == 404, r.status_code
    assert str(CP.CARTE_MAX) in r.json()["detail"], r.json()["detail"]
    # RIEN N'A ÉTÉ ÉCRIT — pas même le dossier de P9 : le refus tombe AVANT
    # le premier rééchantillonnage, c'est tout l'intérêt de la borne.
    assert not _p9_dir(did).exists() or not [
        q for q in _p9_dir(did).iterdir()
        if q.name.startswith("layers_c1000")], "un nom a été écrit"
    # la dernière carte SOUS le plafond passe
    assert _manifeste(did, CP.CARTE_MAX - 1).status_code == 200
    # ── LES ORPHELINS ───────────────────────────────────────────────────
    (CP.cap_dir(did) / CP.SUJET_NAME).write_bytes(_png_rgba(300, 400))
    m = _manifeste(did).json()["layers"]
    assert len(m["layers"]) == 2
    orphelin = _p9_dir(did) / "illustration_c01_capture.png"
    assert orphelin.is_file()
    CP._oublie_sujet(did)
    m2 = _manifeste(did).json()["layers"]
    assert [l["role"] for l in m2["layers"]] == ["recto"]
    assert not orphelin.is_file(), \
        "une couche que plus aucun manifeste ne nomme reste servie par P9"
    s.zero()
