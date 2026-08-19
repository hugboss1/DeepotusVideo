"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 09 · Forge 3D   [P9]
   Proprietaire exclusif de : doc.forge3d · AUCUN z (ce module ne peint pas) ·
   /api/cards/<did>/forge3d/* · prefixe DOM cf-forge3d-
   feuille : css/mod-forge3d.css (tout selecteur y contient .cf-forge3d)

   Export par couches (phase 1). Ce module n'a AUCUN painter : il lit le
   rendu, il n'y dessine jamais.
   ═══════════════════════════════════════════════════════════════════════════ */
(() => {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-forge3d: js/core.js doit etre charge avant ce fichier");

  /* ── LA TABLE DES COUCHES — BLOC MIROIR ─────────────────────────────────
     ═══ CF-FORGE3D-LAYERS-BEGIN ═══
     Le miroir Python est dans backend/app/services/cards/forge3d.py, entre
     les mêmes marqueurs ; test_cards_forge3d compare les deux champ à champ
     et dans l'ordre.
     Les z sont ceux de la Z_TABLE gelée du CORE (core.js:82). */
  const LAYER_ROLES = [
    { role: "fond-matiere", z: [10], module: "texture" },
    { role: "illustration", z: [20], module: "face" },
    { role: "voile-matiere", z: [30], module: "texture" },
    { role: "cadre", z: [40], module: "frame" },
    { role: "typographie", z: [60], module: "type" },
    { role: "ornements", z: [70], module: "frame" },
  ];
  /* ═══ CF-FORGE3D-LAYERS-END ═══ */

  const M = CF.register({
    id: "forge3d",
    title: "Forge 3D",
    icon: "⬢",
    order: 9,
    state: {
      last_export: null,        /* horodatage et compte de faces du dernier
                                    export ; le bordereau n'est pas persisté */
    },
    init(host) {
      host.innerHTML = shell();
      wire(host);
    },
  });

  const $ = (sel) => (M.slot() ? M.slot().querySelector(sel) : null);

  function shell() {
    return '<div class="cf-forge3d-wrap">'
      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Couches de la carte</b></header>'
      + '<p class="hint">Une PNG alpha par élément (fond, illustration, voile, cadre, '
      + 'typo, ornements), recto et verso, plus le composite. Chaque couche est '
      + 'PROUVÉE : l\'empilement doit reproduire la carte au pixel près.</p>'
      + '<button class="btn strong" id="cf-forge3d-export" type="button">'
      + 'Exporter les couches</button>'
      + '<p class="hint" id="cf-forge3d-status"></p>'
      + '<div id="cf-forge3d-slip"></div>'
      + '</section>'
      + '</div>';
  }

  function wire(host) {
    $("#cf-forge3d-export").addEventListener("click", () => exportLayers());
    const slip = $("#cf-forge3d-slip");
    if (slip) slip.addEventListener("click", onSlipClick);
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /* Le meme poids binaire (CEI 80000-13) que le reste du lab (mod-gltf.js,
     mod-print.js) : « Mo » decimal ne se retrouve jamais sur le disque. */
  function weight(n) {
    const v = Number(n) || 0;
    if (v < 1024) return v + " o";
    if (v < 1048576) return (v / 1024).toFixed(1) + " Kio";
    return (v / 1048576).toFixed(2) + " Mio";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     EXPORT — DEUX TEMPS, pour que « rien n'a été envoyé » soit vrai PAR
     CONSTRUCTION et non par discipline de lecture du code.
     Temps 1 (preuve) : les DEUX faces sont rendues et prouvées (CF.layers) ;
     la moindre erreur de painter ou le moindre echec d'empilement NOMME la
     face fautive et REND (aucun FormData, aucun fetch n'existe encore a cet
     instant du code — pas seulement « avant d'etre appele »). Temps 2
     (envoi) : uniquement atteint si les deux faces ont passe le temps 1 —
     chaque face part alors avec SA preuve mesuree.
     Note memoire : les toiles des deux faces (12 couches + 2 composites, au
     lieu de 6+1) restent retenues entre les deux temps — un geste ponctuel
     sur clic, pas une boucle : acceptable. */
  async function exportLayers() {
    const status = $("#cf-forge3d-status");
    const btn = $("#cf-forge3d-export");
    btn.disabled = true;
    try {
      const sides = ["front", "back"];

      /* ── TEMPS 1 : PREUVE DES DEUX FACES, AUCUN RESEAU ────────────────── */
      const preuves = [];
      for (let s = 0; s < sides.length; s++) {
        const face = sides[s];
        status.textContent = "rendu des couches ("
          + (face === "front" ? "recto" : "verso") + ")…";
        const L = await CF.layers(CF.current(), { face: face, groups: LAYER_ROLES });
        if (L.errors && L.errors.length) {
          /* une couche rendue avec une erreur de painter n'est pas une couche
             de confiance : on nomme (face + painters) et on n'envoie rien. */
          status.textContent = "erreur de painter pendant le rendu des couches ("
            + face + " : " + L.errors.map((e) => e.id + " z=" + e.z).join(", ")
            + ") — rien n'a été envoyé.";
          M.toast("rendu des couches en erreur : export refusé", true);
          return;
        }
        if (!L.stack_ok) {
          /* la preuve a echoue : on NOMME et on n'envoie RIEN — un ZIP faux
             est pire qu'un echec dit. */
          const fautive = L.layers.filter((l) => l.mode === "empreinte")
            .map((l) => l.role).join(", ") || "inconnue";
          status.textContent = "preuve d'empilement ÉCHOUÉE (" + face
            + ") — couches en cause : " + fautive + ". Rien n'a été envoyé.";
          M.toast("empilement non reproduit : export refusé", true);
          return;
        }
        preuves.push({ face: face, L: L });
      }

      /* ── TEMPS 2 : LES DEUX FACES SONT PROUVEES — ON ENVOIE ───────────── */
      const results = [];
      for (let p = 0; p < preuves.length; p++) {
        const face = preuves[p].face, L = preuves[p].L;
        const fd = new FormData();
        for (let k = 0; k < L.layers.length; k++) {
          const lay = L.layers[k];
          fd.append("layers", await CF.layerBlob(lay.canvas), lay.role + ".png");
        }
        fd.append("composite", await CF.layerBlob(L.composite), "composite.png");
        fd.append("side", face);
        fd.append("card", String(CF.current ? CF.current() : 0));
        fd.append("paper", L.paper || "#ffffff");
        const modes = {};
        L.layers.forEach((l) => { modes[l.role] = l.mode; });
        fd.append("modes", JSON.stringify(modes));
        fd.append("client_proof", JSON.stringify({ stack_ok: L.stack_ok, diff_px: 0 }));
        status.textContent = "téléversement (" + face + ")…";
        const rep = await M.api.post("layers", fd);
        results.push(rep.layers);
      }
      M.patch({ last_export: { at: new Date().toISOString(), sides: results.length } });
      paintSlip(results);
      status.textContent = "couches livrées, preuve tenue des deux côtés.";
    } catch (e) {
      status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
    } finally {
      btn.disabled = false;
    }
  }

  /* ── LE BORDEREAU — peint depuis la REPONSE mesuree, jamais depuis
     l'intention envoyee : role/mode/couverture/poids viennent des lignes du
     manifeste, l'ecart d'empilement vient de proof.backend.diff_px (second
     avis PIL, cote serveur). Les vignettes chargent le PNG livre par
     GET file/<nom> (patron mod-gltf.js:loadProof/mountViewer — un <img src>
     n'est pas un telechargement, juste une lecture d'apercu). */
  function paintSlip(results) {
    const slip = $("#cf-forge3d-slip");
    if (!slip) return;
    slip.innerHTML = results.map((man) => {
      const rows = man.layers.map((l) =>
        '<div class="cf-forge3d-lay"><img src="'
        + esc(M.api.url("file/" + encodeURIComponent(l.file)))
        + '" alt="" loading="lazy" decoding="async">'
        + '<span class="mono">' + esc(l.role) + " · " + esc(l.mode) + " · "
        + Number(l.coverage_pct) + " % · " + weight(l.bytes) + "</span></div>").join("");
      return '<h4>' + (man.side === "front" ? "Recto" : "Verso") + '</h4>' + rows
        + '<p class="mono">empilement : navigateur strict OK · second avis PIL '
        + Number(man.proof.backend.diff_px) + ' px d\'écart · '
        + '<button class="btn sm" type="button" data-act="grab-zip" data-name="'
        + esc(man.zip.name) + '">' + esc(man.zip.name) + " ("
        + weight(man.zip.bytes) + ')</button></p>';
    }).join("");
  }

  /* ── TELECHARGEMENT — meme provenance que le reste du lab : le ZIP n'est
     jamais un <a href> direct (patron mod-gltf.js:grab). Le blob vient de
     M.api.blob (mint), donc M.download (alias de CF.download) l'accepte —
     un lien nu servirait un blob de provenance inconnue. */
  async function grabZip(name) {
    if (!name) return;
    try {
      const b = await M.api.blob("GET", "file/" + encodeURIComponent(name));
      M.download(b, name);
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    }
  }

  function onSlipClick(e) {
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!b) return;
    if (b.getAttribute("data-act") === "grab-zip") {
      e.preventDefault();
      grabZip(b.getAttribute("data-name"));
    }
  }
})();
