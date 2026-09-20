/*__DZ_DIALOGUE_BEGIN__*/
/* dialogue.js — les dialogues maison de TOUTE l'application (finitions UI,
   20/09/2026). SOURCE : frontend/shared/dialogue.js ; copies OCTET POUR
   OCTET : frontend/dist/shared/dialogue.js (servi à /shared/dialogue.js pour
   l'Atelier, le Cardforge, le Studio 3D, l'Établi, le Spritelab, le Tilelab,
   le Material Forge) et frontend/patches/dialogue.js (injecté dans le bundle
   React par scripts/patch_bundle_dialogue.py). Le banc
   backend/tests/test_dialogue_bundle.py refuse toute dérive entre les trois.

   Le « 127.0.0.1:8765 indique » des captures de l'utilisateur est le titre du
   dialogue NATIF du navigateur (confirm / alert / prompt). Cette couche pose
   `window.__dzDialogue.confirmer(msg, o)` → Promise<bool>,
   `.informer(msg)` → Promise<void>, `.saisir(msg, o)` → Promise<string|null>
   (le contrat de prompt : null = annulé), et REMPLACE `window.alert` (non
   bloquant, même contrat visuel). Les sites `confirm(` / `prompt(` de
   l'application sont réécrits en `await window.__dzDialogue.…(`.

   CHARTE (design_handoff_icones_couleurs §1 / §2.1) : surfaces --srf-panel /
   --srf-raised (repli sur les jetons des pages standalone --bg-panel-2 /
   --bg-panel-3, puis un hex), filets --brd-hard / --brd-soft (repli
   --stroke), textes --txt-hi / --txt-base / --txt-mid (repli --ink),
   en-tête IBM Plex Mono 9,5 px letter-spacing .12em en capitales, aucun
   arrondi de châssis. Entrée = bouton par défaut, Échap = annuler, Tab
   piégé, bouton danger rouge quand le message parle de supprimer. Vanilla
   DOM : aucune dépendance au runtime React ni à une page. */
(function () {
  if (window.__dzDialogue) return;
  var S = {
    voile: "position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:420px;max-width:92vw;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:14px;white-space:pre-wrap;word-break:break-word;color:var(--txt-base,var(--ink,#cfd6e2))",
    champ: "display:block;width:100%;box-sizing:border-box;margin-top:10px;height:28px;padding:0 8px;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:inherit",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    ok: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    danger: "background:#c0392b;border-color:#c0392b;color:#ffffff"
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
      var danger = !!o.danger || (type === "confirmer" && /supprimer|delete|remove|irr[eé]versible|remplacera|interrompt/i.test(String(message)));
      var titre = o.titre || (type === "confirmer" ? "Confirmer" : type === "saisir" ? "Saisie" : "Information");
      var boutons = type === "informer"
        ? [["ok", o.ok || "Fermer", S.ok]]
        : [["annuler", o.annuler || "Annuler", ""], ["ok", o.ok || (danger ? "Supprimer" : "OK"), danger ? S.danger : S.ok]];
      var defaut = (type === "confirmer" && danger) ? "annuler" : "ok";
      var boite = document.createElement("div"); boite.setAttribute("style", S.boite);
      var tete = document.createElement("div"); tete.setAttribute("style", S.tete); tete.textContent = titre;
      var corps = document.createElement("div"); corps.setAttribute("style", S.corps);
      corps.textContent = String(message == null ? "" : message);
      var champ = null;
      if (type === "saisir") {
        champ = document.createElement("input"); champ.type = "text"; champ.setAttribute("style", S.champ);
        champ.value = o.valeur == null ? "" : String(o.valeur);
        if (o.placeholder) champ.placeholder = o.placeholder;
        corps.appendChild(champ);
      }
      var pied = document.createElement("div"); pied.setAttribute("style", S.pied);
      var fini = false;
      var surTouche;
      var fin = function (role) {
        if (fini) return;
        fini = true; courant = null;
        var valeur = champ ? champ.value : null;
        document.removeEventListener("keydown", surTouche, true);
        voile.remove();
        if (type === "confirmer") resoudre(role === "ok");
        else if (type === "saisir") resoudre(role === "ok" ? String(valeur == null ? "" : valeur) : null);
        else resoudre(undefined);
      };
      courant = function () { fin("annuler"); };
      surTouche = function (ev) {
        ev.stopPropagation();
        if (ev.key === "Enter") { ev.preventDefault(); fin(defaut); }
        else if (ev.key === "Escape") { ev.preventDefault(); fin(type === "informer" ? "ok" : "annuler"); }
        else if (ev.key === "Tab") {
          ev.preventDefault();
          var f = Array.prototype.slice.call(voile.querySelectorAll("input, button"));
          var i = f.indexOf(document.activeElement);
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
      voile.addEventListener("click", function (ev) { if (ev.target === voile) fin(type === "informer" ? "ok" : "annuler"); });
      document.body.appendChild(voile);
      document.addEventListener("keydown", surTouche, true);
      if (champ) { champ.focus(); champ.select(); } else if (focusDefaut) focusDefaut.focus();
    });
  }
  window.__dzDialogue = {
    confirmer: function (m, o) { return ouvrir("confirmer", m, o); },
    informer: function (m, o) { return ouvrir("informer", m, o); },
    saisir: function (m, o) { return ouvrir("saisir", m, o); },
    ouvert: function () { return !!courant; }
  };
  window.alert = function (m) { return window.__dzDialogue.informer(m); };
})();
/*__DZ_DIALOGUE_END__*/
