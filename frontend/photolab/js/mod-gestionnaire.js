// mod-gestionnaire.js — t159 (parité L9) : Édition › Préréglages › Gestionnaire de préréglages et Exporter/importer
// des préréglages. Le moteur sert les trois genres qu'il gère (edit.presets.presetManager : pinceaux, formes
// personnalisées, motifs — renommer, supprimer, déplacer par INDEX) et l'échange en DONNÉES
// (edit.presets.exportImportPresets) : l'export se télécharge en .json, l'import lit un .json du PC dans la page et
// l'envoie tel quel ; le pont vérifie forme, taille et l'absence de tout chemin (photolab_registre._v_echange).
// En mode serve le moteur ne garde rien entre deux sessions : l'export est le moyen de conserver ses préréglages.
// « Migrer les préréglages » lit un chemin : refusée, reste « bientôt ». Fonctions PURES exportées (qa/gestionnaire.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";

export const GENRES = ["brushes", "customShapes", "patterns"];
export const GENRES_ECHANGE = ["brushes", "customShapes"];
export const MAX_OCTETS = 2_000_000;
export const cleGenre = (g) => "photolab.gestionnaire.genre." + g.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());

// Déplacement d'un cran : null si impossible (bord de la liste).
export function deplacement(index, sens, longueur) {
  const to = index + sens;
  return to < 0 || to >= longueur ? null : { index, to };
}
// Contenu d'un fichier choisi -> données d'import, ou {erreur} (clé du dictionnaire). La forme fine est jugée par le pont.
export function lireFichier(texte) {
  if (typeof texte !== "string" || texte.length > MAX_OCTETS) return { erreur: "photolab.gestionnaire.trop_gros" };
  let d;
  try { d = JSON.parse(texte); } catch (e) { return { erreur: "photolab.gestionnaire.illisible" }; }
  if (!d || typeof d !== "object" || d.format !== "photocraft-presets") return { erreur: "photolab.gestionnaire.pas_presets" };
  return { donnees: d };
}
export const nomFichier = (date = new Date()) => `preregles-photolab-${date.toISOString().slice(0, 10)}.json`;

