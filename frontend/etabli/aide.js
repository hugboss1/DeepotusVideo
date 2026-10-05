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
  assise: { titre: "Assise", texte: "La face qui touche le plateau. Large et plate, l'impression tient ; étroite, elle se décolle." },
  surplomb: { titre: "Surplomb", texte: "Une paroi trop penchée pour tenir sur la couche d'en dessous. Sous 45 à 60° depuis l'horizontale, il faut un support." },
  support: { titre: "Support", texte: "Structure jetable qui soutient les surplombs. Le slicer la génère ; l'Établi aide à en avoir moins besoin." },
  brim: { titre: "Brim", texte: "Collerette d'une couche autour de la pièce, contre le décollement des coins." },
  raft: { titre: "Raft", texte: "Radeau imprimé sous toute la pièce. Plus sûr qu'un brim, plus coûteux, face rugueuse." },
  jupe: { titre: "Jupe (skirt)", texte: "Contour tracé à côté de la pièce pour amorcer le flux avant de commencer." },
  remplissage: { titre: "Remplissage", texte: "Motif de l'intérieur. 15 % suffisent le plus souvent ; le gyroïde résiste à peu près autant dans tous les sens." },
  couture: { titre: "Couture", texte: "Ligne verticale laissée par le début et la fin de chaque tour de paroi. Le slicer la place ou la disperse." },
  retraction: { titre: "Rétraction", texte: "Le filament est tiré en arrière pendant les déplacements, contre les fils." },
  couche: { titre: "Couche", texte: "Tranche horizontale. 0,2 mm est le compromis courant ; 0,12 mm pour du détail." },
  perimetre: { titre: "Périmètre", texte: "Nombre de tours de paroi. Deux à 0,45 mm font 0,9 mm : le minimum à viser en modélisant." },
  pont: { titre: "Pont", texte: "Couche imprimée au-dessus du vide entre deux appuis. Quelques centimètres, avec un bon refroidissement." },
  warping: { titre: "Warping", texte: "Coins qui se soulèvent en refroidissant. Plateau propre, brim, enceinte fermée." },
  etancheite: { titre: "Étanchéité", texte: "Surface fermée, sans trou ni bord libre. C'est le « fermé » de la barre du bas." },
  manifold: { titre: "Manifold", texte: "Chaque arête appartient à exactement deux faces. Un maillage peut être fermé ET non-manifold." },
  decimation: { titre: "Décimation", texte: "Réduire le nombre de triangles. 500 000 ne s'impriment pas mieux que 100 000, mais ralentissent tout." },
  creusage: { titre: "Creusage", texte: "Remplacer l'intérieur plein par une coque. Surtout utile en résine ; 2 mm pour commencer." },
  drainage: { titre: "Drainage", texte: "Le trou qui laisse sortir la résine (et l'air) d'une pièce creusée. Pas encore dans l'Établi." },
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
  hote.innerHTML = `<div class="dt-label">Aide — préparer avant le slicer</div>
    <ol class="aide-pas">
      <li>Pose une taille cible (rail de droite) : sans elle, aucun millimètre.</li>
      <li>Choisis l'imprimante : le contour vert est son plateau, le rouge la zone exclue.</li>
      <li>Répare en un clic (onglet Fiche), lis le détail dans la barre du bas.</li>
      <li>Pose sur une face (F), puis « écrire la version ».</li>
      <li>Regarde les Surplombs (orange) et les Tranches : tourne jusqu'à ce que l'orange recule.</li>
      <li>Creuse si c'est utile (surtout en résine), paroi de 2 mm pour commencer.</li>
      <li>Range sur le plateau (Sur la plaque) : une vue, le modèle ne bouge pas.</li>
      <li>Mesure, puis onglet Export → « → Impression 3D » et « Ouvrir dans le slicer ».</li>
    </ol>
    <div class="aide-lex">${lignes}</div>
    <a class="aide-tout" href="${esc(lienGuide(null))}" target="_blank" rel="noopener">
      Le chapitre complet du guide, avec les ressources vérifiées →</a>`;
  hote.classList.remove("hidden");
}
