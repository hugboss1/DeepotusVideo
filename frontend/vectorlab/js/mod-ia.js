// mod-ia.js — le dialogue d'illustration IA, POSÉ SUR LE CANEVAS.
//
// Remontée du 06/09/2026 : « quand je clique sur l'icône IA une boîte de
// dialogue type chat IA doit s'ouvrir sur le canvas pour pouvoir y
// renseigner ma demande, et je dois pouvoir demander ou sélectionner le
// modèle que je veux utiliser ». Le champ vivait dans le panneau de
// droite (handoff §9) : il reste, mais l'outil du rail ouvre désormais ce
// dialogue-ci, au-dessus de la scène, déplaçable, avec le fil des
// échanges et le choix du moteur.
//
// Ce que le dialogue AJOUTE au champ du panneau :
//   - le FIL : chaque demande et son verdict restent lisibles, on relance
//     une variante sans retaper ;
//   - le MOTEUR : GET /api/vector/illustration/moteurs nomme les
//     fournisseurs configurés ET leur modèle ; le choix est transmis et
//     la route ne se replie pas sur un autre ;
//   - le COÛT DIT AVANT : le bouton porte le nom du modèle qui va
//     dépenser la clé.
// Le parsage, le filtrage et la pose des tracés restent ceux du panneau
// de verre (mod-vitrail.iaPoser) : une seule voie d'écriture au document.

