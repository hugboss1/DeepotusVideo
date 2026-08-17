/* qa — faux P1. Module LEGITIME : bon dossier, bon id, "use strict".
   Il enregistre un painter a son z (20) et publie son jeton pour que la
   batterie puisse verifier ce que le jeton autorise et ce qu'il refuse. */
"use strict";

(function () {
  const CF = window.CF;
  const rec = (k, verdict, detail) => window.__CFQA.push({ k, verdict, detail: String(detail) });
  const T = (k, attendu, fn) => {
    try { const v = fn(); rec(k, attendu === "refus" ? "OUVERT" : "TENU", JSON.stringify(v) || "ok"); }
    catch (e) { rec(k, attendu === "refus" ? "TENU" : "OUVERT", e.message); }
  };

  /* AVANT d'avoir le moindre jeton : le global n'ecrit plus nulle part. */
  T("global CF.patch depuis un module", "refus", () => CF.patch("face", { fit: "x" }));
  T("global CF.setFormat depuis un module", "refus", () => CF.setFormat({ dpi: 600 }));
  T("global CF.setFormat via forEach (pile blanchie)", "refus", () => { [{ dpi: 600 }].forEach(CF.setFormat); return "passe"; });
  T("global CF.api.patch", "refus", () => CF.api.patch("/cards/x", {}));
  T("window.CF remplacable", "refus", () => {
    "use strict";
    window.CF = { faux: true };
    return "swap accepte";
  });

  const M = CF.register({
    id: "face",
    title: "Face (qa)",
    icon: "\u{1F3A8}",
    order: 1,
    painters: [
      {
        z: 20,
        fn(ctx, geom, doc, card, side) {
          /* LA SIGNATURE : cinq arguments, aucun `scale`. Un painter ne peut
             donc plus distinguer l'apercu du fichier livre. On enregistre ce
             que l'on recoit pour que la batterie le prouve. */
          window.__QA_PAINTER_ARGS = {
            n: arguments.length,
            types: Array.prototype.map.call(arguments, (a) => (a && a.constructor ? a.constructor.name : typeof a)),
            side: String(side),
            transform: (function () { try { const m = ctx.getTransform(); return [m.a, m.b, m.c, m.d, m.e, m.f]; } catch (e) { return null; } })(),
            canvas: [ctx.canvas.width, ctx.canvas.height],
          };
          ctx.fillStyle = "#8844cc";
          ctx.fillRect(10, 10, 60, 60);
        },
      },
    ],
    state: { src: null, fit: "cover", x: 0, y: 0, scale: 1 },
    init(host) { host.textContent = "face(qa)"; },
  });

  window.__QA_FACE = M;
  rec("jeton rendu a mod-face.js", M && M.id === "face" ? "TENU" : "OUVERT", M ? Object.keys(M).join(",") : "aucun");
  T("jeton face : cle hors schema", "refus", () => M.patch({ pas_au_schema: 1 }));
  T("jeton face : cle du schema", "accepte", () => M.patch({ fit: "contain" }));
  T("jeton face : setCards absent du jeton", "refus", () => M.setCards([]));
  T("jeton face : setFormat absent du jeton", "refus", () => M.setFormat({ dpi: 600 }));
  T("jeton face : api hors de son sous-domaine", "refus", () => M.api.url("../frame/vol"));
  T("jeton face : api absolue", "refus", () => M.api.url("/health"));
  rec("jeton face : api chez soi", "TENU", M.api.url("faces"));
})();
