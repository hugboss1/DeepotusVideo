"""t146 — statut : la barre d'état (js/mod-statut.js) : phrase d'aide de l'outil Sélection, pagination des planches.

VERBES : vocabulaire COMPARÉ (mot en tête de segment mis en gras) — les verbes anglais y sont AJOUTÉS (drag, click…)
pour que la phrase anglaise garde ses verbes en gras ; les mots français restent (texte d'aide resté en français
ailleurs, et la comparaison ne coûte rien).
"""
from outils import L, S, X

ENTREES = [
    X("js/mod-statut.js", 4, '"entrée"', "vocabulaire comparé (VERBES), pas affiché"),
    X("js/mod-statut.js", 4, '"échap"', "vocabulaire comparé (VERBES), pas affiché"),
    S("js/mod-statut.js", 4,
      '"suppr", "entree"];',
      '"suppr", "entree",\r\n  "drag", "click", "double-click", "right-click", "shift", "enter", "esc", "del", "delete"];',
      {}),
    L("js/mod-statut.js", 7,
      '"**Glisser** pour utiliser un cadre de sélection. **Cliquer** sur un objet pour le sélectionner. **Clic droit** pendant la sélection pour activer/désactiver le mode Intersection."',
      "vectorlab.statut.select_vide",
      "**Glisser** pour utiliser un cadre de sélection. **Cliquer** sur un objet pour le sélectionner. **Clic droit** pendant la sélection pour activer/désactiver le mode Intersection.",
      "**Drag** to use a selection marquee. **Click** an object to select it. **Right-click** while selecting to toggle Intersection mode."),
    S("js/mod-statut.js", 8,
      '`${nSel} objet${nSel > 1 ? "s" : ""} sélectionné${nSel > 1 ? "s" : ""}. **Glisser** pour déplacer la sélection. **Cliquer** sur un autre objet pour le sélectionner. **Cliquer** sur une zone vide pour annuler la sélection. **Suppr** pour retirer.`',
      'T(nSel > 1 ? "vectorlab.statut.select_plusieurs" : "vectorlab.statut.select_un", { n: nSel })',
      {"vectorlab.statut.select_un": (
          "{n} objet sélectionné. **Glisser** pour déplacer la sélection. **Cliquer** sur un autre objet pour le sélectionner. **Cliquer** sur une zone vide pour annuler la sélection. **Suppr** pour retirer.",
          "{n} object selected. **Drag** to move the selection. **Click** another object to select it. **Click** an empty area to deselect. **Del** to remove."),
       "vectorlab.statut.select_plusieurs": (
          "{n} objets sélectionnés. **Glisser** pour déplacer la sélection. **Cliquer** sur un autre objet pour le sélectionner. **Cliquer** sur une zone vide pour annuler la sélection. **Suppr** pour retirer.",
          "{n} objects selected. **Drag** to move the selection. **Click** another object to select it. **Click** an empty area to deselect. **Del** to remove.")}),
    S("js/mod-statut.js", 30,
      '`${i >= 0 ? i + 1 : 1} sur ${n}`',
      'T("vectorlab.statut.page_sur", { i: i >= 0 ? i + 1 : 1, n })',
      {"vectorlab.statut.page_sur": ("{i} sur {n}", "{i} of {n}")}),
]