import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";
export function initIA(VL) {
  const { $, etat } = VL;
  let moteurs = null;            // [{moteur, modeles[], defaut}] — null si inconnu
  let injoignable = false;       // la ROUTE ne répond pas (≠ aucune clé)
  let actif = "";                // fournisseur choisi ("" = celui des Réglages)
  let busy = false;
  const fil = [];                // [{role:"moi"|"machine", texte, err?}]

  try {
    const m = localStorage.getItem("dz_vl_ia_moteur");
    if (m) actif = m;
  } catch (e) { /* stockage indisponible */ }

  function hote() {
    let el = $("#iaDialogue");
    if (el) return el;
    el = document.createElement("div");
    el.id = "iaDialogue";
    el.className = "ia-dlg";
    el.hidden = true;
    const stage = $("#stage");
    if (!stage) return null;
    stage.appendChild(el);
    return el;
  }

  let modele = "";               // modèle choisi dans le moteur courant
  try {
    const mm = localStorage.getItem("dz_vl_ia_modele");
    if (mm) modele = mm;
  } catch (e) { /* stockage indisponible */ }

  function entree(id) { return (moteurs || []).find((x) => x.moteur === id); }
  function modelesDe(id) { const m = entree(id); return (m && m.modeles) || []; }
  function nomMoteur(id) {
    const m = entree(id);
    return m ? `${id} · ${modele || m.defaut}` : id;
  }

  function rendre() {
    const el = hote();
    if (!el || el.hidden) return;
    const dispo = moteurs || [];
    // DEUX états sourds, et il ne faut pas les confondre (mesuré le
    // 06/09/2026 : la route neuve absente, le serveur rend son index.html
    // en 200 — dire « aucune clé » serait faux et enverrait l'utilisateur
    // dans les Réglages pour rien).
    const sans = moteurs !== null && !dispo.length;
    const muet = sans && injoignable;
    const vide = sans ? (muet
      ? T("vectorlab.ia.moteurs_introuvables")
      : T("vectorlab.ia.aucune_cle")) : "";
    const choisi = actif && dispo.some((m) => m.moteur === actif) ? actif
      : (dispo[0] ? dispo[0].moteur : "");
    const mods = modelesDe(choisi);
    const modeleChoisi = modele && mods.includes(modele) ? modele
      : (mods[0] || "");
    el.innerHTML = `
      <div class="ia-tete" data-poigne="1">
        <span class="ia-titre">${T("vectorlab.ia.titre")}</span>
        <span class="ia-sp"></span>
        <button class="ia-x" data-act="fermer" title="${T("vectorlab.ia.fermer")}" aria-label="${T("vectorlab.ia.fermer")}">${dzi("dz-action-fermer", 16)}</button>
      </div>
      <div class="ia-fil">${fil.length ? fil.map((m) => `
        <div class="ia-msg ${m.role}${m.err ? " err" : ""}">${
          String(m.texte).replace(/[<&]/g, "")}</div>`).join("") : `
        <div class="ia-vide">${T("vectorlab.ia.vide")}</div>`}
      </div>
      <div class="ia-bas">
        <label class="ia-moteur">${T("vectorlab.ia.moteur")}
          <select id="iaMoteur" ${sans ? "disabled" : ""}
            title="${T("vectorlab.ia.moteur_aide")}">
            ${sans ? `<option>${vide}</option>`
              : dispo.map((m) => `<option value="${m.moteur}"${
                  m.moteur === choisi ? " selected" : ""}>${m.moteur
                  }</option>`).join("")}
          </select></label>
        <label class="ia-moteur">${T("vectorlab.ia.modele")}
          <select id="iaModele" ${sans ? "disabled" : ""}
            title="${T("vectorlab.ia.modele_aide")}">
            ${sans ? `<option>—</option>` : modelesDe(choisi).map((x) => `
              <option value="${x}"${x === modeleChoisi ? " selected" : ""}>${
                x}</option>`).join("")}
          </select></label>
        <textarea id="iaTexte" rows="2" placeholder="${T("vectorlab.ia.placeholder")}"
          ${sans ? "disabled" : ""}></textarea>
        <button id="iaGo" class="primaire" ${sans || busy ? "disabled" : ""}
          title="${muet ? T("vectorlab.ia.route_muette")
            : sans ? T("vectorlab.ia.sans_cle")
            : T("vectorlab.ia.payant", { moteur: nomMoteur(choisi) })}"
          >${dzi("dz-media-generer-image", 16)}${busy ? "…" : T("vectorlab.ia.generer")}</button>
      </div>`;
    const t = $("#iaTexte");
    if (t && !busy && !sans) t.focus();
  }

  async function charger() {
    try {
      const r = await fetch("/api/vector/illustration/moteurs");
      // route absente : le serveur rend son index.html en 200 — c'est le
      // JSON qui tranche, pas le code HTTP (mesuré le 06/09/2026)
      const d = r.ok ? await r.json() : null;
      if (d && Array.isArray(d.moteurs)) {
        moteurs = d.moteurs;
        injoignable = false;
        if (!actif && d.actif) actif = d.actif;
      } else if (d && Array.isArray(d.paths)) {
        moteurs = []; injoignable = true;      // ancienne route, sans moteurs
      } else {
        moteurs = []; injoignable = true;
      }
    } catch (e) { moteurs = []; injoignable = true; }
    rendre();
  }

  async function generer() {
    if (busy) return;
    const t = $("#iaTexte"), sel = $("#iaMoteur");
    const q = (t && t.value || "").trim();
    if (!q) {
      fil.push({ role: "machine", texte: T("vectorlab.ia.decrire_dabord"),
                 err: true });
      rendre();
      return;
    }
    const selM = $("#iaModele");
    if (sel && sel.value) {
      actif = sel.value;
      try { localStorage.setItem("dz_vl_ia_moteur", actif); }
      catch (e) { /* stockage indisponible */ }
    }
    if (selM && selM.value && selM.value !== "—") {
      modele = selM.value;
      try { localStorage.setItem("dz_vl_ia_modele", modele); }
      catch (e) { /* stockage indisponible */ }
    }
    fil.push({ role: "moi", texte: q });
    fil.push({ role: "machine", texte: T("vectorlab.ia.generation", { moteur: nomMoteur(actif) }) });
    busy = true;
    rendre();
    let issue;
    try {
      const r = await fetch("/api/vector/illustration", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: q, provider: actif, model: modele }) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || r.statusText);
      const n = VL.iaPoser ? VL.iaPoser(d, q) : 0;
      issue = { role: "machine",
                texte: T("vectorlab.ia.posees", { n, fournisseur: d.provider, modele: d.modele ? ` · ${d.modele}` : "" }) };
    } catch (e) {
      issue = { role: "machine", texte: String(e.message || e).slice(0, 200),
                err: true };
    }
    busy = false;
    fil.pop();                   // retire le « génération… »
    fil.push(issue);
    rendre();
  }

  function ouvrir() {
    const el = hote();
    if (!el) return;
    el.hidden = false;
    if (moteurs === null) charger(); else rendre();
  }
  function fermer() { const el = hote(); if (el) el.hidden = true; }

  const el = hote();
  if (el) {
    el.addEventListener("click", (ev) => {
      if (ev.target.dataset.act === "fermer") { fermer(); VL.setOutil("select"); }
      else if (ev.target.id === "iaGo") generer();
    });
    el.addEventListener("change", (ev) => {
      if (ev.target.id !== "iaMoteur") return;
      actif = ev.target.value;      // chaque moteur a SES modèles
      modele = "";
      rendre();
    });
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey && ev.target.id === "iaTexte") {
        ev.preventDefault();
        generer();
      }
      if (ev.key === "Escape") { fermer(); VL.setOutil("select"); }
    });
    /* déplaçable par sa tête — le dialogue ne doit jamais couvrir la
       partie de la page que l'on regarde */
    el.addEventListener("pointerdown", (ev) => {
      if (!ev.target.closest("[data-poigne]")) return;
      const r = el.getBoundingClientRect();
      const ox = ev.clientX - r.left, oy = ev.clientY - r.top;
      const sr = $("#stage").getBoundingClientRect();
      const bouge = (e2) => {
        el.style.left = Math.max(0, Math.min(sr.width - 60,
          e2.clientX - sr.left - ox)) + "px";
        el.style.top = Math.max(0, Math.min(sr.height - 30,
          e2.clientY - sr.top - oy)) + "px";
        el.style.right = "auto";
      };
      const fin = () => {
        window.removeEventListener("pointermove", bouge);
        window.removeEventListener("pointerup", fin);
      };
      window.addEventListener("pointermove", bouge);
      window.addEventListener("pointerup", fin);
      ev.preventDefault();
    });
  }

  VL.iaOuvrir = ouvrir;
  VL.iaFermer = fermer;
  const suivant = VL.surOutil;
  VL.surOutil = () => {
    suivant();
    if (etat.outil === "ia") ouvrir(); else fermer();
  };
}
