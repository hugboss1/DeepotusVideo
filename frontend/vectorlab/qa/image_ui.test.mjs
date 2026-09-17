// image_ui.test.mjs — la logique PURE de mod-image (résolution d'href,
// pose ajustée à la page, normalisation du rognage, hrefs d'un document,
// liste de la Bibliothèque de repli). initImage n'est jamais importé.
import { href_est_absolu, image_url, image_poser_spec, rognage_normaliser,
         image_hrefs, libListeHTML } from "../js/mod-image.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

ok("absolu : data/blob/http/https//", ["data:x", "blob:x", "http://a", "https://a", "/api/x"]
   .every(href_est_absolu) && !href_est_absolu("img1.png") && !href_est_absolu(""));
ok("image_url résout un nom relatif dans le magasin du doc",
   image_url("ab c", "img1.png") === "/api/vector/docs/ab%20c/images/img1.png",
   image_url("ab c", "img1.png"));
ok("image_url laisse l'absolu", image_url("d", "/api/images/x.png") === "/api/images/x.png");

{
  const s = image_poser_spec({ w: 1600, h: 800 }, { w: 400, h: 300 });
  ok("pose : contenue dans la page, centrée, ratio gardé",
     s.w === 400 && s.h === 200 && s.x === 0 && s.y === 50, JSON.stringify(s));
  const p = image_poser_spec({ w: 100, h: 50 }, { w: 400, h: 300 });
  ok("pose : une petite image garde sa taille native, centrée",
     p.w === 100 && p.h === 50 && p.x === 150 && p.y === 125, JSON.stringify(p));
  let refus = 0;
  try { image_poser_spec({ w: 0, h: 5 }, { w: 4, h: 4 }); } catch { refus++; }
  ok("pose : taille native nulle refusée", refus === 1);
}
{
  const nat = { w: 800, h: 400 };
  ok("rognage entier → null", rognage_normaliser({ x: 0, y: 0, w: 800, h: 400 }, nat) === null);
  ok("rognage null → null", rognage_normaliser(null, nat) === null);
  const r = rognage_normaliser({ x: -10, y: 10, w: 900, h: 50.6 }, nat);
  ok("rognage borné à l'image, arrondi", JSON.stringify(r) === JSON.stringify({ x: 0, y: 10, w: 800, h: 51 }), JSON.stringify(r));
  const m = rognage_normaliser({ x: 799, y: 399, w: 0, h: 0 }, nat);
  ok("rognage : au moins 1 px", m.w === 1 && m.h === 1);
}
{
  const doc = { v: 1, taille: { w: 1, h: 1 }, calques: [
    { id: "c1", objets: [{ id: "a", type: "image", href: "img1.png", nat: { w: 1, h: 1 }, x: 0, y: 0, w: 1, h: 1 },
      { id: "g", type: "groupe", enfants: [{ id: "b", type: "image", href: "img2.png", nat: { w: 1, h: 1 }, x: 0, y: 0, w: 1, h: 1 },
        { id: "c", type: "image", href: "img1.png", nat: { w: 1, h: 1 }, x: 0, y: 0, w: 1, h: 1 }] }] },
    { id: "c2", objets: [{ id: "r", type: "rect", x: 0, y: 0, w: 1, h: 1 }] }] };
  ok("image_hrefs : uniques, dans l'ordre, groupes compris",
     JSON.stringify(image_hrefs(doc)) === JSON.stringify(["img1.png", "img2.png"]));
  ok("image_hrefs : état vide → []", image_hrefs({ calques: [{ id: "c", objets: [] }] }).length === 0);
}
{
  const h = libListeHTML([{ filename: "a<b>.png", width: 10, height: 20 }, { filename: "z.png" }], "");
  ok("libListeHTML échappe et porte le nom en data", h.includes("&lt;b&gt;") && h.includes('data-lib-nom="a&lt;b&gt;.png"'), h);
  ok("libListeHTML : vignette sur /api/images/<nom>", h.includes('src="/api/images/a%3Cb%3E.png"'), h);
  const v = libListeHTML([], "chat");
  ok("libListeHTML : état vide qui NOMME la recherche", v.includes("chat") && v.includes("Aucune image"), v);
  const f = libListeHTML([{ filename: "chat.png" }, { filename: "chien.png" }], "CHA");
  ok("libListeHTML filtre insensible à la casse", f.includes("chat.png") && !f.includes("chien.png"));
}

if (echecs.length) {
  console.error("ECHECS image_ui :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA image_ui : PASS (16 controles)");
