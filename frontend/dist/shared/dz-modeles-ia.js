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
   gratuit, toutes les entrées disponibles OU NON.

   SOURCE UNIQUE de deux règles, recopiées À L'IDENTIQUE (banc test_encarts_ia) :
   - ORDRE des voies : dz-champ-ia.js (ORDRE_VOIES) et le maillon de queue
     encartsia du bundle (dzImgOpts) ;
   - le PRIX : `prixUsd` (même ligne de code dans dz-champ-ia.js et dans le
     maillon encartsia) — « $ » + la valeur arrondie au millième, zéros de fin
     retirés mais au moins deux décimales (0.145 → $0.145, 0.04 → $0.04,
     0.22 → $0.22), suffixe d'unité (/image, /s, /min, /1k ; t186 : /30 images,
     /16 images pour le détourage vidéo facturé par tranche d'images), indépendant de la
     langue ; un prix nul, absent ou illisible n'est JAMAIS « gratuit » : il
     rend "" et l'affichage dit « prix à mesurer ». */
(function (W) {
  /* les textes de repli quand le dictionnaire manque (page chargée sans
     /shared/dz-i18n-dico.js, clé pas encore assemblée) — comme VOIES_FR de dz-champ-ia */
  var FR = {
    "ia.prix.a_mesurer": "prix à mesurer", "ia.cle.a_ajouter": "clé {cle} à ajouter dans Réglages",
    "ia.voie.fal": "via la clé fal", "ia.voie.openai": "avec votre clé OpenAI", "ia.voie.gemini": "avec votre clé Gemini",
    "ia.voie.elevenlabs": "avec votre clé ElevenLabs", "ia.voie.meshy": "avec votre clé Meshy",
    "ia.voie.heygen": "avec votre clé HeyGen", "ia.voie.local": "local, gratuit"
  };
  function T(k, v) {
    var t = W.dzT ? W.dzT(k, v) : (typeof dzT === "function" ? dzT(k, v) : k);   // eslint-disable-line no-undef
    if (!t || t === k) {
      t = FR[k] || k;
      for (var x in (v || {})) t = t.split("{" + x + "}").join(v[x]);
    }
    return t;
  }
  var ORDRE = ["fal", "openai", "gemini", "elevenlabs", "meshy", "heygen", "local"];
  function prixUsd(usd, unite) { var v = Number(usd); if (!(v > 0) || !isFinite(v)) return ""; var s = (Math.round(v * 1000) / 1000).toFixed(3); while (/\.\d{3,}$/.test(s) && s.charAt(s.length - 1) === "0") s = s.slice(0, -1); return "$" + s + ({ image: "/image", s: "/s", min: "/min", "1k": "/1k", "30 images": "/30 images", "16 images": "/16 images" }[unite] || ""); }
  function prix(usd, unite) {
    return prixUsd(usd, unite) || T("ia.prix.a_mesurer");
  }
  /* t186 (G4) : une option de la voie LOCALE sans prix est gratuite pour de vrai (son <optgroup> le dit déjà) —
     ni « prix à mesurer », ni prix : le libellé seul. Les autres voies gardent la règle (jamais « gratuit »). */
  function texte(m) {
    var p = prixUsd(m.usd, m.unite);
    return (m.label || m.id) + (p ? " · " + p : m.voie === "local" ? "" : " · " + prix(m.usd, m.unite))
      + (m.dispo === false && m.cle ? " · " + T("ia.cle.a_ajouter", { cle: m.cle }) : "");
  }
  /* rang d'une voie : l'ordre ORDRE, une voie inconnue (ou absente) APRÈS toutes */
  function rang(v) { var k = ORDRE.indexOf(v); return k < 0 ? 99 : k; }
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
  /* remplit le <select> (un <optgroup> par voie) et rend la valeur RETENUE : l'appelant
     y recale son état (la valeur demandée peut ne plus être proposée) */
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
    el.__dzModeles = mods;                   // la liste COURANTE, que l'écouteur de change relit
    el.value = valeurInitiale(mods, opts.valeur);
    return el.value;
  }
  /* charge le catalogue puis remplit ; un échec de lecture REJETTE la promesse
     et laisse le <select> tel quel (l'appelant garde son repli) */
  function select(el, nature, opts) {
    opts = opts || {};
    return charger(nature).then(function (tous) {
      var mods = filtrer(tous, opts);
      remplir(el, mods, opts);
      if (opts.onChange && !el.__dzModelesIA) {
        el.__dzModelesIA = true;
        el.addEventListener("change", function () {
          var l = el.__dzModeles || [];
          opts.onChange(el.value, l.filter(function (m) { return m.id === el.value; })[0] || null);
        });
      }
      return mods;
    });
  }
  W.DzModelesIA = { grouper: grouper, prix: prix, prixUsd: prixUsd, texte: texte, filtrer: filtrer, charger: charger,
                    valeurInitiale: valeurInitiale, remplir: remplir, select: select, rang: rang, ORDRE: ORDRE };
})(typeof window !== "undefined" ? window : globalThis);
