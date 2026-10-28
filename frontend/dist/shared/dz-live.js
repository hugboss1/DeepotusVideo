// dz-live.js — t318 (28/10/2026, lot D4 « live multi-destinations »), le DIRECT de l'app vers Twitch, YouTube Live, Kick
// et tout serveur RTMP(S), avec l'annonce Discord (plan docs/superpowers/plans/2026-10-28-t318-live.md, spec boîte à
// outils §8.6). SOURCE : frontend/shared/dz-live.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-live.js, chargée
// par frontend/dist/index.html (`<script type="module">`, après dz-capture.js). Aucun maillon de bundle. Banc :
// backend/tests/test_live_ecran.py.
//
// - Bouton « Direct » [data-dz-live-ouvrir] dans la barre du haut, juste après « Filmer l'app » ; il ouvre la boîte
//   « Passer en direct » (charte de dialogue.js) : titre, destinations de l'espace (comptes live, clés au coffre),
//   ajout d'une destination (bloc data-dz-secret, clé en champ mot de passe), annonce Discord (webhook) et son guide,
//   caméra, habillage (skin, t316).
// - « Passer en direct » (le seul geste qui envoie quoi que ce soit) : POST /api/live/sessions (destinations résolues et
//   refusées AVANT tout flux) → __dzCapture.demarrer (la capture t315 : même scène, même caviardage data-dz-secret, même
//   enregistrement dans la Bibliothèque) → une MediaRecorder sur scene.flux() + la voix mixée, morceaux de 250 ms
//   envoyés par WebSocket local ; le serveur pousse le flux par ffmpeg tee. L'annonce Discord part au premier
//   « en_direct ».
// - Pendant : panneau [data-dz-live-panneau] (santé par destination, débit, images perdues, vitesse ; « Pause écran »
//   = écran « on revient tout de suite » du skin, repli calque live-pause ; « Marqueur » ; « Arrêter le direct » =
//   écran « fin du direct » 2 s puis arrêt de la capture, qui joue l'outro). Aucune clé n'y est jamais affichée.
// - Fin (dz-capture:fin, quelle qu'en soit la cause) : flux coupé, POST …/terminer {capture_id} (marqueurs écrits à
//   côté de la capture, pour les clips de t317), bilan dans le panneau.
// API : window.__dzLive = {ouvrir(), etat(), arreter()}.
import { choisirMimeLive, MORCEAU_MS, TAMPON_MAX, PLATEFORMES, CHAMPS, SERVEURS, corpsAjout, lienDe, niveauFlux,
  formatDebit, messageAnnonce, instantMarqueur } from "./dz-live-logique.js";
import { duree } from "./dz-capture-logique.js";

