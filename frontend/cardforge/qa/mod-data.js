/* qa — faux P4. Le seul jeton qui porte setCards. */
"use strict";

(function () {
  const CF = window.CF;
  const rec = (k, verdict, detail) => window.__CFQA.push({ k, verdict, detail: String(detail) });
  const M = CF.register({
    id: "data",
    title: "Données (qa)",
    order: 4,
    state: { rows: [] },
    init(host) { host.textContent = "data(qa)"; },
  });
  window.__QA_DATA = M;
  try {
    const n = M.setCards([{ id: "a" }, { id: "b" }, { id: "c" }]).length;
    rec("jeton data : setCards", n === 3 ? "TENU" : "OUVERT", n + " cartes");
  } catch (e) {
    rec("jeton data : setCards", "OUVERT", e.message);
  }
})();
