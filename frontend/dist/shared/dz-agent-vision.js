// dz-agent-vision.js — assistant « Demander à Deepotus », lot A5 (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md
// § 2 « Vision en secours ») : UNE image de l'onglet courant, prise APRÈS l'accord de l'utilisateur dans le tiroir.
// getDisplayMedia (le navigateur demande lui-même le partage : second accord), une seule image, pistes coupées aussitôt.
// L'image est réduite à 1 280 px au plus (grand côté) et encodée en JPEG 0,8. Refus si l'utilisateur partage autre
// chose que CET onglet (les coordonnées rendues ne vaudraient rien). SOURCE : frontend/shared ; copie identique :
// frontend/dist/shared (banc backend/tests/test_agent_ecran.py).
import { reduire, memeOnglet } from "./dz-agent-logique.js";

export function captureDisponible() {
  const md = navigator.mediaDevices;
  return !!(window.isSecureContext && md && typeof md.getDisplayMedia === "function");
}

const image = () => new Promise((ok) => requestAnimationFrame(() => ok()));
function nouvelleImage(video) {
  return new Promise((ok) => {
    const t = setTimeout(ok, 600);
    if (typeof video.requestVideoFrameCallback === "function") video.requestVideoFrameCallback(() => { clearTimeout(t); ok(); });
  });
}

// avant() masque le tiroir, apres() le rétablit. Rend {mime, b64, largeur, hauteur, vue:{l, h}}.
// Erreurs : NotAllowedError (partage refusé), Error("autre-surface") (pas cet onglet), Error("capture-vide").
export async function capturer({ avant, apres } = {}) {
  const flux = await navigator.mediaDevices.getDisplayMedia({
    video: { displaySurface: "browser" }, audio: false,
    preferCurrentTab: true, selfBrowserSurface: "include", surfaceSwitching: "exclude", monitorTypeSurfaces: "exclude",
  });
  try {
    const piste = flux.getVideoTracks()[0];
    const reglages = piste && piste.getSettings ? piste.getSettings() : {};
    if (reglages.displaySurface && reglages.displaySurface !== "browser") throw new Error("autre-surface");
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.srcObject = flux;
    await video.play();
    if (avant) avant();
    try {
      await image();
      await image();
      await nouvelleImage(video);                 // une image prise APRÈS le masquage du tiroir
      const vue = { l: window.innerWidth, h: window.innerHeight };
      const vw = video.videoWidth, vh = video.videoHeight;
      if (!memeOnglet(vw, vh, vue)) throw new Error("autre-surface");
      const d = reduire(vw, vh);
      if (!d) throw new Error("capture-vide");
      const c = document.createElement("canvas");
      c.width = d.l;
      c.height = d.h;
      c.getContext("2d").drawImage(video, 0, 0, d.l, d.h);
      const url = c.toDataURL("image/jpeg", 0.8);
      return { mime: "image/jpeg", b64: url.slice(url.indexOf(",") + 1), largeur: d.l, hauteur: d.h, vue };
    } finally {
      if (apres) apres();
    }
  } finally {
    flux.getTracks().forEach((t) => t.stop());
  }
}
