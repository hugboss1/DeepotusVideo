# Vectorlab relooking Affinity — R9 l'outil Nœud de classe Affinity — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Demande de l'utilisateur (18/09, capture 5 du Vectorlab) : « analyse mieux
> l'outil nœud d'Affinity et raffine le nôtre ».

## Analyse de l'outil Nœud d'Affinity

| Geste ou réglage d'Affinity | Aujourd'hui dans le Vectorlab | Décision |
|---|---|---|
| Clic sur un nœud = le sélectionner (rempli), Maj+clic = ajouter, glisser un cadre = plusieurs | oui (mod-tools, lasso d'ancres de mod-outils2) | conservé ; le nœud sélectionné passe en bleu plein |
| **Glisser une poignée** : le nœud reste lisse (la poignée opposée garde sa longueur et s'aligne) ; Alt = casser la tangente (poignée seule) ; Maj = angle contraint | les poignées sont dessinées mais **inertes** | poignées cliquables (`.poignee-noeud`), `poignee_deplacer` pur (modes lisse / libre), Maj → `contraindre_angle` |
| **Glisser un segment** : la courbe se déforme en gardant ses extrémités (une droite devient courbe) | — | `segment_tirer` pur (poids de Bernstein 1 / (3 t (1 − t))), aperçu puis une commande |
| **Double-clic sur un segment** : insère un nœud à cet endroit | diviser au milieu (menu) | `segment_proche` pur → `op_noeud_inserer(id, i, t)` au point cliqué |
| Double-clic sur un nœud : vif ↔ lisse | oui | conservé |
| Suppr : suppression **lisse** (la courbe garde sa forme entre les voisins) | suppression brute | `noeud_supprimer_lisse` pur (un C entre les voisins avec leurs tangentes) |
| Barre contextuelle : Vif · Lisse · Intelligent · Fractionner · Ouvrir / Fermer · Courbe lisse · Relier · Inverser · Aligner (6) · Transformer · Magnétisme aux nœuds | panneau Nœuds partiel | mode select + les huit actions de `VL.actions.plume` + six alignements (`op_noeuds_aligner`) dans la barre |
| Curseur qui change au survol d'un nœud / d'une poignée / d'un segment | — | curseurs CSS sur `.ancre`, `.poignee-noeud`, chemin sélectionné en outil Nœuds |
| Transformer une sélection de nœuds (rotation / échelle par poignées) | `op_noeuds_transformer` + panneau | conservé tel quel (hors barre) |

> **RELEVÉ DE LIVRAISON (18/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (commit `595caa2`, poussé) : `mod-noeud.js` feuille
> (`segment_proche` par échantillonnage, le Z compte comme la droite de
> retour ; `segment_tirer` : une droite devient un C aux tiers puis les
> deux contrôles reçoivent le déplacement pondéré 1 / (3 t (1 − t)) — la
> courbe PASSE par le point tiré ; `poignee_deplacer` lisse — l'opposée
> s'aligne en gardant sa longueur — ou libre ; `noeud_supprimer_lisse` : un
> C entre les voisins avec leurs tangentes, une droite entre deux droites ;
> `point_segment` ; RED constaté, 14 contrôles) ; `mod-noeudui.js` en
> capture sur `#stage` : poignées tirables (`.poignee-noeud` du cœur, Alt =
> libre, Maj = angle contraint, magnétisme sauf Alt), segment du chemin
> sélectionné déformable au glisser, double-clic sur un segment = nœud
> inséré au point (`op_noeud_inserer` à t), Suppr = suppression lisse
> (chaînée avant mod-tools), `VL.actions.noeuds.aligner / al-*` ; barre
> contextuelle de l'outil Nœuds = les huit actions de la Plume + six
> alignements ; cœur : poignées dégénérées non dessinées, ancres choisies
> en bleu plein, `body[data-outil]` ; CSS : curseurs.
>
> **Prouvé en réel** (8799, 1400 × 900, gestes pointeur sur un chemin
> `M L C L`) : 2 poignées cliquables ; tirer la sortante du nœud 1 →
> `C 339.95 59.98 …` ; Alt sur l'entrante du nœud 2 → seule l'entrante
> bouge ; Maj → sortante contrainte à y = 100 ; tirer le milieu de la
> droite → le segment devient `C` ; double-clic au milieu du dernier
> segment → 4 → 5 ancres, ancre 3 sélectionnée ; Suppr → 4 ancres (lisse) ;
> Vif ; bouton « ⇧ » de la barre → alignement haut de deux ancres ; curseur
> `move` sur les ancres, `body[data-outil="noeuds"]` ; 14 champs dans la
> barre ; 0 erreur, document valide.
>
> **Déployé** : installé = base R8 `45a2e4a` (147, 0 divergent) →
> sauvegarde `_backup_predeploy_2026-09-18-relooking-r9` → 150/150 = cible.
>
> **Reste (assumé)** : pas de poignées de rotation / échelle sur la
> sélection de nœuds (le panneau Nœuds garde `op_noeuds_transformer`) ;
> pas de conversion « Intelligent » ; le magnétisme aux nœuds des autres
> objets n'est pas un réglage séparé.

**Architecture :** `mod-noeud.js` feuille : `segment_proche(segs, pt, tol)`
→ `{k, i, t, dist}` (k = index de segment, i = index de l'ancre de fin,
échantillonnage 24 pas, le Z compte comme une droite de retour),
`segment_tirer(segs, k, t, dx, dy)` → segs (L → C aux tiers puis poids),
`poignee_deplacer(segs, i, role, pt, {mode})` → segs (`lisse` par défaut :
l'opposée s'aligne en gardant sa longueur ; `libre` : seule), `noeud_supprimer_lisse(segs, i)` → segs (≥ 3 ancres ; sinon inchangé), `point_segment(segs, k, t)` ; `mod-noeudui.js` : capture sur `#stage` en outil `noeuds` pour les poignées, les segments (pointerdown sur le `[data-objet]` du chemin sélectionné hors ancre), le double-clic sur segment, Suppr lisse (chaînée avant mod-tools), aperçu par patch du clone (patron mod-tools), UNE commande au `pointerup` ; `core.js` : poignées avec `class="poignee-noeud" data-ancre data-role`, ancre sélectionnée bleue pleine ; `mod-contexte` : `noeuds` → select Mode (Vif / Lisse) hors sujet → boutons `plume:*` + `noeuds:al-*` ; `VL.actions.noeuds.aligner(mode)`.

**Tech :** vanilla ESM ; node `qa/run.mjs` ; preuve 8799 par gestes réels.

### Task 1 : `mod-noeud.js` (RED → vert, `qa/noeud.test.mjs`, ≥ 14 contrôles avec états vides)
### Task 2 : `mod-noeudui.js`, `core.js` (poignées cliquables), CSS (curseurs, `pointer-events`), `mod-contexte` (noeuds), `VL.actions.noeuds.aligner`
### Task 3 : preuve en réel — tirer une poignée (le d change, l'opposée reste alignée), Alt (l'opposée ne bouge pas), Maj (angle), tirer un segment droit → C passant par le point, tirer un segment courbe, double-clic sur segment → +1 ancre au bon endroit, Suppr → suppression lisse (C entre voisins), barre : Vif / Lisse / Aligner à gauche sur 2 ancres, curseurs ; 0 erreur, document valide
### Task 4 : déploiement, relevé, mémoire, push
