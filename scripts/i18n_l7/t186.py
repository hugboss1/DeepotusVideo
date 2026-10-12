"""t186 (G4, génération IA enrichie, 12/10/2026) — changement FONCTIONNEL du Card Forge posé APRÈS L7.

La capture (pièce mod-capture) choisit le modèle du détourage du recto dans le registre unique du détourage
(GET /api/ia/catalogue?nature=detourage_image, rempli par DzModelesIA — index.html charge /shared/dz-modeles-ia.js) :
un <optgroup> par voie, le prix sur chaque option, un modèle sans clé VISIBLE ET CHOISISSABLE (décision de
l'utilisateur du 11/10/2026 ; POST /api/cards/{did}/capture/rembg refuse en 503 au lancement), « Sujet à garder »
pour SAM 3 / Bria objet, choix mémorisé (dz_detour_cartes). Garder le défaut (la voie d'avant) envoie la requête
d'avant, sans corps. La table réversible L7 exige : source du poste == base f788790b + éditions ; d'où cette saisie.
"""
from outils import S

ENTREES = [
    S("js/mod-capture.js", 663, "+ '<p class=\"hint\" id=\"cf-capture-ia-note\"></p>'",
      "+ '<label class=\"cf-capture-modele\" style=\"display:flex;flex-direction:column;gap:4px;font-size:12px;margin-bottom:8px\">' + dzT(\"cartes.t186.modele\")\r\n        + '<select id=\"cf-capture-modele\"></select></label>'\r\n      + '<label class=\"cf-capture-modele hidden\" id=\"cf-capture-sujet-champ\" style=\"display:flex;flex-direction:column;gap:4px;font-size:12px;margin-bottom:8px\">'\r\n        + dzT(\"cartes.t186.sujet\") + '<input type=\"text\" id=\"cf-capture-sujet-txt\" maxlength=\"200\"></label>'\r\n      + '<p class=\"hint\" id=\"cf-capture-ia-note\"></p>'",
      {"cartes.t186.modele": ["Modèle de détourage", "Cutout model"], "cartes.t186.sujet": ["Sujet à garder", "Subject to keep"]}),
    S("js/mod-capture.js", 1387, "  async function chargeOptions() {",
      "  /* t186 (G4) : le modèle du détourage du recto — registre unique (DzModelesIA, nature detourage_image : un\r\n     <optgroup> par voie, le prix sur chaque option, un modèle sans clé reste CHOISISSABLE : la route refuse en 503\r\n     au lancement, avant toute dépense). Le défaut est la voie d'avant (local = local-rembg, fal = rembg-fal) : la\r\n     garder envoie la requête d'avant, SANS corps (basculement et tarif d'avant). `sujet` pour SAM 3 / Bria objet.\r\n     Choix mémorisé (localStorage dz_detour_cartes). */\r\n  const DETOUR_LS = \"dz_detour_cartes\";\r\n  function detourDefaut(voie) {\r\n    return voie === \"local\" ? \"local-rembg\" : \"rembg-fal\";\r\n  }\r\n  /* l'offre du bouton quand un AUTRE modèle que la voie d'avant est choisi : libellé, gratuité et prix pris dans\r\n     le catalogue (même chiffre que le toast d'après, qui lit prix_usd de la route) ; fal à 0 $ : « prix à mesurer ».\r\n     Appelée en fin d'offreIA : le bouton, le message d'attente et le contrôle « tarif changé » la voient. */\r\n  function detourAjuste(off) {\r\n    const sel = $(\"#cf-capture-modele\"), m = detourModele();\r\n    if (!off.on || !sel || !m || sel.value === detourDefaut(off.voie)) return off;\r\n    off.gratuit = m.voie === \"local\";\r\n    off.libelle = m.voie === \"local\" ? dzT(\"cartes.capture.detourer_local\")\r\n      : (Number(m.usd) > 0 ? dzT(\"cartes.capture.detourer_fal\", { prix: num(m.usd, 3) }) : dzT(\"cartes.t186.detourer_a_mesurer\"));\r\n    return off;\r\n  }\r\n  function detourModele() {\r\n    const sel = $(\"#cf-capture-modele\");\r\n    return sel ? (sel.__dzModeles || []).find((m) => m.id === sel.value) || null : null;\r\n  }\r\n  function detourMaj() {\r\n    const m = detourModele(), ch = $(\"#cf-capture-sujet-champ\");\r\n    if (ch) ch.classList.toggle(\"hidden\", !(m && m.prompt));\r\n  }\r\n  async function detourInit() {\r\n    const sel = $(\"#cf-capture-modele\");\r\n    if (!sel || sel.__dzDetourPret || !window.DzModelesIA) return;\r\n    sel.__dzDetourPret = true;\r\n    let voulu = \"\";\r\n    try { voulu = localStorage.getItem(DETOUR_LS) || \"\"; } catch (e) { /* stockage indisponible */ }\r\n    try {\r\n      await window.DzModelesIA.select(sel, \"detourage_image\", { valeur: voulu || detourDefaut(offreIA(IA, !!info(\"recto\")).voie), onChange: (v) => {\r\n        try { localStorage.setItem(DETOUR_LS, v); } catch (e) { /* stockage indisponible */ }\r\n        detourMaj(); paint();\r\n      } });\r\n    } catch (e) { sel.__dzDetourPret = false; return; }   // catalogue injoignable : la voie d'avant, sans choix\r\n    detourMaj();\r\n  }\r\n  /* le corps de POST rembg : undefined (requête d'avant) tant que le défaut est gardé */\r\n  function detourCorps() {\r\n    const sel = $(\"#cf-capture-modele\"), v = sel && sel.value;\r\n    if (!v || v === detourDefaut(offreIA(IA, !!info(\"recto\")).voie)) return undefined;\r\n    const c = { modele: v }, m = detourModele();\r\n    if (m && m.prompt) {\r\n      const sj = (($(\"#cf-capture-sujet-txt\") || {}).value || \"\").trim();\r\n      if (!sj) throw new Error(dzT(\"cartes.t186.sujet_requis\"));\r\n      c.sujet = sj;\r\n    }\r\n    return c;\r\n  }\r\n  async function chargeOptions() {",
      {"cartes.t186.sujet_requis": ["Dites quel sujet garder.", "Say which subject to keep."]}),
    S("js/mod-capture.js", 1389, "IA = await lireJson(await M.api.raw(\"GET\", \"ai-options\"));",
      "IA = await lireJson(await M.api.raw(\"GET\", \"ai-options\"));\r\n      detourInit();                // t186 : le catalogue du détourage, une fois la voie d'avant connue",
      {}),
    S("js/mod-capture.js", 346, "    return off;",
      "    return detourAjuste(off);         // t186 : un autre modèle choisi dit SON prix",
      {"cartes.t186.detourer_a_mesurer": ["Détourer le sujet (fal, prix à mesurer)", "Cut out subject (fal, price to be measured)"]}),
    S("js/mod-capture.js", 1450, "         d'argent du tout. */",
      "         d'argent du tout. */\r\n      if (d.voie !== \"local\" && !(estNombre(d.prix_usd) && d.prix_usd > 0)) {   // t186 : fal à 0 $ = « prix à mesurer »\r\n        M.toast(dzT(\"cartes.capture.sujet_ok\", { w: d.w, h: d.h, poids: weight(d.bytes) }) + dzT(\"cartes.t186.fal_a_mesurer\"));\r\n        return;\r\n      }",
      {"cartes.t186.fal_a_mesurer": [" (fal, prix à mesurer)", " (fal, price to be measured)"]}),
    S("js/mod-capture.js", 1428, "    BUSY = true;",
      "    let corpsDetour;\r\n    try { corpsDetour = detourCorps(); } catch (e) { M.toast(e.message, true); return; }\r\n    BUSY = true;",
      {}),
    S("js/mod-capture.js", 1431, "const d = await lireJson(await M.api.raw(\"POST\", \"rembg\"));",
      "const d = await lireJson(await M.api.raw(\"POST\", \"rembg\", corpsDetour));",
      {}),
]
