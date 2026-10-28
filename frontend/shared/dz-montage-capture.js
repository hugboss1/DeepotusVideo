// dz-montage-capture.js — t317 (28/10/2026, lot D3 « montage après coup des captures ») : l'ÉDITEUR DE MONTAGE des
// captures de l'app, façon Screen Studio (plan docs/superpowers/plans/2026-10-28-t317-montage-capture.md, spec boîte
// à outils §8.4).
// SOURCE : frontend/shared/dz-montage-capture.js ; copie OCTET POUR OCTET : frontend/dist/shared/, chargée par
// frontend/dist/index.html (`<script type="module">`, après dz-capture.js). Aucune dépendance au runtime React, aucun
// maillon de bundle, dz-capture.js NON modifié : on entre par l'événement `dz-capture:fin` (bouton « Monter la
// capture » dans la boîte de fin) et par la boîte de départ (« Monter une capture… »), posés de l'extérieur.
// - Le montage (zooms, coupes, chapitres, format, sous-titres) vient du serveur (/api/capture-montage), proposé
//   d'après la piste des clics ; l'aperçu applique les MÊMES formules que le rendu ffmpeg (dz-montage-capture-logique.js).
// - « Rendre » : rendu ffmpeg vers la Bibliothèque ; la transcription de la voix est PAYANTE : son devis s'affiche et
//   rien n'est lancé sans « Confirmer et rendre ». « Planifier un brouillon » : POST /api/schedule (brouillon, sans
//   canaux : ceux du projet actif de l'espace, t307). Rien n'est publié.
// API : window.__dzMontageCapture = {ouvrir(id), liste()}. Banc : backend/tests/test_capture_montage_ecran.py.
import { FORMATS, VITESSES, K_MIN, K_MAX, segments, versSortie, horloge, fenetre, lecture, ajouterZoom, ajouterChapitre,
  retirer, modifier, normaliserZooms, ecranA, clicProche, libelleChapitre, titresRemplis, brouillon } from "./dz-montage-capture-logique.js";

