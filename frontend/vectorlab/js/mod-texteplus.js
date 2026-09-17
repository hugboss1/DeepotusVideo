// mod-texteplus.js — le texte de classe Affinity, côté PUR (lot F) : la
// mesure d'une ligne est INJECTABLE (au banc, une approximation ; au
// navigateur, measureText du canvas), la coupe des lignes suit les mots,
// les retours forcés et coupe aux caractères un mot trop long, les
// <tspan> s'alignent (gauche, centre, droite, justifié par textLength) avec
// retrait de première ligne, interligne et débordement. Module FEUILLE.

const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const _corps = (s) => Number((s && s.corps) || 16);

export function mesure_approx(texte, style = {}) {
  const k = 0.55 * (style.graisse === "bold" || +style.graisse >= 600 ? 1.08 : 1);
  return String(texte || "").length * _corps(style) * k;
}

export function couper_lignes(contenu, largeur, style = {}, mesure = mesure_approx) {
  const m = (t) => mesure(t, style);
  const lignes = [];
  for (const para of String(contenu ?? "").split("\n")) {
    const mots = para.split(" ").filter((w, i, a) => w.length || a.length === 1);
    let ligne = "";
    const pousser = () => { lignes.push(ligne); ligne = ""; };
    for (const mot of mots) {
      const essai = ligne ? ligne + " " + mot : mot;
      if (m(essai) <= largeur || !ligne && m(mot) <= largeur) { ligne = essai; continue; }
      if (ligne) pousser();
      if (m(mot) <= largeur) { ligne = mot; continue; }
      // un mot plus long que la largeur : aux caractères
      let morceau = "";
      for (const ch of mot) {
        if (m(morceau + ch) > largeur && morceau) { lignes.push(morceau); morceau = ""; }
        morceau += ch;
      }
      ligne = morceau;
    }
    lignes.push(ligne);
  }
  return lignes.length ? lignes : [""];
}

// o = {x, y, w, h, style:{corps, interligne, aligner, retrait}} ; les
// lignes qui sortent du cadre tombent (deborde = vrai)
export function cadre_tspans(o, lignes, mesure = mesure_approx) {
  const s = o.style || {};
  const corps = _corps(s), inter = Number(s.interligne || 1.25), al = s.aligner || "gauche", retrait = Number(s.retrait || 0);
  const out = [];
  let deborde = false;
  lignes.forEach((l, i) => {
    const y = o.y + corps + i * corps * inter;
    if (y > o.y + o.h + 1e-9) { deborde = true; return; }
    const r = i === 0 ? retrait : 0;
    let x = o.x + r, anc = "", just = "";
    if (al === "centre") { x = o.x + o.w / 2; anc = ` text-anchor="middle"`; }
    else if (al === "droite") { x = o.x + o.w; anc = ` text-anchor="end"`; }
    else if (al === "justifie") {
      const derniere = i === lignes.length - 1 || lignes[i + 1] === "";
      if (!derniere && l.includes(" ")) just = ` textLength="${o.w - r}" lengthAdjust="spacing"`;
    }
    out.push(`<tspan x="${_n(x)}" y="${_n(y)}"${anc}${just}>${esc(l)}</tspan>`);
  });
  void mesure;
  return { html: out.join(""), deborde };
}
const _n = (v) => String(Math.round(v * 100) / 100);
