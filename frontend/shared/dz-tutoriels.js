// dz-tutoriels.js — t319 (28/10/2026, lot D5 « tutoriels et parcours partagés depuis les captures ») : plan
// docs/superpowers/plans/2026-10-28-t319-tutoriels.md, spec boîte à outils §8.7.
// SOURCE : frontend/shared/dz-tutoriels.js ; copie OCTET POUR OCTET : frontend/dist/shared/, chargée par
// frontend/dist/index.html (`<script type="module">`, après dz-montage-capture.js). Aucun maillon de bundle ;
// dz-capture.js, dz-montage-capture.js et dz-agent*.js NON modifiés : les entrées sont posées de l'extérieur
// (« Tutoriel… » dans le pied de l'éditeur de montage, « Parcours… » dans la boîte « Filmer l'app »).
// - Le BROUILLON DE TUTORIEL d'une capture (/api/tutoriels/captures/{id}) : étapes à garder, titres et phrases FR/EN ;
//   « Fabriquer les brouillons » écrit des brouillons aux formats du guide, des fiches didactiques et du catalogue SANS
//   les publier ; « Exporter le parcours » prépare un `.dzparcours` que l'utilisateur télécharge par un lien.
// - Le REJEU d'un parcours importé : un panneau NON modal (la page reste visible) ; « Montrer » pose le POINTEUR de
//   « Demander » (/shared/dz-agent-pointeur.js) sur le vrai bouton de CETTE installation : l'action vient du serveur,
//   construite depuis le catalogue local, relue par actionSure ; la page n'est jamais cliquée à la place de
//   l'utilisateur, et rien ne bouge sans son geste. Les textes du parcours sont posés par textContent.
// API : window.__dzTutoriels = {ouvrir(id), parcours(), rejouer(pid)}. Banc : backend/tests/test_tutoriels_ecran.py.
import { creerPointeur } from "./dz-agent-pointeur.js";
import { candidats, choisir, composer, etapes as etapesAction } from "./dz-agent-logique.js";
import { MAX_TITRE, MAX_PHRASE, MAX_MOTS, compterMots, borner, dansLangue, actionSure, fenetreEtape, horloge, etapeA }
  from "./dz-tutoriels-logique.js";

