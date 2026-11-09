# Fiches modèle Deepotus, d'après scenario-labs/skills — conception (09/11/2026)

Statut : **questions ouvertes tranchées le 09/11/2026** (voir §7) ; protocole du banc Atelier DA en §8. Rien n'est
codé. Plan : `docs/superpowers/plans/2026-11-09-fiches-modeles.md`.

Sources relues le 09/11/2026 :
- `AGENTS.md` de https://github.com/scenario-labs/skills (commit b96506d, 08/11/2026).
- Les **171 skills** du dépôt : 84 skills cœur, lus en entier avec leurs `references/`, et 87 skills experts
  (Blender, Maya, ZBrush, Unity, Unreal, Godot, Roblox), survolés pour ce qui touche aux modèles.
  Le relevé fait environ 42 000 mots et 1 300 faits étiquetés, rangés dans
  `docs/superpowers/specs/assets/2026-11-09-scenario-skills/` :
  `images.md`, `video.md`, `audio_3d.md`, `transverse.md`, `appliques_experts.md` et `index-skills.txt`.
- Côté Deepotus (origin/main 9ccd9224) :
  - les registres `fal_service.VIDEO_MODELS`, `image_providers.FAL_IMAGES`, `pricing._IMAGE_MODELS`,
    `music_service.MUSIC_MODELS`, `elevenlabs_service.ELEVEN_MODELS`, `catalogue_ia` ;
  - l'outil d'agent `modeles_video` ;
  - les fichiers `docs/agent/AGENT.md`, `docs/agent/metiers/*.md`, `knowledge/methodes.json` et `docs/licences/scenario-mit.md`.

« Modèles » désigne ici les **modèles d'IA** : leurs listes, leurs paramètres et la connaissance de leur usage.
Ce n'est pas l'écran Modèles des mises en page.

---

## 1. Ce que dit l'AGENTS.md de Scenario, et ce qu'on en garde

Le fichier est le **contrat d'écriture** d'une bibliothèque de connaissances procédurales : les skills, chargés par
un agent à la demande. Huit idées se transposent ; le reste est propre à leur dépôt public.

| Idée de Scenario | Chez Deepotus aujourd'hui | Adaptation proposée |
|---|---|---|
| Chargement progressif : seuls `name` et `description` sont toujours lus, le corps n'entre qu'au déclenchement | `AGENT.md` est plafonné à 24 650 caractères et plein, et l'agent ne sait rien des modèles | Un **index** court des fiches (famille + « À utiliser quand… ») ; le corps se lit par un outil, à la demande |
| Budget de mots par corps (cible 1000, refus au-delà de 2500), plan fixe : aperçu, référence rapide, exemple, erreurs fréquentes | Rôles métier d'environ 300 mots, sans plan commun | Fiche de 600 mots en cible et 1200 au plus, en quatre parties, contrôlée par un banc |
| Une famille = une fiche, sans numéro de version : « les versions sont des données, pas une identité » | Les ids versionnés sont dans les registres, sans fiche | Fiches `seedance`, `kling`, `veo`… ; les membres et leurs plafonds sont **lus dans le registre**, jamais recopiés en dur |
| Ne jamais nommer un modèle génératif dans une méthode : on demande une **capacité**, on résout par `recommend` | Les rôles métier ne nomment déjà presque aucun modèle (une mention de Seedance dans monteur.md) | Règle écrite, contrôlée par un banc ; résolution par un outil `recommander_modele(nature, consigne)` |
| Exceptions : les outils déterministes maison sont nommés en dur, avec la raison | — | Exceptions Deepotus : ffmpeg, rembg local, htdemucs, Photolab, briques locales |
| Toute étape payante dit ce qui se passe sans surveillance : budget ou décompte donné, sinon prix et arrêt ; ne jamais promettre une confirmation que le serveur n'impose pas | Devis, `plafonds.verifier` et `confirme_cout` existent déjà | Inchangé. Chaque fiche dit en plus « brouillon d'abord » quand le membre le permet |
| Le devis `recommend` est modélisé (48,2 annoncés, 55 facturés) ; `dry_run` donne le prix exact | `pricing.estimate` est lui aussi modélisé | Une fiche dit quand l'écart est connu, par exemple pour la facturation aux jetons de Seedance 2.5 |
| Validation en deux temps : contrôle **mécanique** (format, budget, liens), puis **épreuve d'application** (agent vierge, cas réel, transcription notée ; variante `--plan-only` gratuite) | Bancs pytest ; un backend de preuve sans clé Anthropic | Banc `test_modeles_fiches`, puis épreuve d'application gratuite sur le backend de preuve (choix + prompt + devis, sans tir) |

