# Vectorlab relooking Affinity — R8 la Plume de classe Affinity — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Demande de l'utilisateur (18/09) : « analyse mieux la fonction outil
> plume d'Affinity et raffine l'outil dans Vectorlab » (deux captures).

## Analyse de la Plume d'Affinity (captures 3 et 4)

| Élément d'Affinity | Aujourd'hui dans le Vectorlab | Décision |
|---|---|---|
| Barre contextuelle : Masque · Sélection · fond · contour · style · 1,5 pt · profil | fond / contour dans l'onglet Couleur | pastilles fond / contour + épaisseur inline dans la barre (délèguent au style courant / à la sélection) |
| **Quatre modes** : Plume (Bézier), Intelligent (lissage automatique), Polygone (droites), Ligne (un segment) | Bézier seulement | select « Mode » ; Intelligent = Catmull-Rom → Bézier à chaque nœud posé ; Polygone = jamais de poignée ; Ligne = finit après le 2e nœud |
| Conversion du nœud : Vif · Lisse · Intelligent | double-clic dans l'outil Nœuds | boutons Vif / Lisse sur le dernier nœud posé (et sur l'ancre sélectionnée du chemin sélectionné) |
| Actions : Fractionner · Ouvrir · Fermer · Courbe lisse · Relier · Inverser | fermer (op), inverser (op), relier (op), diviser (nœuds) | les six dans la barre, `VL.actions.plume` ; Ouvrir et Courbe lisse sont NOUVELLES (pures) |
| Élastique : du dernier nœud au curseur, COURBE si le nœud a une tangente | ligne pointillée droite | `elastique()` pur : C si sortante, L sinon |
| Nœuds : carrés = vifs, ronds = poignées ; premier nœud rouge quand fermable | ronds partout | glyphes par type, premier nœud rouge quand ≥ 2 nœuds et curseur à ≤ 7 px |
| Clic droit (ou glisser droit) = ligne droite | — | `contextmenu` supprimé pendant le tracé : pose un nœud vif sans poignée |
| Glisser + Maj = tangente contrainte à 45° | — | `contraindre_angle` pur |
| Alt = ignorer le magnétisme | — | pas d'aimantation quand Alt |
| Ctrl = outil Nœud temporaire | — | hors périmètre (Ctrl est pris par les raccourcis) — assumé |
| Cliquer / glisser depuis la fin d'une courbe ouverte sélectionnée la prolonge | — | `extremite_proche` pur : fin → on continue ; début → on inverse puis on continue |
| Retour arrière retire le dernier nœud | — | `trace_retirer` pur |
| Phrase d'état d'Affinity | « clic = ancre, glisser = poignées… » | la phrase d'Affinity, verbes gras |

