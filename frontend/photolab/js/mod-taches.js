// mod-taches.js — t419 (Photolab N9, photocraft 0.21) : les longues opérations du moteur en tâche de fond. Le filtre part avec
// `fond: true`, le moteur rend aussitôt un numéro de tâche, l'écran lit sa progression et peut l'annuler (Échap ou bouton).
// Un filtre annulé ou en échec laisse le document intact. La barre n'apparaît qu'après DELAI_BARRE : un filtre rapide ne
// fait rien clignoter. Fonctions PURES exportées (qa/taches-n9.test.mjs).

export const DELAI_BARRE = 400, PAS_LECTURE = 200;
export const estTacheLongue = (id) => typeof id === "string" && (id.startsWith("filter.") || id === "edit.contentAwareFill" || id === "edit.contentAwareScale");
export const pctTache = (j) => Math.max(0, Math.min(100, Math.round((Number(j && j.progress) || 0) * 100)));

// {state} de /taches/<n> -> ce que l'écran doit faire ; null : encore en cours.
export function issueTache(j) {
  if (!j || j.state === "running") return null;
  if (j.state === "done") return { ok: true, r: j.result };
  if (j.state === "cancelled") return { ok: false, annule: true };
  return { ok: false, erreur: j.error || j.message || "" };
}

// Lit la tâche jusqu'à sa fin. `lire(job)`, `attendre(ms)`, `maintenant()` et `montrer(pct)` sont fournis par l'écran (ou le banc).
export async function suivre(job, { lire, attendre, maintenant, montrer }) {
  const t0 = maintenant();
  for (;;) {
    let j;
    try { j = await lire(job); } catch (e) { return { ok: false, erreur: (e && e.message) || "" }; }
    const fin = issueTache(j);
    if (fin) return fin;
    if (maintenant() - t0 >= DELAI_BARRE) montrer(pctTache(j));
    await attendre(PAS_LECTURE);
  }
}

export function initTaches(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  let barre = null;
  const fermer = () => { if (barre) { barre.remove(); barre = null; } };
  function afficher(job) {
    const b = document.createElement("div"); b.className = "pl-tache"; b.setAttribute("role", "status");
    const lib = document.createElement("span"); lib.textContent = T("photolab.tache.calcul");
    const p = document.createElement("progress"); p.max = 100; p.value = 0; p.setAttribute("aria-label", T("photolab.tache.calcul"));
    const v = document.createElement("span"); v.className = "pl-tache-pct";
    const a = document.createElement("button"); a.type = "button"; a.className = "pl-bouton"; a.textContent = T("commun.action.annuler");
    a.addEventListener("click", () => annuler(job));
    b.append(lib, p, v, a); document.body.appendChild(b);
    return { b, p, v, remove: () => b.remove() };
  }
  const annuler = (job) => PL.post(`/taches/${job}/annuler`, {}).catch(() => {});

  PL.suivreTache = async (job) => {
    const echap = (ev) => { if (ev.key === "Escape") { ev.stopPropagation(); ev.preventDefault(); annuler(job); } };
    document.addEventListener("keydown", echap, true);
    try {
      const fin = await suivre(job, {
        lire: (n) => PL.get(`/taches/${n}`, true), attendre: (ms) => new Promise((r) => setTimeout(r, ms)), maintenant: () => performance.now(),
        montrer: (pct) => { if (!barre) barre = afficher(job); barre.p.value = pct; barre.v.textContent = pct + " %"; },
      });
      if (fin.annule) PL.signaler(T("photolab.tache.annulee"));
      else if (!fin.ok) PL.signaler(fin.erreur || T("photolab.tache.echec"), true);
      return fin;
    } finally {
      document.removeEventListener("keydown", echap, true);
      fermer();
    }
  };
}
