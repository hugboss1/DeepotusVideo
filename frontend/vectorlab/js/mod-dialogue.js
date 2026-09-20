// mod-dialogue.js — dialogues maison (confirmer / informer / saisir) qui
// REMPLACENT confirm / alert / prompt natifs (le « 127.0.0.1:8765 indique »
// des captures du 19/09/2026). Partie PURE bancable en tête (spécification,
// touches, cycle de focus) ; partie DOM ensuite : initDialogue(VL) pose
// VL.dialogue.{confirmer, informer, saisir} — toutes asynchrones — rendues
// dans #vlDlg avec le patron .vl-dlg-boite / .vl-dlg-tete de mod-impression.

export function dialogue_spec(type, message, o = {}) {
  const t = ["confirmer", "informer", "saisir"].includes(type) ? type : "informer";
  const corps = String(message ?? "").split("\n").map((l) => l.trim()).filter(Boolean);
  const titre = o.titre || { confirmer: "Confirmer", informer: "Information", saisir: "Saisie" }[t];
  const okLib = o.ok || o.valider || (t === "informer" ? "Fermer" : "OK");
  const boutons = t === "informer"
    ? [{ role: "ok", libelle: okLib, danger: false }]
    : [{ role: "annuler", libelle: o.annuler || "Annuler", danger: false },
       { role: "ok", libelle: okLib, danger: !!o.danger }];
  const champ = t === "saisir" ? { valeur: String(o.valeur ?? ""), placeholder: o.placeholder || "" } : null;
  const defaut = (t === "confirmer" && o.danger) ? "annuler" : "ok";
  return { type: t, titre, corps, boutons, champ, defaut };
}

export function dialogue_touche(spec, key) {
  if (key === "Enter") return spec.defaut;
  if (key === "Escape") return spec.type === "informer" ? "ok" : "annuler";
  return null;
}

export function focus_suivant(n, i, arriere) {
  if (!n) return -1;
  return ((arriere ? i - 1 : i + 1) + n) % n;
}

/* ── DOM ── */
export function initDialogue(VL) {
  let hote = document.querySelector("#vlDlg");
  if (!hote) {
    hote = document.createElement("div");
    hote.id = "vlDlg"; hote.className = "vl-dlg hidden";
    document.body.appendChild(hote);
  }
  let courant = null;   // { resoudre, spec }
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function fermer(role) {
    if (!courant) return;
    const { resoudre, spec } = courant; courant = null;
    const champ = hote.querySelector("input");
    const val = spec.type === "saisir" && champ ? champ.value : null;
    hote.classList.add("hidden"); hote.innerHTML = "";
    if (spec.type === "confirmer") resoudre(role === "ok");
    else if (spec.type === "saisir") resoudre(role === "ok" ? String(val ?? "") : null);
    else resoudre(undefined);
  }

  function ouvrir(spec) {
    if (courant) fermer("annuler");
    return new Promise((resoudre) => {
      courant = { resoudre, spec };
      hote.innerHTML = `<div class="vl-dlg-boite vl-dlg-petite" role="dialog" aria-modal="true" aria-label="${esc(spec.titre)}">
        <div class="vl-dlg-tete"><b>${esc(spec.titre)}</b><span class="spacer"></span><button data-role="${spec.type === "informer" ? "ok" : "annuler"}" title="Fermer">✕</button></div>
        <div class="vl-dlg-corps">${spec.corps.map((l) => `<p>${esc(l)}</p>`).join("")}${spec.champ ? `<input type="text" value="${esc(spec.champ.valeur)}" placeholder="${esc(spec.champ.placeholder)}">` : ""}</div>
        <div class="vl-dlg-pied">${spec.boutons.map((b) => `<button data-role="${b.role}" class="${b.danger ? "vl-dlg-danger" : ""}${b.role === spec.defaut ? " vl-dlg-defaut" : ""}">${esc(b.libelle)}</button>`).join("")}</div>
      </div>`;
      hote.classList.remove("hidden");
      hote.querySelectorAll("[data-role]").forEach((b) => b.addEventListener("click", () => fermer(b.dataset.role)));
      const champ = hote.querySelector("input");
      if (champ) { champ.focus(); champ.select(); }
      else (hote.querySelector(".vl-dlg-pied .vl-dlg-defaut") || hote.querySelector(".vl-dlg-pied button")).focus();
    });
  }

  hote.addEventListener("click", (ev) => {
    if (ev.target === hote && courant) fermer(courant.spec.type === "informer" ? "ok" : "annuler");
  });
  document.addEventListener("keydown", (ev) => {
    if (!courant) return;
    ev.stopPropagation();
    if (ev.key === "Tab") {
      const f = [...hote.querySelectorAll("input, button")];
      const i = Math.max(0, f.indexOf(document.activeElement));
      ev.preventDefault();
      const s = f[focus_suivant(f.length, i, ev.shiftKey)];
      if (s) s.focus();
      return;
    }
    const role = dialogue_touche(courant.spec, ev.key);
    if (role) { ev.preventDefault(); fermer(role); }
  }, true);

  VL.dialogue = {
    confirmer: (message, o = {}) => ouvrir(dialogue_spec("confirmer", message, o)),
    informer: (message, o = {}) => ouvrir(dialogue_spec("informer", message, o)),
    saisir: (message, o = {}) => ouvrir(dialogue_spec("saisir", message, o)),
    ouvert: () => !!courant,
  };
}
