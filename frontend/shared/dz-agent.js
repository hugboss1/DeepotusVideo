// dz-agent.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md,
// 19/10/2026). SOURCE : frontend/shared/dz-agent.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-agent.js,
// chargée par frontend/dist/index.html (`<script type="module">`, après dz-plafonds.js). Aucune dépendance au runtime
// React : le tiroir vit à côté de la SPA. Le banc backend/tests/test_agent_ecran.py vérifie copies, balise et libellés.
//
// Le tiroir : bouton flottant « Demander » + F1 ; POST /api/agent/demander {question, historique, ecran, lang,
// moteur} ; sous chaque réponse, un bouton par action (Montre-moi / Y aller / Guide). L'historique reste dans
// sessionStorage (dz_agent_hist) ; le moteur choisi dans localStorage (dz_agent_moteur). Un 402 `dz_plafond` est
// traité par la couche /shared/dz-plafonds.js (elle enveloppe window.fetch) : rien à faire ici.
//
// t260 (plan 2026-10-20-agent-bulle-deplacable.md) : la bulle couvrait le pied des panneaux (Calques du Photolab…).
// Elle a deux places, gardées dans localStorage : « barre » (défaut, dz_agent_place) = un bouton de la barre du haut
// de la coque, qui ne recouvre rien ; « flottant » = bulle qu'on glisse où l'on veut (dz_agent_pos). On la tire hors
// de la barre pour la rendre flottante, on la lâche sur la barre pour l'y ranger ; clic droit et épingle du tiroir
// font la même chose. Sans barre (démarrage, mise en page sans en-tête), elle reste flottante.
//
// t285b (24/10/2026, plan 2026-10-23-agent-interne, T10b) : deux onglets sous l'en-tête. « Demander » est le tiroir
// d'avant, inchangé ; « Campagnes » monte le composant partagé /shared/dz-campagnes.js (window.DzCampagnes, réutilisé
// tel quel) à la première ouverture de l'onglet. Au-dessus, un sélecteur d'espace de marque : vide par défaut (jamais
// l'espace actif d'office) → rôle « orienteur » ; un espace choisi → conversation NEUVE en rôle « campagnes », le texte
// en cours suit comme brief ; une campagne née avec un espace verrouille le sélecteur. L'onglet ouvert est gardé dans
// sessionStorage (dz_agent_onglet), la conversation en cours aussi (dz_agent_camp : {cid, role, espace}). Quand
// « Demander » rend l'action {type:"campagnes", question}, sa carte « Ouvrir l'agent Campagnes » ouvre l'onglet sur une
// conversation neuve, la question préremplie, JAMAIS envoyée seule (l'envoi vaut accord du devis).
//
// t352 (27/10/2026) : 3e onglet « Veille » : monte /shared/dz-veille.js (window.DzVeille) pour l'espace choisi dans
// son propre sélecteur (l'espace actif par défaut : la veille ne fait que lire). Gardé dans sessionStorage
// (dz_agent_veille). Les flèches gauche / droite parcourent les trois onglets en boucle.
import { etapes, historiqueBorne, choisir, composer, candidats, versEcran, cliquable, prix, releverVisibles,
  MAX_VISIBLES, placeLue, positionLue, borner, glisse, ONGLETS, ongletLu, optionsCampagnes, campagneLue } from "./dz-agent-logique.js";
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
 cursor:pointer;box-shadow:0 0 18px var(--cyan-glow,rgba(240,180,41,.33));touch-action:none;user-select:none;white-space:nowrap}
