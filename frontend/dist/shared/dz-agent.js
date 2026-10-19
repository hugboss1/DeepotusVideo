// dz-agent.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md,
// 19/10/2026). SOURCE : frontend/shared/dz-agent.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-agent.js,
// chargée par frontend/dist/index.html (`<script type="module">`, après dz-plafonds.js). Aucune dépendance au runtime
// React : le tiroir vit à côté de la SPA. Le banc backend/tests/test_agent_ecran.py vérifie copies, balise et libellés.
//
// Le tiroir : bouton flottant « Demander » + F1 ; POST /api/agent/demander {question, historique, ecran, lang,
// moteur} ; sous chaque réponse, un bouton par action (Montre-moi / Y aller / Guide). L'historique reste dans
// sessionStorage (dz_agent_hist) ; le moteur choisi dans localStorage (dz_agent_moteur). Un 402 `dz_plafond` est
// traité par la couche /shared/dz-plafonds.js (elle enveloppe window.fetch) : rien à faire ici.
import { etapes, historiqueBorne, choisir, courbe, composer } from "./dz-agent-logique.js";

if (!window.__dzAgent) {
  window.__dzAgent = true;

  const T = (k, v) => (window.dzT ? window.dzT(k, v) : k);
  const lang = () => (window.dzLang === "en" ? "en" : "fr");
  const lire = (s, k) => { try { return s.getItem(k); } catch (e) { return null; } };
  const ecrire = (s, k, v) => { try { s.setItem(k, v); } catch (e) { /* stockage indisponible : rien de grave */ } };
  const vue = () => lire(window.localStorage, "dz_view") || "quick";
  const el = (tag, attrs, enfants) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "on") for (const [e, f] of Object.entries(v)) n.addEventListener(e, f);
      else if (k === "texte") n.textContent = v;
      else n.setAttribute(k, v);
    }
    for (const c of enfants || []) n.appendChild(c);
    return n;
  };

  let hist = [];
  try { hist = historiqueBorne(JSON.parse(lire(window.sessionStorage, "dz_agent_hist") || "[]")); } catch (e) { hist = []; }
  const garder = () => ecrire(window.sessionStorage, "dz_agent_hist", JSON.stringify(historiqueBorne(hist)));

  const css = el("style", { texte: `
.dzAgentBtn{position:fixed;right:18px;bottom:18px;z-index:9990;border:1px solid var(--cyan,#3ee6d0);
 background:var(--bg-panel,#151519);color:var(--ink-strong,#eaf2ff);border-radius:999px;padding:8px 14px;font-family:inherit;font-size:13px;font-weight:600;line-height:1;
 cursor:pointer;box-shadow:0 0 18px var(--cyan-glow,rgba(240,180,41,.33))}
.dzAgentTiroir{position:fixed;top:0;right:0;bottom:0;width:min(400px,100vw);z-index:9991;display:none;flex-direction:column;
 background:var(--bg-panel,#151519);color:var(--ink,#c9d4e8);border-left:1px solid var(--stroke,#2a2930);font-family:inherit;font-size:13px;line-height:1.5}
.dzAgentTiroir[data-ouvert="1"]{display:flex}
.dzAgentTete{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--stroke,#2a2930)}
.dzAgentTete h2{flex:1;margin:0;font-size:14px;color:var(--ink-strong,#eaf2ff)}
.dzAgentFil{flex:1;overflow:auto;padding:12px 14px;display:flex;flex-direction:column;gap:10px}
.dzAgentMsg{white-space:pre-wrap;border-radius:10px;padding:8px 10px;background:var(--bg-panel-2,#1c1c21)}
.dzAgentMsg[data-role="user"]{align-self:flex-end;background:var(--cyan-soft,rgba(62,230,208,.12))}
.dzAgentActions{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.dzAgentActions button,.dzAgentTete button,.dzAgentPied button{background:transparent;color:inherit;border:1px solid var(--stroke,#2a2930);
 border-radius:8px;padding:4px 8px;cursor:pointer;font:inherit}
.dzAgentPied{display:flex;gap:6px;padding:10px 14px;border-top:1px solid var(--stroke,#2a2930)}
.dzAgentPied textarea{flex:1;resize:none;min-height:38px;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:8px;padding:6px}
.dzAgentTete select{background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:6px}
.dzAgentTete button:disabled,.dzAgentPied button:disabled{opacity:.5;cursor:default}
.dzAgentCurseur{position:fixed;left:0;top:0;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;z-index:2147483002;
 pointer-events:none;background:var(--cyan,#f0b429);box-shadow:0 0 16px 4px var(--cyan-glow,rgba(240,180,41,.33))}
.dzAgentHalo{position:fixed;z-index:2147483002;pointer-events:none;border:2px solid var(--cyan,#f0b429);border-radius:10px;
 box-shadow:0 0 0 4px var(--cyan-glow,rgba(240,180,41,.33)),0 0 24px var(--cyan-glow,rgba(240,180,41,.33));transition:opacity .4s}
.dzAgentBulle{position:fixed;z-index:2147483002;pointer-events:none;background:var(--bg-panel,#151519);color:var(--ink-strong,#eaf2ff);
 border:1px solid var(--cyan,#f0b429);border-radius:8px;padding:4px 8px;font-family:inherit;font-size:12px;font-weight:600;line-height:1.3;white-space:nowrap;transition:opacity .4s}
@media (prefers-reduced-motion: reduce){.dzAgentHalo,.dzAgentBulle{transition:none}}` });

  const fil = el("div", { class: "dzAgentFil", role: "log", "aria-live": "polite" });
  const saisie = el("textarea", { placeholder: T("agent.tiroir.placeholder"), "aria-label": T("agent.tiroir.placeholder") });
  const choix = el("select", { "aria-label": T("agent.moteur.libelle"), title: T("agent.moteur.libelle") });
  const btnEnvoyer = el("button", { texte: T("agent.tiroir.envoyer"), on: { click: () => envoyer() } });
  const btnNouvelle = el("button", { texte: "↺", title: T("agent.tiroir.nouvelle"), "aria-label": T("agent.tiroir.nouvelle"),
    on: { click: () => { if (occupe) return; hist = []; garder(); dessiner(); } } });
  const tiroir = el("aside", { id: "dzAgentTiroir", class: "dzAgentTiroir", "aria-label": T("agent.tiroir.titre") }, [
    el("div", { class: "dzAgentTete" }, [
      el("h2", { texte: T("agent.tiroir.titre") }), choix, btnNouvelle,
      el("button", { texte: "×", title: T("agent.tiroir.fermer"), "aria-label": T("agent.tiroir.fermer"), on: { click: () => basculer(false) } }),
    ]),
    fil,
    el("div", { class: "dzAgentPied" }, [saisie, btnEnvoyer]),
  ]);
  const bouton = el("button", { class: "dzAgentBtn", texte: "? " + T("agent.tiroir.bouton"), title: T("agent.tiroir.bouton_titre"),
    "aria-expanded": "false", "aria-controls": "dzAgentTiroir", on: { click: () => basculer() } });

  function basculer(ouvrir) {
    const o = ouvrir === undefined ? tiroir.dataset.ouvert !== "1" : ouvrir;
    const focusDedans = tiroir.contains(document.activeElement);
    tiroir.dataset.ouvert = o ? "1" : "0";
    bouton.setAttribute("aria-expanded", o ? "true" : "false");
    if (o) { chargerMoteurs(); saisie.focus(); }
    else if (focusDedans) bouton.focus();     // le focus ne reste pas dans un tiroir masqué
  }

  async function chargerMoteurs() {
    if (choix.dataset.charge) return;
    choix.dataset.charge = "1";
    try {
      const r = await fetch("/api/agent/etat");
      const j = await r.json();
      choix.replaceChildren(el("option", { value: "", texte: T("agent.moteur.auto") }),
        ...j.moteurs.map((m) => el("option", { value: m.moteur,
          texte: `${m.nom} · ${T(m.cout === "gratuit" ? "agent.moteur.cout_gratuit" : "agent.moteur.cout_payant")}` })));
      choix.value = lire(window.localStorage, "dz_agent_moteur") || "";
    } catch (e) { delete choix.dataset.charge; }
  }
  choix.addEventListener("change", () => ecrire(window.localStorage, "dz_agent_moteur", choix.value));

  // actionsDuMessage : toutes les actions du message d'où vient le clic (l'ancre introuvable renvoie vers ses guides)
  function boutonAction(a, actionsDuMessage) {
    const l = lang();
    const libelle = a.type === "point" ? T("agent.action.montrer", { libelle: a[l] || a.fr })
      : a.type === "guide" ? T("agent.action.guide", { titre: a[l] || a.fr }) : T("agent.action.aller");
    return el("button", { texte: libelle, on: { click: () => executer(a, actionsDuMessage) } });
  }

  function dessiner(enAttente) {
    const msgs = hist.length ? hist : [{ role: "assistant", texte: T("agent.tiroir.accueil") }];
    fil.replaceChildren(...msgs.map((m) => {
      const b = el("div", { class: "dzAgentMsg", "data-role": m.role, texte: m.texte });
      if (m.actions && m.actions.length) b.appendChild(el("div", { class: "dzAgentActions" }, m.actions.map((x) => boutonAction(x, m.actions))));
      return b;
    }));
    if (enAttente) fil.appendChild(el("div", { class: "dzAgentMsg", "data-role": "assistant", texte: T("agent.reponse.reflechit") }));
    fil.scrollTop = fil.scrollHeight;
  }

  // un seul envoi à la fois ; un échec rend la question à la saisie et ne part jamais dans l'historique du serveur
  let occupe = false;
  async function envoyer() {
    const q = saisie.value.trim();
    if (!q || occupe) return;
    occupe = true;
    btnEnvoyer.disabled = true;
    btnNouvelle.disabled = true;
    saisie.value = "";
    const avant = historiqueBorne(hist.filter((m) => !m.erreur)).map(({ role, texte }) => ({ role, texte }));
    const question = { role: "user", texte: q };
    hist.push(question);
    dessiner(true);
    try {
      const r = await fetch("/api/agent/demander", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, historique: avant, ecran: vue(), lang: lang(), moteur: choix.value || "" }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
      if (typeof j.texte !== "string" || !j.texte.trim()) throw new Error("—");
      hist.push({ role: "assistant", texte: j.texte, actions: Array.isArray(j.actions) ? j.actions : [] });
    } catch (e) {
      const i = hist.indexOf(question);
      if (i >= 0) hist.splice(i, 1);
      hist.push({ role: "assistant", texte: T("agent.reponse.erreur", { msg: (e && e.message) || "—" }), erreur: true });
      if (!saisie.value.trim()) saisie.value = q;     // ne pas écraser ce que l'utilisateur a retapé
    } finally {
      occupe = false;
      btnEnvoyer.disabled = false;
      btnNouvelle.disabled = false;
      garder();
      dessiner();
    }
  }

  // ── les actions ──
  const attendre = (ms) => new Promise((ok) => setTimeout(ok, ms));
  function aller(v) { window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: v } })); }
  function ouvrirReglages(section) {
    try { const u = new URL(window.location.href); u.searchParams.set("section", section); window.history.replaceState(null, "", u); } catch (e) { /* URL non modifiable : l'événement suffit */ }
    window.dispatchEvent(new CustomEvent("dz-reglages-section", { detail: { section } }));
  }
  // libelle (facultatif, ex. ".dzNavLbl") : sélecteur RELATIF à l'élément trouvé, du sous-élément dont le texte sert
  // à la comparaison (le rail : l'icône et le badge ne doivent pas brouiller le libellé).
  function candidats(doc, selecteur, libelle) {
    let n = [];
    try { n = Array.from(doc.querySelectorAll(selecteur)); } catch (e) { n = []; }
    return n.map((x) => {
      const r = x.getBoundingClientRect();
      let sous = null;
      try { sous = libelle ? x.querySelector(libelle) : null; } catch (e) { sous = null; }
      return { noeud: x, texte: (sous || x).textContent, titre: x.getAttribute("title") || "", visible: r.width > 0 && r.height > 0 };
    });
  }
  async function trouver(a, delaiMs) {
    const fin = Date.now() + delaiMs;
    do {
      const c = candidats(document, a.selecteur, a.libelle);
      const i = choisir(c, a, lang());
      if (i >= 0) return c[i].noeud;
      await attendre(150);
    } while (Date.now() < fin);
    return null;
  }

  // ── le pointeur à la Clicky : un curseur part du bouton « Demander », décrit un arc (courbe), puis un halo et une
  // bulle se posent sur la cible. Calques éphémères, au-dessus de tout, transparents aux clics. Un seul pointage à la
  // fois : chaque nouveau pointage (ou un clic hors du tiroir) annule le précédent — animation, minuterie, écouteurs.
  const reduit = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  let calques = [], anim = 0, minuterie = 0, suivre = null, tourPointeur = 0;
  function effacerPointeur() {
    if (anim) cancelAnimationFrame(anim);
    if (minuterie) clearTimeout(minuterie);
    anim = 0; minuterie = 0;
    if (suivre) { window.removeEventListener("scroll", suivre, true); window.removeEventListener("resize", suivre); suivre = null; }
    calques.forEach((c) => c.remove());
    calques = [];
  }

  // cible : un nœud DOM, ou {rect: () => ({x, y, w, h}) | null} pour un élément d'un lab en cadre intégré
  function montrer(cible, libelle) {
    effacerPointeur();
    const mesurer = cible.rect ? () => {
      const q = cible.rect() || { x: 0, y: 0, w: 0, h: 0 };
      return { x: q.x, y: q.y, width: q.w, height: q.h, bottom: q.y + q.h };
    } : () => cible.getBoundingClientRect();
    const b = bouton.getBoundingClientRect();
    const depart = { x: b.x + b.width / 2, y: b.y + b.height / 2 };
    const curseur = el("div", { class: "dzAgentCurseur" });
    const halo = el("div", { class: "dzAgentHalo" });
    const bulle = el("div", { class: "dzAgentBulle", texte: libelle });
    halo.style.opacity = "0"; bulle.style.opacity = "0";
    curseur.style.transform = `translate(${depart.x}px,${depart.y}px)`;
    document.body.append(curseur, halo, bulle);
    calques = [curseur, halo, bulle];
    let arrivee = depart, pose = false;
    // recalcule la place de la cible : au départ, puis à chaque défilement / redimensionnement (même pendant l'arc)
    const placer = () => {
      const r = mesurer();
      arrivee = { x: r.x + r.width / 2, y: r.y + r.height / 2 };
      Object.assign(halo.style, { left: r.x - 6 + "px", top: r.y - 6 + "px", width: r.width + 12 + "px", height: r.height + 12 + "px" });
      const hb = bulle.offsetHeight || 24, lb = bulle.offsetWidth || 0;
      const haut = r.y - hb - 10 >= 8 ? r.y - hb - 10 : r.bottom + 10;          // au-dessus, sinon en dessous
      bulle.style.left = Math.max(8, Math.min(r.x, window.innerWidth - lb - 8)) + "px";
      bulle.style.top = Math.max(8, Math.min(haut, window.innerHeight - hb - 8)) + "px";
      if (pose) curseur.style.transform = `translate(${arrivee.x}px,${arrivee.y}px)`;
    };
    placer();
    suivre = () => placer();
    window.addEventListener("scroll", suivre, { capture: true, passive: true });
    window.addEventListener("resize", suivre);
    const finir = () => {
      anim = 0; pose = true;
      curseur.style.transform = `translate(${arrivee.x}px,${arrivee.y}px)`;
      halo.style.opacity = "1"; bulle.style.opacity = "1";
      minuterie = setTimeout(effacerPointeur, 3200);
    };
    if (reduit()) return finir();
    const debut = performance.now(), duree = 700;
    const pas = (t) => {
      const k = Math.max(0, Math.min(1, (t - debut) / duree));
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;         // ease-in-out
      const p = courbe(depart, arrivee, e);
      curseur.style.transform = `translate(${p.x}px,${p.y}px)`;
      if (k < 1) anim = requestAnimationFrame(pas); else finir();
    };
    anim = requestAnimationFrame(pas);
  }
  document.addEventListener("pointerdown", (ev) => { if (calques.length && !tiroir.contains(ev.target)) effacerPointeur(); }, true);

  // un lab en cadre intégré (a.cadre = "/vectorlab/"…) : on demande au répondeur /shared/dz-agent-cadre.js le
  // rectangle de l'élément ; seule une réponse de même origine, venue de CE cadre et portant notre id, compte.
  let numero = 0;
  function demanderAuCadre(a) {
    const cadres = Array.from(document.querySelectorAll("iframe")).filter((f) => (f.getAttribute("src") || "").includes(a.cadre));
    const cadre = cadres.find((f) => { const b = f.getBoundingClientRect(); return b.width > 0 && b.height > 0; }) || cadres[0];
    if (!cadre || !cadre.contentWindow) return Promise.resolve(null);
    const id = ++numero;
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
        cadre.contentWindow.postMessage({ dzAgent: "trouve", id, selecteur: a.selecteur, libelle: a.libelle || "",
          texte: a.texte, lang: lang() }, location.origin);
      } catch (e) { clearTimeout(fini); window.removeEventListener("message", h); ok(null); }
    });
  }
  function introuvable(actionsDuMessage) {
    const guides = (Array.isArray(actionsDuMessage) ? actionsDuMessage : []).filter((x) => x && x.type === "guide");
    hist.push({ role: "assistant", texte: T("agent.action.introuvable"), actions: guides });
    garder(); dessiner();
  }

  // moi : jeton pris par executer au clic ; un clic plus récent l'invalide (vérifié après chaque attente)
  async function pointer(a, actionsDuMessage, moi) {
    effacerPointeur();
    if (a.cadre) {
      let t = null;
      for (const fin = Date.now() + 4000; !t && Date.now() < fin;) {
        t = await demanderAuCadre(a);                // cadre absent ou pas encore chargé : on réessaie
        if (moi !== tourPointeur) return;
        if (!t) await attendre(250);
      }
      if (!t) return introuvable(actionsDuMessage);
      // suit le défilement de la page (place du cadre) mais pas celui DANS le lab : rectangle intérieur figé
      return montrer({ rect: () => t.cadre.isConnected ? composer(t.cadre.getBoundingClientRect(), t.interne) : null },
        a[lang()] || a.fr);
    }
    const n = await trouver(a, 4000);
    if (moi !== tourPointeur) return;                                            // un autre pointage a pris la main
    if (!n) return introuvable(actionsDuMessage);
    n.scrollIntoView({ block: "center" });
    await attendre(60);
    if (moi !== tourPointeur || !n.isConnected) return;
    montrer(n, a[lang()] || a.fr);
  }
  // le jeton est pris AVANT toute navigation : un clic A (autre écran) puis un clic B (écran courant) → A abandonne
  async function executer(a, actionsDuMessage) {
    const moi = ++tourPointeur;
    for (const e of etapes(a, vue())) {
      if (moi !== tourPointeur) return;
      if (e.faire === "aller") { aller(e.vue); await attendre(350); }
      else if (e.faire === "reglages") { ouvrirReglages(e.section); await attendre(300); }
      else if (e.faire === "guide") window.open("/guide/#" + e.chapitre, "_blank", "noopener");
      else if (e.faire === "pointer") await pointer(a, actionsDuMessage || [], moi);
    }
  }
  window.__dzAgentExecuter = executer;     // pour la tâche 11 et les preuves

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && calques.length) effacerPointeur();     // n'empêche pas la suite (fermeture du tiroir)
    if (ev.key === "F1") { ev.preventDefault(); if (!ev.repeat) basculer(); }
    else if (ev.key === "Escape" && tiroir.dataset.ouvert === "1" && tiroir.contains(ev.target)) {
      ev.preventDefault(); ev.stopPropagation(); basculer(false);
    }
    else if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing && ev.target === saisie) { ev.preventDefault(); envoyer(); }
  });

  const monter = () => { document.head.appendChild(css); document.body.append(bouton, tiroir); dessiner(); };
  if (document.body) monter(); else document.addEventListener("DOMContentLoaded", monter);
}
