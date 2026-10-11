/* DzModelesIA — sélecteur de modèle partagé des pages à part (t183, G1, plan
   « Génération IA enrichie », 11/10/2026).

   Un <optgroup> par VOIE (clé fal, votre clé OpenAI, Gemini…, local), le prix
   sur chaque option. Décision de l'utilisateur (11/10/2026) : une option dont
   la clé manque reste VISIBLE ET CHOISISSABLE — jamais `disabled` —, avec la
   mention dzT("ia.cle.a_ajouter", {cle}) (« clé X à ajouter dans Réglages ») ;
   le serveur refuse le tir en 503 (avant toute dépense) tant que la clé
   manque. Seule exception : un modèle vectoriel (sortie "svg") n'apparaît
   jamais dans un sélecteur raster (option `vectoriel: true` pour l'admettre).

   Source : GET /api/ia/catalogue?nature=… (backend/app/services/catalogue_ia.py),
   gratuit, toutes les entrées disponibles OU NON. */
(function (W) {
  function T(k, v) {
    if (W.dzT) return W.dzT(k, v);
    if (typeof dzT === "function") return dzT(k, v);   // eslint-disable-line no-undef
    return k;
  }
  var ORDRE = ["fal", "openai", "gemini", "elevenlabs", "meshy", "heygen", "local"];
  function enAnglais() {
    try { return !!(W.dzLang && W.dzLang() === "en"); } catch (e) { return false; }
  }
  /* « 0,145 $ » (fr) / « $0.145 » (en) ; unité "s" → « /s », "min" → « /min » ;
     un prix inconnu (0) n'est JAMAIS « gratuit » : « prix à mesurer » */
  function prix(usd, unite) {
    usd = Number(usd);
    if (!usd || !isFinite(usd)) return T("ia.prix.a_mesurer");
    var n = (Math.round(usd * 1000) / 1000).toString();
    var u = unite === "s" ? "/s" : unite === "min" ? "/min" : "";
    return enAnglais() ? "$" + n + u : n.replace(".", ",") + " $" + u;
  }
  function texte(m) {
    return (m.label || m.id) + " · " + prix(m.usd, m.unite)
      + (m.dispo === false && m.cle ? " · " + T("ia.cle.a_ajouter", { cle: m.cle }) : "");
  }
  function grouper(mods) {
    var par = {}, autres = [];
    (mods || []).forEach(function (m) {
      var v = m.voie || "";
      if (ORDRE.indexOf(v) < 0) { if (autres.indexOf(v) < 0) autres.push(v); }
      (par[v] = par[v] || []).push(m);
    });
    return ORDRE.concat(autres).filter(function (v) { return par[v]; }).map(function (v) {
      return {
        voie: v, titre: v ? T("ia.voie." + v) : "",
        options: par[v].map(function (m) {
          return { id: m.id, desactive: false,       // jamais désactivé : décision de l'utilisateur 11/10
                   texte: texte(m), sansCle: m.dispo === false };
        })
      };
    });
  }
  /* les entrées qu'un sélecteur RASTER propose : jamais un modèle vectoriel */
  function filtrer(mods, opts) {
    opts = opts || {};
    return (mods || []).filter(function (m) { return opts.vectoriel || m.sortie !== "svg"; });
  }
  function charger(nature) {
    return W.fetch("/api/ia/catalogue?nature=" + encodeURIComponent(nature), { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("catalogue " + nature + " : " + r.status);
        return r.json();
      }).then(function (d) { return (d && d.modeles) || []; });
  }
  /* la valeur retenue : celle demandée si le sélecteur la propose (même sans
     clé : elle reste choisissable), sinon la première DISPONIBLE, sinon la
     première tout court */
  function valeurInitiale(mods, voulu) {
    if (voulu && mods.some(function (m) { return m.id === voulu; })) return voulu;
    var d = mods.filter(function (m) { return m.dispo !== false; })[0] || mods[0];
    return d ? d.id : "";
  }
  function remplir(el, mods, opts) {
    opts = opts || {};
    var doc = el.ownerDocument || W.document;
    el.textContent = "";
    grouper(mods).forEach(function (g) {
      var og = doc.createElement("optgroup");
      og.label = g.titre;
      g.options.forEach(function (o) {
        var op = doc.createElement("option");
        op.value = o.id;
        op.textContent = o.texte;
        op.disabled = o.desactive;
        if (o.sansCle) op.setAttribute("data-sans-cle", "1");
        og.appendChild(op);
      });
      el.appendChild(og);
    });
    el.value = valeurInitiale(mods, opts.valeur);
    return el.value;
  }
  function select(el, nature, opts) {
    opts = opts || {};
    return charger(nature).then(function (tous) {
      var mods = filtrer(tous, opts);
      remplir(el, mods, opts);
      if (opts.onChange && !el.__dzModelesIA) {
        el.__dzModelesIA = true;
        el.addEventListener("change", function () {
          opts.onChange(el.value, mods.filter(function (m) { return m.id === el.value; })[0] || null);
        });
      }
      return mods;
    });
  }
  W.DzModelesIA = { grouper: grouper, prix: prix, texte: texte, filtrer: filtrer, charger: charger,
                    valeurInitiale: valeurInitiale, remplir: remplir, select: select, ORDRE: ORDRE };
})(typeof window !== "undefined" ? window : globalThis);
