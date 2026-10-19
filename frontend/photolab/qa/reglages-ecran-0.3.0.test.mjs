// qa/reglages-ecran-0.3.0.test.mjs — t251 : le banc de l'éditeur des réglages rejoué sur la fixture 0.3.0 (variantes
// internes) ; qa/reglages-ecran.test.mjs, lui, tourne sur celle du moteur épinglé (0.10, {kind, params}).
globalThis.__dzFixtureReglages = "reglages-inspect-0.3.0.json";
await import("./reglages-ecran.test.mjs?forme=0.3.0");
delete globalThis.__dzFixtureReglages;