Règles d'écriture reprises telles quelles, parce qu'elles servent aussi un lecteur LLM :
- un fait par phrase ;
- garder les mots de condition (seulement, sauf, jamais, avant) ;
- n'expliquer que pour éviter une erreur ;
- dire une fois, puis lier ;
- ne prudencer qu'un chiffre qui change, avec sa date ;
- un seul nom par chose, selon un glossaire : modèle, famille, membre, voie, jumeau, nature, tir, devis, fiche, boîte, outil.

**Non repris** :
- les règles de dépôt public (pnpm, cspell, commitlint, release-please, marketplace) ;
- l'interdiction du tiret cadratin, contraire à la typographie française du dépôt ;
- l'anglais américain ;
- l'interdiction de nommer des modèles dans les fiches elles-mêmes : une fiche Deepotus EST la fiche d'une famille, comme le « membre dédié » chez eux.

### Où vit la version Deepotus

- `docs/agent/modeles/MODELES.md` porte le **contrat des fiches** : format, budget, règles, glossaire, validation.
  C'est l'équivalent de leur AGENTS.md, réduit à ce qui sert ici.
- `docs/agent/modeles/<famille>.md` porte une fiche par famille.
- `docs/agent/modeles/README.md` sert aux mainteneurs : sources, dates de relevé, mentions MIT. L'agent ne le lit pas,
  comme leurs README de skill.
- `AGENTS.md` (racine) reçoit une ligne dans « Fichiers clés » et une règle : « tout nouveau modèle = entrée de registre
  + prix + membre d'une fiche ».

---

## 2. Format d'une fiche

```markdown
---
famille: seedance
natures: [video_i2v, video_fl]          # natures de catalogue_ia
ids: [seedance-v1-pro, seedance-2, seedance-2-fast, seedance-2.5]   # contrôlés par le banc
description: À utiliser quand une vidéo doit garder un mouvement continu, une chorégraphie, ou partir d'une image et finir sur une autre…
voies: [fal]
releve: 2026-11-09
source: scenario-seedance, scenario-seedance-drafts, scenario-seedance-storyboard (MIT)
---
## Aperçu            (3 à 5 lignes : ce que la famille fait mieux que les autres)
## Référence rapide  (puces [PROMPT] [PIÈGE] [CHOIX] [COÛT] ; AUCUN plafond chiffré du registre)
## Exemple           (un brief → le prompt écrit pour ce modèle → les réglages)
## Erreurs fréquentes
```

Au moment de servir la fiche, l'outil **ajoute** un bloc « Membres » généré depuis le registre : durées, ratios,
résolutions, image de fin, audio, négatif, seed, prix, clé présente ou non. Un chiffre du registre n'est donc jamais
écrit deux fois.

**Tronc commun** (`docs/agent/modeles/_commun.md`, servi avec chaque fiche) : les règles valables pour toutes les
familles, relevées dans les cinq lots.

- **Écriture du prompt**
  - Écrire en phrases, pas en tags.
  - Formuler en positif : un mot présent dans le prompt dessine ce qu'il nomme (« no gray » fait du gris).
- **Ratio** : il va dans le champ prévu, jamais dans le texte du prompt, sinon on obtient des bandes noires.
- **Texte dans l'image**
  - Citer le texte entre guillemets, avec son rôle et sa place, et finir par « no other text ».
  - Un prix, une mention légale ou un logo n'est **jamais** généré : il passe par une incrustation (Templates, Montage).
- **Retouche**
  - Écrire « change only X », suivi de ce qui doit rester. Répéter cette liste à chaque passe.
  - Une seule modification par passe.
