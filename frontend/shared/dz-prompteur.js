// dz-prompteur.js — lot SVR (15/11/2026) : le TEXTE d'une prise et le PROMPTEUR de l'enregistreur de l'app
// (conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md, § 11).
// SOURCE : frontend/shared/dz-prompteur.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-prompteur.js, chargée par
// frontend/dist/index.html (`<script type="module">`, AVANT dz-capture.js). Aucune dépendance au runtime React.
// Banc : backend/tests/test_capture_ecran.py (section [T]).
//
// - Groupe « Texte et prompteur » de la boîte de départ de la capture (window.__dzPrompteur.groupeCapture()) :
//   * « Garder le texte de ma voix » : pendant la prise, la reconnaissance vocale DU NAVIGATEUR (gratuite ; la voix passe
//     par son service, d'où la case, jamais cochée d'office) écrit ce qui est dit ; à la fin, le texte est rangé avec la
//     prise (PUT /api/capture/sessions/<id>/texte) ;
//   * « Prompteur » : le texte d'une prise précédente, ou un texte collé, défile pendant la prise.
// - Le prompteur [data-dz-prompteur] est posé sur le corps de la page, HORS de #root : en mode « L'app seule » il n'est
//   pas dans l'image. Si l'image prend tout l'onglet, il n'est PAS affiché (il serait filmé) et la pastille le dit.
//   Vitesse en mots par minute, pause (bouton ou Ctrl+Alt+P), taille du texte, retour au début.
// - « Textes des prises… » : la liste des prises, leur texte (lu, corrigé, envoyé au prompteur) et, pour une prise sans
//   texte, la transcription PAYANTE de sa piste de voix — par les routes de la dictée (devis affiché, puis accord) : ce
//   module ne dépense rien sans le clic « Transcrire ».
// API : window.__dzPrompteur = {groupeCapture(), ouvrirTextes(), disponible()}.
if (!window.__dzPrompteur) {
  const T = (cle, vars) => (typeof window.dzT === "function" ? window.dzT(cle, vars) : cle);
  const lire = (k) => { try { return window.localStorage.getItem(k); } catch (e) { return null; } };
  const ecrire = (k, v) => { try { window.localStorage.setItem(k, v); } catch (e) { /* stockage indisponible */ } };
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
  const S = {
    voile: "position:fixed;inset:0;z-index:2147483005;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:720px;max-width:96vw;max-height:90vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:8px",
    groupe: "display:flex;flex-direction:column;gap:5px",
    titreG: "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    erreur: "font-size:12px;color:var(--red,#e5484d)",
    champ: "font:inherit;font-size:12px;padding:3px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));min-width:0",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    bouton: "font:inherit;font-size:12.5px;padding:4px 10px;border-radius:0;cursor:pointer;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    principal: "font:inherit;font-size:12.5px;padding:4px 10px;border-radius:0;cursor:pointer;background:var(--brand,#f0b429);color:#111;border:1px solid var(--brand,#f0b429);font-weight:600",
    prompteur: "position:fixed;top:46px;left:50%;transform:translateX(-50%);z-index:2147483002;width:min(920px,72vw);border-radius:0;background:rgba(8,10,13,.9);color:#fff;border:1px solid var(--brd-hard,#2a3138);box-shadow:0 8px 28px rgba(0,0,0,.5);font:12px/1.3 system-ui,sans-serif;display:flex;flex-direction:column",
    fenetre: "position:relative;height:190px;overflow:hidden",
    repere: "position:absolute;left:0;right:0;top:38%;height:0;border-top:2px solid var(--brand,#f0b429);opacity:.55;pointer-events:none",
    barre: "display:flex;align-items:center;gap:6px;padding:4px 8px;border-top:1px solid #2a3138;flex-wrap:wrap",
  };
  async function api(methode, url, corps) {
    const r = await fetch(url, { method: methode, headers: corps ? { "Content-Type": "application/json" } : undefined,
      body: corps ? JSON.stringify(corps) : undefined });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((d && typeof d.detail === "string" && d.detail) || String(r.status));
    return d;
  }
  const ctorSR = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const langue = () => (typeof window.dzLang === "function" && window.dzLang() === "en" ? "en-US" : "fr-FR");
  const quand = (iso) => { const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleString(langue(), { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); };
  const minutes = (ms) => { const s = Math.round((ms || 0) / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
  const bouton = (texte, clic, style, attrs) => el("button", Object.assign({ type: "button", style: style || S.bouton, texte, on: { click: clic } }, attrs || {}));

  // ── le groupe de la boîte de départ ──
  let dernierGroupe = null;
  function groupeCapture() {
    const memo = (() => { try { return JSON.parse(lire("dz_prompteur_options") || "{}") || {}; } catch (e) { return {}; } })();
    const garder = el("input", { type: "checkbox", "data-dz-prompteur-option": "transcrire", "aria-label": T("prompteur.groupe.garder") });
    garder.checked = memo.transcrire === true && !!ctorSR();
    garder.disabled = !ctorSR();
    const choix = el("select", { style: S.champ + ";flex:1", "data-dz-prompteur-option": "choix", "aria-label": T("prompteur.groupe.choix") });
    const aire = el("textarea", { rows: 4, maxlength: 60000, style: S.champ + ";resize:vertical;width:100%;box-sizing:border-box;display:none", "data-dz-prompteur-option": "texte",
      placeholder: T("prompteur.groupe.coller"), "aria-label": T("prompteur.groupe.coller") });
    let prises = [];
    const remplir = (garde) => {
      choix.textContent = "";
      choix.appendChild(el("option", { value: "", texte: T("prompteur.groupe.sans") }));
      for (const p of prises) if (p.texte) choix.appendChild(el("option", { value: p.id, texte: T("prompteur.groupe.prise", { date: quand(p.cree_utc), extrait: p.texte.extrait.slice(0, 48) }) }));
      choix.appendChild(el("option", { value: "coller", texte: T("prompteur.groupe.libre") }));
      choix.value = garde && Array.from(choix.options).some((o) => o.value === garde) ? garde : "";
    };
    const choisir = async () => {
      aire.style.display = choix.value ? "" : "none";
      if (choix.value === "coller") { aire.value = lire("dz_prompteur_texte") || ""; return; }
      if (!choix.value) { aire.value = ""; return; }
      try { aire.value = (await api("GET", "/api/capture/sessions/" + choix.value + "/texte")).texte || ""; } catch (e) { aire.value = ""; }
    };
    choix.addEventListener("change", choisir);
    remplir("");
    api("GET", "/api/capture/textes").then((r) => { prises = r.prises || []; remplir(choix.value); }).catch(() => {});
    const noeud = el("div", { style: S.groupe, "data-dz-prompteur-groupe": true }, [
      el("div", { style: S.titreG, texte: T("prompteur.groupe.titre") }),
      el("label", { style: "display:flex;align-items:center;gap:8px;cursor:pointer" }, [garder, el("span", { texte: T("prompteur.groupe.garder") })]),
      el("div", { style: S.note, texte: T(ctorSR() ? "prompteur.groupe.note" : "prompteur.groupe.indisponible") }),
      el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [choix, bouton(T("prompteur.groupe.textes"), () => ouvrirTextes(), S.bouton, { "data-dz-prompteur-textes": true })]),
      aire,
    ]);
    dernierGroupe = { choix, aire, remplir: (id) => api("GET", "/api/capture/textes").then((r) => { prises = r.prises || []; remplir(id); return choisir(); }).catch(() => {}),
      poser: (texte) => { remplir("coller"); aire.style.display = ""; aire.value = texte; ecrire("dz_prompteur_texte", texte); } };
    return { noeud, valeur() {
      const texte = choix.value ? aire.value.trim() : "";
      if (choix.value === "coller") ecrire("dz_prompteur_texte", texte);
      ecrire("dz_prompteur_options", JSON.stringify({ transcrire: garder.checked }));
      return { transcrire: garder.checked, prompteur: texte ? { texte } : null };
    } };
  }

  // ── pendant la prise : le texte en direct et le prompteur ──
  let prise = null;                    // {id, debut, sr, segments, actif, ui}
  function ecouterVoix(p) {
    const SR = ctorSR(); if (!SR) return;
    const lancer = () => {
      if (!prise || prise !== p || !p.actif) return;
      const r = new SR();
      r.lang = langue(); r.continuous = true; r.interimResults = false;
      r.onresult = (ev) => {
        for (let i = ev.resultIndex; i < ev.results.length; i++) {
          const res = ev.results[i], mots = res && res.isFinal && res[0] ? String(res[0].transcript || "").trim() : "";
          if (mots) p.segments.push({ t: Math.max(0, Math.round(performance.now() - p.debut)), texte: mots });
        }
      };
      r.onerror = (ev) => { if (ev && (ev.error === "not-allowed" || ev.error === "service-not-allowed" || ev.error === "network" || ev.error === "audio-capture")) { p.actif = false; p.panne = ev.error; } };
      r.onend = () => { if (p.actif) setTimeout(lancer, 150); };          // le navigateur clôt l'écoute après un silence : on la reprend
      try { r.start(); p.sr = r; } catch (e) { p.actif = false; }
    };
    p.actif = true; lancer();
  }
  function poserPrompteur(texte) {
    const memo = (() => { try { return JSON.parse(lire("dz_prompteur_reglages") || "{}") || {}; } catch (e) { return {}; } })();
    let mpm = Math.min(260, Math.max(60, Number(memo.mpm) || 140)), taille = Math.min(56, Math.max(18, Number(memo.taille) || 30)), pause = false, y = 0, dernier = 0, arret = false;
    const mots = Math.max(1, texte.split(/\s+/).filter(Boolean).length);
    const corps = el("div", { style: "position:absolute;left:0;right:0;top:0;padding:0 22px;white-space:pre-wrap;font-weight:600;will-change:transform", texte, "data-dz-prompteur-texte": true });
    const fenetre = el("div", { style: S.fenetre }, [corps, el("div", { style: S.repere })]);
    const vitesse = el("span", { style: "font-variant-numeric:tabular-nums;min-width:86px" });
    const btnPause = bouton("", () => { pause = !pause; peindre(); }, S.bouton + ";padding:2px 9px;font-size:12px", { "data-dz-prompteur-pause": true });
    const petit = (texteB, nom, clic) => bouton(texteB, clic, S.bouton + ";padding:2px 9px;font-size:12px", { title: T(nom), "aria-label": T(nom) });
    const garder = () => ecrire("dz_prompteur_reglages", JSON.stringify({ mpm, taille }));
    const barre = el("div", { style: S.barre }, [btnPause,
      petit("−", "prompteur.barre.ralentir", () => { mpm = Math.max(60, mpm - 10); garder(); peindre(); }), vitesse,
      petit("+", "prompteur.barre.accelerer", () => { mpm = Math.min(260, mpm + 10); garder(); peindre(); }),
      petit("A−", "prompteur.barre.reduire", () => { taille = Math.max(18, taille - 2); garder(); peindre(); }),
      petit("A+", "prompteur.barre.agrandir", () => { taille = Math.min(56, taille + 2); garder(); peindre(); }),
      bouton(T("prompteur.barre.debut"), () => { y = 0; peindre(); }, S.bouton + ";padding:2px 9px;font-size:12px"),
      el("span", { style: S.note, texte: T("prompteur.barre.note") })]);
    const noeud = el("div", { style: S.prompteur, "data-dz-capture-ui": true, "data-dz-prompteur": true, role: "region", "aria-label": T("prompteur.barre.titre") }, [fenetre, barre]);
    function peindre() {
      corps.style.fontSize = taille + "px"; corps.style.lineHeight = "1.35";
      btnPause.textContent = T(pause ? "prompteur.barre.reprendre" : "prompteur.barre.pause");
      vitesse.textContent = T("prompteur.barre.vitesse", { n: mpm });
      corps.style.transform = `translateY(${Math.round(fenetre.clientHeight * 0.38 - taille * 0.7 - y)}px)`;
    }
    const pas = (t) => {
      if (arret) return;
      const dt = dernier ? Math.min(0.1, (t - dernier) / 1000) : 0; dernier = t;
      const haut = corps.scrollHeight || 1;
      if (!pause && y < haut) { y += (haut / mots) * (mpm / 60) * dt; corps.style.transform = `translateY(${Math.round(fenetre.clientHeight * 0.38 - taille * 0.7 - y)}px)`; }
      requestAnimationFrame(pas);
    };
    const touche = (e) => { if (e.ctrlKey && e.altKey && e.code === "KeyP") { e.preventDefault(); pause = !pause; peindre(); } };
    window.addEventListener("keydown", touche, true);
    document.body.appendChild(noeud); peindre(); requestAnimationFrame(pas);
    return { noeud, retirer() { arret = true; window.removeEventListener("keydown", touche, true); noeud.remove(); } };
  }
  window.addEventListener("dz-capture:debut", (ev) => {
    const s = window.__dzCapture && typeof window.__dzCapture.session === "function" ? window.__dzCapture.session() : null;
    if (!s) return;
    const o = (s.options && s.options.texte) || {};
    prise = { id: (ev.detail && ev.detail.id) || s.id, debut: s.debut || performance.now(), sr: null, segments: [], actif: false, panne: "", ui: null };
    if (o.transcrire) ecouterVoix(prise);
    if (o.prompteur && o.prompteur.texte) {
      if (s.horsImage) prise.ui = poserPrompteur(String(o.prompteur.texte));
      else {                                              // il serait filmé : on ne l'affiche pas, et on le dit
        const p = document.querySelector("[data-dz-capture-pastille]");
        if (p) p.appendChild(el("span", { texte: T("prompteur.barre.coupe"), style: "font-size:11px;color:#f0b429", "data-dz-prompteur-coupe": true }));
      }
    }
  });
  window.addEventListener("dz-capture:fin", async (ev) => {
    const p = prise; prise = null;
    if (!p) return;
    p.actif = false;
    try { if (p.sr) p.sr.stop(); } catch (e) { /* déjà arrêtée */ }
    if (p.ui) p.ui.retirer();
    const ok = ev.detail && ev.detail.capture;
    let message = "";
    if (ok && p.segments.length) {
      await new Promise((r) => setTimeout(r, 400));          // les derniers mots arrivent après l'arrêt de l'écoute
      try {
        const t = await api("PUT", "/api/capture/sessions/" + p.id + "/texte", { source: "navigateur", langue: langue(),
          texte: p.segments.map((x) => x.texte).join("\n"), segments: p.segments });
        message = T("prompteur.fin.garde", { n: t.texte.split(/\s+/).filter(Boolean).length });
      } catch (e) { message = T("prompteur.fin.erreur", { msg: (e && e.message) || "—" }); }
    } else if (ok && p.panne) message = T("prompteur.fin.panne");
    else if (ok && p.sr) message = T("prompteur.fin.rien");
    const fin = document.querySelector("[data-dz-capture-fin] [data-dz-capture-resultat]");
    if (message && fin && fin.parentNode) fin.parentNode.appendChild(el("div", { style: S.note, texte: message, "data-dz-prompteur-fin": true }));
  });

  // ── « Textes des prises… » : lire, corriger, envoyer au prompteur, transcrire (payant, sur devis) ──
  let boite = null;
  function fermerTextes() { if (boite) { boite.remove(); boite = null; } }
  async function ouvrirTextes() {
    if (boite) return;
    const liste = el("div", { style: S.groupe, "data-dz-prompteur-liste": true });
    const etat = el("div", { style: S.note, role: "status" });
    const aire = el("textarea", { rows: 9, maxlength: 60000, style: S.champ + ";resize:vertical;width:100%;box-sizing:border-box", "aria-label": T("prompteur.textes.texte"), "data-dz-prompteur-edition": true });
    const actions = el("div", { style: S.ligne });
    const edition = el("div", { style: S.groupe + ";display:none" }, [el("div", { style: S.titreG, texte: T("prompteur.textes.texte") }), aire, actions]);
    let ouverte = null, occupe = false;
    const dire = (m, erreur) => { etat.textContent = m || ""; etat.style.cssText = erreur ? S.erreur : S.note; };
    const faire = async (action) => { if (occupe) return; occupe = true; dire(T("prompteur.textes.patience")); try { await action(); } catch (e) { dire((e && e.message) || "—", true); } occupe = false; };
    function ouvrir(p, texte) {
      ouverte = p; edition.style.display = ""; aire.value = texte || "";
      actions.textContent = "";
      actions.appendChild(bouton(T("prompteur.textes.enregistrer"), () => faire(async () => {
        await api("PUT", "/api/capture/sessions/" + p.id + "/texte", { source: "saisi", langue: langue(), texte: aire.value });
        dire(T("prompteur.textes.enregistre")); await charger(); }), S.principal, { "data-dz-prompteur-enregistrer": true }));
      actions.appendChild(bouton(T("prompteur.textes.prompteur"), () => { if (dernierGroupe && dernierGroupe.aire.isConnected) { dernierGroupe.poser(aire.value); fermerTextes(); } else { ecrire("dz_prompteur_texte", aire.value); dire(T("prompteur.textes.pret")); } }));
      actions.appendChild(bouton(T("prompteur.textes.copier"), () => { aire.select(); try { navigator.clipboard.writeText(aire.value); } catch (e) { /* presse-papiers fermé : le texte reste sélectionné */ } }));
    }
    // la transcription payante : devis (gratuit), puis accord, puis envoi plafonné au montant affiché
    async function transcrire(p, ligne) {
      const r = await fetch("/api/capture/sessions/" + p.id + "/pistes/voix");
      if (!r.ok) throw new Error(T("prompteur.textes.sansvoix"));
      const blob = await r.blob(), corps = () => { const f = new FormData(); f.append("file", blob, "voix.webm"); return f; };
      const d = await fetch("/api/dictation/estimate", { method: "POST", body: corps() }).then(async (x) => ({ ok: x.ok, j: await x.json().catch(() => ({})) }));
      if (!d.ok || !d.j.available) throw new Error((d.j && (d.j.reason || (typeof d.j.detail === "string" && d.j.detail))) || T("prompteur.textes.indisponible"));
      const devis = el("div", { style: S.ligne + ";border:1px solid var(--brand,#f0b429);padding:5px 8px", "data-dz-prompteur-devis": p.id }, [
        el("span", { texte: T("prompteur.textes.devis", { n: Math.round(d.j.duration_s), fournisseur: d.j.label || d.j.provider, usd: Number(d.j.usd).toFixed(2) }) }),
        bouton(T("prompteur.textes.transcrire.oui"), () => faire(async () => {
          const f = corps(); f.append("max_usd", String(d.j.usd)); f.append("language", langue());
          const x = await fetch("/api/dictation", { method: "POST", body: f }), j = await x.json().catch(() => ({}));
          if (!x.ok) throw new Error((typeof j.detail === "string" && j.detail) || String(x.status));
          await api("PUT", "/api/capture/sessions/" + p.id + "/texte", { source: "transcription", langue: langue(), texte: j.text || "" });
          devis.remove(); dire(T("prompteur.textes.transcrit")); await charger(); ouvrir(p, j.text || "");
        }), S.principal, { "data-dz-prompteur-accord": true }),
        bouton(T("prompteur.textes.transcrire.non"), () => { devis.remove(); dire(""); })]);
      ligne.after(devis); dire("");
    }
    async function charger() {
      const r = await api("GET", "/api/capture/textes");
      liste.textContent = "";
      for (const p of r.prises || []) {
        const ligne = el("div", { style: S.ligne + ";flex-wrap:nowrap;gap:6px;border-bottom:1px solid var(--brd-soft,#222830);padding-bottom:4px", "data-dz-prompteur-prise": p.id }, [
          el("div", { style: "flex:1;min-width:0;display:flex;flex-direction:column" }, [
            el("span", { texte: T("prompteur.textes.prise", { date: quand(p.cree_utc), duree: minutes(p.duree_ms) }) }),
            el("span", { style: S.note + ";overflow:hidden;text-overflow:ellipsis;white-space:nowrap", texte: p.texte ? `${T("prompteur.source." + p.texte.source)} · ${T("prompteur.textes.mots", { n: p.texte.mots })} · ${p.texte.extrait}` : T("prompteur.textes.sanstexte") })]),
          p.texte ? bouton(T("prompteur.textes.ouvrir"), () => faire(async () => { const t = await api("GET", "/api/capture/sessions/" + p.id + "/texte"); ouvrir(p, t.texte); dire(""); }))
            : bouton(T("prompteur.textes.ecrire"), () => { ouvrir(p, ""); dire(""); }),
          p.voix ? bouton(T("prompteur.textes.transcrire"), () => faire(() => transcrire(p, ligne)), S.bouton, { "data-dz-prompteur-transcrire": p.id }) : null]);
        liste.appendChild(ligne);
      }
      if (!(r.prises || []).length) liste.appendChild(el("div", { style: S.note, texte: T("prompteur.textes.vide") }));
      if (dernierGroupe && dernierGroupe.choix.isConnected) dernierGroupe.remplir(dernierGroupe.choix.value);
    }
    boite = el("div", { style: S.voile, "data-dz-capture-ui": true, "data-dz-prompteur-boite": true }, [
      el("div", { style: S.boite, role: "dialog", "aria-modal": "true", "aria-label": T("prompteur.textes.titre") }, [
        el("div", { style: S.tete, texte: T("prompteur.textes.titre") }),
        el("div", { style: S.corps }, [el("div", { style: S.note, texte: T("prompteur.textes.note") }), liste, etat, edition]),
        el("div", { style: S.pied }, [bouton(T("prompteur.textes.fermer"), fermerTextes, S.bouton, { "data-dz-prompteur-fermer": true })]),
      ])]);
    boite.addEventListener("pointerdown", (ev) => { if (ev.target === boite) fermerTextes(); });
    boite.addEventListener("keydown", (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fermerTextes(); } });
    document.body.appendChild(boite);
    try { await charger(); } catch (e) { dire((e && e.message) || "—", true); }
  }

  window.__dzPrompteur = { groupeCapture, ouvrirTextes, disponible: () => !!ctorSR() };
}
