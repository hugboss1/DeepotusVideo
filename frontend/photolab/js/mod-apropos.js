// mod-apropos.js — « À propos du Photolab » (t140, P5, décision D8) : le moteur, sa version et sa licence, les crédits
// des matériaux repris, et CHAQUE texte de licence livré, lisible sur place (GET /api/photolab/licences). Ni nom ni logo
// ArtCraft. Logique PURE exportée (qa/apropos.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";

const FAMILLES = { "Inter": "Inter", "JetBrainsMono": "JetBrains Mono", "biz-ud-mincho": "BIZ UDMincho",
  "biz-ud-pgothic": "BIZ UDPGothic", "shippori-mincho": "Shippori Mincho" };

// Nom de fichier -> libellé lisible (dictionnaire) ; un fichier inconnu garde son nom.
export function libelleLicence(nom, T) {
  const base = String(nom).split("/").pop();
  if (nom === "NOTICE-photocraft.txt") return T("photolab.apropos.lic.notice");
  if (nom === "licences-photocraft/NOTICE") return T("photolab.apropos.lic.notice_amont");
  if (base === "LICENSE-MIT") return T("photolab.apropos.lic.mit");
  if (base === "LICENSE-APACHE") return T("photolab.apropos.lic.apache");
  if (base === "LICENSE-SCOWL.txt") return T("photolab.apropos.lic.scowl");
  if (base === "LICENSE-lucide.txt") return T("photolab.apropos.lic.lucide");
  const m = /^OFL-(.+)\.txt$/.exec(base);
  if (m && FAMILLES[m[1]]) return T("photolab.apropos.lic.police", { famille: FAMILLES[m[1]] });
  return base;
}

const RANG = (nom) => (nom === "NOTICE-photocraft.txt" ? 0 : nom === "licences-photocraft/NOTICE" ? 1 : 2);

// info = réponse de GET /licences (ou null si le pont ne répond pas : les crédits restent).
export function contenuApropos(info, T) {
  const i = info || {};
  const version = i.version || "0.3.0";
  const licence = String(i.licence || "MIT OR Apache-2.0").replace(" OR ", " " + T("photolab.apropos.ou") + " ");
  const lignes = [
    T("photolab.apropos.moteur_v", { version, licence }),
    T("photolab.apropos.icones"),
    T("photolab.apropos.polices"),
    T("photolab.apropos.mots"),
  ];
  const licences = (Array.isArray(i.fichiers) ? i.fichiers : []).slice()
    .sort((a, b) => RANG(a) - RANG(b))
    .map((nom) => ({ nom, libelle: libelleLicence(nom, T), url: "/api/photolab/licences/" + nom.split("/").map(encodeURIComponent).join("/") }));
  return { titre: T("photolab.apropos.titre"), lignes, licences, depot: "https://github.com/" + (i.depot || "storytold/photocraft") };
}

export function initApropos(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.apropos = async function apropos() {
    let info = null;
    try { const r = await fetch("/api/photolab/licences"); if (r.ok) info = await r.json(); } catch (e) { info = null; }
    const c = contenuApropos(info, T);
    await ouvrirDialogue(PL, {
      titre: c.titre, classe: "large apropos",
      boutons: [{ role: "fermer", libelle: T("commun.action.fermer"), principal: true }],
      construire({ corps }) {
        const tete = document.createElement("div"); tete.className = "ap-tete";
        for (const l of c.lignes) { const p = document.createElement("p"); p.textContent = l; tete.appendChild(p); }
        const a = document.createElement("a"); a.href = c.depot; a.target = "_blank"; a.rel = "noopener noreferrer";
        a.textContent = c.depot.replace("https://", ""); a.setAttribute("data-dz-brut", "");
        tete.appendChild(a);
        const bas = document.createElement("div"); bas.className = "ap-bas";
        const liste = document.createElement("div"); liste.className = "ap-liste"; liste.setAttribute("role", "listbox");
        const texte = document.createElement("pre"); texte.className = "ap-texte"; texte.setAttribute("data-dz-brut", "");
        texte.textContent = c.licences.length ? "" : T("photolab.apropos.sans_liste");
        const montrer = async (l, b) => {
          liste.querySelectorAll(".ap-lic").forEach((x) => x.classList.toggle("actif", x === b));
          texte.textContent = T("commun.etat.chargement");
          try { const r = await fetch(l.url); texte.textContent = r.ok ? await r.text() : T("photolab.apropos.illisible"); }
          catch (e) { texte.textContent = T("photolab.apropos.illisible"); }
          texte.scrollTop = 0;
        };
        c.licences.forEach((l, k) => {
          const b = document.createElement("button"); b.type = "button"; b.className = "ap-lic"; b.textContent = l.libelle; b.title = l.nom;
          b.addEventListener("click", () => montrer(l, b));
          liste.appendChild(b);
          if (k === 0) montrer(l, b);
        });
        bas.append(liste, texte);
        corps.append(tete, bas);
      },
    });
  };
}