if (!window.__dzTutoriels) {
  const T = (cle, vars) => (typeof window.dzT === "function" ? window.dzT(cle, vars) : cle);
  const lang = () => { const l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang; return l === "en" ? "en" : "fr"; };
  const vue = () => { try { return window.localStorage.getItem("dz_view") || "quick"; } catch (e) { return "quick"; } };
  const attendre = (ms) => new Promise((ok) => setTimeout(ok, ms));
  const glyphe = (cle) => {
    const s = document.createElement("span");
    s.className = "dzTuGl";
    s.innerHTML = typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: 14 }) : "";   // glyphe de l'app, jamais un texte
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
  function bouton(cle, attrs, icone, principal) {
    const b = el("button", { type: "button", class: principal ? "dzTuP" : "dzTuB", texte: T(cle) });
    if (icone) b.insertBefore(glyphe(icone), b.firstChild);
    return poser(b, attrs);
  }
  const CSS = ".dzTuGl{display:inline-flex;align-items:center;vertical-align:middle;margin-right:5px}.dzTuGl svg{display:block}"
    + ".dzTuV{position:fixed;inset:0;z-index:2147483006;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center}"
    + ".dzTuD{display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-base,var(--ink,#cfd6e2));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif;max-width:96vw;max-height:94vh}"
    + ".dzTuT{padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))}"
    + ".dzTuC{padding:12px 14px;overflow:auto;display:flex;flex-direction:column;gap:10px}"
    + ".dzTuPied{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))}"
    + ".dzTuB,.dzTuP{font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;display:inline-flex;align-items:center;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee))}"
    + ".dzTuP{background:var(--brand,#f0b429);color:#111;border-color:var(--brand,#f0b429);font-weight:600}"
    + ".dzTuB:disabled,.dzTuP:disabled{opacity:.45;cursor:not-allowed}"
    + ".dzTuH{font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))}"
    + ".dzTuL{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:12px}"
    + ".dzTuN{font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))}"
    + ".dzTuE{font-size:12px;color:var(--red,#e5484d)}"
    + ".dzTuI{font:inherit;font-size:12px;padding:3px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));box-sizing:border-box}"
    + ".dzTuS{display:grid;grid-template-columns:22px 1fr 1fr;gap:4px 8px;align-items:start;padding:8px 0;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830))}"
    + ".dzTuS[data-ecartee]{opacity:.5}"
    + ".dzTuR{position:fixed;left:16px;bottom:16px;width:380px;max-width:calc(100vw - 32px);z-index:2147482990;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brand,#f0b429);color:var(--txt-base,var(--ink,#cfd6e2));box-shadow:0 12px 40px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif}"
    + ".dzTuR video{display:block;width:100%;max-height:200px;background:#000}"
    + ".dzTuR .dzTuC{gap:6px;padding:10px 12px}";
  document.head.appendChild(el("style", { "data-dz-tuto-ui": true, texte: CSS }));

  const api = async (url, opts) => {
    const r = await fetch(url, opts);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
    return j;
  };
  const json = (methode, corps) => ({ method: methode, headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });

  function piege(voile, fermer) {
    voile.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fermer(); return; }
      if (ev.key !== "Tab") return;
      const f = Array.from(voile.querySelectorAll("button, input, select, textarea, a[href]")).filter((x) => !x.disabled);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
      else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); }
    });
  }
  function dialogue(titre, attrs, corps, pied, largeur) {
    return el("div", Object.assign({ class: "dzTuV", "data-dz-tuto-ui": true }, attrs), [
      el("div", { class: "dzTuD", role: "dialog", "aria-modal": "true", "aria-label": titre, style: `width:${largeur}px` }, [
        el("div", { class: "dzTuT", texte: titre }), corps, pied])]);
  }

  // ── le brouillon de tutoriel d'une capture ──
  let ouverture = false;
  async function ouvrir(cid) {
    if (ouverture || document.querySelector("[data-dz-tuto-brouillon]")) return;
    ouverture = true;
    let d;
    try { d = await api(`/api/tutoriels/captures/${encodeURIComponent(cid)}`); }
    catch (e) { ouverture = false; return erreurSeule(e.message); }
    ouverture = false;
    let b = d.brouillon, modifie = false, occupe = false;
    let fermer = () => {};
    const etat = el("span", { class: "dzTuN", "data-dz-tuto-etat": true, style: "flex:1 0 100%" });
    const resultat = el("div", { class: "dzTuL", "data-dz-tuto-resultat": true });
    const sale = () => { modifie = true; etat.textContent = T("tuto.etat.modifie"); };
    const titreFr = el("input", { class: "dzTuI", "data-dz-tuto-titre": "fr", maxlength: MAX_TITRE, placeholder: T("tuto.brouillon.titre_fr"),
      "aria-label": T("tuto.brouillon.titre_fr"), style: "flex:1;min-width:200px" });
    const titreEn = el("input", { class: "dzTuI", "data-dz-tuto-titre": "en", maxlength: MAX_TITRE, placeholder: T("tuto.brouillon.titre_en"),
      "aria-label": T("tuto.brouillon.titre_en"), style: "flex:1;min-width:200px" });
    for (const [inp, k] of [[titreFr, "fr"], [titreEn, "en"]]) inp.addEventListener("input", () => { b.titre[k] = borner(inp.value, MAX_TITRE); sale(); });
    const chapitres = el("div", { class: "dzTuN", "data-dz-tuto-chapitres": true });
    const liste = el("div", { "data-dz-tuto-etapes": true });

    const CLES = { "titre.fr": "tuto.etape.titre_fr", "titre.en": "tuto.etape.titre_en", "phrase.fr": "tuto.etape.phrase_fr",
      "phrase.en": "tuto.etape.phrase_en" };
    function champ(e, cle, k, long) {
      const n = el(long ? "textarea" : "input", { class: "dzTuI", "data-dz-tuto-champ": `${cle}.${k}`, maxlength: long ? MAX_PHRASE : MAX_TITRE,
        "aria-label": T(CLES[`${cle}.${k}`]), placeholder: T(CLES[`${cle}.${k}`]), rows: long ? 2 : false,
        style: "width:100%;resize:vertical" });
      n.value = e[cle][k] || "";
      n.addEventListener("input", () => { e[cle][k] = borner(n.value, long ? MAX_PHRASE : MAX_TITRE); sale(); compte(); });
      return n;
    }
    function peindre() {
      titreFr.value = b.titre.fr || ""; titreEn.value = b.titre.en || "";
      chapitres.textContent = b.chapitres.length
        ? T("tuto.brouillon.chapitres", { liste: b.chapitres.map((h) => `${horloge(h.t)} ${h.titre || h.ecran || "—"}`).join(" · ") }) : "";
      liste.replaceChildren();
      if (!b.etapes.length) liste.appendChild(el("div", { class: "dzTuN", texte: T("tuto.brouillon.vide") }));
      b.etapes.forEach((e, i) => {
        const garde = el("input", { type: "checkbox", "data-dz-tuto-garde": e.id, "aria-label": T("tuto.etape.garder") });
        garde.checked = e.garde !== false;
        const ligne = el("div", { class: "dzTuS", "data-dz-tuto-etape": e.id }, [
          garde,
          el("div", { class: "dzTuN", "data-dz-brut": true, style: "grid-column:2 / 4",
            texte: T("tuto.etape.entete", { n: i + 1, quand: horloge(e.t), ecran: e.ecran || "—", fiche: e.fiche || T("tuto.etape.sans_fiche") }) }),
          el("span"), champ(e, "titre", "fr"), champ(e, "titre", "en"),
          el("span"), champ(e, "phrase", "fr", true), champ(e, "phrase", "en", true),
          el("span"), el("div", { class: "dzTuN", "data-dz-tuto-mots": e.id, style: "grid-column:2 / 4" })]);
        if (e.garde === false) ligne.setAttribute("data-ecartee", "");
        garde.addEventListener("change", () => {
          e.garde = garde.checked;
          if (garde.checked) ligne.removeAttribute("data-ecartee"); else ligne.setAttribute("data-ecartee", "");
          sale();
        });
        liste.appendChild(ligne);
      });
      compte();
    }
    function compte() {
      for (const e of b.etapes) {
        const n = liste.querySelector(`[data-dz-tuto-mots="${e.id}"]`);
        if (!n) continue;
        const m = Math.max(compterMots(e.phrase.fr), compterMots(e.phrase.en));
        n.textContent = T(m > MAX_MOTS ? "tuto.etape.mots_trop" : "tuto.etape.mots", { n: m, max: MAX_MOTS });
      }
    }
    async function agir(btn, f) {
      if (occupe) return;
      occupe = true;
      for (const x of pied.querySelectorAll("button")) x.disabled = true;
      try { await f(); }
      catch (e) { etat.textContent = ""; resultat.replaceChildren(el("span", { class: "dzTuE", "data-dz-brut": true, texte: T("tuto.erreur.action", { msg: e.message }) })); }
      finally { occupe = false; for (const x of pied.querySelectorAll("button")) x.disabled = false; }
    }
    const proposerB = bouton("tuto.brouillon.proposer", { "data-dz-tuto-proposer": true, title: T("tuto.brouillon.proposer_aide") }, "dz-action-retour");
    const enregistrerB = bouton("tuto.brouillon.enregistrer", { "data-dz-tuto-enregistrer": true });
    const fabriquerB = bouton("tuto.brouillon.fabriquer", { "data-dz-tuto-fabriquer": true, title: T("tuto.brouillon.fabriquer_aide") }, "dz-nav-guide", true);
    const exporterB = bouton("tuto.brouillon.exporter", { "data-dz-tuto-exporter": true, title: T("tuto.brouillon.exporter_aide") }, "dz-action-exporter");
    const fermerB = bouton("tuto.commun.fermer", { "data-dz-tuto-fermer": true });
    proposerB.addEventListener("click", () => agir(proposerB, async () => {
      b = (await api(`/api/tutoriels/captures/${cid}/proposer`, { method: "POST" })).brouillon;
      peindre(); sale();
    }));
    enregistrerB.addEventListener("click", () => agir(enregistrerB, async () => {
      b = (await api(`/api/tutoriels/captures/${cid}`, json("PUT", { brouillon: b }))).brouillon;
      modifie = false; peindre(); etat.textContent = T("tuto.etat.enregistre");
    }));
    fabriquerB.addEventListener("click", () => agir(fabriquerB, async () => {
      etat.textContent = T("tuto.etat.fabrication");
      const r = await api(`/api/tutoriels/captures/${cid}/fabriquer`, json("POST", { brouillon: b }));
      etat.textContent = "";
      resultat.replaceChildren(el("span", { class: "dzTuN", "data-dz-brut": true, "data-dz-tuto-fabrique": true,
        texte: T("tuto.fabrique.resultat", { scenes: r.scenes, fiches: r.fiches, exemples: r.exemples, dossier: r.dossier }) }));
    }));
    let lien = null;
    exporterB.addEventListener("click", () => agir(exporterB, async () => {
      etat.textContent = T("tuto.etat.export");
      const r = await fetch(`/api/tutoriels/captures/${cid}/parcours`, json("POST", { brouillon: b }));
      if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(typeof j.detail === "string" ? j.detail : String(r.status)); }
      const m = /filename="?([A-Za-z0-9._-]+)"?/.exec(r.headers.get("content-disposition") || "");
      const nom = m ? m[1] : "parcours.dzparcours";
      if (lien) URL.revokeObjectURL(lien);
      lien = URL.createObjectURL(await r.blob());
      etat.textContent = "";
      // un LIEN que l'utilisateur clique lui-même : rien n'est téléchargé sans son geste
      const a = el("a", { href: lien, download: nom, class: "dzTuB", "data-dz-tuto-telecharger": true, style: "text-decoration:none" });
      a.appendChild(glyphe("dz-action-telecharger"));
      a.appendChild(document.createTextNode(T("tuto.export.telecharger", { nom })));
      resultat.replaceChildren(a, el("span", { class: "dzTuN", texte: T("tuto.export.note") }));
    }));
    const pied = el("div", { class: "dzTuPied", style: "justify-content:flex-end" }, [etat, proposerB, enregistrerB, exporterB, fermerB, fabriquerB]);
    const corps = el("div", { class: "dzTuC" }, [
      el("div", { class: "dzTuN", texte: T("tuto.brouillon.intro") }),
      el("div", { class: "dzTuL" }, [titreFr, titreEn]), chapitres,
      el("div", { class: "dzTuH", texte: T("tuto.brouillon.etapes") }), liste, resultat]);
    const quand = d.capture.cree_utc ? new Date(d.capture.cree_utc).toLocaleString() : "";
    const v = dialogue(T("tuto.brouillon.titre", { quand }), { "data-dz-tuto-brouillon": cid }, corps, pied, 860);
    fermer = () => {
      if (modifie && !v.hasAttribute("data-dz-tuto-confirme-fermeture")) {
        v.setAttribute("data-dz-tuto-confirme-fermeture", "");
        etat.textContent = T("tuto.etat.fermer_modifie");
        return;
      }
      if (lien) URL.revokeObjectURL(lien);
      v.remove();
    };
    fermerB.addEventListener("click", () => fermer());
    piege(v, fermer);
    document.body.appendChild(v);
    if (d.propose) etat.textContent = T("tuto.etat.propose", { etapes: b.etapes.length, chapitres: b.chapitres.length });
    peindre();
    fabriquerB.focus();
  }

  function erreurSeule(msg) {
    let fermer = () => {};
    const pied = el("div", { class: "dzTuPied", style: "justify-content:flex-end" }, [bouton("tuto.commun.fermer", { on: { click: () => fermer() } })]);
    const v = dialogue(T("tuto.brouillon.titre", { quand: "" }), { "data-dz-tuto-erreur": true },
      el("div", { class: "dzTuC" }, [el("div", { class: "dzTuE", "data-dz-brut": true, texte: T("tuto.erreur.chargement", { msg }) })]), pied, 460);
    fermer = () => v.remove();
    piege(v, fermer);
    document.body.appendChild(v);
    pied.querySelector("button").focus();
  }

  // ── les parcours importés ──
  async function parcours() {
    if (document.querySelector("[data-dz-tuto-parcours]")) return;
    let fermer = () => {};
    const corps = el("div", { class: "dzTuC", style: "min-height:80px" });
    const etat = el("div", { class: "dzTuN", "data-dz-tuto-import-etat": true });
    const fichier = el("input", { type: "file", accept: ".dzparcours,application/zip", "data-dz-tuto-fichier": true, style: "display:none" });
    // le sélecteur de fichier s'ouvre par le LIBELLÉ cliqué par l'utilisateur (aucun clic simulé)
    const importer = el("label", { class: "dzTuB", "data-dz-tuto-importer": true, tabindex: "0", role: "button" }, [glyphe("dz-action-importer"),
      document.createTextNode(T("tuto.parcours.importer")), fichier]);
    importer.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); fichier.showPicker ? fichier.showPicker() : null; } });
    const pied = el("div", { class: "dzTuPied" }, [importer, el("span", { style: "flex:1" }),
      bouton("tuto.commun.fermer", { "data-dz-tuto-fermer": true, on: { click: () => fermer() } })]);
    const v = dialogue(T("tuto.parcours.titre"), { "data-dz-tuto-parcours": true },
      el("div", {}, [el("div", { class: "dzTuC" }, [el("div", { class: "dzTuN", texte: T("tuto.parcours.intro") }), etat]), corps]), pied, 560);
    fermer = () => v.remove();
    piege(v, fermer);
    document.body.appendChild(v);
    async function charger() {
      corps.replaceChildren(el("div", { class: "dzTuN", texte: T("tuto.parcours.chargement") }));
      try {
        const j = await api("/api/tutoriels/parcours");
        corps.replaceChildren();
        if (!j.parcours.length) corps.appendChild(el("div", { class: "dzTuN", texte: T("tuto.parcours.vide") }));
        for (const p of j.parcours) {
          const retirer = bouton("tuto.parcours.retirer", { "data-dz-tuto-retirer": p.id }, "dz-action-supprimer");
          retirer.addEventListener("click", async () => {
            if (!retirer.hasAttribute("data-confirme")) { retirer.setAttribute("data-confirme", ""); retirer.lastChild.textContent = T("tuto.parcours.retirer_confirmer"); return; }
            try { await api(`/api/tutoriels/parcours/${p.id}`, { method: "DELETE" }); charger(); }
            catch (e) { etat.textContent = T("tuto.erreur.action", { msg: e.message }); }
          });
          corps.appendChild(el("div", { class: "dzTuL", style: "justify-content:space-between", "data-dz-tuto-ligne": p.id }, [
            el("span", { "data-dz-brut": true, texte: `${dansLangue(p.titre, lang()) || T("tuto.parcours.sans_titre")} · `
              + T("tuto.parcours.ligne", { etapes: p.etapes, montrables: p.montrables, duree: horloge(p.duree_ms) }) }),
            el("span", { class: "dzTuL" }, [
              bouton("tuto.parcours.rejouer", { "data-dz-tuto-rejouer": p.id, on: { click: () => { fermer(); rejouer(p.id); } } }, "dz-media-lecture", true),
              retirer])]));
        }
      } catch (e) {
        corps.replaceChildren(el("div", { class: "dzTuE", "data-dz-brut": true, texte: T("tuto.erreur.chargement", { msg: e.message }) }));
      }
    }
    fichier.addEventListener("change", async () => {
      const f = fichier.files && fichier.files[0];
      fichier.value = "";
      if (!f) return;
      etat.textContent = T("tuto.parcours.import_en_cours");
      try {
        await api("/api/tutoriels/parcours/importer", { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: f });
        etat.textContent = T("tuto.parcours.importe");
        await charger();
      } catch (e) { etat.textContent = T("tuto.erreur.import", { msg: e.message }); }
    });
    await charger();
    pied.querySelector("[data-dz-tuto-fermer]").focus();
  }

  // ── le rejeu : panneau non modal, pointeur de « Demander » ──
  let panneau = null;
  async function rejouer(pid) {
    if (panneau) panneau.fermer();
    let p;
    try { p = await api(`/api/tutoriels/parcours/${encodeURIComponent(pid)}`); }
    catch (e) { return erreurSeule(e.message); }
    let i = 0, tour = 0;
    const video = el("video", { src: `/api/tutoriels/parcours/${pid}/video`, controls: true, playsinline: true, preload: "metadata",
      "data-dz-tuto-video": true });
    const numero = el("div", { class: "dzTuH", "data-dz-tuto-numero": true });
    const titre = el("div", { "data-dz-brut": true, "data-dz-tuto-etape-titre": true, style: "font-weight:600;color:var(--txt-hi,#e6e9ee)" });
    const phrase = el("div", { class: "dzTuN", "data-dz-brut": true, "data-dz-tuto-etape-phrase": true });
    const statut = el("div", { class: "dzTuN", "data-dz-tuto-statut": true, role: "status" });
    const prec = bouton("tuto.rejeu.precedent", { "data-dz-tuto-precedent": true }, "dz-action-element-precedent");
    const montrerB = bouton("tuto.rejeu.montrer", { "data-dz-tuto-montrer": true, title: T("tuto.rejeu.montrer_aide") }, "dz-edit-pointe-fleche", true);
    const suiv = bouton("tuto.rejeu.suivant", { "data-dz-tuto-suivant": true }, "dz-action-element-suivant");
    const fermerB = bouton("tuto.commun.fermer", { "data-dz-tuto-rejeu-fermer": true });
    const r = el("div", { class: "dzTuR", role: "region", "aria-label": T("tuto.rejeu.titre"), "data-dz-tuto-rejeu": pid, "data-dz-tuto-ui": true }, [
      el("div", { class: "dzTuT", "data-dz-brut": true, texte: `${T("tuto.rejeu.titre")} · ${dansLangue(p.titre, lang()) || T("tuto.parcours.sans_titre")}` }),
      video,
      el("div", { class: "dzTuC" }, [numero, titre, phrase, statut]),
      el("div", { class: "dzTuPied" }, [prec, montrerB, suiv, el("span", { style: "flex:1" }), fermerB])]);
    const pointeur = creerPointeur({
      depart: () => { const q = montrerB.getBoundingClientRect(); return { x: q.x + q.width / 2, y: q.y + q.height / 2 }; },
      ignorer: (cible) => r.contains(cible),
    });
    function aller(k, lire, deplacer = true) {
      pointeur.effacer(); tour++;
      i = Math.max(0, Math.min(p.etapes.length - 1, k));
      const e = p.etapes[i];
      numero.textContent = T("tuto.rejeu.numero", { n: i + 1, total: p.etapes.length, quand: horloge(e.t) });
      titre.textContent = dansLangue(e.titre, lang()) || T("tuto.rejeu.sans_titre", { n: i + 1 });
      phrase.textContent = dansLangue(e.phrase, lang());
      statut.textContent = e.action ? "" : T("tuto.rejeu.absent");
      montrerB.disabled = !e.action;
      prec.disabled = i === 0; suiv.disabled = i === p.etapes.length - 1;
      if (deplacer) { try { video.currentTime = fenetreEtape(e).debut; } catch (x) { /* métadonnées pas encore lues */ } }
      if (lire) video.play().catch(() => {});
    }
    video.addEventListener("loadedmetadata", () => { try { video.currentTime = fenetreEtape(p.etapes[i]).debut; } catch (x) { /* rien */ } }, { once: true });
    // la tête de lecture déplacée à la main : l'étape affichée suit (sans déplacer la vidéo)
    video.addEventListener("seeked", () => {
      const k = etapeA(p.etapes, Math.round(video.currentTime * 1000));
      if (k !== i) aller(k, false, false);
    });
    video.addEventListener("timeupdate", () => { if (!video.paused && video.currentTime >= fenetreEtape(p.etapes[i]).fin) video.pause(); });
    prec.addEventListener("click", () => aller(i - 1, true));
    suiv.addEventListener("click", () => aller(i + 1, true));
    montrerB.addEventListener("click", () => montrerEtape(p.etapes[i]));
    const fermer = () => { tour++; pointeur.effacer(); video.pause(); video.removeAttribute("src"); r.remove(); if (panneau && panneau.r === r) panneau = null; };
    fermerB.addEventListener("click", fermer);
    r.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !pointeur.actif()) { ev.preventDefault(); fermer(); } });
    panneau = { r, fermer };
    document.body.appendChild(r);
    aller(0, false);
    montrerB.disabled ? suiv.focus() : montrerB.focus();

    // « Montrer » : aller à l'écran puis poser le pointeur sur le bouton de CETTE installation (jamais de clic)
    async function montrerEtape(e) {
      const a = actionSure(e && e.action);
      const moi = ++tour;
      pointeur.effacer();
      if (!a) { statut.textContent = T("tuto.rejeu.absent"); return; }
      statut.textContent = "";
      for (const s of etapesAction(a, vue())) {
        if (moi !== tour) return;
        if (s.faire === "aller") { window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: s.vue } })); await attendre(350); }
        else if (s.faire === "reglages") {
          try { const u = new URL(window.location.href); u.searchParams.set("section", s.section); window.history.replaceState(null, "", u); } catch (x) { /* URL figée */ }
          window.dispatchEvent(new CustomEvent("dz-reglages-section", { detail: { section: s.section } }));
          await attendre(300);
        } else if (s.faire === "pointer") await pointer(a, moi);
      }
    }
    async function pointer(a, moi) {
      const libelle = a[lang()] || a.fr || a.en;
      if (a.cadre) {
        let t = null;
        for (const fin = Date.now() + 8000; !t && Date.now() < fin;) {     // un lab met quelques secondes à s'ouvrir
          t = await demanderAuCadre(a);
          if (moi !== tour) return;
          if (!t) await attendre(250);
        }
        if (!t) { statut.textContent = T("tuto.rejeu.introuvable"); return; }
        return pointeur.montrer({ rect: () => {
          if (!t.cadre.isConnected) return null;
          const q = t.cadre.getBoundingClientRect();
          return q.width > 0 && q.height > 0 ? composer(q, t.interne) : null;
        } }, libelle, t.cadre.contentWindow);
      }
      let n = null;
      for (const fin = Date.now() + 4000; !n && Date.now() < fin;) {
        const c = candidats(document, a.selecteur, a.libelle).filter((x) => !r.contains(x.noeud) && !x.noeud.closest("[data-dz-tuto-ui],.dzAgentTiroir,.dzAgentBtn"));
        const k = choisir(c, a, lang());
        n = k >= 0 ? c[k].noeud : null;
        if (moi !== tour) return;
        if (!n) await attendre(150);
      }
      if (!n) { statut.textContent = T("tuto.rejeu.introuvable"); return; }
      n.scrollIntoView({ block: "center" });
      await attendre(60);
      if (moi !== tour || !n.isConnected) return;
      pointeur.montrer(n, libelle);
    }
  }

  // un lab en cadre intégré : son répondeur /shared/dz-agent-cadre.js rend le rectangle (même origine, ce cadre, notre id)
  let numeroCadre = 0;
  function demanderAuCadre(a) {
    const cadres = Array.from(document.querySelectorAll("iframe")).filter((f) => (f.getAttribute("src") || "").includes(a.cadre));
    const cadre = cadres.find((f) => { const q = f.getBoundingClientRect(); return q.width > 0 && q.height > 0; }) || cadres[0];
    if (!cadre || !cadre.contentWindow) return Promise.resolve(null);
    const id = "tuto" + (++numeroCadre);
    return new Promise((ok) => {
      const fini = setTimeout(() => { window.removeEventListener("message", h); ok(null); }, 1500);
      function h(ev) {
        if (ev.origin !== location.origin || ev.source !== cadre.contentWindow) return;
        if (!ev.data || ev.data.dzAgent !== "rect" || ev.data.id !== id) return;
        clearTimeout(fini);
        window.removeEventListener("message", h);
        ok(ev.data.rect ? { cadre, interne: ev.data.rect } : null);
      }
      window.addEventListener("message", h);
      try {
        cadre.contentWindow.postMessage({ dzAgent: "trouve", id, selecteur: a.selecteur, libelle: a.libelle || "", texte: a.texte, lang: lang() }, location.origin);
      } catch (e) { clearTimeout(fini); window.removeEventListener("message", h); ok(null); }
    });
  }

  // ── entrées posées de l'extérieur ──
  function poserDansEditeur(v) {
    const cid = v.getAttribute("data-dz-montage-editeur");
    const pied = v.querySelector(".dzMcPied");
    if (!cid || !pied || pied.querySelector("[data-dz-tuto-depuis-montage]")) return;
    const b = bouton("tuto.entree.tutoriel", { "data-dz-tuto-depuis-montage": cid, title: T("tuto.entree.tutoriel_aide"),
      on: { click: () => ouvrir(cid) } }, "dz-nav-guide");
    b.style.cssText = "font:inherit;font-size:12.5px;padding:5px 12px";
    pied.insertBefore(b, pied.children[1] || null);
  }
  function poserDansDepart(boite) {
    const dlg = boite.querySelector('[role="dialog"]');
    const pied = dlg && dlg.lastElementChild;
    if (!pied || pied.querySelector("[data-dz-tuto-depuis-depart]")) return;
    const b = bouton("tuto.entree.parcours", { "data-dz-tuto-depuis-depart": true, title: T("tuto.entree.parcours_aide"), on: { click: () => {
      boite.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      parcours(); } } }, "dz-media-lecture");
    pied.insertBefore(b, pied.firstChild);
  }
  new MutationObserver((muts) => {
    for (const mu of muts) for (const n of mu.addedNodes) {
      if (n.nodeType !== 1 || !n.hasAttribute) continue;
      if (n.hasAttribute("data-dz-montage-editeur")) poserDansEditeur(n);
      if (n.hasAttribute("data-dz-capture-boite")) setTimeout(() => poserDansDepart(n), 0);
    }
  }).observe(document.body, { childList: true });

  window.__dzTutoriels = { ouvrir, parcours, rejouer };
}
