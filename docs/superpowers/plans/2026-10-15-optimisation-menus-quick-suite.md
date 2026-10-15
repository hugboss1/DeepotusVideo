# Optimisation des menus — 1 bis. Quick, retours sur l'aperçu (t217-t218)

Date : 15/10/2026. Lot du suivi : « Menus : Quick » (prio 1). Retours de l'utilisateur après l'installation de t216 :
« pas juste l'image qui s'agrandit, mais la fenêtre entière du display, zoomée ET réduite à la molette » ; « sur la Voix
off, une animation de voix off professionnelle dans le display ». Choix de l'utilisateur sur maquette : **B · orbe vocal**.

## Relevé (origin/main ca775a7b)

- L'aperçu est une IIFE de `um` : zone (`position:relative`, flex centré, padding 24, `overflow:hidden`) → fond radial →
  CARTE (`{...je, background:"linear-gradient(160deg, #053040 0%, #02060d 80%)"…}`, hauteur 460 ou largeur 420) qui
  contient la trame, l'en-tête (badge « 9:16 · aperçu », « 1080 × 1920 »), le contenu `DzQuickStage(…)||repli` et le pied
  (« seed:… », « mode · durée ») ; puis la ligne de coût (hors Voix off).
- t216 (maillon dzquick, Z0-Z2) n'enveloppe que le CONTENU : c'est l'image qui zoome, pas la carte ; `off` sur Voix off.
- Voix off : `DzQuickStage` rend un simple texte (`quick.scene.voix_off`). `DzQuickVoice` tient `busy` (génération) et
  `res` (`res.url` → un `<audio controls>` sous `[data-dzvores="ok"]`). La zone d'aperçu ne connaît pas cet état.
- Références « voice visualizer » : orbe des agents vocaux (ElevenLabs UI, orb-ui), états repos / réflexion / parole,
  la parole pilotée par le niveau RÉEL de l'audio (analyse FFT/RMS).

## t217 — Zoom de toute la carte d'aperçu (P1, S)

1. `DzQuickZoom` devient le calque de la zone : `flex:1`, étiré, `position:relative` ; la vue transformée (`translate()
   scale()`, origine 0 0) contient la CARTE entière, qui reste DANS le flux (la zone garde sa hauteur). Molette partout
   dans la zone, autour du curseur, de 25 % à 800 % : agrandir ET réduire. Glisser dès que la vue n'est pas à 100 %.
   Double-clic, touche 0 et badge « 100 % » (coin de la zone) recadrent. Actif sur TOUS les onglets (Voix off compris).
2. Paires : Z1 avant la carte, Z2 après sa fermeture ; l'appel `DzQuickStage(…)||repli` redevient celui d'avant t216.
   Le zoom n'est plus remis à 100 % à chaque image (c'est la fenêtre qu'on règle).
3. Bancs : `test_quick_zoom.py` réécrit ([B] calque, [C] câblage carte). Mutations. Preuve 8799 : vraie molette sur la
   zone (agrandir, réduire), vrai glisser, double-clic.

## t218 — Orbe vocal dans l'aperçu Voix off (P1, M)

1. `DzQuickOrbe` (useReducer/useRef/useEffect, aucun useState) remplace le texte de la branche voice de DzQuickStage :
   cœur sphérique (nappe conique cyan / violet / orange qui tourne, reflet), trois anneaux d'onde, légende sous l'orbe.
   États : **repos** (rotation lente, souffle doux), **génération** (`busy` : rotation et ondes rapides, légende
   « quick.voix.generation »), **lecture** (le `<audio>` du résultat joue : le niveau RMS réel, via AnalyserNode, pilote
   l'échelle et les ondes ; repli en pulsation CSS si l'analyse échoue). `prefers-reduced-motion` fige. Style injecté une
   fois (`#dz-orbe-style`), boucle rAF seulement pendant la lecture.
2. `DzQuickVoice` publie son état : un `x.useEffect` posé après `res=q7[0],setRes=q7[1]` appelle
   `dzVoixEtatPoser(busy,res)` (global `window.dzVoixEtat` + évènement `dz:voix-etat`).
3. Aides pures testables sous node : `dzOrbeEtat(e, lecture)`, `dzOrbeNiveau(octets)`.
4. Banc `test_quick_orbe.py` (hooks simulés, évènements, rendu par état, câblage, CSS reduced-motion, compteurs figés).
   Mutations. Preuve 8799 : repos (deux images à 1 s qui diffèrent), génération (sans clé : état simulé par l'évènement,
   dit comme tel), lecture d'un vrai fichier audio.

Ordre : t217 puis t218, même maillon dzquick, même branche `chantier/quick-display`, une seule PR.
