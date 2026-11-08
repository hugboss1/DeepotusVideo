"""Plateau hexagonal, lot 1 (08/11/2026, tâche 4) — la galerie du Card Forge montre la catégorie d'un jeu.

core.js :
- `galDecksList` garde le champ `categorie` du résumé (seule la valeur « plateau » est retenue, sinon vide) ;
- la section « Reprendre un jeu » gagne un filtre « Tous / Plateaux » (#galFiltre) au-dessus de la grille ;
  le filtre est celui du SERVEUR (`?categorie=plateau`) : un clic recharge la liste, et le total servi est celui du filtre ;
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
      galSyncFiltre();
      /* le filtre est celui du SERVEUR (?categorie=) : la liste bornée aux plus récents ne dit pas où sont les plateaux */
      GAL_DECKS = null; GAL_DECKS_REQ = null;
      const gd = el("#galDecks");
      if (gd) galNote(gd, dzT("cartes.core.chargement_jeux"));
      galDecksList(true).then((l) => galDrawDecks(l),
        (e) => { if (gd) galNote(gd, dzT("cartes.core.jeux_indispo", { err: galMsg(e) }), true); });
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

_ROWS = r"""const rows = Array.isArray(list) ? list : [];
    galSyncFiltre();
    if (!rows.length && GAL_FILTRE === "plateau") { galNote(host, dzT("cartes.plateau.aucun")); return; }"""

_URL = r"""const filtre = GAL_FILTRE;
      GAL_DECKS_REQ = jsonNamed("GET", "/cards/decks?limit=" + GAL_DECKS_MAX + (filtre === "plateau" ? "&categorie=plateau" : "")).then((d) => {"""

_PERIME = r"""if (filtre !== GAL_FILTRE) return GAL_DECKS_REQ || GAL_DECKS || [];   /* réponse d'un filtre abandonné */
        const rows = Array.isArray(d && d.decks) ? d.decks : [];"""

_BADGE = r"""meta.appendChild(galEl("i", "mono", r.id));
      if (r.categorie === "plateau") meta.appendChild(galEl("i", "cf-gal-badge", dzT("cartes.plateau.badge")));"""

ENTREES = [
    # la demande porte le filtre ; la réponse d'un filtre abandonné est écartée
    S(C, 1869, 'GAL_DECKS_REQ = jsonNamed("GET", "/cards/decks?limit=" + GAL_DECKS_MAX).then((d) => {', _crlf(_URL), {}),
    S(C, 1870, "const rows = Array.isArray(d && d.decks) ? d.decks : [];", _crlf(_PERIME), {}),
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
]
