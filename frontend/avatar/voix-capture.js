/* Avatar live G5 (t166) — AudioWorklet de capture : le micro en PCM 16 bits mono, découpé en segments de
   `segment` échantillons, postés au fil principal. Le contexte audio est ouvert à 16 kHz (sampleRate), donc un
   échantillon reçu = un échantillon envoyé : aucun rééchantillonnage ici. */
class VoixCapture extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.taille = (options && options.processorOptions && options.processorOptions.segment) || 16000;
    this.tampon = new Int16Array(this.taille);
    this.n = 0;
  }
  process(entrees) {
    const canal = entrees[0] && entrees[0][0];
    if (canal) {
      for (let i = 0; i < canal.length; i++) {
        const v = Math.max(-1, Math.min(1, canal[i]));
        this.tampon[this.n++] = v < 0 ? v * 0x8000 : v * 0x7fff;
        if (this.n === this.taille) {
          this.port.postMessage(this.tampon.buffer, [this.tampon.buffer]);
          this.tampon = new Int16Array(this.taille);
          this.n = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor("voix-capture", VoixCapture);
