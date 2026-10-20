# Bulle « Demander » : ancrée ou flottante (t260, 20/10/2026)

**Constat (capture de l'utilisateur, 20/10)** : la bulle `.dzAgentBtn` est fixée en bas à droite
(`right:18px; bottom:18px; z-index:9990`). Elle couvre les derniers boutons de la barre du bas du panneau
Calques du Photolab, et de la même façon les pieds de panneaux de tous les écrans (Montage, labs, Réglages).

**Décision** : deux places, au choix de l'utilisateur, retenues dans `localStorage` (`dz_agent_place`).

| Place | Où | Pourquoi |
|---|---|---|
| `barre` (défaut) | bouton compact dans la barre du haut de la coque (`#root header`), juste avant son dernier bouton | la barre est une rangée d'outils : le bouton y prend sa propre place et ne recouvre jamais rien |
| `flottant` | bulle libre, déplaçable à la souris ou au doigt (glisser > 4 px = déplacement, sinon clic) | pour qui préfère l'avoir sous la main ; position mémorisée (`dz_agent_pos`), ramenée dans la fenêtre au redimensionnement |

- Repli : si la barre du haut n'existe pas (écran de démarrage, rendu React pas encore monté, mise en page
  future), la bulle reste flottante ; un `MutationObserver` la réinsère dès que la barre (ré)apparaît ou que
  React la remonte.
- Bascule : bouton épingle dans l'en-tête du tiroir (« Ancrer dans la barre du haut » / « Rendre flottant »)
  et menu du clic droit sur la bulle : ancrer, flottant, remettre à la place par défaut.
- Inchangés : F1, Échap, le pointeur (il part du rectangle de la bulle, où qu'elle soit), la capture
  (A5 masque la bulle pendant la prise).

**Fichiers** : `frontend/shared/dz-agent.js` (+ copie octet pour octet `frontend/dist/shared/`),
`frontend/shared/i18n/agent.json` puis `python scripts/i18n_assembler.py`, banc
`backend/tests/test_agent_ecran.py` (place, glisser, repli), logique pure de bornage dans
`dz-agent-logique.js` + `frontend/shared/qa/agent_logique.test.mjs`.

**Preuve** : backend de preuve, écran Photolab : la bulle ancrée dans la barre ne couvre plus le pied du
panneau Calques ; mode flottant glissé puis rechargé = même place ; fenêtre réduite = bulle ramenée dedans.

**Installation** : statiques seulement (`dz-agent.js`, `dz-agent-logique.js`, `dz-i18n-dico.js` dist) :
aucune relance du backend, un rechargement forcé suffit.

**Pièges relevés en preuve (20/10)** : (1) le pointeur doit être capturé DÈS l'appui — le premier `pointermove`
d'un geste vif tombe déjà hors du bouton (au-dessus de l'iframe du Photolab) et le glisser était perdu ;
(2) le veilleur de la barre passe par `setTimeout`, pas `requestAnimationFrame`, qui ne tourne pas tant que la
fenêtre est masquée (le bouton restait flottant au démarrage).
