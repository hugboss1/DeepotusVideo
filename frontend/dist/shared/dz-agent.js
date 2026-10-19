// dz-agent.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md,
// 19/10/2026). SOURCE : frontend/shared/dz-agent.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-agent.js,
// chargée par frontend/dist/index.html (`<script type="module">`, après dz-plafonds.js). Aucune dépendance au runtime
// React : le tiroir vit à côté de la SPA. Le banc backend/tests/test_agent_ecran.py vérifie copies, balise et libellés.
//
// Le tiroir : bouton flottant « Demander » + F1 ; POST /api/agent/demander {question, historique, ecran, lang,
// moteur} ; sous chaque réponse, un bouton par action (Montre-moi / Y aller / Guide). L'historique reste dans
// sessionStorage (dz_agent_hist) ; le moteur choisi dans localStorage (dz_agent_moteur). Un 402 `dz_plafond` est
// traité par la couche /shared/dz-plafonds.js (elle enveloppe window.fetch) : rien à faire ici.
import { etapes, historiqueBorne, choisir, composer, candidats, versEcran, cliquable, prix, releverVisibles,
  MAX_VISIBLES } from "./dz-agent-logique.js";
import { creerPointeur } from "./dz-agent-pointeur.js";
import { capturer, captureDisponible } from "./dz-agent-vision.js";

