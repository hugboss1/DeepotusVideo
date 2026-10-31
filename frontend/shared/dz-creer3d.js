/* dz-creer3d.js — l'onglet 3D de Game Assets devient « CRÉER » (t389, chantier « 3D Studio à écrans », 31/10/2026,
   plan docs/superpowers/plans/2026-10-31-studio3d-ecrans.md, décision D1) : il ne fait plus que GÉNÉRER le modèle de
   base ; Préparer, Texture, Rig, Affiner, Animer, Exporter et Décor vivent dans le 3D Studio.
   SOURCE : frontend/shared/dz-creer3d.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-creer3d.js, chargée par
   une balise classique dans la SPA (frontend/dist/index.html). L'hôte est posé par le maillon de queue dzcreer3d
   (scripts/patch_bundle_dzcreer3d.py) en tête de l'onglet 3D ; l'ancien formulaire (DzGameAssets) reste dessous,
   replié, le temps de la transition.

   Relevé de Sorceress (Create) : à gauche les modèles (cases à cocher, un job par modèle, réglages par roue), au
   centre la galerie (filtres, cartes par ligne, recherche, volet avant/après source ↔ rendu, liens vers les écrans),
   à droite la saisie (Image / Texte / Multi-images, quantité 1-4, total estimé, Générer). Serveur :
   /api/assets3d/engines (registre + schémas de réglages), /api/studio3d/creer/devis (gratuit), /api/studio3d/creer
   (payant : dialogue maison AVANT, `confirme_cout`, plafond « moteurs3d »), /api/studio3d/modeles (galerie).
   Textes : dzT, zone creer3d (frontend/shared/i18n/creer3d.json). Charte : aucun arrondi, jetons de couleur.

   Le CALCUL (groupes de modèles, corps d'envoi, filtres, relais vers le 3D Studio) est exporté sous node
   (module.exports) pour le banc frontend/shared/qa/creer3d.test.mjs. */