- **Références** : chaque référence reçoit un rôle selon sa position. L'identité passe par une référence unique, jamais
  par un chaînage sortie → sortie.
- **Vidéo à partir d'une image**
  - Ne décrire que le mouvement.
  - Une caméra et une action par plan.
  - Des horodatages quand il y a plusieurs temps.
- **Son** : nommer les sons en positif. « No music » fait échouer la modération audio ; couper l'audio par l'interrupteur.
- **Méthode** : image fixe approuvée → animation depuis cette image → relance depuis l'image approuvée, jamais depuis
  une sortie qui a dérivé.
- **Modération**
  - D'abord changer de **fournisseur**, à coût voisin : les membres d'une même famille partagent le filtre.
  - Ensuite seulement, une réécriture honnête, puis arrêt.
  - Ordre de sévérité relevé : Google, puis ByteDance, OpenAI, Ideogram et Hunyuan, puis FLUX et Recraft.
  - Le jumeau de voie (direct ↔ fal) est le premier recours.
  - Un rendu vidéo refusé est facturé.

---

## 3. Ce qu'il faut ajouter dans l'application

### A. Connaissance (nouveau ; aucun code de fournisseur touché)

Fiches à écrire, une par famille : environ 30 fiches pour couvrir **tous** les ids des registres.

- **Image**
  - gpt-image
  - nano-banana (Gemini image)
  - flux
  - seedream
  - ideogram
  - qwen-image
  - recraft (vecteur)
- **Vidéo**
  - seedance
  - kling
  - veo
  - wan
  - minimax-video (h3-max)
  - ltx
  - pixverse
  - gemini-omni
  - flux-3-max
- **Son**
  - elevenlabs (voix, effets, musique)
  - minimax-music
  - lyria
  - stable-audio
  - ace-step
  - mureka
  - cassetteai
  - hunyuan-foley
  - séparation (htdemucs)
- **3D**
  - meshy
  - rodin
  - tripo
  - hunyuan3d
  - trellis/triposr
  - sam3-objets
- **Détourage** : un seul `detourage` pour rembg, matte, bria et birefnet.

Le contenu de chaque fiche est déjà relevé dans les cinq fichiers de notes : environ 1 300 faits, chacun étiqueté
PROMPT, PARAM, PIÈGE, CHOIX, COÛT ou MÉTHODE.

### B. Outils d'agent (nouvelle boîte « modeles », lecture, gratuite)

| Outil | Rôle | Remplace / complète |
|---|---|---|
| `modeles_lister(nature)` | Liste d'une nature de `catalogue_ia` : prix, voie, clé présente | Généralise `modeles_video`, qui reste en alias |
| `modele_fiche(famille ou id)` | Corps de la fiche + tronc commun + bloc « Membres » généré | — |
| `recommander_modele(nature, consigne, contraintes)` | Classe les membres : filtre par plafonds (durée, ratio, image de fin, références, audio, clé), puis règles CHOIX des fiches, puis prix ; donne un premier choix, une alternative chez **un autre fournisseur** (modération) et la mention « brouillon d'abord » | L'équivalent de leur `recommend` |
| `verifier_prompt(id, prompt)` | Relecture **sans LLM** : tags, ratio écrit en prose, « no music », prix ou mention légale promptés, négatifs en clair, longueur au-delà du plafond du membre | — |

La boîte est donnée aux 9 agents métier et au MCP, comme « methodes » et « briques ». Le banc
`test_agent_outils` est à ajuster.

### C. Paramètres à exposer sur les modèles existants (« renforcer »)

Priorité 1 : le gain est fort et le coût de code faible.

1. **Palier de qualité** pour GPT Image 2 et 2.5 (direct et fal) et Ideogram 4.5. Il est figé à `high` aujourd'hui.
   C'est le premier levier de coût : de low à max, environ 1 à 22 chez GPT, et high coûte environ 3 fois medium chez
   Ideogram. Il permet le « brouillon bas, final haut ».
2. **Ideogram `magic_prompt` coupable** : sinon il paraphrase le texte exact.
3. **GPT Image via fal en plusieurs références** : une seule image est envoyée aujourd'hui ; Sunburst en accepte
   jusqu'à 10.
