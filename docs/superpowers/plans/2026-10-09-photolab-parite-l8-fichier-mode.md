# Photolab parité L8 (t158) — Fichier sûr et Image › Mode sous liste blanche

> Relevé : `specs/2026-10-08-photolab-bientot-liste.md` (29 entrées « L8 fichier-mode ») ; base origin/main ecf945e4,
> branche `chantier/photolab-parite-l8`. Le code amont n'est plus dans le scratchpad : le comportement vient du registre
> et des sondes sur le VRAI moteur (09/10), sans téléchargement.

## Périmètre (29)

Fichier › Ouvrir en tant que, Tout fermer, Fermer les autres, Enregistrer une copie, Revenir, Exportation rapide PNG,
Placer incorporé, Informations sur le fichier ; Image › Mode (12) ; Image › Ajustements › Faire correspondre la couleur ;
Calque › Exportation rapide PNG, Exporter sous ; Calque › Objets intelligents › Lier de nouveau au fichier, Remplacer le
contenu, Exporter le contenu, Convertir en objet lié ; Filtre › Déformation › Déplacement ; Filtre › Rendu › Flamme.

## Faits établis (vrai moteur, 09/10)

- **Le moteur désactive LUI-MÊME** toute commande à chemin ambiant : « automation command `…` uses ambient filesystem
  paths and is disabled » — `file.saveACopy`, `file.revert`, `file.placeEmbedded`, `file.openAs`,
  `layer.quickExportAsPng`, `layer.exportAs`, `layer.smartObjects.{editContents, exportContents, replaceContents,
  relinkToFile, convertToLinked}`, `filter.distort.displace {mapPath}`, `edit.colorSettings`. Seules les méthodes
  `doc.open/save/close/new` touchent au disque. → ces entrées se COMPOSENT dans le pont, ou sont bloquées.
- `image.duplicate {name}` crée une copie (documents distincts, ids de calques RENUMÉROTÉS, même ordre) ; un `doc.save`
  de la copie ne rattache pas l'original. `doc.save` d'un .pcraft rattache le document et efface `dirty` ; un PNG non.
- `edit.copy` (sans sélection : le calque actif sur toute la toile) + `edit.paste {center}` copie entre documents ;
  `document.activate {document}`, `file.close {document}`, `document.inspect {document}` (autre document) existent.
- `image.trim {basedOn:"transparent"}` : « nothing to trim to » si tout est transparent.
- Image › Mode : profils intégrés `srgb, display-p3, adobe-rgb-compat, prophoto-compat, linear-srgb, rec2020,
  gray-gamma-2.2, sgray, lab-d50, coated-cmyk` (casse indifférente) ou `working` ; un chemin .icc sinon — c'est la
  lecture arbitraire de t138. `engine.commands.enabled` suit l'état : Bitmap et Bichromie exigent Niveaux de gris, Table
  des couleurs exige Couleurs indexées, Multicouche refuse Indexées. Bichromie : un nombre d'encres différent du type est
  COMPLÉTÉ ou TRONQUÉ en silence (tritone + 1 encre -> « Warm Brown », « Gold »). Historique : « Mode Change », « Bit
  Depth », « Duotone », « Bitmap », « Multichannel », « Indexed Color », « Color Table ».
- `image.mode.colorTable {}` et `file.fileInfo {}` LISENT sans créer d'étape ; avec des clés, une étape.
- Flamme : `path` = NOM d'un tracé (`path.list`, « work » = tracé de travail) ; un nom inconnu est ignoré en silence
  (`usedPath:false`).
- Objets dynamiques : `doc.inspect` ne rend ni le contenu ni la transformation (rotation, échelle) — seulement `bounds`
  (effets compris).

## Décisions

