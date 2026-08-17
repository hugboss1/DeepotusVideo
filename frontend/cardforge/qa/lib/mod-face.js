/* qa — ATTAQUANT : le bon NOM, le mauvais DOSSIER.
   La revision 1 lisait le nom de BASE du fichier dans la pile : un
   `lib/mod-face.js` pose n'importe ou (vendor/, une copie, un dossier que le
   lint ne regarde pas) avait les pleins droits d'ecriture sur doc.face.
   Ici l'identite est l'URL COMPLETE de la balise <script>. */
"use strict";

(function () {
  const CF = window.CF;
  const rec = (k, verdict, detail) => window.__CFQA.push({ k, verdict, detail: String(detail) });
  try {
    CF.register({ id: "face", title: "COPIE", state: { fit: "VOLE" }, init() { } });
    rec("identite : lib/mod-face.js enregistre 'face'", "OUVERT", "ACCEPTE");
  } catch (e) {
    rec("identite : lib/mod-face.js enregistre 'face'", "TENU", e.message);
  }
  /* et s'il essaie de voler le jeton du vrai module par la variable globale */
  try {
    const vole = window.__QA_FACE;      /* publie EXPRES par le module d'essai */
    vole.patch({ fit: "VOLE-PAR-LIB" });
    rec("identite : un jeton PUBLIE sur window est reutilisable", "NOTE",
      "attendu : une capacite se donne. La regle du builder est de garder son "
      + "jeton dans sa fermeture — ne jamais l'accrocher a window.");
  } catch (e) {
    rec("identite : un jeton PUBLIE sur window est reutilisable", "NOTE", e.message);
  }
})();
