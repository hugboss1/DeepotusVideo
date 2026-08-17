/* qa — faux P3. Painter LENT (40 ms d'attente) : c'est lui qui rend la course
   de CF.side() observable. Sans await dans la boucle de painters, deux rendus
   concurrents ne s'entrelacent pas et le defaut reste invisible — c'est
   exactement pour cela qu'il faut un module d'essai, pas une console. */
"use strict";

(function () {
  const CF = window.CF;
  const M = CF.register({
    id: "type",
    title: "Typo (qa)",
    order: 3,
    painters: [
      {
        z: 60,
        async fn(ctx, geom, doc, card, side) {
          const vu = [];
          vu.push("entree:" + side + "/" + CF.side());
          await new Promise((r) => setTimeout(r, 40));
          vu.push("apres-await:" + side + "/" + CF.side());
          (window.__QA_SIDE_TRACE = window.__QA_SIDE_TRACE || []).push(vu.join(" "));
          ctx.fillStyle = "#111";
          ctx.font = "24px sans-serif";
          ctx.fillText(side === "back" ? "VERSO" : "RECTO", 20, 140);
        },
      },
    ],
    state: { slots: [] },
    init(host) { host.textContent = "type(qa)"; },
  });
  window.__QA_TYPE = M;
})();