4. **Résolution de Nano Banana** (512 à 4K) et ses 14 références : Deepotus en plafonne 9.
5. **Seedance 2.5 brouillon puis finalisation 1080p** : l'id du brouillon se garde 7 jours. C'est rentable seulement si
   l'on jette des prises.
6. **Modèles sans interrupteur audio** (h3-max, gemini-omni, kling-v4, kling-v3-turbo-pro) : ils livrent toujours une
   piste. Le marquer dans le registre (`audio_force`) pour que le Montage la remplace.
7. **Meshy** : `pose_mode`, `should_remesh` et `target_polycount` (sans effet sans remesh), image de texture
   prioritaire sur le texte. **Rodin** : palier et HighPack. Cible relevée pour un objet de jeu : 10 000 à 50 000
   triangles.
8. **Musique** : `bpm`, instrumental par drapeau et non par le texte, paroles hors du champ style. Pour MiniMax :
   `lyrics_optimizer` et une facturation d'environ 700 caractères de paroles par minute.
9. **Voix ElevenLabs** : les balises d'émotion en ligne ne marchent que sur eleven_v3. Sur Multilingual et Flash,
   elles risquent d'être **lues à voix haute** : à filtrer ou à signaler.
10. **Fond transparent** (`background`) sur les modèles image qui le permettent : un fond transparent demandé dans le
    texte du prompt sort opaque.

Priorité 2 : des modes entiers manquent. Deepotus ne fait que de l'image→vidéo, avec ou sans image de fin.

- **Références d'identité**
  - Seedance 2.5 R2V, jusqu'à 30 images.
  - Veo, références ASSET et STYLE.
  - Kling O1 et elements.
  - Gemini Omni R2V.
  - Règle : « ouverture exacte → image de départ ; identité → références ».
- **Multi-plan Kling** (`multi_prompt`, déjà hors registre), **prolongation** (Veo, Gemini Omni, MiniMax Extend) et
  **texte→vidéo**.
- **Recadrage et extension génératifs** (image et vidéo) pour la déclinaison des formats.

### D. Modèles candidats à ajouter

Ces candidats sont cités par les skills mais absents de Deepotus. Leur présence sur fal est à vérifier par le skill
`balayage-fournisseurs-fal` **avant** toute entrée de registre. Rien n'a été vérifié en ligne ici.

- **Image**
  - Seedream 5.0 Lite et Flash, Seedream 4.5, Seedream Layerize Flash
  - Ideogram : Precise Edit, Transparent, Layerize Text, Character
  - Reve v2.1 et Remix
  - Luma Uni-1
  - Grok Imagine Image
  - Gemini 3.1 Lite
  - GPT Image 1.5
  - MAI Image 2.5 : présence sur fal inconnue
  - upscalers fidèles (Topaz, Clarity)
  - Retro Diffusion (pixel art)
  - Flux 2 Dev et Klein, Z-Image, avec leurs **entraîneurs LoRA**
- **Vidéo**
  - Kling O1, Omni, Motion Control, Avatar
  - Wan 2.2 Animate et Reframe, Wan 2.7 Edit
  - MiniMax H3, Extend, Recast
  - Vidu Q3
  - Luma Ray 3.2, avec Edit et Reframe
  - Grok Imagine Video
  - lip-sync et audio→vidéo (OmniHuman, Wan-S2V, Sync)
  - Runway Gen4.5 et Aleph : présence sur fal incertaine
- **Son**
  - ACE-Step 1.5 : Cover, Repaint, prolongation
  - MiniMax Music Cover
  - Sonilo (musique et son depuis une vidéo)
  - ElevenLabs : Dubbing, Speech-to-Speech, Music par sections, clonage de voix (en direct)
  - Whisper ou Wizper pour les sous-titres
- **3D et mondes**
  - Sparc3D et Hitem3D (maillages étanches)
  - Tripo 3.1 multi-vues et texturation
  - mondes en Gaussian splats (Marble, HunyuanWorld, TripoSplat)
  - skybox 360 avec upscaler qui préserve la couture
