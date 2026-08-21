# Branches en attente — audit et plan de résorption (2026-08-21)

Trois branches distantes portaient des commits absents de `main` au moment du
grand nettoyage v2.4.0 (les sept branches entièrement fusionnées ont déjà été
supprimées). Verdict par branche, preuves à l'appui — et, après exécution du
plan le soir même : ZÉRO travail encore en attente, les trois branches
supprimées.

## 1. `claude/blissful-albattani-6665e2` — SUPERSÉDÉE, supprimée

- **Portait** : 966fe4f « fix(voiceover): voix par défaut premade — George (FR)
  / Brian (EN) » (base du 2026-07-06).
- **Preuve de résorption** : `backend/app/config.py` de main porte déjà les
  MÊMES identifiants (`ELEVENLABS_VOICE_ID_EN = nPczCjzI2devNBz1zQrb`,
  `ELEVENLABS_VOICE_ID_FR = JBFqnCBsd6RMkjVDRZzb`) ; `git diff main
  origin/<branche>` sur config.py et .env.example est VIDE, et le reste du
  diff n'est que le retard de la branche (elle ignore `ELEVENLABS_MODEL` et
  tout ce qui a suivi).
- **Plan** : suppression
  (`git push origin --delete claude/blissful-albattani-6665e2`).

## 2. `claude/video-shotcraft-skill-install-7187c4` — SUPERSÉDÉE, supprimée

- **Portait** : a988bee « feat(atelier): W-d — pont video-shotcraft pour
  l'agent de découpage » (base du 2026-07-22, +1499 lignes).
- **Preuve de résorption** : `scripts/gen_shotcraft_catalog.py` existe dans
  main et `frontend/atelier/atelier.js` y porte 13 références `shotcraft` —
  le pont a atterri par une autre voie puis a évolué (l'atelier de main a
  +964/−142 depuis la base de la branche).
- **Plan** : suppression
  (`git push origin --delete claude/video-shotcraft-skill-install-7187c4`).

## 3. `feat/heygen-animate-image` — ENTIÈREMENT résorbée (amendé le 2026-08-21 soir, exécution du plan)

> **AMENDEMENT — le verdict initial de cette section était FAUX.** L'exécution
> du plan (sonde à blanc de l'étape 1) a prouvé que le chantier D est DÉJÀ
> appliqué : les 8 sites du patcher portent tous le texte REMPLACÉ (état
> `hsrc/Hsrc`, bascule Source, panneau image/cinématique, branchement
> `/generate/heygen-image` et `/generate/heygen-cinematic`, castings image,
> filtre Studio — chacun 1×) ; le backend (routes.py:2292/2315, pipeline,
> schémas) et `test_animate_v3.py` sont dans main, suite VERTE re-mesurée.
> Le faux négatif venait de l'audit : le bundle stocke ses libellés en forme
> ÉCHAPPÉE (`Cin\u00e9matique`, `anim\u00e9e`) et les greps de contrôle
> avaient testé la forme rendue (é) puis une casse erronée — leçon : sonder
> un bundle avec les octets EXACTS du patcher, jamais avec le libellé
> reconstruit. L'absence de `.bak_animate` s'explique par le repatriement
> (7b80e17) qui a importé le bundle patché sans ses `.bak_*` (gitignorés).
> Étapes 2-3 sans objet, étape 4 (QA) verte, étape 5 (suppression de la
> branche) exécutée.

- **Portait** : e4b2cb5 (spec C+D), 1d0bc99 (chantier C — choix de moteur
  Avatar III/IV/V par génération, API v3), 0b4992a (chantier D — animer une
  image de la Library + mode cinématique).
- **Résorbé** : la spec
  (`docs/superpowers/specs/2026-07-05-heygen-v3-engine-and-animate-design.md`)
  et les DEUX patchers (`scripts/patch_bundle_engine.py`,
  `scripts/patch_bundle_animate.py`) sont dans main À L'IDENTIQUE (diff
  vide) ; le chantier C est VIVANT dans le bundle livré (« Auto (pipeline
  actuel) » ×2 dans `index-BEOJX8L5.js`).
- ~~**En attente — le chantier D**~~ (verdict initial, invalidé par
  l'amendement ci-dessus : les libellés étaient bien dans le bundle, en forme
  échappée — l'audit les avait cherchés en forme rendue et en mauvaise casse.)

### Plan de résorption du chantier D — EXÉCUTÉ le 2026-08-21, issue : rien à appliquer

1. - [x] **Sonde à blanc** : `python scripts/patch_bundle_animate.py` — le patcher
   est gardé par asserts (« [tag] anchor count=N (want 1). Aborting. ») : il
   ne peut pas corrompre le bundle, et son message dit exactement quelles
   ancres ont dérivé.
2. ~~sans objet~~ **Rafraîchir les ancres** qui comptent ≠ 1 contre le bundle COURANT
   (discipline du chantier : relire l'ancre dans le bundle réel, jamais la
   deviner), en conservant la sémantique D1/D2 du script.
3. ~~sans objet~~ **Appliquer en bout de chaîne** — le patcher pose son `.bak_animate`
   frais ; ne PAS passer par `repatch_all --from animate` pour une première
   application (il n'a pas de bak historique à rejouer).
4. - [x] **QA** : les deux libellés présents dans le bundle ; parcours réel
   « Library → image → Animer » (mock ou clé) ; undo ; lint complet vert
   (R13 octets sains) ; `node frontend\cardforge\qa\test_core_contract.mjs
   --contract` inchangé.
5. - [x] **Puis seulement** : supprimer la branche
   (`git push origin --delete feat/heygen-animate-image`) — faite, la branche
   ne portait plus rien que main n'ait.

## Note

Les trois branches supersédées ne portaient AUCUN contenu que main n'ait
pas — leur suppression ne perd que des doublons historiques (et de vieux
scripts `upgrade-from-v1.x.ps1` volontairement retirés de main au nettoyage
du 06/08). Bilan final : zéro travail en attente sur les branches ; la spec
C+D et `test_animate_v3.py` restent les références vivantes du chantier
heygen dans main.
