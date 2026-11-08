"""Plateau hexagonal, lot 1 (08/11/2026, tâche 4) — la galerie du Card Forge montre la catégorie d'un jeu.

core.js :
- `galDecksList` garde le champ `categorie` du résumé (seule la valeur « plateau » est retenue, sinon vide) ;
- la section « Reprendre un jeu » gagne un filtre « Tous / Plateaux » (#galFiltre) au-dessus de la grille ;
  `galDrawDecks` ne montre que les plateaux quand il est sur « Plateaux » (le total du serveur, lui, reste celui
  de la liste complète) ;
- un jeu `categorie == "plateau"` porte un badge « Plateau » dans sa ligne de méta.
Les angles sont vifs (cardforge.css : aucun border-radius posé ici). Les sauts de ligne des insertions sont CRLF.
"""
from outils import S

C = "js/core.js"


def _crlf(t):
    return t.replace("\n", "\r\n")


_DICO = {
    "cartes.plateau.badge": ("Plateau", "Board"),
    "cartes.plateau.filtre": ("Filtrer les jeux", "Filter decks"),
    "cartes.plateau.filtre_tous": ("Tous", "All"),
    "cartes.plateau.filtre_plateaux": ("Plateaux", "Boards"),
    "cartes.plateau.aucun": ("Aucun plateau pour l'instant.", "No board yet."),
}

_FILTRE = r"""'<div class="cf-gal-filtre" id="galFiltre" role="group" aria-label="' + dzT("cartes.plateau.filtre") + '">'
    + '<button class="btn sm" type="button" data-filtre="tous">' + dzT("cartes.plateau.filtre_tous") + '</button>'
    + '<button class="btn sm" type="button" data-filtre="plateau">' + dzT("cartes.plateau.filtre_plateaux") + '</button></div>'
    + '<div class="cf-gal-decks" id="galDecks"></div></section>'"""

_CABLE = r"""const gf = el("#galFiltre");
    if (gf) gf.addEventListener("click", (e) => {
      const b = e && e.target && e.target.closest ? e.target.closest("button[data-filtre]") : null;
      if (!b) return;
      GAL_FILTRE = b.dataset.filtre === "plateau" ? "plateau" : "tous";
      if (GAL_DECKS) galDrawDecks(GAL_DECKS); else galSyncFiltre();
    });
    const rl = el("#galReload");"""

_ETAT = r"""/* t421 plateau : le filtre de la liste des jeux (« tous » | « plateau ») et son reflet sur les deux boutons */
  let GAL_FILTRE = "tous";
  function galSyncFiltre() {
    document.querySelectorAll("#galFiltre button[data-filtre]").forEach((b) => {
      const on = b.dataset.filtre === GAL_FILTRE;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }
  function galDrawDecks(list) {"""

_ROWS = r"""const toutes = Array.isArray(list) ? list : [];
    const rows = GAL_FILTRE === "plateau" ? toutes.filter((r) => r.categorie === "plateau") : toutes;
    galSyncFiltre();
    if (!rows.length && GAL_FILTRE === "plateau") { galNote(host, dzT("cartes.plateau.aucun")); return; }"""

_BADGE = r"""meta.appendChild(galEl("i", "mono", r.id));
      if (r.categorie === "plateau") meta.appendChild(galEl("i", "cf-gal-badge", dzT("cartes.plateau.badge")));"""

ENTREES = [
    # le résumé garde la catégorie
    S(C, 1873, 'updated: String(x.updated || ""),',
      _crlf('updated: String(x.updated || ""),\n          categorie: x.categorie === "plateau" ? "plateau" : "",'), _DICO),
    # le filtre, au-dessus de la grille des jeux
    S(C, 1992, "'<div class=\"cf-gal-decks\" id=\"galDecks\"></div></section>'", _crlf(_FILTRE), {}),
    # son câblage
    S(C, 2019, 'const rl = el("#galReload");', _crlf(_CABLE), {}),
    # l'état du filtre, juste avant galDrawDecks
    S(C, 2111, "function galDrawDecks(list) {", _crlf(_ETAT), {}),
    # la liste filtrée
    S(C, 2114, "const rows = Array.isArray(list) ? list : [];", _crlf(_ROWS), {}),
    # le badge
    S(C, 2129, 'meta.appendChild(galEl("i", "mono", r.id));', _crlf(_BADGE), {}),
    # la note du total compte les jeux MONTRÉS de la liste complète, pas ceux du filtre
    S(C, 2140, "const montres = Math.min(rows.length, GAL_DECKS_MAX);", "const montres = Math.min(toutes.length, GAL_DECKS_MAX);", {}),
]