- **Hors de portée** : les outils maison de Scenario (PATINA, Caption Studio, compositeurs, GPT-6 Astra 3D « maison »)
  n'existent pas hors de Scenario. On n'en garde que la méthode.

### E. Écarts à revérifier dans nos registres (aucune correction sans relecture du schéma fal)

- **h3-max** : la skill plafonne Max à 768P, notre registre propose 1080P. L'offre Scenario peut différer de fal.
- **gemini-omni** : la skill dit que le prix ne dépend pas de la résolution, alors que `pricing.py` chiffre 720p et
  1080p différemment.
- **Plafond de prompt** de h3-max : 2000 caractères. À reprendre dans `verifier_prompt`.
- **Atelier DA** : son « chaînage d'identité » (sortie → sortie) est l'inverse de ce que la skill consistency
  recommande : base unique + delta. À arbitrer.

---

## 4. Validation

- **Banc `test_modeles_fiches`** :
  - chaque id des registres appartient à une seule fiche ;
  - chaque id cité par une fiche existe ;
  - la description commence par « À utiliser quand » et fait 500 caractères au plus ;
  - le corps fait 1200 mots au plus ;
  - les quatre parties sont présentes ;
  - aucun plafond du registre n'est recopié en dur (durées, ratios) ;
  - `metiers/*.md` et `methodes.json` ne nomment aucun modèle génératif hors de la liste blanche des outils locaux ;
  - la mention MIT est présente quand la fiche s'inspire d'un skill.
- **Mutations** : retirer un id d'une fiche, ou y écrire une durée fausse, doit faire rougir le banc.
- **Épreuve d'application** (gratuite) : sur le backend de preuve sans clé, cinq briefs types sont soumis à l'agent :
  - teaser vertical ;
  - visuel avec prix ;
  - personnage récurrent ;
  - musique avec paroles ;
  - objet 3D de jeu.

  On note le modèle choisi, le prompt et le devis : respect des fiches, aucun tir.
- **Assistant F1** : une ligne dans `AGENT.md`, qui reste sous son plafond, et une mise à jour par le skill
  `connaissance-agent`.

## 5. Droits

Les **171 skills** du dépôt sont publiés sous MIT : chaque `SKILL.md` porte `license: MIT`. Les fiches **reformulent**
des faits ; elles ne copient pas de texte. Chaque fiche porte sa ligne `source:`. `docs/licences/scenario-mit.md` est
mis à jour avec le lot « fiches modèle » et le texte de la licence MIT, à joindre si un texte ou un script est un jour
adapté, par exemple les looks `.cube` du color-grade.

## 6. Découpage initial (remplacé par le découpage révisé du §7 ; numéros à attribuer au suivi, à partir de t475)

| Lot | Contenu | Dépense |
|---|---|---|
| F0 | `MODELES.md` (contrat), `_commun.md`, glossaire, banc `test_modeles_fiches` vide-mais-strict, ligne AGENTS.md | 0 |
| F1 | Outils `modeles_lister`, `modele_fiche`, boîte « modeles » chez les 9 agents + MCP | 0 |
| F2 | Fiches vidéo (9) | 0 |
| F3 | Fiches image (7) + détourage | 0 |
| F4 | Fiches son (10) et 3D (6) | 0 |
| F5 | `recommander_modele` + `verifier_prompt` ; épreuve d'application | 0 |
| F6 | Paramètres priorité 1 (§3.C 1-10), un par un, schéma fal relu à chaque fois | tirs de preuve, sur accord |
| F7 | Balayage fal des candidats (§3.D) → entrées de registre retenues | 0 pour le relevé |
| F8 | Modes priorité 2 (références, multi-plan, prolongation, recadrage) | sur accord |

F0 à F5 ne touchent aucun appel payant ni aucun maillon de bundle. F6 à F8 suivent la règle « nouveau modèle =
entrée VIDEO_MODELS + prix ; menus et agent suivent ».

## 7. Décisions de l'utilisateur (09/11/2026)

1. **Les fiches sont montrées à l'utilisateur**, donc elles existent en **FR et en EN** :
   `docs/agent/modeles/fr/<famille>.md` et `en/<famille>.md`, avec le même front-matter et le même plan. Le banc
   vérifie la parité entre les deux langues. Un « ? » à côté du sélecteur de modèle ouvre la fiche de la famille du
   modèle choisi :
   - lot F1 : dans `DzModelesIA` (pages à part) et `dz-champ-ia` ;
   - plus tard : dans les sélecteurs du bundle.
