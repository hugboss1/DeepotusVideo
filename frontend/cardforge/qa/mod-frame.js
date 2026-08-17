/* qa — faux P2. Module LEGITIME qui joue l'attaquant INTERNE : c'est le cas
   reel du gauntlet — un des huit builders, avec un vrai jeton, qui tente
   d'ecrire chez les autres. Toutes ces lignes doivent etre refusees. */
"use strict";

(function () {
  const CF = window.CF;
  const rec = (k, verdict, detail) => window.__CFQA.push({ k, verdict, detail: String(detail) });

  const M = CF.register({
    id: "frame",
    title: "Cadre (qa)",
    order: 2,
    painters: [{ z: 40, fn(ctx, geom, doc, card, side) { ctx.strokeStyle = "#c9a227"; ctx.lineWidth = 6; ctx.strokeRect(4, 4, ctx.canvas.width - 8, ctx.canvas.height - 8); } }],
    state: { family: "or", line_mm: 1.5 },
    init(host) { host.textContent = "frame(qa)"; },
  });
  window.__QA_FRAME = M;

  const T = (k, attendu, fn) => {
    try { const v = fn(); rec(k, attendu === "refus" ? "OUVERT" : "TENU", (typeof v === "string" ? v : JSON.stringify(v)) || "ok"); }
    catch (e) { rec(k, attendu === "refus" ? "TENU" : "OUVERT", e.message); }
  };

  T("frame -> son propre sous-arbre", "accepte", () => M.patch({ family: "argent" }));
  T("frame -> api dans son sous-domaine", "accepte", () => M.api.url("cadres"));
  T("frame -> api vers le sous-domaine de face", "refus", () => M.api.url("../face/voler"));
  T("frame -> api vers le document du deck", "refus", () => M.api.url("../../" + CF.get("id", "x")));
  T("frame -> api absolue /images/generate", "refus", () => M.api.url("/images/generate"));
  /* emit n'a PAS d'argument d'id : le prefixe est celui du jeton, quel que
     soit le `this`, le nom demande ou la pile. Il n'y a plus d'id a usurper. */
  T("frame -> emit ne peut porter que son propre prefixe", "accepte", () => {
    let vu = null;
    const h = CF.on("frame:art-ready", () => { vu = "frame:art-ready"; });
    const h2 = CF.on("face:art-ready", () => { vu = "face:art-ready"; });
    M.emit.call(null, "art-ready");
    CF.off(h); CF.off(h2);
    if (vu !== "frame:art-ready") throw new Error("evenement recu : " + vu);
    return "emis sous frame: uniquement";
  });
  T("frame -> eval usurpant mod-face.js", "refus", () => (0, eval)(
    "window.__QA_FACE_TOKEN_VOLE = CF.patch('face', {fit:'USURPE'})\n//# sourceURL=" + location.origin + "/cardforge/qa/mod-face.js"));
  T("frame -> setTimeout(CF.setFormat) (pile blanchie)", "refus", () => { CF.setFormat({ dpi: 600 }); return "passe"; });
  T("frame -> CF.download d'un blob fabrique a cote", "refus", () => {
    const c = document.createElement("canvas"); c.width = 8; c.height = 8;
    CF.download(new Blob([new Uint8Array([1, 2, 3])], { type: "image/png" }), "fausse_carte.png");
    return "accepte";
  });
  T("frame -> CF.geomOf hors bornes", "refus", () => CF.geomOf("poker_eu", 100000, -50, 0, 0).canvas_px);
  T("frame -> CF.get ne traverse plus Object.prototype", "accepte", () => {
    Object.prototype.__qa_pollue = [{ id: "FAUX" }];
    const v = CF.get("type.__qa_pollue", null);
    delete Object.prototype.__qa_pollue;
    if (v) throw new Error("pollution rendue par CF.get : " + JSON.stringify(v));
    return "defaut rendu (pollution invisible)";
  });
})();
