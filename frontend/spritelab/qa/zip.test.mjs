// zip.test.mjs — lot 5 : un ZIP « store » (sans compression) écrit en pur JS
// pour les tuiles séparées du Tilelab — signatures, CRC-32, offsets, tailles.
import { crc32, zip_store } from "../zip.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
const bytes = (s) => new TextEncoder().encode(s);
ok("crc32('hello') = 0x3610A686", crc32(bytes("hello")) === 0x3610A686, crc32(bytes("hello")).toString(16));
ok("crc32 vide = 0", crc32(new Uint8Array(0)) === 0);
const z = zip_store([{ nom: "a.txt", data: bytes("hello") }, { nom: "b.bin", data: new Uint8Array([0, 255]) }]);
const dv = new DataView(z.buffer);
ok("commence par PK\x03\x04", dv.getUint32(0, true) === 0x04034b50);
const compte = (sig) => { let n = 0; for (let i = 0; i + 4 <= z.length; i++) if (dv.getUint32(i, true) === sig) n++; return n; };
ok("deux en-têtes locaux, deux entrées centrales, une fin", compte(0x04034b50) === 2 && compte(0x02014b50) === 2 && compte(0x06054b50) === 1);
ok("taille = 30+5+5 + 30+5+2 + 46+5 + 46+5 + 22 = 201", z.length === 201, z.length);
const fin = z.length - 22;
ok("fin de répertoire : 2 entrées, taille du répertoire 102, offset 77", dv.getUint16(fin + 10, true) === 2 && dv.getUint32(fin + 12, true) === 102 && dv.getUint32(fin + 16, true) === 77);
ok("en-tête local a.txt : méthode 0, CRC, tailles 5, nom", dv.getUint16(8, true) === 0 && dv.getUint32(14, true) === 0x3610A686 && dv.getUint32(18, true) === 5 && dv.getUint32(22, true) === 5 && dv.getUint16(26, true) === 5 && new TextDecoder().decode(z.subarray(30, 35)) === "a.txt" && new TextDecoder().decode(z.subarray(35, 40)) === "hello");
ok("nom vide ou données absentes → refus", (() => { try { zip_store([{ nom: "", data: bytes("x") }]); return false; } catch { return true; } })() && (() => { try { zip_store([]); return false; } catch { return true; } })());
if (echecs.length) { console.error("ECHECS zip :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA zip : PASS (8 controles)");