if (!window.__dzLive) {
  const T = (cle, vars) => (typeof window.dzT === "function" ? window.dzT(cle, vars) : cle);
  const langue = () => (typeof window.dzLang === "function" && window.dzLang() === "en" ? "en" : "fr");
  const glyphe = (cle, taille) => {
    const s = document.createElement("span");
    s.className = "dzLiveGl";
    s.innerHTML = typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: taille || 14 }) : "";
    return s;
  };
  const el = (tag, attrs, enfants) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "on") for (const [e, f] of Object.entries(v)) n.addEventListener(e, f);
      else if (k === "texte") n.textContent = v;
      else if (k === "style") n.style.cssText = v;
      else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
    }
    for (const c of enfants || []) if (c) n.appendChild(c);
    return n;
  };
  const attendre = (ms) => new Promise((ok) => setTimeout(ok, ms));
  async function api(url, options) {
    const r = await fetch(url, options);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "HTTP " + r.status);
    return j;
  }
  const json = (methode, corps) => ({ method: methode, headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps || {}) });

  const S = {
    voile: "position:fixed;inset:0;z-index:2147483004;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:540px;max-width:94vw;max-height:90vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;color:var(--txt-base,var(--ink,#cfd6e2))",
    groupe: "display:flex;flex-direction:column;gap:6px",
    titreG: "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    erreur: "font-size:12px;color:var(--red,#e5484d)",
    champ: "font:inherit;font-size:12px;padding:4px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));min-width:0",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    bouton: "font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    petit: "font:inherit;font-size:11.5px;padding:2px 8px;border-radius:0;cursor:pointer;background:transparent;color:inherit;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    direct: "font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;background:#e5484d;color:#fff;border:1px solid #e5484d;font-weight:600",
    carte: "display:flex;align-items:center;gap:8px;padding:6px 8px;border:1px solid var(--brd-soft,var(--stroke,#222830));background:var(--srf-raised,var(--bg-panel-3,#1b2028))",
    panneau: "position:fixed;left:12px;bottom:12px;z-index:2147483003;width:320px;max-width:calc(100vw - 24px);display:flex;flex-direction:column;gap:6px;padding:10px 12px;background:rgba(17,20,25,.96);color:#e6e9ee;border:1px solid #e5484d;font:12px/1.4 system-ui,sans-serif;box-shadow:0 8px 28px rgba(0,0,0,.5)",
    point: "width:9px;height:9px;border-radius:50%;flex:none;display:inline-block",
  };
  const COULEURS = { ok: "#3fb950", attente: "#f0b429", panne: "#e5484d", bon: "#3fb950", faible: "#f0b429", coupe: "#e5484d" };
  const CSS = ".dzLiveGl{display:inline-flex;align-items:center;vertical-align:middle;margin-right:5px}.dzLiveGl svg{display:block}"
    + "[data-dz-live-ouvrir]{display:inline-flex;align-items:center;gap:6px;flex-shrink:0;align-self:center;margin:0 4px;padding:4px 10px;font-size:12px;border-radius:0;cursor:pointer;background:transparent;color:inherit;border:1px solid var(--stroke,#2a3138)}"
    + "[data-dz-live-ouvrir][data-actif]{border-color:#e5484d;color:#e5484d}"
    + "[data-dz-live-ouvrir]:disabled{opacity:.45;cursor:not-allowed}";
  document.head.appendChild(el("style", { "data-dz-live-ui": true, texte: CSS }));

  let direct = null;              // le direct en cours : {id, vue, ws, rec, …}
  const capture = () => window.__dzCapture;

  // ── le bouton de la barre du haut ──
  const bouton = el("button", { type: "button", "data-dz-live-ouvrir": true, "data-dz-capture-ui": true,
    on: { click: () => (direct ? arreter() : ouvrir()) } });
  function peindreBouton() {
    const cap = capture();
    const actif = !!direct;
    bouton.replaceChildren(glyphe(actif ? "dz-media-arret" : "dz-media-badge-direct"),
      document.createTextNode(T(actif ? "live.barre.arreter" : "live.barre.bouton")));
    bouton.toggleAttribute("data-actif", actif);
    const pris = !actif && cap && cap.session && cap.session();           // une capture sans direct est en cours
    bouton.disabled = !actif && (!cap || !cap.disponible() || !!pris);
    bouton.title = T(bouton.disabled ? (pris ? "live.barre.capture_en_cours" : "live.barre.indisponible")
      : (actif ? "live.barre.arreter" : "live.barre.titre"));
  }
  function placerBouton() {
    const h = document.querySelector("#root header");
    if (!h) { if (bouton.isConnected) bouton.remove(); return; }
    const rec = h.querySelector("[data-dz-capture-ouvrir]");
    if (rec) { if (rec.nextSibling !== bouton) h.insertBefore(bouton, rec.nextSibling); return; }
    if (bouton.parentNode !== h) h.insertBefore(bouton, h.querySelector(".dzAgentBtn"));
  }
  let guet = 0;
  new MutationObserver(() => {
    if (guet) return;
    guet = setTimeout(() => { guet = 0; placerBouton(); }, 40);
  }).observe(document.getElementById("root") || document.body, { childList: true, subtree: true });
  window.addEventListener("dz-capture:debut", peindreBouton);
  window.addEventListener("dz-capture:fin", () => setTimeout(peindreBouton, 0));
  peindreBouton();
  placerBouton();

  // ── la boîte « Passer en direct » ──
  let boite = null;
  function fermerBoite() { if (boite) { boite.remove(); boite = null; } }
  function pieger(b, fermer) {
    b.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); return; }
      if (ev.key !== "Tab") return;
      const f = Array.from(b.querySelectorAll("button, input, select, textarea")).filter((x) => !x.disabled && x.offsetParent !== null);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
      else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); }
    });
  }
  const nomPlateforme = (p) => T("live.plateforme." + p);

  function ouvrir() {
    const cap = capture();
    if (direct || boite || !cap || !cap.disponible() || cap.session()) return;
    const erreur = el("div", { style: S.erreur, role: "alert", "data-dz-live-erreur": true });
    const titre = el("input", { type: "text", style: S.champ + ";width:100%", maxlength: "100", "data-dz-live-titre": true,
      "aria-label": T("live.boite.titre_direct"), placeholder: T("live.boite.titre_exemple") });
    const liste = el("div", { style: S.groupe, "data-dz-live-destinations": true });
    const discord = el("select", { style: S.champ, "data-dz-live-discord": true, "aria-label": T("live.annonce.salon") });
    const message = el("textarea", { style: S.champ + ";width:100%;min-height:44px;resize:vertical", maxlength: "1500",
      rows: "2", "data-dz-live-message": true, "aria-label": T("live.annonce.message") });
    let messageTouche = false;
    message.addEventListener("input", () => { messageTouche = true; });
    titre.addEventListener("input", () => { if (!messageTouche) message.value = messageAnnonce(titre.value, T); });
    message.value = messageAnnonce("", T);
    const cam = el("input", { type: "checkbox", "data-dz-live-option": "camera", "aria-label": T("live.boite.camera") });
    const habillage = window.__dzSkins && typeof window.__dzSkins.groupeCapture === "function"
      ? window.__dzSkins.groupeCapture({}) : null;
    let comptes = [];

    async function charger() {
      try {
        const j = await api("/api/comptes?live=1");
        comptes = (j.comptes || []).filter((c) => PLATEFORMES.indexOf(c.plateforme) >= 0);
      } catch (e) { erreur.textContent = T("live.erreur.liste", { msg: e.message || "—" }); comptes = []; }
      const choisis = new Set(Array.from(liste.querySelectorAll("input[data-dz-live-dest]:checked")).map((x) => x.value));
      const dests = comptes.filter((c) => c.plateforme !== "discord");
      liste.replaceChildren(...(dests.length ? dests.map((c) => {
        const caseC = el("input", { type: "checkbox", value: c.id, "data-dz-live-dest": c.id, disabled: !c.disponible,
          "aria-label": nomPlateforme(c.plateforme) + " — " + c.libelle });
        caseC.checked = c.disponible && (choisis.has(c.id) || (!choisis.size && dests.length === 1));
        const lien = lienDe(c);
        return el("label", { style: S.carte, "data-dz-live-carte": c.id }, [caseC,
          el("strong", { texte: nomPlateforme(c.plateforme), style: "font-size:11px;font-family:'IBM Plex Mono',monospace;min-width:84px" }),
          el("span", { texte: c.libelle, "data-dz-brut": true, style: "flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis" }),
          el("span", { texte: T(c.disponible ? "live.dest.prete" : "live.dest.incomplete"),
            style: "font-size:11px;color:" + (c.disponible ? "#3fb950" : "#f0b429") }),
          lien ? el("span", { texte: "↗", title: lien, "data-dz-brut": true, style: "font-size:11px;color:#9aa4ae" }) : null,
          el("button", { type: "button", style: S.petit, "data-dz-live-retirer": c.id, texte: T("live.dest.retirer"),
            "aria-label": T("live.dest.retirer") + " — " + c.libelle, on: { click: (ev) => { ev.preventDefault(); retirer(c); } } })]);
      }) : [el("div", { style: S.note, texte: T("live.dest.aucune"), "data-dz-live-aucune": true })]));
      const dc = comptes.filter((c) => c.plateforme === "discord" && c.disponible);
      const garde = discord.value;
      discord.replaceChildren(el("option", { value: "", texte: T("live.annonce.aucune") }),
        ...dc.map((c) => el("option", { value: c.id, texte: c.libelle, "data-dz-brut": true })));
      discord.value = dc.some((c) => c.id === garde) ? garde : (dc.length === 1 ? dc[0].id : "");
    }
    async function retirer(c) {
      const d = window.__dzDialogue;
      const oui = d && typeof d.confirmer === "function"
        ? await d.confirmer(T("live.dest.retirer_q", { nom: c.libelle }), { titre: T("live.dest.retirer"), ok: T("live.dest.retirer") })
        : window.confirm(T("live.dest.retirer_q", { nom: c.libelle }));
      if (!oui) return;
      try { await api("/api/comptes/" + encodeURIComponent(c.id), { method: "DELETE" }); }
      catch (e) { erreur.textContent = e.message; }
      charger();
    }

    // ajout d'une destination : un bloc SECRET (flouté et caviardé si une capture le filmait), clé en mot de passe
    const ajout = (() => {
      const plat = el("select", { style: S.champ, "data-dz-live-ajout-plateforme": true, "aria-label": T("live.ajout.plateforme") },
        PLATEFORMES.map((p) => el("option", { value: p, texte: nomPlateforme(p) })));
      const libelle = el("input", { type: "text", style: S.champ, maxlength: "80", "data-dz-live-ajout-libelle": true,
        "aria-label": T("live.ajout.libelle"), placeholder: T("live.ajout.libelle") });
      const handle = el("input", { type: "text", style: S.champ, maxlength: "40", "data-dz-live-ajout-handle": true,
        "aria-label": T("live.ajout.handle"), placeholder: T("live.ajout.handle") });
      const serveur = el("input", { type: "text", style: S.champ + ";flex:1", maxlength: "1024", "data-dz-live-ajout-serveur": true,
        "aria-label": T("live.ajout.serveur"), autocomplete: "off", spellcheck: "false" });
      const lien = el("input", { type: "url", style: S.champ + ";flex:1", maxlength: "300", "data-dz-live-ajout-lien": true,
        "aria-label": T("live.ajout.lien"), placeholder: "https://…" });
      const cle = el("input", { type: "password", style: S.champ + ";flex:1", maxlength: "512", "data-dz-live-ajout-cle": true,
        "aria-label": T("live.ajout.cle"), autocomplete: "off", spellcheck: "false" });
      const aide = el("div", { style: S.note, "data-dz-live-ajout-aide": true });
      const lignes = { handle: el("label", { style: S.ligne }, [el("span", { texte: T("live.ajout.handle") }), handle]),
        serveur: el("label", { style: S.ligne }, [el("span", { texte: T("live.ajout.serveur") }), serveur]),
        lien: el("label", { style: S.ligne }, [el("span", { texte: T("live.ajout.lien") }), lien]) };
      const libCle = el("span", { texte: T("live.ajout.cle") });
      const peindre = () => {
        const c = CHAMPS[plat.value];
        lignes.handle.style.display = c.handle ? "" : "none";
        lignes.serveur.style.display = c.serveur ? "" : "none";
        lignes.lien.style.display = c.lien ? "" : "none";
        serveur.placeholder = SERVEURS[plat.value] || "rtmps://…";
        libCle.textContent = T(plat.value === "discord" ? "live.ajout.webhook" : "live.ajout.cle");
        cle.setAttribute("aria-label", libCle.textContent);
        aide.textContent = T("live.ajout.aide_" + plat.value);
      };
      plat.addEventListener("change", peindre);
      const enregistrer = el("button", { type: "button", style: S.bouton, "data-dz-live-ajout-enregistrer": true,
        texte: T("live.ajout.enregistrer") });
      enregistrer.addEventListener("click", async () => {
        const corps = corpsAjout(plat.value, { libelle: libelle.value, handle: handle.value, serveur: serveur.value,
          lien: lien.value, cle: cle.value });
        if (!corps) { erreur.textContent = T("live.ajout.incomplet"); return; }
        enregistrer.disabled = true; erreur.textContent = "";
        try {
          await api("/api/comptes", json("POST", corps));
          cle.value = ""; serveur.value = ""; lien.value = ""; libelle.value = ""; handle.value = "";
          noeud.hidden = true; btnAjout.hidden = false;
          await charger();
        } catch (e) { erreur.textContent = T("live.ajout.erreur", { msg: e.message || "—" }); }
        finally { enregistrer.disabled = false; }
      });
      const annuler = el("button", { type: "button", style: S.bouton, texte: T("live.boite.annuler"),
        on: { click: () => { cle.value = ""; noeud.hidden = true; btnAjout.hidden = false; } } });
      const noeud = el("div", { style: S.groupe + ";padding:8px;border:1px dashed var(--brd-hard,#2a3138)",
        "data-dz-live-ajout": true, "data-dz-secret": true, hidden: true }, [
        el("label", { style: S.ligne }, [el("span", { texte: T("live.ajout.plateforme") }), plat, libelle]),
        lignes.handle, lignes.serveur, lignes.lien,
        el("label", { style: S.ligne }, [libCle, cle]), aide,
        el("div", { style: S.ligne + ";justify-content:flex-end" }, [annuler, enregistrer])]);
      peindre();
      return noeud;
    })();
    const btnAjout = el("button", { type: "button", style: S.petit + ";align-self:flex-start", "data-dz-live-ajouter": true,
      texte: T("live.dest.ajouter"), on: { click: () => { ajout.hidden = false; btnAjout.hidden = true; } } });

    const btnDirect = el("button", { type: "button", style: S.direct, "data-dz-live-demarrer": true, texte: T("live.boite.demarrer") });
    btnDirect.insertBefore(glyphe("dz-media-badge-direct"), btnDirect.firstChild);
    const btnAnnuler = el("button", { type: "button", style: S.bouton, texte: T("live.boite.annuler"), on: { click: fermerBoite } });
    btnDirect.addEventListener("click", async () => {
      const ids = Array.from(liste.querySelectorAll("input[data-dz-live-dest]:checked")).map((x) => x.value);
      if (!ids.length) { erreur.textContent = T("live.erreur.aucune"); return; }
      btnDirect.disabled = true; btnAnnuler.disabled = true; erreur.textContent = T("live.boite.connexion");
      const r = await demarrer({ comptes: ids, titre: titre.value, camera: cam.checked,
        skin: habillage ? habillage.valeur() : undefined, discord: discord.value || null, message: message.value });
      if (r.ok) fermerBoite();
      else { erreur.textContent = r.message; btnDirect.disabled = false; btnAnnuler.disabled = false; }
    });

    boite = el("div", { style: S.voile, "data-dz-capture-ui": true, "data-dz-live-boite": true }, [
      el("div", { style: S.boite, role: "dialog", "aria-modal": "true", "aria-label": T("live.boite.titre") }, [
        el("div", { style: S.tete, texte: T("live.boite.titre") }),
        el("div", { style: S.corps }, [
          el("div", { style: S.groupe }, [el("div", { style: S.titreG, texte: T("live.boite.titre_direct") }), titre]),
          el("div", { style: S.groupe }, [el("div", { style: S.titreG, texte: T("live.dest.titre") }), liste, btnAjout, ajout]),
          el("div", { style: S.groupe, "data-dz-live-annonce": true }, [el("div", { style: S.titreG, texte: T("live.annonce.titre") }),
            el("label", { style: S.ligne }, [el("span", { texte: T("live.annonce.salon") }), discord]), message,
            el("div", { style: S.note, "data-dz-live-discord-guide": true, texte: T("live.annonce.guide") })]),
          el("div", { style: S.groupe }, [el("div", { style: S.titreG, texte: T("live.boite.camera_titre") }),
            el("label", { style: S.ligne }, [cam, el("span", { texte: T("live.boite.camera") })])]),
          habillage ? habillage.noeud : null,
          el("div", { style: S.note, texte: T("live.boite.securite") }),
          erreur,
        ]),
        el("div", { style: S.pied }, [btnAnnuler, btnDirect]),
      ]),
    ]);
    boite.addEventListener("pointerdown", (ev) => { if (ev.target === boite && !btnAnnuler.disabled) fermerBoite(); });
    pieger(boite, () => { if (!btnAnnuler.disabled) fermerBoite(); });
    document.body.appendChild(boite);
    charger();
    titre.focus();
  }

  // ── passer en direct : rend {ok, message?} ; rien ne reste allumé après un échec ──
  function pisteMuette() {
    try {
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      const o = ac.createOscillator(), g = ac.createGain(), d = ac.createMediaStreamDestination();
      g.gain.value = 0; o.connect(g); g.connect(d); o.start();
      const p = d.stream.getAudioTracks()[0];
      p._dzArret = () => { try { o.stop(); } catch (e) { /* arrêté */ } ac.close().catch(() => {}); };
      return p;
    } catch (e) { return null; }
  }

  async function demarrer(o) {
    const cap = capture();
    if (direct || !cap) return { ok: false, message: "" };
    let vue;
    try { vue = await api("/api/live/sessions", json("POST", { comptes: o.comptes, titre: o.titre })); }
    catch (e) { return { ok: false, message: T("live.erreur.ouvrir", { msg: e.message || "—" }) }; }
    const abandon = () => fetch("/api/live/sessions/" + vue.id, { method: "DELETE" }).catch(() => {});
    let memo = {};
    try { memo = JSON.parse(window.localStorage.getItem("dz_capture_options") || "{}") || {}; } catch (e) { memo = {}; }
    const options = Object.assign({}, memo, { camera: !!o.camera, live: true });
    if (o.skin !== undefined) options.skin = o.skin;
    const r = await cap.demarrer(options);
    if (!r || !r.ok) { await abandon(); return { ok: false, message: (r && r.message) || T("live.erreur.capture") }; }
    const ses = cap.session();
    const muette = ses.audio && ses.audio.getAudioTracks().length ? null : pisteMuette();
    const pistes = [...ses.scene.flux(30).getVideoTracks(), ...(muette ? [muette] : ses.audio.getAudioTracks())];
    const mime = choisirMimeLive((m) => window.MediaRecorder.isTypeSupported(m));
    direct = { id: vue.id, vue, titre: o.titre, debutCapture: ses.debut, debut: performance.now(), ws: null, rec: null,
      muette, etat: null, perdus: 0, marqueurs: 0, pause: false, discord: o.discord, message: o.message, annonce: null,
      fini: false, ferme: false };
    window.addEventListener("dz-capture:fin", surFinCapture);
    const proto = location.protocol === "https:" ? "wss://" : "ws://";
    const ws = new WebSocket(proto + location.host + "/api/live/sessions/" + vue.id + "/flux");
    ws.binaryType = "arraybuffer";
    direct.ws = ws;
    ws.addEventListener("open", () => {
      if (!direct || direct.ws !== ws) return;
      const rec = new window.MediaRecorder(new MediaStream(pistes), mime ? { mimeType: mime, videoBitsPerSecond: 6000000 } : undefined);
      rec.addEventListener("dataavailable", (ev) => {
        if (!ev.data || !ev.data.size || ws.readyState !== 1) return;
        if (ws.bufferedAmount > TAMPON_MAX) { direct.perdus++; return; }
        ws.send(ev.data);
      });
      direct.rec = rec;
      rec.start(MORCEAU_MS);
    });
    ws.addEventListener("message", (ev) => {
      let e = null;
      try { e = JSON.parse(ev.data); } catch (x) { return; }
      if (!direct || !e || e.type !== "etat") return;
      direct.etat = e;
      if (e.etat === "en_direct" && direct.discord && !direct.annonce) annoncer();
      peindrePanneau();
    });
    ws.addEventListener("close", () => { if (direct && !direct.fini) { direct.ferme = true; peindrePanneau(); } });
    panneau();
    peindreBouton();
    window.dispatchEvent(new CustomEvent("dz-live:debut", { detail: { id: vue.id } }));
    return { ok: true, id: vue.id };
  }

  async function annoncer() {
    const d = direct;
    d.annonce = { encours: true };
    try {
      const r = await api("/api/live/sessions/" + d.id + "/annonce", json("POST", { compte: d.discord, texte: d.message }));
      d.annonce = { ok: !!r.ok };
    } catch (e) { d.annonce = { ok: false }; }
    peindrePanneau();
  }

  // ── pendant le direct : le panneau ──
  let ui = null;
  function panneau() {
    const temps = el("span", { texte: "00:00", style: "font-variant-numeric:tabular-nums", "data-dz-live-temps": true });
    const niveau = el("span", { "data-dz-live-niveau": true, style: "font-size:11px" });
    const dests = el("div", { style: "display:flex;flex-direction:column;gap:3px", "data-dz-live-sante": true });
    const chiffres = el("div", { style: "font-size:11px;color:#9aa4ae;font-variant-numeric:tabular-nums", "data-dz-live-chiffres": true });
    const infos = el("div", { style: "font-size:11px;color:#9aa4ae", "data-dz-live-infos": true });
    const pause = el("button", { type: "button", style: S.petit, "data-dz-live-pause": true, "aria-pressed": "false",
      on: { click: basculerPause } });
    const marque = el("button", { type: "button", style: S.petit, "data-dz-live-marqueur": true, on: { click: marquer } },
      [glyphe("dz-media-marqueur", 12), document.createTextNode(T("live.panneau.marqueur"))]);
    const stop = el("button", { type: "button", style: S.petit + ";border-color:#e5484d;color:#ff8a8e", "data-dz-live-arreter": true,
      on: { click: () => arreter() } }, [glyphe("dz-media-arret", 12), document.createTextNode(T("live.panneau.arreter"))]);
    const p = el("div", { style: S.panneau, role: "status", "aria-live": "polite", "aria-label": T("live.panneau.titre"),
      "data-dz-capture-ui": true, "data-dz-live-panneau": true }, [
      el("div", { style: "display:flex;align-items:center;gap:8px" }, [
        el("span", { style: S.point + ";background:#e5484d" }),
        el("strong", { texte: T("live.panneau.en_direct"), "data-dz-live-titre-panneau": true }), temps, niveau]),
      dests, chiffres, infos,
      el("div", { style: "display:flex;gap:6px;flex-wrap:wrap", "data-dz-live-actions": true }, [pause, marque, stop])]);
    document.body.appendChild(p);
    ui = { p, temps, niveau, dests, chiffres, infos, pause, marque, stop, minuterie: setInterval(() => {
      if (direct && !direct.fini && ui) ui.temps.textContent = duree(performance.now() - direct.debut);
    }, 500) };
    peindrePanneau();
  }
  function peindrePanneau() {
    if (!ui || !direct) return;
    const e = direct.etat;
    const n = direct.ferme ? "coupe" : niveauFlux(e);
    ui.niveau.textContent = T("live.niveau." + n);
    ui.niveau.style.color = COULEURS[n] || "#9aa4ae";
    ui.dests.replaceChildren(...direct.vue.destinations.map((x, i) => {
      const etat = direct.ferme ? "panne" : ((e && e.destinations && e.destinations[i]) || "attente");
      return el("div", { style: "display:flex;align-items:center;gap:6px", "data-dz-live-dest-etat": etat }, [
        el("span", { style: S.point + ";background:" + COULEURS[etat] }),
        el("span", { texte: nomPlateforme(x.plateforme), style: "font-size:11px;font-family:'IBM Plex Mono',monospace;min-width:84px" }),
        el("span", { texte: x.libelle, "data-dz-brut": true, style: "flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis" }),
        el("span", { texte: T("live.etat." + etat), style: "font-size:11px;color:" + COULEURS[etat] })]);
    }));
    ui.chiffres.textContent = e ? T("live.panneau.chiffres", { debit: formatDebit(e.debit_kbps, langue()),
      fps: e.fps == null ? "—" : Math.round(e.fps), perdues: e.images_perdues == null ? 0 : e.images_perdues,
      vitesse: e.vitesse == null ? "—" : e.vitesse.toFixed(2) }) : T("live.panneau.connexion");
    const infos = [];
    if (direct.marqueurs) infos.push(T("live.panneau.marqueurs", { n: direct.marqueurs }));
    if (direct.annonce && direct.annonce.ok === true) infos.push(T("live.annonce.partie"));
    if (direct.annonce && direct.annonce.ok === false) infos.push(T("live.annonce.ratee"));
    if (direct.perdus) infos.push(T("live.panneau.perdus", { n: direct.perdus }));
    if (direct.ferme) infos.push(T("live.panneau.coupe"));
    ui.infos.textContent = infos.join(" · ");
    ui.pause.replaceChildren(glyphe("dz-media-pause", 12), document.createTextNode(T(direct.pause ? "live.panneau.reprendre" : "live.panneau.pause")));
    ui.pause.setAttribute("aria-pressed", direct.pause ? "true" : "false");
  }

  // l'écran plein cadre (pause / fin) : celui du skin ; sans skin, un calque de repli (z 790, sous le caviardage)
  function ecranPlein(nom) {
    const ses = capture() && capture().session();
    if (!ses) return;
    const viaSkin = window.__dzSkins && typeof window.__dzSkins.ecran === "function" && window.__dzSkins.actuel && window.__dzSkins.actuel()
      ? window.__dzSkins.ecran(nom) : null;
    ses.scene.retirerCalque("live-ecran");
    if (viaSkin !== null || !nom) return;
    const texte = T(nom === "fin" ? "live.ecran.fin" : "live.ecran.pause");
    ses.scene.ajouterCalque({ id: "live-ecran", z: 790, dessiner(ctx, s) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "#0b0f14"; ctx.fillRect(0, 0, s.largeur, s.hauteur);
      ctx.fillStyle = "#e6e9ee"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = "600 " + Math.round(s.largeur / 26) + "px system-ui, sans-serif";
      ctx.fillText(texte, s.largeur / 2, s.hauteur / 2);
    } });
  }
  function basculerPause() {
    if (!direct || direct.fini) return;
    direct.pause = !direct.pause;
    ecranPlein(direct.pause ? "pause" : null);
    peindrePanneau();
  }
  async function marquer() {
    if (!direct || direct.fini) return;
    const n = direct.marqueurs + 1;
    const t = instantMarqueur(performance.now(), direct.debutCapture);
    try {
      await api("/api/live/sessions/" + direct.id + "/marqueurs", json("POST", { t, libelle: T("live.panneau.marqueur_n", { n }) }));
      direct.marqueurs = n;
    } catch (e) { if (ui) ui.infos.textContent = e.message; return; }
    peindrePanneau();
  }

  // ── arrêter : écran « fin du direct » 2 s, puis la capture s'arrête (outro du skin, Bibliothèque) ──
  let arret = null;
  function arreter() {
    if (!direct) return Promise.resolve(null);
    if (arret) return arret;
    arret = (async () => {
      if (ui) { ui.stop.disabled = true; ui.pause.disabled = true; ui.marque.disabled = true; }
      direct.pause = false;
      ecranPlein("fin");
      await attendre(2000);
      ecranPlein(null);
      const cap = capture();
      if (cap && cap.session()) await cap.arreter();          // dz-capture:fin → surFinCapture
      else await surFinCapture({ detail: {} });
    })().finally(() => { arret = null; });
    return arret;
  }
  async function surFinCapture(ev) {
    window.removeEventListener("dz-capture:fin", surFinCapture);
    const d = direct;
    if (!d || d.fini) return;
    d.fini = true;
    try { if (d.rec && d.rec.state !== "inactive") d.rec.stop(); } catch (e) { /* déjà arrêté */ }
    await attendre(400);                                        // le dernier morceau part
    try { d.ws.close(); } catch (e) { /* déjà fermé */ }
    if (d.muette && d.muette._dzArret) { d.muette.stop(); d.muette._dzArret(); }
    const capId = ev && ev.detail && ev.detail.capture ? ev.detail.id : undefined;
    let bilan = null;
    try { bilan = await api("/api/live/sessions/" + d.id + "/terminer", json("POST", capId ? { capture_id: capId } : {})); }
    catch (e) { bilan = { erreur: e.message }; }
    if (ui) clearInterval(ui.minuterie);
    afficherBilan(d, bilan, !!capId);
    direct = null;
    peindreBouton();
    window.dispatchEvent(new CustomEvent("dz-live:fin", { detail: { id: d.id, capture_id: capId || null } }));
  }
  function afficherBilan(d, bilan, enregistre) {
    if (!ui) return;
    const live = bilan && bilan.live;
    const lignes = [];
    if (live) {
      lignes.push(T("live.bilan.duree", { duree: duree(live.duree_ms || 0) }));
      for (const x of live.destinations) lignes.push(nomPlateforme(x.plateforme) + " — " + x.libelle + " : " + T("live.etat." + x.etat));
      lignes.push(T("live.bilan.marqueurs", { n: live.marqueurs.length }));
      lignes.push(T(enregistre ? "live.bilan.enregistre" : "live.bilan.non_enregistre"));
    } else lignes.push(T("live.bilan.erreur", { msg: (bilan && bilan.erreur) || "—" }));
    const fermer = el("button", { type: "button", style: S.petit, texte: T("live.bilan.fermer"), "data-dz-live-bilan-fermer": true,
      on: { click: () => { ui.p.remove(); ui = null; } } });
    const biblio = enregistre ? el("button", { type: "button", style: S.petit, texte: T("live.bilan.biblio"), on: { click: () => {
      ui.p.remove(); ui = null; window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: "library" } })); } } }) : null;
    ui.p.style.borderColor = "#2a3138";
    ui.p.setAttribute("data-dz-live-bilan", "");
    ui.p.replaceChildren(el("strong", { texte: T("live.bilan.titre") }),
      ...lignes.map((l) => el("div", { texte: l, "data-dz-brut": true, style: "font-size:11.5px" })),
      el("div", { style: S.note + ";color:#9aa4ae", texte: T("live.bilan.clips") }),
      el("div", { style: "display:flex;gap:6px;justify-content:flex-end" }, [biblio, fermer]));
  }

  window.__dzLive = {
    ouvrir, arreter,
    etat: () => (direct ? { id: direct.id, etat: direct.etat, pause: direct.pause, marqueurs: direct.marqueurs,
      annonce: direct.annonce, ferme: direct.ferme } : null),
  };
}
