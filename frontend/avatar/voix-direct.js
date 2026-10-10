/* Avatar live G5 (t166, 10/10/2026) — la VOIX EN DIRECT, côté navigateur.

   micro ─► AudioWorklet (PCM 16 kHz, segments d'1 s) ─► POST /api/avatar-live/sessions/voix (le serveur convertit :
   ElevenLabs ou Voixbox RVC, la clé ne vient jamais ici) ─► PCM converti ─► lecture enchaînée dans un
   MediaStreamAudioDestinationNode = la piste audio ENVOYÉE à Decart.
   caméra ─► MediaStreamTrackProcessor ─► file d'attente de `retardMs` ─► MediaStreamTrackGenerator = la piste vidéo
   ENVOYÉE à Decart. Les deux arrivent donc ensemble chez Decart, qui rend image et voix calées (le serveur Decart
   retarde lui-même l'audio de sa propre latence de rendu).
   Sans MediaStreamTrackProcessor (navigateur non Chromium) : la vidéo part sans retard et la page le DIT. */
const SR = 16000;

export function retardVideoPossible() {
  return typeof window.MediaStreamTrackProcessor === "function" && typeof window.MediaStreamTrackGenerator === "function";
}

function retarderVideo(piste, retardMs) {
  const proc = new window.MediaStreamTrackProcessor({ track: piste });
  const gen = new window.MediaStreamTrackGenerator({ kind: "video" });
  const lecteur = proc.readable.getReader();
  const ecrivain = gen.writable.getWriter();
  const file = [];
  let fini = false;
  (async () => {
    for (;;) {
      const { value, done } = await lecteur.read();
      if (done || fini) { if (value) value.close(); break; }
      file.push({ t: performance.now(), f: value });
    }
  })();
  const tic = setInterval(async () => {
    const maintenant = performance.now();
    while (file.length && maintenant - file[0].t >= retardMs) {
      const { f } = file.shift();
      try { await ecrivain.write(f); } catch (e) { f.close(); }
    }
    while (file.length > 240) file.shift().f.close();      // garde-fou mémoire (8 s à 30 i/s)
  }, 10);
  return { piste: gen, arreter: () => { fini = true; clearInterval(tic); file.splice(0).forEach((x) => x.f.close()); try { lecteur.cancel(); } catch (e) { /* déjà */ } } };
}

/**
 * Ouvre la chaîne voix. `convertir(pcmArrayBuffer) -> Promise<ArrayBuffer pcm>` parle au serveur.
 * Rend { flux: MediaStream à envoyer à Decart (vidéo retardée + voix convertie), stats, arreter() }.
 */
export async function ouvrirVoixDirect({ camera, micro, convertir, retardMs, surStats, segmentMs = 500, enVolMax = 4 }) {
  const ctx = new AudioContext({ sampleRate: SR });
  await ctx.audioWorklet.addModule(new URL("./voix-capture.js", import.meta.url));
  const source = ctx.createMediaStreamSource(new MediaStream(micro.getAudioTracks()));
  const capteur = new AudioWorkletNode(ctx, "voix-capture", { processorOptions: { segment: Math.round(SR * segmentMs / 1000) } });
  const muet = ctx.createGain(); muet.gain.value = 0;                // le micro brut n'est JAMAIS entendu ni envoyé
  source.connect(capteur).connect(muet).connect(ctx.destination);
  const sortie = ctx.createMediaStreamDestination();
  const stats = { segments: 0, pertes: 0, latences: [], retardMs };
  // Mesuré le 10/10 : une conversion dure PLUS qu'un segment (~1,5 s pour 0,5 s) -> plusieurs requêtes en vol, qui
  // reviennent dans le désordre. Chaque segment porte son numéro ; la lecture suit l'ORDRE d'envoi ; un segment
  // perdu ou sauté devient un SILENCE de sa durée (le calage sur l'image tient).
  let tete = 0;                                                    // instant de lecture du prochain segment
  let enVol = 0, prochainEnvoi = 0, prochainLu = 0;
  const prets = new Map();
  function jouer(i16) {
    const tampon = ctx.createBuffer(1, Math.max(1, i16.length), SR);
    const f32 = tampon.getChannelData(0);
    for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 0x8000;
    const n = Math.min(80, f32.length >> 2);                       // fondu de 5 ms aux bords : pas de clic aux jointures
    for (let i = 0; i < n; i++) { f32[i] *= i / n; f32[f32.length - 1 - i] *= i / n; }
    const lecteur = ctx.createBufferSource(); lecteur.buffer = tampon; lecteur.connect(sortie);
    tete = Math.max(tete, ctx.currentTime + 0.05);
    lecteur.start(tete); tete += tampon.duration;
  }
  function vider() {
    while (prets.has(prochainLu)) { jouer(prets.get(prochainLu)); prets.delete(prochainLu); prochainLu++; }
  }
  capteur.port.onmessage = async (ev) => {
    const no = prochainEnvoi++;
    const taille = ev.data.byteLength >> 1;
    if (enVol >= enVolMax) {                                       // le serveur ne suit plus : on saute (silence)
      stats.pertes++; prets.set(no, new Int16Array(taille)); vider(); if (surStats) surStats(stats); return;
    }
    enVol++;
    const t0 = performance.now();
    try {
      const pcm = await convertir(ev.data);
      stats.latences.push(Math.round(performance.now() - t0)); if (stats.latences.length > 30) stats.latences.shift();
      prets.set(no, new Int16Array(pcm));
      stats.segments++;
    } catch (e) {
      stats.pertes++; stats.erreur = e.message || String(e);
      prets.set(no, new Int16Array(taille));
    } finally {
      enVol--;
      vider();
      if (surStats) surStats(stats);
    }
  };
  const video = camera.getVideoTracks()[0];
  const ret = retardVideoPossible() ? retarderVideo(video, retardMs) : null;
  const flux = new MediaStream([ret ? ret.piste : video, sortie.stream.getAudioTracks()[0]]);
  return {
    flux, stats, videoRetardee: !!ret,
    arreter: () => { try { ret && ret.arreter(); } catch (e) { /* rien */ } try { ctx.close(); } catch (e) { /* rien */ } },
  };
}
