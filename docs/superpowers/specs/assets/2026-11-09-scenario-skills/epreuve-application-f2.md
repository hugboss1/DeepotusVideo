# Épreuve d'application — fiches vidéo (lot F2, t477, 09/11/2026)

Protocole :
- **Agent** : un agent vierge (« Réalisateur »), sans accès au dépôt ni au web.
- **Lectures permises**, sur le backend de preuve (port 8794, sans clé, aucune dépense) :
  - `GET /api/ia/catalogue?nature=video_i2v` ;
  - `GET /api/modeles/index` ;
  - `GET /api/modeles/fiche`.
- **Trois briefs**. Pour chacun, il rend : modèle, prompt, réglages, coût estimé et suite.

## Résultat

| Brief | Choix | Conforme aux fiches |
|---|---|---|
| A. Teaser vertical 8 s d'une montre, prix à la fin | Veo 3.1 (brouillon Lite) ; repli Kling v3 Pro puis FLUX 3 Max | Oui : prix **jamais** dans le prompt, incrusté au Montage ; format dans le champ ; image de fin ; négatif sans « numbers » ; son ajouté au Montage |
| B. Deux plans enchaînés, budget serré | Seedance 1.0 Pro ; repli Kling v3 Standard | Oui : méthode N + 1 images de bord, toutes dérivées de l'image validée ; revue planche contact ; repli chez un autre fournisseur |
| C. Ambiance 20 s sous voix off | LTX 2.5 Fast ; repli Wan 3.0 | Oui : image fixe validée d'abord ; mouvement seul ; immobiles dits en positif ; clip muet sous la voix |

## Manques relevés et suite donnée

1. **Bloc « Membres » sans négatif ni son.** Corrigé : colonnes « nég. » et « son » (coupé / sans interrupteur), lues dans `VIDEO_MODELS`.
2. **Rapports de prix datés en contradiction avec le tableau** (Seedance « un à six », Veo « cinq fois »). Corrigé : renvoi au tableau Membres.
3. **Tension « ne jamais enchaîner une sortie » contre « partir de la dernière image » (Kling, Veo).** Corrigé dans `_commun` : la continuité (raccord) part de la dernière image, l'identité se vérifie toujours contre l'image validée.
4. **Orbite autour d'un objet vu sur une seule photo.** Ajouté dans `_commun` : les faces cachées sont inventées ; limiter l'angle ou donner une image de fin.
5. **Aucune fiche ne dit quel modèle d'image fabrique les images de départ et de fin.** Prévu au lot F3 (fiches image).
6. **Seedance 1.0 Pro avec image de fin passe par la variante Lite** : on ne sait pas si le prix, le seed et les résolutions changent. À relever (F6, tirs de preuve).
7. **Prix « au palier 720p » du catalogue** alors que certains membres ont un prix unique, et le champ `fl` non documenté pour un agent. Hors fiches : à reprendre en F5 (`recommander_modele`).
8. **Tailles de prompt opposées entre familles** (Veo long, MiniMax court) lors d'un repli « même prompt ». À traiter en F5 (`verifier_prompt`, réécriture par famille).
