/* L'AIDE CONTEXTUELLE DE L'ÉTABLI (tâche T091, plan-etabli T15) — le pas à pas
   en huit gestes, dix-huit mots, une phrase chacun, et le chemin vers le
   chapitre 21 du guide qui les développe.

   POURQUOI DEUX NIVEAUX PLUTÔT QUE DEUX COPIES : le guide porte les
   définitions longues, les chiffres et les liens vérifiés ; l'écran porte la
   phrase qu'on lit sans quitter son geste. Les CLÉS sont les mêmes des deux
   côtés (`lex-<clé>` est l'ancre du guide), et un banc refuse un terme d'ici
   qui n'existerait pas là-bas, dans l'une OU l'autre langue : deux lexiques
   qui divergent valent moins que pas de lexique du tout.

   PAS DE TRADUCTION ICI : l'écran de l'Établi est en français, comme le reste
   de l'application ; seul le LIEN change de langue, d'après le `lang` du
   document — c'est le guide, lui, qui existe en deux langues. */

export const LEXIQUE = {
  assise: { titre: dzT("etabli.et1_lex.assise_titre"), texte: dzT("etabli.et1_lex.assise_texte") },
  surplomb: { titre: dzT("etabli.et1_lex.surplomb_titre"), texte: dzT("etabli.et1_lex.surplomb_texte") },
  support: { titre: dzT("etabli.et1_lex.support_titre"), texte: dzT("etabli.et1_lex.support_texte") },
  brim: { titre: dzT("etabli.et1_lex.brim_titre"), texte: dzT("etabli.et1_lex.brim_texte") },
  raft: { titre: dzT("etabli.et1_lex.raft_titre"), texte: dzT("etabli.et1_lex.raft_texte") },
  jupe: { titre: dzT("etabli.et1_lex.jupe_titre"), texte: dzT("etabli.et1_lex.jupe_texte") },
  remplissage: { titre: dzT("etabli.et1_lex.remplissage_titre"), texte: dzT("etabli.et1_lex.remplissage_texte") },
  couture: { titre: dzT("etabli.et1_lex.couture_titre"), texte: dzT("etabli.et1_lex.couture_texte") },
  retraction: { titre: dzT("etabli.et1_lex.retraction_titre"), texte: dzT("etabli.et1_lex.retraction_texte") },
  couche: { titre: dzT("etabli.et1_lex.couche_titre"), texte: dzT("etabli.et1_lex.couche_texte") },
  perimetre: { titre: dzT("etabli.et1_lex.perimetre_titre"), texte: dzT("etabli.et1_lex.perimetre_texte") },
  pont: { titre: dzT("etabli.et1_lex.pont_titre"), texte: dzT("etabli.et1_lex.pont_texte") },
  warping: { titre: dzT("etabli.et1_lex.warping_titre"), texte: dzT("etabli.et1_lex.warping_texte") },
  etancheite: { titre: dzT("etabli.et1_lex.etancheite_titre"), texte: dzT("etabli.et1_lex.etancheite_texte") },
  manifold: { titre: dzT("etabli.et1_lex.manifold_titre"), texte: dzT("etabli.et1_lex.manifold_texte") },
  decimation: { titre: dzT("etabli.et1_lex.decimation_titre"), texte: dzT("etabli.et1_lex.decimation_texte") },
  creusage: { titre: dzT("etabli.et1_lex.creusage_titre"), texte: dzT("etabli.et1_lex.creusage_texte") },
  drainage: { titre: dzT("etabli.et1_lex.drainage_titre"), texte: dzT("etabli.et1_lex.drainage_texte") },
};

/* Le chapitre du guide, dans la langue du document. `lang` est posé une seule
   fois, sur <html> ; une page servie un jour en anglais suivrait sans qu'on
   touche ici. `null` vise le chapitre entier. */
export function lienGuide(cle) {
  const en = String(document.documentElement.lang || "fr").toLowerCase().startsWith("en");
  const page = en ? "/guide/en.html" : "/guide/fr.html";
  return cle ? `${page}#lex-${cle}` : `${page}#c21`;
}

/* Le panneau. Le pas à pas est celui du chapitre 21 — mêmes huit gestes, même
   ordre (un banc les compare) ; les textes du lexique passent par `esc` : ce
   sont des constantes, mais l'invariant du fichier ne se négocie pas au cas
   par cas. */
export function ouvrirAide(hote, esc) {
  const lignes = Object.entries(LEXIQUE).map(([cle, d]) =>
    `<div class="aide-mot"><b>${esc(d.titre)}</b> — ${esc(d.texte)}
     <a href="${esc(lienGuide(cle))}" target="_blank" rel="noopener">guide</a></div>`).join("");
  hote.innerHTML = `<div class="dt-label">${dzT("etabli.et1_aide.titre")}</div>
    <ol class="aide-pas">
      <li>${dzT("etabli.et1_aide.pas1")}</li>
      <li>${dzT("etabli.et1_aide.pas2")}</li>
      <li>${dzT("etabli.et1_aide.pas3")}</li>
      <li>${dzT("etabli.et1_aide.pas4")}</li>
      <li>${dzT("etabli.et1_aide.pas5")}</li>
      <li>${dzT("etabli.et1_aide.pas6")}</li>
      <li>${dzT("etabli.et1_aide.pas7")}</li>
      <li>${dzT("etabli.et1_aide.pas8")}</li>
    </ol>
    <div class="aide-lex">${lignes}</div>
    <a class="aide-tout" href="${esc(lienGuide(null))}" target="_blank" rel="noopener">
      ${typeof dzIcone === "function" ? dzIcone("dz-nav-guide", { taille: 16, classe: "dzi--16" }) : ""} ${dzT("etabli.et1_aide.chapitre")}</a>`;
  hote.classList.remove("hidden");
}
