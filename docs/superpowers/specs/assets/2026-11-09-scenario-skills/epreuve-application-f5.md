# Épreuve d'application — conseiller sans LLM (lot F5, t492, 10/11/2026)

Protocole :
- **Agent** : un agent vierge (« Producteur »), sans accès au dépôt ni au web.
- **Lectures permises**, sur le backend de preuve (port 8794, sans clé, aucune dépense) :
  - `GET /api/ia/catalogue`, `GET /api/modeles/index`, `GET /api/modeles/fiche` ;
  - `POST /api/modeles/recommander` et `POST /api/modeles/verifier`.
- **Méthode imposée** pour chaque brief : recommander, lire la fiche du choix, écrire le prompt, le passer à
  `verifier` jusqu'à zéro erreur, puis dire son accord ou son désaccord avec la recommandation, fiche à l'appui.
- **Cinq briefs** : clip parfum 9:16 de 6 s avec image de fin et budget 1 $ ; affiche « SOLDES D'HIVER -30 % » avec
  trois brouillons pas chers ; voix off anglaise enjouée avec un rire ; chanson de 60 s avec paroles en français ;
  détourage d'un personnage aux cheveux bouclés puis modèle 3D riggable en FBX.

## Résultat avant correctifs

| Brief | Recommandation | Avis de l'agent |
|---|---|---|
| 1. Clip parfum | Kling v3 Standard | Désaccord : Kling n'a pas de champ format ni de seed ; Veo (brouillon Lite, final Fast) tient tout sous 1 $ |
| 2. Affiche soldes | GPT Image 1 mini | Désaccord : le devis comptait les autres au palier high ; Ideogram ou GPT 2.5 au palier low |
| 3. Voix enjouée | Eleven v3 (avec `balises`) | Accord |
| 4. Chanson 60 s | MiniMax Music 2.0 | Désaccord : 2.0 choisit seul sa durée ; MiniMax 3, ACE-Step en maquette |
| 5. Cheveux puis 3D | Ideogram, puis Rodin | Désaccord sur le détourage (la fiche nomme BiRefNet) ; accord partiel sur Rodin (2.5 au même prix) |

Les vérifications ont corrigé de vrais défauts dans les premiers jets : « 9:16 » en prose, « no music », négatifs en
clair, « with no text ».

## Manques relevés et suite donnée

1. **Mots de la consigne plus forts que l'adéquation.** Corrigé : une contrainte tenue par un CHAMP du membre (format
   listé, image de fin, seed, négatif) ajoute au score ; un format demandé à un membre sans champ format porte un
   avertissement (« le cadre suit l'image de départ »).
2. **Devis au palier par défaut.** Corrigé : contrainte `qualite` (un palier, ou « bas ») ; « brouillon », « pas
   cher », « draft » dans la consigne règlent le devis au palier le plus bas (hypothèse rendue) et ne comptent plus
   comme mots de pertinence.
3. **Durée non réglable non écartée** (MiniMax 2.0 et 2.6). Corrigé : écartés quand une durée est demandée.
4. **Prix à mesurer pénalisé sans le dire.** Corrigé : avertissement « prix à mesurer » ; quand la fiche nomme le
   membre pour la consigne (cheveux → BiRefNet v2), il passe devant.
5. **Classement tronqué à 8.** Corrigé : tout le classement est rendu.
6. **Contraintes illisibles (« six ») en 500 ; inconnues ignorées en silence.** Corrigé : refus nommé (400 sur la
   route, refus de l'outil) ; les clés inconnues sont rendues dans `ignorees` ; valeurs de défaut rendues dans
   `hypotheses`.
7. **Raison de durée fausse** (PixVerse 6 s « hors de 5–8 s »). Corrigé : les durées permises sont listées.
8. **`verifier`** : « -30 % » non vu, « square format » non vu, « with no text » en faux positif, consigne entre
   parenthèses sur v3 non vue, crochet hors palette seulement averti, description vide de SAM 3 non vue, message de
   format faux pour un membre sans champ format. Tous corrigés.
9. **Restent ouverts** (pas de donnée fiable au registre) :
   - plafond et longueur visée du prompt de Veo (la fiche dit 90 à 250 mots, sans chiffre au registre) ;
   - musique : la vérification ne distingue pas description et paroles ;
   - Seedance 1.0 Pro avec image de fin servi par sa variante Lite (prix, seed) ;
   - `pose_rig` trop strict pour une image déjà en A-pose (Hunyuan) ; rig : clé et coût ;
   - chaînes de natures (détourage → retouche → 3D → rig) : pas de planificateur, les méthodes s'en chargent ;
   - texte d'image sans guillemets, absence de « no other text ».