export function initGestionnaire(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const appel = (params) => PL.post("/executer", { command: "edit.presets.presetManager", params });
  const confirmer = async (question, titre, ok) => {
    const d = window.__dzDialogue;
    if (d) return d.confirmer(question, { titre, ok });
    return (await ouvrirDialogue(PL, {
      titre, construire({ corps }) { corps.appendChild(el("p", null, question)); },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: ok, principal: true }],
    })) === "ok";
  };
  const relireTout = () => { if (PL.pinceaux) PL.pinceaux.relire(); for (const f of PL.relirePresets || []) f(); };
  const demanderNom = (actuel) => {
    if (window.__dzDialogue) return window.__dzDialogue.saisir(T("photolab.gestionnaire.nouveau_nom"), { valeur: actuel, titre: T("commun.action.renommer") }).then((v) => (v == null ? null : v.trim() || null));
    let v = null;
    return ouvrirDialogue(PL, {
      titre: T("commun.action.renommer"),
      construire({ corps }) { const i = el("input"); i.type = "text"; i.maxLength = 64; i.value = actuel; i.setAttribute("data-dz-brut", ""); corps.appendChild(i); return () => { v = i.value.trim(); return !!v; }; },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.renommer"), principal: true }],
    }).then((r) => (r === "ok" ? v : null));
  };

  async function gestionnaire() {
    let genre = "brushes", noms = [], choisi = -1;
    await ouvrirDialogue(PL, {
      titre: T("photolab.gestionnaire.titre"), classe: "large pl-gestionnaire",
      boutons: [{ role: "ok", libelle: T("commun.action.fermer"), principal: true }],
      construire({ corps }) {
        const tete = el("div", "cl-tete");
        const choix = el("select"); choix.setAttribute("aria-label", T("photolab.gestionnaire.genre"));
        for (const g of GENRES) { const o = el("option", null, T(cleGenre(g))); o.value = g; choix.appendChild(o); }
        const actions = el("div", "gs-actions");
        const bt = (cle, f) => { const b = el("button", "pl-bouton", T(cle)); b.type = "button"; b.addEventListener("click", f); actions.appendChild(b); return b; };
        const monter = bt("photolab.gestionnaire.monter", () => deplacer(-1));
        const descendre = bt("photolab.gestionnaire.descendre", () => deplacer(+1));
        const renommer = bt("commun.action.renommer", async () => {
          const n = await demanderNom(noms[choisi]);
          if (!n || n === noms[choisi]) return;
          await agir({ action: "rename", index: choisi, newName: n });
        });
        const supprimer = bt("commun.action.supprimer", async () => {
          if (!(await confirmer(T("photolab.gestionnaire.supprimer_q", { nom: noms[choisi] }), T("commun.action.supprimer"), T("commun.action.supprimer")))) return;
          await agir({ action: "delete", index: choisi });
          choisi = Math.min(choisi, noms.length - 1);
          dessiner();
        });
        tete.append(choix, actions);
        const liste = el("div", "cl-liste gs-liste"); liste.setAttribute("role", "listbox");
        const note = el("p", "pf-note", T("photolab.gestionnaire.session"));
        corps.append(tete, liste, note);
        choix.addEventListener("change", () => { genre = choix.value; choisi = -1; lire(); });

        async function agir(params) {
          let r;
          try { r = await appel({ ...params, kind: genre }); } catch (e) { return; }
          if (r && Array.isArray(r[genre])) noms = r[genre];
          dessiner();
        }
        async function deplacer(sens) {
          const d = deplacement(choisi, sens, noms.length);
          if (!d) return;
          await agir({ action: "move", ...d });
          choisi = d.to; dessiner();
        }
        async function lire() {
          let r;
          try { r = await appel({ action: "list", kind: genre }); } catch (e) { noms = []; dessiner(); return; }
          noms = (r && r[genre]) || [];
          dessiner();
        }
        function dessiner() {
          liste.replaceChildren();
          noms.forEach((n, i) => {
            const l = el("div", "cl-ligne gs-ligne" + (i === choisi ? " actif" : ""), n);
            l.setAttribute("role", "option"); l.setAttribute("aria-selected", i === choisi ? "true" : "false");
            l.setAttribute("data-dz-brut", "");
            l.addEventListener("click", () => { choisi = i; dessiner(); });
            liste.appendChild(l);
          });
          const sel = choisi >= 0 && choisi < noms.length;
          monter.disabled = !sel || choisi === 0; descendre.disabled = !sel || choisi === noms.length - 1;
          renommer.disabled = !sel; supprimer.disabled = !sel;
        }
        lire();
      },
    });
    relireTout();
  }

  async function echange() {
    await ouvrirDialogue(PL, {
      titre: T("photolab.echange.titre"), classe: "pl-echange",
      boutons: [{ role: "ok", libelle: T("commun.action.fermer"), principal: true }],
      construire({ corps }) {
        const cases = {};
        for (const g of GENRES_ECHANGE) {
          const l = el("label", "pl-champ pl-case"); const c = el("input"); c.type = "checkbox"; c.checked = true; cases[g] = c;
          l.append(c, el("span", null, T(cleGenre(g)))); corps.appendChild(l);
        }
        const tous = el("label", "pl-champ pl-case"); const ct = el("input"); ct.type = "checkbox";
        tous.append(ct, el("span", null, T("photolab.echange.integres"))); corps.appendChild(tous);
        const ligne = el("div", "gs-actions");
        const bExp = el("button", "pl-bouton", T("commun.action.exporter_suite")); bExp.type = "button";
        const bImp = el("button", "pl-bouton", T("commun.action.importer_suite")); bImp.type = "button";
        const fichier = el("input"); fichier.type = "file"; fichier.accept = ".json,application/json"; fichier.hidden = true;
        ligne.append(bExp, bImp, fichier);
        const msg = el("p", "pl-erreur"); msg.setAttribute("role", "status");
        corps.append(ligne, el("p", "pf-note", T("photolab.gestionnaire.session")), msg);
        const kinds = () => GENRES_ECHANGE.filter((g) => cases[g].checked);
        bExp.addEventListener("click", async () => {
          if (!kinds().length) { msg.textContent = T("photolab.echange.aucun"); return; }
          let r;
          try { r = await PL.post("/executer", { command: "edit.presets.exportImportPresets", params: { action: "export", kinds: kinds(), includeBuiltins: ct.checked } }); }
          catch (e) { return; }
          const a = document.createElement("a");
          a.href = URL.createObjectURL(new Blob([JSON.stringify(r.data)], { type: "application/json" }));
          a.download = nomFichier();
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(() => URL.revokeObjectURL(a.href), 1000);
          msg.textContent = T("photolab.echange.exportes", { n: (r.brushes || 0) + (r.customShapes || 0) });
        });
        bImp.addEventListener("click", () => { if (!kinds().length) { msg.textContent = T("photolab.echange.aucun"); return; } fichier.click(); });
        fichier.addEventListener("change", async () => {
          const f = fichier.files && fichier.files[0];
          fichier.value = "";
          if (!f) return;
          if (f.size > MAX_OCTETS) { msg.textContent = T("photolab.gestionnaire.trop_gros"); return; }
          const l = lireFichier(await f.text());
          if (l.erreur) { msg.textContent = T(l.erreur); return; }
          let r;
          try { r = await PL.post("/executer", { command: "edit.presets.exportImportPresets", params: { action: "import", kinds: kinds(), data: l.donnees } }); }
          catch (e) { msg.textContent = e.message || String(e); return; }
          msg.textContent = T("photolab.echange.importes", { n: (r.brushes || 0) + (r.customShapes || 0) });
          relireTout();
        });
      },
    });
  }

  PL.actions = PL.actions || {};
  PL.actions["edit.presets.presetManager"] = gestionnaire;
  PL.actions["edit.presets.exportImportPresets"] = echange;
  PL.gestionnaire = { gestionnaire, echange };
}
