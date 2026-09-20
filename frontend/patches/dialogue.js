/*__DZ_DIALOGUE_BEGIN__*/
/* dialogue.js — dialogues maison du bundle (finitions UI, 20/09/2026).

   Le « 127.0.0.1:8765 indique » des captures de l'utilisateur est le titre
   du dialogue NATIF du navigateur (confirm / alert). Cette couche pose
   `window.__dzDialogue.confirmer(msg, o)` → Promise<bool> et
   `.informer(msg)` → Promise<void>, REMPLACE `window.alert` (non bloquant,
   même contrat visuel), et le patcher réécrit les 11 sites `confirm(` du
   bundle en `await window.__dzDialogue.confirmer(` (leurs fonctions
   deviennent async là où elles ne l'étaient pas).

   CHARTE (design_handoff_icones_couleurs §1 / §2.1) : surfaces --srf-panel
   / --srf-raised, filets --brd-hard / --brd-soft, textes --txt-hi /
   --txt-base / --txt-mid, en-tête IBM Plex Mono 9,5 px letter-spacing
   .12em en capitales, aucun arrondi de châssis. Entrée = bouton par
   défaut, Échap = annuler, Tab piégé, bouton danger rouge quand le message
   parle de supprimer. Vanilla DOM : aucune dépendance au runtime React. */
(function () {
  if (window.__dzDialogue) return;
  var S = {
    voile: "position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:420px;max-width:92vw;background:var(--srf-panel,#13171c);border:1px solid var(--brd-hard,#2a3138);color:var(--txt-hi,#e6e9ee);box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,#222830);font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,#9aa4ae)",
    corps: "padding:14px;white-space:pre-wrap;word-break:break-word;color:var(--txt-base,#cfd6e2)",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,#222830)",
    btn: "min-width:88px;height:28px;padding:0 12px;background:var(--srf-raised,#1b2028);border:1px solid var(--brd-hard,#2a3138);color:var(--txt-hi,#e6e9ee);cursor:pointer;font:inherit",
    ok: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6)",
    danger: "background:#c0392b;border-color:#c0392b"
  };
  var courant = null;
  function ouvrir(type, message, o) {
    o = o || {};
    return new Promise(function (resoudre) {
      if (courant) courant();
      var voile = document.createElement("div");
      voile.setAttribute("style", S.voile);
      voile.setAttribute("role", "dialog");
      voile.setAttribute("aria-modal", "true");
      voile.className = "dz-dialogue";
      var danger = !!o.danger || (type === "confirmer" && /supprimer|delete|remove|irr[eé]versible/i.test(String(message)));
      var titre = o.titre || (type === "confirmer" ? "Confirmer" : "Information");
      var boutons = type === "confirmer"
        ? [["annuler", o.annuler || "Annuler", ""], ["ok", o.ok || (danger ? "Supprimer" : "OK"), danger ? S.danger : S.ok]]
        : [["ok", o.ok || "Fermer", S.ok]];
      var defaut = (type === "confirmer" && danger) ? "annuler" : "ok";
      var boite = document.createElement("div"); boite.setAttribute("style", S.boite);
      var tete = document.createElement("div"); tete.setAttribute("style", S.tete); tete.textContent = titre;
      var corps = document.createElement("div"); corps.setAttribute("style", S.corps);
      corps.textContent = String(message == null ? "" : message);
      var pied = document.createElement("div"); pied.setAttribute("style", S.pied);
      var fini = false;
      var surTouche;
      var fin = function (role) {
        if (fini) return;
        fini = true; courant = null;
        document.removeEventListener("keydown", surTouche, true);
        voile.remove();
        resoudre(type === "confirmer" ? role === "ok" : undefined);
      };
      courant = function () { fin("annuler"); };
      surTouche = function (ev) {
        ev.stopPropagation();
        if (ev.key === "Enter") { ev.preventDefault(); fin(defaut); }
        else if (ev.key === "Escape") { ev.preventDefault(); fin(type === "confirmer" ? "annuler" : "ok"); }
        else if (ev.key === "Tab") {
          ev.preventDefault();
          var f = pied.querySelectorAll("button");
          var i = Array.prototype.indexOf.call(f, document.activeElement);
          f[((ev.shiftKey ? i - 1 : i + 1) + f.length) % f.length].focus();
        }
      };
      var focusDefaut = null;
      boutons.forEach(function (b) {
        var el = document.createElement("button");
        el.type = "button"; el.setAttribute("style", S.btn + ";" + b[2]);
        el.textContent = b[1]; el.dataset.role = b[0];
        el.addEventListener("click", function () { fin(b[0]); });
        pied.appendChild(el);
        if (b[0] === defaut) focusDefaut = el;
      });
      boite.appendChild(tete); boite.appendChild(corps); boite.appendChild(pied);
      voile.appendChild(boite);
      voile.addEventListener("click", function (ev) { if (ev.target === voile) fin(type === "confirmer" ? "annuler" : "ok"); });
      document.body.appendChild(voile);
      document.addEventListener("keydown", surTouche, true);
      if (focusDefaut) focusDefaut.focus();
    });
  }
  window.__dzDialogue = {
    confirmer: function (m, o) { return ouvrir("confirmer", m, o); },
    informer: function (m, o) { return ouvrir("informer", m, o); },
    ouvert: function () { return !!courant; }
  };
  window.alert = function (m) { return window.__dzDialogue.informer(m); };
})();
/*__DZ_DIALOGUE_END__*/