2. **Ordre** : F0 → F1 → **F2 fiches vidéo** → **F6 réglages de coût** → **FDA Atelier DA** → F3 → F4 → F5 → F7 → F8.
3. **L'Atelier DA est traité dans ce chantier**, par un banc comparatif mesuré (§8) **avant** toute modification de
   la méthode par défaut.

Découpage révisé :

| Lot | Contenu | Dépense |
|---|---|---|
| F0 | Contrat `MODELES.md`, `_commun.md` FR/EN, glossaire, banc `test_modeles_fiches`, ligne AGENTS.md | 0 |
| F1 | `/api/modeles/fiche`, outils `modeles_lister` et `modele_fiche`, boîte « modeles », « ? » des sélecteurs à part | 0 |
| F2 | 9 fiches vidéo FR/EN | 0 |
| F6 | Réglages de coût (§3.C 1-10), un par un, avec le schéma fal relu | tirs de preuve, sur accord |
| FDA | Banc comparatif de l'Atelier DA (§8), puis décision, puis bascule éventuelle | environ 7,5 $, plafond 10 $, sur accord |
| F3 | Fiches image + détourage | 0 |
| F4 | Fiches son + 3D | 0 |
| F5 | `recommander_modele`, `verifier_prompt`, épreuve d'application | 0 |
| F7 | Balayage fal des candidats | 0 |
| F8 | Modes manquants (références, multi-plan, prolongation, recadrage) | sur accord |

---

## 8. Banc comparatif de l'Atelier DA : actuel contre méthode « cohérence »

### Ce que fait le code aujourd'hui (`routes.generate_bible_reference`, `board_service.PANEL_PLANS["character"]`)

- **Visage de face** : c'est le maître (texte → image), avec seed.
- **Profil gauche du visage** : édité depuis le visage de face. C'est une référence directe (profondeur 1).
- **Corps de face** : édité depuis le visage de face (profondeur 1), avec le cadre du canon et un contrôle de
  proportions qui peut relancer jusqu'à 2 fois.
- **Corps profil gauche et corps de dos** : édités depuis le **corps de face**, qui est lui-même une sortie
  (**profondeur 2**). C'est le chaînage d'une sortie sur une autre que la skill consistency déconseille : la dérive
  s'additionne.
- **Profils droits** : obtenus par miroir logiciel, ce qui est déjà conforme.
- **Prompts des panneaux dérivés** : un rappel court (« the exact same person… ») plus le style. Ils ne listent pas les
  éléments à conserver, et l'interdit est écrit en négatif (« absolutely no text, no titles, no lettering »).
- **Une seule image de référence par édition**, quel que soit le fournisseur, alors que Nano Banana 2.1 en accepte 14.

### Ce que la skill consistency change (trois écarts, testés séparément)

1. **Héros validé** : le corps de face ne sert d'ancre qu'**après** un contrôle d'identité face au visage maître. S'il
   dérive, on le régénère. Les vues dérivées partent toutes de ce héros validé, jamais d'une sortie non contrôlée.
2. **Base + delta** :
   - Un texte de base est écrit **une fois**, après avoir regardé le maître. Il liste ce qui ne change pas : coiffure,
     yeux, peau, chaque pièce de tenue et sa couleur, accessoires, palette, lumière.
   - Ce texte est **identique à l'octet** d'un panneau à l'autre. Seule la clause finale change : la vue.
   - La formulation est positive (« plain unlettered studio background ») au lieu de « no text ».
3. **Plusieurs références**, seulement sur les modèles qui les acceptent : chaque vue du corps reçoit **visage maître et
   corps validé**, avec un rôle par position (« image 1 = face identity, image 2 = outfit and proportions »).

### Bras du banc

