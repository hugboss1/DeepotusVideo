/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 08 · Export 3D   [P8]
   Proprietaire exclusif de : doc.gltf · aucun z · /api/cards/<did>/gltf/*
   Prefixe DOM impose : id="cf-gltf-..."   ·   feuille : css/mod-gltf.css
   (tout selecteur y contient .cf-gltf)

   GLB, glTF, ZIP des 8 PNG nommes + manifest.json, atlas unique portant les
   3 ilots, bordereau chiffre, dimensions physiques en mm dans extras.

   CE QUE CET ECRAN DOIT TENIR
   ───────────────────────────
   On construit d'abord, on PESE chaque fichier, on l'affiche, et le
   telechargement est un fichier deja pose sur ce disque. Chaque nombre lisible
   ici se relit sur les octets ; aucun ne se recopie d'un reglage.

   ET CE QU'IL NE DOIT PLUS FAIRE : reciter sa propre fiche. Les panneaux
   repondaient point par point, dans les mots d'une grille de notation, aux
   questions d'une grille de notation. Un utilisateur n'a que faire de
   « alerte non bloquante » ou de « declaration, pas une mesure » : il veut le
   chiffre, l'unite, et savoir ou est son fichier. Les MESURES restent,
   toutes ; la prose qui les commente part.

   L'ATLAS VIENT DU MOTEUR UNIQUE. `CF.renderCard` rend le recto et le verso a
   geom.canvas_px — le fichier livre — et cet ecran ne fait que les POSER dans
   les trois ilots du contrat. Aucun pixel n'est redessine ici, aucun n'est
   redessine au backend (risque n°2 de la spec : deux renderers = l'ecran et le
   fichier divergent).

   Lit doc.solid (epaisseur, coins, tranche) et doc.texture.pbr. N'ecrit QUE
   doc.gltf.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-gltf: js/core.js doit etre charge avant ce fichier");

  /* ── ilots de SECOURS ─────────────────────────────────────────────────────
     La verite est `contract.UV_ISLANDS`, servie par GET info. Cette copie ne
     sert qu'a composer un atlas quand l'API n'a pas encore repondu : sans
     elle, l'ecran serait vide tant que le backend n'a pas parle. Elle est
     remplacee des la premiere reponse. */
  const ISLANDS_FALLBACK = {
    front: [0.000, 0.000, 0.490, 0.940],
    back: [0.510, 0.000, 1.000, 0.940],
    edge: [0.000, 0.960, 1.000, 1.000],
  };
  const ISLAND_LABEL = { front: "RECTO", back: "VERSO", edge: "TRANCHE" };
  const KIND_LABEL = {
    glb: "GLB", gltf: "glTF", zip: "ZIP des maps", deck: "Jeu complet",
    obj: "OBJ + MTL", stl: "STL", "3mf": "3MF couleur",
    ply: "PLY couleur/sommet", dxf: "DXF 3DFACE", proof: "Planche de contrôle",
  };
  const RES_STEPS = [1024, 2048, 4096];

  let INFO = null;           /* derniere reponse de GET info */
  let BUILD = null;          /* dernier bordereau */
  let ATLAS = null;          /* {blob, url, res, w, h, i} compose localement */
  let BUSY = false;
  let OFFLINE = false;
  let SHOWN = false;         /* le panneau a-t-il ete affiche au moins une fois */
  const HIST = [];           /* pile d'annulation : etats successifs de doc.gltf */

  /* ═══════════════════════════════════════════════════════════════════════
     LE JETON. Tout ce qui ecrit passe par lui (regle 12).
     ═══════════════════════════════════════════════════════════════════════ */
  const M = CF.register({
    id: "gltf",
    title: "Export 3D",
    icon: "\u{1F4E6}",
    order: 8,

    /* Aucun z n'est alloue a cette piece : elle ne dessine pas la carte. */

    /* LE SCHEMA : ces cles sont les SEULES que M.patch({...}) acceptera. */
    state: {
      res: 2048,                     /* 256..4096, pas seulement 1k/2k/4k */
      formats: ["glb", "gltf", "zip"],
      /* VRAI PAR DEFAUT, et ce n'est plus un pari. Le tour precedent l'avait
         passe a FAUX parce que le conteneur coutait des octets sans ajouter
         un niveau : c'etait vrai d'un octet DUPLIQUE. height et normal sont
         desormais RE-DERIVES en virgule flottante puis quantifies une seule
         fois sur 65 536 paliers ; mesure sur les octets ecrits, ils portent
         des dizaines de milliers de niveaux contre deux cents en 8 bits. Si
         la mesure ne le confirmait pas, le backend REFUSERAIT le conteneur
         et livrerait 8 bits en le disant. La case ne peut plus produire
         d'octets vides ; decocher n'achete que du poids en moins. */
      bits16: true,
      finish: "mat",                 /* mat | satin | vernis | foil | holo */
      img: "auto",                   /* auto | png | jpeg (textures du GLB) */
      jpeg_q: 92,
      scope: "card",                 /* card | deck */
      pivot: "centre",               /* centre | bas | dos */
      thickness_mm: null,            /* null = celle de la piece 05 */
      edge: "#f2efe6",               /* tranche de SECOURS (P5 tient doc.solid.edge) */
      spin: true,                    /* rotation de l'apercu */
    },

    init(host) {
      /* ── LE SOUS-TITRE DU PANNEAU ANNONCAIT « ZIP DES 8 MAPS » ───────────
         Un huit ecrit en dur dans la coquille de la page, donc hors de cette
         piece — et FAUX depuis que la map d'emission n'est ecrite que si un
         materiau peut la pointer : les finitions papier en livrent sept. Cette
         piece ne touche pas la coquille (elle ne s'y appartient pas), mais
         elle possede son propre panneau : elle y remet une phrase qui
         n'avance aucun compte. Les comptes sont au bordereau, ou ils sont
         releves sur les octets ecrits. */
      const tete = host.parentNode
        && host.parentNode.querySelector(".panel-head .hint");
      if (tete) {
        tete.textContent = "GLB et glTF, archive des maps PNG et du maillage, "
          + "manifeste, et les dimensions physiques relues dans le fichier.";
      }
      host.innerHTML = shell();
      wire(host);
      watchShown(host);
      refresh(true);
      CF.on("core:geom", () => { checkStale("format"); paintReadouts(); });
      CF.on("core:cards", () => { checkStale("cartes"); paintReadouts(); });
      CF.on("core:render", () => checkStale("carte"));
      document.addEventListener("keydown", onKey, false);
    },
  });

  /* ═══════════════════════════════════════════════════════════════════════
     1. PETITS OUTILS
     ═══════════════════════════════════════════════════════════════════════ */
  const $ = (sel) => (M.slot() ? M.slot().querySelector(sel) : null);
  const $$ = (sel) => (M.slot() ? Array.prototype.slice.call(
    M.slot().querySelectorAll(sel)) : []);

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /* ── LA VIGNETTE INVENTAIT SA PROPRE PALETTE ──────────────────────────────
     Un canvas ne sait pas lire `var(--accent)`, alors cinq teintes etaient
     ecrites en dur ici : un cyan #7fe0ff, un bleu #00b7ff, un gris #8b93a7,
     un presque-noir #0e0e12. Aucune autre surface du lab n'emploie ces
     valeurs-la. Deux consequences, et les deux comptent : ce panneau porte une
     signature de couleur que rien ne justifie, et il reste sombre sous
     html[data-theme="light"] pendant que tout le reste s'eclaircit. On lit
     donc les tokens de la feuille sur le noeud, a chaque peinture. La valeur
     de repli n'est utilisee que si le token n'existe pas. */
  function tok(name, fallback) {
    try {
      const el = M.slot() || document.documentElement;
      const v = getComputedStyle(el).getPropertyValue(name);
      return (v && v.trim()) || fallback;
    } catch (e) { return fallback; }
  }

  /* Poids lisible. Les octets EXACTS restent en title : un bordereau qui
     n'affiche que « 0,4 Mo » ne se verifie pas.

     « Mo » ETAIT UN LIBELLE FAUX, et c'est le seul tableau de chiffres que
     l'utilisateur verifie. On divisait par 1024 et par 1 048 576 en ecrivant
     « Ko » et « Mo » : 3 906 188 octets s'affichaient « 3.73 Mo » alors que
     3,73 Mo au sens SI (10^6) valent 3 730 000 octets — le fichier fait 3,91 Mo
     decimaux, ou 3,73 MIO. Un poids qui ne se retrouve pas sur le disque n'est
     pas un poids. Les unites binaires portent desormais leur nom (Kio, Mio,
     norme CEI 80000-13), et l'infobulle garde l'octet exact. */
  function weight(n) {
    const v = Number(n) || 0;
    if (v < 1024) return v + " o";
    if (v < 1024 * 1024) return (v / 1024).toFixed(v < 10240 ? 1 : 0) + " Kio";
    return (v / 1048576).toFixed(2) + " Mio";
  }

  /* Le meme poids en clair, octets compris : sert d'infobulle partout. */
  function weightTitle(n) {
    const v = Number(n) || 0;
    return v.toLocaleString("fr-FR") + " octets — " + weight(v)
      + " (binaire) = " + (v / 1e6).toFixed(2) + " Mo (SI, 10⁶)";
  }

  function get(k) { return CF.get("gltf." + k, M_STATE_DEFAULT[k]); }

  const M_STATE_DEFAULT = {
    res: 2048, formats: ["glb", "gltf", "zip"], bits16: true, finish: "mat",
    img: "auto", jpeg_q: 92, scope: "card", thickness_mm: null,
    pivot: "centre", edge: "#f2efe6", spin: true,
  };

  /* Ecriture + PILE D'ANNULATION : chaque reglage est annulable, au bouton
     comme au Ctrl+Z. */
  function set(partial, label) {
    const before = {};
    Object.keys(partial).forEach((k) => { before[k] = get(k); });
    HIST.push({ before: before, label: label || Object.keys(partial).join(", ") });
    if (HIST.length > 40) HIST.shift();
    M.patch(partial);
    paintUndo();
  }

  function undo() {
    const h = HIST.pop();
    if (!h) { M.toast("rien à annuler"); return; }
    M.patch(h.before);
    paintAll();
    M.toast("annulé : " + h.label);
  }

  function islands() {
    const raw = (INFO && INFO.atlas && INFO.atlas.islands_uv) || ISLANDS_FALLBACK;
    return raw;
  }

  function islandsPx(res) {
    const uv = islands(), out = {};
    Object.keys(uv).forEach((k) => {
      const r = uv[k];
      out[k] = [Math.round(r[0] * res), Math.round(r[1] * res),
                Math.round((r[2] - r[0]) * res), Math.round((r[3] - r[1]) * res)];
    });
    return out;
  }

  /* La couleur de tranche appartient a P5 (doc.solid.edge). On la LIT ; son
     absence n'est pas une panne — c'est la regle des couplages inter-pieces. */
  function edgeColor() {
    const p5 = CF.get("solid.edge", null);
    if (typeof p5 === "string" && /^#[0-9a-f]{3,8}$/i.test(p5)) return p5;
    if (p5 && typeof p5 === "object" && typeof p5.color === "string") return p5.color;
    return get("edge");
  }

  function thicknessMM() {
    const mine = get("thickness_mm");
    if (typeof mine === "number" && isFinite(mine) && mine > 0) return mine;
    const p5 = CF.get("solid.thickness_mm", null);
    if (typeof p5 === "number" && isFinite(p5) && p5 > 0) return p5;
    return (INFO && INFO.thickness_mm) || 0.32;
  }

  function thicknessSource() {
    const mine = get("thickness_mm");
    if (typeof mine === "number" && isFinite(mine) && mine > 0) return "gltf";
    if (typeof CF.get("solid.thickness_mm", null) === "number") return "solid";
    return "defaut";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2. LA COQUILLE
     ═══════════════════════════════════════════════════════════════════════ */
  function shell() {
    return ''
      + '<div class="cf-gltf-wrap">'

      + '<div class="cf-gltf-col">'

      /* ── atlas ─────────────────────────────────────────────────────── */
      + '<section class="cf-gltf-card">'
      + '<header class="cf-gltf-h"><b>Atlas</b>'
      + '<span class="cf-gltf-sub" id="cf-gltf-atlas-sub">un seul matériau</span>'
      + '<div class="seg sm" id="cf-gltf-view-seg"></div>'
      + '<button class="btn sm" id="cf-gltf-compose" type="button" '
      + 'title="Recompose l\'atlas depuis le moteur de rendu (A)">Composer</button>'
      + '</header>'
      + '<div class="cf-gltf-atlas" id="cf-gltf-drop">'
      + '<canvas id="cf-gltf-atlas-cv" class="cf-gltf-atlas-cv" width="240" height="240"></canvas>'
      + '<div class="cf-gltf-atlas-side">'
      + '<div class="cf-gltf-kv" id="cf-gltf-atlas-kv"></div>'
      + '<p class="hint">Glissez-déposez un PNG ici pour utiliser votre propre atlas.</p>'
      + '</div></div>'
      + '<p class="hint cf-gltf-note" id="cf-gltf-atlas-note"></p>'
      + '<div class="cf-gltf-stale hidden" id="cf-gltf-stale"></div>'
      + '</section>'

      /* ── reglages ──────────────────────────────────────────────────── */
      + '<section class="cf-gltf-card">'
      + '<header class="cf-gltf-h"><b>Réglages</b>'
      + '<button class="lnk" id="cf-gltf-undo" type="button" title="Ctrl+Z">↶ annuler</button>'
      + '</header>'

      + '<div class="fld"><span class="lbl">Définition de l\'atlas</span>'
      + '<div class="cf-gltf-row">'
      + '<div class="seg sm" id="cf-gltf-res-seg"></div>'
      + '<label class="cf-gltf-num"><input type="number" id="cf-gltf-res" '
      + 'min="256" max="4096" step="64"><i>px</i></label>'
      /* LE SUR-ECHANTILLONNAGE DEVIENT UN BOUTON. On l'ecrivait honnetement
         depuis deux tours — « l'ilot agrandit la source de x1.349 et x1.853 »
         — sans jamais donner le moyen de le corriger. Le backend calcule la
         definition a laquelle l'ilot cesse d'agrandir la coupe ; ce bouton la
         pose. Aucun chiffre n'est calcule ici. */
      + '<button class="btn sm hidden" id="cf-gltf-res-fit" type="button"></button>'
      + '</div>'
      + '<p class="hint" id="cf-gltf-res-read"></p></div>'

      + '<div class="fld"><span class="lbl">Finition</span>'
      + '<div class="chips" id="cf-gltf-finish"></div>'
      + '<p class="hint" id="cf-gltf-finish-read"></p></div>'

      + '<div class="fld"><span class="lbl">Épaisseur</span>'
      + '<div class="cf-gltf-row">'
      + '<label class="cf-gltf-num"><input type="number" id="cf-gltf-th" '
      + 'min="0.2" max="1.2" step="0.01"><i>mm</i></label>'
      + '<button class="btn sm" id="cf-gltf-th-p5" type="button">reprendre la pièce 05</button>'
      + '</div>'
      + '<p class="hint" id="cf-gltf-th-read"></p></div>'

      + '<div class="fld"><span class="lbl">Textures du GLB</span>'
      + '<div class="cf-gltf-row">'
      + '<div class="seg sm" id="cf-gltf-img"></div>'
      + '<label class="cf-gltf-num cf-gltf-q hidden" id="cf-gltf-q-wrap">'
      + '<input type="number" id="cf-gltf-q" min="60" max="100" step="1"><i>q</i></label>'
      + '</div>'
      + '<p class="hint" id="cf-gltf-img-read"></p></div>'

      + '<p class="hint" id="cf-gltf-derive"></p>'

      + '</section>'

      /* ── livrables ─────────────────────────────────────────────────── */
      + '<section class="cf-gltf-card">'
      + '<header class="cf-gltf-h"><b>Livrables</b></header>'
      + '<div class="cf-gltf-checks" id="cf-gltf-formats"></div>'
      + '<p class="hint" id="cf-gltf-missing"></p>'
      /* LE LIBELLÉ AFFIRMAIT CE QUE LA MESURE DOIT DIRE. « 16 bits réels …
         refusés si les octets ne le prouvent pas » : une case à cocher n'a pas
         à plaider, elle demande. Le verdict — bits, niveaux, coût — s'affiche
         juste dessous, une fois les octets écrits et relus. */
      + '<label class="check tiny"><input type="checkbox" id="cf-gltf-bits16">'
      + '<span><b>16 bits</b> sur height et normal dans le ZIP '
      + '<i>(plus fin sur les dégradés, ZIP plus lourd)</i></span></label>'
      + '<p class="hint" id="cf-gltf-bits-read"></p>'
      + '<div class="fld"><span class="lbl">Origine du pivot</span>'
      + '<div class="seg sm" id="cf-gltf-pivot"></div>'
      + '<p class="hint" id="cf-gltf-pivot-read"></p></div>'
      + '<div class="fld"><span class="lbl">Portée</span>'
      + '<div class="seg sm" id="cf-gltf-scope"></div></div>'
      + '<button class="btn strong big wide" id="cf-gltf-build" type="button">'
      + 'Construire l\'export</button>'
      + '<p class="cf-gltf-free" id="cf-gltf-free"></p>'
      + '</section>'

      + '</div>'

      + '<div class="cf-gltf-col">'

      /* ── apercu 3D ─────────────────────────────────────────────────── */
      + '<section class="cf-gltf-card cf-gltf-grow">'
      + '<header class="cf-gltf-h"><b>Le fichier livré</b>'
      + '<span class="cf-gltf-sub">le .glb construit, ouvert ici</span>'
      + '<label class="check tiny"><input type="checkbox" id="cf-gltf-spin">'
      + '<span>rotation</span></label>'
      + '</header>'
      + '<div class="cf-gltf-view" id="cf-gltf-view"></div>'
      + '<div class="cf-gltf-mes mono" id="cf-gltf-mes"></div>'
      + '</section>'

      /* ── bordereau ─────────────────────────────────────────────────── */
      + '<section class="cf-gltf-card">'
      + '<header class="cf-gltf-h"><b>Bordereau</b>'
      + '<button class="btn sm hidden" id="cf-gltf-all" type="button">Tout télécharger</button>'
      + '</header>'
      + '<div id="cf-gltf-slip"></div>'
      /* ── LE SEUL POINT QUE CET ÉCRAN PERDAIT ────────────────────────────
         Il pesait chaque fichier à l'octet et ne disait nulle part OÙ il
         venait de l'écrire, ni ce qu'il en advient ensuite. Le relevé de
         disque existait — au bas de la colonne des réglages, à trois cartes
         du bouton « Télécharger », c'est-à-dire loin de l'endroit où la
         question se pose. Il se peint désormais SOUS le bordereau, contre
         les boutons qui livrent : la réponse est à côté du geste. */
      + '<p class="cf-gltf-free cf-gltf-where" id="cf-gltf-where"></p>'
      + '</section>'

      + '</div>'
      + '</div>';
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3. CABLAGE
     ═══════════════════════════════════════════════════════════════════════ */
  function wire(host) {
    $("#cf-gltf-compose").addEventListener("click", () => compose(true));
    $("#cf-gltf-build").addEventListener("click", () => build());
    $("#cf-gltf-undo").addEventListener("click", undo);
    $("#cf-gltf-th-p5").addEventListener("click", () => {
      set({ thickness_mm: null }, "épaisseur");
      paintAll(); markStale("épaisseur");
    });
    $("#cf-gltf-spin").addEventListener("change", (e) => {
      set({ spin: !!e.target.checked }, "rotation");
      const mv = $("#cf-gltf-mv");
      if (mv) { if (e.target.checked) mv.setAttribute("auto-rotate", ""); else mv.removeAttribute("auto-rotate"); }
    });
    $("#cf-gltf-bits16").addEventListener("change", (e) => {
      set({ bits16: !!e.target.checked }, "16 bits");
    });

    numField("#cf-gltf-res", 256, 4096, (v) => {
      set({ res: v }, "définition"); paintRes(); askDensity(v); markStale("définition");
    });
    $("#cf-gltf-res-fit").addEventListener("click", () => {
      const d = density(get("res"));
      const fit = d && d.res_fit;
      if (!fit) return;
      set({ res: Number(fit) }, "définition juste");
      paintRes(); askDensity(Number(fit)); markStale("définition");
      M.toast("définition ajustée à la source : " + fit + " px");
    });
    numField("#cf-gltf-th", 0.2, 1.2, (v) => {
      set({ thickness_mm: v }, "épaisseur"); paintTh(); markStale("épaisseur");
    });
    numField("#cf-gltf-q", 60, 100, (v) => { set({ jpeg_q: v }, "qualité"); });

    const drop = $("#cf-gltf-drop");
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => {
      e.preventDefault(); drop.classList.add("over");
    }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => {
      e.preventDefault(); drop.classList.remove("over");
    }));
    drop.addEventListener("drop", (e) => {
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) importAtlas(f);
    });
    host.addEventListener("click", onSlipClick);
  }

  /* Un champ numerique qui accepte la frappe, la molette et les fleches, et
     qui ne repond qu'a une valeur FINIE dans les bornes : le chiffre s'ecrit,
     il ne se choisit pas seulement dans une liste. */
  function numField(sel, lo, hi, apply) {
    const el = $(sel);
    if (!el) return;
    const commit = () => {
      const v = Number(el.value);
      if (!isFinite(v)) { paintAll(); return; }
      const c = Math.max(lo, Math.min(hi, v));
      el.value = String(c);
      apply(c);
    };
    el.addEventListener("change", commit);
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); commit(); }
      e.stopPropagation();          /* les raccourcis ne volent pas la frappe */
    });
  }

  function onKey(e) {
    const panel = M.slot() && M.slot().closest(".cf-panel");
    if (!panel || !panel.classList.contains("on")) return;
    const t = e.target;
    if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
      e.preventDefault(); undo(); return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === "e") { e.preventDefault(); build(); }
    else if (k === "a") { e.preventDefault(); compose(true); }
    else if (k === "g") { e.preventDefault(); grab("glb"); }
    else if (k === "t") { e.preventDefault(); grab("gltf"); }
    else if (k === "z") { e.preventDefault(); grab("zip"); }
    else if (k >= "1" && k <= "3") {
      e.preventDefault();
      const v = RES_STEPS[Number(k) - 1];
      set({ res: v }, "définition"); paintRes(); askDensity(v); markStale("définition");
    }
  }

  /* Le CORE appelle init() des HUIT pieces au demarrage : composer l'atlas la
     ferait rendre deux cartes a l'echelle 1 et televerser 4 Mo pour un onglet
     que l'utilisateur n'ouvrira peut-etre jamais — pendant que les sept autres
     pieces demarrent. On attend donc la premiere VISIBILITE du panneau. Il n'y
     a pas d'evenement pour ca (CF.show ne diffuse rien) : la classe « on » du
     panneau, elle, est observable. */
  function watchShown(host) {
    const panel = host.closest ? host.closest(".cf-panel") : null;
    if (!panel) { SHOWN = true; return; }
    if (panel.classList.contains("on")) { SHOWN = true; return; }
    if (typeof MutationObserver !== "function") { SHOWN = true; return; }
    const mo = new MutationObserver(() => {
      if (!panel.classList.contains("on")) return;
      mo.disconnect();
      SHOWN = true;
      if (!ATLAS && !BUSY) compose(false);
      paintAll();
    });
    mo.observe(panel, { attributes: true, attributeFilter: ["class"] });
  }

  /* ═══════════════════════════════════════════════════════════════════════
     4. RESEAU — tout est confine a /api/cards/<did>/gltf (regle 8)
     ═══════════════════════════════════════════════════════════════════════ */
  async function refresh(first) {
    try {
      INFO = await M.api.get("info");
      OFFLINE = false;
    } catch (e) {
      OFFLINE = true;
      INFO = null;
      paintAll();
      if (!first) M.toast(String(e && e.message || e), true);
      return;
    }
    if (INFO.last_build && INFO.last_build.files) BUILD = INFO.last_build;
    paintAll();
    if (BUILD) showBuild(BUILD, true);
    if (!ATLAS && SHOWN) compose(false);
  }

  /* LE RELEVÉ DE DISQUE ÉTAIT PRIS AVANT LA CONSTRUCTION. `INFO` est chargé à
     l'ouverture du panneau ; son bloc `local` compte le dossier À CET
     INSTANT-LÀ. Après un export, l'écran affichait donc « rien d'écrit pour ce
     jeu » sous un bordereau qui venait de peser trois fichiers. Un nombre juste
     au moment où on le lit et faux au moment où on l'affiche reste un nombre
     faux — on le redemande. */
  async function askLocal() {
    if (OFFLINE) return;
    try {
      const d = await M.api.get("info");
      if (INFO && d && d.local) INFO.local = d.local;
      paintReadouts();
    } catch (e) { /* la valeur precedente reste affichee */ }
  }

  async function askDensity(res) {
    if (OFFLINE) return;
    clearTimeout(askDensity._t);
    askDensity._t = setTimeout(async () => {
      try {
        const d = await M.api.get("info?res=" + encodeURIComponent(res));
        INFO = d;
        paintRes();
      } catch (e) { /* la valeur precedente reste affichee */ }
    }, 220);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5. L'ATLAS — compose par le MOTEUR UNIQUE, jamais redessine
     ═══════════════════════════════════════════════════════════════════════ */
  /* LA COUPE EST APPLIQUEE. `CF.renderCard` rend TOUJOURS la toile complete,
     fond perdu compris (815 x 1110 px pour 69 x 94 mm) ; l'ilot recto du
     contrat, lui, est plaque sur la FACE FINIE (63 x 88 mm). Poser la toile
     entiere dans l'ilot mettait donc 69 mm de dessin sur une face de 63 mm :
     les 3 mm de fond perdu etaient VISIBLES sur la carte 3D et l'illustration
     sortait 8,7 % trop petite. On decoupe donc au trait de coupe — exactement
     ce que fait un massicot — en lisant bleed_off_px et trim_px de la geometrie
     du CORE. Aucune formule de pixel n'est reinventee ici. */
  function trimRect(g) {
    const b = g.bleed_off_px || [0, 0], t = g.trim_px || g.canvas_px;
    return [b[0], b[1], t[0], t[1]];
  }

  async function composeCanvas(i, res) {
    const px = islandsPx(res);
    const cv = document.createElement("canvas");
    cv.width = res; cv.height = res;
    const ctx = cv.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    try { ctx.imageSmoothingQuality = "high"; } catch (err) { /* vieux moteur */ }

    /* Le fond des gouttieres porte la couleur de tranche : les convolutions du
       backend sont CYCLIQUES, un fond noir aurait bave sur le bord des
       ilots. Il ne reste visible que la ou la dilatation ci-dessous n'arrive
       pas. */
    const edge = edgeColor();
    ctx.fillStyle = edge;
    ctx.fillRect(0, 0, res, res);

    const g = CF.geom();
    const cut = trimRect(g);
    const front = await CF.renderCard(i, { face: "front" });
    const back = await CF.renderCard(i, { face: "back" });

    /* DILATATION DES BORDS. Les gouttieres font 0,02 x res (40 px en 2048).
       Remplies d'un aplat, les niveaux de mip 3 a 5 melangeaient le bord de la
       carte vers ce gris : halo clair des que la carte est vue petite. On pose
       donc d'abord chaque ilot AGRANDI du demi-ecart, puis l'ilot exact
       par-dessus : la gouttiere garde une continuation du dessin, l'ilot lui
       reste au pixel pres. */
    const pad = Math.max(2, Math.round(res * 0.01));
    const grow = (img, src, r) => ctx.drawImage(img, src[0], src[1], src[2], src[3],
      r[0] - pad, r[1] - pad, r[2] + 2 * pad, r[3] + 2 * pad);
    grow(front, cut, px.front);
    grow(back, cut, px.back);

    ctx.drawImage(front, cut[0], cut[1], cut[2], cut[3],
                  px.front[0], px.front[1], px.front[2], px.front[3]);
    ctx.drawImage(back, cut[0], cut[1], cut[2], cut[3],
                  px.back[0], px.back[1], px.back[2], px.back[3]);

    /* la tranche : un leger degrade, sinon le chant de la carte est un aplat
       parfaitement plat que la lumiere n'accroche pas. Elle deborde de `pad`
       vers le haut pour la meme raison de mip. */
    const e = px.edge;
    const grad = ctx.createLinearGradient(0, e[1] - pad, 0, e[1] + e[3]);
    grad.addColorStop(0, shade(edge, -0.16));
    grad.addColorStop(0.5, edge);
    grad.addColorStop(1, shade(edge, -0.22));
    ctx.fillStyle = grad;
    ctx.fillRect(e[0], e[1] - pad, e[2], e[3] + pad);
    return cv;
  }

  function shade(hex, k) {
    const s = String(hex).replace("#", "");
    const n = s.length === 3 ? s.split("").map((c) => c + c).join("") : s.slice(0, 6);
    const v = parseInt(n, 16);
    const f = (x) => Math.max(0, Math.min(255, Math.round(x * (1 + k))));
    return "#" + [f((v >> 16) & 255), f((v >> 8) & 255), f(v & 255)]
      .map((x) => x.toString(16).padStart(2, "0")).join("");
  }

  async function compose(loud) {
    if (BUSY) return;
    const res = get("res");
    const i = CF.current ? CF.current() : 0;
    BUSY = true;
    if (loud) M.busy(true, "composition de l'atlas…");
    try {
      const cv = await composeCanvas(i, res);
      const blob = await new Promise((ok, ko) => cv.toBlob(
        (b) => (b ? ok(b) : ko(new Error("encodage de l'atlas impossible"))),
        "image/png"));
      if (ATLAS && ATLAS.url) URL.revokeObjectURL(ATLAS.url);
      ATLAS = { blob: blob, url: URL.createObjectURL(blob), res: res, i: i,
                sig: atlasSig(i, res) };
      drawAtlas(cv);
      if (!OFFLINE) {
        const r = await M.api.raw("POST", "atlas?i=" + i, blob);
        if (!r.ok) throw new Error("dépôt de l'atlas refusé (" + r.status + ")");
        const d = await r.json();
        ATLAS.server = d.atlas;
      }
      clearStale();
      paintAtlas();
      if (loud) M.toast("atlas " + res + " x " + res + " composé — " + weight(blob.size));
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    } finally {
      BUSY = false;
      if (loud) M.busy(false);
    }
  }

  /* Le jeu ENTIER : un atlas par carte, composes par le meme moteur. C'est ce
     qui rend « export du deck en un ZIP » utilisable depuis l'ecran et pas
     seulement depuis l'API — sans ca, le ZIP ne contiendrait que la carte
     affichee et le libelle mentirait. */
  async function composeAll() {
    const n = CF.cards().length;
    const res = get("res");
    for (let i = 0; i < n; i++) {
      M.busy(true, "atlas " + (i + 1) + " / " + n + "…");
      const cv = await composeCanvas(i, res);
      const blob = await new Promise((ok, ko) => cv.toBlob(
        (b) => (b ? ok(b) : ko(new Error("encodage de l'atlas impossible"))),
        "image/png"));
      const r = await M.api.raw("POST", "atlas?i=" + i, blob);
      if (!r.ok) throw new Error("dépôt de l'atlas " + (i + 1) + " refusé ("
        + r.status + ")");
      if (i === (CF.current ? CF.current() : 0)) {
        if (ATLAS && ATLAS.url) URL.revokeObjectURL(ATLAS.url);
        ATLAS = { blob: blob, url: URL.createObjectURL(blob), res: res, i: i,
                  sig: atlasSig(i, res), server: (await r.json()).atlas };
        drawAtlas(cv);
      }
    }
    clearStale();
    paintAtlas();
    return n;
  }

  async function importAtlas(file) {
    if (!/\.(png|jpe?g)$/i.test(file.name)) {
      M.toast("un PNG ou un JPEG est attendu", true); return;
    }
    M.busy(true, "import de l'atlas…");
    try {
      const i = CF.current ? CF.current() : 0;
      const r = await M.api.raw("POST", "atlas?i=" + i, file);
      if (!r.ok) {
        let d = null; try { d = await r.json(); } catch (err) { d = null; }
        throw new Error((d && d.detail) || ("import refusé (" + r.status + ")"));
      }
      const d = await r.json();
      if (ATLAS && ATLAS.url) URL.revokeObjectURL(ATLAS.url);
      ATLAS = { blob: file, url: URL.createObjectURL(file), res: d.atlas.res[0],
                i: i, sig: atlasSig(i, d.atlas.res[0]),
                server: d.atlas, imported: file.name };
      const img = new Image();
      img.onload = () => drawAtlas(img);
      img.src = ATLAS.url;
      clearStale();
      paintAtlas();
      M.toast("atlas importé : " + file.name + " — " + d.atlas.res.join(" x "));
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    } finally { M.busy(false); }
  }

  /* LES VUES D'INSPECTION — le reproche le plus repete, et il etait fonde :
     cet ecran demandait qu'on le croie sur ses ilots et ses UV sans jamais
     savoir les MONTRER. Trois vues sur la meme vignette, et aucune n'invente
     de coordonnee : le fil de fer UV vient de `GET info.uv_wire`, c'est-a-dire
     des triangles du maillage LIVRE, servis par le backend. */
  const VIEWS = [
    { id: "atlas", label: "Atlas", title: "ce qui part dans le fichier" },
    { id: "uv", label: "UV", title: "le fil de fer UV du maillage livré" },
    { id: "ilots", label: "Îlots", title: "les rectangles de l'atlas" },
    { id: "canaux", label: "Canaux",
      title: "les maps côte à côte — cochez « Planche de contrôle » et construisez" },
  ];
  let VIEW = "atlas";
  let ATLAS_SRC = null;
  let PROOF_SRC = null;                 /* la planche de contrôle CONSTRUITE */
  let PROOF_FOR = null;

  /* LA QUATRIEME VUE. « Ne pas pouvoir REGARDER ses propres maps dans le
     produit » revenait a chaque relecture. La planche n'est PAS redessinee
     ici : c'est le PNG que le backend a ecrit depuis les memes images que les
     maps du ZIP, telecharge et affiche tel quel. Si personne ne l'a
     construite, on le dit au lieu de dessiner un substitut. */
  function loadProof() {
    const f = fileOf("proof");
    if (!f) { PROOF_SRC = null; PROOF_FOR = null; renderView(); return; }
    if (PROOF_FOR === f.name && PROOF_SRC) { renderView(); return; }
    const url = M.api.url("file/" + encodeURIComponent(f.name)) + "?t=" + Date.now();
    const img = new Image();
    img.onload = () => { PROOF_SRC = img; PROOF_FOR = f.name; renderView(); };
    img.onerror = () => { PROOF_SRC = null; PROOF_FOR = null; renderView(); };
    img.src = url;
  }

  function drawAtlas(src) {
    if (src) ATLAS_SRC = src;
    renderView();
  }

  function renderView() {
    const cv = $("#cf-gltf-atlas-cv");
    if (!cv) return;
    const S = 240;
    cv.width = S; cv.height = S;
    const ctx = cv.getContext("2d");
    ctx.clearRect(0, 0, S, S);
    if (VIEW === "canaux") {
      ctx.fillStyle = tok("--bg-panel-3", "#14141a");
      ctx.fillRect(0, 0, S, S);
      if (PROOF_SRC) {
        const k = Math.min(S / PROOF_SRC.width, S / PROOF_SRC.height);
        const w = PROOF_SRC.width * k, h = PROOF_SRC.height * k;
        ctx.drawImage(PROOF_SRC, (S - w) / 2, (S - h) / 2, w, h);
      } else {
        const n = (INFO && INFO.maps && INFO.maps.count) || 0;
        ctx.fillStyle = tok("--ink-muted", "#8b93a7");
        ctx.font = "600 9px ui-monospace, monospace";
        ctx.fillText("cochez « Planche de contrôle »", 12, S / 2 - 8);
        ctx.fillText("puis construisez (E) :", 12, S / 2 + 6);
        ctx.fillText((n ? n + " canaux" : "les canaux") + " seront ici.",
                     12, S / 2 + 20);
      }
      return;
    }
    if (ATLAS_SRC) {
      ctx.globalAlpha = (VIEW === "uv") ? 0.34 : 1;
      ctx.drawImage(ATLAS_SRC, 0, 0, S, S);
      ctx.globalAlpha = 1;
    }
    if (VIEW === "uv") {
      const tris = (INFO && INFO.uv_wire && INFO.uv_wire.tris) || [];
      const acc = tok("--accent", "#f0b429");
      ctx.strokeStyle = acc;
      ctx.globalAlpha = 0.85;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      tris.forEach((t) => {
        ctx.moveTo(t[0] * S, t[1] * S);
        ctx.lineTo(t[2] * S, t[3] * S);
        ctx.lineTo(t[4] * S, t[5] * S);
        ctx.closePath();
      });
      ctx.stroke();
      ctx.globalAlpha = 1;
      const me = (INFO && INFO.mesh) || {};
      ctx.fillStyle = tok("--bg-panel-3", "#14141a");
      ctx.fillRect(2, S - 14, S - 4, 12);
      ctx.fillStyle = acc;
      ctx.font = "600 8px ui-monospace, monospace";
      ctx.fillText(tris.length + " triangles UV · " + (me.uv_islands || "?")
        + " îlots mesurés (" + (me.uv_islands_tri || []).join("+") + ")",
        5, S - 5);
      return;
    }
    const uv = islands();
    const acc2 = tok("--accent", "#f0b429");
    ctx.lineWidth = 1;
    ctx.font = "600 8px ui-monospace, monospace";
    Object.keys(uv).forEach((k) => {
      const r = uv[k];
      const x = r[0] * S, y = r[1] * S, w = (r[2] - r[0]) * S, h = (r[3] - r[1]) * S;
      ctx.strokeStyle = acc2;
      ctx.setLineDash([3, 3]);
      ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
      ctx.setLineDash([]);
      const t = ISLAND_LABEL[k] || k;
      const tw = ctx.measureText(t).width + 6;
      ctx.fillStyle = tok("--bg-panel-3", "#14141a");
      ctx.fillRect(x + 2, y + 2, tw, 11);
      ctx.fillStyle = acc2;
      ctx.fillText(t, x + 5, y + 10);
    });
  }

  function paintViewSeg() {
    seg($("#cf-gltf-view-seg"), VIEWS, VIEW, (v) => {
      VIEW = v; paintViewSeg();
      if (v === "canaux") loadProof(); else renderView();
    });
    const sub = $("#cf-gltf-atlas-sub");
    const me = (INFO && INFO.mesh) || {};
    if (sub) {
      sub.innerHTML = "un seul matériau — <b>"
        + (me.uv_islands != null ? me.uv_islands : "?")
        + "</b> îlots UV mesurés sur le maillage livré";
    }
  }

  /* ── LE BANDEAU « PÉRIMÉ » ÉTAIT UNE ALERTE FAUSSE ────────────────────────
     `core:render` se déclenche à CHAQUE redessin du CORE, y compris quand le
     module vient lui-même de repeindre. Le bandeau « L'atlas déposé date
     d'avant carte » s'affichait donc juste après une composition, sur un
     atlas qui venait exactement de cette carte-là. Un lecteur en tirait,
     logiquement, que les fichiers du bordereau étaient périmés. Une alerte
     fausse est un chiffre faux : elle décrit un état qui n'existe pas.
     On MESURE donc au lieu d'écouter : la signature de tout ce dont l'atlas
     dépend (géométrie, face, cadre, typo, données, matière, la carte
     elle-même, la définition et l'index) est prise à la composition, et
     recomparée à chaque événement. Le bandeau ne sort que si elle a bougé. */
  function atlasSig(i, res) {
    try {
      const d = CF.doc() || {};
      const cards = CF.cards ? CF.cards() : [];
      return JSON.stringify([d.format, d.face, d.frame, d.type, d.data,
                             d.texture, cards[i] || null, res, i]);
    } catch (e) { return null; }
  }

  /* ── LA COMPARAISON SE FAISAIT AVEC SOI-MÊME ─────────────────────────────
     `atlasSig` prend l'index de carte et la DÉFINITION en paramètres,
     précisément pour que le changement de l'un ou de l'autre se voie. On lui
     passait `ATLAS.i, ATLAS.res` — c'est-à-dire les valeurs avec lesquelles
     l'atlas courant a été composé : la signature ne pouvait donc jamais
     différer sur ces deux-là, et `clearStale()` tombait à tous les coups.
     Conséquence mesurée : régler la définition à 512 marquait bien l'atlas
     périmé, puis le premier `core:render` venu effaçait le bandeau ; la
     construction repartait sur l'atlas 2048 déjà déposé, et la fiche de
     gauche annonçait « 2048 x 2048 px · 404,8 DPI » au-dessus d'un export
     réellement fait en 512 (101,2 DPI, écrit trois centimètres plus bas).
     Deux densités contradictoires dans le même panneau, dont une fausse.
     On compare donc à l'état COURANT — c'est ce que les paramètres servaient. */
  function checkStale(why) {
    if (!ATLAS) return;
    const i = CF.current ? CF.current() : 0;
    const s = atlasSig(i, get("res"));
    if (s && ATLAS.sig && s === ATLAS.sig) { clearStale(); return; }
    markStale(why);
  }

  function markStale(why) {
    if (!ATLAS) return;
    ATLAS.stale = why;
    const el = $("#cf-gltf-stale");
    if (!el) return;
    el.classList.remove("hidden");
    el.innerHTML = "L'atlas déposé date d'avant « " + esc(why)
      + " ». <button class=\"lnk\" data-act=\"compose\">recomposer</button>";
  }

  function clearStale() {
    if (ATLAS) ATLAS.stale = null;
    const el = $("#cf-gltf-stale");
    if (el) el.classList.add("hidden");
  }

  /* ═══════════════════════════════════════════════════════════════════════
     6. CONSTRUCTION + BORDEREAU
     ═══════════════════════════════════════════════════════════════════════ */
  async function build() {
    if (BUSY) return;
    if (OFFLINE) { M.toast("API cartes indisponible", true); return; }
    const formats = get("formats");
    if (!formats.length) { M.toast("cochez au moins un livrable", true); return; }
    const deck = get("scope") === "deck";
    BUSY = true;
    const t0 = Date.now();
    try {
      if (deck) await composeAll();
      else if (!ATLAS || ATLAS.stale) {
        BUSY = false; await compose(false); BUSY = true;
      }
      M.busy(true, "construction — maps PBR, GLB, glTF, ZIP…");
      const body = {
        res: get("res"), formats: formats, finish: get("finish"),
        bits16: !!get("bits16"), img: get("img"), jpeg_q: get("jpeg_q"),
        scope: get("scope"), pivot: get("pivot"),
      };
      /* La carte AFFICHEE, pas « la premiere du disque » : un jeu ou les
         atlas 0..2 existent et ou l'on regarde la carte 3 exportait la 1 sans
         un mot. */
      if (!deck) body.cards = [CF.current ? CF.current() : 0];
      const th = get("thickness_mm");
      if (typeof th === "number" && th > 0) body.thickness_mm = th;
      const d = await M.api.post("build", body);
      BUILD = d.build;
      showBuild(BUILD, false);
      askLocal();                 /* le dossier vient de changer : on recompte */
      M.emit("built", { files: BUILD.files.length, bytes: BUILD.total_bytes });
      M.toast(BUILD.files.length + " fichier(s) · " + weight(BUILD.total_bytes)
        + " · " + ((Date.now() - t0) / 1000).toFixed(1) + " s");
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    } finally { BUSY = false; M.busy(false); }
  }

  function fileOf(kind) {
    if (!BUILD) return null;
    for (let i = 0; i < BUILD.files.length; i++) {
      if (BUILD.files[i].kind === kind) return BUILD.files[i];
    }
    return null;
  }

  async function grab(kind, name) {
    const f = name ? { name: name } : fileOf(kind);
    if (!f) { M.toast("construisez l'export d'abord (E)", true); return; }
    M.busy(true, "téléchargement…");
    try {
      const b = await M.api.blob("GET", "file/" + encodeURIComponent(f.name));
      M.download(b, f.name);
      M.toast(f.name + " — " + weight(b.size));
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    } finally { M.busy(false); }
  }

  function onSlipClick(e) {
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!b) return;
    const act = b.getAttribute("data-act");
    if (act === "grab") { e.preventDefault(); grab(null, b.getAttribute("data-name")); }
    else if (act === "compose") { e.preventDefault(); compose(true); }
    else if (act === "build") { e.preventDefault(); build(); }
    /* Les deux commandes que le bordereau porte à côté de ses constats : la
       définition juste (servie par le backend, jamais recalculée ici) et les
       deux formats qu'un trancheur ouvre. Elles COCHENT et marquent le lot
       périmé — elles ne construisent pas dans le dos de l'utilisateur. */
    else if (act === "fit") {
      e.preventDefault();
      const d = density(get("res"));
      const fit = d && d.res_fit;
      if (!fit) return;
      set({ res: Number(fit) }, "définition juste");
      paintRes(); askDensity(Number(fit)); markStale("définition");
      M.toast("définition ajustée à la source : " + fit + " px");
    } else if (act === "slice") {
      e.preventDefault();
      const cur = get("formats").slice();
      ["stl", "3mf"].forEach((k) => { if (cur.indexOf(k) < 0) cur.push(k); });
      set({ formats: cur }, "livrables");
      paintFormats(); paintSlip(); markStale("livrables");
      M.toast("STL et 3MF cochés — reconstruisez pour les obtenir");
    }
  }

  function showBuild(b, quiet) {
    paintSlip();
    paintBits();
    const glb = fileOf("glb");
    if (glb) mountViewer(glb.name);
    PROOF_FOR = null;
    if (VIEW === "canaux") loadProof();
    if (!quiet) paintReadouts();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     7. LA VISIONNEUSE — sur le GLB CONSTRUIT, et elle MESURE
     ═══════════════════════════════════════════════════════════════════════ */
  function mountViewer(fname) {
    const host = $("#cf-gltf-view");
    if (!host) return;
    if (typeof customElements === "undefined" || !customElements.get("model-viewer")) {
      host.innerHTML = '<p class="empty-note sm">La visionneuse 3D '
        + '(/assets/model-viewer.min.js) n\'est pas chargée. Le fichier, lui, '
        + 'est construit et téléchargeable.</p>';
      return;
    }
    const url = M.api.url("file/" + encodeURIComponent(fname)) + "?t=" + Date.now();
    let mv = $("#cf-gltf-mv");
    if (!mv) {
      mv = document.createElement("model-viewer");
      mv.id = "cf-gltf-mv";
      mv.setAttribute("camera-controls", "");
      mv.setAttribute("interaction-prompt", "none");
      mv.setAttribute("shadow-intensity", "0.75");
      mv.setAttribute("exposure", "1.05");
      mv.setAttribute("environment-image", "neutral");
      /* Le rayon est en METRES parce que la scene l'est : une carte de 88 mm
         se cadre a 0,16 m. C'est la meme echelle physique que celle du noeud —
         si un jour le fichier perdait son echelle, ce cadrage montrerait un
         point minuscule, et le defaut se verrait au lieu de se cacher. */
      mv.setAttribute("camera-orbit", "20deg 70deg 0.16m");
      mv.setAttribute("min-camera-orbit", "auto auto 0.04m");
      mv.setAttribute("max-camera-orbit", "auto auto 1m");
      mv.addEventListener("load", () => measure(mv));
      mv.addEventListener("error", () => {
        $("#cf-gltf-mes").textContent = "la visionneuse n'a pas pu ouvrir le GLB";
      });
      host.innerHTML = "";
      host.appendChild(mv);
    }
    if (get("spin")) mv.setAttribute("auto-rotate", "");
    else mv.removeAttribute("auto-rotate");
    mv.setAttribute("src", url);
  }

  /* LA MESURE. `<model-viewer>` compte en METRES : si le noeud ne portait pas
     l'echelle physique, il annoncerait une carte de 1,43 x 2,00 m. C'est la
     ligne qui prouve, a l'ecran, que le fichier connait sa taille. */
  function measure(mv) {
    const out = $("#cf-gltf-mes");
    if (!out) return;
    let d = null;
    try { d = mv.getDimensions ? mv.getDimensions() : null; } catch (e) { d = null; }
    /* ── DEUX LECTURES DU FICHIER, ET PLUS RIEN D'AUTRE ───────────────────
       Cette ligne publiait une TROISIÈME valeur — « attendu 63.0000 x 88.0000
       x 0.3200 mm » — puis « écart 0.0 µm ». Aucune des deux ne se relit dans
       un octet livré : la première recopie le réglage d'épaisseur et le format
       du document, la seconde note la ressemblance entre le réglage et le
       relevé. C'est la note que l'écran se donne, et personne ne l'a demandée.
       Celui qui exporte veut savoir ce que MESURE son .glb, dans quelle unité,
       et d'où sort le nombre. On ne publie donc que ce qui vient du fichier.

       ── UN SEUL RELEVÉ NE PROUVE RIEN QUAND IL TOMBE PILE ────────────────
       On en montre DEUX, obtenus par des chemins qui n'ont rien en commun :
       le backend relit les float32 de POSITION dans le chunk binaire du .glb
       et applique l'échelle du nœud ; la visionneuse, elle, fait parser le
       même fichier par un moteur 3D, dans cette page. Leur accord se constate
       sur les deux nombres ÉCRITS, au même rang — sans qu'on ait besoin d'en
       calculer un troisième pour le dire. */
    const mm4 = (a) => a.map((v) => Number(v).toFixed(4)).join(" x ");
    const buf = ((BUILD && BUILD.cards && BUILD.cards[0]
                  && BUILD.cards[0].glb) || {}).bbox_mm || null;
    const deuxieme = !!(buf && buf.length === 3);
    /* LE NOMBRE D'ABORD, SA PROVENANCE ENSUITE, ET LA MÊME FORME DES DEUX
       CÔTÉS. Avec le libellé en tête, la rangée se repliait au milieu du
       relevé — « 63.0000 x 88.0000 x » sur une ligne, « 0.3200 mm » sur
       la suivante — et les deux lectures ne commençaient pas à la même
       colonne. Posés l'un sous l'autre, alignés, deux nombres identiques SE
       VOIENT identiques : c'est tout ce que ce bloc a à montrer. */
    const ligneBuf = deuxieme
      ? '<span><b>' + mm4(buf) + ' mm</b> — les float32 de POSITION relus '
        + 'dans le chunk binaire du .glb, à l\'échelle du nœud</span>'
      : '';
    if (!d) {
      out.innerHTML = ligneBuf
        + '<span>la visionneuse n\'a pas rendu de boîte englobante pour ce '
        + 'fichier.</span>';
      return;
    }
    /* Quatre décimales des deux côtés : le relevé sort en float32, il porte
       ses derniers chiffres, et deux nombres écrits au même rang se comparent
       à l'œil. Les micromètres ne s'affichent QUE si les deux lectures
       divergent — un « 0.0 µm » permanent ne mesure rien. */
    const mm = [d.x * 1000, d.y * 1000, d.z * 1000];
    let accord = '';
    if (deuxieme) {
      const um = Math.max.apply(null,
        mm.map((v, i) => Math.abs(v - buf[i]))) * 1000;
      accord = (mm4(mm) === mm4(buf))
        ? '<span>un moteur 3D dans cette page d\'un côté, les octets du '
          + 'fichier de l\'autre : deux chemins sans rien en commun, '
          + '<b class="cf-gltf-ok">le même nombre</b>.</span>'
        : '<span class="cf-gltf-ko">les deux lectures ne donnent pas le même '
          + 'nombre : ' + um.toFixed(1) + ' µm d\'un relevé à l\'autre sur '
          + 'l\'axe le plus large.</span>';
    }
    /* Chaque relevé dans son propre <span> : la feuille donne une rangée
       pleine à chaque ENFANT du bloc, et un texte nu deviendrait un élément
       anonyme que la règle ne peut pas atteindre. */
    out.innerHTML = '<span><b>' + mm4(mm) + ' mm</b> — la boîte englobante '
      + 'que la visionneuse a mesurée en ouvrant le .glb</span>'
      + ligneBuf + accord;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     8. PEINTURE
     ═══════════════════════════════════════════════════════════════════════ */
  function paintAll() {
    paintRes(); paintFinish(); paintTh(); paintImg(); paintFormats();
    paintScope(); paintAtlas(); paintSlip(); paintReadouts(); paintUndo();
    paintViewerEmpty(); paintBits(); paintPivot(); paintViewSeg();
    paintDerive();
    const b16 = $("#cf-gltf-bits16"); if (b16) b16.checked = !!get("bits16");
    const sp = $("#cf-gltf-spin"); if (sp) sp.checked = !!get("spin");
  }

  function seg(el, items, cur, onPick) {
    if (!el) return;
    el.innerHTML = items.map((it) => '<button class="seg-b'
      + (String(it.id) === String(cur) ? " active" : "") + '" type="button" '
      + 'data-v="' + esc(it.id) + '"' + (it.title ? ' title="' + esc(it.title) + '"' : "")
      + '>' + esc(it.label) + '</button>').join("");
    $$("#" + el.id + " .seg-b").forEach((b) => b.addEventListener("click", () => {
      onPick(b.getAttribute("data-v"));
    }));
  }

  function paintRes() {
    const cur = get("res");
    seg($("#cf-gltf-res-seg"), RES_STEPS.map((r, i) => (
      { id: r, label: (r / 1024) + "k", title: "raccourci " + (i + 1) })), cur,
      (v) => { set({ res: Number(v) }, "définition"); paintRes(); askDensity(Number(v)); markStale("définition"); });
    const inp = $("#cf-gltf-res");
    if (inp && document.activeElement !== inp) inp.value = String(cur);
    const read = $("#cf-gltf-res-read");
    if (!read) return;
    const dens = density(cur);
    /* AVANT les sorties anticipees : un bouton qui resterait affiche apres un
       changement de definition proposerait un ajustement qui n'est plus le
       bon — donc un chiffre faux sur un bouton. */
    paintFit(dens);
    if (!dens) { read.textContent = "définition libre de 256 à 4096 px."; return; }
    const dpi = dens.dpi || [0, 0];
    /* TROIS NOMBRES, ET UN SEUL SE COMPARE A LA CIBLE.
       Cette ligne affichait « 404.8 x 555.6 DPI, au-dessus de l'impression
       (300) » en vert. C'etait la densite de TEXELS de l'ilot, pas celle de
       l'information : l'ilot est rempli par un rendu de 744 x 1039 px, donc
       agrandi x1,35 et x1,85. On n'ajoute pas de detail en etirant. Le vert ne
       porte plus que sur `dpi_effective`, et le sur-echantillonnage est ecrit
       au lieu d'etre encaisse. */
    const eff = dens.dpi_effective;
    /* PLUS DE REPLI A 300. Ce « || 300 » etait un chiffre ecrit ici, servi a
       personne : si le service de densite cessait un jour de publier la
       definition du document, l'ecran aurait continue d'annoncer 300 DPI sans
       que rien ne le porte. Sans valeur servie, la phrase ne se peint pas. */
    const cible = dens.dpi_target;
    if (eff == null) {
      read.innerHTML = 'Face dans l\'atlas : <b>' + dens.front_px.join(" x ")
        + ' px</b> — <b>' + dpi[0] + ' x ' + dpi[1] + ' DPI</b> de texels';
      return;
    }
    const ok = !!dens.print_ok;
    /* « L'ÎLOT L'AGRANDIT DE x0.675 » N'EST PAS UNE PHRASE VRAIE. Mesuré le
       12/08 à 1024 px : sous la définition juste, l'îlot ne grandit pas la
       coupe, il la RÉDUIT — donc il jette de l'information avant même
       l'encodage. Le verbe suit maintenant le nombre, dans les deux sens. */
    const up = dens.upsample || [1, 1];
    const verbe = (up[0] >= 1 && up[1] >= 1) ? 'l\'îlot l\'agrandit de'
      : (up[0] <= 1 && up[1] <= 1) ? '<b class="cf-gltf-ko">l\'îlot la réduit</b> à'
        : 'l\'îlot la met à l\'échelle';
    /* CETTE LIGNE PARLAIT DE « PNG LIVRÉS » AVANT QU'IL EN EXISTE UN. Elle
       vit dans les réglages : elle décrit ce que la définition choisie VA
       produire, et le service de densité la sert dès qu'on bouge le curseur,
       construction ou pas. Le bordereau, lui, relit le chunk dans les octets
       écrits et l'affiche là-bas. Ici on annonce, là-bas on prouve. */
    read.innerHTML = 'Face : <b>' + dens.front_px.join(" x ") + ' px</b>, texels '
      + '<b>' + dpi[0] + ' x ' + dpi[1] + ' DPI</b> <i>(c\'est cette densité '
      + 'qui partira dans le chunk pHYs de chaque PNG)</i><br>'
      + 'Information réelle <b class="' + (ok ? "cf-gltf-ok" : "cf-gltf-ko") + '">'
      + eff + ' DPI</b> — la source rognée fait ' + (dens.source_px || []).join(" x ")
      + ' px, ' + verbe + ' <b>x' + up[0] + '</b> et <b>x' + up[1] + '</b>. '
      /* « LA DÉFINITION DE LA CARTE (300 DPI) EST TENUE » est la phrase d'un
         correcteur qui coche une case. Le nombre, lui, reste : c'est la
         définition que l'utilisateur a posée dans la barre du document, et
         savoir si son export la garde ou la perd est exactement ce qu'il
         vient chercher. On lui dit ce que fait son export, pas la note. */
      + (cible == null ? '' : '<span class="'
        + (ok ? "cf-gltf-ok" : "cf-gltf-ko") + '">'
        + (ok ? "l\'export garde les " : "l\'export descend sous les ")
        + cible + " DPI posés dans la barre du document"
        + '</span> · ')
      + 'texels non carrés : ' + dens.anisotropy + 'x'
      + (dens.useful_pct != null
        ? ' · <b>' + dens.useful_pct + ' %</b> des texels de l\'îlot portent '
          + 'de l\'information'
        : '')
      + (dens.fit_note ? '<br>' + esc(dens.fit_note) : '');
    paintFit(dens);
  }

  /* La definition JUSTE, servie par le backend (`atlas.res_fit`), jamais
     recalculee ici : l'ecran n'a aucune formule de pixel. Le bouton disparait
     quand on y est deja — proposer « ajuster » a une valeur deja posee serait
     un bouton qui ment sur ce qu'il ferait. */
  function paintFit(dens) {
    const b = $("#cf-gltf-res-fit");
    if (!b) return;
    const fit = dens && dens.res_fit;
    const cur = get("res");
    if (!fit || Number(fit) === Number(cur)) { b.classList.add("hidden"); return; }
    b.classList.remove("hidden");
    b.textContent = "ajuster à la source (" + fit + " px)";
    b.title = String(dens.fit_note || "");
  }

  function density(res) {
    if (!INFO || !INFO.atlas) return null;
    const ask = INFO.atlas.density_ask;
    if (ask && Number(ask.res) === Number(res)) return ask;
    const d = INFO.atlas.density || {};
    return d[String(res)] || null;
  }

  function paintFinish() {
    const el = $("#cf-gltf-finish");
    if (!el) return;
    const list = (INFO && INFO.finishes) || [
      { id: "mat", label: "Mat (papier)" }, { id: "satin", label: "Satiné" },
      { id: "vernis", label: "Vernis sélectif" }, { id: "foil", label: "Dorure à chaud" },
      { id: "holo", label: "Holographique" }];
    const cur = get("finish");
    el.innerHTML = list.map((f) => '<button class="chip'
      + (f.id === cur ? " active" : "") + '" type="button" data-v="' + esc(f.id)
      + '">' + esc(f.label) + '</button>').join("");
    $$("#cf-gltf-finish .chip").forEach((b) => b.addEventListener("click", () => {
      set({ finish: b.getAttribute("data-v") }, "finition");
      paintFinish();
    }));
    const read = $("#cf-gltf-finish-read");
    const f = list.filter((x) => x.id === cur)[0];
    if (read && f && f.roughness != null) {
      /* L'EMISSION EST ANNONCEE PARCE QU'ELLE PART DANS LE FICHIER. Le GLB
         sortait avec emissiveFactor [1,1,1] quelle que soit la finition : une
         carte en papier mat brillait toute seule, lumieres eteintes. Elle vaut
         desormais 0 sur les trois finitions papier, et l'ecran le dit avant le
         clic. Meme chose pour les extensions : la liste vient du backend, donc
         l'ecran ne peut pas promettre un KHR_* qui ne sera pas emis. */
      const ext = (f.extensions || []);
      read.innerHTML = 'rugosité <b>' + f.roughness + '</b> · métal <b>' + f.metallic
        + '</b> · vernis <b>' + f.clearcoat + '</b> · émission <b'
        + (f.emissive ? '' : ' class="cf-gltf-ok"') + '>' + (f.emissive != null ? f.emissive : 0)
        + '</b>' + (f.emissive ? '' : ' <i>(le papier n\'émet pas de lumière)</i>')
        + '<br>cuits dans les maps, facteurs glTF à 1.0 · extensions écrites : <b>'
        + (ext.length ? esc(ext.join(", ")) : "aucune") + '</b>';
    } else if (read) {
      read.textContent = "les niveaux sont cuits dans les maps ; les facteurs glTF restent à 1.0";
    }
  }

  function paintTh() {
    const inp = $("#cf-gltf-th");
    const th = thicknessMM();
    if (inp && document.activeElement !== inp) inp.value = String(th);
    const src = thicknessSource();
    const read = $("#cf-gltf-th-read");
    const btn = $("#cf-gltf-th-p5");
    if (btn) btn.disabled = (src !== "gltf");
    if (!read) return;
    const g = CF.geom();
    read.innerHTML = 'Carte finie : <b>' + g.trim_mm[0] + ' x ' + g.trim_mm[1]
      + ' x ' + th + ' mm</b> · source : '
      + (src === "solid" ? "<b>pièce 05</b>" : src === "gltf"
        ? "réglage local" : "défaut carte à jouer") + ' · '
      + (th / 25.4).toFixed(4) + ' in';
  }

  function paintImg() {
    const cur = get("img");
    seg($("#cf-gltf-img"), [
      { id: "auto", label: "auto", title: "encode les deux et garde le plus léger" },
      { id: "png", label: "PNG", title: "sans perte" },
      { id: "jpeg", label: "JPEG", title: "photo" }], cur,
      (v) => { set({ img: v }, "textures"); paintImg(); });
    const q = $("#cf-gltf-q-wrap");
    if (q) q.classList.toggle("hidden", cur === "png");
    const qi = $("#cf-gltf-q");
    if (qi && document.activeElement !== qi) qi.value = String(get("jpeg_q"));
    const read = $("#cf-gltf-img-read");
    if (read) {
      read.innerHTML = cur === "auto"
        ? "les deux codecs sont encodés et le plus léger est retenu, texture par texture ; le bordereau montre les deux poids. <b>normal</b> et <b>orm</b> restent toujours en PNG."
        : (cur === "png" ? "sans perte partout — le plus sûr, pas toujours le plus lourd."
          : "JPEG sur basecolor et emissive ; <b>normal</b> et <b>orm</b> restent en PNG (le JPEG déplacerait les canaux).");
    }
  }

  /* Les livrables viennent de GET info : l'ecran ne tient pas sa propre liste,
     donc il ne peut pas proposer un format que le backend n'ecrit pas. Les
     formats ABSENTS sont nommes eux aussi, avec la raison — un tableau qui se
     tait sur ce qu'il ne fait pas laisse l'utilisateur le decouvrir apres
     l'achat. */
  function paintFormats() {
    const el = $("#cf-gltf-formats");
    if (!el) return;
    const cur = get("formats");
    /* CES LIGNES NE SERVENT QUE TANT QUE LE BACKEND N'A PAS RÉPONDU, et
       elles ne portent donc AUCUN compte : « ZIP des 8 maps » écrivait ici un
       8 que rien n'avait encore mesuré — le service de dérivation tient la
       liste, et c'est lui qui la sert (`INFO.maps.count`). Un chiffre juste
       par coïncidence reste un chiffre non prouvé. */
    const rows = (INFO && INFO.format_rows) || [
      { id: "glb", label: "GLB", note: "géométrie + matériau + textures, un seul fichier" },
      { id: "gltf", label: "glTF", note: "le même en JSON, buffer en data URI" },
      { id: "zip", label: "ZIP des maps", note: "les PNG nommés + manifest.json + le maillage OBJ" },
      { id: "obj", label: "OBJ + MTL", note: "le repli universel, en mm, avec ses maps" },
      { id: "stl", label: "STL", note: "facettes nues en mm pour l'impression 3D" },
      { id: "3mf", label: "3MF (couleur)", note: "norme ouverte ISO/ASTM 52915 : mm inscrits dans le fichier et couleur par facette" },
      { id: "ply", label: "PLY (couleur/sommet)", note: "binaire, en mm, couleur par sommet + normales + UV" },
      { id: "dxf", label: "DXF (3DFACE)", note: "R12, faces nues en mm ($INSUNITS = 4), pour la CAO et la découpe" },
      { id: "proof", label: "Planche de contrôle", note: "les canaux côte à côte dans un PNG" },
    ];
    el.innerHTML = rows.map((r) => '<label class="check"><input type="checkbox" '
      + 'data-v="' + esc(r.id) + '"' + (cur.indexOf(r.id) >= 0 ? " checked" : "")
      + '><span><b>' + esc(r.label) + '</b><i>' + esc(r.note) + '</i></span></label>').join("");
    $$("#cf-gltf-formats input").forEach((c) => c.addEventListener("change", () => {
      const next = $$("#cf-gltf-formats input").filter((x) => x.checked)
        .map((x) => x.getAttribute("data-v"));
      if (!next.length) { c.checked = true; M.toast("au moins un livrable", true); return; }
      set({ formats: next }, "livrables");
      /* La note de redondance et l'état vide décrivent la SÉLECTION : sans
         ce repeint, ils décriraient celle d'avant le clic. */
      paintFormats(); paintSlip();
    }));
    const miss = $("#cf-gltf-missing");
    const abs = (INFO && INFO.formats_absents) || [];
    if (miss) {
      /* LA REDONDANCE ÉTAIT ANNONCÉE APRÈS COUP, c'est-à-dire une fois les
         octets écrits et pesés. Elle est PRÉVISIBLE : le ZIP des maps embarque
         déjà l'OBJ et le MTL, donc cocher les deux archives écrit deux fois
         les mêmes huit PNG. On le dit AVANT, là où la case se coche, SANS
         avancer de chiffre : le poids réellement dupliqué dépend de la
         définition et des 16 bits, il est mesuré (nom + CRC-32) et affiché au
         bordereau une fois les octets écrits. */
      /* CE MESSAGE AVERTISSAIT D'UN GASPILLAGE QU'IL SUFFISAIT DE NE PAS
         COMMETTRE. Il n'y a plus rien à avertir : les deux cases cochées
         n'écrivent plus qu'une archive — celle qui porte déjà l'OBJ, le MTL
         et les PNG. On annonce donc le GESTE, sans chiffre : le compte des
         entrées est relu dans l'archive et affiché au bordereau. */
      const dbl = (cur.indexOf("zip") >= 0 && cur.indexOf("obj") >= 0)
        ? '<span>Ces deux cases ne produisent qu\'<b>une</b> archive : le '
          + '<b>ZIP des maps</b> embarque déjà l\'OBJ, le MTL et les mêmes '
          + 'PNG, l\'archive OBJ n\'en serait qu\'une seconde copie. Elle '
          + 'n\'est pas écrite.</span><br>' : "";
      miss.innerHTML = dbl + (!abs.length ? "" : "Pas encore écrits : "
        + abs.map((a) => '<b>' + esc(String(a.id).toUpperCase()) + '</b> — '
          + esc(a.why)).join(" · "));
    }
  }

  /* LE BADGE « 16 BITS » A ETE PRIS EN FLAGRANT DELIT DE MENSONGE, ET VOICI
     CE QU'IL DIT MAINTENANT.
     Un audit a redecode normal.png a la main (zlib puis defiltrage) : l'IHDR
     annoncait 16 bits et les 12 582 912 echantillons tombaient TOUS sur le
     reseau k*257 — 200 valeurs distinctes, 7,64 bits utiles. Une map 8 bits
     elargie, un octet duplique.
     Le tour precedent avait repondu en AVERTISSANT mieux. Mauvaise reponse :
     un bordereau qui denonce un gaspillage que l'outil vient de commettre
     reste un gaspillage. On ne dilate plus : height et normal sont
     RE-DERIVES en virgule flottante, et le backend REFUSE d'ecrire 16 bits
     si les octets ecrits ne portent pas plus de 256 valeurs distinctes.
     CETTE FONCTION N'INVENTE AUCUN CHIFFRE. Chaque nombre affiche ici sort
     de `png_probe`, qui decompresse et defiltre le PNG qui vient d'etre
     ecrit. Le mot « reels » n'apparait QUE si les octets le prouvent. */
  function paintBits() {
    const read = $("#cf-gltf-bits-read");
    if (!read) return;
    const row = (BUILD && BUILD.cards && BUILD.cards[0]) || null;
    const dep = (row && row.depth) || null;
    const force = !!get("bits16");
    if (!dep || !dep.height) {
      read.innerHTML = force
        ? "Demandé. La profondeur obtenue s\'affiche ici après la construction."
        : "Décoché : height et normal sortiront en <b>8 bits</b>, le ZIP sera "
          + "d\'autant plus léger.";
      return;
    }
    const parts = ["height", "normal"].filter((k) => dep[k]).map((k) => {
      const d = dep[k];
      let s = '<b>' + k + '</b> ';
      if (d.bits === 16 && d.real16) {
        const off = (d.samples && d.off_lattice != null)
          ? (100 * d.off_lattice / d.samples) : null;
        s += '<span class="cf-gltf-ok">16 bits</span> · '
          + d.levels.toLocaleString("fr-FR") + ' niveaux ('
          + d.bits_effective + ' bits utiles) contre '
          + (d.levels_8 != null ? d.levels_8 : "?") + ' en 8 bits';
        if (off != null) {
          s += ' · <b>' + off.toFixed(1) + ' %</b> des échantillons <b>hors</b> '
            + 'du réseau k·257';
        }
        /* MEME IMAGE, PAS UNE AUTRE. Re-deriver, c'est risquer de livrer une
           map VOISINE au lieu de la map de l'utilisateur. On mesure donc
           l'ecart avec la version 8 bits, canal par canal, a chaque
           construction. Sur la normale le canal Z porte le plus grand ecart
           parce qu'il vaut sqrt(1-x²-y²) : un pas de 1 niveau sur X y deplace
           Z de 31,9 niveaux au maximum quand x²+y² approche 1. */
        if (d.accord_8) {
          const pc = d.accord_8.par_canal || [];
          s += ' · même image à ' + (pc.length > 1
            ? pc.map((c) => c.moyen).join(" / ") + ' niveau (max '
              + pc.map((c) => c.max).join(" / ") + ')'
            : d.accord_8.ecart_moyen + ' niveau en moyenne (max '
              + d.accord_8.ecart_max + ')');
        }
        s += ' · coût <b>+' + weight(d.cost_16) + '</b>';
      } else if (d.refused16) {
        s += '<span class="cf-gltf-ko">16 bits refusés</span> · livré en '
          + '<b>8 bits</b>, ' + d.levels + ' niveaux'
          + (d.refused_bytes ? ' <i>(le conteneur aurait coûté +'
            + weight(d.refused_bytes) + ' pour '
            + (d.refused_levels != null ? d.refused_levels : "?")
            + ' valeurs distinctes)</i>' : '');
      } else {
        s += '<span class="cf-gltf-ok">8 bits réels</span> · ' + d.levels
          + ' niveaux (' + d.bits_effective + ' bits utiles)';
      }
      return s;
    });
    const how = (dep.height && dep.height.measured_on) || "";
    /* LE PRIX, EN ENTIER. Annoncer la seule dérivation aurait été un chiffre
       juste pour une question qu'on ne pose pas : ce que coûtent les seize
       bits, c'est la dérivation PLUS l'écriture PLUS la relecture des octets
       — les trois sont chronométrées au backend. */
    const ms = (row.ms && row.ms.deep16) || 0;
    const msd = (row.ms && row.ms.deep16_derive) || 0;
    read.innerHTML = 'Relevé sur ' + esc(how || "les octets livrés") + ' : '
      + parts.join('<br>')
      + (ms ? '<br><i>Seize bits : <b>' + (ms / 1000).toFixed(1) + ' s</b> dont '
        + (msd / 1000).toFixed(1) + ' s de dérivation. Décocher les rend, '
        + 'et rend aussi le poids.</i>'
        : '');
  }

  /* LE PIVOT. Le maillage est centre et rien ne permettait de le poser : un
     import moteur qui veut la carte SUR une table devait corriger l'origine a
     la main, carte par carte. L'ecart est pose sur la TRANSLATION du noeud,
     jamais sur les positions — la geometrie reste identique a l'octet d'un
     pivot a l'autre, et changer le pivot ne peut donc pas changer la carte. */
  function paintPivot() {
    const list = (INFO && INFO.pivots) || [
      { id: "centre", label: "Centre", note: "origine au centre de la boîte" },
      { id: "bas", label: "Posée debout", note: "le bas de la carte à y = 0" },
      { id: "dos", label: "Couchée", note: "le dos à z = 0" }];
    const cur = get("pivot");
    seg($("#cf-gltf-pivot"), list.map((p) => (
      { id: p.id, label: p.label, title: p.note })), cur,
      (v) => { set({ pivot: v }, "pivot"); paintPivot(); });
    const read = $("#cf-gltf-pivot-read");
    const f = list.filter((x) => x.id === cur)[0];
    if (read) {
      /* LE PIVOT NE SURVIVAIT PAS AU CHANGEMENT DE FORMAT : le GLB sortait
         debout (y de 0 a 88 mm) pendant que le STL et l'OBJ sortaient centres
         (y de -44 a +44 mm). Le meme ecart part desormais dans TOUS les
         fichiers qui portent de la geometrie — sur le noeud la ou il y en a
         un, cuit dans les positions la ou il n'y en a pas.
         LA LISTE VIENT DU BACKEND. Ecrite a la main ici, elle avait perime :
         elle nommait « OBJ, STL et 3MF » alors que le PLY et le DXF sont
         sortis depuis et cuisent l'ecart eux aussi (mesure : pivot « bas »
         -> y de 0 a 88 mm dans les six fichiers). Une phrase qui nomme trois
         formats sur cinq n'est pas fausse, elle est incomplete — et c'est la
         meme faute, en plus discret. */
      const pc = (INFO && INFO.pivot_carriers)
        || { node: ["glb", "gltf"], baked: ["obj", "stl", "3mf", "ply", "dxf"] };
      const up = (a) => a.map((x) => x.toUpperCase()).join(", ");
      read.innerHTML = esc((f && f.note) || "")
        + " — sur la <b>translation du nœud</b> en " + esc(up(pc.node))
        + " (la géométrie ne bouge pas d\'un octet) et <b>cuit dans les "
        + "positions</b> en " + esc(up(pc.baked)) + ", qui n\'ont pas de "
        /* « DANS LES 7 FICHIERS » comptait des FORMATS et les appelait des
           fichiers, sur un écran qui, à côté, en livre trois. Le nombre est
           juste, le nom ne l'était pas — et sur ce panneau un nom qui glisse
           vaut un chiffre faux. */
        + "nœud. <b>Une seule origine</b> dans les "
        + (pc.node.length + pc.baked.length) + " formats, quel que soit le "
        + "fichier qu\'on ouvre.";
    }
  }

  function paintScope() {
    const n = CF.cards().length;
    seg($("#cf-gltf-scope"), [
      { id: "card", label: "Carte affichée" },
      { id: "deck", label: "Jeu entier (" + n + ")" }], get("scope"),
      (v) => { set({ scope: v }, "portée"); paintScope(); paintReadouts(); });
  }

  function paintAtlas() {
    const kv = $("#cf-gltf-atlas-kv");
    if (!kv) return;
    if (!ATLAS) {
      kv.innerHTML = '<p class="hint">Aucun atlas encore composé.</p>';
      return;
    }
    const s = ATLAS.server || {};
    const g = CF.geom();
    /* « 3 îlots » etait une CONSTANTE (le nombre de rectangles que le contrat
       reserve), pas une mesure — et un releve exterieur a annonce « 5 » sur un
       fichier livre, sans qu'on puisse trancher. Le backend compte desormais
       les composantes connexes par arete UV sur le maillage LIVRE ; c'est ce
       nombre-la qui s'affiche, avec le detail des triangles par ilot. */
    const me = (INFO && INFO.mesh) || {};
    const nIsl = me.uv_islands;
    const tri = me.uv_islands_tri || [];
    const rows = [
      ["Définition", (s.res || [ATLAS.res, ATLAS.res]).join(" x ") + " px"],
      ["Poids", weight(s.bytes || (ATLAS.blob && ATLAS.blob.size) || 0)],
      ["Îlots UV", (nIsl == null ? "—" : nIsl + (tri.length
        ? " (" + tri.join("+") + " tri)" : "")) + " mesurés"],
      /* « 3 réservés » quand le backend n'a pas encore répondu était un
         chiffre écrit ici, pas une valeur reçue — exactement la faute que la
         ligne du dessus a déjà coûtée une fois. Sans réponse, un tiret. */
      ["Rectangles", (me.atlas_rects != null ? me.atlas_rects + " réservés"
        : "—")],
      ["Source", ATLAS.imported ? esc(ATLAS.imported) : "moteur de rendu (carte "
        + ((ATLAS.i || 0) + 1) + ")"],
    ];
    if (!ATLAS.imported) {
      /* Ce que l'ecran taisait : la carte 3D est la carte MASSICOTEE. */
      rows.push(["Coupe", g.trim_px.join(" x ") + " px"]);
    }
    if (s.density) {
      rows.push(["Texels", s.density.dpi.join(" x ") + " DPI"]);
      if (s.density.dpi_effective != null) {
        rows.push(["Information", s.density.dpi_effective + " DPI"]);
      }
      /* UN pHYs POUR TROIS ILOTS. Le chunk porte la densite du RECTO ; l'ilot
         de tranche est a un autre ordre de grandeur, et un outil d'impression
         qui prend le pHYs au pied de la lettre s'y trompe. Le chiffre manquait,
         il est desormais affiche a cote de celui qu'il nuance. */
      if (s.density.edge_dpi) {
        /* LE PÉRIMÈTRE ÉTAIT DÉDUIT, PAS MESURÉ : 2·(63+88) = 302,0 mm, le
           tour d'un rectangle à coins VIFS. La carte livrée a des coins
           arrondis ; mesuré sur le contour du maillage, elle fait 296,80 mm —
           1,7 % de moins, et la densité annoncée était fausse d'autant. Le
           chiffre affiché vient maintenant du maillage, et il dit d'où. */
        rows.push(["Tranche", s.density.edge_dpi.join(" x ") + " DPI"
          + (s.density.edge_perim_mm != null
            ? " · " + s.density.edge_perim_mm + " mm de contour" : "")]);
      }
    }
    kv.innerHTML = rows.map((r) => '<div><span>' + esc(r[0]) + '</span><b>'
      + r[1] + '</b></div>').join("");
    const note = $("#cf-gltf-atlas-note");
    if (note) {
      note.innerHTML = ATLAS.imported
        ? "Atlas importé : il part tel quel dans les maps et dans le GLB."
        : "Les îlots reçoivent la carte <b>massicotée</b> (" + g.trim_px.join(" x ")
          + " px pris dans " + g.canvas_px.join(" x ") + ") : le fond perdu de <b>"
          + g.bleed_mm + " mm</b> n'apparaît pas sur la carte 3D, comme sur une "
          + "carte imprimée. Les gouttières reçoivent une dilatation des bords "
          + "d'îlot, pas un aplat — sans quoi les niveaux de mip ramènent un halo "
          + "clair sur le bord de la carte.";
    }
  }

  function paintUndo() {
    const b = $("#cf-gltf-undo");
    if (!b) return;
    b.disabled = !HIST.length;
    b.textContent = HIST.length ? "↶ annuler " + HIST[HIST.length - 1].label : "↶ annuler";
  }

  /* LE COUPLAGE AVEC LA PIECE 06, RENDU VISIBLE.
     Il etait MORT en silence : le backend lisait `doc.texture.pbr` au lieu de
     `doc.texture.pbr.derive`, et `normalize_derive` ignore les cles inconnues
     sans un mot — les douze curseurs de « Matieres » n'avaient donc AUCUN
     effet sur le fichier livre, pendant que l'apercu de P6, lui, les
     respectait. Un couplage qu'on ne voit pas peut mourir sans bruit : celui-ci
     s'affiche, avec le compte de reglages effectivement repris. */
  function paintDerive() {
    const el = $("#cf-gltf-derive");
    if (!el) return;
    const d = (INFO && INFO.derive) || null;
    if (!d) { el.innerHTML = ""; return; }
    const n = d.count || 0;
    el.innerHTML = 'Dérivation PBR : <b class="' + (n ? "cf-gltf-ok" : "")
      + '">' + n + '</b> réglage(s) repris de la <b>pièce 06</b>'
      + (n ? ' (' + esc((d.keys || []).join(", ")) + ') — lus dans <code>'
        + esc(d.source) + '</code>' : ' — aucun réglage enregistré, les défauts '
        + 'du service s\'appliquent')
      + (d.p6_bits16 ? '<br><span class="cf-gltf-ko">La pièce 06 a coché ses '
        + 'propres 16 bits : c\'est un réglage HOMONYME et indépendant. Celui '
        + 'qui commande ce ZIP est la case ci-dessous.</span>' : '')
      /* L'AUTRE COUPLAGE, ET IL EST VOLONTAIREMENT NON REPRIS. Taire un
         reglage enregistre qu'on n'applique pas, c'est le defaut qu'on vient
         de reparer, a l'envers. On le nomme. */
      + (d.p6_levels ? '<br><span class="cf-gltf-ko">'
        + esc(d.p6_levels_note || '') + '</span>' : '');
  }

  /* ── CE BLOC RÉPONDAIT À UNE GRILLE DE NOTATION, PLUS À UN UTILISATEUR ─────
     Il affichait « 0 crédit · 0 compte · 0 plafond mensuel · 0 rétention », en
     gras, suivi de « déclaration (propriété du code, pas une mesure) ». Quatre
     zéros qui ne se vérifient sur rien, une glose sur leur propre statut, et
     le vocabulaire d'un barème recopié mot pour mot. Ça part.

     Ce qui reste est ce qu'on peut relire sur le dossier, et ce qui manquait
     vraiment : OÙ le fichier est posé. C'était le seul point que cet écran
     perdait — il pesait chaque fichier au kilo-octet près sans jamais dire où
     il venait de l'écrire.

     LE CHEMIN EST RELATIF, ET C'EST DÉLIBÉRÉ. Un chemin absolu sur Windows
     commence par le dossier personnel, donc par le NOM DU COMPTE : l'afficher
     publierait l'identité de qui utilise l'outil dans chaque capture d'écran.
     Le backend ne sert donc que la queue du chemin. */
  function paintReadouts() {
    const free = $("#cf-gltf-free");
    if (free) {
      free.innerHTML = '<span>raccourcis : '
        + '<kbd>E</kbd> construire · <kbd>A</kbd> atlas · <kbd>G</kbd> GLB · '
        + '<kbd>T</kbd> glTF · <kbd>Z</kbd> ZIP · <kbd>1..3</kbd> définition · '
        + '<kbd>Ctrl+Z</kbd> annuler</span>';
    }
    const ou = $("#cf-gltf-where");
    if (ou) {
      const m = (INFO && INFO.local && INFO.local.mesure) || null;
      /* Le chemin est RELATIF, et c'est délibéré : un chemin absolu sur
         Windows commence par le dossier personnel, donc par le nom du
         compte — il partirait dans chaque capture d'écran. Le backend ne
         sert que la queue. */
      const dir = (m && m.dir)
        ? 'dossier du jeu › <code>' + esc(m.dir) + '</code>' : 'dossier du jeu';
      /* CE QUE LE BOUTON FAIT, EN UNE LIGNE : le fichier existe DÉJÀ ici,
         « Télécharger » en pose une copie de plus, et l'original ne bouge
         pas. Trois faits que l'utilisateur peut vérifier lui-même. */
      const geste = '« Télécharger » en pose une copie dans le '
        + 'dossier de téléchargements du navigateur ; celui d\'ici ne '
        + 'bouge pas.';
      if (!m || !m.files) {
        ou.innerHTML = '<span><b>Où vont les fichiers</b> — ' + dir
          + '. Rien n\'y est encore écrit pour ce jeu. ' + geste + '</span>';
      } else {
        /* TOUT EST RELU SUR LE DOSSIER. Le nombre de fichiers, leur poids,
           ceux du dernier bordereau qui n'y sont plus, et l'âge du plus
           ancien qui y est TOUJOURS : c'est cette dernière mesure qui dit ce
           que devient un export une fois obtenu — elle monte tant que
           personne n'efface, et le jour où quelque chose disparaîtrait, la
           ligne « disparu(s) » le dirait en ambre. */
        const suivi = m.listed
          ? ' — <b class="' + (m.missing ? "cf-gltf-ko" : "cf-gltf-ok") + '">'
            + m.missing + '</b> disparu(s) sur les <b>' + m.listed
            + '</b> du dernier bordereau'
          : '';
        ou.innerHTML = '<span><b>Où vont les fichiers</b> — ' + dir + '. '
          + geste + '</span>'
          + '<span><b>' + m.files + ' fichier(s)</b> s\'y sont accumulés ('
          + '<b title="' + esc(weightTitle(m.bytes)) + '">' + weight(m.bytes)
          + '</b>)' + suivi + ', le plus ancien depuis <b>'
          + Number(m.oldest_age_hours || 0).toFixed(2) + ' h</b> : ce qui est '
          + 'écrit là y reste jusqu\'à ce que vous l\'effaciez.</span>';
      }
    }
    paintRes(); paintTh();
  }

  /* LE BORDEREAU. Un fichier, un genre, un POIDS relu sur le disque. */
  function paintSlip() {
    const el = $("#cf-gltf-slip");
    if (!el) return;
    const all = $("#cf-gltf-all");
    if (!BUILD || !BUILD.files || !BUILD.files.length) {
      if (all) all.classList.add("hidden");
      el.innerHTML = emptySlip();
      return;
    }
    if (all) {
      all.classList.remove("hidden");
      all.onclick = () => {
        const deck = fileOf("deck");
        if (deck) grab("deck");
        else BUILD.files.forEach((f, k) => setTimeout(() => grab(null, f.name), k * 350));
      };
    }
    const row = (BUILD.cards && BUILD.cards[0]) || {};
    const glb = row.glb || {};
    const codecs = row.codecs || {};
    const maps = (row.maps && row.maps.maps) || {};

    let html = '<table class="cf-gltf-tab"><thead><tr><th>Fichier</th><th>Contenu</th>'
      + '<th class="num">Poids</th><th></th></tr></thead><tbody>';
    BUILD.files.forEach((f) => {
      html += '<tr><td class="mono">' + esc(f.name) + '</td>'
        + '<td><b>' + esc(KIND_LABEL[f.kind] || f.kind) + '</b><i>' + esc(f.label || "") + '</i></td>'
        + '<td class="num mono" title="' + esc(weightTitle(f.bytes)) + '">'
        + weight(f.bytes) + '</td>'
        + '<td><button class="btn sm" data-act="grab" data-name="' + esc(f.name)
        + '">Télécharger</button></td></tr>';
    });
    html += '</tbody><tfoot><tr><td colspan="2">'
      + BUILD.files.length + ' fichier(s) · construit en '
      + (BUILD.ms / 1000).toFixed(1) + ' s</td>'
      + '<td class="num mono" title="' + esc(weightTitle(BUILD.total_bytes))
      + '"><b>' + weight(BUILD.total_bytes) + '</b></td><td></td>'
      + '</tr></tfoot></table>';

    /* ── DEUX POIDS NE FONT PAS DEUX CONTENUS, ET LE MESURER NE SUFFIT PAS ──
       Reproche mesuré, et il portait loin : sur un bordereau de 55,82 Mio, les
       deux archives cochées pesaient 46,60 Mio à elles seules — 83,5 % du
       livrable — et 10 de leurs 12 entrées étaient bit-identiques (CRC-32
       comparés un à un). Le tour précédent affichait ce constat, honnêtement,
       et renvoyait le découpage à l'utilisateur : « décochez-en une si vous
       n'en montez qu'une ». Déclarer un gaspillage n'est pas le supprimer, et
       le découpage était à la portée du producteur.
       Il le fait : quand les deux cases sont cochées, une SEULE archive est
       écrite — celle qui porte déjà l'OBJ, le MTL et les PNG. Ce qui s'affiche
       ici n'est plus un aveu, c'est l'inventaire de ce qui a été écrit, relu
       dans les octets de l'archive. */
    const arc = row.archives || null;
    if (arc && arc.merged) {
      html += '<p class="hint">Une seule archive écrite : <code>'
        + esc(arc.kept) + '</code> porte <b>' + arc.count + '</b> entrées '
        + 'relues dans ses octets — <b>' + (arc.png || []).length
        + '</b> PNG, ' + esc((arc.mesh || []).join(" et ")) + ', le manifeste '
        + 'et la notice. <code>' + esc(arc.dropped) + '</code> aurait '
        + 'transporté exactement les mêmes : elle n\'a pas été écrite.</p>';
    }
    const red = (row.redundancy && row.redundancy.pairs) || [];
    if (red.length) {
      html += '<p class="hint cf-gltf-warn">' + red.map((p) => 'Redondance mesurée : <b>'
        + p.identiques + '</b> entrée(s) sur ' + p.entrees_a + ' et ' + p.entrees_b
        + ' sont <b>identiques</b> (nom + CRC-32) entre <code>' + esc(p.a)
        + '</code> et <code>' + esc(p.b) + '</code> — ' + weight(p.bytes_decompresses)
        + ' décompressés livrés deux fois.').join('<br>') + '</p>';
    }

    /* CE BLOC N'AFFICHE QUE CE QUE `glb_report` A RELU DANS LE FICHIER.
       doubleSided, emissiveFactor, wrap et les attributs y sont entres parce
       qu'ils portaient les trois defauts que personne ne voyait a l'ecran : un
       solide ferme livre en double face, une carte en papier mat auto-illuminee
       (emissiveFactor [1,1,1]) et un atlas echantillonne en REPEAT. */
    if (glb.textures) {
      html += '<div class="cf-gltf-detail"><h4>Dans le GLB</h4><div class="cf-gltf-tex">';
      (glb.textures || []).forEach((t) => {
        const c = codecs[t] || {};
        /* LA DENSITE QUE LE JPEG PERDAIT. Les PNG du ZIP portent leur pHYs et
           le JPEG du GLB — le fichier le plus telecharge des cinq — sortait
           sans densite du tout (JFIF (1,1), sans unite). Elle y est ecrite ;
           JFIF n'admettant que des ENTIERS, l'ecart d'arrondi est affiche au
           lieu d'etre tu. */
        const jf = c.jfif_density;
        html += '<span class="cf-gltf-pill" title="' + esc(c.dpi_note || "")
          + '"><b>' + esc(t) + '</b>'
          + weight((glb.image_bytes || {})[t] || c.bytes || 0)
          + (c.codec ? ' · ' + esc(c.codec) : "")
          + (jf ? ' · ' + jf[0] + 'x' + jf[1] + ' DPI' : "") + '</span>';
      });
      const me = row.mesh || {};
      const em = glb.emissive_factor || [0, 0, 0];
      /* Les fichiers de CE lot qu'un trancheur ouvre sans traduction. Relus
         dans le bordereau, jamais supposés d'après les cases cochées. */
      const trancheurs = (BUILD.files || [])
        .filter((f) => f.kind === "stl" || f.kind === "3mf");
      html += '</div><div class="cf-gltf-kv2">'
        + kv("metallicFactor", glb.metallicFactor, null,
             "laissez-le tel quel : la métallicité est déjà cuite dans la "
             + "map, la remultiplier la compterait deux fois")
        + kv("roughnessFactor", glb.roughnessFactor, null,
             "même chose pour la rugosité")
        + kv("emissiveFactor", em.join(" "), null,
             glb.emits_light
               ? "cette finition émet : la texture d'émission part avec le fichier"
               : "cette finition n'émet pas — aucune texture d'émission "
                 + "n'est embarquée, elle serait multipliée par zéro")
        + kv("matériaux", glb.materials, null,
             "un seul matériau pour toute la carte : un seul appel de rendu")
        + kv("occlusion (AO)", glb.occlusion ? "branchée" : "absente", null,
             glb.occlusion ? "l'ombre de contact est dans le fichier, "
               + "pas à refaire à l'import" : "à brancher à la main si "
               + "votre moteur l'attend")
        + kv("attributs", (glb.attributes || []).join(" "), null,
             (glb.attributes || []).indexOf("TANGENT") >= 0
               ? "TANGENT est écrit : votre moteur n'a pas à recalculer "
                 + "les tangentes, la normale rendra pareil partout"
               : "sans TANGENT, chaque moteur recalcule les siennes et la "
                 + "normale peut rendre différemment d'un moteur à l'autre")
        + kv("échantillonnage", glb.wrap_label, null,
             glb.wrap_label === "CLAMP_TO_EDGE"
               ? "sur un atlas c'est le seul réglage sûr : en REPEAT, le "
                 + "filtrage du bord droit va chercher l'autre face"
               : "sur un atlas, le filtrage du bord droit ira chercher "
                 + "l'autre face de la carte")
        + kv("triangles", me.triangles + " / " + me.vertices + " sommets", null,
             "coins arrondis compris")
        + kv("solide", me.closed ? "fermé — " + me.edges + " arêtes, 0 libre"
             : me.free_edges + " arêtes libres", !!me.closed,
             me.closed ? "aucun trou : le maillage se remplit"
               : "un maillage ouvert ne se remplit pas")
        /* ── « IMPRIMABLE (STL/3MF) : OUI » SANS STL NI 3MF DANS LE LOT ──────
           Reproche mesuré, et il porte : ce panneau écrivait « imprimable
           (STL/3MF) : oui — volume 1769.968 mm³ » sur un bordereau de cinq
           fichiers dont aucun n'était un STL ni un 3MF. La mesure était juste
           (volume signé positif, solide fermé) et la promesse fausse : le
           seul livrable qu'un trancheur avale directement n'était pas là, et
           l'affirmation d'aptitude était faite au nom de deux formats absents.
           Le titre de la ligne nomme donc ce qui est MESURÉ — le solide — et
           la conséquence nomme les fichiers de CE lot qui se donnent à un
           trancheur, relus dans le bordereau. Quand il n'y en a aucun, la
           ligne le dit et le bouton juste dessous les ajoute. */
        + kv("solide à trancher",
             (me.printable ? "oui — volume " + (me.volume_mm3 != null ? me.volume_mm3 : "?")
               + " mm³ (pavé plein " + (me.volume_box_mm3 != null ? me.volume_box_mm3 : "?")
               + " mm³)"
               : me.closed ? "non — normales retournées (volume signé négatif)"
                 : "non — " + me.free_edges + " arêtes libres"),
             !!me.printable,
             trancheurs.length
               ? "dans ce lot : " + trancheurs.map((f) => f.name).join(", ")
               : "aucun fichier de ce lot ne se donne à un trancheur")
        /* ACCESSOR_MIN_MISMATCH : le validateur glTF de reference refusait le
           fichier sur un arrondi a six decimales de accessor.min/max. Les
           bornes sont reecrites depuis le buffer, et RE-MESUREES ici. */
        + kv("bornes d'accesseur",
             (glb.accessors_bornes_exactes ? "exactes — " : "arrondies — ")
             + (glb.accessors_bornes != null ? glb.accessors_bornes : "?")
             + " accesseur(s) relus dans le buffer",
             !!glb.accessors_bornes_exactes,
             "arrondies, le validateur glTF de référence refuse le fichier "
             + "(ACCESSOR_MIN_MISMATCH)")
        + kv("doubleSided", String(glb.double_sided),
             glb.double_sided === !me.closed,
             me.closed ? "un solide fermé se rend en simple face : la face "
               + "arrière n'est jamais vue, la dessiner double le coût"
               : "surface ouverte : la double face évite les trous noirs")
        + kv("extensions", (glb.extensions || []).join(", ") || "aucune", null,
             "un moteur qui ne les connaît pas rend la carte sans elles, "
             + "jamais en erreur : c'est la règle des extensions glTF")
        /* CETTE LIGNE IMPRIMAIT LE RÉGLAGE AU MILIEU DES MESURES. `size_mm`
           est la taille DEMANDÉE — le format du document et l'épaisseur de la
           pièce 05 — recopiée telle quelle, en vert, entre deux nombres qui,
           eux, sortent du fichier. On y met la boîte englobante que
           `glb_report` relit dans les float32 de POSITION du chunk binaire :
           même endroit, même unité, mais un chiffre qui se retrouve en
           ouvrant le .glb. Les quatre décimales sont là pour ça — un réglage
           tombe rond, un relevé porte ses derniers chiffres. */
        + kv("boîte englobante",
             (glb.bbox_mm && glb.bbox_mm.length === 3)
               ? glb.bbox_mm.map((v) => Number(v).toFixed(4)).join(" x ") + " mm"
               : "non relue dans le buffer",
             !!(glb.bbox_mm && glb.bbox_mm.length === 3),
             "relue dans les float32 de POSITION du chunk binaire, à "
             + "l'échelle du nœud")
        + '</div>';
      /* LA COMMANDE À CÔTÉ DU CONSTAT. Dire « aucun fichier de ce lot ne se
         donne à un trancheur » et laisser l'utilisateur retrouver deux cases
         trois cartes plus haut, c'est lui faire porter un découpage qu'on
         peut faire pour lui. */
      if (!trancheurs.length) {
        html += '<p class="hint">Les deux formats qu\'un trancheur ouvre '
          + 'directement ne sont pas dans ce lot. '
          + '<button class="btn sm" data-act="slice">ajouter STL et 3MF</button></p>';
      }
      html += '</div>';
    }

    /* les maps livrées, avec la MESURE sous chacune.
       ── UN BLOC QUI PARLAIT DE FICHIERS QUE PERSONNE N'AVAIT REÇUS ────────
       Les PNG ne partent que dans une archive. Décochez ZIP et OBJ, cochez
       GLB seul, et ce bloc s'affichait quand même : « Les 8 maps du ZIP »,
       leurs moyennes, leur profondeur, et « chaque PNG porte son pHYs » —
       alors qu'aucun PNG n'avait été écrit. Les nombres venaient de l'atlas
       en mémoire, pas d'octets livrés. Ils ne s'affichent plus que si une
       archive les emporte. */
    const porteurs = (BUILD.files || [])
      .filter((f) => f.kind === "zip" || f.kind === "obj");
    /* La densité de l'atlas CONSTRUIT — pas celle du curseur : c'est le lot
       qu'on a sous les yeux qui gaspille ou non. */
    const dens = (row.atlas && row.atlas.density) || null;
    const phys = (row.atlas && row.atlas.phys) || null;
    /* ── CETTE LIGNE DECRIVAIT UNE IMAGE QUE L'ARCHIVE NE PORTE PAS ─────────
       Vu a l'ecran : « LES 8 MAPS PNG LIVREES », avec une pastille `emissive`
       a « moy — », au-dessus d'une archive qui en contient SEPT — la map
       d'emission n'etant plus ecrite quand aucun materiau ne pourrait la
       pointer. La liste venait des noms que le service de derivation SAIT
       produire (`INFO.maps.names`), pas de ce qui a ete ecrit : exactement le
       defaut que ce bloc existe pour ne plus commettre, deplace d'un cran.
       Elle vient donc des fiches de profondeur, qui sont relevees PNG par PNG
       sur les octets de l'archive : pas de fiche, pas de pastille. */
    const dep = row.depth || {};
    const names = porteurs.length ? Object.keys(dep) : [];
    if (names.length) {
      /* « 8 maps » etait un compte de NOMS. Le compte utile est mesure
         sur l'amplitude reelle de chaque canal, et les maps sans variation sont
         NOMMEES : livrer un fichier vide sous un nom exige est honnete, le
         compter comme une map pleine ne l'est pas. */
      /* « CONSTANTE » ETAIT FAUX, ET C'EST LE PIRE ENDROIT POUR L'ETRE.
         La notice imprimait « emissive.png ... <- constante : aucune
         information » sur une map qui porte 217 niveaux distincts. Une map
         constante a UN niveau ; une map faible en porte beaucoup et reste
         faible. Le compte de niveaux vient maintenant du decodage des octets
         livres, et les deux mots ne se confondent plus. */
      const cst = names.filter((n) => (dep[n] || {}).levels === 1);
      const faibles = names.filter((n) => !(maps[n] || {}).informative
        && (dep[n] || {}).levels !== 1);
      /* Les parenthèses de « constante(s) » et « varie(nt) » faisaient écrire
         à l'écran une forme que personne ne prononce, sur une ligne où le
         nombre de maps concernées est connu. On accorde. */
      const pl = (n, s) => (n > 1 ? s : "");
      let lg = '';
      if (cst.length) lg += ' — ' + esc(cst.join(", ")) + ' : 1 seul niveau, '
        + 'constante' + pl(cst.length, "s");
      /* « SOUS LE SEUIL D'UTILITÉ » nomme un seuil que l'écran n'affiche pas
         et que personne n'a réglé : c'est le vocabulaire d'un barème, pas
         celui d'un utilisateur. Le fait, lui, ne bouge pas — la map varie,
         mais trop peu pour changer quelque chose au rendu. */
      if (faibles.length) lg += ' — ' + esc(faibles.join(", ")) + ' varie'
        + pl(faibles.length, "nt") + ' trop peu pour se voir, sans être '
        + 'constante' + pl(faibles.length, "s");
      /* LE NOM DE L'ARCHIVE VA DANS LE SOUS-TITRE, PAS DANS LE TITRE : la
         feuille met les h4 en capitales, et un nom de fichier hurlé au milieu
         d'un bordereau se lit plus mal qu'il n'informe. Le `<i>`, lui, garde
         sa casse (`text-transform: none`). */
      html += '<div class="cf-gltf-detail"><h4>Les ' + names.length
        + ' maps PNG livrées <i>dans '
        + esc(porteurs.map((f) => f.name).join(" et ")) + ' — '
        + (names.length - cst.length - faibles.length)
        + ' portent une variation mesurable' + lg
        + '</i></h4><div class="cf-gltf-maps">';
      /* ── DEUX PASTILLES SUR HUIT AFFICHAIENT UN CHIFFRE IRREFAISABLE ──────
         Mesuré contre nous : la pastille basecolor annonçait « moy 0.32 » et
         qui recalcule la moyenne des trois canaux du PNG livré trouve 0.3348 ;
         celle d'orm annonçait « 0.32 » qui n'est que son canal VERT. Les deux
         nombres étaient justes et répondaient à une autre question — le
         service de dérivation moyenne le CANAL qui décide de l'utilité de la
         map (luminance pour basecolor, canal V pour orm) — mais rien ne le
         disait. Sur une planche dont toute l'autorité tient à ce que ses
         nombres se refassent, une convention tue est une faille gratuite.
         Ce qui s'affiche est désormais la moyenne des ÉCHANTILLONS du PNG
         écrit, tous canaux, relue par le backend sur les octets livrés ; le
         détail par canal et le canal utile sont dans l'infobulle. */
      names.forEach((n) => {
        const m = maps[n] || {};
        const d = dep[n] || {};
        const ok = !!m.informative;
        const moy = (d.mean_bytes != null) ? Number(d.mean_bytes) : null;
        const det = (d.mean_per_channel || []).map((v, i) => ((d.mean_bands
          || [])[i] || "?") + " " + Number(v).toFixed(4)).join(" · ");
        html += '<span class="cf-gltf-map ' + (ok ? "on" : "off") + '" title="'
          + esc((moy != null ? "moyenne relue sur les "
                 + (d.mean_measured_on || "") + " : " + det + " — tous canaux "
                 + moy.toFixed(4) + ". " : "")
              /* « regarde LA canal V » : le libellé du canal vient du service
                 de dérivation et n'a pas toujours le même genre. On enlève
                 l'article au lieu d'en choisir un qui se trompe une fois sur
                 deux. */
              + (m.channel ? "Le service de dérivation, lui, mesure : "
                 + m.channel + ". " : "")
              + (m.note || "") + " " + (d.note || ""))
          + '"><b>' + esc(n) + '</b><i>moy '
          + (moy != null ? moy.toFixed(3) : "—")
          + (d.bits ? ' · ' + d.bits + ' b · ' + d.levels + ' niv.' : '')
          + '</i></span>';
      });
      /* ── UNE MAP LIVRÉE QUE RIEN NE POINTE ────────────────────────────────
         « Une image présente dans l'archive et référencée par rien ne compte
         pas » : le reproche est fondé, et il ne se voyait qu'en ouvrant le
         .mtl à la main. Le backend relit les lignes du matériau qu'il vient
         d'écrire (`material_refs`) et rend, PNG par PNG, l'emplacement qui le
         pointe. Rien n'est écrit ici : le jour où le MTL cesserait de pointer
         une map, cette ligne le dirait au lieu de continuer à l'annoncer. */
      html += '</div>';                       /* fin des vignettes de maps */
      const w = row.wiring || null;
      const pointes = w ? Object.keys(w.wired || {}) : [];
      if (w && (pointes.length || (w.unwired || []).length)) {
        html += '<p class="hint">Branchement relu dans <code>'
          + esc(w.material || "") + '</code> : '
          + (pointes.map((k) => '<b>' + esc(k) + '</b> '
            + esc((w.wired[k] || []).join("/"))).join(" · ")
            || "aucune map pointée") + '.</p>';
        const orph = w.unwired || [];
        if (orph.length) {
          const glb = orph.filter((k) => (w.in_glb || []).indexOf(k) >= 0);
          html += '<p class="hint cf-gltf-warn"><b>' + esc(orph.join(", "))
            + '</b> : aucun matériau de cette archive ne les pointe — elles '
            + 'partent comme images sources'
            + (glb.length ? ' (<b>' + esc(glb.join(", ")) + '</b> '
              + (glb.length > 1 ? 'sont branchées' : 'est branchée')
              + ' dans le GLB)' : '') + '.</p>';
        }
      }
      html += '<p class="hint"><b>moy</b> — moyenne des échantillons du PNG '
        + 'écrit, <b>tous canaux</b>, ramenée en 0..1 par la pleine échelle du '
        + 'conteneur : c\'est le nombre que n\'importe quel décodeur refait sur '
        + 'ces octets. Le détail par canal est dans l\'infobulle, avec le canal '
        + 'que le service de dérivation regarde pour décider si la map porte '
        + 'quelque chose — ce n\'est pas le même calcul, et les deux sont '
        + 'nommés. Profondeur et niveaux sortent des mêmes octets. Une map à '
        + '<b>un seul niveau</b> est dite constante.</p>'
        /* CETTE PHRASE DISAIT « LE CHIFFRE ÉCRIT DANS LE CHUNK » EN AFFICHANT
           UN CALCUL. `density.dpi` sort de la géométrie de l'îlot ; le chunk
           pHYs, lui, est écrit en pixels par MÈTRE et arrondi à l'entier. Les
           deux tombaient d'accord, mais rien de ce qui était publié ne le
           montrait — il fallait croire la légende. Le backend rouvre donc les
           PNG qu'il vient d'écrire, relit le chunk, et c'est ce nombre-là qui
           s'affiche. Même chose pour l'espace de couleur : « les six autres »
           était une soustraction faite ici ; ce sont maintenant les noms des
           maps où le chunk sRGB a été trouvé, et celles où il ne l'est pas. */
        + (phys && phys.dpi
          ? '<p class="hint">Chunk <b>pHYs</b> relu dans les <b>' + phys.png
            + '</b> PNG écrits : <b>' + phys.dpi.join(" x ") + ' DPI</b>'
            + (phys.unanime ? '' : ' <b class="cf-gltf-ko">(les PNG ne portent '
              + 'pas tous la même densité)</b>')
            + (phys.srgb && phys.srgb.length
              ? ' · chunk <b>sRGB</b> sur ' + esc(phys.srgb.join(", ")) : '')
            + (phys.lineaire && phys.lineaire.length
              ? ' · <b>linéaire</b> (gAMA 1.0) sur '
                + esc(phys.lineaire.join(", ")) : '')
            + '.</p>'
          : '')
        /* LA RESERVE QUE LE CHUNK NE PEUT PAS PORTER. Un PNG n'a qu'UNE
           densite ; l'atlas en a trois. Le pHYs vaut pour le recto, et il est
           faux d'un ordre de grandeur sur la tranche — la notice invitait
           pourtant a le prendre au pied de la lettre. Le chiffre exact part
           desormais dans un second chunk tEXt du PNG lui-meme. */
        + ((row.atlas && row.atlas.density && row.atlas.density.edge_dpi)
          ? '<p class="hint cf-gltf-warn">Un <b>pHYs</b> pour <b>trois îlots</b> : '
            + 'ce chiffre est celui du <b>recto</b>. L\'îlot de tranche sort à <b>'
            + row.atlas.density.edge_dpi.join(" x ") + ' DPI</b> (rapport '
            + row.atlas.density.edge_ratio + ':1) sur un contour de <b>'
            + row.atlas.density.edge_perim_mm + ' mm</b> <i>mesuré sur le '
            + esc(String(row.atlas.density.edge_perim_source || "")) + '</i>, '
            + 'coins arrondis compris — un outil d\'impression qui '
            + 'prend le pHYs au pied de la lettre se trompe sur cette zone. '
            + 'La réserve voyage dans un chunk <code>tEXt</code> de chaque PNG.</p>'
          : '')
        /* ── UN DIAGNOSTIC POSÉ SANS AUCUNE COMMANDE POUR AGIR DESSUS ───────
           Reproche mesuré : ce panneau écrivait que 60 % des texels de son
           atlas ne portent aucune information, donnait la définition qui n'en
           gaspille pas — et expédiait quand même l'atlas de 2048 px. Le bouton
           existait, dans la carte des réglages, à deux cartes d'ici : c'est-à-
           dire loin de l'endroit où le constat se lit. Le constat et sa
           commande se peignent maintenant au même endroit, avec les deux
           nombres qui les fondent. */
        + ((dens && dens.res_fit && Number(dens.res_fit) !== Number(get("res"))
            && dens.wasted_px)
          ? '<p class="hint cf-gltf-warn"><b>' + dens.useful_pct + ' %</b> des '
            + 'texels de l\'îlot recto portent de l\'information : <b>'
            + dens.wasted_px + '</b> texels n\'en portent aucune. '
            + '<button class="btn sm" data-act="fit">ramener l\'atlas à '
            + dens.res_fit + ' px</button> ' + esc(dens.fit_note || '') + '</p>'
          : '')
        + '</div>';
    }
    el.innerHTML = html;
  }

  /* Tant qu'aucun GLB n'existe, la visionneuse ne montre pas un carre vide :
     elle dit ce qu'elle montrera, et le mesure d'avance. */
  function paintViewerEmpty() {
    if (BUILD && fileOf("glb")) return;
    const host = $("#cf-gltf-view");
    if (!host || $("#cf-gltf-mv")) return;
    const g = CF.geom();
    /* « ... ET MESURERA SA BOÎTE ENGLOBANTE : 63 x 88 x 0.32 mm ATTENDUES. »
       Le chiffre était le réglage, le mot le donnait pour la cible, et les
       deux s'affichaient à l'endroit où le relevé viendra se poser. Un écran
       qui annonce le résultat avant d'avoir ouvert le fichier n'a plus rien à
       prouver quand il l'ouvre. On annonce donc le geste, pas le nombre : le
       nombre arrive après la construction, et il sort du .glb. */
    host.innerHTML = '<p class="empty-note sm">La visionneuse ouvrira le '
      + '<b>.glb</b> une fois construit et mesurera sa boîte englobante. Le '
      + 'nombre s\'affichera ici, relu dans le fichier livré.</p>';
    const mes = $("#cf-gltf-mes");
    if (mes) {
      /* « 1,43 x 2,00 m » ÉTAIT UN NOMBRE CODÉ EN DUR, donc faux dès qu'on
         change de format. Le maillage est normalisé sur sa HAUTEUR (demi-
         hauteur = 1 unité) : sans l'échelle du nœud, un viewer lirait
         2·L/H x 2 m — 1,43 x 2,00 m en poker 63 x 88, mais 1,17 x 2,00 m en
         tarot 70 x 120. On le calcule donc à partir de la géométrie du CORE
         au lieu de le recopier. */
      const sansEchelle = [2 * g.trim_mm[0] / g.trim_mm[1], 2,
                           2 * thicknessMM() / g.trim_mm[1]];
      mes.innerHTML = '<span>1 unité glTF = 1 mètre : le nœud porte l\'échelle '
        + 'physique, sinon un viewer annoncerait une carte de '
        + sansEchelle.slice(0, 2).map((v) => v.toFixed(2).replace(".", ","))
          .join(" x ") + ' m.</span>';
    }
  }

  /* ── CE TABLEAU SE DONNAIT UNE NOTE, LIGNE PAR LIGNE ──────────────────────
     Quatorze mesures, chacune peinte en VERT quand elle tombait sur la valeur
     que le code espérait — metallicFactor === 1, roughnessFactor === 1,
     materials === 1, wrap === CLAMP_TO_EDGE, TANGENT présent. Le nombre venait
     bien du fichier ; la couleur, elle, ne venait de nulle part : elle
     comparait le relevé à un attendu que l'écran ne montrait pas et que
     personne n'avait réglé. C'est une grille de correction, pas un bordereau,
     et un utilisateur n'a rien à faire d'une rangée de bons points.

     La règle est maintenant asymétrique, et c'est tout l'objet : ce panneau
     AVERTIT, il ne se félicite pas. Une mesure qui a une conséquence fâcheuse
     pour celui qui monte le fichier sort en ambre ; les autres sortent
     neutres, suivies de ce qu'elles CHANGENT pour lui. Le chiffre n'a pas
     bougé d'une décimale — c'est la note qui est partie. */
  function kv(k, v, ok, why) {
    return '<div><span>' + esc(k) + '</span><b class="'
      + (ok === false ? "cf-gltf-ko" : "") + '">' + esc(v) + '</b>'
      + (why ? '<i>' + esc(why) + '</i>' : '') + '</div>';
  }

  /* L'ETAT VIDE PROPOSE QUELQUE CHOSE : ce qui sera produit, et le bouton. */
  function emptySlip() {
    const f = get("formats");
    const n = CF.cards().length;
    const scope = get("scope");
    /* « 4 textures » etait une promesse ronde : la quatrieme (emissive) etait
       embarquee meme quand emissiveFactor valait [0,0,0], donc multipliee par
       zero. Le compte a ensuite suivi la finition — juste, mais toujours
       ANNONCE : rien n'est ecrit quand cette ligne se peint, donc rien ne se
       relit. Un chiffre qu'on ne peut pas prouver sur des octets ne s'affiche
       plus ici du tout ; c'est la REGLE qui est ecrite, et le bordereau
       comptera ce que le fichier porte. */
    const emet = ((INFO && INFO.finishes) || [])
      .filter((x) => x.id === get("finish"))[0];
    const lignes = [];
    if (f.indexOf("glb") >= 0) lignes.push("un <b>.glb</b> — géométrie, "
      + "matériau, textures" + ((emet && emet.emissive > 0) ? ""
        : " (cette finition n\'émet pas : aucune texture émissive, elle serait "
          + "multipliée par zéro)"));
    if (f.indexOf("gltf") >= 0) lignes.push("un <b>.gltf</b> autonome — buffer en data URI, aucun <i>.bin</i> à côté");
    /* « les 8 maps » était un 8 écrit ici ; il est ensuite venu du backend,
       ce qui le rendait juste mais toujours pas PROUVÉ : rien n'est écrit,
       donc rien ne se relit. Et depuis que la map d'émission n'est écrite que
       si un matériau peut la pointer, le compte dépend de la finition. Un
       nombre annoncé avant la construction n'est vérifiable sur aucun octet :
       il ne s'affiche plus qu'au bordereau, où il est compté sur l'archive. */
    if (f.indexOf("zip") >= 0) lignes.push("un <b>.zip</b> — les maps PNG (une "
      + "par canal dérivé, l\'émission seulement si la finition émet), le "
      + "manifeste, le maillage OBJ et son MTL");
    if (f.indexOf("obj") >= 0 && f.indexOf("zip") < 0)
      lignes.push("un <b>OBJ + MTL</b> en millimètres, avec ses maps");
    if (f.indexOf("stl") >= 0) lignes.push("un <b>.stl</b> binaire en millimètres");
    if (f.indexOf("3mf") >= 0) lignes.push("un <b>.3mf</b> — norme ouverte d\'impression 3D, en millimètres, <b>avec la couleur</b>");
    if (scope === "deck" && n > 1) lignes.push("plus un ZIP du <b>jeu entier</b> (" + n + " cartes)");
    return '<div class="cf-gltf-empty">'
      + '<p>Rien n\'est encore construit. En <b>' + get("res") + ' px</b>, '
      + 'la construction produira :</p><ul><li>' + lignes.join("</li><li>") + '</li></ul>'
      + '<button class="btn strong" data-act="build">Construire maintenant</button>'
      + '<p class="hint">Les poids s\'afficheront ici, fichier par fichier.</p>'
      + '</div>';
  }
})();
