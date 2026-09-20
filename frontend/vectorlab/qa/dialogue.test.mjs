// dialogue.test.mjs — mod-dialogue : la spécification pure d'un dialogue
// maison (confirmer / informer / saisir), les touches et le cycle de focus.
import { dialogue_spec, dialogue_touche, focus_suivant } from "../js/mod-dialogue.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : "")); };
{
  const c = dialogue_spec("confirmer", "Supprimer le calque « A » ?\nSes objets aussi.", { danger: true });
  ok("confirmer : titre par défaut, corps en lignes, deux boutons OK/Annuler, OK danger, défaut = annuler quand danger",
     c.titre === "Confirmer" && c.corps.length === 2 && c.boutons.length === 2
     && c.boutons[0].role === "annuler" && c.boutons[1].role === "ok" && c.boutons[1].danger === true && c.defaut === "annuler", JSON.stringify(c));
  const c2 = dialogue_spec("confirmer", "Continuer ?", { ok: "Restaurer", annuler: "Repartir du serveur", titre: "Brouillon" });
  ok("confirmer : libellés et titre personnalisés, défaut = ok sans danger", c2.titre === "Brouillon" && c2.boutons[1].libelle === "Restaurer" && c2.boutons[0].libelle === "Repartir du serveur" && c2.defaut === "ok", JSON.stringify(c2));
  const i = dialogue_spec("informer", "Enregistré.");
  ok("informer : un seul bouton Fermer (role ok), défaut ok, pas de champ", i.boutons.length === 1 && i.boutons[0].role === "ok" && i.defaut === "ok" && i.champ === null, JSON.stringify(i));
  const s = dialogue_spec("saisir", "Nom :", { valeur: "calque 1", valider: "Renommer" });
  ok("saisir : un champ avec la valeur initiale, bouton OK libellé, défaut ok", s.champ && s.champ.valeur === "calque 1" && s.boutons[1].libelle === "Renommer" && s.defaut === "ok", JSON.stringify(s));
  ok("état vide : message vide → corps [], type inconnu → informer", dialogue_spec("saisir", "").corps.length === 0 && dialogue_spec("zzz", "x").boutons.length === 1);
  ok("touches : Entrée = défaut, Échap = annuler (ou ok pour informer), autre = null",
     dialogue_touche(c, "Enter") === "annuler" && dialogue_touche(c2, "Enter") === "ok" && dialogue_touche(c, "Escape") === "annuler" && dialogue_touche(i, "Escape") === "ok" && dialogue_touche(c, "a") === null);
  ok("focus piégé : Tab avance, Maj+Tab recule, cyclique", focus_suivant(3, 2, false) === 0 && focus_suivant(3, 0, true) === 2 && focus_suivant(3, 1, false) === 2 && focus_suivant(0, 0, false) === -1);
}
if (echecs.length) { console.error("ECHECS dialogue :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA dialogue : PASS (7 controles)");
