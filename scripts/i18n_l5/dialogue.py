"""t145 — dialogue : les dialogues maison de TOUTE l'application (window.__dzDialogue : confirmer, informer, saisir),
frontend/shared/dialogue.js (copies octet pour octet dans frontend/patches/ et frontend/dist/shared/).

Vanilla DOM, chargé dans le bundle ET dans les pages des labs : dzT n'est pas garanti au moment du chargement (il l'est
quand un dialogue s'ouvre, le runtime dz-i18n.js passant avant) — les libellés passent par __dzT(clé, repli), qui rend
le français si le runtime manque. Gardés : les rôles des boutons ("ok", "annuler"), comparés par fin(role) ; la
détection du danger lit le MESSAGE (français ou anglais : supprimer|delete|remove…), pas un libellé."""
from outils import S, X

CIBLE = "dialogue"
PLAGE = (1, 117)

ENTREES = [
    S('''      var titre = o.titre || (type === "confirmer" ? "Confirmer" : type === "saisir" ? "Saisie" : "Information");''',
      '''      var titre = o.titre || (type === "confirmer" ? __dzT("dialogue.titre.confirmer", "Confirmer")
        : type === "saisir" ? __dzT("dialogue.titre.saisie", "Saisie") : __dzT("dialogue.titre.information", "Information"));''',
      {"dialogue.titre.confirmer": ("Confirmer", "Confirm"), "dialogue.titre.saisie": ("Saisie", "Input"),
       "dialogue.titre.information": ("Information", "Information")}),
    S('''        ? [["ok", o.ok || "Fermer", S.ok]]
        : [["annuler", o.annuler || "Annuler", ""], ["ok", o.ok || (danger ? "Supprimer" : "OK"), danger ? S.danger : S.ok]];''',
      '''        ? [["ok", o.ok || __dzT("commun.action.fermer", "Fermer"), S.ok]]
        : [["annuler", o.annuler || __dzT("commun.action.annuler", "Annuler"), ""],
           ["ok", o.ok || (danger ? __dzT("commun.action.supprimer", "Supprimer") : __dzT("dialogue.bouton.ok", "OK")), danger ? S.danger : S.ok]];''',
      {"commun.action.fermer": ("Fermer", "Close"), "commun.action.annuler": ("Annuler", "Cancel"),
       "commun.action.supprimer": ("Supprimer", "Delete"), "dialogue.bouton.ok": ("OK", "OK")}),
    S('''  var courant = null;
  function ouvrir(type, message, o) {''',
      '''  var courant = null;
  // t145 : libellés par le runtime dz-i18n (chargé avant cette couche partout) ; repli français s'il manque
  function __dzT(cle, repli) { return typeof window.dzT === "function" ? window.dzT(cle) : repli; }
  function ouvrir(type, message, o) {''', {}),
    X('"input, button"', "sélecteur CSS"),
]
ENTREES += [X('"Enter"', "valeur de touche (ev.key) comparée"), X('"Escape"', "valeur de touche (ev.key) comparée"),
            X('"Tab"', "valeur de touche (ev.key) comparée")]