| Bras | Méthode | Fournisseurs |
|---|---|---|
| A | Code actuel, inchangé | flux (Kontext), nano-banana-2.1 |
| B | Écarts 1 + 2 (une référence) | flux (Kontext), nano-banana-2.1 |
| C | Écarts 1 + 2 + 3 (plusieurs références) | nano-banana-2.1 seulement (Kontext n'a qu'une entrée) |

**Isolation de la variable :**
- Pour un personnage et un fournisseur donnés, les trois bras partent du **même visage maître**, généré une seule fois
  et partagé.
- Avec flux, les panneaux qui se correspondent reçoivent le même seed.
- Nano Banana n'a pas de seed : chaque bras est joué **2 fois** pour mesurer la variance.

**Corpus** : 3 personnages, choisis parce qu'ils dérivent différemment :
- un réaliste, si tu es d'accord **Elias du teaser CHARGE**, à partir de son image de référence existante ;
- un manga ;
- un ligne claire à gros nez.

**Volume** :
- 3 personnages × (2 bras flux + 3 bras nano) × 2 répétitions = **30 planches** ;
- chaque planche compte 4 panneaux générés, soit environ **120 images**, plus 6 maîtres.

### Mesures (choisies AVANT le tir)

| Mesure | Comment | Coût |
|---|---|---|
| M1 Identité grossière | Similarité CLIP (le moteur de la Bibliothèque) de chaque panneau à son ancre : visage → visage maître, corps → corps de face | 0 |
| M2 Couleurs de la tenue | Écart ΔE des couleurs dominantes des panneaux corps contre le corps de face (`board_service._palette_colors`) | 0 |
| M3 Grille par élément | Avis vision **à l'aveugle** (`briques` avis, bras masqués et ordre tiré au hasard) : pour chaque élément listé depuis le maître, un verdict parmi conservé, perdu, recoloré, déformé ou ajouté, comme le prescrit la skill. Le juge note aussi le texte parasite, le double visage et le profil du mauvais côté | environ 1 $ |
| M4 Dérive cumulée | Écart de M1 et M3 entre les panneaux de profondeur 2 (profil et dos) et ceux de profondeur 1, dans chaque bras | 0 |
| M5 Proportions | Nombre de têtes mesuré par le contrôle de proportions existant, et nombre de relances | déjà inclus |
| M6 Coût et temps | Dépense réelle par planche (registre), durée | 0 |
| M7 Vote humain | Page locale `vote.html` : pour chaque personnage et fournisseur, les planches en paires, sans étiquette et dans un ordre tiré au hasard. Tu choisis la plus fidèle, ou « égal ». Le vote est enregistré en JSON | 0 |

### Règle de décision (écrite avant le tir)

B remplace A comme méthode par défaut si les trois conditions suivantes sont réunies :
- le score M3 de B est supérieur d'au moins 10 % à celui de A en moyenne, sans être pire de plus de 5 % sur aucun
  personnage ;
- B gagne au moins 60 % des votes M7 non égaux ;
- le coût M6 de B ne dépasse pas celui de A de plus de 20 %.

C remplace B pour les fournisseurs à références multiples selon la même règle, appliquée contre B. M4 sert à
**expliquer** le résultat, pas à décider. Si aucune règle n'est remplie, A reste en place et le rapport dit pourquoi.

### Mise en œuvre et livrables

- **Paramètre interne `methode`** de la route de la planche : « actuel », « ancre » ou « ancre_multi ».
  - Il vaut « actuel » par défaut tant que la décision n'est pas prise.
  - Il est enregistré dans la recette, si bien qu'une recette rejouée garde sa méthode.
- **Script `scripts/banc_da_coherence.py`**, lancé sur le backend de preuve.
  1. Il écrit d'abord le **devis** (environ 7,5 $, plafond 10 $) et s'arrête.
  2. Avec `--confirme`, il tire dans la limite de `max_usd`, sous `plafonds`.
  3. Il range les résultats dans `outputs/bancs/da-coherence-<date>/` : les planches, `mesures.json`, `rapport.md` et
     `vote.html`.
- **Rapport** : un tableau par mesure et par bras, les planches côte à côte, et la décision appliquée selon la règle.
- **Bascule** : seulement après le vote et le rapport, dans une PR séparée. On change le défaut de `methode` ; les
  anciennes recettes restent rejouables.
