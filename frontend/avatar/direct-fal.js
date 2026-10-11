/* Avatar live t168f (11/10/2026) — le Direct par fal (decart/lucy-2-5/realtime), la clé fal seule.

   La page ne parle qu'au BACKEND (/api/avatar-live/fal/relais, JSON) : c'est lui qui tient le WebSocket fal, clé en
   en-tête — la page ne voit ni clé ni jeton. La vidéo, elle, va pair-à-pair navigateur ⇄ Decart (WebRTC), comme avec
   le SDK Decart. Protocole relevé par l'essai réel du 11/10 (spec 2026-10-10-higgsfield-genjutsu-inventaire.md,
   section 10) : la page envoie l'état {prompt, personnage_id} EN PREMIER, reçoit ready puis iceServers, envoie son
   offre, reçoit la réponse ; les candidats ICE vont dans les deux sens. Une consigne à chaud renvoie l'état COMPLET
   (fal le remplace). Le serveur coupe à la durée réservée et le dit par {type: "fin"}.

   Même interface que la connexion du SDK Decart vue par direct.js : set(état), disconnect(), on("sessionEnded" |
   "error", f). Les erreurs portent une clé du dictionnaire (e.cle) : direct.js les traduit. */

const STUN_SECOURS = [{ urls: "stun:stun.l.google.com:19302" }];   // celui que fal donne (relevé du 11/10)

function erreur(cle, vars, texte) {
  const e = new Error(texte || cle);
  e.cle = cle; e.vars = vars || {};
  return e;
}

export function connecterFal(flux, { relais, etat, onRemoteStream, delaiIceMs = 1000, delaiReponseMs = 15000,
  FabriqueWS = WebSocket, FabriquePC = RTCPeerConnection, origine = location } = {}) {
  const ecouteurs = {};
  const emettre = (n, v) => (ecouteurs[n] || []).forEach((f) => { try { f(v); } catch (x) { /* écouteur fautif */ } });
  const url = (origine.protocol === "https:" ? "wss://" : "ws://") + origine.host + relais;
  const ws = new FabriqueWS(url);
  let pc = null, pret = false, fini = false, ferme = false, attenteIce = null;
  const enAttente = [];
  const envoyer = (m) => { if (ws.readyState === 1) ws.send(JSON.stringify(m)); };
  const fermer = () => {
    ferme = true; clearTimeout(attenteIce);
    try { ws.close(1000); } catch (x) { /* déjà fermé */ }
    try { pc && pc.close(); } catch (x) { /* déjà fermé */ }
  };
  const api = {
    set: (e) => { envoyer(Object.assign({ type: "etat" }, e)); return Promise.resolve(); },
    disconnect: fermer,
    on: (n, f) => { (ecouteurs[n] = ecouteurs[n] || []).push(f); },
  };
  return new Promise((ok, ko) => {
    const minuteur = setTimeout(() => echec(erreur("avatar.direct.fal_sans_reponse", { s: delaiReponseMs / 1000 })), delaiReponseMs);
    function echec(e) {
      if (pret) { emettre("error", e); return; }
      clearTimeout(minuteur); fermer(); ko(e);
    }
    async function creerPc(ice) {
      if (pc) return;
      clearTimeout(attenteIce);
      pc = new FabriquePC({ iceServers: Array.isArray(ice) && ice.length ? ice : STUN_SECOURS });
      flux.getTracks().forEach((t) => pc.addTrack(t, flux));
      pc.ontrack = (e) => { if (onRemoteStream) onRemoteStream(e.streams && e.streams[0] ? e.streams[0] : new MediaStream([e.track])); };
      pc.onicecandidate = (e) => {
        if (e.candidate) envoyer({ type: "icecandidate", candidate: { candidate: e.candidate.candidate, sdpMid: e.candidate.sdpMid, sdpMLineIndex: e.candidate.sdpMLineIndex } });
      };
      pc.onconnectionstatechange = () => { if (pc && pc.connectionState === "failed") echec(erreur("avatar.direct.fal_webrtc")); };
      const offre = await pc.createOffer();
      await pc.setLocalDescription(offre);
      envoyer({ type: "offer", sdp: offre.sdp });
    }
    ws.onopen = () => envoyer(Object.assign({ type: "etat" }, etat));
    ws.onmessage = async (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch (x) { return; }
      const ty = String((m && m.type) || "").toLowerCase();
      try {
        if (ty === "ready") {
          if (m.iceServers) await creerPc(m.iceServers);
          else attenteIce = setTimeout(() => { creerPc(null).catch(echec); }, delaiIceMs);
        } else if (ty === "iceservers") await creerPc(m.iceServers);
        else if (ty === "answer" && pc && !pret && m.sdp) {
          await pc.setRemoteDescription({ type: "answer", sdp: m.sdp });
          pret = true; clearTimeout(minuteur);
          for (const c of enAttente.splice(0)) await pc.addIceCandidate(c);
          ok(api);
        } else if (ty === "icecandidate" && m.candidate) {
          if (pc && pret) await pc.addIceCandidate(m.candidate); else enAttente.push(m.candidate);
        } else if (ty === "error" || ty === "x-fal-error") echec(erreur("avatar.direct.fal_refus", { raison: m.error || m.reason || "fal" }));
        else if (ty === "fin") {
          fini = true;
          emettre("sessionEnded", { reason: m.raison, secondes: m.secondes, reel_usd: m.reel_usd });
          fermer();
        }
      } catch (x) { echec(x); }
    };
    ws.onclose = (ev) => {
      if (!pret) echec(erreur("avatar.direct.fal_relais_ferme", { code: ev.code }));
      else if (!fini && !ferme) { fini = true; emettre("sessionEnded", { reason: "relais " + ev.code }); }
    };
  });
}
