/* qa — ATTAQUANT : le squat du registre.
   Un fichier qui n'est PAS mod-print.js tente d'enregistrer l'id "print".
   Dans la revision 1, `register` ne regardait pas qui appelait : le premier
   script charge pouvait prendre les sept autres ids, tuer leurs modules
   (« deja enregistre » a l'evaluation de LEUR fichier), imposer leur schema,
   leur painter et leur panneau. Ici l'identite est celle de <script>. */
"use strict";

(function () {
  const CF = window.CF;
  const rec = (k, verdict, detail) => window.__CFQA.push({ k, verdict, detail: String(detail) });
  try {
    CF.register({
      id: "print",
      title: "SQUAT",
      order: 7,
      state: { vole: true },
      init(host) { host.textContent = "SQUATTE"; },
    });
    rec("registre : un fichier etranger enregistre 'print'", "OUVERT", "ACCEPTE");
  } catch (e) {
    rec("registre : un fichier etranger enregistre 'print'", "TENU", e.message);
  }
  /* et l'usurpation par sourceURL, la ou elle faisait le plus mal */
  try {
    (0, eval)("CF.register({id:'gltf',title:'SQUAT2',state:{},init(){}})\n//# sourceURL=" + location.origin + "/cardforge/qa/mod-gltf.js");
    rec("registre : eval etiquete mod-gltf.js", "OUVERT", "ACCEPTE");
  } catch (e) {
    rec("registre : eval etiquete mod-gltf.js", "TENU", e.message);
  }
})();
