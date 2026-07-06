# Atelier — Adaptation roman → scénario + casting voix + VO minuté (design)

Date: 2026-07-06 · Base: Agent Manuscrit (spec 2026-07-06) · Décisions user:
VO **hybride audiobook** (Narrateur lit la prose, dialogues joués par les
voix castées) ; livraison **A → B → C** séquentielle.

## A. Passe Scénario (CETTE PR — v1.20)
Le manuscrit a vocation lecture/écoute ; le film exige un script. L'agent
adapte chaque chapitre en scènes Fountain SANS toucher au manuscrit :
- Table `scenes`: slugline (INT/EXT + LIEU bible + moment), fountain_text,
  lighting (vocabulaire Lighting de l'app, motivé par le narratif),
  camera_notes (vocabulaire CameraMove + justification), mood, entités en
  scène (personnages + décors — créés dans la bible au besoin →
  RÉUTILISATION inter-chapitres), source_excerpt (traçabilité), duration_s
  + vo_audio (remplis par C).
- Doctrine embarquée dans le prompt (fountain.io, StudioBinder, Story Sense,
  guides d'adaptation): show don't tell, scène à double fonction minimum,
  sluglines standard, action ≤4 lignes au présent, dialogues en sous-texte,
  parentheticals sobres, 1 page ≈ 1 min, scènes 15-90 s.
- Routes: POST /chapters/{id}/screenplay/adapt (job arrière-plan, store
  commun /atelier/manuscript/{jid}), GET /chapters/{id}/scenes, GET
  /chapters/{id}/screenplay (+ ?format=fountain téléchargeable), PUT
  /scenes/{id} (slugline recomposée).
- UI: onglet « Scénario » (Script | Scénario | Storyboard) — cartes scène
  éditables (INT/EXT, moment, éclairage, mood, caméra, corps Fountain),
  chips entités, export .fountain.

## B. Casting voix (PR suivante)
Chaque personnage: voix ElevenLabs suggérée (croisement fiche personnage ×
labels des voix du compte) + 3-5 alternatives du même profil + ▶ pré-écoute
+ accès liste complète. Entité « Narrateur » auto-créée avec sa voix.
Colonnes voice_id/voice_name/voice_alts sur bible_entities.

## C. Voice-over minuté (PR d'après)
Par scène: synthèse multi-voix (narration = Narrateur lisant la prose du
manuscrit correspondante, dialogues = voix des personnages, ton/vitesse/
intensité depuis la bible), assemblage ffmpeg par scène → Library audio,
durée mesurée → scene.duration_s → le storyboard P2 et la production P3 se
calent sur ces temps (méthode animatic).
