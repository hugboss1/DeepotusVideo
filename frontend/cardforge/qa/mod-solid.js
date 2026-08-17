/* qa — MODE BACLE. Ce fichier n'a PAS de "use strict" et declare `init` en
   FONCTION CLASSIQUE : dans ce mode, `CF.doc().solid.thickness_mm = 9.9` ne
   leve pas, c'est un no-op MUET — le module croit avoir ecrit, relit
   l'ancienne valeur et cherche ailleurs pendant une heure. La garantie
   « mutation = TypeError » etait integralement sous-traitee a une directive
   que personne ne verifiait. `register` refuse desormais une fonction
   classique bâclee ; le lint (R9) refuse le fichier au build ; l'audit du
   boot relit la source servie. */

(function () {
  var CF = window.CF;
  var rec = function (k, verdict, detail) { window.__CFQA.push({ k: k, verdict: verdict, detail: String(detail) }); };
  try {
    CF.register({
      id: "solid",
      title: "Volume (bâclé)",
      order: 5,
      state: { thickness_mm: 0.32 },
      init: function (host) { host.textContent = "solid"; },
    });
    rec("mode bâclé : l'enregistrement passe (la sanction vient au boot)", "NOTE",
      "attendu : `register` ne PEUT pas tester la strictesse d'une fonction — "
      + "Object.getOwnPropertyNames rend le meme resultat dans les deux modes "
      + "sur V8 moderne (mesure). C'est la SOURCE qui est relue : voir les deux "
      + "lignes « module sans use strict » en fin de batterie.");
  } catch (e) {
    rec("mode bâclé : l'enregistrement passe (la sanction vient au boot)", "NOTE", e.message);
  }
  /* la demonstration du no-op muet, dans ce meme fichier bâclé */
  try {
    var avant = CF.get("face.fit", null);
    CF.doc().face.fit = "MUTATION-MUETTE";
    rec("mode bâclé : mutation de CF.doc() (no-op muet attendu)", "NOTE",
      "avant=" + avant + " apres=" + CF.get("face.fit", null)
      + " — aucune exception : c'est pour cela que la directive est verifiee au build ET au boot");
  } catch (e) {
    rec("mode bâclé : mutation de CF.doc()", "NOTE", "TypeError (le moteur etait strict) : " + e.message);
  }
})();
