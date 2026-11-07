// qa/formats-n8.test.mjs — t418 (Photolab N8, photocraft 0.21) : formats. Fonctions PURES ; moteur prouvé par backend/tests/test_photolab_n8.py.
import { FORMATS_EXPORT, formatExport, corpsExport, FORMATS_OUVERTURE, routeFichier, ACCEPTES, libelleFormat } from "../js/mod-fichier.js";
import { corpsCopie } from "../js/mod-documents.js";
import { readFileSync } from "node:fs";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, JSON.stringify(detail)); } }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dico = JSON.parse(readFileSync(new URL("../../shared/i18n/photolab.json", import.meta.url), "utf8"));
const routes = readFileSync(new URL("../../../backend/app/api/photolab_routes.py", import.meta.url), "utf8");
const moteur = readFileSync(new URL("../../../backend/app/services/photolab_moteur.py", import.meta.url), "utf8");
const liste = (src, nom) => [...((src.match(new RegExp(nom + " = \\(([\\s\\S]*?)\\)\\n")) || [])[1] || "").matchAll(/"([^"]+)"/g)].map((m) => m[1]);
const T = (c) => (dico[c] ? dico[c].fr : c);

const pont = liste(routes, "FORMATS");
check("1.1 neuf formats d'export de plus", ["jxl", "dds", "exr", "dpx", "cin", "hdr", "bmp", "gif", "qoi"].every((f) => formatExport(f)));
check("1.2 chaque format est accepté par le pont", FORMATS_EXPORT.every((f) => pont.includes(f.format)), pont);
check("1.3 TIFF et DDS ont leur compression", eq(formatExport("tif").compressions, ["none", "lzw", "zip"]) && eq(formatExport("dds").compressions, ["none", "bc1", "bc2", "bc3"]));
check("1.4 le corps porte la compression", eq(corpsExport("tif", "a", 90, "lzw"), { format: "tif", nom: "a", compression: "lzw" }));
check("1.5 sans objet sur un autre format", eq(corpsExport("png", "a", 90, "lzw"), { format: "png", nom: "a" }));
check("1.6 compression par défaut : clé absente", eq(corpsExport("tif", "a"), { format: "tif", nom: "a" }));
check("1.7 une valeur inconnue ne part pas", eq(corpsExport("dds", "a", 90, "lzw"), { format: "dds", nom: "a" }));
check("1.8 l'Enregistrer une copie suit", corpsCopie({ format: "dds", nom: "a", compression: "bc1" }).compression === "bc1");
check("1.9 JPEG XL nommé sans perte", libelleFormat(formatExport("jxl"), T) === dico["photolab.export.jxl"].fr);

const py = liste(moteur, "FORMATS_OUVERTURE");
check("2.1 même liste que le pont", eq([...FORMATS_OUVERTURE].sort(), [...py].sort()), [FORMATS_OUVERTURE.length, py.length]);
for (const e of ["xcf", "dcm", "dicom", "iff", "lbm", "fits", "hdr", "cin", "qoi", "pcx", "xpm", "ico", "ppm", "pfm"])
  check(`2.2 .${e} ouvert par /importer`, routeFichier("a." + e, 10) === "importer", routeFichier("a." + e, 10));
check("2.3 JPEG XL et HEIC ne s'ouvrent pas", !FORMATS_OUVERTURE.includes("jxl") && !FORMATS_OUVERTURE.includes("heic"));
check("2.4 le sélecteur de fichiers les propose", ACCEPTES.includes(".xcf") && ACCEPTES.includes(".dcm"));
for (const c of ["photolab.export.compression", "photolab.export.compression.none", "photolab.export.compression.lzw", "photolab.export.compression.zip",
  "photolab.export.compression.bc1", "photolab.export.compression.bc2", "photolab.export.compression.bc3", "photolab.export.jxl"])
  check(`3.1 ${c} fr et en`, dico[c]?.fr && dico[c]?.en, c);

console.log(`formats-n8 : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
