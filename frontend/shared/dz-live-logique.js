// dz-live-logique.js — t318 (28/10/2026, lot D4 « live multi-destinations »), la logique PURE du direct (aucun DOM) :
// choix du format d'encodage, lecture de la santé du flux, destinations et champs à saisir, message d'annonce.
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared. Banc : backend/tests/test_live_ecran.py
// (joué sous node). Plan docs/superpowers/plans/2026-10-28-t318-live.md, spec boîte à outils §8.6.

// H.264 si le navigateur le donne (ffmpeg le réencode de toute façon : un seul encodage côté serveur), sinon VP8/VP9
export const MIMES_LIVE = ["video/webm;codecs=h264,opus", "video/webm;codecs=vp8,opus", "video/webm;codecs=vp9,opus",
  "video/webm"];
export const MORCEAU_MS = 250;                       // latence visée < 5 s (spec §8.6)
export const TAMPON_MAX = 32 * 1024 * 1024;          // au-delà, un morceau est perdu plutôt que la page étouffée

export function choisirMimeLive(supporte) {
  for (const m of MIMES_LIVE) { try { if (supporte(m)) return m; } catch (e) { /* type refusé */ } }
  return "";
}

// les plateformes du direct (comptes.LIVE côté serveur) et les champs que la boîte demande pour chacune
export const PLATEFORMES = ["twitch", "youtube_live", "kick", "rtmp", "discord"];
export const CHAMPS = {
  twitch: { cle: "TWITCH_STREAM_KEY", serveur: "TWITCH_SERVEUR", serveurRequis: false, lien: null, handle: true },
  youtube_live: { cle: "YOUTUBE_STREAM_KEY", serveur: "YOUTUBE_LIVE_SERVEUR", serveurRequis: false, lien: "YOUTUBE_LIVE_LIEN", handle: false },
  kick: { cle: "KICK_STREAM_KEY", serveur: "KICK_SERVEUR", serveurRequis: true, lien: null, handle: true },
  rtmp: { cle: "RTMP_CLE", serveur: "RTMP_SERVEUR", serveurRequis: true, lien: "RTMP_LIEN", handle: false },
  discord: { cle: "DISCORD_WEBHOOK", serveur: null, serveurRequis: false, lien: null, handle: false },
};
export const SERVEURS = { twitch: "rtmp://live.twitch.tv/app", youtube_live: "rtmp://a.rtmp.youtube.com/live2" };

// le corps de POST /api/comptes pour une destination neuve ; null si un champ requis manque
export function corpsAjout(plateforme, saisie, espace) {
  const c = CHAMPS[plateforme];
  if (!c) return null;
  const s = saisie || {};
  const t = (k) => (typeof s[k] === "string" ? s[k].trim() : "");
  const valeurs = {};
  if (t("cle")) valeurs[c.cle] = t("cle");
  if (c.serveur && t("serveur")) valeurs[c.serveur] = t("serveur");
  if (c.lien && t("lien")) valeurs[c.lien] = t("lien");
  const cleRequise = plateforme !== "rtmp";
  if ((cleRequise && !valeurs[c.cle]) || (c.serveurRequis && !valeurs[c.serveur])) return null;
  const corps = { plateforme, libelle: t("libelle"), handle: c.handle ? t("handle").replace(/^@/, "") : "", valeurs };
  if (espace) corps.espace_id = espace;
  return corps;
}

// le lien public d'une destination (comme live._lien côté serveur), "" s'il n'y en a pas
export function lienDe(compte) {
  if (!compte) return "";
  const c = CHAMPS[compte.plateforme];
  const pub = {};
  for (const ch of compte.champs || []) if (!ch.secret) pub[ch.nom] = ch.valeur;
  const l = c && c.lien ? String(pub[c.lien] || "").trim() : "";
  if (/^https:\/\/[^\s|[\]\\"']{1,290}$/.test(l)) return l;
  const h = String(compte.handle || "").trim().replace(/^@/, "");
  if (!/^[A-Za-z0-9_]{2,40}$/.test(h)) return "";
  if (compte.plateforme === "twitch") return "https://www.twitch.tv/" + h;
  if (compte.plateforme === "kick") return "https://kick.com/" + h;
  return "";
}

// la santé d'ensemble : coupe (rien ne part), faible (ffmpeg ne suit pas le temps réel), bon, ou attente
export function niveauFlux(e) {
  if (!e) return "attente";
  if (e.etat === "arrete" || e.etat === "en_panne") return "coupe";
  if (e.etat !== "en_direct") return "attente";
  if ((typeof e.vitesse === "number" && e.vitesse < 0.9) || (typeof e.fps === "number" && e.fps < 20)) return "faible";
  return "bon";
}

export function formatDebit(kbps, langue) {
  if (typeof kbps !== "number" || !(kbps >= 0)) return "—";
  const sep = langue === "en" ? "." : ",";
  return kbps >= 1000 ? (kbps / 1000).toFixed(1).replace(".", sep) + " Mb/s" : Math.round(kbps) + " kb/s";
}

// le message d'annonce par défaut (le serveur y ajoute les liens publics des destinations)
export function messageAnnonce(titre, T) {
  const t = String(titre || "").trim();
  return t ? T("live.annonce.defaut_titre", { titre: t }) : T("live.annonce.defaut");
}

// l'instant d'un marqueur : ms depuis le début de la capture (celui de la piste des clics, t317 le lit)
export function instantMarqueur(maintenant, debut) {
  return Math.max(0, Math.round((Number(maintenant) || 0) - (Number(debut) || 0)));
}