> **RELEVÉ DE LIVRAISON (18/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (commits `0c6a00b`, `45a2e4a`, poussés) : `mod-plume.js` feuille
> (état de tracé pur et transitions, `elastique`, `contraindre_angle` par
> PROJECTION sur l'axe à 45°, `lisser_catmull`, `chemin_ouvrir /
> chemin_lisser / chemin_fractionner`, `trace_depuis_chemin`,
> `extremite_proche`, `types_ancres` suivant la règle d'`op_noeud_convertir`
> ; RED constaté, 19 contrôles — deux pins du banc ont tranché la
> contrainte et le type d'ancre) ; `mod-plumeui.js` REMPLACE la plume de
> mod-tools (écouteurs en capture + stopPropagation) : quatre modes, clic
> = nœud vif, glisser = nœud lisse, Maj = tangente contrainte, clic droit
> = droite, Alt = sans magnétisme, Retour arrière = retirer, fermeture au
> premier nœud (rouge quand fermable, le fond courant est posé), Entrée /
> Échap / double-clic = finir, prolongation d'une courbe ouverte
> sélectionnée depuis sa fin ou son début (inversion), élastique courbe,
> glyphes carrés / ronds, `VL.actions.plume` (mode, vif, lisse, fractionner,
> ouvrir, fermer, lisserCourbe, relier, inverser), barre contextuelle
> (select Mode + huit boutons `plume:<action>` — les boutons génériques
> délèguent à `VL.actions.<module>.<action>`), phrase d'état d'Affinity.
>
> **Prouvé en réel** (8799, 1400 × 900, gestes pointeur) : clic / clic /
> glisser → C avec poignées, élastique `M … C` (courbe), 2 carrés + 3
> ronds, premier nœud rouge à l'approche ; Maj → sortante à y constant ;
> clic droit → `L` ; Retour arrière 7 → 6 nœuds ; Entrée → chemin posé et
> tracé nul ; Polygone → `M L L` ; Intelligent → des `C` Catmull-Rom ;
> Ligne → un objet `M L` après le 2e clic ; prolongation depuis la fin
> (`… L 448 560`) puis depuis le début (chemin inversé, `M 448 560 … L 240
> 480`) ; Fermer (Z) / Ouvrir / Courbe lisse (3 C) / Inverser / Fractionner
> (+1 objet) / Vif → Lisse ; select Mode de la barre → `polygone` ; fermeture
> au premier nœud → `M 48 640 L 160 640 L 160 720 Z` avec fond ; 0 erreur,
> document valide.
>
> **Déployé** : installé = base R7 `f6414b2` (144, 0 divergent) →
> sauvegarde `_backup_predeploy_2026-09-18-relooking-r8` → 147/147 = cible.
>
> **Reste (assumé)** : Ctrl = outil Nœud temporaire (Ctrl porte les
> raccourcis) et la conversion « Intelligent » d'un nœud isolé ne sont pas
> reproduits ; la tolérance de fermeture est de 7 px écran (Affinity :
> semblable) ; la plume de mod-tools reste dans le code, inatteignable.

**Architecture :** `mod-plume.js` feuille : état de tracé pur `{segs,
ancres, sortante}` et ses transitions (`trace_debut`, `trace_ajouter(trace,
pt, {droite})`, `trace_poignee(trace, pt, {sym})`, `trace_retirer`,
`trace_finir(trace, {fermer}) → d`), `elastique(trace, curseur) → d`,
`contraindre_angle(p0, p, pas)`, `lisser_catmull(points, ferme) → segs`,
`chemin_ouvrir(d)`, `chemin_lisser(d)`, `chemin_fractionner(d, i) → [d…]`,
`trace_depuis_chemin(d)`, `extremite_proche(d, pt, tol) → "fin" | "debut" |
null`, `types_ancres(d) → ["vif"|"lisse"…]` ; `mod-plumeui.js` : REMPLACE
la plume de mod-tools (capture + `stopPropagation` sur `pointerdown` /
`pointermove` / `pointerup` / `contextmenu` / `dblclick` quand l'outil est
`plume`), aperçu dans `#ovTmp`, une commande à la fin (`op_ajouter` ou,
en prolongation, patch du `d`), `VL.actions.plume` (vif, lisse,
fractionner, ouvrir, fermer, lisserCourbe, relier, inverser, mode),
champs de contexte (`mod-contexte` : select mode + boutons d'action), phrase
d'état. La plume de mod-tools reste dans le code mais n'est plus atteinte
(ses écouteurs voient `stopPropagation`).

**Tech :** vanilla ESM ; node `qa/run.mjs` ; preuve 8799 par gestes pointeur réels.

### Task 1 : `mod-plume.js` (RED → vert, banc `qa/plume.test.mjs`, ≥ 16 contrôles dont les états vides)
### Task 2 : `mod-plumeui.js`, `mod-contexte` (plume : mode + actions), `mod-barrecontexte` (boutons d'action génériques → `VL.actions.<module>.<action>`), phrase d'état, glyphes
### Task 3 : preuve en réel — clic / clic / glisser (C), Maj (45°), clic droit (L), Retour arrière (nœud retiré), fermeture au premier nœud (Z), mode Polygone (aucun C), mode Intelligent (des C lissés), mode Ligne (finit à 2), prolongation d'une courbe ouverte sélectionnée depuis sa fin puis depuis son début (inversion), actions Ouvrir / Fermer / Lisser / Fractionner / Inverser sur un chemin, Vif / Lisse sur le dernier nœud, élastique courbe (path C dans #ovTmp), premier nœud rouge ; 0 erreur, document valide
### Task 4 : déploiement, relevé, mémoire, push