.dzAgentBtn[data-place="barre"]{position:static;flex-shrink:0;align-self:center;margin:0 6px;padding:4px 10px;font-size:12px;box-shadow:none;z-index:auto}
.dzAgentBtn[data-glisse="1"]{cursor:grabbing;opacity:.85}
.dzAgentMenu{position:fixed;z-index:9992;display:flex;flex-direction:column;min-width:220px;padding:4px;border:1px solid var(--stroke,#2a2930);
 border-radius:8px;background:var(--bg-panel,#151519);color:var(--ink,#c9d4e8);font-family:inherit;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.45)}
.dzAgentMenu button{background:transparent;color:inherit;border:0;border-radius:6px;padding:6px 10px;text-align:left;cursor:pointer;font:inherit}
.dzAgentMenu button:hover,.dzAgentMenu button:focus-visible{background:var(--bg-panel-2,#1c1c21)}
.dzAgentTete button[aria-pressed="true"]{border-color:var(--cyan,#3ee6d0)}
.dzAgentTiroir{position:fixed;top:0;right:0;bottom:0;width:min(400px,100vw);z-index:9991;display:none;flex-direction:column;
 background:var(--bg-panel,#151519);color:var(--ink,#c9d4e8);border-left:1px solid var(--stroke,#2a2930);font-family:inherit;font-size:13px;line-height:1.5}
.dzAgentTiroir[data-ouvert="1"]{display:flex}
.dzAgentTete{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--stroke,#2a2930)}
.dzAgentTete h2{flex:1;min-width:0;margin:0;font-size:14px;color:var(--ink-strong,#eaf2ff);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
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
.dzAgentTete select{max-width:104px;min-width:0;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:6px}
.dzAgentTete button:disabled,.dzAgentPied button:disabled{opacity:.5;cursor:default}
.dzAgentAccord select{margin:6px 0;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:6px}
.dzAgentAccord p{margin:0}
.dzAgentTiroir [hidden]{display:none!important}
.dzAgentOnglets{display:flex;gap:4px;padding:6px 14px 0;border-bottom:1px solid var(--stroke,#2a2930)}
.dzAgentOnglets button{background:transparent;color:inherit;border:1px solid transparent;border-bottom:0;border-radius:8px 8px 0 0;padding:5px 12px;cursor:pointer;font:inherit}
.dzAgentOnglets button[aria-selected="true"]{border-color:var(--stroke,#2a2930);background:var(--bg-panel-2,#1c1c21);color:var(--ink-strong,#eaf2ff);box-shadow:inset 0 2px 0 var(--cyan,#3ee6d0)}
.dzAgentOnglets button:focus-visible{outline:1px solid var(--cyan,#3ee6d0)}
.dzAgentPan{flex:1;min-height:0;display:flex;flex-direction:column}
.dzAgentCampEspace{display:flex;align-items:center;gap:8px;padding:8px 14px;border-bottom:1px solid var(--stroke,#2a2930)}
.dzAgentCampEspace select{flex:1;min-width:0;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:6px;padding:3px 6px;font:inherit}
.dzAgentCampEspace select:disabled{opacity:.6;cursor:default}
.dzAgentCampHote{flex:1;min-height:0;overflow:auto;display:flex;flex-direction:column}
.dzAgentCampVide{margin:12px 14px;color:var(--ink,#c9d4e8)}` });

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
      if (onglet === "campagnes") return nouvelleCampagne();     // t285b : ↺ sur Campagnes = conversation neuve
      if (onglet === "veille") return veille && veille.recharger();     // t352 : ↺ sur Veille = relire la veille
      if (annulerAccord) annulerAccord(); else if (occupe || enVue) return;
      arreterLecture(); hist = []; garder(); dessiner(); } } });
  // t260 : l'épingle range la bulle dans la barre du haut, ou la rend flottante
  const btnEpingle = el("button", { type: "button", "aria-pressed": "true",
    on: { click: () => changerPlace(place === "barre" ? "flottant" : "barre") } }, [glyphe("dz-etat-epingle")]);
  // t285b : les onglets (tablist / tab / tabpanel, tabindex itinérant, flèches gauche / droite)
  const ongletBouton = (nom, cle) => el("button", { type: "button", role: "tab", id: "dzAgentOnglet-" + nom,
    "aria-controls": "dzAgentPan-" + nom, "aria-selected": "false", tabindex: "-1", "data-dz-agent": "onglet-" + nom,
    texte: T(cle), on: { click: () => choisirOnglet(nom) } });
  const ongDemander = ongletBouton("demander", "agent.onglet.demander"), ongCampagnes = ongletBouton("campagnes", "agent.onglet.campagnes");
  const ongVeille = ongletBouton("veille", "agent.onglet.veille");
  const listeOnglets = el("div", { class: "dzAgentOnglets", role: "tablist", "aria-label": T("agent.onglets.libelle") },
    [ongDemander, ongCampagnes, ongVeille]);
  listeOnglets.addEventListener("keydown", (ev) => {
    if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
    ev.preventDefault();
    const i = ONGLETS.indexOf(onglet), n = ONGLETS.length;     // t352 : trois onglets, en boucle
    choisirOnglet(ONGLETS[(i + (ev.key === "ArrowRight" ? 1 : n - 1)) % n], true);
  });
  const panneau = (nom, enfants) => el("div", { class: "dzAgentPan", role: "tabpanel", id: "dzAgentPan-" + nom,
    "aria-labelledby": "dzAgentOnglet-" + nom, hidden: "" }, enfants);
  const panDemander = panneau("demander", [fil, el("div", { class: "dzAgentPied" }, [saisie, btnMicro, btnEnvoyer])]);
  const selEspace = el("select", { "aria-label": T("agent.campagnes.espace"), title: T("agent.campagnes.espace"),
    "data-dz-agent": "espace" }, [el("option", { value: "", texte: T("agent.campagnes.sans_espace") })]);
  const hoteCampagnes = el("div", { class: "dzAgentCampHote", "data-dz-agent": "hote-campagnes" });
  const panCampagnes = panneau("campagnes", [el("div", { class: "dzAgentCampEspace" }, [selEspace]), hoteCampagnes]);
  const selVeille = el("select", { "aria-label": T("agent.veille.espace"), title: T("agent.veille.espace"),
    "data-dz-agent": "espace-veille" }, [el("option", { value: "", texte: T("agent.campagnes.sans_espace") })]);
  const hoteVeille = el("div", { class: "dzAgentCampHote", "data-dz-agent": "hote-veille" });
  const panVeille = panneau("veille", [el("div", { class: "dzAgentCampEspace" }, [selVeille]), hoteVeille]);
  const tiroir = el("aside", { id: "dzAgentTiroir", class: "dzAgentTiroir", "aria-label": T("agent.tiroir.titre") }, [
    el("div", { class: "dzAgentTete" }, [
      el("h2", { texte: T("agent.tiroir.titre") }), choix, btnEpingle, btnNouvelle,
      el("button", { texte: "×", title: T("agent.tiroir.fermer"), "aria-label": T("agent.tiroir.fermer"), on: { click: () => basculer(false) } }),
    ]),
    listeOnglets, panDemander, panCampagnes, panVeille,
  ]);

  // ── t285b : l'onglet Campagnes ──
  let onglet = ongletLu(lire(window.sessionStorage, "dz_agent_onglet"));
  let camp = null;                      // le composant monté {demonter, cid, recharger}, null avant la 1re ouverture
  let campEtat = campagneLue(lire(window.sessionStorage, "dz_agent_camp"));     // {cid, role, espace} | null
  let espacesLus = false;
  let genCamp = 0;                      // revue T10b : génération du montage ; un surCid d'un composant démonté est ignoré
  const afficherSi = (n, oui) => { if (oui) n.removeAttribute("hidden"); else n.setAttribute("hidden", ""); };
  function choisirOnglet(nom, focus) {
    onglet = ongletLu(nom);
    ecrire(window.sessionStorage, "dz_agent_onglet", onglet);
    for (const [b, p, n] of [[ongDemander, panDemander, "demander"], [ongCampagnes, panCampagnes, "campagnes"],
      [ongVeille, panVeille, "veille"]]) {
      b.setAttribute("aria-selected", n === onglet ? "true" : "false");
      b.setAttribute("tabindex", n === onglet ? "0" : "-1");
      afficherSi(p, n === onglet);
    }
    afficherSi(choix, onglet === "demander");     // l'agent Campagnes a son propre moteur
    if (onglet === "campagnes" && tiroir.dataset.ouvert === "1") ouvrirCampagnes();
    if (onglet === "veille" && tiroir.dataset.ouvert === "1") ouvrirVeille();
    if (focus) ({ campagnes: ongCampagnes, veille: ongVeille }[onglet] || ongDemander).focus();
  }
  // le sélecteur est verrouillé dès qu'une conversation AVEC un espace existe, quel que soit son rôle (relecture de
  // branche t285b : la porte / la carte « espace » de l'orienteur le règle côté serveur) : il ne se change pas d'ici
  function verrouiller() {
    if (campEtat && campEtat.cid && campEtat.espace) selEspace.setAttribute("disabled", "");
    else selEspace.removeAttribute("disabled");
  }
  function garderCampagne(e) {
    campEtat = e;
    if (e) ecrire(window.sessionStorage, "dz_agent_camp", JSON.stringify(e));
    else { try { window.sessionStorage.removeItem("dz_agent_camp"); } catch (x) { /* stockage indisponible */ } }
    verrouiller();
  }
  function demonterCampagne() {
    if (camp) { try { camp.demonter(); } catch (e) { /* déjà démonté */ } }
    camp = null;
    genCamp++;                          // tout surCid encore en vol (POST / du composant démonté) devient périmé
    hoteCampagnes.replaceChildren();
  }
  // o : {espace?, brief?, cid?} → DzCampagnes.monter(hôte, optionsCampagnes(o) + surCid)
  function monterCampagne(o) {
    demonterCampagne();
    const D = window.DzCampagnes;
    if (!D || typeof D.monter !== "function") {
      hoteCampagnes.appendChild(el("p", { class: "dzAgentCampVide", "data-dz-agent": "campagnes-indisponible", texte: T("agent.campagnes.indisponible") }));
      return;
    }
    const opts = optionsCampagnes(o);
    const role = opts.role, espace = opts.espace_id || "";
    const g = ++genCamp;
    opts.surCid = (cid) => { if (g === genCamp && typeof cid === "string" && cid) garderCampagne({ cid, role, espace }); };
    try { camp = D.monter(hoteCampagnes, opts); }
    catch (e) {
      camp = null;
      hoteCampagnes.replaceChildren(el("p", { class: "dzAgentCampVide", "data-dz-agent": "campagnes-indisponible", texte: T("agent.campagnes.indisponible") }));
    }
  }
  function ajouterEspace(id, nom) {
    for (const s of [selEspace, selVeille]) {      // t352 : la même liste nourrit le sélecteur de la Veille
      if (!Array.from(s.children).some((o) => o.getAttribute("value") === id)) s.appendChild(el("option", { value: id, texte: nom || id }));
    }
  }
  let espaceActif = "";                 // t352 : l'espace actif, seul défaut de la Veille (jamais de Campagnes)
  async function chargerEspaces() {
    try {
      const r = await fetch("/api/espaces");     // sans ?archives=true : les seuls espaces NON archivés
      const j = await r.json();
      if (j && typeof j.actif === "string") espaceActif = j.actif;
      for (const e of Array.isArray(j && j.espaces) ? j.espaces : []) {
        if (e && typeof e.id === "string" && !e.archive) ajouterEspace(e.id, typeof e.nom === "string" ? e.nom : e.id);
      }
    } catch (e) { espacesLus = false; }        // relu à la prochaine ouverture
    // jamais l'espace actif d'office : seule la conversation gardée impose le sien
    const voulu = campEtat ? campEtat.espace : "";
    if (voulu) { ajouterEspace(voulu, voulu); selEspace.value = voulu; }
  }
  // relecture de branche t285b : l'espace de la conversation en cours, appris du serveur (GET /api/agent/campagnes/{cid},
  // lecture gratuite). L'orienteur peut l'avoir réglé (porte, carte « espace ») sans que le tiroir le sache : on le
  // relit à l'ouverture de l'onglet, quand on approche le sélecteur (pointerdown / focus) et AVANT d'agir sur un
  // changement. Rend true si la conversation a (désormais) un espace ; le sélecteur l'affiche alors, verrouillé.
  async function apprendreEspace() {
    const e = campEtat;
    if (!e || !e.cid) return false;
    if (e.espace) return true;
    let id = "";
    try {
      const r = await fetch("/api/agent/campagnes/" + encodeURIComponent(e.cid));
      if (r.ok) { const j = await r.json(); id = j && typeof j.espace_id === "string" ? j.espace_id : ""; }
    } catch (x) { id = ""; }                    // illisible : on ne sait rien de plus, rien ne change
    if (!id || campEtat !== e) return !!(campEtat && campEtat.espace);     // une autre conversation a pris la place
    ajouterEspace(id, id);
    garderCampagne({ ...e, espace: id });
    selEspace.value = id;
    return true;
  }
  // ── t352 : l'onglet Veille ──
  let veille = null;                    // le composant monté {demonter, recharger}
  let veilleEspace = null;              // l'espace monté (null : rien encore)
  let chargementEspaces = null;         // la lecture des espaces en cours, partagée entre les deux onglets
  function lireEspaces() {
    if (!espacesLus) { espacesLus = true; chargementEspaces = chargerEspaces(); }
    return chargementEspaces || Promise.resolve();
  }
  function monterVeille(eid) {
    if (veille) { try { veille.demonter(); } catch (e) { /* déjà démonté */ } }
    veille = null;
    veilleEspace = eid;
    hoteVeille.replaceChildren();
    const D = window.DzVeille;
    if (!D || typeof D.monter !== "function") {
      hoteVeille.appendChild(el("p", { class: "dzAgentCampVide", "data-dz-agent": "veille-indisponible", texte: T("agent.veille.indisponible") }));
      return;
    }
    try { veille = D.monter(hoteVeille, { espace_id: eid }); }
    catch (e) { veille = null; hoteVeille.replaceChildren(el("p", { class: "dzAgentCampVide", "data-dz-agent": "veille-indisponible", texte: T("agent.veille.indisponible") })); }
  }
  async function ouvrirVeille() {
    await lireEspaces();
    if (veille && veilleEspace === selVeille.value) return;
    const garde = lire(window.sessionStorage, "dz_agent_veille");
    const connus = Array.from(selVeille.children).map((o) => o.getAttribute("value"));
    selVeille.value = connus.includes(garde) && garde ? garde : (connus.includes(espaceActif) ? espaceActif : "");
    monterVeille(selVeille.value);
  }
  selVeille.addEventListener("change", () => {
    ecrire(window.sessionStorage, "dz_agent_veille", selVeille.value);
    monterVeille(selVeille.value);
  });
  function ouvrirCampagnes() {
    lireEspaces();
    if (!camp) {
      selEspace.value = campEtat ? campEtat.espace : "";
      monterCampagne(campEtat ? { cid: campEtat.cid, espace: campEtat.espace } : {});
    }
    verrouiller();
    apprendreEspace();
  }
  function nouvelleCampagne(brief) {
    garderCampagne(null);
    selEspace.value = "";
    monterCampagne({ brief });
  }
  selEspace.addEventListener("pointerdown", () => { apprendreEspace(); });
  selEspace.addEventListener("focus", () => { apprendreEspace(); });
  selEspace.addEventListener("change", async () => {
    if (selEspace.hasAttribute("disabled")) return;
    const champ = hoteCampagnes.querySelector('[data-dz-camp="champ"]');
    const brief = champ ? String(champ.value || "") : "";
    const espace = selEspace.value;
    const g = genCamp;
    // la conversation a-t-elle reçu un espace côté serveur ? Alors on la garde : sélecteur remis, verrouillé
    if (await apprendreEspace()) { selEspace.value = campEtat.espace; verrouiller(); return; }
    if (g !== genCamp) return;                                  // ↺, carte… pendant la relecture : rien de plus
    garderCampagne(null);
    monterCampagne({ espace, brief });                          // conversation NEUVE : pas de cid
  });
  // la carte de passage de main : conversation neuve, espace vide, la question préremplie (jamais envoyée seule)
  function passerLaMain(question) {
    nouvelleCampagne(typeof question === "string" ? question : "");
    if (tiroir.dataset.ouvert !== "1") basculer(true);
    choisirOnglet("campagnes");
    const champ = hoteCampagnes.querySelector('[data-dz-camp="champ"]');      // le focus suit, dans le champ prérempli
    (champ || ongCampagnes).focus();
  }
  const bouton = el("button", { class: "dzAgentBtn", texte: "? " + T("agent.tiroir.bouton"),
    title: T("agent.tiroir.bouton_titre") + " — " + T("agent.place.astuce"),
    "aria-expanded": "false", "aria-controls": "dzAgentTiroir", "aria-haspopup": "menu",
    on: { click: () => { if (sansClic) { sansClic = false; return; } basculer(); } } });

  // ── t260 : la place de la bulle ──
  let place = placeLue(lire(window.localStorage, "dz_agent_place"));
  let pos = positionLue(lire(window.localStorage, "dz_agent_pos"));
  let sansClic = false;          // le clic qui suit un glisser ne doit pas ouvrir le tiroir
  const barre = () => document.querySelector("#root header");
  const fenetre = () => ({ l: window.innerWidth, h: window.innerHeight });
  const effacerStyle = () => Object.assign(bouton.style, { left: "", top: "", right: "", bottom: "" });
  function poser(p) {            // bulle flottante : coin haut-gauche en px, tenue dans la fenêtre
    const b = bouton.getBoundingClientRect();
    const q = borner(p, { l: b.width || 80, h: b.height || 32 }, fenetre());
    Object.assign(bouton.style, { left: q.x + "px", top: q.y + "px", right: "auto", bottom: "auto" });
    return q;
  }
  function placer() {
    const h = place === "barre" ? barre() : null;
    if (h) {
      if (bouton.parentNode !== h) {
        const dernier = h.lastElementChild;      // avant le dernier bouton de la barre, à côté des compteurs
        h.insertBefore(bouton, dernier && dernier.tagName === "BUTTON" ? dernier : null);
      }
      bouton.dataset.place = "barre";
      effacerStyle();
    } else {
      if (bouton.parentNode !== document.body) document.body.appendChild(bouton);
      bouton.dataset.place = "flottant";
      if (pos) poser(pos); else effacerStyle();
    }
    const t = T(place === "barre" ? "agent.place.flottant" : "agent.place.ancrer");
    btnEpingle.title = t; btnEpingle.setAttribute("aria-label", t);
    btnEpingle.setAttribute("aria-pressed", place === "barre" ? "true" : "false");
  }
  function changerPlace(p, nouvellePos) {
    place = p;
    ecrire(window.localStorage, "dz_agent_place", p);
    if (nouvellePos !== undefined) {
      pos = nouvellePos;
      if (pos) ecrire(window.localStorage, "dz_agent_pos", JSON.stringify(pos));
      else { try { window.localStorage.removeItem("dz_agent_pos"); } catch (e) { /* stockage indisponible */ } }
    }
    placer();
  }
  // React remonte la barre (changement d'écran, de langue) ou la monte après nous : on y remet le bouton
  let guet = 0;
  const veilleur = new MutationObserver(() => {
    if (guet) return;
    guet = setTimeout(() => {      // pas requestAnimationFrame : il dort quand la fenêtre est masquée
      guet = 0;
      if (appui && appui.bouge) return;
      const h = place === "barre" ? barre() : null;
      if ((h && bouton.parentNode !== h) || !bouton.isConnected) placer();
    }, 30);
  });
  window.addEventListener("resize", () => { if (bouton.dataset.place === "flottant" && pos) poser(pos); });

  // glisser : depuis la barre, la bulle en sort et devient flottante ; lâchée sur la barre, elle s'y range
  let appui = null;              // {id, depart:{x,y}, decalage:{x,y}, bouge}
  bouton.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    const b = bouton.getBoundingClientRect();
    appui = { id: ev.pointerId, depart: { x: ev.clientX, y: ev.clientY }, decalage: { x: ev.clientX - b.left, y: ev.clientY - b.top }, bouge: false };
    // capturé DÈS l'appui : un geste vif sort du bouton au premier mouvement (souvent au-dessus d'un lab en iframe)
    try { bouton.setPointerCapture(ev.pointerId); } catch (e) { /* capture refusée : le glisser suit tant qu'on reste dessus */ }
  });
  bouton.addEventListener("pointermove", (ev) => {
    if (!appui || ev.pointerId !== appui.id) return;
    const ici = { x: ev.clientX, y: ev.clientY };
    if (!appui.bouge) {
      if (!glisse(appui.depart, ici)) return;
      appui.bouge = true;
      bouton.dataset.glisse = "1";
      if (bouton.dataset.place === "barre") {
        bouton.dataset.place = "flottant";       // sort de la barre sous le pointeur, sans perdre la capture
        document.body.appendChild(bouton);
        try { bouton.setPointerCapture(ev.pointerId); } catch (e) { /* déplacer le nœud perd la capture : on la reprend */ }
      }
    }
    poser({ x: ici.x - appui.decalage.x, y: ici.y - appui.decalage.y });
  });
  function lacher(ev) {
    if (!appui || ev.pointerId !== appui.id) return;
    const a = appui; appui = null;
    if (!a.bouge) return;
    delete bouton.dataset.glisse;
    sansClic = true; setTimeout(() => { sansClic = false; }, 0);
    const h = barre(), r = h && h.getBoundingClientRect();
    if (r && ev.clientX >= r.left && ev.clientX <= r.right && ev.clientY >= r.top && ev.clientY <= r.bottom) return changerPlace("barre");
    const b = bouton.getBoundingClientRect();
    changerPlace("flottant", { x: Math.round(b.left), y: Math.round(b.top) });
  }
  bouton.addEventListener("pointerup", lacher);
  bouton.addEventListener("pointercancel", (ev) => {
    if (appui && ev.pointerId === appui.id) { appui = null; delete bouton.dataset.glisse; placer(); }
  });

  // clic droit (ou touche Menu) : le menu des places
  let menu = null;
  function fermerMenu() { if (menu) { menu.remove(); menu = null; } }
  bouton.addEventListener("contextmenu", (ev) => {
    ev.preventDefault();
    fermerMenu();
    const entrees = [];
    if (place !== "barre") entrees.push(["agent.place.ancrer", () => changerPlace("barre")]);
    if (place !== "flottant") entrees.push(["agent.place.flottant", () => changerPlace("flottant")]);
    if (place === "flottant" && pos) entrees.push(["agent.place.coin", () => changerPlace("flottant", null)]);
    menu = el("div", { class: "dzAgentMenu", role: "menu", "aria-label": T("agent.place.menu") },
      entrees.map(([cle, faire]) => el("button", { type: "button", role: "menuitem", texte: T(cle),
        on: { click: () => { fermerMenu(); faire(); bouton.focus(); } } })));
    document.body.appendChild(menu);
    const b = bouton.getBoundingClientRect(), m = menu.getBoundingClientRect();
    const x = ev.clientX || b.left, y = ev.clientY || b.bottom;
    const q = borner({ x, y: y + m.height > window.innerHeight ? y - m.height : y }, { l: m.width, h: m.height }, fenetre());
    Object.assign(menu.style, { left: q.x + "px", top: q.y + "px" });
    const premier = menu.querySelector("button");
    if (premier) premier.focus();
  });
  document.addEventListener("pointerdown", (ev) => { if (menu && !menu.contains(ev.target)) fermerMenu(); }, true);

  function basculer(ouvrir) {
    const o = ouvrir === undefined ? tiroir.dataset.ouvert !== "1" : ouvrir;
    const focusDedans = tiroir.contains(document.activeElement);
    tiroir.dataset.ouvert = o ? "1" : "0";
    bouton.setAttribute("aria-expanded", o ? "true" : "false");
    if (!o && annulerAccord) annulerAccord();      // fermer le tiroir pendant l'accord l'annule
    if (o) {
      chargement = null; chargerMoteurs().then(() => { if (!occupe) dessiner(); });     // rechargé : une clé ajoutée à chaud compte ; la voix connue fait apparaître « Lire »
      if (onglet === "campagnes") { ouvrirCampagnes(); ongCampagnes.focus(); }     // t285b
      else if (onglet === "veille") { ouvrirVeille(); ongVeille.focus(); }         // t352
      else saisie.focus();
    }
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
    // t285b : la carte de passage de main vers l'agent Campagnes ne passe pas par executer
    if (a && a.type === "campagnes") {
      return el("button", { type: "button", "data-dz-agent": "ouvrir-campagnes", texte: T("agent.action.campagnes"),
        on: { click: () => passerLaMain(typeof a.question === "string" && a.question ? a.question : (msg && msg.question) || "") } });
    }
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
    if (ev.key === "Escape" && menu) { ev.preventDefault(); fermerMenu(); bouton.focus(); return; }
    if (ev.key === "F1") { ev.preventDefault(); if (!ev.repeat) basculer(); }
    else if (ev.key === "Escape" && tiroir.dataset.ouvert === "1" && tiroir.contains(ev.target) && !dicteeEnCours()) {
      ev.preventDefault(); ev.stopPropagation(); basculer(false);
    }
    else if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing && ev.target === saisie) { ev.preventDefault(); envoyer(); }
  });

  const monter = () => {
    document.head.appendChild(css); document.body.append(bouton, tiroir); placer(); choisirOnglet(onglet); dessiner();
    veilleur.observe(document.getElementById("root") || document.body, { childList: true, subtree: true });
  };
  if (document.body) monter(); else document.addEventListener("DOMContentLoaded", monter);
}
