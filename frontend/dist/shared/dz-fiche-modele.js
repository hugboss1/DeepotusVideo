/* dz-fiche-modele.js — la FICHE d'un modèle d'IA, ouverte par un « ? » (t476, lot F1 « Fiches modèle », 09/11/2026).
   SOURCE : frontend/shared/dz-fiche-modele.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-fiche-modele.js.

   Aucune page ne charge ce script par une balise : DzModelesIA (sélecteurs des pages à part) et dz-champ-ia (pastille
   de modèle, SPA comprise) le chargent AU PREMIER BESOIN par `DzFicheModeleCharger()` (voir plus bas, recopiée dans
   ces deux scripts). Sources : GET /api/modeles/index (quels ids ont une fiche) et GET /api/modeles/fiche?cle=&langue=
   (service backend/app/services/modeles_fiches.py), gratuits.

   Le « ? » n'apparaît QUE pour un modèle dont la famille a une fiche : pas de bouton vide. La fiche est du markdown
   réduit (titres ##, puces, tableaux, `code`, **gras**), rendu ici SANS innerHTML de texte brut : tout est échappé
   avant la mise en forme. Le panneau suit la charte (jetons --bg-panel, --stroke, --fg-*, --r ; aucun rayon écrit). */
(function (W) {
  if (W.DzFicheModele) return;
  var D = W.document;
  var FR = { "modeles.fiche.ouvrir": "Fiche du modèle", "modeles.fiche.fermer": "Fermer la fiche",
             "modeles.fiche.titre": "Fiche : {famille}", "modeles.fiche.erreur": "Fiche indisponible",
             "modeles.fiche.commun": "Règles communes", "modeles.fiche.releve": "Relevé du {date}" };
  function T(k, v) {
    var t = W.dzT ? W.dzT(k, v) : k;
    if (!t || t === k) {
      t = FR[k] || k;
      for (var x in (v || {})) t = t.split("{" + x + "}").join(v[x]);
    }
    return t;
  }
  function langue() { var l = W.dzLang ? W.dzLang() : "fr"; return l === "en" ? "en" : "fr"; }

  var indexP = null;                       // promesse unique de l'index, par langue de chargement
  function index() {
    if (!indexP) {
      indexP = W.fetch("/api/modeles/index?langue=" + langue(), { cache: "no-store" })
        .then(function (r) { if (!r.ok) throw new Error("index " + r.status); return r.json(); })
        .then(function (d) { return (d && d.ids) || {}; })
        .catch(function () { indexP = null; return {}; });
    }
    return indexP;
  }
  function familleDe(id) { return index().then(function (ids) { return ids[id] || null; }); }

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  /* la mise en forme EN LIGNE, sur un texte déjà échappé */
  function enLigne(s) {
    return esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }
  function cellules(l) { return l.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map(function (c) { return c.trim(); }); }
  /* markdown réduit -> HTML (chaîne), chaque texte échappé */
  function rendre(md) {
    var out = [], liste = false, table = null, para = [];
    function finPara() { if (para.length) { out.push("<p>" + enLigne(para.join(" ")) + "</p>"); para = []; } }
    function finListe() { if (liste) { out.push("</ul>"); liste = false; } }
    function finTable() {
      if (!table) return;
      var h = "<table><thead><tr>" + table[0].map(function (c) { return "<th>" + enLigne(c) + "</th>"; }).join("") +
        "</tr></thead><tbody>" + table.slice(1).map(function (r) {
          return "<tr>" + r.map(function (c) { return "<td>" + enLigne(c) + "</td>"; }).join("") + "</tr>";
        }).join("") + "</tbody></table>";
      out.push(h); table = null;
    }
    String(md || "").replace(/\r\n/g, "\n").split("\n").forEach(function (l) {
      if (/^\s*\|/.test(l)) {
        finPara(); finListe();
        if (/^\s*\|[\s:|-]+\|\s*$/.test(l)) return;                 // ligne de séparation
        (table = table || []).push(cellules(l));
        return;
      }
      finTable();
      var m;
      if ((m = /^#{1,6}\s+(.*)$/.exec(l))) { finPara(); finListe(); out.push("<h3>" + enLigne(m[1]) + "</h3>"); return; }
      if ((m = /^\s*[-*]\s+(.*)$/.exec(l))) {
        finPara();
        if (!liste) { out.push("<ul>"); liste = true; }
        out.push("<li>" + enLigne(m[1]) + "</li>");
        return;
      }
      if (!l.trim()) { finPara(); finListe(); return; }
      if (liste && /^\s+\S/.test(l)) {                               // suite d'une puce
        out[out.length - 1] = out[out.length - 1].replace(/<\/li>$/, " " + enLigne(l.trim()) + "</li>");
        return;
      }
      para.push(l.trim());
    });
    finPara(); finListe(); finTable();
    return out.join("");
  }

  var CSS = ".dz-fiche-modele-b{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;" +
    "margin:0 0 0 4px;padding:0;vertical-align:middle;border:1px solid var(--stroke,#2a2930);border-radius:var(--r);" +
    "background:var(--bg-panel-2,#1c1c21);color:var(--fg-2,#c4bfb6);font:var(--fw-3,600) var(--fs-3,12px) var(--font-ui,sans-serif);cursor:pointer}" +
    ".dz-fiche-modele-b:hover,.dz-fiche-modele-b:focus-visible{color:var(--fg-accent,#f0b429);border-color:var(--fg-accent,#f0b429);outline:none}" +
    ".dz-fiche-modele-b[hidden]{display:none}" +
    ".dz-fiche-modele-b.dz-fiche-modele-coin{position:absolute;top:0;right:0;margin:0;width:16px;height:16px;font-size:var(--fs-2,11px)}" +
    ".dz-fiche-modele{position:fixed;z-index:2147483001;right:16px;top:64px;width:min(560px,calc(100vw - 32px));" +
    "max-height:calc(100vh - 96px);display:flex;flex-direction:column;border:1px solid var(--stroke,#2a2930);border-radius:var(--r);" +
    "background:var(--bg-panel,#151519);color:var(--fg-2,#c4bfb6);font:var(--fw-1,400) var(--fs-4,13.5px)/1.5 var(--font-ui,sans-serif);" +
    "box-shadow:0 12px 40px rgba(0,0,0,.45)}" +
    ".dz-fiche-modele header{display:flex;align-items:center;gap:8px;padding:var(--pad-3,12px) var(--pad-4,16px);border-bottom:1px solid var(--stroke,#2a2930)}" +
    ".dz-fiche-modele header strong{flex:1;color:var(--fg-1,#f2efe9);font:var(--fw-3,600) var(--fs-5,16px) var(--font-display,sans-serif)}" +
    ".dz-fiche-modele header small{color:var(--fg-3,#8a857d);font:var(--fs-2,11px) var(--font-mono,monospace)}" +
    ".dz-fiche-modele header button{border:0;background:none;color:var(--fg-3,#8a857d);font-size:18px;cursor:pointer;padding:0 4px}" +
    ".dz-fiche-modele header button:hover,.dz-fiche-modele header button:focus-visible{color:var(--fg-accent,#f0b429);outline:none}" +
    ".dz-fiche-modele .dz-fm-corps{overflow:auto;padding:var(--pad-2,8px) var(--pad-4,16px) var(--pad-4,16px)}" +
    ".dz-fiche-modele h3{margin:14px 0 6px;color:var(--fg-1,#f2efe9);font:var(--fw-3,600) var(--fs-3,12px) var(--font-mono,monospace);text-transform:uppercase;letter-spacing:var(--ls-caps,.12em)}" +
    ".dz-fiche-modele ul{margin:0;padding-left:18px;list-style:disc outside}.dz-fiche-modele li{margin:3px 0}.dz-fiche-modele p{margin:6px 0}" +
    ".dz-fiche-modele code{font:var(--fs-3,12px) var(--font-mono,monospace);color:var(--fg-1,#f2efe9)}" +
    ".dz-fiche-modele table{border-collapse:collapse;width:100%;margin:6px 0;font:var(--fs-2,11px) var(--font-mono,monospace)}" +
    ".dz-fiche-modele th,.dz-fiche-modele td{border:1px solid var(--stroke,#2a2930);padding:3px 6px;text-align:left}" +
    ".dz-fiche-modele th{color:var(--fg-1,#f2efe9)}" +
    ".dz-fiche-modele details{margin-top:14px;border-top:1px solid var(--stroke,#2a2930);padding-top:8px}" +
    ".dz-fiche-modele summary{cursor:pointer;color:var(--fg-3,#8a857d)}";
  function style() {
    if (!D.head || D.getElementById("dz-fiche-modele-css")) return;
    var s = D.createElement("style");
    s.id = "dz-fiche-modele-css";
    s.textContent = CSS;
    D.head.appendChild(s);
  }

  var ouvert = null;
  function fermer() {
    if (!ouvert) return;
    if (ouvert.node.parentNode) ouvert.node.parentNode.removeChild(ouvert.node);
    D.removeEventListener("keydown", ouvert.touche, true);
    var retour = ouvert.retour;
    ouvert = null;
    if (retour && retour.focus) try { retour.focus(); } catch (e) { /* nœud retiré */ }
  }
  /* ouvre la fiche d'un id ou d'une famille ; rend la promesse de la réponse (null si indisponible) */
  function ouvrir(cle, retour) {
    fermer();
    style();
    var p = D.createElement("section");
    p.className = "dz-fiche-modele";
    p.setAttribute("role", "dialog");
    p.setAttribute("aria-label", T("modeles.fiche.ouvrir"));
    p.setAttribute("data-dz-fiche-modele", String(cle || ""));
    var h = D.createElement("header");
    var t = D.createElement("strong");
    t.textContent = T("modeles.fiche.ouvrir");
    var meta = D.createElement("small");
    var x = D.createElement("button");
    x.type = "button";
    x.textContent = "×";
    x.setAttribute("aria-label", T("modeles.fiche.fermer"));
    x.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); fermer(); });
    h.appendChild(t); h.appendChild(meta); h.appendChild(x);
    var c = D.createElement("div");
    c.className = "dz-fm-corps";
    c.textContent = "…";
    p.appendChild(h); p.appendChild(c);
    p.addEventListener("pointerdown", function (ev) { ev.stopPropagation(); });
    (D.body || D.documentElement).appendChild(p);
    var touche = function (ev) { if (ev.key === "Escape") { ev.stopPropagation(); fermer(); } };
    D.addEventListener("keydown", touche, true);
    ouvert = { node: p, touche: touche, retour: retour || null };
    x.focus();
    return W.fetch("/api/modeles/fiche?cle=" + encodeURIComponent(cle) + "&langue=" + langue(), { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then(function (f) {
        if (!ouvert || ouvert.node !== p) return f;
        t.textContent = T("modeles.fiche.titre", { famille: f.famille });
        meta.textContent = f.releve ? T("modeles.fiche.releve", { date: f.releve }) : "";
        c.innerHTML = rendre(f.texte) + (f.commun ? "<details><summary>" + esc(T("modeles.fiche.commun")) +
          "</summary>" + rendre(f.commun) + "</details>" : "");
        return f;
      })
      .catch(function () {
        if (ouvert && ouvert.node === p) c.textContent = T("modeles.fiche.erreur");
        return null;
      });
  }
  /* pose (une fois) le « ? » juste après un <select> de modèles ; il se montre seulement quand la valeur courante a
     une fiche, et suit les changements de valeur */
  function bouton(sel) {
    if (!sel || !sel.parentNode) return null;
    var b = sel.__dzFicheB;
    if (!b) {
      style();
      b = D.createElement("button");
      b.type = "button";
      b.className = "dz-fiche-modele-b";
      b.textContent = "?";
      b.hidden = true;
      b.setAttribute("data-dz-fiche-b", "1");
      b.setAttribute("aria-label", T("modeles.fiche.ouvrir"));
      b.setAttribute("title", T("modeles.fiche.ouvrir"));
      b.addEventListener("click", function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        if (sel.value) ouvrir(sel.value, b);
      });
      sel.parentNode.insertBefore(b, sel.nextSibling);
      placer(sel, b);
      sel.__dzFicheB = b;
      sel.addEventListener("change", function () { maj(sel); });
    }
    maj(sel);
    return b;
  }
  /* la place du « ? » sans casser la mise en page de l'hôte : dans un parent en COLONNE (libellé au-dessus du
     <select>, ex. label.fld du Spritelab), il se met au coin haut droit, sur la ligne du libellé ; un <select> en
     bloc pleine largeur se rétrécit de la largeur du bouton pour le garder sur sa ligne ; sinon, il suit en ligne. */
  function placer(sel, b) {
    if (!W.getComputedStyle) return "ligne";
    var p = sel.parentNode, pcs = W.getComputedStyle(p), scs = W.getComputedStyle(sel);
    if (/flex/.test(pcs.display) && /column/.test(pcs.flexDirection)) {
      if (pcs.position === "static") p.style.position = "relative";
      b.classList.add("dz-fiche-modele-coin");
      return "coin";
    }
    if (scs.display === "block" && sel.offsetWidth >= p.clientWidth - 2) {
      sel.style.display = "inline-block";
      sel.style.width = "calc(100% - 26px)";
      return "retreci";
    }
    return "ligne";
  }
  function maj(sel) {
    var b = sel.__dzFicheB;
    if (!b) return Promise.resolve(false);
    var v = sel.value;
    return familleDe(v).then(function (f) { if (sel.value === v) b.hidden = !f; return !!f; });
  }
  W.DzFicheModele = { index: index, familleDe: familleDe, rendre: rendre, ouvrir: ouvrir, fermer: fermer,
                      bouton: bouton, maj: maj, placer: placer };
})(typeof window !== "undefined" ? window : globalThis);
