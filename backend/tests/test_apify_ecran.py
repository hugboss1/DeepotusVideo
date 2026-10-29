# -*- coding: utf-8 -*-
"""t364 tâche 2 (28/10/2026) — la clé Apify à l'écran : la ligne APIFY_TOKEN de Réglages › Clés d'API.

Plan docs/superpowers/plans/2026-10-28-veille-apify-t364-socle.md, décision 6 (« comme les autres clés »).
[1] le maillon      scripts/patch_bundle_dzapify.py : marqueur x1, aucun .bak_dzapify, --check « déjà appliqué », ancre
                    unique (vue d'avant), hors couche, aller-retour exact, épingles intouchées, node --check ;
[2] réversible      avant_dzapify == defaire, appelé EN TÊTE de avant_dzdiffusion (fusion #473) ;
[3] la ligne        dzFuNeuves porte la ligne APIFY_TOKEN (texte exact) en tête, la fin du tableau (dzwhatsapp) intacte ;
[4] textes          reglages.cles.apify et apify_why existent en FR et en EN ; l'assemblé est à jour.
Run : & $PY tests/test_apify_ecran.py   (depuis backend/)
"""
import os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE  # noqa: E402
import patch_bundle_dzapify as M  # noqa: E402

NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BUNDLE = REPO / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUNDLE.read_bytes()
B = RAW.decode("utf-8")
AVANT = AIDE.avant_dzapify(B)
LIGNE_KAPSO = '{k:"KAPSO_API_KEY",label:dzT("reglages.cles.kapso"),why:dzT("reglages.cles.kapso_why")}'
CONFIRMER = "await window.__dzDialogue.confirmer("

print("[1] le maillon")
check("1.1 marqueur x1 dans le bundle livré", B.count(M.MARKER) == 1, B.count(M.MARKER))
check("1.2 aucun .bak_dzapify laissé", not M.BAK.exists())
check("1.3 bundle en CRLF, sans LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzapify.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", env=dict(os.environ, PYTHONUTF8="1"))
check("1.4 --check : déjà appliqué", "déjà appliqué" in r.stdout, r.stdout + r.stderr)
check("1.5 ancre unique dans la vue d'avant", all(AVANT.count(a) == 1 for a, _z in M.PAIRES))
check("1.6 hors couche", all(M.hors_couche(B, z) for _a, z in M.PAIRES))
# t345 : dzmcp est posé APRÈS dzapify ; avant_dzapify le défait d'abord, l'aller-retour se lit donc sur le bundle d'avant dzmcp
_SANS_MCP = AIDE.avant_dzmcp(B)
check("1.7 aller-retour exact", M.appliquer(AVANT) == _SANS_MCP and M.defaire(_SANS_MCP) == AVANT)
check("1.8 épingles intouchées", B.count("x.useState(") == 731 and B.count("v2.8.0") == 4 and B.count("DzTracks") == 181
      and B.count(CONFIRMER) == 30)
if NODE:
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "b.js"
        f.write_bytes(RAW)
        r = subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True)
        check("1.9 node --check", r.returncode == 0, r.stderr[:300])

print("[2] réversible")
src = (BACKEND / "tests" / "_i18n_l1_aide.py").read_text("utf-8")
i = src.index("def avant_dzdiffusion(")   # fusion #473 : dzapify rejoué APRÈS dzdiffusion (queue de la chaîne)
check("2.1 avant_dzapify appelé en tête de avant_dzdiffusion", "avant_dzapify(bundle)" in src[i:src.index("def ", i + 10)])
check("2.2 la vue d'avant n'a plus le marqueur", M.MARKER not in AVANT)
check("2.3 la chaîne d'avant défait aussi WhatsApp", "/*whatsapppage*/" not in AIDE.avant_whatsapppage(B))

print("[3] la ligne")
check("3.1 ligne APIFY_TOKEN exacte, en tête des lignes neuves de Clés d'API",
      ("function dzFuNeuves(){return[" + M.MARKER + M.LIGNE_APIFY + ",") in B)
check("3.1b la fin du tableau (remplacement de dzwhatsapp) est intacte", (LIGNE_KAPSO + "]}function dzRgCle(") in B)
check("3.2 la ligne Kapso reste, une fois", B.count(LIGNE_KAPSO) == 1)
check("3.3 la clé n'a pas d'autre ligne", B.count('k:"APIFY_TOKEN"') == 1)

print("[4] textes")
menus = __import__("json").loads((REPO / "frontend" / "shared" / "i18n" / "menus.json").read_text("utf-8"))
for k in ("reglages.cles.apify", "reglages.cles.apify_why"):
    check(f"4.1 {k} en FR et EN", menus.get(k, {}).get("fr") and menus.get(k, {}).get("en"), menus.get(k))
r = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", cwd=str(REPO), env=dict(os.environ, PYTHONUTF8="1"))
check("4.2 l'assemblé est à jour", r.returncode == 0, (r.stdout + r.stderr)[-300:])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
