// mod-envoi.js — t139 (Photolab P4, 08/10/2026) : recevoir une image envoyée par un autre écran (« Envoyer vers ›
// Vectorlab » de la Bibliothèque ou du Photolab ; contrat frontend/shared/dz-envoi.js).
// Sans document ouvert : un document NEUF à la taille de l'image est créé, puis ouvert avec `?doc=…&img=…` ; une fois
// le document chargé, l'image y est posée (calque actif) et `img` quitte l'URL. Logique PURE exportée
// (qa/envoi.test.mjs).
import { recevoir } from "../../shared/dz-envoi.js";
import { docVierge } from "./mod-biblio.js";

export const COTE_MAX = 8192;            // borne de la création (parseTaille de mod-biblio)

export function tailleDoc(w, h) {
  if (!(Number.isFinite(w) && Number.isFinite(h) && w > 0 && h > 0)) throw new Error("taille de l'image illisible");
  const k = Math.min(1, COTE_MAX / Math.max(w, h));
  return { w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k)) };
}

// « photolab_20261008-154030_herbe.png » -> « herbe » ; « Mon image.jpg » -> « Mon image ».
function nomDe(fichier) {
  const s = String(fichier || "").replace(/\.[A-Za-z0-9]{2,6}$/, "");
  const m = /^photolab_\d{8}-\d{6}_(.+)$/.exec(s);
  return ((m ? m[1] : s) || "Sans titre").slice(0, 120);
}

export function corpsCreation(fichier, w, h) {
  const name = nomDe(fichier);
  return { name, role: "libre", doc: docVierge(name, w, h) };
}

export function suite(id, image) {
  return "?doc=" + encodeURIComponent(id) + "&img=" + encodeURIComponent(image);
}

// Les dimensions naturelles d'une image de la Bibliothèque (onload : decode() reste suspendu dans un onglet caché).
function dimensions(nom) {
  return new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => res({ w: im.naturalWidth, h: im.naturalHeight });
    im.onerror = () => rej(new Error(`Bibliothèque : « ${nom} » introuvable`));
    im.src = "/api/images/" + encodeURIComponent(nom);
  });
}

export function initEnvoi(VL) {
  // Sans ?doc : un envoi crée son document (true = la page part vers ce document, ne rien afficher d'autre).
  VL.recevoirEnvoi = async () => {
    const r = recevoir("vectorlab");
    if (!r) return false;
    try {
      const nat = await dimensions(r.image);
      const { w, h } = tailleDoc(nat.w, nat.h);
      const rep = await fetch("/api/vector/docs", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpsCreation(r.image, w, h)),
      });
      const d = await rep.json().catch(() => ({}));
      if (!rep.ok) throw new Error(d.detail || rep.statusText);
      location.replace(suite(d.id, r.image));
      return true;
    } catch (e) {
      VL.toast(`Envoi vers le Vectorlab : ${e.message}`, true);
      return false;
    }
  };
  // Document chargé : l'image de `?img=` (ou d'un envoi frais) est posée, une fois.
  VL.poserEnvoi = () => {
    const r = recevoir("vectorlab");
    if (!r) return;
    VL.poserDepuisLibrary(r.image).catch((e) => VL.toast(e.message, true));
  };
}