(function () {
  "use strict";

  var FOURNISSEURS = { "tripo": "Tripo", "tripo-h3.1": "Tripo", "tripo-p2": "Tripo", "tripo-p1": "Tripo",
    "triposr": "Tripo", "hunyuan": "Hunyuan", "hunyuan-3.1": "Hunyuan", "hunyuan-local": "Hunyuan",
    "trellis": "Microsoft", "trellis-2": "Microsoft", "rodin": "Hyper3D", "rodin-2.5": "Hyper3D", "meshy-7.1": "Meshy" };
  var ORDRE = ["Meshy", "Tripo", "Hunyuan", "Microsoft", "Hyper3D"];
  var RELAIS = "deepotus.studio3d.ouvrir";

  var CALC = {
    /* les modèles rangés par fournisseur, dans l'ordre de Sorceress ; les neufs (t390) d'abord dans chaque groupe */
    groupes: function (engines) {
      var g = {};
      (engines || []).forEach(function (e) {
        var f = e.fournisseur || FOURNISSEURS[e.id] || "Autres";
        (g[f] = g[f] || []).push(e);
      });
      Object.keys(g).forEach(function (f) {
        g[f].sort(function (a, b) { return (b.neuf ? 1 : 0) - (a.neuf ? 1 : 0) || String(a.label).localeCompare(b.label); });
      });
      return Object.keys(g).sort(function (a, b) {
        var ia = ORDRE.indexOf(a), ib = ORDRE.indexOf(b);
        return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
      }).map(function (f) { return { fournisseur: f, moteurs: g[f] }; });
    },
    /* en mode texte, seuls les modèles qui savent générer depuis un texte restent cochables */
    cochable: function (e, mode) { return mode !== "texte" || !!e.texte; },
    /* le corps d'envoi : les réglages ne partent que pour les modèles cochés, et sans les valeurs vides */
    corps: function (s) {
      var reg = {};
      (s.moteurs || []).forEach(function (m) {
        var r = (s.reglages || {})[m];
        if (!r) return;
        var propre = {};
        Object.keys(r).forEach(function (k) { if (r[k] !== "" && r[k] != null) propre[k] = r[k]; });
        if (Object.keys(propre).length) reg[m] = propre;
      });
      var b = { mode: s.mode, moteurs: (s.moteurs || []).slice(), quantite: s.quantite || 1, reglages: reg,
        pose: s.pose || "", textures: s.textures !== false };
      if (s.mode === "texte") b.prompt = String(s.prompt || "").trim();
      else {
        b.images = (s.images || []).slice(0, s.mode === "image" ? 1 : 24);
        if (String(s.prompt || "").trim()) b.prompt = String(s.prompt).trim();
      }
      return b;
    },
    /* une valeur saisie dans l'accordéon, convertie au type du schéma (vide = défaut du modèle) */
    valeur: function (reglage, brut) {
      if (reglage.type === "bool") return !!brut;
      if (brut === "" || brut == null) return null;
      if (reglage.type === "int") { var n = parseInt(brut, 10); return isFinite(n) ? n : null; }
      for (var i = 0; i < (reglage.valeurs || []).length; i++) if (String(reglage.valeurs[i]) === String(brut)) return reglage.valeurs[i];
      return null;
    },
    filtres: ["tous", "rigges", "non_rigges"],
    filtrer: function (modeles, filtre, q) {
      q = String(q || "").trim().toLowerCase();
      return (modeles || []).filter(function (m) {
        var rg = !!(m.rig && m.rig.rigge);
        if (filtre === "rigges" && !rg) return false;
        if (filtre === "non_rigges" && rg) return false;
        return !q || [m.nom, m.job, m.moteur].some(function (x) { return String(x || "").toLowerCase().indexOf(q) >= 0; });
      });
    },
    /* le relais vers le 3D Studio : l'iframe du sous-onglet est recréée à chaque visite, sans paramètre ; la coque
       lit ce relais UNE fois au démarrage (s'il a moins d'une minute) puis l'efface */
    relais: function (job, ecran, maintenant) {
      return JSON.stringify({ job: String(job), ecran: String(ecran || "preparer"), t: maintenant || Date.now() });
    },
    usd: function (n) { return "$" + (Math.round(Number(n || 0) * 100) / 100).toFixed(2); },
  };

  if (typeof module !== "undefined" && module.exports) { module.exports = CALC; return; }
  if (window.__dzCreer3d) return;

  function T(k, v) { return typeof window.dzT === "function" ? window.dzT(k, v) : k; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function ico(cle) { return '<svg class="dzi dzi--16" aria-hidden="true" focusable="false"><use href="/shared/icons/dz-icons.svg#' + cle + '"></use></svg>'; }
  function jget(u) { return fetch(u).then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(msg(j, r.status)); return j; }); }); }
  function jpost(u, b) {
    return fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b || {}) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) { var e = new Error(msg(j, r.status)); e.status = r.status; e.detail = j && j.detail; throw e; } return j; }); });
  }
  function msg(j, st) { var d = j && j.detail; return typeof d === "string" ? d : (d && d.message) || String(st); }

  var STYLE = [
    ".c3d{display:grid;grid-template-columns:280px minmax(0,1fr) 300px;min-height:calc(100vh - 160px);border-bottom:1px solid var(--stroke);background:var(--bg-base);color:var(--ink)}",
    ".c3d *{box-sizing:border-box}",
    ".c3d-g,.c3d-d{background:var(--bg-panel);padding:14px;overflow:auto;display:flex;flex-direction:column;gap:8px;max-height:calc(100vh - 160px)}",
    ".c3d-g{border-right:1px solid var(--stroke)}.c3d-d{border-left:1px solid var(--stroke)}",
    ".c3d-c{padding:12px 16px;overflow:auto;max-height:calc(100vh - 160px)}",
    ".c3d-l{margin-top:6px;font-family:var(--f-mono,monospace);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-soft)}",
    ".c3d-n{font-size:11px;line-height:1.5;color:var(--ink-muted)}",
    ".c3d-m{border:1px solid var(--stroke);background:var(--bg-panel-2)}.c3d-m.on{border-color:var(--cat,var(--accent))}",
    ".c3d-m.off{opacity:.45}",
    ".c3d-mh{display:flex;align-items:center;gap:8px;padding:8px 10px}",
    ".c3d-mh b{color:var(--ink-strong);font-size:12.5px}.c3d-mh .px{margin-left:auto;font-family:var(--f-mono,monospace);font-size:10.5px;color:var(--ink-soft)}",
    ".c3d-badge{font-family:var(--f-mono,monospace);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;padding:1px 5px;border:1px solid var(--stroke-strong);color:var(--ink-soft)}",
    ".c3d-roue{border:1px solid var(--stroke);background:transparent;color:var(--ink-soft);width:24px;height:24px;cursor:pointer}",
    ".c3d-reg{display:grid;grid-template-columns:1fr auto;gap:6px 8px;padding:6px 10px 10px;font-size:11.5px}",
    ".c3d-reg select,.c3d-reg input[type=number],.c3d-d select,.c3d-d textarea,.c3d-c input[type=search]{background:var(--bg-panel-3);color:var(--ink-strong);border:1px solid var(--stroke);padding:4px 6px;font:inherit}",
    ".c3d-seg{display:flex;border:1px solid var(--stroke)}.c3d-seg button{flex:1;padding:7px 6px;border:0;border-right:1px solid var(--stroke);background:transparent;color:var(--ink-soft);cursor:pointer;font-size:12px}",
    ".c3d-seg button:last-child{border-right:0}.c3d-seg button.on{background:color-mix(in srgb,var(--cat,var(--accent)) 26%,transparent);color:var(--ink-strong)}",
    ".c3d-imgs{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;max-height:220px;overflow:auto}",
    ".c3d-imgs button{padding:0;border:1px solid var(--stroke);background:var(--bg-panel-3);aspect-ratio:1;cursor:pointer;overflow:hidden}",
    ".c3d-imgs button.on{border:2px solid var(--cat,var(--accent))}.c3d-imgs img{width:100%;height:100%;object-fit:cover}",
    ".c3d-go{width:100%;padding:11px;border:1px solid var(--cat,var(--accent));background:color-mix(in srgb,var(--cat,var(--accent)) 32%,var(--bg-panel-2));color:var(--ink-strong);font-weight:700;cursor:pointer}",
    ".c3d-go:disabled{opacity:.45;cursor:not-allowed}",
    ".c3d-total{display:flex;justify-content:space-between;align-items:baseline;font-size:12px}.c3d-total b{font-size:18px;color:var(--cat,var(--accent))}",
    ".c3d-avis{font-size:12px;color:var(--amber)}",
    ".c3d-out{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}",
    ".c3d-f{padding:5px 10px;border:1px solid var(--stroke);background:transparent;color:var(--ink-soft);font-family:var(--f-mono,monospace);font-size:11px;text-transform:uppercase;cursor:pointer}",
    ".c3d-f.on{border-color:var(--cat,var(--accent));color:var(--ink-strong)}",
    ".c3d-cartes{display:grid;grid-template-columns:repeat(var(--c3d-col,3),minmax(0,1fr));gap:12px}",
    ".c3d-carte{border:1px solid var(--stroke);background:var(--bg-panel)}",
    ".c3d-av{position:relative;aspect-ratio:1;background:var(--bg-panel-3);overflow:hidden}",
    ".c3d-av img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}",
    ".c3d-av .src{clip-path:inset(0 calc(100% - var(--c3d-cut,50%)) 0 0)}",
    ".c3d-av input{position:absolute;left:0;right:0;bottom:6px;width:100%}",
    ".c3d-ct{padding:8px 10px;display:flex;flex-direction:column;gap:2px}.c3d-ct b{font-size:12.5px;color:var(--ink-strong);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    ".c3d-ct span{font-family:var(--f-mono,monospace);font-size:10.5px;color:var(--ink-soft)}",
    ".c3d-ca{display:flex;flex-wrap:wrap;gap:4px;padding:0 8px 8px}.c3d-ca button,.c3d-b{padding:5px 8px;border:1px solid var(--stroke-strong);background:var(--bg-panel-2);color:var(--ink);font-size:11px;cursor:pointer}",
    ".c3d-cours{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}.c3d-cours div{display:flex;gap:8px;font-family:var(--f-mono,monospace);font-size:11px;color:var(--ink-soft)}",
    ".c3d-bar{flex:1;height:4px;background:var(--stroke);align-self:center}.c3d-bar i{display:block;height:100%;background:var(--cat,var(--accent))}",
    ".c3d-pose{border:1px solid var(--stroke);padding:8px;font-size:11.5px;line-height:1.5;color:var(--ink)}",
    "[data-dz-creer3d-ancien].c3d-replie{display:none}",
    ".c3d-ancien{margin:10px 16px;font-size:11.5px}",
  ].join("\n");

  function monter(el) {
    if (!el || el.__dzCreer3d) return;
    el.__dzCreer3d = true;
    if (!document.getElementById("dz-creer3d-style")) {
      var st = document.createElement("style");
      st.id = "dz-creer3d-style";
      st.textContent = STYLE;
      document.head.appendChild(st);
    }
    var S = { engines: [], moteurs: [], reglages: {}, ouverts: {}, mode: "image", images: [], prompt: "",
      quantite: 1, pose: "", biblio: [], modeles: [], filtre: "tous", q: "", col: 3, devis: null, cours: [],
      occupe: false, avis: "" };
    el.innerHTML = '<div class="c3d"><aside class="c3d-g"></aside><main class="c3d-c"></main><aside class="c3d-d"></aside></div>'
      + '<div class="c3d-ancien"><button class="c3d-b" data-ancien="1"></button></div>';
    var G = el.querySelector(".c3d-g"), C = el.querySelector(".c3d-c"), D = el.querySelector(".c3d-d");
    var ancien = el.parentNode && el.parentNode.querySelector("[data-dz-creer3d-ancien]");
    if (ancien) ancien.classList.add("c3d-replie");
    function peindreAncien() {
      el.querySelector("[data-ancien]").textContent = ancien && !ancien.classList.contains("c3d-replie")
        ? T("creer3d.ancien.masquer") : T("creer3d.ancien.montrer");
    }
    peindreAncien();
    el.querySelector("[data-ancien]").addEventListener("click", function () {
      if (ancien) ancien.classList.toggle("c3d-replie");
      peindreAncien();
    });

    /* ── colonne gauche : les modèles ── */
    function peindreG() {
      var h = '<div class="c3d-l">' + esc(T("creer3d.modeles.titre")) + "</div>";
      CALC.groupes(S.engines).forEach(function (g) {
        h += '<div class="c3d-l">' + esc(g.fournisseur) + "</div>";
        g.moteurs.forEach(function (e) {
          var on = S.moteurs.indexOf(e.id) >= 0, ok = CALC.cochable(e, S.mode);
          var prix = e.local ? T("creer3d.modeles.gratuit") : CALC.usd(e.usd_texture);
          h += '<div class="c3d-m' + (on ? " on" : "") + (ok ? "" : " off") + '"><div class="c3d-mh">'
            + '<input type="checkbox" data-moteur="' + esc(e.id) + '"' + (on ? " checked" : "") + (ok ? "" : " disabled")
            + ' aria-label="' + esc(e.label) + '"><b>' + esc(e.label) + "</b>"
            + (e.badge ? '<span class="c3d-badge">' + esc(T("creer3d.badge." + e.badge)) + "</span>" : "")
            + '<span class="px">' + esc(prix) + "</span>"
            + (e.reglages && e.reglages.length ? '<button class="c3d-roue" data-roue="' + esc(e.id) + '" title="'
              + esc(T("creer3d.modeles.reglages")) + '" aria-label="' + esc(T("creer3d.modeles.reglages")) + '">⚙</button>' : "")
            + "</div>";
          if (S.ouverts[e.id] && e.reglages) {
            var r = S.reglages[e.id] || {};
            h += '<div class="c3d-reg">';
            e.reglages.forEach(function (x) {
              var v = r[x.cle] != null ? r[x.cle] : x.defaut;
              h += "<label for=\"c3d-" + esc(e.id + x.cle) + "\">" + esc(x.cle) + (x.surcout ? " (+" + CALC.usd(x.surcout) + ")" : "") + "</label>";
              if (x.type === "bool") h += '<input type="checkbox" id="c3d-' + esc(e.id + x.cle) + '" data-reg="' + esc(e.id) + '" data-cle="' + esc(x.cle) + '"' + (v ? " checked" : "") + ">";
              else if (x.type === "enum") h += '<select id="c3d-' + esc(e.id + x.cle) + '" data-reg="' + esc(e.id) + '" data-cle="' + esc(x.cle) + '">'
                + x.valeurs.map(function (o) { return '<option value="' + esc(o) + '"' + (String(o) === String(v) ? " selected" : "") + ">" + esc(o) + "</option>"; }).join("") + "</select>";
              else h += '<input type="number" id="c3d-' + esc(e.id + x.cle) + '" data-reg="' + esc(e.id) + '" data-cle="' + esc(x.cle) + '" min="' + x.min + '" max="' + x.max + '" placeholder="' + esc(T("creer3d.modeles.auto")) + '" value="' + (v == null ? "" : esc(v)) + '" style="width:100px">';
            });
            h += "</div>";
          }
          h += "</div>";
        });
      });
      h += '<div class="c3d-l">' + esc(T("creer3d.pose.titre")) + '</div><div class="c3d-pose">' + esc(T("creer3d.pose.conseil")) + "</div>"
        + '<div class="c3d-seg">' + ["", "a-pose", "t-pose"].map(function (p) {
          return '<button data-pose="' + p + '" class="' + (S.pose === p ? "on" : "") + '">' + esc(T("creer3d.pose." + (p || "aucune").replace("-", "_"))) + "</button>";
        }).join("") + "</div>";
      G.innerHTML = h;
    }

    /* ── colonne droite : la saisie ── */
    function peindreD() {
      var h = '<div class="c3d-l">' + esc(T("creer3d.saisie.mode")) + '</div><div class="c3d-seg">'
        + ["image", "texte", "multi"].map(function (m) { return '<button data-mode="' + m + '" class="' + (S.mode === m ? "on" : "") + '">' + esc(T("creer3d.mode." + m)) + "</button>"; }).join("") + "</div>"
        + '<div class="c3d-n">' + esc(T("creer3d.aide." + S.mode)) + "</div>";
      if (S.mode !== "texte") {
        h += '<div class="c3d-l">' + esc(T("creer3d.saisie.images", { n: S.images.length })) + '</div><div class="c3d-imgs">'
          + S.biblio.slice(0, 80).map(function (f) {
            return '<button data-img="' + esc(f) + '" class="' + (S.images.indexOf(f) >= 0 ? "on" : "") + '" title="' + esc(f) + '"><img loading="lazy" alt="" src="/api/images/' + encodeURIComponent(f) + '"></button>';
          }).join("") + "</div>";
      }
      h += '<div class="c3d-l">' + esc(T(S.mode === "texte" ? "creer3d.saisie.prompt" : "creer3d.saisie.sujet")) + "</div>"
        + '<textarea rows="3" maxlength="1000" data-prompt="1" style="width:100%">' + esc(S.prompt) + "</textarea>"
        + '<div class="c3d-l">' + esc(T("creer3d.saisie.quantite")) + '</div><div class="c3d-seg">'
        + [1, 2, 3, 4].map(function (q) { return '<button data-q="' + q + '" class="' + (S.quantite === q ? "on" : "") + '">' + q + "</button>"; }).join("") + "</div>"
        + '<div class="c3d-n">' + esc(S.devis ? T("creer3d.saisie.tirs", { n: S.devis.tirs }) : "") + "</div>"
        + '<div class="c3d-total"><span>' + esc(T("creer3d.saisie.estime")) + "</span><b>" + esc(S.devis ? CALC.usd(S.devis.total_usd) : "—") + "</b></div>"
        + '<button class="c3d-go" data-go="1"' + (S.devis && !S.occupe ? "" : " disabled") + ">" + ico("dz-lab3d-generer-modele") + " " + esc(T("creer3d.saisie.generer")) + "</button>"
        + '<div class="c3d-avis">' + esc(S.avis) + "</div>"
        + '<div class="c3d-n">' + esc(T("creer3d.saisie.suite")) + "</div>";
      D.innerHTML = h;
    }

    /* ── centre : la galerie ── */
    function peindreC() {
      var liste = CALC.filtrer(S.modeles, S.filtre, S.q);
      var h = '<div class="c3d-out">' + CALC.filtres.map(function (f) {
        return '<button class="c3d-f' + (S.filtre === f ? " on" : "") + '" data-filtre="' + f + '">' + esc(T("creer3d.filtre." + f)) + " " + CALC.filtrer(S.modeles, f, "").length + "</button>";
      }).join("") + '<label class="c3d-n" style="margin-left:auto">' + esc(T("creer3d.galerie.grille"))
        + ' <input type="range" min="2" max="5" value="' + S.col + '" data-col="1"></label>'
        + '<input type="search" data-q="s" placeholder="' + esc(T("creer3d.galerie.recherche")) + '" value="' + esc(S.q) + '"></div>';
      if (S.cours.length) {
        h += '<div class="c3d-cours">' + S.cours.map(function (c) {
          return "<div><span>" + esc(c.moteur) + " · " + esc(c.job) + '</span><span class="c3d-bar"><i style="width:' + (c.pct || 0) + '%"></i></span><span>' + esc(c.etape || "") + "</span></div>";
        }).join("") + "</div>";
      }
      if (!liste.length) h += '<div class="c3d-n">' + esc(T("creer3d.galerie.vide")) + "</div>";
      h += '<div class="c3d-cartes" style="--c3d-col:' + S.col + '">' + liste.map(function (m) {
        var rg = m.rig && m.rig.rigge;
        return '<article class="c3d-carte"><div class="c3d-av">'
          + (m.vignette ? '<img alt="" loading="lazy" src="' + esc(m.vignette) + '">' : "")
          + (m.source ? '<img class="src" alt="" loading="lazy" src="' + esc(m.source) + '"><input type="range" min="0" max="100" value="50" data-av="1" aria-label="' + esc(T("creer3d.galerie.avant_apres")) + '">' : "")
          + '</div><div class="c3d-ct"><b title="' + esc(m.nom) + '">' + esc(m.nom) + "</b><span>" + esc((m.moteur || "") + (rg ? " · " + T("creer3d.galerie.rigge") : "")) + "</span></div>"
          + '<div class="c3d-ca">' + ["preparer", "texture", "rig", "animer", "decor"].map(function (e) {
            return '<button data-ouvrir="' + esc(m.job) + '" data-ecran="' + e + '">' + esc(T("creer3d.ouvrir." + e)) + "</button>";
          }).join("") + "</div></article>";
      }).join("") + "</div>";
      C.innerHTML = h;
    }

    function tout() { peindreG(); peindreC(); peindreD(); }

    var minuterie = 0;
    function devis() {
      clearTimeout(minuterie);
      S.devis = null;
      minuterie = setTimeout(function () {
        if (!S.moteurs.length || (S.mode === "texte" ? !S.prompt.trim() : !S.images.length)) { S.avis = ""; peindreD(); return; }
        jpost("/api/studio3d/creer/devis", CALC.corps(S)).then(function (d) { S.devis = d; S.avis = ""; peindreD(); })
          .catch(function (e) { S.avis = e.message; peindreD(); });
      }, 250);
      peindreD();
    }

    function generer() {
      if (!S.devis || S.occupe) return;
      var corps = CALC.corps(S);
      var montant = CALC.usd(S.devis.total_usd);
      var dlg = window.__dzDialogue;
      if (!dlg || !dlg.confirmer) { S.avis = T("creer3d.action.sans_dialogue"); return peindreD(); }
      Promise.resolve(dlg.confirmer(T("creer3d.action.confirmer", { n: S.devis.tirs, p: montant }))).then(function (oui) {
        if (!oui) return;
        S.occupe = true; peindreD();
        corps.confirme_cout = true;
        corps.max_usd = S.devis.total_usd;
        return jpost("/api/studio3d/creer", corps).then(function (r) {
          S.cours = (r.tirs || []).map(function (t) { return { job: t.job, job_id: t.job_id, moteur: t.moteur, pct: 5, etape: "" }; }).concat(S.cours);
          S.avis = T("creer3d.action.lance", { n: (r.tirs || []).length });
          suivre();
        });
      }).catch(function (e) { S.avis = e.message; }).then(function () { S.occupe = false; tout(); });
    }

    function suivre() {
      if (!S.cours.length) return;
      Promise.all(S.cours.map(function (c) {
        return jget("/api/jobs/" + encodeURIComponent(c.job_id)).then(function (j) {
          c.pct = j.progress || c.pct; c.etape = j.current_step || ""; c.fini = j.status === "done" || j.status === "failed";
          if (j.status === "failed") c.etape = T("creer3d.action.echec");
        }).catch(function () { c.fini = true; });
      })).then(function () {
        var fini = S.cours.some(function (c) { return c.fini; });
        S.cours = S.cours.filter(function (c) { return !c.fini; });
        if (fini) charger(); else peindreC();
        if (S.cours.length) setTimeout(suivre, 3000);
      });
    }

    function ouvrirDansStudio(job, ecran) {
      try { localStorage.setItem(RELAIS, CALC.relais(job, ecran)); } catch (e) { /* stockage fermé */ }
      window.dispatchEvent(new CustomEvent("deepotus:assets-subtab", { detail: { subtab: "studio3d" } }));
    }

    function charger() {
      return jget("/api/studio3d/modeles").then(function (j) { S.modeles = j.modeles || []; peindreC(); }).catch(function () {});
    }

    el.addEventListener("click", function (ev) {
      var t = ev.target.closest("button");
      if (!t) return;
      if (t.dataset.roue) { S.ouverts[t.dataset.roue] = !S.ouverts[t.dataset.roue]; return peindreG(); }
      if (t.dataset.pose != null) { S.pose = t.dataset.pose; peindreG(); return devis(); }
      if (t.dataset.mode) {
        S.mode = t.dataset.mode;
        if (S.mode === "image") S.images = S.images.slice(0, 1);
        S.moteurs = S.moteurs.filter(function (m) { return CALC.cochable(S.engines.filter(function (e) { return e.id === m; })[0] || {}, S.mode); });
        peindreG(); return devis();
      }
      if (t.dataset.img) {
        var f = t.dataset.img, i = S.images.indexOf(f);
        if (S.mode === "image") S.images = i >= 0 ? [] : [f];
        else if (i >= 0) S.images.splice(i, 1); else S.images.push(f);
        return devis();
      }
      if (t.dataset.q && t.dataset.q !== "s") { S.quantite = +t.dataset.q; return devis(); }
      if (t.dataset.go) return generer();
      if (t.dataset.filtre) { S.filtre = t.dataset.filtre; return peindreC(); }
      if (t.dataset.ouvrir) return ouvrirDansStudio(t.dataset.ouvrir, t.dataset.ecran);
    });
    el.addEventListener("change", function (ev) {
      var t = ev.target;
      if (t.dataset.moteur) {
        var m = t.dataset.moteur, i = S.moteurs.indexOf(m);
        if (t.checked && i < 0) S.moteurs.push(m); else if (!t.checked && i >= 0) S.moteurs.splice(i, 1);
        peindreG(); return devis();
      }
      if (t.dataset.reg) {
        var e = S.engines.filter(function (x) { return x.id === t.dataset.reg; })[0];
        var x = e && e.reglages.filter(function (r) { return r.cle === t.dataset.cle; })[0];
        if (!x) return;
        (S.reglages[e.id] = S.reglages[e.id] || {})[x.cle] = CALC.valeur(x, x.type === "bool" ? t.checked : t.value);
        return devis();
      }
    });
    el.addEventListener("input", function (ev) {
      var t = ev.target;
      if (t.dataset.prompt) { S.prompt = t.value; return devis(); }
      if (t.dataset.col) { S.col = +t.value; return peindreC(); }
      if (t.dataset.q === "s") { S.q = t.value; var p = t.selectionStart; peindreC(); var n = C.querySelector('[data-q="s"]'); if (n) { n.focus(); n.setSelectionRange(p, p); } return; }
      if (t.dataset.av) { t.parentNode.style.setProperty("--c3d-cut", t.value + "%"); }
    });

    tout();
    jget("/api/assets3d/engines").then(function (j) {
      S.engines = (j.engines || []).filter(function (e) { return e.id !== "meshy"; });
      peindreG();
    }).catch(function (e) { S.avis = e.message; peindreD(); });
    jget("/api/images").then(function (j) {
      S.biblio = (j.images || []).slice().sort(function (a, b) { return (b.mtime || 0) - (a.mtime || 0); }).map(function (i) { return i.filename; });
      peindreD();
    }).catch(function () {});
    charger();
  }

  window.__dzCreer3d = { monter: monter, calc: CALC };
})();