if (!window.__dzMontageCapture) {
  const T = (cle, vars) => (typeof window.dzT === "function" ? window.dzT(cle, vars) : cle);
  const glyphe = (cle) => {
    const s = document.createElement("span");
    s.className = "dzMcGl";
    s.innerHTML = typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: 14 }) : "";
    return s;
  };
  const poser = (n, attrs) => {
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "on") for (const [e, f] of Object.entries(v)) n.addEventListener(e, f);
      else if (k === "texte") n.textContent = v;
      else if (k === "style") n.style.cssText = v;
      else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
    }
    return n;
  };
  const el = (tag, attrs, enfants) => {
    const n = poser(document.createElement(tag), attrs);
    for (const c of enfants || []) if (c) n.appendChild(c);
    return n;
  };
  // un bouton de l'éditeur : libellé T(cle), glyphe devant (forme lue par le catalogue de « Demander »)
  function bouton(cle, attrs, icone, principal) {
    const b = el("button", { type: "button", class: principal ? "dzMcP" : "dzMcB", texte: T(cle) });
    if (icone) b.insertBefore(glyphe(icone), b.firstChild);
    return poser(b, attrs);
  }
  const CSS = ".dzMcGl{display:inline-flex;align-items:center;vertical-align:middle;margin-right:5px}.dzMcGl svg{display:block}"
    + ".dzMcV{position:fixed;inset:0;z-index:2147483005;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center}"
    + ".dzMcD{display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-base,var(--ink,#cfd6e2));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif;max-width:96vw;max-height:94vh}"
    + ".dzMcT{padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))}"
    + ".dzMcC{padding:12px 14px;overflow:auto;display:flex;gap:14px}"
    + ".dzMcPied{display:flex;gap:8px;align-items:center;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))}"
    + ".dzMcB,.dzMcP{font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;display:inline-flex;align-items:center;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee))}"
    + ".dzMcP{background:var(--brand,#f0b429);color:#111;border-color:var(--brand,#f0b429);font-weight:600}"
    + ".dzMcB:disabled,.dzMcP:disabled{opacity:.45;cursor:not-allowed}"
    + ".dzMcB[aria-pressed=true]{border-color:var(--brand,#f0b429);color:var(--brand,#f0b429)}"
    + ".dzMcS{display:flex;flex-direction:column;gap:5px;padding-bottom:10px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830))}"
    + ".dzMcH{font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae));display:flex;align-items:center;gap:6px}"
    + ".dzMcL{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:12px}"
    + ".dzMcN{font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))}"
    + ".dzMcE{font-size:12px;color:var(--red,#e5484d)}"
    + ".dzMcI{font:inherit;font-size:12px;padding:3px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))}"
    + ".dzMcI:disabled{opacity:.45}.dzMcD input[type=range]{accent-color:var(--brand,#f0b429)}"
    + ".dzMcF{flex:none;position:relative;height:34px;background:var(--srf-raised,#1b2028);border:1px solid var(--brd-hard,#2a3138);cursor:pointer}"
    + ".dzMcF span{position:absolute;top:0;bottom:0}";
  document.head.appendChild(el("style", { "data-dz-montage-ui": true, texte: CSS }));

  const api = async (url, opts) => {
    const r = await fetch(url, opts);
    const j = await r.json().catch(() => ({}));
    if (!r.ok && r.status !== 409) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
    return { statut: r.status, j };
  };
  const json = (corps) => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });

  function piege(voile, fermer) {
    voile.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); return; }
      if (ev.key !== "Tab") return;
      const f = Array.from(voile.querySelectorAll("button, input, select, textarea")).filter((x) => !x.disabled);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
      else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); }
    });
  }
  function dialogue(titre, attrs, corps, pied, largeur) {
    const v = el("div", Object.assign({ class: "dzMcV", "data-dz-montage-ui": true }, attrs), [
      el("div", { class: "dzMcD", role: "dialog", "aria-modal": "true", "aria-label": titre, style: `width:${largeur}px` }, [
        el("div", { class: "dzMcT", texte: titre }), corps, pied])]);
    return v;
  }

  // ── la liste des captures closes ──
  async function liste() {
    let fermer = () => {};
    const corps = el("div", { class: "dzMcC", style: "flex-direction:column;gap:6px;min-height:80px" },
      [el("div", { class: "dzMcN", texte: T("montagecap.liste.chargement") })]);
    const pied = el("div", { class: "dzMcPied", style: "justify-content:flex-end" },
      [bouton("montagecap.commun.fermer", { on: { click: () => fermer() } })]);
    const v = dialogue(T("montagecap.liste.titre"), { "data-dz-montage-liste": true }, corps, pied, 520);
    fermer = () => v.remove();
    piege(v, fermer);
    document.body.appendChild(v);
    pied.querySelector("button").focus();
    try {
      const { j } = await api("/api/capture-montage/captures");
      corps.replaceChildren();
      if (!j.captures.length) corps.appendChild(el("div", { class: "dzMcN", texte: T("montagecap.liste.vide") }));
      for (const c of j.captures) {
        const quand = c.cree_utc ? new Date(c.cree_utc).toLocaleString() : "—";
        corps.appendChild(el("div", { class: "dzMcL", style: "justify-content:space-between", "data-dz-montage-capture": c.id }, [
          el("span", { "data-dz-brut": true, texte: T("montagecap.liste.ligne",
            { quand, duree: horloge(c.duree_ms), clics: c.clics }) + (c.montage ? " · " + T("montagecap.liste.monte") : "") }),
          bouton("montagecap.liste.monter", { "data-dz-montage-monter": c.id, on: { click: () => { fermer(); ouvrir(c.id); } } },
            "dz-media-film")]));
      }
    } catch (e) {
      corps.replaceChildren(el("div", { class: "dzMcE", "data-dz-brut": true, texte: T("montagecap.erreur.chargement", { msg: e.message }) }));
    }
  }

  // ── l'éditeur ──
  let ouverture = false;            // revue finale : deux « Monter » rapides n'ouvrent qu'un éditeur
  async function ouvrir(id) {
    if (ouverture || document.querySelector("[data-dz-montage-editeur]")) return;
    ouverture = true;
    let d;
    try { d = (await api(`/api/capture-montage/${encodeURIComponent(id)}`)).j; }
    catch (e) { ouverture = false; return erreurSeule(e.message); }
    ouverture = false;
    const duree = d.capture.duree_ms, evts = d.evenements;
    let m = d.montage, modifie = false, sale = () => { modifie = true; etat.textContent = T("montagecap.etat.modifie"); };
    let fermer = () => {};

    // aperçu
    const video = el("video", { src: `/api/capture-montage/${id}/video`, preload: "auto", playsinline: true,
      style: "display:none" });
    const toile = el("canvas", { "data-dz-montage-apercu": true, style: "display:block;background:#000;max-width:100%" });
    const ctx = toile.getContext("2d");
    const temps = el("span", { class: "dzMcN", "data-dz-brut": true, "data-dz-montage-temps": true });
    const lire = bouton("montagecap.apercu.lire", { "data-dz-montage-lire": true }, "dz-media-lecture");
    const frise = el("div", { class: "dzMcF", "data-dz-montage-frise": true, title: T("montagecap.apercu.frise") });
    const tete = el("span", { style: "width:2px;background:var(--brand,#f0b429);z-index:3" });
    const tMs = () => Math.round((video.currentTime || 0) * 1000);
    function peindreApercu() {
      const [ol, oh] = FORMATS[m.format];
      const larg = 520, haut = Math.round(larg * oh / ol);
      const l2 = m.format === "9:16" ? Math.round(360 * ol / oh) : larg, h2 = m.format === "9:16" ? 360 : haut;
      if (toile.width !== l2 || toile.height !== h2) { toile.width = l2; toile.height = h2; }
      ctx.fillStyle = "#000"; ctx.fillRect(0, 0, l2, h2);
      if (video.videoWidth) {
        const f = fenetre(m, tMs(), video.videoWidth, video.videoHeight, m.format);
        ctx.drawImage(video, f.sx, f.sy, f.sl, f.sh, 0, 0, l2, h2);
      }
      const segs = segments(m, duree);
      temps.textContent = T("montagecap.apercu.temps", { t: horloge(tMs()), d: horloge(duree),
        sortie: horloge(versSortie(duree, segs)) });
      tete.style.left = `${(100 * tMs()) / Math.max(1, duree)}%`;
    }
    let boucle = 0;
    function tourner() {
      const l = lecture(m, tMs());
      if (l.saut != null) video.currentTime = l.saut / 1000;
      video.playbackRate = Math.min(16, l.vitesse);
      video.muted = l.vitesse > 1;
      peindreApercu();
      cancelAnimationFrame(boucle);
      boucle = video.paused ? 0 : requestAnimationFrame(tourner);
    }
    lire.addEventListener("click", () => {
      if (video.paused) { video.play().catch(() => {}); cancelAnimationFrame(boucle); boucle = requestAnimationFrame(tourner); }
      else video.pause();
    });
    video.addEventListener("play", () => lire.replaceChildren(glyphe("dz-media-pause"), document.createTextNode(T("montagecap.apercu.pause"))));
    video.addEventListener("pause", () => lire.replaceChildren(glyphe("dz-media-lecture"), document.createTextNode(T("montagecap.apercu.lire"))));
    video.addEventListener("seeked", peindreApercu);
    video.addEventListener("loadeddata", peindreApercu);
    frise.addEventListener("pointerdown", (ev) => {
      const r = frise.getBoundingClientRect();
      video.currentTime = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * duree / 1000;
      peindreApercu();
    });
    function peindreFrise() {
      const pc = (t) => `${(100 * t) / Math.max(1, duree)}%`;
      const enfants = [];
      for (const c of m.coupes) enfants.push(el("span", { style: `left:${pc(c.t0)};width:${pc(c.t1 - c.t0)};background:${c.mode === "couper" ? "rgba(229,72,77,.45)" : "rgba(229,72,77,.22)"}` }));
      for (const z of m.zooms) enfants.push(el("span", { style: `left:${pc(z.t0)};width:${pc(z.t1 - z.t0)};top:4px;bottom:auto;height:10px;background:rgba(240,180,41,.75)` }));
      for (const h of m.chapitres) enfants.push(el("span", { style: `left:${pc(h.t)};width:2px;background:#7aa2f7` }));
      for (const e of evts) if (e.type === "clic") enfants.push(el("span", { style: `left:${pc(e.t)};width:1px;top:auto;height:8px;background:#9aa4ae` }));
      frise.replaceChildren(...enfants, tete);
    }

    // formats
    const formats = el("div", { class: "dzMcL", role: "group", "aria-label": T("montagecap.format.titre") },
      Object.keys(FORMATS).map((f) => {
        const b = el("button", { type: "button", class: "dzMcB", "data-dz-montage-format": f, texte: f,
          title: T("montagecap.format.f" + f.replace(":", "x")) });
        b.addEventListener("click", () => { m = Object.assign({}, m, { format: f }); sale(); tout(); });
        return b;
      }));

    // listes réglables
    const sec = (cle, icone, attrs, enfants) => el("div", Object.assign({ class: "dzMcS" }, attrs),
      [el("div", { class: "dzMcH" }, [glyphe(icone), document.createTextNode(T(cle))])].concat(enfants));
    const secondes = (v, surChange, cle) => {
      const i = el("input", { type: "number", class: "dzMcI", step: "0.1", min: "0", max: String(duree / 1000),
        value: (v / 1000).toFixed(1), style: "width:64px", "aria-label": T(cle) });
      i.addEventListener("change", () => { const n = parseFloat(i.value); if (isFinite(n)) surChange(Math.round(n * 1000)); });
      return i;
    };
    const supprimer = (liste, id_) => {
      const b = el("button", { type: "button", class: "dzMcB", "data-dz-montage-supprimer": liste, title: T("montagecap.commun.supprimer"),
        "aria-label": T("montagecap.commun.supprimer"), style: "padding:3px 7px" }, [glyphe("dz-action-supprimer")]);
      b.firstChild.style.marginRight = "0";
      b.addEventListener("click", () => { m = retirer(m, liste, id_); sale(); tout(); });
      return b;
    };
    const zooms = el("div", { style: "display:flex;flex-direction:column;gap:4px" });
    const coupes = el("div", { style: "display:flex;flex-direction:column;gap:4px" });
    const chapitres = el("div", { style: "display:flex;flex-direction:column;gap:4px" });
    function peindreListes() {
      zooms.replaceChildren(...(m.zooms.length ? m.zooms.map((z, i) => {
        const niveau = el("input", { type: "range", min: String(K_MIN), max: String(K_MAX), step: "0.1", value: String(z.k),
          "aria-label": T("montagecap.zoom.niveau"), style: "width:80px" });
        const val = el("span", { class: "dzMcN", "data-dz-brut": true, texte: `×${Number(z.k).toFixed(1)}` });
        niveau.addEventListener("input", () => { val.textContent = `×${Number(niveau.value).toFixed(1)}`; });
        niveau.addEventListener("change", () => { m = modifier(m, "zooms", z.id, { k: Number(niveau.value) }); sale(); tout(); });
        return el("div", { class: "dzMcL", "data-dz-montage-zoom": z.id }, [
          el("span", { texte: T("montagecap.zoom.ligne", { n: i + 1 }) }),
          secondes(z.t0, (v) => { m = normaliserZooms(modifier(m, "zooms", z.id, { t0: v }), duree); sale(); tout(); }, "montagecap.zoom.debut"),
          secondes(z.t1, (v) => { m = normaliserZooms(modifier(m, "zooms", z.id, { t1: v }), duree); sale(); tout(); }, "montagecap.zoom.fin"),
          niveau, val, supprimer("zooms", z.id)]);
      }) : [el("div", { class: "dzMcN", texte: T("montagecap.zoom.aucun") })]));
      coupes.replaceChildren(...(m.coupes.length ? m.coupes.map((c) => {
        const mode = el("select", { class: "dzMcI", "aria-label": T("montagecap.coupe.mode"), "data-dz-montage-mode": c.id },
          ["accelerer", "couper"].map((x) => el("option", { value: x, texte: T("montagecap.coupe." + x) })));
        mode.value = c.mode;
        mode.addEventListener("change", () => { m = modifier(m, "coupes", c.id, { mode: mode.value }); sale(); tout(); });
        const vit = el("select", { class: "dzMcI", "aria-label": T("montagecap.coupe.vitesse"), disabled: c.mode === "couper" },
          VITESSES.map((v) => el("option", { value: String(v), texte: `×${v}` })));
        vit.value = String(c.vitesse);
        vit.addEventListener("change", () => { m = modifier(m, "coupes", c.id, { vitesse: Number(vit.value) }); sale(); tout(); });
        return el("div", { class: "dzMcL", "data-dz-montage-coupe": c.id }, [
          el("span", { "data-dz-brut": true, texte: `${horloge(c.t0)} – ${horloge(c.t1)}` }), mode, vit, supprimer("coupes", c.id)]);
      }) : [el("div", { class: "dzMcN", texte: T("montagecap.coupe.aucune") })]));
      chapitres.replaceChildren(...m.chapitres.map((h, i) => {
        const titre = el("input", { type: "text", class: "dzMcI", maxlength: "80", value: h.titre, placeholder: libelleChapitre(h, i, T),
          "aria-label": T("montagecap.chapitre.nom"), style: "flex:1;min-width:120px" });
        titre.addEventListener("change", () => { m = modifier(m, "chapitres", h.id, { titre: titre.value.slice(0, 80) }); sale(); });
        return el("div", { class: "dzMcL", "data-dz-montage-chapitre": h.id }, [
          el("span", { "data-dz-brut": true, texte: horloge(h.t) }), titre, supprimer("chapitres", h.id)]);
      }));
    }
    const zoomIci = bouton("montagecap.zoom.ajouter", { "data-dz-montage-zoom-ici": true, on: { click: () => {
      const c = clicProche(evts, tMs());
      m = ajouterZoom(m, tMs(), c.x, c.y, (m.zooms[0] && m.zooms[0].k) || 1.8, duree); sale(); tout(); } } }, "dz-action-zoom-avant");
    const chapIci = bouton("montagecap.chapitre.ajouter", { "data-dz-montage-chapitre-ici": true, on: { click: () => {
      m = ajouterChapitre(m, tMs(), ecranA(evts, tMs())); sale(); tout(); } } }, "dz-nav-chapitres");

    // sous-titres
    const source = el("select", { class: "dzMcI", "data-dz-montage-st": true, "aria-label": T("montagecap.st.source") },
      ["aucun", "texte", "transcrire"].map((x) => el("option", { value: x, texte: T("montagecap.st." + x) })));
    const texte = el("textarea", { class: "dzMcI", rows: "3", maxlength: "20000", "data-dz-montage-st-texte": true,
      placeholder: T("montagecap.st.texte_aide"), "aria-label": T("montagecap.st.texte_aide"), style: "resize:vertical" });
    const langue = el("select", { class: "dzMcI", "aria-label": T("montagecap.st.langue") },
      ["fr", "en"].map((x) => el("option", { value: x, texte: x.toUpperCase() })));
    const noteSt = el("div", { class: "dzMcN" });
    const lireSt = () => {
      m = Object.assign({}, m, { sous_titres: { source: source.value, texte: texte.value, langue: langue.value } });
      texte.style.display = source.value === "texte" ? "" : "none";
      noteSt.textContent = source.value === "transcrire" ? T("montagecap.st.payant") : source.value === "texte" ? T("montagecap.st.gratuit") : "";
    };
    source.addEventListener("change", () => { lireSt(); sale(); });
    texte.addEventListener("change", () => { lireSt(); sale(); });
    langue.addEventListener("change", () => { lireSt(); sale(); });

    // pied, résultat
    const etat = el("div", { class: "dzMcN", "data-dz-montage-etat": true, role: "status", style: "margin-right:auto" });
    const resultat = el("div", { "data-dz-montage-resultat": true, style: "display:none;flex-direction:column;gap:6px" });
    const proposer = bouton("montagecap.pied.proposer", { "data-dz-montage-proposer": true });
    const enregistrer = bouton("montagecap.pied.enregistrer", { "data-dz-montage-enregistrer": true });
    const rendre = bouton("montagecap.pied.rendre", { "data-dz-montage-rendre": true }, "dz-media-rendre", true);
    const fermerB = bouton("montagecap.commun.fermer", { "data-dz-montage-fermer": true });
    const occupe = (oui) => { [proposer, enregistrer, rendre].forEach((b) => { b.disabled = oui; }); };
    proposer.addEventListener("click", async () => {
      occupe(true);
      try { m = (await api(`/api/capture-montage/${id}/proposer`, json({}))).j.montage; sale(); tout(); }
      catch (e) { etat.textContent = T("montagecap.erreur.action", { msg: e.message }); }
      occupe(false);
    });
    enregistrer.addEventListener("click", async () => {
      occupe(true);
      try {
        const r = await api(`/api/capture-montage/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ montage: titresRemplis(m, T) }) });
        m = r.j.montage; modifie = false; tout(); etat.textContent = T("montagecap.etat.enregistre");
      } catch (e) { etat.textContent = T("montagecap.erreur.action", { msg: e.message }); }
      occupe(false);
    });
    async function lancerRendu(confirmation) {
      occupe(true);
      resultat.style.display = "none";
      etat.textContent = T("montagecap.etat.rendu");
      try {
        m = titresRemplis(m, T); tout();
        const corps = Object.assign({ montage: m, titre: T("montagecap.rendu.titre_auto", { quand: new Date().toLocaleString() }) },
          confirmation || {});
        const { statut, j } = await api(`/api/capture-montage/${id}/rendre`, json(corps));
        if (statut === 409 && !j.devis) throw new Error(j.detail || "409");
        if (j.ok) { modifie = false; montrerRendu(j); etat.textContent = T("montagecap.etat.fini"); }
        else montrerDevis(j.devis || {}, statut === 409);
      } catch (e) { etat.textContent = T("montagecap.erreur.action", { msg: e.message }); }
      occupe(false);
    }
    rendre.addEventListener("click", () => lancerRendu(null));
    function montrerDevis(devis, change) {
      resultat.style.display = "flex";
      if (!devis.ok) {
        resultat.replaceChildren(el("div", { class: "dzMcE", "data-dz-montage-devis": "sans-cle", texte: T("montagecap.devis.sans_cle") }));
        etat.textContent = "";
        return;
      }
      const usd = Number(devis.usd || 0).toFixed(4);
      const confirmer = bouton("montagecap.devis.confirmer", { "data-dz-montage-confirmer": true }, null, true);
      confirmer.addEventListener("click", () => lancerRendu({ confirme_cout: true, max_usd: Number(devis.usd || 0) }));
      resultat.replaceChildren(el("div", { "data-dz-montage-devis": "ok", "data-dz-brut": true,
        texte: T(change ? "montagecap.devis.change" : "montagecap.devis.texte", { usd, fournisseur: devis.label || devis.provider || "—",
          duree: horloge((devis.duration_s || 0) * 1000) }) }), el("div", { class: "dzMcL" }, [confirmer]));
      etat.textContent = T("montagecap.etat.devis");
    }
    function montrerRendu(j) {
      resultat.style.display = "flex";
      const chap = el("textarea", { class: "dzMcI", rows: "4", readonly: true, "data-dz-montage-chapitres-texte": true,
        "aria-label": T("montagecap.rendu.chapitres") });
      chap.value = j.chapitres_texte || "";
      const st = j.sous_titres || {};
      const planifier = bouton("montagecap.rendu.planifier", { "data-dz-montage-planifier": true }, "dz-action-ajouter-calendrier");
      const biblio = bouton("montagecap.rendu.biblio", { "data-dz-montage-biblio": true }, "dz-nav-bibliotheque");
      const plan = el("div", { class: "dzMcN", "data-dz-montage-plan": true, role: "status" });
      planifier.addEventListener("click", async () => {
        planifier.disabled = true;
        try {
          await api("/api/schedule", json(brouillon(j, T("montagecap.rendu.titre_post"), m.format)));
          plan.textContent = T("montagecap.rendu.planifie");
        } catch (e) { plan.textContent = T("montagecap.erreur.action", { msg: e.message }); planifier.disabled = false; }
      });
      biblio.addEventListener("click", () => { fermer(); window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: "library" } })); });
      resultat.replaceChildren(
        el("div", { "data-dz-brut": true, "data-dz-montage-fichier": true, texte: T("montagecap.rendu.texte", { fichier: j.fichier, duree: horloge(j.duree_s * 1000) }) }),
        st.etat && st.etat !== "aucun" ? el("div", { class: st.etat === "graves" ? "dzMcN" : "dzMcE", "data-dz-montage-st-etat": st.etat,
          texte: T("montagecap.st_etat." + st.etat, { n: st.repliques || 0 }) }) : null,
        el("div", { class: "dzMcH", texte: T("montagecap.rendu.chapitres") }), chap,
        el("div", { class: "dzMcL" }, [planifier, biblio]), plan, el("div", { class: "dzMcN", texte: T("montagecap.rendu.canaux") }));
    }

    function tout() {
      for (const b of formats.children) b.setAttribute("aria-pressed", String(b.getAttribute("data-dz-montage-format") === m.format));
      source.value = m.sous_titres.source; texte.value = m.sous_titres.texte; langue.value = m.sous_titres.langue;
      lireSt();
      peindreListes(); peindreFrise(); peindreApercu();
    }

    const gauche = el("div", { style: "display:flex;flex-direction:column;gap:8px;width:520px;flex:none;overflow:auto" }, [
      el("div", { style: "display:flex;justify-content:center;background:#000;flex:none" }, [toile]), video,
      el("div", { class: "dzMcL" }, [lire, temps]), frise,
      el("div", { class: "dzMcN", texte: T("montagecap.apercu.legende") }),
      el("div", { class: "dzMcH", texte: T("montagecap.format.titre") }), formats,
      el("div", { class: "dzMcN", texte: T("montagecap.format.note") }), resultat]);
    const droite = el("div", { style: "display:flex;flex-direction:column;gap:10px;flex:1;min-width:340px;overflow:auto" }, [
      sec("montagecap.zoom.titre", "dz-action-zoom-avant", { "data-dz-montage-zooms": true }, [zooms, el("div", { class: "dzMcL" }, [zoomIci])]),
      sec("montagecap.coupe.titre", "dz-media-vitesse", { "data-dz-montage-coupes": true }, [coupes,
        el("div", { class: "dzMcN", texte: T("montagecap.coupe.note") })]),
      sec("montagecap.chapitre.titre", "dz-nav-chapitres", { "data-dz-montage-chapitres": true }, [chapitres, el("div", { class: "dzMcL" }, [chapIci])]),
      sec("montagecap.st.titre", "dz-media-sous-titres", { "data-dz-montage-sous-titres": true }, [
        el("div", { class: "dzMcL" }, [source, langue]), texte, noteSt]),
      el("div", { class: "dzMcN", texte: T("montagecap.editeur.note") })]);
    const pied = el("div", { class: "dzMcPied" }, [etat, proposer, enregistrer, fermerB, rendre]);
    const quand = d.capture.cree_utc ? new Date(d.capture.cree_utc).toLocaleString() : "";
    const v = dialogue(T("montagecap.editeur.titre", { quand }), { "data-dz-montage-editeur": id },
      el("div", { class: "dzMcC" }, [gauche, droite]), pied, 980);
    fermer = () => {
      if (modifie && !v.hasAttribute("data-dz-montage-confirme-fermeture")) {
        v.setAttribute("data-dz-montage-confirme-fermeture", "");
        etat.textContent = T("montagecap.etat.fermer_modifie");
        return;
      }
      cancelAnimationFrame(boucle); video.pause(); video.removeAttribute("src"); v.remove();
    };
    fermerB.addEventListener("click", () => fermer());
    piege(v, fermer);
    document.body.appendChild(v);
    if (d.propose) etat.textContent = T("montagecap.etat.propose", { zooms: m.zooms.length, coupes: m.coupes.length,
      chapitres: m.chapitres.length });
    tout();
    rendre.focus();
  }

  function erreurSeule(msg) {
    let fermer = () => {};
    const pied = el("div", { class: "dzMcPied", style: "justify-content:flex-end" },
      [bouton("montagecap.commun.fermer", { on: { click: () => fermer() } })]);
    const v = dialogue(T("montagecap.liste.titre"), { "data-dz-montage-erreur": true },
      el("div", { class: "dzMcC" }, [el("div", { class: "dzMcE", "data-dz-brut": true, texte: T("montagecap.erreur.chargement", { msg }) })]), pied, 460);
    fermer = () => v.remove();
    piege(v, fermer);
    document.body.appendChild(v);
  }

  // ── entrées posées de l'extérieur (dz-capture.js n'est pas modifié) ──
  // la boîte de fin d'une capture rangée : « Monter la capture »
  window.addEventListener("dz-capture:fin", (ev) => {
    const det = ev.detail || {};
    if (!det.capture || !det.id) return;
    setTimeout(() => {
      const fin = document.querySelector("[data-dz-capture-fin]");
      const pied = fin && fin.querySelector('[role="dialog"]') && fin.querySelector('[role="dialog"]').lastElementChild;
      if (!pied || pied.querySelector("[data-dz-montage-depuis-fin]")) return;
      const b = bouton("montagecap.entree.monter", { "data-dz-montage-depuis-fin": det.id, on: { click: () => { fin.remove(); ouvrir(det.id); } } },
        "dz-media-film");
      b.style.cssText = "font:inherit;font-size:12.5px;padding:5px 12px;margin-right:auto";
      pied.insertBefore(b, pied.firstChild);
    }, 0);
  });
  // la boîte de départ : « Monter une capture… » (ferme la boîte de départ par Échap, son propre chemin)
  function poserEntreeDepart(boite) {
    const pied = boite.querySelector('[role="dialog"]') && boite.querySelector('[role="dialog"]').lastElementChild;
    if (!pied || pied.querySelector("[data-dz-montage-depuis-depart]")) return;
    const b = bouton("montagecap.entree.liste", { "data-dz-montage-depuis-depart": true, on: { click: () => {
      boite.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      liste(); } } }, "dz-media-film");
    b.style.marginRight = "auto";
    pied.insertBefore(b, pied.firstChild);
  }
  new MutationObserver((muts) => {
    for (const mu of muts) for (const n of mu.addedNodes) {
      if (n.nodeType === 1 && n.hasAttribute && n.hasAttribute("data-dz-capture-boite")) poserEntreeDepart(n);
    }
  }).observe(document.body, { childList: true });

  window.__dzMontageCapture = { ouvrir, liste };
}
