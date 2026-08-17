/* qa — faux P6. Deux painters HOSTILES, actives a la demande par la batterie
   (sinon le boot durerait le delai de garde) :
     z=10  une promesse qui ne se resout JAMAIS — une image ou une police qui
           ne charge pas. Elle gelait renderCard pour toujours : l'apercu
           restait `drawing=true` et TOUTES les invalidations suivantes etaient
           jetees, sans erreur ni toast. Les sept autres pieces mouraient avec.
     z=30  redimensionne la toile. Le controle etait HORS du try/catch : le
           rendu ENTIER tombait, l'exception partait dans le .catch() de
           l'apercu, RENDER_ERRORS restait vide et le bandeau restait muet. */
"use strict";

(function () {
  const CF = window.CF;
  const rec = (k, verdict, detail) => window.__CFQA.push({ k, verdict, detail: String(detail) });

  /* la TABLE Z est gelee : ce module ne peut pas prendre le z d'un autre,
     meme dans son PROPRE appel a register, depuis son PROPRE fichier. */
  try {
    CF.register({ id: "texture", title: "vol de z", state: {}, init() { }, painters: [{ z: 20, fn() { } }] });
    rec("table z : texture enregistre un painter a z=20 (face)", "OUVERT", "ACCEPTE");
  } catch (e) {
    rec("table z : texture enregistre un painter a z=20 (face)", "TENU", e.message);
  }
  try {
    CF.register({ id: "texture", title: "vol des reperes", state: {}, init() { }, painters: [{ z: 90, fn() { } }] });
    rec("table z : texture enregistre un painter a z=90 (CORE)", "OUVERT", "ACCEPTE");
  } catch (e) {
    rec("table z : texture enregistre un painter a z=90 (CORE)", "TENU", e.message);
  }

  const M = CF.register({
    id: "texture",
    title: "Matières (qa)",
    order: 6,
    painters: [
      {
        z: 10,
        fn(ctx, geom, doc, card, side) {
          ctx.fillStyle = "#f2ead8";
          ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
          if (window.__QA_HANG) return new Promise(() => { });   /* jamais resolue */
          return undefined;
        },
      },
      {
        z: 30,
        fn(ctx, geom, doc, card, side) {
          if (window.__QA_RESIZE) { ctx.canvas.width = 64; ctx.canvas.height = 64; }
          ctx.fillStyle = "rgba(0,0,0,.05)";
          ctx.fillRect(0, 0, ctx.canvas.width, 6);
        },
      },
    ],
    state: { paper: "lin", grain: 0.2 },
    init(host) { host.textContent = "texture(qa)"; },
  });
  window.__QA_TEXTURE = M;
})();
