"""t460 (08/11/2026) — lot D3 « Déformer », T1 : déformations vivantes dans le module NEUF js/mod-deformer.js (hors
table). Éditions de modules de BASE consignées ici (S) :
  * mod-doc.js : un objet `cache` n'est pas dessiné (la source d'une déformation, hors « Modifier le contenu ») —
    le rendu, l'export et l'impression passent tous par compilerObjet ;
  * mod-bool.js : les enfants `cache` d'un groupe ne comptent pas dans sa géométrie (Pathfinder, découpes…).
(op_derive_detacher décompose aussi une déformation : l'entrée S de t450.py, qui porte la ligne, est étendue.)
Les messages de la zone vectorlab.deformer sont saisis en entrées H."""
from outils import L, S, X, H  # noqa: F401

DOC = "js/mod-doc.js"
BOOL = "js/mod-bool.js"

ENTREES = [
    S(DOC, 325, "function compilerObjet(o, ctx = {}) {",
      "function compilerObjet(o, ctx = {}) {\r\n"
      "  if (o && o.cache) return \"\";   // t460 : la source cachée d'une déformation vivante ne se dessine pas", {}),
    S(BOOL, 135, "for (const e of objet.enfants || []) {",
      "for (const e of objet.enfants || []) {\r\n"
      "        if (e.cache) continue;   // t460 : la source cachée d'une déformation ne compte pas", {}),
    H("vectorlab.deformer.rien", "Déformer : sélectionnez un ou plusieurs objets", "Distort: select one or more objects"),
    H("vectorlab.deformer.sans_geometrie",
      "Déformer : cet objet n'a pas de forme à déformer (convertissez un texte en courbes d'abord)",
      "Distort: this object has no shape to distort (convert a text to outlines first)"),
    H("vectorlab.deformer.effet", "Déformer : effet inconnu « {effet} »", "Distort: unknown effect “{effet}”"),
    H("vectorlab.deformer.style", "Enveloppe : style inconnu « {style} »", "Envelope: unknown style “{style}”"),
    H("vectorlab.deformer.orientation", "Enveloppe : l'orientation est horizontale ou verticale",
      "Envelope: the orientation is horizontal or vertical"),
    H("vectorlab.deformer.pourcent", "Déformer : la valeur va de {min} à {max} %", "Distort: the value ranges from {min} to {max}%"),
    H("vectorlab.deformer.introuvable", "Déformer : objet introuvable ({id})", "Distort: object not found ({id})"),
    H("vectorlab.deformer.pas_deformation", "{id} n'est pas une déformation", "{id} is not a distortion"),
]