if (!window.__dzAgent) {
  window.__dzAgent = true;

  const T = (k, v) => (window.dzT ? window.dzT(k, v) : k);
  const lang = () => { const l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang; return l === "en" ? "en" : "fr"; };
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
  const NS = "http://www.w3.org/2000/svg";
  const glyphe = (cle) => {
    const s = document.createElementNS(NS, "svg");
    for (const [k, v] of Object.entries({ class: "dzi", width: "16", height: "16", "aria-hidden": "true", focusable: "false", "data-dz-icone": cle })) s.setAttribute(k, v);
    const u = document.createElementNS(NS, "use");
    u.setAttribute("href", "/shared/icons/dz-icons.svg#" + cle);
    s.appendChild(u);
    return s;
  };

  let hist = [];
  try { hist = historiqueBorne(JSON.parse(lire(window.sessionStorage, "dz_agent_hist") || "[]")); } catch (e) { hist = []; }
  let annulerAccord = null;   // ferme la boîte d'accord en cours sur « annuler » (tiroir fermé, ↺) : rien n'est envoyé
  let boiteAccord = null;     // la boîte d'accord en cours : dessiner() la remet au bas du fil
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
.dzAgentPied button[aria-busy="true"]{opacity:.6}
.dzAgentPied button[aria-pressed="true"]{border-color:#ef4444;background:#b91c1c;color:#fff}
.dzAgentPied textarea{flex:1;resize:none;min-height:38px;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:8px;padding:6px}
.dzAgentTete select{background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:6px}
.dzAgentTete button:disabled,.dzAgentPied button:disabled{opacity:.5;cursor:default}
.dzAgentAccord select{margin:6px 0;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:6px}
.dzAgentAccord p{margin:0}` });

  const fil = el("div", { class: "dzAgentFil", role: "log", "aria-live": "polite" });
  const saisie = el("textarea", { placeholder: T("agent.tiroir.placeholder"), "aria-label": T("agent.tiroir.placeholder") });
  const choix = el("select", { "aria-label": T("agent.moteur.libelle"), title: T("agent.moteur.libelle") });
  const btnEnvoyer = el("button", { texte: T("agent.tiroir.envoyer"), on: { click: () => envoyer() } });
  // A6 : la dictée passe par la couche des champs IA (/shared/dz-champ-ia.js) : voie 1 du navigateur, voie 2
  // enregistrée avec devis et accord. Le tiroir ne règle que son bouton, sur l'événement `dzia-dictee`.
  const dictee = () => (window.DzChampIA && window.DzChampIA.dictee) || null;
  // l'état de la dictée DE ce champ (annoncé par `dzia-dictee`), pas celui d'un autre champ de la page
  const dicteeEnCours = () => { const e = btnMicro.dataset.etat; return !!e && e !== "repos" && e !== "fini"; };
  const btnMicro = el("button", { type: "button", "aria-pressed": "false", title: T("agent.voix.dicter"),
    "aria-label": T("agent.voix.dicter"), on: { click: () => {
      const d = dictee();
      if (!d || typeof d.basculer !== "function") return dire("agent.voix.indisponible");
      d.basculer(saisie);
    } } }, [glyphe("dz-media-dicter")]);
  saisie.addEventListener("dzia-dictee", (ev) => {
    const e = (ev.detail && ev.detail.etat) || "repos";
    const ecoute = e === "ecoute" || e === "prise";
    const occupee = ["micro", "estime", "accord", "envoi", "fin"].includes(e);
    btnMicro.setAttribute("aria-pressed", ecoute ? "true" : "false");
    btnMicro.setAttribute("aria-busy", occupee ? "true" : "false");
    btnMicro.title = T(occupee ? "agent.voix.occupe" : ecoute ? "agent.voix.arreter" : "agent.voix.dicter");
    btnMicro.setAttribute("aria-label", btnMicro.title);
    btnMicro.replaceChildren(occupee ? document.createTextNode("…") : glyphe(ecoute ? "dz-media-arret" : "dz-media-dicter"));
    btnMicro.dataset.etat = e;
  });
  const btnNouvelle = el("button", { texte: "↺", title: T("agent.tiroir.nouvelle"), "aria-label": T("agent.tiroir.nouvelle"),
    on: { click: () => {
      if (annulerAccord) annulerAccord(); else if (occupe || enVue) return;
      arreterLecture(); hist = []; garder(); dessiner(); } } });
  const tiroir = el("aside", { id: "dzAgentTiroir", class: "dzAgentTiroir", "aria-label": T("agent.tiroir.titre") }, [
    el("div", { class: "dzAgentTete" }, [
      el("h2", { texte: T("agent.tiroir.titre") }), choix, btnNouvelle,
      el("button", { texte: "×", title: T("agent.tiroir.fermer"), "aria-label": T("agent.tiroir.fermer"), on: { click: () => basculer(false) } }),
    ]),
    fil,
    el("div", { class: "dzAgentPied" }, [saisie, btnMicro, btnEnvoyer]),
  ]);
  const bouton = el("button", { class: "dzAgentBtn", texte: "? " + T("agent.tiroir.bouton"), title: T("agent.tiroir.bouton_titre"),
    "aria-expanded": "false", "aria-controls": "dzAgentTiroir", on: { click: () => basculer() } });

  function basculer(ouvrir) {
    const o = ouvrir === undefined ? tiroir.dataset.ouvert !== "1" : ouvrir;
    const focusDedans = tiroir.contains(document.activeElement);
    tiroir.dataset.ouvert = o ? "1" : "0";
    bouton.setAttribute("aria-expanded", o ? "true" : "false");
    if (!o && annulerAccord) annulerAccord();      // fermer le tiroir pendant l'accord l'annule
    if (o) { chargement = null; chargerMoteurs().then(() => { if (!occupe) dessiner(); }); saisie.focus(); }     // rechargé : une clé ajoutée à chaud compte ; la voix connue fait apparaître « Lire »
    else {
      arreterLecture();
      if (dicteeEnCours()) { try { dictee().abandonner(saisie); } catch (e) { /* rien à abandonner */ } }
      if (focusDedans) bouton.focus();     // le focus ne reste pas dans un tiroir masqué
    }
  }

  let etatAgent = null;     // réponse de /api/agent/etat (moteurs avec cout et vision ; voix en A6)
  let chargement = null;    // la promesse du chargement en cours ; remise à null à chaque ouverture du tiroir
  function chargerMoteurs() {
    if (chargement) return chargement;
    chargement = (async () => {
      try {
        const r = await fetch("/api/agent/etat");
        const j = await r.json();
        etatAgent = j;
        choix.replaceChildren(el("option", { value: "", texte: T("agent.moteur.auto") }),
          ...j.moteurs.map((m) => el("option", { value: m.moteur,
            texte: `${m.nom} · ${T(m.cout === "gratuit" ? "agent.moteur.cout_gratuit" : "agent.moteur.cout_payant")}` })));
        choix.value = lire(window.localStorage, "dz_agent_moteur") || "";
      } catch (e) { chargement = null; }
    })();
    return chargement;
  }
  async function moteursConnus() {
    await chargerMoteurs();
    return etatAgent && Array.isArray(etatAgent.moteurs) ? etatAgent.moteurs : [];
  }
  choix.addEventListener("change", () => ecrire(window.localStorage, "dz_agent_moteur", choix.value));

  // actionsDuMessage : toutes les actions du message d'où vient le clic (l'ancre introuvable renvoie vers ses guides)
  function boutonAction(a, actionsDuMessage, msg) {
    const l = lang();
    const libelle = a.type === "point" ? T("agent.action.montrer", { libelle: a[l] || a.fr })
      : a.type === "point_xy" ? T("agent.action.montrer", { libelle: a.libelle || T("agent.vision.ici") })
      : a.type === "voir" ? T("agent.vision.voir")
      : a.type === "guide" ? T("agent.action.guide", { titre: a[l] || a.fr }) : T("agent.action.aller");
    return el("button", { texte: libelle, on: { click: () => executer(a, actionsDuMessage, msg) } });
  }

  // A6 : une réponse lue par la voix des Réglages (POST /api/agent/lire -> MP3). Un clic sur le bouton en cours arrête.
  let lecture = null;     // {ctrl, bouton, texte, msg, titre, audio?, url?}
  function etatBouton(l, enCours) {
    l.bouton.setAttribute("aria-pressed", enCours ? "true" : "false");
    const t = enCours ? T("agent.voix.stop") : l.titre;
    l.bouton.title = t; l.bouton.setAttribute("aria-label", t);
  }
  function arreterLecture() {
    if (!lecture) return;
    const l = lecture; lecture = null;
    try { l.ctrl.abort(); } catch (e) { /* déjà interrompue */ }
    if (l.audio) { try { l.audio.pause(); } catch (e) { /* déjà arrêtée */ } }
    if (l.url) URL.revokeObjectURL(l.url);
    etatBouton(l, false);
  }
  function erreurLecture(e) {
    hist.push({ role: "assistant", texte: T("agent.voix.erreur", { msg: (e && e.message) || "—" }), erreur: true });
    garder(); dessiner(occupe);
  }
  async function lireTexte(m, b, titre) {
    const deja = lecture && lecture.bouton === b;
    arreterLecture();
    if (deja) return;
    const moi = { ctrl: new AbortController(), bouton: b, texte: m.texte, msg: m, titre };
    lecture = moi;                                   // posée AVANT le fetch : fermer ou ↺ pendant le chargement l'abandonne
    etatBouton(moi, true);
    let url = "";
    try {
      const r = await fetch("/api/agent/lire", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texte: m.texte, lang: lang() }), signal: moi.ctrl.signal });
      if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(typeof j.detail === "string" ? j.detail : String(r.status)); }
      const blob = await r.blob();
      if (lecture !== moi) return;                   // arrêtée ou remplacée pendant le chargement : on ne joue pas
      url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      moi.audio = audio; moi.url = url; url = "";
      audio.addEventListener("ended", () => { if (lecture === moi) arreterLecture(); });
      audio.addEventListener("error", () => { if (lecture === moi) { arreterLecture(); erreurLecture(new Error("audio")); } });
      await audio.play();
    } catch (e) {
      if (url) URL.revokeObjectURL(url);
      if (e && e.name === "AbortError") return;      // interrompue par l'utilisateur : silence
      if (lecture === moi) { arreterLecture(); erreurLecture(e); }
    }
  }
  function boutonLire(m) {
    const v = etatAgent && etatAgent.voix;
    if (!v || !v.fournisseur || m.role !== "assistant" || m.erreur || !m.texte) return null;
    const titre = T(v.cout === "gratuit" ? "agent.voix.lire_gratuit" : "agent.voix.lire_payant", { nom: v.nom });
    const b = el("button", { type: "button", title: titre, "aria-label": titre, "aria-pressed": "false" }, [glyphe("dz-media-audio")]);
    if (lecture && lecture.msg === m) {              // un nouveau dessin du fil ne fait pas perdre le bouton de la lecture en cours
      lecture.bouton = b; lecture.titre = titre; etatBouton(lecture, true);
    }
    b.addEventListener("click", () => lireTexte(m, b, titre));
    return b;
  }

  function dessiner(enAttente) {
    const msgs = hist.length ? hist : [{ role: "assistant", texte: T("agent.tiroir.accueil") }];
    fil.replaceChildren(...msgs.map((m) => {
      const b = el("div", { class: "dzAgentMsg", "data-role": m.role, texte: m.texte });
      const boutons = (m.actions || []).map((x) => boutonAction(x, m.actions, m));
      const lireB = hist.includes(m) ? boutonLire(m) : null;     // le message d'accueil n'est pas dans l'historique
      if (lireB) boutons.push(lireB);
      if (boutons.length) b.appendChild(el("div", { class: "dzAgentActions" }, boutons));
      return b;
    }));
    if (enAttente) fil.appendChild(el("div", { class: "dzAgentMsg", "data-role": "assistant", texte: T("agent.reponse.reflechit") }));
    if (boiteAccord) fil.appendChild(boiteAccord);
    fil.scrollTop = fil.scrollHeight;
  }

  // un seul envoi à la fois ; un échec rend la question à la saisie et ne part jamais dans l'historique du serveur
  let occupe = false, enVue = false;
  async function envoyer() {
    const q = saisie.value.trim();
    if (!q || occupe || enVue) return;
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
        body: JSON.stringify({ question: q, historique: avant, ecran: vue(), lang: lang(), moteur: choix.value || "",
          visibles: await releve() }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
      if (typeof j.texte !== "string" || !j.texte.trim()) throw new Error("—");
      hist.push({ role: "assistant", texte: j.texte, actions: Array.isArray(j.actions) ? j.actions : [],
        question: q, avant });
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
  async function trouver(a, delaiMs) {
    const fin = Date.now() + delaiMs;
    do {
      // jamais le tiroir ni le bouton « Demander » eux-mêmes (indices de choisir sur la liste filtrée)
      const c = candidats(document, a.selecteur, a.libelle).filter((x) => !tiroir.contains(x.noeud) && !bouton.contains(x.noeud));
      const i = choisir(c, a, lang());
      if (i >= 0) return c[i].noeud;
      await attendre(150);
    } while (Date.now() < fin);
    return null;
  }

  // ── le pointeur à la Clicky (/shared/dz-agent-pointeur.js) : il part du bouton « Demander » ; un clic dans le
  // tiroir ne l'efface pas.
  const pointeur = creerPointeur({
    depart: () => { const b = bouton.getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; },
    ignorer: (cible) => tiroir.contains(cible),
  });
  const effacerPointeur = pointeur.effacer, montrer = pointeur.montrer;
  let tourPointeur = 0;

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
  // C4 : le relevé de l'écran ouvert — la page (hors tiroir et bouton) + le lab visible, s'il charge le répondeur
  // /shared/dz-agent-cadre.js (liste vérifiée par test_agent_ecran.py ; un autre cadre ferait attendre 400 ms pour
  // rien). Il ne bloque jamais l'envoi : le lab a 400 ms pour répondre, toute erreur donne [] (la question part sans relevé).
  const LABS_CADRES = /^\/(vectorlab|photolab|spritelab|tilelab)\//;
  function cadreVisible() {
    return Array.from(document.querySelectorAll("iframe")).find((f) => {
      const r = f.getBoundingClientRect();
      let chemin = "";
      try { chemin = new URL(f.getAttribute("src") || "", location.href).pathname; } catch (e) { chemin = ""; }
      return r.width > 0 && r.height > 0 && LABS_CADRES.test(chemin) && f.contentWindow;
    }) || null;
  }
  function releveDuCadre(cadre) {
    const id = ++numero;
    return new Promise((ok) => {
      const fini = setTimeout(() => { window.removeEventListener("message", h); ok([]); }, 400);
      function h(ev) {
        if (ev.origin !== location.origin || ev.source !== cadre.contentWindow || !ev.data
          || ev.data.dzAgent !== "visibles" || ev.data.id !== id) return;
        clearTimeout(fini);
        window.removeEventListener("message", h);
        ok(Array.isArray(ev.data.items) ? ev.data.items : []);
      }
      window.addEventListener("message", h);
      try { cadre.contentWindow.postMessage({ dzAgent: "releve", id }, location.origin); }
      catch (e) { clearTimeout(fini); window.removeEventListener("message", h); ok([]); }
    });
  }
  async function releve() {
    try {
      // hors tiroir, bouton et rail de la SPA (nav : les ancres le décrivent déjà, il mangerait le budget) ; les
      // labs, eux, gardent leurs nav (barre de menus, outils)
      const ici = releverVisibles(document, (x) => tiroir.contains(x) || bouton.contains(x)
        || !!(x.closest && x.closest("nav")));
      const cadre = cadreVisible();
      const lab = cadre ? await releveDuCadre(cadre) : [];
      return [...lab, ...ici].slice(0, MAX_VISIBLES);
    } catch (e) { return []; }
  }

  function introuvable(actionsDuMessage) {
    const guides = (Array.isArray(actionsDuMessage) ? actionsDuMessage : []).filter((x) => x && x.type === "guide");
    hist.push({ role: "assistant", texte: T("agent.action.introuvable"), actions: guides, erreur: true });
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
      if (moi !== tourPointeur) return;
      if (!t) return introuvable(actionsDuMessage);
      // suit le défilement de la page (place du cadre) mais pas celui DANS le lab : rectangle intérieur figé
      return montrer({ rect: () => {
        if (!t.cadre.isConnected) return null;
        const b = t.cadre.getBoundingClientRect();
        return b.width > 0 && b.height > 0 ? composer(b, t.interne) : null;     // cadre démonté ou masqué
      } }, a[lang()] || a.fr, t.cadre.contentWindow);
    }
    const n = await trouver(a, 4000);
    if (moi !== tourPointeur) return;                                            // un autre pointage a pris la main
    if (!n) return introuvable(actionsDuMessage);
    n.scrollIntoView({ block: "center" });
    await attendre(60);
    if (moi !== tourPointeur || !n.isConnected) return;
    montrer(n, a[lang()] || a.fr);
  }
  // ── A5 : la vision en secours. Accord (moteurs qui voient, devis gratuit), capture de CET onglet tiroir masqué,
  // second appel avec max_usd = le montant affiché, puis pointage du premier point rendu.
  const cacher = () => { effacerPointeur(); tiroir.style.visibility = "hidden"; bouton.style.visibility = "hidden"; };
  const reafficher = () => { tiroir.style.visibility = ""; bouton.style.visibility = ""; };
  function dire(cle, guides) {
    hist.push({ role: "assistant", texte: T(cle), actions: guides || [], erreur: true });
    garder(); dessiner();
  }

  // rend {moteur, usd} accepté, ou null (annulé)
  function accord(vus, corps) {
    return new Promise((fin) => {
      const texte = el("p", { texte: T("agent.vision.devis") });
      const sel = el("select", { "aria-label": T("agent.vision.moteur"), title: T("agent.vision.moteur") },
        vus.map((m) => el("option", { value: m.moteur, texte: m.nom })));
      sel.value = (vus.find((m) => m.moteur === choix.value) || vus[0]).moteur;
      if (vus.length < 2) sel.hidden = true;
      const oui = el("button", { texte: T("agent.vision.envoyer") });
      const non = el("button", { texte: T("agent.vision.annuler") });
      const boite = el("div", { class: "dzAgentMsg dzAgentAccord", "data-role": "assistant", role: "group" },
        [texte, sel, el("div", { class: "dzAgentActions" }, [oui, non])]);
      let devis = null, tour = 0;
      const fermer = (r) => { boiteAccord = null; annulerAccord = null; boite.remove(); fin(r); };
      annulerAccord = () => fermer(null);
      async function chiffrer() {
        const moi = ++tour;
        oui.disabled = true; devis = null;
        texte.textContent = T("agent.vision.devis");
        try {
          const r = await fetch("/api/agent/estimer", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...corps, moteur: sel.value }) });
          const j = await r.json().catch(() => ({}));
          if (moi !== tour) return;
          if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
          devis = j;
          texte.textContent = j.cout === "gratuit" ? T("agent.vision.accord_gratuit", { nom: j.nom })
            : j.cout === "a_mesurer" ? T("agent.vision.accord_inconnu", { nom: j.nom })
            : T("agent.vision.accord", { nom: j.nom, usd: prix(j.usd, lang()) });
          oui.disabled = !j.vision;
          if (j.vision) oui.focus();
        } catch (e) { if (moi === tour) texte.textContent = T("agent.reponse.erreur", { msg: (e && e.message) || "—" }); }
      }
      sel.addEventListener("change", chiffrer);
      oui.addEventListener("click", () => { if (devis) fermer({ moteur: devis.moteur, usd: devis.usd }); });
      non.addEventListener("click", () => fermer(null));
      boiteAccord = boite;
      fil.appendChild(boite);
      fil.scrollTop = fil.scrollHeight;
      chiffrer();
    });
  }

  async function regarder(msg, actionsDuMessage) {
    if (occupe) {                                  // une réponse est en cours : on le dit au lieu de ne rien faire
      hist.push({ role: "assistant", texte: T("agent.vision.occupe"), erreur: true });
      garder(); dessiner(true);
      return;
    }
    if (occupe || enVue || !msg || !msg.question) return;
    enVue = true;                                  // dès l'entrée : aucune autre demande pendant le chargement
    btnEnvoyer.disabled = true;
    try {
      const guides = (actionsDuMessage || []).filter((x) => x && x.type === "guide");
      if (!captureDisponible()) return dire("agent.vision.indisponible", guides);
      const vus = (await moteursConnus()).filter((m) => m.vision);
      if (!vus.length) return dire("agent.vision.aucun_moteur", guides);
      // le même relevé part avec le devis (/api/agent/estimer) et l'envoi : le serveur chiffre le même message
      const corps = { question: msg.question, historique: msg.avant || [], ecran: vue(), lang: lang(),
        visibles: await releve() };
      const ok = await accord(vus, corps);
      if (!ok) return;
      let cap;
      try { cap = await capturer({ avant: cacher, apres: reafficher }); }
      catch (e) {
        return dire(e && e.name === "NotAllowedError" ? "agent.vision.refusee"
          : e && e.message === "autre-surface" ? "agent.vision.onglet" : "agent.vision.indisponible", guides);
      }
      await envoyerVue({ ...corps, moteur: ok.moteur, max_usd: ok.usd,
        image: { mime: cap.mime, b64: cap.b64, largeur: cap.largeur, hauteur: cap.hauteur } }, cap.vue);
    } finally { enVue = false; btnEnvoyer.disabled = false; }
  }

  async function envoyerVue(corps, vueCapture) {
    occupe = true; btnEnvoyer.disabled = true; btnNouvelle.disabled = true;
    dessiner(true);
    let premier = null, actions = [];
    try {
      const r = await fetch("/api/agent/demander", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corps) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
      if (typeof j.texte !== "string" || !j.texte.trim()) throw new Error("—");
      // pas de nouvelle demande de capture en réponse à une capture
      actions = (Array.isArray(j.actions) ? j.actions : []).filter((x) => x && x.type !== "voir").map((x) => (x && x.type === "point_xy" ? { ...x, vue: vueCapture, ecran: vue() } : x));
      hist.push({ role: "assistant", texte: j.texte, actions });
      premier = actions.find((x) => x && x.type === "point_xy") || null;
    } catch (e) {
      hist.push({ role: "assistant", texte: T("agent.reponse.erreur", { msg: (e && e.message) || "—" }), erreur: true });
    } finally {
      occupe = false; btnEnvoyer.disabled = false; btnNouvelle.disabled = false;
      garder(); dessiner();
    }
    if (premier) executer(premier, actions);       // à la Clicky : on montre tout de suite ce qu'on a trouvé
  }

  // un point rendu en pixels de la capture : l'élément cliquable dessous, sinon un petit halo sur le point
  async function pointerXY(a, moi, actionsDuMessage) {
    effacerPointeur();
    const v = a.vue || { l: window.innerWidth, h: window.innerHeight };
    // rejoué après un changement d'écran, ou une fenêtre redimensionnée : le point ne correspond plus à la page
    // (la hauteur peut bouger : bandeau de partage, compensé plus bas)
    if ((a.ecran && a.ecran !== vue()) || Math.abs(window.innerWidth - v.l) > v.l * 0.04) return introuvable(actionsDuMessage);
    const p = versEcran(a, v);
    if (!p || moi !== tourPointeur) return;
    // le bandeau « partage de cet onglet » du navigateur réduit la fenêtre PENDANT la capture : si la hauteur a changé
    // depuis, un point du quart bas de la vue capturée (barres, boutons du bas) suit le bas de la fenêtre.
    if (window.innerHeight !== v.h && p.y > v.h * 0.75) p.y += window.innerHeight - v.h;
    // le tiroir couvre le point : on le ferme pour voir ce qu'il cachait (le point vient de la capture, tiroir masqué)
    const tb = tiroir.getBoundingClientRect();
    if (tiroir.dataset.ouvert === "1" && p.x >= tb.left && p.x <= tb.right && p.y >= tb.top && p.y <= tb.bottom) {
      basculer(false);
      await attendre(60);
      if (moi !== tourPointeur) return;
    }
    const sous = document.elementsFromPoint(p.x, p.y).find((e) => !tiroir.contains(e) && !bouton.contains(e));
    const n = sous && sous.tagName !== "IFRAME" ? cliquable(sous) : null;
    const libelle = a.libelle || T("agent.vision.ici");
    if (n) return montrer(n, libelle);
    montrer({ rect: () => ({ x: p.x - 16, y: p.y - 16, w: 32, h: 32 }) }, libelle);
  }

  // le jeton est pris AVANT toute navigation : un clic A (autre écran) puis un clic B (écran courant) → A abandonne
  async function executer(a, actionsDuMessage, msg) {
    const moi = ++tourPointeur;
    for (const e of etapes(a, vue())) {
      if (moi !== tourPointeur) return;
      if (e.faire === "aller") { aller(e.vue); await attendre(350); }
      else if (e.faire === "reglages") { ouvrirReglages(e.section); await attendre(300); }
      else if (e.faire === "guide") window.open("/guide/#" + e.chapitre, "_blank", "noopener");
      else if (e.faire === "pointer") await pointer(a, actionsDuMessage || [], moi);
      else if (e.faire === "pointer_xy") await pointerXY(a, moi, actionsDuMessage || []);
      else if (e.faire === "voir") await regarder(msg, actionsDuMessage || []);
    }
  }
  window.__dzAgentExecuter = executer;     // point d'entrée de débogage et de preuve (console)

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && pointeur.actif()) effacerPointeur();     // n'empêche pas la suite (fermeture du tiroir)
    if (ev.key === "F1") { ev.preventDefault(); if (!ev.repeat) basculer(); }
    else if (ev.key === "Escape" && tiroir.dataset.ouvert === "1" && tiroir.contains(ev.target) && !dicteeEnCours()) {
      ev.preventDefault(); ev.stopPropagation(); basculer(false);
    }
    else if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing && ev.target === saisie) { ev.preventDefault(); envoyer(); }
  });

  const monter = () => { document.head.appendChild(css); document.body.append(bouton, tiroir); dessiner(); };
  if (document.body) monter(); else document.addEventListener("DOMContentLoaded", monter);
}
