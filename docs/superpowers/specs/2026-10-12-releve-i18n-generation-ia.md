# Relevé i18n des lots « Génération IA » G0-G9 (t192 · G10) — 12/10/2026

Périmètre : les 48 commits t182→t191 (+ correctifs « (correctif t190) ») entre `32b2d6d6` et `ab7d0c91`.
Méthode : `git blame ab7d0c91` de chaque fichier NON-test touché par ces commits ; seules les lignes dont le dernier
auteur est un commit des lots sont relevées (631 lignes candidates : chaîne accentuée ou mot français), puis relues
une à une. Les fichiers de saisie (`scripts/i18n_l*/…`) portent les paires FR/EN elles-mêmes : relus pour vérifier
que leur sortie (couche, lab) passe bien par `dzT`/`__dzT9`, pas comme oublis.

Verdicts : **déjà traduit** (clé posée par le lot), **corrigé** (t192), **reste voulu** (raison dite).

## 1. Écran

| Fichier:ligne (ab7d0c91) | Texte | Verdict |
|---|---|---|
| `shared/dz-champ-ia.js:884` (t187) | « le modèle de bruitage se choisit à côté du champ » (raison de la pastille SFX) | **corrigé** : `PASTILLE_CLES` → `ia.pastille.pq_sfx` (commun.json), traduit à l'affichage par `TP` |
| `shared/dz-champ-ia.js:1004-1036` (pastille de modèle, t183 a modifié 1026-1036) | « Modèle : X — choisi par la vue (…) », « Aucun modèle disponible », « — le sélecteur de la vue n'en propose aucun », « — cliquer pour changer (écrit dans le sélecteur de la vue) », « aucun modèle » | **corrigé** : `TP("ia.pastille.fixe/lecture/fige/aucun_dispo/vue_sans_aucun/sans_selecteur/choisir/aucun", <français d'avant>)` |
| `shared/dz-champ-ia.js:1052→1108` (t183) | « absent du sélecteur de la vue », « indisponible », « — modèle actuel de la vue », « — choisir ce modèle (…) », `aria-label` « Modèles », title « Modèle de génération », badge « Champ de génération IA » | **corrigé** : `ia.pastille.hors_vue/indisponible/actuel/choisir_ce/modeles/titre/badge` (« Modèles » en `contexte` : L7 le traduit « Templates ») |
| `shared/dz-champ-ia.js:629` | `CLE_ABSENTE` « clé X absente » | **corrigé** : clé existante `ia.cle.absente` |
| `shared/dz-champ-ia.js:909-938` | raisons « le générateur se choisit dans 🎨 DA », « le modèle d'image global : … », « le moteur 3D se choisit dans la vue », « le Spritelab anime avec … » ; noms fixes « HeyGen (photo animée) », « moteur de langage des Réglages » ; raisons de pastille figée « sélecteur de la vue désactivé / vide » | **corrigé** : même table `PASTILLE_CLES` (`ia.pastille.pq_*`, `fixe_*`, `fg_*`) — l'entrée DA est posée après `var DA` (le glyphe 🎨 n'est écrit qu'une fois : test_icones_g6 3.2) |
| `shared/dz-champ-ia.js:637, 648-657` | replis « clé X à ajouter dans Réglages », `VOIES_FR`, « prix à mesurer » | déjà traduit (`ia.cle.a_ajouter`, `ia.voie.*`, `ia.prix.a_mesurer`) — replis vérifiés égaux au dictionnaire |
| `shared/dz-champ-ia.js:1227-1621` (dictée) | « Dicter — … », « Dictée indisponible… » | **reste voulu** : antérieur aux lots G (reste déclaré de L9, module partagé non migré) |
| `shared/dz-modeles-ia.js:29-32` | table `FR` (repli sous node) | déjà traduit — repli = français du dictionnaire (banc [4a]) |
| `shared/dz-modeles-ia.js:43` | unités « /image », « /30 images » | reste voulu : identiques dans les deux langues |
| `atelier/atelier.js`, `cardforge/js/mod-capture.js`, `vectorlab/js/mod-iacalque.js`, `photolab/js/mod-iacalque.js` | (commentaires seulement) | déjà traduit (saisies L8 t189, L7 t186, L6 iacalque, `T()` direct) |
| `patches/montage.js:6796` | « Importés » (table des groupes, t187 y a ajouté `sfx_video`, `vfx_ia`) | déjà traduit ailleurs (`montage.mots.importes`) ; libellés de groupe comparés, pas de texte neuf |
| `patches/sfxstudio.js:1689`, `patches/vfxrack.js:1276` | (dzT déjà posé / commentaire) | déjà traduit (saisies L4 sfx_b, vfx) |
| `spritelab/index.html:131,176,183` | title du modèle de prompt, « Modèle de détourage », « Sujet à garder » | déjà traduit : entrées H de `scripts/i18n_l9/t183.py`/`t186.py` (surcouche) ; options = passe de démarrage L9 puis DzModelesIA |
| `studio3d/index.html:97-98` | « Modèle de détourage », option « Masque des coins (local, gratuit) », « Sujet à garder » | déjà traduit : H de t186 (surcouche pour title/placeholder ; l'`<option>` par la passe de démarrage de studio3d.js, qui traduit toute option connue du dictionnaire) |
| `studio3d/vues.js:216-256`, `spritelab/spritelab.js:1103` | `__dzT9(clé, fr)` | déjà traduit (générateur L9) |
| `avatar/index.html:162` | « Sujet à garder » | déjà traduit (`avatar.decor.sujet`, surcouche) |
| `patches/son-vfx-montage.js:489` (carte Musique) | `v.desc`, `v.label`, ambiances `md.name` servis par `/api/music-models` (catalogue rafraîchi par G5 : 5 modèles neufs) | **corrigé côté serveur** : `catalogues.musique` (copie traduite selon Accept-Language, clés `musique.<id>.desc/nom`, `musique.ambiance.<id>`) |
| `patches/vfxrack.js:1314` | `dzT("vfx.ia.devis",{detail:arm.detail})` — `detail` = libellé de devis du serveur (« Rééclairer (MiniMax H3) (5 s · 720p) — prix à mesurer ») | **corrigé côté serveur** : `pricing._ligne_vfx` rend un `Message` (`pricing.vfx.ligne*`, détail `vfx.det.*`), la route `/vfx-ia` (devis) le dit dans la langue de la requête |
| `patches/vfxrack.js:1033` (matte, G4) | libellé de devis de `/cost/estimate` | **reste voulu** : libellés de devis servis par `/cost/estimate` (toutes natures, antérieur aux lots) — lot L10 |
| libellé de registre « Recraft 4.1 vecteur SVG (via fal) » | jamais proposé : `DzModelesIA.filtrer` (écrans) et `dzImgOpts` (bundle, maillon encartsia) écartent `sortie: "svg"` de tout sélecteur raster | reste voulu (non affiché) |

## 2. Serveur (messages affichés par les écrans)

Mécanisme (t192) : `app.i18n.Message` (une `str` dont le texte est le français d'avant, à l'octet) et `app.i18n.Refus`
(`ValueError` du même texte) gardent clé + variables ; `app.i18n.Nom(id, libellé)` nomme un modèle (libellé du registre
en français, `ia.nom.<id>` en anglais) ; la route rend `texte(x, langue)` — Accept-Language, sinon UI_LANG pour les
routes sans `Request`. Sans en-tête et UI_LANG=fr : rien ne change pour les bancs.

| Fichier | Messages | Verdict |
|---|---|---|
| `routes.py` `/audio/sfx-video` (G5) | clé absente (nom du modèle en français dans un message anglais !), ffprobe illisible, vidéo refusée (format, durée), description trop longue / requise, vidéo introuvable (clip, fichier) | **corrigé** : `_refus_cle(…, _nom_g(id, label))`, `ia.video.duree_illisible`, `ia.video.format(_sans_ext)`, `ia.video.duree_*`, `ia.sfx.prompt_trop_long`, `ia.sfx.prompt_requis`, `ia.video.clip_introuvable`, `ia.fichier.*_introuvable` |
| `routes.py` `/audio/sfx` (G5) | clé absente nommant le libellé français | **corrigé** (`_nom_g`) |
| `routes.py` `/vfx-ia` (G6) + `vfx_ia.py` | clé absente, prompt requis / trop long, option requise / hors bornes / trop longue, reprise, 1080p PixVerse, image exigée / refusée, source (format, durée, images min/max, budget LTX, côtés, poids), insertion hors vidéo, ligne de devis | **corrigé** : `vfx.ia.*`, `ia.prompt.trop_long`, `pricing.vfx.*`, `vfx.det.*`, `ia.nom.<geste>` |
| `routes.py` `/shots/{id}/objets3d` + `storyboard3d.py` (G7) | plan sans image, image illisible, objets à décrire, scène pleine, clé absente | **corrigé** : `storyboard3d.*`, `_nom_g` |
| `routes.py` `_video_plan` (G7 : devis et tir de la vidéo du plan) | sans image de départ, départ / fin introuvable, mouvement requis | **corrigé** : `plan.video.*` |
| `routes.py` `_detourage_controles` (G4 : Studio, Spritelab, Studio3D, Montage, Avatar) | sans `nommer` : français d'avant ; en anglais : les refus `ia.detour.*` de t191 avec le nom `ia.nom.<id>` | **corrigé** (le français reste à l'identique) |
| `routes.py` `/images/process` remove-bg, `detourage.py` | rembg absent, chroma pas assez uni, sujet manquant | **corrigé** : `ia.detour.rembg_absent`, `ia.detour.chroma_pas_uni`, `ia.detour.sujet_manquant` |
| `routes.py` `/images/generate`, `/images/edit` (G0) | « OPENAI_API_KEY non configurée (Réglages) pour X. », « X : pas de retouche (…) » | **corrigé** : `ia.cle.non_configuree`, `ia.image.pas_de_retouche` |
| `routes.py` `/matte` (G4) | clé absente nommant « Général (léger) » | **corrigé** (`_nom_g` → `ia.nom.general`) |
| `cards/capture.py` (G4), `cards/data.py` (G1) | « Détourage refusé : … », « X a refusé le détourage : … », clé absente du lot | **corrigé** : `ia.detour.refuse`, `ia.detour.echec_fournisseur`, `cartes.lot.cle_absente`, `cartes.lot.la_cle` |
| `avatar_live_routes.py` `_decor_sujet` (G4) | sujet manquant | **corrigé** (`texte(e, UI_LANG)`) |
| `photolab_routes.py` (G9) | — | déjà traduit (`photolab.ia.*`, `_m`) |
| refus d'APPEL MAL FORMÉ (« clip_id refusé », « donnez la vidéo … : clip_id ou video_filename », « origine refusée », « options : un objet … », « option inconnue », « … refusé pour … », « attend un nombre/entier/texte/vrai ou faux », « Modèle de storyboard 3D inconnu », « detection_threshold … », « Modèle vidéo inconnu », « duration_s … », ids inconnus des registres, « Recraft vectoriel rend du SVG … ») | jamais déclenchés par l'écran (listes fermées, contrôles bornés) | **reste voulu** — lot L10 ; liste GARDÉE motivée dans le banc ([5b]) |
| `music_service.py` (G5 : `_payload_champs`, `_duree`) | refus et notes (« impose sa durée », « exige des paroles »…) | **reste voulu** : copies des messages d'AVANT G5 (`_payload`), même texte ; à traiter avec eux (L10) |
| `pricing.py` (G4, G5, G7) libellés « — prix à mesurer » du détourage, du bruitage, du storyboard, de la musique | servis par `/cost/estimate` (générique) | **reste voulu** — L10 (seule la ligne VFX IA, collée dans une phrase de l'écran, est corrigée) |
| `current_step` des jobs (« Sonorisée », « VFX IA », « Détourage du sujet (…) ») | étapes de job | **reste voulu** : toutes les étapes de job de l'app sont en français (L10) |
| journaux (`logger.*`), docstrings, `phrase` du catalogue VFX (l'écran a ses clés `vfx.ia.<geste>.phrase`) | — | non affichés |

## 3. Écarts au plan

- Préfixes : le plan annonçait `sfx.json`/`episodes.json`, `atelier.plan.*` seul, `photolab.menu.calque_detourer`,
  et des clés serveur `ia.cle_absente`, `ia.pas_de_fin`, `detour.sujet_requis`, `vfx.image_requise`. Réel : `son.json`
  (`son.sfx.*`, `son.gen.*` ; `sfx.json` n'a qu'une valeur modifiée), `atelier.json` (`atelier.at2_video.*`,
  `atelier.at2_obj3d.*`, `atelier.at2_dzp.*`, `atelier.plan.*`, `atelier.t183_da.*`), `photolab.menu.retirer_fond`,
  `photolab.calques.ia`, serveur `ia.cle.absente_tir`, `ia.video.pas_de_fin`, `ia.detour.*`, `photolab.ia.*` ; et des
  clés hors tableau du plan : `cartes.*`, `sprites.*`, `studio3d.t186.*`, `avatar.decor.*`, `matiere.*`, `studio.*`.
- Compte : 315 clés d'écran posées par G0-G9 (+ 24 t192) et 22 clés serveur (+ 108 t192) — le plan disait « ≥ 60 ».
- Le banc du plan (« contient é/la/les ») attrapait commentaires et replis : remplacé par un tokeniseur JS (chaînes
  hors commentaires/regex), la table de repli vérifiée à part, et une analyse AST des refus serveur.
