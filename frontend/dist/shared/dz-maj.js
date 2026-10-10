/* dz-maj.js — le BANDEAU DE MISE À JOUR (tâche #18, plan Settings T11, 29/09/2026).
   SOURCE : frontend/shared/dz-maj.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-maj.js, servie à
   /shared/dz-maj.js et chargée par une balise classique dans la SPA seulement (frontend/dist/index.html) : les
   pages à part s'ouvrent depuis la SPA, un seul bandeau suffit. Banc : backend/tests/test_p2_maj_ecran.py.

   Le serveur vérifie la dernière Release GitHub une fois par jour au plus (backend/app/services/mise_a_jour.py) ;
   la couche lit le CACHE (/api/reglages/maj, jamais bloquant) 2,5 s après le chargement. Si une version plus récente
   existe, une carte non bloquante centrée sous l'en-tête : version, taille de l'installeur, « Notes de version »,
   « Télécharger » (le serveur range l'installeur dans le dossier de données, EN FOND ; la couche suit le pourcentage
   puis dit le chemin — l'application ne lance JAMAIS l'installeur, c'est l'utilisateur) et « Plus tard », mémorisé
   PAR BALISE (refuser v2.9.0 ne masque pas v3.0.0). Vanilla DOM, aucune dépendance au runtime React. */
(function () {
  if (window.__dzMaj) return;
  var RYTHME_MS = 1200;
  var CLE = "dz_maj_vu_";

  function vu(tag) {
    try { return !!localStorage.getItem(CLE + tag); } catch (e) { return false; }
  }
  function marquer(tag) {
    try { localStorage.setItem(CLE + tag, "1"); } catch (e) { /* stockage indisponible : il reviendra */ }
  }
  function mo(o) { return Math.round((Number(o) || 0) / 1048576) + " Mo"; }
  /* Deepotus Glyph (G6) : l'icône tirée du SPRITE servi (/shared/icons/dz-icons.svg) par <use> — aucune dépendance
     au runtime dz-icons.js. Décorative : le libellé du bouton porte le sens. */
  function glyphe(cle, t) {
    var ns = "http://www.w3.org/2000/svg", s = document.createElementNS(ns, "svg"), u = document.createElementNS(ns, "use");
    s.setAttribute("class", "dzi"); s.setAttribute("width", String(t)); s.setAttribute("height", String(t));
    s.setAttribute("aria-hidden", "true"); s.setAttribute("focusable", "false"); s.setAttribute("data-dz-icone", cle);
    s.setAttribute("style", "vertical-align:-3px;margin-right:6px;fill:currentColor");
    u.setAttribute("href", "/shared/icons/dz-icons.svg#" + cle);
    s.appendChild(u);
    return s;
  }

  function bouton(texte, titre, principal) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = texte;
    b.title = titre;
    b.style.cssText = "height:26px;padding:0 12px;border:1px solid var(--brd-hard,var(--stroke,#2a3138));cursor:pointer;"
      + "font:inherit;font-size:12px;" + (principal
        ? "background:var(--brand,#e0b43c);color:#04121a;border-color:var(--brand,#e0b43c)"
        : "background:var(--srf-raised,var(--bg-panel,#1b2028));color:var(--txt-hi,var(--ink,#e6e9ee))");
    return b;
  }

  function suivre(dl, texte, fin) {
    var tic = setInterval(function () {
      fetch("/api/reglages/maj/telechargement").then(function (R) { return R.json(); }).then(function (p) {
        if (p.fini) {
          clearInterval(tic);
          if (p.erreur) { texte.textContent = "Échec du téléchargement : " + p.erreur; dl.disabled = false; dl.textContent = "Réessayer"; }
          else { texte.textContent = "Installeur enregistré : " + p.chemin + " — fermez l'application puis lancez-le."; dl.remove(); }
          if (fin) fin(p);
          return;
        }
        if (p.total) dl.textContent = "Téléchargement " + Math.round(100 * p.octets / p.total) + " %";
      }).catch(function () { /* on réessaie au tic suivant */ });
    }, RYTHME_MS);
    return tic;
  }

  function poser(m) {
    if (!m || !m.disponible || !m.tag || vu(m.tag)) return null;
    var w = document.createElement("div");
    w.setAttribute("data-dz-maj", m.tag);
    w.setAttribute("role", "status");
    // preuve 8799 (29/09) : une barre pleine largeur à top:0 recouvrait l'en-tête de l'application (commande
    // rapide, pastilles) -> carte flottante centrée SOUS l'en-tête
    w.style.cssText = "position:fixed;top:52px;left:50%;transform:translateX(-50%);width:max-content;max-width:min(820px,92vw);"
      + "z-index:9997;display:flex;gap:12px;align-items:center;padding:8px 14px;"
      + "background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke,#2a3138));"
      + "border-left:4px solid var(--brand,#e0b43c);box-shadow:0 10px 30px rgba(0,0,0,.45);"
      + "color:var(--txt-base,var(--ink,#cfd6e2));font:12.5px/1.4 system-ui,sans-serif";
    var t = document.createElement("div");
    t.style.cssText = "flex:1";
    var a = m.asset || {};
    t.textContent = "Version " + m.tag + " disponible (vous avez la " + m.installee + ")."
      + (a.nom ? " Installeur : " + a.nom + " — " + mo(a.octets) + "." : "");
    w.appendChild(t);
    if (m.url) {
      var n = document.createElement("a");
      n.textContent = "Notes de version";
      n.href = m.url; n.target = "_blank"; n.rel = "noreferrer";
      n.title = "La page de la Release sur GitHub";
      n.style.cssText = "color:var(--cyan,#5fc6ff);text-decoration:none";
      w.appendChild(n);
    }
    if (a.url) {
      var dl = bouton("Télécharger", "Enregistre l'installeur dans le dossier de données (" + mo(a.octets) + ") — il ne sera pas lancé", true);
      if (document.createElementNS && dl.insertBefore) dl.insertBefore(glyphe("dz-action-telecharger", 14), dl.firstChild);
      dl.onclick = function () {
        dl.disabled = true;
        dl.textContent = "Téléchargement…";
        fetch("/api/reglages/maj/telecharger", { method: "POST" }).then(function (R) {
          return R.json().then(function (j) { return { ok: R.ok, j: j }; });
        }).then(function (x) {
          if (!x.ok) { t.textContent = "Échec : " + ((x.j && x.j.detail) || "refus du serveur"); dl.disabled = false; dl.textContent = "Réessayer"; return; }
          suivre(dl, t);
        }).catch(function (e) { t.textContent = "Échec : " + e; dl.disabled = false; dl.textContent = "Réessayer"; });
      };
      w.appendChild(dl);
    }
    var plus = bouton("Plus tard", "Masquer ce bandeau pour la version " + m.tag + " (une version plus récente le fera revenir)", false);
    plus.onclick = function () { marquer(m.tag); if (w.parentNode) w.parentNode.removeChild(w); };
    w.appendChild(plus);
    (document.body || document.documentElement).appendChild(w);
    return w;
  }

  function verifier() {
    return fetch("/api/reglages/maj").then(function (R) { return R.ok ? R.json() : null; })
      .then(poser).catch(function () { return null; });
  }

  window.__dzMaj = { poser: poser, verifier: verifier, suivre: suivre, rythmeMs: RYTHME_MS };
  setTimeout(verifier, 2500);
})();
