// mod-texte3d.js — lot D : le texte devient des CHEMINS (D4) par
// opentype.js vendorisé — donc extrudable et booléen. PUR : la police est
// fournie (opentype.Font), les commandes deviennent un d canonique.
import { chemin_parser, chemin_serialiser } from "./mod-doc.js";

// les polices du dist dont la licence est claire (Google Fonts, OFL) —
// écart dit : les polices de provenance incertaine ne sont pas proposées
export const POLICES = [
  { id: "anton", nom: "Anton", fichier: "Anton.ttf" },
  { id: "archivo", nom: "Archivo Black", fichier: "ArchivoBlack.ttf" },
  { id: "bebas", nom: "Bebas Neue", fichier: "BebasNeue.ttf" },
  { id: "bungee", nom: "Bungee", fichier: "Bungee.ttf" },
  { id: "cinzel", nom: "Cinzel", fichier: "Cinzel.ttf" },
  { id: "plex", nom: "IBM Plex Sans", fichier: "IBMPlexSans.ttf" },
  { id: "inter", nom: "Inter", fichier: "Inter.ttf" },
  { id: "jetbrains", nom: "JetBrains Mono", fichier: "JetBrainsMono.ttf" },
  { id: "monoton", nom: "Monoton", fichier: "Monoton.ttf" },
  { id: "pacifico", nom: "Pacifico", fichier: "Pacifico.ttf" },
  { id: "marker", nom: "Permanent Marker", fichier: "PermanentMarker.ttf" },
  { id: "press", nom: "Press Start 2P", fichier: "PressStart2P.ttf" },
  { id: "righteous", nom: "Righteous", fichier: "Righteous.ttf" },
  { id: "grotesk", nom: "Space Grotesk", fichier: "SpaceGrotesk.ttf" },
  { id: "staatliches", nom: "Staatliches", fichier: "Staatliches.ttf" },
  { id: "abril", nom: "Abril Fatface", fichier: "AbrilFatface.ttf" },
];

export function commandes_vers_d(cmds) {
  const parts = [];
  for (const c of cmds) {
    switch (c.type) {
      case "M": parts.push(`M ${c.x} ${c.y}`); break;
      case "L": parts.push(`L ${c.x} ${c.y}`); break;
      case "Q": parts.push(`Q ${c.x1} ${c.y1} ${c.x} ${c.y}`); break;
      case "C": parts.push(`C ${c.x1} ${c.y1} ${c.x2} ${c.y2} ${c.x} ${c.y}`); break;
      case "Z": parts.push("Z"); break;
      default: throw new Error(`glyphe : commande ${c.type} inconnue`);
    }
  }
  return parts.length ? chemin_serialiser(chemin_parser(parts.join(" "))) : "";
}

// x, y = origine de la ligne de base (comme <text>) ; taille = corps en px
export function texte_vers_d(font, texte, taille, x, y, interlettrage = 0) {
  const s = String(texte || "");
  if (!s) return "";
  const path = font.getPath(s, x, y, taille,
                            { kerning: true, letterSpacing: interlettrage / taille });
  return commandes_vers_d(path.commands);
}