| Entrée | Chez eux | Chez nous | Décision |
|---|---|---|---|
| Tout fermer / Fermer les autres | ferme, demande pour chaque document modifié | `file.closeAll` / `file.closeOthers` ; une confirmation liste les documents modifiés ; **onglets de documents** (tous ceux de la session, clic = `document.activate`, × ferme VRAIMENT) | **Repris** + onglets (jusqu'ici « Fermer » ne faisait que revenir à l'accueil : les documents s'empilaient dans le moteur) |
| Enregistrer une copie | fichier à côté, le document reste lié à l'original | `image.duplicate` -> `doc.save` -> `file.close` -> `document.activate` ; vers Téléchargement ou Bibliothèque (lignée vers l'image d'origine) | **Adapté** (destination Deepotus) |
| Revenir | relit le fichier enregistré, une étape annulable | rouvre le fichier du moteur (entrees/, exports/, biblio/, natif/) et ferme l'ancien : historique perdu, on le DIT dans la confirmation ; grisé sans fichier | **Adapté** |
| Exportation rapide PNG (Fichier) | PNG du document | /enregistrer png puis téléchargement | **Repris** |
| Placer incorporé | choisir un fichier, objet dynamique centré, réduit s'il dépasse, poignées de transformation | Bibliothèque -> `doc.open` d'une copie -> `edit.copy` -> `edit.paste {center}` -> objet dynamique -> réduit si plus grand -> transformation manuelle ouverte | **Adapté** (plusieurs étapes d'historique ; le presse-papiers du moteur est réécrit) |
| Informations sur le fichier | Titre, Auteur, Description, Mots-clés, Copyright… | dialogue prérempli par une lecture (sans étape), écriture = une étape « File Info » ; textes libres (aucun n'est lu comme chemin), URL http(s) seulement | **Repris** |
| Image › Mode (12) | conversions directes, coche du mode et de la profondeur, avertissement d'aplatissement ; Bitmap / Indexées / Bichromie / Table = dialogues | conversions directes (profil de travail) ; coches ; grisé = moteur ; confirmation « aplatit » (Bitmap, Indexées, Multicouche) si plusieurs calques ; Bitmap, Indexées = dialogue du registre ; **Bichromie** : type + encres (nom, couleur), courbes linéaires ; **Table des couleurs** : table lue, grille 16 × 16, préréglages, clic = couleur, transparence | **Repris** ; courbes d'encre **Adapté** (linéaires) ; pont : liste blanche PAR COMMANDE (`PERMIS_REFUSES`), `profile` limité aux ids intégrés, encres = type, table bornée |
| Faire correspondre la couleur | Source = autre document ouvert, calque | liste des AUTRES documents ouverts ; calque source = image fusionnée | **Adapté** |
| Déplacement | après OK, choisir un fichier de déplacement | liste des autres documents ouverts (`mapDocument`) ; `mapPath` refusé | **Adapté** |
| Flamme | exige un tracé | liste des tracés du document (ou aucun : toute la toile) ; le pont vérifie que le tracé existe | **Repris** |
| Calque › Exportation rapide PNG / Exporter sous | le calque seul, rogné ; format, échelle | copie du document, autres calques masqués, rognage du transparent, échelle -> PNG/JPG/WEBP ; téléchargement ou Bibliothèque | **Adapté** |
| Ouvrir en tant que | choisir le décodeur d'un fichier | la Bibliothèque ouvre par le contenu ; le moteur désactive la commande | **Écarté** |
| Remplacer / Exporter le contenu | contenu de l'objet dynamique | le moteur ne lit ni n'écrit le contenu, et ne rend pas la transformation : une composition perdrait rotation et échelle | **Bloqué moteur** |
| Lier de nouveau / Convertir en objet lié | objet lié à un fichier externe | aucun lien vivant possible (moteur désactivé, Bibliothèque sans liens) | **Bloqué moteur** |

Livrées : 24 sur 29 (+ onglets de documents). Restent « bientôt » : Ouvrir en tant que (écarté, `refuse:file.`) et les
4 commandes de contenu d'objet dynamique (bloquées, `sans_ecran` : leur seul champ est un chemin).

Pas de relevé à l'écran de la référence pour ce lot : ces dialogues sont des formulaires ordinaires et le moteur dicte
ses règles ; la structure retenue est dite ci-dessus.

## Relevé d'exécution (09/10/2026)

**Pont.** `photolab_moteur` : `PERMIS_REFUSES` (16 ids rouverts sous un préfixe refusé), `copie_document` et
`exporter_calque` (sur copie, `_sur_copie`), `revenir` (rouvre le fichier du moteur, ferme l'ancien par `index`),
`placer` (ouvre, copie, referme, colle au centre, objet dynamique, renomme, réduit), `verifier_trace` (Flamme, aussi dans
`/apercu`). `photolab_registre.verifier` : permis, `PROFILS_MODE` (profil = id intégré de l'espace, banc contre
`edit.profileInfo`), `_v_bichromie` (encres = type, nom, couleur, courbe), `_v_table` (index 0..255, 256 couleurs,
transparence), `_v_infos` (textes bornés, mots-clés, URL http(s)), `path` de la Flamme = nom de tracé. Routes `/copie`,
`/calque/exporter`, `/revenir`, `/placer` ; destination Bibliothèque = png/jpg, lignée « retouche ».

**Écran.** `mod-documents` (onglets de tous les documents : clic = activer, × = fermer vraiment, « • » par l'écran pour
l'actif et par le moteur pour les autres ; Tout fermer / Fermer les autres avec la liste des modifiés ; Revenir confirmé ;
Enregistrer une copie et Exporter sous (format, qualité, échelle, nom, destination) ; Exportation rapide (document et
calque) ; Placer depuis la Bibliothèque puis transformation manuelle ouverte ; Informations ; listes de choix du dialogue
générique), `mod-mode` (conversions directes, confirmation d'aplatir, coches, Bichromie, Table des couleurs),
`mod-dialogue-reglage` (`options.choix`, `PL.choixDialogue`), `mod-menus` (`PERMIS`, `IDS_DOCUMENTS`, famille « mode »),
`mod-champs` (`CHOIX_ECRAN`), `mod-fichier` (`PL.choisirImage`, ancien onglet unique et « Fermer » retirés).

**Défauts trouvés en route.** `select.rect` des sondes en `rect:[…]` échouait en silence (attend x, y, width, height) ;
`bounds` = [x, y, l, h] ; heredoc qui mange un antislash dans une expression rationnelle ; la famille « mode » n'était
pas distribuée par `activer()` (clic sur Niveaux de gris -> « bientôt ») : banc 6.6 qui exige chaque famille
d'OUVREURS ; deux documents du même nom indiscernables dans les listes de choix -> rang ajouté ; message « copie » pour un
export de calque -> clé propre.

**Bancs.** `test_photolab_fichier_mode` 120/120 (vrai moteur) ; QA `documents` 50 ; bancs figés mis à jour (registre 4c,
routes 15d, formulaires 2.3, champs 2.3-2.4 et 14.2, menus 2.5 et 8.7, textes 8 ; menus 7.3-7.5 neufs) ; libellés
(`photolab.param` / `photolab.valeur` des champs devenus visibles). `apropos` 3, `installeur` 2, `reglages_moteur` 2
rouges : mêmes comptes sur `main` nu (worktree détaché, moteur hors dépôt).
- Mutations : 20 sur 20 tuées (10 au pont, 10 à l'écran ; S2 a d'abord survécu -> cas 6.1b), sources restaurées et
  vérifiées par `cmp`.

**Preuve sur 8797** (vrai backend jetable, gestes par le DOM, EN puis FR ; capture d'écran impossible, volet masqué) :
onglets (3 documents, clic, ×), Fermer les autres, états du menu Fichier, Enregistrer une copie vers la Bibliothèque
(original inchangé), Image › Mode (coches RVB / 8 bits, grisés Bitmap / Bichromie / Table, Niveaux de gris direct,
Trichromie, Indexées avec confirmation d'aplatir puis formulaire, Table : transparence 3 relue au moteur), Informations
(lecture sans étape, URL file:// refusée), Flamme sur le tracé de travail (`path: "work"` envoyé), Correspondance et
Déplacement (listes de documents), Placer (640 × 400 -> 256 × 160 centré, transformation ouverte), export rapide du
calque (256 × 160), Exporter sous 50 % vers la Bibliothèque (128 × 80), Revenir (historique « Open »), Tout fermer.

**Recomptage** `lister_bientot.mjs` : 129 (153 avant) = 24 entrées livrées.

**Fiche d'aide.** Aucune : ce sont des entrées de menu et des dialogues, sans outil ni bouton à id stable à viser.
