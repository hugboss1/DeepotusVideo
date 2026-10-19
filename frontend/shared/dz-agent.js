// dz-agent.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md,
// 19/10/2026). SOURCE : frontend/shared/dz-agent.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-agent.js,
// chargée par frontend/dist/index.html (`<script type="module">`, après dz-plafonds.js). Aucune dépendance au runtime
// React : le tiroir vit à côté de la SPA. Le banc backend/tests/test_agent_ecran.py vérifie copies, balise et libellés.
//
// Le tiroir : bouton flottant « Demander » + F1 ; POST /api/agent/demander {question, historique, ecran, lang,
// moteur} ; sous chaque réponse, un bouton par action (Montre-moi / Y aller / Guide). L'historique reste dans
// sessionStorage (dz_agent_hist) ; le moteur choisi dans localStorage (dz_agent_moteur). Un 402 `dz_plafond` est
// traité par la couche /shared/dz-plafonds.js (elle enveloppe window.fetch) : rien à faire ici.
import { etapes, historiqueBorne, choisir } from "./dz-agent-logique.js";

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
.dzAgentBtn{position:fixed;right:18px;bottom:18px;z-index:2147483000;border:1px solid var(--cyan,#3ee6d0);
 background:var(--panel,#0e1422);color:var(--ink-strong,#eaf2ff);border-radius:999px;padding:8px 14px;font-family:inherit;font-size:13px;font-weight:600;line-height:1;
 cursor:pointer;box-shadow:0 0 18px rgba(62,230,208,.25)}
.dzAgentTiroir{position:fixed;top:0;right:0;bottom:0;width:min(400px,100vw);z-index:2147483001;display:none;flex-direction:column;
 background:var(--panel,#0e1422);color:var(--ink,#c9d4e8);border-left:1px solid var(--line,#24304a);font-family:inherit;font-size:13px;line-height:1.5}
.dzAgentTiroir[data-ouvert="1"]{display:flex}
.dzAgentTete{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--line,#24304a)}
.dzAgentTete h2{flex:1;margin:0;font-size:14px;color:var(--ink-strong,#eaf2ff)}
.dzAgentFil{flex:1;overflow:auto;padding:12px 14px;display:flex;flex-direction:column;gap:10px}
.dzAgentMsg{white-space:pre-wrap;border-radius:10px;padding:8px 10px;background:var(--panel-2,#141c2e)}
.dzAgentMsg[data-role="user"]{align-self:flex-end;background:var(--cyan-soft,rgba(62,230,208,.12))}
.dzAgentActions{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.dzAgentActions button,.dzAgentTete button,.dzAgentPied button{background:transparent;color:inherit;border:1px solid var(--line,#24304a);
 border-radius:8px;padding:4px 8px;cursor:pointer;font:inherit}
.dzAgentPied{display:flex;gap:6px;padding:10px 14px;border-top:1px solid var(--line,#24304a)}
.dzAgentPied textarea{flex:1;resize:none;min-height:38px;background:var(--panel-2,#141c2e);color:inherit;border:1px solid var(--line,#24304a);border-radius:8px;padding:6px}
.dzAgentTete select{background:var(--panel-2,#141c2e);color:inherit;border:1px solid var(--line,#24304a);border-radius:6px}` });

  const fil = el("div", { class: "dzAgentFil", role: "log", "aria-live": "polite" });
  const saisie = el("textarea", { placeholder: T("agent.tiroir.placeholder"), "aria-label": T("agent.tiroir.placeholder") });
  const choix = el("select", { "aria-label": T("agent.moteur.libelle"), title: T("agent.moteur.libelle") });
  const tiroir = el("aside", { class: "dzAgentTiroir", "aria-label": T("agent.tiroir.titre") }, [
    el("div", { class: "dzAgentTete" }, [
      el("h2", { texte: T("agent.tiroir.titre") }), choix,
      el("button", { texte: "↺", title: T("agent.tiroir.nouvelle"), "aria-label": T("agent.tiroir.nouvelle"),
        on: { click: () => { hist = []; garder(); dessiner(); } } }),
      el("button", { texte: "×", title: T("agent.tiroir.fermer"), "aria-label": T("agent.tiroir.fermer"), on: { click: () => basculer(false) } }),
    ]),
    fil,
    el("div", { class: "dzAgentPied" }, [saisie, el("button", { texte: T("agent.tiroir.envoyer"), on: { click: () => envoyer() } })]),
  ]);
  const bouton = el("button", { class: "dzAgentBtn", texte: "? " + T("agent.tiroir.bouton"), title: T("agent.tiroir.bouton_titre"),
    on: { click: () => basculer() } });

  function basculer(ouvrir) {
    const o = ouvrir === undefined ? tiroir.dataset.ouvert !== "1" : ouvrir;
    tiroir.dataset.ouvert = o ? "1" : "0";
    if (o) { chargerMoteurs(); saisie.focus(); }
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

  function boutonAction(a) {
    const l = lang();
    const libelle = a.type === "point" ? T("agent.action.montrer", { libelle: a[l] || a.fr })
      : a.type === "guide" ? T("agent.action.guide", { titre: a[l] || a.fr }) : T("agent.action.aller");
    return el("button", { texte: libelle, on: { click: () => executer(a) } });
  }

  function dessiner(enAttente) {
    const msgs = hist.length ? hist : [{ role: "assistant", texte: T("agent.tiroir.accueil") }];
    fil.replaceChildren(...msgs.map((m) => {
      const b = el("div", { class: "dzAgentMsg", "data-role": m.role, texte: m.texte });
      if (m.actions && m.actions.length) b.appendChild(el("div", { class: "dzAgentActions" }, m.actions.map(boutonAction)));
      return b;
    }));
    if (enAttente) fil.appendChild(el("div", { class: "dzAgentMsg", "data-role": "assistant", texte: T("agent.reponse.reflechit") }));
    fil.scrollTop = fil.scrollHeight;
  }

  async function envoyer() {
    const q = saisie.value.trim();
    if (!q) return;
    saisie.value = "";
    const avant = historiqueBorne(hist).map(({ role, texte }) => ({ role, texte }));
    hist.push({ role: "user", texte: q });
    dessiner(true);
    try {
      const r = await fetch("/api/agent/demander", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, historique: avant, ecran: vue(), lang: lang(), moteur: choix.value || "" }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
      hist.push({ role: "assistant", texte: j.texte, actions: j.actions || [] });
    } catch (e) {
      hist.push({ role: "assistant", texte: T("agent.reponse.erreur", { msg: e.message }) });
      saisie.value = q;
    }
    garder();
    dessiner();
  }

  // ── les actions (le pointeur arrive à la tâche 11) ──
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
  async function pointer(a) {
    const n = await trouver(a, 4000);
    if (!n) { hist.push({ role: "assistant", texte: T("agent.action.introuvable") }); garder(); dessiner(); return; }
    n.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  async function executer(a) {
    for (const e of etapes(a, vue())) {
      if (e.faire === "aller") { aller(e.vue); await attendre(350); }
      else if (e.faire === "reglages") ouvrirReglages(e.section);
      else if (e.faire === "guide") window.open("/guide/#" + e.chapitre, "_blank", "noopener");
      else if (e.faire === "pointer") await pointer(a);
    }
  }
  window.__dzAgentExecuter = executer;     // pour la tâche 11 et les preuves

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "F1") { ev.preventDefault(); basculer(); }
    else if (ev.key === "Escape" && tiroir.dataset.ouvert === "1") basculer(false);
    else if (ev.key === "Enter" && !ev.shiftKey && ev.target === saisie) { ev.preventDefault(); envoyer(); }
  });

  const monter = () => { document.head.appendChild(css); document.body.append(bouton, tiroir); dessiner(); };
  if (document.body) monter(); else document.addEventListener("DOMContentLoaded", monter);
}
